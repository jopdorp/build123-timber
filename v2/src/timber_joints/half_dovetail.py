"""Half-dovetail joint - dovetail insert at top or bottom of beam."""

from dataclasses import dataclass
from timber_joints.dovetail import DovetailInsert


@dataclass
class HalfDovetail(DovetailInsert):
    """A half-dovetail - dovetail insert positioned at top or bottom of beam.
    
    Same as DovetailInsert but at top/bottom instead of centered.
    
    Parameters:
    - beam: The beam (Beam object or Part) to cut the half-dovetail on
    - dovetail_width: Width at the narrow end (base)
    - dovetail_height: Height of the dovetail projection
    - dovetail_length: How far the dovetail extends from the beam end
    - cone_angle: Angle of taper in degrees (renamed from dovetail_angle for consistency)
    - at_start: If True, create at start (X=0); if False, at end (X=length)
    - at_top: If True, position at top; if False, position at bottom
    """
    
    at_top: bool = True

    def _get_z_center(self) -> float:
        """Position dovetail at top or bottom instead of center."""
        if self.at_top:
            return self._height - self.dovetail_height / 2
        else:
            return self.dovetail_height / 2
