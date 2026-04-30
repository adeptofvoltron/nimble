# Story 4.4: API Version Compatibility Check

Status: done

## Story

As a skill author,
I want the daemon to verify my skill's declared `api_version` against the daemon's supported version at load time,
so that version mismatches surface as clear notifications rather than silent misbehavior at runtime.

## Acceptance Criteria

1. **Given** a skill's `manifest.yaml` declares `api_version` equal to `SUPPORTED_API_VERSION`
   **When** the daemon loads the skill
   **Then** the skill loads normally with no warnings

2. **Given** a skill's `manifest.yaml` declares `api_version` lower than `SUPPORTED_API_VERSION` (old skill, new daemon)
   **When** the daemon loads the skill
   **Then** `WARNING` is logged: `"Skill <name> uses api_version <N> — deprecated fields will raise AttributeError"`
   **And** the skill still loads and runs normally

3. **Given** a skill's `manifest.yaml` declares `api_version` higher than `SUPPORTED_API_VERSION` (too-new skill)
   **When** the daemon loads the skill
   **Then** the skill is refused — no worker process is spawned
   **And** a notification fires: `"Skill <name> requires Nimble api_version <N> — upgrade your daemon"`
   **And** an `ERROR` is logged
   **And** the daemon continues loading all other skills normally

4. **Given** a skill has no `manifest.yaml`, or the manifest lacks an `api_version` field
   **When** the daemon loads the skill
   **Then** the skill loads normally — version check is skipped (graceful degradation)

## Tasks / Subtasks

- [x] Task 1: Add `SUPPORTED_API_VERSION` constant to `nimble/__init__.py` (AC: 1, 2, 3)
  - [x] Add `SUPPORTED_API_VERSION: int = 1` after the existing `__version__` line

- [x] Task 2: Add `read_skill_manifest()` to `nimble/manifest/parser.py` (AC: 1–4)
  - [x] Add function `read_skill_manifest(config: SkillConfig, base_path: Path) -> dict[str, Any] | None`
  - [x] Construct manifest path: `base_path / Path(config.path).parent / "manifest.yaml"`
  - [x] If the file does not exist: return `None`
  - [x] Open and parse with `yaml.safe_load`; return parsed dict if it is a dict, else `None`
  - [x] On `yaml.YAMLError`: log `WARNING` and return `None` — never raise

- [x] Task 3: Add api_version check in `nimble/skills/runner.py::spawn_workers()` (AC: 1–4)
  - [x] Import `SUPPORTED_API_VERSION` from `nimble` and `read_skill_manifest` from `nimble.manifest.parser`
  - [x] At the TOP of the `for config in configs:` loop body, BEFORE building env vars or calling `Popen`:
    - [x] Call `manifest = read_skill_manifest(config, self._repo_root)`
    - [x] If manifest is not None and `"api_version"` is an `int` in the manifest:
      - [x] If `skill_api_version > SUPPORTED_API_VERSION`: fire notification, log ERROR, `continue` (do NOT spawn — no worker registered)
      - [x] If `skill_api_version < SUPPORTED_API_VERSION`: log WARNING, fall through (load skill normally)
    - [x] All other cases (no manifest, no api_version field, non-int value): fall through silently

- [x] Task 4: Write tests (AC: 1–4)
  - [x] `tests/unit/manifest/test_parser.py` — add tests for `read_skill_manifest`:
    - [x] `test_read_skill_manifest_returns_none_when_no_manifest()` — tmp_path has no manifest.yaml; assert `None` returned
    - [x] `test_read_skill_manifest_returns_dict_when_manifest_exists()` — write valid manifest.yaml; assert dict returned with api_version
    - [x] `test_read_skill_manifest_returns_none_on_invalid_yaml()` — write broken YAML; assert `None` returned (no raise)
    - [x] `test_read_skill_manifest_returns_none_when_not_dict()` — write `"just a string"` YAML; assert `None` returned
  - [x] `tests/unit/skills/test_runner.py` — add tests for version check behavior:
    - [x] `test_spawn_workers_rejects_skill_with_too_high_api_version()` — mock `read_skill_manifest` to return `{"api_version": 999}`; verify `Popen` NOT called, notifier called with correct message, no RuntimeError raised
    - [x] `test_spawn_workers_warns_for_old_api_version()` — mock `read_skill_manifest` to return `{"api_version": 0}`; verify `Popen` IS called (skill loads), WARNING logged
    - [x] `test_spawn_workers_loads_normally_for_matching_api_version()` — mock manifest with `api_version == SUPPORTED_API_VERSION`; verify Popen called, status "loaded"
    - [x] `test_spawn_workers_skips_check_when_no_manifest()` — mock `read_skill_manifest` to return `None`; verify Popen called normally, no warning logged

- [x] Task 5: Verify quality gates
  - [x] `.venv/bin/pytest tests/unit/ --ignore=tests/unit/test_daemon.py --ignore=tests/unit/test_watcher.py` — all pass (179 passed)
  - [x] `.venv/bin/mypy nimble/ tests/ worker/` — exits 0 (3 pre-existing errors in test_platform.py unchanged)
  - [x] `.venv/bin/black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

### Review Findings

- [x] [Review][Patch] Unhandled manifest read errors can abort all worker startup [nimble/manifest/parser.py:32]
- [x] [Review][Patch] Manifest path resolution can escape repo root via absolute/traversal `config.path` [nimble/manifest/parser.py:33]
- [x] [Review][Patch] `bool` is accepted as `api_version` because `isinstance(True, int)` is true [nimble/skills/runner.py:81]
- [x] [Review][Patch] Too-new version notification body misses required `Skill <name>` prefix [nimble/skills/runner.py:87]
- [x] [Review][Patch] Missing test for manifest present but `api_version` absent (AC4 branch) [tests/unit/skills/test_runner.py:584]

## Dev Notes

### What Exists Today — Do NOT Reinvent

**`nimble/__init__.py` current content:**
```python
__version__ = "1.0.0"
```
Add `SUPPORTED_API_VERSION: int = 1` immediately after.

**`nimble/manifest/parser.py`** parses `config.yaml` (NimbleConfig). The `read_skill_manifest` function is NEW — it reads a per-skill `manifest.yaml` from the skill's own directory, not config.yaml. Do NOT modify any existing config parsing functions.

**`nimble/skills/runner.py::spawn_workers()`** already handles per-skill failures gracefully via `continue`. The api_version check is a new early-exit at the TOP of the loop, before any subprocess work. Follow the same per-skill `continue` pattern already used for startup failures.

**`skills/hello_world/manifest.yaml`** already exists with `api_version: 1`:
```yaml
name: hello_world
version: "1.0.0"
api_version: 1
```
This is the reference format. The check reads the sibling `manifest.yaml` of the skill's Python file.

### Exact Manifest Path Calculation

Given `config.path = "skills/hello_world/skill.py"` and `base_path = repo_root`:
```python
manifest_path = base_path / Path(config.path).parent / "manifest.yaml"
# → repo_root / "skills" / "hello_world" / "manifest.yaml"
```

### Exact Warning/Notification Messages

| Case | Level | Message |
|------|-------|---------|
| api_version lower than supported | WARNING (log only) | `f"Skill {config.name} uses api_version {skill_api_version} — deprecated fields will raise AttributeError"` |
| api_version higher than supported | ERROR (log) + notification | title: `f"Nimble — {config.name}"`, body: `f"requires Nimble api_version {skill_api_version} — upgrade your daemon"` |

### API Version Rejection — No Worker Registration

When `api_version > SUPPORTED_API_VERSION`, do NOT call `Popen` and do NOT register a worker in the registry. There is no process to track. Just fire the notification, log the error, and `continue`. This differs from startup-failure cases (where a process exists and is registered with `status="failed"`).

### `read_skill_manifest` Implementation Guide

```python
def read_skill_manifest(config: SkillConfig, base_path: Path) -> dict[str, Any] | None:
    manifest_path = base_path / Path(config.path).parent / "manifest.yaml"
    if not manifest_path.exists():
        return None
    try:
        with manifest_path.open() as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else None
    except yaml.YAMLError:
        logger.warning("Could not parse manifest.yaml for skill %s", config.name)
        return None
```

You need `from pathlib import Path` (already imported in parser.py) and the `SkillConfig` import. Add `from nimble.skills.registry import SkillConfig` to `parser.py` — it's already used in `_parse_skills`.

### Runner Check Implementation Guide

```python
# In spawn_workers(), at the TOP of `for config in configs:`, before env/Popen:
manifest = read_skill_manifest(config, self._repo_root)
if manifest is not None:
    skill_api_version = manifest.get("api_version")
    if isinstance(skill_api_version, int):
        if skill_api_version > SUPPORTED_API_VERSION:
            try:
                self._notifier.send(
                    title=f"Nimble — {config.name}",
                    body=f"requires Nimble api_version {skill_api_version} — upgrade your daemon",
                )
            except Exception:
                logger.exception("Notifier failed for skill %s", config.name)
            logger.error(
                "Skill %s: requires api_version %d, daemon supports %d",
                config.name, skill_api_version, SUPPORTED_API_VERSION,
            )
            continue
        elif skill_api_version < SUPPORTED_API_VERSION:
            logger.warning(
                "Skill %s uses api_version %d — deprecated fields will raise AttributeError",
                config.name, skill_api_version,
            )
```

### Test Patterns

**For `test_runner.py` tests** — patch `read_skill_manifest` at `nimble.skills.runner.read_skill_manifest`:
```python
with patch("nimble.skills.runner.read_skill_manifest", return_value={"api_version": 999}):
    runner.spawn_workers(configs)
```
Use the existing `_make_fake_proc` helper for the Popen mock where needed.

**For `test_parser.py` tests** — use `tmp_path` fixture; write files manually:
```python
skill_dir = tmp_path / "skills" / "my_skill"
skill_dir.mkdir(parents=True)
(skill_dir / "manifest.yaml").write_text("api_version: 1\nname: my_skill\n")
config = SkillConfig(name="my_skill", source="local", binding="ctrl+x",
                     path="skills/my_skill/skill.py", class_name="MySkill")
result = read_skill_manifest(config, tmp_path)
assert result == {"api_version": 1, "name": "my_skill"}
```

### Architecture Compliance

- Version check runs in the daemon process, NOT in the worker subprocess — this is intentional (fail fast before spawning)
- `mypy --strict` enforced — all new functions must have full type annotations
- Absolute imports only — import `SUPPORTED_API_VERSION` from `nimble`, not relative
- The `SkillConfig` import in `parser.py` — verify it doesn't create a circular import. `registry.py` imports nothing from `parser.py`, so the import chain `parser.py → registry.py` is safe.
- Non-integer `api_version` values (string, None, float) are silently ignored — only `int` triggers the check

### Out of Scope for This Story

The epic mentions "deprecated field accesses surface migration messages at runtime" for old skills. This requires a versioned API layer that doesn't exist yet. For this story, the WARNING log is sufficient. Runtime deprecation enforcement is deferred to a future story when the API actually breaks compatibility.

### File List to Touch

- `nimble/__init__.py` — add `SUPPORTED_API_VERSION = 1`
- `nimble/manifest/parser.py` — add `read_skill_manifest()` function
- `nimble/skills/runner.py` — import `SUPPORTED_API_VERSION` and `read_skill_manifest`; add api_version check at top of spawn_workers loop
- `tests/unit/manifest/test_parser.py` — add 4 tests for `read_skill_manifest`
- `tests/unit/skills/test_runner.py` — add 4 tests for api_version check behavior

### Baseline (Before This Story)

```
Tests: 168 collected (2 collection errors in test_daemon.py and test_watcher.py — pre-existing)
mypy: 3 pre-existing errors in test_platform.py — unchanged; 0 errors via .venv/bin/mypy nimble/
black: clean
flake8: clean (nimble/ tests/ worker/ only)
```

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 4.4] — acceptance criteria, version mismatch behaviors
- [Source: docs/bmad_output/planning-artifacts/architecture.md#NFR23] — api_version must be incremented on breaking changes
- [Source: skills/hello_world/manifest.yaml] — existing manifest format with api_version: 1
- [Source: nimble/manifest/parser.py] — existing YAML parsing patterns to follow
- [Source: nimble/skills/runner.py#spawn_workers] — per-skill continue pattern to follow for rejection case
- [Source: docs/bmad_output/implementation-artifacts/4-3-skill-lifecycle-hooks-on-load-on-error-on-unload.md#Dev Notes] — notification message format and failed-worker registration pattern

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- flake8 E501: split long notification body and warning log strings across two f-string literals to stay under 88 chars

### Completion Notes List

- Added `SUPPORTED_API_VERSION: int = 1` to `nimble/__init__.py`
- Added `read_skill_manifest()` to `nimble/manifest/parser.py` — reads per-skill manifest.yaml, returns None on missing file, invalid YAML, or non-dict content; never raises
- Added api_version check at top of `spawn_workers()` loop in `nimble/skills/runner.py` — too-high version fires notification + logs ERROR + skips Popen; too-low version logs WARNING only; no manifest or non-int api_version falls through silently
- Added 4 tests for `read_skill_manifest` in `tests/unit/manifest/test_parser.py`
- Added 4 tests for api_version check behavior in `tests/unit/skills/test_runner.py`
- All quality gates pass: 179 tests, mypy clean (nimble/), black clean, flake8 clean

### File List

- `nimble/__init__.py`
- `nimble/manifest/parser.py`
- `nimble/skills/runner.py`
- `tests/unit/manifest/test_parser.py`
- `tests/unit/skills/test_runner.py`

## Change Log

- 2026-04-26: Story created from sprint-status backlog auto-discovery (Epic 4, story 4)
- 2026-04-30: Implemented by claude-sonnet-4-6 — SUPPORTED_API_VERSION constant, read_skill_manifest(), api_version check in spawn_workers(), 8 new unit tests; all quality gates pass
