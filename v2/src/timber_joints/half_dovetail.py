"""Half-dovetail joint - dovetail insert at top or bottom of beam."""

from dataclasses import dataclass
from build123d import Align, Box, Part, Location
from timber_joints.beam import Beam
from timber_joints.utils import create_dovetail_cut


@dataclass
class HalfDovetail:
    """A half-dovetail - dovetail insert positioned at top or bottom of beam.
    
    Same as DovetailInsert but at top/bottom instead of centered.
    
    Parameters:
    - beam: The beam to cut the half-dovetail on
    - dovetail_width: Width at the narrow end (base)
    - dovetail_height: Height of the dovetail projection
    - dovetail_length: How far the dovetail extends from the beam end
    - dovetail_angle: Angle of taper in degrees
    - at_start: If True, create at start (X=0); if False, at end (X=length)
    - at_top: If True, position at top; if False, position at bottom
    """
    
    beam: Beam
    dovetail_width: float
    dovetail_height: float
    dovetail_length: float
    dovetail_angle: float = 10.0
    at_start: bool = False
    at_top: bool = True

    @property
    def shape(self) -> Part:
        """Create the half-dovetail."""
        result = self.beam.shape
        
        x_pos = 0 if self.at_start else self.beam.length - self.dovetail_length
        
        # Only difference from DovetailInsert: z_center at top or bottom instead of middle
        if self.at_top:
            z_center = self.beam.height - self.dovetail_height / 2
        else:
            z_center = self.dovetail_height / 2
        
        end_section = Box(
            self.dovetail_length,
            self.beam.width,
            self.beam.height,
            align=(Align.MIN, Align.MIN, Align.MIN)
        )
        end_section = end_section.move(Location((x_pos, 0, 0)))
        
        dovetail_keep = create_dovetail_cut(
            base_width=self.dovetail_width,
            height=self.dovetail_height,
            length=self.dovetail_length,
            cone_angle=self.dovetail_angle,
            y_center=self.beam.width / 2,
            z_center=z_center,
        )
        dovetail_keep = dovetail_keep.move(Location((x_pos, 0, 0)))
        
        return result - (end_section - dovetail_keep)
