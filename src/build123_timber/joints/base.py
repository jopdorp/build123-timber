from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from build123d import Part

if TYPE_CHECKING:
    from build123_timber.elements import Timber


class JointTopology(Enum):
    L = auto()  # Corner - both ends meet
    T = auto()  # One end meets another's length
    X = auto()  # Cross through
    I = auto()  # Splice (collinear)


@dataclass
class Joint(ABC):
    main: Timber
    cross: Timber
    topology: JointTopology = field(init=False, default=JointTopology.T)

    @abstractmethod
    def get_main_feature(self) -> Part | None:
        ...

    @abstractmethod
    def get_cross_feature(self) -> Part | None:
        ...

    def apply(self) -> tuple[Timber, Timber]:
        if main_feature := self.get_main_feature():
            self.main.add_feature(main_feature)
        if cross_feature := self.get_cross_feature():
            self.cross.add_feature(cross_feature)
        return (self.main, self.cross)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(main={self.main}, cross={self.cross})"
