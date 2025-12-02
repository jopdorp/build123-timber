# %%
"""FEA analysis of just a rafter pair.

Minimal test case for contact convergence:
- 2 rafters meeting at peak with tongue-and-fork joint
- Fixed at the bottom (where they would sit on girts)
- Load at the peak
"""

from pathlib import Path
from build123d import Box, Location, Align
from ocp_vscode import reset_show, show_object

from timber_joints.alignment import (
    RafterParams,
    build_rafter_pair,
)
from timber_joints.fea import (
    TimberFrame, 
    LoadBC,
)
from timber_joints.fea.frame import MemberType

from fea_utils import (
    visualize_frame_with_mesh, 
    run_fea_analysis,
    print_load_summary,
    export_results_gltf,
)

reset_show()

# %%
# Create dummy girts just for the rafter building function
# These won't be in the FEA model
girt_section = 150
building_width = 4000  # 4m span

left_girt = Box(
    girt_section,
    500,  # short stub
    girt_section,
    align=(Align.CENTER, Align.CENTER, Align.MIN),
).move(Location((-building_width/2 + girt_section/2, 0, 0)))

right_girt = Box(
    girt_section,
    500,
    girt_section,
    align=(Align.CENTER, Align.CENTER, Align.MIN),
).move(Location((building_width/2 - girt_section/2, 0, 0)))

# %%
# Build rafter pair
rafter_params = RafterParams(
    section=100,
    pitch_angle=30,
    overhang=200,
)

rafter_result = build_rafter_pair(
    left_girt=left_girt,
    right_girt=right_girt,
    y_position=0,
    rafter_params=rafter_params,
)

left_rafter = rafter_result.left_rafter
right_rafter = rafter_result.right_rafter

# %%
# Visualize rafters only
show_object(left_rafter, name="left_rafter", options={"color": "peru", "alpha": 0.5})
show_object(right_rafter, name="right_rafter", options={"color": "sienna", "alpha": 0.5})

# %%
# Get rafter bounds for BC placement
left_bbox = left_rafter.bounding_box()
right_bbox = right_rafter.bounding_box()

# Bottom of rafters (where they would sit on girts) - fix these
rafter_bottom_z = min(left_bbox.min.Z, right_bbox.min.Z)

# Peak of rafters (for load)
peak_z = max(left_bbox.max.Z, right_bbox.max.Z)

print(f"Rafter bottom Z: {rafter_bottom_z:.1f}")
print(f"Rafter peak Z: {peak_z:.1f}")

# %%
# Create FEA frame with just the rafters
# Use POST type so they get fixed at their lowest Z point
frame = TimberFrame()
frame.add_member("left_rafter", left_rafter, MemberType.POST)
frame.add_member("right_rafter", right_rafter, MemberType.POST)

# %%
# Visualize CAD, mesh, and contacts
cad_shapes = [
    (left_rafter, "Left Rafter", "peru"),
    (right_rafter, "Right Rafter", "sienna"),
]

visualize_frame_with_mesh(
    frame, 
    cad_shapes,
    offset_axis="Y",
    cad_offset=0,
    mesh_offset=-500,
    contact_offset=500,
    element_size=40.0,
    element_size_fine=15.0,
)

# %%
# Run FEA with load at peak
def peak_load_filter(nid, x, y, z, part, mesh):
    """Load at top of rafters near the peak."""
    return abs(z - peak_z) < 20.0 and abs(x) < 60.0

peak_load = LoadBC("peak_load", peak_load_filter, dof=3, total_load=-5000.0)  # 500kg down

output_dir = Path(__file__).parent / "fea_rafter_only_output"

print_load_summary([
    {"name": "Peak load", "magnitude_kg": 500, "direction": "down", "location": "rafter peak"},
])

result = run_fea_analysis(
    frame,
    output_dir,
    title="RAFTER PAIR FEA ANALYSIS",
    additional_loads=[peak_load],
    reference_length=building_width,
)

# Export FEA results to GLTF
if result.success:
    export_results_gltf(result, output_dir, reference_length=building_width, scale=1.0)

# %%
