# %%
"""FEA test for 3-bent barn frame with girts (no braces).

This test uses the high-level BarnFrame API to create:
- 3 bents (each with 2 posts + 1 cross beam) spaced along Y axis
- 2 girts running longitudinally connecting post tops along Y
- Posts have tenons going UP into girts (girts have mortises)
"""

from pathlib import Path
from ocp_vscode import reset_show, show_object

from timber_joints.barn import BarnConfig, BarnFrame
from timber_joints.fea import show_fea_results, LoadBC

reset_show()

# Build barn without braces
config = BarnConfig(
    post_height=3000,
    post_section=150,
    beam_length=5000,
    beam_section=150,
    bent_spacing=3000,
    num_bents=3,
    tenon_length=60,
    shoulder_depth=20,
    housing_depth=20,
    post_top_extension=300,
    include_bent_braces=False,
    include_girt_braces=False,
)

barn = BarnFrame.build(config)

# Show the geometry
print("Visualizing barn frame geometry...")
barn.show(show_object)
print(barn.summary())


# %%
# FEA Analysis
frame = barn.to_fea_frame()
output_dir = Path(__file__).parent / "fea_barn_frame_output"

print("=" * 60)
print("3-BENT BARN FRAME FEA ANALYSIS")
print("=" * 60)
print(barn.summary())
print()

# Define additional loads on girts
right_girt_bbox = barn.right_girt.bounding_box()
right_girt_y_quarter = right_girt_bbox.min.Y + (right_girt_bbox.max.Y - right_girt_bbox.min.Y) * 0.25
right_girt_top_z = right_girt_bbox.max.Z

def right_girt_load_filter(nid, x, y, z, part, mesh):
    return (part == "right_girt" and 
            abs(y - right_girt_y_quarter) < 70.0 and 
            abs(z - right_girt_top_z) < 35.0)

left_girt_bbox = barn.left_girt.bounding_box()
left_girt_y_threequarter = left_girt_bbox.min.Y + (left_girt_bbox.max.Y - left_girt_bbox.min.Y) * 0.75
left_girt_right_x = left_girt_bbox.max.X

def left_girt_load_filter(nid, x, y, z, part, mesh):
    return (part == "left_girt" and 
            abs(y - left_girt_y_threequarter) < 70.0 and 
            abs(x - left_girt_right_x) < 35.0)

additional_loads = [
    LoadBC("right_girt_load", right_girt_load_filter, dof=3, total_load=-1000.0),  # 100 kg down
    LoadBC("left_girt_load", left_girt_load_filter, dof=1, total_load=500.0),      # 50kg sideways +X
]

print(f"Additional loads:")
print(f"  - Right girt at Y={right_girt_y_quarter:.1f}mm: 100 kg downward")
print(f"  - Left girt at Y={left_girt_y_threequarter:.1f}mm: 50 kg sideways (+X)")
print(f"  - Self-weight: automatic")
print()

result = frame.analyze(
    additional_loads=additional_loads,
    output_dir=output_dir,
    mesh_size=70.0,
    mesh_size_fine=30.0,
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
    
    limit = config.beam_length / 300  # L/300
    status = "PASS ✓" if abs(result.fea_results.max_uz) < limit else "FAIL ✗"
    print(f"  Limit (L/300): {limit:.2f} mm")
    print(f"  Status: {status}")

print("=" * 60)


# %%
# Visualize FEA results
if result.success:
    # Build original shapes list for visualization
    original_shapes = [(part, name, "sienna" if "post" in name else "burlywood") 
                       for part, name in barn.all_parts()]
    
    show_fea_results(
        mesh_file=str(output_dir / "mesh.inp"),
        frd_file=str(output_dir / "analysis.frd"),
        scale=60.0,
        original_shapes=original_shapes,
        deformed_color="red",
        original_alpha=0.3,
    )
