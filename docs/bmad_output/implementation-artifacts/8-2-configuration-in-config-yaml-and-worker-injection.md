# Story 8.2: `configuration` in `config.yaml` + Worker Injection

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a skill author,
I want my skill to receive user-defined configuration values as `self.configuration` in both `on_load` and `run()`,
So that I can parameterise my skill's behaviour without hardcoding values or prompting the user on every invocation.

## Acceptance Criteria

1. **Given** a skill entry in `config.yaml` with a `configuration: {target_language: es}` block
   **When** `_parse_skills()` parses it
   **Then** the resulting `SkillConfig.configuration == {"target_language": "es"}`

2. **Given** a skill entry with no `configuration` key
   **When** parsed
   **Then** `SkillConfig.configuration == {}` — absence is not an error

3. **Given** a `SkillConfig` with a non-empty `configuration` dict
   **When** `runner.py` builds `skill_config_json`
   **Then** it includes `"configuration": {"target_language": "es"}` in the JSON payload sent via `NIMBLE_SKILL_CONFIG`

4. **Given** the worker subprocess starts and `NIMBLE_SKILL_CONFIG` contains `"configuration": {...}`
   **When** the worker initialises the skill instance
   **Then** `skill.configuration` is set to the dict before `on_load` is called

5. **Given** a skill's `run()` method accesses `self.configuration["target_language"]`
   **When** `run()` is called
   **Then** it returns the value from `config.yaml` — `self.configuration` is available without `on_load` being defined

6. **Given** a skill with no `configuration` in `config.yaml`
   **When** `self.configuration` is accessed
   **Then** it returns `{}` — never raises `AttributeError`

7. **Given** an existing skill that defines `on_load(self, config)` and reads `config["name"]`
   **When** the worker calls `on_load`
   **Then** `config["name"]` still works — the `configuration` key is additive to the existing `skill_config` dict, not replacing it

## Tasks / Subtasks

- [x] Task 1: Add `configuration` field to `SkillConfig` in `nimble/skills/registry.py` (AC: 1, 2)
  - [x] Change `from dataclasses import dataclass` to `from dataclasses import dataclass, field`
  - [x] Add `configuration: dict[str, str] = field(default_factory=dict)` as the last field in `SkillConfig` (after `class_name`)
  - [x] No other changes to `registry.py`

- [x] Task 2: Add `_parse_skill_configuration()` helper and wire it into `_parse_skills()` in `nimble/manifest/parser.py` (AC: 1, 2)
  - [x] Add `def _parse_skill_configuration(entry: dict[str, Any], i: int) -> dict[str, str]:` helper function near the other helpers (before `_parse_skills`)
  - [x] If `configuration` key absent → return `{}`; if not a dict → raise `ConfigError`; iterate items: validate string keys, coerce values to `str(v)` — return `dict[str, str]`
  - [x] In `_parse_skills()`, call `_parse_skill_configuration(entry, i)` and pass result as `configuration=` kwarg to `SkillConfig(...)`

- [x] Task 3: Include `configuration` in `skill_config_json` in `nimble/skills/runner.py` (AC: 3)
  - [x] In `spawn_workers()`, add `"configuration": config.configuration` to the `skill_config_json = json.dumps({...})` dict (after `class_name`)
  - [x] No other changes to `runner.py`

- [x] Task 4: Set `skill.configuration` in `worker/entrypoint.py` before `on_load` (AC: 4, 5, 6, 7)
  - [x] After `skill = skill_class()` (and after the tools build), extract configuration from `skill_config`: `raw_cfg = skill_config.get("configuration")` — if it's a `dict`, coerce to `dict[str, str]`; otherwise default to `{}`
  - [x] Set `skill.configuration = configuration` — before the `if hasattr(skill, "on_load"):` block
  - [x] `on_load(skill_config)` call is unchanged — `skill_config` already contains all keys including the new `"configuration"` key

- [x] Task 5: Write tests (AC: 1–7)
  - [x] `tests/unit/manifest/test_parser.py`: test `load_config` / `_parse_skills` populates `SkillConfig.configuration`; test absence → `{}`; test invalid type raises `ConfigError`
  - [x] `tests/unit/skills/test_runner.py`: test `spawn_workers` includes `"configuration"` in `NIMBLE_SKILL_CONFIG` env var (parse the JSON from `mock_popen` kwargs)
  - [x] `tests/unit/worker/test_entrypoint.py`: test `skill.configuration` is set before `on_load`; test `skill.configuration == {}` when `NIMBLE_SKILL_CONFIG` has no `configuration` key; test `on_load` still receives full `skill_config` including `"name"` key

- [x] Task 6: Quality gates
  - [x] `flake8 nimble/ tests/ worker/` — exits 0 (max line length 88 per `pyproject.toml`)
  - [x] `mypy nimble/ tests/ worker/ --strict` — exits 0 (7 pre-existing errors in unrelated files)
  - [x] `pytest tests/` — all tests pass (no regressions)

## Dev Notes

### What This Story Delivers

Four files change, one concept flows through all of them:

1. `nimble/skills/registry.py` — `SkillConfig` gains `configuration: dict[str, str]`
2. `nimble/manifest/parser.py` — `_parse_skills()` extracts the `configuration` block from `config.yaml`
3. `nimble/skills/runner.py` — `skill_config_json` payload includes `"configuration"`
4. `worker/entrypoint.py` — worker sets `skill.configuration` before calling `on_load`

**Explicitly out of scope:**
- `nimble add` interactive prompting (Story 8.3)
- `append_skill_to_config()` writing a `configuration:` block (Story 8.3)
- Any changes to `ManifestSpec` or `ConfigFieldSpec` (Story 8.1, already done)

### Exact Changes Per File

#### `nimble/skills/registry.py`

Current import:
```python
from dataclasses import dataclass
```

New import:
```python
from dataclasses import dataclass, field
```

Current `SkillConfig`:
```python
@dataclass
class SkillConfig:
    name: str
    source: SkillSource
    binding: str
    path: str
    class_name: str
```

New `SkillConfig` (add one field at the end):
```python
@dataclass
class SkillConfig:
    name: str
    source: SkillSource
    binding: str
    path: str
    class_name: str
    configuration: dict[str, str] = field(default_factory=dict)
```

**No other changes.** All existing `SkillConfig(name=..., source=..., ...)` call sites use keyword args — the new field's default means they all continue to work unchanged.

#### `nimble/manifest/parser.py`

Add this helper function **before** `_parse_skills()` (around line 370):

```python
def _parse_skill_configuration(
    entry: dict[str, Any], i: int
) -> dict[str, str]:
    raw = entry.get("configuration")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(
            f"Skill entry at index {i} 'configuration' must be a mapping"
        )
    result: dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            raise ConfigError(
                f"Skill entry at index {i} 'configuration' keys must be strings"
            )
        result[k] = str(v)
    return result
```

Values are coerced to strings via `str(v)` — if someone writes `count: 5` in YAML (integer), it becomes `"5"`. Keys must be strings (YAML mapping keys are always strings anyway, but we validate defensively).

In `_parse_skills()`, the `skills.append(SkillConfig(...))` block currently ends at line ~405. Change it to:

```python
skills.append(
    SkillConfig(
        name=entry["name"],
        source=source,
        binding=entry["binding"],
        path=entry["path"],
        class_name=entry["class_name"],
        configuration=_parse_skill_configuration(entry, i),  # NEW
    )
)
```

#### `nimble/skills/runner.py`

In `spawn_workers()`, the `skill_config_json = json.dumps({...})` block is at lines 124–132. Add one key:

```python
skill_config_json = json.dumps(
    {
        "name": config.name,
        "source": config.source,
        "binding": config.binding,
        "path": config.path,
        "class_name": config.class_name,
        "configuration": config.configuration,  # NEW
    }
)
```

No other changes to `runner.py`.

#### `worker/entrypoint.py`

In the `run()` function, after `skill = skill_class()` succeeds (and after `tools = _build_tools()` succeeds), add the configuration injection **before** `if hasattr(skill, "on_load"):`. The exact insertion point is between the `tools` construction block (line ~170) and the `on_load` block (line ~172):

```python
# Inject configuration before on_load and run()
configuration: dict[str, str] = {}
raw_cfg = skill_config.get("configuration")
if isinstance(raw_cfg, dict):
    configuration = {str(k): str(v) for k, v in raw_cfg.items()}
skill.configuration = configuration
```

The `skill_config` dict already contains the `"configuration"` key (added in Task 3), so `on_load(skill_config)` naturally receives `config["configuration"]` too (AC 7 — additive, not replacing).

### Test Patterns to Follow

#### `tests/unit/manifest/test_parser.py`

Follow the existing `_write_config(tmp_path, content)` pattern and `load_config()` call:

```python
def test_load_config_skill_with_configuration(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        "skills:\n"
        "  - name: translator\n"
        "    source: local\n"
        "    path: skills/translator/skill.py\n"
        "    class_name: Translator\n"
        "    binding: ctrl+shift+t\n"
        "    configuration:\n"
        "      target_language: es\n"
        "      fallback: en\n",
    )
    result = load_config(cfg)
    assert len(result.skills) == 1
    assert result.skills[0].configuration == {"target_language": "es", "fallback": "en"}


def test_load_config_skill_no_configuration_defaults_to_empty(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        "skills:\n"
        "  - name: my_skill\n"
        "    source: local\n"
        "    path: skills/my_skill/skill.py\n"
        "    class_name: MySkill\n"
        "    binding: ctrl+x\n",
    )
    result = load_config(cfg)
    assert result.skills[0].configuration == {}


def test_load_config_skill_configuration_non_dict_raises(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        "skills:\n"
        "  - name: bad_skill\n"
        "    source: local\n"
        "    path: skills/bad_skill/skill.py\n"
        "    class_name: BadSkill\n"
        "    binding: ctrl+b\n"
        "    configuration: not_a_dict\n",
    )
    with pytest.raises(ConfigError):
        load_config(cfg)
```

Also test integer YAML values are coerced to strings:
```python
def test_load_config_skill_configuration_coerces_values_to_str(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        "skills:\n"
        "  - name: my_skill\n"
        "    source: local\n"
        "    path: skills/my_skill/skill.py\n"
        "    class_name: MySkill\n"
        "    binding: ctrl+x\n"
        "    configuration:\n"
        "      count: 5\n",
    )
    result = load_config(cfg)
    assert result.skills[0].configuration == {"count": "5"}
```

#### `tests/unit/skills/test_runner.py`

The `_make_config()` helper uses keyword args, so it continues working after adding `configuration` to `SkillConfig`. To test that `runner.py` passes `configuration` in the payload, use the existing `mock_popen` pattern:

```python
def test_spawn_workers_passes_configuration_in_skill_config_json() -> None:
    config = SkillConfig(
        name="my-skill",
        source="local",  # type: ignore[arg-type]
        binding="ctrl+shift+a",
        path="/path/to/skill.py",
        class_name="MySkill",
        configuration={"target_language": "es"},
    )
    registry = SkillRegistry()
    runner = _make_runner(registry=registry)
    ok_response = {"invocation_id": "abc", "status": "ok", "error": None}
    fake_proc = _make_fake_proc(ok_response)

    with patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
        runner.spawn_workers([config])
        _, kwargs = mock_popen.call_args
        env = kwargs["env"]
        skill_config = json.loads(env["NIMBLE_SKILL_CONFIG"])
        assert skill_config["configuration"] == {"target_language": "es"}
```

#### `tests/unit/worker/test_entrypoint.py`

Use the existing `_run_with_lines()` pattern but also check `skill.configuration`. For `on_load` testing, check with a skill class that has `on_load`:

```python
def test_worker_sets_skill_configuration_before_on_load() -> None:
    on_load_config: dict[str, Any] = {}

    class _ConfigSkill:
        def on_load(self, config: dict[str, Any]) -> None:
            on_load_config.update(config)

        def run(self, context: Context, tools: Any) -> None:
            pass

    skill_instance = _ConfigSkill()
    stdout_buf = io.StringIO()
    fake_class = MagicMock(return_value=skill_instance)

    env = {
        **os.environ,
        "NIMBLE_SKILL_CONFIG": json.dumps(
            {
                "name": "translator",
                "source": "local",
                "binding": "ctrl+t",
                "path": "skills/translator/skill.py",
                "class_name": "Translator",
                "configuration": {"target_language": "es"},
            }
        ),
    }
    with (
        patch.object(entrypoint_mod, "_load_skill_class", return_value=fake_class),
        patch("sys.stdin", io.StringIO("")),
        patch("sys.stdout", stdout_buf),
        patch.dict(os.environ, env, clear=True),
    ):
        entrypoint_mod.run("fake/path.py", "FakeSkill")

    assert skill_instance.configuration == {"target_language": "es"}
    # on_load still receives the full skill_config dict including "name"
    assert on_load_config["name"] == "translator"
    assert on_load_config["configuration"] == {"target_language": "es"}


def test_worker_configuration_defaults_to_empty_dict() -> None:
    skill_instance = _FakeSkill()
    stdout_buf = io.StringIO()
    fake_class = MagicMock(return_value=skill_instance)

    # NIMBLE_SKILL_CONFIG with no "configuration" key
    env = {
        **os.environ,
        "NIMBLE_SKILL_CONFIG": json.dumps(
            {
                "name": "my_skill",
                "source": "local",
                "binding": "ctrl+x",
                "path": "skills/my_skill/skill.py",
                "class_name": "MySkill",
            }
        ),
    }
    with (
        patch.object(entrypoint_mod, "_load_skill_class", return_value=fake_class),
        patch("sys.stdin", io.StringIO("")),
        patch("sys.stdout", stdout_buf),
        patch.dict(os.environ, env, clear=True),
    ):
        entrypoint_mod.run("fake/path.py", "FakeSkill")

    assert skill_instance.configuration == {}
```

### Architecture Compliance

- `mypy --strict` is enforced project-wide — every new function and field must be fully annotated
- Max line length: 88 (pyproject.toml `[tool.black]`)
- Import order: stdlib → third-party → local (enforced by flake8)
- `from __future__ import annotations` is already at the top of `parser.py` (line 1) and `runner.py` (line 1)
- `worker/entrypoint.py` does NOT have `from __future__ import annotations` — use inline type annotations that work without it (e.g. `dict[str, str]` is fine in Python 3.10+)
- Absolute imports only — no relative imports
- All new dataclass fields use `field(default_factory=...)` for mutable defaults (same pattern as `requires` in `ManifestSpec`)

### Previous Story Intelligence (Story 8.1)

Story 8.1 established:
- `ConfigFieldSpec` dataclass in `parser.py` — `config_fields` on `ManifestSpec` describes what configuration keys a skill *declares*. Story 8.2 is what *delivers* the configuration values to the skill at runtime.
- The `_parse_config_fields()` + `_parse_config_field_entry()` helpers in `parser.py` are the model to follow for `_parse_skill_configuration()` — same file, same validation style, same `ConfigError` exception
- `ManifestSpec.config_fields` is already done — do NOT touch `ManifestSpec`, `ConfigFieldSpec`, or `parse_manifest_yaml()`
- `test_parser.py` uses `_write_config(tmp_path, content)` + `load_config()` — follow exactly; do NOT create a new test file

### Git History Relevant Patterns

From recent commits:
- `e6af40d refactor: split _parse_config_fields into focused helpers` — the helper pattern in `parser.py` was refactored to small focused functions. Follow the same decomposed style for `_parse_skill_configuration`.
- `f6429c4 fix: fix remaining flake8 errors` — E501 (line too long) was a recurring issue. Keep lines under 88 chars.
- `7c8fe6d fix: resolve flake8 E501 and mypy type-arg errors` — mypy errors in parser helpers were specifically `type-arg` errors (missing type args on generic types). Always fully qualify generics: `dict[str, str]` not `dict`.

### Project Structure Notes

Files to change (exactly four):
- `nimble/skills/registry.py` — one import change, one field addition
- `nimble/manifest/parser.py` — one helper function added, one line added to `_parse_skills()`
- `nimble/skills/runner.py` — one key added to `skill_config_json` dict
- `worker/entrypoint.py` — four lines added between `_build_tools()` and `on_load`

Test files to extend (never create new files):
- `tests/unit/manifest/test_parser.py` — extend existing file (already imports `SkillConfig`)
- `tests/unit/skills/test_runner.py` — extend existing file
- `tests/unit/worker/test_entrypoint.py` — extend existing file

### References

- Story 8.2 AC: [Source: docs/bmad_output/planning-artifacts/epics.md#Story-8.2]
- `SkillConfig` dataclass: [Source: nimble/skills/registry.py#14-20]
- `_parse_skills()` function: [Source: nimble/manifest/parser.py#370-407]
- `skill_config_json` construction in `spawn_workers()`: [Source: nimble/skills/runner.py#124-132]
- `run()` function in worker — `skill_config` parsing and `on_load` call: [Source: worker/entrypoint.py#139-184]
- `_parse_config_fields()` helper style reference: [Source: nimble/manifest/parser.py#170-178]
- `field(default_factory=dict)` precedent: [Source: nimble/manifest/parser.py#45-47]
- `mypy --strict` enforcement: [Source: pyproject.toml#[tool.mypy]]
- Flake8 line-length 88: [Source: pyproject.toml#[tool.black]]
- Test pattern for `load_config`: [Source: tests/unit/manifest/test_parser.py#47-100]
- Test pattern for `spawn_workers`: [Source: tests/unit/skills/test_runner.py#50-80]
- Test pattern for `worker/entrypoint.run()`: [Source: tests/unit/worker/test_entrypoint.py#40-65]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Task 1: Added `configuration: dict[str, str] = field(default_factory=dict)` to `SkillConfig`. Updated import from `dataclass` to `dataclass, field`. All existing call sites use keyword args — no breakage.
- Task 2: Added `_parse_skill_configuration()` helper in `parser.py` (before `_parse_skills`). Validates: absent → `{}`, non-dict → `ConfigError`, coerces values to `str`. Wired into `_parse_skills()` as `configuration=` kwarg.
- Task 3: Added `"configuration": config.configuration` to `skill_config_json` in `runner.py`. Single key addition, no other changes.
- Task 4: Injected configuration into `skill.configuration` in `worker/entrypoint.py` between `_build_tools()` and the `on_load` block. `on_load` still receives the full `skill_config` dict (additive, not replacing).
- Task 5: Added 8 new tests across 3 files (4 in test_parser.py, 2 in test_runner.py, 2 in test_entrypoint.py). All 329 tests pass.
- Task 6: flake8 clean, mypy no new errors, pytest 329/329 passed.

### File List

- nimble/skills/registry.py
- nimble/manifest/parser.py
- nimble/skills/runner.py
- worker/entrypoint.py
- tests/unit/manifest/test_parser.py
- tests/unit/skills/test_runner.py
- tests/unit/worker/test_entrypoint.py

## Change Log

- 2026-05-05: Implemented Story 8.2 — `configuration` field added to `SkillConfig`, parsed from `config.yaml`, injected into `NIMBLE_SKILL_CONFIG` JSON, and set on `skill.configuration` before `on_load` in the worker. 8 new tests added.

## Review Findings

- [x] [Review][Patch] Test gap: AC 5 & 6 not fully exercised [tests/unit/worker/test_entrypoint.py]
  - **Fixed:** Added two new test cases:
    - `test_worker_skill_run_accesses_configuration_with_values` — exercises AC 5: verifies skill can access `self.configuration` during `run()` execution
    - `test_worker_skill_run_accesses_empty_configuration_no_error` — exercises AC 6: verifies `self.configuration` returns `{}` without raising `AttributeError`
  - All tests pass (331 total, +2 new)
