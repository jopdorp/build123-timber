"""Shouldered tenon - tenon with angled shoulder (no mortise/housing)."""

import math
from dataclasses import dataclass
from build123d import Part, Polyline, make_face, extrude, Axis, Location
from timber_joints.base_joint import BaseJoint
from timber_joints.utils import create_tenon_cut


@dataclass
class ShoulderedTenon(BaseJoint):
    """Tenon with an angled (wedge-shaped) shoulder.
    
    The shoulder surface is angled - one side flush with tenon base,
    the other cut back by shoulder_depth. Creates a wedge-shaped shoulder.
    """
    
    tenon_width: float
    tenon_height: float
    tenon_length: float
    shoulder_depth: float = 15.0
    at_start: bool = False

    def __post_init__(self) -> None:
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
        """Create the triangular wedge shape for the angled shoulder (deeper at Z=0, flush at Z=height)."""
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
        if self.at_start:
            x_deep = self._bbox_min_x
            x_flush = self._bbox_min_x + self.shoulder_depth
        else:
            x_flush = self._bbox_max_x - self.tenon_length
            x_deep = x_flush - self.shoulder_depth
        
        # Get the tenon cut (material around the tenon portion)
        # create_tenon_cut works on a normalized beam, so we need to offset the result
        tenon_waste = create_tenon_cut(
            beam_length=self._length,
            beam_width=self._width,
            beam_height=self._height,
            tenon_width=self.tenon_width,
            tenon_height=self.tenon_height,
            tenon_length=self.tenon_length + self.shoulder_depth,
            at_start=self.at_start,
        )
        # Move tenon_waste to account for bbox offset
        tenon_waste = tenon_waste.move(Location((self._bbox_min_x, 0, 0)))
        
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
        return math.degrees(math.atan2(self.shoulder_depth, self._height))

    @property
    def rotated_cut_bbox_height(self) -> float:
        """Vertical penetration depth when tenon is rotated by shoulder angle (for horizontal members)."""
        angle_rad = math.radians(self.shoulder_angle)
        total_cut_length = self.tenon_length + self.shoulder_depth
        return total_cut_length * math.sin(angle_rad)

    @property
    def rotated_cut_bbox_width(self) -> float:
        """Horizontal penetration depth when tenon is rotated by shoulder angle (for vertical members)."""
        angle_rad = math.radians(self.shoulder_angle)
        total_cut_length = self.tenon_length + self.shoulder_depth
        return total_cut_length * math.cos(angle_rad)

    def __repr__(self) -> str:
        position = "start" if self.at_start else "end"
        return f"ShoulderedTenon(beam={self.beam}, tenon={self.tenon_width}x{self.tenon_height}x{self.tenon_length}, shoulder_depth={self.shoulder_depth}, at_{position})"
