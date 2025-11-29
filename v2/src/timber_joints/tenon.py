"""Basic tenon - inserting part only (no mortise)."""

from dataclasses import dataclass, field
from typing import Union
from build123d import Part
from timber_joints.beam import Beam
from timber_joints.utils import create_tenon_cut, get_shape_dimensions


@dataclass
class Tenon:
    """The positive (inserting) part of a mortise and tenon joint.
    
    Creates a tenon by removing material around it, leaving a centered
    projection at the beam end.
    
    Parameters:
    - beam: The beam (Beam object or Part) to cut the tenon on
    - tenon_width: Width of the tenon (Y direction)
    - tenon_height: Height of the tenon (Z direction)
    - tenon_length: How far the tenon extends from the beam end
    - at_start: If True, create tenon at start (X=0); if False, at end (X=length)
    """
    
    beam: Union[Beam, Part]
    tenon_width: float
    tenon_height: float
    tenon_length: float
    at_start: bool = False
    
    # Computed dimensions (from bounding box)
    _input_shape: Part = field(init=False, repr=False)
    _length: float = field(init=False, repr=False)
    _width: float = field(init=False, repr=False)
    _height: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate tenon parameters."""
        self._input_shape, self._length, self._width, self._height = get_shape_dimensions(self.beam)
        
        if self.tenon_width <= 0 or self.tenon_width > self._width:
            raise ValueError(f"tenon_width must be between 0 and beam width ({self._width})")
        if self.tenon_height <= 0 or self.tenon_height > self._height:
            raise ValueError(f"tenon_height must be between 0 and beam height ({self._height})")
        if self.tenon_length <= 0 or self.tenon_length > self._length:
            raise ValueError(f"tenon_length must be between 0 and beam length ({self._length})")

    @property
    def shape(self) -> Part:
        """Create the tenon by removing material around the centered projection."""
        waste = create_tenon_cut(
            beam_length=self._length,
            beam_width=self._width,
            beam_height=self._height,
            tenon_width=self.tenon_width,
            tenon_height=self.tenon_height,
            tenon_length=self.tenon_length,
            at_start=self.at_start,
        )
        return self._input_shape - waste

    def __repr__(self) -> str:
        position = "start" if self.at_start else "end"
        return f"Tenon(beam={self.beam}, W={self.tenon_width}, H={self.tenon_height}, L={self.tenon_length}, at_{position})"
