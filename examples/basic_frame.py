# %%
import math

from build123d import Location
from ocp_vscode import show_object, set_defaults, Camera

from build123_timber import (
    Beam,
    Post,
    Timber,
    TimberModel,
    LLapJoint,
    TenonMortiseJoint,
    RafterLayout,
)

set_defaults(reset_camera=Camera.CENTER)

# %%
model = TimberModel(name="TimberFrameShed")

# Dimensions (mm)
width = 3000      # X direction (length of shed)
depth = 4000      # Y direction (front to back)
wall_height = 2400
post_w = 100
beam_w = 100
beam_h = 150
rafter_w = 60
rafter_h = 150
roof_pitch = 30

half_post = post_w / 2

# Four corner posts - vertical
posts_data = [
    ("post_fl", half_post, half_post),
    ("post_fr", width - half_post, half_post),
    ("post_br", width - half_post, depth - half_post),
    ("post_bl", half_post, depth - half_post),
]

posts = {}
for name, x, y in posts_data:
    post = Post(
        length=wall_height,
        width=post_w,
        height=post_w,
        name=name,
        location=Location((x, y, 0), (0, -90, 0)),
    )
    posts[name] = post
    model.add_element(post)

# Top plate beams
beam_front = Beam(
    length=width,
    width=beam_w,
    height=beam_h,
    name="beam_front",
    location=Location((0, half_post, wall_height + beam_h / 2)),
)
beam_back = Beam(
    length=width,
    width=beam_w,
    height=beam_h,
    name="beam_back",
    location=Location((0, depth - half_post, wall_height + beam_h / 2)),
)
beam_left = Beam(
    length=depth,
    width=beam_w,
    height=beam_h,
    name="beam_left",
    location=Location((half_post, 0, wall_height + beam_h / 2), (0, 0, 90)),
)
beam_right = Beam(
    length=depth,
    width=beam_w,
    height=beam_h,
    name="beam_right",
    location=Location((width - half_post, 0, wall_height + beam_h / 2), (0, 0, 90)),
)

for beam in [beam_front, beam_back, beam_left, beam_right]:
    model.add_element(beam)

# Lap joints at corners
LLapJoint(main=beam_front, cross=beam_left).apply()
LLapJoint(main=beam_front, cross=beam_right).apply()
LLapJoint(main=beam_back, cross=beam_left).apply()
LLapJoint(main=beam_back, cross=beam_right).apply()

# Mortise-tenon where posts meet beams
for post in posts.values():
    TenonMortiseJoint(main=beam_front, cross=post, tenon_length=50).apply()
    TenonMortiseJoint(main=beam_back, cross=post, tenon_length=50).apply()

# Ridge beam at center peak
ridge_height = wall_height + beam_h + (depth / 2) * math.tan(math.radians(roof_pitch))
ridge_beam = Beam(
    length=width,
    width=beam_w,
    height=beam_h,
    name="ridge_beam",
    location=Location((0, depth / 2, ridge_height)),
)
model.add_element(ridge_beam)

# Generate rafters using RafterLayout
rafter_layout = RafterLayout(
    plate_front=beam_front,
    plate_back=beam_back,
    ridge=ridge_beam,
    rafter_width=rafter_w,
    rafter_height=rafter_h,
    pitch=roof_pitch,
    spacing=600,
    skip_ends=False,
    overhang=200,
)

for rafter, location in rafter_layout.generate():
    model.add_element(rafter)

# %%
show_object(model.get_compound(), name="timber_frame_shed")
