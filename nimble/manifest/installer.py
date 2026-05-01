from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from nimble.manifest.parser import ManifestSpec
from nimble.platform import is_windows


class InstallError(Exception):
    """Raised when venv creation or pip dependency installation fails."""


def _venv_pip(venv_path: Path) -> Path:
    if is_windows():
        return venv_path / "Scripts" / "pip.exe"
    return venv_path / "bin" / "pip"


def install_skill_venv(spec: ManifestSpec, repo_root: Path) -> None:
    """Create .nimble/skills/<name>/.venv/ and pip-install declared dependencies."""
    skill_dir = repo_root / ".nimble" / "skills" / spec.name
    venv_path = skill_dir / ".venv"

    try:
        skill_dir.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise InstallError(f"venv creation failed: {result.stderr.strip()}")

        if spec.dependencies:
            result = subprocess.run(
                [str(_venv_pip(venv_path)), "install"] + list(spec.dependencies),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise InstallError(f"pip install failed:\n{result.stderr.strip()}")

    except InstallError:
        shutil.rmtree(skill_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(skill_dir, ignore_errors=True)
        raise InstallError(str(exc)) from exc
