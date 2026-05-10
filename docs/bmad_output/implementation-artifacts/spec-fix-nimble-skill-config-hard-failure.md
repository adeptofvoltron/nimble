---
title: 'Fix: NIMBLE_SKILL_CONFIG parse failure reports error instead of silently defaulting'
type: 'bugfix'
created: '2026-05-10'
status: 'done'
route: 'one-shot'
context: []
---

## Intent

**Problem:** When `NIMBLE_SKILL_CONFIG` contains malformed JSON, `worker/entrypoint.py` silently catches the parse exception and proceeds with an empty config dict. The skill loads and runs with wrong/missing configuration, producing confusing silent misbehaviour with no error trace anywhere.

**Approach:** Replace the bare `except: pass` with an explicit error response written to stdout (matching the existing startup error protocol), followed by `return`. The daemon already handles `"status": "error"` responses and marks the worker as failed.

## Suggested Review Order

1. [`worker/entrypoint.py:141-162`](../../worker/entrypoint.py) — the changed parsing block: before/after comparison
2. [`tests/unit/worker/test_entrypoint.py`](../../tests/unit/worker/test_entrypoint.py) — existing tests confirm non-dict JSON (`"[]"`) still silently defaults to `{}` (intentional contract preserved)
