"""Basic tenon - inserting part only (no mortise)."""

from dataclasses import dataclass
from build123d import Part
from timber_joints.base_joint import BaseJoint
from timber_joints.utils import create_tenon_cut


@dataclass
class Tenon(BaseJoint):
    """Centered tenon projection at beam end (removes material around the tenon)."""
    
    tenon_width: float
    tenon_height: float
    tenon_length: float
    at_start: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        
        if self.tenon_width <= 0 or self.tenon_width > self._width:
            raise ValueError(f"tenon_width must be between 0 and beam width ({self._width})")
        if self.tenon_height <= 0 or self.tenon_height > self._height:
            raise ValueError(f"tenon_height must be between 0 and beam height ({self._height})")
        if self.tenon_length <= 0 or self.tenon_length > self._length:
            raise ValueError(f"tenon_length must be between 0 and beam length ({self._length})")

    @property
    def shape(self) -> Part:
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
