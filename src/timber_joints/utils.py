"""Utility functions for timber joints."""

import math
from typing import Tuple
from build123d import Align, Axis, Box, Part, Location, Polyline, make_face, extrude, loft, Sketch, Rectangle, Plane


def get_shape_dimensions(shape) -> Tuple[Part, float, float, float]:
    """Extract Part shape and XYZ dimensions from a Beam or Part.
    
    Accepts either a Beam (with .shape attribute) or raw Part.
    Uses bounding box for dimensions, so works with already-cut shapes.
    """
    if hasattr(shape, 'shape'):
        part_shape = shape.shape
    else:
        part_shape = shape
    
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
    """Create the waste material to subtract for a centered tenon projection."""
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
    
    return end_section - tenon_shape


def create_lap_cut(
    beam_width: float,
    beam_height: float,
    cut_depth: float,
    cut_length: float,
    x_position: float,
    from_top: bool = True,
) -> Part:
    """Create a rectangular lap cut volume to subtract from a beam."""
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
    """Calculate total width increase for a dovetail taper."""
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
    
    Starts at X=0 (narrow, base_width) and extends to X=length (wide).
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
    
    Rotates the post to horizontal, applies the cut class (Tenon, ShoulderedTenon,
    DovetailInsert, etc.), then rotates back to vertical.
    """
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
