"""Unit tests for brace alignment with snapshot values.

These tests verify that brace positions and orientations remain consistent
after refactoring. The explicit coordinate values serve as regression tests.
"""

import sys
import pytest

sys.path.insert(0, "src")

from build123d import Axis, Location
from timber_joints.beam import Beam
from timber_joints.alignment import (
    make_post_vertical,
    align_beam_in_post,
    create_brace_for_bent,
    create_brace_for_girt,
    build_complete_bent,
)


# Tolerance for floating point comparisons (in mm)
TOLERANCE = 0.001


class TestBentBraceAlignment:
    """Test brace alignment for bent (X-axis) braces."""

    @pytest.fixture
    def bent_setup(self):
        """Create a complete bent with braces on both posts."""
        left_post, right_post, beam, _ = build_complete_bent(
            post_height=3000,
            post_section=150,
            beam_length=5000,
            beam_section=150,
            tenon_length=60,
            shoulder_depth=20,
            housing_depth=20,
            post_top_extension=300,
        )

        brace_left_result = create_brace_for_bent(
            post=left_post,
            beam=beam,
            brace_section=100,
            distance_from_post=500,
            at_beam_start=True,
        )

        brace_right_result = create_brace_for_bent(
            post=right_post,
            beam=beam,
            brace_section=100,
            distance_from_post=500,
            at_beam_start=False,
        )

        return {
            "left_post": left_post,
            "right_post": right_post,
            "beam": beam,
            "brace_left": brace_left_result,
            "brace_right": brace_right_result,
        }

    def test_left_brace_position_snapshot(self, bent_setup):
        """Verify left brace bounding box matches expected snapshot values."""
        brace = bent_setup["brace_left"]
        bb = brace.shape.bounding_box()

        # Snapshot values from known-good alignment (verified visually 2024-11-30)
        expected = {
            "min_x": -42.426406771192546,
            "min_y": 25.0,
            "min_z": 2158.12486190167,
            "max_x": 392.76967183913126,
            "max_y": 125.00000000000003,
            "max_z": 2593.320940511994,
        }
        assert abs(bb.min.X - expected["min_x"]) < TOLERANCE, f"min.X: expected {expected['min_x']}, got {bb.min.X:.2f}"
        assert abs(bb.min.Y - expected["min_y"]) < TOLERANCE, f"min.Y: expected {expected['min_y']}, got {bb.min.Y:.2f}"
        assert abs(bb.min.Z - expected["min_z"]) < TOLERANCE, f"min.Z: expected {expected['min_z']}, got {bb.min.Z:.2f}"
        assert abs(bb.max.X - expected["max_x"]) < TOLERANCE, f"max.X: expected {expected['max_x']}, got {bb.max.X:.2f}"
        assert abs(bb.max.Y - expected["max_y"]) < TOLERANCE, f"max.Y: expected {expected['max_y']}, got {bb.max.Y:.2f}"
        assert abs(bb.max.Z - expected["max_z"]) < TOLERANCE, f"max.Z: expected {expected['max_z']}, got {bb.max.Z:.2f}"

    def test_left_brace_angle(self, bent_setup):
        """Verify left brace angle is 45 degrees."""
        brace = bent_setup["brace_left"]
        assert abs(brace.angle - 45.0) < 0.1, f"Expected 45°, got {brace.angle:.2f}°"

    def test_left_brace_at_beam_end(self, bent_setup):
        """Verify left brace is NOT at beam end (it's at beam start)."""
        brace = bent_setup["brace_left"]
        assert brace.at_beam_end is False

    def test_right_brace_position_snapshot(self, bent_setup):
        """Verify right brace bounding box matches expected snapshot values."""
        brace = bent_setup["brace_right"]
        bb = brace.shape.bounding_box()

        # Snapshot values from known-good alignment (verified visually 2024-11-30)
        expected = {
            "min_x": 4424.852813642386,
            "min_y": 25.000000000000014,
            "min_z": 2134.8528137423855,
            "max_x": 4882.426406771193,
            "max_y": 125.00000000000004,
            "max_z": 2592.4264068711927,
        }
        assert abs(bb.min.X - expected["min_x"]) < TOLERANCE, f"min.X: expected {expected['min_x']}, got {bb.min.X:.2f}"
        assert abs(bb.min.Y - expected["min_y"]) < TOLERANCE, f"min.Y: expected {expected['min_y']}, got {bb.min.Y:.2f}"
        assert abs(bb.min.Z - expected["min_z"]) < TOLERANCE, f"min.Z: expected {expected['min_z']}, got {bb.min.Z:.2f}"
        assert abs(bb.max.X - expected["max_x"]) < TOLERANCE, f"max.X: expected {expected['max_x']}, got {bb.max.X:.2f}"
        assert abs(bb.max.Y - expected["max_y"]) < TOLERANCE, f"max.Y: expected {expected['max_y']}, got {bb.max.Y:.2f}"
        assert abs(bb.max.Z - expected["max_z"]) < TOLERANCE, f"max.Z: expected {expected['max_z']}, got {bb.max.Z:.2f}"

    def test_right_brace_angle(self, bent_setup):
        """Verify right brace angle is 45 degrees."""
        brace = bent_setup["brace_right"]
        assert abs(brace.angle - 45.0) < 0.1, f"Expected 45°, got {brace.angle:.2f}°"

    def test_right_brace_at_beam_end(self, bent_setup):
        """Verify right brace IS at beam end."""
        brace = bent_setup["brace_right"]
        assert brace.at_beam_end is True

    def test_left_brace_penetrates_beam(self, bent_setup):
        """Verify left brace penetrates into the beam (max.Z > beam.min.Z)."""
        brace_bb = bent_setup["brace_left"].shape.bounding_box()
        beam_bb = bent_setup["beam"].bounding_box()
        assert brace_bb.max.Z > beam_bb.min.Z, "Left brace should penetrate into beam"

    def test_right_brace_penetrates_beam(self, bent_setup):
        """Verify right brace penetrates into the beam (max.Z > beam.min.Z)."""
        brace_bb = bent_setup["brace_right"].shape.bounding_box()
        beam_bb = bent_setup["beam"].bounding_box()
        assert brace_bb.max.Z > beam_bb.min.Z, "Right brace should penetrate into beam"

    def test_left_brace_penetrates_post(self, bent_setup):
        """Verify left brace penetrates into the left post."""
        brace_bb = bent_setup["brace_left"].shape.bounding_box()
        post_bb = bent_setup["left_post"].bounding_box()
        # Left brace min.X should be less than post max.X (penetrates into post)
        assert brace_bb.min.X < post_bb.max.X, "Left brace should penetrate into left post"

    def test_right_brace_penetrates_post(self, bent_setup):
        """Verify right brace penetrates into the right post."""
        brace_bb = bent_setup["brace_right"].shape.bounding_box()
        post_bb = bent_setup["right_post"].bounding_box()
        # Right brace max.X should be greater than post min.X (penetrates into post)
        assert brace_bb.max.X > post_bb.min.X, "Right brace should penetrate into right post"


class TestGirtBraceAlignment:
    """Test brace alignment for girt (Y-axis) braces."""

    @pytest.fixture
    def girt_setup(self):
        """Create a post with girt and brace."""
        post_height = 2500
        post_section = 150
        girt_length = 3000
        girt_section = 150

        post = Beam(length=post_height, width=post_section, height=post_section)
        girt = Beam(length=girt_length, width=girt_section, height=girt_section)

        vertical_post = make_post_vertical(post.shape)
        girt_along_y = girt.shape.rotate(Axis.Z, 90)

        post_bbox = vertical_post.bounding_box()
        girt_bbox = girt_along_y.bounding_box()
        drop_depth = girt_section
        target_x = (post_bbox.min.X + post_bbox.max.X) / 2 - (girt_bbox.min.X + girt_bbox.max.X) / 2
        target_z = post_bbox.max.Z - drop_depth - girt_bbox.min.Z
        target_y = post_bbox.max.Y - girt_bbox.min.Y

        positioned_girt = girt_along_y.move(Location((target_x, target_y, target_z)))

        brace_result = create_brace_for_girt(
            post=vertical_post,
            girt=positioned_girt,
            brace_section=100,
            distance_from_post=400,
            at_girt_start=False,
        )

        return {
            "post": vertical_post,
            "girt": positioned_girt,
            "brace": brace_result,
        }

    def test_girt_brace_position_snapshot(self, girt_setup):
        """Verify girt brace bounding box matches expected snapshot values."""
        brace = girt_setup["brace"]
        bb = brace.shape.bounding_box()

        # Snapshot values from known-good alignment (verified visually 2024-11-30)
        expected = {
            "min_x": -124.99999999999991,
            "min_y": 107.57359312880713,
            "min_z": 2034.8528137423855,
            "max_x": -24.99999999999983,
            "max_y": 465.14718625761435,
            "max_z": 2392.4264068711927,
        }
        assert abs(bb.min.X - expected["min_x"]) < TOLERANCE, f"min.X: expected {expected['min_x']}, got {bb.min.X:.2f}"
        assert abs(bb.min.Y - expected["min_y"]) < TOLERANCE, f"min.Y: expected {expected['min_y']}, got {bb.min.Y:.2f}"
        assert abs(bb.min.Z - expected["min_z"]) < TOLERANCE, f"min.Z: expected {expected['min_z']}, got {bb.min.Z:.2f}"
        assert abs(bb.max.X - expected["max_x"]) < TOLERANCE, f"max.X: expected {expected['max_x']}, got {bb.max.X:.2f}"
        assert abs(bb.max.Y - expected["max_y"]) < TOLERANCE, f"max.Y: expected {expected['max_y']}, got {bb.max.Y:.2f}"
        assert abs(bb.max.Z - expected["max_z"]) < TOLERANCE, f"max.Z: expected {expected['max_z']}, got {bb.max.Z:.2f}"

    def test_girt_brace_angle(self, girt_setup):
        """Verify girt brace angle is 45 degrees."""
        brace = girt_setup["brace"]
        assert abs(brace.angle - 45.0) < 0.1, f"Expected 45°, got {brace.angle:.2f}°"

    def test_girt_brace_at_beam_end(self, girt_setup):
        """Verify girt brace IS at girt end (at_girt_start=False means at_beam_end=True)."""
        brace = girt_setup["brace"]
        assert brace.at_beam_end is True

    def test_girt_brace_penetrates_girt(self, girt_setup):
        """Verify girt brace penetrates into the girt (max.Z > girt.min.Z)."""
        brace_bb = girt_setup["brace"].shape.bounding_box()
        girt_bb = girt_setup["girt"].bounding_box()
        assert brace_bb.max.Z > girt_bb.min.Z, "Girt brace should penetrate into girt"

    def test_girt_brace_penetrates_post(self, girt_setup):
        """Verify girt brace penetrates into the post."""
        brace_bb = girt_setup["brace"].shape.bounding_box()
        post_bb = girt_setup["post"].bounding_box()
        # Girt brace min.Y should be less than post max.Y (penetrates into post)
        assert brace_bb.min.Y < post_bb.max.Y, "Girt brace should penetrate into post"


class TestGirtBraceAtStartAlignment:
    """Test brace alignment for girt (Y-axis) braces with at_girt_start=True.
    
    This tests the case where the brace points toward -Y (away from +Y girt end).
    This was a missing test case that uncovered a bug in Y-axis correction.
    """

    @pytest.fixture
    def girt_start_setup(self):
        """Create a post with girt and brace pointing toward -Y."""
        post_height = 2500
        post_section = 150
        girt_length = 3000
        girt_section = 150

        post = Beam(length=post_height, width=post_section, height=post_section)
        girt = Beam(length=girt_length, width=girt_section, height=girt_section)

        vertical_post = make_post_vertical(post.shape)
        girt_along_y = girt.shape.rotate(Axis.Z, 90)

        post_bbox = vertical_post.bounding_box()
        girt_bbox = girt_along_y.bounding_box()
        drop_depth = girt_section
        target_x = (post_bbox.min.X + post_bbox.max.X) / 2 - (girt_bbox.min.X + girt_bbox.max.X) / 2
        target_z = post_bbox.max.Z - drop_depth - girt_bbox.min.Z
        target_y = post_bbox.max.Y - girt_bbox.min.Y

        positioned_girt = girt_along_y.move(Location((target_x, target_y, target_z)))

        brace_result = create_brace_for_girt(
            post=vertical_post,
            girt=positioned_girt,
            brace_section=100,
            distance_from_post=400,
            at_girt_start=True,  # Brace points toward -Y
        )

        return {
            "post": vertical_post,
            "girt": positioned_girt,
            "brace": brace_result,
        }

    def test_girt_brace_at_start_position_snapshot(self, girt_start_setup):
        """Verify girt brace (at_girt_start=True) bounding box matches expected snapshot values."""
        brace = girt_start_setup["brace"]
        bb = brace.shape.bounding_box()

        # Snapshot values from known-good alignment (verified visually 2024-11-30)
        expected = {
            "min_x": -124.99999999999991,
            "min_y": -291.8751380983298,
            "min_z": 2057.2303282608686,
            "max_x": -24.99999999999983,
            "max_y": 43.32094051199403,
            "max_z": 2392.4264068711927,
        }
        assert abs(bb.min.X - expected["min_x"]) < TOLERANCE, f"min.X: expected {expected['min_x']}, got {bb.min.X:.2f}"
        assert abs(bb.min.Y - expected["min_y"]) < TOLERANCE, f"min.Y: expected {expected['min_y']}, got {bb.min.Y:.2f}"
        assert abs(bb.min.Z - expected["min_z"]) < TOLERANCE, f"min.Z: expected {expected['min_z']}, got {bb.min.Z:.2f}"
        assert abs(bb.max.X - expected["max_x"]) < TOLERANCE, f"max.X: expected {expected['max_x']}, got {bb.max.X:.2f}"
        assert abs(bb.max.Y - expected["max_y"]) < TOLERANCE, f"max.Y: expected {expected['max_y']}, got {bb.max.Y:.2f}"
        assert abs(bb.max.Z - expected["max_z"]) < TOLERANCE, f"max.Z: expected {expected['max_z']}, got {bb.max.Z:.2f}"

    def test_girt_brace_at_start_angle(self, girt_start_setup):
        """Verify girt brace angle is 45 degrees."""
        brace = girt_start_setup["brace"]
        assert abs(brace.angle - 45.0) < 0.1, f"Expected 45°, got {brace.angle:.2f}°"

    def test_girt_brace_at_start_at_beam_end(self, girt_start_setup):
        """Verify girt brace is NOT at girt end (at_girt_start=True means at_beam_end=False)."""
        brace = girt_start_setup["brace"]
        assert brace.at_beam_end is False

    def test_girt_brace_at_start_penetrates_girt(self, girt_start_setup):
        """Verify girt brace penetrates into the girt (max.Z > girt.min.Z)."""
        brace_bb = girt_start_setup["brace"].shape.bounding_box()
        girt_bb = girt_start_setup["girt"].bounding_box()
        assert brace_bb.max.Z > girt_bb.min.Z, "Girt brace should penetrate into girt"

    def test_girt_brace_at_start_penetrates_post(self, girt_start_setup):
        """Verify girt brace penetrates into the post."""
        brace_bb = girt_start_setup["brace"].shape.bounding_box()
        post_bb = girt_start_setup["post"].bounding_box()
        # Girt brace max.Y should be greater than post min.Y (penetrates into post from -Y side)
        assert brace_bb.max.Y > post_bb.min.Y, "Girt brace should penetrate into post"


class TestBraceSymmetry:
    """Test that left and right braces are symmetric."""

    @pytest.fixture
    def bent_setup(self):
        """Create a complete bent with braces on both posts."""
        left_post, right_post, beam, _ = build_complete_bent(
            post_height=3000,
            post_section=150,
            beam_length=5000,
            beam_section=150,
            tenon_length=60,
            shoulder_depth=20,
            housing_depth=20,
            post_top_extension=300,
        )

        brace_left_result = create_brace_for_bent(
            post=left_post,
            beam=beam,
            brace_section=100,
            distance_from_post=500,
            at_beam_start=True,
        )

        brace_right_result = create_brace_for_bent(
            post=right_post,
            beam=beam,
            brace_section=100,
            distance_from_post=500,
            at_beam_start=False,
        )

        return {
            "brace_left": brace_left_result,
            "brace_right": brace_right_result,
            "beam": beam,
        }

    def test_braces_same_angle(self, bent_setup):
        """Both braces should have the same angle."""
        left_angle = bent_setup["brace_left"].angle
        right_angle = bent_setup["brace_right"].angle
        assert abs(left_angle - right_angle) < 0.1, f"Angles should match: {left_angle:.2f}° vs {right_angle:.2f}°"

    def test_braces_same_y_extent(self, bent_setup):
        """Both braces should have the same Y extent (width)."""
        left_bb = bent_setup["brace_left"].shape.bounding_box()
        right_bb = bent_setup["brace_right"].shape.bounding_box()
        
        left_y_extent = left_bb.max.Y - left_bb.min.Y
        right_y_extent = right_bb.max.Y - right_bb.min.Y
        
        assert abs(left_y_extent - right_y_extent) < TOLERANCE, \
            f"Y extents should match: {left_y_extent:.2f} vs {right_y_extent:.2f}"

    def test_braces_same_z_extent(self, bent_setup):
        """Both braces should have their correct Z extents."""
        left_bb = bent_setup["brace_left"].shape.bounding_box()
        right_bb = bent_setup["brace_right"].shape.bounding_box()
        
        left_z_extent = left_bb.max.Z - left_bb.min.Z
        right_z_extent = right_bb.max.Z - right_bb.min.Z
        
        # Expected values: left=435.1960786103241, right=457.5735931288072 (diff ~22mm due to quarter correction)
        assert abs(left_z_extent - 435.1960786103241) < TOLERANCE, f"Left Z extent: expected 435.1960786103241, got {left_z_extent:.2f}"
        assert abs(right_z_extent - 457.5735931288072) < TOLERANCE, f"Right Z extent: expected 457.5735931288072, got {right_z_extent:.2f}"

    def test_braces_similar_beam_penetration(self, bent_setup):
        """Both braces should penetrate the beam by similar amounts."""
        left_bb = bent_setup["brace_left"].shape.bounding_box()
        right_bb = bent_setup["brace_right"].shape.bounding_box()
        beam_bb = bent_setup["beam"].bounding_box()
        
        left_penetration = left_bb.max.Z - beam_bb.min.Z
        right_penetration = right_bb.max.Z - beam_bb.min.Z
        
        # Expected penetrations (differ slightly due to quarter correction)
        assert abs(left_penetration - 43.320940511994195) < TOLERANCE, \
            f"Left penetration: expected 43.320940511994195, got {left_penetration:.2f}"
        assert abs(right_penetration - 42.42640687119274) < TOLERANCE, \
            f"Right penetration: expected 42.42640687119274, got {right_penetration:.2f}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
