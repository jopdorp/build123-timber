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
    RefinementBox,
    MeshResult,
    CombinedMesh,
    mesh_part,
    get_contact_region_bbox,
    expand_bbox,
    combine_meshes,
    write_mesh_inp,
    find_mesh_contact_faces,
)
from .calculix import (
    ContactParameters,
    StepParameters,
    GrainOrientation,
    TimberMaterial,
    CalculiXInput,
    run_calculix,
    analyze_results,
    FEAResults,
    BEAM_HORIZONTAL_X,
    POST_VERTICAL_Z,
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
    """Configuration for assembly FEA analysis."""
    mesh_size: float = 50.0
    mesh_size_fine: float = 20.0
    refinement_margin: float = 10.0
    contact_gap: float = 0.5
    
    material: TimberMaterial = None
    contact: ContactParameters = None
    step: StepParameters = None
    
    output_dir: Path = None
    
    def __post_init__(self):
        if self.material is None:
            self.material = TimberMaterial()
        if self.contact is None:
            self.contact = ContactParameters()
        if self.step is None:
            self.step = StepParameters()
        if self.output_dir is None:
            self.output_dir = Path("./fea_output")


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
    config: Optional[AssemblyConfig] = None,
    verbose: bool = True,
) -> AssemblyResult:
    """Run FEA analysis on a generic assembly.
    
    This is the main entry point for FEA analysis. It:
    1. Exports parts to STEP and meshes them
    2. Identifies contact regions and refines mesh
    3. Finds contact surfaces between parts
    4. Applies boundary conditions
    5. Runs CalculiX solver
    6. Returns results
    
    Args:
        parts: List of FEAPart definitions
        contacts: List of ContactPair definitions
        fixed_bcs: List of FixedBC definitions  
        load_bcs: List of LoadBC definitions
        config: Analysis configuration
        verbose: Print progress
        
    Returns:
        AssemblyResult with FEA results
    """
    if config is None:
        config = AssemblyConfig()
    
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build part lookup
    part_dict = {p.name: p for p in parts}
    
    # Export parts to STEP
    step_files = {}
    for part in parts:
        step_file = str(output_dir / f"{part.name.lower()}.step")
        export_step(part.shape, step_file)
        step_files[part.name] = step_file
    
    # Pass 1: Coarse mesh to identify contact regions
    if verbose:
        print("Pass 1: Coarse mesh to identify contact regions...")
    
    coarse_meshes = {}
    for part in parts:
        coarse_meshes[part.name] = mesh_part(
            step_files[part.name], part.name.lower(), config.mesh_size
        )
    
    # Find contact regions and build refinement boxes
    refinement_boxes: Dict[str, List[RefinementBox]] = {p.name: [] for p in parts}
    
    for contact in contacts:
        mesh_a = coarse_meshes[contact.part_a]
        mesh_b = coarse_meshes[contact.part_b]
        
        elems_a = [(i + 1, e) for i, e in enumerate(mesh_a.elements)]
        elems_b = [(i + 1, e) for i, e in enumerate(mesh_b.elements)]
        
        faces_a, faces_b = find_mesh_contact_faces(
            elems_a, mesh_a.nodes,
            elems_b, mesh_b.nodes,
            margin=config.mesh_size + config.contact_gap
        )
        
        # Add refinement for part A
        bbox_a = get_contact_region_bbox(faces_a, elems_a, mesh_a.nodes)
        if bbox_a:
            expanded = expand_bbox(bbox_a, config.refinement_margin)
            refinement_boxes[contact.part_a].append(
                RefinementBox(expanded[0], expanded[1], config.mesh_size_fine)
            )
        
        # Add refinement for part B
        bbox_b = get_contact_region_bbox(faces_b, elems_b, mesh_b.nodes)
        if bbox_b:
            expanded = expand_bbox(bbox_b, config.refinement_margin)
            refinement_boxes[contact.part_b].append(
                RefinementBox(expanded[0], expanded[1], config.mesh_size_fine)
            )
    
    # Pass 2: Refined mesh
    if verbose:
        print("Pass 2: Refined mesh at contact regions...")
    
    fine_meshes = {}
    for part in parts:
        fine_meshes[part.name] = mesh_part(
            step_files[part.name],
            part.name.lower(),
            config.mesh_size,
            refinement_boxes[part.name] or None,
        )
        if verbose:
            m = fine_meshes[part.name]
            print(f"  {part.name}: {m.num_nodes} nodes, {m.num_elements} elements")
    
    # Combine meshes
    combined = combine_meshes(fine_meshes)
    
    # Find contact surfaces on refined mesh
    contact_surfaces = {}
    contact_face_counts = {}
    
    for contact in contacts:
        mesh_a = fine_meshes[contact.part_a]
        mesh_b = fine_meshes[contact.part_b]
        
        elems_a = [(i + 1, e) for i, e in enumerate(mesh_a.elements)]
        elems_b = [(i + 1, e) for i, e in enumerate(mesh_b.elements)]
        
        faces_a, faces_b = find_mesh_contact_faces(
            elems_a, mesh_a.nodes,
            elems_b, mesh_b.nodes,
            margin=config.mesh_size_fine + config.contact_gap
        )
        
        # Map to combined mesh element IDs
        offset_a = combined.element_offsets[contact.part_a]
        offset_b = combined.element_offsets[contact.part_b]
        
        surf_a_name = f"{contact.name}_{contact.part_a}_SURF"
        surf_b_name = f"{contact.name}_{contact.part_b}_SURF"
        
        contact_surfaces[surf_a_name] = [(eid + offset_a, f) for eid, f in faces_a]
        contact_surfaces[surf_b_name] = [(eid + offset_b, f) for eid, f in faces_b]
        
        contact_face_counts[contact.name] = len(faces_a) + len(faces_b)
        
        if verbose:
            print(f"  Contact '{contact.name}': {len(faces_a)} + {len(faces_b)} faces")
    
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
    ccx.add_surface_interaction("WOOD_CONTACT", config.contact, config.contact_gap)
    ccx.add_blank()
    
    # Contact pairs
    for contact in contacts:
        surf_a = f"{contact.name}_{contact.part_a}_SURF"
        surf_b = f"{contact.name}_{contact.part_b}_SURF"
        if contact_surfaces[surf_a] and contact_surfaces[surf_b]:
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
    ccx.start_step(config.step)
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
    
    success, stdout, stderr = run_calculix(input_file)
    
    if verbose:
        print(stdout)
        if stderr:
            print(f"STDERR: {stderr}")
    
    # Analyze results
    frd_file = output_dir / "analysis.frd"
    fea_results = analyze_results(frd_file) if success else FEAResults(
        max_displacement=0.0,
        max_uz=0.0,
        displacements={},
        success=False,
    )
    
    if verbose and fea_results.success:
        print(f"\nResults:")
        print(f"  Max displacement: {fea_results.max_displacement:.4f} mm")
        print(f"  Max Z displacement: {fea_results.max_uz:.4f} mm")
    
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
