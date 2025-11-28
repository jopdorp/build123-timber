import pytest

from build123_timber.elements import Timber
from build123_timber.joints import LLapJoint
from build123_timber.model import TimberModel


@pytest.fixture
def empty_model():
    return TimberModel(name="TestModel")


@pytest.fixture
def model_with_elements():
    model = TimberModel(name="TestModel")
    beam1 = Timber.beam(length=2000, width=100, height=150, name="beam1")
    beam2 = Timber.beam(length=1500, width=100, height=150, name="beam2")
    post1 = Timber.post(length=2400, width=100, height=100, name="post1")
    beam1.category = "main"
    beam2.category = "cross"
    post1.category = "support"
    model.add_element(beam1)
    model.add_element(beam2)
    model.add_element(post1)
    return model


class TestTimberModel:
    def test_create_model(self):
        model = TimberModel(name="MyModel")
        assert model.name == "MyModel"
        assert len(model.elements) == 0
        assert len(model.joints) == 0

    def test_add_element(self, empty_model):
        beam = Timber.beam(length=1000, width=50, height=100)
        empty_model.add_element(beam)
        assert len(empty_model.elements) == 1
        assert beam in empty_model.elements

    def test_add_elements(self, empty_model):
        beams = [
            Timber.beam(length=1000, width=50, height=100),
            Timber.beam(length=1500, width=50, height=100),
        ]
        empty_model.add_elements(beams)
        assert len(empty_model.elements) == 2

    def test_remove_element(self, model_with_elements):
        initial_count = len(model_with_elements.elements)
        element_to_remove = model_with_elements.elements[0]
        result = model_with_elements.remove_element(element_to_remove)
        assert result is True
        assert len(model_with_elements.elements) == initial_count - 1
        assert element_to_remove not in model_with_elements.elements

    def test_remove_nonexistent_element(self, empty_model):
        beam = Timber.beam(length=1000, width=50, height=100)
        result = empty_model.remove_element(beam)
        assert result is False

    def test_find_by_category(self, model_with_elements):
        main_elements = model_with_elements.find_by_category("main")
        cross_elements = model_with_elements.find_by_category("cross")
        assert len(main_elements) == 1
        assert len(cross_elements) == 1

    def test_find_by_name(self, model_with_elements):
        results = model_with_elements.find_by_name("beam1")
        assert len(results) == 1
        assert results[0].name == "beam1"

    def test_add_joint(self, empty_model):
        beam1 = Timber.beam(length=2000, width=100, height=150)
        beam2 = Timber.beam(length=1000, width=100, height=150)
        empty_model.add_element(beam1)
        empty_model.add_element(beam2)
        joint = LLapJoint(main=beam1, cross=beam2)
        empty_model.add_joint(joint)
        assert len(empty_model.joints) == 1
        assert joint in empty_model.joints

    def test_get_joints_for_element(self, empty_model):
        beam1 = Timber.beam(length=2000, width=100, height=150)
        beam2 = Timber.beam(length=1000, width=100, height=150)
        beam3 = Timber.beam(length=1000, width=100, height=150)
        empty_model.add_elements([beam1, beam2, beam3])
        joint1 = LLapJoint(main=beam1, cross=beam2)
        joint2 = LLapJoint(main=beam1, cross=beam3)
        empty_model.add_joint(joint1)
        empty_model.add_joint(joint2)
        joints = empty_model.get_joints_for(beam1)
        assert len(joints) == 2

    def test_model_iteration(self, model_with_elements):
        element_count = 0
        for _ in model_with_elements:
            element_count += 1
        assert element_count == len(model_with_elements.elements)

    def test_model_len(self, model_with_elements):
        assert len(model_with_elements) == 3

    def test_model_repr(self, model_with_elements):
        repr_str = repr(model_with_elements)
        assert "TimberModel" in repr_str
        assert "TestModel" in repr_str


class TestModelGeometry:
    def test_get_compound(self, model_with_elements):
        compound = model_with_elements.get_compound()
        assert compound is not None

    def test_get_blanks_compound(self, model_with_elements):
        blanks = model_with_elements.get_blanks_compound()
        assert blanks is not None

    def test_apply_joints(self, empty_model):
        beam1 = Timber.beam(length=2000, width=100, height=150)
        beam2 = Timber.beam(length=1000, width=100, height=150)
        empty_model.add_element(beam1)
        empty_model.add_element(beam2)
        joint = LLapJoint(main=beam1, cross=beam2)
        empty_model.add_joint(joint)
        empty_model.apply_joints()
        assert len(beam1._features) > 0
        assert len(beam2._features) > 0


class TestModelValidationPlan:
    def test_dependency_graph_integrity_plan(self, model_with_elements):
        """TODO: Algorithm sketch
        1. Build adjacency lists per element referencing attached joints.
        2. Run graph traversal to detect cycles or disconnected subgraphs when topology should be tree-like (e.g., frames).
        3. Validate every joint references elements present in the model; flag orphaned references.
        4. Check for duplicated joint signatures (same main/cross pair + type) to avoid double application."""
        pytest.skip("Pending implementation - see plan in docstring")

    def test_compound_export_consistency_plan(self, model_with_elements):
        """TODO: Algorithm sketch
        1. Sum volumes of all element.global_shape solids.
        2. Compare against volume of model.get_compound() and blanks compound after boolean union (accounting for overlaps).
        3. Use bounding-box hashing or mesh comparison to ensure no solids are missing or duplicated during export.
        4. Run test before/after joints applied to ensure features propagate into the compound view."""
        pytest.skip("Pending implementation - see plan in docstring")

    def test_model_serialization_plan(self, model_with_elements):
        """TODO: Algorithm sketch
        1. Serialize model to chosen format (JSON/IFC/etc.).
        2. Reload into a fresh TimberModel and compare:
           a. Element counts & categories.
           b. Geometric hashes (volume + bounding boxes) per element.
           c. Joint parameter dicts.
        3. Fail test if any mismatch occurs to guarantee deterministic persistence."""
        pytest.skip("Pending implementation - see plan in docstring")
