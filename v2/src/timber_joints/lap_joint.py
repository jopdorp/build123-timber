"""Lap joint - positive/inserting part only."""

from dataclasses import dataclass
from build123d import Align, Box, Part, Location
from timber_joints.beam import Beam


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
        # Start with the full beam
        result = self.beam.shape
        
        # Create the material to remove
        # Position at the end of the beam
        x_pos = self.beam.length - self.cut_length
        
        if self.from_top:
            # Cut from top: remove material from top face
            z_pos = self.beam.height - self.cut_depth
            cut = Box(
                self.cut_length,
                self.beam.width,
                self.cut_depth,
                align=(Align.MIN, Align.MIN, Align.MIN)
            )
            cut = cut.move(Location((x_pos, 0, z_pos)))
        else:
            # Cut from bottom: remove material from bottom face
            cut = Box(
                self.cut_length,
                self.beam.width,
                self.cut_depth,
                align=(Align.MIN, Align.MIN, Align.MIN)
            )
            cut = cut.move(Location((x_pos, 0, 0)))
        
        return result - cut

    def __repr__(self) -> str:
        side = "top" if self.from_top else "bottom"
        return f"LapJoint(beam={self.beam}, depth={self.cut_depth}, length={self.cut_length}, from_{side})"
