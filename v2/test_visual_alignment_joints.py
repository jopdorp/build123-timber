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
    beam=beam.shape,
    post=vertical_post,
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
positioned_beam, _, beam_loc = align_beam_in_post(
    beam=beam_with_tenon.shape,
    post=vertical_post,
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
positioned_beam, _, beam_loc = align_beam_in_post(
    beam=beam_with_tenon.shape,
    post=vertical_post,
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
from timber_joints.beam import Beam
from timber_joints.tenon import Tenon
from timber_joints.alignment import align_beam_in_post, make_post_vertical, create_receiving_cut, position_for_blind_mortise

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
positioned_beam, _, _ = align_beam_in_post(
    beam=beam_with_tenon.shape,
    post=vertical_post,
    drop_depth=drop_depth,
)

post_top_extension = 40  # How much the mortise extends above the beam (housing on top)
housing_depth = 20  # How far from the far edge of post the mortise should stop

# Position beam for blind mortise cut using utility function (pass both beam and post)
beam_for_cut, _ = position_for_blind_mortise(
    beam=positioned_beam,
    post=vertical_post,
    tenon_length=tenon_length,
    housing_depth=housing_depth,
    post_top_extension=post_top_extension,
    at_start=True,
)

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

show_object(post_with_mortise.move(Location((0, -300, 0))), name="Post with Mortise", options={"color": "sienna", "alpha": 0.7})
show_object(positioned_beam.move(Location((0, -300, 0))), name="Beam with Tenon", options={"color": "burlywood"})

# %%
# 5.A Blind Shouldered Mortise-and-Tenon - with angled shoulder
# Same as #4 but using shouldered tenon for better bearing surface

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.shouldered_tenon import ShoulderedTenon
from timber_joints.alignment import align_beam_in_post, make_post_vertical, create_receiving_cut, position_for_blind_mortise

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
positioned_beam, _, _ = align_beam_in_post(
    beam=beam_with_tenon.shape,
    post=vertical_post,
    drop_depth=drop_depth,
)

post_top_extension = 40
housing_depth = 20

# Position beam for blind mortise cut using utility function (pass both beam and post)
beam_for_cut, _ = position_for_blind_mortise(
    beam=positioned_beam,
    post=vertical_post,
    tenon_length=tenon_length,
    housing_depth=housing_depth,
    post_top_extension=post_top_extension,
    at_start=True,
)

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

show_object(post_with_mortise.move(Location((0, -600, 0))), name="Post with Shouldered Mortise", options={"color": "sienna", "alpha": 0.7})
show_object(positioned_beam.move(Location((0, -600, 0))), name="Beam with Shouldered Tenon", options={"color": "burlywood"})

# %%
# 5.B Blind Shouldered Mortise-and-Tenon at END of beam (at_start=False)
# Same as #5 but with tenon at the end of beam instead of start

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.shouldered_tenon import ShoulderedTenon
from timber_joints.alignment import align_beam_in_post, make_post_vertical, create_receiving_cut, position_for_blind_mortise

# Post is larger than beam
post = Beam(length=400, width=150, height=150)
beam = Beam(length=600, width=80, height=120)

# Create shouldered tenon at END of beam
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
    at_start=False  # At END of beam
)

# Make post vertical
vertical_post = make_post_vertical(post.shape)

# Align beam in post - at_start=False means beam END goes into post
drop_depth = beam.height
positioned_beam, _, _ = align_beam_in_post(
    beam=beam_with_tenon.shape,
    post=vertical_post,
    drop_depth=drop_depth,
    at_start=False,  # Beam END aligns to post
)

post_top_extension = 40
housing_depth = 20

# Position beam for blind mortise cut using utility function (pass both beam and post)
beam_for_cut, _ = position_for_blind_mortise(
    beam=positioned_beam,
    post=vertical_post,
    tenon_length=tenon_length,
    housing_depth=housing_depth,
    post_top_extension=post_top_extension,
    at_start=False,  # Tenon is at END of beam
)

# Create mortise in post by subtracting the offset beam
post_with_mortise = create_receiving_cut(
    positioned_insert=beam_for_cut,
    receiving_shape=vertical_post,
)

print("=== 5.B Blind Shouldered Mortise-and-Tenon (at_start=False) ===")
print(f"Post: {post.width}W × {post.height}H (larger than beam)")
print(f"Beam: {beam.width}W × {beam.height}H")
print(f"Tenon at END: {tenon_length}L × {tenon_width:.1f}W × {tenon_height:.1f}H")
print(f"Shoulder depth: {shoulder_depth}mm")
print(f"Drop depth: {drop_depth}mm")
print(f"Housing depth: {housing_depth}mm")

show_object(post_with_mortise.move(Location((0, -900, 0))), name="Post with Shouldered Mortise (end)", options={"color": "sienna", "alpha": 0.7})
show_object(positioned_beam.move(Location((0, -900, 0))), name="Beam with Shouldered Tenon (end)", options={"color": "burlywood"})

# %%
# 5.C Blind Shouldered Mortise-and-Tenon with move_post=True (at_start=True)
# Same as #5 but moving the post to the beam instead of beam to post

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.shouldered_tenon import ShoulderedTenon
from timber_joints.alignment import align_beam_in_post, make_post_vertical, create_receiving_cut, position_for_blind_mortise

# Post is larger than beam
post = Beam(length=400, width=150, height=150)
beam = Beam(length=600, width=80, height=120)

# Create shouldered tenon on beam at START
tenon_width = beam.width / 3
tenon_height = beam.height * 2 / 3
tenon_length = 60
shoulder_depth = 20

beam_with_tenon = ShoulderedTenon(
    beam=beam,
    tenon_width=tenon_width,
    tenon_height=tenon_height,
    tenon_length=tenon_length,
    shoulder_depth=shoulder_depth,
    at_start=True
).shape

# Make post vertical
vertical_post = make_post_vertical(post.shape)

# Align post to beam (move_post=True) - beam stays at origin
drop_depth = beam.height
_, positioned_post, _ = align_beam_in_post(
    beam=beam_with_tenon,
    post=vertical_post,
    drop_depth=drop_depth,
    at_start=True,
    move_post=True,  # Move post to beam instead of beam to post
)

post_top_extension = 40
housing_depth = 20

# Position beam for blind mortise cut - pass both beam and positioned post
_, post_for_cut = position_for_blind_mortise(
    beam=beam_with_tenon,
    post=positioned_post,
    tenon_length=tenon_length,
    housing_depth=housing_depth,
    post_top_extension=post_top_extension,
    at_start=True,
)

# Create mortise in positioned post
post_with_mortise = create_receiving_cut(
    positioned_insert=beam_with_tenon,
    receiving_shape=post_for_cut,
)

print("=== 5.C Blind Shouldered Mortise-and-Tenon (move_post=True, at_start=True) ===")
print(f"Post: {post.width}W × {post.height}H (larger than beam)")
print(f"Beam: {beam.width}W × {beam.height}H")
print(f"Tenon at START: {tenon_length}L × {tenon_width:.1f}W × {tenon_height:.1f}H")
print(f"Shoulder depth: {shoulder_depth}mm")
print(f"Drop depth: {drop_depth}mm")
print("Note: Post moved to beam (beam stays at origin)")

show_object(post_with_mortise.move(Location((0, -1200, 0))), name="Post moved to Beam (start)", options={"color": "sienna", "alpha": 0.7})
show_object(beam_with_tenon.move(Location((0, -1200, 0))), name="Beam at origin (start)", options={"color": "burlywood"})

# %%
# 5.D Blind Shouldered Mortise-and-Tenon with move_post=True (at_start=False)
# Same as #5.B but moving the post to the beam instead of beam to post

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.shouldered_tenon import ShoulderedTenon
from timber_joints.alignment import align_beam_in_post, make_post_vertical, create_receiving_cut, position_for_blind_mortise

# Post is larger than beam
post = Beam(length=400, width=150, height=150)
beam = Beam(length=600, width=80, height=120)

# Create shouldered tenon at END of beam
tenon_width = beam.width / 3
tenon_height = beam.height * 2 / 3
tenon_length = 60
shoulder_depth = 20

beam_with_tenon = ShoulderedTenon(
    beam=beam,
    tenon_width=tenon_width,
    tenon_height=tenon_height,
    tenon_length=tenon_length,
    shoulder_depth=shoulder_depth,
    at_start=False  # At END of beam
).shape

# Make post vertical
vertical_post = make_post_vertical(post.shape)

# Align post to beam end (move_post=True) - beam stays at origin
drop_depth = beam.height
_, positioned_post, _ = align_beam_in_post(
    beam=beam_with_tenon,
    post=vertical_post,
    drop_depth=drop_depth,
    at_start=False,  # Joint at beam END
    move_post=True,  # Move post to beam instead of beam to post
)

post_top_extension = 40
housing_depth = 20

# Position beam for blind mortise cut - pass both beam and positioned post
_, post_for_cut = position_for_blind_mortise(
    beam=beam_with_tenon,
    post=positioned_post,
    tenon_length=tenon_length,
    housing_depth=housing_depth,
    post_top_extension=post_top_extension,
    at_start=False,
)

# Create mortise in positioned post
post_with_mortise = create_receiving_cut(
    positioned_insert=beam_with_tenon,
    receiving_shape=post_for_cut,
)

print("=== 5.D Blind Shouldered Mortise-and-Tenon (move_post=True, at_start=False) ===")
print(f"Post: {post.width}W × {post.height}H (larger than beam)")
print(f"Beam: {beam.width}W × {beam.height}H")
print(f"Tenon at END: {tenon_length}L × {tenon_width:.1f}W × {tenon_height:.1f}H")
print(f"Shoulder depth: {shoulder_depth}mm")
print(f"Drop depth: {drop_depth}mm")
print("Note: Post moved to beam end (beam stays at origin)")

show_object(post_with_mortise.move(Location((0, -1500, 0))), name="Post moved to Beam (end)", options={"color": "sienna", "alpha": 0.7})
show_object(beam_with_tenon.move(Location((0, -1500, 0))), name="Beam at origin (end)", options={"color": "burlywood"})

# %%
# 6. Beam with Shouldered Tenons on BOTH ends
# This demonstrates chaining joint cuts - applying tenon to an already-cut shape

from ocp_vscode import show_object
from timber_joints.beam import Beam
from timber_joints.shouldered_tenon import ShoulderedTenon

# Create a beam
beam = Beam(length=5000, width=150, height=150)

# Tenon dimensions
tenon_width = beam.width / 3
tenon_height = beam.height * 2 / 3
tenon_length = 60
shoulder_depth = 20

# Create tenon at start - returns Part
beam_with_start = ShoulderedTenon(
    beam=beam,
    tenon_width=tenon_width,
    tenon_height=tenon_height,
    tenon_length=tenon_length,
    shoulder_depth=shoulder_depth,
    at_start=True,
).shape

# Chain: create tenon at end on the already-cut shape
# This works because all joints now accept Part and use bounding_box for dimensions
beam_with_both_tenons = ShoulderedTenon(
    beam=beam_with_start,  # Pass the Part directly
    tenon_width=tenon_width,
    tenon_height=tenon_height,
    tenon_length=tenon_length,
    shoulder_depth=shoulder_depth,
    at_start=False,
).shape

print("=== 6. Beam with Shouldered Tenons on BOTH Ends ===")
print(f"Beam: {beam.length}L × {beam.width}W × {beam.height}H")
print(f"Tenon: {tenon_length}L × {tenon_width:.1f}W × {tenon_height:.1f}H")
print(f"Shoulder depth: {shoulder_depth}mm")
print("Note: Chained joint calls - second tenon applied to already-cut Part")

show_object(beam_with_both_tenons.move(Location((-1200, 0, 1200))), name="Beam with Both Tenons", options={"color": "burlywood"})

# %%
# 7. Complete Bent - Two posts with beam having shouldered tenons on both ends
# This demonstrates the full assembly with posts at both ends

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.shouldered_tenon import ShoulderedTenon
from timber_joints.alignment import align_beam_in_post, make_post_vertical, create_receiving_cut, position_for_blind_mortise

# Dimensions
post_height = 3000
post_section = 150
beam_length = 5000

# Create posts and beam
post_left = Beam(length=post_height, width=post_section, height=post_section)
post_right = Beam(length=post_height, width=post_section, height=post_section)
beam = Beam(length=beam_length, width=post_section, height=post_section)

# Tenon dimensions
tenon_width = beam.width / 3
tenon_height = beam.height * 2 / 3
tenon_length = 60
shoulder_depth = 20
housing_depth = 20
post_top_extension = 300
drop_depth = beam.height

# Create beam with tenons on BOTH ends
beam_with_start = ShoulderedTenon(
    beam=beam,
    tenon_width=tenon_width,
    tenon_height=tenon_height,
    tenon_length=tenon_length,
    shoulder_depth=shoulder_depth,
    at_start=True,
).shape

beam_with_both_tenons = ShoulderedTenon(
    beam=beam_with_start,
    tenon_width=tenon_width,
    tenon_height=tenon_height,
    tenon_length=tenon_length,
    shoulder_depth=shoulder_depth,
    at_start=False,
).shape

# Make posts vertical
vertical_post_left = make_post_vertical(post_left.shape)
vertical_post_right = make_post_vertical(post_right.shape)

# Step 1: Align beam to LEFT post (beam start at post, move beam to post)
positioned_beam, _, _ = align_beam_in_post(
    beam=beam_with_both_tenons,
    post=vertical_post_left,
    drop_depth=drop_depth,
    at_start=True,
    move_post=False,
)

# Step 2: Create mortise in left post (pass both beam and post)
beam_for_left_cut, _ = position_for_blind_mortise(
    beam=positioned_beam,
    post=vertical_post_left,
    tenon_length=tenon_length,
    housing_depth=housing_depth,
    post_top_extension=post_top_extension,
    at_start=True,
)
left_post_with_mortise = create_receiving_cut(beam_for_left_cut, vertical_post_left)

# Step 3: Align right post to beam end (move post to beam)
_, positioned_post_right, _ = align_beam_in_post(
    beam=positioned_beam,  # Use positioned_beam, not beam_final
    post=vertical_post_right,
    drop_depth=drop_depth,
    at_start=False,
    move_post=True,
)

# Step 4: Create mortise in right post (move post for blind cut)
_, positioned_post_right_cut = position_for_blind_mortise(
    beam=positioned_beam,
    post=positioned_post_right,
    tenon_length=tenon_length,
    housing_depth=housing_depth,
    post_top_extension=post_top_extension,
    at_start=False,
    move_post=True,
)
right_post_with_mortise = create_receiving_cut(positioned_beam, positioned_post_right_cut)

print("=== 7. Complete Bent - Two Posts with Beam ===")
print(f"Post height: {post_height}mm, section: {post_section}mm")
print(f"Beam length: {beam_length}mm")
print(f"Tenon: {tenon_length}L × {tenon_width:.1f}W × {tenon_height:.1f}H")

show_object(left_post_with_mortise.move(Location((-1200, 1800, 1200))), name="Left Post", options={"color": "sienna", "alpha": 0.7})
show_object(right_post_with_mortise.move(Location((-1200, 1800, 1200))), name="Right Post", options={"color": "sienna", "alpha": 0.7})
show_object(positioned_beam.move(Location((-1200, 1800, 1200))), name="Beam with Both Tenons", options={"color": "burlywood"})

# %%
