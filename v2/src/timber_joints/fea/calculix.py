"""CalculiX FEA input generation and solver interface."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import subprocess


@dataclass
class ContactParameters:
    """Parameters for frictional contact between timber surfaces."""
    friction_coeff: float = 0.35  # Wood-on-wood static friction (0.25-0.5 typical)
    normal_penalty: float = 300.0  # Normal contact stiffness (MPa/mm) ≈ E_perpendicular
    stick_slope: float = 300.0  # Tangential penalty stiffness (MPa/mm)
    stabilize: float = 0.01  # Friction stabilization damping
    adjust: float = 1.5  # Contact pair adjustment distance (mm)


@dataclass 
class StepParameters:
    """Parameters for a CalculiX analysis step."""
    initial_increment: float = 0.2
    total_time: float = 1.0
    min_increment: float = 1e-5
    max_increment: float = 0.4
    max_increments: int = 100
    nlgeom: bool = True  # Geometric nonlinearity


@dataclass
class GrainOrientation:
    """Material orientation for orthotropic wood grain direction.
    
    CalculiX *ORIENTATION uses two vectors (a, b) to define material axes:
    - Material axis 1 = a direction (grain/longitudinal)
    - Material axis 2 = a × (b × a), normalized
    - Material axis 3 = a × b, normalized
    """
    name: str
    a_vector: tuple[float, float, float]  # Primary axis (grain direction)
    b_vector: tuple[float, float, float]  # Secondary axis for orientation


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


@dataclass
class TimberMaterial:
    """Orthotropic timber material properties (EN 338).
    
    Default values are for C24 structural softwood.
    All elastic moduli and stresses in MPa.
    """
    name: str = "C24_Softwood"
    
    # Elastic moduli [MPa]
    E_L: float = 11000.0   # Longitudinal (along grain)
    E_R: float = 370.0     # Radial  
    E_T: float = 370.0     # Tangential
    
    # Shear moduli [MPa]
    G_LR: float = 690.0
    G_LT: float = 690.0
    G_RT: float = 50.0
    
    # Poisson's ratios
    nu_LR: float = 0.37
    nu_LT: float = 0.42
    nu_RT: float = 0.47
    
    # Density [kg/m³]
    density: float = 350.0
    
    # Strength values [MPa]
    f_m_k: float = 24.0    # Bending strength
    f_t_0_k: float = 14.0  # Tension parallel to grain
    f_c_0_k: float = 21.0  # Compression parallel to grain
    f_v_k: float = 4.0     # Shear strength


@dataclass
class CalculiXInput:
    """Builder for CalculiX input file."""
    lines: list[str] = field(default_factory=list)
    
    def add_comment(self, text: str):
        """Add a comment line."""
        self.lines.append(f"** {text}")
        return self
    
    def add_blank(self):
        """Add a blank line."""
        self.lines.append("")
        return self
    
    def add_include(self, filename: str):
        """Include another input file."""
        self.lines.append(f"*INCLUDE, INPUT={filename}")
        return self
    
    def add_material(self, material: TimberMaterial):
        """Add orthotropic material definition."""
        self.lines.extend([
            f"*MATERIAL, NAME={material.name}",
            "*ELASTIC, TYPE=ENGINEERING CONSTANTS",
            f"{material.E_L}, {material.E_R}, {material.E_T}, "
            f"{material.nu_LR}, {material.nu_LT}, {material.nu_RT}, "
            f"{material.G_LR}, {material.G_LT},",
            f"{material.G_RT}, 0.0",
            "*DENSITY",
            f"{material.density * 1e-9:.6e}",  # Convert kg/m³ to Mg/mm³
        ])
        return self
    
    def add_orientation(self, orientation: GrainOrientation):
        """Add material orientation for grain direction."""
        ax, ay, az = orientation.a_vector
        bx, by, bz = orientation.b_vector
        self.lines.extend([
            f"*ORIENTATION, NAME={orientation.name}, SYSTEM=RECTANGULAR",
            f"{ax}, {ay}, {az}, {bx}, {by}, {bz}",
        ])
        return self
    
    def add_solid_section(
        self,
        elset: str,
        material: str,
        orientation: Optional[str] = None,
    ):
        """Add solid section assignment."""
        line = f"*SOLID SECTION, ELSET={elset}, MATERIAL={material}"
        if orientation:
            line += f", ORIENTATION={orientation}"
        self.lines.append(line)
        self.lines.append("")  # CalculiX requires blank line after solid section
        return self
    
    def add_surface_interaction(
        self,
        name: str,
        contact: ContactParameters,
        contact_gap: float = 0.5,
    ):
        """Add surface interaction definition for contact."""
        self.lines.extend([
            f"*SURFACE INTERACTION, NAME={name}",
            "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR",
            f"{contact.normal_penalty}, 0.0, {contact_gap}",
            f"*FRICTION, STABILIZE={contact.stabilize}",
            f"{contact.friction_coeff}, {contact.stick_slope}",
        ])
        return self
    
    def add_contact_pair(
        self,
        interaction: str,
        slave_surface: str,
        master_surface: str,
        adjust: float = 1.5,
    ):
        """Add contact pair definition."""
        self.lines.extend([
            f"*CONTACT PAIR, INTERACTION={interaction}, TYPE=SURFACE TO SURFACE, ADJUST={adjust}",
            f"{slave_surface}, {master_surface}",
        ])
        return self
    
    def add_boundary(self, node_ids: list[int], dof_start: int = 1, dof_end: int = 3, value: float = 0.0):
        """Add boundary conditions."""
        self.lines.append("*BOUNDARY")
        for nid in node_ids:
            self.lines.append(f"{nid}, {dof_start}, {dof_end}, {value}")
        return self
    
    def start_step(self, step: StepParameters):
        """Start a new analysis step."""
        nlgeom = ", NLGEOM" if step.nlgeom else ""
        self.lines.extend([
            f"*STEP{nlgeom}, INC={step.max_increments}",
            "*STATIC",
            f"{step.initial_increment}, {step.total_time}, {step.min_increment}, {step.max_increment}",
        ])
        return self
    
    def add_contact_controls(self):
        """Add contact convergence controls."""
        self.lines.extend([
            "*CONTROLS, PARAMETERS=CONTACT",
            "0.005, 0.15, 75, 150",
        ])
        return self
    
    def add_cload(self, node_ids: list[int], dof: int, value: float):
        """Add concentrated loads."""
        self.lines.append("*CLOAD")
        load_per_node = value / len(node_ids) if node_ids else 0
        for nid in node_ids:
            self.lines.append(f"{nid}, {dof}, {load_per_node:.6f}")
        return self
    
    def add_output_requests(self):
        """Add standard output requests."""
        self.lines.extend([
            "*NODE FILE",
            "U, RF",
            "*EL FILE", 
            "S, E",
            "*CONTACT FILE",
            "CDIS, CSTR",
        ])
        return self
    
    def end_step(self):
        """End the current step."""
        self.lines.append("*END STEP")
        return self
    
    def write(self, filepath: str | Path):
        """Write the input file."""
        filepath = Path(filepath)
        with open(filepath, 'w') as f:
            f.write('\n'.join(self.lines))
        return filepath


def run_calculix(
    input_file: str | Path,
    timeout: int = 600,
) -> tuple[bool, str, str]:
    """Run CalculiX solver.
    
    Args:
        input_file: Path to .inp file
        timeout: Maximum solver time in seconds
        
    Returns:
        (success, stdout, stderr)
    """
    input_file = Path(input_file)
    work_dir = input_file.parent
    job_name = input_file.stem
    
    cmd = ["ccx", "-i", job_name]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        success = result.returncode == 0
        return success, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Solver timeout exceeded"
    except FileNotFoundError:
        return False, "", "CalculiX (ccx) not found in PATH"


@dataclass
class FEAResults:
    """Results from CalculiX FEA analysis."""
    max_displacement: float
    max_uz: float  # Z displacement (typically vertical)
    displacements: dict[int, tuple[float, float, float]]  # node_id -> (ux, uy, uz)
    success: bool
    frd_file: Optional[Path] = None
    
    @property
    def max_deflection(self) -> float:
        """Alias for max_displacement."""
        return self.max_displacement


def read_frd_displacements(frd_file: str | Path) -> dict[int, tuple[float, float, float]]:
    """Read displacement results from CalculiX .frd file.
    
    Reads from the LAST DISP block (final increment) in the file.
    Uses fixed-width parsing as per FRD format specification:
    - Column 1-3: record key (e.g., " -1")
    - Column 4-13: node number (10 chars)
    - Column 14-25: value 1 (12 chars)
    - Column 26-37: value 2 (12 chars)
    - Column 38-49: value 3 (12 chars)
    
    Args:
        frd_file: Path to .frd results file
        
    Returns:
        Dictionary of node_id -> (ux, uy, uz)
    """
    frd_file = Path(frd_file)
    
    # Read all lines
    with open(frd_file, 'r') as f:
        lines = f.readlines()
    
    # Find all DISP block starts and their corresponding -3 ends
    disp_blocks = []
    current_start = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith('-4  DISP'):
            current_start = i
        elif line.strip().startswith('-3') and current_start is not None:
            disp_blocks.append((current_start, i))
            current_start = None
    
    if not disp_blocks:
        return {}
    
    # Use the LAST DISP block (final increment)
    start, end = disp_blocks[-1]
    
    displacements = {}
    for i in range(start + 1, end):
        line = lines[i]
        if line.startswith(' -1'):
            try:
                # Fixed-width parsing
                node_id = int(line[3:13])
                ux = float(line[13:25])
                uy = float(line[25:37])
                uz = float(line[37:49])
                displacements[node_id] = (ux, uy, uz)
            except (ValueError, IndexError):
                continue
    
    return displacements


def read_frd_nodes(frd_file: str | Path) -> dict[int, tuple[float, float, float]]:
    """Read node coordinates from CalculiX .frd file.
    
    Uses fixed-width parsing as per FRD format specification:
    - Column 1-3: record key (e.g., " -1")
    - Column 4-13: node number (10 chars)
    - Column 14-25: x coordinate (12 chars)
    - Column 26-37: y coordinate (12 chars)
    - Column 38-49: z coordinate (12 chars)
    
    Args:
        frd_file: Path to .frd results file
        
    Returns:
        Dictionary of node_id -> (x, y, z)
    """
    frd_file = Path(frd_file)
    nodes = {}
    
    with open(frd_file, 'r') as f:
        in_nodes = False
        for line in f:
            if '2C' in line and 'NSET' not in line:
                in_nodes = True
                continue
            elif line.strip().startswith('-3'):
                in_nodes = False
                continue
            
            if in_nodes and line.startswith(' -1'):
                try:
                    # Fixed-width parsing
                    node_id = int(line[3:13])
                    x = float(line[13:25])
                    y = float(line[25:37])
                    z = float(line[37:49])
                    nodes[node_id] = (x, y, z)
                except (ValueError, IndexError):
                    continue
    
    return nodes


def analyze_results(frd_file: str | Path) -> FEAResults:
    """Analyze CalculiX results from .frd file.
    
    Args:
        frd_file: Path to .frd results file
        
    Returns:
        FEAResults with displacement data
    """
    import numpy as np
    
    frd_file = Path(frd_file)
    
    if not frd_file.exists():
        return FEAResults(
            max_displacement=0.0,
            max_uz=0.0,
            displacements={},
            success=False,
        )
    
    displacements = read_frd_displacements(frd_file)
    
    if not displacements:
        return FEAResults(
            max_displacement=0.0,
            max_uz=0.0,
            displacements={},
            success=False,
        )
    
    # Calculate max values
    max_total = 0.0
    max_uz = 0.0
    
    for ux, uy, uz in displacements.values():
        total = np.sqrt(ux**2 + uy**2 + uz**2)
        if total > max_total:
            max_total = total
        if abs(uz) > abs(max_uz):
            max_uz = uz
    
    return FEAResults(
        max_displacement=max_total,
        max_uz=max_uz,
        displacements=displacements,
        success=True,
        frd_file=frd_file,
    )
