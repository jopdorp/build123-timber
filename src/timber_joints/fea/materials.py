"""Material definitions with MFront support.

This module provides timber material definitions that can be:
1. Used directly with simple elastic properties
2. Exported to MFront format for advanced constitutive models
3. Wrapped as UMAT for use with various FEA solvers

MFront materials support:
- Orthotropic elasticity (grain direction dependent)
- Viscoelastic behavior (creep, relaxation)
- Moisture-dependent properties
- Temperature effects

Example::

    # Simple elastic material
    material = TimberMaterial.c24_softwood()
    
    # MFront viscoelastic material
    material = PoplarViscoelastic()
    mfront_code = material.to_mfront()
    
    # Use with a member
    beam = Beam(length=3000, width=150, height=150)
    beam.material = material
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Dict, Any, List
import subprocess


class MaterialModel(Enum):
    """Type of constitutive model."""
    ELASTIC = auto()           # Linear elastic orthotropic
    VISCOELASTIC = auto()      # Generalized Maxwell model
    MOISTURE_DEPENDENT = auto() # Properties vary with moisture content
    DAMAGE = auto()            # Progressive damage model


class GrainDirection(Enum):
    """Material principal directions for wood."""
    LONGITUDINAL = "L"   # Along the grain (fiber direction)
    RADIAL = "R"         # Perpendicular to grain, toward center
    TANGENTIAL = "T"     # Perpendicular to grain, tangent to rings


@dataclass
class GrainOrientation:
    """Material orientation for orthotropic wood grain direction.
    
    Defines the grain direction in global coordinates using two vectors:
    - a_vector: Primary axis (grain/longitudinal direction)
    - b_vector: Secondary axis for orientation plane
    
    The material coordinate system is:
    - Axis 1 (L): a_vector direction (grain)
    - Axis 2 (R): perpendicular to a in the a-b plane
    - Axis 3 (T): perpendicular to both (a × b)
    """
    name: str
    a_vector: tuple[float, float, float]  # Grain direction
    b_vector: tuple[float, float, float]  # Orientation reference


# Common orientations for timber elements
BEAM_HORIZONTAL_X = GrainOrientation(
    name="BEAM_ORIENT",
    a_vector=(1.0, 0.0, 0.0),  # Grain along X
    b_vector=(0.0, 1.0, 0.0),
)

POST_VERTICAL_Z = GrainOrientation(
    name="POST_ORIENT",
    a_vector=(0.0, 0.0, 1.0),  # Grain along Z (vertical)
    b_vector=(1.0, 0.0, 0.0),
)

BRACE_DIAGONAL = GrainOrientation(
    name="BRACE_ORIENT",
    a_vector=(0.707, 0.0, 0.707),  # 45° diagonal
    b_vector=(0.0, 1.0, 0.0),
)


@dataclass
class ElasticConstants:
    """Orthotropic elastic constants for timber.
    
    All moduli in MPa. Convention follows wood science notation:
    - L: Longitudinal (along grain)
    - R: Radial (perpendicular, toward pith)
    - T: Tangential (perpendicular, along rings)
    """
    # Young's moduli [MPa]
    E_L: float   # Longitudinal
    E_R: float   # Radial
    E_T: float   # Tangential
    
    # Shear moduli [MPa]
    G_LR: float  # LR plane
    G_LT: float  # LT plane
    G_RT: float  # RT plane
    
    # Poisson's ratios (dimensionless)
    nu_LR: float  # Strain in R from stress in L
    nu_LT: float  # Strain in T from stress in L
    nu_RT: float  # Strain in T from stress in R


@dataclass
class StrengthProperties:
    """Characteristic strength values for timber (EN 338).
    
    All values in MPa. Subscripts:
    - m: bending
    - t: tension
    - c: compression
    - v: shear
    - 0: parallel to grain
    - 90: perpendicular to grain
    - k: characteristic (5th percentile)
    """
    f_m_k: float = 0.0      # Bending strength
    f_t_0_k: float = 0.0    # Tension parallel to grain
    f_t_90_k: float = 0.0   # Tension perpendicular to grain
    f_c_0_k: float = 0.0    # Compression parallel to grain
    f_c_90_k: float = 0.0   # Compression perpendicular to grain
    f_v_k: float = 0.0      # Shear strength


class TimberMaterial(ABC):
    """Base class for timber materials.
    
    All materials must provide:
    - name: Identifier for the material
    - elastic: Elastic constants
    - density: Material density in kg/m³
    - model_type: Type of constitutive model
    
    Materials can optionally provide:
    - strength: Strength properties for design checks
    - to_mfront(): Export as MFront behavior
    - to_umat(): Export as UMAT subroutine
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Material identifier."""
        pass
    
    @property
    @abstractmethod
    def elastic(self) -> ElasticConstants:
        """Elastic constants."""
        pass
    
    @property
    @abstractmethod
    def density(self) -> float:
        """Density in kg/m³."""
        pass
    
    @property
    def model_type(self) -> MaterialModel:
        """Type of constitutive model (default: elastic)."""
        return MaterialModel.ELASTIC
    
    @property
    def strength(self) -> Optional[StrengthProperties]:
        """Strength properties (optional)."""
        return None
    
    def to_mfront(self) -> str:
        """Export material as MFront behavior definition."""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support MFront export"
        )
    
    def to_calculix_material(self) -> List[str]:
        """Generate CalculiX material definition lines."""
        e = self.elastic
        lines = [
            f"*MATERIAL, NAME={self.name}",
            "*ELASTIC, TYPE=ENGINEERING CONSTANTS",
            f"{e.E_L}, {e.E_R}, {e.E_T}, "
            f"{e.nu_LR}, {e.nu_LT}, {e.nu_RT}, "
            f"{e.G_LR}, {e.G_LT},",
            f"{e.G_RT}, 0.0",
            "*DENSITY",
            f"{self.density * 1e-9:.6e}",  # Convert kg/m³ to Mg/mm³
        ]
        return lines


@dataclass
class SoftwoodC24(TimberMaterial):
    """C24 structural softwood (EN 338).
    
    Common grade for structural timber in Europe.
    Properties represent typical spruce/pine/fir.
    """
    
    @property
    def name(self) -> str:
        return "C24_Softwood"
    
    @property
    def elastic(self) -> ElasticConstants:
        return ElasticConstants(
            E_L=11000.0,   # Along grain
            E_R=370.0,     # Radial
            E_T=370.0,     # Tangential
            G_LR=690.0,
            G_LT=690.0,
            G_RT=50.0,
            nu_LR=0.37,
            nu_LT=0.42,
            nu_RT=0.47,
        )
    
    @property
    def density(self) -> float:
        return 350.0  # kg/m³ (characteristic)
    
    @property
    def strength(self) -> StrengthProperties:
        return StrengthProperties(
            f_m_k=24.0,
            f_t_0_k=14.0,
            f_t_90_k=0.5,
            f_c_0_k=21.0,
            f_c_90_k=2.5,
            f_v_k=4.0,
        )


@dataclass
class HardwoodD30(TimberMaterial):
    """D30 structural hardwood (EN 338).
    
    Common grade for structural hardwood (oak, beech, ash).
    """
    
    @property
    def name(self) -> str:
        return "D30_Hardwood"
    
    @property
    def elastic(self) -> ElasticConstants:
        return ElasticConstants(
            E_L=10000.0,
            E_R=640.0,
            E_T=420.0,
            G_LR=600.0,
            G_LT=600.0,
            G_RT=60.0,
            nu_LR=0.37,
            nu_LT=0.50,
            nu_RT=0.67,
        )
    
    @property
    def density(self) -> float:
        return 530.0
    
    @property
    def strength(self) -> StrengthProperties:
        return StrengthProperties(
            f_m_k=30.0,
            f_t_0_k=18.0,
            f_t_90_k=0.6,
            f_c_0_k=23.0,
            f_c_90_k=8.0,
            f_v_k=3.0,
        )


@dataclass
class PoplarViscoelastic(TimberMaterial):
    """Poplar with orthotropic viscoelastic behavior.
    
    Based on: Simo et al. 2021 - "Using MFront as a Wrapper"
    Implements a generalized Maxwell model with 3 branches for
    time-dependent creep behavior.
    
    This material captures:
    - Orthotropic elastic response
    - Viscoelastic creep under sustained load
    - Stress relaxation
    """
    # Number of Maxwell branches
    num_branches: int = 3
    
    # Viscoelastic Young's moduli for each branch [MPa]
    # Index: [branch][direction L/R/T]
    Ev: List[tuple[float, float, float]] = field(default_factory=lambda: [
        (66.0, 75.0, 97.0),    # Branch 1
        (329.0, 220.0, 384.0), # Branch 2
        (37.0, 22.0, 66.0),    # Branch 3
    ])
    
    # Viscoelastic shear moduli [MPa]
    # Index: [branch][LR/RT/LT]
    Gv: List[tuple[float, float, float]] = field(default_factory=lambda: [
        (66.0, 40.0, 3.0),   # Branch 1
        (57.0, 36.0, 2.0),   # Branch 2
        (57.0, 35.0, 2.0),   # Branch 3
    ])
    
    # Characteristic times [seconds]
    tau: List[float] = field(default_factory=lambda: [100.0, 1000.0, 10000.0])
    
    @property
    def name(self) -> str:
        return "Poplar_Viscoelastic"
    
    @property
    def elastic(self) -> ElasticConstants:
        """Instantaneous elastic constants (E_infinity in Maxwell model)."""
        return ElasticConstants(
            E_L=10285.0,  # Longitudinal
            E_R=635.0,    # Radial
            E_T=369.0,    # Tangential
            G_LR=786.0,
            G_LT=838.0,
            G_RT=114.0,
            nu_LR=0.029,
            nu_LT=0.42,
            nu_RT=0.165,
        )
    
    @property
    def density(self) -> float:
        return 400.0  # Poplar density kg/m³
    
    @property
    def model_type(self) -> MaterialModel:
        return MaterialModel.VISCOELASTIC
    
    def to_mfront(self) -> str:
        """Generate MFront behavior definition.
        
        Based on PoplarOrthotropicGeneralizedMaxwell_2021.mfront from MFrontGallery.
        """
        e = self.elastic
        
        mfront = f'''@DSL DefaultDSL;
@Material Poplar;
@Behaviour OrthotropicGeneralizedMaxwell;
@Author timber_joints (based on Simo et al. 2021);
@Description {{
  "Orthotropic viscoelastic behavior for Poplar wood"
  "Generalized Maxwell model with {self.num_branches} branches"
}}

@StrainMeasure Hencky;
@OrthotropicBehaviour<Pipe>;
@AbaqusOrthotropyManagementPolicy[abaqus, abaqus_explicit] MFront;

// Instantaneous elastic stiffness tensor
@ComputeStiffnessTensor{{{e.E_R}, {e.E_L}, {e.E_T},
                         {e.nu_LR}, {e.nu_LT}, {e.nu_RT},
                         {e.G_LR}, {e.G_LT}, {e.G_RT}}};

@IntegerConstant Nv = {self.num_branches};

// Viscoelastic Young's moduli for each branch
'''
        # Add viscoelastic parameters
        for i, direction in enumerate(["1", "2", "3"]):
            values = [branch[i] for branch in self.Ev]
            values_str = ", ".join(f"{v}" for v in values)
            mfront += f'@Parameter stress Ev{direction}[Nv] = {{{values_str}}};\n'
            mfront += f'Ev{direction}.setEntryName("ViscoelasticYoungModulus{direction}");\n'
        
        # Viscoelastic Poisson ratios (typically zero for wood)
        for pair in ["12", "23", "13"]:
            mfront += f'@Parameter real nuv{pair}[Nv] = {{0, 0, 0}};\n'
            mfront += f'nuv{pair}.setEntryName("ViscoelasticPoissonRatio{pair}");\n'
        
        # Viscoelastic shear moduli
        for i, pair in enumerate(["12", "23", "13"]):
            values = [branch[i] for branch in self.Gv]
            values_str = ", ".join(f"{v}" for v in values)
            mfront += f'@Parameter stress Gv{pair}[Nv] = {{{values_str}}};\n'
            mfront += f'Gv{pair}.setEntryName("ViscoelasticShearModulus{pair}");\n'
        
        # Characteristic times
        tau_str = ", ".join(f"{t}" for t in self.tau)
        mfront += f'''
@Parameter time tau[Nv] = {{{tau_str}}};
tau.setEntryName("CharacteristicTime");

@Import "OrthotropicGeneralizedMaxwell-core.mfront";
'''
        return mfront


@dataclass
class CustomTimberMaterial(TimberMaterial):
    """User-defined timber material with custom properties."""
    _name: str = "Custom_Timber"
    _elastic: ElasticConstants = None
    _density: float = 500.0
    _strength: Optional[StrengthProperties] = None
    
    def __post_init__(self):
        if self._elastic is None:
            # Default to C24-like properties
            self._elastic = ElasticConstants(
                E_L=11000.0, E_R=370.0, E_T=370.0,
                G_LR=690.0, G_LT=690.0, G_RT=50.0,
                nu_LR=0.37, nu_LT=0.42, nu_RT=0.47,
            )
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def elastic(self) -> ElasticConstants:
        return self._elastic
    
    @property
    def density(self) -> float:
        return self._density
    
    @property
    def strength(self) -> Optional[StrengthProperties]:
        return self._strength


# =============================================================================
# MFront Compilation and UMAT Support
# =============================================================================

@dataclass
class MFrontCompiler:
    """Compiler for MFront material behaviors.
    
    Compiles .mfront files to shared libraries that can be used as
    UMAT subroutines with CalculiX, Code_Aster, or Abaqus.
    """
    mfront_path: str = "mfront"  # Path to mfront executable
    output_dir: Path = field(default_factory=lambda: Path("./mfront_output"))
    
    def compile(
        self,
        material: TimberMaterial,
        interface: str = "calculix",
    ) -> Path:
        """Compile material to shared library.
        
        Args:
            material: Material with MFront support
            interface: Target FEA solver interface
                      ('calculix', 'aster', 'abaqus', 'ansys')
        
        Returns:
            Path to compiled shared library
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write MFront source
        mfront_source = material.to_mfront()
        source_file = self.output_dir / f"{material.name}.mfront"
        source_file.write_text(mfront_source)
        
        # Compile with MFront
        interface_map = {
            "calculix": "calculix",
            "aster": "aster",
            "abaqus": "abaqus",
            "ansys": "ansys",
        }
        
        if interface not in interface_map:
            raise ValueError(f"Unknown interface: {interface}")
        
        cmd = [
            self.mfront_path,
            "--obuild",
            f"--interface={interface_map[interface]}",
            str(source_file),
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.output_dir,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            raise RuntimeError(
                f"MFront compilation failed:\n{result.stderr}"
            )
        
        # Return path to library
        lib_name = f"lib{material.name}.so"
        return self.output_dir / "src" / lib_name
    
    def is_available(self) -> bool:
        """Check if MFront is installed and available."""
        try:
            result = subprocess.run(
                [self.mfront_path, "--version"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False


# =============================================================================
# Material Registry
# =============================================================================

class MaterialRegistry:
    """Registry of available timber materials.
    
    Provides easy access to predefined materials and allows
    registration of custom materials.
    """
    _materials: Dict[str, type] = {}
    
    @classmethod
    def register(cls, material_class: type):
        """Register a material class."""
        instance = material_class()
        cls._materials[instance.name] = material_class
        return material_class
    
    @classmethod
    def get(cls, name: str) -> TimberMaterial:
        """Get a material by name."""
        if name not in cls._materials:
            raise KeyError(f"Unknown material: {name}")
        return cls._materials[name]()
    
    @classmethod
    def list_materials(cls) -> List[str]:
        """List all registered materials."""
        return list(cls._materials.keys())


# Register default materials
MaterialRegistry.register(SoftwoodC24)
MaterialRegistry.register(HardwoodD30)
MaterialRegistry.register(PoplarViscoelastic)


# =============================================================================
# Convenience Functions
# =============================================================================

def get_default_material() -> TimberMaterial:
    """Get the default timber material (C24 softwood)."""
    return SoftwoodC24()


def create_material(
    name: str,
    E_L: float,
    E_R: float,
    E_T: float,
    G_LR: float,
    G_LT: float,
    G_RT: float,
    nu_LR: float,
    nu_LT: float,
    nu_RT: float,
    density: float,
) -> TimberMaterial:
    """Create a custom elastic timber material."""
    return CustomTimberMaterial(
        _name=name,
        _elastic=ElasticConstants(
            E_L=E_L, E_R=E_R, E_T=E_T,
            G_LR=G_LR, G_LT=G_LT, G_RT=G_RT,
            nu_LR=nu_LR, nu_LT=nu_LT, nu_RT=nu_RT,
        ),
        _density=density,
    )
