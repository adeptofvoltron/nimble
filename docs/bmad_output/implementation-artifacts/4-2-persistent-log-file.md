# Story 4.2: Persistent Log File

Status: review

## Story

As a user debugging a skill failure,
I want full error details and stack traces written to a persistent log file,
so that the system notification acts as a pointer and I can read the full context in the log.

## Acceptance Criteria

1. **Given** `~/.nimble/nimble.log` is configured as a `RotatingFileHandler` (5MB max, 3 backups)
   **When** a skill raises an exception
   **Then** the full traceback is written to the log at `ERROR` level with the skill name, exception type, file, and line number

2. **Given** the log file reaches 5MB
   **When** the next log entry is written
   **Then** the file rotates — the old file becomes `nimble.log.1` and a new `nimble.log` is started

3. **Given** a worker process is spawned
   **When** it starts
   **Then** it inherits `NIMBLE_LOG_PATH` from the daemon environment and writes to the same log file

4. **Given** `nimble start` is run with the `--debug` flag
   **When** any log entry is written
   **Then** `DEBUG`-level entries appear in the log — they are suppressed at the default `INFO` level

## Tasks / Subtasks

- [x] Task 1: Replace `logging.basicConfig()` in `daemon.py::run()` with `RotatingFileHandler` (AC: 1, 2, 4)
  - [x] Create `~/.nimble/` directory if it does not exist (`Path.home() / ".nimble"`)
  - [x] Add `RotatingFileHandler` targeting `~/.nimble/nimble.log` with `maxBytes=5*1024*1024` and `backupCount=3`
  - [x] Use format `"%(asctime)s %(levelname)s %(name)s: %(message)s"` (same as current basicConfig)
  - [x] Set level to `logging.DEBUG` if `debug=True` else `logging.INFO` on the root logger
  - [x] Keep any stdout handler only if explicitly needed for diagnostics — primary output is the file

- [x] Task 2: Pass `NIMBLE_LOG_PATH` env var from daemon to workers in `runner.py` (AC: 3)
  - [x] In `SkillRunner.spawn_workers()`, add `"NIMBLE_LOG_PATH": str(Path.home() / ".nimble" / "nimble.log")` to the `env` dict alongside `NIMBLE_REPO_ROOT` and `NIMBLE_AI_CONFIG`

- [x] Task 3: Wire up logging in `worker/entrypoint.py` using `NIMBLE_LOG_PATH` (AC: 3)
  - [x] After the sys.path injection block and before any imports that use logging, read `os.environ.get("NIMBLE_LOG_PATH")`
  - [x] If set, configure a `logging.FileHandler` (not RotatingFileHandler — only the daemon owns rotation) pointing at that path, with the same format string
  - [x] Set the root logger level to `logging.INFO` (workers do not receive the `--debug` flag; they will log at INFO by default)
  - [x] Worker log calls should use `logging.getLogger(__name__)` — not print/stderr

- [x] Task 4: Write tests (AC: 1, 2, 3, 4)
  - [x] `tests/unit/test_daemon_logging.py` — new file
    - [x] `test_rotating_handler_configured()` — patch `logging.handlers.RotatingFileHandler`; call `daemon.run()` (patched so it exits immediately); assert RotatingFileHandler was instantiated with correct path, maxBytes=5242880, backupCount=3
    - [x] `test_debug_flag_sets_debug_level()` — same as above with `debug=True`; assert root logger level is `DEBUG`
    - [x] `test_default_level_is_info()` — with `debug=False`; assert root logger level is `INFO`
  - [x] `tests/unit/skills/test_runner_env.py` — **add to existing `tests/unit/skills/test_runner.py`** (not a new file)
    - [x] `test_spawn_workers_passes_log_path_env()` — mock `subprocess.Popen`; call `runner.spawn_workers([fake_skill_config])`; assert `NIMBLE_LOG_PATH` key is present in `Popen` call's `env` kwarg
  - [x] `tests/unit/worker/test_entrypoint_logging.py` — **add to existing `tests/unit/worker/test_entrypoint.py``**
    - [x] `test_log_path_env_wires_file_handler()` — patch `logging.FileHandler`; set `os.environ["NIMBLE_LOG_PATH"]`; trigger the logging setup code path; assert `FileHandler` was instantiated with the expected path

- [x] Task 5: Verify quality gates (AC: all)
  - [x] `python3 -m pytest tests/unit/skills/test_runner.py tests/unit/worker/test_entrypoint.py` — all pass
  - [x] `mypy nimble/ tests/ worker/` — exits 0 on changed files (3 pre-existing errors in `test_platform.py` unchanged)
  - [x] `black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

## Dev Notes

### What Exists Today — Do NOT Reinvent

**Current logging setup in `nimble/daemon.py::run()` (lines 26–29):**
```python
logging.basicConfig(
    level=logging.DEBUG if debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
```
This logs to stdout only. This story replaces it with a file-backed handler.

**Current env vars passed to workers in `nimble/skills/runner.py::spawn_workers()` (lines 82–86):**
```python
env={
    **os.environ,
    "NIMBLE_REPO_ROOT": str(self._repo_root),
    "NIMBLE_AI_CONFIG": ai_config_json,
},
```
Add `NIMBLE_LOG_PATH` here. Do not replace the existing keys.

**`worker/entrypoint.py` has no logging setup today.** The worker uses `sys.stdout.write()` for IPC (not logging). This story adds a `FileHandler` so that any `logger.error()` calls inside the worker write to the shared log — not to interfere with the stdout IPC channel.

### Critical Constraint: Worker Logging Must NOT Touch stdout

The worker's stdout is the IPC channel with the daemon (JSON lines protocol). Worker logging **must write to the file only** — never to stdout. Use `FileHandler`, not `StreamHandler`. If `NIMBLE_LOG_PATH` is not set (e.g. unit tests), do not add any handler — let the root logger's NullHandler silently swallow.

### Log File Location

```python
LOG_PATH = Path.home() / ".nimble" / "nimble.log"
```

Ensure `~/.nimble/` exists before opening the handler — use `LOG_PATH.parent.mkdir(parents=True, exist_ok=True)`.

### RotatingFileHandler Parameters

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    LOG_PATH,
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=3,
)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
```

### Worker FileHandler Setup

The worker must configure its handler early — immediately after the sys.path injection block (lines 1–12 of `worker/entrypoint.py`), before imports that trigger `getLogger` calls:

```python
import logging
import os
from pathlib import Path

_log_path = os.environ.get("NIMBLE_LOG_PATH")
if _log_path:
    _handler = logging.FileHandler(_log_path)
    _handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logging.getLogger().addHandler(_handler)
    logging.getLogger().setLevel(logging.INFO)
```

### Architecture Compliance

- Log file at `~/.nimble/nimble.log` — exactly as specified in architecture ("Logging" section, `~/.nimble/` runtime dir)
- Rotation: 5MB × 3 backups — matches architecture spec verbatim
- Workers inherit log path via `NIMBLE_LOG_PATH` env var — matches architecture: "Daemon and all worker processes write to the same log file (workers inherit the log path via env var)"
- `logging` standard library only — no third-party logging dep
- `mypy --strict` enforced throughout — annotate all new functions and parameters

### Test Strategy

**daemon.py logging setup** — difficult to test directly without importing the module (which fails in CI due to missing `watchdog`). Structure the test to work around this:
- Extract the logging setup logic into a small helper function `_configure_logging(log_path: Path, debug: bool) -> None` in `daemon.py`
- Test that helper directly — it doesn't import `watchdog`
- This also makes the function independently reusable

**runner.py env injection** — mock `subprocess.Popen` (already done in existing runner tests — follow the same pattern). Check `call_args.kwargs["env"]` for the `NIMBLE_LOG_PATH` key.

**worker logging setup** — mock `logging.FileHandler` and assert it's called with the right path. Set and restore `os.environ["NIMBLE_LOG_PATH"]` in setUp/tearDown or use `monkeypatch`.

### File List to Touch

- `nimble/daemon.py` — replace `basicConfig` with `RotatingFileHandler` setup
- `nimble/skills/runner.py` — add `NIMBLE_LOG_PATH` to env dict in `spawn_workers()`
- `worker/entrypoint.py` — add `FileHandler` setup block at top
- `tests/unit/test_daemon_logging.py` — new test file for logging setup
- `tests/unit/skills/test_runner.py` — add env injection test
- `tests/unit/worker/test_entrypoint.py` — add file handler wiring test

### Baseline (Before This Story)

```
Tests: 153 collected (2 collection errors in test_daemon.py and test_watcher.py — pre-existing, due to missing watchdog in test env)
mypy: 3 pre-existing errors in test_platform.py — unchanged
black: clean
flake8: clean
```

### Why Not RotatingFileHandler in Worker

Workers are short-lived (relative to the daemon) and do not own the rotation policy. If all workers opened a `RotatingFileHandler` on the same file, concurrent writes could corrupt the log or trigger spurious rotations. The daemon's single `RotatingFileHandler` owns rotation; workers use plain `FileHandler` (append mode, which is safe for concurrent appends on Linux — the OS guarantees atomicity for writes ≤ PIPE_BUF for regular file appends).

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 4.2] — acceptance criteria, FR34
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Logging] — RotatingFileHandler spec, 5MB/3 backups, NIMBLE_LOG_PATH env var
- [Source: nimble/daemon.py#run] — current basicConfig setup to replace (lines 26–29)
- [Source: nimble/skills/runner.py#spawn_workers] — env dict to extend (lines 82–86)
- [Source: worker/entrypoint.py] — sys.path injection block location, no logging setup today
- [Source: docs/bmad_output/implementation-artifacts/4-1-per-skill-exception-isolation-and-error-notifications.md#Dev Notes] — existing error logging patterns in daemon already writing to `logger.error()`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Extracted `configure_logging(log_path, debug)` into `nimble/logging_setup.py` (separate from `daemon.py`) so it can be unit-tested without the `watchdog` dependency that causes pre-existing collection errors in `test_daemon.py`.
- `daemon.py::run()` now calls `configure_logging` then delegates to the same main loop. No stdout handler is added — file is the only output.
- Worker `FileHandler` setup placed at module level in `entrypoint.py`, immediately after sys.path injection and before downstream imports, using plain `FileHandler` (daemon owns rotation).
- 5 new tests added: 3 in `test_daemon_logging.py`, 1 in `test_runner.py`, 1 in `test_entrypoint.py`. All 158 unit tests pass (153 baseline + 5 new). mypy clean on all changed files. black and flake8 exit 0.

### File List

- `nimble/logging_setup.py` (new)
- `nimble/daemon.py` (modified)
- `nimble/skills/runner.py` (modified)
- `worker/entrypoint.py` (modified)
- `tests/unit/test_daemon_logging.py` (new)
- `tests/unit/skills/test_runner.py` (modified)
- `tests/unit/worker/test_entrypoint.py` (modified)

## Change Log

- 2026-04-26: Implemented persistent log file (story 4-2) — RotatingFileHandler at `~/.nimble/nimble.log` (5MB/3 backups), NIMBLE_LOG_PATH env propagation to workers, worker FileHandler wiring. 5 new tests.
