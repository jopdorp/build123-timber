"""High-level FEA for timber frames.

Provides a simple API that infers assembly structure from frame geometry.
Parts are automatically classified as posts (vertical) or beams (horizontal),
and contacts/boundary conditions follow from spatial relationships.
"""

import copy
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Callable, Tuple

from build123d import Part

from .assembly import (
    FEAPart,
    ContactPair,
    FixedBC,
    LoadBC,
    AssemblyConfig,
    AssemblyResult,
    analyze_assembly,
)
from .materials import (
    GrainOrientation,
    BEAM_HORIZONTAL_X,
    POST_VERTICAL_Z,
)
from .meshing import (
    ContactDefinition,
    MeshingConfig,
    MeshingResult,
    mesh_parts_with_contact_refinement,
    build_mesh_faces_compound,
    get_boundary_faces,
)
from .solver import StepConfig

class MemberType(Enum):
    """Type of structural member based on orientation."""
    POST = auto()    # Vertical member (grain along Z)
    BEAM = auto()    # Horizontal member (grain along X)
    BRACE = auto()   # Diagonal member


@dataclass
class FrameMember:
    """A structural member in a timber frame."""
    name: str
    shape: Part
    member_type: MemberType = None  # Auto-detected if None
    
    def __post_init__(self):
        if self.member_type is None:
            self.member_type = self._detect_type()
    
    def _detect_type(self) -> MemberType:
        """Detect member type from geometry."""
        bbox = self.shape.bounding_box()
        dx = bbox.max.X - bbox.min.X
        dy = bbox.max.Y - bbox.min.Y
        dz = bbox.max.Z - bbox.min.Z
        
        # Longest dimension determines orientation
        if dz > dx and dz > dy:
            return MemberType.POST
        elif dx > dy and dx > dz:
            return MemberType.BEAM
        else:
            return MemberType.BRACE
    
    @property
    def orientation(self) -> GrainOrientation:
        """Get grain orientation for FEA."""
        if self.member_type == MemberType.POST:
            return POST_VERTICAL_Z
        else:
            return BEAM_HORIZONTAL_X
    
    @property 
    def bbox(self):
        return self.shape.bounding_box()
    
    @property
    def is_post(self) -> bool:
        return self.member_type == MemberType.POST
    
    @property
    def is_beam(self) -> bool:
        return self.member_type == MemberType.BEAM
    
    @property
    def is_brace(self) -> bool:
        return self.member_type == MemberType.BRACE


@dataclass
class TimberFrame:
    """A timber frame assembly for FEA analysis.
    
    Automatically detects:
    - Member types (post vs beam) from geometry
    - Contacts between adjacent members
    - Fixed supports at post bases
    - Self-weight loads distributed across members
    """
    members: List[FrameMember] = field(default_factory=list)
    contact_gap: float = 0.5  # Gap for contact analysis
    timber_density: float = 500.0  # kg/m³
    _meshing_result: Optional[MeshingResult] = field(default=None, repr=False)
    
    # Physical constants
    GRAVITY: float = 9.81  # m/s²
    
    def add_member(self, name: str, shape: Part, member_type: MemberType = None) -> "TimberFrame":
        """Add a member to the frame. Returns self for chaining."""
        self.members.append(FrameMember(name, shape, member_type))
        return self
    
    @property
    def posts(self) -> List[FrameMember]:
        """Get all post members."""
        return [m for m in self.members if m.is_post]
    
    @property
    def beams(self) -> List[FrameMember]:
        """Get all beam members."""
        return [m for m in self.members if m.is_beam]
    
    def mesh(
        self,
        element_size: float = 150.0,
        element_size_fine: float = 40.0,
        refinement_margin: float = 20.0,
        force: bool = False,
        verbose: bool = False,
    ) -> MeshingResult:
        """Mesh the frame with contact surface refinement.
        
        Meshes all members and identifies contact surfaces between them.
        The result is cached and reused by get_contact_surfaces() and analyze().
        
        Args:
            element_size: Base element size in mm (default 50)
            element_size_fine: Fine element size for contact areas (default 20)
            refinement_margin: Margin around contact surfaces for refinement (default 10)
            force: If True, re-mesh even if already meshed
            verbose: If True, print progress information
            
        Returns:
            MeshingResult with meshes and contact information
        """
        if self._meshing_result is not None and not force:
            if verbose:
                print("Using cached meshing result")
            return self._meshing_result
        
        import tempfile
        from build123d import export_step
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Export all parts to STEP files
            parts = {}
            for member in self.members:
                step_path = tmpdir_path / f"{member.name}.step"
                export_step(member.shape, str(step_path))
                parts[member.name] = str(step_path)
            
            # Build contact definitions from auto-detected contacts
            contact_defs = [
                ContactDefinition(name=f"contact_{i}", part_a=part_a, part_b=part_b)
                for i, (part_a, part_b) in enumerate(self._find_contacts())
            ]
            
            config = MeshingConfig(
                element_size=element_size,
                element_size_fine=element_size_fine,
                refinement_margin=refinement_margin,
                contact_gap=self.contact_gap,
            )
            
            self._meshing_result = mesh_parts_with_contact_refinement(
                parts,
                contact_defs,
                config,
                verbose,
            )
        
        return self._meshing_result
    
    def _generate_self_weight_loads(self, verbose: bool = True) -> tuple[List[LoadBC], float]:
        """Generate self-weight loads for all members.
        
        Divides each member into 3 equal parts and applies 1/3 of its weight
        at the center of each part (downward, dof=3).
        
        Returns:
            Tuple of (list of LoadBC, total weight in N)
        """
        loads = []
        total_weight = 0.0
        
        for member in self.members:
            bbox = member.bbox
            
            # Calculate volume in m³ (dimensions are in mm)
            volume_mm3 = member.shape.volume
            volume_m3 = volume_mm3 / 1e9  # mm³ to m³
            
            # Calculate weight
            mass_kg = volume_m3 * self.timber_density
            weight_n = mass_kg * self.GRAVITY
            total_weight += weight_n
            
            # Determine primary axis (longest dimension)
            dx = bbox.max.X - bbox.min.X
            dy = bbox.max.Y - bbox.min.Y
            dz = bbox.max.Z - bbox.min.Z
            
            # Generate 3 load points along the longest axis
            third_weight = weight_n / 3
            
            # Center coordinates
            cx = (bbox.min.X + bbox.max.X) / 2
            cy = (bbox.min.Y + bbox.max.Y) / 2
            
            if dz > dx and dz > dy:
                # Vertical member (post) - divide along Z
                positions = [
                    bbox.min.Z + dz * (1/6),
                    bbox.min.Z + dz * (3/6),
                    bbox.min.Z + dz * (5/6),
                ]
                for i, pz in enumerate(positions):
                    def make_filter(name, px, py, pz_target, tol=70.0):
                        def filter_fn(nid, x, y, z, part, mesh):
                            return (part == name and 
                                    abs(x - px) < tol and 
                                    abs(y - py) < tol and 
                                    abs(z - pz_target) < tol)
                        return filter_fn
                    
                    loads.append(LoadBC(
                        f"{member.name}_sw_{i}",
                        make_filter(member.name, cx, cy, pz),
                        dof=3,
                        total_load=-third_weight
                    ))
            elif dx > dy:
                # Horizontal member along X (beam) - divide along X
                positions = [
                    bbox.min.X + dx * (1/6),
                    bbox.min.X + dx * (3/6),
                    bbox.min.X + dx * (5/6),
                ]
                top_z = bbox.max.Z
                for i, px in enumerate(positions):
                    def make_filter(name, px_target, py, pz, tol=70.0):
                        def filter_fn(nid, x, y, z, part, mesh):
                            return (part == name and 
                                    abs(x - px_target) < tol and 
                                    abs(y - py) < tol and 
                                    abs(z - pz) < 35.0)
                        return filter_fn
                    
                    loads.append(LoadBC(
                        f"{member.name}_sw_{i}",
                        make_filter(member.name, px, cy, top_z),
                        dof=3,
                        total_load=-third_weight
                    ))
            else:
                # Horizontal member along Y (girt) - divide along Y
                positions = [
                    bbox.min.Y + dy * (1/6),
                    bbox.min.Y + dy * (3/6),
                    bbox.min.Y + dy * (5/6),
                ]
                top_z = bbox.max.Z
                for i, py in enumerate(positions):
                    def make_filter(name, px, py_target, pz, tol=70.0):
                        def filter_fn(nid, x, y, z, part, mesh):
                            return (part == name and 
                                    abs(x - px) < tol and 
                                    abs(y - py_target) < tol and 
                                    abs(z - pz) < 35.0)
                        return filter_fn
                    
                    loads.append(LoadBC(
                        f"{member.name}_sw_{i}",
                        make_filter(member.name, cx, py, top_z),
                        dof=3,
                        total_load=-third_weight
                    ))
        
        if verbose:
            print(f"Self-weight: {total_weight / self.GRAVITY:.1f} kg ({total_weight:.1f} N)")
            print(f"  {len(loads)} load points (3 per member)")
        
        return loads, total_weight
    
    def _find_contacts(self) -> List[tuple[str, str]]:
        """Find pairs of members that are in contact.
        
        Two members are in contact if their bounding boxes overlap
        (accounting for the contact gap). Uses a generous margin since
        mortise-tenon joints may have tenons extending into the post.
        """
        contacts = []
        # Use larger margin - tenons extend into posts, and mesh_size affects detection
        margin = 100.0  # mm - generous to catch all joints
        
        for i, m1 in enumerate(self.members):
            for m2 in self.members[i+1:]:
                if self._bboxes_overlap(m1.bbox, m2.bbox, margin):
                    # Slave surface (part_a) = tenon side (beam or brace)
                    # Master surface (part_b) = mortise side (post or beam)
                    # Priority: POST > BEAM > BRACE (posts are always master)
                    if m1.is_post and not m2.is_post:
                        # m1 is post (master), m2 is beam/brace (slave)
                        contacts.append((m2.name, m1.name))
                    elif m2.is_post and not m1.is_post:
                        # m2 is post (master), m1 is beam/brace (slave)
                        contacts.append((m1.name, m2.name))
                    elif m1.is_beam and m2.is_brace:
                        # beam is master, brace is slave
                        contacts.append((m2.name, m1.name))
                    elif m2.is_beam and m1.is_brace:
                        # beam is master, brace is slave
                        contacts.append((m1.name, m2.name))
                    else:
                        # Default: m1 is slave, m2 is master
                        contacts.append((m1.name, m2.name))
        
        return contacts
    
    def _bboxes_overlap(self, b1, b2, margin: float) -> bool:
        """Check if two bounding boxes overlap within margin."""
        return not (
            b1.max.X + margin < b2.min.X or b2.max.X + margin < b1.min.X or
            b1.max.Y + margin < b2.min.Y or b2.max.Y + margin < b1.min.Y or
            b1.max.Z + margin < b2.min.Z or b2.max.Z + margin < b1.min.Z
        )
    
    def get_contact_surfaces(
        self,
        mesh_size: float = 150.0,
        mesh_size_fine: float = 40.0,
    ) -> List[Tuple[str, str, "Compound", "Compound"]]:
        """Get mesh contact surfaces for all detected member pairs.
        
        Uses the cached meshing result from mesh() if available,
        otherwise meshes the parts with contact surface refinement.
        Returns visualizable Compound objects built from the refined mesh triangles.
        
        Args:
            mesh_size: Base mesh element size
            mesh_size_fine: Fine element size for contact areas (used if meshing needed)
            
        Returns:
            List of tuples: (name_a, name_b, surface_a, surface_b)
        """
        from .meshing import find_mesh_contact_faces
        
        # Ensure we have a meshing result
        result = self.mesh(
            element_size=mesh_size,
            element_size_fine=mesh_size_fine,
        )
        
        if not result.contact_surfaces:
            return []
        
        # Build visualizable compounds from the mesh contact surfaces
        contact_results = []
        for contact in result.contact_surfaces:
            mesh_a = result.meshes[contact.part_a]
            mesh_b = result.meshes[contact.part_b]
            
            elems_a = [(i + 1, e) for i, e in enumerate(mesh_a.elements)]
            elems_b = [(i + 1, e) for i, e in enumerate(mesh_b.elements)]
            
            # Build compounds from the stored contact faces
            surface_a = build_mesh_faces_compound(contact.faces_a, elems_a, mesh_a.nodes)
            surface_b = build_mesh_faces_compound(contact.faces_b, elems_b, mesh_b.nodes)
            
            contact_results.append((contact.part_a, contact.part_b, surface_a, surface_b))
        
        return contact_results
    
    def analyze(
        self,
        load: float = 0.0,
        load_location: Optional[Callable[[float, float, float], bool]] = None,
        additional_loads: Optional[List[LoadBC]] = None,
        include_self_weight: bool = True,
        mesh_size: float = 150.0,
        mesh_size_fine: float = 40.0,
        initial_increment: float = 0.05,
        max_increments: int = 500,
        output_dir: Path = None,
        verbose: bool = True,
    ) -> AssemblyResult:
        """Run FEA analysis on the frame.
        
        Automatically:
        - Creates contact gap on beams
        - Detects contacts between members
        - Fixes posts at their bases
        - Applies self-weight loads (can be disabled)
        - Applies load at beam midspan (or custom location)
        
        Args:
            load: Total load to apply at main location (N), negative for downward.
                  Set to 0 to skip main load (e.g., when using only additional_loads).
            load_location: Optional function (x,y,z) -> bool for load nodes.
                          Defaults to beam midspan top surface.
            additional_loads: Optional list of additional LoadBC objects
            include_self_weight: Include self-weight of timber members (default True)
            mesh_size: Base mesh element size (mm)
            mesh_size_fine: Fine mesh at contacts (mm)
            initial_increment: Initial load increment (0.0-1.0). Lower values (0.01-0.05)
                             help convergence for contact problems. Default 0.05.
            max_increments: Maximum solver iterations. Default 200.
            output_dir: Directory for output files
            verbose: Print progress
            
        Returns:
            AssemblyResult with FEA results
        """
        if output_dir is None:
            output_dir = Path("./fea_output")
        
        # Build FEA parts
        # Note: No shrinkage needed - the gap is built into the geometry
        # via create_receiving_cut margin parameter
        parts = []
        for member in self.members:
            shape = copy.deepcopy(member.shape)
            parts.append(FEAPart(member.name, shape, member.orientation))
        
        # Auto-detect contacts
        contact_pairs = []
        for i, (part_a, part_b) in enumerate(self._find_contacts()):
            contact_pairs.append(ContactPair(f"contact_{i}", part_a, part_b))
        
        if verbose:
            print(f"Auto-detected {len(contact_pairs)} contacts:")
            for cp in contact_pairs:
                print(f"  {cp.part_a} <-> {cp.part_b}")
        
        # Fixed BCs: posts fixed at bottom
        fixed_bcs = []
        for post in self.posts:
            z_min = post.bbox.min.Z
            fixed_bcs.append(FixedBC(
                f"{post.name}_fixed",
                lambda nid, x, y, z, part, mesh, pname=post.name, zmin=z_min: (
                    part == pname and abs(z - zmin) < 2.0
                )
            ))
        
        # Load BC: default to beam midspan top
        if load_location is None:
            # Find the beam with largest span
            main_beam = max(self.beams, key=lambda m: m.bbox.max.X - m.bbox.min.X)
            beam_bbox = main_beam.bbox
            mid_x = (beam_bbox.min.X + beam_bbox.max.X) / 2
            top_z = beam_bbox.max.Z - self.contact_gap  # Account for shrinkage
            beam_name = main_beam.name
            
            # Use generous tolerance - we want to find the midspan top region
            x_tol = mesh_size * 1.5  # Allow 1.5 mesh elements from center
            z_tol = mesh_size * 0.5  # Allow half mesh element from top
            
            if verbose:
                print(f"Main beam '{beam_name}' bbox: X={beam_bbox.min.X:.1f} to {beam_bbox.max.X:.1f}")
                print(f"Load location: midspan x={mid_x:.1f}mm (±{x_tol:.1f}), top z={top_z:.1f}mm (±{z_tol:.1f})")
            
            def default_load_location(nid, x, y, z, part, mesh):
                return part == beam_name and abs(x - mid_x) < x_tol and abs(z - top_z) < z_tol
            
            load_location_fn = default_load_location
        else:
            # Wrap user function to match signature
            def wrapped_load(nid, x, y, z, part, mesh):
                return load_location(x, y, z)
            load_location_fn = wrapped_load
        
        # Build load BCs
        load_bcs = []
        
        # Add self-weight loads first
        if include_self_weight:
            self_weight_loads, _ = self._generate_self_weight_loads(verbose=verbose)
            load_bcs.extend(self_weight_loads)
        
        # Add main load only if non-zero
        if load != 0.0:
            load_bcs.append(LoadBC("main_load", load_location_fn, dof=3, total_load=load))
        
        # Add any additional loads
        if additional_loads:
            load_bcs.extend(additional_loads)
        
        # Ensure frame is meshed
        meshing_result = self.mesh(
            element_size=mesh_size,
            element_size_fine=mesh_size_fine,
            verbose=verbose,
        )
        
        # Configure and run
        step_config = StepConfig(
            initial_increment=initial_increment,
            max_increments=max_increments,
        )
        config = AssemblyConfig(
            mesh_size=mesh_size,
            mesh_size_fine=mesh_size_fine,
            contact_gap=self.contact_gap,
            step=step_config,
            output_dir=output_dir,
        )
        
        return analyze_assembly(
            parts=parts,
            contacts=contact_pairs,
            fixed_bcs=fixed_bcs,
            load_bcs=load_bcs,
            meshing_result=meshing_result,
            config=config,
            verbose=verbose,
        )
