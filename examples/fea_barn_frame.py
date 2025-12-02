# %%
"""FEA analysis of a 3-bent barn frame WITHOUT braces but WITH rafters.

A barn frame consists of:
- 3 bents (each with 2 posts + 1 cross beam) spaced along Y axis
- 2 girts running longitudinally connecting post tops along Y
- Rafters with tongue-and-fork joint at peak and lap joint at girts
"""

from pathlib import Path
from ocp_vscode import reset_show, show_object

from timber_joints.barn import BarnConfig, BarnFrame
from timber_joints.fea import LoadBC, export_fea_combined_gltf

from fea_utils import visualize_frame_with_mesh, run_fea_analysis

reset_show()

# %%
# Build barn WITHOUT braces but WITH rafters
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
    include_rafters=True,
    rafter_section=100,
    rafter_pitch=30,
    rafter_overhang=300,
)

barn = BarnFrame.build(config)

# Show geometry summary
print("Visualizing barn frame geometry (no braces, with rafters)...")
barn.show(show_object)
print(barn.summary())

# %%
# Visualize CAD, mesh, and contacts
frame = barn.to_fea_frame()

cad_shapes = [(part, name, "sienna" if "post" in name else "burlywood") 
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
    LoadBC("right_girt_load", right_girt_load_filter, dof=3, total_load=-2000.0),  # 200 kg down
    LoadBC("left_girt_load", left_girt_load_filter, dof=1, total_load=800.0),      # 80kg sideways +X
]

print(f"Additional loads:")
print(f"  - Right girt at Y={right_girt_y_quarter:.1f}mm: 200 kg downward")
print(f"  - Left girt at Y={left_girt_y_threequarter:.1f}mm: 80 kg sideways (+X)")
print(f"  - Self-weight: automatic")
print()

# %%
# Run FEA analysis
output_dir = Path(__file__).parent / "fea_barn_frame_output"

result = run_fea_analysis(
    frame,
    output_dir,
    title="3-BENT BARN FRAME FEA ANALYSIS (NO BRACES, WITH RAFTERS)",
    additional_loads=additional_loads,
    reference_length=config.beam_length,
)

# %%
# Export FEA results to GLTF with limit-based colormap
# - Displacement limit: beam_length/300 (L/300)
# - Stress limit: 24 MPa (C24 f_m_k)
if result.success:
    export_fea_combined_gltf(
        output_dir=output_dir,
        scale=4.0,
        reference_length=config.beam_length,
        stress_limit=24.0,  # C24 f_m_k
    )
