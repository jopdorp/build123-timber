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
    GIRT_HORIZONTAL_Y,
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
    # Two-pass meshing with contact refinement
    ContactDefinition,
    MeshingConfig,
    MeshingResult,
    mesh_parts_with_contact_refinement,
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
    show_fea_results_colormap,
    value_to_rainbow_color,
    build_force_arrow,
    read_load_info,
    save_load_info,
)

# =============================================================================
# CalculiX Backend Utilities
# =============================================================================
from .backends.calculix import (
    CalculiXInput,
    run_ccx,
    read_frd_displacements,
    read_frd_nodes,
    read_frd_stresses,
    compute_von_mises,
)

from .assembly import (
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
    # Materials
    "TimberMaterial",
    "MaterialModel",
    "GrainDirection",
    "GrainOrientation",
    "ElasticConstants",
    "StrengthProperties",
    "SoftwoodC24",
    "HardwoodD30",
    "PoplarViscoelastic",
    "CustomTimberMaterial",
    "BEAM_HORIZONTAL_X",
    "GIRT_HORIZONTAL_Y",
    "POST_VERTICAL_Z",
    "BRACE_DIAGONAL",
    "MFrontCompiler",
    "MaterialRegistry",
    "get_default_material",
    "create_material",
    # Solver
    "SolverType",
    "AnalysisType",
    "SolverBackend",
    "BaseSolverBackend",
    "BackendRegistry",
    "FEAPart",
    "ContactPair",
    "ContactParameters",
    "FixedBC",
    "LoadBC",
    "DisplacementBC",
    "AnalysisProblem",
    "MeshConfig",
    "StepConfig",
    "OutputConfig",
    "AnalysisConfig",
    "NodeResult",
    "ElementResult",
    "AnalysisResult",
    "analyze",
    "get_backend",
    # Backends
    "CalculiXBackend",
    "CodeAsterBackend",
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
    "ContactDefinition",
    "MeshingConfig",
    "MeshingResult",
    "mesh_parts_with_contact_refinement",
    # CalculiX utilities
    "CalculiXInput",
    "run_ccx",
    "read_frd_displacements",
    "read_frd_nodes",
    "read_frd_stresses",
    "compute_von_mises",
    # Visualization
    "read_mesh_elements",
    "get_outer_faces",
    "build_triangle_compound",
    "apply_displacements",
    "build_deformed_mesh",
    "show_fea_results",
    "show_fea_results_colormap",
    "value_to_rainbow_color",
    # Assembly API
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
