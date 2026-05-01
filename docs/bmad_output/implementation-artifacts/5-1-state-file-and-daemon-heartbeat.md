# Story 5.1: State File and Daemon Heartbeat

Status: review

## Story

As a CLI user,
I want the daemon to maintain an up-to-date `state.json` file reflecting the current runtime state,
so that `nimble list` and `nimble status` can read it without any IPC round-trip to the daemon process.

## Acceptance Criteria

1. **Given** the daemon starts successfully
   **When** all skills finish loading
   **Then** `~/.nimble/state.json` is written with `pid`, `started_at`, `daemon_version`, and a `skills` array containing each skill's `name`, `source`, `binding`, `status`, and `worker_pid`

2. **Given** the daemon is running
   **When** 5 seconds elapse with no state-change events
   **Then** the state file is rewritten (heartbeat) — keeping `started_at` the same and updating only `worker_pid` values if changed

3. **Given** a skill's status changes (loaded → disabled, worker dies, etc.)
   **When** the state change occurs
   **Then** `state.json` is updated immediately — not deferred to the next heartbeat

4. **Given** the daemon stops cleanly
   **When** the shutdown completes
   **Then** `state.json` is removed and `nimble.pid` is deleted

## Tasks / Subtasks

- [x] Task 1: Extend `nimble/state.py` with state file functions (AC: 1, 2, 4)
  - [x] Add `STATE_FILE: Path = NIMBLE_DIR / "state.json"` constant
  - [x] Add `SkillState` dataclass with fields: `name: str`, `source: str`, `binding: str`, `status: str`, `worker_pid: int | None`
  - [x] Add `write_state(pid, started_at, daemon_version, skills)` — atomic write (tmp + rename), creates `NIMBLE_DIR` if absent
  - [x] Add `remove_state()` — deletes `STATE_FILE`, no-op if absent (same pattern as `remove_pid`)

- [x] Task 2: Add `_build_skill_states` helper in `daemon.py` (AC: 1, 2, 3)
  - [x] Add module-level helper `_build_skill_states(registry) -> list[SkillState]` — iterates `registry.all()`, maps each `SkillWorker` to `SkillState`; `worker_pid` is `worker.process.pid` if `worker.process.poll() is None` else `None`

- [x] Task 3: Write initial state after daemon startup (AC: 1)
  - [x] In `daemon.py::run()`, immediately after the `write_pid(os.getpid())` line, capture `started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()`
  - [x] Call `write_state(os.getpid(), started_at, __version__, _build_skill_states(registry))`
  - [x] Import `datetime` (stdlib) and `from nimble import __version__` and `from nimble.state import ..., STATE_FILE, write_state, remove_state, SkillState`

- [x] Task 4: Add heartbeat thread that also detects dead workers (AC: 2, 3)
  - [x] In `daemon.py::run()`, after initial state write, start a daemon thread that loops: `while not stop_event.wait(5.0): runner.check_for_dead_workers(); write_state(pid, started_at, __version__, _build_skill_states(registry))`
  - [x] Thread must be `daemon=True` so it dies when the main thread exits without needing explicit join
  - [x] `runner.check_for_dead_workers()` already exists in `SkillRunner` — it calls `_disable_dead_worker()` for each dead process. This satisfies AC3 for spontaneous worker deaths (dead worker detected → status updated in registry → next heartbeat or immediate write reflects it)

- [x] Task 5: Write state after config reload (AC: 3)
  - [x] In `daemon.py::_reload_config()`, after `logger.info("Config reloaded: ...")`, call `write_state(pid, started_at, __version__, _build_skill_states(registry))`
  - [x] `pid` and `started_at` are closure variables — they're already accessible inside `_reload_config` since it's a nested function in `run()`

- [x] Task 6: Remove state on clean shutdown (AC: 4)
  - [x] In `daemon.py::run()` `finally` block, after `remove_pid()`, add `remove_state()`
  - [x] Only call if `started` is `True` (same gate as `remove_pid`) — avoids removing a state file that was never created (e.g., startup error path)

- [x] Task 7: Write tests for `write_state` and `remove_state` (AC: 1, 4)
  - [x] `tests/unit/test_state.py` — add:
    - [x] `test_write_state_creates_valid_json()` — call `write_state(...)` with tmp state/pid paths patched, assert JSON file created with correct keys: `pid`, `started_at`, `daemon_version`, `skills`
    - [x] `test_write_state_skill_entry_fields()` — write one `SkillState`, assert skills array contains entry with `name`, `source`, `binding`, `status`, `worker_pid`
    - [x] `test_write_state_worker_pid_none_for_dead_worker()` — pass `SkillState(worker_pid=None)`, assert `worker_pid` is `null` in JSON
    - [x] `test_write_state_is_atomic()` — assert no partial file left if tmp rename fails (mock `Path.rename` to raise, assert `STATE_FILE` does not exist)
    - [x] `test_remove_state_deletes_file()` — write then remove, assert file absent
    - [x] `test_remove_state_noop_if_absent()` — call without file, assert no exception

- [x] Task 8: Write tests for daemon state integration (AC: 1, 2, 4)
  - [x] `tests/unit/test_daemon.py` — add:
    - [x] `test_run_writes_state_on_startup()` — patch `write_state`, run daemon through startup (mock everything including stop_event to exit immediately after startup), assert `write_state` called once with correct pid and daemon_version
    - [x] `test_run_removes_state_on_shutdown()` — patch `remove_state`, run daemon and let it stop, assert `remove_state` called once

- [x] Task 9: Verify quality gates
  - [x] `.venv/bin/pytest tests/unit/ -q` — all tests pass (baseline 211 + ~8 new = ~219)
  - [x] `.venv/bin/mypy nimble/ tests/ worker/` — exits 0 (3 pre-existing errors in test_platform.py unchanged; 0 new errors in nimble/)
  - [x] `.venv/bin/black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

## Dev Notes

### What Already EXISTS — Do NOT Reinvent

**`nimble/state.py`** — already has `NIMBLE_DIR`, `PID_FILE`, `write_pid()`, `read_pid()`, `remove_pid()`, `is_running()`. ADD to this file; do NOT create a new file. Follow the exact style: `from __future__ import annotations`, no logger (keep state.py lean), `NIMBLE_DIR.mkdir(parents=True, exist_ok=True)` before any write.

**`nimble/skills/runner.py::SkillRunner.check_for_dead_workers()`** — already exists (scans `registry.all()`, calls `_disable_dead_worker()` for each dead process). Use it in the heartbeat — do NOT reimplement dead worker detection.

**`nimble/skills/registry.py::SkillWorker`** — the `process` field is `subprocess.Popen[bytes]`; `worker.process.pid` gives the worker PID; `worker.process.poll()` returns `None` if alive. The `status` field is `SkillStatus = Literal["loaded", "disabled", "failed"]`.

**`nimble/__init__.py`** — `__version__ = "1.0.0"`. Import as `from nimble import __version__` in daemon.py. Already used in runner.py as `from nimble import SUPPORTED_API_VERSION` — use the same pattern.

**`nimble/state.py::remove_pid()`** — the existing pattern for `remove_state()`:
```python
def remove_state() -> None:
    try:
        STATE_FILE.unlink()
    except FileNotFoundError:
        pass
```

**Baseline test count: 211 tests pass.**

---

### `state.json` Schema (from architecture.md — treat as a hard contract)

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

**Rules:**
- All keys use `snake_case` — no camelCase (architecture.md explicitly requires snake_case for JSON state file keys)
- `started_at` is ISO 8601 UTC — use `datetime.datetime.now(datetime.timezone.utc).isoformat()`
- `worker_pid` is `int | null` — use `None` for dead/failed workers; JSON serialises this as `null`
- `skills` is always an array — empty array if no skills loaded
- `status` values: `"loaded"`, `"disabled"`, `"failed"` — these are the existing `SkillStatus` literals

---

### Atomic Write Implementation

State file must be written atomically to prevent partial reads by CLI (NFR14 principle):

```python
import json
import os
import tempfile

def write_state(
    pid: int,
    started_at: str,
    daemon_version: str,
    skills: list[SkillState],
) -> None:
    NIMBLE_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "pid": pid,
        "started_at": started_at,
        "daemon_version": daemon_version,
        "skills": [
            {
                "name": s.name,
                "source": s.source,
                "binding": s.binding,
                "status": s.status,
                "worker_pid": s.worker_pid,
            }
            for s in skills
        ],
    }
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data))
    tmp.rename(STATE_FILE)
```

**Why `.with_suffix(".json.tmp")` instead of `tempfile.mkstemp`**: the rename must be on the same filesystem as the destination for atomicity. Writing tmp to the same directory (`.nimble/`) guarantees this. `tempfile.mkstemp` may write to `/tmp` on some systems which may be a different filesystem.

---

### `SkillState` Dataclass

Add to `state.py` (not `registry.py`). It's a view/DTO for serialisation — separate from `SkillWorker` which belongs to the runtime layer:

```python
from dataclasses import dataclass

@dataclass
class SkillState:
    name: str
    source: str
    binding: str
    status: str
    worker_pid: int | None
```

`mypy --strict` note: `worker_pid: int | None` is correct — use `int | None` not `Optional[int]` (the codebase uses the `X | Y` union syntax consistently, see `registry.py`).

---

### Daemon Integration Pattern

**Imports to add in `daemon.py`:**
```python
import datetime
from nimble import __version__
from nimble.state import remove_pid, remove_state, SkillState, write_state, write_pid
```

**`_build_skill_states` module-level helper:**
```python
def _build_skill_states(registry: SkillRegistry) -> list[SkillState]:
    return [
        SkillState(
            name=w.config.name,
            source=w.config.source,
            binding=w.config.binding,
            status=w.status,
            worker_pid=w.process.pid if w.process.poll() is None else None,
        )
        for w in registry.all()
    ]
```

**After `write_pid(os.getpid())` in `run()`:**
```python
write_pid(os.getpid())
started = True
started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
write_state(os.getpid(), started_at, __version__, _build_skill_states(registry))
```

**Heartbeat thread (start immediately after initial state write):**
```python
def _heartbeat() -> None:
    while not stop_event.wait(5.0):
        runner.check_for_dead_workers()
        write_state(os.getpid(), started_at, __version__, _build_skill_states(registry))

heartbeat_thread = threading.Thread(target=_heartbeat, daemon=True)
heartbeat_thread.start()
```

`started_at` and `registry` are captured from the closure — `_heartbeat` is a nested function inside `run()`.

**After `logger.info("Config reloaded: ...")` in `_reload_config()`:**
```python
write_state(os.getpid(), started_at, __version__, _build_skill_states(registry))
```

`started_at` is already a closure variable from `run()` — `_reload_config` is a nested function and can access it directly.

**In `finally` block after `remove_pid()`:**
```python
if started:
    runner.shutdown()
    adapter.stop()
    remove_pid()
    remove_state()
    logger.info("Nimble daemon stopped")
```

---

### Test Patterns for `write_state` and `remove_state`

Follow the exact pattern of existing tests in `test_state.py` — patch `NIMBLE_DIR` and `STATE_FILE`:

```python
import json
import nimble.state as state_module
from nimble.state import SkillState, write_state, remove_state

def test_write_state_creates_valid_json(tmp_path: Path) -> None:
    skills = [
        SkillState(
            name="hello-world",
            source="local",
            binding="ctrl+shift+h",
            status="loaded",
            worker_pid=9999,
        )
    ]
    with (
        patch.object(state_module, "NIMBLE_DIR", tmp_path),
        patch.object(state_module, "STATE_FILE", tmp_path / "state.json"),
    ):
        write_state(12345, "2026-05-01T10:00:00+00:00", "1.0.0", skills)
        data = json.loads((tmp_path / "state.json").read_text())

    assert data["pid"] == 12345
    assert data["started_at"] == "2026-05-01T10:00:00+00:00"
    assert data["daemon_version"] == "1.0.0"
    assert len(data["skills"]) == 1
    assert data["skills"][0]["name"] == "hello-world"
    assert data["skills"][0]["worker_pid"] == 9999

def test_write_state_worker_pid_none_for_dead_worker(tmp_path: Path) -> None:
    skills = [
        SkillState(name="s", source="local", binding="ctrl+a", status="failed", worker_pid=None)
    ]
    with (
        patch.object(state_module, "NIMBLE_DIR", tmp_path),
        patch.object(state_module, "STATE_FILE", tmp_path / "state.json"),
    ):
        write_state(1, "2026-05-01T00:00:00+00:00", "1.0.0", skills)
        data = json.loads((tmp_path / "state.json").read_text())

    assert data["skills"][0]["worker_pid"] is None
```

**Atomic write test — mock `Path.rename` to raise:**
```python
def test_write_state_is_atomic(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    with (
        patch.object(state_module, "NIMBLE_DIR", tmp_path),
        patch.object(state_module, "STATE_FILE", state_file),
        patch("pathlib.Path.rename", side_effect=OSError("disk full")),
        pytest.raises(OSError),
    ):
        write_state(1, "2026-05-01T00:00:00+00:00", "1.0.0", [])
    assert not state_file.exists()
```

---

### Test Patterns for Daemon Integration

Follow the existing style in `tests/unit/test_daemon.py`. The daemon `run()` function uses `stop_event.wait()` to block — set the mock event to immediately return True to simulate immediate stop:

```python
def test_run_writes_state_on_startup(tmp_path: Path) -> None:
    with (
        patch("nimble.daemon.load_config", return_value=MagicMock(skills=[], ai=None)),
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.get_adapter"),
        patch("nimble.daemon.Notifier"),
        patch("nimble.daemon.configure_logging"),
        patch("nimble.daemon.SkillRunner"),
        patch("nimble.daemon.write_pid"),
        patch("nimble.daemon.ConfigWatcher"),
        patch("nimble.daemon.write_state") as mock_write_state,
        patch("nimble.daemon.remove_state"),
        patch("nimble.daemon.remove_pid"),
        patch("nimble.daemon.threading.Event") as mock_event_cls,
    ):
        mock_event_cls.return_value.wait.side_effect = KeyboardInterrupt
        with pytest.raises((KeyboardInterrupt, SystemExit)):
            from nimble.daemon import run
            run(tmp_path)
    assert mock_write_state.called

def test_run_removes_state_on_shutdown(tmp_path: Path) -> None:
    with (
        patch("nimble.daemon.load_config", return_value=MagicMock(skills=[], ai=None)),
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.get_adapter"),
        patch("nimble.daemon.Notifier"),
        patch("nimble.daemon.configure_logging"),
        patch("nimble.daemon.SkillRunner"),
        patch("nimble.daemon.write_pid"),
        patch("nimble.daemon.ConfigWatcher"),
        patch("nimble.daemon.write_state"),
        patch("nimble.daemon.remove_state") as mock_remove_state,
        patch("nimble.daemon.remove_pid"),
        patch("nimble.daemon.threading.Event") as mock_event_cls,
    ):
        mock_event_cls.return_value.wait.side_effect = KeyboardInterrupt
        with pytest.raises((KeyboardInterrupt, SystemExit)):
            from nimble.daemon import run
            run(tmp_path)
    assert mock_remove_state.called
```

**Note:** `from nimble.daemon import run` inside `with` patch blocks ensures patched names are active. If `run` is already imported at the top of the test file (it's used via `daemon_module._dispatch` indirectly), you may need to use `daemon_module.run(tmp_path)` instead. Check the existing import style in `test_daemon.py`.

---

### mypy Compliance

**`_build_skill_states` return type must be annotated:**
```python
def _build_skill_states(registry: SkillRegistry) -> list[SkillState]: ...
```

**`_heartbeat` nested function has no return value — annotate:**
```python
def _heartbeat() -> None: ...
```

**`started_at: str`** — `datetime.datetime.now(...).isoformat()` returns `str`. No `Final` needed.

**`write_state` signature:**
```python
def write_state(
    pid: int,
    started_at: str,
    daemon_version: str,
    skills: list[SkillState],
) -> None: ...
```

**`SkillState.worker_pid: int | None`** — use `int | None`, not `Optional[int]`, consistent with the rest of the codebase (see `registry.py` line `worker_pid: int | None = None` in architecture reference patterns).

---

### Architecture Compliance Checklist

- State file is CLI-readable without IPC (architecture Boundary 2: Daemon ↔ CLI via `state.json`)
- State file path: `~/.nimble/state.json` = `NIMBLE_DIR / "state.json"` — do NOT hardcode the path
- Atomic write (tmp + rename) — no partial reads possible
- `nimble/cli/commands.py` reads state for `list`/`status` commands — that's Story 5.2; do NOT implement CLI commands in this story
- Do NOT add platform-specific logic to `state.py` — it's cross-platform (the path `Path.home() / ".nimble"` already handles this)
- `state.py` stays lean — no logger, no imports beyond stdlib + pathlib

### Out of Scope for This Story

- `nimble list` and `nimble status` CLI commands — those are Story 5.2
- `nimble disable` CLI command — Story 5.3
- Any changes to `nimble/cli/commands.py`
- Writing state to a location other than `~/.nimble/state.json`
- Reading state.json anywhere (only writing)

### File List to Touch

- `nimble/state.py` — add `STATE_FILE`, `SkillState` dataclass, `write_state()`, `remove_state()`
- `nimble/daemon.py` — add imports (`datetime`, `__version__`, new state imports), `_build_skill_states()` helper, initial state write, heartbeat thread, reload state write, `remove_state()` in finally
- `tests/unit/test_state.py` — add 6 new tests for `write_state`/`remove_state`
- `tests/unit/test_daemon.py` — add 2 new tests for state write on startup and removal on shutdown

### Baseline (Before This Story)

```
Tests: 211 passed (0 collection errors)
mypy: 3 pre-existing errors in tests/unit/platform/test_platform.py — unchanged; 0 errors in nimble/
black: clean
flake8: clean (nimble/ tests/ worker/ only)
```

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 5.1] — acceptance criteria, FR38, FR39, FR40
- [Source: docs/bmad_output/planning-artifacts/architecture.md#IPC Model] — state.json schema, 5s heartbeat, Boundary 2 (Daemon ↔ CLI)
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Naming Patterns] — snake_case for JSON keys
- [Source: nimble/state.py] — existing NIMBLE_DIR, PID_FILE, write_pid, remove_pid patterns to follow
- [Source: nimble/daemon.py] — integration points: after write_pid, in _reload_config, in finally
- [Source: nimble/skills/registry.py] — SkillWorker fields: process.pid, status
- [Source: nimble/skills/runner.py::check_for_dead_workers()] — use in heartbeat, do not reimplement
- [Source: nimble/__init__.py] — `__version__ = "1.0.0"`, `SUPPORTED_API_VERSION`
- [Source: tests/unit/test_state.py] — existing test patterns with patched NIMBLE_DIR/PID_FILE to follow
- [Source: tests/unit/test_daemon.py] — existing daemon test patterns with mocked threading.Event

## Dev Agent Record

### Implementation Notes

Added `STATE_FILE`, `SkillState` dataclass, `write_state()` (atomic via tmp+rename), and `remove_state()` to `nimble/state.py` following the existing pid-file patterns exactly.

Added `_build_skill_states()` module-level helper and integrated state writes into daemon startup, heartbeat (5s daemon thread), config reload, and clean shutdown.

**Key discovery:** `patch("threading.Event", ...)` patches `threading.Event` globally and breaks `threading.Thread.__init__`, which uses `Event()` internally for its `_started` flag. Fixed by adding `patch("nimble.daemon.threading.Thread")` to all daemon tests that mock `threading.Event`, preventing the heartbeat thread from being created in test context.

### Completion Notes

- All 9 tasks implemented and verified
- 219 tests pass (211 baseline + 8 new)
- 0 new mypy errors in `nimble/`; pre-existing errors in test files unchanged
- black and flake8 clean

## File List

- `nimble/state.py` — added `STATE_FILE`, `SkillState`, `write_state()`, `remove_state()`
- `nimble/daemon.py` — added imports, `_build_skill_states()`, initial state write, heartbeat thread, reload state write, `remove_state()` in finally; updated 3 existing tests to patch `threading.Thread`
- `tests/unit/test_state.py` — added 6 new tests for `write_state`/`remove_state`
- `tests/unit/test_daemon.py` — added 2 new tests for state write on startup and removal on shutdown; fixed 3 existing tests broken by `threading.Thread` / `threading.Event` interaction

## Change Log

- 2026-05-01: Implemented state file and daemon heartbeat (Story 5.1) — added `STATE_FILE`, `SkillState`, `write_state`, `remove_state` to `nimble/state.py`; integrated heartbeat thread, initial write, config reload write, and shutdown cleanup in `nimble/daemon.py`; 8 new tests added
