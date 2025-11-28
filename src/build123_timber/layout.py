from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator

from build123d import Location

if TYPE_CHECKING:
    from build123_timber.elements import Timber
    from build123_timber.joints.base import Joint


@dataclass
class LinearLayout:
    """Distributes elements along a timber at regular intervals.
    
    Use either `spacing` (distance between elements) or `count` (number of elements).
    """
    along: Timber
    spacing: float | None = None
    count: int | None = None
    skip_start: bool = False
    skip_end: bool = False
    start_offset: float = 0
    end_offset: float = 0

    def positions(self) -> list[float]:
        available_length = self.along.length - self.start_offset - self.end_offset

        if self.count is not None:
            if self.count < 1:
                return []
            if self.count == 1:
                positions = [self.start_offset + available_length / 2]
            else:
                step = available_length / (self.count - 1)
                positions = [self.start_offset + i * step for i in range(self.count)]
        elif self.spacing is not None:
            if self.spacing <= 0:
                return []
            positions = []
            pos = self.start_offset
            while pos <= self.along.length - self.end_offset + 0.001:
                positions.append(pos)
                pos += self.spacing
        else:
            raise ValueError("Must specify either spacing or count")

        if self.skip_start and positions and positions[0] <= self.start_offset + 0.001:
            positions = positions[1:]
        if self.skip_end and positions and positions[-1] >= self.along.length - self.end_offset - 0.001:
            positions = positions[:-1]

        return positions


@dataclass  
class RafterLayout:
    """Creates pairs of rafters from plate beams to a ridge beam.
    
    Generates rafters on both sides of the ridge, properly angled.
    """
    plate_front: Timber
    plate_back: Timber
    ridge: Timber
    rafter_width: float
    rafter_height: float
    pitch: float = 30.0
    spacing: float | None = None
    count: int | None = None
    skip_ends: bool = False
    overhang: float = 0
    
    _rafter_counter: int = field(default=0, repr=False)

    def _calculate_rafter_length(self, plate: Timber) -> float:
        plate_pos = plate.location.position
        ridge_pos = self.ridge.location.position
        
        horizontal_dist = abs(ridge_pos.Y - plate_pos.Y)
        vertical_dist = abs(ridge_pos.Z - plate_pos.Z)
        
        rafter_length = math.sqrt(horizontal_dist**2 + vertical_dist**2)
        return rafter_length + self.overhang

    def generate(self) -> Iterator[tuple[Timber, Location]]:
        from build123_timber.elements import Timber

        layout = LinearLayout(
            along=self.ridge,
            spacing=self.spacing,
            count=self.count,
            skip_start=self.skip_ends,
            skip_end=self.skip_ends,
        )

        ridge_pos = self.ridge.location.position
        front_plate_pos = self.plate_front.location.position
        back_plate_pos = self.plate_back.location.position

        for x_pos in layout.positions():
            front_length = self._calculate_rafter_length(self.plate_front)
            front_rafter = Timber.rafter(
                length=front_length,
                width=self.rafter_width,
                height=self.rafter_height,
                name=f"rafter_front_{self._rafter_counter}",
            )

            front_start_y = front_plate_pos.Y
            front_start_z = front_plate_pos.Z + self.plate_front.height / 2

            ridge_y = ridge_pos.Y
            if front_start_y < ridge_y:
                front_pitch = self.pitch
                front_y = front_start_y - self.overhang * math.cos(math.radians(self.pitch))
            else:
                front_pitch = -self.pitch
                front_y = front_start_y + self.overhang * math.cos(math.radians(self.pitch))

            front_z = front_start_z - self.overhang * math.sin(math.radians(self.pitch))

            actual_x = self.ridge.location.position.X + x_pos
            front_location = Location(
                (actual_x, front_y, front_z),
                (front_pitch, 0, 90)
            )
            front_rafter.location = front_location
            yield front_rafter, front_location

            back_length = self._calculate_rafter_length(self.plate_back)
            back_rafter = Timber.rafter(
                length=back_length,
                width=self.rafter_width,
                height=self.rafter_height,
                name=f"rafter_back_{self._rafter_counter}",
            )

            back_start_y = back_plate_pos.Y
            back_start_z = back_plate_pos.Z + self.plate_back.height / 2

            if back_start_y > ridge_y:
                back_pitch = self.pitch
                back_y = back_start_y + self.overhang * math.cos(math.radians(self.pitch))
            else:
                back_pitch = -self.pitch
                back_y = back_start_y - self.overhang * math.cos(math.radians(self.pitch))

            back_z = back_start_z - self.overhang * math.sin(math.radians(self.pitch))

            back_location = Location(
                (actual_x, back_y, back_z),
                (back_pitch, 0, -90)
            )
            back_rafter.location = back_location
            yield back_rafter, back_location

            self._rafter_counter += 1


@dataclass
class StudLayout:
    """Creates vertical studs between bottom and top plates."""
    bottom_plate: Timber
    top_plate: Timber
    stud_width: float
    stud_depth: float
    spacing: float | None = None
    count: int | None = None
    skip_ends: bool = True

    def generate(self) -> Iterator[Timber]:
        from build123_timber.elements import Timber

        layout = LinearLayout(
            along=self.bottom_plate,
            spacing=self.spacing,
            count=self.count,
            skip_start=self.skip_ends,
            skip_end=self.skip_ends,
        )

        bottom_pos = self.bottom_plate.location.position
        top_pos = self.top_plate.location.position
        stud_length = top_pos.Z - bottom_pos.Z - self.bottom_plate.height / 2 - self.top_plate.height / 2

        for i, x_pos in enumerate(layout.positions()):
            stud = Timber.stud(
                length=stud_length,
                width=self.stud_width,
                height=self.stud_depth,
                name=f"stud_{i}",
            )

            actual_x = bottom_pos.X + x_pos
            stud.location = Location(
                (actual_x, bottom_pos.Y, bottom_pos.Z + self.bottom_plate.height / 2),
                (0, -90, 0)
            )
            yield stud
