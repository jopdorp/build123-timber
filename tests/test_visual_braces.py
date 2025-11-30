"""Visual test for brace alignment functions."""

import sys
sys.path.insert(0, "src")

from build123d import Part, Axis, Location, Box, export_step
from timber_joints.beam import Beam
from timber_joints.alignment import (
    make_post_vertical,
    align_beam_in_post,
    create_brace_for_bent,
    create_brace_for_girt,
    calculate_brace_angle,
    calculate_brace_length,
    build_complete_bent,
)
from pathlib import Path
from ocp_vscode import reset_show, show_object

reset_show()

# Create output directory
output_dir = Path("brace_test_output")
output_dir.mkdir(exist_ok=True)


def test_brace_calculations():
    """Test the brace angle and length calculations."""
    # 45 degree brace (equal horizontal and vertical)
    angle = calculate_brace_angle(100, 100)
    length = calculate_brace_length(100, 100)
    print(f"45° brace: angle={angle:.1f}°, length={length:.1f}mm")
    assert abs(angle - 45.0) < 0.01
    assert abs(length - 141.42) < 0.1
    
    # 60 degree brace (more vertical)
    angle = calculate_brace_angle(100, 173.2)  # tan(60°) ≈ 1.732
    print(f"60° brace: angle={angle:.1f}°")
    assert abs(angle - 60.0) < 0.1
    
    # 30 degree brace (more horizontal)
    angle = calculate_brace_angle(173.2, 100)
    print(f"30° brace: angle={angle:.1f}°")
    assert abs(angle - 30.0) < 0.1
    
    print("✓ Brace calculations correct")


def test_single_brace():
    """Test creating a single brace between a post and beam."""
    # Create a simple post and beam
    post_height = 2500
    post_section = 150
    beam_length = 3000
    beam_section = 150
    
    # Create shapes
    post = Beam(length=post_height, width=post_section, height=post_section)
    beam = Beam(length=beam_length, width=beam_section, height=beam_section)
    
    # Make post vertical and position beam
    vertical_post = make_post_vertical(post.shape)
    
    # Position beam on top of post (dropping into it)
    drop_depth = beam_section
    positioned_beam, _, _ = align_beam_in_post(
        beam=beam.shape,
        post=vertical_post,
        drop_depth=drop_depth,
        at_start=True,
        move_post=False,
    )
    
    # Create a brace at the left post (using default penetration = corner touches beam bottom)
    brace_result = create_brace_for_bent(
        post=vertical_post,
        beam=positioned_beam,
        brace_section=100,  # 100x100mm brace
        distance_from_post=400,  # 400mm from post (creates ~45° brace)
        at_beam_start=True,
    )
    brace = brace_result.shape
    print(f"Brace angle: {brace_result.angle:.1f}°")
    
    # Export for visualization
    export_step(vertical_post, str(output_dir / "post.step"))
    export_step(positioned_beam, str(output_dir / "beam.step"))
    export_step(brace, str(output_dir / "brace.step"))
    
    # Verify brace position
    brace_bbox = brace.bounding_box()
    beam_bbox = positioned_beam.bounding_box()
    post_bbox = vertical_post.bounding_box()
    
    print(f"Post bbox: X=[{post_bbox.min.X:.0f}, {post_bbox.max.X:.0f}], Z=[{post_bbox.min.Z:.0f}, {post_bbox.max.Z:.0f}]")
    print(f"Beam bbox: X=[{beam_bbox.min.X:.0f}, {beam_bbox.max.X:.0f}], Z=[{beam_bbox.min.Z:.0f}, {beam_bbox.max.Z:.0f}]")
    print(f"Brace bbox: X=[{brace_bbox.min.X:.0f}, {brace_bbox.max.X:.0f}], Z=[{brace_bbox.min.Z:.0f}, {brace_bbox.max.Z:.0f}]")
    
    # Brace top should penetrate into beam (lower corner at beam bottom)
    assert brace_bbox.max.Z > beam_bbox.min.Z, "Brace should penetrate into beam"
    
    # Brace should extend from post region toward beam
    assert brace_bbox.min.X >= post_bbox.min.X - 10, "Brace should start near post"
    
    print("✓ Single brace created and positioned correctly")


def test_bent_with_braces():
    """Test creating a complete bent with braces on both posts."""
    # Build a bent
    left_post, right_post, beam, _ = build_complete_bent(
        post_height=3000,
        post_section=150,
        beam_length=5000,
        beam_section=150,
        tenon_length=60,
        shoulder_depth=20,
        housing_depth=20,
        post_top_extension=300,
    )
    
    # Create braces on both ends (using default penetration = corner touches beam bottom)
    brace_left_result = create_brace_for_bent(
        post=left_post,
        beam=beam,
        brace_section=100,
        distance_from_post=500,
        at_beam_start=True,
    )
    
    brace_right_result = create_brace_for_bent(
        post=right_post,
        beam=beam,
        brace_section=100,
        distance_from_post=500,
        at_beam_start=False,
    )
    
    brace_left = brace_left_result.shape
    brace_right = brace_right_result.shape
    
    print(f"Left brace angle: {brace_left_result.angle:.1f}°, at_beam_end: {brace_left_result.at_beam_end}")
    print(f"Right brace angle: {brace_right_result.angle:.1f}°, at_beam_end: {brace_right_result.at_beam_end}")
    
    # The braces already have tenons applied by create_brace_for_bent
    # Just use the shapes directly
    brace_left = brace_left_result.shape
    brace_right = brace_right_result.shape
    
    # Show in viewer
    show_object(left_post, name="Left Post", options={"color": "sienna", "alpha": 0.3})
    show_object(right_post, name="Right Post", options={"color": "sienna", "alpha": 0.3})
    show_object(beam, name="Beam", options={"color": "burlywood", "alpha": 0.3})
    show_object(brace_left, name="Left Brace", options={"color": "orange"})
    show_object(brace_right, name="Right Brace", options={"color": "orange"})
    
    # Export all parts
    export_step(left_post, str(output_dir / "bent_left_post.step"))
    export_step(right_post, str(output_dir / "bent_right_post.step"))
    export_step(beam, str(output_dir / "bent_beam.step"))
    export_step(brace_left, str(output_dir / "bent_brace_left.step"))
    export_step(brace_right, str(output_dir / "bent_brace_right.step"))
    
    print("✓ Bent with braces exported to", output_dir)
    
    # Skip position verification for now - focus on visual check
    print("✓ Bent brace positions - check OCP viewer")


def test_girt_braces():
    """Test creating braces for girts (Y-direction horizontal members)."""
    # Create a post and a girt running along Y
    post_height = 2500
    post_section = 150
    girt_length = 3000
    girt_section = 150
    
    # Create shapes
    post = Beam(length=post_height, width=post_section, height=post_section)
    girt = Beam(length=girt_length, width=girt_section, height=girt_section)
    
    # Make post vertical
    vertical_post = make_post_vertical(post.shape)
    
    # Position girt along Y axis at the top of the post
    # First rotate girt to run along Y, then position it
    girt_along_y = girt.shape.rotate(Axis.Z, 90)  # Now runs along Y
    
    # Position girt at top of post, spanning in Y direction
    post_bbox = vertical_post.bounding_box()
    girt_bbox = girt_along_y.bounding_box()
    
    # Position girt so it's centered on post in X and sits at post top
    drop_depth = girt_section  # Drop into post
    target_x = (post_bbox.min.X + post_bbox.max.X) / 2 - (girt_bbox.min.X + girt_bbox.max.X) / 2
    target_z = post_bbox.max.Z - drop_depth - girt_bbox.min.Z
    # Offset in Y so post is at girt end  
    target_y = post_bbox.max.Y - girt_bbox.min.Y
    
    positioned_girt = girt_along_y.move(Location((target_x, target_y, target_z)))
    
    # Create a brace from post to girt (toward +Y direction, using default penetration)
    brace_result = create_brace_for_girt(
        post=vertical_post,
        girt=positioned_girt,
        brace_section=100,
        distance_from_post=400,
        at_girt_start=False,  # Toward +Y (away from post on +Y side)
    )
    brace = brace_result.shape
    print(f"Girt brace angle: {brace_result.angle:.1f}°")
    
    # Export for visualization
    export_step(vertical_post, str(output_dir / "girt_post.step"))
    export_step(positioned_girt, str(output_dir / "girt.step"))
    export_step(brace, str(output_dir / "girt_brace.step"))
    
    # Verify brace position
    brace_bbox = brace.bounding_box()
    girt_bbox = positioned_girt.bounding_box()
    
    print(f"Post bbox: Y=[{post_bbox.min.Y:.0f}, {post_bbox.max.Y:.0f}], Z=[{post_bbox.min.Z:.0f}, {post_bbox.max.Z:.0f}]")
    print(f"Girt bbox: Y=[{girt_bbox.min.Y:.0f}, {girt_bbox.max.Y:.0f}], Z=[{girt_bbox.min.Z:.0f}, {girt_bbox.max.Z:.0f}]")
    print(f"Girt brace bbox: Y=[{brace_bbox.min.Y:.0f}, {brace_bbox.max.Y:.0f}], Z=[{brace_bbox.min.Z:.0f}, {brace_bbox.max.Z:.0f}]")
    
    show_object(vertical_post, name="Girt Post", options={"color": "sienna", "alpha": 0.3})
    show_object(positioned_girt, name="Girt", options={"color": "burlywood", "alpha": 0.3})
    show_object(brace, name="Girt Brace", options={"color": "orange", "alpha": 0.6})
    # Brace should penetrate into girt (tenon goes into the girt)
    assert brace_bbox.max.Z > girt_bbox.min.Z, "Girt brace should penetrate into girt"
    
    print("✓ Girt brace created and positioned correctly")


if __name__ == "__main__":
    # Only run the bent with braces test for visual verification
    test_bent_with_braces()
    test_girt_braces()
    print("\n✅ Visual brace test complete - check the OCP viewer!")
