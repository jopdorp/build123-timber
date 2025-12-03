# %%
"""Demo showing wooden pegs in timber joints.

Pegs (wooden pins) secure joints:
- Tenon joints: pegged from the SIDE (through post into tenon)
- Lap joints: pegged from the TOP (through rafter into girt)

Pegs are:
- Full section length (goes through entire receiving member)
- 15mm diameter (1.5cm) hardwood
- Glued to both elements (tied constraint in FEA, not contact)
"""

from ocp_vscode import reset_show, show_object

from timber_joints.alignment import (
    JointParams, RafterParams,
    build_complete_bent, add_girts_to_bents, add_rafters_to_barn
)

reset_show()

# %%
# Build bent with pegs enabled
joint_params = JointParams(
    tenon_length=60,
    shoulder_depth=20,
    housing_depth=20,
    include_pegs=True,      # Enable pegs!
    peg_diameter=15.0,      # 1.5cm diameter
    peg_offset=30.0,        # 30mm from shoulder into tenon
)

bent = build_complete_bent(
    post_height=3000,
    post_section=150,
    beam_length=5000,
    joint_params=joint_params,
)

print(f"Bent created with {len(bent.pegs)} pegs for beam-to-post joints")

# Show bent parts
show_object(bent.left_post, name="left_post", options={"color": "sienna", "alpha": 0.7})
show_object(bent.right_post, name="right_post", options={"color": "sienna", "alpha": 0.7})
show_object(bent.beam, name="beam", options={"color": "burlywood", "alpha": 0.7})

# Show pegs (hardwood - darker color)
for i, peg in enumerate(bent.pegs):
    show_object(peg, name=f"tenon_peg_{i+1}", options={"color": "saddlebrown"})

# %%
# Add girts connecting bents
girt_result = add_girts_to_bents(
    bents=[bent],
    y_positions=[0],
    girt_section=150,
    joint_params=joint_params,
)

# %%
# Add rafters with pegs at lap joints
rafter_params = RafterParams(
    section=100,
    pitch_angle=30,
    overhang=200,
    include_pegs=True,      # Enable pegs for lap joints!
    peg_diameter=15.0,
)

rafter_result = add_rafters_to_barn(
    left_girt=girt_result.left_girt,
    right_girt=girt_result.right_girt,
    y_positions=[0],
    rafter_params=rafter_params,
)

print(f"Rafters created with {len(rafter_result.pegs)} pegs for lap joints")

# Show girts
show_object(rafter_result.updated_left_girt, name="left_girt", options={"color": "burlywood", "alpha": 0.7})
show_object(rafter_result.updated_right_girt, name="right_girt", options={"color": "burlywood", "alpha": 0.7})

# Show rafters
for i, pair in enumerate(rafter_result.rafter_pairs):
    show_object(pair.left_rafter, name=f"left_rafter_{i+1}", options={"color": "peru", "alpha": 0.7})
    show_object(pair.right_rafter, name=f"right_rafter_{i+1}", options={"color": "peru", "alpha": 0.7})

# Show lap joint pegs (from top)
for i, peg in enumerate(rafter_result.pegs):
    show_object(peg, name=f"lap_peg_{i+1}", options={"color": "saddlebrown"})

# %%
print("\nPeg Summary:")
print("=" * 50)
print(f"Tenon joint pegs (beam-to-post): {len(bent.pegs)}")
print(f"  - Direction: through Y (side of post)")
print(f"  - Length: {joint_params.peg_diameter}mm post width")
print(f"  - Position: {joint_params.peg_offset}mm from shoulder")
print()
print(f"Lap joint pegs (rafter-to-girt): {len(rafter_result.pegs)}")
print(f"  - Direction: through Z (top of girt)")
print(f"  - Length: full girt height")
print(f"  - Position: center of lap overlap")
print()
print("Peg material: Hardwood (glued to both elements)")
print("=" * 50)

# %%
