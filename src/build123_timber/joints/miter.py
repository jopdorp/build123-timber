from __future__ import annotations

from dataclasses import dataclass

from build123d import Axis, Box, Part, Location

from build123_timber.joints.base import Joint, JointTopology


@dataclass
class LMiterJoint(Joint):
    angle: float = 45.0
    cutoff: float = 0.0
    topology: JointTopology = JointTopology.L

    def _miter_cut(self, timber, angle_sign: float = 1.0) -> Part:
        cut_size = max(timber.width, timber.height) * 3
        cut_box = Box(cut_size, cut_size, cut_size)
        cut_box = cut_box.rotate(Axis.Y, angle_sign * self.angle)
        cut_box = cut_box.move(Location((timber.length + cut_size / 2, 0, 0)))
        return cut_box

    def get_main_feature(self) -> Part:
        return self._miter_cut(self.main, angle_sign=1.0)

    def get_cross_feature(self) -> Part:
        return self._miter_cut(self.cross, angle_sign=-1.0)