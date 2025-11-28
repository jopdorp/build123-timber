from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator

from build123d import Compound

if TYPE_CHECKING:
    from build123_timber.elements import Timber
    from build123_timber.joints import Joint


@dataclass
class TimberModel:
    name: str = "TimberModel"
    elements: list[Timber] = field(default_factory=list)
    joints: list[Joint] = field(default_factory=list)

    def add_element(self, element: Timber) -> None:
        self.elements.append(element)

    def add_elements(self, elements: list[Timber]) -> None:
        self.elements.extend(elements)

    def remove_element(self, element: Timber) -> bool:
        try:
            self.elements.remove(element)
            return True
        except ValueError:
            return False

    def add_joint(self, joint: Joint) -> None:
        self.joints.append(joint)
        joint.main._joints.append(joint)
        joint.cross._joints.append(joint)

    def apply_joints(self) -> None:
        for joint in self.joints:
            joint.apply()

    def get_compound(self) -> Compound:
        return Compound([e.global_shape for e in self.elements])

    def get_blanks_compound(self) -> Compound:
        return Compound([e.blank.move(e.location) for e in self.elements])

    def find_by_category(self, category: str) -> list[Timber]:
        return [e for e in self.elements if e.category == category]

    def find_by_name(self, name: str) -> list[Timber]:
        return [e for e in self.elements if e.name == name]

    def get_joints_for(self, element: Timber) -> list[Joint]:
        return [j for j in self.joints if j.main is element or j.cross is element]

    def __iter__(self) -> Iterator[Timber]:
        return iter(self.elements)

    def __len__(self) -> int:
        return len(self.elements)

    def __repr__(self) -> str:
        return f"TimberModel('{self.name}', elements={len(self.elements)}, joints={len(self.joints)})"
