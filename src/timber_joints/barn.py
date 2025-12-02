"""Barn frame builder - high-level API for creating barn structures.

A barn frame consists of:
- Multiple bents (portal frames) spaced along the Y axis
- Girts connecting the bents longitudinally
- Knee braces for lateral stability (both in bents and under girts)
"""

import copy
from dataclasses import dataclass, field
from typing import Optional
from build123d import Part, Location

from timber_joints.alignment import (
    BraceParams,
    JointParams,
    BentResult,
    GirtResult,
    RafterParams,
    RafterResult,
    build_complete_bent,
    add_girts_to_bents,
    add_rafters_to_barn,
)


@dataclass
class BarnConfig:
    """Configuration for a barn frame (all dimensions in mm)."""
    # Post dimensions
    post_height: float = 3000
    post_section: float = 150
    
    # Beam dimensions (cross beams spanning bents)
    beam_length: float = 5000
    beam_section: float = 150
    
    # Bent spacing (distance between bents along Y)
    bent_spacing: float = 3000
    num_bents: int = 3
    
    # Joint parameters
    tenon_length: float = 60
    shoulder_depth: float = 20
    housing_depth: float = 20
    post_top_extension: float = 300
    
    # Girt parameters (None = use post_section)
    girt_section: Optional[float] = None
    
    # Bent brace parameters (None = no braces)
    bent_brace_section: Optional[float] = 100
    bent_brace_length: float = 707.1  # ~500mm horizontal at 45°
    bent_brace_angle: float = 45.0
    
    # Girt brace parameters (None = use bent_brace values)
    girt_brace_section: Optional[float] = None
    girt_brace_length: Optional[float] = None
    girt_brace_angle: Optional[float] = None
    
    # Rafter parameters
    rafter_section: float = 100.0       # Rafter cross-section
    rafter_pitch: float = 30.0          # Roof pitch in degrees
    rafter_overhang: float = 300.0      # Eave overhang beyond girt
    num_rafters: Optional[int] = None   # Number of rafters (None = one per bent)
    
    # Legacy brace_section for backward compatibility
    brace_section: Optional[float] = None
    brace_length: Optional[float] = None
    
    # What to include
    include_girts: bool = True
    include_bent_braces: bool = True
    include_girt_braces: bool = True
    include_rafters: bool = False       # Rafters disabled by default
    
    def __post_init__(self):
        if self.girt_section is None:
            self.girt_section = self.post_section
        
        # Handle legacy brace_section parameter
        if self.brace_section is not None:
            if self.bent_brace_section == 100:  # Default value, override it
                self.bent_brace_section = self.brace_section
        if self.brace_length is not None:
            if self.bent_brace_length == 707.1:  # Default value
                self.bent_brace_length = self.brace_length
        
        # Girt braces default to bent brace values if not specified
        if self.girt_brace_section is None:
            self.girt_brace_section = self.bent_brace_section
        if self.girt_brace_length is None:
            self.girt_brace_length = self.bent_brace_length
        if self.girt_brace_angle is None:
            self.girt_brace_angle = self.bent_brace_angle

    @property
    def girt_length(self) -> float:
        return (self.num_bents - 1) * self.bent_spacing + self.post_section
    
    def get_joint_params(self) -> JointParams:
        """Convert to JointParams for alignment utilities."""
        return JointParams(
            tenon_length=self.tenon_length,
            shoulder_depth=self.shoulder_depth,
            housing_depth=self.housing_depth,
            post_top_extension=self.post_top_extension,
        )
    
    def get_bent_brace_params(self) -> Optional[BraceParams]:
        """Get BraceParams for bent braces, or None if disabled."""
        if not self.include_bent_braces or not self.bent_brace_section:
            return None
        return BraceParams(
            section=self.bent_brace_section,
            length=self.bent_brace_length,
            angle=self.bent_brace_angle,
            tenon_length=self.tenon_length,
        )
    
    def get_girt_brace_params(self) -> Optional[BraceParams]:
        """Get BraceParams for girt braces, or None if disabled."""
        if not self.include_girt_braces or not self.girt_brace_section:
            return None
        return BraceParams(
            section=self.girt_brace_section,
            length=self.girt_brace_length,
            angle=self.girt_brace_angle,
            tenon_length=self.tenon_length,
        )
    
    def get_rafter_params(self) -> Optional[RafterParams]:
        """Get RafterParams for rafters, or None if disabled."""
        if not self.include_rafters:
            return None
        return RafterParams(
            section=self.rafter_section,
            pitch_angle=self.rafter_pitch,
            overhang=self.rafter_overhang,
        )


@dataclass
class Bent:
    """A single bent (portal frame) with optional braces.
    
    This wraps BentResult with Y position information for barn assembly.
    Note: Properties return deep copies to avoid mutation from build123d's move().
    """
    result: BentResult
    y_position: float = 0
    
    @property
    def left_post(self) -> Part:
        """Left post at Y position."""
        return copy.deepcopy(self.result.left_post).move(Location((0, self.y_position, 0)))
    
    @property
    def right_post(self) -> Part:
        """Right post at Y position."""
        return copy.deepcopy(self.result.right_post).move(Location((0, self.y_position, 0)))
    
    @property
    def beam(self) -> Part:
        """Beam at Y position."""
        return copy.deepcopy(self.result.beam).move(Location((0, self.y_position, 0)))
    
    @property
    def brace_left(self) -> Optional[Part]:
        """Left brace at Y position, or None."""
        if self.result.brace_left is None:
            return None
        return copy.deepcopy(self.result.brace_left).move(Location((0, self.y_position, 0)))
    
    @property
    def brace_right(self) -> Optional[Part]:
        """Right brace at Y position, or None."""
        if self.result.brace_right is None:
            return None
        return copy.deepcopy(self.result.brace_right).move(Location((0, self.y_position, 0)))


@dataclass
class BarnFrame:
    """A complete barn frame structure.
    
    Example::
    
        config = BarnConfig(post_height=3000, beam_length=5000, num_bents=3)
        barn = BarnFrame.build(config)
        barn.show(show_object)
    """
    config: BarnConfig
    bents: list[Bent] = field(default_factory=list)
    girt_result: Optional[GirtResult] = None
    rafter_result: Optional[RafterResult] = None
    
    @property
    def left_girt(self) -> Optional[Part]:
        """Left girt, or None if not built."""
        if self.rafter_result:
            return self.rafter_result.updated_left_girt
        return self.girt_result.left_girt if self.girt_result else None
    
    @property
    def right_girt(self) -> Optional[Part]:
        """Right girt, or None if not built."""
        if self.rafter_result:
            return self.rafter_result.updated_right_girt
        return self.girt_result.right_girt if self.girt_result else None
    
    @property
    def girt_braces(self) -> list[tuple[str, Part]]:
        """List of (name, part) tuples for girt braces."""
        return self.girt_result.braces if self.girt_result else []
    
    @property
    def rafters(self) -> list[tuple[str, Part]]:
        """List of (name, part) tuples for rafters."""
        if not self.rafter_result:
            return []
        result = []
        for i, pair in enumerate(self.rafter_result.rafter_pairs):
            result.append((f"rafter_left_{i+1}", pair.left_rafter))
            result.append((f"rafter_right_{i+1}", pair.right_rafter))
        return result
    
    @classmethod
    def build(cls, config: BarnConfig) -> "BarnFrame":
        """Build a complete barn frame from configuration."""
        barn = cls(config=config)
        barn._build_bents()
        if config.include_girts:
            barn._build_girts()
        if config.include_rafters and config.include_girts:
            barn._build_rafters()
        return barn
    
    def _build_bents(self):
        """Build all bents using build_complete_bent utility."""
        config = self.config
        joint_params = config.get_joint_params()
        brace_params = config.get_bent_brace_params()
        
        for i in range(config.num_bents):
            bent_y = i * config.bent_spacing
            
            # Create bent with optional braces
            bent_result = build_complete_bent(
                post_height=config.post_height,
                post_section=config.post_section,
                beam_length=config.beam_length,
                beam_section=config.beam_section,
                joint_params=joint_params,
                brace_params=brace_params,
            )
            
            self.bents.append(Bent(result=bent_result, y_position=bent_y))
    
    def _build_girts(self):
        """Build girts connecting all bents using add_girts_to_bents utility."""
        config = self.config
        
        # Collect bent results and Y positions
        bent_results = [bent.result for bent in self.bents]
        y_positions = [bent.y_position for bent in self.bents]
        
        # Build girts with optional braces
        self.girt_result = add_girts_to_bents(
            bents=bent_results,
            y_positions=y_positions,
            girt_section=config.girt_section,
            joint_params=config.get_joint_params(),
            brace_params=config.get_girt_brace_params(),
        )
        
        # Update bents with the versions that have tenons cut for girt connection
        for i, updated_bent in enumerate(self.girt_result.updated_bents):
            self.bents[i] = Bent(result=updated_bent, y_position=y_positions[i])
    
    def _build_rafters(self):
        """Build rafters using add_rafters_to_barn utility.
        
        If num_rafters is specified, rafters are evenly distributed along the girt.
        Otherwise, one rafter pair is placed at each bent position.
        """
        if not self.girt_result:
            raise ValueError("Girts must be built before rafters")
        
        config = self.config
        rafter_params = config.get_rafter_params()
        if rafter_params is None:
            return
        
        # Calculate Y positions for rafter pairs
        if config.num_rafters is not None:
            # Evenly distribute rafters along the girt length
            # Rafter center is at y_position, so offset by half section from each end
            girt_bbox = self.girt_result.left_girt.bounding_box()
            rafter_section = rafter_params.section
            girt_start_y = girt_bbox.min.Y
            girt_end_y = girt_bbox.max.Y - rafter_section
            usable_length = girt_end_y - girt_start_y
            
            if config.num_rafters == 1:
                # Single rafter at center
                y_positions = [(girt_start_y + girt_end_y) / 2]
            else:
                # Evenly spaced rafters
                spacing = usable_length / (config.num_rafters - 1)
                y_positions = [girt_start_y + i * spacing for i in range(config.num_rafters)]
        else:
            # Default: one rafter pair at each bent position
            y_positions = [bent.y_position for bent in self.bents]
        
        # Build rafters
        self.rafter_result = add_rafters_to_barn(
            left_girt=self.girt_result.left_girt,
            right_girt=self.girt_result.right_girt,
            y_positions=y_positions,
            rafter_params=rafter_params,
        )
    
    def all_parts(self) -> list[tuple[Part, str]]:
        parts = []
        
        for i, bent in enumerate(self.bents):
            parts.append((bent.left_post, f"bent{i+1}_left_post"))
            parts.append((bent.right_post, f"bent{i+1}_right_post"))
            parts.append((bent.beam, f"bent{i+1}_beam"))
            if bent.brace_left:
                parts.append((bent.brace_left, f"bent{i+1}_brace_left"))
            if bent.brace_right:
                parts.append((bent.brace_right, f"bent{i+1}_brace_right"))
        
        if self.left_girt:
            parts.append((self.left_girt, "left_girt"))
        if self.right_girt:
            parts.append((self.right_girt, "right_girt"))
        
        for name, brace in self.girt_braces:
            parts.append((brace, name))
        
        for name, rafter in self.rafters:
            parts.append((rafter, name))
        
        return parts
    
    def show(self, show_object_func):
        """Display the barn frame using provided show_object function."""
        for part, name in self.all_parts():
            if "brace" in name.lower():
                show_object_func(part, name=name, options={"color": "orange"})
            elif "rafter" in name.lower():
                show_object_func(part, name=name, options={"color": "peru", "alpha": 0.3})
            elif "girt" in name.lower():
                show_object_func(part, name=name, options={"color": "burlywood", "alpha": 0.3})
            elif "beam" in name.lower():
                show_object_func(part, name=name, options={"color": "burlywood", "alpha": 0.3})
            elif "post" in name.lower():
                show_object_func(part, name=name, options={"color": "sienna", "alpha": 0.3})
            else:
                show_object_func(part, name=name)
    
    def summary(self) -> str:
        config = self.config
        lines = [
            f"Barn Frame Summary",
            f"==================",
            f"Bents: {config.num_bents} (spaced {config.bent_spacing}mm apart)",
            f"Posts: {config.post_height}mm tall, {config.post_section}mm section",
            f"Cross beams: {config.beam_length}mm span, {config.beam_section}mm section",
        ]
        if config.include_girts:
            lines.append(f"Girts: {config.girt_length}mm long, {config.girt_section}mm section")
        if config.bent_brace_section:
            lines.append(f"Bent braces: {config.bent_brace_section}mm section, {config.bent_brace_length:.1f}mm length, {config.bent_brace_angle}°")
        if config.girt_brace_section:
            lines.append(f"Girt braces: {config.girt_brace_section}mm section, {config.girt_brace_length:.1f}mm length, {config.girt_brace_angle}°")
        if config.include_rafters:
            lines.append(f"Rafters: {config.rafter_section}mm section, {config.rafter_pitch}° pitch, {config.rafter_overhang}mm overhang")
        
        # Count parts
        num_posts = len(self.bents) * 2
        num_beams = len(self.bents)
        num_girts = 2 if self.left_girt else 0
        num_bent_braces = sum(1 for b in self.bents if b.brace_left) * 2
        num_girt_braces = len(self.girt_braces)
        num_rafters = len(self.rafters)
        total = num_posts + num_beams + num_girts + num_bent_braces + num_girt_braces + num_rafters
        
        lines.extend([
            f"",
            f"Parts: {total} total",
            f"  - Posts: {num_posts}",
            f"  - Beams: {num_beams}",
            f"  - Girts: {num_girts}",
            f"  - Bent braces: {num_bent_braces}",
            f"  - Girt braces: {num_girt_braces}",
            f"  - Rafters: {num_rafters}",
        ])
        
        return "\n".join(lines)
    
    def to_fea_frame(self):
        """Create an FEA TimberFrame from this barn for structural analysis."""
        from timber_joints.fea import TimberFrame, MemberType
        
        frame = TimberFrame()
        
        # Add bent members
        for i, bent in enumerate(self.bents):
            frame.add_member(f"bent{i+1}_left_post", bent.left_post)
            frame.add_member(f"bent{i+1}_right_post", bent.right_post)
            frame.add_member(f"bent{i+1}_beam", bent.beam)
            if bent.brace_left:
                frame.add_member(f"bent{i+1}_brace_left", bent.brace_left, MemberType.BRACE)
            if bent.brace_right:
                frame.add_member(f"bent{i+1}_brace_right", bent.brace_right, MemberType.BRACE)
        
        # Add girts
        if self.left_girt:
            frame.add_member("left_girt", self.left_girt)
        if self.right_girt:
            frame.add_member("right_girt", self.right_girt)
        
        # Add girt braces
        for name, brace in self.girt_braces:
            frame.add_member(name, brace, MemberType.BRACE)
        
        # Add rafters
        for name, rafter in self.rafters:
            frame.add_member(name, rafter)
        
        return frame
