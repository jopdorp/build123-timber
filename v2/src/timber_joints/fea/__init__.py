"""FEA module for timber structural analysis.

This module provides utilities for:
- Mesh generation with contact region refinement
- CalculiX input generation and solver interface
- Results post-processing and visualization

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

from .pipeline import (
    BentFrameConfig,
    BentFrameAnalysisResult,
    analyze_bent_frame,
)

from .visualization import (
    read_mesh_elements,
    get_outer_faces,
    build_triangle_compound,
    apply_displacements,
    build_deformed_mesh,
    show_fea_results,
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
    # Pipeline
    "BentFrameConfig",
    "BentFrameAnalysisResult",
    "analyze_bent_frame",
    # Visualization
    "read_mesh_elements",
    "get_outer_faces",
    "build_triangle_compound",
    "apply_displacements",
    "build_deformed_mesh",
    "show_fea_results",
]
