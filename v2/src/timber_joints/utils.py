"""Utility functions for timber joints."""

from build123d import Align, Box, Part, Location


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
