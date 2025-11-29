# %%
# 1. Beam on Post - alignment only (no joint cuts)
# Beam sits horizontally on top of vertical post

from ocp_vscode import show_object
from timber_joints.beam import Beam
from timber_joints.alignment import align_beam_on_post, make_post_vertical

post = Beam(length=400, width=100, height=100)
beam = Beam(length=600, width=100, height=80)

# Make post vertical
vertical_post = make_post_vertical(post.shape)

# Align beam on top of post
positioned_beam, beam_loc = align_beam_on_post(
    beam_shape=beam.shape,
    beam_length=beam.length,
    beam_width=beam.width,
    beam_height=beam.height,
    post_shape=vertical_post,
    post_length=post.length,
    post_width=post.width,
    post_height=post.height,
)

post_bbox = vertical_post.bounding_box()
beam_bbox = positioned_beam.bounding_box()

print("=== 1. Beam on Post (alignment) ===")
print(f"Post bbox: Z={post_bbox.min.Z:.0f}-{post_bbox.max.Z:.0f}")
print(f"Beam bbox: Z={beam_bbox.min.Z:.0f}-{beam_bbox.max.Z:.0f}")
print(f"Beam bottom ({beam_bbox.min.Z:.0f}) == Post top ({post_bbox.max.Z:.0f}): {abs(beam_bbox.min.Z - post_bbox.max.Z) < 1}")

show_object(vertical_post, name="Post", options={"color": "sienna"})
show_object(positioned_beam, name="Beam on Post", options={"color": "burlywood"})

# %%
# 2. Beam in Post with Tongue-and-Fork joint
# Beam drops INTO post, the entire beam cross-section cuts through the post

from ocp_vscode import show_object
from build123d import Location, Box, Align
from timber_joints.beam import Beam
from timber_joints.tenon import Tenon
from timber_joints.alignment import align_beam_in_post, make_post_vertical, create_receiving_cut

post = Beam(length=400, width=100, height=100)
beam = Beam(length=600, width=100, height=80)

# Create tenon on beam (the "tongue") - goes all the way through the post
tongue_width = beam.width / 3
tenon_length = post.height  # Full depth through the post
beam_with_tenon = Tenon(
    beam=beam,
    tenon_width=tongue_width,
    tenon_height=beam.height,  # Full height
    tenon_length=tenon_length,
    at_start=True  # At start of beam
)

# Make post vertical
vertical_post = make_post_vertical(post.shape)

# Align beam dropped into post
drop_depth = beam.height
positioned_beam, beam_loc = align_beam_in_post(
    beam_shape=beam_with_tenon.shape,
    beam_length=beam.length,
    beam_width=beam.width,
    beam_height=beam.height,
    post_shape=vertical_post,
    post_length=post.length,
    post_width=post.width,
    post_height=post.height,
    drop_depth=drop_depth,
)

# Create the fork by subtracting the beam shape from the post using create_receiving_cut
post_with_fork = create_receiving_cut(
    positioned_insert=positioned_beam,
    receiving_shape=vertical_post,
)

post_bbox = post_with_fork.bounding_box()
beam_bbox = positioned_beam.bounding_box()

print("=== 2. Beam in Post with Tongue-and-Fork ===")
print(f"Post top: Z={post_bbox.max.Z:.0f}")
print(f"Beam bottom: Z={beam_bbox.min.Z:.0f}")
print(f"Drop depth: {drop_depth}mm")
print(f"Tongue width: {tongue_width:.1f}mm")
print(f"Tenon length: {tenon_length}mm (through post)")

show_object(post_with_fork.move(Location((0, 300, 0))), name="Post with Fork", options={"color": "sienna"})
show_object(positioned_beam.move(Location((0, 300, 0))), name="Beam with Tongue", options={"color": "burlywood"})

# %%
# 3. Housed Tongue-and-Fork - beam drops into post but tenon doesn't go all the way through
# Similar to #2 but with shorter tenon that stays inside the post

from ocp_vscode import show_object
from build123d import Location, Box, Align
from timber_joints.beam import Beam
from timber_joints.tenon import Tenon
from timber_joints.alignment import align_beam_in_post, make_post_vertical, create_receiving_cut

post = Beam(length=400, width=100, height=100)
beam = Beam(length=600, width=100, height=80)

# Create tenon on beam (the "tongue") - doesn't go all the way through
tongue_width = beam.width / 3
tenon_length = 80  # Only 80mm into the post, not through it

beam_with_tenon = Tenon(
    beam=beam,
    tenon_width=tongue_width,
    tenon_height=beam.height,  # Full height for tongue-fork
    tenon_length=tenon_length,
    at_start=True
)

# Make post vertical
vertical_post = make_post_vertical(post.shape)

# Align beam dropped into post
drop_depth = beam.height
positioned_beam, beam_loc = align_beam_in_post(
    beam_shape=beam_with_tenon.shape,
    beam_length=beam.length,
    beam_width=beam.width,
    beam_height=beam.height,
    post_shape=vertical_post,
    post_length=post.length,
    post_width=post.width,
    post_height=post.height,
    drop_depth=drop_depth,
)

# Create the housed fork using create_receiving_cut
post_with_fork = create_receiving_cut(
    positioned_insert=positioned_beam,
    receiving_shape=vertical_post,
)

print("=== 3. Housed Tongue-and-Fork ===")
print(f"Tenon: {tenon_length}L × {tongue_width:.1f}W × {beam.height}H")
print(f"Drop depth: {drop_depth}mm")
print(f"Tenon length: {tenon_length}mm (housed, not through)")

show_object(post_with_fork.move(Location((0, 600, 0))), name="Post with Housed Fork", options={"color": "sienna"})
show_object(positioned_beam.move(Location((0, 600, 0))), name="Beam with Tongue", options={"color": "burlywood"})

# %%
# 4. Housed Blind Mortise-and-Tenon - beam smaller than post
# Classic mortise-tenon where tenon goes into a blind hole (not through)
# Beam sits on top of post, tenon projects down into mortise

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.tenon import Tenon
from timber_joints.alignment import align_beam_in_post, make_post_vertical, create_receiving_cut

# Post is larger than beam
post = Beam(length=400, width=150, height=150)
beam = Beam(length=600, width=80, height=120)

# Create tenon on beam - classic 1/3 width, 2/3 height proportions
tenon_width = beam.width / 3
tenon_height = beam.height * 2 / 3
tenon_length = 60  # Blind tenon, not through

beam_with_tenon = Tenon(
    beam=beam,
    tenon_width=tenon_width,
    tenon_height=tenon_height,
    tenon_length=tenon_length,
    at_start=True
)

# Make post vertical
vertical_post = make_post_vertical(post.shape)

# First align beam in the final assembled position
drop_depth = beam.height  # Beam drops by its height
positioned_beam, _ = align_beam_in_post(
    beam_shape=beam_with_tenon.shape,
    beam_length=beam.length,
    beam_width=beam.width,
    beam_height=beam.height,
    post_shape=vertical_post,
    post_length=post.length,
    post_width=post.width,
    post_height=post.height,
    drop_depth=drop_depth,
)

post_top_extension = 40  # How much the mortise extends above the beam (housing on top)
housing_depth = 20  # How far from the far edge of post the mortise should stop
# Mortise should go (post.height - housing_depth) deep
# Tenon is tenon_length, so we move by the difference
blind_offset = post.height - housing_depth - tenon_length
beam_for_cut = positioned_beam.move(Location((blind_offset, 0, -post_top_extension)))

# Create mortise in post by subtracting the offset beam
post_with_mortise = create_receiving_cut(
    positioned_insert=beam_for_cut,
    receiving_shape=vertical_post,
)
print("=== 4. Housed Blind Mortise-and-Tenon ===")
print(f"Post: {post.width}W × {post.height}H (larger than beam)")
print(f"Beam: {beam.width}W × {beam.height}H")
print(f"Tenon: {tenon_length}L × {tenon_width:.1f}W × {tenon_height:.1f}H")
print(f"Drop depth: {drop_depth}mm")
print(f"Housing depth: {housing_depth}mm (extra pocket around tenon)")
print(f"Blind offset: {blind_offset}mm (calculated: post.height - tenon_length + housing_depth)")

show_object(post_with_mortise, name="Post with Mortise", options={"color": "sienna", "alpha": 0.7})
show_object(positioned_beam, name="Beam with Tenon", options={"color": "burlywood"})

# %%
# 5. Blind Shouldered Mortise-and-Tenon - with angled shoulder
# Same as #4 but using shouldered tenon for better bearing surface

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.shouldered_tenon import ShoulderedTenon
from timber_joints.alignment import align_beam_in_post, make_post_vertical, create_receiving_cut

# Post is larger than beam
post = Beam(length=400, width=150, height=150)
beam = Beam(length=600, width=80, height=120)

# Create shouldered tenon on beam
tenon_width = beam.width / 3
tenon_height = beam.height * 2 / 3
tenon_length = 60
shoulder_depth = 20  # Angled shoulder

beam_with_tenon = ShoulderedTenon(
    beam=beam,
    tenon_width=tenon_width,
    tenon_height=tenon_height,
    tenon_length=tenon_length,
    shoulder_depth=shoulder_depth,
    at_start=True
)

# Make post vertical
vertical_post = make_post_vertical(post.shape)

# First align beam in the final assembled position
drop_depth = beam.height
positioned_beam, _ = align_beam_in_post(
    beam_shape=beam_with_tenon.shape,
    beam_length=beam.length,
    beam_width=beam.width,
    beam_height=beam.height,
    post_shape=vertical_post,
    post_length=post.length,
    post_width=post.width,
    post_height=post.height,
    drop_depth=drop_depth,
)

post_top_extension = 40
housing_depth = 20
blind_offset = post.height - housing_depth - tenon_length
beam_for_cut = positioned_beam.move(Location((blind_offset, 0, -post_top_extension)))

# Create mortise in post by subtracting the offset beam
post_with_mortise = create_receiving_cut(
    positioned_insert=beam_for_cut,
    receiving_shape=vertical_post,
)

print("=== 5. Blind Shouldered Mortise-and-Tenon ===")
print(f"Post: {post.width}W × {post.height}H (larger than beam)")
print(f"Beam: {beam.width}W × {beam.height}H")
print(f"Tenon: {tenon_length}L × {tenon_width:.1f}W × {tenon_height:.1f}H")
print(f"Shoulder depth: {shoulder_depth}mm")
print(f"Drop depth: {drop_depth}mm")
print(f"Housing depth: {housing_depth}mm")
print(f"Blind offset: {blind_offset}mm")

show_object(post_with_mortise.move(Location((0, 300, 0))), name="Post with Shouldered Mortise", options={"color": "sienna", "alpha": 0.7})
show_object(positioned_beam.move(Location((0, 300, 0))), name="Beam with Shouldered Tenon", options={"color": "burlywood"})

# %%
