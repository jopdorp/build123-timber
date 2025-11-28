from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from build123d import Box, Location, Part, Plane, Vector

if TYPE_CHECKING:
    from build123_timber.joints.base import Joint


@dataclass
class Timber:
    """A timber element with rectangular cross-section.

    Local coordinate system:
    - X: along the centerline (length)
    - Y: along the width
    - Z: along the height

    Origin at start of centerline, centered on cross-section.
    """

    length: float
    width: float
    height: float
    category: str = ""
    name: str = ""
    location: Location = field(default_factory=Location)
    _features: list[Part] = field(default_factory=list, repr=False)
    _joints: list[Joint] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        for dim, val in [("length", self.length), ("width", self.width), ("height", self.height)]:
            if val <= 0:
                raise ValueError(f"{dim} must be positive, got {val}")

    @classmethod
    def beam(cls, length: float, width: float, height: float, **kwargs) -> Timber:
        return cls(length=length, width=width, height=height, **kwargs)

    @classmethod
    def post(cls, length: float, width: float, height: float | None = None, **kwargs) -> Timber:
        return cls(length=length, width=width, height=height or width, **kwargs)

    @classmethod
    def rafter(cls, length: float, width: float, height: float, **kwargs) -> Timber:
        kwargs.setdefault("category", "rafter")
        return cls(length=length, width=width, height=height, **kwargs)

    @classmethod
    def joist(cls, length: float, width: float, height: float, **kwargs) -> Timber:
        kwargs.setdefault("category", "joist")
        return cls(length=length, width=width, height=height, **kwargs)

    @classmethod
    def stud(cls, length: float, width: float, height: float, **kwargs) -> Timber:
        kwargs.setdefault("category", "stud")
        return cls(length=length, width=width, height=height, **kwargs)

    @property
    def centerline(self) -> tuple[Vector, Vector]:
        return (Vector(0, 0, 0), Vector(self.length, 0, 0))

    @property
    def cross_section_area(self) -> float:
        return self.width * self.height

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height

    @property
    def blank(self) -> Part:
        return Box(self.length, self.width, self.height, align=("MIN", "CENTER", "CENTER"))

    @property
    def shape(self) -> Part:
        result = self.blank
        for feature in self._features:
            result = result - feature
        return result

    @property
    def global_shape(self) -> Part:
        return self.shape.move(self.location)

    def add_feature(self, feature: Part) -> None:
        self._features.append(feature)

    def clear_features(self) -> None:
        self._features.clear()

    def moved(self, loc: Location) -> Timber:
        new = Timber(
            length=self.length,
            width=self.width,
            height=self.height,
            category=self.category,
            name=self.name,
            location=self.location * loc,
        )
        new._features = self._features.copy()
        new._joints = self._joints.copy()
        return new

    def get_face_plane(self, face: str) -> Plane:
        planes = {
            "top": Plane((self.length / 2, 0, self.height / 2), x_dir=(1, 0, 0), z_dir=(0, 0, 1)),
            "bottom": Plane((self.length / 2, 0, -self.height / 2), x_dir=(1, 0, 0), z_dir=(0, 0, -1)),
            "left": Plane((self.length / 2, -self.width / 2, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0)),
            "right": Plane((self.length / 2, self.width / 2, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0)),
            "start": Plane((0, 0, 0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)),
            "end": Plane((self.length, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)),
        }
        if face not in planes:
            raise ValueError(f"Unknown face '{face}'. Use: {list(planes.keys())}")
        return planes[face]

    def __repr__(self) -> str:
        name_str = f"'{self.name}' " if self.name else ""
        return f"Timber({name_str}L={self.length}, W={self.width}, H={self.height})"


Beam = Timber.beam
Post = Timber.post
