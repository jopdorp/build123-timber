"""Half-dovetail joint - dovetail insert at top or bottom of beam."""

from dataclasses import dataclass
from timber_joints.dovetail import DovetailInsert


@dataclass
class HalfDovetail(DovetailInsert):
    """Dovetail positioned at top or bottom of beam instead of centered."""
    
    at_top: bool = True

    def _get_z_center(self) -> float:
        if self.at_top:
            return self._height - self.dovetail_height / 2
        else:
            return self.dovetail_height / 2
