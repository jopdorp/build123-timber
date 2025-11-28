"""Shouldered tenon - tenon with angled shoulder (no mortise/housing)."""

from dataclasses import dataclass
from build123d import Part, Polyline, make_face, extrude
from timber_joints.beam import Beam
from timber_joints.utils import create_tenon_cut


@dataclass
class ShoulderedTenon:
    """A tenon with an angled shoulder - inserting part only.
    
    Creates a tenon with a triangular/angled shoulder. The shoulder surface
    is angled - one side is at the tenon base (flush), the other side is 
    cut back by shoulder_depth. This creates a wedge-shaped shoulder.
    
    Parameters:
    - beam: The beam to cut the shouldered tenon on
    - tenon_width: Width of the tenon projection (Y direction)
    - tenon_height: Height of the tenon projection (Z direction)
    - tenon_length: How far the tenon extends from the flush side of shoulder
    - shoulder_depth: Depth of the angled shoulder at the deep side
    - at_start: If True, create at start (X=0); if False, at end (X=length)
    """
    
    beam: Beam
    tenon_width: float
    tenon_height: float
    tenon_length: float
    shoulder_depth: float = 15.0
    at_start: bool = False

    def __post_init__(self) -> None:
        """Validate shouldered tenon parameters."""
        if self.tenon_width <= 0 or self.tenon_width > self.beam.width:
            raise ValueError(f"tenon_width must be between 0 and beam width ({self.beam.width})")
        if self.tenon_height <= 0 or self.tenon_height > self.beam.height:
            raise ValueError(f"tenon_height must be between 0 and beam height ({self.beam.height})")
        if self.tenon_length <= 0:
            raise ValueError("tenon_length must be positive")
        if self.shoulder_depth <= 0:
            raise ValueError("shoulder_depth must be positive")
        
        total_length = self.tenon_length + self.shoulder_depth
        if total_length > self.beam.length:
            raise ValueError(f"Total length (tenon + shoulder = {total_length}) exceeds beam length ({self.beam.length})")

    def _create_shoulder_wedge(self, x_deep: float, x_flush: float) -> Part:
        """Create the triangular wedge shape for the angled shoulder.
        
        The wedge is deeper at bottom (Z=0), flush at top (Z=height).
        """
        # Triangular wedge: deep at bottom (Z=0), flush at top
        # Points ordered counter-clockwise when viewed from +Y
        profile_points = [
            (x_deep, 0, 0),                     # Deep X, bottom Z
            (x_deep, 0, self.beam.height),     # Deep X, top Z
            (x_flush, 0, 0),                    # Flush X, bottom Z (angled edge)
        ]
        
        wire = Polyline(profile_points, close=True)
        face = make_face(wire)
        # Extrude in +Y direction across beam width
        wedge = extrude(face, amount=self.beam.width)
        return Part(wedge.wrapped)

    @property
    def shape(self) -> Part:
        """Create the shouldered tenon with angled shoulder."""
        # Calculate positions
        if self.at_start:
            x_deep = 0
            x_flush = self.shoulder_depth
        else:
            x_flush = self.beam.length - self.tenon_length
            x_deep = x_flush - self.shoulder_depth
        
        # Get the tenon cut (material around the tenon portion)
        tenon_waste = create_tenon_cut(
            beam_length=self.beam.length,
            beam_width=self.beam.width,
            beam_height=self.beam.height,
            tenon_width=self.tenon_width,
            tenon_height=self.tenon_height,
            tenon_length=self.tenon_length + self.shoulder_depth,
            at_start=self.at_start,
        )
        
        # Create the shoulder wedge (material to keep, not cut)
        shoulder_wedge = self._create_shoulder_wedge(x_deep, x_flush)
        
        # Final cut = tenon waste - shoulder wedge (don't cut the wedge area)
        final_cut = tenon_waste - shoulder_wedge
        
        return self.beam.shape - final_cut

    def __repr__(self) -> str:
        position = "start" if self.at_start else "end"
        return f"ShoulderedTenon(beam={self.beam}, tenon={self.tenon_width}x{self.tenon_height}x{self.tenon_length}, shoulder_depth={self.shoulder_depth}, at_{position})"
