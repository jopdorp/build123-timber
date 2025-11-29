# %%
"""FEA test using generic assembly pipeline."""

from pathlib import Path
from ocp_vscode import reset_show

from timber_joints.alignment import build_complete_bent
from timber_joints.analysis import expand_shape_by_margin
from timber_joints.fea import (
    FEAPart,
    ContactPair,
    FixedBC,
    LoadBC,
    AssemblyConfig,
    analyze_assembly,
    show_fea_results,
    POST_VERTICAL_Z,
    BEAM_HORIZONTAL_X,
)

reset_show()

# Build bent frame
left_post, right_post, beam_positioned, _ = build_complete_bent(
    post_height=3000,
    post_section=150,
    beam_length=5000,
    tenon_length=60,
    shoulder_depth=20,
    housing_depth=20,
    post_top_extension=300,
)

# Create contact gap
margin_gap = 0.5
beam_with_gap = expand_shape_by_margin(beam_positioned, -margin_gap)

# Get bounding boxes for boundary conditions
left_bbox = left_post.bounding_box()
right_bbox = right_post.bounding_box()
beam_bbox = beam_with_gap.bounding_box()

# Define parts
parts = [
    FEAPart("left_post", left_post, POST_VERTICAL_Z),
    FEAPart("right_post", right_post, POST_VERTICAL_Z),
    FEAPart("beam", beam_with_gap, BEAM_HORIZONTAL_X),
]

# Define contact pairs (beam tenons into post mortises)
contacts = [
    ContactPair("left_joint", "beam", "left_post"),
    ContactPair("right_joint", "beam", "right_post"),
]

# Define boundary conditions
fixed_bcs = [
    # Left post fixed at bottom
    FixedBC("left_fixed", lambda nid, x, y, z, part, mesh: part == "left_post" and abs(z - left_bbox.min.Z) < 2.0),
    # Right post fixed at bottom
    FixedBC("right_fixed", lambda nid, x, y, z, part, mesh: part == "right_post" and abs(z - right_bbox.min.Z) < 2.0),
]

beam_mid_x = (beam_bbox.min.X + beam_bbox.max.X) / 2
beam_top_z = beam_bbox.max.Z

load_bcs = [
    # Load at beam midspan top surface
    LoadBC(
        "midspan_load",
        lambda nid, x, y, z, part, mesh: part == "beam" and abs(x - beam_mid_x) < 40.0 and abs(z - beam_top_z) < 2.0,
        dof=3,  # Z direction
        total_load=-10000.0,  # 10 kN downward
    ),
]

# Configure analysis
config = AssemblyConfig(
    mesh_size=50.0,
    mesh_size_fine=20.0,
    contact_gap=margin_gap,
    output_dir=Path(__file__).parent / "fea_pipeline_test_output",
)

print("=" * 60)
print("BENT FRAME FEA ANALYSIS (Generic Assembly Pipeline)")
print("=" * 60)

result = analyze_assembly(
    parts=parts,
    contacts=contacts,
    fixed_bcs=fixed_bcs,
    load_bcs=load_bcs,
    config=config,
    verbose=True,
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
    limit = 5000 / 300  # L/300
    status = "PASS ✓" if abs(result.fea_results.max_uz) < limit else "FAIL ✗"
    print(f"  Limit (L/300): {limit:.2f} mm")
    print(f"  Status: {status}")

print("=" * 60)

# %%
# Visualize FEA results with original CAD

if result.success:
    frd_file = str(config.output_dir / "analysis.frd")
    mesh_file = str(config.output_dir / "mesh.inp")
    
    # Show original shapes and deformed mesh using utility
    show_fea_results(
        mesh_file=mesh_file,
        frd_file=frd_file,
        scale=5.0,
        original_shapes=[
            (left_post, "Left Post (original)", "sienna"),
            (right_post, "Right Post (original)", "sienna"),
            (beam_with_gap, "Beam (original)", "burlywood"),
        ],
        deformed_color="red",
        original_alpha=0.3,
    )
