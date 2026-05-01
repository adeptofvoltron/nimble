from __future__ import annotations

import sys
from pathlib import Path

import pytest

from nimble.manifest.installer import install_skill_venv
from nimble.manifest.parser import ManifestSpec


def _make_spec(**overrides: object) -> ManifestSpec:
    defaults: dict[str, object] = {
        "name": "test-skill",
        "version": "1.0.0",
        "api_version": 1,
        "description": "A test skill",
        "entrypoint": "skill.py",
        "permissions": [],
        "dependencies": [],
        "author": "Test Author",
    }
    defaults.update(overrides)
    return ManifestSpec(**defaults)  # type: ignore[arg-type]


def test_install_skill_venv_creates_real_venv(tmp_path: Path) -> None:
    install_skill_venv(_make_spec(dependencies=[]), tmp_path)

    venv_path = tmp_path / ".nimble" / "skills" / "test-skill" / ".venv"
    assert venv_path.exists()

    if sys.platform == "win32":
        python_bin = venv_path / "Scripts" / "python.exe"
    else:
        python_bin = venv_path / "bin" / "python"
    assert python_bin.exists()


@pytest.mark.slow
def test_install_skill_venv_installs_package(tmp_path: Path) -> None:
    install_skill_venv(_make_spec(dependencies=["pip"]), tmp_path)

    venv_path = tmp_path / ".nimble" / "skills" / "test-skill" / ".venv"
    assert venv_path.exists()
