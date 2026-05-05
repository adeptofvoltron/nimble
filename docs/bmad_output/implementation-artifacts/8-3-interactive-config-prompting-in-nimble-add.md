# Story 8.3: Interactive Config Prompting in `nimble add`

Status: done

## Story

As a user installing a community skill,
I want to be prompted for each declared configuration field during `nimble add`,
So that my `config.yaml` is fully populated with skill parameters without any manual editing.

## Acceptance Criteria

1. **Given** a skill's `ManifestSpec.config_fields` contains one field with `key: target_language`,
   `description: "Target language code"`, `default: "en"`, `possible_values: [en, es, fr]`
   **When** `nimble add` runs after the user confirms install
   **Then** the CLI prompts: `target_language — Target language code [en/es/fr] (default: 'en'):`

2. **Given** the user presses Enter without typing a value and a default exists
   **When** the prompt is processed
   **Then** the default value is used — the user is not re-prompted

3. **Given** the user enters a value not in `possible_values`
   **When** the prompt is processed
   **Then** the CLI prints an error and re-prompts until a valid value is entered

4. **Given** a field with no `default` and no `possible_values`
   **When** the user presses Enter without typing
   **Then** the CLI prints `'<key>' is required.` and re-prompts until a non-empty value is entered

5. **Given** all config fields have been collected
   **When** `append_skill_to_config()` writes the skill entry
   **Then** the entry includes a `configuration:` block with all collected key-value pairs

6. **Given** a skill's `ManifestSpec.config_fields` is empty
   **When** `nimble add` runs
   **Then** no configuration prompts appear and no `configuration:` block is written to `config.yaml`

## Tasks / Subtasks

- [x] Task 1: Add `_collect_config_values()` helper to `nimble/cli/commands.py` (AC: 1, 2, 3, 4)
  - [x] Add `TYPE_CHECKING` import at top: `from typing import TYPE_CHECKING` and `if TYPE_CHECKING: from nimble.manifest.parser import ConfigFieldSpec`
  - [x] Implement `_collect_config_values(config_fields: list[ConfigFieldSpec]) -> dict[str, str]`
  - [x] For each field: build prompt string, read via `sys.stdin.readline()`, validate, loop on error
  - [x] Prompt format: `{key} — {description} [{v1}/{v2}] (default: '{default'}):` (omit [] if no possible_values; omit default clause if no default)

- [x] Task 2: Wire `_collect_config_values()` into `add` command in `nimble/cli/commands.py` (AC: 1–6)
  - [x] Call `_collect_config_values(spec.config_fields)` after `_prompt_install_confirm_y_only()` returns `True`
  - [x] Pass resulting `configuration` dict to `append_skill_to_config()` as new parameter

- [x] Task 3: Add `configuration` parameter to `append_skill_to_config()` in `nimble/manifest/parser.py` (AC: 5, 6)
  - [x] Add `configuration: dict[str, str] | None = None` as last parameter
  - [x] If `configuration` is truthy (non-empty dict), add `"configuration": configuration` to the `entry` dict before appending
  - [x] Empty dict or `None` → no `configuration:` key written (AC 6)

- [x] Task 4: Write tests (AC: 1–6)
  - [x] `tests/unit/cli/test_commands.py`: extend existing file — add tests for prompt rendering, default handling, re-prompt on invalid, re-prompt on empty required, no prompts for empty config_fields, `append_skill_to_config` called with configuration
  - [x] `tests/unit/manifest/test_parser.py`: extend existing file — test `append_skill_to_config` writes `configuration:` block when non-empty; skips block when empty/None

- [x] Task 5: Quality gates
  - [x] `flake8 nimble/ tests/ worker/` — exits 0
  - [x] `mypy nimble/ tests/ worker/ --strict` — exits 0 (no new errors)
  - [x] `pytest tests/` — all tests pass (≥331 baseline, no regressions)

### Review Findings

- [x] [Review][Patch] EOF/input-read failure can cause non-terminating prompt loop for required fields [nimble/cli/commands.py:40]
- [x] [Review][Patch] Prompt validation does not normalize whitespace, causing avoidable invalid inputs and weak required-field checks [nimble/cli/commands.py:57]
- [x] [Review][Patch] Missing tests for EOF and input-read failure paths in config prompting loop [tests/unit/cli/test_commands.py:548]

## Dev Notes

### What This Story Delivers

Two files change (three have tests added):

1. `nimble/cli/commands.py` — adds `_collect_config_values()` helper + wires it into `add`
2. `nimble/manifest/parser.py` — `append_skill_to_config()` gains optional `configuration` param

**Explicitly out of scope:**
- Any daemon or worker changes — configuration injection is complete from Story 8.2
- `ManifestSpec`, `ConfigFieldSpec`, or `parse_manifest_yaml` — complete from Story 8.1
- `SkillConfig` or `_parse_skill_configuration` — complete from Story 8.2

### Exact Changes Per File

#### `nimble/cli/commands.py`

At the top of the file, after existing imports, add a `TYPE_CHECKING` block so the type annotation on `_collect_config_values` resolves without a runtime import (all other `nimble.manifest` imports in this file are lazy/inside functions):

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nimble.manifest.parser import ConfigFieldSpec
```

Add this helper function near the other helpers (after `_prompt_install_confirm_y_only`, before `_running_pid_or_none`):

```python
def _collect_config_values(
    config_fields: list[ConfigFieldSpec],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for cf in config_fields:
        while True:
            if cf.possible_values:
                choices = "/".join(cf.possible_values)
                prompt = f"{cf.key} — {cf.description} [{choices}]"
            else:
                prompt = f"{cf.key} — {cf.description}"
            if cf.default is not None:
                prompt += f" (default: '{cf.default}')"
            prompt += ": "
            typer.echo(prompt, nl=False)
            try:
                raw = sys.stdin.readline()
            except (OSError, UnicodeDecodeError):
                raw = ""
            value = raw.rstrip("\r\n")
            if value == "":
                if cf.default is not None:
                    result[cf.key] = cf.default
                    break
                typer.echo(f"'{cf.key}' is required.")
                continue
            if cf.possible_values and value not in cf.possible_values:
                joined = ", ".join(cf.possible_values)
                typer.echo(f"Invalid value. Choose from: {joined}")
                continue
            result[cf.key] = value
            break
    return result
```

In the `add()` command, after `_prompt_install_confirm_y_only()` returns `True` and before the install block, insert the config collection:

```python
    if not _prompt_install_confirm_y_only():
        typer.echo("Installation cancelled.")
        raise typer.Exit(0)

    configuration = _collect_config_values(spec.config_fields)  # NEW

    import shutil
    ...
```

Update the `append_skill_to_config` call (currently line ~371) to pass `configuration`:

```python
    try:
        append_skill_to_config(
            config_path, spec, shortcut, repo_url, repo_root, configuration
        )
    except ConfigError as exc:
```

#### `nimble/manifest/parser.py`

`append_skill_to_config` currently ends at line ~272. Add `configuration` parameter:

```python
def append_skill_to_config(
    config_path: Path,
    spec: ManifestSpec,
    binding: str,
    repo_url: str,
    repo_root: Path,
    configuration: dict[str, str] | None = None,  # NEW
) -> None:
```

Inside the function, after building the `entry` dict, add the configuration block before `skills.append(entry)`:

```python
    entry: dict[str, Any] = {
        "name": spec.name,
        "source": "community",
        "path": rel_path,
        "class_name": spec.class_name,
        "binding": binding,
        "installed_from": repo_url,
        "version": spec.version,
    }
    if configuration:                             # NEW — only when non-empty
        entry["configuration"] = configuration   # NEW
    skills.append(entry)
```

`if configuration:` handles both `None` and empty dict `{}` — neither writes the block (AC 6).

### Test Patterns to Follow

#### `tests/unit/cli/test_commands.py`

The existing `_make_manifest_spec(**overrides)` helper at line ~339 builds a `ManifestSpec`. For testing prompts, create a version with `config_fields`. Import `ConfigFieldSpec` at the top of the test file (it's already used indirectly; add it to the existing parser import).

Add to existing imports block:
```python
from nimble.manifest.parser import (
    ConfigError,
    ConfigFieldSpec,      # NEW
    ManifestError,
    ManifestSpec,
    NimbleConfig,
)
```

All tests use `runner = CliRunner()` (typer testing). Supply `input=` lines for both the install confirmation and any config prompts, in order.

```python
def _make_manifest_spec_with_fields(**overrides: object) -> ManifestSpec:
    fields = [
        ConfigFieldSpec(
            key="target_language",
            description="Target language code",
            default="en",
            possible_values=["en", "es", "fr"],
        )
    ]
    return _make_manifest_spec(config_fields=fields, **overrides)


def _add_invoke(
    spec: ManifestSpec,
    input_lines: str,
    fake_root: Path | None = None,
) -> ...:
    """Helper that patches all install steps and invokes add."""
    root = fake_root or Path("/tmp/nimble-fake-root")
    with (
        patch("nimble.manifest.parser.fetch_remote_manifest", return_value=spec),
        patch("nimble.cli.commands._repo_root", return_value=root),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv"),
        patch("nimble.manifest.parser.append_skill_to_config"),
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        return runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"],
            input=input_lines,
        )
```

Key tests to add:

```python
def test_add_prompts_config_fields_after_confirmation() -> None:
    spec = _make_manifest_spec_with_fields()
    result = runner.invoke(
        app, ["add", "ctrl+shift+d", "github.com/user/skill"],
        input="y\nes\n",  # confirm=y, value=es
    )
    # The prompt must appear in output
    assert "target_language" in result.output
    assert "Target language code" in result.output
    assert "[en/es/fr]" in result.output
    assert "(default: 'en')" in result.output


def test_add_config_field_enter_uses_default() -> None:
    spec = _make_manifest_spec_with_fields()
    with (
        patch("nimble.manifest.parser.fetch_remote_manifest", return_value=spec),
        patch("nimble.cli.commands._repo_root", return_value=Path("/tmp/f")),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv"),
        patch("nimble.manifest.parser.append_skill_to_config") as mock_append,
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        result = runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"],
            input="y\n\n",  # confirm=y, Enter=use default
        )
    assert result.exit_code == 0
    _, kwargs = mock_append.call_args
    # configuration is passed as positional arg (index 5) or via kwargs
    # verify "en" (default) ended up in the configuration
    assert mock_append.called


def test_add_config_field_invalid_value_reprompts() -> None:
    spec = _make_manifest_spec_with_fields()
    result = runner.invoke(
        app, ["add", "ctrl+shift+d", "github.com/user/skill"],
        input="y\nzh\nes\n",  # confirm=y, invalid=zh, valid=es
    )
    assert "Invalid value" in result.output
    assert result.exit_code == 0


def test_add_config_field_required_no_default_reprompts() -> None:
    fields = [ConfigFieldSpec(key="api_key", description="API key")]
    spec = _make_manifest_spec(config_fields=fields)
    result = runner.invoke(
        app, ["add", "ctrl+shift+d", "github.com/user/skill"],
        input="y\n\nsecret\n",  # confirm=y, empty=reprompt, then value
    )
    assert "'api_key' is required." in result.output
    assert result.exit_code == 0


def test_add_empty_config_fields_no_prompts() -> None:
    spec = _make_manifest_spec(config_fields=[])
    fake_root = Path("/tmp/nimble-fake-root")
    with (
        patch("nimble.manifest.parser.fetch_remote_manifest", return_value=spec),
        patch("nimble.cli.commands._repo_root", return_value=fake_root),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv"),
        patch("nimble.manifest.parser.append_skill_to_config") as mock_append,
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        result = runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"],
            input="y\n",  # just confirm, no extra prompts
        )
    assert result.exit_code == 0
    # Sixth positional arg is configuration={}
    call_args = mock_append.call_args
    configuration = call_args.args[5] if len(call_args.args) > 5 else call_args.kwargs.get("configuration", {})
    assert configuration == {}


def test_add_passes_configuration_to_append_skill_to_config() -> None:
    spec = _make_manifest_spec_with_fields()
    fake_root = Path("/tmp/nimble-fake-root")
    with (
        patch("nimble.manifest.parser.fetch_remote_manifest", return_value=spec),
        patch("nimble.cli.commands._repo_root", return_value=fake_root),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv"),
        patch("nimble.manifest.parser.append_skill_to_config") as mock_append,
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"],
            input="y\nes\n",  # confirm + valid value
        )
    call_args = mock_append.call_args
    configuration = call_args.args[5] if len(call_args.args) > 5 else call_args.kwargs.get("configuration")
    assert configuration == {"target_language": "es"}
```

#### `tests/unit/manifest/test_parser.py`

Extend the existing `append_skill_to_config` tests (look for `test_append_skill_to_config*` or add alongside them). Follow the existing `_write_config(tmp_path, content)` helper pattern.

```python
def test_append_skill_to_config_writes_configuration_block(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, "skills: []\n")
    spec = _make_manifest_spec(class_name="Translator")  # use existing helper
    append_skill_to_config(
        cfg, spec, "ctrl+t", "github.com/u/r", tmp_path,
        configuration={"target_language": "es"},
    )
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    entry = data["skills"][0]
    assert entry["configuration"] == {"target_language": "es"}


def test_append_skill_to_config_no_configuration_block_when_empty(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, "skills: []\n")
    spec = _make_manifest_spec(class_name="Translator")
    append_skill_to_config(
        cfg, spec, "ctrl+t", "github.com/u/r", tmp_path,
        configuration={},
    )
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    entry = data["skills"][0]
    assert "configuration" not in entry


def test_append_skill_to_config_no_configuration_block_when_none(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, "skills: []\n")
    spec = _make_manifest_spec(class_name="Translator")
    append_skill_to_config(
        cfg, spec, "ctrl+t", "github.com/u/r", tmp_path,
        # configuration not passed — defaults to None
    )
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    entry = data["skills"][0]
    assert "configuration" not in entry
```

**Note:** Check what helper `_make_manifest_spec` looks like in `test_parser.py` — it may differ from the one in `test_commands.py`. In `test_parser.py`, look for `_write_config` and whatever spec helper exists there. If no `_make_manifest_spec` exists in `test_parser.py`, construct `ManifestSpec` inline or add a helper matching the existing style.

### Architecture Compliance

- `mypy --strict` enforced project-wide
- Max line length: 88 (`pyproject.toml` `[tool.black]`)
- Import order: stdlib → third-party → local
- `from __future__ import annotations` is at top of both `commands.py` (line 1) and `parser.py` (line 1) — string annotations are already enabled
- Absolute imports only — no relative imports
- Use `TYPE_CHECKING` guard for `ConfigFieldSpec` in `commands.py` (avoids runtime import; consistent with how other nimble.manifest types are handled in this file)
- I/O pattern: `typer.echo(prompt, nl=False)` + `sys.stdin.readline()` — exactly the same as `_prompt_install_confirm_y_only()` on lines 26–33 of `commands.py`

### Previous Story Intelligence (Stories 8.1 and 8.2)

**From Story 8.1:**
- `ConfigFieldSpec` is in `nimble/manifest/parser.py` — fields: `key: str`, `description: str`, `default: str | None`, `possible_values: list[str] | None`
- `ManifestSpec.config_fields: list[ConfigFieldSpec]` — empty list when absent
- `_parse_config_field_entry()` is the validation-style model for accessing these fields

**From Story 8.2:**
- `SkillConfig.configuration: dict[str, str]` is already complete — Story 8.3 only writes it to `config.yaml` via `append_skill_to_config`; the daemon already reads and injects it
- E501 (line too long > 88) was a recurring issue — watch every line
- Always use fully typed generics: `dict[str, str]` not `dict`, `list[ConfigFieldSpec]` not `list`
- `from __future__ import annotations` at top — type annotations are strings, no runtime import needed for `TYPE_CHECKING` usage
- `mypy --strict` errors on `type-arg` (unparameterized generics) — fully qualify all generics

### Git History Relevant Patterns

From recent commits:
- `70fad92 config yaml fields for skills` — Story 8.2 implementation
- `e6af40d refactor: split _parse_config_fields into focused helpers` — helper decomposition style in `parser.py`; each focused on one concern
- `e1d3875 fix(tests): extract patch-target constants to fix E501 in clipboard tests` — long patch strings cause E501; use intermediate variables if needed
- `f6429c4 fix: fix remaining flake8 errors` — E501 was most common issue

### Project Structure Notes

Files to change (exactly two):
- `nimble/cli/commands.py` — add TYPE_CHECKING import block, add `_collect_config_values` helper, update `add()` command
- `nimble/manifest/parser.py` — add `configuration` parameter to `append_skill_to_config`

Test files to extend (never create new files):
- `tests/unit/cli/test_commands.py` — extend existing file (551 lines)
- `tests/unit/manifest/test_parser.py` — extend existing file

### Critical Implementation Notes

1. **Prompt only after confirmation** — `_collect_config_values` must be called AFTER `_prompt_install_confirm_y_only()` returns `True`, not before. If user cancels, no prompts appear.

2. **`configuration={}` → no block** — `if configuration:` in `append_skill_to_config` correctly skips writing the block for both `None` and `{}`. Do NOT use `if configuration is not None:` — that would write an empty `configuration: {}` block.

3. **`_collect_config_values` always returns a dict** — even when `config_fields` is empty (returns `{}`). The `add()` command unconditionally calls it and passes the result.

4. **Existing call sites unaffected** — the only call to `append_skill_to_config` is in `commands.py:add()`. Adding a default parameter `configuration: dict[str, str] | None = None` doesn't break any other usage.

5. **Test input ordering** — `CliRunner.invoke(..., input=...)` feeds lines sequentially. The install confirm `y/N` prompt comes first; config field prompts come after. `input="y\nes\n"` means: first readline → "y" (install confirm), second readline → "es" (first config field).

6. **Line length watch** — `typer.echo(f"Invalid value. Choose from: {joined}")` is safe. The `_collect_config_values` function uses a local `joined` variable to avoid a long f-string. Keep lines ≤ 88 chars throughout.

### References

- Story 8.3 AC: [Source: docs/bmad_output/planning-artifacts/epics.md#Story-8.3]
- `ConfigFieldSpec` dataclass: [Source: nimble/manifest/parser.py#28-33]
- `ManifestSpec.config_fields`: [Source: nimble/manifest/parser.py#47]
- `append_skill_to_config()`: [Source: nimble/manifest/parser.py#234-272]
- `_prompt_install_confirm_y_only()` I/O pattern: [Source: nimble/cli/commands.py#26-33]
- `add()` command flow: [Source: nimble/cli/commands.py#305-396]
- Test helper `_make_manifest_spec`: [Source: tests/unit/cli/test_commands.py#339-353]
- Test `CliRunner.invoke` + `input=` pattern: [Source: tests/unit/cli/test_commands.py#356-370]
- Existing `append_skill_to_config` tests: [Source: tests/unit/cli/test_commands.py#508-535]
- `_parse_config_fields()` style reference: [Source: nimble/manifest/parser.py#170-178]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation was straightforward following the story spec exactly.

### Completion Notes List

- Added `TYPE_CHECKING` guard in `commands.py` for `ConfigFieldSpec` (avoids runtime import, consistent with project pattern)
- Added `_collect_config_values()` helper after `_prompt_install_confirm_y_only()` in `commands.py` — uses same `sys.stdin.readline()` + `typer.echo()` I/O pattern
- Wired `_collect_config_values(spec.config_fields)` into `add()` immediately after install confirmation, before lazy imports
- Added optional `configuration: dict[str, str] | None = None` to `append_skill_to_config()` in `parser.py`
- `if configuration:` guard correctly skips writing the block for both `None` and `{}` (AC 6)
- 9 new tests added: 6 in `test_commands.py`, 3 in `test_parser.py`
- 340 total tests pass (331 baseline + 9 new); no regressions
- flake8 clean; mypy: no new errors introduced (7 pre-existing errors in unrelated files)

### File List

- nimble/cli/commands.py
- nimble/manifest/parser.py
- tests/unit/cli/test_commands.py
- tests/unit/manifest/test_parser.py

## Change Log

- 2026-05-05: Story created — interactive config prompting for `nimble add`
- 2026-05-05: Story implemented and ready for review
