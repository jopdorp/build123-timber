"""FEA module for timber structural analysis.

This module provides utilities for:
- Mesh generation with contact region refinement
- CalculiX input generation and solver interface
- Results post-processing and visualization
- Generic assembly analysis pipeline

Future extensions:
- EasyFEA integration for moisture/shrinkage analysis
- Crack simulation capabilities
"""

from .meshing import (
    RefinementBox,
    MeshResult,
    CombinedMesh,
    mesh_part,
    get_contact_region_bbox,
    expand_bbox,
    get_boundary_faces,
    combine_meshes,
    write_mesh_inp,
)

from .calculix import (
    ContactParameters,
    StepParameters,
    GrainOrientation,
    TimberMaterial,
    CalculiXInput,
    run_calculix,
    FEAResults,
    read_frd_displacements,
    read_frd_nodes,
    analyze_results,
    BEAM_HORIZONTAL_X,
    POST_VERTICAL_Z,
)

from .visualization import (
    read_mesh_elements,
    get_outer_faces,
    build_triangle_compound,
    apply_displacements,
    build_deformed_mesh,
    show_fea_results,
)

from .assembly import (
    FEAPart,
    ContactPair,
    FixedBC,
    LoadBC,
    AssemblyConfig,
    AssemblyResult,
    analyze_assembly,
    nodes_at_location,
    nodes_in_bbox,
)

from .frame import (
    MemberType,
    FrameMember,
    TimberFrame,
)

__all__ = [
    # Meshing
    "RefinementBox",
    "MeshResult", 
    "CombinedMesh",
    "mesh_part",
    "get_contact_region_bbox",
    "expand_bbox",
    "get_boundary_faces",
    "combine_meshes",
    "write_mesh_inp",
    # CalculiX
    "ContactParameters",
    "StepParameters",
    "GrainOrientation",
    "TimberMaterial",
    "CalculiXInput",
    "run_calculix",
    "FEAResults",
    "read_frd_displacements",
    "read_frd_nodes",
    "analyze_results",
    "BEAM_HORIZONTAL_X",
    "POST_VERTICAL_Z",
    # Visualization
    "read_mesh_elements",
    "get_outer_faces",
    "build_triangle_compound",
    "apply_displacements",
    "build_deformed_mesh",
    "show_fea_results",
    # Generic Assembly API
    "FEAPart",
    "ContactPair",
    "FixedBC",
    "LoadBC",
    "AssemblyConfig",
    "AssemblyResult",
    "analyze_assembly",
    "nodes_at_location",
    "nodes_in_bbox",
    # High-level Frame API
    "MemberType",
    "FrameMember",
    "TimberFrame",
]
