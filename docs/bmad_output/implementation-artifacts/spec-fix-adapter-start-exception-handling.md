---
title: 'Fix: adapter.start() failures beyond RuntimeError now caught, logged, and reported'
type: 'bugfix'
created: '2026-05-10'
status: 'done'
route: 'one-shot'
context: []
---

## Intent

**Problem:** `daemon.py` only caught `RuntimeError` from `adapter.start()`. Both hotkey adapters do a lazy `from pynput import keyboard` inside `start()` — if pynput is missing this raises `ImportError`, which propagated uncaught, crashing the daemon with a raw traceback and no user notification. Additionally, no call to `logger.error()` meant adapter startup failures left no trace in the log file.

**Approach:** Split the handler into an explicit `(RuntimeError, ImportError)` branch (known, expected failures) and a broad `except Exception` fallback that prefixes the exception type name and uses `logger.exception()` for unexpected failures. PID file is never written on any failure path (confirmed by new test assertions).

## Suggested Review Order

1. [`nimble/daemon.py:87-98`](../../nimble/daemon.py) — the split exception handler with logging
2. [`tests/unit/test_daemon.py`](../../tests/unit/test_daemon.py) — two new ImportError tests + `write_pid.assert_not_called()` added to both RuntimeError and ImportError exit tests
