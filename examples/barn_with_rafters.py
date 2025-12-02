# %%
"""Barn frame with braces and rafters - CAD visualization only.

A complete barn frame with:
- 3 bents (each with 2 posts + 1 cross beam) spaced along Y axis
- 2 girts running longitudinally connecting post tops along Y
- Knee braces per bent for lateral stability (bent braces)
- Girt braces for longitudinal bracing
- Rafters with tongue-and-fork joint at peak and lap joint at girts
"""

from ocp_vscode import reset_show, show_object

from timber_joints.barn import BarnConfig, BarnFrame

reset_show()

# %%
# Build barn with braces and rafters
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
    # Bent braces: 30°, larger section
    bent_brace_section=150,
    bent_brace_length=1000.0,
    bent_brace_angle=30.0,
    # Girt braces: 45°, smaller section
    girt_brace_section=100,
    girt_brace_length=707.1,
    girt_brace_angle=45.0,
    # Rafters: 30° pitch
    include_rafters=True,
    rafter_section=100,
    rafter_pitch=30,
    rafter_overhang=200,
    num_rafters=7
)

barn = BarnFrame.build(config)

# %%
# Show geometry
print("Barn frame with braces and rafters:")
print(barn.summary())

barn.show(show_object)

# %%
