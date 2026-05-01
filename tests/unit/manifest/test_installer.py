from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nimble.manifest.installer import InstallError, install_skill_venv
from nimble.manifest.parser import ManifestSpec


def _make_spec(**overrides: object) -> ManifestSpec:
    defaults: dict[str, object] = {
        "name": "test-skill",
        "version": "1.0.0",
        "api_version": 1,
        "description": "A test skill",
        "entrypoint": "skill.py",
        "permissions": [],
        "dependencies": ["anthropic"],
        "author": "Test Author",
    }
    defaults.update(overrides)
    return ManifestSpec(**defaults)  # type: ignore[arg-type]


def test_skill_dir_created(tmp_path: Path) -> None:
    with patch("subprocess.run", return_value=MagicMock(returncode=0, stderr="")):
        install_skill_venv(_make_spec(dependencies=[]), tmp_path)
    assert (tmp_path / ".nimble" / "skills" / "test-skill").exists()


def test_venv_subprocess_uses_sys_executable(tmp_path: Path) -> None:
    with patch(
        "subprocess.run", return_value=MagicMock(returncode=0, stderr="")
    ) as mock:
        install_skill_venv(_make_spec(dependencies=[]), tmp_path)
    venv_call_args = mock.call_args_list[0][0][0]
    assert venv_call_args[0] == sys.executable
    assert "-m" in venv_call_args
    assert "venv" in venv_call_args


def test_pip_install_called_with_all_deps(tmp_path: Path) -> None:
    with patch(
        "subprocess.run", return_value=MagicMock(returncode=0, stderr="")
    ) as mock:
        install_skill_venv(_make_spec(dependencies=["anthropic", "openai"]), tmp_path)
    assert mock.call_count == 2
    pip_call_args = mock.call_args_list[1][0][0]
    assert "install" in pip_call_args
    assert "anthropic" in pip_call_args
    assert "openai" in pip_call_args


def test_no_pip_call_for_empty_dependencies(tmp_path: Path) -> None:
    with patch(
        "subprocess.run", return_value=MagicMock(returncode=0, stderr="")
    ) as mock:
        install_skill_venv(_make_spec(dependencies=[]), tmp_path)
    assert mock.call_count == 1


def test_venv_failure_raises_install_error(tmp_path: Path) -> None:
    with patch(
        "subprocess.run", return_value=MagicMock(returncode=1, stderr="venv error")
    ):
        with pytest.raises(InstallError, match="venv creation failed"):
            install_skill_venv(_make_spec(), tmp_path)


def test_venv_failure_cleans_up_skill_dir(tmp_path: Path) -> None:
    with patch(
        "subprocess.run", return_value=MagicMock(returncode=1, stderr="venv error")
    ):
        with pytest.raises(InstallError):
            install_skill_venv(_make_spec(), tmp_path)
    assert not (tmp_path / ".nimble" / "skills" / "test-skill").exists()


def test_pip_failure_raises_install_error(tmp_path: Path) -> None:
    side_effects = [
        MagicMock(returncode=0, stderr=""),
        MagicMock(returncode=1, stderr="No matching distribution"),
    ]
    with patch("subprocess.run", side_effect=side_effects):
        with pytest.raises(InstallError, match="pip install failed"):
            install_skill_venv(_make_spec(), tmp_path)


def test_pip_failure_cleans_up_skill_dir(tmp_path: Path) -> None:
    side_effects = [
        MagicMock(returncode=0, stderr=""),
        MagicMock(returncode=1, stderr="No matching distribution"),
    ]
    with patch("subprocess.run", side_effect=side_effects):
        with pytest.raises(InstallError):
            install_skill_venv(_make_spec(), tmp_path)
    assert not (tmp_path / ".nimble" / "skills" / "test-skill").exists()
