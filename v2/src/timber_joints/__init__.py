"""Timber Joints v2 - Simplified timber joinery library."""

from timber_joints.beam import Beam
from timber_joints.lap_joint import LapJoint
from timber_joints.lap_x_section import LapXSection
from timber_joints.tenon import Tenon
from timber_joints.shouldered_tenon import ShoulderedTenon
from timber_joints.dovetail import DovetailInsert
from timber_joints.half_dovetail import HalfDovetail
from timber_joints.alignment import (
    align_beam_on_post,
    align_beam_in_post,
    make_post_vertical,
    create_receiving_cut,
    position_for_blind_mortise,
    build_complete_bent,
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

# Export adapters
from timber_joints.export import (
    export_frame_to_ifc,
    show_frame,
    export_beam_schedule,
)

# Analysis (optional - requires gmsh/CalculiX)
from timber_joints.analysis import (
    TimberMaterial,
    AnalysisConfig,
    AnalysisResult,
    analyze_element,
    analyze_frame,
    print_analysis_summary,
)

__all__ = [
    # Core
    "Beam",
    "LapJoint",
    "LapXSection",
    "Tenon",
    "ShoulderedTenon",
    "DovetailInsert",
    "HalfDovetail",
    # Utilities
    "get_shape_dimensions",
    # Alignment
    "align_beam_on_post",
    "align_beam_in_post",
    "make_post_vertical",
    "create_receiving_cut",
    "position_for_blind_mortise",
    "build_complete_bent",
    # Frame assembly
    "Role",
    "Element",
    "Joint",
    "TimberFrame",
    "simple_bent",
    "bay_frame",
    # Export
    "export_frame_to_ifc",
    "show_frame",
    "export_beam_schedule",
    # Analysis
    "TimberMaterial",
    "AnalysisConfig",
    "AnalysisResult",
    "analyze_element",
    "analyze_frame",
    "print_analysis_summary",
]
