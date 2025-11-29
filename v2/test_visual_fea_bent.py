# %%
# FEA Analysis of Complete Bent with Friction Contact
#
# Uses pure mesh-based contact detection (no CAD geometry needed for contacts)

from ocp_vscode import show_object, reset_show
from pathlib import Path

from timber_joints.alignment import build_complete_bent
from timber_joints.analysis import (
    expand_shape_by_margin,
    find_mesh_contact_faces,
    build_mesh_faces_compound,
    TimberMaterial,
    generate_calculix_contact_input,
)
from build123d import Location

reset_show()

# Build bent and scale beam down for contact gap
left_post, right_post, beam_positioned, _ = build_complete_bent(
    post_height=3000,
    post_section=150,
    beam_length=5000,
    tenon_length=60,
    shoulder_depth=20,
    housing_depth=20,
    post_top_extension=300,
)

margin_gap = 0.5  # mm gap at contact surfaces - needs to be large enough to clear mortise depth
# Scale beam down slightly to create contact gap
beam_with_gap = expand_shape_by_margin(beam_positioned, -margin_gap)

# Mesh parts and run FEA

from examples.fea_pipeline import (
    run_calculix,
    analyze_results,
    read_frd_nodes,
)
from build123d import export_step
import numpy as np
import gmsh

output_dir = Path(__file__).parent / "fea_bent_output"
output_dir.mkdir(parents=True, exist_ok=True)

material = TimberMaterial()

# Export parts to STEP
export_step(left_post, str(output_dir / "left_post.step"))
export_step(right_post, str(output_dir / "right_post.step"))
export_step(beam_with_gap, str(output_dir / "beam.step"))

# Get bounding boxes for node classification
left_post_bbox = left_post.bounding_box()
right_post_bbox = right_post.bounding_box()
beam_bbox = beam_with_gap.bounding_box()

mesh_size = 50.0  # Base mesh size (mm)
mesh_size_fine = 20.0  # Finer mesh at contact regions (mm)

def mesh_part(step_file: str, part_name: str, mesh_size: float, refinement_boxes: list = None):
    """Mesh a single part and return nodes, elements, and surface info.
    
    Args:
        step_file: Path to STEP file
        part_name: Name for the mesh model
        mesh_size: Base mesh size
        refinement_boxes: List of (min_coords, max_coords, fine_size) tuples for local refinement
                         Each box is ((xmin, ymin, zmin), (xmax, ymax, zmax), fine_mesh_size)
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
        for i, (min_c, max_c, fine_size) in enumerate(refinement_boxes):
            # Create a box field for refinement
            box_field = gmsh.model.mesh.field.add("Box")
            gmsh.model.mesh.field.setNumber(box_field, "VIn", fine_size)
            gmsh.model.mesh.field.setNumber(box_field, "VOut", mesh_size)
            gmsh.model.mesh.field.setNumber(box_field, "XMin", min_c[0])
            gmsh.model.mesh.field.setNumber(box_field, "XMax", max_c[0])
            gmsh.model.mesh.field.setNumber(box_field, "YMin", min_c[1])
            gmsh.model.mesh.field.setNumber(box_field, "YMax", max_c[1])
            gmsh.model.mesh.field.setNumber(box_field, "ZMin", min_c[2])
            gmsh.model.mesh.field.setNumber(box_field, "ZMax", max_c[2])
            gmsh.model.mesh.field.setNumber(box_field, "Thickness", mesh_size)  # Transition zone
            fields.append(box_field)
        
        # Combine all box fields with Min
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
    
    return nodes, elements, surface_elements


def get_contact_bbox(contact_faces, elements_for_contact, nodes):
    """Get bounding box of contact face nodes."""
    # Collect all node IDs from contact faces
    contact_node_ids = set()
    elem_dict = {eid: enodes for eid, enodes in elements_for_contact}
    face_node_indices = [(0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 2, 3)]
    
    for elem_id, face_num in contact_faces:
        elem_nodes = elem_dict[elem_id]
        i, j, k = face_node_indices[face_num - 1]
        contact_node_ids.add(elem_nodes[i])
        contact_node_ids.add(elem_nodes[j])
        contact_node_ids.add(elem_nodes[k])
    
    if not contact_node_ids:
        return None
    
    # Get coordinates
    xs = [nodes[nid][0] for nid in contact_node_ids]
    ys = [nodes[nid][1] for nid in contact_node_ids]
    zs = [nodes[nid][2] for nid in contact_node_ids]
    
    return ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))


# Mesh all three parts - first pass with coarse mesh to find contact regions
left_post_step = str(output_dir / "left_post.step")
right_post_step = str(output_dir / "right_post.step")
beam_step = str(output_dir / "beam.step")

print("Pass 1: Coarse mesh to identify contact regions...")
left_nodes_coarse, left_elements_coarse, _ = mesh_part(left_post_step, "left_post", mesh_size)
right_nodes_coarse, right_elements_coarse, _ = mesh_part(right_post_step, "right_post", mesh_size)
beam_nodes_coarse, beam_elements_coarse, _ = mesh_part(beam_step, "beam", mesh_size)

# Find contact regions on coarse mesh
beam_elements_coarse_for_contact = [(i + 1, elem) for i, elem in enumerate(beam_elements_coarse)]
left_post_elements_coarse_for_contact = [(i + 1, elem) for i, elem in enumerate(left_elements_coarse)]
right_post_elements_coarse_for_contact = [(i + 1, elem) for i, elem in enumerate(right_elements_coarse)]

left_beam_faces_coarse, left_post_faces_coarse = find_mesh_contact_faces(
    beam_elements_coarse_for_contact, beam_nodes_coarse,
    left_post_elements_coarse_for_contact, left_nodes_coarse,
    margin=mesh_size + margin_gap
)
right_beam_faces_coarse, right_post_faces_coarse = find_mesh_contact_faces(
    beam_elements_coarse_for_contact, beam_nodes_coarse,
    right_post_elements_coarse_for_contact, right_nodes_coarse,
    margin=mesh_size + margin_gap
)

# Get bounding boxes of contact regions (with some margin for refinement)
refinement_margin = 10.0  # Small margin around contact region (mm)
left_beam_bbox = get_contact_bbox(left_beam_faces_coarse, beam_elements_coarse_for_contact, beam_nodes_coarse)
right_beam_bbox = get_contact_bbox(right_beam_faces_coarse, beam_elements_coarse_for_contact, beam_nodes_coarse)
left_post_bbox_contact = get_contact_bbox(left_post_faces_coarse, left_post_elements_coarse_for_contact, left_nodes_coarse)
right_post_bbox_contact = get_contact_bbox(right_post_faces_coarse, right_post_elements_coarse_for_contact, right_nodes_coarse)

# Build refinement boxes for each part
def expand_bbox(bbox, margin):
    if bbox is None:
        return None
    return (
        (bbox[0][0] - margin, bbox[0][1] - margin, bbox[0][2] - margin),
        (bbox[1][0] + margin, bbox[1][1] + margin, bbox[1][2] + margin)
    )

beam_refinement_boxes = []
if left_beam_bbox:
    expanded = expand_bbox(left_beam_bbox, refinement_margin)
    beam_refinement_boxes.append((expanded[0], expanded[1], mesh_size_fine))
if right_beam_bbox:
    expanded = expand_bbox(right_beam_bbox, refinement_margin)
    beam_refinement_boxes.append((expanded[0], expanded[1], mesh_size_fine))

left_post_refinement_boxes = []
if left_post_bbox_contact:
    expanded = expand_bbox(left_post_bbox_contact, refinement_margin)
    left_post_refinement_boxes.append((expanded[0], expanded[1], mesh_size_fine))

right_post_refinement_boxes = []
if right_post_bbox_contact:
    expanded = expand_bbox(right_post_bbox_contact, refinement_margin)
    right_post_refinement_boxes.append((expanded[0], expanded[1], mesh_size_fine))

print(f"  Found {len(beam_refinement_boxes)} beam contact regions")
print(f"  Left post contact region: {left_post_bbox_contact}")
print(f"  Right post contact region: {right_post_bbox_contact}")

# Pass 2: Re-mesh with refinement at contact regions
print("\nPass 2: Refined mesh at contact regions...")
left_nodes, left_elements, left_surfaces = mesh_part(left_post_step, "left_post", mesh_size, left_post_refinement_boxes)
right_nodes, right_elements, right_surfaces = mesh_part(right_post_step, "right_post", mesh_size, right_post_refinement_boxes)
beam_nodes, beam_elements, beam_surfaces = mesh_part(beam_step, "beam", mesh_size, beam_refinement_boxes)

print(f"  Left post: {len(left_nodes)} nodes, {len(left_elements)} elements")
print(f"  Right post: {len(right_nodes)} nodes, {len(right_elements)} elements")
print(f"  Beam: {len(beam_nodes)} nodes, {len(beam_elements)} elements")

# Renumber nodes and elements to combine into single mesh
left_node_offset = 0
left_elem_offset = 0
right_node_offset = max(left_nodes.keys())
right_elem_offset = len(left_elements)
beam_node_offset = right_node_offset + max(right_nodes.keys())
beam_elem_offset = right_elem_offset + len(right_elements)

# Combine all nodes with offsets
all_nodes = {}
for nid, coords in left_nodes.items():
    all_nodes[nid + left_node_offset] = coords
for nid, coords in right_nodes.items():
    all_nodes[nid + right_node_offset] = coords
for nid, coords in beam_nodes.items():
    all_nodes[nid + beam_node_offset] = coords

# Combine all elements with offsets
left_elem_ids = []
right_elem_ids = []
beam_elem_ids = []

all_elements = []
for i, elem in enumerate(left_elements):
    elem_id = i + 1 + left_elem_offset
    left_elem_ids.append(elem_id)
    all_elements.append((elem_id, [n + left_node_offset for n in elem]))

for i, elem in enumerate(right_elements):
    elem_id = i + 1 + right_elem_offset
    right_elem_ids.append(elem_id)
    all_elements.append((elem_id, [n + right_node_offset for n in elem]))

for i, elem in enumerate(beam_elements):
    elem_id = i + 1 + beam_elem_offset
    beam_elem_ids.append(elem_id)
    all_elements.append((elem_id, [n + beam_node_offset for n in elem]))

# Find boundary nodes for BCs and loading
tol = 2.0
left_post_bottom_z = left_post_bbox.min.Z
right_post_bottom_z = right_post_bbox.min.Z

fixed_nodes_left = []
fixed_nodes_right = []
load_nodes = []

# Beam midspan for load
beam_mid_x = (beam_bbox.min.X + beam_bbox.max.X) / 2
beam_top_z = beam_bbox.max.Z
load_tol = mesh_size * 0.8

for nid, (x, y, z) in all_nodes.items():
    # Fixed nodes at left post bottom
    if (abs(z - left_post_bottom_z) < tol and
        left_post_bbox.min.X - tol <= x <= left_post_bbox.max.X + tol and
        left_post_bbox.min.Y - tol <= y <= left_post_bbox.max.Y + tol and
        nid <= right_node_offset):  # Left post nodes only
        fixed_nodes_left.append(nid)
    
    # Fixed nodes at right post bottom
    elif (abs(z - right_post_bottom_z) < tol and
          right_post_bbox.min.X - tol <= x <= right_post_bbox.max.X + tol and
          right_post_bbox.min.Y - tol <= y <= right_post_bbox.max.Y + tol and
          right_node_offset < nid <= beam_node_offset):  # Right post nodes only
        fixed_nodes_right.append(nid)
    
    # Load nodes at beam midspan top
    elif (abs(x - beam_mid_x) < load_tol and
          abs(z - beam_top_z) < tol and
          beam_bbox.min.Y - tol <= y <= beam_bbox.max.Y + tol and
          nid > beam_node_offset):  # Beam nodes only
        load_nodes.append(nid)

print(f"\nBoundary conditions:")
print(f"  Left post fixed nodes: {len(fixed_nodes_left)}")
print(f"  Right post fixed nodes: {len(fixed_nodes_right)}")
print(f"  Load nodes: {len(load_nodes)}")

# Find contact faces using original per-part meshes (before renumbering)
# This matches how test_visual_contact_surfaces.py works
print("\nFinding contact faces from mesh bbox intersection...")

# Convert raw element lists to (elem_id, nodes) format for find_mesh_contact_faces
beam_elements_for_contact = [(i + 1, elem) for i, elem in enumerate(beam_elements)]
left_post_elements_for_contact = [(i + 1, elem) for i, elem in enumerate(left_elements)]
right_post_elements_for_contact = [(i + 1, elem) for i, elem in enumerate(right_elements)]

# Find contacts using original nodes (no offsets)
# Use mesh_size_fine for margin since we have refined mesh at contact regions
left_beam_faces_orig, left_post_faces_orig = find_mesh_contact_faces(
    beam_elements_for_contact, beam_nodes,
    left_post_elements_for_contact, left_nodes,
    margin=mesh_size_fine + margin_gap
)

right_beam_faces_orig, right_post_faces_orig = find_mesh_contact_faces(
    beam_elements_for_contact, beam_nodes,
    right_post_elements_for_contact, right_nodes,
    margin=mesh_size_fine + margin_gap
)

# Map element IDs to combined mesh IDs
# beam: elem_id -> elem_id + beam_elem_offset
# left_post: elem_id -> elem_id + left_elem_offset  
# right_post: elem_id -> elem_id + right_elem_offset
left_beam_faces = [(eid + beam_elem_offset, face) for eid, face in left_beam_faces_orig]
left_post_faces = [(eid + left_elem_offset, face) for eid, face in left_post_faces_orig]
right_beam_faces = [(eid + beam_elem_offset, face) for eid, face in right_beam_faces_orig]
right_post_faces = [(eid + right_elem_offset, face) for eid, face in right_post_faces_orig]

print(f"\nContact surfaces (element faces):")
print(f"  Left joint - beam faces: {len(left_beam_faces)}, post faces: {len(left_post_faces)}")
print(f"  Right joint - beam faces: {len(right_beam_faces)}, post faces: {len(right_post_faces)}")

# Visualize the contact faces using original per-part meshes
# (cleaner than using combined mesh with offsets)
left_beam_compound = build_mesh_faces_compound(
    left_beam_faces_orig, beam_elements_for_contact, beam_nodes
)
left_post_compound = build_mesh_faces_compound(
    left_post_faces_orig, left_post_elements_for_contact, left_nodes
)
right_beam_compound = build_mesh_faces_compound(
    right_beam_faces_orig, beam_elements_for_contact, beam_nodes
)
right_post_compound = build_mesh_faces_compound(
    right_post_faces_orig, right_post_elements_for_contact, right_nodes
)

# Build full mesh boundary surfaces for visualization
# Get all boundary faces (faces appearing only once = surface faces)
def get_all_boundary_faces(elements):
    """Get all boundary faces from a mesh."""
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
    return [(eid, fnum) for key, occs in face_count.items() if len(occs) == 1 for eid, fnum in occs]

beam_all_boundary = get_all_boundary_faces(beam_elements_for_contact)
left_post_all_boundary = get_all_boundary_faces(left_post_elements_for_contact)
right_post_all_boundary = get_all_boundary_faces(right_post_elements_for_contact)

beam_mesh_compound = build_mesh_faces_compound(beam_all_boundary, beam_elements_for_contact, beam_nodes)
left_post_mesh_compound = build_mesh_faces_compound(left_post_all_boundary, left_post_elements_for_contact, left_nodes)
right_post_mesh_compound = build_mesh_faces_compound(right_post_all_boundary, right_post_elements_for_contact, right_nodes)

reset_show()

# Y offset for side-by-side comparison
y_offset = 500

# Contact surfaces (original position)
show_object(left_beam_compound, name="Left Beam Contact", options={"color": "red"})
show_object(left_post_compound, name="Left Post Contact", options={"color": "blue"})
show_object(right_beam_compound, name="Right Beam Contact", options={"color": "orange"})
show_object(right_post_compound, name="Right Post Contact", options={"color": "cyan"})

# Full meshes offset in Y for comparison
show_object(beam_mesh_compound.moved(Location((0, y_offset, 0))), name="Beam Mesh", options={"color": "burlywood"})
show_object(left_post_mesh_compound.moved(Location((0, y_offset, 0))), name="Left Post Mesh", options={"color": "sienna", "alpha": 0.3})
show_object(right_post_mesh_compound.moved(Location((0, y_offset, 0))), name="Right Post Mesh", options={"color": "sienna", "alpha": 0.3})

print("\nVisualized contact surfaces (front) and full meshes (offset in Y)!")

# %% 
# Write mesh file and run FEA

mesh_file = str(output_dir / "mesh.inp")
with open(mesh_file, 'w') as f:
    f.write("*NODE, NSET=NALL\n")
    for nid in sorted(all_nodes.keys()):
        x, y, z = all_nodes[nid]
        f.write(f"{nid}, {x:.6f}, {y:.6f}, {z:.6f}\n")
    
    f.write("*ELEMENT, TYPE=C3D4, ELSET=EALL\n")
    for elem_id, nodes in all_elements:
        f.write(f"{elem_id}, {nodes[0]}, {nodes[1]}, {nodes[2]}, {nodes[3]}\n")
    
    # Element sets for each part
    f.write("*ELSET, ELSET=LEFT_POST\n")
    for i, eid in enumerate(left_elem_ids):
        f.write(f"{eid}")
        if (i + 1) % 10 == 0 or i == len(left_elem_ids) - 1:
            f.write("\n")
        else:
            f.write(", ")
    
    f.write("*ELSET, ELSET=RIGHT_POST\n")
    for i, eid in enumerate(right_elem_ids):
        f.write(f"{eid}")
        if (i + 1) % 10 == 0 or i == len(right_elem_ids) - 1:
            f.write("\n")
        else:
            f.write(", ")
    
    f.write("*ELSET, ELSET=BEAM\n")
    for i, eid in enumerate(beam_elem_ids):
        f.write(f"{eid}")
        if (i + 1) % 10 == 0 or i == len(beam_elem_ids) - 1:
            f.write("\n")
        else:
            f.write(", ")
    
    # Combined element set for timber material
    f.write("*ELSET, ELSET=TIMBER\n")
    f.write("LEFT_POST, RIGHT_POST, BEAM\n")
    
    # Element-face surfaces for contact (using *SURFACE with element faces)
    # Format: element_id, Sface_number
    if left_beam_faces:
        f.write("*SURFACE, NAME=LEFT_BEAM_SURF, TYPE=ELEMENT\n")
        for elem_id, face in left_beam_faces:
            f.write(f"{elem_id}, S{face}\n")
    
    if left_post_faces:
        f.write("*SURFACE, NAME=LEFT_POST_SURF, TYPE=ELEMENT\n")
        for elem_id, face in left_post_faces:
            f.write(f"{elem_id}, S{face}\n")
    
    if right_beam_faces:
        f.write("*SURFACE, NAME=RIGHT_BEAM_SURF, TYPE=ELEMENT\n")
        for elem_id, face in right_beam_faces:
            f.write(f"{elem_id}, S{face}\n")
    
    if right_post_faces:
        f.write("*SURFACE, NAME=RIGHT_POST_SURF, TYPE=ELEMENT\n")
        for elem_id, face in right_post_faces:
            f.write(f"{elem_id}, S{face}\n")

print(f"\nMesh file: {mesh_file}")

# Write CalculiX input - single static step with friction from start
# CalculiX doesn't support changing contact between steps, so we use
# friction with stabilization from the beginning

load_magnitude = 10000.0  # 10 kN = ~1 tonne total
load_per_node = load_magnitude / len(load_nodes) if load_nodes else 0

# Friction parameters - realistic wood-on-wood values
friction_coeff = 0.35  # Wood-on-wood static friction (typical range 0.25-0.5)
stick_slope = 1000.0  # Tangential penalty ≈ normal penalty for balanced behavior
stabilize = 0.01  # Friction stabilization (damping for convergence)

ccx_lines = [
    "** CalculiX Complete Bent Frame Analysis",
    "** Single static step with friction contact and stabilization",
    "**",
    "",
    f"*INCLUDE, INPUT=mesh.inp",
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
    "** Frictional surface interaction with stabilization",
    "*SURFACE INTERACTION, NAME=WOOD_CONTACT",
    "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR",
    f"1e3, 0.0, {margin_gap}",
    f"*FRICTION, STABILIZE={stabilize}",
    f"{friction_coeff}, {stick_slope}",
    "",
]

# Contact pairs for joints
if left_beam_faces and left_post_faces:
    ccx_lines.extend([
        "** Left joint contact pair",
        f"*CONTACT PAIR, INTERACTION=WOOD_CONTACT, TYPE=SURFACE TO SURFACE, ADJUST={margin_gap + 1}",
        "LEFT_BEAM_SURF, LEFT_POST_SURF",
        "",
    ])

if right_beam_faces and right_post_faces:
    ccx_lines.extend([
        "** Right joint contact pair", 
        f"*CONTACT PAIR, INTERACTION=WOOD_CONTACT, TYPE=SURFACE TO SURFACE, ADJUST={margin_gap + 1}",
        "RIGHT_BEAM_SURF, RIGHT_POST_SURF",
        "",
    ])

ccx_lines.extend([
    "** Boundary Conditions - Posts fixed at foundation",
    "*BOUNDARY",
])

for node in fixed_nodes_left:
    ccx_lines.append(f"{node}, 1, 3, 0.0")

for node in fixed_nodes_right:
    ccx_lines.append(f"{node}, 1, 3, 0.0")

# Single static step with friction and stabilization
ccx_lines.extend([
    "",
    "** ============================================================",
    "** Single static step with friction contact",
    "** ============================================================",
    "*STEP, NLGEOM, INC=100",
    "*STATIC",
    "0.2, 1.0, 1e-5, 0.4",  # Larger initial step, smaller max
    "",
    "** Contact convergence controls",
    "*CONTROLS, PARAMETERS=CONTACT",
    "0.005, 0.15, 75, 150",
    "",
    "** Full load at beam midspan",
    "*CLOAD",
])

for node in load_nodes:
    ccx_lines.append(f"{node}, 3, {-load_per_node:.6f}")

ccx_lines.extend([
    "",
    "*NODE FILE",
    "U, RF",
    "*EL FILE",
    "S, E",
    "*CONTACT FILE",
    "CDIS, CSTR",
    "",
    "*END STEP",
])

ccx_file = str(output_dir / "analysis.inp")
with open(ccx_file, 'w') as f:
    f.write('\n'.join(ccx_lines))

print(f"\nCalculiX input: {ccx_file}")
print(f"Load: {load_magnitude} N at beam midspan")
print(f"Joint model: Static with friction μ={friction_coeff}")
print(f"  Friction stabilization: {stabilize}")
print(f"  Contact surfaces: {len(left_beam_faces) + len(right_beam_faces)} beam faces, {len(left_post_faces) + len(right_post_faces)} post faces")

# Run CalculiX with full output
print("\nRunning FEA solver...")
import subprocess
from pathlib import Path

ccx_path = Path(ccx_file)
work_dir = ccx_path.parent
job_name = ccx_path.stem

cmd = ["ccx", "-i", job_name]
print(f"Running: {' '.join(cmd)} (in {work_dir})")

result = subprocess.run(
    cmd,
    cwd=work_dir,
    capture_output=True,
    text=True,
    timeout=600,
)

# Print FULL solver output
print("\n" + "="*60)
print("CALCULIX SOLVER OUTPUT")
print("="*60)
print(result.stdout)
if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)
print("="*60)

success = result.returncode == 0
frd_file = str(work_dir / f"{job_name}.frd") if success else None

if success:
    # Analyze results
    results = analyze_results(frd_file)
    print(f"\nFEA Results:")
    print(f"  Max Z displacement: {results['max_uz']:.4f} mm")
    print(f"  Max total displacement: {results['max_total']:.4f} mm")
else:
    print(f"FEA failed: {frd_file}")
    results = None

# Visualize FEA results in OCP
# Show the deformed shape of the COMPLETE BENT overlaid on the original

if results and "displacements" in results:
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.gp import gp_Pnt
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Compound
    
    # Read mesh data from our custom mesh file
    frd_nodes = read_frd_nodes(frd_file)
    displacements = results["displacements"]
    
    # Read elements from our mesh file
    elements = []
    with open(mesh_file, 'r') as f:
        in_elements = False
        for line in f:
            line = line.strip()
            if line.startswith("*ELEMENT"):
                in_elements = True
                continue
            elif line.startswith("*"):
                in_elements = False
                continue
            if in_elements and line and not line.startswith("**"):
                parts = [int(p) for p in line.split(",")]
                if len(parts) == 5:  # elem_id, n1, n2, n3, n4
                    elements.append(parts[1:])  # Just the nodes
    
    # Scale factor for visualization - make deformation visible but not absurd
    # With ~5mm deflection on 5000mm beam, 20x scale shows it clearly
    scale_factor = 20.0  # Moderate exaggeration (5mm -> 100mm visual)
    
    # Calculate displacement magnitudes
    disp_mag = {}
    for node_id, (ux, uy, uz) in displacements.items():
        disp_mag[node_id] = np.sqrt(ux**2 + uy**2 + uz**2)
    
    max_disp = max(disp_mag.values()) if disp_mag else 1.0
    
    # Build deformed coordinates using the original node positions
    deformed_nodes = {}
    for node_id, (x, y, z) in frd_nodes.items():
        if node_id in displacements:
            ux, uy, uz = displacements[node_id]
            deformed_nodes[node_id] = (
                x + ux * scale_factor,
                y + uy * scale_factor,
                z + uz * scale_factor,
            )
    
    # Extract outer triangular faces from tetrahedra
    face_count = {}
    for elem in elements:
        if len(elem) == 4:
            n1, n2, n3, n4 = elem
            faces = [
                tuple(sorted([n1, n2, n3])),
                tuple(sorted([n1, n2, n4])),
                tuple(sorted([n1, n3, n4])),
                tuple(sorted([n2, n3, n4])),
            ]
            for f in faces:
                face_count[f] = face_count.get(f, 0) + 1
    
    outer_faces = [f for f, count in face_count.items() if count == 1]
    
    # Create compound of deformed triangular faces
    builder = BRep_Builder()
    deformed_compound = TopoDS_Compound()
    builder.MakeCompound(deformed_compound)
    
    for face_nodes in outer_faces:
        n1, n2, n3 = face_nodes
        
        if n1 not in deformed_nodes or n2 not in deformed_nodes or n3 not in deformed_nodes:
            continue
        
        p1 = gp_Pnt(*deformed_nodes[n1])
        p2 = gp_Pnt(*deformed_nodes[n2])
        p3 = gp_Pnt(*deformed_nodes[n3])
        
        try:
            polygon = BRepBuilderAPI_MakePolygon(p1, p2, p3, True)
            if polygon.IsDone():
                wire = polygon.Wire()
                face_maker = BRepBuilderAPI_MakeFace(wire, True)
                if face_maker.IsDone():
                    builder.Add(deformed_compound, face_maker.Face())
        except Exception:
            pass
    
    # Show everything together
    print(f"\nVisualization:")
    print(f"  Scale factor: {scale_factor}x")
    print(f"  Max displacement: {max_disp:.4f} mm")
    print(f"  Scaled max: {max_disp * scale_factor:.2f} mm")
    
    reset_show()
    
    # Original structure (semi-transparent)
    show_object(left_post, name="Left Post (original)", options={"color": "sienna", "alpha": 0.3})
    show_object(right_post, name="Right Post (original)", options={"color": "sienna", "alpha": 0.3})
    show_object(beam_with_gap, name="Beam (original)", options={"color": "burlywood", "alpha": 0.3})
    
    # Deformed structure (red mesh)
    show_object(deformed_compound, name=f"Deformed Frame ({scale_factor}x)", options={"color": "red"})

# Summary

print("\n" + "=" * 60)
print("COMPLETE BENT FRAME FEA ANALYSIS SUMMARY")
print("=" * 60)
print(f"Structure: Complete bent frame (2 posts + beam)")
print(f"  Post: 3000 x 150 x 150 mm")
print(f"  Beam: 5000 x 150 x 150 mm")
print(f"  Joints: Shouldered mortise-and-tenon with friction contact")
print(f"  Material: {material.name}")
print(f"  Load: {load_magnitude} N at beam midspan")
print(f"  Boundary: Posts fixed at foundation (Z=0)")
print(f"\nJoint Model (Single Static Step):")
print(f"  - Friction coefficient μ={friction_coeff}")
print(f"  - Friction stabilization: {stabilize}")
print(f"  - Contact: beam tenon faces <-> post mortise faces")

if results:
    print(f"\nResults:")
    print(f"  Max deflection: {results['max_total']:.4f} mm")
    print(f"  Max Z deflection: {results['max_uz']:.4f} mm")
    
    # Simple deflection check (L/300 serviceability limit for beam)
    limit = 5000 / 300
    print(f"  Beam deflection limit (L/300): {limit:.2f} mm")
    
    if abs(results['max_uz']) < limit:
        print(f"  Status: PASS ✓")
    else:
        print(f"  Status: FAIL ✗ (exceeds deflection limit)")
else:
    print("\nFEA analysis did not complete successfully.")

print("=" * 60)

# %%
