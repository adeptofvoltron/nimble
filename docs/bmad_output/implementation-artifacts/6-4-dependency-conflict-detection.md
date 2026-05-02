# Story 6.4: Dependency Conflict Detection

Status: done

## Story

As a user managing multiple community skills,
I want `nimble add` to detect when a new skill's dependencies conflict with packages already in its venv,
So that an incompatible skill fails at install time with a clear message rather than silently breaking at runtime.

## Acceptance Criteria

1. **Given** a skill's venv already has `anthropic==0.20.0` installed (plus a constraining package that requires `anthropic<0.25.0`)
   **When** a new skill version declares `dependencies: [anthropic>=0.30.0]` and `nimble add` runs
   **Then** pip's conflict resolution detects the incompatibility
   **And** `nimble add` aborts with the pip error message quoted — `config.yaml` is not modified (FR24)

2. **Given** there are no dependency conflicts
   **When** pip installs into the skill's venv
   **Then** install completes without error and proceeds to config append

3. **Given** a pre-flight conflict check fails on an EXISTING venv
   **When** `nimble add` aborts
   **Then** the existing venv is preserved intact — it is NOT deleted

## Tasks / Subtasks

- [x] Task 1: Add `check_dependency_conflicts` to `nimble/manifest/installer.py` (AC: 1, 2, 3)
  - [x] Add `check_dependency_conflicts(spec: ManifestSpec, repo_root: Path) -> None` function:
    - Compute `venv_path = repo_root / ".nimble" / "skills" / spec.name / ".venv"`
    - Return immediately (no-op) if `not venv_path.exists()` — no pre-existing venv means no conflict risk
    - Return immediately (no-op) if `not spec.dependencies` — no deps to check
    - Run `subprocess.run([str(_venv_pip(venv_path)), "install", "--dry-run"] + list(spec.dependencies), capture_output=True, text=True)`
    - If `result.returncode != 0`: raise `InstallError(f"Dependency conflict detected:\n{(result.stderr.strip() or result.stdout.strip())}")`
    - Use `result.stderr.strip() or result.stdout.strip()` — pip 22.2+ writes conflict errors to stderr; fallback to stdout for edge cases

- [x] Task 2: Update `install_skill_venv` in `nimble/manifest/installer.py` to preserve existing venvs on failure (AC: 3)
  - [x] Capture `venv_existed = venv_path.exists()` **before** `skill_dir.mkdir(...)` — snapshot prior state
  - [x] Call `check_dependency_conflicts(spec, repo_root)` **before** the `try` block — no changes made yet, no cleanup needed if it raises
  - [x] Change both cleanup guards from `shutil.rmtree(skill_dir, ignore_errors=True)` to:
    ```python
    if not venv_existed:
        shutil.rmtree(skill_dir, ignore_errors=True)
    ```
  - [x] Do NOT change any other logic — venv creation and pip install remain identical

- [x] Task 3: Unit tests in `tests/unit/manifest/test_installer.py` (AC: 1, 2, 3)
  - [x] `test_conflict_check_skipped_when_no_venv(tmp_path)` — patch `subprocess.run`; call `check_dependency_conflicts` with `tmp_path` where venv does NOT exist; assert `mock.call_count == 0` (no subprocess call)
  - [x] `test_conflict_check_skipped_when_no_deps(tmp_path)` — create the venv dir so it "exists": `(tmp_path / ".nimble" / "skills" / "test-skill" / ".venv").mkdir(parents=True)`; patch `subprocess.run`; call with `dependencies=[]`; assert `mock.call_count == 0`
  - [x] `test_conflict_raises_install_error(tmp_path)` — create venv dir; patch `subprocess.run` returning `MagicMock(returncode=1, stderr="ERROR: pip's dependency resolver", stdout="")`; call `check_dependency_conflicts(_make_spec(), tmp_path)`; assert `pytest.raises(InstallError, match="Dependency conflict detected")`
  - [x] `test_conflict_message_falls_back_to_stdout(tmp_path)` — create venv dir; patch returning `MagicMock(returncode=1, stderr="", stdout="conflict info")`; assert raised error contains `"conflict info"`
  - [x] `test_no_conflict_does_not_raise(tmp_path)` — create venv dir; patch returning `MagicMock(returncode=0, stderr="", stdout="")`; call `check_dependency_conflicts(_make_spec(), tmp_path)`; assert no exception raised
  - [x] `test_existing_venv_preserved_on_pip_failure(tmp_path)` — simulate reinstall scenario:
    - Pre-create `skill_dir = tmp_path / ".nimble" / "skills" / "test-skill"` and `(skill_dir / ".venv").mkdir(parents=True)` so `venv_existed=True`
    - Patch `subprocess.run` with `side_effect=[MagicMock(returncode=0, stderr=""), MagicMock(returncode=1, stderr="pip install failed")]` (venv creation succeeds, pip fails)
    - Also patch `check_dependency_conflicts` to be a no-op (avoid double-subprocess concern in this test)
    - Call `install_skill_venv(_make_spec(), tmp_path)` → expect `pytest.raises(InstallError)`
    - Assert `skill_dir.exists()` is `True` — the directory was NOT deleted because `venv_existed=True`
  - [x] `test_new_install_still_cleaned_up_on_failure(tmp_path)` — ensure existing behavior unchanged: venv does NOT exist before call; patch `subprocess.run` returning failure for venv creation; assert `pytest.raises(InstallError)`; assert skill_dir is gone after

- [x] Task 4: Verify quality gates
  - [x] `.venv/bin/pytest tests/unit/ -q` — all tests pass (baseline 281 + ~7 new = ~288)
  - [x] `.venv/bin/mypy nimble/ tests/ worker/` — exits 0 (0 new errors in `nimble/`)
  - [x] `.venv/bin/black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

## Dev Notes

### What Already EXISTS — Do NOT Reinvent

**`nimble/manifest/installer.py`** already has:
- `InstallError(Exception)` — reuse this, do NOT create a new exception class
- `_venv_pip(venv_path: Path) -> Path` — reuse for the dry-run subprocess call
- `install_skill_venv(spec: ManifestSpec, repo_root: Path) -> None` — MODIFY this, do not replace it
- All required imports: `shutil`, `subprocess`, `sys`, `Path`, `ManifestSpec`, `is_windows` already at top of file

**`nimble/platform.py`** already has `is_windows() -> bool` — already used via `_venv_pip`; no new platform import needed.

**`nimble/cli/commands.py`** `add()` already catches `InstallError` and exits with code 1 — NO CLI changes needed for this story. The conflict error bubbles up through the existing error handling.

**`tests/unit/manifest/test_installer.py`** already exists with `_make_spec(**overrides)` helper — add new tests to this file, do NOT create a new file.

### `check_dependency_conflicts` — Full Implementation

```python
def check_dependency_conflicts(spec: ManifestSpec, repo_root: Path) -> None:
    """Pre-flight dry-run: detect conflicts in an existing venv before making any changes."""
    venv_path = repo_root / ".nimble" / "skills" / spec.name / ".venv"
    if not venv_path.exists() or not spec.dependencies:
        return
    result = subprocess.run(
        [str(_venv_pip(venv_path)), "install", "--dry-run"] + list(spec.dependencies),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise InstallError(
            f"Dependency conflict detected:\n"
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
```

**Why `--dry-run`**: pip 22.2+ supports `--dry-run` which resolves the dependency tree without modifying the venv. If resolution fails (e.g., `ResolutionImpossible`), pip exits non-zero with a conflict description in stderr. pip 26.0.1 is in use — this flag is available.

**Why call BEFORE the try block**: `check_dependency_conflicts` makes no filesystem changes. If it raises, there is nothing to clean up. Placing it before `try` keeps the cleanup logic simple.

### Updated `install_skill_venv` — Diff Summary

The ONLY changes to `install_skill_venv` are:
1. Add `venv_existed = venv_path.exists()` before `try`
2. Add `check_dependency_conflicts(spec, repo_root)` before `try`
3. Replace both `shutil.rmtree(skill_dir, ignore_errors=True)` calls with `if not venv_existed: shutil.rmtree(skill_dir, ignore_errors=True)`

```python
def install_skill_venv(spec: ManifestSpec, repo_root: Path) -> None:
    """Create .nimble/skills/<name>/.venv/ and pip-install declared dependencies."""
    skill_dir = repo_root / ".nimble" / "skills" / spec.name
    venv_path = skill_dir / ".venv"
    venv_existed = venv_path.exists()  # ← NEW: snapshot prior state

    check_dependency_conflicts(spec, repo_root)  # ← NEW: pre-flight, no changes made yet

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
        if not venv_existed:  # ← CHANGED: preserve existing venv
            shutil.rmtree(skill_dir, ignore_errors=True)
        raise
    except Exception as exc:
        if not venv_existed:  # ← CHANGED: preserve existing venv
            shutil.rmtree(skill_dir, ignore_errors=True)
        raise InstallError(str(exc)) from exc
```

### Architecture Compliance

- `check_dependency_conflicts` is a pure function (no side effects on success) — consistent with the parser.py validation pattern
- No new module needed — conflict detection belongs in `nimble/manifest/installer.py` (same lifecycle)
- No new exception class — `InstallError` is the right type (install-time failure)
- No `config.yaml` changes in this story — config append is Story 6.5
- NFR14 (config preserved on write failure) — not at risk; no config writes here

### Out of Scope for This Story

- Config append to `config.yaml` (Story 6.5)
- `manifest.lock` write (Story 6.5)
- GitHub clone of skill source files (Story 6.5)
- Detecting conflicts between DIFFERENT skills' venvs — each skill has its own isolated venv; inter-skill isolation is by design

### Baseline (Before This Story)

```
Tests: 281 passed (0 collection errors)
mypy: 3 pre-existing errors in tests/unit/platform/test_platform.py — unchanged; 0 errors in nimble/
black: clean
flake8: clean (nimble/ tests/ worker/)
```

### File List to Touch

- `nimble/manifest/installer.py` — add `check_dependency_conflicts`, update `install_skill_venv` cleanup guards
- `tests/unit/manifest/test_installer.py` — add ~7 new test functions

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 6.4] — acceptance criteria, FR24
- [Source: docs/bmad_output/planning-artifacts/architecture.md#nimble add flow] — sequence confirms no config writes until Story 6.5
- [Source: docs/bmad_output/implementation-artifacts/6-3-per-skill-venv-creation-and-dependency-installation.md#Out of Scope] — "Conflict detection for already-installed skill upgrade (Story 6.4) — Story 6.3 only handles fresh installs"
- [Source: nimble/manifest/installer.py] — current `install_skill_venv` implementation to modify
- [Source: tests/unit/manifest/test_installer.py] — existing test patterns to follow

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No blockers encountered.

### Completion Notes List

- Added `check_dependency_conflicts(spec, repo_root)` to `nimble/manifest/installer.py`: runs `pip install --dry-run` against an existing venv before any filesystem changes; raises `InstallError` on non-zero exit using stderr with stdout fallback.
- Updated `install_skill_venv`: captured `venv_existed` pre-flight, calls `check_dependency_conflicts` before the `try` block, both cleanup guards now conditioned on `not venv_existed` to preserve pre-existing venvs.
- Added 7 new unit tests covering all ACs: skip when no venv, skip when no deps, conflict detected (stderr), conflict detected (stdout fallback), no-conflict no-raise, existing venv preserved on pip failure, new install still cleaned up on failure.
- All 288 tests pass; 0 new mypy errors in `nimble/`; black clean; flake8 clean.

### File List

- `nimble/manifest/installer.py`
- `tests/unit/manifest/test_installer.py`

## Change Log

- 2026-05-02: Added `check_dependency_conflicts` and updated `install_skill_venv` cleanup guards for Story 6.4 (Dependency Conflict Detection)
