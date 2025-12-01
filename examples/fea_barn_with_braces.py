# %%
"""FEA analysis of a 3-bent barn frame WITH braces.

A barn frame with full bracing consists of:
- 3 bents (each with 2 posts + 1 cross beam) spaced along Y axis
- 2 girts running longitudinally connecting post tops along Y
- Knee braces per bent for lateral stability (bent braces)
- Girt braces for longitudinal bracing
"""

from pathlib import Path
from ocp_vscode import reset_show, show_object

from timber_joints.barn import BarnConfig, BarnFrame
from timber_joints.fea import LoadBC

from fea_utils import visualize_frame_with_mesh, run_fea_analysis, visualize_fea_results

reset_show()

# %%
# Build barn WITH braces
# Bent braces: 30°, longer (1000mm brace length)
# Girt braces: 45°, shorter (707mm brace length, ~500mm horizontal)
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
    girt_section=150,
    # Bent braces: 30°, larger (150mm section, 1000mm length)
    bent_brace_section=150,
    bent_brace_length=1000.0,
    bent_brace_angle=30.0,
    # Girt braces: 45°, smaller (100mm section, ~707mm length)
    girt_brace_section=100,
    girt_brace_length=707.1,  # 500 / cos(45°)
    girt_brace_angle=45.0,
)

barn = BarnFrame.build(config)

# Show geometry summary
print("Visualizing barn frame geometry with braces...")
barn.show(show_object)
print(barn.summary())

# %%
# Visualize CAD, mesh, and contacts
frame = barn.to_fea_frame()

cad_shapes = [(part, name, "sienna" if "post" in name else ("orange" if "brace" in name else "burlywood")) 
              for part, name in barn.all_parts()]

visualize_frame_with_mesh(
    frame,
    cad_shapes,
    offset_axis="X",
    cad_offset=0,
    mesh_offset=6000,
    contact_offset=12000,
)

# %%
# Define loads on girts
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

# %%
# Run FEA analysis
output_dir = Path(__file__).parent / "fea_barn_braced_output"

result = run_fea_analysis(
    frame,
    output_dir,
    title="3-BENT BARN FRAME FEA ANALYSIS (WITH BRACES)",
    additional_loads=additional_loads,
    reference_length=config.beam_length,
)

# %%
# Visualize FEA results
visualize_fea_results(result, output_dir, cad_shapes, scale=60.0)
