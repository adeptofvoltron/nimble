---
title: 'Fix flake8 E501 in commands.py'
type: 'chore'
created: '2026-05-01'
status: 'done'
route: 'one-shot'
---

# Fix flake8 E501 in commands.py

## Intent

**Problem:** Two lines in `nimble/cli/commands.py` exceeded the project's 88-character limit, causing flake8 E501 failures.

**Approach:** Wrap the `_skill_columns` function signature and its call site in the `status` command to bring both within the 88-character limit.

## Suggested Review Order

1. [nimble/cli/commands.py:30-32](../../../nimble/cli/commands.py) — wrapped function signature
2. [nimble/cli/commands.py:258-262](../../../nimble/cli/commands.py) — wrapped call site in `status` command
