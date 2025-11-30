"""Barn frame builder - high-level API for creating barn structures.

A barn frame consists of:
- Multiple bents (portal frames) spaced along the Y axis
- Girts connecting the bents longitudinally
- Knee braces for lateral stability (both in bents and under girts)
"""

from dataclasses import dataclass, field
from typing import Optional
from build123d import Part, Location, Axis

from timber_joints.beam import Beam
from timber_joints.tenon import Tenon
from timber_joints.alignment import (
    build_complete_bent,
    create_receiving_cut,
    create_brace_for_bent,
    create_brace_for_girt,
)
from timber_joints.utils import create_vertical_cut


@dataclass
class BarnConfig:
    """Configuration for a barn frame.
    
    All dimensions in millimeters.
    """
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
    
    # Legacy brace_section for backward compatibility
    brace_section: Optional[float] = None
    brace_length: Optional[float] = None
    
    # What to include
    include_girts: bool = True
    include_bent_braces: bool = True
    include_girt_braces: bool = True
    
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
        """Total girt length spanning all bents."""
        return (self.num_bents - 1) * self.bent_spacing + self.post_section


@dataclass
class Bent:
    """A single bent (portal frame) with optional braces."""
    left_post: Part
    right_post: Part
    beam: Part
    brace_left: Optional[Part] = None
    brace_right: Optional[Part] = None
    y_position: float = 0


@dataclass
class BarnFrame:
    """A complete barn frame structure.
    
    Example::
    
        config = BarnConfig(
            post_height=3000,
            beam_length=5000,
            num_bents=3,
            bent_spacing=3000,
        )
        barn = BarnFrame.build(config)
        
        # Access parts
        for bent in barn.bents:
            show_object(bent.left_post)
            show_object(bent.beam)
        
        show_object(barn.left_girt)
        show_object(barn.right_girt)
    """
    config: BarnConfig
    bents: list[Bent] = field(default_factory=list)
    left_girt: Optional[Part] = None
    right_girt: Optional[Part] = None
    girt_braces: list[tuple[str, Part]] = field(default_factory=list)
    
    @classmethod
    def build(cls, config: BarnConfig) -> "BarnFrame":
        """Build a complete barn frame from configuration."""
        barn = cls(config=config)
        barn._build_bents()
        if config.include_girts:
            barn._build_girts()
        if config.include_girt_braces and config.girt_brace_section:
            barn._build_girt_braces()
        return barn
    
    def _build_bents(self):
        """Build all bents and move them to their Y positions."""
        config = self.config
        
        # Tenon dimensions for post tops (if girts are used)
        post_tenon_x = config.post_section * 2 / 3
        post_tenon_y = config.post_section / 3
        
        for i in range(config.num_bents):
            bent_y = i * config.bent_spacing
            
            # Build the bent
            left_post, right_post, beam, _ = build_complete_bent(
                post_height=config.post_height,
                post_section=config.post_section,
                beam_length=config.beam_length,
                beam_section=config.beam_section,
                tenon_length=config.tenon_length,
                shoulder_depth=config.shoulder_depth,
                housing_depth=config.housing_depth,
                post_top_extension=config.post_top_extension,
            )
            
            # Add tenons to post tops if we're including girts
            if config.include_girts:
                left_post = create_vertical_cut(
                    left_post, Tenon, at_top=True,
                    tenon_width=post_tenon_x, tenon_height=post_tenon_y,
                    tenon_length=config.tenon_length,
                )
                right_post = create_vertical_cut(
                    right_post, Tenon, at_top=True,
                    tenon_width=post_tenon_x, tenon_height=post_tenon_y,
                    tenon_length=config.tenon_length,
                )
            
            # Create braces if requested
            brace_left = None
            brace_right = None
            if config.include_bent_braces and config.bent_brace_section:
                brace_left = create_brace_for_bent(
                    post=left_post, beam=beam,
                    brace_section=config.bent_brace_section,
                    brace_length=config.bent_brace_length,
                    angle=config.bent_brace_angle,
                    at_beam_start=True,
                ).shape
                brace_right = create_brace_for_bent(
                    post=right_post, beam=beam,
                    brace_section=config.bent_brace_section,
                    brace_length=config.bent_brace_length,
                    angle=config.bent_brace_angle,
                    at_beam_start=False,
                ).shape
            
            # Move all parts to Y position
            left_post = left_post.move(Location((0, bent_y, 0)))
            right_post = right_post.move(Location((0, bent_y, 0)))
            beam = beam.move(Location((0, bent_y, 0)))
            if brace_left:
                brace_left = brace_left.move(Location((0, bent_y, 0)))
            if brace_right:
                brace_right = brace_right.move(Location((0, bent_y, 0)))
            
            self.bents.append(Bent(
                left_post=left_post,
                right_post=right_post,
                beam=beam,
                brace_left=brace_left,
                brace_right=brace_right,
                y_position=bent_y,
            ))
    
    def _build_girts(self):
        """Build girts connecting all bents."""
        config = self.config
        
        # Get post X positions from first bent
        first_bent = self.bents[0]
        left_bbox = first_bent.left_post.bounding_box()
        right_bbox = first_bent.right_post.bounding_box()
        left_post_x = (left_bbox.min.X + left_bbox.max.X) / 2
        right_post_x = (right_bbox.min.X + right_bbox.max.X) / 2
        
        # Z position for girts (at top of posts, minus tenon/housing)
        girt_z = left_bbox.max.Z - config.tenon_length - config.housing_depth
        
        # Create left girt
        left_girt_beam = Beam(length=config.girt_length, width=config.girt_section, height=config.girt_section)
        left_girt = left_girt_beam.shape.rotate(Axis.Z, 90)
        left_girt_bbox = left_girt.bounding_box()
        left_girt = left_girt.move(Location((
            left_post_x - (left_girt_bbox.min.X + left_girt_bbox.max.X) / 2,
            -left_girt_bbox.min.Y,
            girt_z - left_girt_bbox.min.Z,
        )))
        
        # Create right girt
        right_girt_beam = Beam(length=config.girt_length, width=config.girt_section, height=config.girt_section)
        right_girt = right_girt_beam.shape.rotate(Axis.Z, 90)
        right_girt_bbox = right_girt.bounding_box()
        right_girt = right_girt.move(Location((
            right_post_x - (right_girt_bbox.min.X + right_girt_bbox.max.X) / 2,
            -right_girt_bbox.min.Y,
            girt_z - right_girt_bbox.min.Z,
        )))
        
        # Cut mortises in girts for each bent's posts
        for bent in self.bents:
            left_girt = create_receiving_cut(bent.left_post, left_girt)
            right_girt = create_receiving_cut(bent.right_post, right_girt)
        
        self.left_girt = left_girt
        self.right_girt = right_girt
    
    def _build_girt_braces(self):
        """Build braces running under girts (longitudinal bracing)."""
        if not self.left_girt or not self.right_girt:
            return
        
        config = self.config
        
        for i, bent in enumerate(self.bents):
            # First bent: braces toward +Y only
            if i == 0:
                self._add_girt_brace(bent, toward_plus_y=True, index=i)
            # Last bent: braces toward -Y only
            elif i == config.num_bents - 1:
                self._add_girt_brace(bent, toward_plus_y=False, index=i)
            # Middle bents: braces both directions
            else:
                self._add_girt_brace(bent, toward_plus_y=True, index=i, suffix="a")
                self._add_girt_brace(bent, toward_plus_y=False, index=i, suffix="b")
    
    def _add_girt_brace(self, bent: Bent, toward_plus_y: bool, index: int, suffix: str = ""):
        """Add girt braces for a single bent."""
        config = self.config
        at_girt_start = not toward_plus_y  # at_girt_start=True means toward -Y
        
        # Left side brace
        left_brace = create_brace_for_girt(
            post=bent.left_post, girt=self.left_girt,
            brace_section=config.girt_brace_section,
            brace_length=config.girt_brace_length,
            angle=config.girt_brace_angle,
            at_girt_start=at_girt_start,
        ).shape
        self.girt_braces.append((f"girt_brace_left_{index+1}{suffix}", left_brace))
        
        # Right side brace
        right_brace = create_brace_for_girt(
            post=bent.right_post, girt=self.right_girt,
            brace_section=config.girt_brace_section,
            brace_length=config.girt_brace_length,
            angle=config.girt_brace_angle,
            at_girt_start=at_girt_start,
        ).shape
        self.girt_braces.append((f"girt_brace_right_{index+1}{suffix}", right_brace))
    
    def all_parts(self) -> list[tuple[Part, str]]:
        """Get all parts with their names for visualization."""
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
        
        return parts
    
    def show(self, show_object_func):
        """Display the barn frame using provided show_object function.
        
        Args:
            show_object_func: The show_object function from ocp_vscode
        """
        for part, name in self.all_parts():
            if "brace" in name.lower():
                show_object_func(part, name=name, options={"color": "orange"})
            elif "girt" in name.lower():
                show_object_func(part, name=name, options={"color": "burlywood", "alpha": 0.3})
            elif "beam" in name.lower():
                show_object_func(part, name=name, options={"color": "burlywood", "alpha": 0.3})
            elif "post" in name.lower():
                show_object_func(part, name=name, options={"color": "sienna", "alpha": 0.3})
            else:
                show_object_func(part, name=name)
    
    def summary(self) -> str:
        """Get a summary of the barn frame configuration."""
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
        
        # Count parts
        num_posts = len(self.bents) * 2
        num_beams = len(self.bents)
        num_girts = 2 if self.left_girt else 0
        num_bent_braces = sum(1 for b in self.bents if b.brace_left) * 2
        num_girt_braces = len(self.girt_braces)
        total = num_posts + num_beams + num_girts + num_bent_braces + num_girt_braces
        
        lines.extend([
            f"",
            f"Parts: {total} total",
            f"  - Posts: {num_posts}",
            f"  - Beams: {num_beams}",
            f"  - Girts: {num_girts}",
            f"  - Bent braces: {num_bent_braces}",
            f"  - Girt braces: {num_girt_braces}",
        ])
        
        return "\n".join(lines)
    
    def to_fea_frame(self):
        """Create an FEA TimberFrame from this barn for structural analysis.
        
        Returns:
            timber_joints.fea.TimberFrame ready for analyze()
            
        Example:
            barn = BarnFrame.build(config)
            fea_frame = barn.to_fea_frame()
            result = fea_frame.analyze(output_dir=Path("output"))
        """
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
        
        return frame
