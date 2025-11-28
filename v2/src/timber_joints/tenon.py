"""Basic tenon - inserting part only (no mortise)."""

from dataclasses import dataclass
from build123d import Part
from timber_joints.beam import Beam
from timber_joints.utils import create_tenon_cut


@dataclass
class Tenon:
    """The positive (inserting) part of a mortise and tenon joint.
    
    Creates a tenon by removing material around it, leaving a centered
    projection at the beam end.
    
    Parameters:
    - beam: The beam to cut the tenon on
    - tenon_width: Width of the tenon (Y direction)
    - tenon_height: Height of the tenon (Z direction)
    - tenon_length: How far the tenon extends from the beam end
    - at_start: If True, create tenon at start (X=0); if False, at end (X=length)
    """
    
    beam: Beam
    tenon_width: float
    tenon_height: float
    tenon_length: float
    at_start: bool = False

    def __post_init__(self) -> None:
        """Validate tenon parameters."""
        if self.tenon_width <= 0 or self.tenon_width > self.beam.width:
            raise ValueError(f"tenon_width must be between 0 and beam width ({self.beam.width})")
        if self.tenon_height <= 0 or self.tenon_height > self.beam.height:
            raise ValueError(f"tenon_height must be between 0 and beam height ({self.beam.height})")
        if self.tenon_length <= 0 or self.tenon_length > self.beam.length:
            raise ValueError(f"tenon_length must be between 0 and beam length ({self.beam.length})")

    @property
    def shape(self) -> Part:
        """Create the tenon by removing material around the centered projection."""
        waste = create_tenon_cut(
            beam_length=self.beam.length,
            beam_width=self.beam.width,
            beam_height=self.beam.height,
            tenon_width=self.tenon_width,
            tenon_height=self.tenon_height,
            tenon_length=self.tenon_length,
            at_start=self.at_start,
        )
        return self.beam.shape - waste

    def __repr__(self) -> str:
        position = "start" if self.at_start else "end"
        return f"Tenon(beam={self.beam}, W={self.tenon_width}, H={self.tenon_height}, L={self.tenon_length}, at_{position})"
