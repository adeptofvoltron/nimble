# Deferred Work

## Deferred from: nimble start config auto-create (2026-05-07)

- `nimble/cli/commands.py:_repo_root()`: derives repo root from `Path(__file__).resolve().parent.parent.parent` (the installed package location), not from CWD or a git root. On a system-wide or pipx install, `config.yaml` is created inside the read-only package directory rather than the user's project. Pre-existing across all commands; resolve with a proper CWD-or-git-root detection strategy.

## Deferred from: config.yaml gitignore + auto-create (2026-05-07)

- `nimble/manifest/parser.py` + `nimble/manifest/lock.py`: rollback path (`remove_skill_entry_from_config`) does not delete `config.yaml` if it was created from scratch by `append_skill_to_config`; on `write_lock_entry` failure the rollback removes the skill entry but leaves an empty `config.yaml` behind. Fix: track whether the file was newly created and delete it on full rollback.
- `README.md` quick-start: does not mention copying `config.yaml.example` → `config.yaml` before running `nimble start`; `load_config` will raise an unhandled `FileNotFoundError` (not a `ConfigError`) producing a raw Python traceback. Fix: add setup step to README, and wrap the `open()` call in `load_config` with an `OSError` handler that raises a clean `ConfigError`.
- `.gitignore`: `.nimble` is listed twice — as `.nimble/*` (with `!.nimble/manifest.lock` negation) and again as a bare `.nimble` on the last line; the bare entry is redundant and could shadow the negation on some git versions. Remove the bare `.nimble` line in a cleanup pass.

## Deferred from: spec-fix-skill-module-path-absolute (2026-05-04)

- `nimble/skills/runner.py:137` + `nimble/skills/loader.py` (`validate_skill_paths`): both use `repo_root / config.path` without guarding against absolute paths or `..` traversal in `config.path`. Config is currently trusted, but worth hardening in a validation pass (e.g. assert path is relative and stays within repo_root after `.resolve()`).

## Deferred from: spec-fix-community-skill-worker-loading (2026-05-04)

- `worker/entrypoint.py` — glob-based venv injection may match multiple `python3.x` dirs on unusual shared venv layouts; import resolution order between them is non-deterministic. Extremely unlikely in practice; address in a venv-hardening pass if reported.
- `nimble/skills/runner.py` — community skill isolation now relies solely on `sys.path` injection rather than a venv-isolated Python binary; if `NIMBLE_VENV_PATH` is stripped or the entrypoint is bypassed, skill deps fall back to host Python silently. Acceptable trade-off for now; revisit if skill sandboxing becomes a security requirement.

## Deferred from: code review of 7-1-skill-build-md-ai-authoring-contract.md (2026-05-02)

- ~~`nimble/skills/installer.py` vs `nimble/skills/runner.py`: Community-skill venv path mismatch — **resolved by spec-fix-community-skill-worker-loading (2026-05-04)**~~
- `nimble/skills/runner.py`: `api_version` refusal logic only enforces version check when `type(skill_api_version) is int`; non-int values (e.g. floats truncated by parser, or other coercions) bypass the check. Pre-existing in runner; harden in a parser/runner reliability pass.
- `worker/entrypoint.py:198-201`: `on_error` exceptions are silently swallowed (`except Exception: logger.warning(...)`). Story 7.1 doc patch will reflect current behaviour (re-raise has no effect). If we want true re-raise / exception-replacement semantics, the runner needs a small redesign — capture for a future epic.

## Deferred from: code review of 5-3-nimble-disable.md (2026-05-01)

- `nimble/manifest/parser.py:50`: `disable_skill_in_config` disables only the first matching skill name; duplicate skill names are a pre-existing config integrity gap and make disable semantics ambiguous until uniqueness is enforced.

## Deferred from: code review of 4-2-persistent-log-file.md (2026-04-30)

- `worker/entrypoint.py:15-22`: Worker `FileHandler` opens without a `mkdir` guard — daemon always creates `~/.nimble/` first so this is safe in practice; add mkdir if worker ever runs standalone.
- `nimble/logging_setup.py:7` + `worker/entrypoint.py:18`: Log format string `"%(asctime)s %(levelname)s %(name)s: %(message)s"` is duplicated verbatim — export `_LOG_FORMAT` from `logging_setup.py` and import in worker in a future cleanup.
- `nimble/logging_setup.py:12-14`: No `encoding` argument on `RotatingFileHandler` — may corrupt non-ASCII characters on Windows/non-UTF-8 locales; address in a Windows hardening story.
- `tests/unit/worker/test_entrypoint.py:143`: `importlib.reload(entrypoint_mod)` is fragile for testing module-level init — only viable approach at present; revisit if module gains import-time state that isn't reload-safe.
- `tests/unit/test_daemon_logging.py:13-20`: `_restore_root_logger` fixture does not restore formatters/levels on pre-existing handlers, leaving subtle cross-test pollution potential.
- `nimble/logging_setup.py:12-14`: `log_path is directory` edge case (`IsADirectoryError`) is unguarded — extremely unlikely in practice.

## Deferred from: code review of 4-1-per-skill-exception-isolation-and-error-notifications.md (2026-04-26)

- `nimble/daemon.py:152`: If `DispatchResult.status == "error"` but `result.error is None`, `_dispatch` sends no notification and does not log — consider logging a fallback or tightening runner invariants; not introduced by story 4-1 tests.

## Deferred from: code review of 3-5-input-dialog-tool-primitives (2026-04-26)

- `nimble/tools/input.py:40-71`: `_run_select_dialog` internals (listbox, `on_ok`/`on_cancel`, `curselection` indexing) are unexercised by the test suite — spec deliberately mocked the helper; add integration-level test in a future test-quality story.
- `nimble/tools/input.py:47`: `win.grab_set()` may fail on some X11/EWMH WMs without `win.update()` first — add `win.update()` before `win.grab_set()` in a future hardening pass.
- `nimble/tools/input.py:21-23,35-37`: `except Exception` swallows internal bugs as `RuntimeError("Input dialog is not available")` — consistent with TTS pattern; revisit with a structured exception hierarchy in reliability epic.
- `nimble/tools/input.py`: `root.destroy()` runs in `select()` `finally` after `_run_select_dialog` already destroyed `win` — tkinter tolerates this; revisit if double-destroy produces noise in logs.
- `nimble/tools/input.py`: `ask()`/`select()` are not thread-safe (tkinter main-thread requirement); cross-thread call produces a misleading error message — pre-existing pattern across all tools; document in skill authoring guide (Story 7.1).
- `nimble/tools/input.py:13-22`: `ask()` returns `""` for empty-field OK (falsy, not `None`); skill authors using `if result:` will mishandle silent empty input — document clearly in skill authoring guide (Story 7.1).
- `nimble/tools/input.py:24`: `select()` accepts `choices=[]` with no guard — opens zero-height listbox, OK silently returns `None`; add `if not choices: raise ValueError` in future hardening story.
- `tests/unit/tools/test_input.py`: No test covers the path where `tk.Tk()` succeeds but `askstring` raises — the `finally: root.destroy()` guard is unverified; add in a future test-quality story.

## Deferred from: fix hello_world tests after popup refactor (2026-04-25)

- `tests/unit/skills/test_hello_world.py`: `_REPO_ROOT = Path(__file__).parents[3]` is a fragile depth assumption; `assert spec is not None` is stripped under `-O`; `_load_skill()` bypasses the import system and won't catch broken `__init__.py` chains. All pre-existing; address in a test-quality story.

## Deferred from: hello-world-use-popup-tool (2026-04-25)

- `tools: object` and `context: object` annotations in skill files suppress all static analysis attribute-checking — skills are user-copied templates, so using the real types (`ToolRegistry`, `Context`) would catch typos at analysis time. Project-wide pattern; resolve when typing story targets skill API surface.
- `HelloWorldSkill` has no class/method docstring explaining that `run` is the required entrypoint, what `context` and `tools` contain, etc. — the file is a template for new skill authors. Add guidance when a "skill authoring guide" or template improvement story is scheduled.

## Deferred from: code review of 2-10-cross-platform-context-capture-windows-macos.md (2026-04-24)

- Windows/macOS `_get_selection()` worst-case wall clock: up to three sequential `subprocess.run(..., timeout=0.1)` calls plus `time.sleep(0.05)` can exceed the 200ms hotkey budget (NFR1 / AC8); validate end-to-end with hotkey wiring. Related: assembler latency note from story 2-4 code review.

## Deferred from: code review of 2-5-worker-subprocess-ipc-entrypoint.md (2026-04-21)

- `__getattr__` future footgun — any future `@property` on `Context` that raises `AttributeError` internally will be silently swallowed and replaced with the migration message (`worker/context.py:22-26`).
- `from_dict` no runtime type validation for `mouse_position`/`selection`/`clipboard` — daemon is the authoritative source; validate on the daemon side if enforcement is needed.
- No timeout for hung `skill.run()` — subprocess can block indefinitely with no response to daemon; add timeout mechanism in Story 2.6 or the reliability epic.
- `skill.run()` signature validation only at first dispatch — mismatched parameter count produces a cryptic TypeError; add signature inspection at load time in a future story.
- `exec_module` import failures crash the worker before the IPC loop — partially addressed by assert→raise patch; full structured startup error recovery deferred to reliability epic.
- `json.dumps` can fail if exception `__str__` returns a non-serializable value — extremely rare in practice; defer to future reliability hardening.
- `skill_file` path in error responses is absolute or relative inconsistently — standardize in the UI presentation layer when error display is designed.
- `stdout.flush()` failure (BrokenPipeError) not caught — worker crashes; defer to Story 4.x reliability work.

## Deferred from: code review of 2-4-context-snapshot-assembler.md (2026-04-18)

- Worst-case `build_context()` latency: three subprocess calls each capped at 0.1s plus pynput mouse read can approach or exceed the 200ms hotkey budget (NFR1) under contention; validate end-to-end when wired into `runner.py` (Story 2.6).

## Deferred from: code review of 2-3-windows-hotkey-adapter.md (2026-04-17)

- `WindowsHotkeyAdapter.stop()` calls `listener.join()` with no timeout; if the pynput listener thread hangs, shutdown blocks indefinitely. The same pattern exists on `X11HotkeyAdapter`; resolve with a shared policy (timeouts, daemon semantics, or documented limitation) when reliability work targets hotkey shutdown.

## Deferred from: code review of 1-1-repository-scaffold-with-wired-dev-toolchain (2026-04-16)

- pynput import fails on headless Linux without DISPLAY — `import pynput.keyboard` raises ImportError when DISPLAY is unset (standard CI environments). The HotkeyAdapter ABC boundary (Story 2.1) is the intended isolation, but CI test runs that touch pynput imports will abort.
- Architecture doc uses `nimble.yaml` in one early diagram vs `config.yaml` everywhere else — future agents reading the early diagram may scaffold code pointing at the wrong filename.
- worker/ sys.path injection fragility — `worker/entrypoint.py` (Epic 2) will use `sys.path.insert` to resolve `nimble.*`. If invoked from a non-standard CWD or via symlink, resolution may break. Architecture mentions a `NIMBLE_REPO_ROOT` env var but it is not yet wired.
- plyer >=2.1 constraint vs NFR17 contradiction — NFR17 says "native OS notifications only, no third-party notification dep" but plyer is listed as a core dependency.

## Deferred from: platform-detection-utility refactor (2026-04-24)

- `is_mac()` has no call sites — macOS hotkey adapter not yet implemented; `get_adapter()` raises `RuntimeError` on darwin. Resolves in Story 2.10 (cross-platform context capture / macOS support).
- `is_linux()` returns `True` on Android (`sys.platform == "linux"`) — X11 adapter and xclip/xdotool will fail at runtime on Android. Not a current target platform; revisit if Android support is added.
- Cygwin Python returns `sys.platform == "cygwin"`, so `is_windows()` returns `False` under Cygwin. `get_adapter()` raises `RuntimeError` with a clear message. Acceptable for v1; defer to platform edge-case story if Cygwin support is needed.

## Deferred from: code review of 7-3-readme-security-model-and-inline-skill-example.md (2026-05-02)

- `README.md` quick start: desktop notifications (FR41 + skill popups) require a working session notification stack; headless SSH or hosts without a notifier may show nothing — document in a broader onboarding or troubleshooting story if needed.

## Deferred from: code review of 4-5-yaml-config-validation-and-nimble-validate.md (2026-05-01)

- `nimble/manifest/parser.py:86`: `load_config` assumes YAML root is a mapping and may raise `AttributeError` for scalar/list roots (`data.get(...)`) — pre-existing parser behavior not introduced by this story; defer to parser-hardening follow-up.
