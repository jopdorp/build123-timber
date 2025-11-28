from __future__ import annotations

from dataclasses import dataclass

from build123d import Part

from build123_timber.joints.base import Joint, JointTopology
from build123_timber.joints.utils import calculate_lap_depths, lap_cut


@dataclass
class LapJoint(Joint):
    flip_lap_side: bool = False
    cut_plane_bias: float = 0.5

    def __post_init__(self) -> None:
        if not 0.01 <= self.cut_plane_bias <= 0.99:
            raise ValueError("cut_plane_bias must be between 0.01 and 0.99")

    def _get_lap_depths(self) -> tuple[float, float]:
        return calculate_lap_depths(
            self.main.height,
            self.cross.height,
            self.cut_plane_bias,
            self.flip_lap_side,
        )

    def _get_cut_position_main(self) -> float:
        return self.main.length / 2

    def _get_cut_position_cross(self) -> float:
        return self.cross.length / 2

    def _get_cut_width_main(self) -> float:
        return self.cross.width

    def _get_cut_width_cross(self) -> float:
        return self.main.width

    def get_main_feature(self) -> Part:
        main_depth, _ = self._get_lap_depths()
        return lap_cut(
            self.main,
            cut_width=self._get_cut_width_main(),
            cut_depth=main_depth,
            x_position=self._get_cut_position_main(),
            from_top=not self.flip_lap_side,
        )

    def get_cross_feature(self) -> Part:
        _, cross_depth = self._get_lap_depths()
        return lap_cut(
            self.cross,
            cut_width=self._get_cut_width_cross(),
            cut_depth=cross_depth,
            x_position=self._get_cut_position_cross(),
            from_top=self.flip_lap_side,
        )


@dataclass
class LLapJoint(LapJoint):
    topology: JointTopology = JointTopology.L

    def _get_cut_position_main(self) -> float:
        return self.main.length - self.cross.width / 2

    def _get_cut_position_cross(self) -> float:
        return self.cross.length - self.main.width / 2


@dataclass
class TLapJoint(LapJoint):
    topology: JointTopology = JointTopology.T

    def _get_cut_width_cross(self) -> float:
        return self.main.height


@dataclass
class XLapJoint(LapJoint):
    topology: JointTopology = JointTopology.X
