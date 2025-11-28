"""Tests for timber member alignment."""
import pytest
from build123d import Location, Vector

from build123_timber import Beam, Timber, make_timber_axis, auto_align


# =============================================================================
# Factory functions for visual tests
# =============================================================================

def create_beam_on_post_aligned():
    """Create a beam aligned on top of a post (beam end on post top).
    
    Returns (post, beam) with beam positioned so its start sits on top of post,
    with beam edge aligned to post edge.
    """
    post = Timber.post(length=400, width=100, height=100)
    beam = Beam(length=600, width=100, height=80)
    
    # Post is rotated (0, -90, 0): local X->world Z, local Y->world Y, local Z->world -X
    # Post top-edge in local coords: X=length (top), Y=width/2 (center), Z=height (edge at world X=-100)
    # Direction +X in local becomes +Z in world
    post_axis = make_timber_axis(post, Vector(post.length, post.width/2, post.height), Vector(1, 0, 0))
    
    # Beam START (X=0) bottom, center of width (Y=width/2)
    beam_axis = make_timber_axis(beam, Vector(0, beam.width/2, 0), Vector(0, 0, -1))
    
    auto_align(beam, beam_axis, post, post_axis)
    
    return post, beam


def create_beam_in_post_with_tongue_and_fork():
    """Create beam dropped INTO post with tongue-and-fork joint.
    
    Tongue-and-fork is a mortise-tenon variant where:
    - The mortise goes through full post width (creating a "fork" - two prongs)
    - The beam has a central "tongue" (tenon) that fits in the fork slot
    - The beam sits DOWN into the post by its own height
    
    Returns (post, beam, joint) with joint applied.
    """
    from build123_timber.joints import TenonMortiseJoint
    
    post = Timber.post(length=400, width=100, height=100)
    beam = Beam(length=600, width=100, height=80)
    
    # Beam drops INTO post - beam bottom at (post_top - beam_height)
    # Post top is at Z=400 (local X=400), beam bottom should be at Z=320 (local X=320)
    # Post local X maps to world Z
    connection_x_local = post.length - beam.height  # Beam bottom position in post
    
    post_axis = make_timber_axis(
        post, 
        Vector(connection_x_local, post.width/2, post.height),  # At beam bottom level, centered Y, at edge
        Vector(1, 0, 0)
    )
    
    # Beam START (X=0), bottom center
    beam_axis = make_timber_axis(beam, Vector(0, beam.width/2, 0), Vector(0, 0, -1))
    
    auto_align(beam, beam_axis, post, post_axis)
    
    # Now apply the joint - through mortise creates the fork
    # Tongue (tenon) is 1/3 beam width, full beam height
    tongue_width = beam.width / 3
    
    # Mortise position: center of beam in post (local X = post.length - beam.height/2)
    mortise_x = post.length - beam.height / 2
    
    # For post with rotation (0,-90,0): local Z=height face points to world -X
    # Beam comes from world -X direction, so mortise enters from "right" (Z=height) face
    joint = TenonMortiseJoint(
        main=post,
        cross=beam,
        tenon_length=post.height,  # Through the full post height (Z direction = depth into post)
        tenon_height=beam.height,  # Full height of beam
        tenon_width=tongue_width,  # Central tongue
        through_tenon=True,  # Creates the fork by going all the way through
        mortise_x_position=mortise_x,  # At top of post where beam sits
        tenon_at_start=True,  # Tenon at start of beam (X=0)
        mortise_face="right",  # Mortise enters from Z=height face (faces world -X)
    )
    joint.apply()
    
    return post, beam, joint


# =============================================================================
# Tests
# =============================================================================

class TestBeamOnPostAlignment:
    """Test aligning a horizontal beam END on top of a vertical post."""

    def test_beam_end_on_post_z_alignment(self):
        """Beam end bottom should meet post top."""
        post, beam = create_beam_on_post_aligned()
        
        post_bbox = post.global_shape.bounding_box()
        beam_bbox = beam.global_shape.bounding_box()
        
        # Beam bottom should be at post top
        assert beam_bbox.min.Z == pytest.approx(post_bbox.max.Z, abs=1)

    def test_beam_end_on_post_edge_alignment(self):
        """Beam edge should align with post edge (not center)."""
        post, beam = create_beam_on_post_aligned()
        
        post_bbox = post.global_shape.bounding_box()
        beam_bbox = beam.global_shape.bounding_box()
        
        # Beam Y min should be at post Y min (edge aligned)
        assert beam_bbox.min.Y == pytest.approx(post_bbox.min.Y, abs=1)
        
        # Beam X min should be at post X min (beam starts at post edge)
        assert beam_bbox.min.X == pytest.approx(post_bbox.min.X, abs=1)

    def test_beam_in_post_with_tongue_and_fork(self):
        """Apply tongue-and-fork joint (through mortise-tenon) to beam in post.
        
        Beam should drop INTO post, with fork (through mortise) in post
        and tongue (tenon) on beam.
        """
        post, beam, joint = create_beam_in_post_with_tongue_and_fork()
        
        # Both timbers should have material removed
        post_removed = post.blank.volume - post.shape.volume
        beam_removed = beam.blank.volume - beam.shape.volume
        
        assert post_removed > 0, "Post should have fork (through mortise) cut"
        assert beam_removed > 0, "Beam should have tongue (tenon) formed"
        
        # Beam should still be a single solid (tongue connected)
        assert len(beam.shape.solids()) == 1, "Beam with tongue should be single solid"
        
        # Beam should be dropped into post
        post_bbox = post.global_shape.bounding_box()
        beam_bbox = beam.global_shape.bounding_box()
        
        # Beam bottom should be BELOW post top (inside the post)
        assert beam_bbox.min.Z < post_bbox.max.Z, "Beam should be dropped into post"
        # Beam bottom should be at post_top - beam_height
        expected_beam_bottom = post_bbox.max.Z - beam.height
        assert beam_bbox.min.Z == pytest.approx(expected_beam_bottom, abs=1)
