"""Alignment utilities for positioning timber joints."""

from build123d import Location, Axis, Part


def _calculate_beam_position(
    beam: Part,
    post: Part,
    drop_depth: float,
    at_start: bool,
) -> tuple[float, float, float]:
    """Calculate where beam should be positioned relative to post at origin.
    
    Args:
        beam: The beam Part
        post: The vertical post Part (at origin)
        drop_depth: How far the beam drops into the post
        at_start: If True, joint at beam start; if False, at beam end
    
    Returns:
        (target_x, target_y, target_z) for beam's bbox.min
    """
    beam_bbox = beam.bounding_box()
    post_bbox = post.bounding_box()
    
    # Get actual dimensions from bounding boxes
    beam_length = beam_bbox.max.X - beam_bbox.min.X
    beam_width = beam_bbox.max.Y - beam_bbox.min.Y
    post_width = post_bbox.max.Y - post_bbox.min.Y
    
    if at_start:
        # Beam start at post - beam extends in +X direction from post's inner edge
        target_x = post_bbox.min.X
    else:
        # Beam end at post - beam's max.X should align with post's inner edge (max.X)
        # So beam's min.X = post's max.X - beam_length
        target_x = post_bbox.max.X - beam_length
    
    # Center beam on post width
    target_y = post_bbox.min.Y + (post_width - beam_width) / 2
    
    # Beam drops into post by drop_depth from post top
    target_z = post_bbox.max.Z - drop_depth
    
    return target_x, target_y, target_z


def _calculate_post_position(
    beam: Part,
    post: Part,
    drop_depth: float,
    at_start: bool,
) -> tuple[float, float, float]:
    """Calculate where post should be positioned relative to beam at origin.
    
    The post is positioned so the beam end goes INTO the post (overlapping).
    
    Args:
        beam: The beam Part (at origin)
        post: The vertical post Part
        drop_depth: How far the beam drops into the post
        at_start: If True, joint at beam start; if False, at beam end
    
    Returns:
        (target_x, target_y, target_z) for post's bbox.min
    """
    beam_bbox = beam.bounding_box()
    post_bbox = post.bounding_box()
    
    # Get actual dimensions from bounding boxes
    beam_width = beam_bbox.max.Y - beam_bbox.min.Y
    post_x_extent = post_bbox.max.X - post_bbox.min.X  # Post's X dimension (depth/thickness)
    post_width = post_bbox.max.Y - post_bbox.min.Y
    post_z_extent = post_bbox.max.Z - post_bbox.min.Z  # Post's Z dimension (height when vertical)
    
    if at_start:
        # Post at beam start - beam's min.X should be INSIDE the post
        # Post's min.X should be at beam's min.X (beam start enters post from post's min.X side)
        target_x = beam_bbox.min.X
    else:
        # Post at beam end - beam's max.X should be INSIDE the post
        # Post's max.X should be at beam's max.X, so post's min.X = beam's max.X - post_x_extent
        target_x = beam_bbox.max.X - post_x_extent
    
    # Center post on beam width
    target_y = beam_bbox.min.Y + (beam_width - post_width) / 2
    
    # Post top (max.Z) should be at beam's min.Z + drop_depth
    # Post's min.Z = (beam.min.Z + drop_depth) - post_z_extent
    target_z = beam_bbox.min.Z + drop_depth - post_z_extent
    
    return target_x, target_y, target_z


def _move_shape_to_position(shape: Part, target_x: float, target_y: float, target_z: float) -> tuple[Part, Location]:
    """Move a shape so its bounding box min aligns with target coordinates.
    
    Args:
        shape: The Part to move
        target_x, target_y, target_z: Target coordinates for bbox.min
    
    Returns:
        (moved_shape, location)
    """
    bbox = shape.bounding_box()
    location = Location((
        target_x - bbox.min.X,
        target_y - bbox.min.Y,
        target_z - bbox.min.Z
    ))
    return shape.move(location), location


def align_beam_on_post(
    beam: Part,
    post: Part,
) -> tuple[Part, Location]:
    """Align a beam on top of a post.
    
    The beam is positioned horizontally on top of the vertical post,
    with beam start at post edge.
    
    Args:
        beam: The beam Part (with any joint cuts applied)
        post: The post Part (already made vertical)
    
    Returns:
        (positioned_beam, beam_location)
    """
    beam_bbox = beam.bounding_box()
    post_bbox = post.bounding_box()
    
    # Get actual dimensions from bounding boxes
    beam_width = beam_bbox.max.Y - beam_bbox.min.Y
    post_width = post_bbox.max.Y - post_bbox.min.Y
    
    # Beam sits on top of post, starting at post edge
    beam_x = post_bbox.min.X
    beam_y = post_bbox.min.Y + (post_width - beam_width) / 2
    beam_z = post_bbox.max.Z
    
    return _move_shape_to_position(beam, beam_x, beam_y, beam_z)


def align_beam_in_post(
    beam: Part,
    post: Part,
    drop_depth: float,
    at_start: bool = True,
    move_post: bool = False,
) -> tuple[Part, Part, Location]:
    """Align a beam dropped INTO a post (for tongue-and-fork style joints).
    
    The beam is positioned so it drops into the post by drop_depth.
    
    Args:
        beam: The beam Part (with any joint cuts applied)
        post: The post Part (already made vertical)
        drop_depth: How far the beam drops into the post
        at_start: If True, joint at beam start; if False, at beam end
        move_post: If True, move post to beam; if False, move beam to post
    
    Returns:
        (positioned_beam, positioned_post, location)
    """
    if move_post:
        # Keep beam at origin, move post to beam
        target_x, target_y, target_z = _calculate_post_position(beam, post, drop_depth, at_start)
        positioned_post, post_location = _move_shape_to_position(post, target_x, target_y, target_z)
        return beam, positioned_post, post_location
    else:
        # Keep post at origin, move beam to post
        target_x, target_y, target_z = _calculate_beam_position(beam, post, drop_depth, at_start)
        positioned_beam, beam_location = _move_shape_to_position(beam, target_x, target_y, target_z)
        return positioned_beam, post, beam_location


def make_post_vertical(post_shape: Part) -> Part:
    """Rotate a post to be vertical (length along Z axis).
    
    Args:
        post_shape: The post Part in default orientation (length along X)
    
    Returns:
        The post rotated to be vertical
    """
    return post_shape.rotate(Axis.Y, -90)


def create_receiving_cut(
    positioned_insert: Part,
    receiving_shape: Part,
) -> Part:
    """Subtract the insert from the receiving shape to create a mortise/pocket."""
    return receiving_shape - positioned_insert


def position_for_blind_mortise(
    beam: Part,
    post: Part,
    tenon_length: float,
    housing_depth: float = 0,
    post_top_extension: float = 0,
    at_start: bool = True,
    move_post: bool = False,
) -> tuple[Part, Part]:
    """Position beam and post for cutting a blind mortise.
    
    Offsets the beam or post to create a mortise that doesn't go all the way through.
    
    Args:
        beam: The beam Part (already positioned)
        post: The post Part (already positioned)
        tenon_length: Length of the tenon projection
        housing_depth: Material to leave at far side of post (default 0)
        post_top_extension: Extend cut above beam for housing (default 0)
        at_start: If True, tenon at beam start; if False, at beam end
        move_post: If True, move post instead of beam
    
    Returns:
        (beam_for_cut, post_for_cut) - one moved for mortise cut, other unchanged
    """
    post_bbox = post.bounding_box()
    
    # Calculate post's X extent (thickness)
    post_x_extent = post_bbox.max.X - post_bbox.min.X
    blind_offset = post_x_extent - housing_depth - tenon_length
    
    # Determine which direction to offset to create blind mortise
    if at_start:
        # Tenon at beam start - offset in -X direction (into post)
        x_offset = blind_offset
    else:
        # Tenon at beam end - offset in +X direction (into post)
        x_offset = -blind_offset
    
    if move_post:
        # Move post instead of beam (reverse both offsets)
        # Post moves in opposite direction to achieve same relative cut position
        post_for_cut = post.move(Location((-x_offset, 0, post_top_extension)))
        return beam, post_for_cut
    else:
        # Move beam (default)
        beam_for_cut = beam.move(Location((x_offset, 0, -post_top_extension)))
        return beam_for_cut, post


def build_complete_bent(
    post_height: float = 3000,
    post_section: float = 150,
    beam_length: float = 5000,
    beam_section: float = None,
    tenon_length: float = 60,
    shoulder_depth: float = 20,
    housing_depth: float = 20,
    post_top_extension: float = 300,
) -> tuple[Part, Part, Part, "Beam"]:
    """Build a complete bent with shouldered tenon joints.
    
    Creates two posts with a beam connected by shouldered tenon joints.
    The beam has tenons on both ends, and mortises are cut in the posts.
    
    Args:
        post_height: Height of the posts (length before rotation)
        post_section: Cross-section size of posts (width = height)
        beam_length: Length of the connecting beam
        beam_section: Cross-section size of beam (defaults to post_section)
        tenon_length: Length of tenon projections
        shoulder_depth: Depth of angled shoulder on tenon
        housing_depth: Material left at far side of mortise
        post_top_extension: Extra mortise height above beam for housing
        
    Returns:
        (left_post_with_mortise, right_post_with_mortise, positioned_beam, beam)
        - left_post_with_mortise: Left post Part with mortise cut
        - right_post_with_mortise: Right post Part with mortise cut  
        - positioned_beam: Beam Part in final position (with tenons on both ends)
        - beam: Original Beam object (for FEA mesh generation)
    """
    # Import here to avoid circular imports
    from timber_joints.beam import Beam
    from timber_joints.shouldered_tenon import ShoulderedTenon
    
    beam_section = beam_section or post_section
    
    # Create posts and beam
    post_left = Beam(length=post_height, width=post_section, height=post_section)
    post_right = Beam(length=post_height, width=post_section, height=post_section)
    beam = Beam(length=beam_length, width=beam_section, height=beam_section)
    
    # Tenon dimensions: 1/3 width, 2/3 height
    tenon_width = beam.width / 3
    tenon_height = beam.height * 2 / 3
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
    
    # Step 1: Align beam to LEFT post (beam start at post)
    positioned_beam, _, _ = align_beam_in_post(
        beam=beam_with_both_tenons,
        post=vertical_post_left,
        drop_depth=drop_depth,
        at_start=True,
        move_post=False,
    )
    
    # Step 2: Create mortise in left post
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
        beam=positioned_beam,
        post=vertical_post_right,
        drop_depth=drop_depth,
        at_start=False,
        move_post=True,
    )
    
    # Step 4: Create mortise in right post
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
    
    return left_post_with_mortise, right_post_with_mortise, positioned_beam, beam
