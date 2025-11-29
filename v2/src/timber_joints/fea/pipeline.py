"""High-level FEA analysis pipelines for timber structures."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from build123d import Part, export_step

from .meshing import (
    RefinementBox,
    MeshResult,
    mesh_part,
    get_contact_region_bbox,
    expand_bbox,
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
    analyze_results,
    FEAResults,
    BEAM_HORIZONTAL_X,
    POST_VERTICAL_Z,
)
from ..analysis import find_mesh_contact_faces


@dataclass
class BentFrameConfig:
    """Configuration for bent frame FEA analysis."""
    # Mesh parameters
    mesh_size: float = 50.0  # Base mesh size (mm)
    mesh_size_fine: float = 20.0  # Fine mesh at contacts (mm)
    refinement_margin: float = 10.0  # Margin around contact regions (mm)
    
    # Contact gap
    contact_gap: float = 0.5  # Gap between contact surfaces (mm)
    
    # Load
    load_magnitude: float = 10000.0  # Load at beam midspan (N)
    
    # Material and contact
    material: TimberMaterial = None
    contact: ContactParameters = None
    step: StepParameters = None
    
    # Output
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
class BentFrameAnalysisResult:
    """Results from bent frame analysis."""
    fea_results: FEAResults
    mesh_file: Path
    input_file: Path
    
    # Node counts
    num_nodes: int = 0
    num_elements: int = 0
    
    # Contact info
    left_contact_faces: int = 0
    right_contact_faces: int = 0
    
    # Boundary conditions
    fixed_nodes_left: int = 0
    fixed_nodes_right: int = 0
    load_nodes: int = 0
    
    @property
    def success(self) -> bool:
        return self.fea_results.success
    
    @property
    def max_deflection(self) -> float:
        return self.fea_results.max_displacement
    
    @property
    def max_uz(self) -> float:
        return self.fea_results.max_uz


def analyze_bent_frame(
    left_post: Part,
    right_post: Part,
    beam: Part,
    config: Optional[BentFrameConfig] = None,
    verbose: bool = True,
) -> BentFrameAnalysisResult:
    """Run complete FEA analysis on a bent frame.
    
    Args:
        left_post: Left post Part with mortise cut
        right_post: Right post Part with mortise cut
        beam: Beam Part with tenons (scaled for contact gap)
        config: Analysis configuration
        verbose: Print progress information
        
    Returns:
        BentFrameAnalysisResult with FEA results and metadata
    """
    if config is None:
        config = BentFrameConfig()
    
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Export parts to STEP
    left_post_step = str(output_dir / "left_post.step")
    right_post_step = str(output_dir / "right_post.step")
    beam_step = str(output_dir / "beam.step")
    
    export_step(left_post, left_post_step)
    export_step(right_post, right_post_step)
    export_step(beam, beam_step)
    
    # Get bounding boxes for node classification
    left_post_bbox = left_post.bounding_box()
    right_post_bbox = right_post.bounding_box()
    beam_bbox = beam.bounding_box()
    
    # Pass 1: Coarse mesh to identify contact regions
    if verbose:
        print("Pass 1: Coarse mesh to identify contact regions...")
    
    left_mesh_coarse = mesh_part(left_post_step, "left_post", config.mesh_size)
    right_mesh_coarse = mesh_part(right_post_step, "right_post", config.mesh_size)
    beam_mesh_coarse = mesh_part(beam_step, "beam", config.mesh_size)
    
    # Convert to format for contact detection
    beam_elems_coarse = [(i + 1, elem) for i, elem in enumerate(beam_mesh_coarse.elements)]
    left_elems_coarse = [(i + 1, elem) for i, elem in enumerate(left_mesh_coarse.elements)]
    right_elems_coarse = [(i + 1, elem) for i, elem in enumerate(right_mesh_coarse.elements)]
    
    # Find contact regions
    left_beam_faces_c, left_post_faces_c = find_mesh_contact_faces(
        beam_elems_coarse, beam_mesh_coarse.nodes,
        left_elems_coarse, left_mesh_coarse.nodes,
        margin=config.mesh_size + config.contact_gap
    )
    right_beam_faces_c, right_post_faces_c = find_mesh_contact_faces(
        beam_elems_coarse, beam_mesh_coarse.nodes,
        right_elems_coarse, right_mesh_coarse.nodes,
        margin=config.mesh_size + config.contact_gap
    )
    
    # Get refinement boxes
    beam_refinement = []
    left_bbox = get_contact_region_bbox(left_beam_faces_c, beam_elems_coarse, beam_mesh_coarse.nodes)
    if left_bbox:
        expanded = expand_bbox(left_bbox, config.refinement_margin)
        beam_refinement.append(RefinementBox(expanded[0], expanded[1], config.mesh_size_fine))
    
    right_bbox = get_contact_region_bbox(right_beam_faces_c, beam_elems_coarse, beam_mesh_coarse.nodes)
    if right_bbox:
        expanded = expand_bbox(right_bbox, config.refinement_margin)
        beam_refinement.append(RefinementBox(expanded[0], expanded[1], config.mesh_size_fine))
    
    left_post_refinement = []
    left_post_contact_bbox = get_contact_region_bbox(left_post_faces_c, left_elems_coarse, left_mesh_coarse.nodes)
    if left_post_contact_bbox:
        expanded = expand_bbox(left_post_contact_bbox, config.refinement_margin)
        left_post_refinement.append(RefinementBox(expanded[0], expanded[1], config.mesh_size_fine))
    
    right_post_refinement = []
    right_post_contact_bbox = get_contact_region_bbox(right_post_faces_c, right_elems_coarse, right_mesh_coarse.nodes)
    if right_post_contact_bbox:
        expanded = expand_bbox(right_post_contact_bbox, config.refinement_margin)
        right_post_refinement.append(RefinementBox(expanded[0], expanded[1], config.mesh_size_fine))
    
    # Pass 2: Refined mesh at contact regions
    if verbose:
        print("Pass 2: Refined mesh at contact regions...")
    
    left_mesh = mesh_part(left_post_step, "left_post", config.mesh_size, left_post_refinement)
    right_mesh = mesh_part(right_post_step, "right_post", config.mesh_size, right_post_refinement)
    beam_mesh = mesh_part(beam_step, "beam", config.mesh_size, beam_refinement)
    
    if verbose:
        print(f"  Left post: {left_mesh.num_nodes} nodes, {left_mesh.num_elements} elements")
        print(f"  Right post: {right_mesh.num_nodes} nodes, {right_mesh.num_elements} elements")
        print(f"  Beam: {beam_mesh.num_nodes} nodes, {beam_mesh.num_elements} elements")
    
    # Combine meshes
    combined = combine_meshes({
        "LEFT_POST": left_mesh,
        "RIGHT_POST": right_mesh,
        "BEAM": beam_mesh,
    })
    
    # Find contact faces on refined mesh
    beam_elems = [(i + 1, elem) for i, elem in enumerate(beam_mesh.elements)]
    left_elems = [(i + 1, elem) for i, elem in enumerate(left_mesh.elements)]
    right_elems = [(i + 1, elem) for i, elem in enumerate(right_mesh.elements)]
    
    left_beam_faces_orig, left_post_faces_orig = find_mesh_contact_faces(
        beam_elems, beam_mesh.nodes,
        left_elems, left_mesh.nodes,
        margin=config.mesh_size_fine + config.contact_gap
    )
    right_beam_faces_orig, right_post_faces_orig = find_mesh_contact_faces(
        beam_elems, beam_mesh.nodes,
        right_elems, right_mesh.nodes,
        margin=config.mesh_size_fine + config.contact_gap
    )
    
    # Map to combined mesh element IDs
    beam_offset = combined.element_offsets["BEAM"]
    left_offset = combined.element_offsets["LEFT_POST"]
    right_offset = combined.element_offsets["RIGHT_POST"]
    
    left_beam_faces = [(eid + beam_offset, face) for eid, face in left_beam_faces_orig]
    left_post_faces = [(eid + left_offset, face) for eid, face in left_post_faces_orig]
    right_beam_faces = [(eid + beam_offset, face) for eid, face in right_beam_faces_orig]
    right_post_faces = [(eid + right_offset, face) for eid, face in right_post_faces_orig]
    
    if verbose:
        print(f"\nContact surfaces:")
        print(f"  Left joint: {len(left_beam_faces)} beam, {len(left_post_faces)} post faces")
        print(f"  Right joint: {len(right_beam_faces)} beam, {len(right_post_faces)} post faces")
    
    # Write mesh file
    mesh_file = output_dir / "mesh.inp"
    contact_surfaces = {
        "LEFT_BEAM_SURF": left_beam_faces,
        "LEFT_POST_SURF": left_post_faces,
        "RIGHT_BEAM_SURF": right_beam_faces,
        "RIGHT_POST_SURF": right_post_faces,
    }
    write_mesh_inp(combined, mesh_file, contact_surfaces)
    
    # Find boundary and load nodes
    tol = 2.0
    left_node_max = combined.node_offsets["RIGHT_POST"]
    right_node_max = combined.node_offsets["BEAM"]
    
    fixed_nodes_left = []
    fixed_nodes_right = []
    load_nodes = []
    
    beam_mid_x = (beam_bbox.min.X + beam_bbox.max.X) / 2
    beam_top_z = beam_bbox.max.Z
    load_tol = config.mesh_size * 0.8
    
    for nid, (x, y, z) in combined.nodes.items():
        # Left post fixed at bottom
        if (abs(z - left_post_bbox.min.Z) < tol and
            left_post_bbox.min.X - tol <= x <= left_post_bbox.max.X + tol and
            left_post_bbox.min.Y - tol <= y <= left_post_bbox.max.Y + tol and
            nid <= left_node_max):
            fixed_nodes_left.append(nid)
        
        # Right post fixed at bottom
        elif (abs(z - right_post_bbox.min.Z) < tol and
              right_post_bbox.min.X - tol <= x <= right_post_bbox.max.X + tol and
              right_post_bbox.min.Y - tol <= y <= right_post_bbox.max.Y + tol and
              left_node_max < nid <= right_node_max):
            fixed_nodes_right.append(nid)
        
        # Load at beam midspan top
        elif (abs(x - beam_mid_x) < load_tol and
              abs(z - beam_top_z) < tol and
              beam_bbox.min.Y - tol <= y <= beam_bbox.max.Y + tol and
              nid > right_node_max):
            load_nodes.append(nid)
    
    if verbose:
        print(f"\nBoundary conditions:")
        print(f"  Left post fixed: {len(fixed_nodes_left)} nodes")
        print(f"  Right post fixed: {len(fixed_nodes_right)} nodes")
        print(f"  Load nodes: {len(load_nodes)}")
    
    # Build CalculiX input
    ccx = CalculiXInput()
    ccx.add_comment("CalculiX Bent Frame Analysis")
    ccx.add_comment("Generated by timber_joints.fea")
    ccx.add_blank()
    
    ccx.add_include("mesh.inp")
    ccx.add_blank()
    
    ccx.add_material(config.material)
    ccx.add_blank()
    
    ccx.add_comment("Grain orientations")
    ccx.add_orientation(BEAM_HORIZONTAL_X)
    ccx.add_orientation(POST_VERTICAL_Z)
    ccx.add_blank()
    
    ccx.add_comment("Solid sections with grain orientation")
    ccx.add_solid_section("BEAM", config.material.name, BEAM_HORIZONTAL_X.name)
    ccx.add_solid_section("LEFT_POST", config.material.name, POST_VERTICAL_Z.name)
    ccx.add_solid_section("RIGHT_POST", config.material.name, POST_VERTICAL_Z.name)
    
    ccx.add_comment("Contact interaction")
    ccx.add_surface_interaction("WOOD_CONTACT", config.contact, config.contact_gap)
    ccx.add_blank()
    
    if left_beam_faces and left_post_faces:
        ccx.add_comment("Left joint contact")
        ccx.add_contact_pair("WOOD_CONTACT", "LEFT_BEAM_SURF", "LEFT_POST_SURF", config.contact.adjust)
        ccx.add_blank()
    
    if right_beam_faces and right_post_faces:
        ccx.add_comment("Right joint contact")
        ccx.add_contact_pair("WOOD_CONTACT", "RIGHT_BEAM_SURF", "RIGHT_POST_SURF", config.contact.adjust)
        ccx.add_blank()
    
    ccx.add_comment("Boundary conditions - posts fixed at foundation")
    ccx.add_boundary(fixed_nodes_left + fixed_nodes_right)
    ccx.add_blank()
    
    ccx.add_comment("Static analysis step")
    ccx.start_step(config.step)
    ccx.add_contact_controls()
    ccx.add_blank()
    
    ccx.add_comment(f"Load: {config.load_magnitude} N at beam midspan")
    ccx.add_cload(load_nodes, 3, -config.load_magnitude)
    ccx.add_blank()
    
    ccx.add_output_requests()
    ccx.add_blank()
    ccx.end_step()
    
    input_file = output_dir / "analysis.inp"
    ccx.write(input_file)
    
    if verbose:
        print(f"\nRunning CalculiX solver...")
    
    # Run solver
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
    
    return BentFrameAnalysisResult(
        fea_results=fea_results,
        mesh_file=mesh_file,
        input_file=input_file,
        num_nodes=len(combined.nodes),
        num_elements=len(combined.elements),
        left_contact_faces=len(left_beam_faces) + len(left_post_faces),
        right_contact_faces=len(right_beam_faces) + len(right_post_faces),
        fixed_nodes_left=len(fixed_nodes_left),
        fixed_nodes_right=len(fixed_nodes_right),
        load_nodes=len(load_nodes),
    )
