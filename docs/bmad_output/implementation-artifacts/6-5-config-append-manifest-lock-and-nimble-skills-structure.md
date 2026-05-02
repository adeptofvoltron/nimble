# Story 6.5: Config Append, `manifest.lock`, and `.nimble/skills/` Structure

Status: done

## Story

As a user,
I want `nimble add` to update my `config.yaml` and lock the skill version automatically,
So that my setup is reproducible on any machine without manual config editing.

## Acceptance Criteria

1. **Given** install succeeds (venv created, deps installed, skill files cloned)
   **When** `nimble add` appends to `config.yaml`
   **Then** the skill entry is added with `source: community`, `path`, `class_name`, `binding`, `installed_from`, and `version` fields using an atomic write (FR25, FR31, NFR14)
   **And** `config.yaml` is fully valid after the write — `nimble validate` exits 0

2. **Given** the config append completes
   **When** `manifest.lock` is updated
   **Then** it records the skill `name`, `installed_from` repo URL, and `version` — enabling reproducible installs (FR26)
   **And** `manifest.lock` is written using an atomic write (NFR14)

3. **Given** `.nimble/skills/<name>/` is created during install
   **When** the directory structure is inspected
   **Then** it contains the cloned skill source files and `.venv/` (FR43)
   **And** `.nimble/` is already listed in `.gitignore` except `manifest.lock` — this is already done, no change needed

4. **Given** `config.yaml` is updated via atomic write after install
   **When** the daemon is running and the file watcher detects the change
   **Then** it spawns a new pre-warmed worker for the installed skill — no `nimble restart` required
   **Note:** This AC is verified by the existing watcher + daemon infrastructure (Stories 2.8, 5.1). No new watcher code needed in this story; just ensure `config.yaml` is written correctly.

5. **Given** the manifest declares no `class_name` or an empty `class_name`
   **When** `nimble add` attempts to append to `config.yaml`
   **Then** it aborts with a clear error: `"manifest.yaml must declare 'class_name' for community skill installation"`
   **And** `config.yaml` is not modified

## Tasks / Subtasks

- [x] Task 1: Create `nimble/manifest/lock.py` — manifest.lock read/write (AC: 2)
  - [x] Create file with `read_lock(lock_path: Path) -> dict[str, dict[str, str]]`
    - If file doesn't exist: return `{}`
    - Load YAML, return `data["skills"]` as dict keyed by skill name
    - On any parse/IO error: return `{}` (lock is advisory — don't crash on bad state)
  - [x] Create `write_lock_entry(lock_path: Path, name: str, installed_from: str, version: str) -> None`
    - Call `read_lock(lock_path)` to get current entries
    - Add/overwrite `skills[name] = {"installed_from": installed_from, "version": version}`
    - Serialize to YAML: `yaml.dump({"skills": skills}, default_flow_style=False, allow_unicode=True)`
    - Write using `atomic_write` from `nimble.manifest.parser` (reuse, do NOT duplicate)
    - `lock_path.parent.mkdir(parents=True, exist_ok=True)` before atomic_write in case `.nimble/` doesn't exist

- [x] Task 2: Add `clone_skill_repo` to `nimble/manifest/installer.py` (AC: 3)
  - [x] Add `clone_skill_repo(repo_url: str, skill_dir: Path) -> None`
    - Run `subprocess.run(["git", "clone", "--depth=1", repo_url, str(skill_dir)], capture_output=True, text=True)`
    - If `returncode != 0`: raise `InstallError(f"Failed to clone {repo_url}:\n{result.stderr.strip()}")`
    - `skill_dir` must NOT exist before calling (git clone creates it); caller is responsible for cleanup on error
  - [x] No changes to `install_skill_venv` — order in `commands.py` will be: clone first, then install venv

- [x] Task 3: Add `append_skill_to_config` to `nimble/manifest/parser.py` (AC: 1, 5)
  - [x] Add `append_skill_to_config(config_path: Path, spec: ManifestSpec, binding: str, repo_url: str, repo_root: Path) -> None`
    - Validate `spec.class_name` is non-empty; if empty raise `ConfigError("manifest.yaml must declare 'class_name' for community skill installation")`
    - Read current `config.yaml` via `yaml.safe_load` (same pattern as `disable_skill_in_config`)
    - Compute `rel_path = str(Path(".nimble") / "skills" / spec.name / spec.entrypoint)`
    - Build entry dict (KEEP key order for readability):
      ```python
      entry = {
          "name": spec.name,
          "source": "community",
          "path": rel_path,
          "class_name": spec.class_name,
          "binding": binding,
          "installed_from": repo_url,
          "version": spec.version,
      }
      ```
    - `raw.setdefault("skills", []).append(entry)` — don't overwrite existing skills
    - Serialize and write via `atomic_write(config_path, yaml.dump(raw, default_flow_style=False, allow_unicode=True))`
    - On read error: raise `ConfigError(f"Failed to read config.yaml: {exc}")`

- [x] Task 4: Update `commands.py` `add` command to call new steps in full sequence (AC: 1, 2, 3, 4, 5)
  - [x] After `_prompt_install_confirm_y_only()` succeeds, restructure the install flow:
    ```
    1. clone_skill_repo(repo_url, skill_dir)       ← NEW (this story)
    2. install_skill_venv(spec, repo_root)          ← exists (6.3/6.4)
    3. append_skill_to_config(...)                  ← NEW (this story)
    4. write_lock_entry(...)                        ← NEW (this story)
    5. echo success
    ```
  - [x] `skill_dir = repo_root / ".nimble" / "skills" / spec.name`
  - [x] Wrap clone in try/except `InstallError` — same error handling as venv install
  - [x] Wrap `append_skill_to_config` in try/except `ConfigError` — echo error, exit 1
  - [x] `manifest.lock` path: `repo_root / ".nimble" / "manifest.lock"`
  - [x] Import: `from nimble.manifest.lock import write_lock_entry`
  - [x] Import: `from nimble.manifest.installer import clone_skill_repo`
  - [x] Import: `from nimble.manifest.parser import append_skill_to_config, ConfigError`
  - [x] On clone failure: ensure `skill_dir` is cleaned up (`shutil.rmtree(skill_dir, ignore_errors=True)`) before raising
  - [x] Final success message: `typer.echo(f"Skill '{spec.name}' installed and bound to {shortcut}.")`

- [x] Task 5: Unit tests for `lock.py` in `tests/unit/manifest/test_lock.py` (AC: 2)
  - [x] `test_read_lock_missing_file(tmp_path)` — returns `{}`
  - [x] `test_read_lock_empty_skills(tmp_path)` — YAML with `skills: {}` returns `{}`
  - [x] `test_write_lock_entry_creates_file(tmp_path)` — call write_lock_entry, assert file content contains name/url/version
  - [x] `test_write_lock_entry_overwrites_existing(tmp_path)` — write twice for same name, assert only latest version
  - [x] `test_write_lock_entry_preserves_other_entries(tmp_path)` — two entries, one updated, assert other unchanged
  - [x] `test_write_lock_entry_creates_nimble_dir(tmp_path)` — lock_path in nonexistent `.nimble/` subdir; assert write succeeds

- [x] Task 6: Unit tests for `clone_skill_repo` in `tests/unit/manifest/test_installer.py` (AC: 3)
  - [x] `test_clone_skill_repo_success(tmp_path)` — patch `subprocess.run` returning `MagicMock(returncode=0)`; assert no exception raised; assert called with correct args including `--depth=1`
  - [x] `test_clone_skill_repo_failure(tmp_path)` — patch returning `MagicMock(returncode=1, stderr="fatal: repo not found")`; assert `pytest.raises(InstallError, match="Failed to clone")`

- [x] Task 7: Unit tests for `append_skill_to_config` in `tests/unit/manifest/test_parser.py` (AC: 1, 5)
  - [x] `test_append_skill_to_config_adds_entry(tmp_path)` — write minimal `config.yaml` with `skills: []`; call append; reload YAML; assert entry with all 7 keys present
  - [x] `test_append_skill_to_config_preserves_existing(tmp_path)` — start with one skill; call append; assert both skills present
  - [x] `test_append_skill_to_config_empty_class_name_raises(tmp_path)` — spec with `class_name=""`; assert `pytest.raises(ConfigError, match="class_name")`
  - [x] `test_append_skill_to_config_uses_atomic_write(tmp_path)` — patch `atomic_write`; assert it's called (verify NFR14 compliance)

- [x] Task 8: Quality gates
  - [x] `.venv/bin/pytest tests/unit/ -q` — 300 passed (288 baseline + 12 new)
  - [x] `.venv/bin/mypy nimble/` — exits 0 (pre-existing test errors unchanged)
  - [x] `.venv/bin/black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

### Review Findings

- [x] [Review][Decision] Policy if lock write fails after config append — **Resolved (A):** On `write_lock_entry` failure, `remove_skill_entry_from_config` removes the newly appended skill and the CLI exits with a clear message; dual failure (lock + rollback) surfaces both errors. [`nimble/cli/commands.py`, `nimble/manifest/parser.py`]

- [x] [Review][Patch] Mirror `disable_skill_in_config` and reject non-list `skills` before append — **Fixed:** `append_skill_to_config` validates `skills` is a list and raises `ConfigError` otherwise. [`nimble/manifest/parser.py`]

- [x] [Review][Patch] Treat whitespace-only `class_name` as invalid for community install — **Fixed:** Uses `not (spec.class_name or "").strip()` before append. [`nimble/manifest/parser.py`]

## Dev Notes

### What Already EXISTS — Do NOT Reinvent

**`nimble/manifest/parser.py`** has:
- `atomic_write(path: Path, content: str) -> None` — reuse in `lock.py` for manifest.lock write; import it, don't copy it
- `disable_skill_in_config(config_path, skill_name)` — follow this exact pattern for `append_skill_to_config` (load → modify → atomic_write)
- `ManifestSpec` — `spec.name`, `spec.version`, `spec.entrypoint`, `spec.class_name`, `spec.permissions`, `spec.dependencies`
- `ConfigError` — reuse for config-append errors

**`nimble/manifest/installer.py`** has:
- `InstallError` — reuse for clone errors
- `install_skill_venv(spec, repo_root)` — already handles venv creation and dep install; don't touch it
- `_venv_pip(venv_path)` — internal helper; not needed in this story

**`nimble/cli/commands.py`** has:
- `_repo_root() -> Path` — returns `Path(__file__).resolve().parent.parent.parent` (repo root); use this
- `add()` command — currently ends after `install_skill_venv`; extend it, don't rewrite it
- `shutil` is NOT currently imported in commands.py — add it if needed for skill_dir cleanup on clone failure

**`nimble/manifest/__init__.py`** — currently empty; no changes needed

**`.gitignore`** — already has `.nimble/*` with `!.nimble/manifest.lock` (line 7-8 of .gitignore). DO NOT modify .gitignore.

### Current `add` Command Flow (End of Story 6.4)

```python
# commands.py add() — current state at end of 6.4
spec = fetch_remote_manifest(repo_url)
# ... show permissions, confirm ...
install_skill_venv(spec, _repo_root())
typer.echo(f"Dependencies installed for '{spec.name}'.")
```

**Target flow after Story 6.5:**
```python
spec = fetch_remote_manifest(repo_url)
# ... show permissions, confirm ...
repo_root = _repo_root()
skill_dir = repo_root / ".nimble" / "skills" / spec.name

# Step 1: clone skill source files
try:
    clone_skill_repo(repo_url, skill_dir)
except InstallError as exc:
    typer.echo(str(exc), err=True)
    raise typer.Exit(1)

# Step 2: create venv + install deps (existing)
try:
    install_skill_venv(spec, repo_root)
except InstallError as exc:
    shutil.rmtree(skill_dir, ignore_errors=True)  # clean cloned files
    typer.echo(str(exc), err=True)
    raise typer.Exit(1)

# Step 3: append to config.yaml
config_path = repo_root / "config.yaml"
try:
    append_skill_to_config(config_path, spec, shortcut, repo_url, repo_root)
except ConfigError as exc:
    typer.echo(str(exc), err=True)
    raise typer.Exit(1)

# Step 4: update manifest.lock
lock_path = repo_root / ".nimble" / "manifest.lock"
write_lock_entry(lock_path, spec.name, repo_url, spec.version)

typer.echo(f"Skill '{spec.name}' installed and bound to {shortcut}.")
```

**Note:** If `install_skill_venv` fails after cloning, `skill_dir` must be cleaned up. `install_skill_venv` only cleans up if `venv_existed=False` at the TIME it's called — since we just cloned, `.venv` doesn't exist yet so `venv_existed=False`, meaning `install_skill_venv` will clean up `skill_dir` on failure. This is correct and NO extra cleanup is needed in the `except InstallError` block. But confirm this behavior by reading the current `install_skill_venv` logic.

Wait — `install_skill_venv` checks `venv_path = skill_dir / ".venv"` and `venv_existed = venv_path.exists()`. After cloning, `.venv` does NOT exist (git won't create it), so `venv_existed=False`. On failure, it runs `shutil.rmtree(skill_dir, ignore_errors=True)` which removes the cloned files too. This is the correct "clean slate" behavior for a fresh install.

**Implication:** The `except InstallError` in the `add` command for Step 2 does NOT need to call `shutil.rmtree` — `install_skill_venv` already handles cleanup. Just echo and exit.

### `manifest.lock` Format

```yaml
skills:
  log-diagnosis:
    installed_from: https://github.com/user/nimble-log-diagnosis
    version: 1.0.0
  another-skill:
    installed_from: https://github.com/user/another-skill
    version: 2.3.1
```

- Dict keyed by skill name (not a list) for O(1) lookup and idempotent overwrite
- `installed_from` is the exact repo_url passed to `nimble add`
- `version` is `spec.version` from the fetched manifest

### `config.yaml` Entry After Append

```yaml
skills:
  - name: hello_world
    source: local
    path: skills/hello_world/skill.py
    class_name: HelloWorldSkill
    binding: ctrl+l
  - name: log-diagnosis
    source: community
    path: .nimble/skills/log-diagnosis/skill.py
    class_name: LogDiagnosisSkill
    binding: ctrl+shift+d
    installed_from: https://github.com/user/nimble-log-diagnosis
    version: 1.0.0
```

**Key invariants:**
- `source: community` — required for runner.py to use the community venv Python
- `path` is relative to repo root (e.g., `.nimble/skills/log-diagnosis/skill.py`) — NOT absolute
- `class_name` must be non-empty (validated in `append_skill_to_config`)
- `installed_from` and `version` are extra fields tolerated by `_parse_skills` (it uses `.get()` for unknown keys)

### Community Skill Python Executable Resolution

`nimble/skills/runner.py` selects the Python executable for community skills using:
```
.nimble/skills/<name>/.venv/bin/python   (Linux/macOS)
.nimble/skills/<name>/.venv/Scripts/python.exe  (Windows)
```
This is keyed off `source == "community"` in `SkillConfig`. Story 6.5 writes `source: community` — the runner will automatically pick the venv Python. No changes to runner.py needed.

### `clone_skill_repo` — Git Dependency

`git` must be available on the system PATH. If not, the subprocess will fail with `FileNotFoundError` which is NOT caught by the `if result.returncode != 0` check. Add a catch for `FileNotFoundError`:
```python
try:
    result = subprocess.run(...)
except FileNotFoundError:
    raise InstallError("'git' not found — install git to use 'nimble add'")
```

### Architecture Compliance

- `nimble/manifest/lock.py` is the canonical location for manifest.lock operations [Source: docs/bmad_output/planning-artifacts/architecture.md#Repository Module Structure]
- `atomic_write` in `parser.py` is the shared utility for safe config writes — import it in `lock.py`, do not duplicate (NFR14)
- `append_skill_to_config` belongs in `parser.py` alongside `disable_skill_in_config` — same file, same pattern
- No changes to `nimble/skills/runner.py`, `nimble/watcher.py`, or `nimble/daemon.py` — AC4 is satisfied by existing infrastructure
- Absolute imports only: `from nimble.manifest.parser import atomic_write, ConfigError` (not relative)
- All new functions must be fully annotated (`mypy --strict` enforced)

### `_parse_skills` Tolerance for Extra Fields

`_parse_skills` in `parser.py` checks for `required_fields = {"name", "source", "path", "class_name", "binding"}`. Extra keys (`installed_from`, `version`) are silently ignored (the dict is read with `.get()` for required keys only). The appended entry is valid for `load_config` as-is.

### Out of Scope for This Story

- `nimble reinstall` / `nimble upgrade` commands — future work
- Handling duplicate skill names in config (deferred per `deferred-work.md`)
- macOS support for entrypoint detection
- Removing a community skill (`nimble remove` — not in scope for v1)

### Baseline (Before This Story)

```
Tests: 288 passed (0 collection errors)
mypy: 3 pre-existing errors in tests/unit/platform/test_platform.py — unchanged; 0 errors in nimble/
black: clean
flake8: clean (nimble/ tests/ worker/)
lock.py: does not exist yet
```

### Project Structure Notes

**New files:**
- `nimble/manifest/lock.py` — NEW (does not exist; `ls nimble/manifest/` confirms: `__init__.py`, `installer.py`, `parser.py` only)
- `tests/unit/manifest/test_lock.py` — NEW

**Modified files:**
- `nimble/manifest/installer.py` — add `clone_skill_repo`
- `nimble/manifest/parser.py` — add `append_skill_to_config`
- `nimble/cli/commands.py` — extend `add` command with 4-step flow; add `shutil` import if needed

**Not touched:**
- `nimble/skills/runner.py` — no changes
- `nimble/watcher.py` — no changes
- `nimble/daemon.py` — no changes
- `.gitignore` — already correct

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 6.5] — acceptance criteria (FR25, FR26, FR31, FR43)
- [Source: docs/bmad_output/planning-artifacts/architecture.md#nimble add flow] — full install sequence
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Repository Module Structure] — lock.py location
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Configuration] — atomic write requirement (NFR14)
- [Source: docs/bmad_output/implementation-artifacts/6-4-dependency-conflict-detection.md#Out of Scope] — confirms config append/lock write are Story 6.5
- [Source: nimble/manifest/installer.py] — InstallError, install_skill_venv, _venv_pip patterns
- [Source: nimble/manifest/parser.py] — atomic_write, disable_skill_in_config patterns to follow
- [Source: nimble/cli/commands.py] — current add() command to extend
- [Source: .gitignore] — .nimble/* with !.nimble/manifest.lock already correct

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Implemented `nimble/manifest/lock.py` with `read_lock` and `write_lock_entry`; reuses `atomic_write` from parser.py (NFR14 compliance).
- Added `clone_skill_repo` to `nimble/manifest/installer.py` with `FileNotFoundError` guard for missing git.
- Added `append_skill_to_config` to `nimble/manifest/parser.py` following `disable_skill_in_config` pattern; validates `class_name` non-empty (AC5).
- Extended `commands.py` `add` command with 4-step flow: clone → venv → config append → lock write. `install_skill_venv` handles cleanup of cloned files on venv failure (confirmed by reading existing logic).
- Updated 3 existing `test_commands.py` tests to mock the new `clone_skill_repo`, `append_skill_to_config`, and `write_lock_entry` calls.
- 300 tests pass (288 baseline + 12 new). 0 new mypy errors in `nimble/`. black and flake8 clean.

### File List

- nimble/manifest/lock.py (new)
- nimble/manifest/installer.py (modified)
- nimble/manifest/parser.py (modified)
- nimble/cli/commands.py (modified)
- tests/unit/manifest/test_lock.py (new)
- tests/unit/manifest/test_installer.py (modified)
- tests/unit/manifest/test_parser.py (modified)
- tests/unit/cli/test_commands.py (modified)

## Change Log

- 2026-05-02: Implemented Story 6.5 — created `nimble/manifest/lock.py`, added `clone_skill_repo` to installer.py, added `append_skill_to_config` to parser.py, extended `add` command with 4-step install flow (clone → venv → config append → lock write), added 12 new unit tests, updated 3 existing tests for new mocking requirements.
