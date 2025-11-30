"""
Brace Tenon Joint for diagonal timber braces.

The brace tenon is a shouldered tenon with an angled tip cut that matches
the brace angle. This allows the tenon to sit flush against the receiving
member (post or beam) while the shoulder provides bearing surface.

This is applied to a horizontal (axis-aligned) brace BEFORE rotation.
The angle is read from the PositionedBrace or passed explicitly.
"""

import math
from dataclasses import dataclass, field
from typing import Union, TYPE_CHECKING
from build123d import Part
from timber_joints.shouldered_tenon import ShoulderedTenon
from timber_joints.utils import get_shape_dimensions

if TYPE_CHECKING:
    from timber_joints.alignment import PositionedBrace


@dataclass
class BraceTenon:
    """
    Creates a tenon on a brace (applied while brace is horizontal).
    
    The brace should be axis-aligned along X when this is applied.
    The angle is read from the PositionedBrace object or passed explicitly.
    
    Args:
        brace: The brace (PositionedBrace object or Part)
        tenon_width: Width of tenon (typically 1/3 brace width)
        tenon_height: Height of tenon (typically 1/2 brace height)
        tenon_length: How far tenon projects (60-100mm typical)
        brace_angle: Angle from horizontal in degrees (optional if brace is PositionedBrace)
        at_start: If True, tenon at start; if False, at end
    """

    brace: Union[Part, "PositionedBrace"]
    tenon_width: float
    tenon_height: float
    tenon_length: float
    brace_angle: float = None  # degrees, read from PositionedBrace if not provided
    at_start: bool = True

    # Computed field
    shape: Part = field(init=False, repr=False)

    def __post_init__(self):
        # Import here to avoid circular import
        from timber_joints.alignment import PositionedBrace
        
        # Extract angle and shape from PositionedBrace if provided
        if isinstance(self.brace, PositionedBrace):
            if self.brace_angle is None:
                self.brace_angle = self.brace.angle
            self._brace_shape = self.brace.shape
        else:
            if self.brace_angle is None:
                raise ValueError("brace_angle is required when brace is a Part")
            self._brace_shape = self.brace
        
        self.shape = self._create_brace_tenon()

    def _create_brace_tenon(self) -> Part:
        """
        Apply shouldered tenon to the axis-aligned brace.
        The shoulder depth is calculated from the brace angle.
        """
        brace_shape = self._brace_shape
        
        # Get dimensions of brace
        _, brace_length, brace_width, brace_height = get_shape_dimensions(brace_shape)
        
        # Calculate shoulder depth from brace angle
        # The shoulder creates the angled cut at the tenon base
        angle_rad = math.radians(self.brace_angle)
        shoulder_depth = brace_height * math.tan(angle_rad)
        
        # Ensure shoulder_depth + tenon_length fits in brace
        max_total = brace_length / 3
        if shoulder_depth + self.tenon_length > max_total:
            shoulder_depth = max(1.0, max_total - self.tenon_length)
        
        # Apply shouldered tenon
        shouldered = ShoulderedTenon(
            beam=brace_shape,
            tenon_width=self.tenon_width,
            tenon_height=self.tenon_height,
            tenon_length=self.tenon_length,
            shoulder_depth=shoulder_depth,
            at_start=self.at_start,
        )
        
        return shouldered.shape

