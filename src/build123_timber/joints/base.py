from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from build123d import Part

if TYPE_CHECKING:
    from build123_timber.elements import Timber
    from build123_timber.alignment import ConnectionPoint, TimberFace, CrossOrientation


class JointTopology(Enum):
    L = auto()  # Corner - both ends meet
    T = auto()  # One end meets another's length
    X = auto()  # Cross through
    I = auto()  # Splice (collinear)


@dataclass
class Joint(ABC):
    main: Timber
    cross: Timber
    topology: JointTopology = field(init=False, default=JointTopology.T)

    main_point: ConnectionPoint | float | None = field(default=None, repr=False)
    main_face: TimberFace | None = field(default=None, repr=False)
    cross_point: ConnectionPoint | float | None = field(default=None, repr=False)
    cross_face: TimberFace | None = field(default=None, repr=False)
    orientation: CrossOrientation | None = field(default=None, repr=False)
    angle: float | None = field(default=None, repr=False)

    def get_default_alignment(self) -> dict:
        from build123_timber.alignment import (
            ConnectionPoint, TimberFace, CrossOrientation
        )
        defaults = {
            JointTopology.L: {
                "main_point": ConnectionPoint.end(),
                "main_face": TimberFace.END,
                "cross_point": ConnectionPoint.start(),
                "cross_face": TimberFace.START,
                "orientation": CrossOrientation.PERPENDICULAR,
                "angle": 90.0,
            },
            JointTopology.T: {
                "main_point": ConnectionPoint.center(),
                "main_face": TimberFace.TOP,
                "cross_point": ConnectionPoint.end(),
                "cross_face": TimberFace.END,
                "orientation": CrossOrientation.PERPENDICULAR,
                "angle": 90.0,
            },
            JointTopology.X: {
                "main_point": ConnectionPoint.center(),
                "main_face": TimberFace.TOP,
                "cross_point": ConnectionPoint.center(),
                "cross_face": TimberFace.BOTTOM,
                "orientation": CrossOrientation.PERPENDICULAR,
                "angle": 90.0,
            },
            JointTopology.I: {
                "main_point": ConnectionPoint.end(),
                "main_face": TimberFace.END,
                "cross_point": ConnectionPoint.start(),
                "cross_face": TimberFace.START,
                "orientation": CrossOrientation.PARALLEL,
                "angle": 0.0,
            },
        }
        return defaults.get(self.topology, defaults[JointTopology.T])

    def align(self) -> Joint:
        from build123_timber.alignment import (
            JointAlignment, ConnectionPoint, TimberFace, CrossOrientation
        )

        defaults = self.get_default_alignment()

        if isinstance(self.main_point, (int, float)):
            main_pt = ConnectionPoint.at(float(self.main_point))
        elif self.main_point is not None:
            main_pt = self.main_point
        else:
            main_pt = defaults["main_point"]

        if isinstance(self.cross_point, (int, float)):
            cross_pt = ConnectionPoint.at(float(self.cross_point))
        elif self.cross_point is not None:
            cross_pt = self.cross_point
        else:
            cross_pt = defaults["cross_point"]

        alignment = JointAlignment(
            main_point=main_pt,
            main_face=self.main_face if self.main_face is not None else defaults["main_face"],
            cross_point=cross_pt,
            cross_face=self.cross_face if self.cross_face is not None else defaults["cross_face"],
            orientation=self.orientation if self.orientation is not None else defaults["orientation"],
            angle=self.angle if self.angle is not None else defaults["angle"],
        )

        self.cross.location = alignment.compute_cross_location(self.main, self.cross)
        return self

    @abstractmethod
    def get_main_feature(self) -> Part | None:
        ...

    @abstractmethod
    def get_cross_feature(self) -> Part | None:
        ...

    def apply(self) -> tuple[Timber, Timber]:
        if main_feature := self.get_main_feature():
            self.main.add_feature(main_feature)
        if cross_feature := self.get_cross_feature():
            self.cross.add_feature(cross_feature)
        return (self.main, self.cross)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(main={self.main}, cross={self.cross})"
