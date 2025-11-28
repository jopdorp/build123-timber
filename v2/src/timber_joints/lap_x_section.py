"""Lap joint at a cross-section point along the beam."""

from dataclasses import dataclass
from build123d import Part
from timber_joints.beam import Beam
from timber_joints.utils import create_lap_cut


@dataclass
class LapXSection:
    """A lap joint cut at a specific point along the beam (not at the end).
    
    Creates a lap cut centered around a specified X position along the beam.
    This is useful for cross-lap joints where two beams intersect.
    
    Parameters:
    - beam: The beam to cut the lap on
    - cut_depth: How deep to cut (from top or bottom)
    - cut_length: Length of the cut along X axis
    - x_position: Center point of the lap cut along the beam length
    - from_top: If True, cut from top; if False, cut from bottom
    """
    
    beam: Beam
    cut_depth: float
    cut_length: float
    x_position: float
    from_top: bool = True

    def __post_init__(self) -> None:
        """Validate lap parameters."""
        if self.cut_depth <= 0 or self.cut_depth >= self.beam.height:
            raise ValueError(f"cut_depth must be between 0 and beam height ({self.beam.height})")
        if self.cut_length <= 0:
            raise ValueError("cut_length must be positive")
        
        # Check that the cut fits within the beam
        half_length = self.cut_length / 2
        if self.x_position - half_length < 0:
            raise ValueError(f"Lap cut extends past beam start (x_position={self.x_position}, cut_length={self.cut_length})")
        if self.x_position + half_length > self.beam.length:
            raise ValueError(f"Lap cut extends past beam end (x_position={self.x_position}, cut_length={self.cut_length})")

    @property
    def shape(self) -> Part:
        """Create the beam with a lap cut at the specified cross-section."""
        result = self.beam.shape
        
        # Calculate X start position (centered on x_position)
        x_start = self.x_position - self.cut_length / 2
        
        cut = create_lap_cut(
            beam_width=self.beam.width,
            beam_height=self.beam.height,
            cut_depth=self.cut_depth,
            cut_length=self.cut_length,
            x_position=x_start,
            from_top=self.from_top,
        )
        
        return result - cut

    def __repr__(self) -> str:
        direction = "top" if self.from_top else "bottom"
        return f"LapXSection(beam={self.beam}, depth={self.cut_depth}, length={self.cut_length}, at_x={self.x_position}, from_{direction})"
