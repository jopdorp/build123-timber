"""CalculiX solver backend.

CalculiX is an open-source FEA solver compatible with Abaqus input format.
This backend generates .inp files and runs the ccx solver.

Features:
- Orthotropic material support
- Frictional contact
- Nonlinear geometry
- MFront UMAT integration (when compiled with MFront support)

Requirements:
- CalculiX (ccx) must be in PATH
- For MFront materials: CalculiX compiled with UMAT support
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np

from build123d import export_step

from ..solver import (
    SolverType,
    SolverBackend,
    BaseSolverBackend,
    AnalysisProblem,
    AnalysisConfig,
    AnalysisResult,
    FEAPart,
    ContactPair,
    FixedBC,
    LoadBC,
    BackendRegistry,
)
from ..materials import TimberMaterial, GrainOrientation
from ..meshing import (
    MeshResult,
    CombinedMesh,
    ContactDefinition,
    MeshingConfig,
    MeshingResult,
    mesh_parts_with_contact_refinement,
    write_mesh_inp,
)


@dataclass
class CalculiXInput:
    """Builder for CalculiX input files."""
    lines: List[str] = field(default_factory=list)
    
    def add_comment(self, text: str) -> "CalculiXInput":
        self.lines.append(f"** {text}")
        return self
    
    def add_blank(self) -> "CalculiXInput":
        self.lines.append("")
        return self
    
    def add_include(self, filename: str) -> "CalculiXInput":
        self.lines.append(f"*INCLUDE, INPUT={filename}")
        return self
    
    def add_material(self, material: TimberMaterial) -> "CalculiXInput":
        """Add orthotropic material definition."""
        self.lines.extend(material.to_calculix_material())
        return self
    
    def add_orientation(self, orientation: GrainOrientation) -> "CalculiXInput":
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
    ) -> "CalculiXInput":
        """Add solid section assignment."""
        line = f"*SOLID SECTION, ELSET={elset}, MATERIAL={material}"
        if orientation:
            line += f", ORIENTATION={orientation}"
        self.lines.append(line)
        self.lines.append("")
        return self
    
    def add_surface_interaction(
        self,
        name: str,
        friction_coeff: float,
        normal_penalty: float,
        stick_slope: float,
        stabilize: float,
        contact_gap: float,
    ) -> "CalculiXInput":
        """Add surface interaction for contact."""
        self.lines.extend([
            f"*SURFACE INTERACTION, NAME={name}",
            "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR",
            f"{normal_penalty}, 0.0, {contact_gap}",
            f"*FRICTION, STABILIZE={stabilize}",
            f"{friction_coeff}, {stick_slope}",
        ])
        return self
    
    def add_contact_pair(
        self,
        interaction: str,
        slave_surface: str,
        master_surface: str,
        adjust: float,
    ) -> "CalculiXInput":
        """Add contact pair definition."""
        self.lines.extend([
            f"*CONTACT PAIR, INTERACTION={interaction}, TYPE=SURFACE TO SURFACE, ADJUST={adjust}",
            f"{slave_surface}, {master_surface}",
        ])
        return self
    
    def add_boundary(
        self,
        node_ids: List[int],
        dof_start: int = 1,
        dof_end: int = 3,
        value: float = 0.0,
    ) -> "CalculiXInput":
        """Add boundary conditions."""
        self.lines.append("*BOUNDARY")
        for nid in node_ids:
            self.lines.append(f"{nid}, {dof_start}, {dof_end}, {value}")
        return self
    
    def start_step(
        self,
        initial_inc: float,
        total_time: float,
        min_inc: float,
        max_inc: float,
        max_increments: int,
        nlgeom: bool,
    ) -> "CalculiXInput":
        """Start analysis step."""
        nlgeom_str = ", NLGEOM" if nlgeom else ""
        self.lines.extend([
            f"*STEP{nlgeom_str}, INC={max_increments}",
            "*STATIC",
            f"{initial_inc}, {total_time}, {min_inc}, {max_inc}",
        ])
        return self
    
    def add_contact_controls(self) -> "CalculiXInput":
        """Add contact convergence controls."""
        self.lines.extend([
            "*CONTROLS, PARAMETERS=CONTACT",
            "0.005, 0.15, 75, 150",
        ])
        return self
    
    def add_cload(
        self,
        node_ids: List[int],
        dof: int,
        total_load: float,
    ) -> "CalculiXInput":
        """Add concentrated loads distributed over nodes."""
        if not node_ids:
            return self
        self.lines.append("*CLOAD")
        load_per_node = total_load / len(node_ids)
        for nid in node_ids:
            self.lines.append(f"{nid}, {dof}, {load_per_node:.6f}")
        return self
    
    def add_output_requests(self) -> "CalculiXInput":
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
    
    def end_step(self) -> "CalculiXInput":
        """End the current step."""
        self.lines.append("*END STEP")
        return self
    
    def write(self, filepath: Path) -> Path:
        """Write the input file."""
        filepath = Path(filepath)
        with open(filepath, 'w') as f:
            f.write('\n'.join(self.lines))
        return filepath


def run_ccx(
    input_file: Path,
    timeout: int = 600,
) -> tuple[bool, str, str]:
    """Run CalculiX solver.
    
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


def read_frd_displacements(frd_file: Path) -> Dict[int, tuple[float, float, float]]:
    """Read displacement results from CalculiX .frd file.
    
    Reads from the LAST DISP block (final increment).
    """
    frd_file = Path(frd_file)
    
    with open(frd_file, 'r') as f:
        lines = f.readlines()
    
    # Find all DISP blocks
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
    
    # Use last DISP block
    start, end = disp_blocks[-1]
    
    displacements = {}
    for i in range(start + 1, end):
        line = lines[i]
        if line.startswith(' -1'):
            try:
                node_id = int(line[3:13])
                ux = float(line[13:25])
                uy = float(line[25:37])
                uz = float(line[37:49])
                displacements[node_id] = (ux, uy, uz)
            except (ValueError, IndexError):
                continue
    
    return displacements


def read_frd_nodes(frd_file: Path) -> Dict[int, tuple[float, float, float]]:
    """Read node coordinates from CalculiX .frd file."""
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
                    node_id = int(line[3:13])
                    x = float(line[13:25])
                    y = float(line[25:37])
                    z = float(line[37:49])
                    nodes[node_id] = (x, y, z)
                except (ValueError, IndexError):
                    continue
    
    return nodes


@BackendRegistry.register
class CalculiXBackend(BaseSolverBackend):
    """CalculiX FEA solver backend."""
    
    @property
    def solver_type(self) -> SolverType:
        return SolverType.CALCULIX
    
    def is_available(self) -> bool:
        """Check if CalculiX is installed."""
        try:
            result = subprocess.run(
                ["ccx", "-v"],
                capture_output=True,
                text=True,
            )
            return True  # ccx -v returns non-zero but that's OK
        except FileNotFoundError:
            return False
    
    def solve(
        self,
        problem: AnalysisProblem,
        config: AnalysisConfig,
        verbose: bool = True,
    ) -> AnalysisResult:
        """Run CalculiX analysis."""
        output_dir = self._ensure_output_dir(config)
        
        # Export parts to STEP
        step_files = {}
        for part in problem.parts:
            step_file = output_dir / f"{part.name.lower()}.step"
            export_step(part.shape, str(step_file))
            step_files[part.name] = str(step_file)
        
        # Mesh parts with contact refinement
        if verbose:
            print("Meshing parts...")
        
        contacts = [
            ContactDefinition(name=c.name, part_a=c.part_a, part_b=c.part_b)
            for c in problem.contacts
        ]
        mesh_config = MeshingConfig(
            element_size=config.mesh.element_size,
            element_size_fine=config.mesh.element_size_fine,
            refinement_margin=config.mesh.refinement_margin,
            contact_gap=config.contact_gap,
        )
        
        meshing_result = mesh_parts_with_contact_refinement(
            step_files, contacts, mesh_config, verbose
        )
        
        # Write mesh file
        mesh_file = output_dir / "mesh.inp"
        write_mesh_inp(meshing_result.combined, mesh_file, meshing_result.contact_surfaces)
        
        # Apply boundary conditions
        bc_node_lists = self._apply_boundary_conditions(
            problem, config, meshing_result.meshes, meshing_result.combined, verbose
        )
        
        # Generate CalculiX input
        input_file = self._generate_input(
            problem, config, meshing_result.combined, meshing_result.contact_surfaces, 
            bc_node_lists, output_dir
        )
        
        # Run solver
        if verbose:
            print("\nRunning CalculiX solver...")
        
        success, stdout, stderr = run_ccx(input_file)
        
        if verbose:
            print(stdout)
            if stderr:
                print(f"STDERR: {stderr}")
        
        # Parse results
        return self._parse_results(success, output_dir, stdout, stderr, mesh_file, input_file)
    
    def _apply_boundary_conditions(
        self,
        problem: AnalysisProblem,
        config: AnalysisConfig,
        fine_meshes: Dict[str, MeshResult],
        combined: CombinedMesh,
        verbose: bool,
    ) -> Dict[str, List[int]]:
        """Apply boundary conditions and return node lists."""
        bc_node_lists = {}
        
        # Build node to part mapping
        node_to_part = {}
        for part_name, offset in combined.node_offsets.items():
            mesh = fine_meshes[part_name]
            for orig_nid in mesh.nodes.keys():
                node_to_part[orig_nid + offset] = part_name
        
        all_bcs = problem.fixed_bcs + problem.load_bcs
        
        for bc in all_bcs:
            nodes = []
            for nid, (x, y, z) in combined.nodes.items():
                part_name = node_to_part.get(nid, "")
                if bc.node_filter(nid, x, y, z, part_name, combined):
                    nodes.append(nid)
            bc_node_lists[bc.name] = nodes
            if verbose:
                print(f"  BC '{bc.name}': {len(nodes)} nodes")
        
        return bc_node_lists
    
    def _generate_input(
        self,
        problem: AnalysisProblem,
        config: AnalysisConfig,
        combined: CombinedMesh,
        contact_surfaces: Dict[str, List],
        bc_node_lists: Dict[str, List[int]],
        output_dir: Path,
    ) -> Path:
        """Generate CalculiX input file."""
        ccx = CalculiXInput()
        
        ccx.add_comment("CalculiX Analysis")
        ccx.add_comment("Generated by timber_joints.fea")
        ccx.add_blank()
        
        ccx.add_include("mesh.inp")
        ccx.add_blank()
        
        # Materials
        materials_added = set()
        for part in problem.parts:
            material = part.material or config.default_material
            if material.name not in materials_added:
                ccx.add_material(material)
                materials_added.add(material.name)
        ccx.add_blank()
        
        # Orientations and sections
        ccx.add_comment("Part orientations and sections")
        for part in problem.parts:
            ccx.add_orientation(part.orientation)
            material = part.material or config.default_material
            ccx.add_solid_section(part.name, material.name, part.orientation.name)
        ccx.add_blank()
        
        # Contact
        if problem.contacts:
            ccx.add_comment("Contact interaction")
            contact_cfg = config.contact
            ccx.add_surface_interaction(
                "WOOD_CONTACT",
                contact_cfg.friction_coeff,
                contact_cfg.normal_penalty,
                contact_cfg.stick_slope,
                contact_cfg.stabilize,
                config.contact_gap,
            )
            ccx.add_blank()
            
            for contact in problem.contacts:
                surf_a = f"{contact.name}_{contact.part_a}_SURF"
                surf_b = f"{contact.name}_{contact.part_b}_SURF"
                if contact_surfaces.get(surf_a) and contact_surfaces.get(surf_b):
                    ccx.add_comment(f"Contact: {contact.name}")
                    ccx.add_contact_pair(
                        "WOOD_CONTACT", surf_a, surf_b, contact_cfg.adjust
                    )
                    ccx.add_blank()
        
        # Fixed BCs
        all_fixed = []
        for bc in problem.fixed_bcs:
            all_fixed.extend(bc_node_lists.get(bc.name, []))
        
        if all_fixed:
            ccx.add_comment("Fixed boundary conditions")
            ccx.add_boundary(all_fixed)
            ccx.add_blank()
        
        # Analysis step
        step_cfg = config.step
        ccx.add_comment("Static analysis step")
        ccx.start_step(
            step_cfg.initial_increment,
            step_cfg.total_time,
            step_cfg.min_increment,
            step_cfg.max_increment,
            step_cfg.max_increments,
            step_cfg.nonlinear_geometry,
        )
        
        if problem.contacts:
            ccx.add_contact_controls()
        ccx.add_blank()
        
        # Loads
        for bc in problem.load_bcs:
            nodes = bc_node_lists.get(bc.name, [])
            if nodes:
                ccx.add_comment(f"Load: {bc.name}")
                ccx.add_cload(nodes, bc.dof, bc.total_load)
                ccx.add_blank()
        
        ccx.add_output_requests()
        ccx.add_blank()
        ccx.end_step()
        
        input_file = output_dir / "analysis.inp"
        ccx.write(input_file)
        return input_file
    
    def _parse_results(
        self,
        success: bool,
        output_dir: Path,
        stdout: str,
        stderr: str,
        mesh_file: Path,
        input_file: Path,
    ) -> AnalysisResult:
        """Parse CalculiX results."""
        frd_file = output_dir / "analysis.frd"
        
        if not success or not frd_file.exists():
            return AnalysisResult(
                success=False,
                solver_type=SolverType.CALCULIX,
                error_message=stderr or "Analysis failed",
                solver_output=stdout,
                input_file=input_file,
                mesh_file=mesh_file,
            )
        
        # Read displacements
        displacements = read_frd_displacements(frd_file)
        
        if not displacements:
            return AnalysisResult(
                success=False,
                solver_type=SolverType.CALCULIX,
                error_message="No displacement results found",
                solver_output=stdout,
                input_file=input_file,
                results_file=frd_file,
                mesh_file=mesh_file,
            )
        
        # Calculate max values
        max_total = 0.0
        max_ux = 0.0
        max_uy = 0.0
        max_uz = 0.0
        
        for ux, uy, uz in displacements.values():
            total = np.sqrt(ux**2 + uy**2 + uz**2)
            if total > max_total:
                max_total = total
            if abs(ux) > abs(max_ux):
                max_ux = ux
            if abs(uy) > abs(max_uy):
                max_uy = uy
            if abs(uz) > abs(max_uz):
                max_uz = uz
        
        return AnalysisResult(
            success=True,
            solver_type=SolverType.CALCULIX,
            max_displacement=max_total,
            max_displacement_x=max_ux,
            max_displacement_y=max_uy,
            max_displacement_z=max_uz,
            node_displacements=displacements,
            input_file=input_file,
            results_file=frd_file,
            mesh_file=mesh_file,
            solver_output=stdout,
        )
