from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from build123d import Location, Vector, Axis, Part, Edge, Compound

if TYPE_CHECKING:
    from build123_timber.elements import Timber


class ConnectionEnd(Enum):
    START = auto()
    END = auto()
    CENTER = auto()


@dataclass
class ConnectionPoint:
    end: ConnectionEnd | None = None
    position: float | None = None
    fraction: float | None = None

    @classmethod
    def start(cls) -> ConnectionPoint:
        return cls(end=ConnectionEnd.START)

    @classmethod
    def end(cls) -> ConnectionPoint:
        return cls(end=ConnectionEnd.END)

    @classmethod
    def center(cls) -> ConnectionPoint:
        return cls(end=ConnectionEnd.CENTER)

    @classmethod
    def at(cls, position: float) -> ConnectionPoint:
        return cls(position=position)

    @classmethod
    def at_fraction(cls, fraction: float) -> ConnectionPoint:
        if not 0 <= fraction <= 1:
            raise ValueError(f"Fraction must be 0-1, got {fraction}")
        return cls(fraction=fraction)

    def resolve(self, timber: Timber) -> float:
        if self.end == ConnectionEnd.START:
            return 0.0
        if self.end == ConnectionEnd.END:
            return timber.length
        if self.end == ConnectionEnd.CENTER:
            return timber.length / 2
        if self.position is not None:
            return self.position
        if self.fraction is not None:
            return timber.length * self.fraction
        return 0.0


def show_lcs(timber: Timber, size: float = 50) -> tuple[Edge, Edge, Edge]:
    """Show local coordinate system of a Timber as 3 colored axis lines.
    
    Returns (x_line, y_line, z_line) colored red, green, blue.
    Use this to debug orientation issues.
    """
    origin = timber.location.position
    rot = timber.location.orientation
    
    rot_tuple = tuple(rot)
    rx, ry, rz = rot_tuple[0], rot_tuple[1], rot_tuple[2]
    
    x_dir = _rotate_vector(Vector(1, 0, 0), rx, ry, rz)
    y_dir = _rotate_vector(Vector(0, 1, 0), rx, ry, rz)
    z_dir = _rotate_vector(Vector(0, 0, 1), rx, ry, rz)
    
    x_end = Vector(origin.X + x_dir.X * size, origin.Y + x_dir.Y * size, origin.Z + x_dir.Z * size)
    y_end = Vector(origin.X + y_dir.X * size, origin.Y + y_dir.Y * size, origin.Z + y_dir.Z * size)
    z_end = Vector(origin.X + z_dir.X * size, origin.Y + z_dir.Y * size, origin.Z + z_dir.Z * size)
    
    x_line = Edge.make_line(origin, x_end)
    y_line = Edge.make_line(origin, y_end)
    z_line = Edge.make_line(origin, z_end)
    
    return (x_line, y_line, z_line)


def _rotate_vector(v: Vector, rx: float, ry: float, rz: float) -> Vector:
    """Rotate vector by Euler angles (degrees)."""
    x, y, z = v.X, v.Y, v.Z
    
    rz_rad = math.radians(rz)
    cos_z, sin_z = math.cos(rz_rad), math.sin(rz_rad)
    x, y = x * cos_z - y * sin_z, x * sin_z + y * cos_z
    
    ry_rad = math.radians(ry)
    cos_y, sin_y = math.cos(ry_rad), math.sin(ry_rad)
    x, z = x * cos_y + z * sin_y, -x * sin_y + z * cos_y
    
    rx_rad = math.radians(rx)
    cos_x, sin_x = math.cos(rx_rad), math.sin(rx_rad)
    y, z = y * cos_x - z * sin_x, y * sin_x + z * cos_x
    
    return Vector(x, y, z)


def make_timber_axis(timber: Timber, local_point: Vector, local_direction: Vector) -> Axis:
    """Create an axis in world coordinates from timber's local coordinate system.
    
    Args:
        timber: The timber element
        local_point: Point in timber's local coords (e.g., Vector(0,0,0) for origin)
        local_direction: Direction in timber's local coords (e.g., Vector(1,0,0) for along length)
    
    Returns:
        Axis in world coordinates
    """
    rot = timber.location.orientation
    rot_tuple = tuple(rot)
    rx, ry, rz = rot_tuple[0], rot_tuple[1], rot_tuple[2]
    
    world_point = _local_to_world(timber, local_point)
    world_dir = _rotate_vector(local_direction, rx, ry, rz)
    
    return Axis(world_point, world_dir)


def _local_to_world(timber: Timber, local_point: Vector) -> Vector:
    """Convert local point to world coordinates."""
    origin = timber.location.position
    rot = timber.location.orientation
    rot_tuple = tuple(rot)
    rx, ry, rz = rot_tuple[0], rot_tuple[1], rot_tuple[2]
    
    rotated = _rotate_vector(local_point, rx, ry, rz)
    return Vector(origin.X + rotated.X, origin.Y + rotated.Y, origin.Z + rotated.Z)


def auto_align(
    tenon_timber: Timber,
    tenon_axis: Axis,
    mortise_timber: Timber,
    mortise_axis: Axis,
) -> Timber:
    """Align tenon timber into mortise timber using axis matching.
    
    This is the universal auto-alignment algorithm:
    1. Rotates tenon so its axis aligns with mortise axis (opposing direction)
    2. Translates tenon base point onto mortise base point
    
    Args:
        tenon_timber: The timber with the tenon (will be moved)
        tenon_axis: Axis defining tenon protrusion direction
        mortise_axis: Axis defining mortise receiving direction
    
    Returns:
        The tenon_timber with updated location
    """
    tenon_dir = Vector(tenon_axis.direction.X, tenon_axis.direction.Y, tenon_axis.direction.Z)
    mortise_dir = Vector(mortise_axis.direction.X, mortise_axis.direction.Y, mortise_axis.direction.Z)
    
    target_dir = Vector(-mortise_dir.X, -mortise_dir.Y, -mortise_dir.Z)
    
    rotation = _compute_rotation_to_align(tenon_dir, target_dir)
    
    translation = Vector(
        mortise_axis.position.X - tenon_axis.position.X,
        mortise_axis.position.Y - tenon_axis.position.Y,
        mortise_axis.position.Z - tenon_axis.position.Z,
    )
    
    current_rot = tuple(tenon_timber.location.orientation)
    new_rot = (
        current_rot[0] + rotation[0],
        current_rot[1] + rotation[1],
        current_rot[2] + rotation[2],
    )
    
    current_pos = tenon_timber.location.position
    new_pos = (
        current_pos.X + translation.X,
        current_pos.Y + translation.Y,
        current_pos.Z + translation.Z,
    )
    
    tenon_timber.location = Location(new_pos, new_rot)
    return tenon_timber


def _compute_rotation_to_align(from_dir: Vector, to_dir: Vector) -> tuple[float, float, float]:
    """Compute Euler rotation to align from_dir with to_dir."""
    from_dir = _normalize(from_dir)
    to_dir = _normalize(to_dir)
    
    dot = from_dir.X * to_dir.X + from_dir.Y * to_dir.Y + from_dir.Z * to_dir.Z
    
    if dot > 0.9999:
        return (0, 0, 0)
    if dot < -0.9999:
        return (0, 180, 0)
    
    angle = math.acos(max(-1, min(1, dot)))
    
    cross = Vector(
        from_dir.Y * to_dir.Z - from_dir.Z * to_dir.Y,
        from_dir.Z * to_dir.X - from_dir.X * to_dir.Z,
        from_dir.X * to_dir.Y - from_dir.Y * to_dir.X,
    )
    cross = _normalize(cross)
    
    angle_deg = math.degrees(angle)
    
    if abs(cross.Z) > 0.9:
        return (0, 0, angle_deg if cross.Z > 0 else -angle_deg)
    elif abs(cross.Y) > 0.9:
        return (0, angle_deg if cross.Y > 0 else -angle_deg, 0)
    elif abs(cross.X) > 0.9:
        return (angle_deg if cross.X > 0 else -angle_deg, 0, 0)
    else:
        return (0, 0, angle_deg)


def _normalize(v: Vector) -> Vector:
    """Normalize a vector."""
    length = math.sqrt(v.X**2 + v.Y**2 + v.Z**2)
    if length < 1e-10:
        return Vector(0, 0, 1)
    return Vector(v.X / length, v.Y / length, v.Z / length)


class TimberFace(Enum):
    TOP = auto()
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()
    START = auto()
    END = auto()


class CrossOrientation(Enum):
    PERPENDICULAR = auto()
    PARALLEL = auto()
    ANGLED = auto()


@dataclass
class JointAlignment:
    """Legacy alignment class - use auto_align() for new code."""
    main_point: ConnectionPoint | None = None
    main_face: TimberFace = TimberFace.TOP
    cross_point: ConnectionPoint | None = None
    cross_face: TimberFace = TimberFace.END
    orientation: CrossOrientation = CrossOrientation.PERPENDICULAR
    angle: float = 90.0
    offset: tuple[float, float, float] = (0, 0, 0)

    def compute_cross_location(self, main: Timber, cross: Timber) -> Location:
        main_x = self.main_point.resolve(main) if self.main_point else main.length / 2
        cross_conn = self.cross_point.resolve(cross) if self.cross_point else 0.0

        main_pos = main.location.position
        main_rot = tuple(main.location.orientation)
        main_z_rot = main_rot[2] if len(main_rot) >= 3 else 0.0

        local_conn_x, local_conn_y = _rotate_z(main_x, 0, main_z_rot)
        conn_x = main_pos.X + local_conn_x
        conn_y = main_pos.Y + local_conn_y
        conn_z = main_pos.Z

        face_offset_local = self._get_face_offset(main, cross)
        face_off_x, face_off_y = _rotate_z(face_offset_local[0], face_offset_local[1], main_z_rot)
        face_off_z = face_offset_local[2]

        cross_rotation = self._compute_cross_rotation(main_z_rot, cross)

        cross_offset = self._get_cross_origin_offset(cross, cross_conn)
        rot_z = cross_rotation[2]
        cross_off_x, cross_off_y = _rotate_z(cross_offset[0], cross_offset[1], rot_z)
        cross_off_z = cross_offset[2]

        final_x = conn_x + face_off_x - cross_off_x + self.offset[0]
        final_y = conn_y + face_off_y - cross_off_y + self.offset[1]
        final_z = conn_z + face_off_z - cross_off_z + self.offset[2]

        return Location((final_x, final_y, final_z), cross_rotation)

    def _get_face_offset(self, main: Timber, cross: Timber) -> tuple[float, float, float]:
        if self.main_face == TimberFace.TOP:
            return (0, 0, main.height / 2)
        elif self.main_face == TimberFace.BOTTOM:
            return (0, 0, -main.height / 2)
        elif self.main_face == TimberFace.LEFT:
            return (0, -main.width / 2, 0)
        elif self.main_face == TimberFace.RIGHT:
            return (0, main.width / 2, 0)
        elif self.main_face == TimberFace.START:
            return (-main.width / 2, 0, 0)
        elif self.main_face == TimberFace.END:
            return (main.width / 2, 0, 0)
        return (0, 0, 0)

    def _get_cross_origin_offset(self, cross: Timber, cross_conn: float) -> tuple[float, float, float]:
        if self.cross_face == TimberFace.END:
            return (cross_conn, 0, 0)
        elif self.cross_face == TimberFace.START:
            return (cross_conn, 0, 0)
        elif self.cross_face == TimberFace.TOP:
            return (cross_conn, 0, cross.height / 2)
        elif self.cross_face == TimberFace.BOTTOM:
            return (cross_conn, 0, -cross.height / 2)
        elif self.cross_face == TimberFace.LEFT:
            return (cross_conn, -cross.width / 2, 0)
        elif self.cross_face == TimberFace.RIGHT:
            return (cross_conn, cross.width / 2, 0)
        return (cross_conn, 0, 0)

    def _compute_cross_rotation(self, main_z_rot: float, cross: Timber) -> tuple[float, float, float]:
        rx, ry, rz = 0.0, 0.0, 0.0

        if self.orientation == CrossOrientation.PERPENDICULAR:
            rz = main_z_rot + 90
        elif self.orientation == CrossOrientation.PARALLEL:
            rz = main_z_rot
        elif self.orientation == CrossOrientation.ANGLED:
            rz = main_z_rot + self.angle

        if self.cross_face == TimberFace.TOP:
            rx = 90
        elif self.cross_face == TimberFace.BOTTOM:
            rx = -90

        if self.main_face == TimberFace.TOP and self.cross_face == TimberFace.END:
            rx = -90
            rz = main_z_rot + 90 if self.orientation == CrossOrientation.PERPENDICULAR else main_z_rot

        return (rx, ry, rz)


def _rotate_z(x: float, y: float, angle_deg: float) -> tuple[float, float]:
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)


class VerticalAlign(Enum):
    TOP = auto()
    BOTTOM = auto()
    CENTER = auto()
    FLUSH_TOP = auto()
    FLUSH_BOTTOM = auto()


class HorizontalAlign(Enum):
    LEFT = auto()
    RIGHT = auto()
    CENTER = auto()


START = ConnectionPoint.start()
END = ConnectionPoint.end()
CENTER = ConnectionPoint.center()
