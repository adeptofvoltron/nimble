---
title: 'Fix community skill worker loading'
type: 'bugfix'
created: '2026-05-04'
status: 'done'
context: []
baseline_commit: 'b45a2afc5fc070307cb770e0dbb94e5486cea572'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Community skills always show `[FAILED]` in `nimble status` because `spawn_workers` launches their worker subprocess with the community venv's isolated Python, which (a) lives at the wrong path (`~/.nimble/` instead of `{repo_root}/.nimble/`) causing `FileNotFoundError`, and (b) even with the correct path, lacks `pyyaml` and other nimble deps that `entrypoint.py` imports at module level — so the worker exits before sending its handshake.

**Approach:** Always launch worker subprocesses with the main nimble Python (`sys.executable`), which already has all nimble deps. Pass the community skill's venv path as a new `NIMBLE_VENV_PATH` env var so `entrypoint.py` can prepend its `site-packages` to `sys.path` before nimble is imported, making skill-specific deps available.

## Boundaries & Constraints

**Always:**
- All workers (local and community) use `sys.executable` — the same Python that runs the daemon
- Community venv `site-packages` are injected via `sys.path` in `entrypoint.py`, before any nimble imports
- Existing IPC protocol (handshake, stdin/stdout JSON) unchanged
- All 308 existing tests must continue to pass

**Ask First:**
- If community venv's `site-packages` glob finds zero matches (venv missing or broken) — surface the error to the user rather than silently continuing

**Never:**
- Install nimble's own dependencies into community skill venvs
- Change the venv creation location in `installer.py`
- Modify the daemon start/stop flow

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Community skill, venv present | `source=community`, `.nimble/skills/<name>/.venv/` exists | Worker starts, handshake succeeds, status=`loaded` | — |
| Local skill | `source=local` | Worker uses `sys.executable`, no venv injection | — |
| Community venv missing | `NIMBLE_VENV_PATH` set but directory absent | `sys.path` unchanged (glob returns nothing), worker may fail on skill's own deps | Existing failed-handshake handling marks skill `failed`, logs error |
| `NIMBLE_VENV_PATH` empty/unset | Local skill or env var missing | No site-packages injection, proceeds normally | — |

</frozen-after-approval>

## Code Map

- `nimble/skills/runner.py` — `_get_python_executable` (currently returns community venv Python — must change to always return `sys.executable`); `spawn_workers` env dict (add `NIMBLE_VENV_PATH`)
- `worker/entrypoint.py` — module-level sys.path setup (lines 6–12); site-packages injection must go here, before line 35 (`from nimble.manifest.parser import AiConfig`)
- `tests/unit/skills/test_runner.py` — `test_spawn_workers_community_uses_venv_python` asserts the old venv-path behavior; must be replaced with assertions for `sys.executable` + `NIMBLE_VENV_PATH`

## Tasks & Acceptance

**Execution:**
- [x] `nimble/skills/runner.py` -- Replace `_get_python_executable` body: remove venv-path logic, always return `sys.executable`. Add `_get_community_venv_path(config, repo_root) -> str` that returns `str(repo_root / ".nimble" / "skills" / config.name / ".venv")` for community skills and `""` otherwise. In `spawn_workers` env dict, add `"NIMBLE_VENV_PATH": _get_community_venv_path(config, self._repo_root)`.
- [x] `worker/entrypoint.py` -- After the `_env_root` sys.path block (line 12) and before logging setup, add: read `NIMBLE_VENV_PATH`; if non-empty, glob `{venv_path}/lib/python*/site-packages` and `sys.path.insert(1, ...)` each match not already present.
- [x] `tests/unit/skills/test_runner.py` -- Replace `test_spawn_workers_community_uses_venv_python`: assert `cmd[0] == sys.executable` and that `kwargs["env"]["NIMBLE_VENV_PATH"]` contains `.nimble` and the skill name.

**Acceptance Criteria:**
- Given `nimble add` has installed a community skill, when `nimble start` is run, then `nimble status` shows the skill as `loaded` (not `failed`)
- Given a local skill, when daemon starts, then its worker still uses `sys.executable` (no change to local skill behavior)
- Given community venv is missing, when daemon starts, then skill is marked `failed` gracefully without crashing the daemon
- Given all tests run, then `python -m pytest tests/ -x -q` exits 0 with 308 passed

## Design Notes

The `entrypoint.py` already inserts `repo_root` into `sys.path` at lines 6–8 so nimble source is importable. The community venv's site-packages must be inserted **after** that (position 1, not 0) so nimble's own modules take priority over any conflicting packages the skill might bundle.

Example injection (after line 12) — globs both Linux/macOS and Windows layouts:

```python
_venv_path = os.environ.get("NIMBLE_VENV_PATH")
if _venv_path:
    import glob as _glob
    for _pat in [
        str(Path(_venv_path) / "lib" / "python*" / "site-packages"),  # Linux/macOS
        str(Path(_venv_path) / "Lib" / "site-packages"),               # Windows
    ]:
        for _sp in _glob.glob(_pat):
            if _sp not in sys.path:
                sys.path.insert(1, _sp)
```

## Spec Change Log

**Iteration 1 loopback — bad_spec: Windows venv path**
- Triggering finding: glob pattern `lib/python*/site-packages` (Linux-only) was missing `Lib/site-packages` (Windows). Old `_get_python_executable` branched on `is_windows()` explicitly; new implementation dropped that awareness.
- What was amended: Design Notes glob example updated to iterate both platform patterns. `is_windows` import removal added as a patch task.
- Known-bad state avoided: Community skills silently fail to inject deps on Windows because glob returns zero matches.
- KEEP: `sys.path.insert(1, sp)` position; `if _sp not in sys.path:` guard; `_get_community_venv_path` returning `""` for non-community skills.

## Verification

**Commands:**
- `python -m pytest tests/ -x -q` -- expected: 308 passed
- `nimble restart && nimble status` -- expected: translate shows `loaded`
- `.nimble/skills/translate/.venv/bin/python -c "import googletrans"` -- expected: no error (confirms skill dep still reachable via injected path)

## Suggested Review Order

**Core fix — Python executable and venv path routing**

- Entry point: `_get_python_executable` simplified + `_get_community_venv_path` added; this is why workers now load.
  [`runner.py:53`](../../../nimble/skills/runner.py#L53)

- Env dict: `NIMBLE_VENV_PATH` wired to the community venv — the channel from runner to entrypoint.
  [`runner.py:150`](../../../nimble/skills/runner.py#L150)

**Community venv injection — entrypoint sys.path setup**

- Platform-aware glob injects venv site-packages before any nimble imports; Linux + Windows both covered.
  [`entrypoint.py:14`](../../../worker/entrypoint.py#L14)

**Tests**

- Updated assertion: confirms `sys.executable` used and `NIMBLE_VENV_PATH` carries the right path.
  [`test_runner.py:66`](../../../tests/unit/skills/test_runner.py#L66)
