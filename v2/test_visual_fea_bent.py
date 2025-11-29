# %%
# FEA Analysis of Complete Bent (Test 7 + FEA)
# This demonstrates running structural analysis on a timber frame assembly

from ocp_vscode import show_object, reset_show
from build123d import Location, Part
from pathlib import Path

from timber_joints.alignment import build_complete_bent

# Build the Complete Bent using utility function

# Dimensions
post_height = 3000
post_section = 150
beam_length = 5000
tenon_length = 60
shoulder_depth = 20
housing_depth = 20
post_top_extension = 300

left_post_with_mortise, right_post_with_mortise, positioned_beam, beam = build_complete_bent(
    post_height=post_height,
    post_section=post_section,
    beam_length=beam_length,
    tenon_length=tenon_length,
    shoulder_depth=shoulder_depth,
    housing_depth=housing_depth,
    post_top_extension=post_top_extension,
)

print("=== Complete Bent Assembly ===")
print(f"Post height: {post_height}mm, section: {post_section}mm")
print(f"Beam length: {beam_length}mm")

# Show the assembled bent
reset_show()
show_object(left_post_with_mortise, name="Left Post", options={"color": "sienna", "alpha": 0.7})
show_object(right_post_with_mortise, name="Right Post", options={"color": "sienna", "alpha": 0.7})
show_object(positioned_beam, name="Beam", options={"color": "burlywood"})

from examples.fea_pipeline import (
    TimberMaterial,
    write_calculix_input,
    run_calculix,
    analyze_results,
    read_frd_nodes,
    read_frd_displacements,
    read_mesh_elements,
)
import numpy as np
import os

# Output directory for FEA files
output_dir = Path(__file__).parent / "fea_bent_output"
output_dir.mkdir(parents=True, exist_ok=True)

# Material properties
material = TimberMaterial(name="C24_Softwood")

# Create mesh for simply supported beam (fixed at BOTH ends, load in middle)
# This is different from the cantilever in fea_pipeline.py

print("\n=== FEA Analysis of Simply Supported Beam ===")
print("Generating mesh...")

try:
    import gmsh
except ImportError:
    raise ImportError("gmsh not installed. Run: pip install gmsh")

gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.add("timber_beam_simply_supported")

# Create box geometry
mesh_size = 50.0
box = gmsh.model.occ.addBox(0, 0, 0, beam.length, beam.width, beam.height)
gmsh.model.occ.synchronize()

# Physical group for volume
volumes = gmsh.model.getEntities(dim=3)
timber_tag = gmsh.model.addPhysicalGroup(3, [v[1] for v in volumes])
gmsh.model.setPhysicalName(3, timber_tag, "TIMBER")

gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
gmsh.option.setNumber("Mesh.SaveAll", 0)
gmsh.model.mesh.generate(3)

# Get nodes
node_tags, node_coords, _ = gmsh.model.mesh.getNodes()

# Find boundary nodes - BOTH ends are fixed (simply supported)
tol = 1e-3
left_fixed_nodes = []  # x = 0
right_fixed_nodes = []  # x = beam.length
load_nodes = []  # x = beam.length / 2 (middle)

mid_x = beam.length / 2
load_tol = mesh_size * 0.6  # Wider tolerance for mid-span nodes

for i, tag in enumerate(node_tags):
    x = node_coords[3 * i]
    if abs(x) < tol:
        left_fixed_nodes.append(int(tag))
    elif abs(x - beam.length) < tol:
        right_fixed_nodes.append(int(tag))
    elif abs(x - mid_x) < load_tol:
        load_nodes.append(int(tag))

# Export mesh
mesh_file = os.path.join(str(output_dir), "mesh.inp")
gmsh.write(mesh_file)

print(f"Mesh: {len(node_tags)} nodes")
print(f"  Left support (x=0): {len(left_fixed_nodes)} nodes")
print(f"  Right support (x={beam.length}): {len(right_fixed_nodes)} nodes")
print(f"  Load nodes (x≈{mid_x}): {len(load_nodes)} nodes")

gmsh.finalize()

# Write custom CalculiX input for simply supported beam

load_magnitude = 10000.0  # 10 kN distributed load at midspan
load_per_node = load_magnitude / len(load_nodes) if load_nodes else 0

ccx_lines = [
    "** CalculiX Simply Supported Beam Analysis",
    "** Timber material - beam supported at both ends",
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
    f"*SOLID SECTION, ELSET=TIMBER, MATERIAL={material.name}",
    "",
    "** Boundary Conditions - Simply supported (pinned at both ends)",
    "** Left end: fix all translations",
    "*BOUNDARY",
]

for node in left_fixed_nodes:
    ccx_lines.append(f"{node}, 1, 3, 0.0")

ccx_lines.append("** Right end: fix Y and Z (allow X for thermal expansion)")
for node in right_fixed_nodes:
    ccx_lines.append(f"{node}, 2, 3, 0.0")  # Only fix Y and Z

ccx_lines.extend([
    "",
    "*STEP",
    "*STATIC",
    "",
    "** Distributed load at midspan (downward in Z)",
    "*CLOAD",
])

for node in load_nodes:
    ccx_lines.append(f"{node}, 3, {-load_per_node:.6f}")

ccx_lines.extend([
    "",
    "*NODE FILE",
    "U",
    "*EL FILE", 
    "S",
    "",
    "*END STEP",
])

ccx_file = str(output_dir / "analysis.inp")
with open(ccx_file, 'w') as f:
    f.write('\n'.join(ccx_lines))

print(f"\nCalculiX input: {ccx_file}")
print(f"Load: {load_magnitude} N distributed over {len(load_nodes)} nodes at midspan")

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
# Show the deformed shape overlaid on the original bent

if results and "displacements" in results:
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.gp import gp_Pnt
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Compound
    
    # Read mesh data
    nodes = read_frd_nodes(frd_file)
    displacements = results["displacements"]
    elements = read_mesh_elements(mesh_file)
    
    # Scale factor for visualization
    scale_factor = 20.0  # Exaggerate displacement for visibility
    
    # Calculate displacement magnitudes
    disp_mag = {}
    for node_id, (ux, uy, uz) in displacements.items():
        disp_mag[node_id] = np.sqrt(ux**2 + uy**2 + uz**2)
    
    max_disp = max(disp_mag.values()) if disp_mag else 1.0
    
    # Build deformed coordinates (shifted to match positioned beam)
    # The mesh was created at origin, but our beam is positioned
    beam_bbox = positioned_beam.bounding_box()
    beam_origin_x = beam_bbox.min.X
    beam_origin_y = beam_bbox.min.Y
    beam_origin_z = beam_bbox.min.Z
    
    deformed_nodes = {}
    for node_id, (x, y, z) in nodes.items():
        if node_id in displacements:
            ux, uy, uz = displacements[node_id]
            # Shift to positioned beam location + scaled deformation
            deformed_nodes[node_id] = (
                x + beam_origin_x + ux * scale_factor,
                y + beam_origin_y + uy * scale_factor,
                z + beam_origin_z + uz * scale_factor,
            )
    
    # Extract outer triangular faces from tetrahedra
    face_count = {}
    for elem in elements:
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
    show_object(left_post_with_mortise, name="Left Post", options={"color": "sienna", "alpha": 0.3})
    show_object(right_post_with_mortise, name="Right Post", options={"color": "sienna", "alpha": 0.3})
    show_object(positioned_beam, name="Original Beam", options={"color": "burlywood", "alpha": 0.3})
    
    # Deformed beam (red mesh)
    show_object(deformed_compound, name=f"Deformed Beam ({scale_factor}x)", options={"color": "red"})

# Summary

print("\n" + "=" * 60)
print("BENT FRAME FEA ANALYSIS SUMMARY")
print("=" * 60)
print(f"Structure: Simply supported beam between two posts")
print(f"  Post: {post_height} x {post_section} x {post_section} mm")
print(f"  Beam: {beam_length} x {post_section} x {post_section} mm")
print(f"  Material: {material.name}")
print(f"  Load: {load_magnitude} N at midspan")
print(f"  Boundary: Pinned at both ends (left fixed, right roller)")

if results:
    print(f"\nResults:")
    print(f"  Max deflection: {results['max_total']:.4f} mm")
    
    # Simple deflection check (L/300 serviceability limit for simply supported)
    limit = beam_length / 300
    print(f"  Deflection limit (L/300): {limit:.2f} mm")
    
    if results['max_total'] < limit:
        print(f"  Status: PASS ✓")
    else:
        print(f"  Status: FAIL ✗ (exceeds deflection limit)")
else:
    print("\nFEA analysis did not complete successfully.")

print("=" * 60)

# %%
