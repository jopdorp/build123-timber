"""Alignment utilities for positioning timber joints."""

import copy
import math
from dataclasses import dataclass, field
from typing import Optional, List, Type, TYPE_CHECKING
from build123d import Location, Axis, Part, Plane

if TYPE_CHECKING:
    from timber_joints.base_joint import BaseJoint


@dataclass
class JointParams:
    """Configuration for mortise-tenon joints (default: ShoulderedTenon)."""
    joint_class: Optional[Type["BaseJoint"]] = None
    tenon_length: float = 60.0
    tenon_width_ratio: float = 1/3      # Tenon width as fraction of beam width
    tenon_height_ratio: float = 2/3     # Tenon height as fraction of beam height
    shoulder_depth: float = 20.0
    housing_depth: float = 20.0
    post_top_extension: float = 300.0
    # Peg parameters
    include_pegs: bool = False          # Whether to include pegs in joints
    peg_diameter: float = 15.0          # Peg diameter (1.5cm default)
    peg_offset: float = 30.0            # Distance from shoulder to peg center
    
    def get_joint_class(self):
        if self.joint_class is None:
            from timber_joints.shouldered_tenon import ShoulderedTenon
            return ShoulderedTenon
        return self.joint_class
    
    def get_tenon_dimensions(self, beam_width: float, beam_height: Optional[float] = None) -> tuple[float, float]:
        """Calculate tenon width and height from beam dimensions."""
        if beam_height is None:
            beam_height = beam_width  # Assume square section if height not provided
        return beam_width * self.tenon_width_ratio, beam_height * self.tenon_height_ratio


@dataclass
class BraceParams:
    """Configuration for knee braces (default joint: BraceTenon)."""
    section: float = 100.0
    length: float = 707.0
    angle: float = 45.0
    tenon_length: float = 60.0
    post_joint_class: Optional[Type["BaseJoint"]] = None
    beam_joint_class: Optional[Type["BaseJoint"]] = None
    # Peg parameters
    include_pegs: bool = False          # Whether to include pegs in brace joints
    peg_diameter: float = 15.0          # Peg diameter (1.5cm default)
    peg_offset: float = 30.0            # Distance from shoulder to peg center
    
    def get_post_joint_class(self):
        if self.post_joint_class is None:
            from timber_joints.brace_tenon import BraceTenon
            return BraceTenon
        return self.post_joint_class
    
    def get_beam_joint_class(self):
        if self.beam_joint_class is None:
            from timber_joints.brace_tenon import BraceTenon
            return BraceTenon
        return self.beam_joint_class


@dataclass
class BentResult:
    """Result from creating a bent (portal frame)."""
    left_post: Part
    right_post: Part
    beam: Part
    brace_left: Optional[Part] = None
    brace_right: Optional[Part] = None
    pegs: List[Part] = field(default_factory=list)  # Pegs for tenon joints
    
    # Dimensions for reference
    post_section: float = 0.0
    beam_section: float = 0.0
    beam_length: float = 0.0


@dataclass
class GirtResult:
    """Result from adding girts to bents."""
    left_girt: Part
    right_girt: Part
    updated_bents: List["BentResult"]  # Bents with tenons cut for girt connection
    braces: List[tuple[str, Part]] = field(default_factory=list)


@dataclass
class RafterParams:
    """Configuration for roof rafters."""
    section: float = 100.0          # Rafter cross-section (square)
    pitch_angle: float = 30.0       # Roof pitch in degrees
    overhang: float = 200.0         # Eave overhang beyond girt
    tongue_width_ratio: float = 1/3  # Tongue width as fraction of section
    lap_depth_ratio: float = 0.5    # Lap joint depth as fraction of section
    # Peg parameters
    include_pegs: bool = False       # Whether to include pegs in lap joints
    peg_diameter: float = 15.0       # Peg diameter (1.5cm default)
    peg_offset: float = 30.0         # Distance from shoulder to peg center
    
    def get_tongue_width(self) -> float:
        """Get tongue width for peak joint."""
        return self.section * self.tongue_width_ratio
    
    def get_lap_depth(self) -> float:
        """Get lap joint depth for girt connection."""
        return self.section * self.lap_depth_ratio


@dataclass
class RafterPair:
    """A pair of rafters meeting at the ridge."""
    left_rafter: Part   # Rafter on left side (negative X)
    right_rafter: Part  # Rafter on right side (positive X)
    left_girt: Part     # Left girt with lap cut
    right_girt: Part    # Right girt with lap cut
    pegs: List[Part] = field(default_factory=list)  # Pegs for lap joints and peak joint
    peg_holes: List[Part] = field(default_factory=list)  # Peg holes for cutting girts


@dataclass
class RafterResult:
    """Result from adding rafters to a barn frame."""
    rafter_pairs: List[RafterPair]  # One pair per bent
    updated_left_girt: Part         # Left girt with all lap cuts
    updated_right_girt: Part        # Right girt with all lap cuts


@dataclass
class PositionedBrace:
    """A brace with its positioning and cut receiving members.
    
    Stores the brace Part along with the post and horizontal member
    that have had mortises cut for the brace tenons.
    """
    shape: Part
    post: Part  # Post with mortise cut
    horizontal_member: Part  # Beam/girt with mortise cut
    angle: float  # degrees from horizontal
    at_beam_end: bool  # True = right/end side, False = left/start side
    brace_section: float
    axis: Axis = Axis.X  # X for bent braces, Y for girt braces


def get_tenon_penetration(brace_tenon: "BraceTenon") -> float:
    """Get tenon penetration depth into the receiving member (perpendicular to surface)."""
    return brace_tenon.rotated_cut_bbox_width


def _calculate_brace_position_along_axis(
    post_bbox_min: float,
    post_bbox_max: float,
    rot_bbox_min: float,
    rot_bbox_max: float,
    penetration: float,
    at_member_start: bool,
    invert: bool = False,
) -> float:
    """Calculate brace position along horizontal axis. Y-axis uses inverted logic."""
    use_start_logic = at_member_start if not invert else not at_member_start
    
    if use_start_logic:
        post_inside = post_bbox_max
        return post_inside - rot_bbox_min - penetration
    else:
        post_inside = post_bbox_min
        return post_inside - rot_bbox_max + penetration


def _get_axis_values(bbox, axis: Axis) -> tuple[float, float]:
    """Get (min, max) values along the specified axis from a bounding box."""
    if axis == Axis.X:
        return bbox.min.X, bbox.max.X
    else:
        return bbox.min.Y, bbox.max.Y


def _get_perpendicular_axis(axis: Axis) -> Axis:
    """Get the perpendicular axis (X <-> Y)."""
    return Axis.Y if axis == Axis.X else Axis.X


def _calculate_brace_centering(
    post_center: float,
    rot_bbox_min: float,
    rot_bbox_max: float,
) -> float:
    """Calculate brace position to center it on the post."""
    rot_bbox_center = (rot_bbox_min + rot_bbox_max) / 2
    return post_center - rot_bbox_center


def _calculate_beam_position(
    beam: Part,
    post: Part,
    drop_depth: float,
    at_start: bool,
) -> tuple[float, float, float]:
    """Calculate where beam should be positioned relative to post at origin."""
    beam_bbox = beam.bounding_box()
    post_bbox = post.bounding_box()
    
    # Get actual dimensions from bounding boxes
    beam_length = beam_bbox.max.X - beam_bbox.min.X
    beam_width = beam_bbox.max.Y - beam_bbox.min.Y
    post_width = post_bbox.max.Y - post_bbox.min.Y
    
    if at_start:
        # Beam start at post - beam extends in +X direction from post's inner edge
        target_x = post_bbox.min.X
    else:
        # Beam end at post - beam's max.X should align with post's inner edge (max.X)
        # So beam's min.X = post's max.X - beam_length
        target_x = post_bbox.max.X - beam_length
    
    # Center beam on post width
    target_y = post_bbox.min.Y + (post_width - beam_width) / 2
    
    # Beam drops into post by drop_depth from post top
    target_z = post_bbox.max.Z - drop_depth
    
    return target_x, target_y, target_z


def _calculate_post_position(
    beam: Part,
    post: Part,
    drop_depth: float,
    at_start: bool,
) -> tuple[float, float, float]:
    """Calculate where post should be positioned relative to beam at origin.
    
    The post is positioned so the beam end goes INTO the post (overlapping).
    """
    beam_bbox = beam.bounding_box()
    post_bbox = post.bounding_box()
    
    # Get actual dimensions from bounding boxes
    beam_width = beam_bbox.max.Y - beam_bbox.min.Y
    post_x_extent = post_bbox.max.X - post_bbox.min.X  # Post's X dimension (depth/thickness)
    post_width = post_bbox.max.Y - post_bbox.min.Y
    post_z_extent = post_bbox.max.Z - post_bbox.min.Z  # Post's Z dimension (height when vertical)
    
    if at_start:
        # Post at beam start - beam's min.X should be INSIDE the post
        # Post's min.X should be at beam's min.X (beam start enters post from post's min.X side)
        target_x = beam_bbox.min.X
    else:
        # Post at beam end - beam's max.X should be INSIDE the post
        # Post's max.X should be at beam's max.X, so post's min.X = beam's max.X - post_x_extent
        target_x = beam_bbox.max.X - post_x_extent
    
    # Center post on beam width
    target_y = beam_bbox.min.Y + (beam_width - post_width) / 2
    
    # Post top (max.Z) should be at beam's min.Z + drop_depth
    # Post's min.Z = (beam.min.Z + drop_depth) - post_z_extent
    target_z = beam_bbox.min.Z + drop_depth - post_z_extent
    
    return target_x, target_y, target_z


def _move_shape_to_position(shape: Part, target_x: float, target_y: float, target_z: float) -> tuple[Part, Location]:
    """Move a shape so its bounding box min aligns with target coordinates."""
    bbox = shape.bounding_box()
    location = Location((
        target_x - bbox.min.X,
        target_y - bbox.min.Y,
        target_z - bbox.min.Z
    ))
    return shape.move(location), location


def align_beam_on_post(beam: Part, post: Part) -> tuple[Part, Location]:
    """Align a beam horizontally on top of a vertical post, with beam start at post edge."""
    beam_bbox = beam.bounding_box()
    post_bbox = post.bounding_box()
    
    # Get actual dimensions from bounding boxes
    beam_width = beam_bbox.max.Y - beam_bbox.min.Y
    post_width = post_bbox.max.Y - post_bbox.min.Y
    
    # Beam sits on top of post, starting at post edge
    beam_x = post_bbox.min.X
    beam_y = post_bbox.min.Y + (post_width - beam_width) / 2
    beam_z = post_bbox.max.Z
    
    return _move_shape_to_position(beam, beam_x, beam_y, beam_z)


def align_beam_in_post(
    beam: Part,
    post: Part,
    drop_depth: float,
    at_start: bool = True,
    move_post: bool = False,
) -> tuple[Part, Part, Location]:
    """Align a beam dropped INTO a post (for tongue-and-fork style joints)."""
    if move_post:
        # Keep beam at origin, move post to beam
        target_x, target_y, target_z = _calculate_post_position(beam, post, drop_depth, at_start)
        positioned_post, post_location = _move_shape_to_position(post, target_x, target_y, target_z)
        return beam, positioned_post, post_location
    else:
        # Keep post at origin, move beam to post
        target_x, target_y, target_z = _calculate_beam_position(beam, post, drop_depth, at_start)
        positioned_beam, beam_location = _move_shape_to_position(beam, target_x, target_y, target_z)
        return positioned_beam, post, beam_location


def make_post_vertical(post_shape: Part) -> Part:
    """Rotate a post to be vertical (length along Z axis instead of X)."""
    return post_shape.rotate(Axis.Y, -90)


def create_receiving_cut(
    positioned_insert: Part,
    receiving_shape: Part,
    margin: float = None,
) -> Part:
    """Subtract the insert from receiving shape to create a mortise/pocket.
    
    Positive margin makes the mortise larger than the tenon for clearance.
    If margin is None, uses the central config's cad_cut_margin.
    """
    if margin is None:
        from timber_joints.config import DEFAULT_CONFIG
        margin = DEFAULT_CONFIG.cad_cut_margin
    if margin > 0:
        from timber_joints.utils import expand_shape_by_margin
        insert_with_margin = expand_shape_by_margin(positioned_insert, margin)
        return receiving_shape - insert_with_margin
    return receiving_shape - positioned_insert


def position_for_blind_mortise(
    beam: Part,
    post: Part,
    tenon_length: float,
    housing_depth: float = 0,
    post_top_extension: float = 0,
    at_start: bool = True,
    move_post: bool = False,
) -> tuple[Part, Part]:
    """Offset beam or post to create a blind mortise (doesn't go through)."""
    post_bbox = post.bounding_box()
    
    # Calculate post's X extent (thickness)
    post_x_extent = post_bbox.max.X - post_bbox.min.X
    blind_offset = post_x_extent - housing_depth - tenon_length
    
    # Determine which direction to offset to create blind mortise
    if at_start:
        # Tenon at beam start - offset in -X direction (into post)
        x_offset = blind_offset
    else:
        # Tenon at beam end - offset in +X direction (into post)
        x_offset = -blind_offset
    
    if move_post:
        # Move post instead of beam (reverse both offsets)
        # Post moves in opposite direction to achieve same relative cut position
        post_for_cut = post.move(Location((-x_offset, 0, post_top_extension)))
        return beam, post_for_cut
    else:
        # Move beam (default)
        beam_for_cut = beam.move(Location((x_offset, 0, -post_top_extension)))
        return beam_for_cut, post


def calculate_brace_angle(horizontal_distance: float, vertical_distance: float) -> float:
    """Calculate brace angle from horizontal in degrees (0=horizontal, 90=vertical)."""
    return math.degrees(math.atan2(vertical_distance, horizontal_distance))


def calculate_brace_length(horizontal_distance: float, vertical_distance: float) -> float:
    """Calculate required brace length (diagonal distance)."""
    return math.sqrt(horizontal_distance**2 + vertical_distance**2)


def _create_brace(
    post: Part,
    horizontal_member: Part,
    brace_section: float,
    at_member_start: bool,
    axis: Axis,
    tenon_width: float = None,
    tenon_length: float = 60.0,
    angle: float = 45.0,
    brace_length: float = 707.0,
) -> PositionedBrace:
    """Create and position a brace between a post and horizontal member.
    
    Handles both bent braces (X axis) and girt braces (Y axis). The brace penetrates
    into the horizontal member until the lower corner touches the member bottom surface.
    """
    from timber_joints.beam import Beam
    from timber_joints.brace_tenon import BraceTenon
    
    post_bbox = post.bounding_box()
    member_bbox = horizontal_member.bounding_box()
    
    # Set up tenon dimensions
    if tenon_width is None:
        tenon_width = brace_section / 3
    
    # === UNIFIED APPROACH ===
    # Create brace with tenons: positions depend on which end connects to what
    # - at_member_start=True: post at start of brace, member at end
    # - at_member_start=False: member at start of brace, post at end
    
    # Create brace WITHOUT cuts first (for positioning reference)
    brace_no_cuts = Beam(length=brace_length, width=brace_section, height=brace_section).shape
    
    # Also create brace WITH cuts
    brace_for_cuts = Beam(length=brace_length, width=brace_section, height=brace_section).shape
    
    # Determine tenon positions based on brace orientation
    post_tenon_at_start = at_member_start
    member_tenon_at_start = not at_member_start
    
    # For mirrored braces (at_member_start=False), use complementary angle for tenon cuts
    # This ensures both braces have matching shoulder geometry at their respective ends
    tenon_angle = angle if at_member_start else 90.0 - angle

    if at_member_start:
        # adjust tenon length to account for shoulder depth based on angle
        tenon_length_adjusted_post = tenon_length / math.cos(math.radians(tenon_angle))
        tenon_length_adjusted_member = tenon_length / math.cos(math.radians(90 - tenon_angle))
    else:
        # adjust tenon length to account for shoulder depth based on angle
        tenon_length_adjusted_post = tenon_length / math.sin(math.radians(tenon_angle))
        tenon_length_adjusted_member = tenon_length / math.sin(math.radians(90 - tenon_angle))

    # Cut post tenon
    brace_with_post_tenon = BraceTenon(
        brace=brace_for_cuts,
        tenon_width=tenon_width,
        tenon_length=tenon_length_adjusted_post,
        brace_angle=tenon_angle,
        at_start=post_tenon_at_start,
    )
    
    # Cut member tenon
    brace_with_both_tenons = BraceTenon(
        brace=brace_with_post_tenon.shape,
        tenon_width=tenon_width,
        tenon_length=tenon_length_adjusted_member,
        brace_angle=tenon_angle,
        at_start=member_tenon_at_start,
    )
    brace_with_cuts = brace_with_both_tenons.shape
    
    # Penetration depths use the same utility function for both directions
    horizontal_penetration = get_tenon_penetration(brace_with_post_tenon)
    vertical_penetration = get_tenon_penetration(brace_with_both_tenons)
    
    # Determine rotation axis for tilting (perpendicular to brace direction)
    tilt_axis = Axis.Y if axis == Axis.X else Axis.X
    
    # For Y-axis braces, first rotate 90° around Z to align with Y axis
    if axis == Axis.Y:
        brace_no_cuts = brace_no_cuts.rotate(Axis.Z, 90)
        brace_with_cuts = brace_with_cuts.rotate(Axis.Z, 90)
    
    # Angle sign: +angle tilts up-right (for at_member_start=False)
    #            -angle tilts up-left (for at_member_start=True)
    angle_sign = -1 if at_member_start else 1
    rotated_brace_no_cuts = brace_no_cuts.rotate(tilt_axis, angle_sign * angle)
    rotated_brace_with_cuts = brace_with_cuts.rotate(tilt_axis, angle_sign * angle)
    
    # Use brace WITHOUT cuts for positioning (consistent bbox)
    rot_bbox = rotated_brace_no_cuts.bounding_box()

    # Target Z: brace top aligns with member bottom + penetration
    target_top_z = member_bbox.min.Z + vertical_penetration
    target_z = target_top_z - rot_bbox.max.Z
    
    # Position along the brace axis - same logic for X and Y
    # Get coordinates along the brace axis and perpendicular to it
    perp_axis = _get_perpendicular_axis(axis)
    post_bbox_along = _get_axis_values(post_bbox, axis)
    rot_bbox_along = _get_axis_values(rot_bbox, axis)
    post_center_perp = (post_bbox.min.Y + post_bbox.max.Y) / 2 if axis == Axis.X else (post_bbox.min.X + post_bbox.max.X) / 2
    rot_bbox_perp = _get_axis_values(rot_bbox, perp_axis)
    
    # Y-axis uses inverted logic
    invert = axis == Axis.Y
    
    target_along = _calculate_brace_position_along_axis(
        post_bbox_along[0], post_bbox_along[1],
        rot_bbox_along[0], rot_bbox_along[1],
        horizontal_penetration, at_member_start, invert
    )
    target_perp = _calculate_brace_centering(post_center_perp, rot_bbox_perp[0], rot_bbox_perp[1])
    
    # Assign to X/Y based on axis
    target_x = target_along if axis == Axis.X else target_perp
    target_y = target_perp if axis == Axis.X else target_along
    
    # Position the cut brace using the calculated targets
    positioned_brace = rotated_brace_with_cuts.move(Location((target_x, target_y, target_z)))
    
    # Cut mortises in receiving members
    post_with_mortise = create_receiving_cut(positioned_brace, post)
    member_with_mortise = create_receiving_cut(positioned_brace, horizontal_member)
    
    return PositionedBrace(
        shape=positioned_brace,
        post=post_with_mortise,
        horizontal_member=member_with_mortise,
        angle=angle,
        at_beam_end=not at_member_start,
        brace_section=brace_section,
        axis=axis,
    )


def create_brace_for_bent(
    post: Part,
    beam: Part,
    brace_section: float,
    brace_length: float,
    at_beam_start: bool = True,
    tenon_width: float = None,
    tenon_height: float = None,
    tenon_length: float = 60.0,
    angle: float = 45.0,
) -> PositionedBrace:
    """Create and position a brace between a post and beam in a bent.
    
    Brace penetrates into beam until lower corner touches beam bottom surface.
    """
    return _create_brace(
        post=post,
        horizontal_member=beam,
        brace_section=brace_section,
        brace_length=brace_length,
        at_member_start=at_beam_start,
        axis=Axis.X,
        tenon_width=tenon_width,
        tenon_length=tenon_length,
        angle=angle,
    )


def create_brace_for_girt(
    post: Part,
    girt: Part,
    brace_section: float,
    brace_length: float,
    at_girt_start: bool = True,
    tenon_width: float = None,
    tenon_height: float = None,
    tenon_length: float = 60.0,
    angle: float = 45.0,
) -> PositionedBrace:
    """Create and position a brace between a post and girt (Y axis).
    
    Similar to create_brace_for_bent but for girts running along Y axis.
    """
    return _create_brace(
        post=post,
        horizontal_member=girt,
        brace_section=brace_section,
        brace_length=brace_length,
        at_member_start=at_girt_start,
        axis=Axis.Y,
        tenon_width=tenon_width,
        tenon_length=tenon_length,
        angle=angle,
    )


def create_tenon_peg_for_mortise(
    beam_bbox,
    post_bbox,
    tenon_width: float,
    tenon_height: float,
    tenon_length: float,
    peg_offset: float,
    peg_diameter: float,
    at_start: bool = True,
) -> Part:
    """Create a peg for a beam-to-post tenon joint.
    
    The peg goes through the post (Y direction) perpendicular to the tenon,
    positioned peg_offset distance from the shoulder into the tenon.
    
    Args:
        beam_bbox: Bounding box of the positioned beam
        post_bbox: Bounding box of the post (vertical)
        tenon_width: Width of the tenon
        tenon_height: Height of the tenon
        tenon_length: Length of the tenon penetrating into post
        peg_offset: Distance from shoulder to peg center
        peg_diameter: Diameter of the peg
        at_start: True if joint is at beam start, False for beam end
    
    Returns:
        Cylindrical peg positioned to pass through tenon
    """
    from timber_joints.utils import create_peg
    
    # Peg length is full post width (Y direction)
    peg_length = post_bbox.max.Y - post_bbox.min.Y
    
    # Create peg along Y axis
    peg = create_peg(length=peg_length, diameter=peg_diameter, axis=Axis.Y)
    
    # Calculate peg position
    # Z position: center of tenon height in the beam
    beam_center_z = (beam_bbox.min.Z + beam_bbox.max.Z) / 2
    
    # X position: offset from shoulder into the tenon (inside the post)
    if at_start:
        # Tenon at beam start - peg is at beam start + offset
        peg_x = beam_bbox.min.X + peg_offset
    else:
        # Tenon at beam end - peg is at beam end - offset
        peg_x = beam_bbox.max.X - peg_offset
    
    # Y position: start at post's Y min
    peg_y = post_bbox.min.Y
    
    # Move peg to position
    peg = peg.move(Location((peg_x, peg_y, beam_center_z)))
    
    return peg


def create_lap_peg_for_rafter(
    rafter_bbox,
    girt_bbox,
    peg_diameter: float,
    lap_depth: float,
    peg_offset: float = 30.0,
    pitch_angle: float = 0.0,
) -> Part:
    """Create a peg for a rafter-to-girt lap joint.
    
    The peg goes perpendicular to the rafter (tilted with pitch angle),
    positioned offset from the inner edge of the girt into the lap.
    
    Args:
        rafter_bbox: Bounding box of the rafter
        girt_bbox: Bounding box of the girt
        peg_diameter: Diameter of the peg
        lap_depth: Depth of the lap cut (how deep into the rafter)
        peg_offset: Distance from girt inner edge to peg center
        pitch_angle: Roof pitch angle in degrees (for rotating the peg)
    
    Returns:
        Cylindrical peg positioned to pass through lap joint
    """
    import math
    from timber_joints.utils import create_peg
    
    # Peg length goes through lap depth plus into girt (total = lap_depth + some girt penetration)
    # Use lap_depth * 2 to go through rafter lap and into girt
    peg_length = lap_depth * 2
    
    # Create peg along Z axis initially
    peg = create_peg(length=peg_length, diameter=peg_diameter, axis=Axis.Z)
    
    # Y position: center of rafter in Y
    peg_y = (rafter_bbox.min.Y + rafter_bbox.max.Y) / 2
    
    # X position: offset from girt inner edge into the lap
    # Left rafter (negative X side): girt inner edge is max.X, peg goes toward -X
    # Right rafter (positive X side): girt inner edge is min.X, peg goes toward +X
    rafter_center_x = (rafter_bbox.min.X + rafter_bbox.max.X) / 2
    girt_center_x = (girt_bbox.min.X + girt_bbox.max.X) / 2
    
    is_left_rafter = rafter_center_x < girt_center_x
    
    # Calculate angle offset for tilted peg
    angle_rad = math.radians(pitch_angle)
    
    if is_left_rafter:
        # Left rafter - peg offset from girt's max.X toward -X
        # Also offset X for the tilted peg (peg tilts outward, bottom moves toward center)
        x_tilt_offset = (peg_length / 2) * math.sin(angle_rad)
        peg_x = girt_bbox.max.X - peg_offset + x_tilt_offset
        # Rotate peg to be perpendicular to left rafter (tilted outward)
        peg = peg.rotate(Axis.Y, pitch_angle)
    else:
        # Right rafter - peg offset from girt's min.X toward +X
        # Also offset X for the tilted peg (peg tilts outward, bottom moves toward center)
        x_tilt_offset = (peg_length / 2) * math.sin(angle_rad)
        peg_x = girt_bbox.min.X + peg_offset - x_tilt_offset
        # Rotate peg to be perpendicular to right rafter (tilted outward)
        peg = peg.rotate(Axis.Y, -pitch_angle)
    
    # Z position: lower the peg so it penetrates through the tilted rafter into the girt
    # The tilted rafter section requires section/cos(angle) of vertical travel to pass through
    # The peg needs to be lowered to account for the tilted rafter thickness
    z_offset = lap_depth / math.cos(angle_rad) - lap_depth
    peg_z = girt_bbox.max.Z - lap_depth - z_offset
    
    # Move peg to position
    peg = peg.move(Location((peg_x, peg_y, peg_z)))
    
    return peg


def create_peak_peg_for_rafter(
    left_rafter_bbox,
    right_rafter_bbox,
    peg_diameter: float,
    peg_offset: float,
    pitch_angle: float,
    rafter_section: float,
) -> Part:
    """Create a peg for the tongue-and-fork joint at the rafter peak.
    
    The peg goes through the Y direction (side of both rafters) at the peak,
    passing through the tongue (left rafter) and fork (right rafter).
    
    Args:
        left_rafter_bbox: Bounding box of the positioned left rafter
        right_rafter_bbox: Bounding box of the positioned right rafter
        peg_diameter: Diameter of the peg
        peg_offset: Distance from the shoulder along the tongue
        pitch_angle: Roof pitch angle in degrees
        rafter_section: Rafter cross-section size
    
    Returns:
        Cylindrical peg positioned at the peak joint
    """
    import math
    from timber_joints.utils import create_peg
    
    # Peg goes through Y direction
    peg_length = max(
        right_rafter_bbox.max.Y - right_rafter_bbox.min.Y,
        left_rafter_bbox.max.Y - left_rafter_bbox.min.Y,
    )
    peg = create_peg(length=peg_length, diameter=peg_diameter, axis=Axis.Y)
    
    # Peak is where the two rafters meet - use the overlap region
    # The peak X is approximately at the center where both rafters overlap
    peak_x = (left_rafter_bbox.max.X + right_rafter_bbox.min.X) / 2
    
    # The peak Z is at the top of the rafters
    peak_z = max(left_rafter_bbox.max.Z, right_rafter_bbox.max.Z)
    
    # The tongue goes from the left rafter into the right rafter
    # Peg should be offset from the shoulder (where tongue meets left rafter body)
    # and centered in the tenon cross-section
    angle_rad = math.radians(pitch_angle)
    
    # The tongue center line is at rafter_section/2 from the top surface
    # perpendicular to the rafter direction
    # First find the center of the tenon (offset perpendicular to rafter)
    center_offset = rafter_section / 2
    
    # Tongue direction is along the left rafter (going toward +X and -Z from peak)
    # Start from peak, offset perpendicular to get to center, then offset along tongue
    peg_x = peak_x - peg_offset * math.cos(angle_rad) + center_offset * math.sin(angle_rad)
    peg_z = peak_z - center_offset * math.cos(angle_rad) - peg_offset * math.sin(angle_rad)
    
    # Y position at rafter front
    peg_y = min(left_rafter_bbox.min.Y, right_rafter_bbox.min.Y)
    
    peg = peg.move(Location((peg_x, peg_y, peg_z)))
    
    return peg


def create_brace_peg(
    brace_bbox,
    receiving_member_bbox,
    peg_diameter: float,
    brace_angle: float,
    brace_section: float,
    tenon_length: float,
    is_post_connection: bool,
    is_left_brace: bool = True,
) -> Part:
    """Create a peg for a brace tenon joint.
    
    The peg goes through the receiving member (Y direction) perpendicular to the brace,
    centered in the tenon (at tenon_length/2 from the shoulder).
    
    Args:
        brace_bbox: Bounding box of the positioned brace
        receiving_member_bbox: Bounding box of the post or beam
        peg_diameter: Diameter of the peg
        brace_angle: Angle of the brace in degrees
        brace_section: Cross-section size of the brace
        tenon_length: Length of the tenon (peg will be at center)
        is_post_connection: True for post (lower) connection, False for beam (upper)
        is_left_brace: True for left brace (goes up-right), False for right brace (goes up-left)
    
    Returns:
        Cylindrical peg positioned to pass through brace tenon
    """
    import math
    from timber_joints.utils import create_peg
    
    # Peg goes through Y direction (side of receiving member)
    peg_length = receiving_member_bbox.max.Y - receiving_member_bbox.min.Y
    peg = create_peg(length=peg_length, diameter=peg_diameter, axis=Axis.Y)
    
    angle_rad = math.radians(brace_angle)
    
    # The brace centerline runs through the middle of the brace body.
    # For a left brace at angle θ going up-right:
    #   - At the post end, the brace is at its lowest Z
    #   - The centerline Z at the post face = brace_bottom_at_post + (section/2)/cos(θ)
    #   - But the brace bottom at the post varies with X along the brace
    #
    # Key insight: The brace bounding box min/max give us the extremes.
    # For the post connection, the brace center in Z at the receiving member face can be 
    # found using the centerline: brace runs at angle θ, so the center follows this slope.
    #
    # For POST connection (horizontal tenon):
    #   - Peg X = inside post - tenon_length/2
    #   - Peg Z = center of brace at that X position
    #
    # The center of the brace bbox gives us the center of the whole brace.
    # From there, we can calculate the center at a specific X.
    
    brace_center_x = (brace_bbox.min.X + brace_bbox.max.X) / 2
    brace_center_z = (brace_bbox.min.Z + brace_bbox.max.Z) / 2
    
    if is_post_connection:
        # Tenon goes horizontally into post
        if is_left_brace:
            peg_x = receiving_member_bbox.max.X - tenon_length / 2
            # Brace centerline has slope tan(angle), going up to the right
            # At peg_x, Z offset from center = (peg_x - brace_center_x) * tan(angle)
            peg_z = brace_center_z + (peg_x - brace_center_x) * math.tan(angle_rad)
        else:
            peg_x = receiving_member_bbox.min.X + tenon_length / 2
            # Right brace goes up to the left, so negative slope
            peg_z = brace_center_z - (peg_x - brace_center_x) * math.tan(angle_rad)
    else:
        # Tenon goes vertically into beam (from below)
        peg_z = receiving_member_bbox.min.Z + tenon_length / 2
        
        if is_left_brace:
            # Find X at the beam level using brace centerline
            # At peg_z, X offset from center = (peg_z - brace_center_z) / tan(angle)
            peg_x = brace_center_x + (peg_z - brace_center_z) / math.tan(angle_rad)
        else:
            # Right brace: at higher Z, X is lower (going left)
            peg_x = brace_center_x - (peg_z - brace_center_z) / math.tan(angle_rad)
    
    peg_y = receiving_member_bbox.min.Y
    
    peg = peg.move(Location((peg_x, peg_y, peg_z)))
    return peg


def  build_complete_bent(
    post_height: float = 3000,
    post_section: float = 150,
    beam_length: float = 5000,
    beam_section: float = None,
    joint_params: JointParams = None,
    brace_params: BraceParams = None,
) -> BentResult:
    """Build a bent (two posts + beam) with optional braces."""
    from timber_joints.beam import Beam
    
    if joint_params is None:
        joint_params = JointParams()
    
    beam_section = beam_section or post_section
    
    # Get the joint class for post/beam connection
    JointClass = joint_params.get_joint_class()
    
    # Create posts and beam
    post_left = Beam(length=post_height, width=post_section, height=post_section)
    post_right = Beam(length=post_height, width=post_section, height=post_section)
    beam = Beam(length=beam_length, width=beam_section, height=beam_section)
    
    # Tenon dimensions from joint params
    tenon_width, tenon_height = joint_params.get_tenon_dimensions(beam.width, beam.height)
    drop_depth = beam.height
    
    # Create beam with tenons on BOTH ends using the configured joint class
    beam_with_start = JointClass(
        beam=beam,
        tenon_width=tenon_width,
        tenon_height=tenon_height,
        tenon_length=joint_params.tenon_length,
        shoulder_depth=joint_params.shoulder_depth,
        at_start=True,
    ).shape

    beam_with_both_tenons = JointClass(
        beam=beam_with_start,
        tenon_width=tenon_width,
        tenon_height=tenon_height,
        tenon_length=joint_params.tenon_length,
        shoulder_depth=joint_params.shoulder_depth,
        at_start=False,
    ).shape
    
    # Make posts vertical
    vertical_post_left = make_post_vertical(post_left.shape)
    vertical_post_right = make_post_vertical(post_right.shape)
    
    # Step 1: Align beam to LEFT post (beam start at post)
    positioned_beam, _, _ = align_beam_in_post(
        beam=beam_with_both_tenons,
        post=vertical_post_left,
        drop_depth=drop_depth,
        at_start=True,
        move_post=False,
    )
    
    # Step 2: Create mortise in left post
    beam_for_left_cut, _ = position_for_blind_mortise(
        beam=positioned_beam,
        post=vertical_post_left,
        tenon_length=joint_params.tenon_length,
        housing_depth=joint_params.housing_depth,
        post_top_extension=joint_params.post_top_extension,
        at_start=True,
    )
    left_post_with_mortise = create_receiving_cut(beam_for_left_cut, vertical_post_left)
    
    # Step 3: Align right post to beam end (move post to beam)
    _, positioned_post_right, _ = align_beam_in_post(
        beam=positioned_beam,
        post=vertical_post_right,
        drop_depth=drop_depth,
        at_start=False,
        move_post=True,
    )
    
    # Step 4: Create mortise in right post
    _, positioned_post_right_cut = position_for_blind_mortise(
        beam=positioned_beam,
        post=positioned_post_right,
        tenon_length=joint_params.tenon_length,
        housing_depth=joint_params.housing_depth,
        post_top_extension=joint_params.post_top_extension,
        at_start=False,
        move_post=True,
    )
    right_post_with_mortise = create_receiving_cut(positioned_beam, positioned_post_right_cut)
    
    left_post = left_post_with_mortise
    right_post = right_post_with_mortise
    beam = positioned_beam
    
    # Create pegs for beam-to-post joints if requested
    pegs = []
    if joint_params.include_pegs:
        # Left post peg (beam start)
        left_peg = create_tenon_peg_for_mortise(
            beam_bbox=beam_for_left_cut.bounding_box(),
            post_bbox=vertical_post_left.bounding_box(),
            tenon_width=tenon_width,
            tenon_height=tenon_height,
            tenon_length=joint_params.tenon_length,
            peg_offset=joint_params.peg_offset,
            peg_diameter=joint_params.peg_diameter,
            at_start=True,
        )
        pegs.append(left_peg)
        # Cut peg hole from left post and beam
        left_post = left_post - left_peg
        beam = beam - left_peg
        
        # Right post peg (beam end)
        right_peg = create_tenon_peg_for_mortise(
            beam_bbox=positioned_beam.bounding_box(),
            post_bbox=positioned_post_right_cut.bounding_box(),
            tenon_width=tenon_width,
            tenon_height=tenon_height,
            tenon_length=joint_params.tenon_length,
            peg_offset=joint_params.peg_offset,
            peg_diameter=joint_params.peg_diameter,
            at_start=False,
        )
        pegs.append(right_peg)
        # Cut peg hole from right post and beam
        right_post = right_post - right_peg
        beam = beam - right_peg
    
    # Add braces if requested
    brace_left = None
    brace_right = None
    if brace_params is not None:
        left_brace_result = create_brace_for_bent(
            post=left_post, beam=beam,
            brace_section=brace_params.section,
            brace_length=brace_params.length,
            angle=brace_params.angle,
            tenon_length=brace_params.tenon_length,
            at_beam_start=True,
        )
        brace_left = left_brace_result.shape
        left_post = left_brace_result.post
        beam = left_brace_result.horizontal_member
        
        right_brace_result = create_brace_for_bent(
            post=right_post, beam=beam,
            brace_section=brace_params.section,
            brace_length=brace_params.length,
            angle=brace_params.angle,
            tenon_length=brace_params.tenon_length,
            at_beam_start=False,
        )
        brace_right = right_brace_result.shape
        right_post = right_brace_result.post
        beam = right_brace_result.horizontal_member
        
        # Create brace pegs if requested
        if brace_params.include_pegs:
            # Left brace pegs (2 pegs: post connection and beam connection)
            left_brace_bbox = brace_left.bounding_box()
            left_post_bbox = left_post.bounding_box()
            beam_bbox = beam.bounding_box()
            
            # Peg for left brace to post connection
            left_brace_post_peg = create_brace_peg(
                brace_bbox=left_brace_bbox,
                receiving_member_bbox=left_post_bbox,
                peg_diameter=brace_params.peg_diameter,
                brace_angle=brace_params.angle,
                brace_section=brace_params.section,
                tenon_length=brace_params.tenon_length,
                is_post_connection=True,
                is_left_brace=True,
            )
            pegs.append(left_brace_post_peg)
            # Cut peg hole from left post and left brace
            left_post = left_post - left_brace_post_peg
            brace_left = brace_left - left_brace_post_peg
            
            # Peg for left brace to beam connection
            left_brace_beam_peg = create_brace_peg(
                brace_bbox=left_brace_bbox,
                receiving_member_bbox=beam_bbox,
                peg_diameter=brace_params.peg_diameter,
                brace_angle=brace_params.angle,
                brace_section=brace_params.section,
                tenon_length=brace_params.tenon_length,
                is_post_connection=False,
                is_left_brace=True,
            )
            pegs.append(left_brace_beam_peg)
            # Cut peg hole from beam and left brace
            beam = beam - left_brace_beam_peg
            brace_left = brace_left - left_brace_beam_peg
            
            # Right brace pegs (2 pegs: post connection and beam connection)
            right_brace_bbox = brace_right.bounding_box()
            right_post_bbox = right_post.bounding_box()
            
            # Peg for right brace to post connection
            right_brace_post_peg = create_brace_peg(
                brace_bbox=right_brace_bbox,
                receiving_member_bbox=right_post_bbox,
                peg_diameter=brace_params.peg_diameter,
                brace_angle=brace_params.angle,
                brace_section=brace_params.section,
                tenon_length=brace_params.tenon_length,
                is_post_connection=True,
                is_left_brace=False,
            )
            pegs.append(right_brace_post_peg)
            # Cut peg hole from right post and right brace
            right_post = right_post - right_brace_post_peg
            brace_right = brace_right - right_brace_post_peg
            
            # Peg for right brace to beam connection
            right_brace_beam_peg = create_brace_peg(
                brace_bbox=right_brace_bbox,
                receiving_member_bbox=beam_bbox,
                peg_diameter=brace_params.peg_diameter,
                brace_angle=brace_params.angle,
                brace_section=brace_params.section,
                tenon_length=brace_params.tenon_length,
                is_post_connection=False,
                is_left_brace=False,
            )
            pegs.append(right_brace_beam_peg)
            # Cut peg hole from beam and right brace
            beam = beam - right_brace_beam_peg
            brace_right = brace_right - right_brace_beam_peg
    
    return BentResult(
        left_post=left_post,
        right_post=right_post,
        beam=beam,
        brace_left=brace_left,
        brace_right=brace_right,
        pegs=pegs,
        post_section=post_section,
        beam_section=beam_section,
        beam_length=beam_length,
    )


def add_girts_to_bents(
    bents: List[BentResult],
    y_positions: List[float],
    girt_section: float = None,
    joint_params: JointParams = None,
    brace_params: BraceParams = None,
) -> GirtResult:
    """Connect bents with longitudinal girts and optional braces."""
    from timber_joints.beam import Beam
    from timber_joints.tenon import Tenon
    from timber_joints.utils import create_vertical_cut
    
    if len(bents) != len(y_positions):
        raise ValueError("Number of bents must match number of y_positions")
    
    if joint_params is None:
        joint_params = JointParams()
    
    # Use first bent's dimensions as reference
    first_bent = bents[0]
    if girt_section is None:
        girt_section = first_bent.post_section
    
    # Add tenons to post tops for girt connection
    post_section = first_bent.post_section
    tenon_width, tenon_height = joint_params.get_tenon_dimensions(post_section, post_section)
    
    updated_bents = []
    for bent in bents:
        left_post = create_vertical_cut(
            bent.left_post, Tenon, at_top=True,
            tenon_width=tenon_width, tenon_height=tenon_height,
            tenon_length=joint_params.tenon_length,
        )
        right_post = create_vertical_cut(
            bent.right_post, Tenon, at_top=True,
            tenon_width=tenon_width, tenon_height=tenon_height,
            tenon_length=joint_params.tenon_length,
        )
        updated_bents.append(BentResult(
            left_post=left_post,
            right_post=right_post,
            beam=bent.beam,
            brace_left=bent.brace_left,
            brace_right=bent.brace_right,
            post_section=bent.post_section,
            beam_section=bent.beam_section,
            beam_length=bent.beam_length,
        ))
    bents = updated_bents
    
    # Calculate girt length from bent positions
    y_min = min(y_positions)
    y_max = max(y_positions)
    girt_length = (y_max - y_min) + first_bent.post_section
    
    # Get post positions from first bent (moved to y=0 reference)
    left_bbox = first_bent.left_post.bounding_box()
    right_bbox = first_bent.right_post.bounding_box()
    left_post_x = (left_bbox.min.X + left_bbox.max.X) / 2
    right_post_x = (right_bbox.min.X + right_bbox.max.X) / 2
    
    # Z position for girts (at top of posts, accounting for tenon/housing)
    girt_z = left_bbox.max.Z - joint_params.tenon_length - joint_params.housing_depth
    
    # Create and position left girt
    left_girt_beam = Beam(length=girt_length, width=girt_section, height=girt_section)
    left_girt = left_girt_beam.shape.rotate(Axis.Z, 90)
    left_girt_bbox = left_girt.bounding_box()
    left_girt = left_girt.move(Location((
        left_post_x - (left_girt_bbox.min.X + left_girt_bbox.max.X) / 2,
        y_min - left_girt_bbox.min.Y,
        girt_z - left_girt_bbox.min.Z,
    )))
    
    # Create and position right girt
    right_girt_beam = Beam(length=girt_length, width=girt_section, height=girt_section)
    right_girt = right_girt_beam.shape.rotate(Axis.Z, 90)
    right_girt_bbox = right_girt.bounding_box()
    right_girt = right_girt.move(Location((
        right_post_x - (right_girt_bbox.min.X + right_girt_bbox.max.X) / 2,
        y_min - right_girt_bbox.min.Y,
        girt_z - right_girt_bbox.min.Z,
    )))
    
    # Cut mortises in girts for each bent's posts
    for bent, y_pos in zip(bents, y_positions):
        # Move bent posts to their Y position for the cut (deepcopy to avoid mutating original)
        left_post_at_y = copy.deepcopy(bent.left_post).move(Location((0, y_pos, 0)))
        right_post_at_y = copy.deepcopy(bent.right_post).move(Location((0, y_pos, 0)))
        left_girt = create_receiving_cut(left_post_at_y, left_girt)
        right_girt = create_receiving_cut(right_post_at_y, right_girt)
    
    # Add braces if requested
    braces = []
    if brace_params is not None:
        num_bents = len(bents)
        final_bents = []
        
        for i, (bent, y_pos) in enumerate(zip(bents, y_positions)):
            # Move posts to Y position for brace creation (deepcopy to avoid mutating original)
            left_post_at_y = copy.deepcopy(bent.left_post).move(Location((0, y_pos, 0)))
            right_post_at_y = copy.deepcopy(bent.right_post).move(Location((0, y_pos, 0)))
            
            # Determine brace directions based on position
            # First bent: braces toward +Y only
            # Last bent: braces toward -Y only
            # Middle bents: both directions
            if i == 0:
                directions = [(True, "")]  # toward +Y
            elif i == num_bents - 1:
                directions = [(False, "")]  # toward -Y
            else:
                directions = [(True, "a"), (False, "b")]  # both
            
            for toward_plus_y, suffix in directions:
                at_girt_start = not toward_plus_y
                
                # Left side brace
                left_brace_result = create_brace_for_girt(
                    post=left_post_at_y, girt=left_girt,
                    brace_section=brace_params.section,
                    brace_length=brace_params.length,
                    angle=brace_params.angle,
                    tenon_length=brace_params.tenon_length,
                    at_girt_start=at_girt_start,
                )
                braces.append((f"girt_brace_left_{i+1}{suffix}", left_brace_result.shape))
                left_girt = left_brace_result.horizontal_member
                left_post_at_y = left_brace_result.post  # Accumulate cuts on post
                
                # Right side brace
                right_brace_result = create_brace_for_girt(
                    post=right_post_at_y, girt=right_girt,
                    brace_section=brace_params.section,
                    brace_length=brace_params.length,
                    angle=brace_params.angle,
                    tenon_length=brace_params.tenon_length,
                    at_girt_start=at_girt_start,
                )
                braces.append((f"girt_brace_right_{i+1}{suffix}", right_brace_result.shape))
                right_girt = right_brace_result.horizontal_member
                right_post_at_y = right_brace_result.post  # Accumulate cuts on post
            
            # Move posts back to Y=0 and update the bent with cut posts
            left_post_final = left_post_at_y.move(Location((0, -y_pos, 0)))
            right_post_final = right_post_at_y.move(Location((0, -y_pos, 0)))
            final_bents.append(BentResult(
                left_post=left_post_final,
                right_post=right_post_final,
                beam=bent.beam,
                brace_left=bent.brace_left,
                brace_right=bent.brace_right,
                post_section=bent.post_section,
                beam_section=bent.beam_section,
                beam_length=bent.beam_length,
            ))
        
        # Use bents with girt brace mortises cut
        bents = final_bents
    
    return GirtResult(
        left_girt=left_girt,
        right_girt=right_girt,
        updated_bents=bents,  # Bents with tenons AND girt brace mortises cut
        braces=braces,
    )

from timber_joints.beam import Beam
from timber_joints.shouldered_tenon import ShoulderedTenon
from timber_joints.lap_joint import LapJoint
from build123d import Part, Box, Vector, Location, Axis, Align, Compound
from ocp_vscode import show_object

def build_rafter_pair(
    left_girt: Part,
    right_girt: Part,
    y_position: float,
    rafter_params: RafterParams,
) -> RafterPair:
    from timber_joints.utils import create_peg
    
    # Full building width (outer edge to outer edge of girts)
    building_width = right_girt.bounding_box().max.X - left_girt.bounding_box().min.X
    half_building_width = building_width / 2
    # Center X position between girts
    building_center_x = (left_girt.bounding_box().min.X + right_girt.bounding_box().max.X) / 2
    building_height = left_girt.bounding_box().max.Z
    tenon_length = rafter_params.section * 2 * math.tan(math.radians(rafter_params.pitch_angle))
    # Girt section is the X extent (width of the timber cross-section)
    girt_section = left_girt.bounding_box().max.X - left_girt.bounding_box().min.X
    # Top surface offset along the rafter due to pitch angle
    # Lap length: from overhang tip to inner edge of girt (where rafter top surface meets girt inner edge)
    lap_length = rafter_params.overhang + rafter_params.section / 2 * math.tan(math.radians(rafter_params.pitch_angle))
    # Rafter length: from overhang tip to peak, plus extra for the peak joint overlap
    # The rafter needs to extend past center by section/cos(angle) for the tongue-and-fork joint
    peak_extension = rafter_params.section / math.cos(math.radians(rafter_params.pitch_angle))
    # rafter_length = half_building_width / math.cos(math.radians(rafter_params.pitch_angle)) + rafter_params.overhang + peak_extension + (rafter_params.section / 2) * math.tan(math.radians(rafter_params.pitch_angle)) - girt_section * math.tan(math.radians(rafter_params.pitch_angle))# inside edge
    rafter_length = half_building_width / math.cos(math.radians(rafter_params.pitch_angle)) + rafter_params.overhang + peak_extension - rafter_params.section * math.tan(math.radians(rafter_params.pitch_angle)) # middle
    # rafter_length = half_building_width / math.cos(math.radians(rafter_params.pitch_angle)) + rafter_params.overhang + peak_extension # outside edge
    
    lap_depth = rafter_params.get_lap_depth()
    
    # === LEFT RAFTER ===
    left_rafter_beam = Beam(
        length=rafter_length,
        width=rafter_params.section,
        height=rafter_params.section,
    )

    left_rafter_with_lap = LapJoint(
        beam=left_rafter_beam.shape,
        cut_length=lap_length,
        cut_depth=lap_depth,
        from_top=False,
        at_start=True,
    ).shape
    
    # Create lap peg BEFORE rotation (rafter is horizontal, peg is vertical)
    left_lap_peg = None
    left_peg_hole = None
    if rafter_params.include_pegs:
        peg_length = rafter_params.section  # Full rafter section
        left_lap_peg = create_peg(length=peg_length, diameter=rafter_params.peg_diameter, axis=Axis.Z)
        # Position peg in the lap area: offset from start of lap joint (girt-side edge at x=lap_length)
        peg_x = lap_length - rafter_params.peg_offset  # offset inward from girt-side edge of lap
        peg_y = rafter_params.section / 2  # center of rafter width
        peg_z = 0  # start at bottom of rafter (peg goes through full section)
        left_lap_peg = left_lap_peg.move(Location((peg_x, peg_y, peg_z)))
        # Create peg hole (same position, will be used to cut rafter and girt)
        left_peg_hole = create_peg(length=peg_length, diameter=rafter_params.peg_diameter, axis=Axis.Z)
        left_peg_hole = left_peg_hole.move(Location((peg_x, peg_y, peg_z)))
        # Cut peg hole from rafter (before adding tenon)
        left_rafter_with_lap = left_rafter_with_lap - left_peg_hole

    left_rafter_with_tenon = ShoulderedTenon(
        beam=left_rafter_with_lap,
        tenon_width=rafter_params.section / 3,
        tenon_height=rafter_params.section,
        tenon_length=tenon_length,
        shoulder_depth=rafter_params.section * math.tan(math.radians(rafter_params.pitch_angle)),
        at_start=False,
    ).shape
    
    # Rotate left rafter (and peg together if exists)
    left_rafter_rotated = left_rafter_with_tenon.rotate(
        Axis.Y,
        -rafter_params.pitch_angle,
    )
    if left_lap_peg is not None:
        left_lap_peg = left_lap_peg.rotate(Axis.Y, -rafter_params.pitch_angle)
    if left_peg_hole is not None:
        left_peg_hole = left_peg_hole.rotate(Axis.Y, -rafter_params.pitch_angle)

    # === RIGHT RAFTER ===
    right_rafter_beam = Beam(
        length=rafter_length,
        width=rafter_params.section,
        height=rafter_params.section,
    )
    
    right_rafter_with_lap = LapJoint(
        beam=right_rafter_beam.shape,
        cut_length=lap_length,
        cut_depth=lap_depth,
        from_top=False,
        at_start=False,
    ).shape
    
    # Create lap peg BEFORE rotation for right rafter
    right_lap_peg = None
    right_peg_hole = None
    if rafter_params.include_pegs:
        peg_length = rafter_params.section  # Full rafter section
        right_lap_peg = create_peg(length=peg_length, diameter=rafter_params.peg_diameter, axis=Axis.Z)
        # Position peg in the lap area: offset from start of lap joint (which is at rafter_length - lap_length)
        peg_x = rafter_length - lap_length + rafter_params.peg_offset  # offset from start of lap joint
        peg_y = rafter_params.section / 2  # center of rafter width
        peg_z = 0  # start at bottom of rafter (peg goes through full section)
        right_lap_peg = right_lap_peg.move(Location((peg_x, peg_y, peg_z)))
        # Create peg hole (same position, will be used to cut rafter and girt)
        right_peg_hole = create_peg(length=peg_length, diameter=rafter_params.peg_diameter, axis=Axis.Z)
        right_peg_hole = right_peg_hole.move(Location((peg_x, peg_y, peg_z)))
        # Cut peg hole from rafter
        right_rafter_with_lap = right_rafter_with_lap - right_peg_hole
    
    # Rotate and position right rafter (and peg)
    right_rafter_rotated = right_rafter_with_lap.rotate(
        Axis.Y,
        rafter_params.pitch_angle,
    ).move(Location((
        rafter_length * math.cos(math.radians(rafter_params.pitch_angle)) - rafter_params.section * 2,
        0,
        rafter_length * math.sin(math.radians(rafter_params.pitch_angle)),
    )))
    
    if right_lap_peg is not None:
        right_lap_peg = right_lap_peg.rotate(
            Axis.Y,
            rafter_params.pitch_angle,
        ).move(Location((
            rafter_length * math.cos(math.radians(rafter_params.pitch_angle)) - rafter_params.section * 2,
            0,
            rafter_length * math.sin(math.radians(rafter_params.pitch_angle)),
        )))
    
    if right_peg_hole is not None:
        right_peg_hole = right_peg_hole.rotate(
            Axis.Y,
            rafter_params.pitch_angle,
        ).move(Location((
            rafter_length * math.cos(math.radians(rafter_params.pitch_angle)) - rafter_params.section * 2,
            0,
            rafter_length * math.sin(math.radians(rafter_params.pitch_angle)),
        )))

    right_rafter_with_mortise = create_receiving_cut(
        positioned_insert=left_rafter_rotated,
        receiving_shape=right_rafter_rotated,
    )

    left_trimbox = Box(
        height=rafter_params.section,
        width=rafter_params.section,
        length=rafter_length,
        align=(Align.MIN, Align.MIN, Align.MIN),
    )
    left_trimbox = left_trimbox.rotate(
        Axis.Y,
        -rafter_params.pitch_angle,
    ).move(Location((
        0,
        0,
        rafter_params.section * math.tan(math.radians(rafter_params.pitch_angle)) * 2
    )))
    right_rafter_trimmed = right_rafter_with_mortise - left_trimbox

    right_trimbox = Box(
        height=rafter_params.section,
        width=rafter_params.section,
        length=rafter_length,
        align=(Align.MIN, Align.MIN, Align.MIN),
    )
    right_trimbox = right_trimbox.rotate(
        Axis.Y,
        rafter_params.pitch_angle,
    ).move(Location((
        rafter_length * math.cos(math.radians(rafter_params.pitch_angle)) - rafter_params.section * 2,      
        0,
        rafter_length * math.sin(math.radians(rafter_params.pitch_angle)) + rafter_params.section * math.tan(math.radians(rafter_params.pitch_angle)) * 2,
    )))
    left_after_trimmed = left_rafter_rotated - right_trimbox

    rafter_pair = [left_after_trimmed, right_rafter_trimmed]
    rafter_pair_bbox = Compound(rafter_pair).bounding_box()
    # Center using the midpoint of the bounding box
    rafter_pair_center_x = (rafter_pair_bbox.min.X + rafter_pair_bbox.max.X) / 2
    
    # Z position: rafter top face aligns with girt top
    girt_top = left_girt.bounding_box().max.Z
    
    # Final positioning offset
    final_offset = Location((
        building_center_x - rafter_pair_center_x,
        y_position,
        building_height - lap_length * math.sin(math.radians(rafter_params.pitch_angle)) - rafter_params.section / 2 * math.cos(math.radians(rafter_params.pitch_angle)),
    ))

    moved_rafter_pair = [rafter.move(final_offset) for rafter in rafter_pair]
    left_rafter_positioned, right_rafter_positioned = moved_rafter_pair
    
    # Move pegs and peg holes with the same final offset
    pegs = []
    peg_holes = []
    if rafter_params.include_pegs:
        if left_lap_peg is not None:
            left_lap_peg = left_lap_peg.move(final_offset)
            pegs.append(left_lap_peg)
        
        if left_peg_hole is not None:
            left_peg_hole = left_peg_hole.move(final_offset)
            peg_holes.append(left_peg_hole)
        
        if right_lap_peg is not None:
            right_lap_peg = right_lap_peg.move(final_offset)
            pegs.append(right_lap_peg)
        
        if right_peg_hole is not None:
            right_peg_hole = right_peg_hole.move(final_offset)
            peg_holes.append(right_peg_hole)
        
        # Peak peg (tongue-and-fork joint)
        peak_peg = create_peak_peg_for_rafter(
            left_rafter_bbox=left_rafter_positioned.bounding_box(),
            right_rafter_bbox=right_rafter_positioned.bounding_box(),
            peg_diameter=rafter_params.peg_diameter,
            peg_offset=rafter_params.peg_offset,
            pitch_angle=rafter_params.pitch_angle,
            rafter_section=rafter_params.section,
        )
        pegs.append(peak_peg)
        # Cut peg hole from both rafters
        left_rafter_positioned = left_rafter_positioned - peak_peg
        right_rafter_positioned = right_rafter_positioned - peak_peg
    
    return RafterPair(
        left_rafter=left_rafter_positioned,
        right_rafter=right_rafter_positioned,
        left_girt=left_girt,
        right_girt=right_girt,
        pegs=pegs,
        peg_holes=peg_holes,
    )


def add_rafters_to_barn(
    left_girt: Part,
    right_girt: Part,
    y_positions: List[float],
    rafter_params: RafterParams = None,
) -> RafterResult:
    """Add rafters to a barn frame at each bent position.
    
    Creates rafter pairs at each Y position, with tongue-and-fork joints
    at the peak and lap joints at the girts. Cuts lap joints into girts.
    
    Args:
        left_girt: Left girt (will be updated with lap cuts)
        right_girt: Right girt (will be updated with lap cuts)
        y_positions: Y positions for each rafter pair (typically bent positions)
        rafter_params: Configuration for rafters (default: RafterParams())
    
    Returns:
        RafterResult with all rafter pairs and updated girts with lap cuts
    """
    if rafter_params is None:
        rafter_params = RafterParams()
    
    rafter_pairs = []
    all_left_rafters = []
    all_right_rafters = []
    all_left_peg_holes = []
    all_right_peg_holes = []
    
    for y_pos in y_positions:
        pair = build_rafter_pair(
            left_girt=left_girt,
            right_girt=right_girt,
            y_position=y_pos,
            rafter_params=rafter_params,
        )
        rafter_pairs.append(pair)
        all_left_rafters.append(pair.left_rafter)
        all_right_rafters.append(pair.right_rafter)
        # Collect peg holes: first hole is for left girt, second is for right girt
        if len(pair.peg_holes) >= 1:
            all_left_peg_holes.append(pair.peg_holes[0])
        if len(pair.peg_holes) >= 2:
            all_right_peg_holes.append(pair.peg_holes[1])
    
    # Cut lap joints into girts using all rafters as cutting shapes
    updated_left_girt = left_girt
    updated_right_girt = right_girt
    
    # Cut left girt with all left rafters
    left_rafter_compound = Compound(all_left_rafters)
    updated_left_girt = create_receiving_cut(left_rafter_compound, updated_left_girt)
    
    # Cut right girt with all right rafters
    right_rafter_compound = Compound(all_right_rafters)
    updated_right_girt = create_receiving_cut(right_rafter_compound, updated_right_girt)
    
    # Cut peg holes from girts
    if all_left_peg_holes:
        left_peg_hole_compound = Compound(all_left_peg_holes)
        updated_left_girt = updated_left_girt - left_peg_hole_compound
    
    if all_right_peg_holes:
        right_peg_hole_compound = Compound(all_right_peg_holes)
        updated_right_girt = updated_right_girt - right_peg_hole_compound
    
    return RafterResult(
        rafter_pairs=rafter_pairs,
        updated_left_girt=updated_left_girt,
        updated_right_girt=updated_right_girt,
    )
