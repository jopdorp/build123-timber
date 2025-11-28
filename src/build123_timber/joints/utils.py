from __future__ import annotations

import math

from build123d import Align, Box, Location, Part, extrude, Polyline, make_face

from build123_timber.elements import Timber


def create_cutting_box(
    length: float,
    width: float,
    height: float,
    position: tuple[float, float, float] = (0, 0, 0),
    align: tuple = (Align.CENTER, Align.CENTER, Align.CENTER),
) -> Part:
    box = Box(length, width, height, align=align)
    if position != (0, 0, 0):
        box = box.move(Location(position))
    return box


def lap_cut(
    timber: Timber,
    cut_width: float,
    cut_depth: float,
    x_position: float,
    from_top: bool = True,
) -> Part:
    # Timber has corner origin at (0,0,0), extends to (length, width, height)
    # Position cut centered on X at x_position, spanning full Y width, at top or bottom Z
    z_position = timber.height - cut_depth if from_top else 0
    return create_cutting_box(
        length=cut_width,
        width=timber.width,
        height=cut_depth,
        position=(x_position - cut_width / 2, 0, z_position),
        align=(Align.MIN, Align.MIN, Align.MIN),
    )


def end_cut(timber: Timber, cut_depth: float, from_end: bool = True) -> Part:
    # Timber has corner origin at (0,0,0)
    # Cut extends beyond timber to ensure full removal
    x_pos = timber.length - cut_depth if from_end else -cut_depth
    return create_cutting_box(
        length=cut_depth * 2,
        width=timber.width * 2,
        height=timber.height * 2,
        position=(x_pos, -timber.width / 2, -timber.height / 2),
        align=(Align.MIN, Align.MIN, Align.MIN),
    )


def notch_cut(
    timber: Timber,
    notch_width: float,
    notch_depth: float,
    x_position: float,
    notch_length: float | None = None,
    from_top: bool = True,
) -> Part:
    if notch_length is None:
        notch_length = notch_width
    # Timber has corner origin at (0,0,0)
    z_position = timber.height - notch_depth if from_top else 0
    # Center the notch on Y (timber width)
    y_position = (timber.width - notch_width) / 2
    return create_cutting_box(
        length=notch_length,
        width=notch_width,
        height=notch_depth,
        position=(x_position - notch_length / 2, y_position, z_position),
        align=(Align.MIN, Align.MIN, Align.MIN),
    )


def mortise_cut(
    timber: Timber,
    mortise_width: float,
    mortise_height: float,
    mortise_depth: float,
    x_position: float,
    from_face: str = "front",
) -> Part:
    """Create a mortise (rectangular hole) in the timber.
    
    Args:
        timber: The timber to cut the mortise into
        mortise_width: Width of mortise opening (perpendicular to depth direction)
        mortise_height: Height of mortise opening (perpendicular to depth direction)
        mortise_depth: How deep the mortise goes into the timber
        x_position: Position along timber length (X) where mortise is centered
        from_face: Which face the mortise enters from:
            - "front" (default): Y=0 face, mortise in Y direction
            - "back": Y=width face, mortise in -Y direction
            - "top": Z=height face, mortise in -Z direction  
            - "bottom": Z=0 face, mortise in Z direction
            - "right": Z=height face for post (same as top conceptually)
    
    For "front"/"back": mortise_width is in X, mortise_height is in Z
    For "top"/"bottom"/"right": mortise_width is in X, mortise_height is in Y
    """
    # Timber has corner origin at (0,0,0), extends to (length, width, height)
    
    if from_face in ("front",):
        # Mortise enters from Y=0 face, goes in +Y direction
        # mortise_width in X, mortise_height in Z, depth in Y
        return create_cutting_box(
            length=mortise_width,
            width=mortise_depth,
            height=mortise_height,
            position=(x_position - mortise_width / 2, 0, (timber.height - mortise_height) / 2),
            align=(Align.MIN, Align.MIN, Align.MIN),
        )
    elif from_face in ("back",):
        # Mortise enters from Y=width face, goes in -Y direction
        return create_cutting_box(
            length=mortise_width,
            width=mortise_depth,
            height=mortise_height,
            position=(x_position - mortise_width / 2, timber.width - mortise_depth, (timber.height - mortise_height) / 2),
            align=(Align.MIN, Align.MIN, Align.MIN),
        )
    elif from_face in ("top", "right"):
        # Mortise enters from Z=height face, goes in -Z direction
        # For this face: mortise_width maps to Y, mortise_height maps to X
        # (rotated 90° compared to front face)
        return create_cutting_box(
            length=mortise_height,  # Swapped: height goes to X
            width=mortise_width,    # Swapped: width goes to Y
            height=mortise_depth,
            position=(x_position - mortise_height / 2, (timber.width - mortise_width) / 2, timber.height - mortise_depth),
            align=(Align.MIN, Align.MIN, Align.MIN),
        )
    elif from_face in ("bottom",):
        # Mortise enters from Z=0 face, goes in +Z direction
        return create_cutting_box(
            length=mortise_width,
            width=mortise_height,
            height=mortise_depth,
            position=(x_position - mortise_width / 2, (timber.width - mortise_height) / 2, 0),
            align=(Align.MIN, Align.MIN, Align.MIN),
        )
    else:
        raise ValueError(f"Unknown face: {from_face}. Use 'front', 'back', 'top', 'bottom', or 'right'")


def tenon_cut(
    timber: Timber,
    tenon_width: float,
    tenon_height: float,
    tenon_length: float,
    tenon_y_offset: float = 0,
    at_start: bool = False,
) -> Part:
    """Create a cut to form a reduced tenon (smaller than full cross-section).
    
    Removes material from the end of the timber, leaving only the tenon projecting.
    Used when tenon dimensions are smaller than the timber cross-section.
    
    Args:
        timber: The timber to cut
        tenon_width: Width of tenon (Y direction)
        tenon_height: Height of tenon (Z direction)
        tenon_length: Length of tenon projection (X direction)
        tenon_y_offset: Offset in Y direction from center
        at_start: If True, tenon at X=0 (start); if False, tenon at X=length (end)
    """
    # Timber has corner origin at (0,0,0)
    # Remove end of timber, then add back the tenon shape
    # The full_end must start exactly where the tenon starts so the tenon stays connected
    
    if at_start:
        # Tenon at start (X=0)
        x_pos = 0
    else:
        # Tenon at end (X=length)
        x_pos = timber.length - tenon_length
    
    full_end = create_cutting_box(
        length=tenon_length,
        width=timber.width,
        height=timber.height,
        position=(x_pos, 0, 0),
        align=(Align.MIN, Align.MIN, Align.MIN),
    )
    # Tenon centered on width and height
    tenon_y = (timber.width - tenon_width) / 2 + tenon_y_offset
    tenon_z = (timber.height - tenon_height) / 2
    tenon = create_cutting_box(
        length=tenon_length,
        width=tenon_width,
        height=tenon_height,
        position=(x_pos, tenon_y, tenon_z),
        align=(Align.MIN, Align.MIN, Align.MIN),
    )
    return full_end - tenon


def calculate_lap_depths(
    height_a: float,
    height_b: float,
    bias: float = 0.5,
    flipped: bool = False,
) -> tuple[float, float]:
    overlap_height = min(height_a, height_b)
    if flipped:
        return (overlap_height * (1 - bias), overlap_height * bias)
    return (overlap_height * bias, overlap_height * (1 - bias))


def housing_cut(
    timber: Timber,
    housing_width: float,
    housing_depth: float,
    housing_length: float,
    x_position: float,
) -> Part:
    """Create a housing (shallow recess) in the timber surface.
    
    The housing is a shallow rectangular pocket on the Y=0 face,
    used to seat the shoulder of a cross timber. Centered on X and Z.
    
    Args:
        timber: The timber to cut the housing into
        housing_width: Width of housing in X direction
        housing_depth: Depth of housing into timber (Y direction)  
        housing_length: Length of housing in Z direction (usually cross timber height)
        x_position: X position of housing center
    """
    # Housing enters from Y=0 face, centered on X and Z (like mortise)
    return create_cutting_box(
        length=housing_width,
        width=housing_depth,
        height=housing_length,
        position=(x_position - housing_width / 2, 0, (timber.height - housing_length) / 2),
        align=(Align.MIN, Align.MIN, Align.MIN),
    )


def angled_housing_cut(
    timber: Timber,
    housing_width: float,
    housing_depth: float,
    housing_length: float,
    x_position: float,
    shoulder_angle: float,
) -> Part:
    """Create an angled housing (wedge-shaped recess) in the timber surface.
    
    The housing is a triangular wedge on the Y=0 face. One side is flush with
    the surface (depth 0), the other side is at housing_depth. Used for angled 
    joints where the cross timber meets the main at an angle.
    
    Args:
        timber: The timber to cut the housing into
        housing_width: Width of housing in X direction
        housing_depth: Maximum depth of housing into timber (Y direction) at the deep side
        housing_length: Length of housing in Z direction (usually cross timber height)
        x_position: X position of housing center
        shoulder_angle: Angle of the shoulder in degrees (+ = deep at min X, - = deep at max X)
    """
    x_min = x_position - housing_width / 2
    x_max = x_position + housing_width / 2
    
    # Triangle profile in XY plane - one side flush, other side at depth
    if shoulder_angle >= 0:
        # Deep at min X, flush at max X - triangle
        profile_points = [
            (x_min, 0),              # Front left
            (x_max, 0),              # Front right (also back right - flush)
            (x_min, housing_depth),  # Back left (deep)
        ]
    else:
        # Flush at min X, deep at max X - triangle
        profile_points = [
            (x_min, 0),              # Front left (also back left - flush)
            (x_max, 0),              # Front right
            (x_max, housing_depth),  # Back right (deep)
        ]
    
    # Create profile and extrude in Z direction
    z_min = (timber.height - housing_length) / 2
    wire = Polyline(profile_points, close=True)
    face = make_face(wire)
    face = face.move(Location((0, 0, z_min)))
    
    wedge = extrude(face, amount=housing_length)
    return Part(wedge.wrapped)


def angled_tenon_cut(
    timber: Timber,
    tenon_width: float,
    tenon_height: float,
    tenon_length: float,
    housing_depth: float,
    shoulder_angle: float,
) -> Part:
    """Create a cut to form a tenon with an angled shoulder.
    
    Removes material from the end of the timber, leaving only the tenon projecting.
    The shoulder (surface around the tenon) is angled - one side is at the tenon
    base, the other side is cut back by housing_depth.
    
    Note: tenon_width is in timber's Z direction, tenon_height is in timber's Y direction
    (rotated 90° from regular tenon to match housing orientation).
    
    Args:
        timber: The timber to cut
        tenon_width: Width of the tenon (Z direction - across timber height)
        tenon_height: Height of the tenon (Y direction - across timber width)
        tenon_length: Length of tenon projecting from the flush side of shoulder
        housing_depth: Depth of the angled shoulder at the deep side
        shoulder_angle: Angle of the shoulder in degrees (+ = deep at Y=0)
    """
    x_end = timber.length
    x_tenon_start = x_end - tenon_length  # Flush side of shoulder (tenon base)
    x_deep = x_tenon_start - housing_depth  # Deep side of shoulder
    
    # Tenon dimensions are swapped: width->Z, height->Y
    # Center tenon on timber cross-section
    tenon_y = (timber.width - tenon_height) / 2
    tenon_z = (timber.height - tenon_width) / 2
    
    # Full end block from deep side to timber end (covers both shoulder and tenon area)
    full_cut = create_cutting_box(
        length=tenon_length + housing_depth,
        width=timber.width,
        height=timber.height,
        position=(x_deep, 0, 0),
        align=(Align.MIN, Align.MIN, Align.MIN),
    )
    
    # Tenon shape - the part we keep, extends full length of cut
    tenon = create_cutting_box(
        length=tenon_length + housing_depth,
        width=tenon_height,  # Y direction
        height=tenon_width,  # Z direction
        position=(x_deep, tenon_y, tenon_z),
        align=(Align.MIN, Align.MIN, Align.MIN),
    )
    
    # Triangle to keep (not cut) - connects the shoulder area to the timber body
    # The triangle goes from x_deep (where it meets timber body) to x_tenon_start
    if shoulder_angle >= 0:
        # Deep at Y=0, flush at Y=timber.width
        # Keep triangle: the part that connects to timber body at x_deep
        profile_points = [
            (x_deep, 0),                   # At deep X, Y=0 (connects to body)
            (x_deep, timber.width),        # At deep X, full Y (connects to body)
            (x_tenon_start, timber.width), # At flush X, full Y (the angled edge)
        ]
    else:
        # Flush at Y=0, deep at Y=timber.width
        profile_points = [
            (x_deep, 0),                   # At deep X, Y=0 (connects to body)
            (x_tenon_start, 0),            # At flush X, Y=0 (the angled edge)
            (x_deep, timber.width),        # At deep X, full Y (connects to body)
        ]
    
    wire = Polyline(profile_points, close=True)
    face = make_face(wire)
    keep_triangle = extrude(face, amount=timber.height)
    keep_triangle = Part(keep_triangle.wrapped)
    
    # Build the cut shape:
    # 1. Start with full block
    # 2. Subtract tenon (creates shape around tenon)
    # 3. Subtract keep_triangle (removes the part we don't want to cut)
    around_tenon = full_cut - tenon
    final_cut = around_tenon - keep_triangle
    
    return final_cut
