# %%
"""FEA test for 3-bent barn frame with girts.

This test creates a barn frame structure with:
- 3 bents (each with 2 posts + 1 cross beam) spaced along Y axis
- 2 girts running longitudinally connecting post tops along Y
- Posts have tenons going UP into girts (girts have mortises)
"""

from pathlib import Path
from build123d import Part, Location, Axis
from ocp_vscode import reset_show, show

from timber_joints.alignment import build_complete_bent, create_receiving_cut
from timber_joints.beam import Beam
from timber_joints.tenon import Tenon
from timber_joints.utils import create_vertical_cut
from timber_joints.fea import TimberFrame, show_fea_results, LoadBC

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


# %%
# Build the 3-bent barn frame

# Y positions of the three bents
bent_y_positions = [0, BENT_SPACING, 2 * BENT_SPACING]

# Tenon dimensions for post tops
# When post is vertical, tenon goes up into girt which runs along Y
# tenon_width = dimension along X (narrow), tenon_height = dimension along Y (wide)
POST_TENON_X = POST_SECTION * 2 / 3   # 2/3 of post section (wide dimension, along girt)
POST_TENON_Y = POST_SECTION / 3       # 1/3 of post section (narrow dimension)

# Build the three bents using existing build_complete_bent
# Then add tenons to post tops using create_vertical_cut
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
    
    # Add tenons to post tops using create_vertical_cut
    # tenon_width maps to X, tenon_height maps to Y when rotated back vertical
    left_post = create_vertical_cut(
        left_post,
        Tenon,
        at_top=True,
        tenon_width=POST_TENON_X,
        tenon_height=POST_TENON_Y,
        tenon_length=TENON_LENGTH,
    )
    right_post = create_vertical_cut(
        right_post,
        Tenon,
        at_top=True,
        tenon_width=POST_TENON_X,
        tenon_height=POST_TENON_Y,
        tenon_length=TENON_LENGTH,
    )
    
    # Move bent to its Y position
    left_post = left_post.move(Location((0, bent_y, 0)))
    right_post = right_post.move(Location((0, bent_y, 0)))
    beam = beam.move(Location((0, bent_y, 0)))
    
    bents.append({
        "left_post": left_post,
        "right_post": right_post,
        "beam": beam,
        "y": bent_y,
    })

# Get post X positions from first bent (they're the same for all bents)
first_bent_left = bents[0]["left_post"].bounding_box()
first_bent_right = bents[0]["right_post"].bounding_box()
left_post_x = (first_bent_left.min.X + first_bent_left.max.X) / 2
right_post_x = (first_bent_right.min.X + first_bent_right.max.X) / 2

# Get Z position for girts (on top of posts, minus tenon length, minus housing depth)
girt_z = first_bent_left.max.Z - TENON_LENGTH - HOUSING_DEPTH

# Create left girt (connecting all left posts) - plain beam rotated to run along Y
left_girt_beam = Beam(length=GIRT_LENGTH, width=GIRT_SECTION, height=GIRT_SECTION)
left_girt = left_girt_beam.shape.rotate(Axis.Z, 90)
# Position: center on left_post_x, start at Y=0, at girt_z
left_girt_bbox = left_girt.bounding_box()
left_girt = left_girt.move(Location((
    left_post_x - (left_girt_bbox.min.X + left_girt_bbox.max.X) / 2,
    -left_girt_bbox.min.Y,  # Start at Y=0
    girt_z - left_girt_bbox.min.Z,
)))

# Create right girt (connecting all right posts)
right_girt_beam = Beam(length=GIRT_LENGTH, width=GIRT_SECTION, height=GIRT_SECTION)
right_girt = right_girt_beam.shape.rotate(Axis.Z, 90)
right_girt_bbox = right_girt.bounding_box()
right_girt = right_girt.move(Location((
    right_post_x - (right_girt_bbox.min.X + right_girt_bbox.max.X) / 2,
    -right_girt_bbox.min.Y,
    girt_z - right_girt_bbox.min.Z,
)))

# Cut mortises in girts by subtracting each post's tenon
for bent in bents:
    left_girt = create_receiving_cut(bent["left_post"], left_girt)
    right_girt = create_receiving_cut(bent["right_post"], right_girt)

# Show the geometry
print("Visualizing barn frame geometry...")
all_parts = []
for i, bent in enumerate(bents):
    all_parts.append((bent["left_post"], f"Bent {i+1} Left Post"))
    all_parts.append((bent["right_post"], f"Bent {i+1} Right Post"))
    all_parts.append((bent["beam"], f"Bent {i+1} Beam"))
    
all_parts.append((left_girt, "Left Girt"))
all_parts.append((right_girt, "Right Girt"))

# Show all parts together using show_object
from ocp_vscode import show_object
for part, part_name in all_parts:
    if "Girt" in part_name:
        show_object(part, name=part_name, options={"alpha": 0.5})
    else:
        show_object(part, name=part_name)

print("Geometry rendered. Check the visualization.")
print(f"Total parts: {len(all_parts)}")


# %%
# FEA Analysis
frame = TimberFrame()

# Add bent members
for i, bent in enumerate(bents):
    frame.add_member(f"bent{i+1}_left_post", bent["left_post"])
    frame.add_member(f"bent{i+1}_right_post", bent["right_post"])
    frame.add_member(f"bent{i+1}_beam", bent["beam"])

# Add girts
frame.add_member("left_girt", left_girt)
frame.add_member("right_girt", right_girt)

# Analyze
output_dir = Path(__file__).parent / "fea_barn_frame_output"

print("=" * 60)
print("3-BENT BARN FRAME FEA ANALYSIS")
print("=" * 60)
print(f"Frame configuration:")
print(f"  - 3 bents spaced {BENT_SPACING}mm apart")
print(f"  - Posts: {POST_HEIGHT}mm tall, {POST_SECTION}mm section")
print(f"  - Cross beams: {BEAM_LENGTH}mm span")
print(f"  - Girts: {GIRT_LENGTH}mm long, {GIRT_SECTION}mm section")
print(f"  - Total members: {len(frame.members)}")
print()

# Define additional loads on girts
# Right girt: 1/4 along Y (Y=1537.5mm), 0.5 tonne downward = 500kg * 9.81 = 4905 N
right_girt_bbox = right_girt.bounding_box()
right_girt_y_quarter = right_girt_bbox.min.Y + (right_girt_bbox.max.Y - right_girt_bbox.min.Y) * 0.25
right_girt_top_z = right_girt_bbox.max.Z
right_girt_center_x = (right_girt_bbox.min.X + right_girt_bbox.max.X) / 2

def right_girt_load_filter(nid, x, y, z, part, mesh):
    return (part == "right_girt" and 
            abs(y - right_girt_y_quarter) < 70.0 and 
            abs(z - right_girt_top_z) < 35.0)

# Left girt: 3/4 along Y (Y=4612.5mm), 100kg sideways (positive X) = 100kg * 9.81 = 981 N
left_girt_bbox = left_girt.bounding_box()
left_girt_y_threequarter = left_girt_bbox.min.Y + (left_girt_bbox.max.Y - left_girt_bbox.min.Y) * 0.75
left_girt_center_z = (left_girt_bbox.min.Z + left_girt_bbox.max.Z) / 2
left_girt_right_x = left_girt_bbox.max.X  # Apply on right side of left girt

def left_girt_load_filter(nid, x, y, z, part, mesh):
    return (part == "left_girt" and 
            abs(y - left_girt_y_threequarter) < 70.0 and 
            abs(x - left_girt_right_x) < 35.0)

additional_loads = [
    LoadBC("right_girt_load", right_girt_load_filter, dof=3, total_load=-4905.0),  # 0.5 tonne down
    LoadBC("left_girt_load", left_girt_load_filter, dof=1, total_load=981.0),      # 100kg sideways +X
]

print(f"Additional loads:")
print(f"  - Right girt at Y={right_girt_y_quarter:.1f}mm: 500 kg downward")
print(f"  - Left girt at Y={left_girt_y_threequarter:.1f}mm: 100 kg sideways (+X)")
print()

result = frame.analyze(
    load=-10000.0,  # 10 kN downward (applied to center beam)
    additional_loads=additional_loads,
    output_dir=output_dir,
    mesh_size=70.0,        # Coarser default mesh
    mesh_size_fine=30.0,   # Finer mesh at joints
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
    
    # Serviceability check (based on center beam span)
    limit = BEAM_LENGTH / 300  # L/300
    status = "PASS ✓" if abs(result.fea_results.max_uz) < limit else "FAIL ✗"
    print(f"  Limit (L/300): {limit:.2f} mm")
    print(f"  Status: {status}")

print("=" * 60)


# Visualize FEA results

if result.success:
    # Build list of original shapes for visualization
    original_shapes = []
    for i, bent in enumerate(bents):
        original_shapes.append((bent["left_post"], f"Bent {i+1} LP", "sienna"))
        original_shapes.append((bent["right_post"], f"Bent {i+1} RP", "sienna"))
        original_shapes.append((bent["beam"], f"Bent {i+1} Beam", "burlywood"))
    
    original_shapes.append((left_girt, "Left Girt", "peru"))
    original_shapes.append((right_girt, "Right Girt", "peru"))
    
    show_fea_results(
        mesh_file=str(output_dir / "mesh.inp"),
        frd_file=str(output_dir / "analysis.frd"),
        scale=5.0,
        original_shapes=original_shapes,
        deformed_color="red",
        original_alpha=0.3,
    )
