"""
Brace Tenon Joint for diagonal timber braces.

The brace tenon is a shouldered tenon with release cuts that allow the tenon
to fit cleanly into the receiving member (post or beam).

CRITICAL GEOMETRY:
- The brace is horizontal (axis-aligned along X) when these cuts are made
- The shoulder creates an angled bearing surface
- Release cuts must be VERTICAL after rotation (aligned with the receiving member)
- This means: on the horizontal brace, release cuts are at the BRACE ANGLE

Release cuts:
1. Side release: A vertical plane (after rotation) that starts at the shoulder edge
   and runs along the side of the tenon. This prevents the tenon sides from
   binding against the mortise walls.
   
2. Tip release: A vertical plane (after rotation) at the tenon tip that creates
   clearance for the tenon to seat properly.

These cuts are made as angled wedges on the horizontal brace, so that after
rotation they become vertical relief cuts.
"""

import math
from dataclasses import dataclass, field
from typing import Union, TYPE_CHECKING
from build123d import Part, Polyline, make_face, extrude, Box, Location
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
    
    The tenon is always FULL HEIGHT of the brace to simplify the joint geometry.
    
    Args:
        brace: The brace (PositionedBrace object or Part)
        tenon_width: Width of tenon (Y direction, typically 1/3 brace width)
        tenon_length: How far tenon projects (60-100mm typical)
        brace_angle: Angle from horizontal in degrees (optional if brace is PositionedBrace)
        at_start: If True, tenon at start; if False, at end
    """

    brace: Union[Part, "PositionedBrace"]
    tenon_width: float
    tenon_length: float
    brace_angle: float = None  # degrees, read from PositionedBrace if not provided
    at_start: bool = True

    # Computed fields
    shape: Part = field(init=False, repr=False)
    rotated_cut_bbox_height: float = field(init=False, repr=False)
    rotated_cut_bbox_width: float = field(init=False, repr=False)
    tenon_height: float = field(init=False, repr=False)  # Computed as full brace height

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
        
        self.shape, self.rotated_cut_bbox_height, self.rotated_cut_bbox_width = self._create_brace_tenon()

    def _create_release_cuts(
        self, 
        brace_length: float,
        brace_width: float, 
        brace_height: float,
        shoulder_depth: float,
    ) -> Part:
        """Create release cuts on the tenon tip.
        
        Simple approach: create a box at the tenon tip, rotate it by the
        brace angle, then subtract. This creates a cut that will be 
        vertical after the brace is rotated into position.
        
        For at_start=False, we mirror the shape around the center of the brace.
        """
        from build123d import Axis, Align, Plane
        
        # Release cut box size - make it big enough
        release_size = brace_height * 2

        # Create release box for at_start=True case
        # Tenon tip at X=0, rotation pivot at (0, 0, 0)
        # Box aligned with max X at 0, min Z at 0 (sitting at bottom-left corner)
        release_box = Box(release_size, brace_width, release_size, 
                        align=(Align.MAX, Align.MIN, Align.MIN))
        # Rotate positive angle (CCW) - box swings up into the tenon
        release_box = release_box.rotate(Axis.Y, self.brace_angle)
        
        if not self.at_start:
            # Mirror around the center of the brace (YZ plane at X=brace_length/2)
            mirror_plane = Plane.YZ.offset(brace_length / 2)
            release_box = release_box.mirror(mirror_plane)
            
        return Part(release_box.wrapped)

    def _create_brace_tenon(self) -> tuple[Part, float, float]:
        """
        Apply shouldered tenon to the axis-aligned brace.
        The shoulder depth is calculated from the brace angle.
        Tenon is always full height of the brace.
        
        Returns:
            (shape, rotated_cut_bbox_height, rotated_cut_bbox_width) - the cut brace and penetration depths
        """
        brace_shape = self._brace_shape
        
        # Get dimensions of brace
        _, brace_length, brace_width, brace_height = get_shape_dimensions(brace_shape)
        
        # Tenon is full height
        self.tenon_height = brace_height
        
        # Calculate shoulder depth from brace angle
        angle_rad = math.radians(self.brace_angle)
        shoulder_depth = brace_height * math.tan(angle_rad)
        
        # Apply shouldered tenon with full height
        shouldered = ShoulderedTenon(
            beam=brace_shape,
            tenon_width=self.tenon_width,
            tenon_height=brace_height,  # Full height
            tenon_length=self.tenon_length,
            shoulder_depth=shoulder_depth,
            at_start=self.at_start,
        )
        
        # Get the base shape with shoulder
        result_shape = shouldered.shape
        
        # Create and apply release cuts
        release_cuts = self._create_release_cuts(
            brace_length, brace_width, brace_height, shoulder_depth
        )
        
        result_shape = result_shape - release_cuts
        
        return result_shape, shouldered.rotated_cut_bbox_height, shouldered.rotated_cut_bbox_width

