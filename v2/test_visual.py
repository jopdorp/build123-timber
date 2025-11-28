# %%
# 1. Plain Beam (reference)
# Expected: Box at origin extending in +X, +Y, +Z

from ocp_vscode import show_object
from timber_joints.beam import Beam

beam = Beam(length=300, width=100, height=100)
bbox = beam.shape.bounding_box()

print("=== 1. Plain Beam (reference) ===")
print(f"BBox: X={bbox.min.X:.0f}-{bbox.max.X:.0f}, Y={bbox.min.Y:.0f}-{bbox.max.Y:.0f}, Z={bbox.min.Z:.0f}-{bbox.max.Z:.0f}")

show_object(beam.shape, name="Plain Beam", options={"color": "orange"})

# %%
# 2. Lap Joint - positive/inserting end
# Beam with half-depth cut at the end, ready to insert into matching cut

from ocp_vscode import show_object
from build123d import Align, Box, Location
from timber_joints.beam import Beam
from timber_joints.lap_joint import LapJoint

beam = Beam(length=300, width=100, height=100)
lap = LapJoint(
    beam=beam,
    cut_depth=50,  # Half the height
    cut_length=100,
    from_top=True
)

print("=== 2. Lap Joint (inserting end) ===")
print(f"Cut depth: {lap.cut_depth}mm (from top)")
print(f"Cut length: {lap.cut_length}mm")

# Show cut shape on left, result on right
show_object(beam.shape, name="Beam blank", options={"color": "orange", "alpha": 0.3})
show_object(lap.shape.move(Location((400, 0, 0))), name="Lap Joint result", options={"color": "green"})

# %%
# 3. Basic Tenon - centered projection at beam end
# Classic mortise-tenon proportions: 1/3 width, 2/3 height

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.tenon import Tenon

beam = Beam(length=300, width=100, height=100)
tenon = Tenon(
    beam=beam,
    tenon_width=100 / 3,   # ~33mm (classic 1/3 width)
    tenon_height=100 * 2 / 3,  # ~67mm (classic 2/3 height)
    tenon_length=50,
    at_start=False
)

print("=== 3. Basic Tenon ===")
print(f"Tenon: {tenon.tenon_length}L × {tenon.tenon_width:.1f}W × {tenon.tenon_height:.1f}H")

show_object(beam.shape, name="Beam blank", options={"color": "orange", "alpha": 0.3})
show_object(tenon.shape.move(Location((400, 0, 0))), name="Tenon result", options={"color": "blue"})

# %%
# 4. Shouldered Tenon - tenon with angled/triangular shoulder
# The angled shoulder creates a wedge-shaped bearing surface

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.shouldered_tenon import ShoulderedTenon

beam = Beam(length=300, width=100, height=100)
shouldered = ShoulderedTenon(
    beam=beam,
    tenon_width=100 / 3,
    tenon_height=100 * 2 / 3,
    tenon_length=40,
    shoulder_depth=20,
    at_start=False
)

print("=== 4. Shouldered Tenon (angled) ===")
print(f"Tenon: {shouldered.tenon_length}L × {shouldered.tenon_width:.1f}W × {shouldered.tenon_height:.1f}H")
print(f"Shoulder depth: {shouldered.shoulder_depth}mm")

show_object(beam.shape, name="Beam blank", options={"color": "orange", "alpha": 0.3})
show_object(shouldered.shape.move(Location((400, 0, 0))), name="Shouldered Tenon result", options={"color": "purple"})

# %%
# 5. Dovetail Insert - tapered projection
# Widens toward the base for mechanical locking

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.dovetail import DovetailInsert

beam = Beam(length=300, width=100, height=100)
dovetail = DovetailInsert(
    beam=beam,
    dovetail_width=100 / 3,
    dovetail_height=50,
    dovetail_length=50,
    cone_angle=10.0,
    at_start=False
)

narrow, wide = dovetail._get_widths()

print("=== 5. Dovetail Insert ===")
print(f"Dovetail: {dovetail.dovetail_length}L × {dovetail.dovetail_height}H")
print(f"Width: {narrow:.1f}mm (tip) → {wide:.1f}mm (base)")
print(f"Cone angle: {dovetail.cone_angle}°")

show_object(beam.shape, name="Beam blank", options={"color": "orange", "alpha": 0.3})
show_object(dovetail.shape.move(Location((400, 0, 0))), name="Dovetail Insert result", options={"color": "red"})

# %%
# 6. Lap X-Section - lap cut at a cross-section point along the beam
# Used for cross-lap joints where two beams intersect

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.lap_x_section import LapXSection

beam = Beam(length=300, width=100, height=100)
lap_x = LapXSection(
    beam=beam,
    cut_depth=50,  # Half depth
    cut_length=100,  # Width of intersecting beam
    x_position=150,  # Center of beam
    from_top=True
)

print("=== 6. Lap X-Section (cross lap) ===")
print(f"Cut depth: {lap_x.cut_depth}mm (from top)")
print(f"Cut length: {lap_x.cut_length}mm at X={lap_x.x_position}mm")

show_object(beam.shape, name="Beam blank", options={"color": "orange", "alpha": 0.3})
show_object(lap_x.shape.move(Location((400, 0, 0))), name="Lap X-Section result", options={"color": "cyan"})

# %%
# 7. Half-Dovetail - dovetail insert at top or bottom of beam
# Same as dovetail insert but positioned at top/bottom instead of centered

from ocp_vscode import show_object
from build123d import Location
from timber_joints.beam import Beam
from timber_joints.half_dovetail import HalfDovetail

beam = Beam(length=300, width=100, height=100)
half_dt = HalfDovetail(
    beam=beam,
    dovetail_width=40,
    dovetail_height=50,
    dovetail_length=70,
    dovetail_angle=20.0,
    at_start=False,
    at_top=True
)

print("=== 7. Half-Dovetail ===")
print(f"Dovetail: {half_dt.dovetail_length}L × {half_dt.dovetail_height}H at top")

show_object(beam.shape, name="Beam blank", options={"color": "orange", "alpha": 0.3})
show_object(half_dt.shape.move(Location((400, 0, 0))), name="Half-Dovetail result", options={"color": "magenta"})

# %%
# 8. Beam on Post - alignment only (no joint cuts)
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

print("=== 8. Beam on Post (alignment) ===")
print(f"Post bbox: Z={post_bbox.min.Z:.0f}-{post_bbox.max.Z:.0f}")
print(f"Beam bbox: Z={beam_bbox.min.Z:.0f}-{beam_bbox.max.Z:.0f}")
print(f"Beam bottom ({beam_bbox.min.Z:.0f}) == Post top ({post_bbox.max.Z:.0f}): {abs(beam_bbox.min.Z - post_bbox.max.Z) < 1}")

show_object(vertical_post, name="Post", options={"color": "sienna"})
show_object(positioned_beam, name="Beam on Post", options={"color": "burlywood"})

# %%
# 9. Beam in Post with Tongue-and-Fork joint
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

print("=== 9. Beam in Post with Tongue-and-Fork ===")
print(f"Post top: Z={post_bbox.max.Z:.0f}")
print(f"Beam bottom: Z={beam_bbox.min.Z:.0f}")
print(f"Drop depth: {drop_depth}mm")
print(f"Tongue width: {tongue_width:.1f}mm")
print(f"Tenon length: {tenon_length}mm (through post)")

show_object(post_with_fork.move(Location((0, 300, 0))), name="Post with Fork", options={"color": "sienna"})
show_object(positioned_beam.move(Location((0, 300, 0))), name="Beam with Tongue", options={"color": "burlywood"})

# %%
# 10. Housed Tongue-and-Fork - beam drops into post but tenon doesn't go all the way through
# Similar to #9 but with shorter tenon that stays inside the post

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

print("=== 10. Housed Tongue-and-Fork ===")
print(f"Tenon: {tenon_length}L × {tongue_width:.1f}W × {beam.height}H")
print(f"Drop depth: {drop_depth}mm")
print(f"Tenon length: {tenon_length}mm (housed, not through)")

show_object(post_with_fork.move(Location((0, 600, 0))), name="Post with Housed Fork", options={"color": "sienna"})
show_object(positioned_beam.move(Location((0, 600, 0))), name="Beam with Tongue", options={"color": "burlywood"})

# %%
# 11. Housed Blind Mortise-and-Tenon - beam smaller than post
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
print("=== 11. Housed Blind Mortise-and-Tenon ===")
print(f"Post: {post.width}W × {post.height}H (larger than beam)")
print(f"Beam: {beam.width}W × {beam.height}H")
print(f"Tenon: {tenon_length}L × {tenon_width:.1f}W × {tenon_height:.1f}H")
print(f"Drop depth: {drop_depth}mm")
print(f"Housing depth: {housing_depth}mm (extra pocket around tenon)")
print(f"Blind offset: {blind_offset}mm (calculated: post.height - tenon_length + housing_depth)")

show_object(post_with_mortise, name="Post with Mortise", options={"color": "sienna", "alpha": 0.7})
show_object(positioned_beam, name="Beam with Tenon", options={"color": "burlywood"})

# %%
