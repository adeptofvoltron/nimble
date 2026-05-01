# Story 5.2: `nimble list` and `nimble status`

Status: done

## Story

As a user,
I want to see all loaded skills and daemon health at a glance from the CLI,
so that I can quickly confirm what's running, what's bound to which shortcut, and whether anything has failed.

## Acceptance Criteria

1. **Given** the daemon is running and `nimble list` is run
   **When** `state.json` is read
   **Then** output shows each skill's name, source (`local`/`community`), binding, and status (`loaded`/`disabled`/`failed`) — one skill per line (FR38)

2. **Given** the daemon is not running and `nimble list` is run
   **When** no `state.json` or stale PID is found
   **Then** the command prints `"Nimble daemon is not running"` and exits 0 — no crash

3. **Given** `nimble status` is run while the daemon is running
   **When** `state.json` is read
   **Then** output shows daemon `pid`, `started_at`, `daemon_version`, and a per-skill breakdown of load state (FR39)

4. **Given** `nimble status` is run and a skill has `status: failed`
   **When** the output is displayed
   **Then** the failed skill is visually distinguished (marked `[FAILED]`) so it's immediately obvious

## Tasks / Subtasks

- [x] Task 1: Add `read_state()` to `nimble/state.py` (AC: 1, 2, 3, 4)
  - [x] Add `from typing import Any` import
  - [x] Add `read_state() -> dict[str, Any] | None` — reads and parses `STATE_FILE`; returns `None` on `FileNotFoundError` or `json.JSONDecodeError`

- [x] Task 2: Add `list_skills` command to `nimble/cli/commands.py` (AC: 1, 2)
  - [x] Register as `@app.command(name="list")` (function name `list_skills` to avoid shadowing builtin)
  - [x] Call `state.read_state()` — if `None`, print `"Nimble daemon is not running"` and return (exit 0)
  - [x] Check `state.is_running(data["pid"])` — if dead, print `"Nimble daemon is not running"` and return (exit 0)
  - [x] For each skill in `data["skills"]`, print: `name  source  binding  status` — one per line
  - [x] If `data["skills"]` is empty, print `"No skills loaded"`

- [x] Task 3: Add `status` command to `nimble/cli/commands.py` (AC: 3, 4)
  - [x] Register as `@app.command()` (function name `status`)
  - [x] Call `state.read_state()` — if `None` or PID dead, print `"Nimble daemon is not running"` and return (exit 0)
  - [x] Print daemon line: `f"Daemon: pid={data['pid']}  started={data['started_at']}  version={data['daemon_version']}"`
  - [x] Print blank line then `"Skills:"`
  - [x] For each skill: print `  name  source  binding  status` — failed skills show `[FAILED]` instead of `failed`

- [x] Task 4: Add unit tests for `list` and `status` commands (AC: 1, 2, 3, 4)
  - [x] `test_list_shows_skills_when_running()` — patch `read_state` with one loaded skill, patch `is_running` True; assert skill name/binding/status in output
  - [x] `test_list_no_state_file()` — patch `read_state` returning `None`; assert "not running" in output, exit 0
  - [x] `test_list_stale_state_file()` — patch `read_state` with pid data, patch `is_running` False; assert "not running" in output, exit 0
  - [x] `test_list_no_skills()` — patch `read_state` with empty `skills` list; assert "No skills loaded" in output
  - [x] `test_status_shows_daemon_and_skills()` — patch `read_state` with daemon fields + skills, patch `is_running` True; assert pid/started_at/daemon_version and skill name in output
  - [x] `test_status_failed_skill_marked()` — patch `read_state` with a `status: failed` skill; assert `[FAILED]` in output
  - [x] `test_status_not_running()` — patch `read_state` returning `None`; assert "not running" in output, exit 0

- [x] Task 5: Verify quality gates
  - [x] `.venv/bin/pytest tests/unit/ -q` — all tests pass (baseline 219 + ~7 new = ~226)
  - [x] `.venv/bin/mypy nimble/ tests/ worker/` — exits 0 (pre-existing 3 errors in `test_platform.py` unchanged; 0 new errors in `nimble/`)
  - [x] `.venv/bin/black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

### Review Findings

- [x] [Review][Patch] Unvalidated PID conversion can crash `nimble list/status` on malformed state [nimble/cli/commands.py:195]
- [x] [Review][Patch] `status` header assumes required keys always exist and can raise `KeyError` [nimble/cli/commands.py:221]
- [x] [Review][Patch] Skill row formatting uses strict dict indexing and can crash on malformed skill entries [nimble/cli/commands.py:204]
- [x] [Review][Patch] `read_state()` does not handle non-JSON read failures (`OSError`/encoding errors) [nimble/state.py:87]

## Dev Notes

### What Already EXISTS — Do NOT Reinvent

**`nimble/state.py`** — already has `NIMBLE_DIR`, `PID_FILE`, `STATE_FILE`, `SkillState` dataclass, `write_state()`, `remove_state()`, `read_pid()`, `is_running()`. ADD `read_state()` to this file only — do NOT create a new file. File begins with `from __future__ import annotations`; add `from typing import Any` after the stdlib imports.

**`nimble/cli/commands.py`** — already has `start`, `stop`, `restart`, `validate` commands wired to `app = typer.Typer(...)`. Add `list_skills` and `status` as new `@app.command()` decorated functions. The module already imports `import nimble.state as state` — use `state.read_state()` and `state.is_running()` directly.

**`state.json` schema (hard contract — do not deviate):**
```json
{
  "pid": 12345,
  "started_at": "2026-04-16T10:00:00+00:00",
  "daemon_version": "1.0.0",
  "skills": [
    {
      "name": "log-diagnosis",
      "source": "local",
      "binding": "ctrl+shift+d",
      "status": "loaded",
      "worker_pid": 12346
    }
  ]
}
```
Status values: `"loaded"`, `"disabled"`, `"failed"` — these are the existing `SkillStatus` literals.

**`tests/unit/cli/test_commands.py`** — existing CLI tests use `typer.testing.CliRunner`. Patch `nimble.cli.commands.state.read_pid`, `nimble.cli.commands.state.is_running` etc. — always patch on the `nimble.cli.commands.state` module, not the `nimble.state` module. File imports at top: `from typer.testing import CliRunner` and `runner = CliRunner()`.

---

### `read_state()` Implementation

Add to `nimble/state.py` (after the `is_running` function):

```python
from typing import Any

def read_state() -> dict[str, Any] | None:
    try:
        raw: dict[str, Any] = json.loads(STATE_FILE.read_text())
        return raw
    except (FileNotFoundError, json.JSONDecodeError):
        return None
```

**Why explicit annotation `raw: dict[str, Any]`:** `json.loads` returns `Any`; annotating the local variable asserts the type so mypy `--strict` does not flag a `no-any-return` warning on the function.

---

### `list_skills` Command Implementation

```python
@app.command(name="list")
def list_skills() -> None:
    """List all configured skills and their status."""
    data = state.read_state()
    if data is None:
        typer.echo("Nimble daemon is not running")
        return
    pid = data.get("pid")
    if pid is None or not state.is_running(int(pid)):
        typer.echo("Nimble daemon is not running")
        return
    skills = data.get("skills", [])
    if not skills:
        typer.echo("No skills loaded")
        return
    for skill in skills:
        typer.echo(
            f"{skill['name']:<20} {skill['source']:<12} {skill['binding']:<20} {skill['status']}"
        )
```

**`name="list"`** — required because `list` is a Python builtin and cannot be used as a function name.

---

### `status` Command Implementation

```python
@app.command()
def status() -> None:
    """Show daemon health and per-skill status."""
    data = state.read_state()
    if data is None:
        typer.echo("Nimble daemon is not running")
        return
    pid = data.get("pid")
    if pid is None or not state.is_running(int(pid)):
        typer.echo("Nimble daemon is not running")
        return
    typer.echo(
        f"Daemon: pid={data['pid']}  started={data['started_at']}  version={data['daemon_version']}"
    )
    typer.echo("")
    typer.echo("Skills:")
    for skill in data.get("skills", []):
        status_display = "[FAILED]" if skill["status"] == "failed" else skill["status"]
        typer.echo(
            f"  {skill['name']:<20} {skill['source']:<12} {skill['binding']:<20} {status_display}"
        )
```

---

### Test Implementation

Follow the exact pattern of existing CLI tests. The key pattern: patch on `nimble.cli.commands.state`, not `nimble.state`.

```python
_SAMPLE_STATE = {
    "pid": 12345,
    "started_at": "2026-05-01T10:00:00+00:00",
    "daemon_version": "1.0.0",
    "skills": [
        {
            "name": "hello-world",
            "source": "local",
            "binding": "ctrl+shift+h",
            "status": "loaded",
            "worker_pid": 12346,
        }
    ],
}

def test_list_shows_skills_when_running() -> None:
    with (
        patch("nimble.cli.commands.state.read_state", return_value=_SAMPLE_STATE),
        patch("nimble.cli.commands.state.is_running", return_value=True),
    ):
        result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "hello-world" in result.output
    assert "ctrl+shift+h" in result.output
    assert "loaded" in result.output

def test_list_no_state_file() -> None:
    with patch("nimble.cli.commands.state.read_state", return_value=None):
        result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "not running" in result.output

def test_list_stale_state_file() -> None:
    with (
        patch("nimble.cli.commands.state.read_state", return_value=_SAMPLE_STATE),
        patch("nimble.cli.commands.state.is_running", return_value=False),
    ):
        result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "not running" in result.output

def test_list_no_skills() -> None:
    data = {**_SAMPLE_STATE, "skills": []}
    with (
        patch("nimble.cli.commands.state.read_state", return_value=data),
        patch("nimble.cli.commands.state.is_running", return_value=True),
    ):
        result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "No skills loaded" in result.output

def test_status_shows_daemon_and_skills() -> None:
    with (
        patch("nimble.cli.commands.state.read_state", return_value=_SAMPLE_STATE),
        patch("nimble.cli.commands.state.is_running", return_value=True),
    ):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "12345" in result.output
    assert "1.0.0" in result.output
    assert "hello-world" in result.output

def test_status_failed_skill_marked() -> None:
    data = {
        **_SAMPLE_STATE,
        "skills": [
            {**_SAMPLE_STATE["skills"][0], "status": "failed"}
        ],
    }
    with (
        patch("nimble.cli.commands.state.read_state", return_value=data),
        patch("nimble.cli.commands.state.is_running", return_value=True),
    ):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "[FAILED]" in result.output

def test_status_not_running() -> None:
    with patch("nimble.cli.commands.state.read_state", return_value=None):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "not running" in result.output
```

---

### mypy Compliance

**`read_state` signature:**
```python
def read_state() -> dict[str, Any] | None: ...
```
Requires `from typing import Any` added to `state.py`.

**`list_skills` and `status` return type:** `-> None` — Typer commands are always `-> None`.

**`data.get("pid")` returns `Any`** — `int(pid)` cast is needed before passing to `state.is_running(pid: int)`. Mypy will flag passing `Any` to `int` as a no-op but won't error; however `int(pid)` is explicit and safe.

**Avoid `int | None` ambiguity:** `pid = data.get("pid")` returns `Any`; check `if pid is None` then cast — `state.is_running(int(pid))` is correct.

---

### Architecture Compliance

- CLI reads `state.json` directly — no IPC round-trip (architecture: Boundary 2, Daemon ↔ CLI via `state.json`)
- The daemon removes `state.json` on clean shutdown — so missing file = daemon not running
- Stale state detection: if `state.json` exists but `is_running(pid)` is False, daemon crashed without cleanup
- `nimble list` exits 0 even when daemon is not running (AC2 explicitly: "exits 0 — no crash")
- `nimble status` also exits 0 when daemon is not running (same pattern for consistency)
- Do NOT read `config.yaml` for these commands — `state.json` is the only source
- Do NOT implement `nimble disable` here — that is Story 5.3

### Out of Scope for This Story

- `nimble disable` — Story 5.3
- Modifying `state.json` format
- Any changes to `nimble/daemon.py`
- Any changes to `nimble/state.py` beyond adding `read_state()` and `from typing import Any`

### File List to Touch

- `nimble/state.py` — add `from typing import Any` and `read_state()` function
- `nimble/cli/commands.py` — add `list_skills` and `status` commands
- `tests/unit/cli/test_commands.py` — add 7 new tests for list and status

### Baseline (Before This Story)

```
Tests: 219 passed (0 collection errors)
mypy: 3 pre-existing errors in tests/unit/platform/test_platform.py — unchanged; 0 errors in nimble/
black: clean
flake8: clean (nimble/ tests/ worker/ only)
```

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 5.2] — acceptance criteria, FR38, FR39
- [Source: docs/bmad_output/planning-artifacts/architecture.md#IPC Model] — state.json schema, CLI reads state directly
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Naming Patterns] — snake_case, `X | Y` unions
- [Source: nimble/state.py] — existing `STATE_FILE`, `is_running()`, `read_pid()` patterns to follow; `write_state()` for state.json schema reference
- [Source: nimble/cli/commands.py] — existing `import nimble.state as state`, Typer `app`, command pattern
- [Source: tests/unit/cli/test_commands.py] — `CliRunner` pattern, patch namespace `nimble.cli.commands.state.*`
- [Source: docs/bmad_output/implementation-artifacts/5-1-state-file-and-daemon-heartbeat.md] — state.json schema, SkillState, write_state implementation

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

Fixed flake8 E501 violations in the f-string output lines by splitting them with implicit string concatenation. Fixed mypy indexing error in test_status_failed_skill_marked by building the failed skill dict explicitly instead of indexing into _SAMPLE_STATE.

### Completion Notes List

- Added `read_state() -> dict[str, Any] | None` to `nimble/state.py` using the established `json.loads` + exception-catch pattern.
- Added `list_skills` command (`@app.command(name="list")`) to `nimble/cli/commands.py` — prints one skill per line with fixed-width columns; "No skills loaded" for empty list; exits 0 when daemon not running.
- Added `status` command to `nimble/cli/commands.py` — prints daemon header (pid/started/version) then per-skill rows; replaces `failed` with `[FAILED]` for visual distinction; exits 0 when daemon not running.
- Added 7 unit tests to `tests/unit/cli/test_commands.py` covering all 4 ACs: loaded skill display, no state file, stale state, no skills, daemon+skill display, failed skill marking, not-running for status.
- All 228 unit tests pass (7 new); 0 new mypy errors in `nimble/`; black clean; flake8 clean.

### File List

- `nimble/state.py`
- `nimble/cli/commands.py`
- `tests/unit/cli/test_commands.py`

## Change Log

- 2026-05-01: Implemented `read_state()`, `nimble list`, and `nimble status` commands with 7 unit tests (228 total passing, all quality gates clean)
