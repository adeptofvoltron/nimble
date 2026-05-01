# Story 4.5: YAML Config Validation and `nimble validate`

Status: done

## Story

As a user editing `config.yaml`,
I want the daemon to catch config errors at load time with line-precise messages, and to be able to run a pre-flight check without starting the daemon,
so that I fix config problems in seconds rather than discovering them from a silent daemon failure.

## Acceptance Criteria

1. **Given** `config.yaml` has a YAML syntax error (e.g. tab character on line 12)
   **When** the daemon or `nimble validate` parses it
   **Then** a `ConfigError` is raised with message `"config.yaml line 12: <description>"` — never a raw PyYAML exception (FR29)

2. **Given** `nimble validate` is run on a valid `config.yaml`
   **When** parsing and validation complete
   **Then** the command exits 0 and prints `"config.yaml is valid"` — no daemon is started (FR30)

3. **Given** `nimble validate` is run on an invalid `config.yaml`
   **When** a validation error is found
   **Then** the command exits non-zero and prints the line-precise error — same format as daemon startup errors

4. **Given** a config write fails mid-way (e.g. disk full)
   **When** the atomic write (write-to-tmp + rename) is used
   **Then** the original `config.yaml` is preserved intact — no partial or corrupted state (NFR14)

## Tasks / Subtasks

- [x] Task 1: Add `nimble validate` command to `nimble/cli/commands.py` (AC: 2, 3)
  - [x] Add `@app.command()` function `validate()` with no arguments
  - [x] Get `config_path = _repo_root() / "config.yaml"`
  - [x] Call `load_config(config_path)` inside a try/except block
  - [x] On `ConfigError`: `typer.echo(str(exc), err=True)` then `raise typer.Exit(1)`
  - [x] On `FileNotFoundError`: `typer.echo(f"config.yaml not found at {config_path}", err=True)` then `raise typer.Exit(1)`
  - [x] On success: `typer.echo("config.yaml is valid")` and return normally (exits 0)

- [x] Task 2: Add `atomic_write()` to `nimble/manifest/parser.py` (AC: 4)
  - [x] Add function `atomic_write(path: Path, content: str) -> None`
  - [x] Write `content` to `path.parent / (path.name + ".tmp")` with `encoding="utf-8"`
  - [x] Call `tmp_path.replace(path)` — `replace()` is cross-platform atomic on POSIX; on Windows it overwrites atomically
  - [x] In `except` block: call `tmp_path.unlink(missing_ok=True)` then `raise`
  - [x] Export `atomic_write` — it will be called by `nimble disable` (Story 5.3) and `nimble add` (Story 6.5)

- [x] Task 3: Write tests for `validate` command (AC: 2, 3)
  - [x] `tests/unit/cli/test_commands.py` — add tests:
    - [x] `test_validate_valid_config()` — patch `load_config` to return a `NimbleConfig`; assert exit 0 and "config.yaml is valid" in output
    - [x] `test_validate_invalid_config()` — patch `load_config` to raise `ConfigError("config.yaml line 3: ...")`; assert exit 1 and error message in output
    - [x] `test_validate_missing_config()` — patch `load_config` to raise `FileNotFoundError`; assert exit 1 and "not found" in output

- [x] Task 4: Write tests for `atomic_write()` (AC: 4)
  - [x] `tests/unit/manifest/test_parser.py` — add tests:
    - [x] `test_atomic_write_creates_file_with_correct_content()` — call `atomic_write(tmp_path / "config.yaml", "content")`; assert file exists with correct content
    - [x] `test_atomic_write_no_tmp_file_left_on_success()` — after successful write, assert no `.tmp` file remains
    - [x] `test_atomic_write_preserves_original_on_failure()` — write original content; mock `Path.replace` to raise `OSError`; call `atomic_write`; assert original content unchanged and no `.tmp` file left
    - [x] `test_atomic_write_uses_same_directory_for_tmp()` — assert tmp file is in same directory as target (so rename is same-filesystem atomic)

- [x] Task 5: Verify quality gates
  - [x] `.venv/bin/pytest tests/unit/ --ignore=tests/unit/test_daemon.py --ignore=tests/unit/test_watcher.py` — all pass (183 baseline + new tests)
  - [x] `.venv/bin/mypy nimble/ tests/ worker/` — exits 0 (3 pre-existing errors in test_platform.py unchanged)
  - [x] `.venv/bin/black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

## Dev Notes

### What Exists Today — Do NOT Reinvent

**`nimble/manifest/parser.py::load_config()`** — ALREADY handles FR29. It catches `yaml.YAMLError` and raises `ConfigError(f"config.yaml line {line}: {problem}")`. The line-precise error format is implemented and tested. Do NOT modify this function.

**`nimble/manifest/parser.py::ConfigError`** — the exception class already exists. Import it in `commands.py`.

**`nimble/cli/commands.py::_repo_root()`** — returns `Path(__file__).resolve().parent.parent.parent`. Use this to locate `config.yaml`.

**Existing CLI commands** — `start`, `stop`, `restart`, `_run` (hidden). The `validate` command is the only thing missing from the CLI for this story. Do NOT modify existing commands.

**Existing test patterns in `tests/unit/cli/test_commands.py`**:
```python
from typer.testing import CliRunner
from nimble.cli.commands import app

runner = CliRunner()

def test_some_command() -> None:
    with patch("nimble.cli.commands.state.read_pid", return_value=None):
        result = runner.invoke(app, ["command-name"])
    assert result.exit_code == 0
    assert "expected text" in result.output
```

### `validate` Command Implementation

```python
@app.command()
def validate() -> None:
    """Validate config.yaml without starting the daemon."""
    from nimble.manifest.parser import ConfigError, load_config

    config_path = _repo_root() / "config.yaml"
    try:
        load_config(config_path)
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    except FileNotFoundError:
        typer.echo(f"config.yaml not found at {config_path}", err=True)
        raise typer.Exit(1)
    typer.echo("config.yaml is valid")
```

Import `ConfigError` and `load_config` inside the function body (consistent with how `daemon` is imported in `_run`) — this avoids eager imports at module load time.

### `atomic_write()` Implementation

```python
def atomic_write(path: Path, content: str) -> None:
    tmp = path.parent / (path.name + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
```

**Why `replace()` not `rename()`:** `Path.replace()` maps to `os.replace()` which overwrites the destination atomically on POSIX and on Windows (Python 3.3+). `Path.rename()` on Windows raises `FileExistsError` if the target exists. Since `config.yaml` always exists when `atomic_write` is called, `replace()` is required for cross-platform correctness.

**Why same directory for tmp:** The `rename`/`replace` operation is only atomic when source and destination are on the same filesystem. Using `path.parent / (path.name + ".tmp")` guarantees this. Do NOT write the tmp file to `/tmp` or any other location.

### Test Patterns for `validate`

Patch `load_config` at `nimble.cli.commands.load_config` — the import is inside the function body, so you must patch the name at the call site after the `from` import resolves:

```python
from nimble.manifest.parser import ConfigError

def test_validate_valid_config(tmp_path: Path) -> None:
    from nimble.manifest.parser import NimbleConfig
    with patch("nimble.cli.commands.load_config", return_value=NimbleConfig(skills=[])):
        result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "config.yaml is valid" in result.output

def test_validate_invalid_config() -> None:
    with patch(
        "nimble.cli.commands.load_config",
        side_effect=ConfigError("config.yaml line 3: found character '\\t'"),
    ):
        result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1
    assert "line 3" in result.output
```

**Note:** Since `load_config` is imported inside the function body via `from nimble.manifest.parser import ConfigError, load_config`, the patch target must be `nimble.cli.commands.load_config` — not `nimble.manifest.parser.load_config`. However, because the import is inside the function, the name won't exist in `nimble.cli.commands` before the function runs. Use `patch` as a context manager around `runner.invoke` to ensure it's active when the function imports.

Actually — because the import is inside the function body each call, you need to patch it at the module level:

```python
with patch("nimble.manifest.parser.load_config", side_effect=ConfigError(...)):
    result = runner.invoke(app, ["validate"])
```

Patch `nimble.manifest.parser.load_config` directly since the `from ... import` inside the function body resolves at call time.

### Test Pattern for `atomic_write`

```python
def test_atomic_write_preserves_original_on_failure(tmp_path: Path) -> None:
    target = tmp_path / "config.yaml"
    target.write_text("original", encoding="utf-8")

    with patch.object(Path, "replace", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            atomic_write(target, "new content")

    assert target.read_text(encoding="utf-8") == "original"
    assert not (tmp_path / "config.yaml.tmp").exists()
```

### Architecture Compliance

- `atomic_write` lives in `nimble/manifest/parser.py` — this module owns all config file I/O. Stories 5.3 (`nimble disable`) and 6.5 (`nimble add`) will import and call it.
- `validate` command must NOT call `start()` or touch the daemon in any way — it is a pure read operation
- `mypy --strict` enforced — `atomic_write(path: Path, content: str) -> None` must have full annotations
- Absolute imports only: `from nimble.manifest.parser import ConfigError, load_config, atomic_write`

### What load_config Already Validates

The existing `load_config()` checks:
- YAML parse errors (YAMLError → ConfigError with line number) ✅
- `skills` must be a list ✅
- Each skill entry must be a dict with `name`, `source`, `path`, `class_name`, `binding` fields ✅
- `source` must be `"local"` or `"community"` ✅
- `ai` block (if present) must have `provider`, `model`, `api_key_env` fields ✅

The `validate` command gets all of this for free — just call `load_config` and handle the exceptions.

### Out of Scope for This Story

- Skill file existence check (is `path` actually a file?) — deferred to the daemon loader or a future enhancement
- `nimble disable` command — Story 5.3 (it will use `atomic_write` from this story)
- `nimble add` command — Story 6.5 (it will use `atomic_write` from this story)
- Schema validation beyond what `load_config` already checks (field types, binding format) — not in AC

### File List to Touch

- `nimble/cli/commands.py` — add `validate()` command
- `nimble/manifest/parser.py` — add `atomic_write()` function
- `tests/unit/cli/test_commands.py` — add 3 tests for `validate`
- `tests/unit/manifest/test_parser.py` — add 4 tests for `atomic_write`

### Baseline (Before This Story)

```
Tests: 183 passed (2 collection errors in test_daemon.py and test_watcher.py — pre-existing)
mypy: 3 pre-existing errors in tests/unit/platform/test_platform.py — unchanged; 0 errors in nimble/
black: clean
flake8: clean (nimble/ tests/ worker/ only)
```

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 4.5] — acceptance criteria, FR29, FR30, NFR14
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Configuration] — atomic write pattern requirement
- [Source: nimble/manifest/parser.py] — existing `load_config()` and `ConfigError` to reuse
- [Source: nimble/cli/commands.py] — existing CLI command structure, `_repo_root()` helper, typer patterns
- [Source: tests/unit/cli/test_commands.py] — CliRunner test patterns to follow
- [Source: docs/bmad_output/implementation-artifacts/4-4-api-version-compatibility-check.md] — test mock patterns for unit tests

### Review Findings

- [x] [Review][Patch] `atomic_write` uses a shared temp filename and can race under concurrent writers [`nimble/manifest/parser.py:32`] — fixed with unique temp files via `tempfile.mkstemp`
- [x] [Review][Patch] `validate` does not handle unreadable config (`PermissionError`/`OSError`) with clean CLI error output [`nimble/cli/commands.py:171`] — fixed with explicit `OSError` handling and test coverage
- [x] [Review][Defer] `load_config` assumes mapping root and can raise `AttributeError` on scalar/list YAML roots [`nimble/manifest/parser.py:86`] — deferred, pre-existing

## Dev Agent Record

### Implementation Notes

- Added `validate()` command to `nimble/cli/commands.py` — imports `ConfigError` and `load_config` inside the function body (lazy import, consistent with `_run`'s `from nimble.daemon import run` pattern). Handles `ConfigError` (exit 1, line-precise message to stderr), `FileNotFoundError` (exit 1, "not found" message), and success (exit 0, "config.yaml is valid").
- Added `atomic_write(path, content)` to `nimble/manifest/parser.py` — writes to a `.tmp` sibling first, then `Path.replace()` (cross-platform atomic overwrite). On any exception, the tmp file is cleaned up and the original is preserved.
- Patch target for `validate` tests: `nimble.manifest.parser.load_config` (import is inside function body — resolves at call time from the source module, not a cached name in `commands`).

### Completion Notes

- 190 tests pass (7 new: 3 for `validate`, 4 for `atomic_write`)
- mypy: 3 pre-existing errors in `test_platform.py` — unchanged; 0 new errors
- black: clean; flake8: clean
- All 4 ACs satisfied

## File List

- `nimble/cli/commands.py` — added `validate()` command
- `nimble/manifest/parser.py` — added `atomic_write()` function
- `tests/unit/cli/test_commands.py` — added 3 tests for `validate`; added `ConfigError`, `NimbleConfig` imports
- `tests/unit/manifest/test_parser.py` — added 4 tests for `atomic_write`; added `patch` import, `atomic_write` import

## Change Log

- 2026-05-01: Implemented `nimble validate` CLI command and `atomic_write()` utility — Story 4.5
