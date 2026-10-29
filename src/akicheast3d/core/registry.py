"""Registries, in denen sich Module anmelden.

Ein Modul meldet seine Klasse mit einem Dekorator an:

    from akicheast3d.core.registry import tools

    @tools.register
    class DistanceTool(Tool):
        name = "Distanz messen"
        ...

Damit die Anmeldung beim Start läuft, wird das Modul im `__init__.py`
seines Pakets importiert (segmentation/, tools/ oder export/).
"""

from __future__ import annotations

from typing import Generic, TypeVar

from akicheast3d.core.interfaces import Exporter, Segmenter, Tool

T = TypeVar("T")


class Registry(Generic[T]):
    def __init__(self, kind: str, base: type[T]) -> None:
        self._kind = kind
        self._base = base
        self._classes: dict[str, type[T]] = {}

    def register(self, cls: type[T]) -> type[T]:
        if not (isinstance(cls, type) and issubclass(cls, self._base)):
            raise TypeError(f"{cls!r} ist kein {self._kind}.")
        name = getattr(cls, "name", "")
        if not isinstance(name, str) or not name.strip():
            raise TypeError(f"{cls.__name__} braucht einen Namen (Attribut 'name').")
        if name in self._classes:
            raise ValueError(f"{self._kind} '{name}' ist bereits angemeldet.")
        self._classes[name] = cls
        return cls

    def names(self) -> list[str]:
        """Namen aller angemeldeten Klassen in der Reihenfolge der Anmeldung."""
        return list(self._classes)

    def create(self, name: str) -> T:
        try:
            cls = self._classes[name]
        except KeyError:
            raise KeyError(f"Kein {self._kind} mit dem Namen '{name}'.") from None
        return cls()

    def __contains__(self, name: object) -> bool:
        return name in self._classes

    def __len__(self) -> int:
        return len(self._classes)


segmenters: Registry[Segmenter] = Registry("Segmentierer", Segmenter)
tools: Registry[Tool] = Registry("Werkzeug", Tool)
exporters: Registry[Exporter] = Registry("Exporter", Exporter)
