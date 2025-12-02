# %%
"""FEA analysis of a bent frame with braces, girts, and rafters.

A minimal barn structure for FEA:
- 2 bents (close together to keep model small)
- Each bent: 2 posts + 1 beam + 2 knee braces
- 2 girts connecting the bents (with proper tenon joints)
- Rafters with lap joints into girts
"""

from pathlib import Path
from build123d import Location
from ocp_vscode import reset_show, show_object

from timber_joints.alignment import (
    JointParams, 
    build_complete_bent, 
    BraceParams,
    RafterParams,
    add_girts_to_bents,
    add_rafters_to_barn,
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
# Build two bents (close together for a compact FEA model)
joint_params = JointParams(
    tenon_length=60,
    shoulder_depth=20,
    housing_depth=20,
)

brace_params = BraceParams(
    length=1200,
    section=100,
    tenon_length=60,
    angle=45,
)

bent1 = build_complete_bent(
    post_height=3000,
    post_section=150,
    beam_length=5000,
    joint_params=joint_params,
    brace_params=brace_params,
)


# %%
# Add girts connecting the two bents (this adds tenons to posts and cuts mortises in girts)
y_positions = [0]  # Two bents 500mm apart

girt_result = add_girts_to_bents(
    bents=[bent1],
    y_positions=y_positions,
    girt_section=150,
    joint_params=joint_params,
    brace_params=None,  # No girt braces for this example
)

# Get updated bents with tenons cut
updated_bents = girt_result.updated_bents

# %%
# Add rafters with proper lap joints into girts
rafter_params = RafterParams(
    section=100,
    pitch_angle=30,
    overhang=300,
)

rafter_result = add_rafters_to_barn(
    left_girt=girt_result.left_girt,
    right_girt=girt_result.right_girt,
    y_positions=[y + (girt_result.left_girt.bounding_box().size.Y - rafter_params.section) / 2 for y in y_positions],  # One rafter pair per bent
    rafter_params=rafter_params,
)

# Use the girts with lap cuts from rafter result
left_girt = rafter_result.updated_left_girt
right_girt = rafter_result.updated_right_girt

# %%
# Collect all parts for visualization and FEA
parts = []

# Bent 1 parts (at y=0)
bent1_result = updated_bents[0]
parts.append((bent1_result.left_post.move(Location((0, y_positions[0], 0))), "bent1_left_post", "sienna"))
parts.append((bent1_result.right_post.move(Location((0, y_positions[0], 0))), "bent1_right_post", "sienna"))
parts.append((bent1_result.beam.move(Location((0, y_positions[0], 0))), "bent1_beam", "burlywood"))
if bent1_result.brace_left:
    parts.append((bent1_result.brace_left.move(Location((0, y_positions[0], 0))), "bent1_brace_left", "orange"))
if bent1_result.brace_right:
    parts.append((bent1_result.brace_right.move(Location((0, y_positions[0], 0))), "bent1_brace_right", "orange"))

# Girts
parts.append((left_girt, "left_girt", "burlywood"))
parts.append((right_girt, "right_girt", "burlywood"))

# Rafters
for i, rafter_pair in enumerate(rafter_result.rafter_pairs):
    parts.append((rafter_pair.left_rafter, f"rafter_{i+1}_left", "peru"))
    parts.append((rafter_pair.right_rafter, f"rafter_{i+1}_right", "peru"))

# %%
# Visualize all parts
for shape, name, color in parts:
    show_object(shape, name=name, options={"color": color, "alpha": 0.5})

# %%
# Create FEA frame
frame = TimberFrame()

for shape, name, color in parts:
    if "post" in name:
        frame.add_member(name, shape, MemberType.POST)
    elif "brace" in name:
        frame.add_member(name, shape, MemberType.BRACE)
    else:
        frame.add_member(name, shape, MemberType.BEAM)

# %%
# Visualize CAD, mesh, and contacts
cad_shapes = [(shape, name, color) for shape, name, color in parts]

visualize_frame_with_mesh(
    frame, 
    cad_shapes,
    offset_axis="Y",
    cad_offset=0,
    mesh_offset=-1000,
    contact_offset=1000,
    element_size=80.0,
    element_size_fine=25.0,
)

# %%
# Run FEA analysis with load at rafter peaks
# Find the peak Z of rafters
peak_z = max(
    rafter_result.rafter_pairs[0].left_rafter.bounding_box().max.Z,
    rafter_result.rafter_pairs[0].right_rafter.bounding_box().max.Z,
)

def peak_load_filter(nid, x, y, z, part, mesh):
    # Load at rafter peaks - top of rafters near centerline
    return ("rafter" in part and 
            abs(z - peak_z) < 30.0 and
            abs(x) < 100.0)  # Near centerline

peak_load = LoadBC("peak_load", peak_load_filter, dof=3, total_load=-1000.0)  # 100kg down

output_dir = Path(__file__).parent / "fea_bent_with_rafters_output"

print_load_summary([
    {"name": "Peak load", "magnitude_kg": 100, "direction": "down", "location": "rafter peaks"},
])

result = run_fea_analysis(
    frame,
    output_dir,
    title="BENT WITH GIRTS AND RAFTERS FEA ANALYSIS",
    additional_loads=[],
    reference_length=5000.0  # beam span
)

# Export FEA results to GLTF
export_results_gltf(result, output_dir, reference_length=5000.0, scale=1.0)

# %%
