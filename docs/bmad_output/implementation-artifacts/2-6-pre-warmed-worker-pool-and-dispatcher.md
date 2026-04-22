# Story 2.6: Pre-Warmed Worker Pool and Dispatcher

Status: done

## Story

As a hotkey user,
I want my hotkey to trigger a skill with end-to-end latency under 200ms,
So that the interaction feels instant and I never wait for a Python cold start.

## Acceptance Criteria

1. **Given** `nimble/skills/runner.py` manages a pool of pre-warmed worker subprocesses
   **When** the daemon starts with N skills loaded
   **Then** N worker subprocesses are spawned (one per skill) with the correct Python executable for their venv
   **And** each worker is alive and ready before the first hotkey is accepted

2. **Given** a hotkey fires for a skill
   **When** the dispatcher in `runner.py` sends the context payload to the worker's stdin
   **Then** the round-trip (dispatch to result received) completes in under 200ms under normal system load (NFR1)

3. **Given** a worker process dies unexpectedly
   **When** `runner.py` detects this via `poll()`
   **Then** the skill is disabled, a system notification is fired, and the daemon continues serving other skills

4. **Given** author skills (`source: local`) vs community skills (`source: community`)
   **When** workers are spawned
   **Then** author skills use `sys.executable`; community skills use `.nimble/skills/<name>/.venv/bin/python` (Linux/macOS) or `.nimble/skills/<name>/.venv/Scripts/python.exe` (Windows) — satisfying FR8

## Tasks / Subtasks

- [x] Task 1: Create `nimble/skills/__init__.py` — empty package init (AC: 1)
  - [x] Empty file — mirrors existing `nimble/context/__init__.py` and `nimble/hotkeys/__init__.py` pattern

- [x] Task 2: Create `nimble/skills/registry.py` — in-memory skill registry (AC: 1, 3, 4)
  - [x] Define `SkillSource = Literal["local", "community"]`
  - [x] Define `SkillStatus = Literal["loaded", "disabled", "failed"]`
  - [x] Define `@dataclass SkillConfig` with fields: `name: str`, `source: SkillSource`, `binding: str`, `path: str`, `class_name: str`
  - [x] Define `@dataclass SkillWorker` with fields: `config: SkillConfig`, `process: subprocess.Popen[bytes]`, `status: SkillStatus`, `python_executable: str`
  - [x] Define `class SkillRegistry` with `register(worker: SkillWorker) -> None`, `get(name: str) -> SkillWorker | None`, `all() -> list[SkillWorker]`, `disable(name: str) -> None`
  - [x] `disable()` sets `worker.status = "failed"` and logs ERROR — does NOT terminate the process (runner handles that)
  - [x] All fields and return types annotated; `mypy --strict` passes

- [x] Task 3: Create `nimble/skills/runner.py` — worker pool + dispatcher (AC: 1, 2, 3, 4)
  - [x] Define `@dataclass SkillError` with: `type: str`, `message: str`, `skill_file: str`, `line: int`
  - [x] Define `@dataclass DispatchResult` with: `invocation_id: str`, `status: Literal["ok", "error"]`, `error: SkillError | None = None`
  - [x] Define `class SkillRunner` with:
    - `__init__(self, registry: SkillRegistry, notifier: Any, repo_root: Path) -> None`
    - `spawn_workers(self, configs: list[SkillConfig]) -> None` — spawns all workers, populates registry
    - `dispatch(self, skill_name: str, context: dict[str, Any]) -> DispatchResult` — sends invocation, reads result
    - `check_for_dead_workers(self) -> None` — call from main loop; polls all workers, disables dead ones
    - `shutdown(self) -> None` — terminates all worker processes cleanly
  - [x] `spawn_workers()`: for each config, determine `python_executable` (see venv resolution below), call `subprocess.Popen([python_executable, str(repo_root / "worker" / "entrypoint.py"), config.path, config.class_name], stdin=PIPE, stdout=PIPE, stderr=PIPE, env={**os.environ, "NIMBLE_REPO_ROOT": str(repo_root)})`, register the SkillWorker
  - [x] `dispatch()`: generate `invocation_id = str(uuid.uuid4())`, build payload `{"invocation_id": invocation_id, "context": context}`, write `json.dumps(payload) + "\n"` to worker stdin and flush, readline from worker stdout, parse JSON, return `DispatchResult`
  - [x] `dispatch()`: if `worker.process.poll() is not None` before sending → worker is dead → call `_disable_dead_worker()` → raise `RuntimeError(f"Worker for skill {skill_name!r} is not running")`
  - [x] `check_for_dead_workers()`: iterate all `registry.all()`, call `worker.process.poll()` on each, if not None → call `_disable_dead_worker()`
  - [x] `_disable_dead_worker(worker: SkillWorker) -> None` (private): call `registry.disable(worker.config.name)`, call `notifier.send(title=f"Nimble — {worker.config.name}", body=f"Worker process died unexpectedly. Skill disabled.")`
  - [x] `shutdown()`: for each worker in `registry.all()`, call `worker.process.terminate()` then `worker.process.wait(timeout=5.0)` (SIGTERM on Linux, TerminateProcess on Windows via subprocess API)
  - [x] All functions annotated; `mypy --strict` passes; absolute imports only

- [x] Task 4: Venv Python resolution (AC: 4) — implement `_get_python_executable(config: SkillConfig, repo_root: Path) -> str` in `runner.py`
  - [x] `local` source → `sys.executable`
  - [x] `community` source, Linux/macOS (`sys.platform != "win32"`) → `str(Path.home() / ".nimble" / "skills" / config.name / ".venv" / "bin" / "python")`
  - [x] `community` source, Windows → `str(Path.home() / ".nimble" / "skills" / config.name / ".venv" / "Scripts" / "python.exe")`
  - [x] Function is a module-level helper (not a method), fully annotated

- [x] Task 5: Create `tests/unit/skills/__init__.py` — empty (AC: all)

- [x] Task 6: Create `tests/unit/skills/test_registry.py` (AC: 1, 3)
  - [x] `test_register_and_get()`: register a SkillWorker, assert `get(name)` returns it
  - [x] `test_get_unknown_returns_none()`: `get("nonexistent")` returns `None`
  - [x] `test_all_returns_all_registered()`: register 2 workers, assert `all()` length is 2
  - [x] `test_disable_sets_status_failed()`: register a worker with status "loaded", call `disable()`, assert `status == "failed"`
  - [x] Use `Mock()` for `subprocess.Popen` instances — never spawn real subprocesses in unit tests

- [x] Task 7: Create `tests/unit/skills/test_runner.py` (AC: 1, 2, 3, 4)
  - [x] Use `unittest.mock.patch("subprocess.Popen")` to intercept worker spawning — never spawn real subprocesses
  - [x] `test_spawn_workers_local_uses_sys_executable()`: spawn a local skill, assert `Popen` was called with `sys.executable` as the first list element
  - [x] `test_spawn_workers_community_uses_venv_python()`: spawn a community skill, assert `Popen` was called with the venv Python path
  - [x] `test_dispatch_happy_path()`: mock worker's stdout to return a valid `{"invocation_id": "...", "status": "ok", "error": null}` line, assert `DispatchResult.status == "ok"`
  - [x] `test_dispatch_error_response()`: mock worker stdout to return an error JSON, assert `DispatchResult.status == "error"` and `DispatchResult.error.type` is populated
  - [x] `test_check_for_dead_workers_disables_and_notifies()`: set `process.poll()` to return non-None (dead process), call `check_for_dead_workers()`, assert `registry.get(name).status == "failed"` and `fake_notifier.sent` has one entry
  - [x] `test_dispatch_on_dead_worker_raises()`: set `process.poll()` to return non-None before dispatch, assert `RuntimeError` is raised
  - [x] `test_shutdown_terminates_all_workers()`: call `shutdown()`, assert `process.terminate()` was called for each worker
  - [x] Use `FakeNotifier` from `tests.conftest` — do NOT import `plyer` or any notification dep in tests

- [x] Task 8: Verify quality gates
  - [x] `mypy nimble/ tests/ worker/` — exits 0
  - [x] `pytest` — all tests pass (42 existing + 16 new = 58 total, ≥ 55 required)
  - [x] `black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

### Review Findings

- [x] [Review][Patch] AC2 latency contract interpretation (measure-only) — dispatch now logs measured elapsed latency instead of hardcoded `0.0ms`.
- [x] [Review][Patch] Missing readiness verification before marking workers loaded [nimble/skills/runner.py:48]
- [x] [Review][Patch] Dispatch write path race can raise unhandled BrokenPipe/OSError [nimble/skills/runner.py:90]
- [x] [Review][Patch] Malformed `error` payload can crash dispatch parsing [nimble/skills/runner.py:113]
- [x] [Review][Patch] Invalid worker `status` values are accepted without contract validation [nimble/skills/runner.py:127]
- [x] [Review][Patch] Dead worker notifications can repeat on every health-check cycle [nimble/skills/runner.py:131]
- [x] [Review][Patch] `notifier.send()` exceptions can break dead-worker handling flow [nimble/skills/runner.py:138]
- [x] [Review][Patch] Partial startup failure can leave already-spawned workers orphaned [nimble/skills/runner.py:48]
- [x] [Review][Patch] Missing tests for write/flush failure and malformed `error` object handling [tests/unit/skills/test_runner.py:149]

## Dev Notes

### Role in the Daemon Architecture

This story creates the **missing middle layer** between the hotkey event (Stories 2.1–2.3), context assembly (Story 2.4), and the worker subprocess (Story 2.5). After this story, the dispatch chain is complete:

```
pynput hotkey event (x11.py / windows.py)
  → daemon.py calls runner.dispatch(skill_name, context)  ← STORY 2.6
  → runner.py writes JSON payload to worker stdin
  → worker/entrypoint.py executes skill.run(context, tools)  ← Story 2.5 (DONE)
  → worker writes JSON result to stdout
  → runner.py reads and parses result → DispatchResult
  → if error: notifier.send(...)
```

Story 2.7 (YAML config loading) will feed `SkillConfig` objects into `runner.spawn_workers()`. Story 2.8 (daemon main loop) will call `runner.check_for_dead_workers()` in the main loop and `runner.shutdown()` on daemon stop. This story produces only the runner/registry — it is **not yet wired into a real daemon**, but must be fully unit-tested in isolation.

### Files to Create (all new — `nimble/skills/` does not yet exist)

```
nimble/skills/__init__.py            ← new (empty)
nimble/skills/registry.py            ← new
nimble/skills/runner.py              ← new
tests/unit/skills/__init__.py        ← new (empty)
tests/unit/skills/test_registry.py   ← new
tests/unit/skills/test_runner.py     ← new
```

Do NOT touch: `worker/`, `nimble/context/`, `nimble/hotkeys/`, `tests/unit/worker/`.

### IPC Contract (Hard — Do Not Deviate)

The exact schemas are defined in architecture.md §Worker IPC Protocol and implemented in Story 2.5. The runner **must** produce and consume these byte-for-byte:

**runner → worker (stdin):**
```json
{"invocation_id": "uuid4-string", "context": {"selection": "...", "clipboard": "...", "active_app": "...", "mouse_position": [x, y]}}
```
Followed by `\n` and `stdin.flush()`.

**worker → runner (stdout success):**
```json
{"invocation_id": "uuid4-string", "status": "ok", "error": null}
```

**worker → runner (stdout error):**
```json
{"invocation_id": "uuid4-string", "status": "error", "error": {"type": "KeyError", "message": "...", "skill_file": "...", "line": 14}}
```

Rules:
- One JSON line per message (terminated by `\n`)
- `invocation_id` must be echoed back — use it to correlate responses
- `status` is always `"ok"` or `"error"` — no other values
- After writing to stdin, call `stdin.flush()` before reading stdout — otherwise the worker blocks waiting for input

### subprocess.Popen Spawn Command

```python
import subprocess
import os

proc = subprocess.Popen(
    [python_executable, str(repo_root / "worker" / "entrypoint.py"), config.path, config.class_name],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env={**os.environ, "NIMBLE_REPO_ROOT": str(repo_root)},
)
```

- `stdin=PIPE` and `stdout=PIPE` are required for IPC
- `stderr=PIPE` captures worker stderr (logs) without polluting the daemon's stdout
- `NIMBLE_REPO_ROOT` env var is the belt-and-suspenders fallback for `sys.path` injection in the worker (see Story 2.5 Dev Notes)
- Do NOT use `shell=True` — pass args as a list

### stdin/stdout I/O — Buffering Gotcha

Worker stdout is line-buffered in text mode but **binary** via `subprocess.PIPE`. Use:

```python
# Writing (bytes mode)
payload_bytes = (json.dumps(payload) + "\n").encode("utf-8")
worker.process.stdin.write(payload_bytes)  # type: ignore[union-attr]
worker.process.stdin.flush()               # type: ignore[union-attr]

# Reading (bytes mode → decode)
line = worker.process.stdout.readline()    # type: ignore[union-attr]
result = json.loads(line.decode("utf-8"))
```

`worker/entrypoint.py` calls `sys.stdout.flush()` after every write (Story 2.5 contract) — so readline() will not deadlock on a live worker. However, if the worker is dead, `readline()` returns `b""`. Guard against this:

```python
line = worker.process.stdout.readline()
if not line:
    raise RuntimeError(f"Worker for {skill_name!r} died during dispatch")
```

### Worker Death Detection

`process.poll()` returns `None` if alive, an integer exit code if dead. Check **before** dispatch:

```python
if worker.process.poll() is not None:
    self._disable_dead_worker(worker)
    raise RuntimeError(f"Worker for skill {skill_name!r} is not running")
```

Also call `check_for_dead_workers()` from the daemon's main loop (Story 2.8) to proactively detect deaths between hotkey firings.

### Dataclass Structures

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Literal
import subprocess

SkillSource = Literal["local", "community"]
SkillStatus = Literal["loaded", "disabled", "failed"]


@dataclass
class SkillConfig:
    name: str
    source: SkillSource
    binding: str
    path: str
    class_name: str


@dataclass
class SkillWorker:
    config: SkillConfig
    process: subprocess.Popen[bytes]
    status: SkillStatus
    python_executable: str


@dataclass
class SkillError:
    type: str
    message: str
    skill_file: str
    line: int


@dataclass
class DispatchResult:
    invocation_id: str
    status: Literal["ok", "error"]
    error: SkillError | None = None
```

### Test Mocking Strategy

Never spawn real subprocesses in unit tests. Use `unittest.mock.MagicMock()` to fake the `Popen` object:

```python
from unittest.mock import MagicMock, patch
import json

def _make_fake_proc(response: dict) -> MagicMock:
    proc = MagicMock()
    proc.poll.return_value = None  # alive
    response_line = (json.dumps(response) + "\n").encode("utf-8")
    proc.stdout.readline.return_value = response_line
    proc.stdin = MagicMock()
    proc.stderr = MagicMock()
    return proc

# In test:
with patch("subprocess.Popen", return_value=_make_fake_proc({...})) as mock_popen:
    runner.spawn_workers([config])
    result = runner.dispatch("my-skill", context)
    assert result.status == "ok"
```

### Notifier Interface

`SkillRunner.__init__` accepts `notifier` typed as `Any` (or an informal protocol) — the real `plyer`-based notifier ships in Story 4.1. For now, use `FakeNotifier` from `tests/conftest.py` in all tests. The notifier must expose `send(title: str, body: str) -> None`.

Do NOT import `plyer` or anything notification-related inside `runner.py` itself — the notifier is injected via `__init__`.

### Venv Python Resolution (Cross-Platform)

```python
import sys
from pathlib import Path

def _get_python_executable(config: SkillConfig) -> str:
    if config.source == "local":
        return sys.executable
    # community skill — use its isolated venv Python
    base = Path.home() / ".nimble" / "skills" / config.name / ".venv"
    if sys.platform == "win32":
        return str(base / "Scripts" / "python.exe")
    return str(base / "bin" / "python")
```

### mypy --strict Notes

- `subprocess.Popen[bytes]` requires the generic parameter — `Popen` without `[bytes]` fails strict mode
- `worker.process.stdin` is typed as `IO[bytes] | None` — use `# type: ignore[union-attr]` only after you've confirmed stdin is not None (it won't be since we pass `stdin=PIPE`)
- `Literal["ok", "error"]` in `DispatchResult.status` is valid in strict mode with `from __future__ import annotations`
- The `notifier` param typed as `Any` is acceptable here — strict mode allows `Any` as an escape hatch for injected dependencies not yet typed

### Logging

Follow architecture.md §Logging Patterns:

```python
import logging
logger = logging.getLogger(__name__)

# On spawn success:
logger.info("Skill %s loaded (source=%s, binding=%s)", config.name, config.source, config.binding)
# On dispatch timing:
logger.debug("Skill %s dispatch completed in %.1fms", skill_name, elapsed_ms)
# On worker death:
logger.error("Worker for skill %s died (exit code %s). Skill disabled.", name, exit_code)
```

### Previous Story (2.5) Patterns to Carry Forward

- **Never write non-JSON to worker stdin** — the worker's IPC loop expects exactly one JSON line; any other write corrupts the framing
- **`sys.stdout.flush()` equivalent on the runner side**: after every `stdin.write()`, call `stdin.flush()` — otherwise the worker's `readline()` will block
- **Mock all subprocess calls in unit tests** — same discipline as 2.4 and 2.5
- **`try/except Exception` around dispatch** — runner must not let a malformed worker response crash the daemon; parse errors should surface as DispatchResult errors

### Project Structure Notes

- `nimble/skills/` is a new package — create all three files from scratch
- `runner.py` imports from `nimble.skills.registry` using absolute imports (never relative)
- The `tests/unit/skills/` directory mirrors `nimble/skills/` per architecture.md §Test Patterns
- Architecture.md also lists `tests/unit/skills/test_loader.py` — that is for Story 2.7 (skill loader/YAML config); do NOT create it here

### Cross-Story Dependencies

- **Story 2.5** (DONE): `worker/entrypoint.py` is the subprocess this story spawns. IPC contract established. Context object field names are: `selection`, `clipboard`, `active_app`, `mouse_position`.
- **Story 2.7** (next): Will add `nimble/manifest/parser.py` which parses `config.yaml` and produces `list[SkillConfig]` → feeds into `runner.spawn_workers()`. For this story, construct `SkillConfig` objects manually in tests.
- **Story 2.8** (later): `daemon.py` main loop will call `runner.check_for_dead_workers()` on a timer and `runner.shutdown()` at exit. Leave these methods as described — Story 2.8 just wires them up.
- **Story 3.x** (later): Tool primitives replace the `None` tools stub in the worker. No changes needed in `runner.py` for that.
- **Story 4.1** (later): Real `notifier.py` replaces the injected stub. `SkillRunner.__init__` already accepts it as a parameter — no interface change needed.

### References

- [Source: docs/bmad_output/planning-artifacts/architecture.md#Daemon Process Model] — pre-warmed worker rationale, worker lifecycle
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Worker IPC Protocol] — exact JSON schemas (hard contract)
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Per-Skill Venv Activation] — `sys.executable` vs venv Python selection
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Complete Project Directory Structure] — `nimble/skills/runner.py`, `registry.py` file locations
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Type Annotation Patterns] — `@dataclass`, `Literal`, `| None` usage
- [Source: docs/bmad_output/planning-artifacts/architecture.md#All AI Agents MUST] — naming, imports, test structure rules
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Error Handling Patterns] — dispatcher error → notification pipeline
- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 2.6] — acceptance criteria, FR8 coverage
- [Source: docs/bmad_output/planning-artifacts/epics.md#NonFunctional Requirements] — NFR1 (<200ms), NFR4 (<50MB), NFR11 (isolation)
- [Source: docs/bmad_output/implementation-artifacts/2-5-worker-subprocess-ipc-entrypoint.md#IPC Protocol — Hard Contract] — exact JSON field names confirmed in implementation
- [Source: docs/bmad_output/implementation-artifacts/2-5-worker-subprocess-ipc-entrypoint.md#Review Findings] — `threading.local` for invocation_id, `if`/`raise` not `assert`, callable check on skill class

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation proceeded without blockers.

### Completion Notes List

- Created `nimble/skills/` package with `registry.py` (SkillConfig, SkillWorker, SkillRegistry dataclasses) and `runner.py` (SkillError, DispatchResult, SkillRunner class with spawn/dispatch/check/shutdown).
- Implemented `_get_python_executable()` as module-level helper in `runner.py` — local skills use `sys.executable`, community skills use per-platform venv Python path.
- IPC follows hard contract from Story 2.5: one JSON line per message with `\n` termination, `stdin.flush()` after every write, empty `readline()` guard for dead workers.
- 16 new tests added (5 registry + 11 runner); all use `MagicMock` for `subprocess.Popen` — no real subprocesses spawned.
- mypy strict, black, and flake8 all pass. Total tests: 58 (was 42).

### File List

- nimble/skills/__init__.py (new)
- nimble/skills/registry.py (new)
- nimble/skills/runner.py (new)
- tests/unit/skills/__init__.py (new)
- tests/unit/skills/test_registry.py (new)
- tests/unit/skills/test_runner.py (new)

### Change Log

- 2026-04-22: Implemented Story 2.6 — pre-warmed worker pool and dispatcher. Created nimble/skills package (registry + runner) with full unit test coverage. 58 tests pass, all quality gates green.
