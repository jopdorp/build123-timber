"""Base class for timber joints."""

from dataclasses import dataclass, field
from typing import Union
from build123d import Part
from timber_joints.beam import Beam
from timber_joints.utils import get_shape_dimensions


@dataclass
class BaseJoint:
    """Base class for timber joints that provides common dimension extraction.
    
    All joint classes that operate on beams can inherit from this to get
    automatic shape and dimension extraction from either Beam objects or Parts.
    
    Subclasses should:
    1. Define their additional fields BEFORE calling super().__post_init__()
    2. Implement the `shape` property to create the joint geometry
    """
    
    beam: Union[Beam, Part]
    
    # Computed dimensions (from bounding box)
    _input_shape: Part = field(init=False, repr=False)
    _length: float = field(init=False, repr=False)
    _width: float = field(init=False, repr=False)
    _height: float = field(init=False, repr=False)
    # Bounding box offsets (to handle shapes that don't start at origin)
    _bbox_min_x: float = field(init=False, repr=False)
    _bbox_max_x: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Extract dimensions from beam."""
        self._input_shape, self._length, self._width, self._height = get_shape_dimensions(self.beam)
        # Also store the actual bbox positions for correct positioning
        bbox = self._input_shape.bounding_box()
        self._bbox_min_x = bbox.min.X
        self._bbox_max_x = bbox.max.X
    
    @property
    def shape(self) -> Part:
        """Create the joint geometry. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement shape property")
