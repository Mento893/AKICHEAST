"""Prüft die Architektur- und Datenschutzregeln aus CLAUDE.md im Quellcode."""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src" / "akicheast3d"

MODULE_PACKAGES = ("loading", "segmentation", "ui", "tools", "export")
NETWORK_MODULES = {
    "socket", "ssl", "http", "urllib", "urllib3", "requests", "httpx",
    "aiohttp", "ftplib", "smtplib", "websocket", "websockets",
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def source_files(directory: Path) -> list[Path]:
    return sorted(directory.rglob("*.py"))


@pytest.mark.parametrize("path", source_files(SRC / "core"), ids=lambda p: p.name)
def test_core_does_not_import_modules(path):
    forbidden = {f"akicheast3d.{package}" for package in MODULE_PACKAGES}
    for name in imported_modules(path):
        assert not any(name == f or name.startswith(f + ".") for f in forbidden), name
        assert not name.startswith("PySide6"), "Der Kern ist unabhängig von Qt"


@pytest.mark.parametrize("path", source_files(SRC), ids=lambda p: str(p.relative_to(SRC)))
def test_no_network_imports(path):
    for name in imported_modules(path):
        assert name.split(".")[0] not in NETWORK_MODULES, name
