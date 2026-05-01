# Story 5.3: `nimble disable`

Status: done

## Story

As a user,
I want to disable a specific skill from the CLI without editing `config.yaml` manually,
So that I can quickly turn off a misbehaving skill without stopping the entire daemon.

## Acceptance Criteria

1. **Given** `nimble disable log-diagnosis` is run while the daemon is running
   **When** the CLI writes `disabled: true` to the skill entry in `config.yaml` via atomic write
   **Then** the file watcher detects the change, the daemon shuts down the `log-diagnosis` worker, and `state.json` reflects `status: disabled` for that skill (FR40)

2. **Given** `nimble disable <skill>` is run for a skill name that does not exist in `config.yaml`
   **When** the CLI looks up the skill
   **Then** it exits non-zero with `"No skill named '<skill>' found in config.yaml"` — `config.yaml` is not modified

3. **Given** `nimble disable <skill>` is run and the config write fails
   **When** the atomic write detects an error
   **Then** `config.yaml` is left unchanged (NFR14) and the CLI prints a clear error message

## Tasks / Subtasks

- [x] Task 1: Update `_parse_skills` in `nimble/manifest/parser.py` to skip disabled skills (AC: 1)
  - [x] In `_parse_skills`, skip entries where `entry.get("disabled") is True` — they should not appear in the returned `list[SkillConfig]`

- [x] Task 2: Add `disable_skill_in_config` to `nimble/manifest/parser.py` (AC: 1, 2, 3)
  - [x] Read `config_path` with `yaml.safe_load` (wrap in try/except OSError/yaml.YAMLError → raise as `OSError`)
  - [x] Treat `None` result as `{}`; verify `skills` is a list
  - [x] Find skill entry by `entry.get("name") == skill_name`
  - [x] If not found: `raise ValueError(f"No skill named '{skill_name}' found in config.yaml")`
  - [x] Set `skill_entry["disabled"] = True`
  - [x] Serialize with `yaml.dump(raw, default_flow_style=False, allow_unicode=True)` and write via `atomic_write(config_path, content)` — `atomic_write` already handles rollback on failure (NFR14)

- [x] Task 3: Add `mark_disabled` to `nimble/skills/registry.py` (AC: 1)
  - [x] Add `mark_disabled(self, name: str) -> None` — sets `worker.status = "disabled"` if worker exists; no logging (this is intentional, not an error)

- [x] Task 4: Update `_reload_config` in `nimble/daemon.py` to propagate "disabled" status (AC: 1)
  - [x] After loading `new_config`, re-read the raw YAML to identify which skill names have `disabled: true`; store in `disabled_names: set[str]` (wrap in broad try/except → default to empty set)
  - [x] After the `for name in to_remove: _shutdown_worker(name)` loop, call `registry.mark_disabled(name)` for each name that is in `disabled_names` — this overrides the "failed" status set by `_shutdown_worker`
  - [x] Import `yaml` is already present in `parser.py`; in `daemon.py` add `import yaml` after existing stdlib imports
  - [x] The `import yaml` in `daemon.py` is new — add it to the stdlib/third-party imports section

- [x] Task 5: Add `disable` command to `nimble/cli/commands.py` (AC: 1, 2, 3)
  - [x] Add `@app.command()` decorated function `disable(skill_name: str = typer.Argument(...)) -> None`
  - [x] Import `disable_skill_in_config` from `nimble.manifest.parser` inside the function body (matching the pattern of `validate` which imports `load_config` inside the function)
  - [x] On `ValueError`: `typer.echo(str(exc), err=True)` then `raise typer.Exit(1)`
  - [x] On `OSError`: `typer.echo(f"Failed to update config.yaml: {exc}", err=True)` then `raise typer.Exit(1)`
  - [x] On success: `typer.echo(f"Skill '{skill_name}' disabled")`

- [x] Task 6: Add unit tests for `disable` command in `tests/unit/cli/test_commands.py` (AC: 1, 2, 3)
  - [x] `test_disable_success()` — patch `nimble.cli.commands.disable_skill_in_config` (imported inside function, patch the parser module directly: `nimble.manifest.parser.disable_skill_in_config`) to succeed; assert exit 0, "disabled" in output
  - [x] `test_disable_skill_not_found()` — patch to raise `ValueError("No skill named 'x' found in config.yaml")`; assert exit 1, error message in output
  - [x] `test_disable_write_fails()` — patch to raise `OSError("disk full")`; assert exit 1, "Failed to update" in output

- [x] Task 7: Add unit tests for `disable_skill_in_config` in `tests/unit/manifest/test_parser.py` (AC: 1, 2, 3)
  - [x] `test_disable_skill_sets_disabled_flag(tmp_path)` — write a config with one skill; call `disable_skill_in_config`; reload with `yaml.safe_load`; assert skill has `disabled: True`
  - [x] `test_disable_skill_not_found_raises(tmp_path)` — config has skill "foo", call with "bar"; assert `ValueError` raised, config file unchanged
  - [x] `test_disable_skill_preserves_other_fields(tmp_path)` — assert name/binding/path still intact after disable
  - [x] `test_parse_skills_skips_disabled_entries(tmp_path)` — config with one active and one `disabled: true` skill; `load_config` returns only the active skill

- [x] Task 8: Verify quality gates
  - [x] `.venv/bin/pytest tests/unit/ -q` — all tests pass (baseline 233 + ~7 new = ~240)
  - [x] `.venv/bin/mypy nimble/ tests/ worker/` — exits 0 (pre-existing 3 errors in `test_platform.py` unchanged; 0 new errors in `nimble/`)
  - [x] `.venv/bin/black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

### Review Findings

- [x] [Review][Decision] Disabled status persistence across daemon restart — Resolved as runtime-only for Story 5.3 (accepted by user), so no patch required in this story scope.
- [x] [Review][Patch] Disabled status regresses to failed on heartbeat [nimble/skills/runner.py:364]
- [x] [Review][Patch] Re-enable via config reload does not respawn previously disabled worker [nimble/daemon.py:161]
- [x] [Review][Patch] AC2 test does not assert exact error text [tests/unit/cli/test_commands.py:316]
- [x] [Review][Patch] Missing daemon reload test coverage for disable lifecycle [tests/unit/daemon]
- [x] [Review][Defer] Duplicate skill names make disable behavior ambiguous [nimble/manifest/parser.py:50] — deferred, pre-existing

## Dev Notes

### What Already EXISTS — Do NOT Reinvent

**`nimble/manifest/parser.py`** — already has `atomic_write(path: Path, content: str) -> None` (write-to-tmp + rename pattern). Use it directly. Do NOT re-implement atomic write logic. The file already imports `yaml`, `os`, `tempfile`, `Path`.

**`nimble/cli/commands.py`** — already has `_repo_root() -> Path` (repo root helper), `app = typer.Typer(...)`, and existing `validate` command pattern for importing from `nimble.manifest.parser` inside the function body. Use `_repo_root() / "config.yaml"` as the config path.

**`nimble/skills/registry.py`** — already has `SkillRegistry` with `register`, `get`, `all`, `disable` methods. `disable(name)` sets status="failed" (for unexpected worker death) and logs an error — do NOT change it. Add `mark_disabled` as a separate method.

**`nimble/daemon.py`** — already has `_shutdown_worker(name)` which terminates the process and calls `registry.disable(name)` (status="failed"). The `_reload_config` function already handles add/remove/unchanged diffing. `yaml` is NOT currently imported in daemon.py — add `import yaml` in the third-party imports block (after `from watchdog...` imports).

**`nimble/state.py`** — `read_state()`, `write_state()`, `is_running()` — no changes needed in this story.

**`tests/unit/cli/test_commands.py`** — uses `typer.testing.CliRunner` and `runner = CliRunner()` at module level. Always patch on the module that imports the symbol, not where it's defined. The `disable` command imports `disable_skill_in_config` inside the function body — patch at `nimble.manifest.parser.disable_skill_in_config`.

---

### `disable_skill_in_config` Implementation

Add to `nimble/manifest/parser.py` (after `atomic_write`):

```python
def disable_skill_in_config(config_path: Path, skill_name: str) -> None:
    try:
        with config_path.open() as f:
            raw = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as exc:
        raise OSError(f"Failed to read config.yaml: {exc}") from exc

    if raw is None:
        raw = {}

    skills = raw.get("skills", [])
    if not isinstance(skills, list):
        raise OSError("config.yaml 'skills' is not a list")

    for entry in skills:
        if isinstance(entry, dict) and entry.get("name") == skill_name:
            entry["disabled"] = True
            content = yaml.dump(raw, default_flow_style=False, allow_unicode=True)
            atomic_write(config_path, content)
            return

    raise ValueError(f"No skill named '{skill_name}' found in config.yaml")
```

**Why `yaml.dump` is safe here:** `config.yaml` is machine-read; reformatting is acceptable. `default_flow_style=False` preserves block style for readability. `atomic_write` handles rollback on write failure automatically (NFR14).

**mypy note:** `raw` is typed as `dict[str, Any]` implicitly. No annotation needed since it's a local variable inferred from `yaml.safe_load` which returns `Any`.

---

### `_parse_skills` Change

In `_parse_skills`, add a skip guard after the `isinstance(entry, dict)` check:

```python
for i, entry in enumerate(raw):
    if not isinstance(entry, dict):
        raise ConfigError(f"Skill entry at index {i} must be a mapping")

    if entry.get("disabled"):          # <-- ADD THIS GUARD
        continue                        # skip disabled skills silently

    missing = required_fields - entry.keys()
    ...
```

**Position:** The `disabled` check must come BEFORE the `required_fields` check — disabled entries in config may be missing required fields (e.g., partially configured skill that was disabled). Skipping early avoids a false `ConfigError`.

---

### `mark_disabled` Implementation

Add to `SkillRegistry` in `nimble/skills/registry.py`:

```python
def mark_disabled(self, name: str) -> None:
    worker = self._workers.get(name)
    if worker is not None:
        worker.status = "disabled"
```

No logging needed — intentional config-driven disable is not an error.

---

### `_reload_config` Daemon Change

In `nimble/daemon.py`, modify `_reload_config` to detect and propagate "disabled" status:

```python
def _reload_config(cfg_path: Path) -> None:
    try:
        new_config = load_config(cfg_path)
        new_validated = validate_skill_paths(new_config.skills, repo_root)
    except ConfigError as exc:
        logger.error("Config reload error (keeping current state): %s", exc)
        return

    # Detect skills explicitly disabled via config (they're absent from new_validated)
    try:
        with cfg_path.open() as f:
            raw_yaml = yaml.safe_load(f) or {}
        disabled_names: set[str] = {
            str(s["name"])
            for s in raw_yaml.get("skills", [])
            if isinstance(s, dict) and s.get("disabled") and s.get("name")
        }
    except Exception:
        disabled_names = set()

    current: dict[str, SkillConfig] = {
        w.config.name: w.config for w in registry.all() if w.status != "failed"
    }
    incoming: dict[str, SkillConfig] = {s.name: s for s in new_validated}

    to_remove = [
        name
        for name, cfg in current.items()
        if name not in incoming or incoming[name] != cfg
    ]
    to_add = [
        cfg
        for cfg in new_validated
        if cfg.name not in current or current[cfg.name] != cfg
    ]
    unchanged = [
        cfg
        for cfg in new_validated
        if cfg.name in current and current[cfg.name] == cfg
    ]

    for name in to_remove:
        _shutdown_worker(name)
        if name in disabled_names:
            registry.mark_disabled(name)   # override "failed" → "disabled"

    runner.spawn_workers(to_add)

    for skill in to_add:
        adapter.register(
            skill.binding, _make_callback(skill.name, runner, notifier)
        )

    logger.info(
        "Config reloaded: +%d added, -%d removed, =%d unchanged",
        len(to_add),
        len(to_remove),
        len(unchanged),
    )
    skills = _build_skill_states(registry)
    write_state(pid, started_at, __version__, skills)
```

**Why read raw YAML again:** `load_config` via `_parse_skills` silently skips disabled skills — they don't appear in `new_validated`. The only way to know a skill was intentionally disabled (vs deleted from config) is to read the raw YAML directly.

**Why `import yaml` at top of daemon.py:** `yaml` is a third-party dependency already used via `nimble.manifest.parser`; it's safe to import directly in daemon.py. Add it to the third-party block after `from watchdog...` imports.

---

### `disable` CLI Command Implementation

```python
@app.command()
def disable(
    skill_name: str = typer.Argument(..., help="Name of the skill to disable"),
) -> None:
    """Disable a skill without editing config.yaml manually."""
    from nimble.manifest.parser import disable_skill_in_config

    config_path = _repo_root() / "config.yaml"
    try:
        disable_skill_in_config(config_path, skill_name)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    except OSError as exc:
        typer.echo(f"Failed to update config.yaml: {exc}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Skill '{skill_name}' disabled")
```

**Pattern note:** Matches `validate` command — import from `nimble.manifest.parser` inside the function body, use `_repo_root()` for config path.

---

### Test Implementations

#### CLI Tests (`tests/unit/cli/test_commands.py`)

```python
def test_disable_success() -> None:
    with patch(
        "nimble.manifest.parser.disable_skill_in_config"
    ):
        result = runner.invoke(app, ["disable", "hello-world"])
    assert result.exit_code == 0
    assert "disabled" in result.output


def test_disable_skill_not_found() -> None:
    with patch(
        "nimble.manifest.parser.disable_skill_in_config",
        side_effect=ValueError("No skill named 'hello-world' found in config.yaml"),
    ):
        result = runner.invoke(app, ["disable", "hello-world"])
    assert result.exit_code == 1
    assert "No skill named" in result.output


def test_disable_write_fails() -> None:
    with patch(
        "nimble.manifest.parser.disable_skill_in_config",
        side_effect=OSError("disk full"),
    ):
        result = runner.invoke(app, ["disable", "hello-world"])
    assert result.exit_code == 1
    assert "Failed to update" in result.output
```

**Patch target:** `nimble.manifest.parser.disable_skill_in_config` — this is where the function is defined. Even though `commands.py` imports it inside the function body via `from nimble.manifest.parser import disable_skill_in_config`, patching the source module works because the `import` happens at call time and Python resolves the name from the module dict.

#### Parser Tests (`tests/unit/manifest/test_parser.py`)

```python
def test_disable_skill_sets_disabled_flag(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "skills:\n"
        "  - name: hello-world\n"
        "    source: local\n"
        "    path: skills/hello_world/skill.py\n"
        "    class_name: HelloWorldSkill\n"
        "    binding: ctrl+shift+h\n"
    )
    disable_skill_in_config(cfg, "hello-world")
    import yaml
    data = yaml.safe_load(cfg.read_text())
    assert data["skills"][0].get("disabled") is True


def test_disable_skill_not_found_raises(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("skills:\n  - name: foo\n    source: local\n    path: p\n    class_name: C\n    binding: b\n")
    original = cfg.read_text()
    with pytest.raises(ValueError, match="No skill named 'bar'"):
        disable_skill_in_config(cfg, "bar")
    assert cfg.read_text() == original  # config unchanged


def test_disable_skill_preserves_other_fields(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "skills:\n"
        "  - name: hello-world\n"
        "    source: local\n"
        "    path: skills/hello_world/skill.py\n"
        "    class_name: HelloWorldSkill\n"
        "    binding: ctrl+shift+h\n"
    )
    disable_skill_in_config(cfg, "hello-world")
    import yaml
    skill = yaml.safe_load(cfg.read_text())["skills"][0]
    assert skill["name"] == "hello-world"
    assert skill["binding"] == "ctrl+shift+h"
    assert skill["path"] == "skills/hello_world/skill.py"


def test_parse_skills_skips_disabled_entries(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "skills:\n"
        "  - name: active-skill\n"
        "    source: local\n"
        "    path: skills/active/skill.py\n"
        "    class_name: ActiveSkill\n"
        "    binding: ctrl+shift+a\n"
        "  - name: disabled-skill\n"
        "    source: local\n"
        "    path: skills/disabled/skill.py\n"
        "    class_name: DisabledSkill\n"
        "    binding: ctrl+shift+d\n"
        "    disabled: true\n"
    )
    result = load_config(cfg)
    assert len(result.skills) == 1
    assert result.skills[0].name == "active-skill"
```

**Import note:** Add `from nimble.manifest.parser import disable_skill_in_config` to the imports at the top of `test_parser.py`.

---

### mypy Compliance

**`disable_skill_in_config` signature:**
```python
def disable_skill_in_config(config_path: Path, skill_name: str) -> None: ...
```
No new type annotations required beyond what already exists in the file.

**`mark_disabled` signature:**
```python
def mark_disabled(self, name: str) -> None: ...
```

**`disable` command:**
```python
def disable(skill_name: str = typer.Argument(...)) -> None: ...
```
Return type `-> None` required for Typer commands.

**`daemon.py` import:** `import yaml` is a third-party import — place it after `from watchdog...` imports (already at lines 9–16) and before `from nimble...` imports.

---

### Architecture Compliance

- CLI writes `disabled: true` to `config.yaml` — no IPC, no daemon API call (architecture: Boundary 3, Daemon ↔ Config via file watcher)
- Atomic write used for all `config.yaml` mutations (NFR14)
- File watcher (`watchdog`) already detects changes in `nimble/watcher.py` and calls `_reload_config` — no watcher changes needed
- `_parse_skills` skips disabled skills → they appear in `to_remove` in `_reload_config` → worker is shut down
- `registry.mark_disabled` overrides "failed" → "disabled" after `_shutdown_worker` so `state.json` reflects the intentional disable
- Do NOT read `state.json` in the CLI `disable` command — config.yaml is the source of truth for disable

### Out of Scope for This Story

- `nimble enable` (re-enabling a skill)
- Modifying `nimble/watcher.py`
- Integration testing of the full file-watcher loop (unit tests only)
- Any changes to `nimble/state.py`

### File List to Touch

- `nimble/manifest/parser.py` — update `_parse_skills` to skip disabled, add `disable_skill_in_config`
- `nimble/skills/registry.py` — add `mark_disabled` method
- `nimble/daemon.py` — add `import yaml`, update `_reload_config` to detect disabled skills
- `nimble/cli/commands.py` — add `disable` command
- `tests/unit/cli/test_commands.py` — add 3 new tests
- `tests/unit/manifest/test_parser.py` — add 4 new tests, update imports

### Baseline (Before This Story)

```
Tests: 233 passed (0 collection errors)
mypy: 3 pre-existing errors in tests/unit/platform/test_platform.py — unchanged; 0 errors in nimble/
black: clean
flake8: clean (nimble/ tests/ worker/ only)
```

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 5.3] — acceptance criteria, FR40
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Configuration] — `disabled: true` flag, atomic write pattern
- [Source: docs/bmad_output/planning-artifacts/architecture.md#IPC Model] — `nimble disable` flow via file watcher
- [Source: nimble/manifest/parser.py] — existing `atomic_write`, `_parse_skills`, `load_config` patterns
- [Source: nimble/skills/registry.py] — `SkillRegistry`, `SkillWorker`, `disable()` method
- [Source: nimble/daemon.py] — `_reload_config`, `_shutdown_worker`, `_build_skill_states`
- [Source: nimble/cli/commands.py] — `validate` command pattern (inline import, `_repo_root()` usage)
- [Source: tests/unit/cli/test_commands.py] — `CliRunner` pattern, patch namespace
- [Source: tests/unit/manifest/test_parser.py] — existing parser test patterns with `tmp_path`
- [Source: docs/bmad_output/implementation-artifacts/5-2-nimble-list-and-nimble-status.md] — previous story patterns

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Added `disable` guard in `_parse_skills` before required-fields check so disabled entries (which may lack required fields) are silently skipped
- Implemented `disable_skill_in_config` in parser.py using existing `atomic_write` for safe config mutation; raises `ValueError` for unknown skill, `OSError` for read/write failures
- Added `mark_disabled` to `SkillRegistry` as a separate method from `disable` — intentional config-driven disable sets status="disabled", not "failed"
- Updated `_reload_config` in daemon.py to re-read raw YAML and call `registry.mark_disabled` after `_shutdown_worker` for skills with `disabled: true`; added `import yaml` to daemon.py imports
- Added `disable` CLI command following the `validate` command pattern (inline import, `_repo_root()` for config path)
- 7 new unit tests added (3 CLI, 4 parser); all 240 tests pass; mypy 0 new errors in nimble/; black and flake8 clean

### File List

- nimble/manifest/parser.py
- nimble/skills/registry.py
- nimble/daemon.py
- nimble/cli/commands.py
- tests/unit/cli/test_commands.py
- tests/unit/manifest/test_parser.py

## Change Log

- 2026-05-01: Story created — ready for dev
- 2026-05-01: Implementation complete — all 8 tasks done, 240 tests pass, status set to review
