---
stepsCompleted: ["step-01-init", "step-02-discovery", "step-02b-vision", "step-02c-executive-summary", "step-03-success", "step-04-journeys", "step-05-domain", "step-06-innovation", "step-07-project-type", "step-08-scoping", "step-09-functional", "step-10-nonfunctional", "step-11-polish", "step-12-complete"]
status: complete
completedAt: "2026-04-16"
inputDocuments:
  - docs/bmad_output/planning-artifacts/product-brief-nimble.md
  - docs/bmad_output/planning-artifacts/research/market-nimble-competitive-landscape-research-2026-04-15.md
  - docs/bmad_output/brainstorming/brainstorming-session-2026-04-16-nimble-template.md
  - docs/scratchprd.md
workflowType: 'prd'
classification:
  projectType: developer_tool
  domain: general developer productivity / automation
  complexity: medium
  projectContext: greenfield
---

# Product Requirements Document - Nimble

**Author:** Bernard
**Date:** 2026-04-16

## Executive Summary

Nimble is a cross-platform hotkey daemon for Python developers that executes user-defined skills on keypress — without leaving the current context. It targets Python developers on Linux, Windows, and macOS who automate repetitive tasks (AI queries, text translation, clipboard manipulation, TTS) and are blocked by the platform fragmentation of existing tools: AutoHotkey is Windows-only with a proprietary scripting language; Raycast is macOS-primary with no Linux roadmap; sxhkd is X11-only and actively breaking under the Wayland transition underway across Ubuntu, Fedora, and Arch. No cross-platform, Python-native hotkey skill framework exists. Nimble fills that gap exactly.

Distribution is a forkable template repository, not an installable package. Users fork, write skills as Python classes, and bind them via YAML. Community skills distribute via `nimble add <repo-url>` — git as the distribution layer, no platform account required. An AI tool primitive is a first-class citizen: `tools.ai.ask(context.selection)` triggers an LLM query from anywhere with a single keypress.

### What Makes This Special

Four structural differentiators, each absent in every competitor:

1. **Python-native skill execution** — skills are plain Python classes; no proprietary scripting language, no JavaScript, no LISP config syntax
2. **Cross-platform (Linux, Windows, and macOS)** — Raycast is macOS-primary with no Linux roadmap; AutoHotkey ignores Linux and macOS; sxhkd ignores Windows and macOS. Nimble is the only tool in the category that runs on all three platforms.
3. **AI as a first-class primitive** — `tools.ai.ask()` is a core tool, not a plugin; 74% of developers are integrating AI and no hotkey tool gives them a keyboard-triggered path to it
4. **Ownable, forkable distribution** — `nimble add <repo-url>` uses GitHub as a decentralized workflow registry; developers trust git over any marketplace

The core insight: `nimble add` turns every shared skill repo into a distribution event — a self-reinforcing ecosystem flywheel built on infrastructure developers already use and trust.

The timing is structurally favorable: Python adoption hit 57.9% in 2025 (largest single-year jump of any language), 74% of developers are integrating AI tools, and the Wayland rollout is actively displacing sxhkd users who are searching for alternatives right now. This migration cohort is the most motivated early adopter available.

## Project Classification

- **Project Type:** Developer tool — background daemon distributed as a forkable template repository with a companion CLI
- **Domain:** General developer productivity and automation
- **Complexity:** Medium — no regulated domain requirements, but real cross-platform OS-level integration complexity (global hotkey capture across X11/Wayland/Win32, daemon lifecycle management, process isolation)
- **Project Context:** Greenfield

## Success Criteria

### User Success

- The author has replaced 3 or more previously manual repetitive tasks with Nimble hotkeys in daily use
- Every triggered workflow either produces a correct result or surfaces a clear error notification — no silent failures
- A new workflow can be written, bound, and running without restarting the system in under 15 minutes

### Business Success

- Organic forks and stars from developers the author has no prior relationship with — any signal that the project was discovered and evaluated independently
- 5 or more community-contributed workflows appear on GitHub from non-author contributors within 3 months of launch
- `nimble add <repo-url>` is used in the wild — at least one community workflow is installed via the CLI by a non-author user
- `skill-build.md` proves useful in practice — developers report that an AI assistant can scaffold a new workflow from it with minimal correction

### Technical Success

- Hotkey-to-workflow execution latency under 200ms (perceived as instant)
- Daemon runs stably through normal daily use without requiring manual restarts; systemd (Linux) and Task Scheduler (Windows) handle startup and crash recovery
- Global error handler catches all unhandled workflow exceptions and surfaces them as system notifications — zero silent failures

### Measurable Outcomes

| Outcome | Target | Timeframe |
|---|---|---|
| Author's manual tasks replaced | 3+ | By end of first week of daily use |
| Community contributors | 5+ non-author workflow repos | 3 months post-launch |
| `nimble add` used in wild | 1+ non-author install | 3 months post-launch |
| Daemon stability | No unexplained crashes in daily use | Ongoing |

## User Journeys

### Journey 1: The Builder — Writing Your First Skill

**Persona:** Lena, 32, backend engineer on Linux. She writes Python daily, uses Claude for coding, and has a habit she's been meaning to automate for months: selecting a block of log output, asking Claude what's wrong, and reading the response in a popup. She found Nimble on a HN thread about sxhkd alternatives.

**Opening Scene:** Lena forks the Nimble template on a Tuesday afternoon. The README promises a working hotkey in under five minutes. She runs `pip install -r requirements.txt`, `nimble start` — a confirmation notification fires: "Nimble daemon running." A test hotkey fires, a popup appears. It works. She doesn't stop there.

**Rising Action:** She opens `skill-build.md` at the root of her fork — it's prominently linked from the README as the starting point for building. She describes what she wants to Claude: "Select text, send to Claude with prompt 'what's wrong with this log output?', show response in popup." Claude scaffolds the skill class in one pass — correct structure, correct imports, context field referenced correctly. She drops the file into `skills/`, adds two lines to `config.yaml`, restarts the daemon.

**Climax:** She selects a gnarly stack trace in her terminal, presses `Ctrl+Shift+D`. The popup appears with Claude's diagnosis in under three seconds.

**Resolution:** By end of week, Lena has three skills running in `skills/` — all committed to her fork. She's replaced tasks she was doing manually multiple times a day. She pushes her log-diagnosis skill to a public repo and links it in the HN thread where she found Nimble.

**Requirements revealed:** `skill-build.md` prominently discoverable from README; daemon startup confirmation notification; class-based skill interface; `skills/` directory as author workspace (committed to fork); context object with `selection` field; AI tool primitive; popup tool; YAML binding; daemon restart workflow; `manifest.yaml` for publishing.

---

### Journey 2: The Consumer — Installing a Community Skill

**Persona:** Marcus, 28, data engineer on Windows. He doesn't want to write skills — he wants results. He saw Lena's link in a Reddit thread, clicked through to her log-diagnosis skill repo, and decided he wants it.

**Opening Scene:** Marcus has Nimble running with the default example. He's on Lena's skill repo page. Before running anything, he skims the `manifest.yaml` — permissions, dependencies, entrypoint. He sees `permissions: [ai, popup]` and `dependencies: [anthropic]`. Reasonable. He copies the `nimble add` command.

**Rising Action:** He runs `nimble add ctrl+shift+d github.com/lena/nimble-log-diagnosis`. Nimble reads the manifest, checks for dependency conflicts with existing skills, installs `anthropic`, appends the binding and skill entry to `config.yaml` with `source: community`. He restarts the daemon.

**Climax:** He presses `Ctrl+Shift+D` over a Python traceback in his editor. The popup fires with a diagnosis. He didn't write a single line of Python.

**Resolution:** Marcus has four community skills installed in `.nimble/skills/`, all referenced in his `config.yaml`. His `manifest.lock` is committed so his setup is reproducible on any machine.

**Requirements revealed:** `nimble add` CLI; manifest reading with permissions display; dependency conflict detection at install time; automatic config YAML append with `source: community`; `manifest.lock` for pinned versions; works on Windows; `.nimble/skills/` as tool-managed directory (gitignored except lock file).

---

### Journey 3: The Skill Breaks — Error Recovery

**Persona:** Lena again, six weeks in. She's updated her `anthropic` library and her AI skill silently started failing — the response format changed and her skill is throwing a `KeyError` on the response object.

**Opening Scene:** She presses `Ctrl+Shift+D` over a log block. Nothing. No popup. She tries again. Still nothing.

**Rising Action:** A system notification fires: *"Nimble — log-diagnosis: KeyError: 'content' in skill.py line 14. See ~/.nimble/nimble.log for details."* The daemon is still running. Only this skill failed. She opens `skill.py`, sees the issue immediately — the response structure changed. One-line fix.

**Climax:** She saves the file, restarts the daemon. No errors at startup. She presses the hotkey — the popup fires correctly. Total downtime: four minutes.

**Resolution:** She adds an `on_load` check that validates the API response format on startup. Next time the library changes, she'll know at `nimble start`, not at hotkey-fire time. The system notification on startup reads: *"Nimble — log-diagnosis: on_load failed: unexpected API response shape. Skill disabled until restart."*

**Requirements revealed:** Global error handler that surfaces exceptions as system notifications with file + line context; daemon continues running after single skill failure (per-skill exception isolation at dispatch layer, including `threading.excepthook` for thread exceptions); log file as canonical error record with notification as pointer; `on_load` lifecycle hook for startup validation; startup failure disables the offending skill with clear notification.

---

### Journey 4: The Maintainer — Handling a Breaking Change

**Persona:** Bernard (the author), three months post-launch. He's refactoring the context object — `context.selected_text` is being renamed to `context.selection`. This is a breaking change for any skill using the old field name.

**Opening Scene:** He needs to release v1.1. He knows this will break installed skills using the old name. He wants the error to be informative and self-resolving, not mysterious.

**Rising Action:** Because `context` is a smart object (not a plain dict), he adds a `__getattr__` override: accessing `context.selected_text` raises `AttributeError: "context.selected_text was renamed to context.selection in v1.1 — update your skill."` He updates `skill-build.md` to reflect the new field name, bumps `api_version` in the manifest spec, and releases v1.1.

**Climax:** A user with an old skill upgrades the daemon. The system notification on first hotkey-fire reads: *"Nimble — translate: AttributeError: context.selected_text was renamed to context.selection in v1.1 — update your skill."* The user finds the fix in thirty seconds.

**Resolution:** Two users open GitHub issues quoting the error message. Both close their own issues after reading it. The `skill-build.md` update ensures any AI-scaffolded skills going forward use the correct field name.

**Requirements revealed:** `context` as a smart object with `__getattr__` for deprecation messages (not a plain dict or dataclass); `api_version` field in `manifest.yaml`; compatibility check at load time against daemon's supported API version; `skill-build.md` treated as a living contract, updated with every interface change.

---

### Journey 5: The Abandoner — First 15 Minutes

**Persona:** Dmitri, 35, DevOps engineer on Linux. He found Nimble via a "sxhkd alternatives" Reddit thread. He's skeptical — he's tried three tools in the last six months and abandoned all of them. He gives Nimble 15 minutes.

**Opening Scene:** He forks, clones, runs `pip install -r requirements.txt`. Then `nimble start`. Nothing happens. No confirmation, no error. He checks `ps aux`. The daemon is running — but he doesn't know that.

**Failure Point:** He edits `config.yaml`, adds a binding, restarts. The YAML has a subtle indentation error (spaces vs tabs). The daemon fails to start silently. He waits. Nothing fires. He checks the process — it's gone. No error message, no log hint. He closes the terminal. Nimble loses him here.

**What Should Happen Instead:** `nimble start` prints: *"Daemon started. Press Ctrl+Shift+H to test — a popup should appear."* On YAML error: *"config.yaml line 12: expected block mapping, found tab character. Run \`nimble validate\` to check your config."*

**Resolution (correct path):** With validation feedback, Dmitri fixes the indentation, restarts, sees the confirmation popup. His first hotkey fires. He stays.

**Requirements revealed:** Daemon startup confirmation output (stdout + system notification); YAML validation at load time with line-precise error messages; `nimble validate` command for pre-flight config checking; bundled test hotkey that fires immediately after install to confirm the daemon is working.

---

### Journey 6: The Skeptic — Trust and Permissions

**Persona:** Irina, 38, security engineer on Linux. She's interested in Nimble but will not run arbitrary background software without understanding exactly what it can access and what it sends over the network.

**Opening Scene:** She reads the README. It mentions the AI tool sends text to an LLM API. She wants to know: what data leaves the machine, when, and to where? She also wants to know what the daemon can do — can it read her filesystem? Modify files?

**Rising Action:** The README has a dedicated "Security model" section. It states: the daemon runs as the current user with no elevated privileges; the AI tool sends only the text you explicitly pass via `tools.ai.ask(text)` — no background telemetry, no clipboard sniffing outside an active skill invocation; `permissions` in `manifest.yaml` are declarative and visible before install but not enforced by a sandbox in v1. She reads a community skill's manifest before installing: `permissions: [ai, clipboard]`. She understands what she's accepting.

**Climax:** She installs one community skill after reviewing its source code directly on GitHub. She's comfortable. The install works.

**Resolution:** Irina is a convert — and more importantly, she's the person who writes the "I audited Nimble and here's what I found" blog post that becomes the community's trust anchor.

**Requirements revealed:** Security model documented in README (data flow, privilege level, no telemetry); `permissions` field in `manifest.yaml` displayed during `nimble add` before install confirmation; explicit acknowledgment that v1 permissions are declarative (not sandboxed); source inspection facilitated by manifest linking to skill repo.

---

### Journey Requirements Summary

| Capability Area | Journeys That Reveal It |
|---|---|
| Daemon startup confirmation + test hotkey | Abandoner, Builder |
| YAML validation with line-precise errors + `nimble validate` | Abandoner |
| `skills/` (author-owned) vs `.nimble/skills/` (tool-owned) separation | Builder, Consumer |
| `source: local\|community` tagging in config.yaml | Builder, Consumer |
| `manifest.lock` for pinned community versions | Consumer |
| `nimble add` with manifest preview + dep conflict detection | Consumer, Skeptic |
| Global error handler (per-skill isolation, threading.excepthook) | Skill Breaks |
| Log file as canonical error record | Skill Breaks |
| `on_load` lifecycle hook for startup validation | Skill Breaks |
| `context` as smart object with `__getattr__` deprecation | Maintainer |
| `api_version` in manifest + compatibility check at load | Maintainer |
| `skill-build.md` as living contract (updated with interface changes) | Builder, Maintainer |
| Security model documentation + permissions display | Skeptic |
| AI + popup tool primitives | Builder, Consumer |
| Cross-platform (Linux, Windows, macOS) | Builder (Linux), Consumer (Windows), any macOS user |

## Domain-Specific Requirements

### OS-Level Integration Constraints

**Linux (X11):** Global hotkey capture via `pynput`/`evdev` requires the daemon process to have keyboard event access. On most Linux distributions this means the running user must be a member of the `input` group, or the daemon must be invoked with appropriate permissions. This is a documented install requirement — no privilege escalation is provided or attempted by Nimble. Users on restrictive systems must configure group membership manually.

**Linux (Wayland):** Global hotkey capture is not available through a standard cross-compositor API. Wayland-native support is deferred to v1.1. Users on Wayland-only desktops must run an X11 compatibility layer (XWayland) for v1 to function. The daemon detects Wayland at startup and prints an actionable error if XWayland is unavailable.

**Windows:** Global hotkey registration via `RegisterHotKey` (Win32) cannot capture OS-reserved combinations (`Win+L`, `Ctrl+Alt+Del`, `Win+R`, etc.). Attempts to bind reserved combinations are silently ignored by the OS. Nimble detects this at daemon start and logs a warning for any binding that matches known reserved combinations.

**macOS:** Global hotkey capture via `pynput` works natively on macOS without elevated privileges. Context capture for `clipboard` uses `pbpaste` (always available). `active_app` uses `osascript` (no extra permissions needed). `selection` capture uses clipboard simulation (save clipboard → simulate Cmd+C → read → restore) in v1; users who grant Accessibility access in System Settings → Privacy & Security get more reliable selection capture in a future story.

### Privacy Model

The context object captures `selection`, `clipboard`, `active_app`, and `mouse_position` **only at hotkey-fire time** — there is no continuous background monitoring of any of these values. No data leaves the machine except what a skill explicitly sends (e.g., via `tools.ai.ask(text)`).

**Privacy warning at install time:** When `nimble add` installs a skill whose `manifest.yaml` declares `permissions` that include `ai`, `clipboard`, or `selection`, the CLI displays a warning before completing the install:

```
⚠ This skill requests the following permissions:
  - ai     (may send text to an external LLM API)
  - clipboard (reads clipboard content at hotkey-fire time)

Install anyway? [y/N]
```

The user must explicitly confirm. Permissions are declarative — not enforced by a sandbox in v1 — but they are visible and require acknowledgment.

### Dependency Isolation

Each skill installed via `nimble add` runs in its own isolated Python virtual environment, created and managed by Nimble in `.nimble/venvs/<skill-name>/`. Dependencies declared in `manifest.yaml` are installed into the skill's venv, not the user's system or active Python environment.

**Implications:**
- No dependency conflicts between skills, or between skills and the user's Python environment
- `nimble add` creates the venv and runs `pip install` into it as part of the install flow
- The daemon activates the correct per-skill venv at invocation time
- Disk usage scales with number of installed skills and their dependency trees
- Skills in `skills/` (author-written) run in the daemon's own Python environment; only community-installed skills get isolated venvs

### Known Operational Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Reserved OS hotkey silently not captured (Windows) | Medium | Warn at daemon startup if binding matches known reserved combinations |
| Wayland users have no global hotkey support | High | Document clearly in README; detect Wayland at startup and print actionable error |
| `input` group not configured on Linux | Medium | Daemon startup error message with exact fix command |
| Per-skill venv creation fails (disk space, permissions) | Medium | `nimble add` fails with clear error before modifying config.yaml |
| Skill venv unavailable at hotkey-fire time | Low | Daemon detects missing venv at load time, disables skill with notification |
| macOS Accessibility permission not granted | Low | `selection` falls back to clipboard simulation; document in README |
| macOS Gatekeeper blocks daemon on first run | Low | Document: open System Settings → Privacy & Security → allow nimble |

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. Git as a decentralized skill marketplace (`nimble add <repo-url>`)**
No hotkey or desktop automation tool has used version control infrastructure as its distribution layer. The insight is that developers already trust GitHub — the `nimble add` model turns any public repo into an installable, versioned, auditable unit of automation. This isn't a workaround; it's a deliberate inversion: distribution without a platform, discovery without a marketplace. The ecosystem bootstraps through the same social graph developers already use (stars, forks, HN links).

**2. `skill-build.md` as an AI onboarding contract**
This is a genuinely novel developer experience pattern. Rather than writing documentation that humans read and AI ignores, `skill-build.md` is structured specifically for AI consumption — it gives an LLM assistant a complete interface contract (method signatures, context object shape, tool primitive APIs, good practices) so a developer can describe intent in plain English and get a correct, runnable skill scaffold in one pass. This is "AI as a contributor who's already been onboarded," not "AI as a chatbot you have to re-explain everything to." No comparable pattern exists in any developer tool template today.

**3. Programmable hotkey workflows with rich context injection**
Every existing hotkey tool treats a keypress as a trigger for a command. Nimble treats it as a trigger for a Python function that receives a rich snapshot of the user's current state: selected text, clipboard, active application, mouse position. That context injection layer — combined with a composable tool registry (AI, popup, TTS, clipboard, input dialog) — creates a new programming model: *ambient automation*. The developer writes once; the skill runs correctly in any application context.

**4. AI as a composable tool primitive (not a product feature)**
Raycast has AI features. GitHub Copilot is an AI product. Nimble has `tools.ai.ask(text)` — a one-line primitive you write against, compose with other tools, and trigger from a global hotkey. AI is a tool in a toolkit, not the product itself. This framing scales to any LLM, any use case, any context — because it's a framework, not a feature.

### Market Context & Competitive Landscape

The gap is confirmed uncontested by the market research: no cross-platform, Python-native hotkey workflow daemon exists. The `nimble add` distribution model has no direct analogue. The closest comparison is `pip` + GitHub for Python packages, but applied to interactive desktop automation rather than library code. The `skill-build.md` AI authoring pattern has no known precedent in any developer tooling.

### Validation Approach

| Innovation | Validation Signal | Timeframe |
|---|---|---|
| `nimble add` ecosystem model | 5+ community skills from non-author contributors | 3 months post-launch |
| `skill-build.md` AI authoring contract | Developers report AI scaffolds correct skills with minimal correction | First month of use |
| Context injection + tool registry | Author replaces 3+ manual tasks in first week | Week 1 of daily use |
| AI primitive composability | Community builds AI-powered skills without forking core | 2 months post-launch |

### Risk Mitigation

| Innovation Risk | Mitigation |
|---|---|
| `nimble add` trust problem blocks adoption | Declarative permissions + install-time warning; audit-friendly manifest |
| `skill-build.md` drifts from codebase | Treat as first-class artifact; breaking changes require `skill-build.md` update as PR prerequisite |
| AI primitive API changes make skills fragile | `tools.ai` is an abstraction layer — swap the underlying model/provider without changing skill code |
| "New paradigm" takes too long to explain at launch | Lead with the demo, not the concept — a working AI hotkey in the README's first 20 lines is self-explanatory |

## Developer Tool Specific Requirements

### Project-Type Overview

Nimble is a developer tool distributed as a forkable GitHub template repository. In v1, there is no PyPI package — the fork model is intentional and load-bearing: it gives users full ownership of their configuration, skills, and daemon setup. PyPI distribution is a future consideration (v2+). The tool is editor-agnostic by design; no IDE integration is planned. The `skill-build.md` authoring contract covers the AI-assisted authoring experience across all editors.

### Language Matrix

| Language | Support | Notes |
|---|---|---|
| Python 3.10+ | Full | Only supported language for skill authoring |
| Other languages | None | Out of scope — skills are Python classes or functions |

Python version minimum is determined by the oldest supported version across the daemon's dependencies (`pynput`, `evdev`, `pywin32`). Documented minimum: Python 3.10+.

### Installation Methods

| Method | Status | Notes |
|---|---|---|
| Fork GitHub template | ✅ v1 | Primary installation path |
| `pip install nimble` (PyPI) | 🔜 v2+ | v1 constraint — not yet packaged |
| `nimble add <shortcut> <repo-url>` | ✅ v1 | Community skill installation only, not daemon install |

**First-run installation sequence (v1):**
```
git clone <your-fork>
pip install -r requirements.txt
nimble start
# Confirmation notification fires: "Nimble daemon running."
```

The `requirements.txt` pins the daemon's core dependencies. Skill dependencies are installed into per-skill venvs by `nimble add` — they never touch `requirements.txt`.

### API Surface

**Skill interface (class-based):**
```python
class MySkill:
    def on_load(self, config): ...      # optional — startup validation
    def run(self, context, tools): ...  # required — hotkey handler
    def on_error(self, exc): ...        # optional — pre-handler error enrichment
    def on_unload(self): ...            # optional — cleanup on daemon stop
```

**Context object fields:**
```python
context.selection      # str — currently selected text (empty string if none)
context.clipboard      # str — current clipboard content
context.active_app     # str — name of the active application
context.mouse_position # tuple[int, int] — (x, y) cursor coordinates; enables positional popups and app-zone-aware skills
```

`context` is a smart object — accessing a deprecated field raises `AttributeError` with a migration message rather than a silent `KeyError`.

**Tool primitives:**
```python
tools.ai.ask(text, prompt=None)    # Send text to configured LLM, return response
tools.popup.show(text)             # Display result in a popup near cursor
tools.clipboard.get()              # Read clipboard
tools.clipboard.set(text)          # Write to clipboard
tools.tts.speak(text)              # Text-to-speech
tools.input.ask(prompt)            # Show input dialog, return user string
tools.input.select(prompt, options)# Show selection dialog, return chosen option
```

**Manifest spec (`manifest.yaml`):**
```yaml
name: my-skill
version: 1.0.0
api_version: 1          # Nimble API version this skill was written against
description: What this skill does
entrypoint: skill.py::MySkill   # file::ClassName OR file::function_name
requires: [selection]           # context fields this skill needs
permissions: [ai, popup]        # declared permissions shown at install time
dependencies: [anthropic]       # pip packages installed into skill venv
author: github.com/user
```

**YAML config binding:**
```yaml
skills:
  - name: log-diagnosis
    source: local                  # local | community
    path: skills/log_diagnosis.py

  - name: gh-pr
    source: community
    path: .nimble/skills/gh_pr/skill.py
    installed_from: https://github.com/user/nimble-gh-pr
    version: "1.2.0"

bindings:
  - shortcut: ctrl+shift+d
    skill: log-diagnosis
```

### Code Examples

The v1 template ships with **no bundled example skills** in `skills/`. The `skill-build.md` authoring contract serves as the primary onboarding path for builders — a developer describes intent to an AI assistant, which scaffolds a working skill using the documented interface.

The README must include at minimum one inline code example (not a runnable file) showing a complete minimal skill to establish the pattern for first-time readers.

### Migration Guide

Skills declare `api_version` in their manifest. The daemon checks compatibility at load time:

| Scenario | Behaviour |
|---|---|
| `api_version` matches daemon's supported version | Skill loads normally |
| `api_version` lower than supported (old skill, new daemon) | Loads with deprecation warning in log; deprecated fields raise `AttributeError` with migration message at access time |
| `api_version` higher than supported (skill ahead of daemon) | Daemon refuses to load skill, fires notification: "Skill requires Nimble api_version X — upgrade your daemon" |

`skill-build.md` is the migration guide for skill authors — updated on every interface change as a PR prerequisite. The CHANGELOG documents breaking changes with the exact `api_version` bump that introduced them.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Experience MVP — the bar is a working daemon that makes the author say "I would miss this if it were gone." Personal utility is the primary validation signal. Community adoption is the growth signal.

**Resource Requirements:** Single developer (the author). No external dependencies, no team coordination overhead. Build time is self-paced.

### MVP Feature Set — v1

**Core User Journeys Supported:**
- The Builder — forks repo, writes first skill via `skill-build.md` + AI scaffolding
- The Consumer — discovers and installs community skill via `nimble add`
- The Skill Breaks — error surfaces clearly, daemon survives, user fixes in minutes
- The Maintainer — breaking changes communicated via deprecation errors

**Must-Have Capabilities:**

*Daemon Core*
- Global hotkey daemon for Linux (X11) and Windows
- Context builder: `selection`, `clipboard`, `active_app`, `mouse_position` captured at hotkey-fire time
- Class-based skill interface: `run(context, tools)` with optional `on_load`, `on_error`, `on_unload`
- `context` as smart object with `__getattr__` deprecation support
- YAML config: shortcut → skill mapping with `source: local|community` tagging
- systemd service (Linux) and Task Scheduler (Windows)

*Tool Primitives*
- `tools.ai.ask()` — LLM query with configurable provider
- `tools.popup.show()` — popup near cursor
- `tools.clipboard.get()` / `tools.clipboard.set()`
- `tools.tts.speak()`
- `tools.input.ask()` / `tools.input.select()`

*Reliability & Error Handling*
- Global error handler: per-skill exception isolation, `threading.excepthook` coverage
- System notification on skill failure with file + line context
- Log file (`~/.nimble/nimble.log`) as canonical error record
- Daemon startup confirmation notification + bundled test hotkey
- YAML validation at load time with line-precise error messages
- `nimble validate` pre-flight config check

*Distribution & Community*
- `skills/` (author-owned, committed) vs `.nimble/skills/` (tool-owned, gitignored) directory structure
- `manifest.yaml` per-skill spec (`name`, `version`, `api_version`, `entrypoint`, `requires`, `permissions`, `dependencies`, `author`)
- `manifest.lock` for pinned community skill versions
- `nimble add <shortcut> <repo-url>`: reads manifest, displays permissions warning, creates per-skill venv, installs pip deps, appends to config
- Per-skill Python virtual environments in `.nimble/venvs/<skill-name>/`
- Dependency conflict detection within per-skill venv at install time

*Operational CLI*
- `nimble start` / `nimble stop` / `nimble restart`
- `nimble validate` — config validation without starting daemon
- `nimble list` — show all loaded skills with source, binding, and status
- `nimble status` — daemon health + per-skill load state
- `nimble disable <skill>` — disable a skill without editing YAML manually

*Developer Experience*
- `skill-build.md` AI authoring contract — complete interface spec for AI-assisted skill scaffolding
- `api_version` compatibility checking at load time
- README inline code example showing a minimal complete skill

*Security & Privacy*
- Permissions declared in `manifest.yaml`, displayed at `nimble add` install time with explicit confirmation
- Security model documented in README (data flow, privilege level, no telemetry)
- Wayland detection at startup with actionable error message

### Post-MVP Features

**v1.1:**
- Function-style skills (`def run(context, tools)`) alongside class-based skills
- Skill chaining with pipe syntax (`skillA | {field_mapping} | skillB`)
- Wayland-native global hotkey support

**v2+:**
- Per-project `.nimble/` config overlay (context-aware hotkeys per working directory)
- Bundled showcase skills (translate, AI query, summarize, TTS read-aloud)
- Community skill discovery layer (GitHub topic tags or lightweight index)
- `nimble publish` — package and push a skill to GitHub from the CLI
- `nimble outdated` — detect community skills with newer versions available
- Optional workflow signing / sandboxing
- PyPI package distribution

### Risk Mitigation Strategy

| Risk Type | Risk | Mitigation |
|---|---|---|
| Technical | Per-skill venv creation adds complexity to `nimble add` | Implement as the only dependency model from day one — no "shared env" fallback to maintain |
| Technical | Global hotkey capture behaves differently on each platform | OS adapter abstraction isolates platform code; Linux and Windows tested independently |
| Market | Launch timing — sxhkd migration window is time-bounded | Ship before Wayland displacement is complete; Wayland support in v1.1 while momentum is high |
| Market | No community skills at launch (cold start) | Target builders first; `skill-build.md` lowers contribution bar; author seeds 2-3 skills on day one |
| Resource | Single developer scope creep | v1/v1.1/v2 line is explicit — any feature not in v1 list is v2 by default |

## Functional Requirements

### Hotkey & Context Capture

- **FR1:** The daemon can capture global keyboard shortcuts triggered from any application context on Linux (X11) and Windows
- **FR2:** The daemon can build a context snapshot at hotkey-fire time containing selected text, clipboard content, active application name, and mouse position
- **FR3:** The daemon can map keyboard shortcut bindings to skills via YAML configuration
- **FR4:** The daemon can detect a Wayland environment at startup and surface an actionable error message with remediation steps
- **FR5:** The daemon can detect Windows OS-reserved hotkey combinations and warn the user at startup

### Skill Execution Engine

- **FR6:** The daemon can load Python skill classes from user-specified file paths at startup
- **FR7:** The daemon can dispatch a hotkey event to the corresponding skill's `run()` method with context and tools
- **FR8:** The daemon can activate a skill's isolated virtual environment before skill execution
- **FR9:** Skills can declare optional lifecycle methods (`on_load`, `on_error`, `on_unload`) that the daemon invokes at defined points in the daemon lifecycle
- **FR10:** The daemon can check a skill's declared `api_version` against the supported version at load time and refuse to load incompatible skills with a clear notification
- **FR11:** The context object can surface accesses to deprecated field names with a migration message instead of a silent key error
- **FR12:** The daemon can be configured to start automatically at system login on Linux and Windows

### Tool Primitives

- **FR13:** Skills can query a configured LLM with arbitrary text and receive a text response
- **FR14:** Skills can display a text popup near the current cursor position
- **FR15:** Skills can read the current clipboard content
- **FR16:** Skills can write content to the clipboard
- **FR17:** Skills can speak text aloud via the system text-to-speech engine
- **FR18:** Skills can prompt the user for a text input via a dialog and receive the entered string
- **FR19:** Skills can prompt the user to select from a list of options via a dialog and receive the chosen selection

### Distribution & Community Skills

- **FR20:** Users can install a community skill from a GitHub repository URL with a single CLI command specifying the shortcut and repository
- **FR21:** The CLI can display a skill's declared permissions to the user and require explicit confirmation before completing installation
- **FR22:** The CLI can create an isolated Python virtual environment for each community-installed skill
- **FR23:** The CLI can install a skill's declared pip dependencies into its isolated virtual environment
- **FR24:** The CLI can detect dependency conflicts within a skill's virtual environment at install time and abort with a clear error
- **FR25:** The CLI can automatically append a skill binding and entry to the YAML configuration after successful installation
- **FR26:** Users can lock community skill versions to ensure reproducible installs across machines
- **FR27:** Each community skill can declare its name, version, API version, entrypoint, required context fields, permissions, pip dependencies, and author in a manifest file

### Configuration Management

- **FR28:** Users can define skill bindings, source tagging, and skill metadata via a YAML configuration file
- **FR29:** The daemon can validate configuration file syntax at load time and report errors with line-precise messages
- **FR30:** Users can run a pre-flight configuration validation without starting the daemon
- **FR31:** The CLI can append new skill entries to the configuration file in a structured, format-safe manner

### Error Handling & Reliability

- **FR32:** The daemon can continue operating after an unhandled exception in any single skill without restarting
- **FR33:** The daemon can surface skill exceptions as system notifications containing the skill name, exception type, and source location
- **FR34:** The daemon can write full error details and stack traces to a persistent log file
- **FR35:** The daemon can catch unhandled exceptions from threads spawned within skills
- **FR36:** The daemon can disable a skill that raises an exception during its `on_load` check and surface a startup notification identifying the skill and error

### Operational CLI

- **FR37:** Users can start, stop, and restart the daemon via CLI commands
- **FR38:** Users can list all configured skills with their source, binding, and current load status
- **FR39:** Users can view the daemon's operational health and each skill's runtime state
- **FR40:** Users can disable a specific skill without manually editing the YAML configuration
- **FR41:** The daemon can fire a confirmation notification on successful startup

### Developer Experience & Ecosystem

- **FR42:** Author-written skills can be stored in a dedicated directory that is tracked in the user's fork
- **FR43:** Community-installed skills can be stored in a tool-managed directory separate from author-written skills
- **FR44:** The template repository can provide a structured AI authoring contract file containing the complete skill interface specification for use with AI coding assistants
- **FR45:** Users can verify a correct daemon installation via a built-in test hotkey that confirms the daemon is running and responsive

## Non-Functional Requirements

### Performance

- **NFR1:** Hotkey-fire to skill execution start latency must be under 200ms on both Linux and Windows under normal system load
- **NFR2:** Daemon startup time (cold start to first hotkey ready) must complete within 5 seconds on a standard developer machine
- **NFR3:** `nimble add` skill installation (excluding pip download time) must complete within 10 seconds
- **NFR4:** The daemon must not consume more than 50MB of RSS memory at idle with 10 or fewer skills loaded
- **NFR5:** Per-skill venv activation overhead must not contribute more than 50ms to the hotkey-to-execution latency budget

### Security & Privacy

- **NFR6:** The daemon must run with standard user-level privileges only — no elevated permissions, no setuid, no capability bits beyond what is required for keyboard capture on Linux
- **NFR7:** Context data (`selection`, `clipboard`, `active_app`, `mouse_position`) must be captured only at hotkey-fire time — no continuous background monitoring of any context field
- **NFR8:** No telemetry, usage data, or diagnostic information may be transmitted anywhere without explicit user action
- **NFR9:** The `nimble add` command must display all declared skill permissions and require explicit user confirmation before modifying the filesystem or configuration
- **NFR10:** Community skill source code must be retrievable and auditable by the user before or after installation (no obfuscated or pre-compiled-only distribution)

### Reliability

- **NFR11:** A skill-level exception must not crash or restart the daemon — per-skill failure isolation must be maintained for all exception types including those raised in spawned threads
- **NFR12:** The daemon must recover to full operation after a system restart without manual intervention when configured for autostart
- **NFR13:** The daemon must not produce silent failures — every error condition (skill failure, startup warning, incompatible skill, Wayland detection) must surface a user-visible notification or log entry
- **NFR14:** YAML configuration corruption introduced by `nimble add` must be detectable at write time before the daemon is affected — the existing config must be preserved on any write failure
- **NFR15:** System notifications for skill errors must be delivered within 500ms of the exception being caught

### Integration

- **NFR16:** The AI tool primitive must support configurable LLM providers — changing the underlying model or API endpoint must not require modifying skill code
- **NFR17:** System notifications must use the native OS notification mechanism (libnotify/D-Bus on Linux, Win32 notifications on Windows) — no third-party notification dependency
- **NFR18:** The systemd service unit and Windows Task Scheduler task must support standard start/stop/restart lifecycle operations without daemon-specific tooling
- **NFR19:** The per-skill venv model must be compatible with standard Python virtual environment tooling (`pip`, `venv`) — no proprietary package management required

### Maintainability

- **NFR20:** The OS-specific hotkey capture implementation must be isolated behind an adapter interface — the core daemon must contain no platform-specific code
- **NFR21:** `skill-build.md` must be updated as part of any pull request that changes the skill interface, context object fields, or tool primitive signatures — this is a required artifact, not optional documentation
- **NFR22:** The codebase must be readable and self-contained enough for a Python developer who did not write it to fork and modify a skill or tool primitive within one hour of first reading
- **NFR23:** The `api_version` field in `manifest.yaml` must be incremented on every breaking change to the skill interface — no silent breaking changes
