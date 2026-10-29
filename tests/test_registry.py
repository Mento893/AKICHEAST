from pathlib import Path

import numpy as np
import pytest

from akicheast3d.core import (
    Exporter,
    Registry,
    Segmenter,
    Structure,
    Tool,
    Volume,
    exporters,
    segmenters,
    tools,
)


class DummySegmenter(Segmenter):
    name = "Dummy"

    def segment(self, volume, progress=None):
        if progress:
            progress(1.0)
        return [Structure("Alles", np.ones(volume.hu.shape), color=(1.0, 1.0, 1.0))]


class DummyTool(Tool):
    name = "Dummy-Werkzeug"

    def create_panel(self, context):
        return None


def test_register_and_create():
    registry = Registry("Segmentierer", Segmenter)
    assert registry.register(DummySegmenter) is DummySegmenter
    assert "Dummy" in registry
    assert registry.names() == ["Dummy"]
    assert len(registry) == 1

    segmenter = registry.create("Dummy")
    volume = Volume(np.zeros((2, 2, 2)), spacing=(1.0, 1.0, 1.0))
    reported = []
    result = segmenter.segment(volume, reported.append)
    assert result[0].mask.shape == volume.hu.shape
    assert reported == [1.0]


def test_register_works_as_decorator():
    registry = Registry("Werkzeug", Tool)

    @registry.register
    class Measure(Tool):
        name = "Messen"

        def create_panel(self, context):
            return None

    assert isinstance(registry.create("Messen"), Measure)


def test_duplicate_name_raises():
    registry = Registry("Segmentierer", Segmenter)
    registry.register(DummySegmenter)
    with pytest.raises(ValueError):
        registry.register(DummySegmenter)


def test_wrong_base_class_raises():
    registry = Registry("Segmentierer", Segmenter)
    with pytest.raises(TypeError):
        registry.register(DummyTool)


def test_missing_name_raises():
    class Nameless(Segmenter):
        def segment(self, volume, progress=None):
            return []

    with pytest.raises(TypeError):
        Registry("Segmentierer", Segmenter).register(Nameless)


def test_unknown_name_raises():
    with pytest.raises(KeyError):
        Registry("Exporter", Exporter).create("Gibt es nicht")


def test_interfaces_are_abstract():
    for interface in (Segmenter, Tool, Exporter):
        with pytest.raises(TypeError):
            interface()


def test_exporter_receives_path(tmp_path):
    class TextExporter(Exporter):
        name = "Text"
        file_filter = "Text (*.txt)"

        def export(self, context, path: Path):
            path.write_text(context.session.series_description, encoding="utf-8")

    class Context:
        class session:
            series_description = "Thorax"

        def render_image(self):
            return np.zeros((2, 2, 3), dtype=np.uint8)

    target = tmp_path / "out.txt"
    TextExporter().export(Context(), target)
    assert target.read_text(encoding="utf-8") == "Thorax"


def test_global_registries_exist():
    assert segmenters.names() is not None
    assert tools.names() is not None
    assert exporters.names() is not None
