from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from build123d import Align, Box, Cylinder, Part, Location, fillet, chamfer

from build123_timber.joints.base import Joint, JointTopology
from build123_timber.joints.utils import mortise_cut, tenon_cut, housing_cut


class TenonShape(Enum):
    SQUARE = auto()
    ROUND = auto()
    ROUNDED = auto()
    CHAMFERED = auto()


@dataclass
class TenonMortiseJoint(Joint):
    """Mortise and tenon joint.
    
    By default, creates a tenon that is 1/3 the timber width and 2/3 the timber height,
    which is the classic proportioning for a strong mortise and tenon joint.
    """
    tenon_length: float = 50.0
    tenon_width: float | None = None  # None = 1/3 timber width
    tenon_height: float | None = None  # None = 2/3 timber height
    shape: TenonShape = TenonShape.SQUARE
    shape_radius: float = 5.0
    through_tenon: bool = False
    clearance: float = 0.5
    topology: JointTopology = JointTopology.T

    def __post_init__(self) -> None:
        # Default: classic proportions (1/3 width, 2/3 height)
        if self.tenon_width is None:
            self.tenon_width = self.cross.width / 3
        if self.tenon_height is None:
            self.tenon_height = self.cross.height * 2 / 3

        if self.tenon_width > self.cross.width:
            raise ValueError("Tenon width cannot exceed cross timber width")
        if self.tenon_height > self.cross.height:
            raise ValueError("Tenon height cannot exceed cross timber height")

    def _create_tenon(self) -> Part:
        tenon = Box(
            self.tenon_length,
            self.tenon_width,
            self.tenon_height,
            align=(Align.MIN, Align.CENTER, Align.CENTER),
        )

        if self.shape == TenonShape.ROUND:
            cap = Cylinder(
                radius=min(self.tenon_width, self.tenon_height) / 2,
                height=self.tenon_width,
                rotation=(90, 0, 0),
            )
            cap = cap.move(Location((self.tenon_length, 0, 0)))
            tenon = tenon + cap
        elif self.shape == TenonShape.ROUNDED and self.shape_radius > 0:
            try:
                tenon = fillet(tenon, self.shape_radius)
            except Exception:
                pass
        elif self.shape == TenonShape.CHAMFERED and self.shape_radius > 0:
            try:
                tenon = chamfer(tenon, self.shape_radius)
            except Exception:
                pass

        return tenon

    def get_main_feature(self) -> Part:
        mortise_depth = (
            self.main.width + 10 if self.through_tenon
            else self.tenon_length + self.clearance
        )
        return mortise_cut(
            self.main,
            mortise_width=self.tenon_width + self.clearance,
            mortise_height=self.tenon_height + self.clearance,
            mortise_depth=mortise_depth,
            x_position=self.main.length / 2,
        )

    def get_cross_feature(self) -> Part:
        return tenon_cut(
            self.cross,
            tenon_width=self.tenon_width,
            tenon_height=self.tenon_height,
            tenon_length=self.tenon_length,
        )


@dataclass
class HousedTenonMortiseJoint(Joint):
    """Housed mortise and tenon joint.
    
    Combines a mortise/tenon with a housing (shallow recess) in the main timber.
    The housing provides additional bearing surface and helps locate the joint.
    The cross timber has a shoulder that sits into the housing.
    
    Main timber gets:
    - Housing: shallow recess on Y=0 face
    - Mortise: deeper hole inside the housing for the tenon
    
    Cross timber gets:
    - Shoulder: material removed to create step that fits into housing  
    - Tenon: projecting piece that fits into mortise
    """
    tenon_length: float = 50.0
    tenon_width: float | None = None  # None = 1/3 timber width
    tenon_height: float | None = None  # None = 2/3 timber height
    housing_depth: float = 10.0  # Depth of housing recess
    shape: TenonShape = TenonShape.SQUARE
    shape_radius: float = 5.0
    through_tenon: bool = False
    clearance: float = 0.5
    topology: JointTopology = JointTopology.T

    def __post_init__(self) -> None:
        # Default: classic proportions (1/3 width, 2/3 height)
        if self.tenon_width is None:
            self.tenon_width = self.cross.width / 3
        if self.tenon_height is None:
            self.tenon_height = self.cross.height * 2 / 3

        if self.tenon_width > self.cross.width:
            raise ValueError("Tenon width cannot exceed cross timber width")
        if self.tenon_height > self.cross.height:
            raise ValueError("Tenon height cannot exceed cross timber height")
        if self.housing_depth >= self.main.width:
            raise ValueError("Housing depth cannot exceed main timber width")

    def get_main_feature(self) -> Part:
        """Create combined housing + mortise cut for main timber."""
        # Housing: full width/height of cross timber, shallow depth
        housing = housing_cut(
            self.main,
            housing_width=self.cross.width + self.clearance,
            housing_depth=self.housing_depth,
            housing_length=self.cross.height + self.clearance,
            x_position=self.main.length / 2,
        )
        
        # Mortise: inside the housing, deeper
        mortise_depth = (
            self.main.width + 10 if self.through_tenon
            else self.tenon_length + self.clearance + self.housing_depth
        )
        mortise = mortise_cut(
            self.main,
            mortise_width=self.tenon_width + self.clearance,
            mortise_height=self.tenon_height + self.clearance,
            mortise_depth=mortise_depth,
            x_position=self.main.length / 2,
        )
        
        return housing + mortise

    def get_cross_feature(self) -> Part:
        """Create shoulder + tenon cut for cross timber.
        
        The shoulder is the step that sits into the housing.
        The tenon projects from the shoulder into the mortise.
        """
        return tenon_cut(
            self.cross,
            tenon_width=self.tenon_width,
            tenon_height=self.tenon_height,
            tenon_length=self.tenon_length + self.housing_depth,
        )
