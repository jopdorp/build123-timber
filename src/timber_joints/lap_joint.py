"""Lap joint - positive/inserting part only."""

from dataclasses import dataclass
from build123d import Part
from timber_joints.base_joint import BaseJoint
from timber_joints.utils import create_lap_cut


@dataclass
class LapJoint(BaseJoint):
    """Beam end with material removed from one side for lap joints."""
    
    cut_depth: float
    cut_length: float
    from_top: bool = True
    at_start: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        
        if self.cut_depth <= 0 or self.cut_depth >= self._height:
            raise ValueError(f"cut_depth must be between 0 and beam height ({self._height})")
        if self.cut_length <= 0 or self.cut_length > self._length:
            raise ValueError(f"cut_length must be between 0 and beam length ({self._length})")

    @property
    def shape(self) -> Part:
        if self.at_start:
            x_pos = 0
        else:
            x_pos = self._length - self.cut_length
        
        cut = create_lap_cut(
            beam_width=self._width,
            beam_height=self._height,
            cut_depth=self.cut_depth,
            cut_length=self.cut_length,
            x_position=x_pos,
            from_top=self.from_top,
        )
        
        return self._input_shape - cut

    def __repr__(self) -> str:
        side = "top" if self.from_top else "bottom"
        position = "start" if self.at_start else "end"
        return f"LapJoint(beam={self.beam}, depth={self.cut_depth}, length={self.cut_length}, from_{side}, at_{position})"
