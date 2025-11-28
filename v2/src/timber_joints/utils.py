"""Utility functions for timber joints."""

import math
from build123d import Align, Box, Part, Location, Polyline, make_face, extrude, loft, Sketch, Rectangle, Plane


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
