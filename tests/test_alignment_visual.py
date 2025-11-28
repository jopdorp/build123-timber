# %%
"""Visual tests for timber member alignment.

Run each cell to visualize alignment scenarios.
"""
from ocp_vscode import show_object, set_defaults, Camera

set_defaults(
    reset_camera=Camera.CENTER,
    grid=(True, True, True),
)

# %%
# 1. Beam on top of Post - member alignment only (no joint cuts)
# Expected: Beam end sits horizontally on top of vertical post

from ocp_vscode import show_object
from test_alignment import create_beam_on_post_aligned

post, beam = create_beam_on_post_aligned()

post_bbox = post.global_shape.bounding_box()
beam_bbox = beam.global_shape.bounding_box()

print("=== 1. Beam on top of Post ===")
print(f"Post bbox: X={post_bbox.min.X:.0f}-{post_bbox.max.X:.0f}, Y={post_bbox.min.Y:.0f}-{post_bbox.max.Y:.0f}, Z={post_bbox.min.Z:.0f}-{post_bbox.max.Z:.0f}")
print(f"Beam bbox: X={beam_bbox.min.X:.0f}-{beam_bbox.max.X:.0f}, Y={beam_bbox.min.Y:.0f}-{beam_bbox.max.Y:.0f}, Z={beam_bbox.min.Z:.0f}-{beam_bbox.max.Z:.0f}")
print(f"Beam bottom Z ({beam_bbox.min.Z:.0f}) == Post top Z ({post_bbox.max.Z:.0f}): {abs(beam_bbox.min.Z - post_bbox.max.Z) < 1}")

show_object(post.global_shape, name="Post", options={"color": "sienna"})
show_object(beam.global_shape, name="Beam on top", options={"color": "burlywood"})

# %%
# 2. Beam IN Post with Tongue-and-Fork joint (through mortise-tenon)
# Expected: Beam dropped INTO post, fork (through mortise) in post, tongue on beam

from ocp_vscode import show_object
from build123d import Location
from test_alignment import create_beam_in_post_with_tongue_and_fork

post2, beam2, joint = create_beam_in_post_with_tongue_and_fork()

post2_bbox = post2.global_shape.bounding_box()
beam2_bbox = beam2.global_shape.bounding_box()

print("=== 2. Beam IN Post with Tongue-and-Fork ===")
print(f"Post bbox: X={post2_bbox.min.X:.0f}-{post2_bbox.max.X:.0f}, Y={post2_bbox.min.Y:.0f}-{post2_bbox.max.Y:.0f}, Z={post2_bbox.min.Z:.0f}-{post2_bbox.max.Z:.0f}")
print(f"Beam bbox: X={beam2_bbox.min.X:.0f}-{beam2_bbox.max.X:.0f}, Y={beam2_bbox.min.Y:.0f}-{beam2_bbox.max.Y:.0f}, Z={beam2_bbox.min.Z:.0f}-{beam2_bbox.max.Z:.0f}")
print(f"Beam bottom Z ({beam2_bbox.min.Z:.0f}) inside post (should be {post2_bbox.max.Z - beam2.height:.0f})")
print(f"Tenon: {joint.tenon_length}L x {joint.tenon_width:.1f}W x {joint.tenon_height:.1f}H (through={joint.through_tenon})")
print(f"Post volume removed: {post2.blank.volume - post2.shape.volume:.0f}")
print(f"Beam volume removed: {beam2.blank.volume - beam2.shape.volume:.0f}")

show_object(post2.global_shape.moved(Location((0, 300, 0))), name="Post2 with fork", options={"color": "sienna"})
show_object(beam2.global_shape.moved(Location((0, 300, 0))), name="Beam2 with tongue", options={"color": "burlywood"})

# %%
