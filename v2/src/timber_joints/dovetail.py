"""Dovetail insert - positive part only."""

import math
from dataclasses import dataclass
from build123d import Align, Box, Part, Location
from timber_joints.beam import Beam
from timber_joints.utils import create_dovetail_cut, calculate_dovetail_taper


@dataclass
class DovetailInsert:
    """The positive (inserting) part of a dovetail joint.
    
    Creates a dovetail-shaped projection at the beam end that tapers
    outward (narrower at the base/beam, wider at the tip/end).
    
    Parameters:
    - beam: The beam to cut the dovetail on
    - dovetail_width: Width at the narrow end (base, where it meets beam)
    - dovetail_height: Height of the dovetail
    - dovetail_length: How far the dovetail extends from the beam end
    - cone_angle: Angle of taper in degrees (how much it widens toward tip)
    - at_start: If True, create at start (X=0); if False, at end (X=length)
    """
    
    beam: Beam
    dovetail_width: float
    dovetail_height: float
    dovetail_length: float
    cone_angle: float = 10.0
    at_start: bool = False

    def __post_init__(self) -> None:
        """Validate dovetail parameters."""
        if self.dovetail_width <= 0 or self.dovetail_width > self.beam.width:
            raise ValueError(f"dovetail_width must be between 0 and beam width ({self.beam.width})")
        if self.dovetail_height <= 0 or self.dovetail_height > self.beam.height:
            raise ValueError(f"dovetail_height must be between 0 and beam height ({self.beam.height})")
        if self.dovetail_length <= 0 or self.dovetail_length > self.beam.length:
            raise ValueError(f"dovetail_length must be between 0 and beam length ({self.beam.length})")
        if not 0 < self.cone_angle < 45:
            raise ValueError("cone_angle must be between 0 and 45 degrees")

    def _get_widths(self) -> tuple[float, float]:
        """Calculate the base (narrow) and tip (wide) widths of the dovetail.
        
        Returns: (base_width, tip_width) where tip_width > base_width
        """
        taper = calculate_dovetail_taper(self.cone_angle, self.dovetail_length) / 2
        base_width = self.dovetail_width
        tip_width = self.dovetail_width + 2 * taper
        return base_width, tip_width

    @property
    def shape(self) -> Part:
        """Create the dovetail insert by removing material around the tapered projection."""
        result = self.beam.shape
        
        # Determine position based on at_start
        if self.at_start:
            x_pos = 0
        else:
            x_pos = self.beam.length - self.dovetail_length
        
        # Full end section (to be subtracted from)
        end_section = Box(
            self.dovetail_length,
            self.beam.width,
            self.beam.height,
            align=(Align.MIN, Align.MIN, Align.MIN)
        )
        end_section = end_section.move(Location((x_pos, 0, 0)))
        
        # Create the tapered dovetail shape centered in beam cross-section
        dovetail_keep = create_dovetail_cut(
            base_width=self.dovetail_width,
            height=self.dovetail_height,
            length=self.dovetail_length,
            cone_angle=self.cone_angle,
            y_center=self.beam.width / 2,
            z_center=self.beam.height / 2,
        )
        dovetail_keep = dovetail_keep.move(Location((x_pos, 0, 0)))
        
        # Material to remove = end_section - dovetail_keep
        waste = end_section - dovetail_keep
        
        return result - waste

    def __repr__(self) -> str:
        position = "start" if self.at_start else "end"
        base, tip = self._get_widths()
        return f"DovetailInsert(beam={self.beam}, {base:.1f}→{tip:.1f}x{self.dovetail_height}x{self.dovetail_length}, angle={self.cone_angle}°, at_{position})"
