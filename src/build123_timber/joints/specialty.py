from __future__ import annotations

from dataclasses import dataclass

from build123d import Align, Axis, Box, Cylinder, Part, Location

from build123_timber.joints.base import Joint, JointTopology
from build123_timber.joints.utils import notch_cut


@dataclass
class BirdsmouthJoint(Joint):
    seat_depth: float | None = None
    heel_depth: float | None = None
    rafter_angle: float = 30.0
    topology: JointTopology = JointTopology.T

    def __post_init__(self) -> None:
        if self.seat_depth is None:
            self.seat_depth = self.cross.height / 3
        if self.heel_depth is None:
            self.heel_depth = self.seat_depth

    def get_main_feature(self) -> Part | None:
        return None

    def get_cross_feature(self) -> Part:
        seat_cut = Box(
            self.main.width * 2,
            self.cross.width,
            self.seat_depth,
            align=(Align.CENTER, Align.CENTER, Align.MAX),
        )
        seat_cut = seat_cut.move(Location((0, 0, -self.cross.height / 2)))

        heel_cut = Box(
            self.heel_depth,
            self.cross.width,
            self.cross.height,
            align=(Align.MAX, Align.CENTER, Align.MIN),
        )
        heel_cut = heel_cut.move(
            Location((-self.main.width / 2, 0, -self.cross.height / 2))
        )

        birdsmouth = seat_cut + heel_cut
        x_pos = self.cross.length - self.main.width
        return birdsmouth.move(Location((x_pos, 0, 0)))


@dataclass
class FrenchRidgeLapJoint(Joint):
    flip_lap_side: bool = False
    drillhole_diam: float = 0.0
    topology: JointTopology = JointTopology.L

    def _get_overlap(self) -> float:
        return max(self.main.width, self.cross.width)

    def _create_ridge_lap(self, timber, is_main: bool) -> Part:
        overlap = self._get_overlap()
        lap_depth = timber.height / 2
        flip = self.flip_lap_side
        at_top = (is_main and not flip) or (not is_main and flip)

        lap_cut = Box(
            overlap,
            timber.width,
            lap_depth,
            align=(Align.MIN, Align.CENTER, Align.MIN if at_top else Align.MAX),
        )

        x_pos = timber.length - overlap
        z_pos = timber.height / 2 if at_top else -timber.height / 2
        lap_cut = lap_cut.move(Location((x_pos, 0, z_pos)))

        angle = 2.0 if at_top else -2.0
        lap_cut = lap_cut.rotate(Axis.Y, angle)

        return lap_cut

    def get_main_feature(self) -> Part:
        return self._create_ridge_lap(self.main, is_main=True)

    def get_cross_feature(self) -> Part:
        lap_cut = self._create_ridge_lap(self.cross, is_main=False)

        if self.drillhole_diam > 0:
            overlap = self._get_overlap()
            hole = Cylinder(
                radius=self.drillhole_diam / 2,
                height=self.cross.height * 1.5,
            )
            hole = hole.move(Location((self.cross.length - overlap / 2, 0, 0)))
            lap_cut = lap_cut + hole

        return lap_cut


@dataclass
class StepJoint(Joint):
    step_shape: int = 0  # 0=step, 1=heel, 2=double
    step_depth: float | None = None
    heel_depth: float | None = None
    tapered_heel: bool = False
    topology: JointTopology = JointTopology.T

    def __post_init__(self) -> None:
        if self.step_depth is None:
            self.step_depth = self.cross.height / 4
        if self.heel_depth is None:
            self.heel_depth = self.step_depth

    def get_main_feature(self) -> Part | None:
        return notch_cut(
            self.main,
            notch_width=self.cross.width,
            notch_depth=self.step_depth,
            x_position=self.main.length / 2,
        )

    def get_cross_feature(self) -> Part:
        cuts = []

        if self.step_shape in [0, 2]:
            step = Box(
                self.main.height,
                self.cross.width,
                self.step_depth,
                align=(Align.MIN, Align.CENTER, Align.MIN),
            )
            step = step.move(Location((
                self.cross.length - self.main.height,
                0,
                -self.cross.height / 2
            )))
            cuts.append(step)

        if self.step_shape in [1, 2]:
            heel = Box(
                self.heel_depth,
                self.cross.width,
                self.cross.height / 2,
                align=(Align.MAX, Align.CENTER, Align.MIN),
            )
            heel = heel.move(Location((
                self.cross.length - self.main.height,
                0,
                -self.cross.height / 2
            )))
            if self.tapered_heel:
                heel = heel.rotate(Axis.Y, 15)
            cuts.append(heel)

        if cuts:
            result = cuts[0]
            for cut in cuts[1:]:
                result = result + cut
            return result

        return Box(1, self.cross.width, self.cross.height).move(
            Location((self.cross.length, 0, 0))
        )
