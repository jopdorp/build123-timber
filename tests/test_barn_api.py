# %%
"""Test the BarnFrame high-level API.

This demonstrates how the new BarnFrame class simplifies barn creation
compared to the verbose manual approach in test_visual_fea_barn_braced.py
"""

import sys
sys.path.insert(0, "src")

from ocp_vscode import reset_show, show_object
from timber_joints.barn import BarnConfig, BarnFrame

reset_show()


# %%
# Build a barn with the high-level API - just a few lines!

config = BarnConfig(
    post_height=3000,
    post_section=150,
    beam_length=5000,
    bent_spacing=3000,
    num_bents=3,
    brace_section=100,
    brace_distance_from_post=500,
)

barn = BarnFrame.build(config)

# Print summary
print(barn.summary())

# %%
# Visualize - also just one line!
barn.show(show_object)

print("\n✅ Barn displayed - check OCP viewer!")


# %%
# Customization examples

# Simple barn without braces
simple_config = BarnConfig(
    post_height=2500,
    beam_length=4000,
    num_bents=2,
    bent_spacing=2500,
    include_bent_braces=False,
    include_girt_braces=False,
)
simple_barn = BarnFrame.build(simple_config)
print(f"\nSimple barn (no braces): {len(simple_barn.all_parts())} parts")


# Barn without girts (just bents with knee braces)
bents_only_config = BarnConfig(
    post_height=3000,
    beam_length=5000,
    num_bents=3,
    bent_spacing=3000,
    include_girts=False,
    include_girt_braces=False,
)
bents_only = BarnFrame.build(bents_only_config)
print(f"Bents only: {len(bents_only.all_parts())} parts")


# Large barn
large_config = BarnConfig(
    post_height=4000,
    post_section=200,
    beam_length=8000,
    beam_section=200,
    bent_spacing=4000,
    num_bents=5,
    brace_section=150,
    brace_distance_from_post=600,
)
large_barn = BarnFrame.build(large_config)
print(f"Large barn: {len(large_barn.all_parts())} parts")
