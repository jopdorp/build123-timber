# %%
"""FEA test using high-level frame API."""

from pathlib import Path
from build123d import Location
from ocp_vscode import reset_show, show_object

from timber_joints.alignment import build_complete_bent, BraceParams
from timber_joints.fea import TimberFrame, show_fea_results, LoadBC

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
# Visualize CAD geometry, mesh geometry, and mesh contact surfaces side by side

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

# 2. Mesh geometry (triangulated surfaces)
print("Generating mesh geometry...")
mesh_geometry = frame.get_mesh_geometry(mesh_size=50.0)
print(f"Generated {len(mesh_geometry)} mesh parts")

for name, mesh_compound in mesh_geometry:
    mesh_offset = mesh_compound.move(Location((0, Y_MESH, 0)))
    show_object(mesh_offset, name=f"Mesh: {name}", options={"color": "lightgray", "alpha": 0.7})

# 3. Mesh contact surfaces
print("Extracting contact surfaces...")
contact_surfaces = frame.get_contact_surfaces(mesh_size=50.0)
print(f"Found {len(contact_surfaces)} contact pairs")

for name_a, name_b, surface_a, surface_b in contact_surfaces:
    # Offset surfaces in Y for visibility
    surface_a_offset = surface_a.move(Location((0, Y_CONTACT, 0)))
    surface_b_offset = surface_b.move(Location((0, Y_CONTACT, 0)))
    
    show_object(surface_a_offset, name=f"Contact: {name_a}->{name_b} (A)", options={"color": "red"})
    show_object(surface_b_offset, name=f"Contact: {name_a}->{name_b} (B)", options={"color": "blue"})
    
    # Print surface areas
    area_a = sum(f.area for f in surface_a.faces())
    area_b = sum(f.area for f in surface_b.faces())
    print(f"  {name_a} <-> {name_b}: A={area_a:.0f}mm², B={area_b:.0f}mm²")

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
