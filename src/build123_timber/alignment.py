from __future__ import annotations

import math
from typing import TYPE_CHECKING

from build123d import Location, Vector, Axis, Edge

if TYPE_CHECKING:
    from build123_timber.elements import Timber


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


def map_tenon_to_mortise_dimensions(
    tenon_timber: Timber,
    mortise_timber: Timber,
    tenon_width: float,
    tenon_height: float,
    mortise_face: str = "front",
) -> tuple[float, float]:
    """Map tenon dimensions (in tenon timber's local space) to mortise dimensions (in mortise timber's local space).
    
    The tenon is defined in the cross timber's local coordinates:
    - tenon_width: Y direction of tenon timber
    - tenon_height: Z direction of tenon timber
    
    This function determines how these map to the mortise opening dimensions
    after considering both timbers' rotations and which face the mortise is on.
    
    Args:
        tenon_timber: The timber with the tenon (cross timber)
        mortise_timber: The timber with the mortise (main timber)
        tenon_width: Width of tenon in tenon timber's local Y
        tenon_height: Height of tenon in tenon timber's local Z
        mortise_face: Which face of mortise timber the mortise is on:
            - "front"/"back": mortise opening in X and Z
            - "top"/"bottom"/"right": mortise opening in X and Y
    
    Returns:
        (mortise_dim1, mortise_dim2) dimensions for the mortise opening
        - For front/back face: (width in X, height in Z)
        - For top/bottom/right face: (width in X, height in Y)
    """
    # Get rotation info for both timbers
    tenon_rot = tuple(tenon_timber.location.orientation)
    mortise_rot = tuple(mortise_timber.location.orientation)
    
    # Transform tenon's local Y and Z to world coordinates
    tenon_y_world = _rotate_vector(Vector(0, 1, 0), *tenon_rot)
    tenon_z_world = _rotate_vector(Vector(0, 0, 1), *tenon_rot)
    
    # Get mortise timber's local axes in world coordinates
    mortise_x_world = _rotate_vector(Vector(1, 0, 0), *mortise_rot)
    mortise_y_world = _rotate_vector(Vector(0, 1, 0), *mortise_rot)
    mortise_z_world = _rotate_vector(Vector(0, 0, 1), *mortise_rot)
    
    # Determine which mortise axes define the opening based on face
    if mortise_face in ("front", "back"):
        # Mortise opening is in X and Z of mortise timber
        axis1_world = mortise_x_world  # width direction
        axis2_world = mortise_z_world  # height direction
    else:  # top, bottom, right
        # Mortise opening is in X and Y of mortise timber
        axis1_world = mortise_x_world  # width direction
        axis2_world = mortise_y_world  # height direction
    
    # Check how tenon Y and Z align with mortise opening axes
    tenon_y_to_axis1 = abs(_dot(tenon_y_world, axis1_world))
    tenon_y_to_axis2 = abs(_dot(tenon_y_world, axis2_world))
    tenon_z_to_axis1 = abs(_dot(tenon_z_world, axis1_world))
    tenon_z_to_axis2 = abs(_dot(tenon_z_world, axis2_world))
    
    # Determine mapping based on strongest alignment
    # tenon_width is in tenon Y, tenon_height is in tenon Z
    
    # Check if tenon Y aligns more with axis1 or axis2
    if tenon_y_to_axis1 > tenon_y_to_axis2:
        # tenon Y -> axis1 (mortise dim1), tenon Z -> axis2 (mortise dim2)
        mortise_dim1 = tenon_width
        mortise_dim2 = tenon_height
    else:
        # tenon Y -> axis2 (mortise dim2), tenon Z -> axis1 (mortise dim1)
        mortise_dim1 = tenon_height
        mortise_dim2 = tenon_width
    
    return (mortise_dim1, mortise_dim2)


def _dot(a: Vector, b: Vector) -> float:
    """Dot product of two vectors."""
    return a.X * b.X + a.Y * b.Y + a.Z * b.Z
