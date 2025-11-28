from __future__ import annotations

import math
from dataclasses import dataclass

from build123d import Box, Part, Location, Vector, Rotation

from build123_timber.joints.base import Joint, JointTopology


@dataclass
class LMiterJoint(Joint):
    cutoff: float = 0.0
    topology: JointTopology = JointTopology.L

    def _get_miter_angle(self) -> float:
        main_dir = self.main.location.orientation * Vector(1, 0, 0)
        cross_dir = self.cross.location.orientation * Vector(1, 0, 0)
        dot = main_dir.dot(cross_dir)
        angle_rad = math.acos(max(-1.0, min(1.0, dot)))
        return (180 - math.degrees(angle_rad)) / 2

    def _miter_cut(self, timber, angle_sign: float = 1.0) -> Part:
        miter_angle = self._get_miter_angle()
        cut_size = max(timber.width, timber.height) * 3
        cut_box = Box(cut_size, cut_size, cut_size)
        cut_box = cut_box.rotate(Rotation(0, angle_sign * miter_angle, 0))
        cut_box = cut_box.move(Location((timber.length + cut_size / 2, 0, 0)))
        return cut_box

    def get_main_feature(self) -> Part:
        return self._miter_cut(self.main, angle_sign=1.0)

    def get_cross_feature(self) -> Part:
        return self._miter_cut(self.cross, angle_sign=-1.0)
