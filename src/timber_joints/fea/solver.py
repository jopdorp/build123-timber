"""Solver backend abstraction for FEA analysis.

This module defines the protocol for FEA solver backends, allowing
the same analysis setup to run on different solvers (CalculiX, Code_Aster, etc.)
without code changes.

The architecture separates:
1. Problem definition (geometry, materials, BCs) - solver-independent
2. Solver input generation - backend-specific
3. Solver execution - backend-specific
4. Results parsing - backend-specific

Example::

    from timber_joints.fea import CalculiXBackend, CodeAsterBackend
    
    # Configure analysis once
    config = AnalysisConfig(...)
    problem = AnalysisProblem(parts, contacts, bcs)
    
    # Run with CalculiX
    result_ccx = CalculiXBackend().solve(problem, config)
    
    # Run with Code_Aster (same problem definition)
    result_aster = CodeAsterBackend().solve(problem, config)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Protocol, List, Dict, Optional, Callable, runtime_checkable

from build123d import Part

from .materials import TimberMaterial, GrainOrientation, get_default_material


# =============================================================================
# Solver Types
# =============================================================================

class SolverType(Enum):
    """Available FEA solver backends."""
    CALCULIX = auto()
    CODE_ASTER = auto()
    # Future: ABAQUS, ANSYS, FENICS, etc.


class AnalysisType(Enum):
    """Type of structural analysis."""
    STATIC = auto()           # Static equilibrium
    QUASI_STATIC = auto()     # Time-dependent with inertia neglected
    DYNAMIC = auto()          # Full dynamic analysis
    MODAL = auto()            # Eigenvalue/natural frequencies
    BUCKLING = auto()         # Linear buckling


# =============================================================================
# Problem Definition (Solver-Independent)
# =============================================================================

@dataclass
class FEAPart:
    """A part for FEA analysis with material and orientation."""
    name: str
    shape: Part
    orientation: GrainOrientation
    material: Optional[TimberMaterial] = None


@dataclass 
class ContactPair:
    """Contact between two parts."""
    name: str
    part_a: str  # Slave surface
    part_b: str  # Master surface


@dataclass
class ContactParameters:
    """Parameters for frictional contact.
    
    For timber joints with contact regions.
    Default values derived from central config.
    """
    friction_coeff: float = 0.35
    normal_penalty: float = 100.0    # MPa/mm - stiffer contact
    stick_slope: float = 100.0       # Match normal_penalty
    stabilize: float = 0.01          # Low stabilization - let contact converge naturally
    adjust: float = None             # mm - adjustment distance (from config if None)
    
    def __post_init__(self):
        # Small ADJUST needed to establish initial contact, but keep it minimal
        # to avoid artificial strain. Derived from mortise clearance.
        if self.adjust is None:
            from timber_joints.config import DEFAULT_CONFIG
            self.adjust = DEFAULT_CONFIG.contact_adjust


# Node filter function signature
NodeFilter = Callable[[int, float, float, float, str, "CombinedMesh"], bool]


@dataclass
class FixedBC:
    """Fixed (zero displacement) boundary condition."""
    name: str
    node_filter: NodeFilter
    dofs: tuple[int, ...] = (1, 2, 3)  # Default: fix all DOFs


@dataclass
class LoadBC:
    """Concentrated load boundary condition."""
    name: str
    node_filter: NodeFilter
    dof: int  # 1=X, 2=Y, 3=Z
    total_load: float


@dataclass
class DisplacementBC:
    """Prescribed displacement boundary condition."""
    name: str
    node_filter: NodeFilter
    dof: int
    value: float


@dataclass
class AnalysisProblem:
    """Complete problem definition for FEA analysis."""
    parts: List[FEAPart]
    contacts: List[ContactPair] = field(default_factory=list)
    fixed_bcs: List[FixedBC] = field(default_factory=list)
    load_bcs: List[LoadBC] = field(default_factory=list)
    displacement_bcs: List[DisplacementBC] = field(default_factory=list)


# =============================================================================
# Analysis Configuration
# =============================================================================

@dataclass
class MeshConfig:
    """Mesh generation configuration."""
    element_size: float = 50.0        # Base element size (mm)
    element_size_fine: float = 20.0   # Fine mesh at contacts (mm)
    refinement_margin: float = 10.0   # Expand refinement regions (mm)
    element_type: str = "C3D10"       # Default: 10-node tetrahedral


@dataclass
class StepConfig:
    """Analysis step configuration.
    
    For contact problems - moderate increments for stability.
    """
    initial_increment: float = 0.2   # Start with 20% of load
    total_time: float = 1.0
    min_increment: float = 0.01     # Allow very small increments if needed
    max_increment: float = 0.5       # Larger steps to reach ~5 increments
    max_increments: int = 100        # Enough increments
    nonlinear_geometry: bool = True


@dataclass
class OutputConfig:
    """Output request configuration."""
    displacements: bool = True
    stresses: bool = True
    strains: bool = True
    reaction_forces: bool = True
    contact_output: bool = True


@dataclass
class AnalysisConfig:
    """Complete analysis configuration."""
    analysis_type: AnalysisType = AnalysisType.STATIC
    
    # Default material (used if part has no material assigned)
    default_material: TimberMaterial = None
    
    # Contact parameters
    contact: ContactParameters = None
    contact_gap: float = None  # mm, from central config
    
    # Mesh settings
    mesh: MeshConfig = None
    
    # Step settings
    step: StepConfig = None
    
    # Output settings
    output: OutputConfig = None
    
    # Working directory
    output_dir: Path = None
    
    def __post_init__(self):
        from ..config import DEFAULT_CONFIG
        if self.default_material is None:
            self.default_material = get_default_material()
        if self.contact is None:
            self.contact = ContactParameters()
        if self.contact_gap is None:
            self.contact_gap = DEFAULT_CONFIG.contact_gap
        if self.mesh is None:
            self.mesh = MeshConfig()
        if self.step is None:
            self.step = StepConfig()
        if self.output is None:
            self.output = OutputConfig()
        if self.output_dir is None:
            self.output_dir = Path("./fea_output")


# =============================================================================
# Results (Solver-Independent)
# =============================================================================

@dataclass
class NodeResult:
    """Results at a single node."""
    node_id: int
    x: float
    y: float
    z: float
    displacement: tuple[float, float, float] = (0.0, 0.0, 0.0)
    reaction_force: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class ElementResult:
    """Results for a single element."""
    element_id: int
    stress: tuple[float, ...] = None  # (S11, S22, S33, S12, S23, S13)
    strain: tuple[float, ...] = None


@dataclass
class AnalysisResult:
    """Results from FEA analysis."""
    success: bool
    solver_type: SolverType
    
    # Displacement results
    max_displacement: float = 0.0
    max_displacement_x: float = 0.0
    max_displacement_y: float = 0.0
    max_displacement_z: float = 0.0
    
    # Node results (optional, can be large)
    node_displacements: Dict[int, tuple[float, float, float]] = field(default_factory=dict)
    node_reactions: Dict[int, tuple[float, float, float]] = field(default_factory=dict)
    
    # Stress results (optional)
    max_stress: float = 0.0
    max_von_mises: float = 0.0
    
    # File paths
    input_file: Optional[Path] = None
    results_file: Optional[Path] = None
    mesh_file: Optional[Path] = None
    
    # Error information
    error_message: str = ""
    solver_output: str = ""
    
    @property
    def max_deflection(self) -> float:
        """Alias for max_displacement."""
        return self.max_displacement


# =============================================================================
# Solver Backend Protocol
# =============================================================================

@runtime_checkable
class SolverBackend(Protocol):
    """Protocol for FEA solver backends.
    
    Implementations must provide:
    - solver_type: Identifier for this solver
    - is_available(): Check if solver is installed
    - solve(): Run analysis and return results
    """
    
    @property
    def solver_type(self) -> SolverType:
        """Return the solver type identifier."""
        ...
    
    def is_available(self) -> bool:
        """Check if this solver is available on the system."""
        ...
    
    def solve(
        self,
        problem: AnalysisProblem,
        config: AnalysisConfig,
        verbose: bool = True,
    ) -> AnalysisResult:
        """Run analysis and return results.
        
        Args:
            problem: The analysis problem definition
            config: Analysis configuration
            verbose: Print progress information
            
        Returns:
            AnalysisResult with displacements, stresses, etc.
        """
        ...


class BaseSolverBackend(ABC):
    """Base class for solver backends with common functionality."""
    
    @property
    @abstractmethod
    def solver_type(self) -> SolverType:
        """Return the solver type identifier."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this solver is available."""
        pass
    
    @abstractmethod
    def solve(
        self,
        problem: AnalysisProblem,
        config: AnalysisConfig,
        verbose: bool = True,
    ) -> AnalysisResult:
        """Run analysis and return results."""
        pass
    
    def _ensure_output_dir(self, config: AnalysisConfig) -> Path:
        """Create output directory if needed."""
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir


# =============================================================================
# Backend Registry
# =============================================================================

class BackendRegistry:
    """Registry of available solver backends."""
    _backends: Dict[SolverType, type] = {}
    _default: Optional[SolverType] = None
    
    @classmethod
    def register(cls, backend_class: type):
        """Register a solver backend class."""
        instance = backend_class()
        cls._backends[instance.solver_type] = backend_class
        if cls._default is None:
            cls._default = instance.solver_type
        return backend_class
    
    @classmethod
    def get(cls, solver_type: SolverType) -> SolverBackend:
        """Get a backend instance by type."""
        if solver_type not in cls._backends:
            raise KeyError(f"Unknown solver backend: {solver_type}")
        return cls._backends[solver_type]()
    
    @classmethod
    def get_default(cls) -> SolverBackend:
        """Get the default solver backend."""
        if cls._default is None:
            raise RuntimeError("No solver backends registered")
        return cls.get(cls._default)
    
    @classmethod
    def set_default(cls, solver_type: SolverType):
        """Set the default solver backend."""
        if solver_type not in cls._backends:
            raise KeyError(f"Unknown solver backend: {solver_type}")
        cls._default = solver_type
    
    @classmethod
    def list_backends(cls) -> List[SolverType]:
        """List all registered backends."""
        return list(cls._backends.keys())
    
    @classmethod
    def available_backends(cls) -> List[SolverType]:
        """List backends that are currently available."""
        return [
            st for st in cls._backends
            if cls._backends[st]().is_available()
        ]


# =============================================================================
# Convenience Functions
# =============================================================================

def get_backend(solver_type: Optional[SolverType] = None) -> SolverBackend:
    """Get a solver backend.
    
    Args:
        solver_type: Specific solver to use, or None for default
        
    Returns:
        SolverBackend instance
    """
    if solver_type is None:
        return BackendRegistry.get_default()
    return BackendRegistry.get(solver_type)


def analyze(
    problem: AnalysisProblem,
    config: Optional[AnalysisConfig] = None,
    backend: Optional[SolverType] = None,
    verbose: bool = True,
) -> AnalysisResult:
    """Run FEA analysis using the specified (or default) backend.
    
    This is the main entry point for running analyses.
    
    Args:
        problem: Analysis problem definition
        config: Analysis configuration (uses defaults if None)
        backend: Solver backend to use (uses default if None)
        verbose: Print progress
        
    Returns:
        AnalysisResult
        
    Example::
    
        problem = AnalysisProblem(parts=[...], contacts=[...], ...)
        result = analyze(problem)  # Uses default backend
        
        # Or specify a backend
        result = analyze(problem, backend=SolverType.CODE_ASTER)
    """
    if config is None:
        config = AnalysisConfig()
    
    solver = get_backend(backend)
    
    if not solver.is_available():
        return AnalysisResult(
            success=False,
            solver_type=solver.solver_type,
            error_message=f"Solver {solver.solver_type.name} is not available",
        )
    
    return solver.solve(problem, config, verbose)
