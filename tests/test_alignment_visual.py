# %%
"""Visual comparison of alignment approaches.

Run each cell to visually compare JointAlignment vs auto_align.
"""
from ocp_vscode import show_object, set_defaults, Camera

set_defaults(
    reset_camera=Camera.CENTER,
    grid=(True, True, True),
)

# %%
# 1. JointAlignment - L-Lap Joint at corner
# Expected: Two beams meeting at 90° at corner, with lap cuts

from build123d import Location
from build123_timber import Timber, LLapJoint

main = Timber.beam(length=400, width=80, height=80)
cross = Timber.beam(length=300, width=80, height=80)

joint = LLapJoint(main=main, cross=cross)
joint.align()
joint.apply()

print("=== 1. JointAlignment - LLapJoint ===")
print(f"Main: pos={main.location.position}, rot={tuple(main.location.orientation)}")
print(f"Cross: pos={cross.location.position}, rot={tuple(cross.location.orientation)}")

main_bbox = main.global_shape.bounding_box()
cross_bbox = cross.global_shape.bounding_box()
print(f"Main bbox: X={main_bbox.min.X:.0f}-{main_bbox.max.X:.0f}, Y={main_bbox.min.Y:.0f}-{main_bbox.max.Y:.0f}, Z={main_bbox.min.Z:.0f}-{main_bbox.max.Z:.0f}")
print(f"Cross bbox: X={cross_bbox.min.X:.0f}-{cross_bbox.max.X:.0f}, Y={cross_bbox.min.Y:.0f}-{cross_bbox.max.Y:.0f}, Z={cross_bbox.min.Z:.0f}-{cross_bbox.max.Z:.0f}")

show_object(main.global_shape, name="Main (orange)", options={"color": "orange"})
show_object(cross.global_shape, name="Cross (blue)", options={"color": "blue"})

# %%
# 2. JointAlignment - T-Lap Joint at center
# Expected: Cross beam meets main at center, perpendicular

from build123d import Location
from build123_timber import Timber, TLapJoint

main = Timber.beam(length=400, width=80, height=80)
cross = Timber.beam(length=300, width=80, height=80)

joint = TLapJoint(main=main, cross=cross)
joint.align()
joint.apply()

print("=== 2. JointAlignment - TLapJoint ===")
print(f"Main: pos={main.location.position}, rot={tuple(main.location.orientation)}")
print(f"Cross: pos={cross.location.position}, rot={tuple(cross.location.orientation)}")

main_bbox = main.global_shape.bounding_box()
cross_bbox = cross.global_shape.bounding_box()
print(f"Main bbox: X={main_bbox.min.X:.0f}-{main_bbox.max.X:.0f}, Y={main_bbox.min.Y:.0f}-{main_bbox.max.Y:.0f}, Z={main_bbox.min.Z:.0f}-{main_bbox.max.Z:.0f}")
print(f"Cross bbox: X={cross_bbox.min.X:.0f}-{cross_bbox.max.X:.0f}, Y={cross_bbox.min.Y:.0f}-{cross_bbox.max.Y:.0f}, Z={cross_bbox.min.Z:.0f}-{cross_bbox.max.Z:.0f}")

show_object(main.global_shape, name="Main (orange)", options={"color": "orange"})
show_object(cross.global_shape, name="Cross (blue)", options={"color": "blue"})

# %%
# 3. JointAlignment - X-Lap Joint (cross in middle)
# Expected: Both beams cross at their centers

from build123d import Location
from build123_timber import Timber, XLapJoint

main = Timber.beam(length=400, width=80, height=80)
cross = Timber.beam(length=400, width=80, height=80)

joint = XLapJoint(main=main, cross=cross)
joint.align()
joint.apply()

print("=== 3. JointAlignment - XLapJoint ===")
print(f"Main: pos={main.location.position}, rot={tuple(main.location.orientation)}")
print(f"Cross: pos={cross.location.position}, rot={tuple(cross.location.orientation)}")

main_bbox = main.global_shape.bounding_box()
cross_bbox = cross.global_shape.bounding_box()
print(f"Main bbox: X={main_bbox.min.X:.0f}-{main_bbox.max.X:.0f}, Y={main_bbox.min.Y:.0f}-{main_bbox.max.Y:.0f}, Z={main_bbox.min.Z:.0f}-{main_bbox.max.Z:.0f}")
print(f"Cross bbox: X={cross_bbox.min.X:.0f}-{cross_bbox.max.X:.0f}, Y={cross_bbox.min.Y:.0f}-{cross_bbox.max.Y:.0f}, Z={cross_bbox.min.Z:.0f}-{cross_bbox.max.Z:.0f}")

show_object(main.global_shape, name="Main (orange)", options={"color": "orange"})
show_object(cross.global_shape, name="Cross (blue)", options={"color": "blue"})

# %%
# 4. auto_align - Post into plate (vertical into horizontal)
# Expected: Post stands vertically on top of plate

from build123d import Location, Vector
from build123_timber import Timber, make_timber_axis, auto_align

plate = Timber.beam(length=600, width=100, height=100)
post = Timber.post(length=400, width=80, height=80, location=Location((800, 0, 200)))

print("=== 4. auto_align - Post into Plate ===")
print(f"BEFORE:")
print(f"  Plate: pos={plate.location.position}, rot={tuple(plate.location.orientation)}")
print(f"  Post: pos={post.location.position}, rot={tuple(post.location.orientation)}")

# Create axes: post bottom points down (-Z in local = -X after rotation), plate top points up
tenon_axis = make_timber_axis(post, Vector(0, 0, 0), Vector(-1, 0, 0))  # post start, pointing into
mortise_axis = make_timber_axis(plate, Vector(300, 50, 100), Vector(0, 0, 1))  # plate top center, pointing up

auto_align(post, tenon_axis, plate, mortise_axis)

print(f"AFTER:")
print(f"  Plate: pos={plate.location.position}, rot={tuple(plate.location.orientation)}")
print(f"  Post: pos={post.location.position}, rot={tuple(post.location.orientation)}")

plate_bbox = plate.global_shape.bounding_box()
post_bbox = post.global_shape.bounding_box()
print(f"Plate bbox: X={plate_bbox.min.X:.0f}-{plate_bbox.max.X:.0f}, Y={plate_bbox.min.Y:.0f}-{plate_bbox.max.Y:.0f}, Z={plate_bbox.min.Z:.0f}-{plate_bbox.max.Z:.0f}")
print(f"Post bbox: X={post_bbox.min.X:.0f}-{post_bbox.max.X:.0f}, Y={post_bbox.min.Y:.0f}-{post_bbox.max.Y:.0f}, Z={post_bbox.min.Z:.0f}-{post_bbox.max.Z:.0f}")

show_object(plate.global_shape, name="Plate (orange)", options={"color": "orange"})
show_object(post.global_shape, name="Post (blue)", options={"color": "blue"})

# %%
# 5. auto_align - Beam into post (horizontal into vertical)
# Expected: Beam extends horizontally from the side of a vertical post

from build123d import Location, Vector
from build123_timber import Timber, make_timber_axis, auto_align

post = Timber.post(length=500, width=100, height=100)
beam = Timber.beam(length=400, width=80, height=80, location=Location((500, 0, 100)))

print("=== 5. auto_align - Beam into Post ===")
print(f"BEFORE:")
print(f"  Post: pos={post.location.position}, rot={tuple(post.location.orientation)}")
print(f"  Beam: pos={beam.location.position}, rot={tuple(beam.location.orientation)}")

# Beam end into post side
tenon_axis = make_timber_axis(beam, Vector(0, 0, 0), Vector(-1, 0, 0))  # beam start, pointing back
mortise_axis = make_timber_axis(post, Vector(0, 50, 250), Vector(1, 0, 0))  # post side at mid-height

auto_align(beam, tenon_axis, post, mortise_axis)

print(f"AFTER:")
print(f"  Post: pos={post.location.position}, rot={tuple(post.location.orientation)}")
print(f"  Beam: pos={beam.location.position}, rot={tuple(beam.location.orientation)}")

post_bbox = post.global_shape.bounding_box()
beam_bbox = beam.global_shape.bounding_box()
print(f"Post bbox: X={post_bbox.min.X:.0f}-{post_bbox.max.X:.0f}, Y={post_bbox.min.Y:.0f}-{post_bbox.max.Y:.0f}, Z={post_bbox.min.Z:.0f}-{post_bbox.max.Z:.0f}")
print(f"Beam bbox: X={beam_bbox.min.X:.0f}-{beam_bbox.max.X:.0f}, Y={beam_bbox.min.Y:.0f}-{beam_bbox.max.Y:.0f}, Z={beam_bbox.min.Z:.0f}-{beam_bbox.max.Z:.0f}")

show_object(post.global_shape, name="Post (orange)", options={"color": "orange"})
show_object(beam.global_shape, name="Beam (blue)", options={"color": "blue"})

# %%
# 6. Comparison: Same scenario with both approaches
# L-corner joint - main along X, cross along Y

from build123d import Location, Vector
from build123_timber import Timber, LLapJoint, make_timber_axis, auto_align

# --- JointAlignment approach ---
main_ja = Timber.beam(length=400, width=80, height=80)
cross_ja = Timber.beam(length=300, width=80, height=80)

joint = LLapJoint(main=main_ja, cross=cross_ja)
joint.align()
# Don't apply cuts yet - just compare positions

# --- auto_align approach ---
main_aa = Timber.beam(length=400, width=80, height=80)
cross_aa = Timber.beam(length=300, width=80, height=80, location=Location((500, 500, 0)))

# Cross end meets main end, perpendicular
tenon_axis = make_timber_axis(cross_aa, Vector(0, 0, 0), Vector(-1, 0, 0))
mortise_axis = make_timber_axis(main_aa, Vector(400, 40, 40), Vector(0, 1, 0))

auto_align(cross_aa, tenon_axis, main_aa, mortise_axis)

print("=== 6. Comparison: JointAlignment vs auto_align ===")
print(f"JointAlignment:")
print(f"  Main: pos={main_ja.location.position}")
print(f"  Cross: pos={cross_ja.location.position}, rot={tuple(cross_ja.location.orientation)}")
print(f"auto_align:")
print(f"  Main: pos={main_aa.location.position}")
print(f"  Cross: pos={cross_aa.location.position}, rot={tuple(cross_aa.location.orientation)}")

# Show JointAlignment result (left)
show_object(main_ja.global_shape, name="JA Main", options={"color": "orange"})
show_object(cross_ja.global_shape, name="JA Cross", options={"color": "blue"})

# Show auto_align result (right, offset by 600)
main_aa_offset = main_aa.moved(Location((0, 600, 0)))
cross_aa_offset = cross_aa.moved(Location((0, 600, 0)))
show_object(main_aa_offset.global_shape, name="AA Main", options={"color": "darkorange"})
show_object(cross_aa_offset.global_shape, name="AA Cross", options={"color": "darkblue"})

# %%
