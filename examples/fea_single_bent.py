# %%
"""FEA test using high-level frame API."""

from pathlib import Path
import tempfile
from build123d import Location, export_step
from ocp_vscode import reset_show, show_object

from timber_joints.alignment import build_complete_bent, BraceParams
from timber_joints.fea import (
    TimberFrame, show_fea_results, LoadBC,
    get_boundary_faces, build_mesh_faces_compound,
    mesh_parts_with_contact_refinement, ContactDefinition, MeshingConfig,
)

reset_show()

# Build bent frame with braces
bent = build_complete_bent(
    post_height=3000,
    post_section=150,
    beam_length=5000,
    brace_params=BraceParams(),
)
left_post, right_post, beam = bent.left_post, bent.right_post, bent.beam
braces = [b for b in [bent.brace_left, bent.brace_right] if b is not None]


# Frame dimensions for reference
BEAM_LENGTH = 5000  # mm

# Create frame and add members
frame = TimberFrame()
frame.add_member("left_post", left_post)
frame.add_member("right_post", right_post)
frame.add_member("beam", beam)
for i, brace in enumerate(braces):
    frame.add_member(f"brace_{i}", brace)

# %%
# Visualize CAD geometry, REFINED mesh geometry, and contact surfaces

Y_CAD = 0         # CAD geometry at origin
Y_MESH = -500     # Mesh geometry offset
Y_CONTACT = 500   # Contact surfaces offset

# 1. CAD geometry (original shapes)
print("Showing CAD geometry...")
show_object(left_post, name="CAD: Left Post", options={"color": "sienna", "alpha": 0.5})
show_object(right_post, name="CAD: Right Post", options={"color": "sienna", "alpha": 0.5})
show_object(beam, name="CAD: Beam", options={"color": "burlywood", "alpha": 0.5})
for i, brace in enumerate(braces):
    show_object(brace, name=f"CAD: Brace {i}", options={"color": "orange", "alpha": 0.5})

# 2. Generate REFINED mesh with contact detection using the utility
print("Generating refined mesh with contact detection...")
with tempfile.TemporaryDirectory() as tmpdir:
    # Export all parts to STEP
    step_files = {}
    for member in frame.members:
        step_path = Path(tmpdir) / f"{member.name}.step"
        export_step(member.shape, str(step_path))
        step_files[member.name] = str(step_path)
    
    # Define contacts (auto-detect from frame)
    contact_defs = []
    for i, (part_a, part_b) in enumerate(frame._find_contacts()):
        contact_defs.append(ContactDefinition(f"contact_{i}", part_a, part_b))
    
    print(f"Contact pairs to mesh: {len(contact_defs)}")
    for cd in contact_defs:
        print(f"  {cd.part_a} <-> {cd.part_b}")
    
    # Mesh with contact refinement (two-pass)
    mesh_config = MeshingConfig(
        element_size=150.0,
        element_size_fine=40.0,
        refinement_margin=20.0,
        contact_gap=0.5,
    )
    
    meshing_result = mesh_parts_with_contact_refinement(
        step_files, contact_defs, mesh_config, verbose=True
    )
    
    # 3. Visualize refined mesh boundaries
    print(f"\nRefined mesh: {meshing_result.total_nodes} nodes, {meshing_result.total_elements} elements")
    
    for part_name, mesh in meshing_result.meshes.items():
        elems = [(i + 1, e) for i, e in enumerate(mesh.elements)]
        boundary_faces = get_boundary_faces(elems)
        mesh_compound = build_mesh_faces_compound(boundary_faces, elems, mesh.nodes)
        mesh_offset = mesh_compound.move(Location((0, Y_MESH, 0)))
        show_object(mesh_offset, name=f"Refined Mesh: {part_name}", options={"color": "lightgray", "alpha": 0.7})
        print(f"  {part_name}: {mesh.num_nodes} nodes, {mesh.num_elements} elements")
    
    # 4. Visualize contact surfaces from the refined mesh
    print(f"\nContact surfaces:")
    for surf_name, faces in meshing_result.contact_surfaces.items():
        if not faces:
            continue
        
        # Build compound from contact faces using combined mesh
        mesh_compound = build_mesh_faces_compound(
            faces, 
            meshing_result.combined.elements, 
            meshing_result.combined.nodes
        )
        
        # Color by surface type (A vs B)
        color = "red" if "_SURF" in surf_name and surf_name.count("_") >= 2 else "blue"
        # Alternate colors for clarity
        if "part_a" in surf_name.lower() or surf_name.endswith("_SURF"):
            parts = surf_name.rsplit("_", 2)
            if len(parts) >= 2:
                color = "red" if parts[-2] != parts[-1].replace("_SURF", "") else "blue"
        
        surface_offset = mesh_compound.move(Location((0, Y_CONTACT, 0)))
        show_object(surface_offset, name=f"Contact: {surf_name}", options={"color": color})
        print(f"  {surf_name}: {len(faces)} faces")

# %%
# Run FEA analysis

# Add 1 tonne load at beam midspan
beam_bbox = beam.bounding_box()
mid_x = (beam_bbox.min.X + beam_bbox.max.X) / 2
top_z = beam_bbox.max.Z

def main_load_filter(nid, x, y, z, part, mesh):
    return (part == "beam" and 
            abs(x - mid_x) < 70.0 and 
            abs(z - top_z) < 35.0)

main_load = LoadBC("main_load", main_load_filter, dof=3, total_load=-9810.0)  # 1 tonne down

# Analyze - self-weight is automatic!
output_dir = Path(__file__).parent / "fea_pipeline_test_output"

print("=" * 60)
print("BENT FRAME FEA ANALYSIS")
print("=" * 60)
print(f"Loads:")
print(f"  - Main load: 1000 kg (1 tonne) at beam midspan")
print(f"  - Self-weight: automatic")
print()

result = frame.analyze(
    additional_loads=[main_load],
    output_dir=output_dir,
)

print("\n" + "=" * 60)
print("ANALYSIS SUMMARY")
print("=" * 60)
print(f"Success: {result.success}")
print(f"Mesh: {result.num_nodes} nodes, {result.num_elements} elements")

if result.success:
    print(f"\nDeflection Results:")
    print(f"  Max total: {result.fea_results.max_displacement:.4f} mm")
    print(f"  Max Z: {result.fea_results.max_uz:.4f} mm")
    
    # Serviceability check
    limit = BEAM_LENGTH / 300  # L/300
    status = "PASS ✓" if abs(result.fea_results.max_uz) < limit else "FAIL ✗"
    print(f"  Limit (L/300): {limit:.2f} mm")
    print(f"  Status: {status}")

print("=" * 60)

# %%
# Visualize FEA results

if result.success:
    show_fea_results(
        mesh_file=str(output_dir / "mesh.inp"),
        frd_file=str(output_dir / "analysis.frd"),
        scale=5.0,
        original_shapes=[
            (left_post, "Left Post", "sienna"),
            (right_post, "Right Post", "sienna"),
            (beam, "Beam", "burlywood"),
        ] + [(brace, f"Brace {i}", "orange") for i, brace in enumerate(braces)],
        deformed_color="red",
        original_alpha=0.3,
    )
