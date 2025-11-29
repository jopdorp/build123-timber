"""High-level FEA for timber frames.

Provides a simple API that infers assembly structure from frame geometry.
Parts are automatically classified as posts (vertical) or beams (horizontal),
and contacts/boundary conditions follow from spatial relationships.
"""

import copy
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Callable

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
from .calculix import (
    GrainOrientation,
    BEAM_HORIZONTAL_X,
    POST_VERTICAL_Z,
)


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


@dataclass
class TimberFrame:
    """A timber frame assembly for FEA analysis.
    
    Automatically detects:
    - Member types (post vs beam) from geometry
    - Contacts between adjacent members
    - Fixed supports at post bases
    """
    members: List[FrameMember] = field(default_factory=list)
    contact_gap: float = 0.5  # Gap for contact analysis
    
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
                    # Beam is typically the slave surface (part_a)
                    if m1.is_beam and m2.is_post:
                        contacts.append((m1.name, m2.name))
                    elif m2.is_beam and m1.is_post:
                        contacts.append((m2.name, m1.name))
                    else:
                        contacts.append((m1.name, m2.name))
        
        return contacts
    
    def _bboxes_overlap(self, b1, b2, margin: float) -> bool:
        """Check if two bounding boxes overlap within margin."""
        return not (
            b1.max.X + margin < b2.min.X or b2.max.X + margin < b1.min.X or
            b1.max.Y + margin < b2.min.Y or b2.max.Y + margin < b1.min.Y or
            b1.max.Z + margin < b2.min.Z or b2.max.Z + margin < b1.min.Z
        )
    
    def analyze(
        self,
        load: float = 10000.0,
        load_location: Optional[Callable[[float, float, float], bool]] = None,
        additional_loads: Optional[List[LoadBC]] = None,
        mesh_size: float = 50.0,
        mesh_size_fine: float = 20.0,
        output_dir: Path = None,
        verbose: bool = True,
    ) -> AssemblyResult:
        """Run FEA analysis on the frame.
        
        Automatically:
        - Creates contact gap on beams
        - Detects contacts between members
        - Fixes posts at their bases
        - Applies load at beam midspan (or custom location)
        
        Args:
            load: Total load to apply (N), negative for downward
            load_location: Optional function (x,y,z) -> bool for load nodes.
                          Defaults to beam midspan top surface.
            additional_loads: Optional list of additional LoadBC objects
            mesh_size: Base mesh element size (mm)
            mesh_size_fine: Fine mesh at contacts (mm)
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
        
        load_bcs = [LoadBC("main_load", load_location_fn, dof=3, total_load=load)]
        
        # Add any additional loads
        if additional_loads:
            load_bcs.extend(additional_loads)
        
        # Configure and run
        config = AssemblyConfig(
            mesh_size=mesh_size,
            mesh_size_fine=mesh_size_fine,
            contact_gap=self.contact_gap,
            output_dir=output_dir,
        )
        
        return analyze_assembly(
            parts=parts,
            contacts=contact_pairs,
            fixed_bcs=fixed_bcs,
            load_bcs=load_bcs,
            config=config,
            verbose=verbose,
        )
