"""FEA analysis adapter for timber frames."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Tuple
import os

from build123d import Part, Location, Box, Align, Compound

from timber_joints.frame import TimberFrame, Element, Role


# =============================================================================
# Contact Surface Utilities
# =============================================================================

def get_bbox_solid(bbox) -> Part:
    """Create a solid box from a bounding box."""
    size_x = bbox.max.X - bbox.min.X
    size_y = bbox.max.Y - bbox.min.Y
    size_z = bbox.max.Z - bbox.min.Z
    box = Box(size_x, size_y, size_z, align=(Align.MIN, Align.MIN, Align.MIN))
    return box.move(Location((bbox.min.X, bbox.min.Y, bbox.min.Z)))


def scale_shape_in_place(shape: Part, scale_factor: float) -> Part:
    """Scale a shape from its center (not from origin)."""
    center = shape.bounding_box().center()
    centered = shape.move(Location((-center.X, -center.Y, -center.Z)))
    scaled = centered.scale(scale_factor)
    return scaled.move(Location((center.X, center.Y, center.Z)))


def expand_shape_by_margin(shape: Part, margin: float) -> Part:
    """
    Scale a shape to expand its bounding box by a fixed margin on each axis.
    
    Unlike uniform scaling, this calculates independent scale factors per axis
    to achieve the same absolute margin expansion on each side.
    
    Note: This function creates a copy of the input shape to avoid mutation.
    
    Args:
        shape: The shape to expand
        margin: Fixed amount (mm) to add to each side of each axis
    
    Returns:
        A new shape scaled non-uniformly to achieve the margin expansion
    """
    import copy
    from OCP.gp import gp_GTrsf, gp_XYZ
    from OCP.BRepBuilderAPI import BRepBuilderAPI_GTransform
    
    # Deep copy to avoid mutating the original
    shape = copy.deepcopy(shape)
    
    bbox = shape.bounding_box()
    center = bbox.center()
    
    # Calculate size in each dimension
    size_x = bbox.max.X - bbox.min.X
    size_y = bbox.max.Y - bbox.min.Y
    size_z = bbox.max.Z - bbox.min.Z
    
    # Calculate scale factor for each axis to add margin to each side
    scale_x = (size_x + 2 * margin) / size_x if size_x > 0 else 1.0
    scale_y = (size_y + 2 * margin) / size_y if size_y > 0 else 1.0
    scale_z = (size_z + 2 * margin) / size_z if size_z > 0 else 1.0
    
    # Move shape to origin, apply non-uniform scale, move back
    centered = shape.move(Location((-center.X, -center.Y, -center.Z)))
    
    # Create non-uniform scaling transformation
    gtrsf = gp_GTrsf()
    gtrsf.SetValue(1, 1, scale_x)
    gtrsf.SetValue(2, 2, scale_y)
    gtrsf.SetValue(3, 3, scale_z)
    
    transform = BRepBuilderAPI_GTransform(centered.wrapped, gtrsf, True)
    scaled = Part(transform.Shape())
    
    return scaled.move(Location((center.X, center.Y, center.Z)))


def find_contact_surface(target_shape: Part, other_shape: Part, margin: float = 0.1) -> Compound:
    """
    Find the contact surface region between two shapes.
    
    Returns only the faces from target_shape that are in the contact region,
    filtering out bbox artifact faces (faces on the bbox boundary planes).
    
    Args:
        target_shape: The shape to extract the contact region from
        other_shape: The shape whose bounding box defines the contact region
        margin: Fixed amount (mm) to expand bbox on each side
    
    Returns:
        A Compound containing only the faces from target_shape that are in the
        contact region (artifact faces from the bbox cut are filtered out)
    """
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Compound
    
    # Create expanded bbox solid for intersection
    other_bbox = other_shape.bounding_box()
    size_x = other_bbox.max.X - other_bbox.min.X + 2 * margin
    size_y = other_bbox.max.Y - other_bbox.min.Y + 2 * margin
    size_z = other_bbox.max.Z - other_bbox.min.Z + 2 * margin
    expanded_bbox_solid = Box(size_x, size_y, size_z, align=(Align.MIN, Align.MIN, Align.MIN))
    expanded_bbox_solid = expanded_bbox_solid.move(Location((
        other_bbox.min.X - margin,
        other_bbox.min.Y - margin,
        other_bbox.min.Z - margin
    )))
    
    # Get the expanded bbox boundaries for artifact filtering
    expanded_bbox = expanded_bbox_solid.bounding_box()
    bbox_planes = [
        expanded_bbox.min.X, expanded_bbox.max.X,
        expanded_bbox.min.Y, expanded_bbox.max.Y,
        expanded_bbox.min.Z, expanded_bbox.max.Z,
    ]
    
    # Boolean intersection
    intersection = target_shape & expanded_bbox_solid
    
    # Filter out faces that lie on any bbox boundary plane
    # Use a small fixed tolerance for plane detection (independent of margin)
    plane_tol = 0.1
    kept_faces = []
    
    for face in intersection.faces():
        center = face.center()
        
        # Check if face center is on any bbox boundary plane
        on_bbox_plane = False
        for plane_coord in bbox_planes:
            if (abs(center.X - plane_coord) < plane_tol or
                abs(center.Y - plane_coord) < plane_tol or
                abs(center.Z - plane_coord) < plane_tol):
                on_bbox_plane = True
                break
        
        if not on_bbox_plane:
            kept_faces.append(face)
    
    # Build a compound from kept faces
    if kept_faces:
        builder = BRep_Builder()
        compound = TopoDS_Compound()
        builder.MakeCompound(compound)
        for face in kept_faces:
            builder.Add(compound, face.wrapped)
        return Compound(compound)
    else:
        # Fallback to full intersection if filtering removes everything
        return intersection


def find_joint_contact_surfaces(
    inserting_part: Part, 
    receiving_part: Part, 
    margin: float = 2
) -> Tuple[Compound, Compound]:
    """
    Find both contact surfaces for a mortise-tenon style joint.
    
    This is the recommended way to extract contact surfaces for FEA analysis.
    It correctly handles the two-step extraction:
    1. Tenon = inserting_part faces inside receiving_part region
    2. Mortise = receiving_part faces inside tenon region (NOT full inserting_part!)
    
    Args:
        inserting_part: The part with the tenon/insert (e.g., beam)
        receiving_part: The part with the mortise/pocket (e.g., post)
        margin: Fixed amount (mm) to expand bbox on each side
    
    Returns:
        Tuple of (tenon_contact, mortise_contact) Compounds
    """
    # Step 1: Find tenon surfaces (inserting part inside receiving part)
    tenon_contact = find_contact_surface(inserting_part, receiving_part, margin)
    
    # Step 2: Find mortise surfaces using TENON bbox (not full inserting part!)
    # This is critical - the tenon region defines exactly where the mortise is
    mortise_contact = find_contact_surface(receiving_part, tenon_contact, margin)
    
    return tenon_contact, mortise_contact


def find_mesh_contact_faces(
    elements_a: List[Tuple[int, List[int]]],
    nodes_a: dict,
    elements_b: List[Tuple[int, List[int]]],
    nodes_b: dict,
    margin: float = 1.0
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """
    Find mesh element faces at the contact region between two meshed parts.
    
    Pure mesh-based approach - no CAD geometry needed:
    1. Find boundary faces (faces only used by one element = surface faces)
    2. Compute bounding boxes of both meshes
    3. Find the intersection region of the bounding boxes (with margin)
    4. Return boundary faces from each part that lie in the intersection region
    
    Args:
        elements_a: Elements of mesh A as (element_id, [n1, n2, n3, n4]) tuples
        nodes_a: Nodes of mesh A as {node_id: (x, y, z)}
        elements_b: Elements of mesh B as (element_id, [n1, n2, n3, n4]) tuples
        nodes_b: Nodes of mesh B as {node_id: (x, y, z)}
        margin: Margin (mm) to expand the intersection region for tolerance
    
    Returns:
        Tuple of (faces_a, faces_b) where each is a list of (element_id, face_number)
        for CalculiX *SURFACE definition. Face numbers are 1-4 for C3D4 elements.
    """
    # C3D4 face definitions: which nodes form each face
    face_node_indices = [
        (0, 1, 2),  # S1
        (0, 1, 3),  # S2
        (1, 2, 3),  # S3
        (0, 2, 3),  # S4
    ]
    
    def get_boundary_faces(elements):
        """
        Find boundary faces - faces that appear in only one element.
        Internal faces are shared by two elements, boundary faces are not.
        Returns dict mapping (elem_id, face_num) to sorted node tuple.
        """
        # Count how many times each face (as sorted node tuple) appears
        face_count = {}  # sorted_nodes -> [(elem_id, face_num), ...]
        
        for elem_id, elem_nodes in elements:
            for face_idx, (i, j, k) in enumerate(face_node_indices):
                n1, n2, n3 = elem_nodes[i], elem_nodes[j], elem_nodes[k]
                face_key = tuple(sorted([n1, n2, n3]))
                if face_key not in face_count:
                    face_count[face_key] = []
                face_count[face_key].append((elem_id, face_idx + 1))
        
        # Boundary faces appear exactly once
        boundary_faces = {}
        for face_key, occurrences in face_count.items():
            if len(occurrences) == 1:
                elem_id, face_num = occurrences[0]
                boundary_faces[(elem_id, face_num)] = face_key
        
        return boundary_faces
    
    def get_mesh_bbox(nodes: dict):
        """Get bounding box of mesh nodes."""
        coords = list(nodes.values())
        if not coords:
            return None
        min_x = min(c[0] for c in coords)
        max_x = max(c[0] for c in coords)
        min_y = min(c[1] for c in coords)
        max_y = max(c[1] for c in coords)
        min_z = min(c[2] for c in coords)
        max_z = max(c[2] for c in coords)
        return (min_x, max_x, min_y, max_y, min_z, max_z)
    
    def bbox_intersection(bbox_a, bbox_b, margin):
        """Find intersection of two bounding boxes, expanded by margin."""
        min_x = max(bbox_a[0], bbox_b[0]) - margin
        max_x = min(bbox_a[1], bbox_b[1]) + margin
        min_y = max(bbox_a[2], bbox_b[2]) - margin
        max_y = min(bbox_a[3], bbox_b[3]) + margin
        min_z = max(bbox_a[4], bbox_b[4]) - margin
        max_z = min(bbox_a[5], bbox_b[5]) + margin
        
        # Check if there's actually an intersection
        if min_x > max_x or min_y > max_y or min_z > max_z:
            return None
        return (min_x, max_x, min_y, max_y, min_z, max_z)
    
    def face_in_bbox(face_nodes, nodes, bbox):
        """Check if all 3 nodes of a face are inside the bounding box."""
        for nid in face_nodes:
            if nid not in nodes:
                return False
            x, y, z = nodes[nid]
            if not (bbox[0] <= x <= bbox[1] and
                    bbox[2] <= y <= bbox[3] and
                    bbox[4] <= z <= bbox[5]):
                return False
        return True
    
    # Step 1: Find boundary faces for each mesh
    print("  Finding boundary faces...")
    boundary_a = get_boundary_faces(elements_a)
    boundary_b = get_boundary_faces(elements_b)
    print(f"  Mesh A: {len(boundary_a)} boundary faces, Mesh B: {len(boundary_b)} boundary faces")
    
    # Step 2: Get bounding boxes
    bbox_a = get_mesh_bbox(nodes_a)
    bbox_b = get_mesh_bbox(nodes_b)
    
    if bbox_a is None or bbox_b is None:
        print("  Could not compute bounding boxes!")
        return [], []
    
    print(f"  Mesh A bbox: X[{bbox_a[0]:.1f}, {bbox_a[1]:.1f}] Y[{bbox_a[2]:.1f}, {bbox_a[3]:.1f}] Z[{bbox_a[4]:.1f}, {bbox_a[5]:.1f}]")
    print(f"  Mesh B bbox: X[{bbox_b[0]:.1f}, {bbox_b[1]:.1f}] Y[{bbox_b[2]:.1f}, {bbox_b[3]:.1f}] Z[{bbox_b[4]:.1f}, {bbox_b[5]:.1f}]")
    
    # Step 3: Find intersection with margin
    intersection = bbox_intersection(bbox_a, bbox_b, margin)
    if intersection is None:
        print("  No bounding box intersection found!")
        return [], []
    
    print(f"  Intersection (±{margin}mm): X[{intersection[0]:.1f}, {intersection[1]:.1f}] Y[{intersection[2]:.1f}, {intersection[3]:.1f}] Z[{intersection[4]:.1f}, {intersection[5]:.1f}]")
    
    # Step 4: Filter boundary faces by intersection bbox
    faces_a = []
    for (elem_id, face_num), face_nodes in boundary_a.items():
        if face_in_bbox(face_nodes, nodes_a, intersection):
            faces_a.append((elem_id, face_num))
    
    faces_b = []
    for (elem_id, face_num), face_nodes in boundary_b.items():
        if face_in_bbox(face_nodes, nodes_b, intersection):
            faces_b.append((elem_id, face_num))
    
    print(f"  Found {len(faces_a)} faces from mesh A, {len(faces_b)} faces from mesh B in contact region")
    
    return faces_a, faces_b


# C3D4 face node indices (used by multiple functions)
C3D4_FACE_NODE_INDICES = [(0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 2, 3)]


def build_mesh_faces_compound(
    mesh_faces: List[Tuple[int, int]],
    elements: List[Tuple[int, List[int]]],
    nodes: dict
) -> Compound:
    """
    Build a build123d Compound of triangular faces from mesh face definitions.
    
    Useful for visualizing contact surfaces or any mesh faces in OCP viewer.
    
    Args:
        mesh_faces: List of (element_id, face_number) tuples where face_number is 1-4
        elements: List of (element_id, [n1, n2, n3, n4]) tuples (C3D4 tetrahedra)
        nodes: Dict mapping node_id to (x, y, z) coordinates
    
    Returns:
        A build123d Compound containing triangular faces for visualization
    """
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.gp import gp_Pnt
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Compound
    
    elem_dict = {eid: enodes for eid, enodes in elements}
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    
    for elem_id, face_num in mesh_faces:
        if elem_id not in elem_dict:
            continue
        elem_nodes = elem_dict[elem_id]
        i, j, k = C3D4_FACE_NODE_INDICES[face_num - 1]  # face_num is 1-based
        n1, n2, n3 = elem_nodes[i], elem_nodes[j], elem_nodes[k]
        
        if n1 not in nodes or n2 not in nodes or n3 not in nodes:
            continue
        
        p1 = gp_Pnt(*nodes[n1])
        p2 = gp_Pnt(*nodes[n2])
        p3 = gp_Pnt(*nodes[n3])
        
        try:
            polygon = BRepBuilderAPI_MakePolygon(p1, p2, p3, True)
            if polygon.IsDone():
                face_maker = BRepBuilderAPI_MakeFace(polygon.Wire(), True)
                if face_maker.IsDone():
                    builder.Add(compound, face_maker.Face())
        except Exception:
            pass
    
    return Compound(compound)


# Keep the old function for CAD-based approach if needed
def find_mesh_faces_on_surface(
    elements: List[Tuple[int, List[int]]],
    nodes: dict,
    contact_surface: Compound,
    tolerance: float = 1.0,
    bbox_margin: float = 5.0
) -> List[Tuple[int, int]]:
    """
    Find mesh element faces that lie on a CAD contact surface.
    
    Uses CAD surface bounding box for fast filtering.
    For pure mesh-based contact detection, use find_mesh_contact_faces instead.
    
    Args:
        elements: List of (element_id, [n1, n2, n3, n4]) tuples (C3D4 tetrahedra)
        nodes: Dict mapping node_id to (x, y, z) coordinates
        contact_surface: CAD Compound containing the contact faces
        tolerance: Max distance (mm) from surface to consider a node "on" it
        bbox_margin: Margin (mm) to expand bbox for filtering
    
    Returns:
        List of (element_id, face_number) tuples for CalculiX *SURFACE definition
    """
    # C3D4 face definitions
    face_node_indices = [
        (0, 1, 2),  # S1
        (0, 1, 3),  # S2
        (1, 2, 3),  # S3
        (0, 2, 3),  # S4
    ]
    
    # Get bounding box of the CAD contact surface
    bbox = contact_surface.bounding_box()
    bbox_min_x = bbox.min.X - bbox_margin
    bbox_max_x = bbox.max.X + bbox_margin
    bbox_min_y = bbox.min.Y - bbox_margin
    bbox_max_y = bbox.max.Y + bbox_margin
    bbox_min_z = bbox.min.Z - bbox_margin
    bbox_max_z = bbox.max.Z + bbox_margin
    
    # Find nodes in bbox
    nodes_in_bbox = set()
    for nid, (x, y, z) in nodes.items():
        if (bbox_min_x <= x <= bbox_max_x and
            bbox_min_y <= y <= bbox_max_y and
            bbox_min_z <= z <= bbox_max_z):
            nodes_in_bbox.add(nid)
    
    print(f"  Found {len(nodes_in_bbox)}/{len(nodes)} nodes in contact region bbox")
    
    # Find faces where all 3 nodes are in bbox
    result = []
    for elem_id, elem_nodes in elements:
        for face_idx, (i, j, k) in enumerate(face_node_indices):
            n1, n2, n3 = elem_nodes[i], elem_nodes[j], elem_nodes[k]
            if n1 in nodes_in_bbox and n2 in nodes_in_bbox and n3 in nodes_in_bbox:
                result.append((elem_id, face_idx + 1))
    
    print(f"  Found {len(result)} mesh faces in contact region")
    return result


# =============================================================================
# Material and Analysis Configuration
# =============================================================================


@dataclass
class TimberMaterial:
    """Orthotropic timber material properties (EN 338)."""
    name: str = "C24_Softwood"
    
    # Elastic moduli [MPa]
    E_L: float = 11000.0   # Longitudinal (along grain)
    E_R: float = 370.0     # Radial  
    E_T: float = 370.0     # Tangential
    
    # Shear moduli [MPa]
    G_LR: float = 690.0
    G_LT: float = 690.0
    G_RT: float = 50.0
    
    # Poisson's ratios
    nu_LR: float = 0.37
    nu_LT: float = 0.42
    nu_RT: float = 0.47
    
    # Density [kg/m³]
    density: float = 350.0
    
    # Strength [MPa]
    f_m_k: float = 24.0    # Bending


@dataclass
class AnalysisConfig:
    """Configuration for FEA analysis."""
    mesh_size: float = 20.0
    load_magnitude: float = 1000.0  # N
    scale_factor: float = 50.0      # For visualization
    output_dir: str = "./analysis_output"
    
    # Boundary conditions by role
    fixed_roles: tuple = (Role.POST,)  # Elements fixed at base
    loaded_roles: tuple = (Role.BEAM, Role.PLATE)  # Elements receiving load


@dataclass
class AnalysisResult:
    """Results from FEA analysis."""
    success: bool
    max_displacement: float = 0.0
    max_stress: float = 0.0
    frd_file: Optional[str] = None
    mesh_file: Optional[str] = None
    error: Optional[str] = None


def analyze_element(
    element: Element,
    material: TimberMaterial,
    config: AnalysisConfig,
) -> AnalysisResult:
    """Run FEA analysis on a single element.
    
    Uses gmsh → CalculiX pipeline.
    """
    # Import here to avoid circular deps and allow optional usage
    try:
        from examples.fea_pipeline import (
            create_beam_mesh,
            write_calculix_input,
            run_calculix,
            analyze_results,
        )
    except ImportError:
        return AnalysisResult(
            success=False,
            error="FEA pipeline not available. Ensure fea_pipeline.py is in examples/",
        )
    
    output_dir = Path(config.output_dir) / element.name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Generate mesh
        mesh_file, fixed_nodes, load_nodes = create_beam_mesh(
            element.beam, str(output_dir), config.mesh_size
        )
        
        # Write CalculiX input
        ccx_file = str(output_dir / "analysis.inp")
        write_calculix_input(
            mesh_file, ccx_file, material,
            fixed_nodes, load_nodes, config.load_magnitude
        )
        
        # Run solver
        success, frd_file = run_calculix(ccx_file)
        
        if not success:
            return AnalysisResult(success=False, error=frd_file)
        
        # Parse results
        results = analyze_results(frd_file)
        
        return AnalysisResult(
            success=True,
            max_displacement=results.get("max_total", 0),
            frd_file=frd_file,
            mesh_file=mesh_file,
        )
        
    except Exception as e:
        return AnalysisResult(success=False, error=str(e))


def analyze_frame(
    frame: TimberFrame,
    material: TimberMaterial = None,
    config: AnalysisConfig = None,
) -> dict[str, AnalysisResult]:
    """Run FEA analysis on all elements in a frame.
    
    Returns dict mapping element names to results.
    """
    material = material or TimberMaterial()
    config = config or AnalysisConfig()
    
    results = {}
    for name, element in frame.elements.items():
        print(f"Analyzing {name} ({element.role.name})...")
        results[name] = analyze_element(element, material, config)
    
    return results


def print_analysis_summary(results: dict[str, AnalysisResult]):
    """Print summary of analysis results."""
    print("\n" + "=" * 50)
    print("ANALYSIS SUMMARY")
    print("=" * 50)
    
    for name, result in results.items():
        if result.success:
            print(f"{name}: max disp = {result.max_displacement:.4f} mm")
        else:
            print(f"{name}: FAILED - {result.error}")


# =============================================================================
# Multi-Step Friction Contact Utilities
# =============================================================================


def generate_friction_contact_steps(
    load_nodes: List[int],
    load_magnitude: float,
    n_load_steps: int = 10,
    friction_coeff: float = 0.4,
    stick_slope: float = 2000.0,
    use_stabilize: bool = False,
    stabilize_coeff: float = 0.05,
) -> List[str]:
    """
    Generate CalculiX input lines for multi-step friction contact loading.
    
    This implements the industry-standard approach for friction contact:
    1. Step 0: Close contact gaps (no load, no friction)
    2. Step 1: Apply first load increment (no friction yet)  
    3. Steps 2-N: Apply remaining load increments with friction active
    
    This sequence allows contact to establish before friction engages,
    avoiding the stick-slip oscillation that causes non-convergence.
    
    Args:
        load_nodes: List of node IDs to apply load to
        load_magnitude: Total load in N (will be distributed across nodes)
        n_load_steps: Number of load increments (default 10 = 10% each)
        friction_coeff: Coefficient of friction μ (default 0.4 for wood)
        stick_slope: Stick slope for penalty friction (default 2000)
        use_stabilize: Use *FRICTION, STABILIZE for additional stability
        stabilize_coeff: Stabilization coefficient (default 0.05)
    
    Returns:
        List of CalculiX input lines for all analysis steps
    """
    lines = []
    load_per_node = load_magnitude / len(load_nodes) if load_nodes else 0
    
    # Calculate cumulative load fractions
    fractions = [(i + 1) / n_load_steps for i in range(n_load_steps)]
    
    # Step 0: Contact seating only (no load, no friction)
    lines.extend([
        "",
        "** ============================================================",
        "** STEP 0: Contact seating (close gaps, no load, no friction)",
        "** ============================================================",
        "*STEP, NLGEOM, INC=40",
        "*STATIC",
        "0.1, 1.0, 1e-6, 0.2",
        "",
        "** No loads - just establish contact",
        "",
        "*NODE FILE",
        "U",
        "*END STEP",
    ])
    
    # Step 1: First load increment WITHOUT friction
    # This allows contact to settle under pressure before friction activates
    lines.extend([
        "",
        "** ============================================================",
        f"** STEP 1: Load {fractions[0]*100:.0f}% (NO friction yet)",
        "** ============================================================",
        "*STEP, NLGEOM, INC=50",
        "*STATIC",
        "0.05, 1.0, 1e-6, 0.1",
        "",
        "*CLOAD",
    ])
    
    for node in load_nodes:
        lines.append(f"{node}, 3, {-load_per_node * fractions[0]:.6f}")
    
    lines.extend([
        "",
        "*NODE FILE",
        "U, RF",
        "*EL FILE",
        "S, E",
        "*CONTACT FILE",
        "CDIS, CSTR",
        "*END STEP",
    ])
    
    # Steps 2+: Remaining load increments WITH friction
    for step_num, fraction in enumerate(fractions[1:], start=2):
        lines.extend([
            "",
            "** ============================================================",
            f"** STEP {step_num}: Load {fraction*100:.0f}% WITH friction",
            "** ============================================================",
            "*STEP, NLGEOM, INC=60",
            "*STATIC",
            "0.05, 1.0, 1e-6, 0.1",
            "",
        ])
        
        # Enable friction
        if use_stabilize:
            lines.append(f"*FRICTION, STABILIZE={stabilize_coeff}")
        else:
            lines.append("*FRICTION")
        lines.append(f"{friction_coeff}, {stick_slope}")
        
        lines.extend([
            "",
            "*CLOAD",
        ])
        
        for node in load_nodes:
            lines.append(f"{node}, 3, {-load_per_node * fraction:.6f}")
        
        lines.extend([
            "",
            "*NODE FILE",
            "U, RF",
            "*EL FILE", 
            "S, E",
            "*CONTACT FILE",
            "CDIS, CSTR",
            "*END STEP",
        ])
    
    return lines


def generate_calculix_contact_input(
    mesh_file: str,
    material: "TimberMaterial",
    fixed_nodes_left: List[int],
    fixed_nodes_right: List[int],
    load_nodes: List[int],
    load_magnitude: float,
    contact_pairs: List[dict],
    margin_gap: float = 1.0,
    n_load_steps: int = 10,
    friction_coeff: float = 0.4,
    use_stabilize: bool = False,
) -> str:
    """
    Generate complete CalculiX input file content for friction contact analysis.
    
    This creates a multi-step analysis that:
    1. Establishes contact (no load, no friction)
    2. Applies first load increment (no friction)
    3. Incrementally increases load with friction active
    
    Args:
        mesh_file: Path to mesh.inp file (will use *INCLUDE)
        material: TimberMaterial with orthotropic properties
        fixed_nodes_left: Node IDs fixed at left support
        fixed_nodes_right: Node IDs fixed at right support
        load_nodes: Node IDs for load application
        load_magnitude: Total load in N
        contact_pairs: List of dicts with 'slave' and 'master' surface names
        margin_gap: Initial contact gap in mm
        n_load_steps: Number of load increments
        friction_coeff: Coefficient of friction μ
        use_stabilize: Use *FRICTION, STABILIZE
    
    Returns:
        Complete CalculiX input file content as string
    """
    lines = [
        "** CalculiX Friction Contact Analysis (Multi-Step Method)",
        "** Generated by timber_joints.analysis",
        "**",
        "** Strategy: Contact seating → First load (no friction) → Load with friction",
        "** This avoids stick-slip oscillation during initial contact establishment",
        "**",
        "",
        f"*INCLUDE, INPUT={Path(mesh_file).name}",
        "",
        f"*MATERIAL, NAME={material.name}",
        "*ELASTIC, TYPE=ENGINEERING CONSTANTS",
        f"{material.E_L}, {material.E_R}, {material.E_T}, "
        f"{material.nu_LR}, {material.nu_LT}, {material.nu_RT}, "
        f"{material.G_LR}, {material.G_LT},",
        f"{material.G_RT}, 0.0",
        "*DENSITY",
        f"{material.density * 1e-9:.6e}",
        "",
        "*SOLID SECTION, ELSET=TIMBER, MATERIAL=" + material.name,
        "",
        "** Surface interaction - LINEAR penalty contact with friction",
        "*SURFACE INTERACTION, NAME=WOOD_CONTACT",
        "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR",
        f"1e3, 0.0, {margin_gap}",  # slope K, sigma_inf=0, c0 = margin_gap
        "",
    ]
    
    # Contact pairs
    for i, pair in enumerate(contact_pairs):
        lines.extend([
            f"** Contact pair {i+1}: {pair.get('name', f'joint_{i+1}')}",
            f"*CONTACT PAIR, INTERACTION=WOOD_CONTACT, TYPE=NODE TO SURFACE, ADJUST={margin_gap + 1}",
            f"{pair['slave']}, {pair['master']}",
            "",
        ])
    
    # Convergence controls
    lines.extend([
        "** Relaxed convergence for contact problems",
        "*CONTROLS, PARAMETERS=TIME INCREMENTATION",
        "20,30,9,200,10,4,,5",
        "*CONTROLS, PARAMETERS=FIELD, FIELD=DISPLACEMENT",
        "0.25, 0.5, 1e-5, ,0.02, 1e-5",
        "*CONTROLS, PARAMETERS=CONTACT",
        "0.001, 0.1, 100, 200",
        "",
        "** Boundary Conditions - Posts fixed at foundation",
        "*BOUNDARY",
    ])
    
    for node in fixed_nodes_left:
        lines.append(f"{node}, 1, 3, 0.0")
    
    for node in fixed_nodes_right:
        lines.append(f"{node}, 1, 3, 0.0")
    
    # Add multi-step friction loading
    step_lines = generate_friction_contact_steps(
        load_nodes=load_nodes,
        load_magnitude=load_magnitude,
        n_load_steps=n_load_steps,
        friction_coeff=friction_coeff,
        use_stabilize=use_stabilize,
    )
    lines.extend(step_lines)
    
    return '\n'.join(lines)
