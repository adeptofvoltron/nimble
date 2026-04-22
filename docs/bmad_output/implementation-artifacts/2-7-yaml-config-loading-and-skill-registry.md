# Story 2.7: YAML Config Loading and Skill Registry

Status: done

## Story

As a skill author,
I want to define my hotkey bindings and skill paths in a `config.yaml` file,
so that the daemon knows which skills to load and which shortcuts to register.

## Acceptance Criteria

1. **Given** `config.yaml` exists at repo root with a `skills` list
   **When** `nimble/manifest/parser.py` parses it via `load_config(config_path)`
   **Then** it returns a `NimbleConfig` dataclass containing a `list[SkillConfig]` with all fields resolved — mypy strict-typed throughout

2. **Given** a skill entry has `source: local` and a valid `path`
   **When** `validate_skill_paths(configs, base_path)` in `nimble/skills/loader.py` is called
   **And** the validated configs are fed into `runner.spawn_workers()` (Story 2.6 — already exists)
   **Then** the registry holds a mapping of skill name → `SkillWorker` with `source`, `binding`, and `status == "loaded"`

3. **Given** `config.yaml` has a YAML syntax error (e.g. tab character in indentation)
   **When** `load_config()` reads it
   **Then** it raises `ConfigError` with message `"config.yaml line N: <yaml error description>"` — never a raw PyYAML exception (FR29)

4. **Given** a skill entry references a file path that does not exist on disk
   **When** `validate_skill_paths()` checks each path against the base directory
   **Then** it raises `ConfigError` identifying the skill name and missing path — not a silent failure (NFR13)

## Tasks / Subtasks

- [x] Task 1: Create `nimble/manifest/__init__.py` (AC: all)
  - [x] Empty package init — mirrors `nimble/context/__init__.py` and `nimble/skills/__init__.py` pattern

- [x] Task 2: Create `nimble/manifest/parser.py` — config.yaml parser (AC: 1, 3)
  - [x] Define `class ConfigError(Exception)` — single exception for all config problems (syntax + field validation)
  - [x] Define `@dataclass NimbleConfig` with field `skills: list[SkillConfig]`
  - [x] Define `load_config(config_path: Path) -> NimbleConfig` — public entry point
    - [x] Open and parse YAML via `yaml.safe_load()`
    - [x] Catch `yaml.YAMLError` → re-raise as `ConfigError(f"config.yaml line {line}: {problem}")` using `exc.problem_mark.line + 1` and `exc.problem`; fall back to `"?"` and `str(exc)` if attrs absent
    - [x] Treat `None` result from `safe_load` (empty file) as `{}`
    - [x] Call `_parse_skills(data.get("skills", []))` — unknown top-level keys (e.g. `bindings`) silently ignored
    - [x] Return `NimbleConfig(skills=parsed_skills)`
  - [x] Define `_parse_skills(raw: Any) -> list[SkillConfig]` — module-level helper, NOT a public API
    - [x] Raise `ConfigError` if `raw` is not a `list`
    - [x] For each entry: validate it is a `dict`, validate all 5 required fields present (`name`, `source`, `path`, `class_name`, `binding`)
    - [x] Validate `source` is `"local"` or `"community"` — raise `ConfigError` on invalid value with entry index
    - [x] Construct and append `SkillConfig(name=..., source=..., binding=..., path=..., class_name=...)`
  - [x] All functions annotated; `mypy --strict` passes; absolute imports only; module-level logger

- [x] Task 3: Create `nimble/skills/loader.py` — skill path validator (AC: 2, 4)
  - [x] Define `validate_skill_paths(configs: list[SkillConfig], base_path: Path) -> list[SkillConfig]`
    - [x] For each config: construct `skill_path = base_path / config.path`
    - [x] If `not skill_path.exists()`: raise `ConfigError(f"Skill '{config.name}': path '{config.path}' does not exist")`
    - [x] Return same `configs` list unchanged if all paths valid
  - [x] Import `ConfigError` from `nimble.manifest.parser` — do NOT redefine it here
  - [x] All functions annotated; `mypy --strict` passes; absolute imports only; module-level logger

- [x] Task 4: Create `tests/unit/manifest/__init__.py` (AC: all)
  - [x] Empty — mirrors `tests/unit/skills/__init__.py` pattern

- [x] Task 5: Create `tests/unit/manifest/test_parser.py` (AC: 1, 3)
  - [x] `test_load_single_local_skill()`: write valid YAML to `tmp_path / "config.yaml"`, call `load_config()`, assert `NimbleConfig.skills[0]` has correct name, source, binding, path, class_name
  - [x] `test_load_empty_skills_list()`: `skills: []` → `NimbleConfig(skills=[])`
  - [x] `test_load_missing_skills_key()`: YAML with only `bindings: []` (no `skills` key) → `NimbleConfig(skills=[])` — missing key treated as empty
  - [x] `test_load_syntax_error_raises_config_error_with_line()`: write `"skills:\n\t- name: oops\n"` (tab before list item) to tmp file, assert `ConfigError` with `"line"` in message
  - [x] `test_load_missing_required_field_raises_config_error()`: skill entry missing `class_name` → `ConfigError`
  - [x] `test_load_invalid_source_raises_config_error()`: `source: invalid` → `ConfigError`
  - [x] `test_load_community_skill_parsed_correctly()`: skill with `source: community` → `SkillConfig.source == "community"`
  - [x] Use `tmp_path` pytest fixture for all file I/O — never read the real `config.yaml`

- [x] Task 6: Create `tests/unit/skills/test_loader.py` (AC: 2, 4)
  - [x] `test_validate_all_paths_exist()`: create skill `.py` file in `tmp_path`, call `validate_skill_paths()`, assert returns same list unchanged
  - [x] `test_validate_missing_path_raises_config_error()`: skill config pointing to non-existent file → `ConfigError` with skill name in message
  - [x] `test_validate_multiple_skills_first_missing_raises()`: two skills, first path missing → `ConfigError` names the missing skill
  - [x] `test_full_chain_parser_loader_registry()`: write `config.yaml` + skill `.py` in `tmp_path` → parse → validate → mock `subprocess.Popen` → `runner.spawn_workers()` → assert `registry.get(name).status == "loaded"` and `source`/`binding` correct (AC2 integration test)
    - [x] Use `unittest.mock.patch("subprocess.Popen")` with `MagicMock()` — never spawn real subprocesses
    - [x] Set `mock_proc.poll.return_value = None` (worker alive) and mock `stdin`, `stdout`, `stderr` attributes

- [x] Task 7: Verify quality gates (AC: all)
  - [x] `mypy nimble/ tests/ worker/` — exits 0 (strict mode)
  - [x] `pytest` — all tests pass (63 existing + 11 new = 74 total)
  - [x] `black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

## Dev Notes

### Role in the Daemon Architecture

Story 2.7 adds the config loading layer that bridges `config.yaml` to the pre-warmed worker pool from Story 2.6. After this story, the startup chain is:

```
config.yaml (on disk)
  → load_config(config_path)        [nimble/manifest/parser.py]   ← THIS STORY
  → validate_skill_paths(configs)   [nimble/skills/loader.py]     ← THIS STORY
  → runner.spawn_workers(configs)   [nimble/skills/runner.py]     Story 2.6 (DONE)
  → SkillRegistry                   [nimble/skills/registry.py]   Story 2.6 (DONE)
```

Story 2.8 (daemon main loop) wires these together in `daemon.py` and adds the `watchdog` file watcher for live reloading. This story is purely the parser and loader — not yet connected to a running daemon.

### New Files (all new — no existing files modified)

```
nimble/manifest/__init__.py          ← new (empty)
nimble/manifest/parser.py            ← new
nimble/skills/loader.py              ← new
tests/unit/manifest/__init__.py      ← new (empty)
tests/unit/manifest/test_parser.py   ← new
tests/unit/skills/test_loader.py     ← new
```

Do NOT modify: `nimble/skills/registry.py`, `nimble/skills/runner.py`, `worker/`, `nimble/hotkeys/`, `nimble/context/`, `tests/conftest.py`.

### `config.yaml` Schema for This Story

Current `config.yaml` at repo root is `skills: []\nbindings: []`. The parser reads the `skills` list; `bindings` and all other top-level keys are silently ignored. A populated `config.yaml` looks like:

```yaml
skills:
  - name: hello-world
    source: local
    path: skills/hello_world/skill.py
    class_name: HelloWorldSkill
    binding: ctrl+shift+h
  - name: log-diagnosis
    source: community
    path: skills/log_diagnosis/skill.py
    class_name: LogDiagnosisSkill
    binding: ctrl+shift+d
```

All 5 fields (`name`, `source`, `path`, `class_name`, `binding`) are required. The `disabled` field (used by `nimble disable` in Story 5.3) and `installed_from`/`version` fields (used by `nimble add` in Story 6.x) are not yet needed — do not add them.

### `NimbleConfig` and Import Chain

```python
# nimble/manifest/parser.py
from nimble.skills.registry import SkillConfig  # SkillConfig already exists from 2.6

@dataclass
class NimbleConfig:
    skills: list[SkillConfig]
```

Import chain — no circular dependencies:
```
nimble.skills.registry   → defines SkillConfig (no imports from manifest or loader)
    ↑
nimble.manifest.parser   → imports SkillConfig; defines ConfigError + NimbleConfig
    ↑
nimble.skills.loader     → imports SkillConfig from registry + ConfigError from parser
```

### PyYAML Error Extraction

```python
import yaml

try:
    with config_path.open() as f:
        data = yaml.safe_load(f)
except yaml.YAMLError as exc:
    mark = getattr(exc, "problem_mark", None)
    line = (mark.line + 1) if mark else "?"
    problem = getattr(exc, "problem", str(exc))
    raise ConfigError(f"config.yaml line {line}: {problem}") from exc
```

`mark.line` is 0-indexed; `+ 1` converts to 1-indexed (human-readable). The `getattr` fallbacks handle edge cases where `ScannerError` attrs are missing. The AC requires exactly: `"config.yaml line N: <description>"`.

### Triggering a YAML Syntax Error in Tests

Tab characters before YAML list items reliably trigger `yaml.scanner.ScannerError`:

```python
bad_yaml.write_text("skills:\n\t- name: oops\n")
```

This gives `problem_mark.line == 1` → `ConfigError("config.yaml line 2: ...")`.

### `validate_skill_paths` Pattern

```python
from nimble.manifest.parser import ConfigError
from nimble.skills.registry import SkillConfig
from pathlib import Path

def validate_skill_paths(configs: list[SkillConfig], base_path: Path) -> list[SkillConfig]:
    for config in configs:
        skill_path = base_path / config.path
        if not skill_path.exists():
            raise ConfigError(
                f"Skill '{config.name}': path '{config.path}' does not exist"
            )
    return configs
```

`base_path` is the repo root (directory containing `config.yaml`). If `config.path` is absolute, `base_path / absolute_path` returns the absolute path unchanged — fine for now since YAML paths should always be relative. Tests use `tmp_path` as `base_path`.

### Full-Chain AC2 Test Scaffold

```python
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nimble.manifest.parser import load_config
from nimble.skills.loader import validate_skill_paths
from nimble.skills.registry import SkillRegistry
from nimble.skills.runner import SkillRunner


def test_full_chain_parser_loader_registry(tmp_path: Path) -> None:
    skill_file = tmp_path / "skills" / "hello.py"
    skill_file.parent.mkdir()
    skill_file.write_text("class HelloSkill:\n    pass\n")

    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text(
        "skills:\n"
        "  - name: hello\n"
        "    source: local\n"
        "    path: skills/hello.py\n"
        "    class_name: HelloSkill\n"
        "    binding: ctrl+shift+h\n"
    )

    nimble_config = load_config(config_yaml)
    validated = validate_skill_paths(nimble_config.skills, tmp_path)

    registry = SkillRegistry()
    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    fake_proc.stdin = MagicMock()
    fake_proc.stdout = MagicMock()
    fake_proc.stderr = MagicMock()

    with patch("subprocess.Popen", return_value=fake_proc):
        runner = SkillRunner(
            registry=registry, notifier=MagicMock(), repo_root=tmp_path
        )
        runner.spawn_workers(validated)

    worker = registry.get("hello")
    assert worker is not None
    assert worker.config.source == "local"
    assert worker.config.binding == "ctrl+shift+h"
    assert worker.status == "loaded"
```

### Patterns Carried Forward from Story 2.6

- **`from __future__ import annotations`** at top of every new module (enables `list[X]` syntax without quotes in Python 3.10+)
- **Absolute imports only** — `from nimble.skills.registry import SkillConfig`, never `from ..skills.registry import ...`
- **`@dataclass` for all structured data** — `NimbleConfig` is a dataclass, not a dict or namedtuple
- **Module-level logger** — `logger = logging.getLogger(__name__)` in parser.py and loader.py
- **`Any` from `typing`** required for `_parse_skills(raw: Any)` to satisfy strict mode
- **Never mock the real `config.yaml`** — all parser tests use `tmp_path` to write temp files

### `mypy --strict` Notes

- `NimbleConfig.skills: list[SkillConfig]` — valid with `from __future__ import annotations`
- `_parse_skills(raw: Any) -> list[SkillConfig]` — `Any` parameter acceptable in strict mode as escape hatch for unvalidated YAML input
- `validate_skill_paths(...) -> list[SkillConfig]` — return type must match the input type; do not return `list[Any]`
- `yaml` does not ship stubs; `ignore_missing_imports = true` in `pyproject.toml` already covers this

### Deferred Items (do not address in this story)

From `deferred-work.md`:
- `build_context()` worst-case latency validation — still pending
- Worker `__getattr__` footgun — deferred to reliability epic

Story 2.7 deferred to Story 4.5:
- `nimble validate` CLI command (re-uses `load_config()` + `validate_skill_paths()` — just not wired yet)

Story 2.7 deferred to Story 5.3:
- `disabled: true` field in skill config entries — parser can simply ignore it for now

Story 2.7 deferred to Story 6.1:
- `parse_manifest(manifest_path)` for community skill `manifest.yaml` — added to same `parser.py` file later

### Cross-Story Dependencies

- **Story 2.6** (DONE): `SkillConfig`, `SkillRegistry` in `nimble/skills/registry.py`; `SkillRunner.spawn_workers(configs: list[SkillConfig])` in `nimble/skills/runner.py`. Parser output is direct input to `spawn_workers()`.
- **Story 2.8** (next): `daemon.py` main loop calls `load_config(repo_root / "config.yaml")`, `validate_skill_paths(config.skills, repo_root)`, `runner.spawn_workers(validated)` as part of startup. Also wires `nimble/watcher.py` watchdog to reload on config changes.
- **Story 4.5** (later): `nimble validate` CLI re-uses `load_config()` + `validate_skill_paths()` — no changes to parser or loader needed.
- **Story 6.1** (later): Adds `parse_manifest()` to `nimble/manifest/parser.py` alongside `load_config()`.

### References

- [Source: docs/bmad_output/planning-artifacts/architecture.md#Configuration] — config.yaml schema, atomic write, file watcher rationale
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Complete Project Directory Structure] — `nimble/manifest/parser.py`, `nimble/skills/loader.py` file locations
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Error Handling Patterns] — ConfigError format with line number (FR29)
- [Source: docs/bmad_output/planning-artifacts/architecture.md#All AI Agents MUST] — naming, import, type annotation rules
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Naming Patterns] — snake_case for all YAML keys; constants UPPER_SNAKE_CASE
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Test Patterns] — `tests/unit/<package>/test_<module>.py` mirrors source structure
- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 2.7] — acceptance criteria, FR3/FR6/FR28/FR29, NFR13 coverage
- [Source: docs/bmad_output/implementation-artifacts/2-6-pre-warmed-worker-pool-and-dispatcher.md#Dataclass Structures] — exact SkillConfig field names: name, source, binding, path, class_name
- [Source: docs/bmad_output/implementation-artifacts/2-6-pre-warmed-worker-pool-and-dispatcher.md#Cross-Story Dependencies] — spawn_workers() interface confirmed

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- mypy 1.20.1 raises `[import-untyped]` for PyYAML even with `ignore_missing_imports = true` in pyproject.toml (behavior changed from older mypy). Added `# type: ignore[import-untyped]` inline on the yaml import in parser.py — targeted suppression, no new dev dependencies needed.

### Completion Notes List

- Implemented `nimble/manifest/parser.py`: `ConfigError`, `NimbleConfig` dataclass, `load_config()`, and `_parse_skills()`. All 5 required skill fields validated; YAML syntax errors wrapped with line number per FR29; empty/missing `skills` key treated as `[]`.
- Implemented `nimble/skills/loader.py`: `validate_skill_paths()` checks each skill path against `base_path`, raises `ConfigError` naming the missing skill per NFR13.
- 11 new tests (7 parser, 4 loader/integration) covering all 4 ACs. Full-chain AC2 integration test mocks `subprocess.Popen` and asserts `status == "loaded"`, `source`, and `binding` on the registry worker.
- All 74 tests pass. mypy strict, black, and flake8 all exit 0.

### File List

- nimble/manifest/__init__.py
- nimble/manifest/parser.py
- nimble/skills/loader.py
- tests/unit/manifest/__init__.py
- tests/unit/manifest/test_parser.py
- tests/unit/skills/test_loader.py

## Change Log

- 2026-04-22: Implemented YAML config loader and skill path validator. Added nimble/manifest package with ConfigError, NimbleConfig, load_config(); nimble/skills/loader.py with validate_skill_paths(). 11 new tests; 74 total pass. All quality gates (mypy strict, black, flake8) green.
