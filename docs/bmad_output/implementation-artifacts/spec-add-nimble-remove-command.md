---
title: 'Add nimble remove command'
type: 'feature'
created: '2026-05-07'
status: 'done'
baseline_commit: '8634d55e93f04aa3ef305e7a09b2efff98ce6ba6'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no way to uninstall a skill installed via `nimble add` — users must manually edit `config.yaml`, delete the `.nimble/skills/<name>/` directory, and remove the lock entry.

**Approach:** Add a `nimble remove <skill-name>` CLI command that removes the config entry, lock entry, and skill directory in a single step after a `y/N` confirmation prompt.

## Boundaries & Constraints

**Always:**
- Require `y/Y` confirmation before any state is modified.
- Remove the skill entry from `config.yaml` first; abort with exit 1 on failure.
- Remove the lock entry from `manifest.lock` after config update — warn on `OSError`, do not abort.
- Delete `.nimble/skills/<skill-name>/` after config update — warn if absent, do not abort.
- Print a restart hint if the daemon is running at removal time.

**Ask First:** None — the operation is clear enough to proceed without mid-task human decisions.

**Never:**
- Add a `--yes`/`--force` flag — explicit confirmation is intentional UX.
- Stop the daemon before removing — let the user decide when to restart.
- Fail the removal if the skill directory or lock entry is absent (may have been cleaned up manually).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | skill in config + lock + dir; user enters `y` | config entry removed, lock entry removed, dir deleted, "Skill 'name' removed." | N/A |
| Confirmation declined | user enters `n` or empty | "Removal cancelled.", exit 0, no state changed | N/A |
| Skill not in config | no matching entry in config.yaml | "Skill 'name' not found in config.yaml", exit 1 | ConfigError propagated |
| Dir missing | config entry present, dir absent | config + lock updated, warn "Skill directory not found — skipping.", exit 0 | warn only |
| Lock entry missing | config entry present, no lock entry for name | config updated, no warning needed (silent no-op), exit 0 | silent |
| Daemon running | removal succeeds while daemon is running | success + "Nimble is running — restart with 'nimble restart' to apply changes." | N/A |

</frozen-after-approval>

## Code Map

- `nimble/manifest/lock.py` — add `remove_lock_entry(lock_path, skill_name)` here; `read_lock` / `write_lock_entry` already present
- `nimble/manifest/parser.py:277` — existing `remove_skill_entry_from_config` (rollback helper, "Rollback failed:" prefix); add new `remove_skill_from_config` with user-friendly messages
- `nimble/cli/commands.py` — all CLI commands live here; `state`, `_repo_root`, `_do_stop` already imported
- `tests/unit/manifest/test_lock.py` — existing lock tests use `read_lock` / `write_lock_entry`; append tests for `remove_lock_entry`
- `tests/unit/cli/test_commands.py` — existing CLI tests; append tests for `remove`

## Tasks & Acceptance

**Execution:**
- [x] `nimble/manifest/lock.py` -- add `remove_lock_entry(lock_path: Path, skill_name: str) -> None` -- reads the lock, removes the named key if present (silently no-ops if absent or file missing), rewrites atomically via `atomic_write`
- [x] `nimble/manifest/parser.py` -- add `remove_skill_from_config(config_path: Path, skill_name: str) -> None` -- iterates the `skills` list, deletes all entries whose `name` matches, rewrites atomically; raises `ConfigError(f"Skill {skill_name!r} not found in config.yaml")` if none found
- [x] `nimble/cli/commands.py` -- add `remove` Typer command: prompt `y/N`, call `remove_skill_from_config` (exit 1 on `ConfigError`), call `remove_lock_entry` (warn on `OSError`), `shutil.rmtree` the skill dir (warn if absent), print success, print restart hint if daemon running
- [x] `tests/unit/manifest/test_lock.py` -- add tests: existing key removed and file updated; missing key is a no-op; missing lock file is a no-op
- [x] `tests/unit/cli/test_commands.py` -- add tests: happy path removes all three; confirmation declined leaves state unchanged; skill absent from config exits 1; dir absent still succeeds; daemon running shows restart hint

**Acceptance Criteria:**
- Given a skill exists in config, lock, and dir, when `nimble remove <name>` is confirmed with `y`, then the config entry is removed, the lock entry is removed, the skill dir is deleted, "Skill '<name>' removed." is printed, and the process exits 0.
- Given the user enters `n` at the prompt, when `nimble remove <name>` is run, then nothing is modified, "Removal cancelled." is printed, and the process exits 0.
- Given the skill has no entry in config.yaml, when `nimble remove <name>` is confirmed, then "Skill '<name>' not found in config.yaml" is printed on stderr and the process exits 1.
- Given the skill directory is absent, when `nimble remove <name>` is confirmed, then config and lock are still updated, a warning about the missing dir is printed, and the process exits 0.
- Given the daemon is running when removal succeeds, then "Nimble is running — restart with 'nimble restart' to apply changes." is printed.

## Verification

**Commands:**
- `pytest tests/unit/manifest/test_lock.py tests/unit/cli/test_commands.py -q` -- expected: all new tests pass, zero regressions
- `flake8 nimble/manifest/lock.py nimble/manifest/parser.py nimble/cli/commands.py` -- expected: exit 0
- `mypy nimble/manifest/lock.py nimble/manifest/parser.py nimble/cli/commands.py` -- expected: no errors

## Suggested Review Order

**Uninstall operation flow**

- Entry point: command signature and y/N confirmation gate before any state changes
  [`commands.py:474`](../../../nimble/cli/commands.py#L474)

- Ordered teardown: config first (abort on failure), then lock and dir (warn-only)
  [`commands.py:497`](../../../nimble/cli/commands.py#L497)

- Directory deletion with OSError guard; dir-absent is warn-not-abort
  [`commands.py:510`](../../../nimble/cli/commands.py#L510)

- Daemon-running hint appended only after all mutations succeed
  [`commands.py:522`](../../../nimble/cli/commands.py#L522)

**Config mutation**

- New user-facing function: removes all matches; contrast with rollback helper's last-match
  [`parser.py:307`](../../../nimble/manifest/parser.py#L307)

**Lock mutation**

- Idempotent removal: early-return on absent key avoids a needless atomic write
  [`lock.py:38`](../../../nimble/manifest/lock.py#L38)

**Tests**

- Happy path verifies skill directory is actually deleted, not just output text
  [`test_commands.py:759`](../../../tests/unit/cli/test_commands.py#L759)

- Lock unit tests: key removed, missing key no-op, missing file no-op
  [`test_lock.py:63`](../../../tests/unit/manifest/test_lock.py#L63)
