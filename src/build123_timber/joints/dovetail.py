from __future__ import annotations

import math
from dataclasses import dataclass

from build123d import Align, Box, Part, Location

from build123_timber.joints.base import Joint, JointTopology
from build123_timber.joints.utils import tenon_cut


@dataclass
class DovetailJoint(Joint):
    dovetail_length: float = 50.0
    dovetail_width: float | None = None
    dovetail_height: float | None = None
    cone_angle: float = 10.0
    clearance: float = 0.5
    topology: JointTopology = JointTopology.T

    def __post_init__(self) -> None:
        if self.dovetail_width is None:
            self.dovetail_width = self.cross.width / 3
        if self.dovetail_height is None:
            self.dovetail_height = self.cross.height / 2
        if not 0 < self.cone_angle < 45:
            raise ValueError("cone_angle must be between 0 and 45 degrees")

    def _get_widths(self) -> tuple[float, float]:
        taper = math.tan(math.radians(self.cone_angle)) * self.dovetail_height
        narrow = max(self.dovetail_width - taper, 1.0)
        wide = self.dovetail_width + taper
        return narrow, wide

    def _create_dovetail_solid(self) -> Part:
        return Box(
            self.dovetail_length,
            self.dovetail_width,
            self.dovetail_height,
            align=(Align.MIN, Align.CENTER, Align.CENTER),
        )

    def get_main_feature(self) -> Part:
        housing = Box(
            self.dovetail_width + self.clearance,
            self.dovetail_length + self.clearance,
            self.dovetail_height + self.clearance,
            align=(Align.CENTER, Align.MIN, Align.CENTER),
        )
        x_pos = self.main.length / 2
        y_pos = -self.main.width / 2
        z_pos = self.main.height / 2 - self.dovetail_height / 2
        return housing.move(Location((x_pos, y_pos, z_pos)))

    def get_cross_feature(self) -> Part:
        return tenon_cut(
            self.cross,
            tenon_width=self.dovetail_width,
            tenon_height=self.dovetail_height,
            tenon_length=self.dovetail_length,
        )


@dataclass
class HousedDovetailJoint(DovetailJoint):
    housing_depth: float = 10.0
    stop_distance: float = 10.0

    def get_main_feature(self) -> Part:
        dovetail_housing = super().get_main_feature()
        housing = Box(
            self.cross.width,
            self.dovetail_length - self.stop_distance,
            self.housing_depth,
            align=(Align.CENTER, Align.MIN, Align.CENTER),
        )
        x_pos = self.main.length / 2
        y_pos = -self.main.width / 2 + self.stop_distance
        z_pos = self.main.height / 2 - self.housing_depth / 2
        housing = housing.move(Location((x_pos, y_pos, z_pos)))
        return dovetail_housing + housing
