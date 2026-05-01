# Story 6.3: Per-Skill Venv Creation and Dependency Installation

Status: done

## Story

As a user installing a community skill,
I want the skill's pip dependencies installed into an isolated virtual environment,
so that they never conflict with my system Python or other skills' dependencies.

## Acceptance Criteria

1. **Given** the user confirms the install
   **When** `nimble add` proceeds
   **Then** a venv is created at `.nimble/skills/<name>/.venv/` using `python -m venv` (FR22)

2. **Given** the skill's `manifest.yaml` declares `dependencies: [anthropic]`
   **When** the venv is created
   **Then** `pip install anthropic` runs into the skill's venv — not the system Python or daemon env (FR23)

3. **Given** a dependency installation fails (e.g. package not found on PyPI)
   **When** pip exits non-zero
   **Then** the partially created venv is cleaned up, `config.yaml` is not modified, and a clear error is printed (NFR14)

4. **Given** `nimble add` excluding pip download completes
   **When** timing is measured
   **Then** all steps except the pip network download complete in under 10 seconds (NFR3)

## Tasks / Subtasks

- [x] Task 1: Create `nimble/manifest/installer.py` (AC: 1, 2, 3, 4)
  - [x] Add `InstallError(Exception)` class — raised for all venv/pip failures
  - [x] Add `_venv_pip(venv_path: Path) -> Path` — returns `venv_path / "Scripts" / "pip.exe"` on Windows, `venv_path / "bin" / "pip"` otherwise; import `from nimble.platform import is_windows`
  - [x] Add `install_skill_venv(spec: ManifestSpec, repo_root: Path) -> None`:
    - Compute `skill_dir = repo_root / ".nimble" / "skills" / spec.name`
    - Compute `venv_path = skill_dir / ".venv"`
    - `skill_dir.mkdir(parents=True, exist_ok=True)` — creates `.nimble/skills/<name>/`
    - Run `subprocess.run([sys.executable, "-m", "venv", str(venv_path)], capture_output=True, text=True)` — use `sys.executable`, NOT `"python"` or `"python3"`
    - If `returncode != 0`: cleanup and raise `InstallError(f"venv creation failed: {result.stderr.strip()}")`
    - If `spec.dependencies` is non-empty: run `subprocess.run([str(_venv_pip(venv_path)), "install"] + list(spec.dependencies), capture_output=True, text=True)` — install ALL deps in one invocation
    - If pip `returncode != 0`: cleanup and raise `InstallError(f"pip install failed:\n{result.stderr.strip()}")`
    - Cleanup pattern: wrap entire body in `try/except` — on `InstallError` or unexpected exception: `shutil.rmtree(skill_dir, ignore_errors=True)` then re-raise (wrap non-`InstallError` as `InstallError`)
  - [x] Module-level imports: `from __future__ import annotations`, `import shutil`, `import subprocess`, `import sys`, `from pathlib import Path`, `from nimble.manifest.parser import ManifestSpec`, `from nimble.platform import is_windows`

- [x] Task 2: Update `nimble/cli/commands.py` — replace the placeholder line (AC: 1, 2, 3)
  - [x] Delete the placeholder: `typer.echo(f"Skill '{spec.name}' confirmed — installation is not implemented yet.")`
  - [x] In its place, add lazy import (inside `add()` function body, after the existing `from nimble.manifest.parser import ...`): `from nimble.manifest.installer import InstallError, install_skill_venv`
  - [x] Add progress echo: `typer.echo(f"Installing '{spec.name}'...")`
  - [x] Call `install_skill_venv(spec, _repo_root())` inside `try/except InstallError as exc: typer.echo(str(exc), err=True); raise typer.Exit(1)`
  - [x] On success: `typer.echo(f"Dependencies installed for '{spec.name}'.")`

- [x] Task 3: Unit tests in `tests/unit/manifest/test_installer.py` (AC: 1, 2, 3)
  - [x] Imports: `from unittest.mock import MagicMock, patch`, `import pytest`, `from pathlib import Path`, `from nimble.manifest.installer import InstallError, install_skill_venv`, `from nimble.manifest.parser import ManifestSpec`
  - [x] Add `_make_spec(**overrides)` helper returning `ManifestSpec` with defaults `name="test-skill", version="1.0.0", api_version=1, description="A test skill", entrypoint="skill.py", permissions=[], dependencies=["anthropic"], author="Test Author"`
  - [x] `test_skill_dir_created(tmp_path)` — patch `subprocess.run` returning `MagicMock(returncode=0, stderr="")`, call `install_skill_venv(_make_spec(dependencies=[]), tmp_path)`; assert `(tmp_path / ".nimble" / "skills" / "test-skill").exists()`
  - [x] `test_venv_subprocess_uses_sys_executable(tmp_path)` — patch `subprocess.run`, call with `dependencies=[]`; assert first call's argv[0] is `sys.executable` and argv contains `"-m"` and `"venv"`
  - [x] `test_pip_install_called_with_all_deps(tmp_path)` — patch `subprocess.run`, call with `dependencies=["anthropic", "openai"]`; assert `mock.call_count == 2`; assert pip call contains `"install"`, `"anthropic"`, `"openai"` all in the same argv
  - [x] `test_no_pip_call_for_empty_dependencies(tmp_path)` — patch `subprocess.run`, call with `dependencies=[]`; assert `mock.call_count == 1` (venv only, no pip)
  - [x] `test_venv_failure_raises_install_error(tmp_path)` — patch `subprocess.run` returning `returncode=1, stderr="venv error"`; assert `pytest.raises(InstallError, match="venv creation failed")`
  - [x] `test_venv_failure_cleans_up_skill_dir(tmp_path)` — same as above; after exception, assert `(tmp_path / ".nimble" / "skills" / "test-skill").exists()` is `False`
  - [x] `test_pip_failure_raises_install_error(tmp_path)` — patch `subprocess.run` with `side_effect=[MagicMock(returncode=0, stderr=""), MagicMock(returncode=1, stderr="No matching distribution")]`; assert `pytest.raises(InstallError, match="pip install failed")`
  - [x] `test_pip_failure_cleans_up_skill_dir(tmp_path)` — same as above; after exception, assert skill_dir is gone

- [x] Task 4: Update `tests/unit/cli/test_commands.py` — fix tests that now reach the install step (AC: 1, 2, 3)
  - [x] Add `from nimble.manifest.installer import InstallError` to imports
  - [x] Update `test_add_confirms_and_proceeds()` — add `patch("nimble.manifest.installer.install_skill_venv")` as second context manager; add `mock_install.assert_called_once()` assertion
  - [x] Add `test_add_install_error_exits_with_code_1()` — patch `fetch_remote_manifest` returning `_make_manifest_spec()`; patch `nimble.manifest.installer.install_skill_venv` with `side_effect=InstallError("pip failed")`; invoke with `input="y\n"`; assert `exit_code == 1`; assert `"pip failed"` in output

- [x] Task 5: Create `tests/integration/test_nimble_add.py` (AC: 1, 2)
  - [x] `test_install_skill_venv_creates_real_venv(tmp_path)` — call `install_skill_venv` with `dependencies=[]` and real `tmp_path`; assert `(tmp_path / ".nimble" / "skills" / "test-skill" / ".venv").exists()`; assert venv `bin/python` (Linux) or `Scripts/python.exe` (Windows) exists inside venv
  - [x] Mark pip-network tests with `@pytest.mark.slow` or skip with `pytest.importorskip` / condition — do NOT make the whole file require network

- [x] Task 6: Verify quality gates
  - [x] `.venv/bin/pytest tests/unit/ -q` — all tests pass (baseline 269 + ~10 new = ~279)
  - [x] `.venv/bin/mypy nimble/ tests/ worker/` — exits 0 (0 new errors in `nimble/`)
  - [x] `.venv/bin/black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

## Dev Notes

### What Already EXISTS — Do NOT Reinvent

**`nimble/manifest/parser.py`** already has:
- `ManifestSpec` dataclass with `dependencies: list[str]` — these are the pip package specifiers to install (e.g. `["anthropic", "openai>=1.0"]`)
- `ManifestError(Exception)` — do NOT reuse for installer failures; create separate `InstallError`

**`nimble/platform.py`** already has:
- `is_windows() -> bool` — use for cross-platform pip path, do NOT use `sys.platform == "win32"` directly; import `from nimble.platform import is_windows`

**`nimble/cli/commands.py`** already has:
- `_repo_root() -> Path` — returns `Path(__file__).resolve().parent.parent.parent` (3 levels up from `nimble/cli/commands.py` = repo root)
- The `add()` command at line 305, with the placeholder at line 338: `typer.echo(f"Skill '{spec.name}' confirmed — installation is not implemented yet.")` — **this exact line is replaced in Task 2**
- Lazy import pattern already established: all commands import from `nimble.manifest.*` inside the function body — follow this for `install_skill_venv` too

**`tests/unit/manifest/test_parser.py`** already exists — follow its structure for `test_installer.py` (same directory, same import pattern)

**`tests/unit/cli/test_commands.py`** already has `test_add_confirms_and_proceeds` — this test will **break** in story 6.3 if not updated, because `input="y\n"` now reaches the install step. Patch `nimble.manifest.installer.install_skill_venv` in that test.

### Venv Path Convention

Community skill venvs live at **repo root** `.nimble/`, not `~/.nimble/`:
- Runtime state files (pid, log, state.json): `Path.home() / ".nimble"` (see `nimble/state.py`)
- Community skill venvs: `_repo_root() / ".nimble" / "skills" / spec.name / ".venv"`
- The repo-root `.nimble/` is gitignored via `.nimble/*` in `.gitignore`; `manifest.lock` is kept via `!.nimble/manifest.lock`

This means `install_skill_venv` must receive `repo_root: Path` — do NOT call `_repo_root()` inside the installer module (that would tie it to the CLI). Keep the installer pure: it takes what it's given.

### New Module: `nimble/manifest/installer.py`

Create this file. The `nimble/manifest/` package is the right home because:
- The architecture's `nimble add` flow shows: `manifest/parser.py → venv creation → pip install → manifest/lock.py`
- Installer is part of the manifest/installation lifecycle, not the skill runtime

```python
# nimble/manifest/installer.py
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
```

### Updated `add()` in `commands.py`

Replace the placeholder line (line 338) with:

```python
    from nimble.manifest.installer import InstallError, install_skill_venv

    typer.echo(f"Installing '{spec.name}'...")
    try:
        install_skill_venv(spec, _repo_root())
    except InstallError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)

    typer.echo(f"Dependencies installed for '{spec.name}'.")
```

The `from nimble.manifest.parser import ManifestError, fetch_remote_manifest` import already exists above this (from Story 6.2). Add the installer import directly after it, still inside the function body.

Story 6.5 will replace `typer.echo(f"Dependencies installed for '{spec.name}'.")` with the final config-append success message.

### Patch Target for Tests

Since `install_skill_venv` is imported lazily (inside the `add()` function body), the correct patch target for CLI tests is:

```python
patch("nimble.manifest.installer.install_skill_venv")
```

This patches at the definition site, which the lazy import will pick up each time `add()` is invoked. This is the same pattern established in Story 6.2 for `fetch_remote_manifest` (`"nimble.manifest.parser.fetch_remote_manifest"`).

### Architecture Compliance

- All steps in `install_skill_venv` run synchronously (no threads/async) — consistent with the existing CLI command patterns
- `spec.dependencies` is a `list[str]` — pip accepts version specifiers like `anthropic>=0.30.0` natively; no parsing needed
- No config.yaml modification in this story — that is Story 6.5 (`manifest/parser.py` atomic write + `manifest/lock.py`)
- No skill source files cloned from GitHub in this story — venv + deps only. The GitHub clone/copy step is also Story 6.5
- NFR3 (<10s excluding pip download): venv creation is ~1-3s; no artificial delays; the constraint is automatically satisfied by simple `subprocess.run` calls

### Out of Scope for This Story

- Cloning/downloading skill source files from GitHub (Story 6.5)
- `config.yaml` append (Story 6.5)
- `manifest.lock` write (Story 6.5)
- `nimble/manifest/lock.py` module (Story 6.5)
- Conflict detection for already-installed skill upgrade (Story 6.4) — Story 6.3 only handles fresh installs
- Daemon hot-reload of newly installed skill (Story 6.5, triggered by watchdog on config.yaml change)

### File List to Touch

- `nimble/manifest/installer.py` — **NEW FILE**
- `nimble/cli/commands.py` — replace placeholder (line 338), add lazy import + install call
- `tests/unit/manifest/test_installer.py` — **NEW FILE**
- `tests/unit/cli/test_commands.py` — update `test_add_confirms_and_proceeds`, add `test_add_install_error_exits_with_code_1`
- `tests/integration/test_nimble_add.py` — **NEW FILE** (integration test for real venv)

### Baseline (Before This Story)

```
Tests: 269 passed (0 collection errors)
mypy: 3 pre-existing errors in tests/unit/platform/test_platform.py — unchanged; 0 errors in nimble/
black: clean
flake8: clean (nimble/ tests/ worker/)
```

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 6.3] — acceptance criteria, FR22, FR23, NFR14, NFR3
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Per-Skill Venv Activation] — `sys.executable` for author skills vs `.venv/bin/python` for community skills; worker subprocess model
- [Source: docs/bmad_output/planning-artifacts/architecture.md#nimble add flow] — sequence: permissions → confirm → venv → pip → lock → config append
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Repository Module Structure] — `.nimble/skills/<name>/.venv/` location; `nimble/manifest/` package
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Complete Project Directory Structure] — `tests/integration/test_nimble_add.py` planned
- [Source: nimble/state.py] — confirms `~/.nimble` for runtime state; community skills use repo-root `.nimble/`
- [Source: .gitignore] — `.nimble/*` gitignored at repo root; `!.nimble/manifest.lock` kept
- [Source: docs/bmad_output/implementation-artifacts/6-2-permissions-display-and-install-confirmation.md] — existing `add()` command structure, lazy import pattern, patch at definition site, `_make_manifest_spec` helper

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Created `nimble/manifest/installer.py` with `InstallError`, `_venv_pip`, and `install_skill_venv`. Venv created via `sys.executable -m venv`; pip installed in one subprocess call; failed installs clean up `skill_dir` via `shutil.rmtree`.
- Updated `nimble/cli/commands.py` `add()`: replaced placeholder echo with lazy import + `install_skill_venv` call; `InstallError` surfaces to stderr with exit code 1; success echoes "Dependencies installed for '...'" (Story 6.5 will replace with final config-append message).
- Added 8 unit tests in `tests/unit/manifest/test_installer.py` covering venv creation, pip invocation, error handling, and cleanup.
- Updated `tests/unit/cli/test_commands.py`: patched `install_skill_venv` in tests that reach the install step; added `test_add_install_error_exits_with_code_1`.
- Added `tests/integration/test_nimble_add.py` with real venv creation test (no network) and a `@pytest.mark.slow` pip-install test.
- Quality gates: 278 unit tests pass (+9 new), mypy 0 errors in `nimble/`, black clean, flake8 clean.

### File List

- nimble/manifest/installer.py (new)
- nimble/cli/commands.py (modified)
- tests/unit/manifest/test_installer.py (new)
- tests/unit/cli/test_commands.py (modified)
- tests/integration/test_nimble_add.py (new)
- docs/bmad_output/implementation-artifacts/6-3-per-skill-venv-creation-and-dependency-installation.md (modified)
- docs/bmad_output/implementation-artifacts/sprint-status.yaml (modified)

## Change Log

- 2026-05-02: Implemented per-skill venv creation and dependency installation (Story 6.3). Added `nimble/manifest/installer.py` with `InstallError` and `install_skill_venv`; wired into `nimble add` command; 8 unit tests + integration test; all quality gates pass.
- 2026-05-02: Code review (BMAD) — findings appended under Review Findings.
- 2026-05-02: Post-review fixes — safe manifest `name` validation in parser; staged `tests/integration/test_nimble_add.py`; registered `pytest.mark.slow`; story marked done.

### Review Findings

- [x] [Review][Patch] `spec.name` is not constrained to a single path segment — a malicious or mistaken manifest `name` containing `..` or `/` builds paths like `.nimble/skills/../../outside/.venv` and can create directories outside the intended skills tree [`nimble/manifest/installer.py` — `skill_dir` / `venv_path`; consider validating in `parse_manifest_yaml` or a shared helper so all callers benefit] — **resolved 2026-05-02:** `_validate_manifest_skill_name()` in `nimble/manifest/parser.py` + unit tests in `tests/unit/manifest/test_parser.py`.

- [x] [Review][Patch] `tests/integration/test_nimble_add.py` is required by Task 5 but was still untracked at review time — add it to version control so CI and reviewers see the integration coverage [repository root — `git status`] — **resolved 2026-05-02:** file added to git index.
