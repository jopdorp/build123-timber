from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from build123d import Box, Cylinder, Part, Location, fillet, chamfer

from build123_timber.joints.base import Joint, JointTopology
from build123_timber.joints.utils import mortise_cut, shoulder_cuts


class TenonShape(Enum):
    SQUARE = auto()
    ROUND = auto()
    ROUNDED = auto()
    CHAMFERED = auto()


@dataclass
class TenonMortiseJoint(Joint):
    tenon_length: float = 50.0
    tenon_width: float | None = None
    tenon_height: float | None = None
    shape: TenonShape = TenonShape.SQUARE
    shape_radius: float = 5.0
    through_tenon: bool = False
    clearance: float = 0.5
    topology: JointTopology = JointTopology.T

    def __post_init__(self) -> None:
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
            align=("MIN", "CENTER", "CENTER"),
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
        return shoulder_cuts(
            self.cross,
            tenon_width=self.tenon_width,
            tenon_height=self.tenon_height,
            tenon_length=self.tenon_length,
        )
