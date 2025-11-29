"""Utility functions for timber joints."""

import math
from typing import Tuple
from build123d import Align, Axis, Box, Part, Location, Polyline, make_face, extrude, loft, Sketch, Rectangle, Plane


def get_shape_dimensions(shape) -> Tuple[Part, float, float, float]:
    """Extract the Part shape and its dimensions from a Beam or Part.
    
    This utility function allows joint classes to accept either a Beam object
    (with .shape attribute) or a raw Part. It uses bounding box to determine
    dimensions, making it work with already-cut shapes.
    
    Args:
        shape: Either a Beam object (with .shape and dimension attributes) 
               or a Part object
    
    Returns:
        Tuple of (part_shape, length, width, height) where:
        - part_shape: The Part geometry
        - length: X dimension (from bounding box)
        - width: Y dimension (from bounding box)
        - height: Z dimension (from bounding box)
    """
    # Get the underlying Part shape
    if hasattr(shape, 'shape'):
        part_shape = shape.shape
    else:
        part_shape = shape
    
    # Always use bounding box for dimensions - works for both pristine beams and cut shapes
    bbox = part_shape.bounding_box()
    length = bbox.max.X - bbox.min.X
    width = bbox.max.Y - bbox.min.Y
    height = bbox.max.Z - bbox.min.Z
    
    return part_shape, length, width, height


def create_tenon_cut(
    beam_length: float,
    beam_width: float,
    beam_height: float,
    tenon_width: float,
    tenon_height: float,
    tenon_length: float,
    at_start: bool = False,
) -> Part:
    """Create material to remove around a centered tenon projection.
    
    Returns the "waste" shape that should be subtracted from the beam
    to leave only the centered tenon projecting.
    
    Args:
        beam_length: Length of the beam (X direction)
        beam_width: Width of the beam (Y direction)
        beam_height: Height of the beam (Z direction)
        tenon_width: Width of the tenon (Y direction)
        tenon_height: Height of the tenon (Z direction)
        tenon_length: Length of the tenon projection (X direction)
        at_start: If True, tenon at X=0; if False, tenon at X=beam_length
    
    Returns:
        Part representing material to remove (full end section minus tenon)
    """
    # Calculate offsets to center the tenon
    y_offset = (beam_width - tenon_width) / 2
    z_offset = (beam_height - tenon_height) / 2
    
    # Determine position based on at_start
    if at_start:
        x_pos = 0
    else:
        x_pos = beam_length - tenon_length
    
    # Full end section (everything in the tenon zone)
    end_section = Box(
        tenon_length,
        beam_width,
        beam_height,
        align=(Align.MIN, Align.MIN, Align.MIN)
    )
    end_section = end_section.move(Location((x_pos, 0, 0)))
    
    # Centered tenon shape (what we want to keep)
    tenon_shape = Box(
        tenon_length,
        tenon_width,
        tenon_height,
        align=(Align.MIN, Align.MIN, Align.MIN)
    )
    tenon_shape = tenon_shape.move(Location((x_pos, y_offset, z_offset)))
    
    # Material to remove = end_section - tenon_shape
    return end_section - tenon_shape


def create_lap_cut(
    beam_width: float,
    beam_height: float,
    cut_depth: float,
    cut_length: float,
    x_position: float,
    from_top: bool = True,
) -> Part:
    """Create a rectangular lap cut volume.
    
    Args:
        beam_width: Width of the beam (Y direction)
        beam_height: Height of the beam (Z direction)
        cut_depth: Depth of cut from surface
        cut_length: Length of the cut (X direction)
        x_position: X position where the cut starts (MIN aligned)
        from_top: If True, cut from top; if False, cut from bottom
    
    Returns:
        Part representing material to remove
    """
    if from_top:
        z_pos = beam_height - cut_depth
    else:
        z_pos = 0
    
    cut = Box(
        cut_length,
        beam_width,
        cut_depth,
        align=(Align.MIN, Align.MIN, Align.MIN)
    )
    return cut.move(Location((x_position, 0, z_pos)))


def calculate_dovetail_taper(angle: float, length: float) -> float:
    """Calculate the width increase for a dovetail given angle and length.
    
    Args:
        angle: Dovetail angle in degrees
        length: Length over which the taper occurs
    
    Returns:
        Total taper (width increase on each side is half this value)
    """
    return 2 * math.tan(math.radians(angle)) * length


def create_dovetail_cut(
    base_width: float,
    height: float,
    length: float,
    cone_angle: float,
    y_center: float,
    z_center: float,
) -> Part:
    """Create a tapered dovetail solid (wider at tip than base).
    
    The shape starts at X=0 (narrow) and extends to X=length (wide).
    
    Args:
        base_width: Width at base (narrow end, X=0)
        height: Height of the dovetail (Z direction)
        length: Length of the dovetail (X direction)
        cone_angle: Angle of taper in degrees
        y_center: Y position to center the shape on
        z_center: Z position to center the shape on
    
    Returns:
        Part representing the dovetail solid
    """
    taper = math.tan(math.radians(cone_angle)) * length
    tip_width = base_width + 2 * taper
    
    # Create the base rectangle (narrow, at X=0)
    base_sketch = Sketch() + Rectangle(base_width, height)
    
    # Create the tip rectangle (wider, at X=length)
    tip_sketch = Sketch() + Rectangle(tip_width, height)
    
    # Position the sketches in Y-Z plane (perpendicular to X axis)
    base_face = Plane.YZ * base_sketch
    tip_face = Plane.YZ.offset(length) * tip_sketch
    
    # Loft between the two faces and position
    dovetail = loft([base_face, tip_face])
    return dovetail.move(Location((0, y_center, z_center)))


def create_vertical_cut(post: Part, cut_class, at_top: bool = True, **cut_kwargs) -> Part:
    """Apply a horizontal joint cut class to a vertical post.
    
    This utility rotates the post to horizontal orientation, applies the cut
    using any joint class (Tenon, ShoulderedTenon, DovetailInsert, etc.),
    then rotates the result back to vertical.
    
    Args:
        post: The vertical post Part (oriented along Z axis)
        cut_class: A joint class that takes a beam/Part as first argument
                   (e.g., Tenon, ShoulderedTenon, DovetailInsert)
        at_top: If True, cut at top of post (Z+); if False, cut at bottom (Z-)
        **cut_kwargs: Additional keyword arguments passed to the cut class
                      (e.g., tenon_width, tenon_height, tenon_length)
    
    Returns:
        Post Part with the cut applied
        
    Example:
        >>> from timber_joints.tenon import Tenon
        >>> post_with_tenon = create_vertical_cut(
        ...     post,
        ...     Tenon,
        ...     at_top=True,
        ...     tenon_width=50,
        ...     tenon_height=100,
        ...     tenon_length=60,
        ... )
    """
    # Get post position for restoration
    bbox = post.bounding_box()
    original_min_x = bbox.min.X
    original_min_y = bbox.min.Y
    original_min_z = bbox.min.Z
    
    # Move post so Z starts at 0 and XY are centered at origin
    post_center_x = (bbox.min.X + bbox.max.X) / 2
    post_center_y = (bbox.min.Y + bbox.max.Y) / 2
    post_at_origin = post.move(Location((-post_center_x, -post_center_y, -original_min_z)))
    
    # Rotate post from vertical (Z) to horizontal (X)
    # Rotate +90° around Y axis: Z+ becomes X+ (post extends in +X direction)
    post_horizontal = post_at_origin.rotate(Axis.Y, 90)
    
    # Now the beam should go from X=0 to X=height, centered on Y and Z
    # But Tenon expects beam starting at origin with Y and Z from 0
    # Move to align with origin
    h_bbox = post_horizontal.bounding_box()
    post_horizontal = post_horizontal.move(Location((
        -h_bbox.min.X,  # Move so X starts at 0
        -h_bbox.min.Y,  # Move so Y starts at 0
        -h_bbox.min.Z,  # Move so Z starts at 0
    )))
    
    # Apply the cut class
    # at_top=True means cut at original Z+ which is now X+ (at_start=False)
    # at_top=False means cut at original Z- which is now X=0 (at_start=True)
    cut_kwargs['at_start'] = not at_top
    
    # Create the cut - the class will use .shape property to get the result
    cut_instance = cut_class(beam=post_horizontal, **cut_kwargs)
    cut_result = cut_instance.shape
    
    # Move back to centered position before rotation
    r_bbox = cut_result.bounding_box()
    cut_centered = cut_result.move(Location((
        -r_bbox.min.X,  # X starts at 0
        -(r_bbox.min.Y + r_bbox.max.Y) / 2,  # Center on Y
        -(r_bbox.min.Z + r_bbox.max.Z) / 2,  # Center on Z
    )))
    
    # Rotate back to vertical (-90° around Y)
    result_vertical = cut_centered.rotate(Axis.Y, -90)
    
    # Move back to original position
    v_bbox = result_vertical.bounding_box()
    return result_vertical.move(Location((
        original_min_x - v_bbox.min.X + (bbox.max.X - bbox.min.X - (v_bbox.max.X - v_bbox.min.X)) / 2,
        original_min_y - v_bbox.min.Y + (bbox.max.Y - bbox.min.Y - (v_bbox.max.Y - v_bbox.min.Y)) / 2,
        original_min_z - v_bbox.min.Z,
    )))
