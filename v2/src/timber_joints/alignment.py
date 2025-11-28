"""Alignment utilities for positioning timber joints."""

import math
from build123d import Location, Vector, Axis, Part


def align_beam_on_post(
    beam_shape: Part,
    beam_length: float,
    beam_width: float,
    beam_height: float,
    post_shape: Part,
    post_length: float,
    post_width: float,
    post_height: float,
) -> tuple[Part, Location]:
    """Align a beam on top of a post.
    
    The beam is positioned horizontally on top of the vertical post,
    with beam start at post edge.
    
    Args:
        beam_shape: The beam Part (with any joint cuts applied)
        beam_length: Length of beam (X direction)
        beam_width: Width of beam (Y direction)  
        beam_height: Height of beam (Z direction)
        post_shape: The post Part (with any joint cuts applied)
        post_length: Length of post (becomes height when vertical)
        post_width: Width of post (Y direction)
        post_height: Height of post (X direction when vertical)
    
    Returns:
        (positioned_beam, beam_location) - the beam moved to position and its Location
    """
    # Post is vertical: rotated so length is along Z
    # Post top is at Z = post_length
    # Post occupies X: -post_height to 0, Y: 0 to post_width
    
    # Position beam so:
    # - Bottom of beam (Z=0) sits on top of post (Z=post_length)
    # - Start of beam (X=0) aligns with edge of post (X=-post_height)
    # - Beam is centered on post width
    
    beam_x = -post_height
    beam_y = (post_width - beam_width) / 2
    beam_z = post_length
    
    beam_location = Location((beam_x, beam_y, beam_z))
    positioned_beam = beam_shape.move(beam_location)
    
    return positioned_beam, beam_location


def align_beam_in_post(
    beam_shape: Part,
    beam_length: float,
    beam_width: float,
    beam_height: float,
    post_shape: Part,
    post_length: float,
    post_width: float,
    post_height: float,
    drop_depth: float,
) -> tuple[Part, Location]:
    """Align a beam dropped INTO a post (for tongue-and-fork style joints).
    
    The beam is positioned so it drops into the post by drop_depth.
    
    Args:
        beam_shape: The beam Part (with any joint cuts applied)
        beam_length: Length of beam (X direction)
        beam_width: Width of beam (Y direction)
        beam_height: Height of beam (Z direction)
        post_shape: The post Part (with any joint cuts applied)
        post_length: Length of post (becomes height when vertical)
        post_width: Width of post (Y direction)
        post_height: Height of post (X direction when vertical)
        drop_depth: How far the beam drops into the post
    
    Returns:
        (positioned_beam, beam_location) - the beam moved to position and its Location
    """
    # Position beam so:
    # - Bottom of beam is at Z = post_length - drop_depth
    # - Start of beam aligns with edge of post
    # - Beam is centered on post width
    
    beam_x = -post_height
    beam_y = (post_width - beam_width) / 2
    beam_z = post_length - drop_depth
    
    beam_location = Location((beam_x, beam_y, beam_z))
    positioned_beam = beam_shape.move(beam_location)
    
    return positioned_beam, beam_location


def make_post_vertical(post_shape: Part) -> Part:
    """Rotate a post to be vertical (length along Z axis).
    
    Args:
        post_shape: The post Part in default orientation (length along X)
    
    Returns:
        The post rotated to be vertical
    """
    # Rotate -90 around Y axis: X -> Z
    return post_shape.rotate(Axis.Y, -90)


def create_receiving_cut(
    positioned_insert: Part,
    receiving_shape: Part,
) -> Part:
    return receiving_shape - positioned_insert
