# %%
"""FEA test for 3-bent barn frame with girts AND braces.

This test extends the barn frame with:
- 3 bents (each with 2 posts + 1 cross beam) spaced along Y axis
- 2 girts running longitudinally connecting post tops along Y
- 4 knee braces per bent (2 per post) for lateral stability
"""

from pathlib import Path
from build123d import Part, Location, Axis
from ocp_vscode import reset_show, show

from timber_joints.alignment import (
    build_complete_bent,
    create_receiving_cut,
    create_brace_for_bent,
    create_brace_for_girt,
)
from timber_joints.beam import Beam
from timber_joints.tenon import Tenon
from timber_joints.utils import create_vertical_cut
from timber_joints.fea import TimberFrame, MemberType, show_fea_results, LoadBC

reset_show()

# Frame dimensions
POST_HEIGHT = 3000  # mm
POST_SECTION = 150  # mm
BEAM_LENGTH = 5000  # mm (cross beam span)
BENT_SPACING = 3000  # mm (spacing between bents along Y)
TENON_LENGTH = 60  # mm
SHOULDER_DEPTH = 20  # mm
HOUSING_DEPTH = 20  # mm
POST_TOP_EXTENSION = 300  # mm (mortise extends above beam)

# Girt dimensions
GIRT_LENGTH = 2 * BENT_SPACING + POST_SECTION  # Total length spanning 3 bents
GIRT_SECTION = POST_SECTION  # Same section as posts

# Brace dimensions
BRACE_SECTION = 100  # mm - 100x100 braces
BRACE_DIST_FROM_POST = 500  # mm from post (creates ~45° angle)


# %%
# Build the 3-bent barn frame

# Y positions of the three bents
bent_y_positions = [0, BENT_SPACING, 2 * BENT_SPACING]

# Tenon dimensions for post tops
POST_TENON_X = POST_SECTION * 2 / 3   # 2/3 of post section
POST_TENON_Y = POST_SECTION / 3       # 1/3 of post section

# Build the three bents
bents = []
for i, bent_y in enumerate(bent_y_positions):
    left_post, right_post, beam, _ = build_complete_bent(
        post_height=POST_HEIGHT,
        post_section=POST_SECTION,
        beam_length=BEAM_LENGTH,
        tenon_length=TENON_LENGTH,
        shoulder_depth=SHOULDER_DEPTH,
        housing_depth=HOUSING_DEPTH,
        post_top_extension=POST_TOP_EXTENSION,
    )
    
    # Add tenons to post tops
    left_post = create_vertical_cut(
        left_post, Tenon, at_top=True,
        tenon_width=POST_TENON_X, tenon_height=POST_TENON_Y,
        tenon_length=TENON_LENGTH,
    )
    right_post = create_vertical_cut(
        right_post, Tenon, at_top=True,
        tenon_width=POST_TENON_X, tenon_height=POST_TENON_Y,
        tenon_length=TENON_LENGTH,
    )
    
    # Create knee braces for this bent (before moving to Y position)
    brace_left = create_brace_for_bent(
        post=left_post, beam=beam,
        brace_section=BRACE_SECTION,
        distance_from_post=BRACE_DIST_FROM_POST,
        at_beam_start=True,
    ).shape
    brace_right = create_brace_for_bent(
        post=right_post, beam=beam,
        brace_section=BRACE_SECTION,
        distance_from_post=BRACE_DIST_FROM_POST,
        at_beam_start=False,
    ).shape
    
    # Move all parts to Y position
    left_post = left_post.move(Location((0, bent_y, 0)))
    right_post = right_post.move(Location((0, bent_y, 0)))
    beam = beam.move(Location((0, bent_y, 0)))
    brace_left = brace_left.move(Location((0, bent_y, 0)))
    brace_right = brace_right.move(Location((0, bent_y, 0)))
    
    bents.append({
        "left_post": left_post,
        "right_post": right_post,
        "beam": beam,
        "brace_left": brace_left,
        "brace_right": brace_right,
        "y": bent_y,
    })

# Get post X positions from first bent
first_bent_left = bents[0]["left_post"].bounding_box()
first_bent_right = bents[0]["right_post"].bounding_box()
left_post_x = (first_bent_left.min.X + first_bent_left.max.X) / 2
right_post_x = (first_bent_right.min.X + first_bent_right.max.X) / 2

# Get Z position for girts
girt_z = first_bent_left.max.Z - TENON_LENGTH - HOUSING_DEPTH

# Create girts
left_girt_beam = Beam(length=GIRT_LENGTH, width=GIRT_SECTION, height=GIRT_SECTION)
left_girt = left_girt_beam.shape.rotate(Axis.Z, 90)
left_girt_bbox = left_girt.bounding_box()
left_girt = left_girt.move(Location((
    left_post_x - (left_girt_bbox.min.X + left_girt_bbox.max.X) / 2,
    -left_girt_bbox.min.Y,
    girt_z - left_girt_bbox.min.Z,
)))

right_girt_beam = Beam(length=GIRT_LENGTH, width=GIRT_SECTION, height=GIRT_SECTION)
right_girt = right_girt_beam.shape.rotate(Axis.Z, 90)
right_girt_bbox = right_girt.bounding_box()
right_girt = right_girt.move(Location((
    right_post_x - (right_girt_bbox.min.X + right_girt_bbox.max.X) / 2,
    -right_girt_bbox.min.Y,
    girt_z - right_girt_bbox.min.Z,
)))

# Cut mortises in girts
for bent in bents:
    left_girt = create_receiving_cut(bent["left_post"], left_girt)
    right_girt = create_receiving_cut(bent["right_post"], right_girt)

# Create girt braces (braces running along Y, under girts)
# These provide longitudinal bracing
girt_braces = []

# Braces from bent 1 posts toward bent 2 (at_girt_start=False means toward +Y)
# Left side
girt_brace_left_1 = create_brace_for_girt(
    post=bents[0]["left_post"], girt=left_girt,
    brace_section=BRACE_SECTION,
    distance_from_post=BRACE_DIST_FROM_POST,
    at_girt_start=False,  # Toward +Y
).shape
girt_braces.append(("girt_brace_left_1", girt_brace_left_1))

# Right side
girt_brace_right_1 = create_brace_for_girt(
    post=bents[0]["right_post"], girt=right_girt,
    brace_section=BRACE_SECTION,
    distance_from_post=BRACE_DIST_FROM_POST,
    at_girt_start=False,
).shape
girt_braces.append(("girt_brace_right_1", girt_brace_right_1))

# Braces from bent 3 posts toward bent 2 (at_girt_start=True means toward -Y)
girt_brace_left_3 = create_brace_for_girt(
    post=bents[2]["left_post"], girt=left_girt,
    brace_section=BRACE_SECTION,
    distance_from_post=BRACE_DIST_FROM_POST,
    at_girt_start=True,  # Toward -Y
).shape
girt_braces.append(("girt_brace_left_3", girt_brace_left_3))

girt_brace_right_3 = create_brace_for_girt(
    post=bents[2]["right_post"], girt=right_girt,
    brace_section=BRACE_SECTION,
    distance_from_post=BRACE_DIST_FROM_POST,
    at_girt_start=True,
).shape
girt_braces.append(("girt_brace_right_3", girt_brace_right_3))

# Braces from bent 2 (middle) posts - both directions
# Toward bent 1 (-Y direction)
girt_brace_left_2a = create_brace_for_girt(
    post=bents[1]["left_post"], girt=left_girt,
    brace_section=BRACE_SECTION,
    distance_from_post=BRACE_DIST_FROM_POST,
    at_girt_start=True,  # Toward -Y (bent 1)
).shape
girt_braces.append(("girt_brace_left_2a", girt_brace_left_2a))

girt_brace_right_2a = create_brace_for_girt(
    post=bents[1]["right_post"], girt=right_girt,
    brace_section=BRACE_SECTION,
    distance_from_post=BRACE_DIST_FROM_POST,
    at_girt_start=True,  # Toward -Y (bent 1)
).shape
girt_braces.append(("girt_brace_right_2a", girt_brace_right_2a))

# Toward bent 3 (+Y direction)
girt_brace_left_2b = create_brace_for_girt(
    post=bents[1]["left_post"], girt=left_girt,
    brace_section=BRACE_SECTION,
    distance_from_post=BRACE_DIST_FROM_POST,
    at_girt_start=False,  # Toward +Y (bent 3)
).shape
girt_braces.append(("girt_brace_left_2b", girt_brace_left_2b))

girt_brace_right_2b = create_brace_for_girt(
    post=bents[1]["right_post"], girt=right_girt,
    brace_section=BRACE_SECTION,
    distance_from_post=BRACE_DIST_FROM_POST,
    at_girt_start=False,  # Toward +Y (bent 3)
).shape
girt_braces.append(("girt_brace_right_2b", girt_brace_right_2b))


# %%
# Visualize the geometry
print("Visualizing barn frame geometry with braces...")
all_parts = []
for i, bent in enumerate(bents):
    all_parts.append((bent["left_post"], f"Bent {i+1} Left Post"))
    all_parts.append((bent["right_post"], f"Bent {i+1} Right Post"))
    all_parts.append((bent["beam"], f"Bent {i+1} Beam"))
    all_parts.append((bent["brace_left"], f"Bent {i+1} Brace Left"))
    all_parts.append((bent["brace_right"], f"Bent {i+1} Brace Right"))
    
all_parts.append((left_girt, "Left Girt"))
all_parts.append((right_girt, "Right Girt"))

for name, brace in girt_braces:
    all_parts.append((brace, name))

from ocp_vscode import show_object
for part, part_name in all_parts:
    if "brace" in part_name.lower():
        show_object(part, name=part_name, options={"color": "orange"})
    elif "Girt" in part_name:
        show_object(part, name=part_name, options={"color": "burlywood", "alpha": 0.3})
    elif "Beam" in part_name:
        show_object(part, name=part_name, options={"color": "burlywood", "alpha": 0.3})
    elif "Post" in part_name:
        show_object(part, name=part_name, options={"color": "sienna", "alpha": 0.3})
    else:
        show_object(part, name=part_name)

print("Geometry rendered. Check the visualization.")
print(f"Total parts: {len(all_parts)}")
print(f"  - Posts: 6")
print(f"  - Beams: 3")
print(f"  - Girts: 2")
print(f"  - Bent knee braces: 6 (2 per bent)")
print(f"  - Girt braces: {len(girt_braces)}")


# %%
# FEA Analysis
frame = TimberFrame()

# Add bent members
for i, bent in enumerate(bents):
    frame.add_member(f"bent{i+1}_left_post", bent["left_post"])
    frame.add_member(f"bent{i+1}_right_post", bent["right_post"])
    frame.add_member(f"bent{i+1}_beam", bent["beam"])
    # Add braces with explicit BRACE type
    frame.add_member(f"bent{i+1}_brace_left", bent["brace_left"], MemberType.BRACE)
    frame.add_member(f"bent{i+1}_brace_right", bent["brace_right"], MemberType.BRACE)

# Add girts
frame.add_member("left_girt", left_girt)
frame.add_member("right_girt", right_girt)

# Add girt braces
for name, brace in girt_braces:
    frame.add_member(name, brace, MemberType.BRACE)

output_dir = Path(__file__).parent / "fea_barn_braced_output"

print("=" * 60)
print("3-BENT BARN FRAME WITH BRACES - FEA ANALYSIS")
print("=" * 60)
print(f"Frame configuration:")
print(f"  - 3 bents spaced {BENT_SPACING}mm apart")
print(f"  - Posts: {POST_HEIGHT}mm tall, {POST_SECTION}mm section")
print(f"  - Cross beams: {BEAM_LENGTH}mm span")
print(f"  - Girts: {GIRT_LENGTH}mm long, {GIRT_SECTION}mm section")
print(f"  - Knee braces: {BRACE_SECTION}mm section, {BRACE_DIST_FROM_POST}mm from post")
print(f"  - Total members: {len(frame.members)}")
print()

# Additional loads
right_girt_bbox = right_girt.bounding_box()
right_girt_y_quarter = right_girt_bbox.min.Y + (right_girt_bbox.max.Y - right_girt_bbox.min.Y) * 0.25
right_girt_top_z = right_girt_bbox.max.Z

def right_girt_load_filter(nid, x, y, z, part, mesh):
    return (part == "right_girt" and 
            abs(y - right_girt_y_quarter) < 70.0 and 
            abs(z - right_girt_top_z) < 35.0)

left_girt_bbox = left_girt.bounding_box()
left_girt_y_threequarter = left_girt_bbox.min.Y + (left_girt_bbox.max.Y - left_girt_bbox.min.Y) * 0.75
left_girt_right_x = left_girt_bbox.max.X

def left_girt_load_filter(nid, x, y, z, part, mesh):
    return (part == "left_girt" and 
            abs(y - left_girt_y_threequarter) < 70.0 and 
            abs(x - left_girt_right_x) < 35.0)

additional_loads = [
    LoadBC("right_girt_load", right_girt_load_filter, dof=3, total_load=-1000.0),  # 100 kg down
    LoadBC("left_girt_load", left_girt_load_filter, dof=1, total_load=500.0),      # 50kg sideways +X
]

print(f"Additional loads:")
print(f"  - Right girt at Y={right_girt_y_quarter:.1f}mm: 100 kg downward")
print(f"  - Left girt at Y={left_girt_y_threequarter:.1f}mm: 50 kg sideways (+X)")
print(f"  - Self-weight: automatic")
print()

result = frame.analyze(
    additional_loads=additional_loads,
    output_dir=output_dir,
    mesh_size=100.0,  # Coarser mesh for braces
    mesh_size_fine=50.0,
)

print("\n" + "=" * 60)
print("ANALYSIS SUMMARY")
print("=" * 60)
print(f"Success: {result.success}")
print(f"Mesh: {result.num_nodes} nodes, {result.num_elements} elements")

if result.success:
    print(f"\nDeflection Results:")
    print(f"  Max total: {result.fea_results.max_displacement:.4f} mm")
    print(f"  Max Z: {result.fea_results.max_uz:.4f} mm")
    
    limit = BEAM_LENGTH / 300  # L/300
    status = "PASS ✓" if abs(result.fea_results.max_uz) < limit else "FAIL ✗"
    print(f"  Limit (L/300): {limit:.2f} mm")
    print(f"  Status: {status}")

print("=" * 60)


# %%
# Visualize FEA results
if result.success:
    original_shapes = []
    for i, bent in enumerate(bents):
        original_shapes.append((bent["left_post"], f"Bent {i+1} LP", "sienna"))
        original_shapes.append((bent["right_post"], f"Bent {i+1} RP", "sienna"))
        original_shapes.append((bent["beam"], f"Bent {i+1} Beam", "burlywood"))
        original_shapes.append((bent["brace_left"], f"Bent {i+1} BL", "orange"))
        original_shapes.append((bent["brace_right"], f"Bent {i+1} BR", "orange"))
    
    original_shapes.append((left_girt, "Left Girt", "peru"))
    original_shapes.append((right_girt, "Right Girt", "peru"))
    
    for name, brace in girt_braces:
        original_shapes.append((brace, name, "orange"))
    
    show_fea_results(
        mesh_file=str(output_dir / "mesh.inp"),
        frd_file=str(output_dir / "analysis.frd"),
        scale=60.0,
        original_shapes=original_shapes,
        deformed_color="red",
        original_alpha=0.3,
    )
