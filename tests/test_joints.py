import pytest

from build123_timber.elements import Timber
from build123_timber.joints import (
    JointTopology,
    LButtJoint,
    TButtJoint,
    LLapJoint,
    TLapJoint,
    XLapJoint,
    LMiterJoint,
    TenonMortiseJoint,
    DovetailJoint,
    BirdsmouthJoint,
)


@pytest.fixture
def main_timber():
    return Timber.beam(length=2000, width=100, height=150)


@pytest.fixture
def cross_timber():
    return Timber.beam(length=1000, width=100, height=150)


class TestJointTopology:
    def test_topology_values(self):
        assert JointTopology.L is not None
        assert JointTopology.T is not None
        assert JointTopology.X is not None
        assert JointTopology.I is not None


class TestButtJoints:
    def test_l_butt_joint_creation(self, main_timber, cross_timber):
        joint = LButtJoint(main=main_timber, cross=cross_timber)
        assert joint.main is main_timber
        assert joint.cross is cross_timber
        assert joint.topology == JointTopology.L

    def test_l_butt_joint_features(self, main_timber, cross_timber):
        joint = LButtJoint(main=main_timber, cross=cross_timber)
        main_feature = joint.get_main_feature()
        cross_feature = joint.get_cross_feature()
        assert main_feature is None
        assert cross_feature is not None

    def test_t_butt_joint_creation(self, main_timber, cross_timber):
        joint = TButtJoint(main=main_timber, cross=cross_timber)
        assert joint.topology == JointTopology.T

    def test_t_butt_with_mill_depth(self, main_timber, cross_timber):
        joint = TButtJoint(main=main_timber, cross=cross_timber, mill_depth=10.0)
        main_feature = joint.get_main_feature()
        assert main_feature is not None


class TestLapJoints:
    def test_l_lap_joint_creation(self, main_timber, cross_timber):
        joint = LLapJoint(main=main_timber, cross=cross_timber)
        assert joint.topology == JointTopology.L

    def test_l_lap_joint_features(self, main_timber, cross_timber):
        joint = LLapJoint(main=main_timber, cross=cross_timber)
        main_feature = joint.get_main_feature()
        cross_feature = joint.get_cross_feature()
        assert main_feature is not None
        assert cross_feature is not None

    def test_lap_cut_plane_bias(self, main_timber, cross_timber):
        joint = LLapJoint(main=main_timber, cross=cross_timber, cut_plane_bias=0.7)
        main_depth, cross_depth = joint._get_lap_depths()
        assert main_depth > cross_depth

    def test_lap_flip_side(self, main_timber, cross_timber):
        joint_normal = LLapJoint(main=main_timber, cross=cross_timber)
        joint_flipped = LLapJoint(main=main_timber, cross=cross_timber, flip_lap_side=True)
        assert joint_normal.flip_lap_side is False
        assert joint_flipped.flip_lap_side is True

    def test_t_lap_joint_creation(self, main_timber, cross_timber):
        joint = TLapJoint(main=main_timber, cross=cross_timber)
        assert joint.topology == JointTopology.T

    def test_x_lap_joint_creation(self, main_timber, cross_timber):
        joint = XLapJoint(main=main_timber, cross=cross_timber)
        assert joint.topology == JointTopology.X

    def test_invalid_cut_plane_bias(self, main_timber, cross_timber):
        with pytest.raises(ValueError):
            LLapJoint(main=main_timber, cross=cross_timber, cut_plane_bias=0.0)
        with pytest.raises(ValueError):
            LLapJoint(main=main_timber, cross=cross_timber, cut_plane_bias=1.0)


class TestMiterJoints:
    def test_l_miter_joint_creation(self, main_timber, cross_timber):
        joint = LMiterJoint(main=main_timber, cross=cross_timber)
        assert joint.topology == JointTopology.L

    def test_l_miter_joint_features(self, main_timber, cross_timber):
        joint = LMiterJoint(main=main_timber, cross=cross_timber)
        main_feature = joint.get_main_feature()
        cross_feature = joint.get_cross_feature()
        assert main_feature is not None
        assert cross_feature is not None


class TestTenonMortiseJoint:
    def test_tenon_mortise_creation(self, main_timber, cross_timber):
        joint = TenonMortiseJoint(main=main_timber, cross=cross_timber, tenon_length=50)
        assert joint.tenon_length == 50

    def test_auto_tenon_dimensions(self, main_timber, cross_timber):
        joint = TenonMortiseJoint(main=main_timber, cross=cross_timber)
        assert joint.tenon_width == cross_timber.width / 3
        assert joint.tenon_height == cross_timber.height * 2 / 3

    def test_custom_tenon_dimensions(self, main_timber, cross_timber):
        joint = TenonMortiseJoint(
            main=main_timber, cross=cross_timber,
            tenon_length=60, tenon_width=40, tenon_height=80
        )
        assert joint.tenon_length == 60
        assert joint.tenon_width == 40
        assert joint.tenon_height == 80

    def test_invalid_tenon_width(self, main_timber, cross_timber):
        with pytest.raises(ValueError):
            TenonMortiseJoint(main=main_timber, cross=cross_timber, tenon_width=200)

    def test_tenon_mortise_features(self, main_timber, cross_timber):
        joint = TenonMortiseJoint(main=main_timber, cross=cross_timber)
        main_feature = joint.get_main_feature()
        cross_feature = joint.get_cross_feature()
        assert main_feature is not None
        assert cross_feature is not None


class TestDovetailJoint:
    def test_dovetail_creation(self, main_timber, cross_timber):
        joint = DovetailJoint(main=main_timber, cross=cross_timber, dovetail_length=50)
        assert joint.dovetail_length == 50
        assert joint.topology == JointTopology.T

    def test_dovetail_cone_angle(self, main_timber, cross_timber):
        joint = DovetailJoint(main=main_timber, cross=cross_timber, cone_angle=12.0)
        assert joint.cone_angle == 12.0

    def test_invalid_cone_angle(self, main_timber, cross_timber):
        with pytest.raises(ValueError):
            DovetailJoint(main=main_timber, cross=cross_timber, cone_angle=0)
        with pytest.raises(ValueError):
            DovetailJoint(main=main_timber, cross=cross_timber, cone_angle=50)


class TestBirdsmouthJoint:
    def test_birdsmouth_creation(self, main_timber, cross_timber):
        joint = BirdsmouthJoint(main=main_timber, cross=cross_timber)
        assert joint.topology == JointTopology.T

    def test_birdsmouth_auto_depth(self, main_timber, cross_timber):
        joint = BirdsmouthJoint(main=main_timber, cross=cross_timber)
        assert joint.seat_depth == cross_timber.height / 3

    def test_birdsmouth_custom_depth(self, main_timber, cross_timber):
        joint = BirdsmouthJoint(main=main_timber, cross=cross_timber, seat_depth=40)
        assert joint.seat_depth == 40


class TestJointApplication:
    def test_apply_joint(self, main_timber, cross_timber):
        joint = LLapJoint(main=main_timber, cross=cross_timber)
        joint.apply()
        assert len(main_timber._features) > 0
        assert len(cross_timber._features) > 0
