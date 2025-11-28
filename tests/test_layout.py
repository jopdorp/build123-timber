import pytest
import math
from build123d import Location

from build123_timber import (
    Beam,
    Timber,
    LinearLayout,
    RafterLayout,
    StudLayout,
)


class TestLinearLayout:
    def test_positions_with_spacing(self):
        beam = Beam(length=1000, width=80, height=80)
        layout = LinearLayout(along=beam, spacing=200)

        positions = layout.positions()

        assert len(positions) == 6
        assert positions[0] == 0
        assert positions[-1] == 1000

    def test_positions_with_count(self):
        beam = Beam(length=1000, width=80, height=80)
        layout = LinearLayout(along=beam, count=5)

        positions = layout.positions()

        assert len(positions) == 5
        assert positions[0] == 0
        assert positions[-1] == 1000
        assert positions[2] == 500

    def test_positions_with_count_one(self):
        beam = Beam(length=1000, width=80, height=80)
        layout = LinearLayout(along=beam, count=1)

        positions = layout.positions()

        assert len(positions) == 1
        assert positions[0] == 500

    def test_skip_start(self):
        beam = Beam(length=1000, width=80, height=80)
        layout = LinearLayout(along=beam, spacing=200, skip_start=True)

        positions = layout.positions()

        assert len(positions) == 5
        assert positions[0] == 200

    def test_skip_end(self):
        beam = Beam(length=1000, width=80, height=80)
        layout = LinearLayout(along=beam, spacing=200, skip_end=True)

        positions = layout.positions()

        assert len(positions) == 5
        assert positions[-1] == 800

    def test_skip_both_ends(self):
        beam = Beam(length=1000, width=80, height=80)
        layout = LinearLayout(along=beam, spacing=200, skip_start=True, skip_end=True)

        positions = layout.positions()

        assert len(positions) == 4
        assert positions[0] == 200
        assert positions[-1] == 800

    def test_start_offset(self):
        beam = Beam(length=1000, width=80, height=80)
        layout = LinearLayout(along=beam, spacing=200, start_offset=100)

        positions = layout.positions()

        assert positions[0] == 100

    def test_end_offset(self):
        beam = Beam(length=1000, width=80, height=80)
        layout = LinearLayout(along=beam, spacing=200, end_offset=100)

        positions = layout.positions()

        assert positions[-1] <= 900

    def test_no_spacing_or_count_raises(self):
        beam = Beam(length=1000, width=80, height=80)
        layout = LinearLayout(along=beam)

        with pytest.raises(ValueError):
            layout.positions()

    def test_zero_count_returns_empty(self):
        beam = Beam(length=1000, width=80, height=80)
        layout = LinearLayout(along=beam, count=0)

        positions = layout.positions()

        assert len(positions) == 0

    def test_zero_spacing_returns_empty(self):
        beam = Beam(length=1000, width=80, height=80)
        layout = LinearLayout(along=beam, spacing=0)

        positions = layout.positions()

        assert len(positions) == 0


class TestLinearLayoutEvenDistribution:
    def test_even_distribution_with_count(self):
        beam = Beam(length=1200, width=80, height=80)
        layout = LinearLayout(along=beam, count=7)

        positions = layout.positions()

        for i in range(len(positions) - 1):
            spacing = positions[i + 1] - positions[i]
            assert abs(spacing - 200) < 0.01

    def test_count_with_offsets(self):
        beam = Beam(length=1000, width=80, height=80)
        layout = LinearLayout(along=beam, count=5, start_offset=100, end_offset=100)

        positions = layout.positions()

        assert len(positions) == 5
        assert positions[0] == 100
        assert positions[-1] == 900


class TestRafterLayout:
    def test_generate_returns_pairs(self):
        plate_front = Beam(length=3000, width=100, height=150, location=Location((0, 50, 2400)))
        plate_back = Beam(length=3000, width=100, height=150, location=Location((0, 3950, 2400)))
        ridge = Beam(length=3000, width=100, height=150, location=Location((0, 2000, 3500)))

        layout = RafterLayout(
            plate_front=plate_front,
            plate_back=plate_back,
            ridge=ridge,
            rafter_width=60,
            rafter_height=150,
            pitch=30,
            count=3,
        )

        rafters = list(layout.generate())

        assert len(rafters) == 6

    def test_generate_with_spacing(self):
        plate_front = Beam(length=3000, width=100, height=150, location=Location((0, 50, 2400)))
        plate_back = Beam(length=3000, width=100, height=150, location=Location((0, 3950, 2400)))
        ridge = Beam(length=3000, width=100, height=150, location=Location((0, 2000, 3500)))

        layout = RafterLayout(
            plate_front=plate_front,
            plate_back=plate_back,
            ridge=ridge,
            rafter_width=60,
            rafter_height=150,
            pitch=30,
            spacing=1000,
        )

        rafters = list(layout.generate())

        assert len(rafters) >= 4

    def test_rafters_have_correct_dimensions(self):
        plate_front = Beam(length=3000, width=100, height=150, location=Location((0, 50, 2400)))
        plate_back = Beam(length=3000, width=100, height=150, location=Location((0, 3950, 2400)))
        ridge = Beam(length=3000, width=100, height=150, location=Location((0, 2000, 3500)))

        layout = RafterLayout(
            plate_front=plate_front,
            plate_back=plate_back,
            ridge=ridge,
            rafter_width=60,
            rafter_height=150,
            pitch=30,
            count=2,
        )

        for rafter, location in layout.generate():
            assert rafter.width == 60
            assert rafter.height == 150

    def test_skip_ends(self):
        plate_front = Beam(length=3000, width=100, height=150, location=Location((0, 50, 2400)))
        plate_back = Beam(length=3000, width=100, height=150, location=Location((0, 3950, 2400)))
        ridge = Beam(length=3000, width=100, height=150, location=Location((0, 2000, 3500)))

        layout_with_ends = RafterLayout(
            plate_front=plate_front,
            plate_back=plate_back,
            ridge=ridge,
            rafter_width=60,
            rafter_height=150,
            pitch=30,
            count=5,
            skip_ends=False,
        )

        layout_skip_ends = RafterLayout(
            plate_front=plate_front,
            plate_back=plate_back,
            ridge=ridge,
            rafter_width=60,
            rafter_height=150,
            pitch=30,
            count=5,
            skip_ends=True,
        )

        rafters_with_ends = list(layout_with_ends.generate())
        rafters_skip_ends = list(layout_skip_ends.generate())

        assert len(rafters_skip_ends) < len(rafters_with_ends)

    def test_overhang_increases_length(self):
        plate_front = Beam(length=3000, width=100, height=150, location=Location((0, 50, 2400)))
        plate_back = Beam(length=3000, width=100, height=150, location=Location((0, 3950, 2400)))
        ridge = Beam(length=3000, width=100, height=150, location=Location((0, 2000, 3500)))

        layout_no_overhang = RafterLayout(
            plate_front=plate_front,
            plate_back=plate_back,
            ridge=ridge,
            rafter_width=60,
            rafter_height=150,
            pitch=30,
            count=1,
            overhang=0,
        )

        layout_with_overhang = RafterLayout(
            plate_front=plate_front,
            plate_back=plate_back,
            ridge=ridge,
            rafter_width=60,
            rafter_height=150,
            pitch=30,
            count=1,
            overhang=300,
        )

        rafters_no = list(layout_no_overhang.generate())
        rafters_with = list(layout_with_overhang.generate())

        assert rafters_with[0][0].length > rafters_no[0][0].length


class TestStudLayout:
    def test_generate_returns_studs(self):
        bottom = Beam(length=3000, width=100, height=50, location=Location((0, 0, 0)))
        top = Beam(length=3000, width=100, height=50, location=Location((0, 0, 2400)))

        layout = StudLayout(
            bottom_plate=bottom,
            top_plate=top,
            stud_width=50,
            stud_depth=100,
            count=5,
        )

        studs = list(layout.generate())

        assert len(studs) >= 3

    def test_studs_correct_length(self):
        bottom = Beam(length=3000, width=100, height=50, location=Location((0, 0, 0)))
        top = Beam(length=3000, width=100, height=50, location=Location((0, 0, 2400)))

        layout = StudLayout(
            bottom_plate=bottom,
            top_plate=top,
            stud_width=50,
            stud_depth=100,
            count=3,
        )

        for stud in layout.generate():
            expected_length = 2400 - 50
            assert abs(stud.length - expected_length) < 1

    def test_studs_vertical_orientation(self):
        bottom = Beam(length=3000, width=100, height=50, location=Location((0, 0, 0)))
        top = Beam(length=3000, width=100, height=50, location=Location((0, 0, 2400)))

        layout = StudLayout(
            bottom_plate=bottom,
            top_plate=top,
            stud_width=50,
            stud_depth=100,
            spacing=600,
        )

        for stud in layout.generate():
            rot = tuple(stud.location.orientation)
            assert abs(rot[1] - (-90)) < 1


class TestLayoutIntegration:
    def test_linear_layout_for_joists(self):
        beam = Beam(length=4000, width=100, height=200, location=Location((0, 0, 0)))
        layout = LinearLayout(along=beam, spacing=400, skip_start=True, skip_end=True)

        positions = layout.positions()
        joists = []

        for i, pos in enumerate(positions):
            joist = Timber.joist(
                length=3000,
                width=50,
                height=200,
                name=f"joist_{i}",
                location=Location((pos, 0, 0), (0, 0, 90)),
            )
            joists.append(joist)

        assert len(joists) == len(positions)
        for joist in joists:
            assert joist.length == 3000


class TestLayoutValidationPlan:
    def test_linear_layout_structural_spacing_plan(self):
        """TODO: Algorithm sketch
        1. Create fixtures for common joist/rafter spans with mandated spacing (e.g., 400, 600 mm OC).
        2. Run LinearLayout with spacing/count/offset permutations.
        3. Compute consecutive deltas of positions and compare with target spacing ± tolerance.
        4. Validate first/last positions respect skip/start offsets by ensuring distance to ends ≥ bearing requirement.
        5. Emit descriptive failure messages referencing code tables."""
        pytest.skip("Pending implementation - see plan in docstring")

    def test_rafter_layout_paired_geometry_plan(self):
        """TODO: Algorithm sketch
        1. Generate rafters via RafterLayout for known geometry (given pitch, overhang, seat depth).
        2. For each rafter solid, intersect with plate/ridge planes to extract heel and seat cut polygons.
        3. Measure bearing lengths and compare to theoretical `rafter_height * cos(pitch)` etc.
        4. Confirm mirrored rafters share axes and their apex meets the ridge centerline within tolerance."""
        pytest.skip("Pending implementation - see plan in docstring")

    def test_stud_layout_load_path_plan(self):
        """TODO: Algorithm sketch
        1. Define roof/joist load points projected onto the top plate.
        2. Generate studs and collect their centerlines.
        3. Project load points to wall plane and ensure each lands within tolerance of a stud centerline.
        4. Fail if any load lacks supporting stud or if stud spacing exceeds max allowed for the wall type."""
        pytest.skip("Pending implementation - see plan in docstring")
