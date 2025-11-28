import pytest
import math
from build123d import Location, Vector

from build123_timber import (
    Beam,
    Timber,
    LLapJoint,
    TLapJoint,
    XLapJoint,
    LMiterJoint,
    TenonMortiseJoint,
    DovetailJoint,
    ConnectionPoint,
    ConnectionEnd,
    TimberFace,
    CrossOrientation,
    JointAlignment,
    START,
    END,
    CENTER,
    show_lcs,
    make_timber_axis,
    auto_align,
)


class TestConnectionPoint:
    def test_start_constant(self):
        assert START.end == ConnectionEnd.START

    def test_end_constant(self):
        assert END.end == ConnectionEnd.END

    def test_center_constant(self):
        assert CENTER.end == ConnectionEnd.CENTER

    def test_resolve_start(self):
        timber = Beam(length=400, width=80, height=80)
        assert START.resolve(timber) == 0.0

    def test_resolve_end(self):
        timber = Beam(length=400, width=80, height=80)
        assert END.resolve(timber) == 400.0

    def test_resolve_center(self):
        timber = Beam(length=400, width=80, height=80)
        assert CENTER.resolve(timber) == 200.0

    def test_at_position(self):
        timber = Beam(length=400, width=80, height=80)
        point = ConnectionPoint.at(150)
        assert point.resolve(timber) == 150.0

    def test_at_fraction(self):
        timber = Beam(length=400, width=80, height=80)
        point = ConnectionPoint.at_fraction(0.25)
        assert point.resolve(timber) == 100.0

    def test_at_fraction_invalid(self):
        with pytest.raises(ValueError):
            ConnectionPoint.at_fraction(1.5)

    def test_at_fraction_zero(self):
        timber = Beam(length=400, width=80, height=80)
        point = ConnectionPoint.at_fraction(0.0)
        assert point.resolve(timber) == 0.0

    def test_at_fraction_one(self):
        timber = Beam(length=400, width=80, height=80)
        point = ConnectionPoint.at_fraction(1.0)
        assert point.resolve(timber) == 400.0


class TestJointAlignment:
    def test_compute_basic_location(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=300, width=80, height=80)

        alignment = JointAlignment(
            main_point=END,
            main_face=TimberFace.END,
            cross_point=START,
            cross_face=TimberFace.START,
            orientation=CrossOrientation.PERPENDICULAR,
        )

        loc = alignment.compute_cross_location(main, cross)
        pos = loc.position

        assert abs(pos.X - 400) < 100

    def test_alignment_with_offset(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=300, width=80, height=80)

        alignment = JointAlignment(
            main_point=END,
            main_face=TimberFace.END,
            cross_point=START,
            cross_face=TimberFace.START,
            offset=(10, 20, 30),
        )

        loc = alignment.compute_cross_location(main, cross)
        pos = loc.position

        assert pos.X > 390


class TestLLapJointAlignment:
    def test_align_positions_cross_at_main_end(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=300, width=80, height=80)

        joint = LLapJoint(main=main, cross=cross)
        joint.align()

        cross_pos = cross.location.position
        assert abs(cross_pos.X - 400) < 100

    def test_align_cross_perpendicular(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=300, width=80, height=80)

        joint = LLapJoint(main=main, cross=cross)
        joint.align()

        cross_rot = tuple(cross.location.orientation)
        assert abs(abs(cross_rot[2]) - 90) < 5 or cross_rot[2] == 0

    def test_align_preserves_main_location(self):
        main = Beam(length=400, width=80, height=80, location=Location((100, 200, 300)))
        cross = Beam(length=300, width=80, height=80)

        original_main_pos = main.location.position

        joint = LLapJoint(main=main, cross=cross)
        joint.align()

        assert main.location.position.X == original_main_pos.X
        assert main.location.position.Y == original_main_pos.Y
        assert main.location.position.Z == original_main_pos.Z

    def test_align_with_rotated_main(self):
        main = Beam(length=400, width=80, height=80, location=Location((0, 0, 0), (0, 0, 45)))
        cross = Beam(length=300, width=80, height=80)

        joint = LLapJoint(main=main, cross=cross)
        joint.align()

        cross_rot = tuple(cross.location.orientation)
        assert cross_rot[2] != 0

    def test_shapes_meet_at_corner(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=300, width=80, height=80)

        joint = LLapJoint(main=main, cross=cross)
        joint.align()
        joint.apply()

        main_bb = main.global_shape.bounding_box()
        cross_bb = cross.global_shape.bounding_box()

        assert abs(main_bb.max.X - cross_bb.min.X) < 200
        assert main_bb.max.Y > cross_bb.min.Y or cross_bb.max.Y > main_bb.min.Y


class TestTLapJointAlignment:
    def test_align_positions_cross_at_main_center(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=300, width=80, height=80)

        joint = TLapJoint(main=main, cross=cross)
        joint.align()

        cross_pos = cross.location.position
        assert abs(cross_pos.X - 200) < 100

    def test_align_with_custom_main_position(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=300, width=80, height=80)

        joint = TLapJoint(main=main, cross=cross, main_point=100)
        joint.align()

        cross_pos = cross.location.position
        assert abs(cross_pos.X - 100) < 100

    def test_align_with_fraction_position(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=300, width=80, height=80)

        joint = TLapJoint(main=main, cross=cross, main_point=ConnectionPoint.at_fraction(0.75))
        joint.align()

        cross_pos = cross.location.position
        assert abs(cross_pos.X - 300) < 100


class TestXLapJointAlignment:
    def test_align_positions_both_at_centers(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=400, width=80, height=80)

        joint = XLapJoint(main=main, cross=cross)
        joint.align()

        cross_pos = cross.location.position
        assert abs(cross_pos.X - 200) < 100

    def test_shapes_intersect_at_centers(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=400, width=80, height=80)

        joint = XLapJoint(main=main, cross=cross)
        joint.align()
        joint.apply()

        main_center = Vector(200, 0, 0)
        cross_center = cross.location.position

        distance = abs(main_center.X - cross_center.X)
        assert distance < 150


class TestMiterJointAlignment:
    def test_align_positions_cross_at_main_end(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=300, width=80, height=80)

        joint = LMiterJoint(main=main, cross=cross)
        joint.align()

        cross_pos = cross.location.position
        assert abs(cross_pos.X - 400) < 100


class TestTenonMortiseAlignment:
    def test_align_positions_cross_perpendicular(self):
        main = Beam(length=400, width=100, height=100)
        cross = Beam(length=300, width=60, height=80)

        joint = TenonMortiseJoint(main=main, cross=cross, tenon_length=40)
        joint.align()

        cross_rot = tuple(cross.location.orientation)
        assert cross_rot[2] != 0 or cross_rot[0] != 0


class TestChainedCalls:
    def test_align_returns_joint(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=300, width=80, height=80)

        joint = LLapJoint(main=main, cross=cross)
        result = joint.align()

        assert result is joint

    def test_chained_align_apply(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=300, width=80, height=80)

        result = LLapJoint(main=main, cross=cross).align().apply()

        assert result == (main, cross)
        assert len(main._features) > 0 or len(cross._features) > 0

    def test_full_workflow(self):
        main = Beam(length=400, width=80, height=80, location=Location((0, 0, 0)))
        cross = Beam(length=300, width=80, height=80)

        LLapJoint(main=main, cross=cross).align().apply()

        main_shape = main.global_shape
        cross_shape = cross.global_shape

        assert main_shape.volume < 400 * 80 * 80
        assert cross_shape.volume < 300 * 80 * 80


class TestMultipleJointsOnSameMain:
    def test_two_t_joints_at_different_positions(self):
        main = Beam(length=600, width=80, height=80)
        cross1 = Beam(length=200, width=60, height=60)
        cross2 = Beam(length=200, width=60, height=60)

        TLapJoint(main=main, cross=cross1, main_point=150).align().apply()
        TLapJoint(main=main, cross=cross2, main_point=450).align().apply()

        cross1_x = cross1.location.position.X
        cross2_x = cross2.location.position.X

        assert abs(cross1_x - 150) < 150
        assert abs(cross2_x - 450) < 150
        assert abs(cross2_x - cross1_x - 300) < 150


class TestEdgeCases:
    def test_align_with_zero_length_timber_raises(self):
        with pytest.raises(ValueError):
            Beam(length=0, width=80, height=80)

    def test_align_with_negative_length_raises(self):
        with pytest.raises(ValueError):
            Beam(length=-100, width=80, height=80)

    def test_align_cross_start_not_at_zero(self):
        main = Beam(length=400, width=80, height=80)
        cross = Beam(length=300, width=80, height=80)

        joint = TLapJoint(main=main, cross=cross, cross_point=CENTER)
        joint.align()

        cross_pos = cross.location.position
        assert cross_pos.X < 400


class TestShowLcs:
    def test_returns_three_edges(self):
        beam = Beam(length=400, width=80, height=80)
        x, y, z = show_lcs(beam, size=50)
        
        from build123d import Edge
        assert isinstance(x, Edge)
        assert isinstance(y, Edge)
        assert isinstance(z, Edge)

    def test_axes_start_at_timber_origin(self):
        beam = Beam(length=400, width=80, height=80, location=Location((100, 200, 300)))
        x, y, z = show_lcs(beam, size=50)
        
        origin = beam.location.position
        x_start = x.start_point()
        assert abs(x_start.X - origin.X) < 1
        assert abs(x_start.Y - origin.Y) < 1
        assert abs(x_start.Z - origin.Z) < 1

    def test_rotated_timber_axes_rotate(self):
        beam = Beam(length=400, width=80, height=80, location=Location((0, 0, 0), (0, 0, 90)))
        x, y, z = show_lcs(beam, size=100)
        
        x_end = x.end_point()
        assert abs(x_end.Y - 100) < 1


class TestMakeTimberAxis:
    def test_axis_at_origin(self):
        beam = Beam(length=400, width=80, height=80)
        axis = make_timber_axis(beam, Vector(0, 0, 0), Vector(1, 0, 0))
        
        assert abs(axis.position.X) < 1
        assert abs(axis.position.Y) < 1
        assert abs(axis.position.Z) < 1
        assert abs(axis.direction.X - 1) < 0.01

    def test_axis_at_end(self):
        beam = Beam(length=400, width=80, height=80)
        axis = make_timber_axis(beam, Vector(400, 0, 0), Vector(1, 0, 0))
        
        assert abs(axis.position.X - 400) < 1

    def test_rotated_timber_axis(self):
        beam = Beam(length=400, width=80, height=80, location=Location((0, 0, 0), (0, 0, 90)))
        axis = make_timber_axis(beam, Vector(100, 0, 0), Vector(1, 0, 0))
        
        assert abs(axis.position.Y - 100) < 1
        assert abs(axis.direction.Y - 1) < 0.01


class TestAutoAlign:
    def test_aligns_post_vertical_into_plate(self):
        plate = Beam(length=600, width=100, height=100)
        post = Timber.post(length=400, width=80, height=80, location=Location((800, 0, 200)))
        
        tenon_axis = make_timber_axis(post, Vector(0, 0, 0), Vector(-1, 0, 0))
        mortise_axis = make_timber_axis(plate, Vector(300, 0, 50), Vector(0, 0, 1))
        
        auto_align(post, tenon_axis, plate, mortise_axis)
        
        post_pos = post.location.position
        assert abs(post_pos.X - 300) < 1
        assert abs(post_pos.Z - 50) < 1

    def test_aligns_beam_horizontal_into_post(self):
        post = Timber.post(length=500, width=100, height=100, location=Location((0, 0, 0), (90, 0, 0)))
        beam = Beam(length=400, width=80, height=80, location=Location((500, 0, 100)))
        
        tenon_axis = make_timber_axis(beam, Vector(400, 0, 0), Vector(1, 0, 0))
        mortise_axis = make_timber_axis(post, Vector(50, 0, 250), Vector(0, 1, 0))
        
        initial_beam_z = beam.location.position.Z
        
        auto_align(beam, tenon_axis, post, mortise_axis)
        
        beam_pos = beam.location.position
        assert beam_pos.X != 500

    def test_preserves_main_timber_location(self):
        plate = Beam(length=600, width=100, height=100, location=Location((100, 200, 300)))
        post = Timber.post(length=400, width=80, height=80, location=Location((0, 0, 0)))
        
        original_plate_pos = plate.location.position
        
        tenon_axis = make_timber_axis(post, Vector(0, 0, 0), Vector(-1, 0, 0))
        mortise_axis = make_timber_axis(plate, Vector(300, 0, 50), Vector(0, 0, 1))
        
        auto_align(post, tenon_axis, plate, mortise_axis)
        
        assert plate.location.position.X == original_plate_pos.X
        assert plate.location.position.Y == original_plate_pos.Y
        assert plate.location.position.Z == original_plate_pos.Z


class TestAlignmentValidationPlan:
    def test_joint_alignment_face_snap_plan(self):
        """TODO: Algorithm sketch
        1. Enumerate every main_face/cross_face combination together with expected outward normal vectors in local coordinates.
        2. After calling Joint.align(), query the BREP face on the main timber closest to the theoretical contact plane.
        3. Sample three non-collinear points on both faces, transform them to world coords, and verify:
           a. Face normals are antiparallel (dot product approx -1).
           b. Projected polygons overlap by the required area (≥ tolerance) using shapely-style 2D projection.
           c. Edge distances from ConnectionPoint location equal the requested offsets (within mm tolerance).
        4. Repeat with the main timber rotated arbitrarily to guarantee world-space invariance."""
        pytest.skip("Pending implementation - see plan in docstring")

    def test_auto_align_axis_mapping_plan(self):
        """TODO: Algorithm sketch
        1. Build fixture pairs of Axis objects covering colinear, opposite, and skew configurations plus random rotations.
        2. Run auto_align() and capture the tenon timber's updated Location.
        3. Recompute tenon_axis after motion and verify:
           a. Axis.direction is parallel (dot≈1) to -mortise_axis.direction.
           b. Axis.position coincides with mortise_axis.position within tolerance.
           c. Associated shoulder plane normal (from closest face) is parallel to mortise host face.
        4. Assert translation magnitude equals analytic vector between axis bases prior to alignment."""
        pytest.skip("Pending implementation - see plan in docstring")

    def test_make_timber_axis_local_global_plan(self):
        """TODO: Algorithm sketch
        1. Generate thousands of random Euler rotations/offsets for a Timber instance.
        2. For each, pick random local anchor/direction vectors.
        3. Compute world coordinates via explicit homogeneous transform matrices.
        4. Call make_timber_axis() and assert both start point and direction match the manual transform within 1e-6 using vector norms.
        5. Include degenerate cases (zero-length direction) to confirm graceful failure."""
        pytest.skip("Pending implementation - see plan in docstring")

    def test_show_lcs_visual_regression_plan(self):
        """TODO: Algorithm sketch
        1. Use deterministic rotations and call show_lcs() to get three Edge objects.
        2. Sample parametric points (t=0.25,0.5,0.75) along each edge and compare with theoretical axis endpoints derived from the timber's Location transform.
        3. Fail the test if any deviation exceeds visual tolerance (e.g., 0.5 mm) to guarantee arrows remain trustworthy for debugging.
        4. (Optional) Export temporary SVG/JSON snapshots for manual regression when geometry kernels change."""
        pytest.skip("Pending implementation - see plan in docstring")
