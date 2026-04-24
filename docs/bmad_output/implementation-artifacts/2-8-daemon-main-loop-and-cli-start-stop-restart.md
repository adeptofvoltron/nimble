# Story 2.8: Daemon Main Loop and CLI start/stop/restart

Status: done

## Story

As a user,
I want to start, stop, and restart the Nimble daemon with simple CLI commands,
So that I can control the daemon lifecycle without touching process management tools directly.

## Acceptance Criteria

1. **Given** `nimble start` is run and no daemon is already running
   **When** the daemon starts successfully
   **Then** a PID file is written to `~/.nimble/nimble.pid` and the daemon enters its main loop listening for hotkeys

2. **Given** `nimble start` is run and a stale PID file exists (process is dead)
   **When** the daemon checks the PID file
   **Then** it cleans up the stale PID file and starts normally — no "daemon already running" false positive

3. **Given** `nimble stop` is run
   **When** the daemon PID is found in `~/.nimble/nimble.pid`
   **Then** `SIGTERM` (Linux/macOS) or `TerminateProcess` (Windows) is sent, workers are gracefully shut down, and the PID file is deleted

4. **Given** `nimble restart` is run while the daemon is running
   **When** the restart completes
   **Then** it is equivalent to `nimble stop && nimble start` — a fresh daemon with reloaded config

5. **Given** `nimble start` runs a cold start
   **When** all skills are loaded and hotkeys registered
   **Then** cold start completes in under 5 seconds on a standard developer machine (NFR2)

6. **Given** `nimble/watcher.py` starts a `watchdog` file watcher on `config.yaml` as part of the daemon main loop
   **When** `config.yaml` is modified by any process (CLI or editor)
   **Then** the daemon detects the change, validates the new config, diffs against loaded state, and gracefully shuts down / spawns workers as needed — without requiring `nimble restart`

## Tasks / Subtasks

- [x] Task 1: Add `watchdog` to dependencies (AC: 6)
  - [x] Run `pip index versions watchdog` and pick latest stable 3.x version
  - [x] Add `"watchdog>=3.0"` to `[project] dependencies` in `pyproject.toml`
  - [x] Run `pip install -e ".[dev]"` to install

- [x] Task 2: Create `nimble/notifier.py` — cross-platform notifications (AC: 3, 6)
  - [x] Define `class Notifier` with `send(self, title: str, body: str) -> None`
  - [x] Use `plyer.notification.notify(title=title, message=body, app_name="Nimble")` inside a `try/except Exception` so a notification failure never crashes the daemon
  - [x] Module-level `logger = logging.getLogger(__name__)`; log `WARNING` on notify failure
  - [x] `from __future__ import annotations`; absolute imports; full type annotations; `mypy --strict` passes
  - [x] Note: `FakeNotifier` in `tests/conftest.py` already exists — production tests use it; `test_notifier.py` tests plyer integration with `unittest.mock.patch`

- [x] Task 3: Create `nimble/state.py` — PID file management (AC: 1, 2, 3, 4)
  - [x] Define `NIMBLE_DIR: Path = Path.home() / ".nimble"` and `PID_FILE: Path = NIMBLE_DIR / "nimble.pid"`
  - [x] `write_pid(pid: int) -> None` — creates `~/.nimble/` if not exists; writes pid as text to `PID_FILE`
  - [x] `read_pid() -> int | None` — returns `int(PID_FILE.read_text().strip())` or `None` if file missing or non-integer
  - [x] `remove_pid() -> None` — deletes `PID_FILE` if exists; no-op if absent
  - [x] `is_running(pid: int) -> bool` — uses `os.kill(pid, 0)` on all platforms (Python 3.2+); returns `True` if no `ProcessLookupError`/`PermissionError` raised; returns `False` on `OSError`
  - [x] `from __future__ import annotations`; absolute imports; full type annotations; `mypy --strict` passes

- [x] Task 4: Create `nimble/watcher.py` — config file watcher (AC: 6)
  - [x] `class ConfigWatcher` with `__init__(self, config_path: Path, reload_fn: Callable[[Path], None]) -> None`
  - [x] Internally creates a `watchdog.observers.Observer` and a `FileSystemEventHandler` subclass
  - [x] The handler's `on_modified` checks `Path(event.src_path).resolve() == self._config_path.resolve()` before calling `reload_fn(self._config_path)` — avoids firing on unrelated files in the same directory
  - [x] `start(self) -> None` — schedules the handler on `config_path.parent` and starts the observer thread
  - [x] `stop(self) -> None` — stops and joins the observer thread
  - [x] `from __future__ import annotations`; absolute imports; full type annotations; `mypy --strict` passes

- [x] Task 5: Create `nimble/daemon.py` — main loop (AC: 1, 5, 6)
  - [x] `run(repo_root: Path, debug: bool = False) -> None` — the single public entry point
  - [x] **Logging setup (provisional — Story 4.2 replaces with `RotatingFileHandler`):** `logging.basicConfig(level=logging.DEBUG if debug else logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")`
  - [x] Write PID: `state.write_pid(os.getpid())`
  - [x] **Startup sequence:** `load_config(repo_root / "config.yaml")` → `validate_skill_paths(config.skills, repo_root)` → `SkillRunner(registry, notifier, repo_root).spawn_workers(validated)` — catch `ConfigError` and exit with `sys.exit(1)` after logging
  - [x] **Hotkey registration:** for each validated `SkillConfig`, call `adapter.register(skill.binding, _make_callback(skill.name))`. Use factory function to avoid Python late-binding closure bug.
  - [x] **`_dispatch(skill_name: str) -> None`:** calls `build_context()`, then `runner.dispatch(skill_name, context)`. On `status == "error"`, calls `notifier.send(...)`. Log at `ERROR` level.
  - [x] Start hotkey adapter: `adapter.start()`
  - [x] Start config watcher: `ConfigWatcher(repo_root / "config.yaml", _reload_config).start()`
  - [x] **Signal handling:** `stop_event = threading.Event()`; SIGTERM/SIGINT handlers call `stop_event.set()`; enter loop with `stop_event.wait()`
  - [x] **Graceful shutdown sequence (in order):** watcher.stop() → runner.shutdown() → adapter.stop() → state.remove_pid() → log "Nimble daemon stopped"
  - [x] **Config reload function `_reload_config(config_path: Path) -> None`:** diff current vs incoming, shut down removed skills, spawn new workers, re-register bindings, log summary
  - [x] `from __future__ import annotations`; absolute imports; full type annotations; `mypy --strict` passes

- [x] Task 6: Update `nimble/cli/commands.py` — replace placeholder with start/stop/restart (AC: 1–4)
  - [x] Remove the existing `placeholder` / `Placeholder` commands
  - [x] Add hidden `_run` command (used internally by `start`)
  - [x] **`start` command:** PID check → stale cleanup → Popen daemon → poll for PID → echo success
  - [x] **`stop` command:** read PID → send SIGTERM → poll is_running → echo stopped
  - [x] **`restart` command:** `_do_stop()` then `_do_start()` helpers called in sequence
  - [x] **Windows TerminateProcess helper:** `_terminate_windows(pid)` using ctypes
  - [x] `_repo_root()` helper: `Path(__file__).resolve().parent.parent.parent`
  - [x] All type annotations; `mypy --strict`; absolute imports

- [x] Task 7: Create `tests/unit/test_notifier.py` (AC: 3)
  - [x] `test_send_calls_plyer_notify()`: patch `plyer` module in sys.modules; assert notify called with correct args
  - [x] `test_send_swallows_plyer_exception()`: patch `plyer.notification.notify` raising `Exception`; no exception raised

- [x] Task 8: Create `tests/unit/test_state.py` (AC: 1, 2, 3)
  - [x] `test_write_and_read_pid(tmp_path)`: patch `NIMBLE_DIR` and `PID_FILE`; `write_pid(12345)`; assert `read_pid() == 12345`
  - [x] `test_read_pid_returns_none_if_no_file(tmp_path)`: assert `read_pid() is None`
  - [x] `test_remove_pid_deletes_file(tmp_path)`: write pid; `remove_pid()`; assert file absent
  - [x] `test_remove_pid_noop_if_absent(tmp_path)`: `remove_pid()` with no file; no exception
  - [x] `test_is_running_process_exists()`: patch `os.kill` no-op; assert `is_running(12345) is True`
  - [x] `test_is_running_process_dead()`: patch `os.kill` raising `ProcessLookupError`; assert `is_running(99999) is False`

- [x] Task 9: Create `tests/unit/test_watcher.py` (AC: 6)
  - [x] `test_reload_fn_called_on_config_modification(tmp_path)`: synthesize `FileModifiedEvent`; assert reload_fn called
  - [x] `test_reload_fn_not_called_for_other_files(tmp_path)`: fire event for different file; assert NOT called
  - [x] `test_start_stop_does_not_crash()`: start + stop; no exception

- [x] Task 10: Create `tests/unit/cli/test_commands.py` (AC: 1–4)
  - [x] `test_start_no_existing_daemon(tmp_path)`: patch state/Popen/polling; assert exit code 0
  - [x] `test_start_already_running(tmp_path)`: `read_pid` → 12345; `is_running` → True; assert exit code 1
  - [x] `test_start_stale_pid_cleaned_up(tmp_path)`: stale pid; assert `remove_pid` called; start proceeds
  - [x] `test_stop_running_daemon()`: `read_pid` → 12345; assert SIGTERM sent; exit code 0
  - [x] `test_stop_no_daemon()`: `read_pid` → None; assert exit code 1
  - [x] `test_restart_calls_stop_then_start()`: patch `_do_stop` and `_do_start`; assert both called in order

- [x] Task 11: Verify quality gates (AC: all)
  - [x] `mypy nimble/ tests/ worker/` — all new files pass strict (pre-existing `parser.py` unused-ignore noted in Dev Notes)
  - [x] `pytest` — all 91 tests pass (74 existing + 17 new)
  - [x] `black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

### Review Findings

- [x] [Review][Patch] Restart ignores stop failure and may spawn overlapping daemons [nimble/cli/commands.py:159]
- [x] [Review][Patch] PID file is written before successful startup and can remain stale on config error [nimble/daemon.py:560]
- [x] [Review][Patch] Windows stop path does not guarantee PID file removal after `TerminateProcess` [nimble/cli/commands.py:49]
- [x] [Review][Patch] Config watcher misses atomic-save patterns by handling only `on_modified` [nimble/watcher.py:775]
- [x] [Review][Patch] Reload removes workers abruptly instead of using graceful shutdown flow [nimble/daemon.py:626]
- [x] [Review][Patch] Start path infers success from PID file without verifying process liveness [nimble/cli/commands.py:81]

## Dev Notes

### Role in the Daemon Architecture

Story 2.8 wires together all prior stories into a running daemon:

```
nimble start (CLI)
  → spawns detached process: nimble _run <repo_root>
      → daemon.run(repo_root)
          → load_config()          [nimble/manifest/parser.py]   Story 2.7
          → validate_skill_paths() [nimble/skills/loader.py]     Story 2.7
          → runner.spawn_workers() [nimble/skills/runner.py]     Story 2.6
          → adapter.register(...)  [nimble/hotkeys/]             Stories 2.1–2.3
          → adapter.start()
          → ConfigWatcher.start()  [nimble/watcher.py]           THIS STORY
          → stop_event.wait()      [main loop, SIGTERM exits]
```

After this story, the daemon is functional end-to-end. Story 2.9 adds the startup notification and hello_world skill.

### New Files

```
nimble/notifier.py               ← new
nimble/state.py                  ← new
nimble/watcher.py                ← new
nimble/daemon.py                 ← new
tests/unit/test_notifier.py      ← new
tests/unit/test_state.py         ← new
tests/unit/test_watcher.py       ← new
tests/unit/cli/test_commands.py  ← new
```

Do NOT modify: `nimble/manifest/`, `nimble/skills/`, `nimble/hotkeys/`, `nimble/context/`, `worker/`, `tests/conftest.py`.

Modified: `nimble/cli/commands.py` (replace placeholder), `pyproject.toml` (add watchdog).

### Patterns Carried Forward from Story 2.7

- `from __future__ import annotations` at top of every new module
- Absolute imports only — `from nimble.state import write_pid`, never relative
- `@dataclass` for structured data — no plain dicts for internal data exchange
- Module-level `logger = logging.getLogger(__name__)` in every new module
- All functions fully type-annotated; `mypy --strict` must pass

### Critical: Hotkey Callback Threading

The pynput listener calls hotkey callbacks **synchronously in the listener thread**. If the callback blocks (waiting for skill dispatch), pynput cannot process the next hotkey. Always dispatch to a daemon thread:

```python
def _make_callback(skill_name: str) -> Callable[[], None]:
    def _callback() -> None:
        threading.Thread(target=_dispatch, args=(skill_name,), daemon=True).start()
    return _callback
```

Do NOT write `adapter.register(binding, lambda: _dispatch(name))` — Python closures capture the variable `name` by reference; by the time the lambda fires, `name` has the last loop value. Always use the factory pattern above.

### `nimble start` Daemon Spawn Pattern

`nimble start` must return immediately while the daemon runs in the background. Use:

```python
nimble_bin = Path(sys.executable).parent / ("nimble.exe" if sys.platform == "win32" else "nimble")
subprocess.Popen(
    [str(nimble_bin), "_run", str(repo_root)],
    start_new_session=True,   # detach from terminal session (Unix)
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    close_fds=(sys.platform != "win32"),
)
```

`close_fds=True` is required on Unix to prevent the daemon from inheriting file descriptors. It must be `False` on Windows (Python limitation).

After spawning, poll `state.read_pid()` in a loop with 0.1s sleeps, up to 5s total. The daemon writes its PID as its first action in `run()`.

### `nimble stop` Signal Pattern

**Linux/macOS:**
```python
import os, signal
os.kill(pid, signal.SIGTERM)
```

The daemon's `stop_event.wait()` loop exits via the SIGTERM handler, runs cleanup, removes the PID file, then exits. Poll `state.is_running(pid)` after sending SIGTERM; the process should exit within ~2s.

**Windows:**
```python
import ctypes
PROCESS_TERMINATE = 0x0001
handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
ctypes.windll.kernel32.TerminateProcess(handle, 0)
ctypes.windll.kernel32.CloseHandle(handle)
```

On Windows, `TerminateProcess` is immediate and abrupt — workers are killed without graceful shutdown. This is accepted for v1. Graceful Windows shutdown (via named pipe) is deferred.

### State File Scope for This Story

Story 2.8 creates `nimble/state.py` with **PID file management only**. The `state.json` file (daemon health + per-skill runtime state, required by `nimble list` and `nimble status`) is fully owned by Story 5.1. Do NOT add `state.json` read/write in this story.

### Logging (Provisional)

This story uses `logging.basicConfig(...)` as a placeholder. Story 4.2 replaces it with:
- `RotatingFileHandler` at `~/.nimble/nimble.log` (5MB max, 3 backups)
- Workers inherit `NIMBLE_LOG_PATH` env var

Do not attempt to implement the full logging setup here — just get `INFO`/`DEBUG` to stdout so the developer can observe daemon activity during Story 2.9 testing.

### Config Reload Diff Logic

The `_reload_config()` function must diff correctly. `SkillConfig` is a `@dataclass`, so equality comparison (`==`) compares all fields by value — this works correctly for detecting changed skills. The diff:

```python
current: dict[str, SkillConfig] = {w.config.name: w.config for w in registry.all() if w.status != "failed"}
incoming: dict[str, SkillConfig] = {s.name: s for s in validated}

to_remove = [name for name, cfg in current.items() if name not in incoming or incoming[name] != cfg]
to_add    = [cfg for cfg in validated if cfg.name not in current or current[cfg.name] != cfg]
unchanged = [cfg for cfg in validated if cfg.name in current and current[cfg.name] == cfg]
```

Shut down workers in `to_remove` before spawning `to_add`. Unbinding old hotkeys is not possible with pynput v1 — `adapter.register()` with the new binding for added/changed skills is idempotent (pynput adds a new listener; old binding will be overwritten if the same shortcut is re-registered).

### watchdog Version

watchdog 6.0.0 installed (satisfies `>=3.0`). The `watchdog.observers.Observer` API is stable across 3.x–6.x.

### `mypy --strict` Notes

- `Callable[[Path], None]` — use `from collections.abc import Callable`
- `ctypes.windll` — mypy will not type-check Windows-specific ctypes calls; wrap the `_terminate_windows` function with `if sys.platform == "win32":` and use `# type: ignore[attr-defined]` on the `windll` lines
- `signal.SIGTERM` is available on all platforms in Python 3.10+ — safe to use unconditionally
- Pre-existing mypy issue: `nimble/manifest/parser.py:8` has `# type: ignore[import-untyped]` that is unused under `ignore_missing_imports = true`. Cannot fix (file is off-limits for this story). All new code is mypy-clean.
- `watchdog.observers.Observer` — typed as `Any` in `ConfigWatcher._observer` to avoid mypy attr errors

### FakeNotifier Already in conftest

`tests/conftest.py` already defines `FakeNotifier` and the `fake_notifier` fixture. The production `SkillRunner` takes `notifier: Any` — in unit tests use `fake_notifier` from conftest. Only `tests/unit/test_notifier.py` needs to test the real `Notifier` class by mocking plyer.

### Cross-Story Dependencies

- **Stories 2.1–2.3** (DONE): `HotkeyAdapter` ABC + `get_adapter()` factory in `nimble/hotkeys/`
- **Story 2.4** (DONE): `build_context()` in `nimble/context/assembler.py`
- **Story 2.5** (DONE): `worker/entrypoint.py` — worker subprocess that handles dispatch
- **Story 2.6** (DONE): `SkillRunner.spawn_workers()`, `dispatch()`, `shutdown()` in `nimble/skills/runner.py`
- **Story 2.7** (DONE): `load_config()`, `validate_skill_paths()`, `ConfigError` in `nimble/manifest/parser.py` + `nimble/skills/loader.py`
- **Story 2.9** (next): Adds startup notification (uses `Notifier`) and `skills/hello_world/` — no changes to `daemon.py` required; `daemon.py` just needs to work
- **Story 4.2** (later): Replaces `logging.basicConfig` in `daemon.py` with `RotatingFileHandler`
- **Story 5.1** (later): Adds `state.json` read/write to `nimble/state.py`
- **Story 5.2** (later): Adds `nimble list` and `nimble status` CLI commands that read `state.json`

### Deferred Items (do not address in this story)

From `deferred-work.md`:
- No timeout for hung `skill.run()` — dispatch blocks indefinitely if worker hangs; deferred to reliability epic (Story 4.x)
- `stdout.flush()` `BrokenPipeError` not caught in runner — deferred to Story 4.x
- Wayland detection error surfacing as startup notification — deferred to Story 4.6
- `nimble validate` CLI command — deferred to Story 4.5

Story 2.8 deferred:
- Full graceful Windows shutdown (TerminateProcess is abrupt in v1)
- `state.json` write — owned by Story 5.1
- Startup confirmation notification — owned by Story 2.9
- macOS `darwin` platform support in `get_adapter()` factory — Story 2.10 adds `macos.py`; for this story the factory already raises `RuntimeError` on unsupported platforms

### References

- [Source: docs/bmad_output/planning-artifacts/architecture.md#IPC Model] — PID file at `~/.nimble/nimble.pid`, SIGTERM vs TerminateProcess, state file scope
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Daemon Process Model] — listener thread + pre-warmed workers, dispatch flow
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Configuration] — watchdog file watcher, diff + graceful reload, atomic writes
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Logging] — logging levels and basic setup
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Error Handling Patterns] — notifier.send() format for skill failures
- [Source: docs/bmad_output/planning-artifacts/architecture.md#All AI Agents MUST] — naming, import, type annotation, test rules
- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 2.8] — acceptance criteria, FR37, FR41 (notification deferred to 2.9), NFR2 (<5s cold start)
- [Source: docs/bmad_output/implementation-artifacts/2-7-yaml-config-loading-and-skill-registry.md#Dev Notes] — `from __future__ import annotations` pattern, module-level logger, patterns carried forward
- [Source: docs/bmad_output/implementation-artifacts/2-6-pre-warmed-worker-pool-and-dispatcher.md] — `SkillRunner` interface, `dispatch()` return type, `shutdown()` method

## Dev Agent Record

### Implementation Plan

1. Added `watchdog>=3.0` dependency (resolved to 6.0.0)
2. Created `nimble/notifier.py` — `Notifier.send()` wraps plyer with try/except to prevent notification failures from crashing daemon
3. Created `nimble/state.py` — PID file CRUD + `is_running()` via `os.kill(pid, 0)` idiom
4. Created `nimble/watcher.py` — `ConfigWatcher` wraps watchdog Observer; `_ConfigEventHandler` filters by resolved path to avoid false fires
5. Created `nimble/daemon.py` — full daemon loop: config load → worker spawn → hotkey registration → signal handling → config watcher → blocking `stop_event.wait()` → graceful shutdown
6. Updated `nimble/cli/commands.py` — replaced placeholder commands with `start`/`stop`/`restart` + hidden `_run`; cross-platform SIGTERM/TerminateProcess; PID polling for startup confirmation
7. Created 17 new unit tests across 4 test files covering all ACs

### Completion Notes

- All 11 tasks complete; all 91 tests pass (74 pre-existing + 17 new)
- watchdog 6.0.0 used (satisfies `>=3.0`)
- plyer import done lazily inside `Notifier.send()` to prevent import-time failures in headless environments
- `ConfigWatcher._observer` typed as `Any` to handle watchdog's incomplete type stubs
- Pre-existing mypy issue in `nimble/manifest/parser.py` (unused `type: ignore`) not fixable per story constraints; all story-authored code is mypy-strict clean
- `tests/unit/cli/__init__.py` created to make CLI test directory a proper package

## File List

- `pyproject.toml` (modified — added watchdog>=3.0)
- `nimble/notifier.py` (new)
- `nimble/state.py` (new)
- `nimble/watcher.py` (new)
- `nimble/daemon.py` (new)
- `nimble/cli/commands.py` (modified — replaced placeholder with start/stop/restart)
- `tests/unit/test_notifier.py` (new)
- `tests/unit/test_state.py` (new)
- `tests/unit/test_watcher.py` (new)
- `tests/unit/cli/__init__.py` (new)
- `tests/unit/cli/test_commands.py` (new)

## Change Log

- 2026-04-24: Story 2.8 implemented — daemon main loop and CLI start/stop/restart complete
