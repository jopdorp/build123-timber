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
    
    def get_joint_class(self):
        if self.joint_class is None:
            from timber_joints.shouldered_tenon import ShoulderedTenon
            return ShoulderedTenon
        return self.joint_class
    
    def get_tenon_dimensions(self, beam_width: float, beam_height: float) -> tuple[float, float]:
        """Calculate tenon width and height from beam dimensions."""
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
    
    return BentResult(
        left_post=left_post,
        right_post=right_post,
        beam=beam,
        brace_left=brace_left,
        brace_right=brace_right,
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
    
    if len(bents) < 2:
        raise ValueError("Need at least 2 bents to add girts")
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
