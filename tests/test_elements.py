import pytest
from build123d import Vector

from build123_timber.elements import Timber, Beam, Post


class TestTimber:
    def test_create_timber(self):
        t = Timber(length=1000, width=50, height=100)
        assert t.length == 1000
        assert t.width == 50
        assert t.height == 100

    def test_invalid_dimensions(self):
        with pytest.raises(ValueError):
            Timber(length=0, width=50, height=100)
        with pytest.raises(ValueError):
            Timber(length=1000, width=-50, height=100)
        with pytest.raises(ValueError):
            Timber(length=1000, width=50, height=0)

    def test_centerline(self):
        t = Timber(length=1000, width=50, height=100)
        start, end = t.centerline
        assert start == Vector(0, 0, 0)
        assert end == Vector(1000, 0, 0)

    def test_cross_section_area(self):
        t = Timber(length=1000, width=50, height=100)
        assert t.cross_section_area == 5000

    def test_volume(self):
        t = Timber(length=1000, width=50, height=100)
        assert t.volume == 5_000_000

    def test_blank_shape(self):
        t = Timber(length=1000, width=50, height=100)
        blank = t.blank
        assert blank is not None
        bbox = blank.bounding_box()
        assert abs(bbox.size.X - 1000) < 0.01
        assert abs(bbox.size.Y - 50) < 0.01
        assert abs(bbox.size.Z - 100) < 0.01

    def test_face_planes(self):
        t = Timber(length=1000, width=50, height=100)
        for face in ["top", "bottom", "left", "right", "start", "end"]:
            plane = t.get_face_plane(face)
            assert plane is not None


class TestFactoryMethods:
    def test_beam_factory(self):
        beam = Timber.beam(length=2000, width=50, height=150)
        assert beam.length == 2000
        assert beam.width == 50
        assert beam.height == 150

    def test_post_factory(self):
        post = Timber.post(length=2400, width=100, height=100)
        assert post.length == 2400

    def test_rafter_factory(self):
        rafter = Timber.rafter(length=3000, width=50, height=200)
        assert rafter.length == 3000
        assert rafter.category == "rafter"

    def test_joist_factory(self):
        joist = Timber.joist(length=4000, width=50, height=200)
        assert joist.length == 4000
        assert joist.category == "joist"

    def test_stud_factory(self):
        stud = Timber.stud(length=2400, width=40, height=90)
        assert stud.length == 2400
        assert stud.category == "stud"


class TestConvenienceAliases:
    def test_beam_alias(self):
        beam = Beam(length=2000, width=50, height=150)
        assert beam.length == 2000

    def test_post_alias(self):
        post = Post(length=2400, width=100, height=100)
        assert post.length == 2400

    def test_aliases_produce_timber(self):
        beam = Beam(length=2000, width=50, height=150)
        post = Post(length=2400, width=100, height=100)
        assert isinstance(beam, Timber)
        assert isinstance(post, Timber)
