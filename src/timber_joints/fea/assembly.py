"""Generic FEA analysis pipeline for timber assemblies.

This module provides composable building blocks for FEA analysis:
- Part definitions with material and orientation
- Contact pair definitions
- Boundary condition definitions
- Generic assembly analysis

The frame.py module provides a higher-level API (TimberFrame) that
auto-detects contacts and boundary conditions from geometry.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

from build123d import Part, export_step, BoundBox

from .meshing import (
    MeshResult,
    MeshingResult,
    CombinedMesh,
    ContactDefinition,
    MeshingConfig,
    mesh_parts_with_contact_refinement,
    write_mesh_inp,
)
from .materials import (
    GrainOrientation,
    TimberMaterial,
    BEAM_HORIZONTAL_X,
    POST_VERTICAL_Z,
    get_default_material,
)
from .backends.calculix import (
    CalculiXInput,
    run_ccx,
    read_frd_displacements,
    read_frd_stresses,
    compute_von_mises,
)
from .solver import (
    ContactParameters,
    StepConfig,
)


# =============================================================================
# Part Definition
# =============================================================================

@dataclass
class FEAPart:
    """A part for FEA analysis with material and orientation."""
    name: str
    shape: Part
    orientation: GrainOrientation
    material: Optional[TimberMaterial] = None  # Uses default if None
    
    @property
    def bbox(self) -> BoundBox:
        return self.shape.bounding_box()


# =============================================================================
# Contact Definition
# =============================================================================

@dataclass
class ContactPair:
    """Definition of contact between two parts."""
    name: str
    part_a: str  # Part name (slave surface)
    part_b: str  # Part name (master surface)


# =============================================================================
# Boundary Conditions
# =============================================================================

# Type for node filter functions: (node_id, x, y, z, part_name, combined_mesh) -> bool
NodeFilter = Callable[[int, float, float, float, str, CombinedMesh], bool]


@dataclass
class FixedBC:
    """Fixed boundary condition."""
    name: str
    node_filter: NodeFilter


@dataclass
class LoadBC:
    """Concentrated load boundary condition."""
    name: str
    node_filter: NodeFilter
    dof: int  # 1=X, 2=Y, 3=Z
    total_load: float  # Total load, distributed over selected nodes


# =============================================================================
# Analysis Configuration
# =============================================================================

@dataclass
class AssemblyConfig:
    """Configuration for assembly FEA analysis.
    
    Default mesh sizes tuned for timber frames (5m span, ~50mm contacts).
    Contact parameters derived from central config.
    """
    mesh_size: float = 150.0  # Coarse base mesh for bulk material
    mesh_size_fine: float = 40.0  # Fine mesh at contact surfaces (~1-2 per contact)
    refinement_margin: float = 20.0  # Margin around contact regions
    contact_gap: float = None  # CalculiX contact gap c0 (from config if None)
    
    material: TimberMaterial = None
    contact: ContactParameters = None
    step: StepConfig = None
    
    output_dir: Path = None
    
    def __post_init__(self):
        from timber_joints.config import DEFAULT_CONFIG
        if self.contact_gap is None:
            self.contact_gap = DEFAULT_CONFIG.contact_gap
        if self.material is None:
            self.material = get_default_material()
        if self.contact is None:
            self.contact = ContactParameters()
        if self.step is None:
            self.step = StepConfig()
        if self.output_dir is None:
            self.output_dir = Path("./fea_output")


@dataclass
class FEAResults:
    """Results from CalculiX FEA analysis."""
    max_displacement: float
    max_uz: float  # Z displacement (typically vertical)
    displacements: Dict[int, Tuple[float, float, float]]  # node_id -> (ux, uy, uz)
    success: bool
    frd_file: Optional[Path] = None
    max_von_mises: float = 0.0  # Max von Mises stress (MPa)
    max_stress: float = 0.0  # Max principal/normal stress (MPa)
    
    @property
    def max_deflection(self) -> float:
        """Alias for max_displacement."""
        return self.max_displacement


@dataclass
class AssemblyResult:
    """Results from assembly FEA analysis."""
    fea_results: FEAResults
    mesh_file: Path
    input_file: Path
    combined_mesh: CombinedMesh
    contact_faces: Dict[str, int]  # contact_name -> face count
    bc_nodes: Dict[str, int]  # bc_name -> node count
    
    @property
    def success(self) -> bool:
        return self.fea_results.success
    
    @property
    def num_nodes(self) -> int:
        return len(self.combined_mesh.nodes)
    
    @property
    def num_elements(self) -> int:
        return len(self.combined_mesh.elements)


# =============================================================================
# Generic Analysis Pipeline
# =============================================================================

def analyze_assembly(
    parts: List[FEAPart],
    contacts: List[ContactPair],
    fixed_bcs: List[FixedBC],
    load_bcs: List[LoadBC],
    meshing_result: MeshingResult,
    config: Optional[AssemblyConfig] = None,
    verbose: bool = True,
) -> AssemblyResult:
    """Run FEA analysis on a generic assembly.
    
    This is the main entry point for FEA analysis. It:
    1. Uses pre-computed mesh from TimberFrame.mesh()
    2. Applies boundary conditions
    3. Runs CalculiX solver
    4. Returns results
    
    Args:
        parts: List of FEAPart definitions
        contacts: List of ContactPair definitions
        fixed_bcs: List of FixedBC definitions  
        load_bcs: List of LoadBC definitions
        meshing_result: Pre-computed MeshingResult from TimberFrame.mesh()
        config: Analysis configuration
        verbose: Print progress
        
    Returns:
        AssemblyResult with FEA results
    """
    import numpy as np
    
    if config is None:
        config = AssemblyConfig()
    
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Export parts to STEP (needed for mesh.inp even if we have cached mesh)
    step_files = {}
    for part in parts:
        step_file = str(output_dir / f"{part.name.lower()}.step")
        export_step(part.shape, step_file)
        step_files[part.name] = step_file
    
    # Use pre-computed mesh from TimberFrame.mesh()
    combined = meshing_result.combined
    contact_surfaces = meshing_result.contact_surfaces
    fine_meshes = meshing_result.meshes
    
    # Count contact faces
    contact_face_counts = {}
    for contact in contacts:
        surf_a = f"{contact.name}_{contact.part_a}_SURF"
        surf_b = f"{contact.name}_{contact.part_b}_SURF"
        count_a = len(contact_surfaces.get(surf_a, []))
        count_b = len(contact_surfaces.get(surf_b, []))
        contact_face_counts[contact.name] = count_a + count_b
    
    # Write mesh file
    mesh_file = output_dir / "mesh.inp"
    write_mesh_inp(combined, mesh_file, contact_surfaces)
    
    # Apply boundary conditions
    bc_node_lists: Dict[str, List[int]] = {}
    
    # Find which part each node belongs to
    node_to_part = {}
    for part_name, offset in combined.node_offsets.items():
        mesh = fine_meshes[part_name]
        for orig_nid in mesh.nodes.keys():
            node_to_part[orig_nid + offset] = part_name
    
    for bc in fixed_bcs + load_bcs:
        nodes = []
        for nid, (x, y, z) in combined.nodes.items():
            part_name = node_to_part.get(nid, "")
            if bc.node_filter(nid, x, y, z, part_name, combined):
                nodes.append(nid)
        bc_node_lists[bc.name] = nodes
        if verbose:
            print(f"  BC '{bc.name}': {len(nodes)} nodes")
    
    # Build CalculiX input
    ccx = CalculiXInput()
    ccx.add_comment("CalculiX Assembly Analysis")
    ccx.add_comment("Generated by timber_joints.fea")
    ccx.add_blank()
    
    ccx.add_include("mesh.inp")
    ccx.add_blank()
    
    ccx.add_material(config.material)
    ccx.add_blank()
    
    # Add orientations and sections for each part
    ccx.add_comment("Part orientations and sections")
    for part in parts:
        ccx.add_orientation(part.orientation)
        material = part.material or config.material
        ccx.add_solid_section(part.name, material.name, part.orientation.name)
    ccx.add_blank()
    
    # Contact interaction
    ccx.add_comment("Contact interaction")
    ccx.add_surface_interaction(
        "WOOD_CONTACT",
        config.contact.friction_coeff,
        config.contact.normal_penalty,
        config.contact.stick_slope,
        config.contact.stabilize,
        config.contact_gap,
    )
    ccx.add_blank()
    
    # Contact pairs
    for contact in contacts:
        surf_a = f"{contact.name}_{contact.part_a}_SURF"
        surf_b = f"{contact.name}_{contact.part_b}_SURF"
        if contact_surfaces.get(surf_a) and contact_surfaces.get(surf_b):
            ccx.add_comment(f"Contact: {contact.name}")
            ccx.add_contact_pair("WOOD_CONTACT", surf_a, surf_b, config.contact.adjust)
            ccx.add_blank()
    
    # Fixed BCs
    all_fixed_nodes = []
    for bc in fixed_bcs:
        all_fixed_nodes.extend(bc_node_lists[bc.name])
    
    if all_fixed_nodes:
        ccx.add_comment("Fixed boundary conditions")
        ccx.add_boundary(all_fixed_nodes)
        ccx.add_blank()
    
    # Analysis step
    ccx.add_comment("Static analysis step")
    step = config.step
    ccx.start_step(
        step.initial_increment,
        step.total_time,
        step.min_increment,
        step.max_increment,
        step.max_increments,
        step.nonlinear_geometry,
    )
    ccx.add_contact_controls()
    ccx.add_blank()
    
    # Loads
    for bc in load_bcs:
        nodes = bc_node_lists[bc.name]
        if nodes:
            ccx.add_comment(f"Load: {bc.name}")
            ccx.add_cload(nodes, bc.dof, bc.total_load)
            ccx.add_blank()
    
    ccx.add_output_requests()
    ccx.add_blank()
    ccx.end_step()
    
    input_file = output_dir / "analysis.inp"
    ccx.write(input_file)
    
    # Run solver
    if verbose:
        print("\nRunning CalculiX solver...")
    
    success, stdout, stderr = run_ccx(input_file)
    
    if verbose:
        print(stdout)
        if stderr:
            print(f"STDERR: {stderr}")
    
    # Parse results
    frd_file = output_dir / "analysis.frd"
    if success and frd_file.exists():
        displacements = read_frd_displacements(frd_file)
        if displacements:
            max_total = 0.0
            max_uz = 0.0
            for ux, uy, uz in displacements.values():
                total = np.sqrt(ux**2 + uy**2 + uz**2)
                if total > max_total:
                    max_total = total
                if abs(uz) > abs(max_uz):
                    max_uz = uz
            
            # Read stresses
            max_von_mises = 0.0
            max_stress = 0.0
            stresses = read_frd_stresses(frd_file)
            if stresses:
                for sxx, syy, szz, sxy, syz, szx in stresses.values():
                    vm = compute_von_mises(sxx, syy, szz, sxy, syz, szx)
                    if vm > max_von_mises:
                        max_von_mises = vm
                    # Track max normal stress
                    for s in (sxx, syy, szz):
                        if s > max_stress:
                            max_stress = s
            
            fea_results = FEAResults(
                max_displacement=max_total,
                max_uz=max_uz,
                displacements=displacements,
                success=True,
                frd_file=frd_file,
                max_von_mises=max_von_mises,
                max_stress=max_stress,
            )
        else:
            fea_results = FEAResults(
                max_displacement=0.0, max_uz=0.0, displacements={}, success=False
            )
    else:
        fea_results = FEAResults(
            max_displacement=0.0, max_uz=0.0, displacements={}, success=False
        )
    
    if verbose and fea_results.success:
        print(f"\nResults:")
        print(f"  Max displacement: {fea_results.max_displacement:.4f} mm")
        print(f"  Max Z displacement: {fea_results.max_uz:.4f} mm")
        print(f"  Max von Mises stress: {fea_results.max_von_mises:.2f} MPa")
    
    return AssemblyResult(
        fea_results=fea_results,
        mesh_file=mesh_file,
        input_file=input_file,
        combined_mesh=combined,
        contact_faces=contact_face_counts,
        bc_nodes={bc.name: len(bc_node_lists[bc.name]) for bc in fixed_bcs + load_bcs},
    )


# =============================================================================
# Convenience Functions for Common Cases
# =============================================================================

def nodes_at_z_min(part_name: str, tolerance: float = 2.0) -> NodeFilter:
    """Create filter for nodes at the minimum Z of a specific part."""
    def filter_fn(nid, x, y, z, node_part, mesh):
        if node_part != part_name:
            return False
        # Get part's Z min from its nodes
        part_nodes = [
            mesh.nodes[n] for n in mesh.nodes
            if n in mesh.nodes  # All nodes for now
        ]
        # This is a simplification - in practice we'd track part bboxes
        return z < tolerance
    return filter_fn


def nodes_at_location(
    x: Optional[float] = None,
    y: Optional[float] = None, 
    z: Optional[float] = None,
    tolerance: float = 2.0,
    part_name: Optional[str] = None,
) -> NodeFilter:
    """Create filter for nodes at a specific location."""
    def filter_fn(nid, nx, ny, nz, node_part, mesh):
        if part_name and node_part != part_name:
            return False
        if x is not None and abs(nx - x) > tolerance:
            return False
        if y is not None and abs(ny - y) > tolerance:
            return False
        if z is not None and abs(nz - z) > tolerance:
            return False
        return True
    return filter_fn


def nodes_in_bbox(
    x_min: float, x_max: float,
    y_min: float, y_max: float,
    z_min: float, z_max: float,
    part_name: Optional[str] = None,
) -> NodeFilter:
    """Create filter for nodes within a bounding box."""
    def filter_fn(nid, x, y, z, node_part, mesh):
        if part_name and node_part != part_name:
            return False
        return (x_min <= x <= x_max and
                y_min <= y <= y_max and
                z_min <= z <= z_max)
    return filter_fn
