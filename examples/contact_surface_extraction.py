# %%
# Visual Test: Contact Surface Extraction
#
# Tests find_joint_contact_surfaces from analysis.py
# Extracts and visualizes tenon/mortise contact regions for a timber bent

from ocp_vscode import show_object, reset_show
from build123d import Location

from timber_joints.alignment import build_complete_bent
from timber_joints.utils import scale_shape_in_place

# Build bent and downscale beam to create gap for contact analysis
bent = build_complete_bent(
    post_height=3000,
    post_section=150,
    beam_length=5000,
)
left_post, right_post, beam_positioned = bent.left_post, bent.right_post, bent.beam

beam_with_gap = scale_shape_in_place(beam_positioned, 1 - 1e-6)

# Extract contact surfaces (uses default tolerance of 0.1mm)
left_tenon, left_mortise = find_joint_contact_surfaces(beam_with_gap, left_post)
right_tenon, right_mortise = find_joint_contact_surfaces(beam_with_gap, right_post)

# Visualize: Row 1 = geometry, Row 2 = tenons (red), Row 3 = mortises (blue)
y_offset = 500
reset_show()

show_object(left_post, name="Left Post", options={"color": "sienna", "alpha": 0.3})
show_object(right_post, name="Right Post", options={"color": "sienna", "alpha": 0.3})
show_object(beam_with_gap, name="Beam", options={"color": "burlywood", "alpha": 0.3})

show_object(left_tenon.moved(Location((0, y_offset, 0))), name="Left Tenon", options={"color": "red"})
show_object(right_tenon.moved(Location((0, y_offset, 0))), name="Right Tenon", options={"color": "red"})

show_object(left_mortise.moved(Location((0, 2*y_offset, 0))), name="Left Mortise", options={"color": "blue"})
show_object(right_mortise.moved(Location((0, 2*y_offset, 0))), name="Right Mortise", options={"color": "blue"})

# Summary
left_tenon_area = sum(f.area for f in left_tenon.faces())
left_mortise_area = sum(f.area for f in left_mortise.faces())
right_tenon_area = sum(f.area for f in right_tenon.faces())
right_mortise_area = sum(f.area for f in right_mortise.faces())

print(f"Left joint:  tenon {len(left_tenon.faces())} faces ({left_tenon_area:.0f}mm²), "
      f"mortise {len(left_mortise.faces())} faces ({left_mortise_area:.0f}mm²)")
print(f"Right joint: tenon {len(right_tenon.faces())} faces ({right_tenon_area:.0f}mm²), "
      f"mortise {len(right_mortise.faces())} faces ({right_mortise_area:.0f}mm²)")

# %%
# Visual Test 2: Using expand_shape_by_margin instead of scale_shape_in_place
#
# This test uses a fixed margin (in mm) to shrink the beam, which gives
# consistent gap size regardless of beam dimensions.

from timber_joints.utils import expand_shape_by_margin

# Build a fresh bent
bent2 = build_complete_bent(
    post_height=3000,
    post_section=150,
    beam_length=5000,
)
left_post2, right_post2, beam_positioned2 = bent2.left_post, bent2.right_post, bent2.beam

# Shrink beam by 0.5mm on each side using expand_shape_by_margin with negative margin
beam_with_gap2 = expand_shape_by_margin(beam_positioned2, -0.5)

# Extract contact surfaces
left_tenon2, left_mortise2 = find_joint_contact_surfaces(beam_with_gap2, left_post2)
right_tenon2, right_mortise2 = find_joint_contact_surfaces(beam_with_gap2, right_post2)

# Visualize with Z offset to separate from first test
z_offset = 1000
reset_show()

show_object(left_post2.moved(Location((0, 0, z_offset))), name="Left Post (expand)", options={"color": "sienna", "alpha": 0.3})
show_object(right_post2.moved(Location((0, 0, z_offset))), name="Right Post (expand)", options={"color": "sienna", "alpha": 0.3})
show_object(beam_with_gap2.moved(Location((0, 0, z_offset))), name="Beam (expand)", options={"color": "burlywood", "alpha": 0.3})

show_object(left_tenon2.moved(Location((0, y_offset, z_offset))), name="Left Tenon (expand)", options={"color": "red"})
show_object(right_tenon2.moved(Location((0, y_offset, z_offset))), name="Right Tenon (expand)", options={"color": "red"})

show_object(left_mortise2.moved(Location((0, 2*y_offset, z_offset))), name="Left Mortise (expand)", options={"color": "blue"})
show_object(right_mortise2.moved(Location((0, 2*y_offset, z_offset))), name="Right Mortise (expand)", options={"color": "blue"})

# Summary
left_tenon_area2 = sum(f.area for f in left_tenon2.faces())
left_mortise_area2 = sum(f.area for f in left_mortise2.faces())
right_tenon_area2 = sum(f.area for f in right_tenon2.faces())
right_mortise_area2 = sum(f.area for f in right_mortise2.faces())

print(f"\n=== Test 2: expand_shape_by_margin(-0.5mm) ===")
print(f"Left joint:  tenon {len(left_tenon2.faces())} faces ({left_tenon_area2:.0f}mm²), "
      f"mortise {len(left_mortise2.faces())} faces ({left_mortise_area2:.0f}mm²)")
print(f"Right joint: tenon {len(right_tenon2.faces())} faces ({right_tenon_area2:.0f}mm²), "
      f"mortise {len(right_mortise2.faces())} faces ({right_mortise_area2:.0f}mm²)")

# %%
# Visual Test 3: Pure mesh-based contact face detection
#
# This test meshes the parts and finds contact faces using only
# mesh bounding box intersection - no CAD geometry needed!

from ocp_vscode import show_object, reset_show
from build123d import Location, Compound, export_step
from pathlib import Path
import gmsh
from timber_joints.alignment import build_complete_bent
from timber_joints.utils import expand_shape_by_margin
from timber_joints.fea.meshing import find_mesh_contact_faces, build_mesh_faces_compound

# Build a fresh bent
bent3 = build_complete_bent(
    post_height=3000,
    post_section=150,
    beam_length=5000,
)
left_post3, right_post3, beam_positioned3 = bent3.left_post, bent3.right_post, bent3.beam

beam_with_gap3 = expand_shape_by_margin(beam_positioned3, -0.5)

# Export to STEP for meshing
output_dir = Path(__file__).parent / "contact_test_output"
output_dir.mkdir(parents=True, exist_ok=True)

export_step(left_post3, str(output_dir / "left_post.step"))
export_step(beam_with_gap3, str(output_dir / "beam.step"))

# Mesh the parts
mesh_size = 30.0

def mesh_part(step_file: str, part_name: str):
    """Mesh a part and return nodes and elements."""
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add(part_name)
    gmsh.model.occ.importShapes(step_file)
    gmsh.model.occ.synchronize()
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size * 0.5)
    gmsh.model.mesh.generate(3)
    
    # Get nodes: {node_id: (x, y, z)}
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    nodes = {}
    for i, tag in enumerate(node_tags):
        nodes[int(tag)] = (node_coords[3*i], node_coords[3*i+1], node_coords[3*i+2])
    
    # Get C3D4 tetrahedra: [(element_id, [node1, node2, node3, node4]), ...]
    elem_types, elem_tags, elem_node_tags = gmsh.model.mesh.getElements(dim=3)
    elements = []
    for i, elem_type in enumerate(elem_types):
        if elem_type == 4:  # C3D4 tetrahedron
            tags = elem_node_tags[i]
            for j in range(0, len(tags), 4):
                elem_id = len(elements) + 1
                elements.append((elem_id, [int(tags[j+k]) for k in range(4)]))
    
    gmsh.finalize()
    return nodes, elements

print("\n=== Test 3: Pure mesh-based contact detection ===")
print("Meshing parts...")

left_post_nodes, left_post_elements = mesh_part(str(output_dir / "left_post.step"), "left_post")
beam_nodes, beam_elements = mesh_part(str(output_dir / "beam.step"), "beam")

print(f"Left post: {len(left_post_nodes)} nodes, {len(left_post_elements)} elements")
print(f"Beam: {len(beam_nodes)} nodes, {len(beam_elements)} elements")

# Find contact faces using pure mesh approach (no CAD needed!)
# margin should be larger than shoulder_depth (20mm) to capture shoulder faces
print("\nFinding contact faces from mesh bounding box intersection...")
beam_contact_faces, post_contact_faces = find_mesh_contact_faces(
    beam_elements, beam_nodes,
    left_post_elements, left_post_nodes,
    margin=mesh_size  # > shoulder_depth to include shoulder contact faces
)

print(f"Beam contact: {len(beam_contact_faces)} mesh faces")
print(f"Post contact: {len(post_contact_faces)} mesh faces")

# Build mesh face compounds using library function
beam_contact_compound = build_mesh_faces_compound(beam_contact_faces, beam_elements, beam_nodes)
post_contact_compound = build_mesh_faces_compound(post_contact_faces, left_post_elements, left_post_nodes)

# Visualize
y_offset = 500
z_offset3 = 2000
reset_show()

# Original geometry (transparent)
show_object(left_post3.moved(Location((0, 0, z_offset3))), name="Left Post", options={"color": "sienna", "alpha": 0.2})
show_object(beam_with_gap3.moved(Location((0, 0, z_offset3))), name="Beam", options={"color": "burlywood", "alpha": 0.2})

# Mesh contact faces
show_object(beam_contact_compound.moved(Location((0, y_offset, z_offset3))), name="Beam Contact Faces", options={"color": "orange"})
show_object(post_contact_compound.moved(Location((0, 2*y_offset, z_offset3))), name="Post Contact Faces", options={"color": "cyan"})

print("\nVisualization: Beam contact (orange), Post contact (cyan)")

# %%
