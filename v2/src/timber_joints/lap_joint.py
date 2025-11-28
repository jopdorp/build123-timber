"""Lap joint - positive/inserting part only."""

from dataclasses import dataclass
from build123d import Part
from timber_joints.beam import Beam
from timber_joints.utils import create_lap_cut


@dataclass
class LapJoint:
    """The positive (inserting) part of a lap joint.
    
    This is the beam end that has material removed from one side,
    allowing it to insert into a matching cut in another beam.
    
    Parameters:
    - beam: The beam to cut the lap joint on
    - cut_depth: How deep to cut into the beam (typically half the beam height)
    - cut_length: How long the lap cut extends along the beam
    - from_top: If True, cut from top face; if False, cut from bottom face
    """
    
    beam: Beam
    cut_depth: float
    cut_length: float
    from_top: bool = True

    def __post_init__(self) -> None:
        """Validate lap joint parameters."""
        if self.cut_depth <= 0 or self.cut_depth >= self.beam.height:
            raise ValueError(f"cut_depth must be between 0 and beam height ({self.beam.height})")
        if self.cut_length <= 0 or self.cut_length > self.beam.length:
            raise ValueError(f"cut_length must be between 0 and beam length ({self.beam.length})")

    @property
    def shape(self) -> Part:
        """Create the lap joint shape by removing material from beam end."""
        result = self.beam.shape
        
        # Cut at end of beam
        x_pos = self.beam.length - self.cut_length
        
        cut = create_lap_cut(
            beam_width=self.beam.width,
            beam_height=self.beam.height,
            cut_depth=self.cut_depth,
            cut_length=self.cut_length,
            x_position=x_pos,
            from_top=self.from_top,
        )
        
        return result - cut

    def __repr__(self) -> str:
        side = "top" if self.from_top else "bottom"
        return f"LapJoint(beam={self.beam}, depth={self.cut_depth}, length={self.cut_length}, from_{side})"
