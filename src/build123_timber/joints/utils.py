from __future__ import annotations

from build123d import Box, Location, Part

from build123_timber.elements import Timber


def create_cutting_box(
    length: float,
    width: float,
    height: float,
    position: tuple[float, float, float] = (0, 0, 0),
    align: tuple = ("CENTER", "CENTER", "CENTER"),
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
    z_offset = timber.height / 2 - cut_depth / 2 if from_top else -timber.height / 2 + cut_depth / 2
    return create_cutting_box(
        length=cut_width,
        width=timber.width,
        height=cut_depth,
        position=(x_position, 0, z_offset),
    )


def end_cut(timber: Timber, cut_depth: float, from_end: bool = True) -> Part:
    x_pos = timber.length + cut_depth / 2 if from_end else -cut_depth / 2
    return create_cutting_box(
        length=cut_depth * 2,
        width=timber.width * 2,
        height=timber.height * 2,
        position=(x_pos, 0, 0),
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
    z_offset = timber.height / 2 - notch_depth / 2 if from_top else -timber.height / 2 + notch_depth / 2
    return create_cutting_box(
        length=notch_length,
        width=notch_width,
        height=notch_depth,
        position=(x_position, 0, z_offset),
    )


def mortise_cut(
    timber: Timber,
    mortise_width: float,
    mortise_height: float,
    mortise_depth: float,
    x_position: float,
    clearance: float = 0.5,
) -> Part:
    return create_cutting_box(
        length=mortise_width + clearance,
        width=mortise_depth,
        height=mortise_height + clearance,
        position=(x_position, -timber.width / 2, 0),
        align=("CENTER", "MIN", "CENTER"),
    )


def shoulder_cuts(
    timber: Timber,
    tenon_width: float,
    tenon_height: float,
    tenon_length: float,
    tenon_y_offset: float = 0,
) -> Part:
    full_end = create_cutting_box(
        length=tenon_length + 10,
        width=timber.width,
        height=timber.height,
        position=(timber.length - tenon_length / 2, 0, 0),
    )
    tenon = create_cutting_box(
        length=tenon_length,
        width=tenon_width,
        height=tenon_height,
        position=(timber.length - tenon_length / 2, tenon_y_offset, 0),
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
