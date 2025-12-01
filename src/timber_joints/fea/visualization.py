"""FEA visualization utilities for OCP CAD Viewer."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
from OCP.gp import gp_Pnt
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound

from build123d import Compound

from .backends.calculix import read_frd_nodes, read_frd_displacements, read_frd_stresses, compute_von_mises


# C3D4 tetrahedron face definitions (0-indexed into node list)
# Each face is defined with outward-pointing normal using right-hand rule
# Face i is opposite to node i
C3D4_FACE_INDICES = [
    (1, 3, 2),  # Face 0: opposite to node 0
    (0, 2, 3),  # Face 1: opposite to node 1
    (0, 3, 1),  # Face 2: opposite to node 2
    (0, 1, 2),  # Face 3: opposite to node 3
]


def value_to_limit_color(value: float, limit: float) -> str:
    """Convert a value to a color based on fraction of allowable limit.
    
    Color scheme (engineering standard):
    - 0-50% of limit: Blue → Cyan (safe)
    - 50-80% of limit: Cyan → Green (acceptable)
    - 80-100% of limit: Green → Yellow → Orange (warning)
    - 100-120% of limit: Orange → Red (exceeded)
    - >120% of limit: Magenta/Purple (critical failure)
    
    Args:
        value: The actual value
        limit: The allowable limit (e.g., L/300 for displacement, f_m_k for stress)
        
    Returns:
        Hex color string like "#FF0000"
    """
    if limit <= 0:
        return "#0000FF"  # Blue if no limit
    
    # Ratio of value to limit
    ratio = value / limit
    
    if ratio <= 0.5:
        # Blue (0%) to Cyan (50%)
        t = ratio / 0.5
        r, g, b = 0, int(255 * t), 255
    elif ratio <= 0.8:
        # Cyan (50%) to Green (80%)
        t = (ratio - 0.5) / 0.3
        r, g, b = 0, 255, int(255 * (1 - t))
    elif ratio <= 1.0:
        # Green (80%) to Yellow (100%) - warning zone starts
        t = (ratio - 0.8) / 0.2
        r, g, b = int(255 * t), 255, 0
    elif ratio <= 1.2:
        # Yellow (100%) to Red (120%) - limit exceeded
        t = (ratio - 1.0) / 0.2
        r, g, b = 255, int(255 * (1 - t)), 0
    else:
        # Red (120%) to Magenta (150%+) - critical
        t = min(1.0, (ratio - 1.2) / 0.3)
        r, g, b = 255, 0, int(255 * t)
    
    return f"#{r:02X}{g:02X}{b:02X}"


def get_limit_color_bands(limit: float, n_bands: int = 2048) -> List[Tuple[float, float, str]]:
    """Get discrete color bands for limit-based colormap.
    
    Bands are distributed to give more resolution near the limit:
    - 2/3 of bands from 0 to limit (0-100%)
    - 1/3 of bands from limit to 1.5*limit (100-150%)
    
    Returns list of (lower_value, upper_value, hex_color) tuples.
    """
    bands = []
    
    # Bands below limit (0-100%): 2/3 of total bands
    n_below = (n_bands * 2) // 3
    for i in range(n_below):
        lower = limit * i / n_below
        upper = limit * (i + 1) / n_below
        mid = (lower + upper) / 2
        color = value_to_limit_color(mid, limit)
        bands.append((lower, upper, color))
    
    # Bands above limit (100-150%): 1/3 of total bands
    n_above = n_bands - n_below
    for i in range(n_above):
        lower = limit * (1.0 + 0.5 * i / n_above)
        upper = limit * (1.0 + 0.5 * (i + 1) / n_above)
        mid = (lower + upper) / 2
        color = value_to_limit_color(mid, limit)
        bands.append((lower, upper, color))
    
    return bands


# Legacy function for backward compatibility
def value_to_rainbow_color(value: float, min_val: float, max_val: float) -> str:
    """Convert a value to a rainbow color (blue -> cyan -> green -> yellow -> red).
    
    Args:
        value: The value to colormap
        min_val: Minimum value (maps to blue)
        max_val: Maximum value (maps to red)
        
    Returns:
        Hex color string like "#FF0000"
    """
    if max_val <= min_val:
        return "#0000FF"  # All blue if no range
    
    # Normalize to 0-1, treat max as "limit"
    normalized = (value - min_val) / (max_val - min_val)
    return value_to_limit_color(normalized * max_val, max_val)


def get_color_bands(n_bands: int = 12) -> List[Tuple[float, float, str]]:
    """Get discrete color bands for the rainbow colormap.
    
    Returns list of (lower_frac, upper_frac, hex_color) tuples.
    """
    bands = []
    for i in range(n_bands):
        lower = i / n_bands
        upper = (i + 1) / n_bands
        mid = (lower + upper) / 2
        color = value_to_limit_color(mid, 1.0)
        bands.append((lower, upper, color))
    return bands


def read_mesh_elements(mesh_file: str) -> List[List[int]]:
    """Read tetrahedral element connectivity from CalculiX mesh file.
    
    Args:
        mesh_file: Path to mesh.inp file
        
    Returns:
        List of [n1, n2, n3, n4] node lists for each C3D4 element
    """
    elements = []
    in_elements = False
    
    with open(mesh_file, 'r') as f:
        for line in f:
            if '*ELEMENT' in line.upper() and 'C3D4' in line.upper():
                in_elements = True
                continue
            if in_elements:
                if line.startswith('*'):
                    in_elements = False
                    continue
                parts = line.strip().split(',')
                if len(parts) >= 5:
                    try:
                        nodes = [int(parts[i].strip()) for i in range(1, 5)]
                        elements.append(nodes)
                    except ValueError:
                        pass
    return elements


def get_outer_faces(
    elements: List[List[int]], 
    nodes: Optional[Dict[int, Tuple[float, float, float]]] = None
) -> List[Tuple[int, int, int]]:
    """Extract boundary triangular faces from tetrahedral mesh with consistent outward normals.
    
    Boundary faces appear exactly once (not shared between elements).
    Uses proper winding order to ensure outward-pointing normals.
    
    Args:
        elements: List of [n1, n2, n3, n4] element connectivity
        nodes: Optional dict mapping node_id to (x, y, z) coordinates.
               If provided, normals are verified to point outward.
        
    Returns:
        List of (n1, n2, n3) node tuples for boundary faces with consistent winding
    """
    # Track faces: key is sorted tuple for comparison, value is (actual_winding, element_idx, opposite_node_idx)
    face_data = {}
    
    for elem_idx, elem in enumerate(elements):
        for face_idx, (i, j, k) in enumerate(C3D4_FACE_INDICES):
            # Get the actual node IDs with proper winding
            n1, n2, n3 = elem[i], elem[j], elem[k]
            
            # Create a sorted key for identifying shared faces
            face_key = tuple(sorted([n1, n2, n3]))
            
            if face_key in face_data:
                # Face is shared - mark for removal
                face_data[face_key] = None
            else:
                # First time seeing this face - store with proper winding
                # Also store the opposite node (for outward normal verification)
                opposite_node = elem[face_idx]  # The node opposite to this face
                face_data[face_key] = (n1, n2, n3, opposite_node)
    
    # Extract boundary faces (those that appear exactly once)
    boundary_faces = []
    for face_key, data in face_data.items():
        if data is not None:
            n1, n2, n3, opposite_node = data
            
            # If we have node coordinates, verify the normal points outward
            if nodes is not None and n1 in nodes and n2 in nodes and n3 in nodes and opposite_node in nodes:
                # Compute face centroid
                p1 = np.array(nodes[n1])
                p2 = np.array(nodes[n2])
                p3 = np.array(nodes[n3])
                face_center = (p1 + p2 + p3) / 3
                
                # Compute face normal using right-hand rule
                v1 = p2 - p1
                v2 = p3 - p1
                normal = np.cross(v1, v2)
                
                # Vector from opposite node to face center should align with normal
                # (the normal should point away from the element interior)
                opposite_pt = np.array(nodes[opposite_node])
                outward_dir = face_center - opposite_pt
                
                # If normal points inward (dot product negative), flip winding
                if np.dot(normal, outward_dir) < 0:
                    n1, n2, n3 = n1, n3, n2  # Flip winding
            
            boundary_faces.append((n1, n2, n3))
    
    return boundary_faces


def build_triangle_compound(
    triangles: List[Tuple[int, int, int]],
    nodes: Dict[int, Tuple[float, float, float]],
) -> Compound:
    """Build a build123d Compound from triangular faces.
    
    Args:
        triangles: List of (n1, n2, n3) node ID tuples
        nodes: Dict mapping node_id to (x, y, z) coordinates
        
    Returns:
        build123d Compound of triangular faces
    """
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    
    for n1, n2, n3 in triangles:
        if n1 not in nodes or n2 not in nodes or n3 not in nodes:
            continue
        
        p1, p2, p3 = gp_Pnt(*nodes[n1]), gp_Pnt(*nodes[n2]), gp_Pnt(*nodes[n3])
        
        try:
            polygon = BRepBuilderAPI_MakePolygon(p1, p2, p3, True)
            if polygon.IsDone():
                face_maker = BRepBuilderAPI_MakeFace(polygon.Wire(), True)
                if face_maker.IsDone():
                    builder.Add(compound, face_maker.Face())
        except Exception:
            pass
    
    return Compound(compound)


def apply_displacements(
    nodes: Dict[int, Tuple[float, float, float]],
    displacements: Dict[int, Tuple[float, float, float]],
    scale: float = 1.0,
) -> Dict[int, Tuple[float, float, float]]:
    """Apply scaled displacements to node coordinates.
    
    Args:
        nodes: Original node coordinates
        displacements: Node displacements (ux, uy, uz)
        scale: Displacement scale factor for visualization
        
    Returns:
        New dict with deformed coordinates
    """
    deformed = {}
    for nid, (x, y, z) in nodes.items():
        if nid in displacements:
            ux, uy, uz = displacements[nid]
            deformed[nid] = (x + ux * scale, y + uy * scale, z + uz * scale)
        else:
            deformed[nid] = (x, y, z)
    return deformed


def build_deformed_mesh(
    mesh_file: str,
    frd_file: str,
    scale: float = 10.0,
) -> Tuple[Compound, Dict]:
    """Build deformed mesh visualization from FEA results.
    
    Args:
        mesh_file: Path to mesh.inp file
        frd_file: Path to .frd results file
        scale: Displacement magnification factor
        
    Returns:
        Tuple of (deformed_compound, info_dict)
        info_dict contains: nodes, displacements, max_disp, elements
    """
    nodes = read_frd_nodes(frd_file)
    displacements = read_frd_displacements(frd_file)
    elements = read_mesh_elements(mesh_file)
    
    if not nodes or not displacements or not elements:
        raise ValueError("Missing mesh or results data")
    
    # Calculate max displacement
    max_disp = 0.0
    for ux, uy, uz in displacements.values():
        mag = np.sqrt(ux**2 + uy**2 + uz**2)
        if mag > max_disp:
            max_disp = mag
    
    # Build deformed coordinates
    deformed_nodes = apply_displacements(nodes, displacements, scale)
    
    # Get boundary faces and build compound (pass nodes for proper normal orientation)
    outer_faces = get_outer_faces(elements, nodes)
    deformed_compound = build_triangle_compound(outer_faces, deformed_nodes)
    
    info = {
        "nodes": nodes,
        "deformed_nodes": deformed_nodes,
        "displacements": displacements,
        "max_displacement": max_disp,
        "num_elements": len(elements),
        "num_surface_faces": len(outer_faces),
        "scale_factor": scale,
        "outer_faces": outer_faces,
        "elements": elements,
    }
    
    return deformed_compound, info


def build_colored_mesh_by_bands(
    faces: List[Tuple[int, int, int]],
    nodes: Dict[int, Tuple[float, float, float]],
    node_values: Dict[int, float],
    min_val: float,
    max_val: float,
    n_bands: int = 12,
) -> List[Tuple[Compound, str]]:
    """Build mesh compounds colored by discrete bands of a scalar field.
    
    Groups faces by color band to reduce number of objects displayed.
    
    Args:
        faces: List of (n1, n2, n3) node ID tuples
        nodes: Dict mapping node_id to (x, y, z) coordinates
        node_values: Dict mapping node_id to scalar value (e.g., displacement mag)
        min_val: Minimum value for colormap
        max_val: Maximum value for colormap
        n_bands: Number of color bands
        
    Returns:
        List of (compound, hex_color) tuples, one per band
    """
    bands = get_color_bands(n_bands)
    band_faces = {i: [] for i in range(n_bands)}
    
    val_range = max_val - min_val if max_val > min_val else 1.0
    
    for face in faces:
        n1, n2, n3 = face
        # Use average value of face nodes
        vals = []
        for nid in (n1, n2, n3):
            if nid in node_values:
                vals.append(node_values[nid])
        
        if not vals:
            continue
        
        avg_val = sum(vals) / len(vals)
        normalized = (avg_val - min_val) / val_range
        normalized = max(0.0, min(0.9999, normalized))  # Clamp to [0, 1)
        
        band_idx = int(normalized * n_bands)
        band_faces[band_idx].append(face)
    
    result = []
    for i, (lower, upper, color) in enumerate(bands):
        if band_faces[i]:
            compound = build_triangle_compound(band_faces[i], nodes)
            result.append((compound, color))
    
    return result


def build_colored_mesh_by_limit(
    faces: List[Tuple[int, int, int]],
    nodes: Dict[int, Tuple[float, float, float]],
    node_values: Dict[int, float],
    limit: float,
) -> List[Tuple[Compound, str, float, float]]:
    """Build mesh compounds colored by fraction of allowable limit.
    
    Uses engineering color scheme:
    - Blue/Cyan: 0-50% of limit (safe)
    - Green: 50-80% of limit (acceptable)  
    - Yellow/Orange: 80-100% of limit (warning)
    - Red: 100-120% of limit (exceeded)
    - Magenta: >120% of limit (critical)
    
    Args:
        faces: List of (n1, n2, n3) node ID tuples
        nodes: Dict mapping node_id to (x, y, z) coordinates
        node_values: Dict mapping node_id to scalar value
        limit: Allowable limit value
        
    Returns:
        List of (compound, hex_color, band_min, band_max) tuples
    """
    bands = get_limit_color_bands(limit)
    band_faces = {i: [] for i in range(len(bands))}
    
    for face in faces:
        n1, n2, n3 = face
        # Use average value of face nodes
        vals = []
        for nid in (n1, n2, n3):
            if nid in node_values:
                vals.append(node_values[nid])
        
        if not vals:
            continue
        
        avg_val = sum(vals) / len(vals)
        
        # Find which band this value belongs to
        for i, (lower, upper, color) in enumerate(bands):
            if lower <= avg_val < upper:
                band_faces[i].append(face)
                break
        else:
            # Value exceeds all bands, put in last band
            band_faces[len(bands) - 1].append(face)
    
    result = []
    for i, (lower, upper, color) in enumerate(bands):
        if band_faces[i]:
            compound = build_triangle_compound(band_faces[i], nodes)
            result.append((compound, color, lower, upper))
    
    return result


def show_fea_results(
    mesh_file: str,
    frd_file: str,
    scale: float = 10.0,
    original_shapes: Optional[List[Tuple[Any, str, str]]] = None,
    deformed_color: str = "red",
    original_alpha: float = 0.3,
):
    """Visualize FEA results in OCP CAD Viewer (legacy single-color version).
    
    Args:
        mesh_file: Path to mesh.inp file
        frd_file: Path to .frd results file  
        scale: Displacement magnification factor
        original_shapes: List of (shape, name, color) tuples to show
        deformed_color: Color for deformed mesh
        original_alpha: Transparency for original shapes
    """
    from ocp_vscode import show_object, reset_show
    
    deformed, info = build_deformed_mesh(mesh_file, frd_file, scale)
    
    print(f"\nFEA Visualization:")
    print(f"  Elements: {info['num_elements']}")
    print(f"  Surface faces: {info['num_surface_faces']}")
    print(f"  Max displacement: {info['max_displacement']:.4f} mm")
    print(f"  Scale factor: {scale}x")
    print(f"  Scaled max: {info['max_displacement'] * scale:.2f} mm")
    
    reset_show()
    
    # Show original geometry
    if original_shapes:
        for shape, name, color in original_shapes:
            show_object(shape, name=name, options={"color": color, "alpha": original_alpha})
    
    # Show deformed mesh
    show_object(deformed, name=f"Deformed ({scale}x)", options={"color": deformed_color})
    
    return info


def show_fea_results_colormap(
    mesh_file: str,
    frd_file: str,
    scale: float = 10.0,
    original_shapes: Optional[List[Tuple[Any, str, str]]] = None,
    original_alpha: float = 0.3,
    show_displacement: bool = True,
    show_stress: bool = True,
    displacement_offset: Tuple[float, float, float] = (0, 0, 0),
    stress_offset: Tuple[float, float, float] = (8000, 0, 0),
    displacement_limit: Optional[float] = None,
    stress_limit: Optional[float] = None,
    reference_length: Optional[float] = None,
):
    """Visualize FEA results with limit-based colormaps for displacement and stress.
    
    Colors are based on fraction of allowable limits:
    - Blue/Cyan (0-50%): Safe
    - Green (50-80%): Acceptable
    - Yellow/Orange (80-100%): Warning - approaching limit
    - Red (100-120%): Exceeded limit
    - Magenta (>120%): Critical failure
    
    Args:
        mesh_file: Path to mesh.inp file
        frd_file: Path to .frd results file  
        scale: Displacement magnification factor
        original_shapes: List of (shape, name, color) tuples to show
        original_alpha: Transparency for original shapes
        show_displacement: Show displacement colormap
        show_stress: Show stress colormap
        displacement_offset: (x, y, z) offset for displacement visualization
        stress_offset: (x, y, z) offset for stress visualization
        displacement_limit: Allowable displacement (mm). If None, uses reference_length/300
        stress_limit: Allowable stress (MPa). If None, uses 24 MPa (C24 bending strength)
        reference_length: Reference length for L/300 displacement limit (mm)
        
    Returns:
        Dict with visualization info including max values and limit checks
    """
    from ocp_vscode import show
    from build123d import Location
    
    # Load mesh and results
    nodes = read_frd_nodes(frd_file)
    displacements = read_frd_displacements(frd_file)
    elements = read_mesh_elements(mesh_file)
    
    if not nodes or not displacements or not elements:
        raise ValueError("Missing mesh or results data")
    
    # Calculate displacement magnitudes
    disp_magnitudes = {}
    max_disp = 0.0
    for nid, (ux, uy, uz) in displacements.items():
        mag = np.sqrt(ux**2 + uy**2 + uz**2)
        disp_magnitudes[nid] = mag
        if mag > max_disp:
            max_disp = mag
    
    # Load stresses if needed
    stresses = {}
    von_mises = {}
    max_vm = 0.0
    if show_stress:
        stresses = read_frd_stresses(frd_file)
        for nid, (sxx, syy, szz, sxy, syz, szx) in stresses.items():
            vm = compute_von_mises(sxx, syy, szz, sxy, syz, szx)
            von_mises[nid] = vm
            if vm > max_vm:
                max_vm = vm
    
    # Determine limits
    if displacement_limit is None:
        if reference_length is not None:
            displacement_limit = reference_length / 300  # L/300 serviceability
        else:
            # Estimate from geometry - use max coordinate range
            coords = list(nodes.values())
            x_range = max(c[0] for c in coords) - min(c[0] for c in coords)
            y_range = max(c[1] for c in coords) - min(c[1] for c in coords)
            z_range = max(c[2] for c in coords) - min(c[2] for c in coords)
            reference_length = max(x_range, y_range, z_range)
            displacement_limit = reference_length / 300
    
    if stress_limit is None:
        # Default to C24 softwood bending strength (characteristic value)
        stress_limit = 24.0  # MPa
    
    # Build deformed coordinates
    deformed_nodes = apply_displacements(nodes, displacements, scale)
    
    # Get boundary faces (pass nodes for proper normal orientation)
    outer_faces = get_outer_faces(elements, nodes)
    
    # Check against limits
    disp_ratio = max_disp / displacement_limit if displacement_limit > 0 else 0
    stress_ratio = max_vm / stress_limit if stress_limit > 0 else 0
    
    disp_status = "✓ OK" if disp_ratio <= 1.0 else "✗ EXCEEDED"
    stress_status = "✓ OK" if stress_ratio <= 1.0 else "✗ EXCEEDED"
    
    print(f"\n{'='*60}")
    print(f"FEA RESULTS - LIMIT-BASED COLORMAP")
    print(f"{'='*60}")
    print(f"Mesh: {len(elements)} elements, {len(outer_faces)} surface faces")
    print(f"Scale factor: {scale}x")
    print()
    print(f"DISPLACEMENT CHECK:")
    print(f"  Max displacement: {max_disp:.4f} mm")
    print(f"  Allowable (L/300): {displacement_limit:.4f} mm")
    print(f"  Ratio: {disp_ratio*100:.1f}% {disp_status}")
    print()
    if show_stress:
        print(f"STRESS CHECK:")
        print(f"  Max von Mises: {max_vm:.2f} MPa")
        print(f"  Allowable: {stress_limit:.1f} MPa")
        print(f"  Ratio: {stress_ratio*100:.1f}% {stress_status}")
        print()
    
    print(f"COLOR LEGEND:")
    print(f"  Blue/Cyan:  0-50% of limit (safe)")
    print(f"  Green:      50-80% of limit (acceptable)")
    print(f"  Yellow:     80-100% of limit (warning)")
    print(f"  Red:        100-120% of limit (EXCEEDED)")
    print(f"  Magenta:    >120% of limit (CRITICAL)")
    print(f"{'='*60}")
    
    # Collect all objects to show
    objects_to_show = []
    
    # Original geometry (offset to the left)
    if original_shapes:
        for shape, name, color in original_shapes:
            offset_shape = shape.move(Location((-8000, 0, 0)))
            objects_to_show.append((offset_shape, f"Original: {name}", {"color": color, "alpha": original_alpha}))
    
    # Displacement colormap using limits
    if show_displacement:
        disp_bands = build_colored_mesh_by_limit(
            outer_faces, deformed_nodes, disp_magnitudes, displacement_limit
        )
        for compound, color, band_min, band_max in disp_bands:
            offset_compound = compound.move(Location(displacement_offset))
            # Label with percentage of limit
            pct_min = band_min / displacement_limit * 100
            pct_max = band_max / displacement_limit * 100
            objects_to_show.append((
                offset_compound, 
                f"Disp {pct_min:.0f}-{pct_max:.0f}%", 
                {"color": color}
            ))
    
    # Stress colormap using limits
    if show_stress and von_mises:
        stress_bands = build_colored_mesh_by_limit(
            outer_faces, deformed_nodes, von_mises, stress_limit
        )
        for compound, color, band_min, band_max in stress_bands:
            offset_compound = compound.move(Location(stress_offset))
            # Label with percentage of limit
            pct_min = band_min / stress_limit * 100
            pct_max = band_max / stress_limit * 100
            objects_to_show.append((
                offset_compound,
                f"Stress {pct_min:.0f}-{pct_max:.0f}%",
                {"color": color}
            ))
    
    # Show all objects
    shapes = [obj for obj, name, opts in objects_to_show]
    names = [name for obj, name, opts in objects_to_show]
    colors = [opts.get("color", "gray") for obj, name, opts in objects_to_show]
    alphas = [opts.get("alpha", 1.0) for obj, name, opts in objects_to_show]
    
    show(*shapes, names=names, colors=colors, alphas=alphas, render_edges=False)
    
    print(f"\nLayout:")
    print(f"  Left (-8000): Original geometry")
    print(f"  Center (0): Displacement (limit={displacement_limit:.2f}mm)")
    if show_stress:
        print(f"  Right (+8000): Stress (limit={stress_limit:.1f}MPa)")
    
    return {
        "max_displacement": max_disp,
        "max_von_mises": max_vm,
        "displacement_limit": displacement_limit,
        "stress_limit": stress_limit,
        "displacement_ratio": disp_ratio,
        "stress_ratio": stress_ratio,
        "displacement_ok": disp_ratio <= 1.0,
        "stress_ok": stress_ratio <= 1.0,
        "num_elements": len(elements),
        "num_surface_faces": len(outer_faces),
        "scale_factor": scale,
    }
