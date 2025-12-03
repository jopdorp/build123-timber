# %%
"""Single bent with braces, girts, rafters, and pegs.

Demonstrates a complete single bent (portal frame) with:
- 2 posts + 1 cross beam + 2 girts
- Knee braces for lateral stability
- A pair of rafters with tongue-and-fork joint at peak and lap joints into girts
- Wooden pegs at all tenon joints
"""

from build123d import Compound, Location
from ocp_vscode import reset_show, show_object

from timber_joints.alignment import (
    build_complete_bent,
    JointParams,
    BraceParams,
    RafterParams,
    add_girts_to_bents,
    add_rafters_to_barn,
)

reset_show()

# %%
# Configuration
POST_HEIGHT = 3000
POST_SECTION = 150
BEAM_LENGTH = 5000
BEAM_SECTION = 150
GIRT_SECTION = 150

# Joint parameters with pegs enabled
joint_params = JointParams(
    tenon_length=60,
    shoulder_depth=20,
    housing_depth=20,
    post_top_extension=300,
    include_pegs=True,
    peg_diameter=15,
    peg_offset=30,
)

# Brace parameters with pegs
brace_params = BraceParams(
    section=100,
    length=707,
    angle=60,
    tenon_length=60,
    include_pegs=True,
    peg_diameter=15,
    peg_offset=30,
)

# Rafter parameters with pegs
rafter_params = RafterParams(
    section=100,
    pitch_angle=30,
    overhang=200,
    include_pegs=True,
    peg_diameter=15,
)

# %%
# Build the bent
bent = build_complete_bent(
    post_height=POST_HEIGHT,
    post_section=POST_SECTION,
    beam_length=BEAM_LENGTH,
    beam_section=BEAM_SECTION,
    joint_params=joint_params,
    brace_params=brace_params,
)

print(f"Bent created with {len(bent.pegs)} pegs")

# %%
# Add girts to the bent (single bent means girts are short, just post_section length)
y_positions = [0]

girt_result = add_girts_to_bents(
    bents=[bent],
    y_positions=y_positions,
    girt_section=GIRT_SECTION,
    joint_params=joint_params,
    brace_params=None,  # No girt braces for single bent
)

# Get updated bent with tenons cut and girts
updated_bent = girt_result.updated_bents[0]

# %%
# Add rafters with proper lap joints into girts
rafter_result = add_rafters_to_barn(
    left_girt=girt_result.left_girt,
    right_girt=girt_result.right_girt,
    y_positions=[y + (girt_result.left_girt.bounding_box().size.Y - rafter_params.section) / 2 for y in y_positions],
    rafter_params=rafter_params,
)

# Use the girts with lap cuts from rafter result
left_girt = rafter_result.updated_left_girt
right_girt = rafter_result.updated_right_girt
rafter_pair = rafter_result.rafter_pairs[0]

print(f"Rafter pair created with {len(rafter_pair.pegs)} pegs")

# %%
# Collect all pegs
all_pegs = bent.pegs + rafter_pair.pegs
print(f"Total pegs: {len(all_pegs)}")

# %%
# Show everything
# Posts (moved to Y position)
show_object(updated_bent.left_post.move(Location((0, y_positions[0], 0))), name="left_post", options={"color": "sienna", "alpha": 0.3})
show_object(updated_bent.right_post.move(Location((0, y_positions[0], 0))), name="right_post", options={"color": "sienna", "alpha": 0.3})

# Beam
show_object(updated_bent.beam.move(Location((0, y_positions[0], 0))), name="beam", options={"color": "burlywood", "alpha": 0.3})

# Braces
if updated_bent.brace_left:
    show_object(updated_bent.brace_left.move(Location((0, y_positions[0], 0))), name="brace_left", options={"color": "orange"})
if updated_bent.brace_right:
    show_object(updated_bent.brace_right.move(Location((0, y_positions[0], 0))), name="brace_right", options={"color": "orange"})

# Girts
show_object(left_girt, name="left_girt", options={"color": "burlywood", "alpha": 0.3})
show_object(right_girt, name="right_girt", options={"color": "burlywood", "alpha": 0.3})

# Rafters
show_object(rafter_pair.left_rafter, name="left_rafter", options={"color": "peru", "alpha": 0.3})
show_object(rafter_pair.right_rafter, name="right_rafter", options={"color": "peru", "alpha": 0.3})

# Pegs as a single compound with reduced detail
if all_pegs:
    show_object(Compound(all_pegs), name="pegs", options={
        "color": "saddlebrown",
        "angular_tolerance": 30,
        "deviation": 5,
    })

print(f"""
Single Bent Summary
===================
Posts: 2 ({POST_SECTION}mm section, {POST_HEIGHT}mm height)
Beam: 1 ({BEAM_SECTION}mm section, {BEAM_LENGTH}mm span)
Girts: 2 ({GIRT_SECTION}mm section, running along Y)
Braces: 2 ({brace_params.section}mm section, {brace_params.angle}° angle)
Rafters: 2 ({rafter_params.section}mm section, {rafter_params.pitch_angle}° pitch)
Pegs: {len(all_pegs)} total
  - Beam-to-post tenons: 2
  - Brace-to-post tenons: 2
  - Brace-to-beam tenons: 2
  - Rafter lap joints: 2
  - Rafter peak joint: 1
""")

# %%
