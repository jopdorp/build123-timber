"""Mesh generation utilities for timber FEA using gmsh."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Tuple, Dict
import gmsh

from build123d import Compound


@dataclass
class RefinementBox:
    """A box region for mesh refinement."""
    min_coords: tuple[float, float, float]
    max_coords: tuple[float, float, float]
    mesh_size: float


@dataclass
class MeshResult:
    """Result of meshing a single part."""
    nodes: dict[int, tuple[float, float, float]]
    elements: list[list[int]]  # List of [n1, n2, n3, n4] for C3D4 elements
    surfaces: dict[int, list[list[int]]]  # surface_tag -> list of [n1, n2, n3] faces
    
    @property
    def num_nodes(self) -> int:
        return len(self.nodes)
    
    @property
    def num_elements(self) -> int:
        return len(self.elements)


def mesh_part(
    step_file: str,
    part_name: str,
    mesh_size: float,
    refinement_boxes: Optional[list[RefinementBox]] = None,
) -> MeshResult:
    """Mesh a single part and return nodes, elements, and surface info.
    
    Args:
        step_file: Path to STEP file
        part_name: Name for the mesh model
        mesh_size: Base mesh size
        refinement_boxes: List of RefinementBox for local refinement
        
    Returns:
        MeshResult with nodes, elements, and surface information
    """
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add(part_name)
    
    gmsh.model.occ.importShapes(step_file)
    gmsh.model.occ.synchronize()
    
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size * 0.3)
    
    # Add refinement fields for contact regions
    if refinement_boxes:
        fields = []
        for box in refinement_boxes:
            box_field = gmsh.model.mesh.field.add("Box")
            gmsh.model.mesh.field.setNumber(box_field, "VIn", box.mesh_size)
            gmsh.model.mesh.field.setNumber(box_field, "VOut", mesh_size)
            gmsh.model.mesh.field.setNumber(box_field, "XMin", box.min_coords[0])
            gmsh.model.mesh.field.setNumber(box_field, "XMax", box.max_coords[0])
            gmsh.model.mesh.field.setNumber(box_field, "YMin", box.min_coords[1])
            gmsh.model.mesh.field.setNumber(box_field, "YMax", box.max_coords[1])
            gmsh.model.mesh.field.setNumber(box_field, "ZMin", box.min_coords[2])
            gmsh.model.mesh.field.setNumber(box_field, "ZMax", box.max_coords[2])
            gmsh.model.mesh.field.setNumber(box_field, "Thickness", mesh_size)
            fields.append(box_field)
        
        if len(fields) > 1:
            min_field = gmsh.model.mesh.field.add("Min")
            gmsh.model.mesh.field.setNumbers(min_field, "FieldsList", fields)
            gmsh.model.mesh.field.setAsBackgroundMesh(min_field)
        elif len(fields) == 1:
            gmsh.model.mesh.field.setAsBackgroundMesh(fields[0])
    
    gmsh.model.mesh.generate(3)
    
    # Get nodes
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    nodes = {}
    for i, tag in enumerate(node_tags):
        nodes[int(tag)] = (
            node_coords[3*i],
            node_coords[3*i + 1],
            node_coords[3*i + 2]
        )
    
    # Get C3D4 elements (4-node tetrahedra)
    elem_types, _, elem_node_tags = gmsh.model.mesh.getElements(dim=3)
    elements = []
    for i, elem_type in enumerate(elem_types):
        if elem_type == 4:  # C3D4
            tags = elem_node_tags[i]
            for j in range(0, len(tags), 4):
                elements.append([int(tags[j+k]) for k in range(4)])
    
    # Get surface faces for contact
    surfaces = gmsh.model.getEntities(dim=2)
    surface_elements = {}
    for _, tag in surfaces:
        elem_types_s, _, elem_node_tags_s = gmsh.model.mesh.getElements(dim=2, tag=tag)
        faces = []
        for i, et in enumerate(elem_types_s):
            if et == 2:  # 3-node triangles
                tags = elem_node_tags_s[i]
                for j in range(0, len(tags), 3):
                    faces.append([int(tags[j+k]) for k in range(3)])
        if faces:
            surface_elements[tag] = faces
    
    gmsh.finalize()
    
    return MeshResult(nodes=nodes, elements=elements, surfaces=surface_elements)


def get_contact_region_bbox(
    contact_faces: list[tuple[int, int]],
    elements_for_contact: list[tuple[int, list[int]]],
    nodes: dict[int, tuple[float, float, float]],
) -> Optional[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    """Get bounding box of contact face nodes.
    
    Args:
        contact_faces: List of (element_id, face_number) tuples
        elements_for_contact: List of (element_id, [n1, n2, n3, n4]) tuples
        nodes: Node coordinate dictionary
        
    Returns:
        ((xmin, ymin, zmin), (xmax, ymax, zmax)) or None if no contacts
    """
    contact_node_ids = set()
    elem_dict = {eid: enodes for eid, enodes in elements_for_contact}
    face_node_indices = [(0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 2, 3)]
    
    for elem_id, face_num in contact_faces:
        if elem_id not in elem_dict:
            continue
        elem_nodes = elem_dict[elem_id]
        i, j, k = face_node_indices[face_num - 1]
        contact_node_ids.add(elem_nodes[i])
        contact_node_ids.add(elem_nodes[j])
        contact_node_ids.add(elem_nodes[k])
    
    if not contact_node_ids:
        return None
    
    xs = [nodes[nid][0] for nid in contact_node_ids]
    ys = [nodes[nid][1] for nid in contact_node_ids]
    zs = [nodes[nid][2] for nid in contact_node_ids]
    
    return ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))


def expand_bbox(
    bbox: tuple[tuple[float, float, float], tuple[float, float, float]],
    margin: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Expand a bounding box by a margin in all directions."""
    return (
        (bbox[0][0] - margin, bbox[0][1] - margin, bbox[0][2] - margin),
        (bbox[1][0] + margin, bbox[1][1] + margin, bbox[1][2] + margin)
    )


def get_boundary_faces(
    elements: list[tuple[int, list[int]]],
) -> list[tuple[int, int]]:
    """Get all boundary faces from a tetrahedral mesh.
    
    Args:
        elements: List of (elem_id, [n1, n2, n3, n4]) tuples
        
    Returns:
        List of (element_id, face_number) for boundary faces
    """
    face_node_indices = [(0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 2, 3)]
    face_count = {}
    
    for elem_id, elem_nodes in elements:
        for face_idx, (i, j, k) in enumerate(face_node_indices):
            n1, n2, n3 = elem_nodes[i], elem_nodes[j], elem_nodes[k]
            face_key = tuple(sorted([n1, n2, n3]))
            if face_key not in face_count:
                face_count[face_key] = []
            face_count[face_key].append((elem_id, face_idx + 1))
    
    # Return only boundary faces (appear once)
    return [
        (eid, fnum) 
        for key, occs in face_count.items() 
        if len(occs) == 1 
        for eid, fnum in occs
    ]


@dataclass
class CombinedMesh:
    """Combined mesh from multiple parts with element sets."""
    nodes: dict[int, tuple[float, float, float]]
    elements: list[tuple[int, list[int]]]  # (elem_id, [n1, n2, n3, n4])
    element_sets: dict[str, list[int]]  # part_name -> list of element IDs
    node_offsets: dict[str, int]  # part_name -> node offset
    element_offsets: dict[str, int]  # part_name -> element offset


def combine_meshes(
    meshes: dict[str, MeshResult],
) -> CombinedMesh:
    """Combine multiple MeshResults into a single mesh.
    
    Args:
        meshes: Dictionary of part_name -> MeshResult
        
    Returns:
        CombinedMesh with renumbered nodes/elements and element sets
    """
    all_nodes = {}
    all_elements = []
    element_sets = {}
    node_offsets = {}
    element_offsets = {}
    
    current_node_offset = 0
    current_elem_offset = 0
    
    for part_name, mesh in meshes.items():
        node_offsets[part_name] = current_node_offset
        element_offsets[part_name] = current_elem_offset
        
        # Add nodes with offset
        for nid, coords in mesh.nodes.items():
            all_nodes[nid + current_node_offset] = coords
        
        # Add elements with offset and track element set
        elem_ids = []
        for i, elem in enumerate(mesh.elements):
            elem_id = i + 1 + current_elem_offset
            elem_ids.append(elem_id)
            all_elements.append((elem_id, [n + current_node_offset for n in elem]))
        
        element_sets[part_name] = elem_ids
        
        # Update offsets for next part
        current_node_offset += max(mesh.nodes.keys())
        current_elem_offset += len(mesh.elements)
    
    return CombinedMesh(
        nodes=all_nodes,
        elements=all_elements,
        element_sets=element_sets,
        node_offsets=node_offsets,
        element_offsets=element_offsets,
    )


def write_mesh_inp(
    mesh: CombinedMesh,
    filepath: str | Path,
    contact_surfaces: Optional[dict[str, list[tuple[int, int]]]] = None,
):
    """Write combined mesh to CalculiX .inp format.
    
    Args:
        mesh: CombinedMesh to write
        filepath: Output file path
        contact_surfaces: Dict of surface_name -> list of (elem_id, face_num)
    """
    filepath = Path(filepath)
    
    with open(filepath, 'w') as f:
        # Nodes
        f.write("*NODE, NSET=NALL\n")
        for nid in sorted(mesh.nodes.keys()):
            x, y, z = mesh.nodes[nid]
            f.write(f"{nid}, {x:.6f}, {y:.6f}, {z:.6f}\n")
        
        # Elements
        f.write("*ELEMENT, TYPE=C3D4, ELSET=EALL\n")
        for elem_id, nodes in mesh.elements:
            f.write(f"{elem_id}, {nodes[0]}, {nodes[1]}, {nodes[2]}, {nodes[3]}\n")
        
        # Element sets for each part
        for part_name, elem_ids in mesh.element_sets.items():
            elset_name = part_name.upper().replace(" ", "_")
            f.write(f"*ELSET, ELSET={elset_name}\n")
            for i, eid in enumerate(elem_ids):
                f.write(f"{eid}")
                if (i + 1) % 10 == 0 or i == len(elem_ids) - 1:
                    f.write("\n")
                else:
                    f.write(", ")
        
        # Combined element set for all timber (max 16 entries per line for CalculiX)
        f.write("*ELSET, ELSET=TIMBER\n")
        elset_names = [name.upper().replace(" ", "_") for name in mesh.element_sets.keys()]
        # Write names in chunks of 16 (CalculiX limit)
        for i in range(0, len(elset_names), 16):
            chunk = elset_names[i:i+16]
            f.write(", ".join(chunk) + "\n")
        
        # Contact surfaces
        if contact_surfaces:
            for surf_name, faces in contact_surfaces.items():
                if faces:
                    f.write(f"*SURFACE, NAME={surf_name}, TYPE=ELEMENT\n")
                    for elem_id, face in faces:
                        f.write(f"{elem_id}, S{face}\n")


# =============================================================================
# Mesh Visualization and Contact Detection
# =============================================================================

# C3D4 face node indices (which 3 nodes form each of the 4 faces of a tetrahedron)
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


def find_mesh_contact_faces(
    elements_a: List[Tuple[int, List[int]]],
    nodes_a: dict,
    elements_b: List[Tuple[int, List[int]]],
    nodes_b: dict,
    margin: float = 1.0,
    verbose: bool = True,
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
        for CalculiX ``*SURFACE`` definition. Face numbers are 1-4 for C3D4 elements.
    """
    def get_boundary_faces_dict(elements):
        """
        Find boundary faces - faces that appear in only one element.
        Returns dict mapping (elem_id, face_num) to sorted node tuple.
        """
        face_count = {}
        
        for elem_id, elem_nodes in elements:
            for face_idx, (i, j, k) in enumerate(C3D4_FACE_NODE_INDICES):
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
    
    if verbose:
        print("  Finding boundary faces...")
    boundary_a = get_boundary_faces_dict(elements_a)
    boundary_b = get_boundary_faces_dict(elements_b)
    if verbose:
        print(f"  Mesh A: {len(boundary_a)} boundary faces, Mesh B: {len(boundary_b)} boundary faces")
    
    bbox_a = get_mesh_bbox(nodes_a)
    bbox_b = get_mesh_bbox(nodes_b)
    
    if bbox_a is None or bbox_b is None:
        if verbose:
            print("  Could not compute bounding boxes!")
        return [], []
    
    if verbose:
        print(f"  Mesh A bbox: X[{bbox_a[0]:.1f}, {bbox_a[1]:.1f}] Y[{bbox_a[2]:.1f}, {bbox_a[3]:.1f}] Z[{bbox_a[4]:.1f}, {bbox_a[5]:.1f}]")
        print(f"  Mesh B bbox: X[{bbox_b[0]:.1f}, {bbox_b[1]:.1f}] Y[{bbox_b[2]:.1f}, {bbox_b[3]:.1f}] Z[{bbox_b[4]:.1f}, {bbox_b[5]:.1f}]")
    
    intersection = bbox_intersection(bbox_a, bbox_b, margin)
    if intersection is None:
        if verbose:
            print("  No bounding box intersection found!")
        return [], []
    
    if verbose:
        print(f"  Intersection (±{margin}mm): X[{intersection[0]:.1f}, {intersection[1]:.1f}] Y[{intersection[2]:.1f}, {intersection[3]:.1f}] Z[{intersection[4]:.1f}, {intersection[5]:.1f}]")
    
    faces_a = []
    for (elem_id, face_num), face_nodes in boundary_a.items():
        if face_in_bbox(face_nodes, nodes_a, intersection):
            faces_a.append((elem_id, face_num))
    
    faces_b = []
    for (elem_id, face_num), face_nodes in boundary_b.items():
        if face_in_bbox(face_nodes, nodes_b, intersection):
            faces_b.append((elem_id, face_num))
    
    if verbose:
        print(f"  Found {len(faces_a)} faces from mesh A, {len(faces_b)} faces from mesh B in contact region")
    
    return faces_a, faces_b


# =============================================================================
# Two-Pass Meshing with Contact Refinement
# =============================================================================

@dataclass
class ContactDefinition:
    """Definition of a contact pair between two parts."""
    name: str
    part_a: str  # Part name (slave surface)
    part_b: str  # Part name (master surface)


@dataclass
class MeshingConfig:
    """Configuration for mesh generation.
    
    For timber frames (5m span, ~50mm contact surfaces):
    - element_size: 150mm for bulk material (few elements, good stiffness)
    - element_size_fine: 40mm at contacts (~1-2 elements per contact, easier convergence)
    """
    element_size: float = 150.0       # Base element size (mm) - coarse for bulk
    element_size_fine: float = 40.0   # Fine mesh at contacts (mm) - ~1-2 per contact
    refinement_margin: float = 20.0   # Expand refinement regions (mm)
    contact_gap: float = 0.5          # Gap tolerance for contact detection (mm)


@dataclass
class MeshingResult:
    """Result of meshing multiple parts with contact refinement."""
    meshes: Dict[str, MeshResult]           # part_name -> MeshResult
    combined: CombinedMesh                   # Combined mesh for all parts
    contact_surfaces: Dict[str, List[Tuple[int, int]]]  # surface_name -> [(elem_id, face_num)]
    
    @property
    def total_nodes(self) -> int:
        return len(self.combined.nodes)
    
    @property
    def total_elements(self) -> int:
        return len(self.combined.elements)


def mesh_parts_with_contact_refinement(
    step_files: Dict[str, str],
    contacts: List[ContactDefinition],
    config: MeshingConfig,
    verbose: bool = True,
) -> MeshingResult:
    """Mesh multiple parts with automatic contact region refinement.
    
    This is a two-pass meshing approach:
    1. First pass: Coarse mesh to identify contact regions
    2. Second pass: Fine mesh with refinement at contact regions
    
    Args:
        step_files: Dict of part_name -> path to STEP file
        contacts: List of ContactDefinition for contact pairs
        config: MeshingConfig with mesh sizes and tolerances
        verbose: Print progress information
        
    Returns:
        MeshingResult with meshes, combined mesh, and contact surfaces
    """
    part_names = list(step_files.keys())
    
    # Pass 1: Coarse mesh to identify contact regions
    if verbose:
        print("Pass 1: Coarse mesh for contact detection...")
    
    coarse_meshes = {}
    for part_name, step_file in step_files.items():
        coarse_meshes[part_name] = mesh_part(
            step_file, part_name.lower(), config.element_size
        )
    
    # Find contact regions and build refinement boxes
    refinement_boxes: Dict[str, List[RefinementBox]] = {name: [] for name in part_names}
    
    for contact in contacts:
        mesh_a = coarse_meshes[contact.part_a]
        mesh_b = coarse_meshes[contact.part_b]
        
        elems_a = [(i + 1, e) for i, e in enumerate(mesh_a.elements)]
        elems_b = [(i + 1, e) for i, e in enumerate(mesh_b.elements)]
        
        faces_a, faces_b = find_mesh_contact_faces(
            elems_a, mesh_a.nodes,
            elems_b, mesh_b.nodes,
            margin=config.element_size + config.contact_gap,
            verbose=verbose,
        )
        
        # Add refinement boxes for both parts
        for part_name, faces, elems, nodes in [
            (contact.part_a, faces_a, elems_a, mesh_a.nodes),
            (contact.part_b, faces_b, elems_b, mesh_b.nodes),
        ]:
            bbox = get_contact_region_bbox(faces, elems, nodes)
            if bbox:
                expanded = expand_bbox(bbox, config.refinement_margin)
                refinement_boxes[part_name].append(
                    RefinementBox(expanded[0], expanded[1], config.element_size_fine)
                )
    
    # Pass 2: Refined mesh
    if verbose:
        print("Pass 2: Refined mesh at contacts...")
    
    fine_meshes = {}
    for part_name, step_file in step_files.items():
        fine_meshes[part_name] = mesh_part(
            step_file,
            part_name.lower(),
            config.element_size,
            refinement_boxes[part_name] or None,
        )
        if verbose:
            m = fine_meshes[part_name]
            print(f"  {part_name}: {m.num_nodes} nodes, {m.num_elements} elements")
    
    # Combine meshes
    combined = combine_meshes(fine_meshes)
    
    # Find contact surfaces on refined mesh
    # Use tighter margin for fine mesh - we want actual contact faces, not nearby faces
    contact_surfaces = {}
    
    for contact in contacts:
        mesh_a = fine_meshes[contact.part_a]
        mesh_b = fine_meshes[contact.part_b]
        
        elems_a = [(i + 1, e) for i, e in enumerate(mesh_a.elements)]
        elems_b = [(i + 1, e) for i, e in enumerate(mesh_b.elements)]
        
        # Use smaller margin for fine mesh contact detection
        # This should only capture faces that are actually in contact
        fine_margin = config.element_size_fine * 0.5 + config.contact_gap
        
        faces_a, faces_b = find_mesh_contact_faces(
            elems_a, mesh_a.nodes,
            elems_b, mesh_b.nodes,
            margin=fine_margin,
            verbose=verbose,
        )
        
        # Map to combined mesh element IDs
        offset_a = combined.element_offsets[contact.part_a]
        offset_b = combined.element_offsets[contact.part_b]
        
        surf_a = f"{contact.name}_{contact.part_a}_SURF"
        surf_b = f"{contact.name}_{contact.part_b}_SURF"
        
        contact_surfaces[surf_a] = [(eid + offset_a, f) for eid, f in faces_a]
        contact_surfaces[surf_b] = [(eid + offset_b, f) for eid, f in faces_b]
        
        if verbose:
            print(f"  Contact '{contact.name}': {len(faces_a)} + {len(faces_b)} faces")
    
    return MeshingResult(
        meshes=fine_meshes,
        combined=combined,
        contact_surfaces=contact_surfaces,
    )
