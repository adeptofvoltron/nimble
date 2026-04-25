# Deferred Work

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
