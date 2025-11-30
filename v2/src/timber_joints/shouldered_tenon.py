"""Shouldered tenon - tenon with angled shoulder (no mortise/housing)."""

import math
from dataclasses import dataclass
from build123d import Part, Polyline, make_face, extrude, Axis, Location
from timber_joints.base_joint import BaseJoint
from timber_joints.utils import create_tenon_cut


@dataclass
class ShoulderedTenon(BaseJoint):
    """A tenon with an angled shoulder - inserting part only.
    
    Creates a tenon with a triangular/angled shoulder. The shoulder surface
    is angled - one side is at the tenon base (flush), the other side is 
    cut back by shoulder_depth. This creates a wedge-shaped shoulder.
    
    Parameters:
    - beam: The beam (Beam object or Part) to cut the shouldered tenon on
    - tenon_width: Width of the tenon projection (Y direction)
    - tenon_height: Height of the tenon projection (Z direction)
    - tenon_length: How far the tenon extends from the flush side of shoulder
    - shoulder_depth: Depth of the angled shoulder at the deep side
    - at_start: If True, create at start (X=0); if False, at end (X=length)
    """
    
    tenon_width: float
    tenon_height: float
    tenon_length: float
    shoulder_depth: float = 15.0
    at_start: bool = False

    def __post_init__(self) -> None:
        """Validate shouldered tenon parameters."""
        super().__post_init__()
        
        if self.tenon_width <= 0 or self.tenon_width > self._width:
            raise ValueError(f"tenon_width must be between 0 and beam width ({self._width})")
        if self.tenon_height <= 0 or self.tenon_height > self._height:
            raise ValueError(f"tenon_height must be between 0 and beam height ({self._height})")
        if self.tenon_length <= 0:
            raise ValueError("tenon_length must be positive")
        if self.shoulder_depth <= 0:
            raise ValueError("shoulder_depth must be positive")
        
        total_length = self.tenon_length + self.shoulder_depth
        if total_length > self._length:
            raise ValueError(f"Total length (tenon + shoulder = {total_length}) exceeds beam length ({self._length})")

    def _create_shoulder_wedge(self, x_deep: float, x_flush: float) -> Part:
        """Create the triangular wedge shape for the angled shoulder.
        
        The wedge is deeper at bottom (Z=0), flush at top (Z=height).
        """
        # Triangular wedge: deep at bottom (Z=0), flush at top
        # Points ordered counter-clockwise when viewed from +Y
        profile_points = [
            (x_deep, 0, 0),                # Deep X, bottom Z
            (x_deep, 0, self._height),     # Deep X, top Z
            (x_flush, 0, 0),               # Flush X, bottom Z (angled edge)
        ]
        
        wire = Polyline(profile_points, close=True)
        face = make_face(wire)
        # Extrude in +Y direction across beam width
        wedge = extrude(face, amount=self._width)
        return Part(wedge.wrapped)

    @property
    def shape(self) -> Part:
        """Create the shouldered tenon with angled shoulder."""
        # Calculate positions
        if self.at_start:
            x_deep = 0
            x_flush = self.shoulder_depth
        else:
            x_flush = self._length - self.tenon_length
            x_deep = x_flush - self.shoulder_depth
        
        # Get the tenon cut (material around the tenon portion)
        tenon_waste = create_tenon_cut(
            beam_length=self._length,
            beam_width=self._width,
            beam_height=self._height,
            tenon_width=self.tenon_width,
            tenon_height=self.tenon_height,
            tenon_length=self.tenon_length + self.shoulder_depth,
            at_start=self.at_start,
        )
        
        # Create the shoulder wedge (material to keep, not cut)
        shoulder_wedge = self._create_shoulder_wedge(x_deep, x_flush)
        if self.at_start:
            # Rotate 180° around Z to flip the shoulder angle direction
            shoulder_wedge = shoulder_wedge.rotate(Axis.Z, 180)
            # After rotation, wedge is at negative X and Y - move it back to align with tenon waste
            bbox = shoulder_wedge.bounding_box()
            tenon_waste_bbox = tenon_waste.bounding_box()
            shoulder_wedge = shoulder_wedge.move(Location((tenon_waste_bbox.max.X - bbox.max.X, -bbox.min.Y, 0)))
        # Final cut = tenon waste - shoulder wedge (don't cut the wedge area)
        final_cut = tenon_waste - shoulder_wedge
        
        return self._input_shape - final_cut

    @property 
    def shoulder_angle(self) -> float:
        """Return the shoulder angle in degrees."""
        return math.degrees(math.atan2(self.shoulder_depth, self._height))

    @property
    def rotated_cut_bbox_height(self) -> float:
        """Return the vertical penetration depth when the tenon is rotated by shoulder angle.
        
        This is how far the brace end extends vertically (Z) when the brace is tilted.
        Use this for penetration into horizontal members (beams/girts).
        Includes both tenon_length and shoulder_depth.
        """
        angle_rad = math.radians(self.shoulder_angle)
        total_cut_length = self.tenon_length + self.shoulder_depth
        return total_cut_length * math.sin(angle_rad)

    @property
    def rotated_cut_bbox_width(self) -> float:
        """Return the horizontal penetration depth when the tenon is rotated by shoulder angle.
        
        This is how far the brace end extends horizontally (X or Y) when the brace is tilted.
        Use this for penetration into vertical members (posts).
        Includes both tenon_length and shoulder_depth.
        """
        angle_rad = math.radians(self.shoulder_angle)
        total_cut_length = self.tenon_length + self.shoulder_depth
        return total_cut_length * math.cos(angle_rad)

    def __repr__(self) -> str:
        position = "start" if self.at_start else "end"
        return f"ShoulderedTenon(beam={self.beam}, tenon={self.tenon_width}x{self.tenon_height}x{self.tenon_length}, shoulder_depth={self.shoulder_depth}, at_{position})"
