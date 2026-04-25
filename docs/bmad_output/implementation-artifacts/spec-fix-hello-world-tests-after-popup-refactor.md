---
title: 'Fix hello_world tests after popup refactor'
type: 'bugfix'
created: '2026-04-25'
status: 'done'
route: 'one-shot'
---

# Fix hello_world tests after popup refactor

## Intent

**Problem:** Two tests in `test_hello_world.py` passed `None` as `tools` and patched `plyer.notification.notify` directly — both assumptions broke when the skill stopped calling plyer and started delegating to `tools.popup.show()`, causing `AttributeError: 'NoneType' object has no attribute 'popup'` in CI.

**Approach:** Replace `None` with a `MagicMock()` for `tools`, assert on `tools.popup.show()` instead of plyer internals, and remove the exception-swallowing test whose concern now belongs to `PopupTool`.

## Suggested Review Order

- The only changed test: mock tools properly, assert on the popup tool call.
  [`test_hello_world.py:22`](../../../tests/unit/skills/test_hello_world.py#L22)
