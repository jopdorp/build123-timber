"""Tests for Timber element creation, positioning, and rotation.

VALIDATION STRATEGY:
====================
Each test has a clear algorithm to validate correctness:

1. Dimension tests: Compare input values with stored properties exactly
2. Bounding box tests: Query geometry and verify dimensions match inputs
3. Position tests: Verify blank origin at corner (0, 0, 0)
4. Rotation tests: Apply rotation, verify bounding box and centerline transform correctly
5. Location tests: Verify world vs local coordinate transforms work correctly

STRUCTURE:
==========
Each test class has:
- create_* functions that generate the test fixtures (importable for visual validation)
- test_* functions that run assertions on the fixtures
"""
import pytest
import math
from build123d import Vector, Location, Box, Align

from build123_timber.elements import Timber, Beam, Post


# =============================================================================
# CREATION FUNCTIONS - Importable for visual validation in Jupyter notebook
# =============================================================================

def create_basic_timber():
    """Create a basic timber with standard dimensions."""
    return Timber(length=1000, width=50, height=100)


def create_timber_with_floats():
    """Create two timbers - integer and float dimensions - for comparison."""
    t_integer = Timber(length=1000, width=50, height=100)
    t_float = Timber(length=1000.5, width=50.25, height=100.75)
    return t_integer, t_float


def create_timber_with_name():
    """Create timber with name attribute."""
    return Timber(length=1000, width=50, height=100, name="main_beam")


def create_beam_via_factory():
    """Create beam using factory method.
    
    BEAM: Horizontal structural member spanning between supports.
    Default orientation: length along X (horizontal), height along Z.
    Typical use: floor beams, header beams, lintels.
    """
    return Timber.beam(length=2000, width=50, height=150)


def create_beam_via_alias():
    """Create beam using Beam alias."""
    return Beam(length=2000, width=50, height=150)


def create_post_via_factory():
    """Create post using factory method.
    
    POST: Vertical load-bearing member.
    Default orientation: length along Z (vertical), pointing up.
    Rotated 90° around Y axis so local X becomes world Z.
    Typical use: columns, vertical supports.
    """
    return Timber.post(length=2400, width=100, height=100)


def create_post_with_default_height():
    """Create post with default height (square section)."""
    return Timber.post(length=2400, width=100)


def create_rafter():
    """Create rafter with category auto-set.
    
    RAFTER: Sloped roof structural member.
    Default orientation: Pitched at 30° angle, sloping upward from start to end.
    The rafter rises from low (near origin) to high (away from origin).
    Typical use: roof framing from eave to ridge.
    """
    return Timber.rafter(length=3000, width=50, height=200)


def create_joist():
    """Create joist with category auto-set.
    
    JOIST: Horizontal member supporting floor or ceiling.
    Default orientation: length along X (horizontal), height along Z.
    Typically placed in parallel series.
    Typical use: floor framing, ceiling framing.
    """
    return Timber.joist(length=4000, width=50, height=200)


def create_stud():
    """Create stud with category auto-set.
    
    STUD: Vertical wall framing member.
    Default orientation: length along Z (vertical), pointing up.
    Rotated 90° around Y axis so local X becomes world Z.
    Typical use: wall framing between plates.
    """
    return Timber.stud(length=2400, width=40, height=90)


def create_girt():
    """Create girt with category auto-set.
    
    GIRT: Horizontal wall member connecting posts.
    Default orientation: length along Y (perpendicular to main span).
    Rotated 90° around Z axis so local X becomes world Y.
    Typical use: horizontal bracing between posts in timber frame walls.
    """
    return Timber.girt(length=3000, width=50, height=150)


def create_purlin():
    """Create purlin with category auto-set.
    
    PURLIN: Horizontal roof member perpendicular to rafters.
    Default orientation: length along Y (along the building length).
    Rotated 90° around Z axis so local X becomes world Y.
    Typical use: supports roof sheathing, spans between rafters.
    """
    return Timber.purlin(length=6000, width=50, height=100)


def create_plate():
    """Create plate with category auto-set.
    
    PLATE: Horizontal member at top/bottom of wall framing.
    Default orientation: length along Y (along the wall length).
    Rotated 90° around Z axis so local X becomes world Y.
    Typical use: top plate, bottom plate (sole plate) in wall framing.
    """
    return Timber.plate(length=4000, width=90, height=40)


def create_factory_methods_comparison():
    """Create all factory method timbers for visual comparison, pre-positioned.
    
    Returns a dict with members organized by orientation, positioned in rows
    with minimal spacing (just enough to not overlap).
    
    Row 1 (Y=0): ALONG X - beam, joist
    Row 2 (Y=300): ALONG Y - girt, purlin, plate (spread along X)
    Row 3 (Y=500): VERTICAL - post, stud
    Row 4 (Y=700): PITCHED - rafter
    
    Note: We pass location to the factory methods directly rather than using
    .moved() because .moved() compounds in local coordinates, but factory
    methods apply location in world coordinates before rotation.
    """
    # Row 1: Along X members (Y=0)
    # beam: 2000x50x150, joist: 4000x50x200
    beam = Timber.beam(length=2000, width=50, height=150)
    joist = Timber.joist(length=4000, width=50, height=200, location=Location((0, 100, 0)))
    
    # Row 2: Along Y members (spread along X since they extend in Y)
    # girt: X-size=50, purlin: X-size=50, plate: X-size=90
    girt = Timber.girt(length=3000, width=50, height=150, location=Location((0, 300, 0)))
    purlin = Timber.purlin(length=6000, width=50, height=100, location=Location((100, 300, 0)))
    plate = Timber.plate(length=4000, width=90, height=40, location=Location((200, 300, 0)))
    
    # Row 3: Vertical members (spread along X, further right to not overlap with Y members)
    # post: X-size=100, stud: X-size=90
    # Y members extend to Y=3000+ so place vertical members at X=350+
    post = Timber.post(length=2400, width=100, height=100, location=Location((350, 300, 0)))
    stud = Timber.stud(length=2400, width=40, height=90, location=Location((500, 300, 0)))
    
    # Pitched member (further right to not overlap with vertical members)
    # rafter extends along X (with pitch), place after stud
    rafter = Timber.rafter(length=3000, width=50, height=200, location=Location((650, 300, 0)))
    
    return {
        "beam": beam,
        "joist": joist,
        "girt": girt,
        "purlin": purlin,
        "plate": plate,
        "post": post,
        "stud": stud,
        "rafter": rafter,
    }


def create_timber_at_origin():
    """Create timber at default origin location."""
    return Timber(length=1000, width=50, height=100)


def create_timber_translated():
    """Create timber translated to (100, 200, 300)."""
    return Timber(length=1000, width=50, height=100, location=Location((100, 200, 300)))


def create_timber_rotated_z90():
    """Create timber rotated 90° around Z axis."""
    return Timber(length=1000, width=50, height=100, location=Location((0, 0, 0), (0, 0, 90)))


def create_timber_rotated_x90():
    """Create timber rotated 90° around X axis."""
    return Timber(length=1000, width=50, height=100, location=Location((0, 0, 0), (90, 0, 0)))


def create_timber_rotated_y90():
    """Create timber rotated 90° around Y axis."""
    return Timber(length=1000, width=50, height=100, location=Location((0, 0, 0), (0, 90, 0)))


def create_timber_rotated_arbitrary():
    """Create timber with arbitrary rotation."""
    return Timber(length=1000, width=50, height=100, location=Location((0, 0, 0), (45, 30, 60)))


def create_timber_rotated_and_translated():
    """Create timber rotated 90° Z then translated."""
    return Timber(length=1000, width=50, height=100, location=Location((100, 200, 0), (0, 0, 90)))


def create_timber_with_cut():
    """Create timber with a cutting feature applied.
    
    Cut is a 100×50×50 box at the origin corner (Align.MIN).
    """
    t = Timber(length=1000, width=50, height=100)
    cut = Box(100, 50, 50, align=(Align.MIN, Align.MIN, Align.MIN))
    t.add_feature(cut)
    return t


# =============================================================================
# TEST CLASSES
# =============================================================================

class TestTimberCreation:
    """Tests for basic Timber instantiation and dimension storage."""

    def test_create_timber_stores_dimensions(self):
        """Algorithm: Create timber, verify each dimension equals input exactly."""
        t = create_basic_timber()
        assert t.length == 1000
        assert t.width == 50
        assert t.height == 100

    def test_create_timber_with_floats(self):
        """Algorithm: Compare integer vs float timber - verify float precision preserved in geometry."""
        t_integer, t_float = create_timber_with_floats()
        
        # Verify stored dimensions
        assert t_integer.length == 1000
        assert t_float.length == 1000.5
        assert t_float.width == 50.25
        assert t_float.height == 100.75
        
        # Verify geometry reflects the difference
        bbox_int = t_integer.blank.bounding_box()
        bbox_float = t_float.blank.bounding_box()
        
        tol = 0.01
        assert abs(bbox_float.size.X - bbox_int.size.X - 0.5) < tol
        assert abs(bbox_float.size.Y - bbox_int.size.Y - 0.25) < tol
        assert abs(bbox_float.size.Z - bbox_int.size.Z - 0.75) < tol

    def test_create_timber_with_name(self):
        """Algorithm: Verify optional name attribute is stored."""
        t = create_timber_with_name()
        assert t.name == "main_beam"

    def test_create_timber_with_category(self):
        """Algorithm: Verify optional category attribute is stored."""
        t = Timber(length=1000, width=50, height=100, category="beam")
        assert t.category == "beam"

    def test_invalid_zero_length_raises(self):
        """Algorithm: Zero dimension must raise ValueError immediately."""
        with pytest.raises(ValueError, match="length must be positive"):
            Timber(length=0, width=50, height=100)

    def test_invalid_negative_width_raises(self):
        """Algorithm: Negative dimension must raise ValueError immediately."""
        with pytest.raises(ValueError, match="width must be positive"):
            Timber(length=1000, width=-50, height=100)

    def test_invalid_zero_height_raises(self):
        """Algorithm: Zero dimension must raise ValueError immediately."""
        with pytest.raises(ValueError, match="height must be positive"):
            Timber(length=1000, width=50, height=0)


class TestTimberFactories:
    """Tests for factory methods - verifying correct orientation and geometry.
    
    Each factory method creates a timber with a specific default orientation:
    - ALONG X: beam, joist (length along world X)
    - ALONG Y: girt, purlin, plate (length along world Y)
    - ALONG Z: post, stud (length along world Z, vertical)
    - PITCHED: rafter (angled, length partially along X and Z)
    
    We verify orientation by checking global_shape bounding box dimensions.
    """

    def test_beam_orientation_along_x(self):
        """Beam should be horizontal with length along X axis.
        
        Expected bbox: X=length(2000), Y=width(50), Z=height(150)
        """
        beam = create_beam_via_factory()
        bbox = beam.global_shape.bounding_box()
        
        tol = 0.01
        assert abs(bbox.size.X - 2000) < tol, f"Beam X should be 2000 (length), got {bbox.size.X}"
        assert abs(bbox.size.Y - 50) < tol, f"Beam Y should be 50 (width), got {bbox.size.Y}"
        assert abs(bbox.size.Z - 150) < tol, f"Beam Z should be 150 (height), got {bbox.size.Z}"
        # Verify starts at origin
        assert abs(bbox.min.X) < tol, "Beam should start at X=0"
        assert abs(bbox.min.Y) < tol, "Beam should start at Y=0"
        assert abs(bbox.min.Z) < tol, "Beam should start at Z=0"

    def test_beam_alias_equivalent_to_factory(self):
        """Beam alias should produce identical geometry to factory."""
        beam1 = create_beam_via_factory()
        beam2 = create_beam_via_alias()
        
        bbox1 = beam1.global_shape.bounding_box()
        bbox2 = beam2.global_shape.bounding_box()
        
        tol = 0.01
        assert abs(bbox1.size.X - bbox2.size.X) < tol
        assert abs(bbox1.size.Y - bbox2.size.Y) < tol
        assert abs(bbox1.size.Z - bbox2.size.Z) < tol

    def test_post_orientation_along_z(self):
        """Post should be vertical with length along Z axis.
        
        Expected bbox: X=height(100), Y=width(100), Z=length(2400)
        Post is rotated -90° around Y, so local X (length) becomes world Z.
        """
        post = create_post_via_factory()
        bbox = post.global_shape.bounding_box()
        
        tol = 0.01
        assert abs(bbox.size.Z - 2400) < tol, f"Post Z should be 2400 (length), got {bbox.size.Z}"
        assert abs(bbox.size.X - 100) < tol, f"Post X should be 100 (height), got {bbox.size.X}"
        assert abs(bbox.size.Y - 100) < tol, f"Post Y should be 100 (width), got {bbox.size.Y}"
        # Verify bottom at Z=0 (standing on ground)
        assert abs(bbox.min.Z) < tol, "Post should start at Z=0 (on ground)"

    def test_post_with_default_height_square_section(self):
        """Post with no height should have square cross-section (width × width)."""
        post = create_post_with_default_height()
        bbox = post.global_shape.bounding_box()
        
        tol = 0.01
        # Square section: both X and Y should equal width (100)
        assert abs(bbox.size.X - 100) < tol, "Post X should equal width"
        assert abs(bbox.size.Y - 100) < tol, "Post Y should equal width"

    def test_joist_orientation_along_x(self):
        """Joist should be horizontal with length along X axis.
        
        Expected bbox: X=length(4000), Y=width(50), Z=height(200)
        """
        joist = create_joist()
        bbox = joist.global_shape.bounding_box()
        
        tol = 0.01
        assert abs(bbox.size.X - 4000) < tol, f"Joist X should be 4000 (length), got {bbox.size.X}"
        assert abs(bbox.size.Y - 50) < tol, f"Joist Y should be 50 (width), got {bbox.size.Y}"
        assert abs(bbox.size.Z - 200) < tol, f"Joist Z should be 200 (height), got {bbox.size.Z}"
        assert joist.category == "joist"

    def test_stud_orientation_along_z(self):
        """Stud should be vertical with length along Z axis.
        
        Expected bbox: X=height(90), Y=width(40), Z=length(2400)
        """
        stud = create_stud()
        bbox = stud.global_shape.bounding_box()
        
        tol = 0.01
        assert abs(bbox.size.Z - 2400) < tol, f"Stud Z should be 2400 (length), got {bbox.size.Z}"
        assert abs(bbox.size.X - 90) < tol, f"Stud X should be 90 (height), got {bbox.size.X}"
        assert abs(bbox.size.Y - 40) < tol, f"Stud Y should be 40 (width), got {bbox.size.Y}"
        assert abs(bbox.min.Z) < tol, "Stud should start at Z=0 (on ground)"
        assert stud.category == "stud"

    def test_girt_orientation_along_y(self):
        """Girt should be horizontal with length along Y axis.
        
        Expected bbox: X=width(50), Y=length(3000), Z=height(150)
        Girt is rotated 90° around Z, so local X (length) becomes world Y.
        """
        girt = create_girt()
        bbox = girt.global_shape.bounding_box()
        
        tol = 0.01
        assert abs(bbox.size.Y - 3000) < tol, f"Girt Y should be 3000 (length), got {bbox.size.Y}"
        assert abs(bbox.size.X - 50) < tol, f"Girt X should be 50 (width), got {bbox.size.X}"
        assert abs(bbox.size.Z - 150) < tol, f"Girt Z should be 150 (height), got {bbox.size.Z}"
        assert girt.category == "girt"

    def test_purlin_orientation_along_y(self):
        """Purlin should be horizontal with length along Y axis.
        
        Expected bbox: X=width(50), Y=length(6000), Z=height(100)
        """
        purlin = create_purlin()
        bbox = purlin.global_shape.bounding_box()
        
        tol = 0.01
        assert abs(bbox.size.Y - 6000) < tol, f"Purlin Y should be 6000 (length), got {bbox.size.Y}"
        assert abs(bbox.size.X - 50) < tol, f"Purlin X should be 50 (width), got {bbox.size.X}"
        assert abs(bbox.size.Z - 100) < tol, f"Purlin Z should be 100 (height), got {bbox.size.Z}"
        assert purlin.category == "purlin"

    def test_plate_orientation_along_y(self):
        """Plate should be horizontal with length along Y axis.
        
        Expected bbox: X=width(90), Y=length(4000), Z=height(40)
        """
        plate = create_plate()
        bbox = plate.global_shape.bounding_box()
        
        tol = 0.01
        assert abs(bbox.size.Y - 4000) < tol, f"Plate Y should be 4000 (length), got {bbox.size.Y}"
        assert abs(bbox.size.X - 90) < tol, f"Plate X should be 90 (width), got {bbox.size.X}"
        assert abs(bbox.size.Z - 40) < tol, f"Plate Z should be 40 (height), got {bbox.size.Z}"
        assert plate.category == "plate"

    def test_rafter_pitched_orientation(self):
        """Rafter should be pitched at 30° angle.
        
        With 30° pitch rotating around Y axis, the rafter slopes upward.
        The timber's local height extends backward when pitched, so:
        - bbox.min.X will be negative (height * sin(pitch))
        - bbox.max.X will be length * cos(pitch)
        - bbox.max.Z will be length * sin(pitch) + height * cos(pitch)
        
        For length=3000, width=50, height=200, pitch=30°:
        - min.X ≈ -200 * sin(30°) = -100
        - max.X ≈ 3000 * cos(30°) ≈ 2598
        - max.Z ≈ 3000 * sin(30°) + 200 * cos(30°) ≈ 1500 + 173 ≈ 1673
        """
        import math
        rafter = create_rafter()
        bbox = rafter.global_shape.bounding_box()
        
        tol = 1  # tolerance for trigonometry
        length = 3000
        height = 200
        pitch_rad = math.radians(30)
        
        expected_max_x = length * math.cos(pitch_rad)  # ~2598
        expected_min_x = -height * math.sin(pitch_rad)  # ~-100
        expected_max_z = length * math.sin(pitch_rad) + height * math.cos(pitch_rad)  # ~1673
        
        assert abs(bbox.max.X - expected_max_x) < tol, f"Rafter max.X should be ~{expected_max_x:.0f}, got {bbox.max.X:.0f}"
        assert abs(bbox.min.X - expected_min_x) < tol, f"Rafter min.X should be ~{expected_min_x:.0f}, got {bbox.min.X:.0f}"
        assert abs(bbox.max.Z - expected_max_z) < tol, f"Rafter max.Z should be ~{expected_max_z:.0f}, got {bbox.max.Z:.0f}"
        assert abs(bbox.min.Z) < tol, "Rafter should start at Z=0"
        assert rafter.category == "rafter"


class TestTimberProperties:
    """Tests for computed properties (centerline, area, volume)."""

    def test_centerline_start_at_origin(self):
        """Algorithm: Centerline start must be at local origin (0,0,0)."""
        t = create_basic_timber()
        start, end = t.centerline
        assert start.X == 0
        assert start.Y == 0
        assert start.Z == 0

    def test_centerline_end_at_length(self):
        """Algorithm: Centerline end must be at (length, 0, 0)."""
        t = create_basic_timber()
        start, end = t.centerline
        assert end.X == 1000
        assert end.Y == 0
        assert end.Z == 0

    def test_cross_section_area_formula(self):
        """Algorithm: Area = width × height, verify formula exactly."""
        t = create_basic_timber()
        assert t.cross_section_area == 50 * 100  # 5000

    def test_volume_formula(self):
        """Algorithm: Volume = length × width × height, verify formula exactly."""
        t = create_basic_timber()
        assert t.volume == 1000 * 50 * 100  # 5,000,000


class TestTimberBlankGeometry:
    """Tests for blank shape geometry and coordinate system.
    
    CRITICAL INVARIANT: Timber blank must be:
    - X-aligned: origin at X=0, extends to X=length
    - Y-aligned: origin at Y=0, extends to Y=width  
    - Z-aligned: origin at Z=0, extends to Z=height
    
    This ensures consistent local coordinate system for all operations.
    """

    def test_blank_exists(self):
        """Algorithm: Blank property must return a Part object."""
        t = create_basic_timber()
        blank = t.blank
        assert blank is not None

    def test_blank_bounding_box_dimensions(self):
        """Algorithm: Query bbox, verify size matches input dimensions within tolerance."""
        t = create_basic_timber()
        bbox = t.blank.bounding_box()
        
        tol = 0.01
        assert abs(bbox.size.X - 1000) < tol, f"X size {bbox.size.X} != 1000"
        assert abs(bbox.size.Y - 50) < tol, f"Y size {bbox.size.Y} != 50"
        assert abs(bbox.size.Z - 100) < tol, f"Z size {bbox.size.Z} != 100"

    def test_blank_x_starts_at_zero(self):
        """Algorithm: Bbox min.X must equal 0 (blank origin at start)."""
        t = create_basic_timber()
        bbox = t.blank.bounding_box()
        
        tol = 0.01
        assert abs(bbox.min.X - 0) < tol, f"X min {bbox.min.X} != 0"

    def test_blank_x_ends_at_length(self):
        """Algorithm: Bbox max.X must equal length."""
        t = create_basic_timber()
        bbox = t.blank.bounding_box()
        
        tol = 0.01
        assert abs(bbox.max.X - 1000) < tol, f"X max {bbox.max.X} != 1000"

    def test_blank_y_starts_at_zero(self):
        """Algorithm: Bbox min.Y must equal 0 (corner origin)."""
        t = create_basic_timber()
        bbox = t.blank.bounding_box()
        
        tol = 0.01
        assert abs(bbox.min.Y - 0) < tol, f"Y min {bbox.min.Y} != 0"

    def test_blank_z_starts_at_zero(self):
        """Algorithm: Bbox min.Z must equal 0 (corner origin)."""
        t = create_basic_timber()
        bbox = t.blank.bounding_box()
        
        tol = 0.01
        assert abs(bbox.min.Z - 0) < tol, f"Z min {bbox.min.Z} != 0"

    def test_blank_y_extents(self):
        """Algorithm: Bbox Y extents must be 0 to width."""
        t = create_basic_timber()
        bbox = t.blank.bounding_box()
        
        tol = 0.01
        assert abs(bbox.min.Y - 0) < tol, f"Y min {bbox.min.Y} != 0"
        assert abs(bbox.max.Y - 50) < tol, f"Y max {bbox.max.Y} != 50"

    def test_blank_z_extents(self):
        """Algorithm: Bbox Z extents must be 0 to height."""
        t = create_basic_timber()
        bbox = t.blank.bounding_box()
        
        tol = 0.01
        assert abs(bbox.min.Z - 0) < tol, f"Z min {bbox.min.Z} != 0"
        assert abs(bbox.max.Z - 100) < tol, f"Z max {bbox.max.Z} != 100"


class TestTimberPositioning:
    """Tests for timber positioning via Location."""

    def test_default_location_at_origin(self):
        """Algorithm: Default location should be identity (origin, no rotation).
        
        Visual test 4: BBox should be X: 0-1000, Y: 0-50, Z: 0-100
        """
        t = create_timber_at_origin()
        pos = t.location.position
        rot = tuple(t.location.orientation)
        
        assert pos.X == 0
        assert pos.Y == 0
        assert pos.Z == 0
        assert rot == (0, 0, 0)
        
        # Verify world-space bounding box (visual test 4)
        bbox = t.global_shape.bounding_box()
        tol = 0.01
        assert abs(bbox.min.X - 0) < tol
        assert abs(bbox.max.X - 1000) < tol
        assert abs(bbox.min.Y - 0) < tol
        assert abs(bbox.max.Y - 50) < tol
        assert abs(bbox.min.Z - 0) < tol
        assert abs(bbox.max.Z - 100) < tol

    def test_create_with_position(self):
        """Algorithm: Location position should be stored exactly."""
        t = create_timber_translated()
        pos = t.location.position
        
        assert pos.X == 100
        assert pos.Y == 200
        assert pos.Z == 300

    def test_global_shape_translated(self):
        """Algorithm: global_shape bbox should be offset by location position.
        
        Visual test 5: BBox X: 100-1100, Y: 200-250, Z: 300-400
        """
        t = create_timber_translated()
        
        bbox = t.global_shape.bounding_box()
        tol = 0.01
        
        # X should be shifted by 100 (from 0-1000 to 100-1100)
        assert abs(bbox.min.X - 100) < tol
        assert abs(bbox.max.X - 1100) < tol
        
        # Y should be shifted by 200 (from 0-50 to 200-250)
        assert abs(bbox.min.Y - 200) < tol
        assert abs(bbox.max.Y - 250) < tol
        
        # Z should be shifted by 300 (from 0-100 to 300-400)
        assert abs(bbox.min.Z - 300) < tol
        assert abs(bbox.max.Z - 400) < tol


class TestTimberRotation:
    """Tests for timber rotation via Location.
    
    VALIDATION ALGORITHM for rotation:
    1. Create timber with known rotation
    2. Get global_shape bounding box
    3. Verify bbox dimensions changed appropriately
    4. For 90° rotations, verify dimension swaps
    5. For arbitrary angles, verify using rotation matrices
    """

    def test_rotation_z_90_swaps_xy(self):
        """Algorithm: 90° Z rotation should swap X and Y dimensions in bbox.
        
        Visual test 6: BBox size X=50, Y=1000, Z=100
        Local X (length=1000) becomes world Y
        Local Y (width=50) becomes world -X
        """
        t = create_timber_rotated_z90()
        bbox = t.global_shape.bounding_box()
        
        tol = 0.01
        # After 90° Z rotation: length is along Y, width is along X
        assert abs(bbox.size.Y - 1000) < tol, f"Y size {bbox.size.Y} should be 1000 (length)"
        assert abs(bbox.size.X - 50) < tol, f"X size {bbox.size.X} should be 50 (width)"
        assert abs(bbox.size.Z - 100) < tol, f"Z size {bbox.size.Z} should be 100 (height)"
        
        # Verify absolute position (corner at origin rotates to (-50, 0, 0))
        assert abs(bbox.min.X - (-50)) < tol, f"min.X {bbox.min.X} should be -50"
        assert abs(bbox.max.X - 0) < tol, f"max.X {bbox.max.X} should be 0"
        assert abs(bbox.min.Y - 0) < tol, f"min.Y {bbox.min.Y} should be 0"
        assert abs(bbox.max.Y - 1000) < tol, f"max.Y {bbox.max.Y} should be 1000"
        assert abs(bbox.min.Z - 0) < tol, f"min.Z {bbox.min.Z} should be 0"
        assert abs(bbox.max.Z - 100) < tol, f"max.Z {bbox.max.Z} should be 100"

    def test_rotation_x_90_swaps_yz(self):
        """Algorithm: 90° X rotation should swap Y and Z dimensions in bbox.
        
        Visual test 7: BBox size X=1000, Y=100, Z=50
        Local Y (width=50) becomes world Z
        Local Z (height=100) becomes world -Y
        """
        t = create_timber_rotated_x90()
        bbox = t.global_shape.bounding_box()
        
        tol = 0.01
        # After 90° X rotation: height is along Y, width is along Z
        assert abs(bbox.size.X - 1000) < tol, f"X size {bbox.size.X} should be 1000 (length)"
        assert abs(bbox.size.Z - 50) < tol, f"Z size {bbox.size.Z} should be 50 (width)"
        assert abs(bbox.size.Y - 100) < tol, f"Y size {bbox.size.Y} should be 100 (height)"
        
        # Verify absolute position (corner at origin rotates to (0, -100, 0))
        assert abs(bbox.min.X - 0) < tol, f"min.X {bbox.min.X} should be 0"
        assert abs(bbox.max.X - 1000) < tol, f"max.X {bbox.max.X} should be 1000"
        assert abs(bbox.min.Y - (-100)) < tol, f"min.Y {bbox.min.Y} should be -100"
        assert abs(bbox.max.Y - 0) < tol, f"max.Y {bbox.max.Y} should be 0"
        assert abs(bbox.min.Z - 0) < tol, f"min.Z {bbox.min.Z} should be 0"
        assert abs(bbox.max.Z - 50) < tol, f"max.Z {bbox.max.Z} should be 50"

    def test_rotation_y_90_swaps_xz(self):
        """Algorithm: 90° Y rotation should swap X and Z dimensions in bbox.
        
        Visual test 8: BBox size X=100, Y=50, Z=1000
        Local X (length=1000) becomes world -Z
        Local Z (height=100) becomes world X
        """
        t = create_timber_rotated_y90()
        bbox = t.global_shape.bounding_box()
        
        tol = 0.01
        # After 90° Y rotation: length is along Z, height is along X
        assert abs(bbox.size.Z - 1000) < tol, f"Z size {bbox.size.Z} should be 1000 (length)"
        assert abs(bbox.size.Y - 50) < tol, f"Y size {bbox.size.Y} should be 50 (width)"
        assert abs(bbox.size.X - 100) < tol, f"X size {bbox.size.X} should be 100 (height)"
        
        # Verify absolute position (corner at origin rotates to (0, 0, -1000))
        assert abs(bbox.min.X - 0) < tol, f"min.X {bbox.min.X} should be 0"
        assert abs(bbox.max.X - 100) < tol, f"max.X {bbox.max.X} should be 100"
        assert abs(bbox.min.Y - 0) < tol, f"min.Y {bbox.min.Y} should be 0"
        assert abs(bbox.max.Y - 50) < tol, f"max.Y {bbox.max.Y} should be 50"
        assert abs(bbox.min.Z - (-1000)) < tol, f"min.Z {bbox.min.Z} should be -1000"
        assert abs(bbox.max.Z - 0) < tol, f"max.Z {bbox.max.Z} should be 0"

    def test_rotation_preserves_volume(self):
        """Algorithm: Rotation must not change volume."""
        t_original = create_basic_timber()
        t_rotated = create_timber_rotated_arbitrary()
        
        vol_original = t_original.blank.volume
        vol_rotated = t_rotated.global_shape.volume
        
        tol = 1  # tolerance for floating point
        assert abs(vol_original - vol_rotated) < tol


class TestTimberRotationAndPosition:
    """Tests for combined rotation and translation."""

    def test_rotation_then_translation(self):
        """Algorithm: Position should be applied after rotation (not rotated).
        
        Visual test 10: Timber rotated 90° Z then translated to (100, 200, 0)
        After rotation: length along Y, width along X
        After translation: shifted by (100, 200, 0)
        """
        t = create_timber_rotated_and_translated()
        bbox = t.global_shape.bounding_box()
        
        tol = 0.01
        # After 90° Z rotation: length is along Y (size 1000), width along X (size 50)
        assert abs(bbox.size.Y - 1000) < tol
        assert abs(bbox.size.X - 50) < tol
        assert abs(bbox.size.Z - 100) < tol
        
        # Absolute position: rotated gives X: -50 to 0, Y: 0 to 1000
        # Then translated by (100, 200, 0): X: 50 to 100, Y: 200 to 1200
        assert abs(bbox.min.X - 50) < tol, f"min.X {bbox.min.X} should be 50"
        assert abs(bbox.max.X - 100) < tol, f"max.X {bbox.max.X} should be 100"
        assert abs(bbox.min.Y - 200) < tol, f"min.Y {bbox.min.Y} should be 200"
        assert abs(bbox.max.Y - 1200) < tol, f"max.Y {bbox.max.Y} should be 1200"
        assert abs(bbox.min.Z - 0) < tol, f"min.Z {bbox.min.Z} should be 0"
        assert abs(bbox.max.Z - 100) < tol, f"max.Z {bbox.max.Z} should be 100"


class TestTimberMoved:
    """Tests for the moved() method which returns a copy with new location."""

    def test_moved_returns_new_timber(self):
        """Algorithm: moved() should return a new Timber instance, not modify original."""
        t1 = create_basic_timber()
        t2 = t1.moved(Location((100, 0, 0)))
        
        assert t1 is not t2
        assert t1.location.position.X == 0
        assert t2.location.position.X == 100

    def test_moved_preserves_dimensions(self):
        """Algorithm: moved() should preserve all dimensions."""
        t1 = create_basic_timber()
        t2 = t1.moved(Location((100, 200, 300)))
        
        assert t2.length == 1000
        assert t2.width == 50
        assert t2.height == 100

    def test_moved_compounds_location(self):
        """Algorithm: moved() should compound locations (multiply transforms)."""
        t1 = Timber(length=1000, width=50, height=100, location=Location((100, 0, 0)))
        t2 = t1.moved(Location((50, 0, 0)))
        
        # Final position should be 150
        assert abs(t2.location.position.X - 150) < 0.01


class TestTimberFacePlanes:
    """Tests for face plane metadata.
    
    VALIDATION ALGORITHM:
    1. Get plane for each face
    2. Verify plane origin is at face center
    3. Verify plane normal points outward
    """

    def test_top_face_plane_position(self):
        """Algorithm: Top face plane should be at Z = height."""
        t = create_basic_timber()
        plane = t.get_face_plane("top")
        
        tol = 0.01
        assert abs(plane.origin.Z - 100) < tol  # height = 100

    def test_top_face_plane_normal(self):
        """Algorithm: Top face normal should point up (+Z)."""
        t = create_basic_timber()
        plane = t.get_face_plane("top")
        
        tol = 0.01
        assert abs(plane.z_dir.Z - 1) < tol

    def test_bottom_face_plane_position(self):
        """Algorithm: Bottom face plane should be at Z = 0."""
        t = create_basic_timber()
        plane = t.get_face_plane("bottom")
        
        tol = 0.01
        assert abs(plane.origin.Z - 0) < tol

    def test_bottom_face_plane_normal(self):
        """Algorithm: Bottom face normal should point down (-Z)."""
        t = create_basic_timber()
        plane = t.get_face_plane("bottom")
        
        tol = 0.01
        assert abs(plane.z_dir.Z - (-1)) < tol

    def test_left_face_plane_position(self):
        """Algorithm: Left face plane should be at Y = 0."""
        t = create_basic_timber()
        plane = t.get_face_plane("left")
        
        tol = 0.01
        assert abs(plane.origin.Y - 0) < tol

    def test_left_face_plane_normal(self):
        """Algorithm: Left face normal should point left (-Y)."""
        t = create_basic_timber()
        plane = t.get_face_plane("left")
        
        tol = 0.01
        assert abs(plane.z_dir.Y - (-1)) < tol

    def test_right_face_plane_position(self):
        """Algorithm: Right face plane should be at Y = width."""
        t = create_basic_timber()
        plane = t.get_face_plane("right")
        
        tol = 0.01
        assert abs(plane.origin.Y - 50) < tol  # width = 50

    def test_right_face_plane_normal(self):
        """Algorithm: Right face normal should point right (+Y)."""
        t = create_basic_timber()
        plane = t.get_face_plane("right")
        
        tol = 0.01
        assert abs(plane.z_dir.Y - 1) < tol

    def test_start_face_plane_position(self):
        """Algorithm: Start face plane should be at X = 0."""
        t = create_basic_timber()
        plane = t.get_face_plane("start")
        
        tol = 0.01
        assert abs(plane.origin.X - 0) < tol

    def test_start_face_plane_normal(self):
        """Algorithm: Start face normal should point backward (-X)."""
        t = create_basic_timber()
        plane = t.get_face_plane("start")
        
        tol = 0.01
        assert abs(plane.z_dir.X - (-1)) < tol

    def test_end_face_plane_position(self):
        """Algorithm: End face plane should be at X = length."""
        t = create_basic_timber()
        plane = t.get_face_plane("end")
        
        tol = 0.01
        assert abs(plane.origin.X - 1000) < tol

    def test_end_face_plane_normal(self):
        """Algorithm: End face normal should point forward (+X)."""
        t = create_basic_timber()
        plane = t.get_face_plane("end")
        
        tol = 0.01
        assert abs(plane.z_dir.X - 1) < tol

    def test_invalid_face_raises(self):
        """Algorithm: Unknown face name should raise ValueError."""
        t = create_basic_timber()
        with pytest.raises(ValueError, match="Unknown face"):
            t.get_face_plane("invalid")


class TestTimberFeatures:
    """Tests for feature (cut) management."""

    def test_add_feature_reduces_volume(self):
        """Algorithm: Adding a cut feature should reduce shape volume by exact amount.
        
        Visual test 11: Timber 1000×50×100 with 100×50×50 cut at corner.
        Box uses Align.MIN to place it at origin corner (matching timber alignment).
        Expected cut volume: 100×50×50 = 250,000 mm³
        """
        t = create_basic_timber()
        original_volume = t.shape.volume
        
        # Add cutting box at origin corner (Align.MIN matches timber alignment)
        cut = Box(100, 50, 50, align=(Align.MIN, Align.MIN, Align.MIN))
        t.add_feature(cut)
        
        new_volume = t.shape.volume
        cut_volume = original_volume - new_volume
        expected_cut_volume = 100 * 50 * 50  # 250,000
        
        assert new_volume < original_volume
        assert abs(cut_volume - expected_cut_volume) < 1, f"Cut volume {cut_volume} != expected {expected_cut_volume}"
        
        # Verify world-space: bounding box should change at start
        # Original: X 0-1000, after cut at start: X 100-1000 (if full width/height cut)
        # But this cut is only 50 high (half of 100), so bbox Z unchanged
        bbox = t.shape.bounding_box()
        tol = 0.01
        # X: cut removes 0-100, so min.X becomes 0 (partial cut, not full cross-section)
        # Actually since cut is 50×50 and timber is 50×100, the cut is full width but half height
        # So there's still material at X=0-100 in Z=50-100, bbox.min.X stays at 0
        assert abs(bbox.min.X - 0) < tol
        assert abs(bbox.max.X - 1000) < tol

    def test_clear_features_restores_volume(self):
        """Algorithm: Clearing features should restore original volume."""
        t = create_timber_with_cut()
        t.clear_features()
        
        original_volume = t.blank.volume
        assert abs(t.shape.volume - original_volume) < 1
