# %%
"""FEA test using high-level frame API."""

from pathlib import Path
from ocp_vscode import reset_show

from timber_joints.alignment import build_complete_bent
from timber_joints.fea import TimberFrame, show_fea_results

reset_show()

# Build bent frame
left_post, right_post, beam, _ = build_complete_bent(
    post_height=3000,
    post_section=150,
    beam_length=5000,
    tenon_length=60,
    shoulder_depth=20,
    housing_depth=20,
    post_top_extension=300,
)

# Create frame and add members
frame = TimberFrame()
frame.add_member("left_post", left_post)
frame.add_member("right_post", right_post)
frame.add_member("beam", beam)

# Analyze - that's it!
output_dir = Path(__file__).parent / "fea_pipeline_test_output"

print("=" * 60)
print("BENT FRAME FEA ANALYSIS")
print("=" * 60)

result = frame.analyze(
    load=-10000.0,  # 10 kN downward
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
    limit = 5000 / 300  # L/300
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
        ],
        deformed_color="red",
        original_alpha=0.3,
    )
