# Story 2.5: Worker Subprocess IPC Entrypoint

Status: ready-for-dev

## Story

As the daemon dispatcher,
I want a worker subprocess that receives a JSON context payload on stdin, executes the skill's `run()` method, and writes a JSON result to stdout,
So that skill execution is fully isolated from the daemon process and any skill exception cannot crash the daemon.

## Acceptance Criteria

1. **Given** `worker/entrypoint.py` is the worker subprocess script
   **When** it receives a valid JSON invocation on stdin: `{"invocation_id": "<uuid>", "context": {...}}`
   **Then** it reconstructs a `Context` object, calls `skill.run(context, tools)`, and writes `{"invocation_id": "<uuid>", "status": "ok", "error": null}` to stdout

2. **Given** `skill.run()` raises an unhandled exception
   **When** the worker catches it
   **Then** it writes `{"invocation_id": "<uuid>", "status": "error", "error": {"type": "...", "message": "...", "skill_file": "...", "line": N}}` to stdout
   **And** the worker process stays alive for the next invocation

3. **Given** `threading.excepthook` is set at worker startup
   **When** a thread spawned inside `skill.run()` raises an unhandled exception
   **Then** it is caught and serialised as an error response on stdout — not silently lost (FR35)

4. **Given** `worker/context.py` defines the `Context` class
   **When** a deprecated field name (e.g. `context.selected_text`) is accessed
   **Then** `AttributeError` is raised with a migration message — not a silent `KeyError` (FR11)

5. **Given** a community skill worker is spawned using the skill's isolated venv Python (which does not have `nimble` installed)
   **When** `worker/entrypoint.py` starts
   **Then** it inserts the repo root into `sys.path` before any other imports — using `Path(__file__).parent.parent` — so that `nimble.tools` and `nimble.context` are importable regardless of the active venv
   **And** the daemon also passes `NIMBLE_REPO_ROOT` as an environment variable to the worker as a fallback path resolution mechanism

## Tasks / Subtasks

- [ ] Task 1: Create `worker/context.py` — worker-side Context class (AC: 1, 4)
  - [ ] Define `Context` as a `@dataclass` with fields: `selection: str`, `clipboard: str`, `active_app: str`, `mouse_position: list[int]`
  - [ ] Implement `__getattr__` to raise `AttributeError` with a migration message for any field name not in the dataclass (e.g. `"Context has no field 'selected_text'. Did you mean 'selection'?"`)
  - [ ] Add `@classmethod from_dict(cls, data: dict[str, Any]) -> Context` that constructs a `Context` from the JSON-decoded invocation payload's `"context"` field
  - [ ] All fields required — no Optional, no defaults — a missing field is a hard error (broken IPC contract)
  - [ ] Annotate every parameter and return type (`mypy --strict`)

- [ ] Task 2: Create `worker/entrypoint.py` — IPC loop (AC: 1, 2, 3, 5)
  - [ ] First two lines (before any other imports): insert repo root into `sys.path` via `Path(__file__).parent.parent`, then check `NIMBLE_REPO_ROOT` env var as fallback
  - [ ] Set `threading.excepthook` immediately at module startup (before entering the IPC loop) to serialise thread exceptions as error responses on stdout
  - [ ] Accept skill module path and skill class name as CLI arguments (argv[1], argv[2])
  - [ ] Dynamically import the skill class from the given path using `importlib`
  - [ ] Instantiate the skill class once; enter the IPC loop (read stdin line by line)
  - [ ] Each line: `json.loads()` → extract `invocation_id` + `context` dict → `Context.from_dict(context)` → `skill.run(context, tools)` → write `{"invocation_id": ..., "status": "ok", "error": null}\n` to stdout
  - [ ] On any exception from `skill.run()`: extract `type`, `message`, `skill_file`, `line` from `traceback`; write error JSON to stdout; flush; continue loop (worker stays alive)
  - [ ] Every stdout write must call `sys.stdout.flush()` immediately after — daemon reads are blocking
  - [ ] Pass a stub `ToolRegistry` (or `None`) as `tools` for now — full tool primitives are Story 3.x; worker must not crash if skill ignores `tools`
  - [ ] Use `sys.stderr` for internal worker logs — never write non-JSON to stdout (would break the IPC framing)

- [ ] Task 3: Create `tests/unit/worker/test_context.py` (AC: 1, 4)
  - [ ] Create `tests/unit/worker/__init__.py` — empty, mirrors source structure
  - [ ] Test `Context.from_dict()` with a fully valid payload → all fields set correctly
  - [ ] Test `Context.from_dict()` with `mouse_position` as `[1920, 1080]` → `list[int]` not modified
  - [ ] Test accessing `context.selection` → returns the value
  - [ ] Test accessing `context.selected_text` (deprecated alias) → raises `AttributeError` with a migration message string
  - [ ] Test accessing `context.unknown_field` → raises `AttributeError` with a migration message string

- [ ] Task 4: Create `tests/unit/worker/test_entrypoint.py` (AC: 1, 2, 3, 5)
  - [ ] Test happy path: valid JSON line on stdin → worker calls `skill.run()` → stdout line is valid JSON with `status: "ok"` and correct `invocation_id`
  - [ ] Test error path: `skill.run()` raises `KeyError("missing_key")` → stdout contains `status: "error"`, `error.type == "KeyError"`, `error.message` non-empty, `invocation_id` echoed
  - [ ] Test worker survives error: after one error response, worker processes the next valid invocation correctly
  - [ ] Test `sys.path` injection: verify repo root is in `sys.path` after worker initialisation (can inspect `sys.path[0]` or patch `Path.parent.parent`)
  - [ ] Mock `skill.run()` — never execute real skill code in unit tests
  - [ ] Thread exception test: spawn a thread that raises inside a fake `skill.run()` → verify `threading.excepthook` serialises it to stdout as an error response

- [ ] Task 5: Verify quality gates
  - [ ] `mypy nimble/ tests/ worker/` — exits 0
  - [ ] `pytest` — all tests pass (existing 31 + new worker tests = target ≥ 40)
  - [ ] `black --check nimble/ tests/ worker/` — exits 0
  - [ ] `flake8 nimble/ tests/ worker/` — exits 0

## Dev Notes

### Role in the Daemon Architecture

This story creates the worker subprocess that Story 2.6 (`nimble/skills/runner.py`) will spawn. The dispatch flow is:

```
pynput hotkey event
  → daemon dispatches to runner.py (Story 2.6)
  → runner.py calls build_context()   ← Story 2.4 (DONE)
  → runner.py builds IPC payload: {"invocation_id": ..., "context": <result>}
  → runner.py writes payload to worker stdin
  → worker/entrypoint.py (THIS STORY) reads from stdin
  → worker reconstructs Context.from_dict(payload["context"])
  → worker calls skill.run(context, tools)
  → worker writes JSON result to stdout
  → runner.py reads result
```

`worker/entrypoint.py` is a **standalone script**, not a daemon module. It is spawned as a subprocess by `runner.py`. The `worker/` package must remain importable-independent: it cannot import from `nimble/` at the module level (it uses `sys.path` injection to reach `nimble.tools` at runtime).

### IPC Protocol — Hard Contract

The exact JSON schemas below are contractual between this worker (Story 2.5) and the dispatcher (Story 2.6). Any deviation causes silent failures.

**Daemon → Worker (stdin, one JSON line per invocation):**
```json
{
  "invocation_id": "uuid4-string",
  "context": {
    "selection": "selected text or empty string",
    "clipboard": "clipboard content",
    "active_app": "application name",
    "mouse_position": [x, y]
  }
}
```

**Worker → Daemon (stdout, success):**
```json
{"invocation_id": "uuid4-string", "status": "ok", "error": null}
```

**Worker → Daemon (stdout, error):**
```json
{
  "invocation_id": "uuid4-string",
  "status": "error",
  "error": {
    "type": "KeyError",
    "message": "human-readable message",
    "skill_file": "skills/log_diagnosis.py",
    "line": 14
  }
}
```

**Rules (from architecture.md §Worker IPC Protocol):**
- Every message is a single JSON line terminated by `\n` — no multi-line payloads
- `invocation_id` is always a UUID4 generated by the daemon; worker echoes it back unchanged
- `status` is always `"ok"` or `"error"` — no other values
- `mouse_position` in the context payload is always a 2-element array — never null
- `selection` and `clipboard` are always strings — never null

### Context Class Design (worker/context.py)

```python
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class Context:
    selection: str
    clipboard: str
    active_app: str
    mouse_position: list[int]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Context:
        return cls(
            selection=data["selection"],
            clipboard=data["clipboard"],
            active_app=data["active_app"],
            mouse_position=data["mouse_position"],
        )

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(
            f"Context has no field '{name}'. "
            f"Valid fields: selection, clipboard, active_app, mouse_position."
        )
```

The `__getattr__` is only called for attributes not found via normal lookup — the four dataclass fields are accessed normally; `__getattr__` only fires for unknown names. This is the FR11 deprecation mechanism.

### sys.path Injection — Must Be First Thing in entrypoint.py

```python
import sys
from pathlib import Path

# Must precede all nimble.* imports — community skill venvs don't have nimble installed
_repo_root = Path(__file__).parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
# Belt-and-suspenders: env var fallback from daemon
_env_root = os.environ.get("NIMBLE_REPO_ROOT")
if _env_root and _env_root not in sys.path:
    sys.path.insert(0, _env_root)
```

This MUST appear before `from nimble.tools import ...` — otherwise community skill workers (which run under a venv without `nimble` installed) will fail with `ModuleNotFoundError` on import.

### threading.excepthook Pattern

```python
import threading
import json
import sys

def _thread_excepthook(args: threading.ExceptHookArgs) -> None:
    import traceback
    tb = args.exc_traceback
    last_frame = traceback.extract_tb(tb)[-1] if tb else None
    response = {
        "invocation_id": _current_invocation_id,  # module-level var, set per invocation
        "status": "error",
        "error": {
            "type": type(args.exc_value).__name__,
            "message": str(args.exc_value),
            "skill_file": last_frame.filename if last_frame else "",
            "line": last_frame.lineno if last_frame else 0,
        },
    }
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()

threading.excepthook = _thread_excepthook
```

Set this ONCE at worker startup. The `_current_invocation_id` module-level variable is updated at the start of each invocation so threaded errors reference the correct invocation.

### Error Extraction from Exceptions

```python
import traceback

def _extract_error(exc: BaseException) -> dict[str, Any]:
    tb = exc.__traceback__
    last_frame = traceback.extract_tb(tb)[-1] if tb else None
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "skill_file": last_frame.filename if last_frame else "",
        "line": last_frame.lineno if last_frame else 0,
    }
```

### Tools Stub for This Story

Story 3.x implements full tool primitives. For Story 2.5, pass `None` as `tools` to `skill.run(context, tools)`. The `hello_world` skill used in Story 2.9 must not call `tools` methods — or accept `None` gracefully. Do NOT build a real `ToolRegistry` here; that is Story 3.1+.

### Skill Dynamic Import

```python
import importlib.util
import sys

def _load_skill_class(module_path: str, class_name: str) -> type:
    spec = importlib.util.spec_from_file_location("skill_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return getattr(module, class_name)  # type: ignore[no-any-return]
```

### worker/ Package Structure Note

`worker/__init__.py` already exists (empty). Do NOT move or modify it. The new files are additive:

```
worker/__init__.py              ← EXISTS (empty, do not touch)
worker/context.py               ← NEW
worker/entrypoint.py            ← NEW (executable script)
tests/unit/worker/__init__.py   ← NEW (empty)
tests/unit/worker/test_context.py     ← NEW
tests/unit/worker/test_entrypoint.py  ← NEW
```

### mypy --strict Compliance

- `entrypoint.py` uses `importlib.util` — add `# type: ignore[attr-defined]` only where mypy cannot resolve dynamic loader types; annotate everything else
- `_load_skill_class` return type is `type` — acceptable; the skill instance type is opaque at this layer
- `threading.ExceptHookArgs` is available from Python 3.8+ stdlib — no import guard needed

### Architecture Guardrails

| Rule | Reason |
|---|---|
| `sys.path` injection before ALL imports | Community venv Pythons don't have `nimble` installed |
| `threading.excepthook` set at startup | FR35 — thread exceptions must not be silently lost |
| Worker stays alive after error | FR32 — daemon must not restart for skill errors |
| Every stdout write followed by `flush()` | Daemon stdin reader is blocking — unflushed buffer = deadlock |
| Never write non-JSON to stdout | IPC framing — daemon expects exactly one JSON line per response |
| `invocation_id` always echoed back | Dispatcher correlates async responses by ID |
| `Context.from_dict` raises `KeyError` on missing field | IPC contract violation = hard error, not silent default |
| `__getattr__` raises `AttributeError` with message | FR11 — migration guidance, not silent `None` |

### Previous Story Patterns to Reuse

From Story 2.4:
- **Lazy import pattern:** Story 2.4 used lazy `from pynput import mouse` inside a function to avoid import-time failures in CI. Apply the same lazy import approach for any platform-specific imports in the worker.
- **`try/except Exception` guardrails:** Story 2.4 wrapped every OS call in broad exception handlers that return safe defaults. The worker IPC loop must similarly wrap `skill.run()` — never let an unhandled exception escape the loop.
- **Mock all external calls in tests:** Story 2.4 mocked subprocess and pynput at module level. For worker tests, mock `skill.run()` and `importlib` loading — never execute real skill code in unit tests.
- **`sys.platform` guards:** Not applicable here (worker is cross-platform by design), but the `sys.path` injection pattern follows the same "guard before using platform-specific path" spirit.

From Stories 2.2/2.3 (hotkey adapters):
- All CI tests passed by mocking OS APIs at the module level, not at the subprocess level. Follow the same approach for worker tests — mock at `worker.entrypoint` module scope.

### Cross-Story Context

- **Story 2.4** (`nimble/context/assembler.py`): `build_context()` returns exactly the shape that becomes the `"context"` field in the IPC payload. `Context.from_dict()` in this story reconstructs from that shape — field names MUST match: `selection`, `clipboard`, `active_app`, `mouse_position`.
- **Story 2.6** (`nimble/skills/runner.py`): Will spawn `worker/entrypoint.py` as a subprocess and write invocation payloads to its stdin. The runner expects `status: "ok"` or `status: "error"` — no other values.
- **Story 3.x** (`nimble/tools/`): Will replace the `None` tools stub with a real `ToolRegistry`. Worker entrypoint signature `skill.run(context, tools)` must be established here so Story 3.x only needs to inject the real tools object.
- **Story 4.3** (`on_load`, `on_error`, `on_unload` hooks): Will extend `entrypoint.py` to call lifecycle methods. Leave room in the IPC loop structure for pre-loop `on_load` call and post-error `on_error` call.

### Project Structure Notes

- `worker/` lives at **repo root** alongside `nimble/` and `tests/` — NOT inside the `nimble/` package. See architecture.md §Complete Project Directory Structure.
- `worker/entrypoint.py` is spawned as a **script** (`python worker/entrypoint.py <path> <class>`), not imported as a module. The `sys.path` injection pattern works because `__file__` resolves to the full path.
- `mypy` is configured to check `nimble/` and `tests/` via pyproject.toml. To include `worker/`, the CI command or pyproject.toml may need `worker/` added to the checked paths — verify and update if needed.

### References

- [Source: docs/bmad_output/planning-artifacts/architecture.md#Worker IPC Protocol] — exact JSON field names, types, and constraints
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Daemon Process Model] — sys.path injection rationale and pattern
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Per-Skill Venv Activation] — community skill venv Python, NIMBLE_REPO_ROOT env var
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Complete Project Directory Structure] — worker/ at repo root, not inside nimble/
- [Source: docs/bmad_output/planning-artifacts/architecture.md#All AI Agents MUST] — naming, imports, dataclasses, test structure
- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 2.5] — acceptance criteria
- [Source: docs/bmad_output/planning-artifacts/epics.md#NonFunctional Requirements] — NFR11 (isolation), NFR13 (no silent failures)
- [Source: docs/bmad_output/implementation-artifacts/2-4-context-snapshot-assembler.md#IPC Contract] — exact return shape that Context.from_dict must accept
- [Source: docs/bmad_output/implementation-artifacts/2-4-context-snapshot-assembler.md#Dev Notes] — lazy import pattern, mock-all-OS-calls test approach

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List
