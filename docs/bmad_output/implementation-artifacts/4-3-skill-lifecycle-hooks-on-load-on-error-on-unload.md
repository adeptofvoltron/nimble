# Story 4.3: Skill Lifecycle Hooks (`on_load`, `on_error`, `on_unload`)

Status: done

## Story

As a skill author,
I want to declare optional `on_load`, `on_error`, and `on_unload` methods on my skill class,
so that I can validate dependencies at startup, enrich errors before they surface, and clean up resources when the daemon shuts down.

## Acceptance Criteria

1. **Given** a skill class defines `on_load(self, config)`
   **When** the worker subprocess starts
   **Then** `on_load` is called before the worker enters the IPC loop — before the first hotkey can be dispatched (FR9)

2. **Given** `on_load` raises an exception
   **When** the worker detects this
   **Then** the skill is marked disabled in the registry, a startup notification fires: `"Nimble — <skill-name>: on_load failed: <message>. Skill disabled until restart."` (FR36)
   **And** the daemon continues loading all other skills normally

3. **Given** a skill class defines `on_error(self, exc)`
   **When** `run()` raises an exception
   **Then** `on_error` is called with the exception before it is serialised — the skill can enrich or transform the error message

4. **Given** a skill class defines `on_unload(self)`
   **When** the daemon shuts down or the skill is disabled
   **Then** `on_unload` is called on the worker before the subprocess exits

## Tasks / Subtasks

- [x] Task 1: Add startup handshake protocol to `worker/entrypoint.py` (AC: 1, 2)
  - [x] In `run()`, after tools build succeeds, check `hasattr(skill, "on_load")`. If present, call `skill.on_load(skill_config)` where `skill_config` is loaded from `NIMBLE_SKILL_CONFIG` env var (JSON dict)
  - [x] If `on_load` raises: write `{"invocation_id": "", "status": "error", "error": _extract_error(exc), "phase": "on_load"}` to stdout, flush, return (do not enter IPC loop)
  - [x] On ALL successful startup paths (class loaded, tools built, on_load passed): write `{"invocation_id": "", "status": "ok", "error": null}` before entering the IPC loop — this is the startup handshake
  - [x] Existing failure paths (class init failure, tools build failure) already write error + return; ensure they DON'T also write the success handshake

- [x] Task 2: Add `on_error` support in `worker/entrypoint.py` (AC: 3)
  - [x] In the IPC loop `except Exception as exc` block, before calling `_extract_error(exc)`:
    - [x] Check `hasattr(skill, "on_error")`
    - [x] If present, call `skill.on_error(exc)` inside a nested try/except — if `on_error` itself raises, log and use the original exception
    - [x] The error dict to serialise comes from `_extract_error(exc)` using whatever exception is current after `on_error`

- [x] Task 3: Add `on_unload` support in `worker/entrypoint.py` (AC: 4)
  - [x] After the IPC loop's `for line in sys.stdin:` ends (stdin closed = daemon shutdown or skill disabled):
    - [x] Check `hasattr(skill, "on_unload")`
    - [x] If present, call `skill.on_unload()` inside a try/except; log any exception at WARNING level (do not propagate — worker is shutting down anyway)

- [x] Task 4: Pass `NIMBLE_SKILL_CONFIG` env var from daemon to workers in `runner.py` (AC: 1)
  - [x] In `SkillRunner.spawn_workers()`, add `"NIMBLE_SKILL_CONFIG": json.dumps({"name": config.name, "source": config.source, "binding": config.binding, "path": config.path, "class_name": config.class_name})` to the `env` dict alongside the existing keys

- [x] Task 5: Read startup handshake in `runner.py` and handle failures gracefully (AC: 2)
  - [x] After `subprocess.Popen(...)` and the existing `proc.poll()` check, remove the `raise RuntimeError` for poll-detected exit; instead, fall through to the handshake read
  - [x] Read one line from `proc.stdout.readline()` — this blocks until the worker writes the handshake (or the process exits, returning `b""`)
  - [x] If empty bytes (process died without writing): disable skill gracefully — `self._registry.register(worker_with_failed_status)`, fire notification `"Nimble — <name>: failed to start. Skill disabled until restart."`, log ERROR, `continue` to next config
  - [x] If handshake `status == "ok"`: proceed normally (register worker, log info)
  - [x] If handshake `status == "error"` with `"phase": "on_load"`: disable skill gracefully — fire notification `"Nimble — <name>: on_load failed: <message>. Skill disabled until restart."`, log ERROR, `continue`
  - [x] If handshake `status == "error"` without phase (class init or tools build failure): disable skill gracefully — fire notification `"Nimble — <name>: failed to load: <message>. Skill disabled until restart."`, log ERROR, `continue`
  - [x] In ALL failure cases: do NOT raise RuntimeError (daemon must continue loading other skills)
  - [x] Update `spawn_workers` so that the outer `try/except` block still catches `subprocess.Popen` failures (e.g. Python executable not found), but NOT worker startup failures (those are handled per-skill)

- [x] Task 6: Write tests (AC: 1–4)
  - [x] `tests/unit/worker/test_entrypoint.py` — add tests:
    - [x] `test_on_load_called_before_ipc_loop()` — skill has `on_load(self, config)` that records call; verify it's called (and with a dict) before any IPC invocation is processed
    - [x] `test_on_load_failure_writes_error_response()` — skill with `on_load` that raises; verify error response has `"phase": "on_load"` and process writes it then doesn't enter IPC loop
    - [x] `test_on_error_called_when_run_raises()` — skill with `on_error(self, exc)` that enriches message; verify the serialised error uses the enriched message
    - [x] `test_on_error_itself_raising_uses_original_exception()` — skill with `on_error` that raises; verify original exception type is serialised (not the on_error exception)
    - [x] `test_on_unload_called_after_ipc_loop()` — skill with `on_unload(self)` that records call; run with empty stdin; verify `on_unload` was called after loop exits
    - [x] `test_success_handshake_written_before_ipc_loop()` — verify the ok handshake `{"invocation_id": "", "status": "ok"}` is the first line written when startup succeeds
  - [x] `tests/unit/skills/test_runner.py` — add tests:
    - [x] `test_spawn_workers_passes_skill_config_env()` — verify `NIMBLE_SKILL_CONFIG` key in Popen env and that it's valid JSON with skill name/binding
    - [x] `test_spawn_workers_on_load_failure_disables_skill_and_continues()` — mock Popen so first worker writes on_load error + exits, second worker ok; verify both skills are processed, first has `status == "failed"`, notifier was called for first
    - [x] `test_spawn_workers_startup_crash_no_output_disables_gracefully()` — mock Popen so worker exits with empty stdout; verify skill is disabled and no RuntimeError raised
    - [x] `test_spawn_workers_reads_ok_handshake_and_registers_worker()` — mock Popen with ok handshake; verify worker is registered with status "loaded"

- [x] Task 7: Verify quality gates
  - [x] `python3 -m pytest tests/unit/ --ignore=tests/unit/test_daemon.py --ignore=tests/unit/test_watcher.py` — all pass (168 collected, 168 passed)
  - [x] `mypy nimble/ tests/ worker/` — exits 0 on changed files (3 pre-existing errors in `test_platform.py` unchanged)
  - [x] `black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

## Dev Notes

### What Exists Today — Do NOT Reinvent

**Current worker startup flow in `worker/entrypoint.py::run()` (lines 122–145):**
```python
def run(module_path: str, class_name: str) -> None:
    try:
        skill_class = _load_skill_class(module_path, class_name)
        skill = skill_class()
    except Exception as exc:
        startup_response = {"invocation_id": "", "status": "error", "error": _extract_error(exc)}
        sys.stdout.write(json.dumps(startup_response) + "\n")
        sys.stdout.flush()
        return
    try:
        tools = _build_tools()
    except RuntimeError as exc:
        startup_tools_error = {"invocation_id": "", "status": "error", "error": _extract_error(exc)}
        sys.stdout.write(json.dumps(startup_tools_error) + "\n")
        sys.stdout.flush()
        return

    for line in sys.stdin:   # IPC loop
        ...
```

Do NOT add a success handshake before the `on_load` call — only after all startup steps succeed.

**Current IPC loop error handler (lines 163–170):**
```python
except Exception as exc:
    response = {
        "invocation_id": invocation_id,
        "status": "error",
        "error": _extract_error(exc),
    }
```
`on_error` must be called here, before `_extract_error(exc)`, using the (possibly transformed) exception.

**Current runner env dict in `runner.py::spawn_workers()` (lines 82–87):**
```python
env={
    **os.environ,
    "NIMBLE_REPO_ROOT": str(self._repo_root),
    "NIMBLE_AI_CONFIG": ai_config_json,
    "NIMBLE_LOG_PATH": str(Path.home() / ".nimble" / "nimble.log"),
},
```
Add `NIMBLE_SKILL_CONFIG` here. Do NOT replace existing keys.

**Current poll check in `runner.py::spawn_workers()` (lines 95–100):**
```python
if proc.poll() is not None:
    raise RuntimeError(
        f"Worker for skill {config.name!r} exited during startup "
        f"(exit code {proc.poll()!r})"
    )
self._registry.register(worker)
```
Replace this entire block: delete the poll check, read the startup handshake instead. Handle all failure cases gracefully (per-skill disable, continue) rather than raising.

### Startup Handshake Protocol

The new worker protocol has an explicit startup handshake as the FIRST line on stdout:

**Success:**
```json
{"invocation_id": "", "status": "ok", "error": null}
```

**Failure (on_load specifically):**
```json
{"invocation_id": "", "status": "error", "error": {"type": "ValueError", "message": "API key not set", "skill_file": "skills/my_skill/skill.py", "line": 12}, "phase": "on_load"}
```

**Failure (class init or tools build):**
```json
{"invocation_id": "", "status": "error", "error": {"type": "ImportError", "message": "...", "skill_file": "...", "line": 0}}
```
(No `"phase"` key — present only for `on_load` failures.)

The runner reads exactly one line from stdout after spawning. If this line is empty bytes (process died without writing), the skill is disabled with a generic message.

### `on_load` Config Object

`on_load(self, config)` receives a plain dict loaded from `NIMBLE_SKILL_CONFIG` env var:
```python
config = json.loads(os.environ.get("NIMBLE_SKILL_CONFIG", "{}"))
# Example: {"name": "my-skill", "source": "local", "binding": "ctrl+shift+d",
#            "path": "skills/my_skill/skill.py", "class_name": "MySkill"}
```
Load this in `worker/entrypoint.py` before the `run()` function (or at the top of `run()`). Pass it directly to `on_load`. If `NIMBLE_SKILL_CONFIG` is missing or invalid JSON, pass `{}` — do not raise.

### `on_error` Semantics

The skill's `on_error` is an enrichment hook, not a recovery hook. It can:
- Append context to `exc.args` (hacky but works)
- Log additional info
- Simply ignore the exception (return None/nothing)

The returned value from `on_error` is ignored. Whatever exception is active after `on_error` (the original `exc`) is what gets serialised. If `on_error` raises, catch it, log at WARNING, and serialise the original `exc`.

```python
# In the IPC loop except block:
if hasattr(skill, "on_error"):
    try:
        skill.on_error(exc)
    except Exception:
        logger.warning("on_error raised in skill %s", config.name, exc_info=True)
response = {
    "invocation_id": invocation_id,
    "status": "error",
    "error": _extract_error(exc),  # still the original exc
}
```

But `_extract_error` needs access to the exception object. Since `on_error` doesn't return anything that replaces `exc`, the error dict is always built from the original `exc`. This is intentional — the notification message format is the daemon's concern, not the skill's.

### `on_unload` Semantics

Called after `for line in sys.stdin:` loop exits (stdin EOF = daemon shutdown). Worker is about to exit. Exceptions from `on_unload` are caught and logged at WARNING — never propagated (the process is exiting anyway).

```python
# After the IPC loop:
if hasattr(skill, "on_unload"):
    try:
        skill.on_unload()
    except Exception:
        logger.warning("on_unload raised in skill", exc_info=True)
```

### Notification Messages

The runner must fire these exact notification messages via `self._notifier.send()`:

| Case | Title | Body |
|------|-------|-------|
| `on_load` failure | `f"Nimble — {config.name}"` | `f"on_load failed: {error_message}. Skill disabled until restart."` |
| Class init / tools build failure | `f"Nimble — {config.name}"` | `f"failed to load: {error_message}. Skill disabled until restart."` |
| No output from worker (crashed) | `f"Nimble — {config.name}"` | `"failed to start. Skill disabled until restart."` |

### Registering Failed Workers

When a worker fails to start, the skill must still be registered in the registry with `status="failed"` (not registered at all or left as "unknown"). This ensures `check_for_dead_workers()` can skip already-failed workers (existing logic).

Use the pattern:
```python
worker = SkillWorker(
    config=config,
    process=proc,
    status="failed",
    python_executable=python_executable,
)
self._registry.register(worker)
```

### Architecture Compliance

- `on_load`, `on_error`, `on_unload` are optional — detected with `hasattr`. Never require skills to implement them.
- All three hooks run inside the worker subprocess — never in the daemon process.
- `on_unload` is NOT called when `check_for_dead_workers()` kills a zombie — only when stdin closes gracefully. (Workers that die unexpectedly have no opportunity to run `on_unload`.)
- `mypy --strict` enforced — annotate all new parameters and return types. Use `object` for the `config` dict type passed to `on_load` if needed, or `dict[str, object]`.
- Absolute imports only. No relative imports.

### Test Strategy

**Entrypoint tests** — follow the existing `_run_with_lines` helper pattern. For new lifecycle hook tests:
- Create fake skill classes with lifecycle methods that record calls (set attributes on `self`).
- For `test_success_handshake_written_before_ipc_loop`, run with one invocation line; the FIRST output line is the handshake (check it), the SECOND is the invocation response.
- For `test_on_load_failure_writes_error_response`, run with stdin having invocation lines; verify only ONE output line (the error) and the invocation lines are never processed.

**Runner tests** — use `_make_fake_proc` pattern already established. For startup handshake tests:
- Mock `proc.stdout.readline.return_value` to return the handshake JSON + `\n` encoded.
- For on_load failure: return an error response with `phase: "on_load"`, set `proc.poll.return_value = 0` (exited cleanly after writing error).

### File List to Touch

- `worker/entrypoint.py` — add on_load/on_error/on_unload; add success handshake; add NIMBLE_SKILL_CONFIG loading
- `nimble/skills/runner.py` — add NIMBLE_SKILL_CONFIG env var; replace poll-check with handshake read; handle startup failures gracefully
- `tests/unit/worker/test_entrypoint.py` — add 6 new lifecycle hook tests
- `tests/unit/skills/test_runner.py` — add 4 new handshake/startup tests

### Baseline (Before This Story)

```
Tests: 158 collected (2 collection errors in test_daemon.py and test_watcher.py — pre-existing, due to missing watchdog in test env)
mypy: 3 pre-existing errors in test_platform.py — unchanged
black: clean
flake8: clean
```

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 4.3] — acceptance criteria, FR9, FR36
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Worker lifecycle] — worker is the isolation boundary, hooks run in worker
- [Source: worker/entrypoint.py#run] — current startup flow and IPC loop to extend
- [Source: nimble/skills/runner.py#spawn_workers] — poll check to replace with handshake read
- [Source: docs/bmad_output/implementation-artifacts/4-2-persistent-log-file.md#Dev Notes] — NIMBLE_LOG_PATH pattern for env var passing (same pattern for NIMBLE_SKILL_CONFIG)
- [Source: docs/bmad_output/implementation-artifacts/4-1-per-skill-exception-isolation-and-error-notifications.md] — existing notification format and error serialisation patterns

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Fixed `tests/unit/skills/test_loader.py` — raw MagicMock proc lacked `readline` setup; added ok handshake response to match the new startup handshake protocol.
- Updated 3 existing entrypoint tests (`test_happy_path_produces_ok_response`, `test_error_path_produces_error_response`, `test_worker_survives_error_and_processes_next`) to account for the new success handshake as the first stdout line.

### Completion Notes List

- Added `logger = logging.getLogger(__name__)` to `worker/entrypoint.py`.
- `run()` now loads `NIMBLE_SKILL_CONFIG` from env (fallback `{}`), calls `on_load(skill_config)` after tools build, emits the startup handshake (`{"invocation_id": "", "status": "ok", "error": null}`) on success, calls `on_error(exc)` in the IPC loop exception handler, and calls `on_unload()` after stdin closes.
- `on_load` failure writes `{"phase": "on_load"}` error and returns without entering the IPC loop.
- `runner.py` `spawn_workers` now passes `NIMBLE_SKILL_CONFIG` env var and reads the startup handshake instead of the old poll-check. Per-skill startup failures (empty output, on_load error, class init / tools error) register the worker as `status="failed"`, fire a typed notification, and `continue` — daemon processes all other skills normally. `subprocess.Popen` failures still propagate and trigger cleanup of already-started workers.
- 10 new tests added (6 entrypoint lifecycle, 4 runner handshake). Total: 168 (was 158).

### File List

- `worker/entrypoint.py`
- `nimble/skills/runner.py`
- `tests/unit/worker/test_entrypoint.py`
- `tests/unit/skills/test_runner.py`
- `tests/unit/skills/test_loader.py`

## Change Log

- 2026-04-26: Story created from sprint-status backlog auto-discovery (Epic 4, story 3)
- 2026-04-26: Implemented skill lifecycle hooks (on_load, on_error, on_unload) and startup handshake protocol

### Review Findings

- [x] [Review][Patch] Worker startup can block indefinitely on handshake read [nimble/skills/runner.py]
- [x] [Review][Patch] Failed-start workers are registered but not explicitly terminated/reaped [nimble/skills/runner.py]
- [x] [Review][Patch] `on_load` config contract allows non-dict JSON payloads [worker/entrypoint.py]
