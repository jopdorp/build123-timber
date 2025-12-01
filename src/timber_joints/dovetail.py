"""Dovetail insert - positive part only."""

import math
from dataclasses import dataclass
from build123d import Align, Box, Part, Location
from timber_joints.base_joint import BaseJoint
from timber_joints.utils import create_dovetail_cut, calculate_dovetail_taper


@dataclass
class DovetailInsert(BaseJoint):
    """Dovetail-shaped projection that tapers outward (narrower at base, wider at tip)."""
    
    dovetail_width: float
    dovetail_height: float
    dovetail_length: float
    cone_angle: float = 10.0
    at_start: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        
        if self.dovetail_width <= 0 or self.dovetail_width > self._width:
            raise ValueError(f"dovetail_width must be between 0 and beam width ({self._width})")
        if self.dovetail_height <= 0 or self.dovetail_height > self._height:
            raise ValueError(f"dovetail_height must be between 0 and beam height ({self._height})")
        if self.dovetail_length <= 0 or self.dovetail_length > self._length:
            raise ValueError(f"dovetail_length must be between 0 and beam length ({self._length})")
        if not 0 < self.cone_angle < 45:
            raise ValueError("cone_angle must be between 0 and 45 degrees")

    def _get_widths(self) -> tuple[float, float]:
        """Calculate (base_width, tip_width) where tip_width > base_width."""
        taper = calculate_dovetail_taper(self.cone_angle, self.dovetail_length) / 2
        base_width = self.dovetail_width
        tip_width = self.dovetail_width + 2 * taper
        return base_width, tip_width

    @property
    def shape(self) -> Part:
        if self.at_start:
            x_pos = 0
        else:
            x_pos = self._length - self.dovetail_length
        
        # Full end section (to be subtracted from)
        end_section = Box(
            self.dovetail_length,
            self._width,
            self._height,
            align=(Align.MIN, Align.MIN, Align.MIN)
        )
        end_section = end_section.move(Location((x_pos, 0, 0)))
        
        # Create the tapered dovetail shape centered in beam cross-section
        dovetail_keep = create_dovetail_cut(
            base_width=self.dovetail_width,
            height=self.dovetail_height,
            length=self.dovetail_length,
            cone_angle=self.cone_angle,
            y_center=self._width / 2,
            z_center=self._get_z_center(),
        )
        dovetail_keep = dovetail_keep.move(Location((x_pos, 0, 0)))
        
        # Material to remove = end_section - dovetail_keep
        waste = end_section - dovetail_keep
        
        return self._input_shape - waste

    def _get_z_center(self) -> float:
        return self._height / 2

    def __repr__(self) -> str:
        position = "start" if self.at_start else "end"
        base, tip = self._get_widths()
        return f"DovetailInsert(beam={self.beam}, {base:.1f}→{tip:.1f}x{self.dovetail_height}x{self.dovetail_length}, angle={self.cone_angle}°, at_{position})"
