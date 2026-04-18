---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories"]
inputDocuments:
  - docs/bmad_output/planning-artifacts/prd.md
  - docs/bmad_output/planning-artifacts/architecture.md
---

# Nimble - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Nimble, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: The daemon can capture global keyboard shortcuts triggered from any application context on Linux (X11), Windows, and macOS
FR2: The daemon can build a context snapshot at hotkey-fire time containing selected text, clipboard content, active application name, and mouse position
FR3: The daemon can map keyboard shortcut bindings to skills via YAML configuration
FR4: The daemon can detect a Wayland environment at startup and surface an actionable error message with remediation steps
FR5: The daemon can detect Windows OS-reserved hotkey combinations and warn the user at startup
FR6: The daemon can load Python skill classes from user-specified file paths at startup
FR7: The daemon can dispatch a hotkey event to the corresponding skill's `run()` method with context and tools
FR8: The daemon can activate a skill's isolated virtual environment before skill execution
FR9: Skills can declare optional lifecycle methods (`on_load`, `on_error`, `on_unload`) that the daemon invokes at defined points in the daemon lifecycle
FR10: The daemon can check a skill's declared `api_version` against the supported version at load time and refuse to load incompatible skills with a clear notification
FR11: The context object can surface accesses to deprecated field names with a migration message instead of a silent key error
FR12: The daemon can be configured to start automatically at system login on Linux and Windows
FR13: Skills can query a configured LLM with arbitrary text and receive a text response
FR14: Skills can display a text popup near the current cursor position
FR15: Skills can read the current clipboard content
FR16: Skills can write content to the clipboard
FR17: Skills can speak text aloud via the system text-to-speech engine
FR18: Skills can prompt the user for a text input via a dialog and receive the entered string
FR19: Skills can prompt the user to select from a list of options via a dialog and receive the chosen selection
FR20: Users can install a community skill from a GitHub repository URL with a single CLI command specifying the shortcut and repository
FR21: The CLI can display a skill's declared permissions to the user and require explicit confirmation before completing installation
FR22: The CLI can create an isolated Python virtual environment for each community-installed skill
FR23: The CLI can install a skill's declared pip dependencies into its isolated virtual environment
FR24: The CLI can detect dependency conflicts within a skill's virtual environment at install time and abort with a clear error
FR25: The CLI can automatically append a skill binding and entry to the YAML configuration after successful installation
FR26: Users can lock community skill versions to ensure reproducible installs across machines
FR27: Each community skill can declare its name, version, API version, entrypoint, required context fields, permissions, pip dependencies, and author in a manifest file
FR28: Users can define skill bindings, source tagging, and skill metadata via a YAML configuration file
FR29: The daemon can validate configuration file syntax at load time and report errors with line-precise messages
FR30: Users can run a pre-flight configuration validation without starting the daemon
FR31: The CLI can append new skill entries to the configuration file in a structured, format-safe manner
FR32: The daemon can continue operating after an unhandled exception in any single skill without restarting
FR33: The daemon can surface skill exceptions as system notifications containing the skill name, exception type, and source location
FR34: The daemon can write full error details and stack traces to a persistent log file
FR35: The daemon can catch unhandled exceptions from threads spawned within skills
FR36: The daemon can disable a skill that raises an exception during its `on_load` check and surface a startup notification identifying the skill and error
FR37: Users can start, stop, and restart the daemon via CLI commands
FR38: Users can list all configured skills with their source, binding, and current load status
FR39: Users can view the daemon's operational health and each skill's runtime state
FR40: Users can disable a specific skill without manually editing the YAML configuration
FR41: The daemon can fire a confirmation notification on successful startup
FR42: Author-written skills can be stored in a dedicated directory that is tracked in the user's fork
FR43: Community-installed skills can be stored in a tool-managed directory separate from author-written skills
FR44: The template repository can provide a structured AI authoring contract file containing the complete skill interface specification for use with AI coding assistants
FR45: Users can verify a correct daemon installation via a built-in test hotkey that confirms the daemon is running and responsive

### NonFunctional Requirements

NFR1: Hotkey-fire to skill execution start latency must be under 200ms on both Linux and Windows under normal system load
NFR2: Daemon startup time (cold start to first hotkey ready) must complete within 5 seconds on a standard developer machine
NFR3: `nimble add` skill installation (excluding pip download time) must complete within 10 seconds
NFR4: The daemon must not consume more than 50MB of RSS memory at idle with 10 or fewer skills loaded
NFR5: Per-skill venv activation overhead must not contribute more than 50ms to the hotkey-to-execution latency budget
NFR6: The daemon must run with standard user-level privileges only — no elevated permissions, no setuid, no capability bits beyond what is required for keyboard capture on Linux
NFR7: Context data (`selection`, `clipboard`, `active_app`, `mouse_position`) must be captured only at hotkey-fire time — no continuous background monitoring of any context field
NFR8: No telemetry, usage data, or diagnostic information may be transmitted anywhere without explicit user action
NFR9: The `nimble add` command must display all declared skill permissions and require explicit user confirmation before modifying the filesystem or configuration
NFR10: Community skill source code must be retrievable and auditable by the user before or after installation (no obfuscated or pre-compiled-only distribution)
NFR11: A skill-level exception must not crash or restart the daemon — per-skill failure isolation must be maintained for all exception types including those raised in spawned threads
NFR12: The daemon must recover to full operation after a system restart without manual intervention when configured for autostart
NFR13: The daemon must not produce silent failures — every error condition (skill failure, startup warning, incompatible skill, Wayland detection) must surface a user-visible notification or log entry
NFR14: YAML configuration corruption introduced by `nimble add` must be detectable at write time before the daemon is affected — the existing config must be preserved on any write failure
NFR15: System notifications for skill errors must be delivered within 500ms of the exception being caught
NFR16: The AI tool primitive must support configurable LLM providers — changing the underlying model or API endpoint must not require modifying skill code
NFR17: System notifications must use the native OS notification mechanism (libnotify/D-Bus on Linux, Win32 notifications on Windows) — no third-party notification dependency
NFR18: The systemd service unit and Windows Task Scheduler task must support standard start/stop/restart lifecycle operations without daemon-specific tooling
NFR19: The per-skill venv model must be compatible with standard Python virtual environment tooling (`pip`, `venv`) — no proprietary package management required
NFR20: The OS-specific hotkey capture implementation must be isolated behind an adapter interface — the core daemon must contain no platform-specific code
NFR21: `skill-build.md` must be updated as part of any pull request that changes the skill interface, context object fields, or tool primitive signatures — this is a required artifact, not optional documentation
NFR22: The codebase must be readable and self-contained enough for a Python developer who did not write it to fork and modify a skill or tool primitive within one hour of first reading
NFR23: The `api_version` field in `manifest.yaml` must be incremented on every breaking change to the skill interface — no silent breaking changes

### Additional Requirements

- **Dev Toolchain First Story:** The architecture explicitly mandates `pip install -e ".[dev]"` as the first implementation step — wiring up black, flake8, mypy, and pytest before any daemon code. This yields a dedicated Epic 1 / Story 1.
- **Starter Template:** No framework starter applies. The forkable repo template itself is the starter, built on `pyproject.toml` with hatchling 1.29.0 as the build backend.
- **Tooling Stack (pinned versions):** hatchling 1.29.0, typer 0.24.1, pynput 1.8.1, pyyaml 6.0, plyer 2.1, watchdog (version to confirm at implementation time), black 26.3.1, flake8 7.3.0, mypy 1.20.1
- **Pre-warmed subprocess workers:** Each loaded skill gets a persistent worker subprocess spawned at daemon startup with the correct venv activated. Hotkey dispatch writes a JSON context payload to worker stdin; the worker stays alive for subsequent invocations. This is the mechanism that keeps end-to-end latency under 200ms.
- **Worker IPC Protocol:** JSON lines over stdin/stdout. Exact schemas defined in architecture (invocation_id, context fields, status "ok"/"error", error object with type/message/skill_file/line). Must be treated as a hard contract — both sides must agree exactly.
- **IPC / Control Plane:** PID file at `~/.nimble/nimble.pid`; state file at `~/.nimble/state.json` (written on every state change + 5s heartbeat); CLI reads state/PID files directly (no socket IPC in v1).
- **Config change detection:** `watchdog` file watcher on `config.yaml`. On detected change: validate, diff, gracefully shut down affected workers, spawn new ones. All config writes must use atomic write (write to tmp + rename) to prevent partial reads (NFR14).
- **Logging:** Standard `logging` module with `RotatingFileHandler` at `~/.nimble/nimble.log` (5MB max, 3 backups). Log level INFO by default; DEBUG via `--debug` flag. All worker processes inherit the log path via env var and write to the same file.
- **Autostart:** `autostart/nimble.service` (systemd unit for Linux) and `autostart/nimble.xml` (Windows Task Scheduler task) ship in the template.
- **FakeHotkeyAdapter:** Must exist in `tests/unit/hotkeys/fake_adapter.py` from Story 1 (or the infrastructure story). All unit tests must use it — never real X11/Win32 APIs in tests.
- **Stale PID file cleanup:** `nimble start` must detect and clean up a stale PID file (process no longer running) before starting, to avoid false "daemon already running" errors after a crash.
- **Hello World skill:** `skills/hello_world/` ships with the template and must be pre-bound in the template `config.yaml` (e.g. `ctrl+shift+h`) so the test hotkey (FR45) fires immediately after `nimble start` without user configuration.
- **`threading.excepthook`:** `worker/entrypoint.py` must set `threading.excepthook` at startup to capture exceptions from threads spawned within skill `run()` methods, serialised as error responses on stdout.
- **Platform detection location:** Wayland detection belongs in `nimble/hotkeys/x11.py`; Windows reserved hotkey detection belongs in `nimble/hotkeys/windows.py` — not in `daemon.py`.
- **Atomic config writes:** All CLI commands that mutate `config.yaml` (nimble add, nimble disable) must use write-to-tmp + rename to preserve the existing config on any write failure.
- **`mypy --strict` enforced** across the entire engine package. All function parameters and return types must be annotated.
- **Absolute imports only** — relative imports are forbidden throughout the codebase.

### UX Design Requirements

_No UX Design document found for this project. This section is not applicable._

### FR Coverage Map

FR1: Epic 2 — Global hotkey capture (X11 + Windows)
FR2: Epic 2 — Context snapshot at hotkey-fire time
FR3: Epic 2 — YAML shortcut → skill binding
FR4: Epic 4 — Wayland detection + actionable error
FR5: Epic 4 — Windows reserved hotkey warning
FR6: Epic 2 — Load Python skill classes at startup
FR7: Epic 2 — Dispatch hotkey to skill `run()`
FR8: Epic 2 — Per-skill venv activation (pre-warmed workers)
FR9: Epic 4 — `on_load`, `on_error`, `on_unload` lifecycle hooks
FR10: Epic 4 — `api_version` compatibility check at load
FR11: Epic 4 — Smart context `__getattr__` deprecation messages
FR12: Epic 7 — Autostart via systemd (Linux) + Task Scheduler (Windows)
FR13: Epic 3 — `tools.ai.ask()` — LLM query
FR14: Epic 3 — `tools.popup.show()` — popup near cursor
FR15: Epic 3 — `tools.clipboard.get()`
FR16: Epic 3 — `tools.clipboard.set()`
FR17: Epic 3 — `tools.tts.speak()`
FR18: Epic 3 — `tools.input.ask()`
FR19: Epic 3 — `tools.input.select()`
FR20: Epic 6 — `nimble add <shortcut> <repo-url>`
FR21: Epic 6 — Permissions display + explicit confirmation
FR22: Epic 6 — Per-skill venv creation
FR23: Epic 6 — pip dep install into skill venv
FR24: Epic 6 — Dependency conflict detection at install
FR25: Epic 6 — Auto-append binding to config.yaml
FR26: Epic 6 — `manifest.lock` version pinning
FR27: Epic 6 — `manifest.yaml` full spec
FR28: Epic 2 — YAML config file for bindings and skill metadata
FR29: Epic 4 — Load-time config validation with line-precise errors
FR30: Epic 4 — `nimble validate` pre-flight check
FR31: Epic 6 — Format-safe CLI config append
FR32: Epic 4 — Per-skill exception isolation — daemon survives failures
FR33: Epic 4 — System notification on skill failure with file + line
FR34: Epic 4 — Persistent log file
FR35: Epic 4 — Thread exception capture in workers
FR36: Epic 4 — `on_load` failure disables skill + notification
FR37: Epic 2 — `nimble start` / `stop` / `restart`
FR38: Epic 5 — `nimble list` — skills with source/binding/status
FR39: Epic 5 — `nimble status` — daemon health + per-skill state
FR40: Epic 5 — `nimble disable` — disable skill without editing YAML
FR41: Epic 2 — Startup confirmation notification
FR42: Epic 2 — `skills/` author-owned directory
FR43: Epic 6 — `.nimble/skills/` tool-managed directory
FR44: Epic 7 — `skill-build.md` AI authoring contract
FR45: Epic 2 — Bundled test hotkey

## Epic List

### Epic 1: Project Foundation & Dev Toolchain
The development environment is fully operational — any contributor can clone, install, run linting/typechecking/tests, and resolve the `nimble` CLI entry point before any daemon logic is written.
**FRs covered:** None directly (architectural prerequisite enabling all future epics)

### Epic 2: A Hotkey Fires a Skill
Users can start the Nimble daemon on Linux, Windows, or macOS, configure hotkey bindings in YAML, write a Python skill class, and have it execute with a full context snapshot on keypress — the core "it works" experience.
**FRs covered:** FR1, FR2, FR3, FR6, FR7, FR8, FR28, FR37, FR41, FR42, FR45

### Epic 3: Skills Can Do Real Work — Tool Primitives
Skills can query an AI, display popups, read/write the clipboard, speak via TTS, and prompt the user for input — enabling the full range of workflow automation.
**FRs covered:** FR13, FR14, FR15, FR16, FR17, FR18, FR19

### Epic 4: The Daemon Never Silently Fails — Reliability & Error Handling
Every skill failure surfaces a clear system notification; the daemon survives all exceptions including threaded ones; YAML config is validated at load time with line-precise errors; API version mismatches and platform edge cases are caught before they cause silent failures.
**FRs covered:** FR4, FR5, FR9, FR10, FR11, FR29, FR30, FR32, FR33, FR34, FR35, FR36

### Epic 5: Operational Visibility — Inspect and Manage Without Touching Files
Users can list all loaded skills with their source/binding/status, check daemon health, and disable a skill from the CLI — no manual YAML editing required.
**FRs covered:** FR38, FR39, FR40

### Epic 6: Community Skills — Install from GitHub with One Command
Users can run `nimble add <shortcut> <repo-url>`, review declared permissions, and have a community skill installed with isolated dependencies and a locked version — reproducible across machines.
**FRs covered:** FR20, FR21, FR22, FR23, FR24, FR25, FR26, FR27, FR31, FR43

### Epic 7: Launch-Ready — Developer Experience & Ecosystem Artifacts
The template ships with `skill-build.md` (AI authoring contract), a working README with inline skill example, autostart files for both platforms, and a documented security model — everything needed to share the project publicly.
**FRs covered:** FR12, FR44

---

## Epic 1: Project Foundation & Dev Toolchain

The development environment is fully operational — any contributor can clone, install, run linting/typechecking/tests, and resolve the `nimble` CLI entry point before any daemon logic is written.

### Story 1.1: Repository Scaffold with Wired Dev Toolchain

As a contributor,
I want a correctly structured repository with all core and dev dependencies configured and installable via `pip install -e ".[dev]"`,
So that I can immediately run linting, typechecking, formatting, and tests — and resolve the `nimble` CLI entry point — without any manual setup.

**Acceptance Criteria:**

**Given** the repository is cloned on a machine with Python 3.10+
**When** `pip install -e ".[dev]"` is run
**Then** all core dependencies (typer, pynput, pyyaml, plyer) and dev dependencies (black, flake8, mypy, pytest) are installed without errors
**And** running `nimble --help` resolves to the Typer app and prints help text

**Given** a Python file exists in the `nimble/` package
**When** `black --check nimble/` is run
**Then** black validates formatting using line-length=88 and target python3.10

**Given** the `nimble/` package exists
**When** `mypy nimble/` is run
**Then** mypy applies `--strict` mode with `python_version = "3.10"` and `ignore_missing_imports = true`

**Given** the `tests/` directory exists
**When** `pytest` is run
**Then** pytest discovers `testpaths = ["tests"]` and exits cleanly (zero failures, even on an empty suite)

---

### Story 1.2: Test Infrastructure Foundation

As a developer writing tests,
I want shared test fixtures and a `FakeHotkeyAdapter` available from day one,
So that all unit tests can use the fake adapter and common fixtures without real OS APIs or duplicated setup code.

**Acceptance Criteria:**

**Given** `tests/unit/hotkeys/fake_adapter.py` exists
**When** a test imports `FakeHotkeyAdapter`
**Then** it implements the `HotkeyAdapter` ABC with `register(shortcut, callback)`, `start()`, and `stop()` methods and tracks registered shortcuts in a `registered: list[str]` attribute

**Given** `tests/conftest.py` exists
**When** any test module in the `tests/` tree is collected by pytest
**Then** the `fake_adapter`, `tmp_config`, and `fake_notifier` fixtures are available without any per-module imports

**Given** `tmp_config` fixture is used in a test
**When** the fixture is requested
**Then** it creates a temporary `config.yaml` at `tmp_path / "config.yaml"` pre-populated with `skills: []\nbindings: []\n`

**Given** the `nimble/hotkeys/base.py` module exists
**When** mypy checks the file
**Then** `HotkeyAdapter` is defined as an abstract base class with all methods annotated and passing `--strict`

---

### Story 1.3: CI Workflow

As a maintainer,
I want a GitHub Actions workflow that runs linting, typechecking, and tests automatically on every push and pull request,
So that regressions are caught before merging and the codebase always stays in a verifiable state.

**Acceptance Criteria:**

**Given** `.github/workflows/ci.yml` exists
**When** a push or pull request event fires on any branch
**Then** the workflow runs three jobs in sequence: `lint` (flake8), `typecheck` (mypy), and `test` (pytest)

**Given** the lint job runs
**When** any Python file in `nimble/` or `tests/` violates flake8 rules
**Then** the job fails with a non-zero exit code and the workflow is marked failed

**Given** the typecheck job runs
**When** any type annotation error exists under `mypy --strict`
**Then** the job fails and blocks the pull request

**Given** the test job runs
**When** all tests pass
**Then** the workflow completes successfully and reports a green status check on the commit

---

## Epic 2: A Hotkey Fires a Skill

Users can start the Nimble daemon, configure hotkey bindings in YAML, write a Python skill class, and have it execute with a full context snapshot on keypress — the core "it works" experience.

### Story 2.1: HotkeyAdapter ABC and Platform Factory

As a developer,
I want a `HotkeyAdapter` abstract base class and a platform factory that selects the correct implementation at runtime,
So that the core daemon never contains platform-specific code and tests can always swap in the `FakeHotkeyAdapter`.

**Acceptance Criteria:**

**Given** `nimble/hotkeys/base.py` exists
**When** a class inherits from `HotkeyAdapter`
**Then** it must implement `register(shortcut: str, callback: Callable[[], None]) -> None`, `start() -> None`, and `stop() -> None` — mypy enforces this at strict mode

**Given** `nimble/hotkeys/__init__.py` exposes a `get_adapter() -> HotkeyAdapter` factory
**When** the factory is called on Linux (X11)
**Then** it returns an instance of `X11HotkeyAdapter`

**When** the factory is called on Windows
**Then** it returns an instance of `WindowsHotkeyAdapter`

**Given** `FakeHotkeyAdapter` is substituted for the real adapter in tests
**When** `register("ctrl+shift+d", callback)` is called
**Then** `"ctrl+shift+d"` appears in `fake_adapter.registered` and no real OS API is invoked

---

### Story 2.2: X11 Hotkey Adapter (Linux)

As a Linux user running X11,
I want the daemon to capture my configured keyboard shortcuts from any application context,
So that my skills execute regardless of which window is focused.

**Acceptance Criteria:**

**Given** `nimble/hotkeys/x11.py` implements `HotkeyAdapter` using pynput
**When** `register("ctrl+shift+d", callback)` is called and the user presses Ctrl+Shift+D
**Then** `callback` is invoked within 200ms

**Given** `X11HotkeyAdapter.start()` is called on a Wayland-only session (no XWayland)
**Then** it raises a descriptive `RuntimeError` with a message indicating Wayland is detected and XWayland is required for v1
**And** the error is surfaced as an actionable startup message (FR4)

**Given** the adapter is running
**When** `stop()` is called
**Then** the pynput listener is cleanly terminated with no dangling threads

---

### Story 2.3: Windows Hotkey Adapter

As a Windows user,
I want the daemon to capture my configured keyboard shortcuts globally,
So that my skills execute regardless of which application is in focus.

**Acceptance Criteria:**

**Given** `nimble/hotkeys/windows.py` implements `HotkeyAdapter` using pynput
**When** `register("ctrl+shift+d", callback)` is called and the user presses Ctrl+Shift+D
**Then** `callback` is invoked within 200ms

**Given** a binding is registered for a known Windows-reserved combination (e.g. `win+l`)
**When** `WindowsHotkeyAdapter.start()` is called
**Then** a `WARNING` log entry is written identifying the reserved shortcut (FR5)
**And** the daemon starts normally — the warning is non-fatal

**Given** `stop()` is called while the adapter is running
**When** the adapter shuts down
**Then** the pynput listener terminates cleanly

---

### Story 2.4: Context Snapshot Assembler

As a skill author,
I want the daemon to capture a full context snapshot at the moment a hotkey fires,
So that my skill receives the selected text, clipboard content, active application, and cursor position without me having to query them manually.

**Acceptance Criteria:**

**Given** `nimble/context/assembler.py` exports `build_context() -> dict[str, Any]`
**When** called at hotkey-fire time
**Then** it returns a dict with keys `selection` (str), `clipboard` (str), `active_app` (str), `mouse_position` ([int, int]) — never null values (empty string for unavailable text fields)

**Given** no text is selected
**When** `build_context()` is called
**Then** `selection` is `""` — not `None`

**Given** context is built
**When** it is serialized to JSON
**Then** all fields round-trip without loss (strings stay strings, `mouse_position` stays a 2-element integer array)

**Given** NFR7 — context must not be captured continuously
**When** `build_context()` is inspected
**Then** it performs a one-shot OS query per call — no background threads, no polling

---

### Story 2.5: Worker Subprocess IPC Entrypoint

As the daemon dispatcher,
I want a worker subprocess that receives a JSON context payload on stdin, executes the skill's `run()` method, and writes a JSON result to stdout,
So that skill execution is fully isolated from the daemon process and any skill exception cannot crash the daemon.

**Acceptance Criteria:**

**Given** `worker/entrypoint.py` is the worker subprocess script
**When** it receives a valid JSON invocation on stdin: `{"invocation_id": "<uuid>", "context": {...}}`
**Then** it reconstructs a `Context` object, calls `skill.run(context, tools)`, and writes `{"invocation_id": "<uuid>", "status": "ok", "error": null}` to stdout

**Given** `skill.run()` raises an unhandled exception
**When** the worker catches it
**Then** it writes `{"invocation_id": "<uuid>", "status": "error", "error": {"type": "...", "message": "...", "skill_file": "...", "line": N}}` to stdout
**And** the worker process stays alive for the next invocation

**Given** `threading.excepthook` is set at worker startup
**When** a thread spawned inside `skill.run()` raises an unhandled exception
**Then** it is caught and serialised as an error response on stdout — not silently lost (FR35)

**Given** `worker/context.py` defines the `Context` class
**When** a deprecated field name (e.g. `context.selected_text`) is accessed
**Then** `AttributeError` is raised with a migration message — not a silent `KeyError` (FR11)

**Given** a community skill worker is spawned using the skill's isolated venv Python (which does not have `nimble` installed)
**When** `worker/entrypoint.py` starts
**Then** it inserts the repo root into `sys.path` before any other imports — using `Path(__file__).parent.parent` — so that `nimble.tools` and `nimble.context` are importable regardless of the active venv
**And** the daemon also passes `NIMBLE_REPO_ROOT` as an environment variable to the worker as a fallback path resolution mechanism

---

### Story 2.6: Pre-Warmed Worker Pool and Dispatcher

As a hotkey user,
I want my hotkey to trigger a skill with end-to-end latency under 200ms,
So that the interaction feels instant and I never wait for a Python cold start.

**Acceptance Criteria:**

**Given** `nimble/skills/runner.py` manages a pool of pre-warmed worker subprocesses
**When** the daemon starts with N skills loaded
**Then** N worker subprocesses are spawned (one per skill) with the correct Python executable for their venv
**And** each worker is alive and ready before the first hotkey is accepted

**Given** a hotkey fires for skill `log-diagnosis`
**When** the dispatcher in `runner.py` sends the context payload to the worker's stdin
**Then** the round-trip (dispatch to result received) completes in under 200ms under normal system load (NFR1)

**Given** a worker process dies unexpectedly
**When** `runner.py` detects this via `poll()`
**Then** the skill is disabled, a system notification is fired, and the daemon continues serving other skills

**Given** author skills (`source: local`) vs community skills (`source: community`)
**When** workers are spawned
**Then** author skills use `sys.executable`; community skills use `.nimble/skills/<name>/.venv/bin/python` (Linux) or `.nimble/skills/<name>/.venv/Scripts/python.exe` (Windows) — satisfying FR8

---

### Story 2.7: YAML Config Loading and Skill Registry

As a skill author,
I want to define my hotkey bindings and skill paths in a `config.yaml` file,
So that the daemon knows which skills to load and which shortcuts to register.

**Acceptance Criteria:**

**Given** `config.yaml` exists at repo root with a `skills` list and `bindings` list
**When** `nimble/manifest/parser.py` parses it
**Then** it returns a validated config object with all skills and bindings resolved — mypy strict-typed throughout

**Given** a skill entry has `source: local` and a valid `path`
**When** it is registered in `nimble/skills/registry.py`
**Then** the registry holds a mapping of skill name → `SkillWorker` with `source`, `binding`, and `status` fields

**Given** `config.yaml` has a syntax error (tabs instead of spaces)
**When** the parser reads it
**Then** it raises `ConfigError` with the message `"config.yaml line N: <yaml error description>"` (FR29)

**Given** a skill entry references a file that does not exist
**When** the registry attempts to load it
**Then** it raises a `ConfigError` identifying the missing path — not a silent failure (NFR13)

---

### Story 2.8: Daemon Main Loop and CLI start/stop/restart

As a user,
I want to start, stop, and restart the Nimble daemon with simple CLI commands,
So that I can control the daemon lifecycle without touching process management tools directly.

**Acceptance Criteria:**

**Given** `nimble start` is run and no daemon is already running
**When** the daemon starts successfully
**Then** a PID file is written to `~/.nimble/nimble.pid` and the daemon enters its main loop listening for hotkeys

**Given** `nimble start` is run and a stale PID file exists (process is dead)
**When** the daemon checks the PID file
**Then** it cleans up the stale PID file and starts normally — no "daemon already running" false positive

**Given** `nimble stop` is run
**When** the daemon PID is found in `~/.nimble/nimble.pid`
**Then** `SIGTERM` (Linux) or `TerminateProcess` (Windows) is sent, workers are gracefully shut down, and the PID file is deleted

**Given** `nimble restart` is run while the daemon is running
**When** the restart completes
**Then** it is equivalent to `nimble stop && nimble start` — a fresh daemon with reloaded config

**Given** `nimble start` runs a cold start
**When** all skills are loaded and hotkeys registered
**Then** cold start completes in under 5 seconds on a standard developer machine (NFR2)

**Given** `nimble/watcher.py` starts a `watchdog` file watcher on `config.yaml` as part of the daemon main loop
**When** `config.yaml` is modified by any process (CLI or editor)
**Then** the daemon detects the change, validates the new config, diffs against loaded state, and gracefully shuts down / spawns workers as needed — without requiring `nimble restart`

---

### Story 2.9: Startup Confirmation, Hello World Skill, and Bundled Test Hotkey

As a first-time user,
I want to see a confirmation notification and fire a test hotkey immediately after `nimble start`,
So that I know the daemon is running and responsive without having to write any skill code first.

**Acceptance Criteria:**

**Given** the daemon starts successfully
**When** all skills are loaded and hotkeys are registered
**Then** a system notification fires: "Nimble daemon running." (FR41)

**Given** `skills/hello_world/skill.py` and `skills/hello_world/manifest.yaml` exist in the template
**When** the template `config.yaml` is used unchanged
**Then** `ctrl+shift+h` is pre-bound to the `hello_world` skill

**Given** the user presses `ctrl+shift+h` after `nimble start`
**When** the hello_world skill executes
**Then** a popup appears confirming the daemon is working — no user configuration required (FR45)

**Given** the `skills/` directory is tracked in the user's git fork
**When** a user commits their skills
**Then** `skills/hello_world/` is committed alongside any user-written skills (FR42)

---

### Story 2.10: Cross-Platform Context Capture (Windows + macOS)

As a skill author on Windows or macOS,
I want `build_context()` to return real values for `clipboard`, `active_app`, and `selection` — not empty strings,
So that my skills work the same way regardless of which OS I'm running.

**Acceptance Criteria:**

**Given** `build_context()` is called on Windows
**When** text is in the clipboard
**Then** `clipboard` returns that text via PowerShell `Get-Clipboard`

**Given** `build_context()` is called on Windows
**When** an application window is focused
**Then** `active_app` returns the window title via `ctypes` (no extra deps)

**Given** `build_context()` is called on Windows
**When** text is selected in any application
**Then** `selection` returns that text via clipboard simulation (save → Ctrl+C → read → restore); `""` on any failure

**Given** `build_context()` is called on macOS
**When** text is in the clipboard
**Then** `clipboard` returns that text via `pbpaste`

**Given** `build_context()` is called on macOS
**When** an application is in the foreground
**Then** `active_app` returns the app name via `osascript`

**Given** `build_context()` is called on macOS
**When** text is selected in any application
**Then** `selection` returns that text via clipboard simulation (save → Cmd+C → read → restore); `""` on any failure

**Given** clipboard simulation is used for `selection`
**When** the simulation completes
**Then** the original clipboard content is restored — the user's clipboard is not permanently modified

**Given** all OS calls use `timeout=0.1`
**When** any subprocess hangs
**Then** it is killed and the field returns `""` — within the 200ms hotkey budget (NFR1)

---

## Epic 3: Skills Can Do Real Work — Tool Primitives

Skills can query an AI, display popups, read/write the clipboard, speak via TTS, and prompt the user for input — enabling the full range of workflow automation.

### Story 3.1: AI Tool Primitive (`tools.ai.ask`)

As a skill author,
I want to call `tools.ai.ask(text, prompt=None)` and receive a text response from a configured LLM,
So that I can build AI-powered workflows without knowing or caring which provider or model is being used.

**Acceptance Criteria:**

**Given** `config.yaml` contains an `ai` block with `provider`, `model`, and `api_key_env`
**When** `tools.ai.ask("explain this error")` is called from a skill
**Then** the configured LLM is queried and a string response is returned

**Given** the `provider` in `config.yaml` is changed from `anthropic` to `openai`
**When** the daemon reloads the worker
**Then** subsequent `tools.ai.ask()` calls use the new provider — skill code is unchanged (NFR16)

**Given** the API key environment variable is not set
**When** `tools.ai.ask()` is called
**Then** a clear `RuntimeError` is raised naming the missing env var — not a cryptic provider SDK error

---

### Story 3.2: Popup Tool Primitive (`tools.popup.show`)

As a skill author,
I want to call `tools.popup.show(text)` and have the result appear near the cursor,
So that I can surface skill output without the user switching windows.

**Acceptance Criteria:**

**Given** `tools.popup.show("Hello, Nimble!")` is called
**When** the skill runs on Linux
**Then** a system notification appears using the native mechanism (plyer/libnotify) with the provided text

**When** the skill runs on Windows
**Then** a system notification appears using the native Win32 mechanism (NFR17)

**Given** the text passed to `popup.show()` is an empty string
**When** the popup fires
**Then** it displays gracefully — no crash or silent failure

---

### Story 3.3: Clipboard Tool Primitives (`tools.clipboard.get` / `tools.clipboard.set`)

As a skill author,
I want to read from and write to the clipboard via `tools.clipboard.get()` and `tools.clipboard.set(text)`,
So that I can build skills that manipulate clipboard content as part of a workflow.

**Acceptance Criteria:**

**Given** text is currently in the clipboard
**When** `tools.clipboard.get()` is called
**Then** it returns the clipboard content as a string — never `None`

**Given** `tools.clipboard.set("transformed output")` is called
**When** the skill completes
**Then** the clipboard contains `"transformed output"` on both Linux and Windows

**Given** the clipboard is empty
**When** `tools.clipboard.get()` is called
**Then** it returns `""` — not `None`

---

### Story 3.4: TTS Tool Primitive (`tools.tts.speak`)

As a skill author,
I want to call `tools.tts.speak(text)` to have the system read text aloud,
So that I can build hands-free skills that deliver output via audio.

**Acceptance Criteria:**

**Given** `tools.tts.speak("Processing complete")` is called
**When** the skill runs on Linux
**Then** the system TTS engine speaks the text aloud

**When** the skill runs on Windows
**Then** the system TTS engine (SAPI) speaks the text aloud

**Given** TTS is unavailable on the system
**When** `tools.tts.speak()` is called
**Then** a `RuntimeError` is raised with a clear message — not a silent no-op

---

### Story 3.5: Input Dialog Tool Primitives (`tools.input.ask` / `tools.input.select`)

As a skill author,
I want to prompt the user for text input or a selection choice mid-skill,
So that I can build interactive workflows that require user input at execution time.

**Acceptance Criteria:**

**Given** `tools.input.ask("Enter search query:")` is called
**When** the dialog appears
**Then** the user can type a string and confirm, and the entered string is returned to the skill

**Given** `tools.input.select("Choose action:", ["Summarize", "Translate", "Explain"])` is called
**When** the dialog appears
**Then** the user can pick one option, and the selected string is returned to the skill

**Given** the user dismisses either dialog without confirming
**When** the dialog closes
**Then** the tool returns `None` — the skill can check for this and exit gracefully

---

## Epic 4: The Daemon Never Silently Fails — Reliability & Error Handling

Every skill failure surfaces a clear system notification; the daemon survives all exceptions including threaded ones; YAML config is validated at load time with line-precise errors; API version mismatches and platform edge cases are caught before they cause silent failures.

### Story 4.1: Per-Skill Exception Isolation and Error Notifications

As a user,
I want skill failures to surface as clear system notifications without stopping the daemon,
So that one broken skill never takes down my other running skills.

**Acceptance Criteria:**

**Given** a skill's `run()` method raises an unhandled exception
**When** the worker sends an error response to the dispatcher
**Then** the daemon fires a system notification: `"Nimble — <skill-name>: <ExceptionType>: <message> in <file> line <N>"` (FR33)
**And** the daemon continues running all other skills normally (FR32)
**And** the notification is delivered within 500ms of the exception being caught (NFR15)

**Given** a thread spawned inside `skill.run()` raises an unhandled exception
**When** `threading.excepthook` catches it in the worker
**Then** the error is serialised and sent to the daemon dispatcher, which fires the same notification format (FR35)

**Given** `nimble/notifier.py` implements cross-platform notification dispatch
**When** `notifier.send(title, body)` is called on Linux
**Then** it uses plyer/libnotify — no third-party notification dep beyond plyer (NFR17)

**When** `notifier.send(title, body)` is called on Windows
**Then** it uses the Win32 notification mechanism via plyer (NFR17)

---

### Story 4.2: Persistent Log File

As a user debugging a skill failure,
I want full error details and stack traces written to a persistent log file,
So that the system notification acts as a pointer and I can read the full context in the log.

**Acceptance Criteria:**

**Given** `~/.nimble/nimble.log` is configured as a `RotatingFileHandler` (5MB max, 3 backups)
**When** a skill raises an exception
**Then** the full traceback is written to the log at `ERROR` level with the skill name, exception type, file, and line number

**Given** the log file reaches 5MB
**When** the next log entry is written
**Then** the file rotates — the old file becomes `nimble.log.1` and a new `nimble.log` is started

**Given** a worker process is spawned
**When** it starts
**Then** it inherits `NIMBLE_LOG_PATH` from the daemon environment and writes to the same log file

**Given** `nimble start` is run with the `--debug` flag
**When** any log entry is written
**Then** `DEBUG`-level entries appear in the log — they are suppressed at the default `INFO` level

---

### Story 4.3: Skill Lifecycle Hooks (`on_load`, `on_error`, `on_unload`)

As a skill author,
I want to declare optional `on_load`, `on_error`, and `on_unload` methods on my skill class,
So that I can validate dependencies at startup, enrich errors before they surface, and clean up resources when the daemon shuts down.

**Acceptance Criteria:**

**Given** a skill class defines `on_load(self, config)`
**When** the worker subprocess starts
**Then** `on_load` is called before the worker enters the IPC loop — before the first hotkey can be dispatched (FR9)

**Given** `on_load` raises an exception
**When** the worker detects this
**Then** the skill is marked disabled in the registry, a startup notification fires: `"Nimble — <skill-name>: on_load failed: <message>. Skill disabled until restart."` (FR36)
**And** the daemon continues loading all other skills normally

**Given** a skill class defines `on_error(self, exc)`
**When** `run()` raises an exception
**Then** `on_error` is called with the exception before it is serialised — the skill can enrich or transform the error message

**Given** a skill class defines `on_unload(self)`
**When** the daemon shuts down or the skill is disabled
**Then** `on_unload` is called on the worker before the subprocess exits

---

### Story 4.4: API Version Compatibility Check

As a daemon maintainer,
I want skills to declare their `api_version` and have the daemon check compatibility at load time,
So that outdated or too-new skills fail with an informative message rather than a confusing runtime error.

**Acceptance Criteria:**

**Given** a skill's `manifest.yaml` declares `api_version: 1` and the daemon supports `api_version: 1`
**When** the skill is loaded
**Then** it loads normally with no warnings (FR10)

**Given** a skill declares `api_version` lower than the daemon's supported version (old skill, new daemon)
**When** the skill loads
**Then** a `WARNING` is logged: `"Skill <name> uses api_version <N> — deprecated fields will raise AttributeError"`
**And** the skill loads and runs — deprecated field accesses surface migration messages at runtime (FR11)

**Given** a skill declares `api_version` higher than the daemon's supported version
**When** the daemon attempts to load it
**Then** the skill is refused with a notification: `"Skill <name> requires Nimble api_version <N> — upgrade your daemon"` (FR10)
**And** the daemon continues loading all other skills

---

### Story 4.5: YAML Config Validation and `nimble validate`

As a user editing `config.yaml`,
I want the daemon to catch config errors at load time with line-precise messages, and to be able to run a pre-flight check without starting the daemon,
So that I fix config problems in seconds rather than discovering them from a silent daemon failure.

**Acceptance Criteria:**

**Given** `config.yaml` has a YAML syntax error (e.g. tab character on line 12)
**When** the daemon or `nimble validate` parses it
**Then** a `ConfigError` is raised with message `"config.yaml line 12: <description>"` — never a raw PyYAML exception (FR29)

**Given** `nimble validate` is run on a valid `config.yaml`
**When** parsing and validation complete
**Then** the command exits 0 and prints `"config.yaml is valid"` — no daemon is started (FR30)

**Given** `nimble validate` is run on an invalid `config.yaml`
**When** a validation error is found
**Then** the command exits non-zero and prints the line-precise error — same format as daemon startup errors

**Given** a config write fails mid-way (e.g. disk full)
**When** the atomic write (write-to-tmp + rename) is used
**Then** the original `config.yaml` is preserved intact — no partial or corrupted state (NFR14)

---

### Story 4.6: Platform Edge Case Handling (Wayland + Windows Reserved Hotkeys + macOS Accessibility)

As a user on an unsupported or restricted platform configuration,
I want actionable error messages at daemon startup rather than silent failures,
So that I know exactly what to fix and how.

**Acceptance Criteria:**

**Given** `nimble start` is run on Linux with `$WAYLAND_DISPLAY` set and no XWayland available
**When** the X11 adapter initialises
**Then** the daemon exits with a notification and stdout message: `"Nimble requires XWayland on Wayland sessions. Install XWayland or set DISPLAY to your X11 display."` (FR4)

**Given** `nimble start` is run on Linux with `$WAYLAND_DISPLAY` set but XWayland is available (`$DISPLAY` is set)
**When** the X11 adapter initialises
**Then** the daemon starts normally — Wayland + XWayland is a supported configuration

**Given** a binding in `config.yaml` matches a known Windows-reserved hotkey (e.g. `win+l`)
**When** `nimble start` runs on Windows
**Then** a `WARNING` log entry and startup notification identifies the reserved binding by name (FR5)
**And** the daemon starts — the warning is non-fatal

**Given** `build_context()` is called on macOS and Accessibility access has not been granted
**When** clipboard simulation is used for `selection`
**Then** the daemon logs a one-time INFO message: `"macOS: Accessibility not granted — selection uses clipboard simulation. Grant access in System Settings → Privacy & Security → Accessibility for more reliable capture."`
**And** the daemon continues normally — this is non-fatal (NFR13)

---

## Epic 5: Operational Visibility — Inspect and Manage Without Touching Files

Users can list all loaded skills with their source/binding/status, check daemon health, and disable a skill from the CLI — no manual YAML editing required.

### Story 5.1: State File and Daemon Heartbeat

As a CLI user,
I want the daemon to maintain an up-to-date `state.json` file reflecting the current runtime state,
So that `nimble list` and `nimble status` can read it without any IPC round-trip to the daemon process.

**Acceptance Criteria:**

**Given** the daemon starts successfully
**When** each skill finishes loading
**Then** `~/.nimble/state.json` is written with `pid`, `started_at`, `daemon_version`, and a `skills` array containing each skill's `name`, `source`, `binding`, `status`, and `worker_pid`

**Given** the daemon is running
**When** 5 seconds elapse with no state-change events
**Then** the state file is rewritten (heartbeat) — keeping `started_at` the same and updating only `worker_pid` values if changed

**Given** a skill's status changes (loaded → disabled, worker dies, etc.)
**When** the state change occurs
**Then** `state.json` is updated immediately — not deferred to the next heartbeat

**Given** the daemon stops cleanly
**When** the shutdown completes
**Then** `state.json` is removed and `nimble.pid` is deleted

---

### Story 5.2: `nimble list` and `nimble status`

As a user,
I want to see all loaded skills and daemon health at a glance from the CLI,
So that I can quickly confirm what's running, what's bound to which shortcut, and whether anything has failed.

**Acceptance Criteria:**

**Given** the daemon is running and `nimble list` is run
**When** `state.json` is read
**Then** output shows each skill's name, source (`local`/`community`), binding, and status (`loaded`/`disabled`/`failed`) — one skill per line (FR38)

**Given** the daemon is not running and `nimble list` is run
**When** no `state.json` or stale PID is found
**Then** the command prints `"Nimble daemon is not running"` and exits 0 — no crash

**Given** `nimble status` is run while the daemon is running
**When** `state.json` is read
**Then** output shows daemon `pid`, `started_at`, `daemon_version`, and a per-skill breakdown of load state (FR39)

**Given** `nimble status` is run and a skill has `status: failed`
**When** the output is displayed
**Then** the failed skill is visually distinguished (e.g. marked `[FAILED]`) so it's immediately obvious

---

### Story 5.3: `nimble disable`

As a user,
I want to disable a specific skill from the CLI without editing `config.yaml` manually,
So that I can quickly turn off a misbehaving skill without stopping the entire daemon.

**Acceptance Criteria:**

**Given** `nimble disable log-diagnosis` is run while the daemon is running
**When** the CLI writes `disabled: true` to the skill entry in `config.yaml` via atomic write
**Then** the file watcher detects the change, the daemon shuts down the `log-diagnosis` worker, and `state.json` reflects `status: disabled` for that skill (FR40)

**Given** `nimble disable <skill>` is run for a skill name that does not exist in `config.yaml`
**When** the CLI looks up the skill
**Then** it exits non-zero with `"No skill named '<skill>' found in config.yaml"` — `config.yaml` is not modified

**Given** `nimble disable <skill>` is run and the config write fails
**When** the atomic write detects an error
**Then** `config.yaml` is left unchanged (NFR14) and the CLI prints a clear error message

---

## Epic 6: Community Skills — Install from GitHub with One Command

Users can run `nimble add <shortcut> <repo-url>`, review declared permissions, and have a community skill installed with isolated dependencies and a locked version — reproducible across machines.

### Story 6.1: `manifest.yaml` Parsing and Validation

As the `nimble add` command,
I want to fetch and validate a skill's `manifest.yaml` from a GitHub repository,
So that I have a verified, typed representation of the skill's metadata before touching the filesystem.

**Acceptance Criteria:**

**Given** a valid `manifest.yaml` at a remote repository URL
**When** `nimble/manifest/parser.py` fetches and parses it
**Then** it returns a typed `ManifestSpec` dataclass with all required fields: `name`, `version`, `api_version`, `description`, `entrypoint`, `requires`, `permissions`, `dependencies`, `author` (FR27)

**Given** the remote `manifest.yaml` is missing a required field (e.g. `entrypoint`)
**When** parsing is attempted
**Then** a `ManifestError` is raised identifying the missing field — install is aborted before any filesystem changes

**Given** a `manifest.yaml` with `api_version` higher than the daemon supports
**When** it is parsed
**Then** a `ManifestError` is raised: `"Skill requires Nimble api_version <N> — upgrade your daemon"` — install is aborted

---

### Story 6.2: Permissions Display and Install Confirmation

As a security-conscious user,
I want to see a skill's declared permissions before anything is installed,
So that I can make an informed decision about what I'm allowing to run on my machine.

**Acceptance Criteria:**

**Given** `nimble add ctrl+shift+d github.com/user/nimble-log-diagnosis` is run
**When** the manifest is fetched and parsed
**Then** the CLI displays the skill name, description, author, and a permissions block before any prompt (FR21)

**Given** the skill declares `permissions: [ai, clipboard]`
**When** the permissions block is displayed
**Then** each permission is shown with a one-line description of what it can do:
`- ai     (may send text to an external LLM API)`
`- clipboard (reads clipboard content at hotkey-fire time)` (NFR9)

**Given** the permissions are displayed
**When** the user is prompted `"Install anyway? [y/N]"`
**Then** the default is `N` — the user must explicitly type `y` to proceed
**And** any input other than `y` / `Y` aborts the install with no filesystem changes

---

### Story 6.3: Per-Skill Venv Creation and Dependency Installation

As a user installing a community skill,
I want the skill's pip dependencies installed into an isolated virtual environment,
So that they never conflict with my system Python or other skills' dependencies.

**Acceptance Criteria:**

**Given** the user confirms the install
**When** `nimble add` proceeds
**Then** a venv is created at `.nimble/skills/<name>/.venv/` using `python -m venv` (FR22)

**Given** the skill's `manifest.yaml` declares `dependencies: [anthropic]`
**When** the venv is created
**Then** `pip install anthropic` runs into the skill's venv — not the system Python or daemon env (FR23)

**Given** a dependency installation fails (e.g. package not found on PyPI)
**When** pip exits non-zero
**Then** the partially created venv is cleaned up, `config.yaml` is not modified, and a clear error is printed (NFR14)

**Given** `nimble add` excluding pip download completes
**When** timing is measured
**Then** all steps except the pip network download complete in under 10 seconds (NFR3)

---

### Story 6.4: Dependency Conflict Detection

As a user managing multiple community skills,
I want `nimble add` to detect when a new skill's dependencies conflict with packages already in its venv,
So that an incompatible skill fails at install time with a clear message rather than silently breaking at runtime.

**Acceptance Criteria:**

**Given** a skill's venv already has `anthropic==0.20.0` installed
**When** a new skill version declares `dependencies: [anthropic>=0.30.0]` and `nimble add` runs
**Then** pip's conflict resolution detects the incompatibility
**And** `nimble add` aborts with the pip error message quoted — `config.yaml` is not modified (FR24)

**Given** there are no dependency conflicts
**When** pip installs into the skill's venv
**Then** install completes without error and proceeds to config append

---

### Story 6.5: Config Append, `manifest.lock`, and `.nimble/skills/` Structure

As a user,
I want `nimble add` to update my `config.yaml` and lock the skill version automatically,
So that my setup is reproducible on any machine without manual config editing.

**Acceptance Criteria:**

**Given** install succeeds (venv created, deps installed)
**When** `nimble add` appends to `config.yaml`
**Then** the skill entry is added with `source: community`, `path`, `installed_from`, and `version` fields using an atomic write (FR25, FR31, NFR14)

**Given** the config append completes
**When** `manifest.lock` is updated
**Then** it records the skill name, repo URL, and pinned version — enabling reproducible installs (FR26)

**Given** `.nimble/skills/<name>/` is created during install
**When** the directory structure is inspected
**Then** it contains the skill source files and `.venv/` — and `.nimble/` is listed in `.gitignore` except for `manifest.lock` (FR43)

**Given** the file watcher detects the `config.yaml` change after install
**When** the daemon reacts
**Then** it spawns a new pre-warmed worker for the installed skill without requiring `nimble restart`

---

## Epic 7: Launch-Ready — Developer Experience & Ecosystem Artifacts

The template ships with `skill-build.md` (AI authoring contract), a working README with inline skill example, autostart files for both platforms, and a documented security model — everything needed to share the project publicly.

### Story 7.1: `skill-build.md` AI Authoring Contract

As a skill author using an AI coding assistant,
I want a structured authoring contract at `.ai/skill-build.md` that gives the AI everything it needs to scaffold a correct skill in one pass,
So that I can describe my intent in plain English and get a working skill without re-explaining the interface.

**Acceptance Criteria:**

**Given** `.ai/skill-build.md` exists at repo root
**When** an AI coding assistant reads it
**Then** it contains the complete skill interface spec: class structure, all lifecycle methods with signatures, the full `context` object field list, all `tools.*` method signatures with parameter types and return types (FR44)

**Given** a developer describes a skill intent to an AI with `skill-build.md` as context
**When** the AI scaffolds the skill
**Then** the output uses the correct class structure, correct imports, and correct `context` field names — no deprecated fields, no invented methods

**Given** any PR changes the skill interface, `context` object fields, or `tools.*` signatures
**When** the PR is reviewed
**Then** `skill-build.md` must be updated as part of that PR — it is a required artifact, not optional documentation (NFR21)

**Given** `manifest.yaml` spec changes between `api_version` bumps
**When** `skill-build.md` is updated
**Then** it reflects the current `api_version` and notes any fields that changed — so AI-scaffolded skills always target the current API (NFR23)

---

### Story 7.2: Autostart Configuration (systemd + Windows Task Scheduler)

As a user who wants Nimble to start automatically at login,
I want ready-to-use autostart configuration files for both Linux and Windows,
So that I can enable persistent daemon startup without writing service files from scratch.

**Acceptance Criteria:**

**Given** `autostart/nimble.service` exists in the template
**When** a Linux user runs `systemctl --user enable autostart/nimble.service` and reboots
**Then** the Nimble daemon starts automatically at login and is manageable via `systemctl --user start/stop/restart nimble` (FR12, NFR18)

**Given** `autostart/nimble.xml` exists in the template
**When** a Windows user imports it via Task Scheduler
**Then** the Nimble daemon starts at login and is manageable via standard Task Scheduler controls (FR12, NFR18)

**Given** the autostart service is configured and the system restarts unexpectedly
**When** the OS recovers
**Then** the daemon restarts automatically without manual intervention (NFR12)

---

### Story 7.3: README, Security Model, and Inline Skill Example

As a first-time visitor to the Nimble repository,
I want a README that gets me to a working hotkey in under five minutes and explains exactly what the daemon can and cannot access,
So that I can start using Nimble immediately and trust what I'm running.

**Acceptance Criteria:**

**Given** `README.md` exists at repo root
**When** a new user reads the first section
**Then** the first-run sequence (`git clone`, `pip install -r requirements.txt`, `nimble start`) is shown with the expected output — including the startup confirmation notification

**Given** the README contains an inline code example
**When** a developer reads it
**Then** it shows a complete minimal skill class (not a link to a file — inline in the README) with `run(self, context, tools)`, one `tools.*` call, and the corresponding `config.yaml` binding (NFR22)

**Given** the README contains a "Security model" section
**When** a security-conscious user reads it
**Then** it states: the daemon runs as the current user with no elevated privileges; context data is captured only at hotkey-fire time; no background monitoring; no telemetry; `permissions` in `manifest.yaml` are declarative and displayed at install time

**Given** the README links to `.ai/skill-build.md`
**When** a builder wants to write their first skill
**Then** `skill-build.md` is discoverable from the README as the starting point for skill authoring (FR44)
