"""FEA module for timber structural analysis.

This module provides:
- **Materials**: Orthotropic timber materials with MFront support
- **Solver backends**: Pluggable FEA solvers (CalculiX, Code_Aster)
- **Mesh generation**: Contact region refinement
- **Results post-processing**: Displacement/stress visualization

Architecture
------------
The FEA system uses a backend abstraction allowing the same analysis
to run on different solvers:

    from timber_joints.fea import analyze, SolverType
    
    # Use default backend (CalculiX)
    result = analyze(problem)
    
    # Or specify a backend
    result = analyze(problem, backend=SolverType.CODE_ASTER)

Materials
---------
Materials support MFront for advanced constitutive models:

    from timber_joints.fea import SoftwoodC24, PoplarViscoelastic
    
    # Simple elastic material
    material = SoftwoodC24()
    
    # Viscoelastic material (MFront)
    material = PoplarViscoelastic()
    mfront_code = material.to_mfront()

Backward Compatibility
---------------------
The original CalculiX-specific API is still available for existing code.
"""

# =============================================================================
# Materials System (NEW)
# =============================================================================
from .materials import (
    # Base classes
    TimberMaterial,
    MaterialModel,
    GrainDirection,
    GrainOrientation,
    ElasticConstants,
    StrengthProperties,
    # Predefined materials
    SoftwoodC24,
    HardwoodD30,
    PoplarViscoelastic,
    CustomTimberMaterial,
    # Common orientations
    BEAM_HORIZONTAL_X,
    POST_VERTICAL_Z,
    BRACE_DIAGONAL,
    # MFront support
    MFrontCompiler,
    MaterialRegistry,
    # Convenience
    get_default_material,
    create_material,
)

# =============================================================================
# Solver Backend System (NEW)
# =============================================================================
from .solver import (
    # Solver types
    SolverType,
    AnalysisType,
    SolverBackend,
    BaseSolverBackend,
    BackendRegistry,
    # Problem definition
    FEAPart,
    ContactPair,
    ContactParameters,
    FixedBC,
    LoadBC,
    DisplacementBC,
    AnalysisProblem,
    # Configuration
    MeshConfig,
    StepConfig,
    OutputConfig,
    AnalysisConfig,
    # Results
    NodeResult,
    ElementResult,
    AnalysisResult,
    # Main entry point
    analyze,
    get_backend,
)

# =============================================================================
# Solver Backends
# =============================================================================
from .backends import (
    CalculiXBackend,
    CodeAsterBackend,
)

# =============================================================================
# Meshing
# =============================================================================
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
    # Mesh visualization and contact detection
    C3D4_FACE_NODE_INDICES,
    build_mesh_faces_compound,
    find_mesh_contact_faces,
)

# =============================================================================
# Visualization
# =============================================================================
from .visualization import (
    read_mesh_elements,
    get_outer_faces,
    build_triangle_compound,
    apply_displacements,
    build_deformed_mesh,
    show_fea_results,
)

# =============================================================================
# Legacy API (for backward compatibility)
# =============================================================================
from .calculix import (
    ContactParameters as LegacyContactParameters,
    StepParameters,
    GrainOrientation as LegacyGrainOrientation,
    TimberMaterial as LegacyTimberMaterial,
    CalculiXInput,
    run_calculix,
    FEAResults,
    read_frd_displacements,
    read_frd_nodes,
    analyze_results,
    BEAM_HORIZONTAL_X as LEGACY_BEAM_HORIZONTAL_X,
    POST_VERTICAL_Z as LEGACY_POST_VERTICAL_Z,
)

from .assembly import (
    FEAPart as LegacyFEAPart,
    ContactPair as LegacyContactPair,
    FixedBC as LegacyFixedBC,
    LoadBC as LegacyLoadBC,
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
    "C3D4_FACE_NODE_INDICES",
    "build_mesh_faces_compound",
    "find_mesh_contact_faces",
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
