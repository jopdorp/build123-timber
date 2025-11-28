from __future__ import annotations

from dataclasses import dataclass

from build123d import Part

from build123_timber.joints.base import Joint, JointTopology
from build123_timber.joints.utils import end_cut, notch_cut


@dataclass
class ButtJoint(Joint):
    mill_depth: float = 0.0

    def get_main_feature(self) -> Part | None:
        return None

    def get_cross_feature(self) -> Part:
        return end_cut(self.cross, cut_depth=self.main.width)


@dataclass
class LButtJoint(ButtJoint):
    topology: JointTopology = JointTopology.L

    def get_cross_feature(self) -> Part:
        return end_cut(self.cross, cut_depth=self.main.width)


@dataclass
class TButtJoint(ButtJoint):
    topology: JointTopology = JointTopology.T

    def get_main_feature(self) -> Part | None:
        if self.mill_depth <= 0:
            return None
        return notch_cut(
            self.main,
            notch_width=self.cross.width,
            notch_depth=self.mill_depth,
            x_position=self.main.length / 2,
        )

    def get_cross_feature(self) -> Part:
        return end_cut(self.cross, cut_depth=self.main.height)
