"""Timber frame assembly - composing beams into structures."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from build123d import Part, Location, Axis, Compound

from timber_joints.beam import Beam
from timber_joints.tenon import Tenon
from timber_joints.shouldered_tenon import ShoulderedTenon
from timber_joints.alignment import (
    align_beam_in_post,
    make_post_vertical,
    create_receiving_cut,
)


class Role(Enum):
    """Structural role of a timber element."""
    POST = auto()      # Vertical support
    BEAM = auto()      # Horizontal spanning member
    GIRT = auto()      # Horizontal between posts (connects frames)
    RAFTER = auto()    # Sloped roof member
    STUD = auto()      # Vertical infill between posts
    BRACE = auto()     # Diagonal support
    PLATE = auto()     # Top plate on posts
    SILL = auto()      # Bottom plate/foundation
    PEG = auto()       # Wooden pin fastener
    WEDGE = auto()     # Locking wedge


@dataclass
class Element:
    """A timber element with its role and placement."""
    name: str
    beam: Beam
    role: Role
    location: Location = field(default_factory=lambda: Location((0, 0, 0)))
    rotation: tuple[Axis, float] = None  # Optional rotation (axis, degrees)
    shape: Part = field(init=False, repr=False)
    
    def __post_init__(self):
        """Build the positioned shape."""
        self.shape = self.beam.shape
        if self.rotation:
            axis, angle = self.rotation
            self.shape = self.shape.rotate(axis, angle)
        self.shape = self.shape.move(self.location)
    
    @classmethod
    def post(cls, name: str, length: float, width: float, height: float,
             location: Location = None) -> "Element":
        """Create a vertical post."""
        beam = Beam(length, width, height)
        loc = location or Location((0, 0, 0))
        return cls(name, beam, Role.POST, loc, rotation=(Axis.Y, -90))
    
    @classmethod
    def horizontal(cls, name: str, role: Role, length: float, width: float, height: float,
                   location: Location = None) -> "Element":
        """Create a horizontal element (beam, girt, plate, sill)."""
        beam = Beam(length, width, height)
        loc = location or Location((0, 0, 0))
        return cls(name, beam, role, loc)


@dataclass 
class Joint:
    """A joint connecting two elements."""
    name: str
    element_a: Element  # Typically the receiving member (mortise)
    element_b: Element  # Typically the inserting member (tenon)
    joint_type: str = "mortise_tenon"
    
    # Joint parameters
    tenon_width: float = None
    tenon_height: float = None  
    tenon_length: float = 60.0
    
    def __post_init__(self):
        """Set default tenon dimensions if not specified."""
        if self.tenon_width is None:
            self.tenon_width = self.element_b.beam.width / 3
        if self.tenon_height is None:
            self.tenon_height = self.element_b.beam.height * 2 / 3


@dataclass
class TimberFrame:
    """A complete timber frame assembly."""
    name: str = "Frame"
    elements: dict[str, Element] = field(default_factory=dict)
    joints: list[Joint] = field(default_factory=list)
    
    def add(self, element: Element) -> "TimberFrame":
        """Add an element to the frame."""
        self.elements[element.name] = element
        return self
    
    def add_post(self, name: str, length: float, width: float, height: float,
                 x: float = 0, y: float = 0, z: float = 0) -> "TimberFrame":
        """Add a vertical post at position."""
        elem = Element.post(name, length, width, height, Location((x, y, z)))
        return self.add(elem)
    
    def add_beam(self, name: str, length: float, width: float, height: float,
                 x: float = 0, y: float = 0, z: float = 0,
                 role: Role = Role.BEAM) -> "TimberFrame":
        """Add a horizontal beam at position."""
        elem = Element.horizontal(name, role, length, width, height, Location((x, y, z)))
        return self.add(elem)
    
    def join(self, element_a_name: str, element_b_name: str,
             joint_type: str = "mortise_tenon",
             tenon_length: float = 60.0) -> "TimberFrame":
        """Create a joint between two elements."""
        elem_a = self.elements[element_a_name]
        elem_b = self.elements[element_b_name]
        joint = Joint(
            name=f"{element_a_name}_{element_b_name}",
            element_a=elem_a,
            element_b=elem_b,
            joint_type=joint_type,
            tenon_length=tenon_length,
        )
        self.joints.append(joint)
        return self
    
    def join_shouldered_tenon(
        self,
        post_name: str,
        beam_name: str,
        at_start: bool = True,
        tenon_length: float = 60.0,
        shoulder_depth: float = 20.0,
        housing_depth: float = 20.0,
        post_top_extension: float = 40.0,
    ) -> "TimberFrame":
        """Join a beam to a post with a shouldered tenon joint.
        
        Args:
            post_name: Name of the post element (receives mortise)
            beam_name: Name of the beam element (gets tenon)
            at_start: If True, tenon at beam start (left); if False, at end (right)
            tenon_length: Length of the tenon projection
            shoulder_depth: Depth of the angled shoulder
            housing_depth: How far from post edge the mortise stops
            post_top_extension: Extra mortise depth above beam
        """
        post_elem = self.elements[post_name]
        beam_elem = self.elements[beam_name]
        
        post = post_elem.beam
        beam = beam_elem.beam
        
        # Check if beam already has been positioned by a previous joint
        beam_positioned = hasattr(beam_elem, '_beam_origin')
        
        # Default tenon dimensions: 1/3 width, 2/3 height
        tenon_width = beam.width / 3
        tenon_height = beam.height * 2 / 3
        
        # Create shouldered tenon on beam (in beam's local coords)
        beam_with_tenon = ShoulderedTenon(
            beam=beam,
            tenon_width=tenon_width,
            tenon_height=tenon_height,
            tenon_length=tenon_length,
            shoulder_depth=shoulder_depth,
            at_start=at_start,
        )
        
        # Make post vertical (in post's local coords)
        vertical_post = make_post_vertical(post.shape)
        
        drop_depth = beam.height
        blind_offset = post.height - housing_depth - tenon_length
        
        if not beam_positioned:
            # FIRST JOINT: Position beam relative to post, post stays at its location
            
            # Align beam to post (post at origin)
            positioned_beam, _, _ = align_beam_in_post(
                beam_shape=beam_with_tenon.shape,
                beam_length=beam.length,
                beam_width=beam.width,
                beam_height=beam.height,
                post_shape=vertical_post,
                post_length=post.length,
                post_width=post.width,
                post_height=post.height,
                drop_depth=drop_depth,
                at_start=True,  # First joint always at beam start
                move_post=False,
            )
            
            # Create mortise cut shape
            beam_for_cut = positioned_beam.move(Location((blind_offset, 0, -post_top_extension)))
            post_with_mortise = create_receiving_cut(beam_for_cut, vertical_post)
            
            # Move both to post's world location
            world_loc = post_elem.location
            post_elem.shape = post_with_mortise.move(world_loc)
            beam_elem.shape = positioned_beam.move(world_loc)
            
            # Remember beam's world origin for second joint
            beam_elem._beam_origin = world_loc
            
        else:
            # SECOND JOINT: Beam already positioned, position post at beam's other end
            
            beam_origin = beam_elem._beam_origin
            
            # Cut the second tenon into the existing beam shape
            # The tenon cut is the material removed: original - tenoned
            tenon_cut = beam.shape - beam_with_tenon.shape
            tenon_cut_at_origin = tenon_cut.move(beam_origin)
            beam_elem.shape = beam_elem.shape - tenon_cut_at_origin
            
            # Calculate where the right post should be:
            # Beam origin is at left post, beam extends in +X
            # Right post should be at beam_origin.X + beam_length - post_height
            origin_pos = beam_origin.position
            post_x = origin_pos.X + beam.length
            post_y = origin_pos.Y + (beam.width - post.width) / 2
            post_z = origin_pos.Z  # Same Z level
            
            # Position post at beam end and create mortise
            # For this we align beam (with tenon at end) to post, then extract the offset
            beam_at_end, positioned_post, _ = align_beam_in_post(
                beam_shape=beam_with_tenon.shape,
                beam_length=beam.length,
                beam_width=beam.width,
                beam_height=beam.height,
                post_shape=vertical_post,
                post_length=post.length,
                post_width=post.width,
                post_height=post.height,
                drop_depth=drop_depth,
                at_start=False,  # Joint at beam end
                move_post=False,
            )
            
            # Create mortise in post
            beam_for_cut = beam_at_end.move(Location((blind_offset, 0, -post_top_extension)))
            post_with_mortise = create_receiving_cut(beam_for_cut, positioned_post)
            
            # Move post to its world position (at beam end)
            post_world_loc = Location((post_x, post_y, post_z))
            post_elem.shape = post_with_mortise.move(post_world_loc)
        
        # Record joint
        joint = Joint(
            name=f"{post_name}_{beam_name}_shouldered",
            element_a=post_elem,
            element_b=beam_elem,
            joint_type="shouldered_tenon",
            tenon_width=tenon_width,
            tenon_height=tenon_height,
            tenon_length=tenon_length,
        )
        self.joints.append(joint)
        
        return self
    
    @property
    def shape(self) -> Part:
        """Combine all elements into a single shape."""
        if not self.elements:
            return Part()
        shapes = [e.shape for e in self.elements.values()]
        return Compound(shapes)
    
    def by_role(self, role: Role) -> list[Element]:
        """Get all elements with a specific role."""
        return [e for e in self.elements.values() if e.role == role]
    
    @property
    def posts(self) -> list[Element]:
        return self.by_role(Role.POST)
    
    @property
    def beams(self) -> list[Element]:
        return self.by_role(Role.BEAM)
    
    @property
    def girts(self) -> list[Element]:
        return self.by_role(Role.GIRT)
    
    @property
    def rafters(self) -> list[Element]:
        return self.by_role(Role.RAFTER)


# =============================================================================
# FRAME TEMPLATES
# =============================================================================

def simple_bent(
    post_height: float = 3000,
    post_section: float = 150,
    beam_length: float = 4000,
    beam_section: float = 150,
    name: str = "Bent",
) -> TimberFrame:
    """Create a simple bent (two posts with connecting beam).
    
    A bent is the basic unit of timber framing - a 2D portal frame.
    
         ┌─────────────────────┐  <- Beam (tie beam/plate)
         │                     │
         │                     │
         │                     │  <- Posts
         │                     │
         ╧                     ╧
    """
    frame = TimberFrame(name)
    
    # Two posts
    frame.add_post("post_left", post_height, post_section, post_section, x=0, y=0, z=0)
    frame.add_post("post_right", post_height, post_section, post_section, 
                   x=beam_length - post_section, y=0, z=0)
    
    # Connecting beam on top
    frame.add_beam("beam", beam_length, beam_section, beam_section,
                   x=-post_section, y=0, z=post_height, role=Role.PLATE)
    
    return frame


def bay_frame(
    width: float = 4000,
    depth: float = 3000,
    height: float = 3000,
    post_section: float = 150,
    beam_section: float = 150,
    name: str = "Bay",
) -> TimberFrame:
    """Create a bay frame (4 posts with connecting beams/girts).
    
    A bay is a 3D structural unit bounded by posts at corners.
    
    Top view:
        G ═══════════ G    G = Girt
        ║             ║
        B             B    B = Beam  
        ║             ║
        G ═══════════ G
    """
    frame = TimberFrame(name)
    ps = post_section
    
    # Four corner posts
    frame.add_post("post_fl", height, ps, ps, x=0, y=0, z=0)         # Front-left
    frame.add_post("post_fr", height, ps, ps, x=width-ps, y=0, z=0)  # Front-right
    frame.add_post("post_bl", height, ps, ps, x=0, y=depth-ps, z=0)  # Back-left
    frame.add_post("post_br", height, ps, ps, x=width-ps, y=depth-ps, z=0)  # Back-right
    
    # Front and back beams (span width)
    frame.add_beam("beam_front", width, beam_section, beam_section,
                   x=-ps, y=0, z=height, role=Role.BEAM)
    frame.add_beam("beam_back", width, beam_section, beam_section,
                   x=-ps, y=depth-ps, z=height, role=Role.BEAM)
    
    # Side girts (span depth)  
    frame.add_beam("girt_left", depth, beam_section, beam_section,
                   x=-ps, y=0, z=height, role=Role.GIRT)
    frame.add_beam("girt_right", depth, beam_section, beam_section,
                   x=width-2*ps, y=0, z=height, role=Role.GIRT)
    
    return frame
