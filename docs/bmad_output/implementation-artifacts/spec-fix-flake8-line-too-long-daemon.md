---
title: 'Fix flake8 E501 line-too-long in daemon._state_signature'
type: 'chore'
created: '2026-05-01'
status: 'done'
route: 'one-shot'
---

## Intent

**Problem:** `nimble/daemon.py:42` exceeded the project's 88-character line limit, causing `flake8` to fail with E501.

**Approach:** Split the function signature of `_state_signature` across multiple lines using a trailing comma; confirmed Black and mypy still pass.

## Suggested Review Order

- [`nimble/daemon.py:42`](../../nimble/daemon.py) — signature split (the only change)
