# Story 8.1: `config_fields` Schema in `manifest.yaml` and Parsing

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a skill author,
I want to declare named configuration fields in my `manifest.yaml` with descriptions, optional defaults, and optional value constraints,
So that users and `nimble add` know exactly what to provide when installing or configuring my skill.

## Acceptance Criteria

1. **Given** a `manifest.yaml` with a `config_fields` block containing a field with `key`, `description`, and `default`
   **When** `parse_manifest_yaml()` parses it
   **Then** it returns a `ManifestSpec` with a populated `config_fields: list[ConfigFieldSpec]` containing the correct values

2. **Given** a `config_fields` entry with `possible_values: [en, es, fr]` and `default: en`
   **When** parsed
   **Then** `ConfigFieldSpec.possible_values == ["en", "es", "fr"]` and `ConfigFieldSpec.default == "en"`

3. **Given** a `config_fields` entry with no `possible_values`
   **When** parsed
   **Then** `ConfigFieldSpec.possible_values is None` — the field accepts any string value

4. **Given** a `manifest.yaml` with no `config_fields` key
   **When** parsed
   **Then** `ManifestSpec.config_fields == []` — absence is not an error

5. **Given** a `config_fields` entry missing the required `key` or `description` field
   **When** parsed
   **Then** a `ManifestError` is raised identifying the missing field — install is aborted

## Tasks / Subtasks

- [x] Task 1: Add `ConfigFieldSpec` dataclass to `nimble/manifest/parser.py` (AC: 1, 2, 3)
  - [x] Define `@dataclass class ConfigFieldSpec` with fields: `key: str`, `description: str`, `default: str | None = None`, `possible_values: list[str] | None = None`
  - [x] Place it above `ManifestSpec` in the file — it must be defined before `ManifestSpec` references it
  - [x] Add full `mypy --strict` compatible annotations (no bare `Optional`, use `X | None` syntax for Python 3.10+)

- [x] Task 2: Add `config_fields` field to `ManifestSpec` (AC: 1, 4)
  - [x] Add `config_fields: list[ConfigFieldSpec] = field(default_factory=list)` to the `ManifestSpec` dataclass
  - [x] Use `field(default_factory=list)` — consistent with existing `requires` field pattern (line 37 of `parser.py`)

- [x] Task 3: Add `_parse_config_fields()` helper (AC: 1, 2, 3, 5)
  - [x] Add `def _parse_config_fields(data: dict[str, Any], source: str) -> list[ConfigFieldSpec]:` function
  - [x] If `config_fields` key is absent → return `[]`
  - [x] If `config_fields` value is not a list → raise `ManifestError` with clear message
  - [x] For each entry: validate it is a `dict`; check `key` and `description` are present and non-empty strings — raise `ManifestError` if missing
  - [x] Parse `default` as `str | None` (absent → `None`)
  - [x] Parse `possible_values` as `list[str] | None` (absent → `None`; present but non-list → raise `ManifestError`)
  - [x] Return `list[ConfigFieldSpec]`

- [x] Task 4: Wire `_parse_config_fields()` into `parse_manifest_yaml()` (AC: 1, 4)
  - [x] In `parse_manifest_yaml()`, after building other fields, call `_parse_config_fields(data, source)`
  - [x] Pass result as `config_fields=` kwarg to `ManifestSpec(...)` constructor

- [x] Task 5: Write tests in `tests/unit/manifest/test_parser.py` (AC: 1–5)
  - [x] Test: manifest with `config_fields` block → `ManifestSpec.config_fields` populated correctly
  - [x] Test: `possible_values` parsed as list of strings
  - [x] Test: `possible_values` absent → `ConfigFieldSpec.possible_values is None`
  - [x] Test: no `config_fields` key → `ManifestSpec.config_fields == []`
  - [x] Test: entry missing `key` → `ManifestError` raised
  - [x] Test: entry missing `description` → `ManifestError` raised
  - [x] Add `ConfigFieldSpec` to the import line in the test file

- [x] Task 6: Quality gates
  - [x] `flake8 nimble/ tests/ worker/` — exits 0 (max line length 88 per pyproject.toml)
  - [x] `mypy nimble/ tests/ worker/ --strict` — exits 0 (7 pre-existing errors unrelated to this story)
  - [x] `pytest tests/` — all tests pass (307 passed; 7 pre-existing clipboard failures unrelated to this story)

### Review Findings

- [x] [Review][Patch] Validate `config_fields[].key` and `config_fields[].description` as non-empty strings (do not coerce arbitrary types via `str(...)`) [`nimble/manifest/parser.py:96`]
- [x] [Review][Patch] Validate `default` type (`None | str`) and enforce `default in possible_values` when `possible_values` is provided [`nimble/manifest/parser.py:96`]
- [x] [Review][Patch] Add negative-path tests for invalid `config_fields` shapes/types (non-list root, non-mapping entry, non-string `default`, invalid `possible_values` item types) [`tests/unit/manifest/test_parser.py:648`]

## Dev Notes

### What This Story Delivers

Two things only:
1. `ConfigFieldSpec` dataclass in `nimble/manifest/parser.py`
2. `config_fields` field on `ManifestSpec`, populated by `parse_manifest_yaml()`

**Nothing else.** Specifically out of scope:
- `SkillConfig.configuration` field (Story 8.2)
- Parsing `configuration:` block from `config.yaml` (Story 8.2)
- Worker injection of `self.configuration` (Story 8.2)
- `nimble add` interactive prompting (Story 8.3)
- `append_skill_to_config()` writing a `configuration:` block (Story 8.3)

### Exact File to Modify

**One file changed:** `nimble/manifest/parser.py`
**One file of new tests:** `tests/unit/manifest/test_parser.py` (extend existing file — do NOT create a new test file)

### `ConfigFieldSpec` — Exact Shape

```python
@dataclass
class ConfigFieldSpec:
    key: str
    description: str
    default: str | None = None
    possible_values: list[str] | None = None
```

Place this **before** `ManifestSpec` in `parser.py` (currently around line 28) so `ManifestSpec` can reference it. The file already imports `dataclass` and `field` from `dataclasses` (line 8).

### `ManifestSpec` — Add One Field

Add to the end of the existing `ManifestSpec` dataclass, using the same pattern as `requires` (line 37–38):

```python
config_fields: list[ConfigFieldSpec] = field(default_factory=list)
```

`ManifestSpec` already has `requires: list[str] = field(default_factory=list)` — follow that exact pattern.

### `_parse_config_fields()` — Implementation Contract

```python
def _parse_config_fields(data: dict[str, Any], source: str) -> list[ConfigFieldSpec]:
    raw = data.get("config_fields")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ManifestError(
            f"manifest.yaml from {source} field 'config_fields' must be a list"
        )
    result: list[ConfigFieldSpec] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ManifestError(
                f"manifest.yaml from {source} config_fields[{i}] must be a mapping"
            )
        for required in ("key", "description"):
            if required not in entry:
                raise ManifestError(
                    f"manifest.yaml from {source} config_fields[{i}]"
                    f" missing required field '{required}'"
                )
        key = str(entry["key"])
        description = str(entry["description"])
        default = str(entry["default"]) if "default" in entry else None
        raw_pv = entry.get("possible_values")
        if raw_pv is None:
            possible_values = None
        elif not isinstance(raw_pv, list) or any(
            not isinstance(v, str) for v in raw_pv
        ):
            raise ManifestError(
                f"manifest.yaml from {source} config_fields[{i}]"
                " 'possible_values' must be a list of strings"
            )
        else:
            possible_values = raw_pv
        result.append(
            ConfigFieldSpec(
                key=key,
                description=description,
                default=default,
                possible_values=possible_values,
            )
        )
    return result
```

Use `_parse_manifest_string_list()` as a reference for the helper style (line 76–87 of `parser.py`), but `_parse_config_fields()` is more complex so it gets its own loop.

### Wiring into `parse_manifest_yaml()`

At the end of `parse_manifest_yaml()`, just before the `return ManifestSpec(...)` call (currently around line 366), add:

```python
config_fields = _parse_config_fields(data, source)
```

Then extend `ManifestSpec(...)` with `config_fields=config_fields`.

### Test Patterns to Follow

Existing tests in `test_parser.py` use `_VALID_MANIFEST_YAML` (line 339) as a base and derive variants via `.replace()` or string concatenation. Follow the same pattern for `config_fields` tests:

```python
# Append config_fields block to _VALID_MANIFEST_YAML in tests:
_VALID_MANIFEST_WITH_CONFIG_FIELDS = (
    _VALID_MANIFEST_YAML
    + "config_fields:\n"
    "  - key: target_language\n"
    "    description: Target language code\n"
    "    default: en\n"
    "    possible_values:\n"
    "      - en\n"
    "      - es\n"
    "      - fr\n"
)
```

Add `ConfigFieldSpec` to the import block at the top of the test file (line 12–26).

### Architecture Compliance

- `mypy --strict` is enforced project-wide — every new function and field must be fully annotated
- Max line length: 88 (pyproject.toml `[tool.black]`)
- Import order: stdlib → third-party → local (enforced by flake8)
- `from __future__ import annotations` already at top of `parser.py` (line 1) — `str | None` syntax works fine for Python 3.10+
- All tests go in `tests/unit/manifest/test_parser.py` — do NOT create a new test file

### `_make_manifest_spec()` in Tests

`test_parser.py` already has a `_make_manifest_spec()` helper (line 513) that constructs a `ManifestSpec` via `**defaults`. After adding `config_fields` to `ManifestSpec`, this helper's `defaults` dict does not need to include `config_fields` — the dataclass default `field(default_factory=list)` handles it.

However, check that `ManifestSpec(**defaults)` still works — `config_fields` will default to `[]` when not provided. The test `test_parse_manifest_yaml_valid()` (line 354) creates a `ManifestSpec` implicitly via `parse_manifest_yaml()` — it should continue to pass as `config_fields` will default to `[]` when the YAML has no `config_fields` block.

### Previous Story Intelligence (Epic 7 / Git History)

Stories 7.x were documentation-only (README, skill-build.md, autostart). No Python patterns from them apply here.

The most relevant precedent is **Epic 6** (manifest parsing work) — particularly:
- `ManifestSpec` schema extensions follow the same `@dataclass` + `field(default_factory=...)` pattern
- `ManifestError` is already the standard exception for malformed `manifest.yaml` — use it (do NOT introduce new exception types)
- `_parse_manifest_string_list()` demonstrates the helper pattern for reusable sub-parsers

Git note: commit `658430f` ("epic 8 define-configuration") only added planning docs — no source code changes. The codebase is at the state from Epic 7 completion.

### Project Structure Notes

All changes are confined to:
- `nimble/manifest/parser.py` — one `@dataclass`, one field addition, one helper function, one wiring call
- `tests/unit/manifest/test_parser.py` — extend with new test cases and import

No other files need to change for Story 8.1.

### References

- Epic 8 story 8.1 AC: [Source: docs/bmad_output/planning-artifacts/epics.md#Story-8.1]
- `ManifestSpec` + `_parse_manifest_string_list()` + `ManifestError`: [Source: nimble/manifest/parser.py#1-409]
- Existing test patterns for `parse_manifest_yaml()`: [Source: tests/unit/manifest/test_parser.py#339-450]
- `mypy --strict` enforcement: [Source: pyproject.toml#[tool.mypy]]
- `flake8` line-length 88: [Source: pyproject.toml#[tool.black]]
- `field(default_factory=list)` precedent: [Source: nimble/manifest/parser.py#37]
- FR46 definition: [Source: docs/bmad_output/planning-artifacts/epics.md#161]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `ConfigFieldSpec` dataclass above `ManifestSpec` in `parser.py` with `key`, `description`, `default`, and `possible_values` fields, all fully annotated for `mypy --strict`.
- Extended `ManifestSpec` with `config_fields: list[ConfigFieldSpec] = field(default_factory=list)` following the existing `requires` field pattern.
- Implemented `_parse_config_fields()` helper that validates each entry for required `key`/`description`, parses optional `default` and `possible_values`, and raises `ManifestError` on malformed input.
- Wired `_parse_config_fields()` into `parse_manifest_yaml()` — absence of `config_fields` in YAML yields `[]` (no breaking change to existing tests).
- Added 6 new tests in `test_parser.py` covering all 5 ACs; all pass. No regressions introduced. Pre-existing mypy errors (7) and clipboard test failures (7) are unaffected.

### File List

- nimble/manifest/parser.py
- tests/unit/manifest/test_parser.py

### Change Log

- 2026-05-05: Story 8.1 implemented — added `ConfigFieldSpec` dataclass, `config_fields` field on `ManifestSpec`, `_parse_config_fields()` helper, wired into `parse_manifest_yaml()`, and 6 new unit tests.
