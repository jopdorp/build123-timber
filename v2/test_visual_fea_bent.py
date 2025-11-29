# %%
# FEA Analysis of Complete Bent with Friction Contact
#
# Uses find_joint_contact_surfaces from analysis.py to extract contact regions

from ocp_vscode import show_object, reset_show
from pathlib import Path

from timber_joints.alignment import build_complete_bent
from timber_joints.analysis import (
    expand_shape_by_margin,
    find_joint_contact_surfaces,
    find_mesh_faces_on_surface,
    TimberMaterial,
)
from build123d import Location


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

# Scale beam down slightly to create contact gap (use actual beam shape, not a box)
beam_with_gap = expand_shape_by_margin(beam_positioned, -1.0)

# Extract contact surfaces (margin in mm to expand bbox on each side)
contact_margin = 2
left_tenon, left_mortise = find_joint_contact_surfaces(beam_with_gap, left_post, contact_margin)
right_tenon, right_mortise = find_joint_contact_surfaces(beam_with_gap, right_post, contact_margin)

# Show geometry with contact surfaces
reset_show()
show_object(left_post, name="Left Post", options={"color": "sienna", "alpha": 0.3})
show_object(right_post, name="Right Post", options={"color": "sienna", "alpha": 0.3})
show_object(beam_with_gap, name="Beam", options={"color": "burlywood", "alpha": 0.3})
show_object(left_tenon, name="Left Tenon", options={"color": "red"})
show_object(right_tenon, name="Right Tenon", options={"color": "red"})
show_object(left_mortise, name="Left Mortise", options={"color": "blue"})
show_object(right_mortise, name="Right Mortise", options={"color": "blue"})
# show_object(left_tenon.move(Location((0,0,200))), name="Left Tenon", options={"color": "red"})
# show_object(right_tenon.move(Location((0,0,200))), name="Right Tenon", options={"color": "red"})
# show_object(left_mortise.move(Location((0,200,200))), name="Left Mortise", options={"color": "blue"})
# show_object(right_mortise.move(Location((0,200,200))), name="Right Mortise", options={"color": "blue"})

# %%
# Mesh parts and run FEA

from examples.fea_pipeline import (
    run_calculix,
    analyze_results,
    read_frd_nodes,
)
from build123d import Location, export_step
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

mesh_size = 40.0

def mesh_part(step_file: str, part_name: str, mesh_size: float):
    """Mesh a single part and return nodes, elements, and surface info."""
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add(part_name)
    
    gmsh.model.occ.importShapes(step_file)
    gmsh.model.occ.synchronize()
    
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size * 0.5)
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
    elem_types, elem_tags, elem_node_tags = gmsh.model.mesh.getElements(dim=3)
    elements = []
    for i, elem_type in enumerate(elem_types):
        if elem_type == 4:  # C3D4
            tags = elem_node_tags[i]
            for j in range(0, len(tags), 4):
                elements.append([int(tags[j+k]) for k in range(4)])
    
    # Get surface faces for contact
    surfaces = gmsh.model.getEntities(dim=2)
    surface_elements = {}
    for dim, tag in surfaces:
        elem_types_s, elem_tags_s, elem_node_tags_s = gmsh.model.mesh.getElements(dim=2, tag=tag)
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

# Mesh all three parts
left_post_step = str(output_dir / "left_post.step")
right_post_step = str(output_dir / "right_post.step")
beam_step = str(output_dir / "beam.step")

left_nodes, left_elements, left_surfaces = mesh_part(left_post_step, "left_post", mesh_size)
right_nodes, right_elements, right_surfaces = mesh_part(right_post_step, "right_post", mesh_size)
beam_nodes, beam_elements, beam_surfaces = mesh_part(beam_step, "beam", mesh_size)

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

# Find boundary nodes and contact surfaces
tol = 2.0
left_post_bottom_z = left_post_bbox.min.Z
right_post_bottom_z = right_post_bbox.min.Z

fixed_nodes_left = []
fixed_nodes_right = []
load_nodes = []

left_joint_beam_nodes = []
left_joint_post_nodes = []
right_joint_beam_nodes = []
right_joint_post_nodes = []

left_joint_x_min = left_post_bbox.min.X - tol
left_joint_x_max = left_post_bbox.max.X + tol
right_joint_x_min = right_post_bbox.min.X - tol
right_joint_x_max = right_post_bbox.max.X + tol

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
    
    # Left joint contact surfaces
    if (left_joint_x_min <= x <= left_joint_x_max and
        beam_bbox.min.Z - tol <= z <= beam_bbox.max.Z + tol):
        if nid > beam_node_offset:  # Beam node
            left_joint_beam_nodes.append(nid)
        elif nid <= right_node_offset:  # Left post node
            left_joint_post_nodes.append(nid)
    
    # Right joint contact surfaces
    if (right_joint_x_min <= x <= right_joint_x_max and
        beam_bbox.min.Z - tol <= z <= beam_bbox.max.Z + tol):
        if nid > beam_node_offset:  # Beam node
            right_joint_beam_nodes.append(nid)
        elif right_node_offset < nid <= beam_node_offset:  # Right post node
            right_joint_post_nodes.append(nid)

print(f"\nBoundary conditions:")
print(f"  Left post fixed nodes: {len(fixed_nodes_left)}")
print(f"  Right post fixed nodes: {len(fixed_nodes_right)}")
print(f"  Load nodes: {len(load_nodes)}")
print(f"\nContact surfaces:")
print(f"  Left joint - beam nodes: {len(left_joint_beam_nodes)}, post nodes: {len(left_joint_post_nodes)}")
print(f"  Right joint - beam nodes: {len(right_joint_beam_nodes)}, post nodes: {len(right_joint_post_nodes)}")

# Create element lists with proper structure
left_post_elements = [(eid, nodes) for eid, nodes in all_elements if eid in left_elem_ids]
right_post_elements = [(eid, nodes) for eid, nodes in all_elements if eid in right_elem_ids]
beam_elements_list = [(eid, nodes) for eid, nodes in all_elements if eid in beam_elem_ids]

# Find mesh faces that lie on the CAD contact surfaces
print("\nFinding mesh faces on contact surfaces...")
left_beam_faces = find_mesh_faces_on_surface(beam_elements_list, all_nodes, left_tenon)
left_post_faces = find_mesh_faces_on_surface(left_post_elements, all_nodes, left_mortise)

right_beam_faces = find_mesh_faces_on_surface(beam_elements_list, all_nodes, right_tenon)
right_post_faces = find_mesh_faces_on_surface(right_post_elements, all_nodes, right_mortise)

print(f"\nContact surfaces (element faces):")
print(f"  Left joint - beam faces: {len(left_beam_faces)}, post faces: {len(left_post_faces)}")
print(f"  Right joint - beam faces: {len(right_beam_faces)}, post faces: {len(right_post_faces)}")

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

# Write CalculiX input with contact pairs and friction
load_magnitude = 10000.0  # 10 kN
load_per_node = load_magnitude / len(load_nodes) if load_nodes else 0

# Friction coefficient for wood-on-wood
friction_coeff = 0.4  # Typical for wood

ccx_lines = [
    "** CalculiX Complete Bent Frame Analysis with Friction Contact",
    "** Three separate parts with friction at mortise-tenon joints",
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
    "** Surface interaction definition with friction",
    "*SURFACE INTERACTION, NAME=WOOD_FRICTION",
    "*FRICTION",
    f"{friction_coeff}, 1e5",  # friction coeff, stick slope (lower = easier convergence)
    "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR",
    "1e4, 0.0, 1e4",  # Softer contact stiffness, clearance at zero pressure, K_infinity
    "",
]

# Contact pairs for joints
# In CalculiX contact: slave surface, master surface
# Smaller/finer mesh should be slave, larger/coarser should be master
# For mortise-tenon: beam tenon (slave) contacts post mortise (master)

if left_beam_faces and left_post_faces:
    ccx_lines.extend([
        "** Left joint contact pair (beam tenon to post mortise)",
        "*CONTACT PAIR, INTERACTION=WOOD_FRICTION, TYPE=SURFACE TO SURFACE",
        "LEFT_BEAM_SURF, LEFT_POST_SURF",
        "",
    ])

if right_beam_faces and right_post_faces:
    ccx_lines.extend([
        "** Right joint contact pair (beam tenon to post mortise)",
        "*CONTACT PAIR, INTERACTION=WOOD_FRICTION, TYPE=SURFACE TO SURFACE",
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

ccx_lines.extend([
    "",
    "** Analysis step - nonlinear static for contact",
    "*STEP, NLGEOM, INC=10",
    "*STATIC",
    "0.1, 1.0, 0.001, 0.5",  # Initial time inc, total time, min inc, max inc
    "",
    "** Load at beam midspan",
    "*CLOAD",
])

for node in load_nodes:
    ccx_lines.append(f"{node}, 3, {-load_per_node:.6f}")

ccx_lines.extend([
    "",
    "** Output requests",
    "*NODE FILE",
    "U, RF",  # Displacements and reaction forces
    "*EL FILE",
    "S, E",  # Stresses and strains
    "*CONTACT FILE",
    "CSTR, PCON",  # Contact stress and contact pressure
    "",
    "*END STEP",
])

ccx_file = str(output_dir / "analysis.inp")
with open(ccx_file, 'w') as f:
    f.write('\n'.join(ccx_lines))

print(f"\nCalculiX input: {ccx_file}")
print(f"Load: {load_magnitude} N at beam midspan")
print(f"Joint model: Contact pairs with friction (mu={friction_coeff})")
print(f"Contact surfaces: {len(left_beam_faces) + len(right_beam_faces)} beam faces, "
      f"{len(left_post_faces) + len(right_post_faces)} post faces")

# Run CalculiX
print("\nRunning FEA solver...")
success, frd_file = run_calculix(ccx_file)

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
    
    # Scale factor for visualization - keep it reasonable
    # Typical deflection might be 1-10mm, scale by 10x to make visible
    scale_factor = 10.0
    
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
print(f"\nJoint Model:")
print(f"  - Parts meshed separately (3 bodies)")
print(f"  - Contact pairs with friction (mu={friction_coeff})")
print(f"  - Contact surfaces: beam tenon faces <-> post mortise faces")
print(f"  - Surface-to-surface contact formulation")

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
