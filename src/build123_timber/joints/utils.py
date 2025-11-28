from __future__ import annotations

from build123d import Align, Box, Location, Part

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
) -> Part:
    # Timber has corner origin at (0,0,0)
    # Mortise enters from Y=0 face, centered on X and Z
    # Caller is responsible for adding clearance to dimensions
    return create_cutting_box(
        length=mortise_width,
        width=mortise_depth,
        height=mortise_height,
        position=(x_position - mortise_width / 2, 0, (timber.height - mortise_height) / 2),
        align=(Align.MIN, Align.MIN, Align.MIN),
    )


def tenon_cut(
    timber: Timber,
    tenon_width: float,
    tenon_height: float,
    tenon_length: float,
    tenon_y_offset: float = 0,
) -> Part:
    """Create a cut to form a reduced tenon (smaller than full cross-section).
    
    Removes material from the end of the timber, leaving only the tenon projecting.
    Used when tenon dimensions are smaller than the timber cross-section.
    """
    # Timber has corner origin at (0,0,0)
    # Remove end of timber, then add back the tenon shape
    # The full_end must start exactly where the tenon starts so the tenon stays connected
    full_end = create_cutting_box(
        length=tenon_length,
        width=timber.width,
        height=timber.height,
        position=(timber.length - tenon_length, 0, 0),
        align=(Align.MIN, Align.MIN, Align.MIN),
    )
    # Tenon centered on width and height
    tenon_y = (timber.width - tenon_width) / 2 + tenon_y_offset
    tenon_z = (timber.height - tenon_height) / 2
    tenon = create_cutting_box(
        length=tenon_length,
        width=tenon_width,
        height=tenon_height,
        position=(timber.length - tenon_length, tenon_y, tenon_z),
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
