"""The workspace exposes every package from ADR-0014, typed and versioned."""

import importlib
import tomllib
from importlib.resources import files
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ("core", "raw", "sim", "proc", "ingest", "lake", "edge", "pipelines", "api")


@pytest.mark.parametrize("short", PACKAGES)
def test_package_imports_with_its_distribution_version(short: str) -> None:
    module = importlib.import_module(f"shoalscope_{short}")
    pyproject = ROOT / "packages" / f"shoalscope-{short}" / "pyproject.toml"
    expected = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    assert module.__version__ == expected


@pytest.mark.parametrize("short", PACKAGES)
def test_package_ships_a_type_marker(short: str) -> None:
    assert files(f"shoalscope_{short}").joinpath("py.typed").is_file()


def test_root_depends_on_every_workspace_package() -> None:
    root = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    on_disk = {p.name for p in (ROOT / "packages").iterdir() if (p / "pyproject.toml").is_file()}
    assert set(root["project"]["dependencies"]) == on_disk == {f"shoalscope-{s}" for s in PACKAGES}
