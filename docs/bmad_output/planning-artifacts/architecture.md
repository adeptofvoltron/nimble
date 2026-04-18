---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-04-16'
inputDocuments:
  - docs/bmad_output/planning-artifacts/prd.md
  - docs/bmad_output/planning-artifacts/product-brief-nimble.md
  - docs/bmad_output/planning-artifacts/research/market-nimble-competitive-landscape-research-2026-04-15.md
  - docs/bmad_output/brainstorming/brainstorming-session-2026-04-16-nimble-template.md
workflowType: 'architecture'
project_name: 'Nimble'
user_name: 'Bernard'
date: '2026-04-16'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements (45 total across 8 areas):**

- **Hotkey & Context Capture (FR1–FR5):** Global hotkey daemon for Linux (X11) and Windows; context snapshot at fire time (selection, clipboard, active_app, mouse_position); Wayland detection; Windows reserved hotkey warning
- **Skill Execution Engine (FR6–FR12):** Load Python skill classes; dispatch to `run(context, tools)`; per-skill venv activation; lifecycle hooks (`on_load`, `on_error`, `on_unload`); `api_version` compatibility check; smart context object with `__getattr__` deprecation; autostart via systemd/Task Scheduler
- **Tool Primitives (FR13–FR19):** `tools.ai.ask()`, `tools.popup.show()`, `tools.clipboard.get/set()`, `tools.tts.speak()`, `tools.input.ask/select()`
- **Distribution & Community Skills (FR20–FR27):** `nimble add <shortcut> <repo-url>`; permissions display + confirmation; per-skill venv creation; pip dep install into venv; conflict detection; auto config append; `manifest.lock` for version pinning; `manifest.yaml` spec
- **Configuration Management (FR28–FR31):** YAML binding config; load-time validation with line-precise errors; `nimble validate` pre-flight; format-safe CLI config append
- **Error Handling & Reliability (FR32–FR36):** Per-skill exception isolation including threaded exceptions; system notification on failure with file + line context; persistent log file; `on_load` failure disables skill with notification
- **Operational CLI (FR37–FR41):** start/stop/restart; list; status; disable; startup confirmation notification
- **Developer Experience (FR42–FR45):** `skills/` vs `.nimble/skills/` separation; `skill-build.md` AI authoring contract; bundled test hotkey

**Non-Functional Requirements (23 total across 5 areas):**

- **Performance:** <200ms hotkey-to-execution (NFR1); <5s cold start (NFR2); <10s `nimble add` excluding pip (NFR3); <50MB RSS at idle with ≤10 skills (NFR4); <50ms venv activation overhead (NFR5)
- **Security & Privacy:** User-level privileges only (NFR6); context captured only at fire time, no continuous monitoring (NFR7); no telemetry (NFR8); explicit install confirmation for permissions (NFR9); auditable source (NFR10)
- **Reliability:** Skill failures never crash daemon including threaded exceptions (NFR11); autostart recovery without manual intervention (NFR12); zero silent failures (NFR13); config preserved on write failure (NFR14); notifications within 500ms of exception catch (NFR15)
- **Integration:** Configurable LLM provider without skill code changes (NFR16); native OS notifications only — no third-party notification dep (NFR17); standard systemd/Task Scheduler lifecycle (NFR18); standard `pip`/`venv` tooling only (NFR19)
- **Maintainability:** OS hotkey capture behind adapter interface, no platform code in core (NFR20); `skill-build.md` updated on every interface change as PR prerequisite (NFR21); readable enough for an unfamiliar Python developer to fork and modify within one hour (NFR22); `api_version` incremented on every breaking change (NFR23)

**Scale & Complexity:**

- Primary domain: System daemon + CLI tooling (Python)
- Complexity level: Medium (no regulated domain, no multi-tenancy — but real OS-level integration, per-skill venv lifecycle, async dispatch, fault isolation)
- Estimated architectural components: ~8 (hotkey capture adapter, context builder, skill loader, dispatch engine, tool registry, venv manager, CLI, notification adapter)

### Technical Constraints & Dependencies

- **Python 3.10+** minimum (determined by pynput/evdev/pywin32 requirements)
- **Linux X11 only in v1** — Wayland deferred to v1.1; Wayland detection + actionable error required at startup
- **No PyPI packaging in v1** — forkable template repo is the distribution model
- **Per-skill venv overhead ≤50ms** — venv activation must not break the 200ms end-to-end latency budget
- **`pynput` / `evdev`** for Linux X11 hotkey capture; **`pywin32`** for Win32 hotkey registration; **`pynput`** for macOS (works natively, no additional dep)
- **Native OS notifications only** — libnotify/D-Bus on Linux, Win32 on Windows, `osascript` on macOS
- **macOS context capture** — `pbpaste` (clipboard), `osascript` (active app), clipboard simulation via `pynput` keyboard (selection) — no extra deps beyond existing requirements
- **No sandboxing in v1** — permissions are declarative only

### Cross-Cutting Concerns Identified

1. **Error handling & notification** — spans daemon dispatch, skill loader, venv manager, CLI, and `on_load` lifecycle; every layer funnels to the same notification + log pipeline with zero silent failures
2. **Cross-platform adaptation** — hotkey capture, OS notifications, autostart (systemd vs Task Scheduler), and file path conventions all vary by platform; each needs an adapter boundary
3. **Configuration state coordination** — daemon and CLI share `config.yaml` and `manifest.lock`; concurrent writes need safe append semantics with rollback on failure (NFR14)
4. **Latency budget management** — the 200ms end-to-end budget is shared across hotkey capture, context build, venv activation, and skill dispatch
5. **Skill lifecycle management** — load, `on_load`, dispatch, `on_error`, `on_unload`, and disable-on-failure span multiple components and need a consistent state machine
6. **Logging & observability** — log file as canonical record + system notification as pointer; both must be reachable from every failure path

### Repository Module Structure

Confirmed structure based on collaborative review:

```
nimble/                          # repo root (forkable GitHub template)
│
├── nimble/                      # core Python package (the daemon engine)
│   ├── __init__.py
│   ├── daemon.py                # main loop, lifecycle management
│   ├── hotkeys/                 # hotkey subsystem — NFR20 adapter seam
│   │   ├── __init__.py
│   │   ├── base.py              # HotkeyAdapter ABC
│   │   ├── x11.py               # X11/Linux implementation
│   │   ├── windows.py           # Windows implementation
│   │   └── macos.py             # macOS implementation (pynput-based)
│   ├── skills/                  # skill loading, lifecycle, venv orchestration
│   │   ├── __init__.py
│   │   ├── loader.py            # discovers + imports skills
│   │   ├── runner.py            # dispatches skills, enforces <200ms budget
│   │   └── registry.py          # in-memory skill registry
│   ├── context/                 # context object assembly
│   │   ├── __init__.py
│   │   └── assembler.py         # builds Context(selection, clipboard, …)
│   ├── tools/                   # tool primitives registry — tools.ai.ask() etc.
│   │   ├── __init__.py
│   │   ├── ai.py
│   │   ├── popup.py
│   │   ├── clipboard.py
│   │   ├── tts.py
│   │   └── input.py
│   ├── manifest/                # manifest.yaml parsing + manifest.lock management
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   └── lock.py
│   └── cli/                     # CLI entry points
│       ├── __init__.py
│       └── commands.py          # start/stop/restart/validate/list/status/disable/add
│
├── skills/                      # author skills (committed to fork)
│   └── example_skill/
│       ├── skill.py
│       └── manifest.yaml
│
├── .nimble/                     # tool-managed runtime dir (gitignored)
│   └── skills/                  # community skills, each with own venv
│
├── .ai/                         # AI authoring artifacts
│   └── skill-build.md           # AI authoring contract — first-class, not docs
│
├── tests/
│   ├── unit/
│   │   └── platform/            # FakeHotkeyAdapter lives here from day one
│   └── integration/
│
├── pyproject.toml               # engine deps only — skill deps go in manifest.yaml
├── nimble.yaml                  # user hotkey config (committed to fork)
└── .gitignore                   # must include .nimble/
```

**Key structural decisions:**
- `hotkeys/` uses an ABC (`HotkeyAdapter`) — not a plugin system; two known targets (X11, Windows), selected at startup via factory in `hotkeys/__init__.py`
- `tools/` package name aligns with the runtime parameter name (`tools.ai.ask()`) — no mismatch between package and interface
- `skill-build.md` in `.ai/` at repo root — first-class AI authoring contract, not documentation
- Platform detection logic belongs in `hotkeys/__init__.py` factory, not in `daemon.py`
- `pyproject.toml` defines engine deps only; skill deps live in per-skill `manifest.yaml` and install into `.nimble/skills/<name>/.venv/`

## Starter Template Evaluation

### Primary Technology Domain

Python system daemon + CLI tooling — no framework starter applies.
The template repo itself is the "starter"; the decisions below are baked
into `pyproject.toml` and the development toolchain inherited by all forks.

### Tooling Stack

| Concern | Choice | Version | Rationale |
|---|---|---|---|
| Build backend | hatchling | 1.29.0 | Modern PEP 517/518, no lockfile opinion, clean editable installs |
| CLI framework | typer | 0.24.1 | Type-annotation-driven, auto-generates help text, built on click |
| Hotkey capture | pynput | 1.8.1 | Cross-platform (X11 + Windows) in one library — v1 mandate |
| Type checking | mypy | 1.20.1 | Standard Python static typing |
| Formatter | black | 26.3.1 | Uncompromising formatter, zero config |
| Linter | flake8 | 7.3.0 | Style guide enforcement |

### pyproject.toml Scaffold

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "nimble"
version = "1.0.0"
description = "Cross-platform Python hotkey daemon"
requires-python = ">=3.10"
dependencies = [
    "typer>=0.24.1",
    "pynput>=1.8.1",
    "pyyaml>=6.0",
    "plyer>=2.1",        # cross-platform system notifications
]

[project.scripts]
nimble = "nimble.cli.commands:app"

[tool.hatch.build.targets.wheel]
packages = ["nimble"]

[tool.black]
line-length = 88
target-version = ["py310"]

[tool.mypy]
python_version = "3.10"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### Architectural Decisions Established by Tooling Stack

**Language & Runtime:** Python 3.10+ minimum; `mypy --strict` enforced across the engine package

**CLI entry point:** `nimble.cli.commands:app` — Typer `app` object; all commands registered as `@app.command()` decorators; help text auto-generated from type annotations and docstrings

**Notifications:** `plyer` for cross-platform system notifications (libnotify on Linux, Win32 on Windows) — satisfies NFR17 without a custom adapter for v1

**Build & install:** `pip install -e .` for local development; `nimble` CLI available immediately after install; no `hatch` CLI required by forks

**Formatting:** Black 2026 stable style (`line-length = 88`, one blank line after imports enforced)

**Note:** `pip install -e ".[dev]"` should be the first implementation story, wiring up the dev toolchain before any daemon code is written.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Daemon process model: pre-warmed subprocess workers
- Per-skill venv activation: subprocess always (all skills)
- Config file: `config.yaml` at repo root
- IPC model: PID file + signals + state file

**Important Decisions (Shape Architecture):**
- Config change detection: file watcher (daemon adapts without restart)
- State persistence: `config.yaml` as source of truth; daemon reacts to changes

**Deferred Decisions (Post-MVP):**
- Subprocess worker pooling per skill (v1 uses one worker per skill)
- Named pipe / socket IPC for richer real-time protocol (v2 if needed)
- PyPI packaging (v2+)

### Daemon Process Model

**Decision:** Listener thread + pre-warmed subprocess workers per skill

**Rationale:** A fresh Python subprocess cold start (~80–150ms) would consume most or all of the 200ms hotkey-to-execution budget (NFR1). Pre-warming solves this: the daemon spawns one persistent worker subprocess per loaded skill at startup, with the correct venv already activated. A hotkey press sends a serialised context payload to the appropriate worker via stdin/stdout; dispatch latency drops to ~5–20ms.

**Architecture:**
```
pynput listener thread
    → hotkey event
    → dispatcher looks up worker for skill
    → writes JSON context payload to worker stdin
    → worker executes skill.run(context, tools)
    → worker writes result/error to stdout
    → dispatcher receives result, triggers notification if needed
    → worker stays alive for next invocation
```

**Worker lifecycle:**
- Spawned at daemon start for each loaded skill (with correct venv activated for community skills)
- If worker process dies unexpectedly → daemon detects via `poll()`, disables skill, fires system notification (NFR13)
- Restarted on `nimble restart` or config reload

**Context serialisation:** context fields (`selection`, `clipboard`, `active_app`, `mouse_position`) serialised as JSON over stdin/stdout — all field types are JSON-native (strings, tuples → arrays)

**Cascading implication:** The context object in the worker process is reconstructed from the JSON payload — the smart-object `__getattr__` deprecation behaviour must be implemented in the worker-side `Context` class, not in the daemon.

### Per-Skill Venv Activation

**Decision:** All skills (author and community) execute in subprocesses

**Rationale:** Consistent with the pre-warmed worker model. Author skills use the daemon's own Python environment (no separate venv); community skills use their `.nimble/skills/<name>/.venv/`. The worker spawn command differs: author skills use `sys.executable`; community skills use `.nimble/skills/<name>/.venv/bin/python` (Linux) or `.nimble/skills/<name>/.venv/Scripts/python.exe` (Windows).

**Isolation guarantee:** A skill exception — including unhandled exceptions in threads spawned within the skill — cannot propagate to the daemon process (NFR11). The worker subprocess is the isolation boundary.

**`sys.path` injection — how community skill workers access `nimble.tools`:**

Community skill workers run under the skill's isolated venv Python, which does not have `nimble` installed. Yet the worker entrypoint must import `nimble.tools` to construct the `ToolRegistry` passed to `skill.run(context, tools)`. The solution is `sys.path` injection at the top of `worker/entrypoint.py`, before any imports:

```python
import sys
from pathlib import Path

# Repo root is always two levels up from worker/entrypoint.py
sys.path.insert(0, str(Path(__file__).parent.parent))

from nimble.tools import ToolRegistry  # importable in any venv
```

This works because:
- The community venv Python executes `worker/entrypoint.py` as a script path — `__file__` is always resolvable to the repo root
- The venv provides the skill's pip dependencies (e.g. `anthropic`); `sys.path` injection provides `nimble.*`
- Skill code never imports `nimble` directly — it only uses the `tools` and `context` objects passed as parameters to `run(context, tools)`

The daemon passes the repo root path to the worker as an environment variable (`NIMBLE_REPO_ROOT`) as a belt-and-suspenders fallback, but `Path(__file__).parent.parent` is the primary mechanism.

### Configuration

**Decision:** `config.yaml` at repo root is the single source of truth for all runtime state

**Scope:**
- Hotkey → skill bindings
- Skill metadata (`source`, `path`, `installed_from`, `version`)
- `disabled: true` flag per skill (written by `nimble disable`)
- AI provider settings (`provider`, `model`, env var name for API key)

**Config change detection:** daemon runs a file watcher on `config.yaml` using `watchdog` (cross-platform inotify/FSEvents/ReadDirectoryChanges abstraction). On change:
1. Parse and validate the new config (line-precise error on parse failure — NFR14)
2. Diff against loaded state: identify added, removed, changed, disabled skills
3. Gracefully shut down affected workers; spawn new workers for added/changed skills
4. Log the reload event; fire a notification only if a skill fails to reload

**`watchdog` version:** to be verified at implementation time via `pip index versions watchdog`

### IPC Model

**Decision:** PID file + OS signals + state file

**PID file:** `~/.nimble/nimble.pid` written at daemon start, deleted on clean shutdown

| CLI command | Mechanism |
|---|---|
| `nimble stop` | Read PID → `SIGTERM` (Linux) / `TerminateProcess` (Windows) |
| `nimble restart` | `nimble stop` + `nimble start` |
| `nimble status` | Read `~/.nimble/state.json` |
| `nimble list` | Read `~/.nimble/state.json` |
| `nimble disable <skill>` | Write `disabled: true` to `config.yaml`; daemon reacts via file watcher |

**State file:** `~/.nimble/state.json` — daemon writes on every state change event (skill loaded, skill failed, skill disabled, daemon start/stop) and on a 5s heartbeat. CLI reads it directly; no IPC round-trip needed.

```json
{
  "pid": 12345,
  "started_at": "2026-04-16T10:00:00Z",
  "daemon_version": "1.0.0",
  "skills": [
    {
      "name": "log-diagnosis",
      "source": "local",
      "binding": "ctrl+shift+d",
      "status": "loaded",
      "worker_pid": 12346
    }
  ]
}
```

**Cascading implication:** `nimble start` must check for a stale PID file (process no longer running) and clean it up before starting — avoids "daemon already running" false positives after a crash.

### LLM Provider Abstraction

**Decision:** `tools.ai` is an abstraction layer configured in `config.yaml`; skill code never references a provider directly (NFR16)

**Config:**
```yaml
ai:
  provider: anthropic       # anthropic | openai | ollama
  model: claude-sonnet-4-6
  api_key_env: ANTHROPIC_API_KEY
```

**Worker-side:** `tools.ai.ask(text, prompt=None)` reads provider config at worker startup, constructs the appropriate client. Changing `provider` or `model` in `config.yaml` triggers a worker reload — skills pick up the new provider without modification.

### Logging

**Decision:** Standard `logging` module with `RotatingFileHandler` at `~/.nimble/nimble.log`

- Log level: `INFO` by default; `DEBUG` via `--debug` flag on `nimble start`
- Rotation: 5MB max, 3 backups
- Every skill exception logged with full traceback; system notification fires as a pointer (NFR13, NFR15)
- Daemon and all worker processes write to the same log file (workers inherit the log path via env var)

## Implementation Patterns & Consistency Rules

### Critical Conflict Points (8 identified)

Areas where AI agents will make different choices if not explicitly specified:
worker IPC protocol, error propagation format, YAML key naming, Python naming,
type annotation coverage, test structure, import style, skill lifecycle signatures.

---

### Naming Patterns

**Python code — snake_case throughout:**
```python
# ✅ correct
def load_skill(skill_path: str) -> SkillWorker: ...
worker_pid: int
config_file: Path

# ❌ wrong
def loadSkill(skillPath: str): ...
workerPid: int
```

**File and module names — snake_case:**
```
nimble/skills/loader.py       ✅
nimble/skills/skillLoader.py  ❌
```

**YAML config keys — snake_case:**
```yaml
# ✅ correct
api_key_env: ANTHROPIC_API_KEY
installed_from: https://github.com/...

# ❌ wrong
apiKeyEnv: ANTHROPIC_API_KEY
installedFrom: https://github.com/...
```

**JSON state file keys — snake_case** (consistent with Python; no camelCase in
`state.json` even though JSON conventionally uses camelCase):
```json
{ "worker_pid": 123, "started_at": "..." }
```

**Constants — UPPER_SNAKE_CASE:**
```python
MAX_DISPATCH_LATENCY_MS = 200
STATE_FILE_PATH = Path.home() / ".nimble" / "state.json"
```

---

### Worker IPC Protocol

**This is the highest-risk conflict point.** Daemon and worker must agree on exact
payload structure. Any deviation causes silent failures.

**Daemon → Worker (stdin, one JSON line per invocation):**
```json
{
  "invocation_id": "uuid4-string",
  "context": {
    "selection": "selected text or empty string",
    "clipboard": "clipboard content",
    "active_app": "application name",
    "mouse_position": [x, y]
  }
}
```

**Worker → Daemon (stdout, one JSON line per response):**
```json
{
  "invocation_id": "uuid4-string",
  "status": "ok",
  "error": null
}
```

**Worker → Daemon (error case):**
```json
{
  "invocation_id": "uuid4-string",
  "status": "error",
  "error": {
    "type": "KeyError",
    "message": "human-readable message",
    "skill_file": "skills/log_diagnosis.py",
    "line": 14
  }
}
```

**Rules:**
- Every message is a single JSON line terminated by `\n` — no multi-line payloads
- `invocation_id` is always a UUID4 generated by the daemon; worker echoes it back
- `status` is always `"ok"` or `"error"` — no other values
- `mouse_position` is always a 2-element array `[x, y]` — never a dict, never null
- `selection` and `clipboard` are always strings — never null (use `""` for empty)

---

### Error Handling Patterns

**Worker error → notification pipeline:**
```python
# ✅ correct pattern in dispatcher
result = worker.dispatch(context)
if result.status == "error":
    notifier.send(
        title=f"Nimble — {skill_name}",
        body=f"{result.error.type}: {result.error.message} in {result.error.skill_file} line {result.error.line}"
    )
    logger.error("Skill %s failed: %s", skill_name, result.error, exc_info=False)
```

**Never catch broad exceptions silently:**
```python
# ❌ wrong — swallows error, violates NFR13
try:
    worker.dispatch(context)
except Exception:
    pass

# ✅ correct — always surface
except Exception as exc:
    notifier.send(...)
    logger.error(...)
```

**Config parse errors — always include line number:**
```python
# ✅ correct
raise ConfigError(f"config.yaml line {mark.line + 1}: {message}")
```

---

### Type Annotation Patterns

`mypy --strict` is enforced. All agents must follow:

```python
# ✅ correct — all parameters and return types annotated
def dispatch(self, context: Context) -> DispatchResult: ...
def load_skill(path: Path, source: SkillSource) -> SkillWorker: ...

# ❌ wrong — missing return type, missing parameter type
def dispatch(self, context): ...
def load_skill(path, source): ...
```

**Use `X | None` only when None is a real valid value:**
```python
worker_pid: int | None = None    # ✅ pid not yet known
active_app: str = ""             # ✅ always a string, never None
```

**Dataclasses for structured data objects:**
```python
@dataclass
class DispatchResult:
    invocation_id: str
    status: Literal["ok", "error"]
    error: SkillError | None = None

@dataclass
class SkillError:
    type: str
    message: str
    skill_file: str
    line: int
```

---

### Import Patterns

**Always use absolute imports** — relative imports are forbidden:
```python
# ✅ correct
from nimble.hotkeys.base import HotkeyAdapter
from nimble.context.assembler import build_context

# ❌ wrong
from .base import HotkeyAdapter
from ..context.assembler import build_context
```

**Import order** (enforced by flake8 + black):
1. stdlib
2. third-party
3. `nimble.*` internal

---

### Test Patterns

**Test location:** `tests/unit/<package>/test_<module>.py` mirrors source structure:
```
nimble/hotkeys/x11.py      → tests/unit/hotkeys/test_x11.py
nimble/skills/loader.py    → tests/unit/skills/test_loader.py
nimble/cli/commands.py     → tests/unit/cli/test_commands.py
```

**Always use `FakeHotkeyAdapter` — never touch real X11/Windows APIs in tests:**
```python
# tests/unit/platform/fake_adapter.py — exists from day one
class FakeHotkeyAdapter(HotkeyAdapter):
    def __init__(self) -> None:
        self.registered: list[str] = []
    def register(self, shortcut: str, callback: Callable) -> None:
        self.registered.append(shortcut)
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

**Integration tests** (`tests/integration/`) may use real filesystem and real subprocess
workers, but never real hotkey capture or real OS notifications.

**Shared fixtures in `tests/conftest.py`:**
```python
@pytest.fixture
def fake_adapter() -> FakeHotkeyAdapter:
    return FakeHotkeyAdapter()

@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    config = tmp_path / "config.yaml"
    config.write_text("skills: []\nbindings: []\n")
    return config
```

---

### Logging Patterns

**Log levels:**
| Level | Use for |
|---|---|
| `DEBUG` | Worker lifecycle events, config reload diffs, dispatch timing |
| `INFO` | Daemon start/stop, skill loaded/unloaded, `nimble add` installs |
| `WARNING` | Reserved hotkey detected, stale PID file cleaned up, deprecated field accessed |
| `ERROR` | Skill execution failure, config parse error, worker died unexpectedly |

**Log message format — always include skill name when relevant:**
```python
# ✅ correct
logger.info("Skill %s loaded (source=%s, binding=%s)", name, source, binding)
logger.error("Skill %s failed: %s at %s:%d", name, exc_type, file, line)

# ❌ wrong — no context
logger.error("Skill failed")
```

---

### All AI Agents MUST:

1. Use snake_case for all Python identifiers, YAML keys, and JSON state file keys
2. Annotate every function parameter and return type (`mypy --strict` compatible)
3. Use absolute imports only (`from nimble.x.y import Z`)
4. Follow the exact worker IPC JSON schema — no field additions without updating both sides
5. Never catch exceptions silently — always route to `notifier.send()` + `logger.error()`
6. Use `FakeHotkeyAdapter` in all unit tests — never real platform APIs
7. Place tests at `tests/unit/<package>/test_<module>.py` mirroring source structure
8. Use `@dataclass` for all structured data (no plain dicts for internal data exchange)

## Project Structure & Boundaries

### Complete Project Directory Structure

```
nimble/                                    # repo root (forkable GitHub template)
│
├── nimble/                                # core Python package
│   ├── __init__.py                        # version, package metadata
│   ├── daemon.py                          # main loop, worker lifecycle orchestration
│   │                                      # FR1–FR5, FR32–FR36, FR41
│   ├── hotkeys/                           # NFR20 adapter seam
│   │   ├── __init__.py                    # platform factory: returns correct adapter
│   │   ├── base.py                        # HotkeyAdapter ABC
│   │   ├── x11.py                         # Linux X11 — pynput keyboard listener
│   │   └── windows.py                     # Windows — pynput keyboard listener
│   │                                      # FR1, FR4, FR5
│   ├── skills/                            # skill lifecycle management
│   │   ├── __init__.py
│   │   ├── loader.py                      # discovers + validates skill classes
│   │   ├── runner.py                      # pre-warmed worker pool, dispatch, IPC
│   │   └── registry.py                    # in-memory: name → SkillWorker
│   │                                      # FR6–FR12, FR32–FR36
│   ├── context/
│   │   ├── __init__.py
│   │   └── assembler.py                   # builds Context snapshot at hotkey-fire time
│   │                                      # FR2, FR11
│   ├── tools/                             # tool primitives — tools.ai.ask() etc.
│   │   ├── __init__.py                    # ToolRegistry dataclass
│   │   ├── ai.py                          # FR13, NFR16
│   │   ├── popup.py                       # FR14
│   │   ├── clipboard.py                   # FR15, FR16
│   │   ├── tts.py                         # FR17
│   │   └── input.py                       # FR18, FR19
│   ├── manifest/
│   │   ├── __init__.py
│   │   ├── parser.py                      # manifest.yaml + config.yaml parse/validate
│   │   └── lock.py                        # manifest.lock read/write, version pinning
│   │                                      # FR27–FR31, NFR14
│   ├── cli/
│   │   ├── __init__.py
│   │   └── commands.py                    # Typer app — all CLI commands
│   │                                      # FR20–FR26, FR37–FR41
│   ├── notifier.py                        # cross-platform system notifications
│   │                                      # NFR13, NFR15, NFR17
│   ├── state.py                           # state.json read/write, PID file management
│   └── watcher.py                         # watchdog config.yaml file watcher
│                                          # FR29, NFR14
│
├── worker/                                # worker subprocess entrypoint
│   ├── __init__.py
│   ├── entrypoint.py                      # stdin/stdout IPC loop, skill execution
│   └── context.py                         # worker-side Context class with __getattr__
│                                          # FR7–FR11 (worker side)
│
├── skills/                                # author skills (committed to fork)
│   └── hello_world/
│       ├── skill.py                       # example skill — ships with template
│       └── manifest.yaml
│
├── .nimble/                               # tool-managed (gitignored)
│   ├── skills/                            # community skills
│   │   └── <skill-name>/
│   │       ├── skill.py
│   │       ├── manifest.yaml
│   │       └── .venv/
│   ├── nimble.pid                         # daemon PID file
│   ├── nimble.log                         # rotating log (5MB × 3)
│   └── state.json                         # daemon + skill runtime state
│
├── .ai/
│   └── skill-build.md                     # AI authoring contract — FR44
│
├── autostart/
│   ├── nimble.service                     # systemd unit file (Linux) — FR12
│   └── nimble.xml                         # Windows Task Scheduler task — FR12
│
├── tests/
│   ├── conftest.py                        # shared fixtures: FakeHotkeyAdapter,
│   │                                      # tmp_config, fake_notifier
│   ├── unit/
│   │   ├── hotkeys/
│   │   │   ├── fake_adapter.py            # FakeHotkeyAdapter (imported by conftest)
│   │   │   ├── test_base.py
│   │   │   ├── test_x11.py
│   │   │   └── test_windows.py
│   │   ├── skills/
│   │   │   ├── test_loader.py
│   │   │   ├── test_runner.py
│   │   │   └── test_registry.py
│   │   ├── context/
│   │   │   └── test_assembler.py
│   │   ├── tools/
│   │   │   ├── test_ai.py
│   │   │   ├── test_popup.py
│   │   │   ├── test_clipboard.py
│   │   │   ├── test_tts.py
│   │   │   └── test_input.py
│   │   ├── manifest/
│   │   │   ├── test_parser.py
│   │   │   └── test_lock.py
│   │   ├── cli/
│   │   │   └── test_commands.py
│   │   ├── worker/
│   │   │   ├── test_entrypoint.py
│   │   │   └── test_context.py
│   │   ├── test_notifier.py
│   │   ├── test_state.py
│   │   └── test_watcher.py
│   └── integration/
│       ├── test_daemon_lifecycle.py       # start/stop/restart with real filesystem
│       ├── test_skill_dispatch.py         # real worker subprocess, fake skill
│       ├── test_nimble_add.py             # full nimble add flow, tmp venv
│       └── test_config_reload.py         # watchdog reload with config mutations
│
├── .github/
│   └── workflows/
│       └── ci.yml                         # lint + typecheck + test on push/PR
│
├── pyproject.toml                         # engine deps, build config, tool config
├── config.yaml                            # user hotkey config (committed to fork)
├── .gitignore                             # must include .nimble/ (except manifest.lock)
└── README.md                              # inline skill example, two-zone model,
                                           # security model, first-run instructions
```

### Architectural Boundaries

**Boundary 1: Daemon ↔ Worker (subprocess IPC)**
- **Protocol:** JSON lines over stdin/stdout (defined in step 5)
- **Daemon side:** `nimble/skills/runner.py` — writes invocation payloads, reads results
- **Worker side:** `worker/entrypoint.py` — reads payloads, executes skill, writes results
- **Constraint:** Nothing above this boundary may import from `worker/`; the worker is an independent process

**Boundary 2: Daemon ↔ CLI (state file + PID file)**
- **Protocol:** `~/.nimble/state.json` (read by CLI), `~/.nimble/nimble.pid` (read by CLI)
- **Daemon side:** `nimble/state.py` — writes state on events + 5s heartbeat
- **CLI side:** `nimble/cli/commands.py` — reads state for `status`/`list`; reads PID for `stop`/`restart`
- **Constraint:** CLI never imports from `nimble/daemon.py` or `nimble/skills/` — only reads files

**Boundary 3: Daemon ↔ Config (file watcher)**
- **Protocol:** `watchdog` events on `config.yaml`
- **Daemon side:** `nimble/watcher.py` watches; `nimble/daemon.py` reacts (reload workers)
- **CLI side:** `nimble/cli/commands.py` writes to `config.yaml` for `disable`/`nimble add`
- **Constraint:** All config writes must use atomic write (write to tmp + rename) to prevent partial reads

**Boundary 4: Platform ↔ Core (hotkey adapter)**
- **Protocol:** `HotkeyAdapter` ABC in `nimble/hotkeys/base.py`
- **Platform side:** `x11.py`, `windows.py` — implement the ABC
- **Core side:** `nimble/daemon.py` — calls only ABC methods, never platform-specific code
- **Constraint:** `nimble/daemon.py` must never import `x11` or `windows` directly; always via factory in `nimble/hotkeys/__init__.py`

### FR Category → File Mapping

| FR Category | FR Numbers | Primary Files |
|---|---|---|
| Hotkey & Context Capture | FR1–FR5 | `nimble/hotkeys/`, `nimble/context/assembler.py`, `nimble/daemon.py` |
| Skill Execution Engine | FR6–FR12 | `nimble/skills/`, `worker/entrypoint.py`, `worker/context.py` |
| Tool Primitives | FR13–FR19 | `nimble/tools/` |
| Distribution & Community Skills | FR20–FR27 | `nimble/cli/commands.py`, `nimble/manifest/` |
| Configuration Management | FR28–FR31 | `nimble/manifest/parser.py`, `nimble/watcher.py`, `nimble/cli/commands.py` |
| Error Handling & Reliability | FR32–FR36 | `nimble/skills/runner.py`, `nimble/notifier.py`, `worker/entrypoint.py` |
| Operational CLI | FR37–FR41 | `nimble/cli/commands.py`, `nimble/state.py` |
| Developer Experience | FR42–FR45 | `skills/hello_world/`, `.ai/skill-build.md`, `README.md` |

### Data Flow

**Hotkey → Skill execution:**
```
pynput (x11.py / windows.py)
  → HotkeyAdapter.callback()
  → daemon.py dispatches to runner.py
  → runner.py assembles context via context/assembler.py
  → runner.py writes JSON payload to worker stdin
  → worker/entrypoint.py reconstructs Context
  → worker/entrypoint.py calls skill.run(context, tools)
  → worker writes JSON result to stdout
  → runner.py reads result
  → if error: notifier.py → system notification + logger
  → state.py updates state.json
```

**`nimble add` flow:**
```
cli/commands.py
  → manifest/parser.py reads remote manifest.yaml
  → displays permissions, awaits confirmation
  → creates .nimble/skills/<name>/.venv/
  → pip installs dependencies into venv
  → manifest/lock.py appends to manifest.lock
  → manifest/parser.py appends to config.yaml (atomic write)
  → watcher.py detects config.yaml change
  → daemon.py spawns new worker for installed skill
```

**`nimble disable` flow:**
```
cli/commands.py
  → manifest/parser.py writes disabled: true to config.yaml (atomic write)
  → watcher.py detects change
  → daemon.py shuts down worker for disabled skill
  → state.py updates state.json: skill status → "disabled"
```

### Cross-Cutting Concerns → Files

| Concern | Files |
|---|---|
| Error handling + notification | `nimble/notifier.py`, `nimble/skills/runner.py`, `worker/entrypoint.py` |
| Logging | `nimble/daemon.py` (setup), all modules (usage), `worker/entrypoint.py` (worker log) |
| Cross-platform adaptation | `nimble/hotkeys/`, `nimble/notifier.py`, `nimble/state.py` (path handling) |
| Config coordination | `nimble/manifest/parser.py`, `nimble/watcher.py`, `nimble/cli/commands.py` |
| Latency budget | `nimble/skills/runner.py` (dispatch timing), `worker/entrypoint.py` (execution) |
| Skill lifecycle state machine | `nimble/skills/registry.py`, `nimble/daemon.py`, `nimble/state.py` |

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** All library choices (pynput, typer, watchdog, plyer, black,
flake8, mypy) target Python 3.10+ with no version conflicts. The pre-warmed subprocess
worker model is consistent with the per-skill venv strategy and the JSON IPC protocol.
The control plane (watchdog file watcher + atomic writes + PID/state files) forms a
coherent, race-condition-resistant design.

**Pattern Consistency:** snake_case naming, absolute imports, `@dataclass` for data
objects, and `mypy --strict` are consistent across the engine, worker, CLI, and test
layers. No contradictory conventions detected.

**Structure Alignment:** The 4 architectural boundaries (daemon↔worker, daemon↔CLI,
daemon↔config, platform↔core) map cleanly to distinct file/package groups. No boundary
is crossed by the wrong layer.

### Requirements Coverage Validation ✅

**Functional Requirements (45/45 covered):**
All 8 FR categories have explicit file mappings. Three implementation notes:

- **FR45 (bundled test hotkey):** `skills/hello_world/` ships with the template and
  must be pre-bound in the template `config.yaml` (e.g. `ctrl+shift+h`) so the test
  hotkey fires immediately after `nimble start` without any user configuration.

- **FR4 + FR5 (platform detection):** Wayland detection lives in
  `nimble/hotkeys/x11.py` (check `$WAYLAND_DISPLAY` at adapter init, raise actionable
  error if XWayland unavailable). Windows reserved hotkey detection lives in
  `nimble/hotkeys/windows.py` (check binding against known reserved combinations at
  worker spawn time, log WARNING).

- **FR35 (thread exception capture in worker):** `worker/entrypoint.py` must set
  `threading.excepthook` at startup to catch exceptions from threads spawned within
  skill `run()` methods. These must be serialised as error responses on stdout, not
  silently lost.

**Non-Functional Requirements (23/23 covered):**
- NFR1 (<200ms): pre-warmed workers eliminate Python cold-start from hotpath ✅
- NFR5 (<50ms venv overhead): venv activated once at worker spawn, not per-invocation ✅
- NFR11 (skill failures don't crash daemon): subprocess boundary enforces this ✅
- NFR14 (config preserved on write failure): atomic write pattern (write tmp + rename) ✅
- NFR20 (OS adapter interface): `HotkeyAdapter` ABC in `nimble/hotkeys/base.py` ✅

### Implementation Readiness Validation ✅

**Decision Completeness:** All critical decisions documented with library versions.
Worker IPC protocol fully specified with exact JSON schemas. The highest-risk
cross-boundary interface has concrete examples and explicit rules.

**Structure Completeness:** Complete file tree defined with FR annotations on every
file. All 4 boundaries have explicit constraints. Data flows documented for the 3 most
complex operations (hotkey dispatch, `nimble add`, `nimble disable`).

**Pattern Completeness:** 8 conflict points identified and resolved. All agents have
unambiguous rules for naming, imports, types, error handling, tests, and logging.

### Gap Analysis Results

**Critical Gaps:** None — all FRs and NFRs have architectural support.

**Implementation Notes (addressed above):**
- FR45: Ship `config.yaml` template with `ctrl+shift+h → hello_world` pre-bound
- FR4/FR5: Platform detection logic explicitly belongs in `hotkeys/x11.py` and `hotkeys/windows.py`
- FR35: `threading.excepthook` must be set in `worker/entrypoint.py` at startup

**Deferred (by design):**
- Wayland-native hotkey support (v1.1)
- PyPI packaging (v2+)
- Per-project config overlay (v2+)
- `nimble publish` / `nimble outdated` CLI commands (v2+)

### Architecture Completeness Checklist

- [x] Project context thoroughly analysed — 45 FRs, 23 NFRs across 8 + 5 categories
- [x] Scale and complexity assessed — medium, single developer, greenfield
- [x] Technical constraints identified — Python 3.10+, X11 only v1, no PyPI v1
- [x] Cross-cutting concerns mapped — 6 concerns, all with owning files
- [x] Critical decisions documented with versions — process model, venv, IPC, config, LLM, logging
- [x] Technology stack fully specified — hatchling 1.29.0, typer 0.24.1, pynput 1.8.1, black 26.3.1, flake8 7.3.0, mypy 1.20.1
- [x] Implementation patterns defined — 8 conflict points resolved
- [x] Complete directory structure defined with FR annotations
- [x] 4 architectural boundaries established with explicit constraints
- [x] Requirements → file mapping complete
- [x] Data flows documented for all major operations

### Architecture Readiness Assessment

**Overall Status: READY FOR IMPLEMENTATION**

**Confidence Level: High**

**Key Strengths:**
- Worker subprocess boundary provides hard fault isolation with zero daemon risk
- Pre-warmed workers solve the 200ms latency constraint definitively
- Atomic config writes + file watcher create a clean, race-safe control plane
- `HotkeyAdapter` ABC enforces the cross-platform boundary at compile time (mypy)
- Worker IPC JSON schema specified to field level — no agent ambiguity

**Areas for Future Enhancement:**
- Wayland-native support (v1.1) will require a new `HotkeyAdapter` implementation
- Worker pool sizing (currently 1 worker per skill) may need tuning for high-frequency skills
- The `tools.ai` abstraction layer could support streaming responses in v2

### Implementation Handoff

**First implementation priority:**
```bash
pip install -e ".[dev]"
```
Wire up the dev toolchain (black, flake8, mypy, pytest) before any daemon code is
written. Verify `nimble` CLI entry point resolves correctly after install.

**Implementation sequence guidance:**
1. `nimble/hotkeys/base.py` — HotkeyAdapter ABC (establishes the platform contract)
2. `nimble/hotkeys/x11.py` + `windows.py` — platform adapters
3. `nimble/context/assembler.py` — Context snapshot builder
4. `worker/context.py` + `worker/entrypoint.py` — worker IPC loop
5. `nimble/skills/runner.py` — pre-warmed worker pool + dispatcher
6. `nimble/tools/` — all tool primitives
7. `nimble/manifest/` — parser + lock
8. `nimble/cli/commands.py` — all CLI commands
9. `nimble/daemon.py` — main loop wiring everything together
10. `autostart/` files — systemd unit + Windows Task Scheduler XML
