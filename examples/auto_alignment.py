# %%
from build123d import Location, Compound, Vector
from ocp_vscode import show_object, set_defaults, Camera

from build123_timber import (
    Beam,
    Timber,
    TenonMortiseJoint,
    show_lcs,
    make_timber_axis,
    auto_align,
)

set_defaults(reset_camera=Camera.CENTER)

# %%
# LCS Visualizer Demo
# Shows the local coordinate system of each timber as colored axes:
# - Red = X axis (along timber length)
# - Green = Y axis (across timber width)
# - Blue = Z axis (timber height)

beam = Beam(length=400, width=80, height=80, name="demo_beam")
x_axis, y_axis, z_axis = show_lcs(beam, size=100)

show_object(beam.blank, name="beam", options={"color": "burlywood"})
show_object(x_axis, name="X_axis", options={"color": "red"})
show_object(y_axis, name="Y_axis", options={"color": "green"})
show_object(z_axis, name="Z_axis", options={"color": "blue"})

# %%
# LCS of rotated timber - see how axes rotate with it
rotated_beam = Beam(length=400, width=80, height=80, location=Location((0, 300, 0), (0, 0, 45)))
rx, ry, rz = show_lcs(rotated_beam, size=100)

show_object(rotated_beam.blank, name="rotated_beam", options={"color": "tan"})
show_object(rx, name="rotated_X", options={"color": "red"})
show_object(ry, name="rotated_Y", options={"color": "green"})
show_object(rz, name="rotated_Z", options={"color": "blue"})

# %%
# Auto-Alignment Example 1: Post tenon into beam mortise
# The post has a tenon at its bottom, beam has mortise on top

# Horizontal beam (plate)
plate = Beam(length=600, width=100, height=100, name="plate", location=Location((0, 600, 0)))

# Vertical post - initially positioned elsewhere
post = Timber.post(length=400, width=80, height=80, name="post", location=Location((800, 600, 200)))

# Define the axes for alignment:
# - Tenon axis: at post's START (bottom), pointing outward (-X in post's local coords since post is oriented with length along X)
# - Mortise axis: at plate's center-top, pointing upward (+Z)

# Post tenon protrudes from its start (X=0) in -X direction (into the mortise)
tenon_axis = make_timber_axis(post, Vector(0, 0, 0), Vector(-1, 0, 0))

# Mortise on plate at center-top, receiving from above (+Z direction into plate)
mortise_axis = make_timber_axis(plate, Vector(300, 0, 50), Vector(0, 0, 1))

# Auto-align: moves and rotates post so tenon meets mortise
auto_align(post, tenon_axis, plate, mortise_axis)

# Now apply the joinery cuts
TenonMortiseJoint(main=plate, cross=post, tenon_length=50).apply()

# Show with LCS
px, py, pz = show_lcs(plate, size=80)
postx, posty, postz = show_lcs(post, size=80)

show_object(plate.global_shape, name="plate", options={"color": "burlywood"})
show_object(post.global_shape, name="post", options={"color": "peru"})
show_object(Compound([px, py, pz]), name="plate_lcs")
show_object(Compound([postx, posty, postz]), name="post_lcs")

# %%
# Auto-Alignment Example 2: Beam end tenon into post mortise (horizontal T-joint)

# Vertical post
post2 = Timber.post(length=500, width=100, height=100, name="post2", location=Location((0, 1200, 0), (90, 0, 0)))

# Horizontal beam - starts somewhere else
beam2 = Beam(length=400, width=80, height=80, name="beam2", location=Location((500, 1200, 100)))

# Tenon at beam's END, pointing in +X direction
beam_tenon = make_timber_axis(beam2, Vector(400, 0, 0), Vector(1, 0, 0))

# Mortise on post's side at height 250, receiving from +Y direction
post_mortise = make_timber_axis(post2, Vector(50, 0, 250), Vector(0, 1, 0))

auto_align(beam2, beam_tenon, post2, post_mortise)

TenonMortiseJoint(main=post2, cross=beam2, tenon_length=50).apply()

show_object(post2.global_shape, name="post2", options={"color": "sienna"})
show_object(beam2.global_shape, name="beam2", options={"color": "burlywood"})

# %%
# Auto-Alignment Example 3: Angled brace
# Brace connects post to beam at 45 degrees

post3 = Timber.post(length=400, width=100, height=100, name="post3", location=Location((0, 1800, 0), (90, 0, 0)))
beam3 = Beam(length=500, width=100, height=100, name="beam3", location=Location((50, 1800, 350)))

# Brace timber - starts unpositioned
brace = Beam(length=300, width=60, height=60, name="brace", location=Location((400, 1800, 200)))

# Brace tenon at START, pointing in -X direction (will insert into post)
brace_tenon = make_timber_axis(brace, Vector(0, 0, 0), Vector(-1, 0, 0))

# Housing on post at angle - 45 degrees up and to the right
# At height 150 on post, receiving at 45 degree angle
import math
angle = math.radians(45)
brace_housing = make_timber_axis(
    post3, 
    Vector(50, 0, 150),  # Point on post face
    Vector(math.cos(angle), 0, math.sin(angle))  # 45 degree direction
)

auto_align(brace, brace_tenon, post3, brace_housing)

show_object(post3.global_shape, name="post3", options={"color": "sienna"})
show_object(beam3.global_shape, name="top_beam", options={"color": "burlywood"})
show_object(brace.global_shape, name="brace", options={"color": "peru"})

# %%
# Summary: The key insight is that auto_align() works by:
# 1. Defining where the tenon/protrusion is and which direction it points
# 2. Defining where the mortise/housing is and which direction it receives from
# 3. Rotating and translating the tenon timber so axes align (opposing directions)
#
# This solves all the problems of:
# - Wrong rotation (tenon twisted 90°)
# - Wrong face (mortise on side instead of top)
# - Floating joints (not seated properly)
# - Mirrored axes
