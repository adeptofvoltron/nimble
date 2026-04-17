# Deferred Work

## Deferred from: code review of 1-1-repository-scaffold-with-wired-dev-toolchain (2026-04-16)

- pynput import fails on headless Linux without DISPLAY — `import pynput.keyboard` raises ImportError when DISPLAY is unset (standard CI environments). The HotkeyAdapter ABC boundary (Story 2.1) is the intended isolation, but CI test runs that touch pynput imports will abort.
- Architecture doc uses `nimble.yaml` in one early diagram vs `config.yaml` everywhere else — future agents reading the early diagram may scaffold code pointing at the wrong filename.
- worker/ sys.path injection fragility — `worker/entrypoint.py` (Epic 2) will use `sys.path.insert` to resolve `nimble.*`. If invoked from a non-standard CWD or via symlink, resolution may break. Architecture mentions a `NIMBLE_REPO_ROOT` env var but it is not yet wired.
- plyer >=2.1 constraint vs NFR17 contradiction — NFR17 says "native OS notifications only, no third-party notification dep" but plyer is listed as a core dependency.
