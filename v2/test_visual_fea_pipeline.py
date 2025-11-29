# %%
"""Simplified FEA test using refactored pipeline."""

from pathlib import Path
from ocp_vscode import show_object, reset_show

from timber_joints.alignment import build_complete_bent
from timber_joints.analysis import expand_shape_by_margin
from timber_joints.fea import (
    BentFrameConfig,
    analyze_bent_frame,
    show_fea_results,
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

# Configure and run analysis
config = BentFrameConfig(
    mesh_size=50.0,
    mesh_size_fine=20.0,
    contact_gap=margin_gap,
    load_magnitude=10000.0,  # 10 kN
    output_dir=Path(__file__).parent / "fea_pipeline_test_output",
)

print("=" * 60)
print("BENT FRAME FEA ANALYSIS (Refactored Pipeline)")
print("=" * 60)

result = analyze_bent_frame(
    left_post=left_post,
    right_post=right_post,
    beam=beam_with_gap,
    config=config,
    verbose=True,
)

print("\n" + "=" * 60)
print("ANALYSIS SUMMARY")
print("=" * 60)
print(f"Success: {result.success}")
print(f"Mesh: {result.num_nodes} nodes, {result.num_elements} elements")
print(f"Contact faces: {result.left_contact_faces} left, {result.right_contact_faces} right")

if result.success:
    print(f"\nDeflection Results:")
    print(f"  Max total: {result.max_deflection:.4f} mm")
    print(f"  Max Z: {result.max_uz:.4f} mm")
    
    # Serviceability check
    limit = 5000 / 300  # L/300
    status = "PASS ✓" if abs(result.max_uz) < limit else "FAIL ✗"
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
