"""Simplified Beam class for timber joints."""

from dataclasses import dataclass
from build123d import Align, Box, Part


@dataclass
class Beam:
    """A rectangular timber beam.

    Local coordinate system:
    - X: along the length
    - Y: along the width
    - Z: along the height

    Origin at corner (0,0,0), beam extends in positive X, Y, Z directions.
    """

    length: float
    width: float
    height: float

    def __post_init__(self) -> None:
        """Validate beam dimensions."""
        for dim, val in [("length", self.length), ("width", self.width), ("height", self.height)]:
            if val <= 0:
                raise ValueError(f"{dim} must be positive, got {val}")

    @property
    def shape(self) -> Part:
        """Create the solid beam shape."""
        return Box(
            self.length,
            self.width,
            self.height,
            align=(Align.MIN, Align.MIN, Align.MIN)
        )

    def __repr__(self) -> str:
        return f"Beam(L={self.length}, W={self.width}, H={self.height})"
