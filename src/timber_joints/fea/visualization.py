"""FEA visualization utilities for 3D Viewer for VSCode via GLTF export."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import numpy as np

from .backends.calculix import read_frd_nodes, read_frd_displacements, read_frd_stresses, compute_von_mises
from .materials import get_default_material

# Import trimesh for mesh export with vertex colors
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False


def hex_to_rgba_int(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    """Convert hex color string to RGBA integers (0-255 range).
    
    Args:
        hex_color: Color string like "#FF0000" or "FF0000"
        alpha: Alpha value (0-255)
        
    Returns:
        (r, g, b, a) tuple with values in 0-255 range
    """
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b, alpha)


# C3D4 tetrahedron face definitions (0-indexed into node list)
C3D4_FACE_INDICES = [
    (1, 3, 2),  # Face 0: opposite to node 0
    (0, 2, 3),  # Face 1: opposite to node 1
    (0, 3, 1),  # Face 2: opposite to node 2
    (0, 1, 2),  # Face 3: opposite to node 3
]


def read_load_info(output_dir: Path) -> List[Dict]:
    """Read load information from JSON file saved during analysis.
    
    Args:
        output_dir: Directory containing loads.json
        
    Returns:
        List of dicts with keys: name, position, direction, magnitude
    """
    load_file = output_dir / "loads.json"
    if not load_file.exists():
        return []
    
    with open(load_file, 'r') as f:
        return json.load(f)


def save_load_info(output_dir: Path, loads: List[Dict]):
    """Save load information to JSON file for visualization.
    
    Args:
        output_dir: Directory to save loads.json
        loads: List of dicts with keys: name, position, direction, magnitude
    """
    load_file = output_dir / "loads.json"
    with open(load_file, 'w') as f:
        json.dump(loads, f, indent=2)


def read_material_info(output_dir: Path) -> Dict[str, Dict]:
    """Read material information from JSON file saved during analysis.
    
    Args:
        output_dir: Directory containing materials.json
        
    Returns:
        Dict mapping part name to material info including stress_limit (f_m_k)
    """
    material_file = output_dir / "materials.json"
    if not material_file.exists():
        return {}
    
    with open(material_file, 'r') as f:
        return json.load(f)


def save_material_info(output_dir: Path, materials: Dict[str, Dict]):
    """Save material information to JSON file for visualization.
    
    Args:
        output_dir: Directory to save materials.json
        materials: Dict mapping part name to material info with keys:
            - name: material name
            - stress_limit: f_m_k (characteristic bending strength in MPa)
    """
    material_file = output_dir / "materials.json"
    with open(material_file, 'w') as f:
        json.dump(materials, f, indent=2)


def value_to_limit_color(value: float, limit: float) -> str:
    """Convert a value to a color based on fraction of allowable limit.
    
    Continuous color scheme:
    - 0-50% of limit: Blue → Cyan (safe)
    - 50-80% of limit: Cyan → Green (acceptable)
    - 80-100% of limit: Green → Red (warning to limit)
    - 100-200% of limit: Red → Magenta (exceeded)
    - 200-500% of limit: Magenta → Purple (critical)
    
    Args:
        value: The actual value
        limit: The allowable limit
        
    Returns:
        Hex color string like "#FF0000"
    """
    if limit <= 0:
        return "#0000FF"
    
    ratio = value / limit
    
    if ratio <= 0.5:
        t = ratio / 0.5
        r, g, b = 0, int(255 * t), 255
    elif ratio <= 0.8:
        t = (ratio - 0.5) / 0.3
        r, g, b = 0, 255, int(255 * (1 - t))
    elif ratio <= 1.0:
        t = (ratio - 0.8) / 0.2
        r = int(255 * t)
        g = int(255 * (1 - t))
        b = 0
    elif ratio <= 2.0:
        t = (ratio - 1.0) / 1.0
        r, g, b = 255, 0, int(255 * t)
    elif ratio <= 3.0:
        t = (ratio - 2.0) / 1.0
        r, g, b = int(255 - 127 * t), 0, 255
    else:
        t = min(1.0, (ratio - 3.0) / 2.0)
        r, g, b = int(128 - 64 * t), 0, int(255 - 127 * t)
    
    return f"#{r:02X}{g:02X}{b:02X}"


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


def read_mesh_element_sets(mesh_file: str) -> Dict[str, List[int]]:
    """Read element sets from CalculiX mesh file.
    
    Args:
        mesh_file: Path to mesh.inp file
        
    Returns:
        Dict mapping part name (lowercase) to list of element IDs
    """
    element_sets = {}
    current_elset = None
    current_elements = []
    
    # Skip known aggregate sets (like TIMBER that combines other sets)
    skip_sets = {'TIMBER', 'EALL'}
    
    with open(mesh_file, 'r') as f:
        for line in f:
            if line.startswith('*ELSET'):
                # Save previous set if any
                if current_elset and current_elset not in skip_sets:
                    # Convert element set name back to part name (lowercase)
                    part_name = current_elset.lower()
                    element_sets[part_name] = current_elements
                
                # Parse new elset name
                for part in line.split(','):
                    part = part.strip()
                    if part.upper().startswith('ELSET='):
                        current_elset = part.split('=')[1].strip().upper()
                        break
                current_elements = []
                continue
            
            if current_elset and not line.startswith('*'):
                # Parse element IDs (can be numbers or elset references)
                parts = line.strip().rstrip(',').split(',')
                for p in parts:
                    p = p.strip()
                    if p.isdigit():
                        current_elements.append(int(p))
        
        # Save last set
        if current_elset and current_elset not in skip_sets and current_elements:
            part_name = current_elset.lower()
            element_sets[part_name] = current_elements
    
    return element_sets


def read_mesh_elements_indexed(mesh_file: str) -> Dict[int, List[int]]:
    """Read tetrahedral elements from CalculiX mesh file, indexed by element ID.
    
    Args:
        mesh_file: Path to mesh.inp file
        
    Returns:
        Dict mapping element_id to [n1, n2, n3, n4] node list
    """
    elements = {}
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
                        elem_id = int(parts[0].strip())
                        nodes = [int(parts[i].strip()) for i in range(1, 5)]
                        elements[elem_id] = nodes
                    except ValueError:
                        pass
    return elements


def create_node_to_part_mapping(mesh_file: str) -> Dict[int, str]:
    """Create mapping from node IDs to part names based on element sets.
    
    Args:
        mesh_file: Path to mesh.inp file
        
    Returns:
        Dict mapping node_id to part name
    """
    element_sets = read_mesh_element_sets(mesh_file)
    elements = read_mesh_elements_indexed(mesh_file)
    
    node_to_part = {}
    for part_name, elem_ids in element_sets.items():
        for elem_id in elem_ids:
            if elem_id in elements:
                for node_id in elements[elem_id]:
                    # First part wins (node can belong to multiple parts at boundaries)
                    if node_id not in node_to_part:
                        node_to_part[node_id] = part_name
    
    return node_to_part


def get_outer_faces(
    elements: List[List[int]], 
    nodes: Optional[Dict[int, Tuple[float, float, float]]] = None
) -> List[Tuple[int, int, int]]:
    """Extract boundary triangular faces from tetrahedral mesh.
    
    Boundary faces appear exactly once (not shared between elements).
    
    Args:
        elements: List of [n1, n2, n3, n4] element connectivity
        nodes: Optional dict mapping node_id to (x, y, z) for normal verification
        
    Returns:
        List of (n1, n2, n3) node tuples for boundary faces
    """
    face_data = {}
    
    for elem_idx, elem in enumerate(elements):
        for face_idx, (i, j, k) in enumerate(C3D4_FACE_INDICES):
            n1, n2, n3 = elem[i], elem[j], elem[k]
            face_key = tuple(sorted([n1, n2, n3]))
            
            if face_key in face_data:
                face_data[face_key] = None  # Shared face
            else:
                opposite_node = elem[face_idx]
                face_data[face_key] = (n1, n2, n3, opposite_node)
    
    boundary_faces = []
    for face_key, data in face_data.items():
        if data is not None:
            n1, n2, n3, opposite_node = data
            
            if nodes is not None and all(n in nodes for n in [n1, n2, n3, opposite_node]):
                p1 = np.array(nodes[n1])
                p2 = np.array(nodes[n2])
                p3 = np.array(nodes[n3])
                face_center = (p1 + p2 + p3) / 3
                
                v1 = p2 - p1
                v2 = p3 - p1
                normal = np.cross(v1, v2)
                
                opposite_pt = np.array(nodes[opposite_node])
                outward_dir = face_center - opposite_pt
                
                if np.dot(normal, outward_dir) < 0:
                    n1, n2, n3 = n1, n3, n2
            
            boundary_faces.append((n1, n2, n3))
    
    return boundary_faces


def apply_displacements(
    nodes: Dict[int, Tuple[float, float, float]],
    displacements: Dict[int, Tuple[float, float, float]],
    scale: float = 1.0,
) -> Dict[int, Tuple[float, float, float]]:
    """Apply scaled displacements to node coordinates.
    
    Args:
        nodes: Original node coordinates
        displacements: Node displacements (ux, uy, uz)
        scale: Displacement scale factor
        
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


def build_arrow_mesh(
    position: Tuple[float, float, float],
    direction: Tuple[float, float, float],
    arrow_length: float = 0.3,
    shaft_radius: float = 0.015,
    head_radius: float = 0.04,
    head_length: float = 0.08,
    offset: float = 0.05,
    color: Tuple[int, int, int, int] = (255, 0, 0, 255),
    unit_scale: float = 0.001,
    center_x: float = 0.0,
) -> "trimesh.Trimesh":
    """Build a 3D arrow mesh for visualizing force vectors.
    
    Arrow points in the direction of the force, positioned outside the material.
    
    Args:
        position: (x, y, z) point where force is applied (in mm, FEA coords)
        direction: (dx, dy, dz) force direction in FEA coords (will be normalized)
        arrow_length: Total arrow length in meters
        shaft_radius: Radius of arrow shaft in meters
        head_radius: Radius of arrow head base in meters
        head_length: Length of arrow head cone in meters
        offset: Distance to offset arrow tip from position in meters
        color: RGBA color tuple (0-255)
        unit_scale: Scale factor for position (default 0.001 = mm to meters)
        center_x: X center offset to subtract from position
        
    Returns:
        trimesh.Trimesh of the arrow, or None if direction is zero
    """
    if not TRIMESH_AVAILABLE:
        return None
    
    # Normalize direction in FEA coordinates
    dx, dy, dz = direction
    length = np.sqrt(dx**2 + dy**2 + dz**2)
    if length < 1e-10:
        return None
    dx, dy, dz = dx/length, dy/length, dz/length
    
    # Transform direction from FEA coords (X, Y, Z) to viewer coords (X, Z, Y)
    # FEA Y -> Viewer Z, FEA Z -> Viewer Y
    dir_viewer = np.array([dx, dz, dy])
    
    # Create shaft (cylinder) and head (cone) using trimesh primitives
    shaft_length = arrow_length - head_length
    
    # Create cylinder for shaft - centered at origin along Z
    shaft = trimesh.creation.cylinder(
        radius=shaft_radius,
        height=shaft_length,
        sections=16,
    )
    # Shaft is centered, move so bottom is at z=0
    shaft.apply_translation([0, 0, shaft_length / 2])
    
    # Create cone for head - tip at top
    head = trimesh.creation.cone(
        radius=head_radius,
        height=head_length,
        sections=16,
    )
    # Cone is created with base at z=0 and tip at z=height
    # Move so base connects to top of shaft
    head.apply_translation([0, 0, shaft_length])
    
    # Combine shaft and head
    arrow = trimesh.util.concatenate([shaft, head])
    
    # Calculate rotation matrix to align +Z axis with viewer direction vector
    z_axis = np.array([0, 0, 1])
    target = dir_viewer / np.linalg.norm(dir_viewer)
    
    # Handle the case where target is parallel or anti-parallel to z_axis
    dot = np.dot(z_axis, target)
    if abs(dot - 1.0) < 1e-6:
        # Already aligned
        rotation_matrix = np.eye(4)
    elif abs(dot + 1.0) < 1e-6:
        # Opposite direction - rotate 180 around X
        rotation_matrix = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
    else:
        # General case - rotate around cross product
        axis = np.cross(z_axis, target)
        axis = axis / np.linalg.norm(axis)
        angle = np.arccos(np.clip(dot, -1.0, 1.0))
        rotation_matrix = trimesh.transformations.rotation_matrix(angle, axis)
    
    arrow.apply_transform(rotation_matrix)
    
    # Convert position from mm to meters and apply coordinate transform
    # FEA: X, Y, Z -> Viewer: X, Z, Y (swap Y and Z)
    px = (position[0] - center_x) * unit_scale
    py = position[2] * unit_scale  # FEA Z becomes Viewer Y
    pz = position[1] * unit_scale  # FEA Y becomes Viewer Z
    
    # Position the arrow so its TIP is near (but outside) the load application point
    # Arrow tip is at arrow_length along the direction
    # Move base to: position - (arrow_length + offset) * direction
    total_offset = arrow_length + offset
    offset_position = (
        px - total_offset * target[0],
        py - total_offset * target[1],
        pz - total_offset * target[2],
    )
    
    arrow.apply_translation(offset_position)
    
    # Apply color to all vertices
    arrow.visual.vertex_colors = np.tile(color, (len(arrow.vertices), 1))
    
    return arrow


def export_fea_combined_gltf(
    output_dir: str,
    scale: float = 10.0,
    displacement_limit: Optional[float] = None,
    stress_limit: Optional[float] = None,
    reference_length: Optional[float] = None,
    spacing: float = 8.0,
    unit_scale: float = 0.001,
    auto_open: bool = True,
    show_loads: bool = True,
    arrow_scale: float = 1.0,
) -> Dict[str, Any]:
    """Export FEA results as a single GLTF with original, displacement, and stress side by side.
    
    Creates one GLTF file containing three meshes arranged horizontally:
    - Left: Original shape (gray)
    - Center: Displacement colored mesh (deformed) with load arrows
    - Right: Stress colored mesh (deformed) with load arrows
    
    Stress coloring uses per-part material stress limits (f_m_k) when available.
    
    Args:
        output_dir: Directory containing mesh.inp and analysis.frd, output goes here too
        scale: Displacement magnification factor
        displacement_limit: Limit for displacement (default: L/300)
        stress_limit: Fallback limit for stress if per-part materials not available
        reference_length: Reference length for L/300 calculation
        spacing: Spacing between meshes in meters (default 8.0)
        unit_scale: Scale factor to convert coordinates (default 0.001 = mm to meters)
        auto_open: If True, automatically open the GLTF file in VSCode
        show_loads: If True, show force arrows at load application points
        arrow_scale: Scale factor for force arrows (1.0 = default size)
        
    Returns:
        Dict with info for the export
    """
    if not TRIMESH_AVAILABLE:
        raise ImportError(
            "trimesh is required for GLTF export. "
            "Install with: pip install trimesh[easy]"
        )
    
    # Derive file paths from output_dir
    output_dir_path = Path(output_dir)
    mesh_file = str(output_dir_path / "mesh.inp")
    frd_file = str(output_dir_path / "analysis.frd")
    output_file = str(output_dir_path / "fea_results.gltf")
    
    # Load mesh and results
    nodes = read_frd_nodes(frd_file)
    displacements = read_frd_displacements(frd_file)
    stresses = read_frd_stresses(frd_file)
    elements = read_mesh_elements(mesh_file)
    
    if not nodes or not displacements or not elements:
        raise ValueError("Missing mesh or results data")
    
    # Calculate displacement values
    disp_values = {}
    max_disp = 0.0
    for nid, (ux, uy, uz) in displacements.items():
        mag = np.sqrt(ux**2 + uy**2 + uz**2)
        disp_values[nid] = mag
        if mag > max_disp:
            max_disp = mag
    
    # Determine displacement limit
    if displacement_limit is None:
        if reference_length is not None:
            displacement_limit = reference_length / 300
        else:
            coords = list(nodes.values())
            x_range = max(c[0] for c in coords) - min(c[0] for c in coords)
            y_range = max(c[1] for c in coords) - min(c[1] for c in coords)
            z_range = max(c[2] for c in coords) - min(c[2] for c in coords)
            reference_length = max(x_range, y_range, z_range)
            displacement_limit = reference_length / 300
    
    # Calculate stress values
    stress_values = {}
    max_stress = 0.0
    for nid, (sxx, syy, szz, sxy, syz, szx) in stresses.items():
        vm = compute_von_mises(sxx, syy, szz, sxy, syz, szx)
        stress_values[nid] = vm
        if vm > max_stress:
            max_stress = vm
    
    # Get per-node stress limits from per-part materials
    node_to_part = create_node_to_part_mapping(mesh_file)
    material_info = read_material_info(output_dir_path)
    
    # Build per-node stress limits
    node_stress_limits = {}
    fallback_stress_limit = stress_limit
    
    if fallback_stress_limit is None:
        # Get fallback stress limit from default timber material
        material = get_default_material()
        if material.strength is not None:
            fallback_stress_limit = material.strength.f_m_k
        else:
            fallback_stress_limit = 24.0  # Fallback to C24 bending strength
    
    # Map each node to its part's stress limit
    for nid in nodes:
        part_name = node_to_part.get(nid)
        if part_name and part_name in material_info:
            node_stress_limits[nid] = material_info[part_name].get("stress_limit", fallback_stress_limit)
        else:
            node_stress_limits[nid] = fallback_stress_limit
    
    # Calculate max stress ratio for reporting
    max_stress_ratio = 0.0
    max_stress_part = None
    for nid, stress_val in stress_values.items():
        limit = node_stress_limits.get(nid, fallback_stress_limit)
        ratio = stress_val / limit if limit > 0 else 0
        if ratio > max_stress_ratio:
            max_stress_ratio = ratio
            max_stress_part = node_to_part.get(nid, "unknown")
    
    # Calculate per-part max stress and ratio
    part_stress_results = {}
    for nid, stress_val in stress_values.items():
        part_name = node_to_part.get(nid)
        if part_name:
            limit = node_stress_limits.get(nid, fallback_stress_limit)
            if part_name not in part_stress_results:
                part_stress_results[part_name] = {
                    "max_stress": stress_val,
                    "limit": limit,
                    "ratio": stress_val / limit if limit > 0 else 0,
                }
            else:
                if stress_val > part_stress_results[part_name]["max_stress"]:
                    part_stress_results[part_name]["max_stress"] = stress_val
                    part_stress_results[part_name]["ratio"] = stress_val / limit if limit > 0 else 0

    # Build deformed coordinates
    deformed_nodes = apply_displacements(nodes, displacements, scale)
    
    # Get boundary faces
    outer_faces = get_outer_faces(elements, nodes)
    
    # Calculate mesh center for proper spacing
    coords = list(nodes.values())
    center_x = (max(c[0] for c in coords) + min(c[0] for c in coords)) / 2
    
    def build_mesh_with_offset(node_coords, node_values, limit_or_limits, x_offset, default_color=None, alpha=255):
        """Build a trimesh with given nodes, colors, and X offset.
        
        Args:
            node_coords: Dict[int, tuple] node coordinates
            node_values: Dict[int, float] values per node
            limit_or_limits: float (single limit) or Dict[int, float] (per-node limits)
            x_offset: X offset for positioning
            default_color: If set, use this color for all vertices
            alpha: Alpha value for transparency (0-255, default 255 = opaque)
        """
        # Handle both single limit and per-node limits
        use_per_node_limits = isinstance(limit_or_limits, dict)
        single_limit = limit_or_limits if not use_per_node_limits else None
        
        node_to_vertex = {}
        vertices = []
        colors = []
        
        for face in outer_faces:
            for nid in face:
                if nid not in node_to_vertex:
                    if nid not in node_coords:
                        continue
                    x, y, z = node_coords[nid]
                    
                    # Apply unit scale and swap Y/Z, add X offset
                    xs = (x - center_x) * unit_scale + x_offset
                    ys = z * unit_scale
                    zs = y * unit_scale
                    
                    # Get color
                    if default_color is not None:
                        rgba = default_color
                    else:
                        value = node_values.get(nid, 0.0)
                        if use_per_node_limits:
                            limit = limit_or_limits.get(nid, fallback_stress_limit)
                        else:
                            limit = single_limit
                        hex_color = value_to_limit_color(value, limit)
                        rgba = hex_to_rgba_int(hex_color, alpha=alpha)
                    
                    vertex_idx = len(vertices)
                    node_to_vertex[nid] = vertex_idx
                    vertices.append([xs, ys, zs])
                    colors.append(rgba)
        
        # Build faces with reversed winding for correct normals
        faces = []
        for n1, n2, n3 in outer_faces:
            if n1 in node_to_vertex and n2 in node_to_vertex and n3 in node_to_vertex:
                v1, v2, v3 = node_to_vertex[n1], node_to_vertex[n2], node_to_vertex[n3]
                faces.append([v1, v3, v2])  # Reversed winding
        
        vertices_np = np.array(vertices, dtype=np.float64)
        faces_np = np.array(faces, dtype=np.int64)
        colors_np = np.array(colors, dtype=np.uint8)
        
        mesh = trimesh.Trimesh(
            vertices=vertices_np,
            faces=faces_np,
            vertex_colors=colors_np,
            process=False,
        )
        
        # For transparency, we need to set the material's alphaMode
        # while keeping vertex colors. We do this by accessing the visual's material.
        if alpha < 255 and hasattr(mesh.visual, 'material'):
            # The vertex colors are already set, just update material for transparency
            if mesh.visual.material is not None:
                mesh.visual.material.alphaMode = 'BLEND'
        
        return mesh
    
    # Build three meshes side by side
    original_mesh = build_mesh_with_offset(
        nodes, {}, 1.0, -spacing,
        default_color=(180, 180, 180, 255)  # Gray
    )
    
    disp_mesh = build_mesh_with_offset(
        deformed_nodes, disp_values, displacement_limit, 0.0
    )
    
    # Use per-node stress limits for stress visualization (semi-transparent)
    stress_mesh = build_mesh_with_offset(
        deformed_nodes, stress_values, node_stress_limits, spacing,
        alpha=180  # Semi-transparent
    )
    
    # Combine into a scene
    scene = trimesh.Scene()
    scene.add_geometry(original_mesh, node_name="original")
    scene.add_geometry(disp_mesh, node_name="displacement")
    scene.add_geometry(stress_mesh, node_name="stress")
    
    # Add load arrows
    if show_loads:
        output_dir = Path(mesh_file).parent
        loads = read_load_info(output_dir)
        
        # Filter out self-weight loads (they have "_sw_" in name)
        custom_loads = [l for l in loads if "_sw_" not in l["name"]]
        
        for i, load in enumerate(custom_loads):
            pos = tuple(load["position"])
            direction = tuple(load["direction"])
            
            # Arrow parameters scaled
            arrow_length = 0.3 * arrow_scale
            shaft_radius = 0.015 * arrow_scale
            head_radius = 0.04 * arrow_scale
            head_length = 0.08 * arrow_scale
            
            # Add arrow to displacement view (center, offset = 0)
            arrow_disp = build_arrow_mesh(
                position=pos,
                direction=direction,
                arrow_length=arrow_length,
                shaft_radius=shaft_radius,
                head_radius=head_radius,
                head_length=head_length,
                color=(255, 50, 50, 255),  # Red
                unit_scale=unit_scale,
                center_x=center_x,
            )
            if arrow_disp:
                scene.add_geometry(arrow_disp, node_name=f"load_disp_{i}")
            
            # Add arrow to stress view (right, offset = spacing)
            arrow_stress = build_arrow_mesh(
                position=pos,
                direction=direction,
                arrow_length=arrow_length,
                shaft_radius=shaft_radius,
                head_radius=head_radius,
                head_length=head_length,
                color=(255, 50, 50, 255),  # Red
                unit_scale=unit_scale,
                center_x=center_x,
            )
            if arrow_stress:
                # Offset to stress position
                arrow_stress.apply_translation([spacing, 0, 0])
                scene.add_geometry(arrow_stress, node_name=f"load_stress_{i}")
    
    # Export to GLTF, then post-process to add transparency material
    output_path = Path(output_file)
    gltf_data = scene.export(file_type='gltf')
    
    # Post-process GLTF to add material with alphaMode for transparency
    # gltf_data is a dict with buffer files and 'model.gltf'
    if isinstance(gltf_data, dict) and 'model.gltf' in gltf_data:
        import json as json_module
        gltf_json = json_module.loads(gltf_data['model.gltf'])
        
        # Add a transparent material
        if 'materials' not in gltf_json:
            gltf_json['materials'] = []
        
        # Add material for stress mesh (transparent)
        stress_material_idx = len(gltf_json['materials'])
        gltf_json['materials'].append({
            "name": "stress_transparent",
            "pbrMetallicRoughness": {
                "baseColorFactor": [1.0, 1.0, 1.0, 0.8],
                "metallicFactor": 0.0,
                "roughnessFactor": 0.8
            },
            "alphaMode": "BLEND"
        })
        
        # The stress mesh is the 3rd geometry added (index 2: original=0, displacement=1, stress=2)
        # Assign the transparent material to its primitives
        if 'meshes' in gltf_json and len(gltf_json['meshes']) > 2:
            stress_mesh = gltf_json['meshes'][2]
            for primitive in stress_mesh.get('primitives', []):
                primitive['material'] = stress_material_idx
        
        # Write the modified GLTF
        gltf_data['model.gltf'] = json_module.dumps(gltf_json).encode()
        
        # Save all files
        for filename, content in gltf_data.items():
            filepath = output_path.parent / filename
            if filename == 'model.gltf':
                filepath = output_path
            with open(filepath, 'wb') as f:
                f.write(content if isinstance(content, bytes) else content.encode())
    else:
        # Fallback: just save directly
        scene.export(str(output_path), file_type='gltf')
    
    disp_ratio = max_disp / displacement_limit if displacement_limit > 0 else 0
    
    print(f"\n{'='*60}")
    print("FEA RESULTS EXPORTED (Combined GLTF)")
    print(f"{'='*60}")
    print(f"Output: {output_path}")
    print(f"\nLayout (left to right):")
    print(f"  1. Original shape (gray)")
    print(f"  2. Displacement: max {max_disp:.4f} mm ({disp_ratio*100:.1f}% of limit)")
    print(f"  3. Stress: max {max_stress:.2f} MPa ({max_stress_ratio*100:.1f}% of limit in {max_stress_part})")
    print(f"\nLimits:")
    print(f"  Displacement: {displacement_limit:.4f} mm (L/300)")
    
    # Show per-part stress results
    if part_stress_results:
        print(f"\nPer-Member Stress Check:")
        all_passed = True
        for part_name in sorted(part_stress_results.keys()):
            result = part_stress_results[part_name]
            max_s = result["max_stress"]
            limit = result["limit"]
            ratio = result["ratio"]
            passed = ratio <= 1.0
            status = "✓ PASS" if passed else "✗ FAIL"
            if not passed:
                all_passed = False
            print(f"  {part_name}: {max_s:.2f} / {limit:.1f} MPa = {ratio*100:.1f}% {status}")
        print(f"\n  Overall: {'✓ ALL PASS' if all_passed else '✗ SOME FAIL'}")
    
    # Show per-part stress limits if we have material info
    if material_info:
        print(f"\nMaterial Assignments:")
        for part_name, info in material_info.items():
            limit = info.get("stress_limit", fallback_stress_limit)
            mat_name = info.get("name", "unknown")
            print(f"  {part_name}: {mat_name} (f_m_k = {limit:.1f} MPa)")
    
    if show_loads:
        output_dir = Path(mesh_file).parent
        loads = read_load_info(output_dir)
        custom_loads = [l for l in loads if "_sw_" not in l["name"]]
        if custom_loads:
            print(f"\nLoads (red arrows):")
            for load in custom_loads:
                print(f"  {load['name']}: {load['magnitude']:.0f} N")
    print(f"\nColor Legend:")
    print(f"  Blue→Cyan:      0-50% of limit (safe)")
    print(f"  Cyan→Green:     50-80% of limit (acceptable)")
    print(f"  Green→Red:      80-100% of limit (warning)")
    print(f"  Red→Magenta:    100-200% of limit (EXCEEDED)")
    print(f"  Magenta→Purple: 200-500% of limit (critical)")
    print(f"{'='*60}")
    
    # Auto-open in VSCode
    if auto_open:
        import subprocess
        try:
            subprocess.run(["code", str(output_path)], check=False)
            print(f"\nOpened: {output_path}")
        except FileNotFoundError:
            print(f"\nCould not auto-open (VSCode 'code' command not found)")
            print(f"Manually open: {output_path}")
    
    return {
        "output_file": str(output_path),
        "max_displacement": max_disp,
        "max_stress": max_stress,
        "displacement_limit": displacement_limit,
        "stress_limit": fallback_stress_limit,  # Fallback for API compatibility
        "displacement_ratio": disp_ratio,
        "stress_ratio": max_stress_ratio,  # Now the max ratio across all parts
        "displacement_ok": disp_ratio <= 1.0,
        "stress_ok": max_stress_ratio <= 1.0,
        "max_stress_part": max_stress_part,
        "material_info": material_info,
        "part_stress_results": part_stress_results,  # Per-part stress info
    }
