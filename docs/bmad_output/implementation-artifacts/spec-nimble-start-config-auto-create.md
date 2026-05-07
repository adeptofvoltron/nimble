---
title: 'nimble start: auto-create config.yaml when missing'
type: 'chore'
created: '2026-05-07'
status: 'done'
route: 'one-shot'
---

## Intent

**Problem:** `nimble start` (and `nimble restart`) crash with a raw Python traceback when `config.yaml` doesn't exist, because `load_config` doesn't handle `FileNotFoundError`.

**Approach:** Bootstrap an empty `config.yaml` in `_do_start` before launching the daemon subprocess, with a user-visible notice and a clean error if the write fails.

## Suggested Review Order

1. [`nimble/cli/commands.py`](../../../../nimble/cli/commands.py) — `_do_start`: config bootstrap block (covers both `start` and `restart`)
