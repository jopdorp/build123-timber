"""Timber Joints v2 - Simplified timber joinery library."""

from timber_joints.base_joint import BaseJoint
from timber_joints.beam import Beam
from timber_joints.lap_joint import LapJoint
from timber_joints.lap_x_section import LapXSection
from timber_joints.tenon import Tenon
from timber_joints.shouldered_tenon import ShoulderedTenon
from timber_joints.dovetail import DovetailInsert
from timber_joints.half_dovetail import HalfDovetail
from timber_joints.brace_tenon import BraceTenon
from timber_joints.alignment import (
    align_beam_on_post,
    align_beam_in_post,
    make_post_vertical,
    create_receiving_cut,
    position_for_blind_mortise,
    build_complete_bent,
    calculate_brace_angle,
    calculate_brace_length,
    create_brace_for_bent,
    create_brace_for_girt,
    PositionedBrace,
)
from timber_joints.utils import get_shape_dimensions

# Frame assembly
from timber_joints.frame import (
    Role,
    Element,
    Joint,
    TimberFrame,
    simple_bent,
    bay_frame,
)

# Barn frame builder
from timber_joints.barn import (
    BarnConfig,
    Bent,
    BarnFrame,
)

# Export adapters
from timber_joints.export import (
    export_frame_to_ifc,
    show_frame,
    export_beam_schedule,
)

# Shape utilities
from timber_joints.utils import (
    get_bbox_solid,
    scale_shape_in_place,
    expand_shape_by_margin,
)

# Mesh utilities (from fea.meshing)
from timber_joints.fea.meshing import (
    find_mesh_contact_faces,
    build_mesh_faces_compound,
)

__all__ = [
    # Core
    "BaseJoint",
    "Beam",
    "LapJoint",
    "LapXSection",
    "Tenon",
    "ShoulderedTenon",
    "DovetailInsert",
    "HalfDovetail",
    "BraceTenon",
    # Utilities
    "get_shape_dimensions",
    # Alignment
    "align_beam_on_post",
    "align_beam_in_post",
    "make_post_vertical",
    "create_receiving_cut",
    "position_for_blind_mortise",
    "build_complete_bent",
    "calculate_brace_angle",
    "calculate_brace_length",
    "create_brace_for_bent",
    "create_brace_for_girt",
    "PositionedBrace",
    # Frame assembly
    "Role",
    "Element",
    "Joint",
    "TimberFrame",
    "simple_bent",
    "bay_frame",
    # Barn frame builder
    "BarnConfig",
    "Bent",
    "BarnFrame",
    # Export
    "export_frame_to_ifc",
    "show_frame",
    "export_beam_schedule",
    # Shape utilities
    "get_bbox_solid",
    "scale_shape_in_place",
    "expand_shape_by_margin",
    # Mesh utilities
    "find_mesh_contact_faces",
    "build_mesh_faces_compound",
]
