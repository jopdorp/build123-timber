from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from build123d import Align, Box, Location, Part, Plane, Vector

if TYPE_CHECKING:
    from build123_timber.joints.base import Joint


@dataclass
class Timber:
    """A timber element with rectangular cross-section.

    Local coordinate system:
    - X: along the length
    - Y: along the width
    - Z: along the height

    Origin at corner (0,0,0), timber extends in positive X, Y, Z directions.
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
        """Create a horizontal beam (length along X)."""
        return cls(length=length, width=width, height=height, **kwargs)

    @classmethod
    def post(cls, length: float, width: float, height: float | None = None, **kwargs) -> Timber:
        """Create a vertical post (length along Z).
        
        The post is rotated so local X (length) points along world Z (up).
        """
        loc = kwargs.pop("location", Location())
        # Rotate -90° around Y to point length (local X) upward (world Z)
        rotation = Location((0, 0, 0), (0, -90, 0))
        return cls(length=length, width=width, height=height or width, location=loc * rotation, **kwargs)

    @classmethod
    def rafter(cls, length: float, width: float, height: float, pitch: float = 30.0, **kwargs) -> Timber:
        """Create a rafter with roof pitch angle.
        
        The rafter is rotated around Y axis by the pitch angle, so it slopes upward
        from start (low) to end (high), like a roof member going from eave to ridge.
        
        Args:
            pitch: Roof pitch angle in degrees (default 30°). 0 = horizontal.
        """
        kwargs.setdefault("category", "rafter")
        loc = kwargs.pop("location", Location())
        # Rotate around Y axis to create roof pitch (negative to slope upward toward +X)
        rotation = Location((0, 0, 0), (0, -pitch, 0))
        return cls(length=length, width=width, height=height, location=loc * rotation, **kwargs)

    @classmethod
    def joist(cls, length: float, width: float, height: float, **kwargs) -> Timber:
        """Create a horizontal joist (length along X)."""
        kwargs.setdefault("category", "joist")
        return cls(length=length, width=width, height=height, **kwargs)

    @classmethod
    def stud(cls, length: float, width: float, height: float, **kwargs) -> Timber:
        """Create a vertical stud (length along Z).
        
        The stud is rotated so local X (length) points along world Z (up).
        """
        kwargs.setdefault("category", "stud")
        loc = kwargs.pop("location", Location())
        # Rotate -90° around Y to point length (local X) upward (world Z)
        rotation = Location((0, 0, 0), (0, -90, 0))
        return cls(length=length, width=width, height=height, location=loc * rotation, **kwargs)

    @classmethod
    def girt(cls, length: float, width: float, height: float, **kwargs) -> Timber:
        """Create a horizontal girt (length along Y).
        
        A girt is a horizontal member in wall framing that connects posts,
        running perpendicular to the main span direction.
        Rotated 90° around Z so local X (length) points along world Y.
        """
        kwargs.setdefault("category", "girt")
        loc = kwargs.pop("location", Location())
        # Rotate 90° around Z to point length (local X) along world Y
        rotation = Location((0, 0, 0), (0, 0, 90))
        return cls(length=length, width=width, height=height, location=loc * rotation, **kwargs)

    @classmethod
    def purlin(cls, length: float, width: float, height: float, **kwargs) -> Timber:
        """Create a horizontal purlin (length along Y).
        
        A purlin is a horizontal roof member running perpendicular to rafters,
        supporting roof sheathing. Runs along the length of the building.
        Rotated 90° around Z so local X (length) points along world Y.
        """
        kwargs.setdefault("category", "purlin")
        loc = kwargs.pop("location", Location())
        # Rotate 90° around Z to point length (local X) along world Y
        rotation = Location((0, 0, 0), (0, 0, 90))
        return cls(length=length, width=width, height=height, location=loc * rotation, **kwargs)

    @classmethod
    def plate(cls, length: float, width: float, height: float, **kwargs) -> Timber:
        """Create a horizontal plate (length along Y).
        
        A plate is a horizontal member at top or bottom of wall framing
        (top plate, bottom plate / sole plate). Runs along the wall length.
        Rotated 90° around Z so local X (length) points along world Y.
        """
        kwargs.setdefault("category", "plate")
        loc = kwargs.pop("location", Location())
        # Rotate 90° around Z to point length (local X) along world Y
        rotation = Location((0, 0, 0), (0, 0, 90))
        return cls(length=length, width=width, height=height, location=loc * rotation, **kwargs)

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
        return Box(self.length, self.width, self.height, align=(Align.MIN, Align.MIN, Align.MIN))

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
            "top": Plane((self.length / 2, self.width / 2, self.height), x_dir=(1, 0, 0), z_dir=(0, 0, 1)),
            "bottom": Plane((self.length / 2, self.width / 2, 0), x_dir=(1, 0, 0), z_dir=(0, 0, -1)),
            "left": Plane((self.length / 2, 0, self.height / 2), x_dir=(1, 0, 0), z_dir=(0, -1, 0)),
            "right": Plane((self.length / 2, self.width, self.height / 2), x_dir=(1, 0, 0), z_dir=(0, 1, 0)),
            "start": Plane((0, self.width / 2, self.height / 2), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)),
            "end": Plane((self.length, self.width / 2, self.height / 2), x_dir=(0, 1, 0), z_dir=(1, 0, 0)),
        }
        if face not in planes:
            raise ValueError(f"Unknown face '{face}'. Use: {list(planes.keys())}")
        return planes[face]

    def __repr__(self) -> str:
        name_str = f"'{self.name}' " if self.name else ""
        return f"Timber({name_str}L={self.length}, W={self.width}, H={self.height})"


Beam = Timber.beam
Post = Timber.post
