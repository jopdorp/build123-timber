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


# =============================================================================
# Factory functions for creating test data (importable by visual tests)
# =============================================================================

def create_l_lap_joint_main_cut():
    """Create L-lap joint and return (main timber, cut geometry, joint)."""
    main = Timber.beam(length=400, width=80, height=80)
    cross = Timber.beam(length=300, width=80, height=80)
    joint = LLapJoint(main=main, cross=cross)
    cut = joint.get_main_feature()
    return main, cut, joint


def create_l_lap_joint_applied():
    """Create L-lap joint, apply it, return (main, cross, joint)."""
    main = Timber.beam(length=400, width=80, height=80)
    cross = Timber.beam(length=300, width=80, height=80)
    joint = LLapJoint(main=main, cross=cross)
    joint.apply()
    return main, cross, joint


def create_t_lap_joint_cuts():
    """Create T-lap joint and return (main, cross, main_cut, cross_cut, joint)."""
    main = Timber.beam(length=400, width=80, height=80)
    cross = Timber.beam(length=300, width=80, height=80)
    joint = TLapJoint(main=main, cross=cross)
    main_cut = joint.get_main_feature()
    cross_cut = joint.get_cross_feature()
    return main, cross, main_cut, cross_cut, joint


def create_t_lap_joint_applied():
    """Create T-lap joint, apply it, return (main, cross, joint)."""
    main = Timber.beam(length=400, width=80, height=80)
    cross = Timber.beam(length=300, width=80, height=80)
    joint = TLapJoint(main=main, cross=cross)
    joint.apply()
    return main, cross, joint


def create_x_lap_joint_applied():
    """Create X-lap joint, apply it, return (main, cross, joint)."""
    main = Timber.beam(length=400, width=80, height=80)
    cross = Timber.beam(length=400, width=80, height=80)
    joint = XLapJoint(main=main, cross=cross)
    joint.apply()
    return main, cross, joint


def create_x_lap_joint_cuts():
    """Create X-lap joint and return (main, cross, main_cut, cross_cut, joint)."""
    main = Timber.beam(length=400, width=80, height=80)
    cross = Timber.beam(length=400, width=80, height=80)
    joint = XLapJoint(main=main, cross=cross)
    main_cut = joint.get_main_feature()
    cross_cut = joint.get_cross_feature()
    return main, cross, main_cut, cross_cut, joint


def create_tenon_mortise_joint_cuts():
    """Create mortise-tenon joint and return (main, cross, main_cut, cross_cut, joint).
    
    Main: 400×80×80 beam, receives mortise (hole) at center
    Cross: 300×80×80 beam, tenon formed at end
    Tenon: 50 length, ~26.67 width (1/3), ~53.33 height (2/3) - classic proportions
    """
    main = Timber.beam(length=400, width=80, height=80)
    cross = Timber.beam(length=300, width=80, height=80)
    joint = TenonMortiseJoint(main=main, cross=cross, tenon_length=50)
    main_cut = joint.get_main_feature()
    cross_cut = joint.get_cross_feature()
    return main, cross, main_cut, cross_cut, joint


def create_tenon_mortise_joint_applied():
    """Create mortise-tenon joint, apply it, return (main, cross, joint)."""
    main = Timber.beam(length=400, width=80, height=80)
    cross = Timber.beam(length=300, width=80, height=80)
    joint = TenonMortiseJoint(main=main, cross=cross, tenon_length=50)
    joint.apply()
    return main, cross, joint


def create_housed_tenon_mortise_joint_cuts():
    """Create housed mortise-tenon joint and return (main, cross, main_cut, cross_cut, joint).
    
    Main: 400×120×120 beam (larger to accommodate housing), receives housing + mortise
    Cross: 300×80×80 beam, shoulder + tenon formed at end
    Housing: 10mm deep recess for cross timber shoulder
    Tenon: 50 length, ~26.67 width (1/3), ~53.33 height (2/3) - classic proportions
    """
    main = Timber.beam(length=400, width=120, height=120)  # Larger main for housing
    cross = Timber.beam(length=300, width=80, height=80)
    from build123_timber.joints import HousedTenonMortiseJoint
    joint = HousedTenonMortiseJoint(main=main, cross=cross, tenon_length=50, housing_depth=10)
    main_cut = joint.get_main_feature()
    cross_cut = joint.get_cross_feature()
    return main, cross, main_cut, cross_cut, joint


def create_housed_tenon_mortise_joint_applied():
    """Create housed mortise-tenon joint, apply it, return (main, cross, joint)."""
    main = Timber.beam(length=400, width=120, height=120)  # Larger main for housing
    cross = Timber.beam(length=300, width=80, height=80)
    from build123_timber.joints import HousedTenonMortiseJoint
    joint = HousedTenonMortiseJoint(main=main, cross=cross, tenon_length=50, housing_depth=10)
    joint.apply()
    return main, cross, joint


def create_angled_tenon_mortise_joint_cuts():
    """Create angled mortise-tenon joint and return (main, cross, main_cut, cross_cut, joint).
    
    Main: 400×120×120 beam (larger to accommodate housing), receives angled housing + mortise
    Cross: 300×80×80 beam, angled shoulder + tenon formed at end
    Housing: 15mm max depth, 15 degree angle
    Tenon: 50 length, ~26.67 width (1/3), ~53.33 height (2/3) - classic proportions
    """
    main = Timber.beam(length=400, width=120, height=120)  # Larger main for housing
    cross = Timber.beam(length=300, width=80, height=80)
    from build123_timber.joints import AngledTenonMortiseJoint
    joint = AngledTenonMortiseJoint(
        main=main, cross=cross, tenon_length=50, housing_depth=15, shoulder_angle=15
    )
    main_cut = joint.get_main_feature()
    cross_cut = joint.get_cross_feature()
    return main, cross, main_cut, cross_cut, joint


def create_angled_tenon_mortise_joint_applied():
    """Create angled mortise-tenon joint, apply it, return (main, cross, joint)."""
    main = Timber.beam(length=400, width=120, height=120)  # Larger main for housing
    cross = Timber.beam(length=300, width=80, height=80)
    from build123_timber.joints import AngledTenonMortiseJoint
    joint = AngledTenonMortiseJoint(
        main=main, cross=cross, tenon_length=50, housing_depth=15, shoulder_angle=15
    )
    joint.apply()
    return main, cross, joint


# Note: removed "shouldered" variants - all mortise/tenon joints have reduced tenons by default


# =============================================================================
# Fixtures
# =============================================================================

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

    def test_l_lap_joint_main_cut_position(self):
        """L-lap main cut should be at the END of the timber."""
        main, cut, _ = create_l_lap_joint_main_cut()
        bbox = cut.bounding_box()

        # Cut should be at end: X from (length - cross.width) to length
        assert bbox.min.X == pytest.approx(400 - 80, abs=1), f"Cut X min should be 320, got {bbox.min.X}"
        assert bbox.max.X == pytest.approx(400, abs=1), f"Cut X max should be 400, got {bbox.max.X}"
        # Cut should span full Y width
        assert bbox.min.Y == pytest.approx(0, abs=1), f"Cut Y min should be 0, got {bbox.min.Y}"
        assert bbox.max.Y == pytest.approx(80, abs=1), f"Cut Y max should be 80, got {bbox.max.Y}"
        # Cut depth is half height (default bias=0.5), from top
        assert bbox.min.Z == pytest.approx(40, abs=1), f"Cut Z min should be 40, got {bbox.min.Z}"
        assert bbox.max.Z == pytest.approx(80, abs=1), f"Cut Z max should be 80, got {bbox.max.Z}"

    def test_l_lap_joint_cross_cut_position(self):
        """L-lap cross cut should be at the END of the cross timber."""
        _, _, joint = create_l_lap_joint_main_cut()
        cut = joint.get_cross_feature()
        bbox = cut.bounding_box()

        # Cut should be at end: X from (length - main.width) to length
        assert bbox.min.X == pytest.approx(300 - 80, abs=1), f"Cut X min should be 220, got {bbox.min.X}"
        assert bbox.max.X == pytest.approx(300, abs=1), f"Cut X max should be 300, got {bbox.max.X}"
        # Cut should span full Y width
        assert bbox.min.Y == pytest.approx(0, abs=1), f"Cut Y min should be 0, got {bbox.min.Y}"
        assert bbox.max.Y == pytest.approx(80, abs=1), f"Cut Y max should be 80, got {bbox.max.Y}"
        # Cut depth is half height (default bias=0.5), from bottom
        assert bbox.min.Z == pytest.approx(0, abs=1), f"Cut Z min should be 0, got {bbox.min.Z}"
        assert bbox.max.Z == pytest.approx(40, abs=1), f"Cut Z max should be 40, got {bbox.max.Z}"

    def test_l_lap_joint_volume_removed(self):
        """L-lap should remove correct volume from each timber."""
        main, cross, _ = create_l_lap_joint_applied()

        # Expected removal: width × cut_width × half_height = 80 × 80 × 40 = 256,000
        expected_removal = 80 * 80 * 40
        main_removed = main.blank.volume - main.shape.volume
        cross_removed = cross.blank.volume - cross.shape.volume

        assert main_removed == pytest.approx(expected_removal, rel=0.01), \
            f"Main removed {main_removed}, expected {expected_removal}"
        assert cross_removed == pytest.approx(expected_removal, rel=0.01), \
            f"Cross removed {cross_removed}, expected {expected_removal}"

    def test_l_lap_joint_resulting_shape_bbox(self):
        """After L-lap cut, timber bbox should remain same (cut is internal)."""
        main, cross, _ = create_l_lap_joint_applied()

        main_bbox = main.shape.bounding_box()
        cross_bbox = cross.shape.bounding_box()

        # Main timber bbox unchanged
        assert main_bbox.min.X == pytest.approx(0, abs=1)
        assert main_bbox.max.X == pytest.approx(400, abs=1)
        assert main_bbox.min.Z == pytest.approx(0, abs=1)
        assert main_bbox.max.Z == pytest.approx(80, abs=1)

        # Cross timber bbox unchanged
        assert cross_bbox.min.X == pytest.approx(0, abs=1)
        assert cross_bbox.max.X == pytest.approx(300, abs=1)
        assert cross_bbox.min.Z == pytest.approx(0, abs=1)
        assert cross_bbox.max.Z == pytest.approx(80, abs=1)

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

    def test_t_lap_joint_main_cut_position(self):
        """T-lap main cut should be in the MIDDLE of the timber."""
        main, cross, main_cut, cross_cut, _ = create_t_lap_joint_cuts()
        bbox = main_cut.bounding_box()

        # Cut should be centered: X from (length/2 - cross.width/2) to (length/2 + cross.width/2)
        assert bbox.min.X == pytest.approx(200 - 40, abs=1), f"Cut X min should be 160, got {bbox.min.X}"
        assert bbox.max.X == pytest.approx(200 + 40, abs=1), f"Cut X max should be 240, got {bbox.max.X}"

    def test_t_lap_joint_cross_cut_position(self):
        """T-lap cross cut should be at the END of the cross timber."""
        main, cross, main_cut, cross_cut, _ = create_t_lap_joint_cuts()
        bbox = cross_cut.bounding_box()

        # Cross cut at end: X from (length - main.width) to length
        # cross.length=300, main.width=80, so X should be 220-300
        assert bbox.min.X == pytest.approx(300 - 80, abs=1), f"Cut X min should be 220, got {bbox.min.X}"
        assert bbox.max.X == pytest.approx(300, abs=1), f"Cut X max should be 300, got {bbox.max.X}"

    def test_x_lap_joint_creation(self, main_timber, cross_timber):
        joint = XLapJoint(main=main_timber, cross=cross_timber)
        assert joint.topology == JointTopology.X

    def test_x_lap_joint_both_cuts_centered(self):
        """X-lap both cuts should be in the MIDDLE of each timber."""
        main, cross, main_cut, cross_cut, _ = create_x_lap_joint_cuts()
        main_bbox = main_cut.bounding_box()
        cross_bbox = cross_cut.bounding_box()

        # Both centered at length/2
        assert main_bbox.min.X == pytest.approx(200 - 40, abs=1)
        assert main_bbox.max.X == pytest.approx(200 + 40, abs=1)
        assert cross_bbox.min.X == pytest.approx(200 - 40, abs=1)
        assert cross_bbox.max.X == pytest.approx(200 + 40, abs=1)

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

    def test_default_tenon_dimensions(self, main_timber, cross_timber):
        """Default tenon should be 1/3 width, 2/3 height (classic proportions)."""
        joint = TenonMortiseJoint(main=main_timber, cross=cross_timber)
        assert joint.tenon_width == pytest.approx(cross_timber.width / 3)
        assert joint.tenon_height == pytest.approx(cross_timber.height * 2 / 3)

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

    def test_tenon_mortise_has_both_features(self, main_timber, cross_timber):
        """Mortise/tenon joint should have cuts on both timbers."""
        joint = TenonMortiseJoint(main=main_timber, cross=cross_timber)
        main_feature = joint.get_main_feature()
        cross_feature = joint.get_cross_feature()
        assert main_feature is not None  # Mortise hole
        assert cross_feature is not None  # Tenon formation

    def test_mortise_position(self):
        """Mortise should be centered on X, entering from Y=0 face."""
        main, cross, main_cut, cross_cut, joint = create_tenon_mortise_joint_cuts()
        bbox = main_cut.bounding_box()
        
        # Mortise centered at main.length/2 = 200
        expected_width = joint.tenon_width + joint.clearance
        expected_x_min = 200 - expected_width / 2
        expected_x_max = 200 + expected_width / 2
        
        assert bbox.min.X == pytest.approx(expected_x_min, abs=1), f"Mortise X min: {bbox.min.X}"
        assert bbox.max.X == pytest.approx(expected_x_max, abs=1), f"Mortise X max: {bbox.max.X}"
        
        # Mortise enters from Y=0 face, depth = tenon_length + clearance
        expected_depth = joint.tenon_length + joint.clearance
        assert bbox.min.Y == pytest.approx(0, abs=1), f"Mortise Y min: {bbox.min.Y}"
        assert bbox.max.Y == pytest.approx(expected_depth, abs=1), f"Mortise Y max: {bbox.max.Y}"
        
        # Mortise centered on Z
        expected_height = joint.tenon_height + joint.clearance
        expected_z_min = (80 - expected_height) / 2
        expected_z_max = (80 + expected_height) / 2
        assert bbox.min.Z == pytest.approx(expected_z_min, abs=1), f"Mortise Z min: {bbox.min.Z}"
        assert bbox.max.Z == pytest.approx(expected_z_max, abs=1), f"Mortise Z max: {bbox.max.Z}"

    def test_tenon_cut_position(self):
        """Tenon cut should be at end of cross timber."""
        main, cross, main_cut, cross_cut, joint = create_tenon_mortise_joint_cuts()
        bbox = cross_cut.bounding_box()
        
        # Tenon cut at end: X from (length - tenon_length) to length
        assert bbox.min.X == pytest.approx(250, abs=1), f"Tenon cut X min: {bbox.min.X}"
        assert bbox.max.X == pytest.approx(300, abs=1), f"Tenon cut X max: {bbox.max.X}"
        
        # Full width and height of timber (material removed around tenon)
        assert bbox.min.Y == pytest.approx(0, abs=1)
        assert bbox.max.Y == pytest.approx(80, abs=1)
        assert bbox.min.Z == pytest.approx(0, abs=1)
        assert bbox.max.Z == pytest.approx(80, abs=1)

    def test_mortise_volume(self):
        """Mortise should remove (width+clearance) × depth × (height+clearance)."""
        main, cross, joint = create_tenon_mortise_joint_applied()
        
        # Expected mortise volume (rectangular hole)
        mortise_width = joint.tenon_width + joint.clearance
        mortise_depth = joint.tenon_length + joint.clearance
        mortise_height = joint.tenon_height + joint.clearance
        expected_removal = mortise_width * mortise_depth * mortise_height
        
        actual_removal = main.blank.volume - main.shape.volume
        assert actual_removal == pytest.approx(expected_removal, rel=0.01), \
            f"Mortise volume: {actual_removal:.0f}, expected: {expected_removal:.0f}"

    def test_tenon_volume(self):
        """Tenon cut should remove full end minus the tenon volume."""
        main, cross, joint = create_tenon_mortise_joint_applied()
        
        # Full end that gets cut: tenon_length × width × height
        # Minus tenon that stays: tenon_length × tenon_width × tenon_height
        full_cut = joint.tenon_length * cross.width * cross.height
        tenon_volume = joint.tenon_length * joint.tenon_width * joint.tenon_height
        expected_removal = full_cut - tenon_volume
        
        actual_removal = cross.blank.volume - cross.shape.volume
        assert actual_removal == pytest.approx(expected_removal, rel=0.01), \
            f"Tenon cut volume: {actual_removal:.0f}, expected: {expected_removal:.0f}"

    def test_resulting_shape_bbox(self):
        """After cuts, outer bounding boxes should remain unchanged."""
        main, cross, joint = create_tenon_mortise_joint_applied()
        
        main_bbox = main.shape.bounding_box()
        cross_bbox = cross.shape.bounding_box()
        
        # Main timber bbox unchanged (mortise is internal)
        assert main_bbox.min.X == pytest.approx(0, abs=1)
        assert main_bbox.max.X == pytest.approx(400, abs=1)
        
        # Cross timber bbox unchanged (tenon extends to original end)
        assert cross_bbox.min.X == pytest.approx(0, abs=1)
        assert cross_bbox.max.X == pytest.approx(300, abs=1)

    def test_cross_timber_is_single_solid(self):
        """Cross timber with tenon should remain one connected solid."""
        main, cross, joint = create_tenon_mortise_joint_applied()
        assert len(cross.shape.solids()) == 1, "Tenon should be connected to timber body"
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


class TestJointValidationPlan:
    def test_boolean_volume_conservation_plan(self, main_timber, cross_timber):
        """TODO: Algorithm sketch
        1. Clone timbers before joint.apply(), capturing baseline volumes (BV_main, BV_cross).
        2. Apply joint, recompute volumes (AV_main, AV_cross) and removed material solids if available.
        3. Compute theoretical removal volume from joint parameters (e.g., lap_depth * overlap_area).
        4. Assert |(BV−AV) − theory| < tolerance for both timbers; flag overcuts that exceed spec.
        5. Repeat across random sizes to ensure scaling correctness."""
        pytest.skip("Pending implementation - see plan in docstring")

    def test_reference_surface_alignment_plan(self, main_timber, cross_timber):
        """TODO: Algorithm sketch
        1. For each joint type, define expected ConnectionPoint on main & cross plus reference normal vectors.
        2. After joint.align(), query actual face normals using nearest-face lookup.
        3. Compare normals via dot product, ensure offsets from timber start/end equal requested distances.
        4. Validate cross timber orientation (Euler angles) against the joint's orientation enum meaning.
        5. Use randomized main timber rotations to ensure world-space invariance."""
        pytest.skip("Pending implementation - see plan in docstring")

    def test_parametric_dimension_limits_plan(self, main_timber, cross_timber):
        """TODO: Algorithm sketch
        1. Define legal ranges for each joint parameter.
        2. Use property-based testing (Hypothesis) to generate values inside/outside bounds.
        3. For valid values, compute derived dimensions and assert they are ≤ parent timber dims.
        4. For invalid values, assert ValueError with explicit message substring.
        5. Store failing seeds to reproduce regressions."""
        pytest.skip("Pending implementation - see plan in docstring")

    def test_tooling_clearance_plan(self, main_timber, cross_timber):
        """TODO: Algorithm sketch
        1. After joint.apply(), extract edge curves of the cut feature.
        2. Measure smallest internal fillet radius/kerf width and compare against configured tooling diameter.
        3. Fail if any radius < tool_radius/2 or if slot depth exceeds tooling reach.
        4. Provide per-joint tooling profiles so the same test validates dovetails, birdsmouths, etc."""
        pytest.skip("Pending implementation - see plan in docstring")
