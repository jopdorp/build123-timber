"""Alignment utilities for positioning timber joints."""

import math
from dataclasses import dataclass
from build123d import Location, Axis, Part



@dataclass
class PositionedBrace:
    """A brace with its positioning and angle information.
    
    This stores the brace Part along with the angle needed for creating
    specialized tenon cuts. The tenon cuts have:
    - One face aligned with the brace angle
    - Another face perpendicular to the post/beam/girt (90°)
    - The tip aligned with the post/beam/girt surface
    
    Attributes:
        shape: The positioned brace Part
        angle: Angle from horizontal in degrees (e.g., 45° for equal horizontal/vertical)
        at_beam_end: True if brace is at beam end (right), False if at beam start (left)
        brace_section: Cross-section size of the brace
        axis: The horizontal axis along which the brace runs (Axis.X or Axis.Y)
    """
    shape: Part
    angle: float  # degrees from horizontal
    at_beam_end: bool  # True = right/end side, False = left/start side
    brace_section: float
    axis: Axis = Axis.X  # X for bent braces, Y for girt braces


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
    margin: float = 0.2,
) -> Part:
    """Subtract the insert from the receiving shape to create a mortise/pocket.
    
    Args:
        positioned_insert: The insert Part (e.g., tenon) already positioned
        receiving_shape: The receiving Part (e.g., post) to cut
        margin: Gap to add around insert for clearance (default 0.2mm).
                Positive values make the mortise larger than the tenon.
                
    Returns:
        The receiving shape with the mortise cut
    """
    if margin > 0:
        from timber_joints.analysis import expand_shape_by_margin
        insert_with_margin = expand_shape_by_margin(positioned_insert, margin)
        return receiving_shape - insert_with_margin
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


def calculate_brace_angle(
    horizontal_distance: float,
    vertical_distance: float,
) -> float:
    """Calculate the angle of a brace from horizontal.
    
    Args:
        horizontal_distance: Horizontal span of the brace (X or Y direction)
        vertical_distance: Vertical span of the brace (Z direction)
    
    Returns:
        Angle in degrees from horizontal (0 = horizontal, 90 = vertical)
    """
    return math.degrees(math.atan2(vertical_distance, horizontal_distance))


def calculate_brace_length(
    horizontal_distance: float,
    vertical_distance: float,
) -> float:
    """Calculate the required length of a brace.
    
    Args:
        horizontal_distance: Horizontal span of the brace (X or Y direction)
        vertical_distance: Vertical span of the brace (Z direction)
    
    Returns:
        Length of the brace (diagonal distance)
    """
    return math.sqrt(horizontal_distance**2 + vertical_distance**2)


def _create_brace(
    post: Part,
    horizontal_member: Part,
    brace_section: float,
    distance_from_post: float,
    at_member_start: bool,
    axis: Axis,
    tenon_width: float = None,
    tenon_height: float = None,
    tenon_length: float = 60.0,
) -> PositionedBrace:
    """Create and position a brace between a post and horizontal member.
    
    This is the core brace creation function that handles both bent braces (X axis)
    and girt braces (Y axis). The brace runs at approximately 45 degrees, with the
    brace penetrating into the horizontal member until the lower corner of the brace
    end touches the member bottom surface.
    
    Args:
        post: The vertical post Part (already positioned)
        horizontal_member: The horizontal beam/girt Part (already positioned)
        brace_section: Cross-section size of the brace (width = height)
        distance_from_post: Distance from post inside face to brace corner at member
        at_member_start: If True, brace at member start; if False, at member end
        axis: Axis.X for bent braces, Axis.Y for girt braces
        tenon_width: Width of tenon (default: brace_section / 3)
        tenon_height: Height of tenon (default: brace_section * 2/3)
        tenon_length: Length of tenon projection (default: 60mm)
    
    Returns:
        PositionedBrace with shape, angle, position info for tenon cuts
    """
    from timber_joints.beam import Beam
    from timber_joints.brace_tenon import BraceTenon
    
    post_bbox = post.bounding_box()
    member_bbox = horizontal_member.bounding_box()
    
    # Get post center
    post_center_x = (post_bbox.min.X + post_bbox.max.X) / 2
    post_center_y = (post_bbox.min.Y + post_bbox.max.Y) / 2
    
    # Calculate connection points
    horizontal_dist = distance_from_post
    vertical_dist = horizontal_dist  # 45 degree angle
    
    # Calculate angle (from horizontal)
    angle = calculate_brace_angle(horizontal_dist, vertical_dist)
    
    # Calculate actual brace length
    brace_length = calculate_brace_length(horizontal_dist, vertical_dist)
    
    # Create the brace (without tenon cuts first - we'll use this bbox for positioning)
    brace_beam = Beam(length=brace_length, width=brace_section, height=brace_section)
    brace = brace_beam.shape
    
    # Set up tenon dimensions
    if tenon_width is None:
        tenon_width = brace_section / 3
    if tenon_height is None:
        tenon_height = brace_section * 2 / 3
    
    # Create the brace WITH tenon cuts first (to get rotated_cut_bbox_height for positioning)
    brace_for_cuts = Beam(length=brace_length, width=brace_section, height=brace_section).shape
    
    # Cut tenon at post end (start of brace)
    brace_with_post_tenon = BraceTenon(
        brace=brace_for_cuts,
        tenon_width=tenon_width,
        tenon_height=tenon_height,
        tenon_length=tenon_length,
        brace_angle=angle,
        at_start=True,
    )
    
    # Cut tenon at member end (end of brace)
    brace_with_both_tenons = BraceTenon(
        brace=brace_with_post_tenon.shape,
        tenon_width=tenon_width,
        tenon_height=tenon_height,
        tenon_length=tenon_length,
        brace_angle=angle,
        at_start=False,
    )
    brace_with_cuts = brace_with_both_tenons.shape
    
    # Get the penetration depth from the tenon cut (how far tenon tip extends when tilted)
    penetration_depth = brace_with_both_tenons.rotated_cut_bbox_height
    
    # Brace bounding box top aligns with member bottom, then penetrates by tenon projection
    target_top_z = member_bbox.min.Z + penetration_depth
    
    # Determine rotation axis for tilting (perpendicular to brace direction)
    # X-axis brace tilts around Y; Y-axis brace tilts around X
    tilt_axis = Axis.Y if axis == Axis.X else Axis.X
    
    # For Y-axis braces, first rotate 90° around Z to align with Y axis
    if axis == Axis.Y:
        brace = brace.rotate(Axis.Z, 90)
    
    # Determine sign for angle based on which end of the member the brace is at
    angle_sign = -1 if at_member_start else 1
    rotated_brace = brace.rotate(tilt_axis, angle_sign * angle)
    
    # Use the ORIGINAL brace bbox (no tenon cuts) for positioning
    rot_bbox = rotated_brace.bounding_box()
    
    # Calculate positioning along the brace axis
    # Align brace bounding box edge with the post inside face, then penetrate by tenon projection
    # Horizontal penetration from the post tenon (cos component of tenon length)
    horizontal_penetration = brace_with_post_tenon.rotated_cut_bbox_width
    
    if axis == Axis.X:
        # Position along X axis
        if at_member_start:
            # Brace at beam start - post is on the left, brace penetrates into post
            post_inside = post_bbox.max.X
            target_x = post_inside - rot_bbox.min.X - horizontal_penetration
        else:
            # Brace at beam end - post is on the right, brace penetrates into post
            post_inside = post_bbox.min.X
            target_x = post_inside - rot_bbox.max.X + horizontal_penetration
        
        # Center on Y (same as post)
        target_y = post_center_y - (rot_bbox.min.Y + rot_bbox.max.Y) / 2
    else:  # axis == Axis.Y
        # Position along Y axis
        if at_member_start:
            # Brace toward -Y - post is on the +Y side, brace penetrates into post
            post_inside = post_bbox.min.Y
            target_y = post_inside - rot_bbox.max.Y + horizontal_penetration
        else:
            # Brace toward +Y - post is on the -Y side, brace penetrates into post
            post_inside = post_bbox.max.Y
            target_y = post_inside - rot_bbox.min.Y - horizontal_penetration
        
        # Center on X (same as post)
        target_x = post_center_x - (rot_bbox.min.X + rot_bbox.max.X) / 2
    
    target_z = target_top_z - rot_bbox.max.Z
    
    # Apply same rotations to the brace with cuts
    if axis == Axis.Y:
        brace_with_cuts = brace_with_cuts.rotate(Axis.Z, 90)
    brace_with_cuts = brace_with_cuts.rotate(tilt_axis, angle_sign * angle)
    
    # Position using the offset calculated from the original bbox
    positioned_shape = brace_with_cuts.move(Location((target_x, target_y, target_z)))
    return PositionedBrace(
        shape=positioned_shape,
        angle=angle,
        at_beam_end=not at_member_start,
        brace_section=brace_section,
        axis=axis,
    )


def create_brace_for_bent(
    post: Part,
    beam: Part,
    brace_section: float,
    distance_from_post: float,
    at_beam_start: bool = True,
    tenon_width: float = None,
    tenon_height: float = None,
    tenon_length: float = 60.0,
) -> PositionedBrace:
    """Create and position a brace between a post and beam in a bent.
    
    This is a higher-level function that creates a brace of the right length
    and positions it to connect a post to a beam. The brace runs at approximately
    45 degrees, with the brace penetrating into the beam until the lower corner
    of the brace end touches the beam bottom surface.
    
    Args:
        post: The vertical post Part (already positioned)
        beam: The horizontal beam Part (already positioned)
        brace_section: Cross-section size of the brace (width = height)
        distance_from_post: Distance from post inside face to brace corner at beam
        at_beam_start: If True, brace at beam start (left post)
                       If False, brace at beam end (right post)
        tenon_width: Width of tenon (default: brace_section / 3)
        tenon_height: Height of tenon (default: brace_section * 2/3)
        tenon_length: Length of tenon projection (default: 60mm)
    
    Returns:
        PositionedBrace with shape, angle, position info for tenon cuts
    """
    return _create_brace(
        post=post,
        horizontal_member=beam,
        brace_section=brace_section,
        distance_from_post=distance_from_post,
        at_member_start=at_beam_start,
        axis=Axis.X,
        tenon_width=tenon_width,
        tenon_height=tenon_height,
        tenon_length=tenon_length,
    )


def create_brace_for_girt(
    post: Part,
    girt: Part,
    brace_section: float,
    distance_from_post: float = 300.0,
    at_girt_start: bool = True,
    tenon_width: float = None,
    tenon_height: float = None,
    tenon_length: float = 60.0,
) -> PositionedBrace:
    """Create and position a brace between a post and girt.
    
    Similar to create_brace_for_bent, but for girts which run along the Y axis.
    The brace runs at approximately 45 degrees, with the brace penetrating into 
    the girt until the lower corner of the brace end touches the girt bottom.
    
    Args:
        post: The vertical post Part (already positioned)
        girt: The horizontal girt Part (already positioned, running along Y)
        brace_section: Cross-section size of the brace (width = height)
        distance_from_post: Distance from post inside face for brace bottom connection  
        at_girt_start: If True, brace at girt start (toward -Y)
                       If False, brace at girt end (toward +Y)
        tenon_width: Width of tenon (default: brace_section / 3)
        tenon_height: Height of tenon (default: brace_section * 2/3)
        tenon_length: Length of tenon projection (default: 60mm)
    
    Returns:
        PositionedBrace with shape, angle, position info for tenon cuts
    """
    return _create_brace(
        post=post,
        horizontal_member=girt,
        brace_section=brace_section,
        distance_from_post=distance_from_post,
        at_member_start=at_girt_start,
        axis=Axis.Y,
        tenon_width=tenon_width,
        tenon_height=tenon_height,
        tenon_length=tenon_length,
    )


def  build_complete_bent(
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
