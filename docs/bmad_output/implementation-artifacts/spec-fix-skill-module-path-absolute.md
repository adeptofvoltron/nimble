---
title: 'Fix skill module path passed to worker as absolute'
type: 'bugfix'
created: '2026-05-04'
status: 'done'
route: 'one-shot'
---

# Fix skill module path passed to worker as absolute

## Intent

**Problem:** `runner.py` passes `config.path` (a relative path from `config.yaml`, e.g. `skills/hello_world/skill.py`) as a positional CLI argument to the worker entrypoint. `spec_from_file_location` in the entrypoint resolves it against the subprocess's CWD — not `repo_root` — so skills fail to load whenever `nimble` is not invoked from the repo directory.

**Approach:** Prepend `self._repo_root` in the `Popen` call: `str(self._repo_root / config.path)`. One-character change, consistent with how the entrypoint path is already resolved on the adjacent line.

## Suggested Review Order

- The single changed line: relative → absolute skill path in Popen args.
  [`runner.py:137`](../../../nimble/skills/runner.py#L137)
