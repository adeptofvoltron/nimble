# Story 4.1: Per-Skill Exception Isolation and Error Notifications

Status: done

## Story

As a user,
I want skill failures to surface as clear system notifications without stopping the daemon,
so that one broken skill never takes down my other running skills.

## Acceptance Criteria

1. **Given** a skill's `run()` method raises an unhandled exception
   **When** the worker sends an error response to the dispatcher
   **Then** the daemon fires a system notification with title `"Nimble — <skill-name>"` and body `"<ExceptionType>: <message> in <file> line <N>"` (FR33)
   **And** the daemon continues running all other skills normally (FR32)
   **And** the notification is delivered within 500ms of the exception being caught (NFR15)

2. **Given** a thread spawned inside `skill.run()` raises an unhandled exception
   **When** `threading.excepthook` catches it in the worker
   **Then** the error is serialised and sent to the daemon dispatcher, which fires the same notification format (FR35)

3. **Given** `nimble/notifier.py` implements cross-platform notification dispatch
   **When** `notifier.send(title, body)` is called on Linux
   **Then** it uses plyer/libnotify — no third-party notification dep beyond plyer (NFR17)

4. **When** `notifier.send(title, body)` is called on Windows
   **Then** it uses the Win32 notification mechanism via plyer (NFR17)

## Tasks / Subtasks

- [x] Task 1: Add `_dispatch` error notification tests to `tests/unit/test_daemon.py` (AC: 1, 2)
  - [x] Import `SkillError`, `DispatchResult` from `nimble.skills.runner`
  - [x] `test_dispatch_fires_notification_on_skill_error()` — mock `build_context` + `runner.dispatch` returning error DispatchResult; assert `notifier.sent` has one entry
  - [x] `test_dispatch_notification_title_and_body_format()` — assert exact title `"Nimble — my-skill"` and body `"ValueError: oops in skills/foo.py line 42"`
  - [x] `test_dispatch_no_notification_on_success()` — mock runner returning ok DispatchResult; assert `notifier.sent` is empty
  - [x] `test_dispatch_logs_error_on_skill_failure()` — patch `nimble.daemon.logger`; assert `logger.error` called once after error dispatch
  - [x] `test_dispatch_thread_exception_fires_same_notification_format()` — identical to AC1 test but constructed via the same DispatchResult shape produced by `_thread_excepthook`; confirms AC2 path

- [x] Task 2: Verify quality gates (AC: all)
  - [x] `python3 -m pytest` — all existing tests still pass; new tests pass
  - [x] `mypy nimble/ tests/ worker/` — exits 0 on changed files (7 pre-existing errors in test_platform.py, watcher.py, manifest/parser.py, tools/ai.py unchanged)
  - [x] `black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

## Dev Notes

### What Is Already Implemented (Do NOT Reinvent)

All production code for this story is **already in place from earlier stories**. This story's job is test coverage.

**The complete error notification pipeline — existing files, no changes needed:**

```
skill raises exception
  → worker/entrypoint.py catches, serialises to {"status": "error", "error": {...}}
  → nimble/skills/runner.py::SkillRunner.dispatch() returns DispatchResult(status="error", error=SkillError(...))
  → nimble/daemon.py::_dispatch() detects error, calls notifier.send(title, body)
  → nimble/notifier.py::Notifier.send() forwards to plyer.notification.notify()
```

**Thread exception path — also already implemented:**
- `worker/entrypoint.py` sets `threading.excepthook = _thread_excepthook` at module level
- `_thread_excepthook` serialises the exception to the same `{"status": "error", "error": {...}}` JSON format on stdout
- The daemon dispatcher reads it identically — same code path, same notification

### Existing Implementations to Reference (Do NOT Duplicate)

**`nimble/daemon.py::_dispatch()`** — the function under test:
```python
def _dispatch(skill_name: str, runner: SkillRunner, notifier: Notifier) -> None:
    context = build_context()
    result = runner.dispatch(skill_name, context)
    if result.status == "error" and result.error is not None:
        error = result.error
        notifier.send(
            title=f"Nimble — {skill_name}",
            body=(
                f"{error.type}: {error.message}"
                f" in {error.skill_file} line {error.line}"
            ),
        )
        logger.error(
            "Skill %s dispatch error: %s: %s in %s line %d",
            skill_name, error.type, error.message, error.skill_file, error.line,
        )
```

**`nimble/notifier.py::Notifier`** — uses plyer with lazy import, swallows exceptions:
```python
class Notifier:
    def send(self, title: str, body: str) -> None:
        try:
            from plyer import notification
            notification.notify(title=title, message=body, app_name="Nimble")
        except Exception:
            logger.warning("Notifier failed to send notification", exc_info=True)
```

**`tests/conftest.py::FakeNotifier`** — already defined, use it (subclasses `Notifier` for type checking):
```python
from nimble.notifier import Notifier

class FakeNotifier(Notifier):
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, title: str, body: str) -> None:
        self.sent.append((title, body))
```

**`nimble/skills/runner.py`** — `SkillError` and `DispatchResult` dataclasses already defined here. Import from this module, do NOT redefine.

### Test Pattern for `test_daemon.py`

The existing `test_daemon.py` imports `import nimble.daemon as daemon_module` — follow this pattern to call `daemon_module._dispatch(...)` directly.

**Pattern for all `_dispatch` tests:**
```python
from unittest.mock import MagicMock, patch
import nimble.daemon as daemon_module
from nimble.skills.runner import DispatchResult, SkillError
from tests.conftest import FakeNotifier

def test_dispatch_fires_notification_on_skill_error() -> None:
    notifier = FakeNotifier()
    error = SkillError(type="ValueError", message="oops", skill_file="skills/foo.py", line=42)
    dispatch_result = DispatchResult(invocation_id="x", status="error", error=error)
    mock_runner = MagicMock()
    mock_runner.dispatch.return_value = dispatch_result

    with patch("nimble.daemon.build_context", return_value={}):
        daemon_module._dispatch("my-skill", mock_runner, notifier)

    assert len(notifier.sent) == 1
    title, body = notifier.sent[0]
    assert title == "Nimble — my-skill"
    assert body == "ValueError: oops in skills/foo.py line 42"
```

**For `test_dispatch_no_notification_on_success`:** Use `DispatchResult(invocation_id="x", status="ok")` (no `error` field needed — it defaults to `None`).

**For `test_dispatch_logs_error_on_skill_failure`:** Patch `nimble.daemon.logger` and assert `logger.error.assert_called_once()`.

**For `test_dispatch_thread_exception_fires_same_notification_format`:** Construct a `DispatchResult` with a `SkillError` matching what `_thread_excepthook` would produce (type, message, skill_file, line all strings/int). Assert the same notification format fires — proving AC2 at the daemon level.

### Why 500ms (NFR15) Is Satisfied by Design

`_dispatch()` runs in a per-invocation daemon thread (`daemon.py::_make_callback` spawns `threading.Thread(target=_dispatch, ...)`). The notification fires synchronously within that thread immediately after `runner.dispatch()` returns the error JSON. No queue, no batch, no delay. NFR15 is structurally guaranteed.

### Known Deferred Issues (Do NOT Address in This Story)

From `docs/bmad_output/implementation-artifacts/deferred-work.md`:
- **Hung skill timeout**: `runner.py::dispatch()` calls `stdout.readline()` which blocks indefinitely if a skill hangs. No timeout mechanism exists yet. Deferred to a later Epic 4 story.
- **BrokenPipeError on flush**: `stdout.flush()` in the worker is not caught. Deferred to reliability work.
- **No periodic dead-worker health check**: `check_for_dead_workers()` exists in `runner.py` but is not called on a timer from `daemon.py`'s main loop — dead workers are only detected at dispatch time. Not an AC for this story; deferred to Epic 5 state monitoring work.

### Architecture Compliance

- `nimble/notifier.py` placement: correct per architecture (cross-cutting concern, top-level under `nimble/`)
- Tests in `tests/unit/test_daemon.py`: correct location (mirrors `nimble/daemon.py`)
- `mypy --strict` throughout — `SkillError`, `DispatchResult` are `@dataclass` (not plain dicts)
- Absolute imports only: `from nimble.skills.runner import SkillError, DispatchResult`
- `FakeNotifier` from `tests.conftest` — do not re-define

### Current Baseline (Before This Story)

```
Tests: 153 passed (from Story 3.5)
mypy: 7 pre-existing errors (test_platform.py, watcher.py, manifest/parser.py, tools/ai.py) — unchanged
```

### Project Structure Notes

- `tests/unit/test_daemon.py` — add new tests here; existing 2 tests (`test_startup_notification_fires`, `test_startup_notification_title_and_body`) must continue to pass
- No new files needed
- No changes to production code

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 4.1] — acceptance criteria, FR32, FR33, FR35
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Error Handling Patterns] — `notifier.send()` call pattern in dispatcher
- [Source: nimble/daemon.py#_dispatch] — the function under test
- [Source: nimble/notifier.py] — Notifier implementation
- [Source: nimble/skills/runner.py] — SkillError, DispatchResult dataclasses
- [Source: worker/entrypoint.py#_thread_excepthook] — thread exception serialization (AC2 worker side)
- [Source: tests/unit/worker/test_entrypoint.py#test_thread_excepthook_serialises_to_stdout] — existing thread excepthook test to reference

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added 5 tests to `tests/unit/test_daemon.py` covering the `_dispatch()` error notification path (AC1, AC2).
- Made `FakeNotifier` extend `Notifier` in `tests/conftest.py` to satisfy mypy structural typing (resolved 5 new mypy errors).
- All 165 tests pass; mypy has only 3 pre-existing errors in `test_platform.py`; black and flake8 clean.
- No production code was modified.

### File List

- tests/unit/test_daemon.py (modified)
- tests/conftest.py (modified)

### Change Log

- 2026-04-26: Added 5 `_dispatch` error notification tests; made FakeNotifier a subclass of Notifier for mypy compliance.

### Review Findings

- [x] [Review][Patch] Sync FakeNotifier documentation snippet with `tests/conftest.py` — fixed during review (Dev Notes code block now shows `FakeNotifier(Notifier)`).

- [x] [Review][Defer] `_dispatch` if `status == "error"` but `result.error is None` — no notification and no `logger.error`; ambiguous if runner mis-serializes. [`nimble/daemon.py:152`] — deferred, pre-existing / not introduced by this change.
