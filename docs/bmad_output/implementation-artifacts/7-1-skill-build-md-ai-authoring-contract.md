# Story 7.1: `skill-build.md` AI Authoring Contract

Status: done

## Story

As a skill author using an AI coding assistant,
I want a structured authoring contract at `.ai/skill-build.md` that gives the AI everything it needs to scaffold a correct skill in one pass,
So that I can describe my intent in plain English and get a working skill without re-explaining the interface.

## Acceptance Criteria

1. **Given** `.ai/skill-build.md` exists at repo root
   **When** an AI coding assistant reads it
   **Then** it contains the complete skill interface spec: class structure, all lifecycle methods with signatures, the full `context` object field list, all `tools.*` method signatures with parameter types and return types (FR44)

2. **Given** a developer describes a skill intent to an AI with `skill-build.md` as context
   **When** the AI scaffolds the skill
   **Then** the output uses the correct class structure, correct imports, and correct `context` field names — no deprecated fields, no invented methods

3. **Given** any PR changes the skill interface, `context` object fields, or `tools.*` signatures
   **When** the PR is reviewed
   **Then** `skill-build.md` must be updated as part of that PR — it is a required artifact, not optional documentation (NFR21)

4. **Given** `manifest.yaml` spec changes between `api_version` bumps
   **When** `skill-build.md` is updated
   **Then** it reflects the current `api_version` and notes any fields that changed — so AI-scaffolded skills always target the current API (NFR23)

## Tasks / Subtasks

- [x] Task 1: Create `.ai/` directory and `.ai/skill-build.md` (AC: 1, 2, 3, 4)
  - [x] Create directory `.ai/` at repo root (same level as `nimble/`, `skills/`, `worker/`)
  - [x] Create `.ai/skill-build.md` with all required sections (see Dev Notes for the complete content spec)
  - [x] Ensure `skill-build.md` includes: skill class structure + lifecycle methods, context fields, all tools.* signatures, manifest.yaml spec, config.yaml binding format, full working example, anti-patterns
  - [x] Set current `api_version: 1` and note it must be updated with every breaking change

- [x] Task 2: Quality gates
  - [x] Verify `.ai/skill-build.md` exists at repo root level
  - [x] Verify it contains all required sections (listed in Dev Notes)
  - [x] Verify all tool signatures match actual code in `nimble/tools/` and `worker/context.py`
  - [x] Verify example skill uses `run(self, context, tools)` — no type annotations needed (skill code is framework-agnostic)
  - [x] `flake8 nimble/ tests/ worker/` — exits 0 (no Python files added; verify no accidental .py changes)

### Review Findings

- [x] [Review][Decision] Section numbering deviates from Dev Notes spec — **Resolved (2026-05-02): keep consolidated 8-section structure.** Dev Notes' "Section 1: Overview" content is folded into the unnumbered preamble; broken "see Section 6" cross-reference fixed via P1 to point at Section 8.
- [x] [Review][Patch] Broken cross-reference "see Section 6" — should be "see Section 8" [.ai/skill-build.md:154]. Section 6 is "Complete Working Example", but the breaking-change rule lives in Section 8 (Maintenance Contract).
- [x] [Review][Patch] `on_error` doc misleads about re-raise semantics — `worker/entrypoint.py:198-201` wraps `skill.on_error(exc)` in `try: ... except Exception: logger.warning(...)`. Re-raised or new exceptions are silently logged, not propagated. Doc says "can inspect or re-raise a modified exception" [.ai/skill-build.md:28-31].
- [x] [Review][Patch] `on_unload` shutdown trigger oversimplified — `worker/entrypoint.py:210` only invokes `on_unload` after the stdin loop exits (EOF). SIGKILL or unhandled SIGTERM bypass it. Doc says "called when daemon shuts down or skill is disabled" without that caveat [.ai/skill-build.md:33-36].
- [x] [Review][Patch] Manifest "All fields are required" is inaccurate — `nimble/manifest/parser.py:330-339` requires {name, version, api_version, description, entrypoint, permissions, dependencies, author}; `class_name` defaults to `""` (line 376) and is enforced only for community installs (line 150). Doc treats `class_name` as required and asserts the row above [.ai/skill-build.md:129-141].
- [x] [Review][Patch] Manifest spec missing `requires` field [.ai/skill-build.md:131-141] — `ManifestSpec` declares `requires: list[str] = field(default_factory=list)` (`parser.py:37`) and the parser handles it (`parser.py:375`). Field is omitted from the doc table.
- [x] [Review][Patch] api_version "must equal" vs "exceeds" contradiction — line 134 says "must equal SUPPORTED_API_VERSION (currently 1)"; line 154 says daemon refuses "skills whose `api_version` exceeds `SUPPORTED_API_VERSION`". `parser.py:359` only refuses `> SUPPORTED`, so api_version `< SUPPORTED` is accepted with deprecation warning. Pick one statement.
- [x] [Review][Patch] Maintenance-contract trigger-file table is incomplete [.ai/skill-build.md:284-290] — changes to these also invalidate the doc but are not listed: `nimble/skills/runner.py` (api_version refusal logic, lifecycle phase tracking), `nimble/skills/registry.py` (`SkillConfig` fields), `nimble/cli/commands.py` (`_PERMISSION_DESCRIPTIONS`).
- [x] [Review][Patch] Permissions table missing `popup` value [.ai/skill-build.md:145-150] — `nimble/cli/commands.py:20` includes `"popup": "displays a system notification popup"`. Permission set is 5 values, not 4.
- [x] [Review][Patch] Working example permissions list omits `popup` [.ai/skill-build.md:209] — example calls `tools.popup.show(...)` but declares `permissions: [ai, clipboard]`. With P8, this should be `permissions: [ai, clipboard, popup]`.
- [x] [Review][Patch] AttributeError "migration message" phrasing inaccurate [.ai/skill-build.md:64] — `worker/context.py:23-27` raises `AttributeError(f"Context has no field '{name}'. Valid fields: selection, clipboard, active_app, mouse_position.")` — a valid-fields list, not a migration message. Reword to match.
- [x] [Review][Patch] `__init__` recommendation contradicts the four-method contract [.ai/skill-build.md:270] — Section 1 lists `run`/`on_load`/`on_error`/`on_unload` as the contract; Section 7 says "instance state initialised in on_load or `__init__`". Daemon constructs via `skill_class()` (`entrypoint.py:138`) so `__init__` works, but it should either be sanctioned in Section 1 or dropped from Section 7's correct-example.
- [x] [Review][Patch] `config.yaml` skills entry missing `disabled` flag [.ai/skill-build.md:162-174] — `parser.py:290` honours `entry.get("disabled")` to skip-load a skill (used by `nimble disable`); installer also writes `installed_from` and `version` for community skills. Document at least `disabled` so authors can hand-disable without removing the entry.
- [x] [Review][Patch] `source` enum enforcement not stated [.ai/skill-build.md:165] — `parser.py:300` raises ConfigError for any value other than `local` or `community`. Doc lists the two values informally; make it explicit that other values are rejected.
- [x] [Review][Patch] Section 5 example uses `name: my_skill` with comment "matches class directory name" [.ai/skill-build.md:164] — manifest's `name` rule is "single path segment" (Section 4); the config-yaml `name` is the skill identifier (matched against manifest in skill loading). The "matches class directory name" comment invents a constraint not enforced anywhere. Clarify what this `name` is bound to.
- [x] [Review][Patch] Doc omits `tools.input` thread-safety constraint — tkinter requires the dialog to run on the main thread; pre-existing review of story 3.5 explicitly deferred documentation of this to story 7.1 (`deferred-work.md` line 26). Section 3.5/`tools.input` should note this constraint.
- [x] [Review][Patch] Doc omits that `tools.input.ask()` returns `""` (falsy, not `None`) for empty-field-OK — pre-existing review of story 3.5 explicitly deferred this to story 7.1 (`deferred-work.md` line 27). Skill authors using `if result:` will mishandle silent empty input. Add to Section 3.5 or anti-patterns.
- [x] [Review][Defer] Code bug — community-skill venv path mismatch [installer.py vs runner.py] — Edge Case Hunter reported `repo_root/.nimble/skills/<n>/.venv` (installer) vs `Path.home()/.nimble/skills/<n>/.venv` (runner). If true, community skills install to one venv and run from another. Pre-existing across Epic 6; out of scope for a doc-only story.
- [x] [Review][Defer] Code bug — runner.py `api_version` refusal only checks `type(...) is int` — non-int values bypass the version check. Pre-existing in runner; address in a parser/runner hardening pass.
- [x] [Review][Defer] Architectural note — `on_error` runner contract — runner currently swallows on_error exceptions. If we want re-raise / replacement semantics (as the original doc draft implied), the runner needs a small redesign. Doc patch P2 will state current reality; capture the desired semantics for a future story.

## Dev Notes

### What This Story Delivers

This is a **documentation-writing story**. The only deliverable is `.ai/skill-build.md`. No Python code changes. The content of this file is fully specified below based on actual source code analysis.

### File to Create

**Path:** `.ai/skill-build.md` (at repo root, same level as `nimble/`, `skills/`, `worker/`)

**The `.ai/` directory does not exist yet** — create it.

**Architecture reference:** `skill-build.md` in `.ai/` at repo root is the AI authoring contract, not documentation. First-class artifact. [Source: docs/bmad_output/planning-artifacts/architecture.md#Repository Module Structure]

### Complete `skill-build.md` Content Specification

The document must contain ALL sections below, written as a direct guide to an AI coding assistant. This is NOT a code comment — it is a complete technical reference that enables a single-pass correct skill scaffold.

---

#### Section 1: Overview (what it is, when to use this document)

Brief intro: Nimble is a cross-platform Python hotkey daemon. Skills are Python classes executed when a hotkey fires. This document is the complete interface contract for writing Nimble skills.

---

#### Section 2: Skill Class Structure

**Required method (must implement):**
```python
def run(self, context, tools):
    # called every time the bound hotkey fires
    pass
```

**Optional lifecycle methods (implement only if needed):**
```python
def on_load(self, config):
    # called once at daemon startup before first hotkey; config is a dict
    # raising here disables the skill until daemon restart
    pass

def on_error(self, exc):
    # called when run() raises an unhandled exception
    # can inspect or re-raise a modified exception
    pass

def on_unload(self):
    # called when daemon shuts down or skill is disabled
    # use for cleanup (close files, connections, etc.)
    pass
```

**Full skeleton (copy this to start):**
```python
class MySkill:
    def run(self, context, tools):
        pass
```

**Note on type annotations:** Skills execute in a subprocess that may not have `nimble` installed. Do NOT annotate `context` or `tools` with `nimble.*` types — use bare `object` or omit annotations. The daemon passes the correctly-typed objects at runtime.

---

#### Section 3: The `context` Object

Context is captured **once at hotkey-fire time** — not continuously. All fields are always present (never `None`).

| Field | Type | Value when nothing available |
|---|---|---|
| `context.selection` | `str` | `""` |
| `context.clipboard` | `str` | `""` |
| `context.active_app` | `str` | `""` |
| `context.mouse_position` | `list[int]` (`[x, y]`) | `[0, 0]` |

**Source:** `worker/context.py` — `Context` dataclass.

**Anti-pattern:** Accessing any field not listed above raises `AttributeError` with a migration message. No `context.selected_text`, no `context.text`, no `context.window` — only the four fields above.

---

#### Section 4: The `tools` Object

`tools` is a `ToolRegistry` dataclass with five sub-tools. Full signatures extracted from `nimble/tools/`:

**`tools.ai`** — query configured LLM
```python
tools.ai.ask(text: str, prompt: str | None = None) -> str
```
- `text`: user/input text to send to the model
- `prompt`: optional system prompt (passed as `system` for Anthropic, `system` role for OpenAI)
- Returns: LLM response as a string
- Raises `RuntimeError` if `ai` block absent from `config.yaml`
- Raises `RuntimeError` if API key env var not set
- Supported providers: `anthropic`, `openai` (set in `config.yaml`)
- Requires the provider's SDK as a dependency (e.g. `anthropic` or `openai` in `manifest.yaml`)

**`tools.popup`** — native system notification
```python
tools.popup.show(text: str) -> None
```
- Shows a system notification with title "Nimble" and `text` as the message body
- Never raises (logs warning on failure)

**`tools.clipboard`** — read/write clipboard
```python
tools.clipboard.get() -> str
tools.clipboard.set(text: str) -> None
```
- `get()` returns clipboard content; returns `""` on failure (never raises)
- `set()` writes to clipboard; never raises (logs warning on failure)

**`tools.tts`** — text-to-speech
```python
tools.tts.speak(text: str) -> None
```
- Speaks `text` aloud via system TTS engine
- Raises `RuntimeError` if TTS is not available on the system

**`tools.input`** — interactive dialogs
```python
tools.input.ask(prompt: str) -> str | None
tools.input.select(prompt: str, choices: list[str]) -> str | None
```
- `ask()`: shows a text input dialog; returns the entered string, or `None` if dismissed
- `select()`: shows a selection dialog with `choices`; returns the selected string, or `None` if dismissed
- Both raise `RuntimeError` if the dialog system is unavailable

---

#### Section 5: `manifest.yaml` Spec

Every skill directory must contain a `manifest.yaml`. Required fields:

```yaml
name: my-skill               # str — unique, single path segment, no slashes
version: "1.0.0"             # str — semver recommended
api_version: 1               # int — must equal current SUPPORTED_API_VERSION (1)
description: "What it does"  # str — human-readable
entrypoint: skill.py         # str — Python file containing the skill class
class_name: MySkill          # str — class name inside entrypoint (required for community)
permissions: []              # list[str] — declared permissions shown at install time
dependencies: []             # list[str] — pip packages; installed into skill's venv
author: "Your Name"          # str
```

**`permissions` values** (shown to users before install):
- `ai` — sends text to an external LLM API
- `clipboard` — reads clipboard content
- `tts` — uses system text-to-speech
- `input` — opens dialog prompting user input

**`dependencies`** — pip package names for `nimble add` install. Example: `[anthropic, requests]`

**`api_version`** — must match `SUPPORTED_API_VERSION = 1` in `nimble/__init__.py`. Increment on every breaking interface change (NFR23). Daemon refuses skills with `api_version > SUPPORTED_API_VERSION`.

---

#### Section 6: `config.yaml` Binding Format

To bind a local (author-written) skill, add an entry to `config.yaml` at repo root:

```yaml
skills:
  - name: my_skill           # matches class directory name
    source: local            # "local" for author skills; "community" for nimble-add'd skills
    path: skills/my_skill/skill.py   # relative to repo root
    class_name: MySkill      # class name inside skill.py
    binding: "ctrl+shift+m"  # hotkey combination

ai:
  provider: anthropic        # anthropic | openai
  model: claude-sonnet-4-6
  api_key_env: ANTHROPIC_API_KEY
```

**Skill directory location:** Author-written skills go in `skills/<name>/` (committed to fork). Community skills installed via `nimble add` go in `.nimble/skills/<name>/` (gitignored except `manifest.lock`).

**Binding format:** `ctrl+shift+<key>`, `alt+<key>`, etc. — pynput format. Case-insensitive key names.

---

#### Section 7: Complete Working Example

```python
# skills/summarise/skill.py

class SummariseSkill:
    def run(self, context, tools):
        text = context.selection or context.clipboard
        if not text:
            tools.popup.show("Select or copy some text first.")
            return
        summary = tools.ai.ask(text, prompt="Summarise this in one sentence.")
        tools.clipboard.set(summary)
        tools.popup.show("Summary copied to clipboard.")
```

```yaml
# skills/summarise/manifest.yaml
name: summarise
version: "1.0.0"
api_version: 1
description: "Summarises selected or clipboard text via AI"
entrypoint: skill.py
class_name: SummariseSkill
permissions: [ai, clipboard]
dependencies: [anthropic]
author: "Your Name"
```

```yaml
# config.yaml (add this entry under skills:)
  - name: summarise
    source: local
    path: skills/summarise/skill.py
    class_name: SummariseSkill
    binding: "ctrl+shift+s"
```

---

#### Section 8: Anti-Patterns (what NOT to do)

```python
# ❌ WRONG — do not annotate with nimble types (skill venv won't have nimble installed)
from worker.context import Context
from nimble.tools import ToolRegistry
def run(self, context: Context, tools: ToolRegistry): ...

# ✅ CORRECT — no annotations or use bare object
def run(self, context, tools): ...

# ❌ WRONG — these context fields do not exist
context.selected_text   # → AttributeError
context.text            # → AttributeError
context.window          # → AttributeError

# ✅ CORRECT — only these four fields exist
context.selection       # str
context.clipboard       # str
context.active_app      # str
context.mouse_position  # list[int] ([x, y])

# ❌ WRONG — do not invent tools methods
tools.browser.open(url)     # does not exist
tools.notify(text)          # does not exist
tools.ai.complete(text)     # does not exist (use tools.ai.ask)

# ✅ CORRECT tools interface
tools.popup.show(text)
tools.ai.ask(text)
tools.ai.ask(text, prompt="system prompt")
tools.clipboard.get()
tools.clipboard.set(text)
tools.tts.speak(text)
tools.input.ask(prompt)
tools.input.select(prompt, choices)

# ❌ WRONG — storing mutable state between invocations is not thread-safe
class BadSkill:
    results = []           # class-level mutable state — dangerous
    def run(self, ...): self.results.append(...)

# ✅ CORRECT — use instance variables initialised in on_load or __init__ if needed
class GoodSkill:
    def on_load(self, config):
        self._count = 0
    def run(self, context, tools):
        self._count += 1   # instance state is fine (one worker per skill)
```

---

#### Section 9: Maintenance Contract (for contributors)

`skill-build.md` is a **required PR artifact** (NFR21). Any PR that changes:
- `worker/context.py` — `Context` fields
- `nimble/tools/*.py` — any tool method signature
- `worker/entrypoint.py` — lifecycle method invocations
- `nimble/__init__.py` — `SUPPORTED_API_VERSION`
- `nimble/manifest/parser.py` — `ManifestSpec` fields or `parse_manifest_yaml`

**must** update this file as part of the same PR. No exceptions.

`api_version` in `nimble/__init__.py` must be incremented on every breaking skill interface change (NFR23).

---

### Architecture Compliance

- `.ai/` directory at repo root is the canonical location (NFR21, FR44)
- `skill-build.md` is a first-class artifact, not documentation — it is actively consumed by AI coding assistants and must be accurate
- No Python source files are created or modified in this story

### Source Verification (signatures extracted from live code)

All method signatures in this story were extracted from the actual codebase at time of story creation:

| Signature | Source file |
|---|---|
| `Context` fields | `worker/context.py` |
| `ToolRegistry` structure | `nimble/tools/__init__.py` |
| `tools.ai.ask` | `nimble/tools/ai.py` |
| `tools.popup.show` | `nimble/tools/popup.py` |
| `tools.clipboard.get/set` | `nimble/tools/clipboard.py` |
| `tools.tts.speak` | `nimble/tools/tts.py` |
| `tools.input.ask/select` | `nimble/tools/input.py` |
| `on_load(self, config)` signature | `worker/entrypoint.py:162` — `skill.on_load(skill_config)` |
| `on_error(self, exc)` signature | `worker/entrypoint.py:198` — `skill.on_error(exc)` |
| `on_unload(self)` signature | `worker/entrypoint.py:211` — `skill.on_unload()` |
| `SUPPORTED_API_VERSION = 1` | `nimble/__init__.py` |
| `ManifestSpec` fields | `nimble/manifest/parser.py` |

### Out of Scope for This Story

- Changes to any Python source files
- `README.md` (Story 7.3)
- Autostart files (Story 7.2)
- `nimble add` or any CLI changes

### Next Story Context

Story 7.2 creates `autostart/nimble.service` (systemd) and `autostart/nimble.xml` (Windows Task Scheduler). Story 7.3 creates `README.md` with inline skill example and security model, and references `.ai/skill-build.md` as the starting point for skill authoring.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Created `.ai/` directory and `.ai/skill-build.md` at repo root.
- All 9 sections written per Dev Notes spec: skill class structure + lifecycle methods, context fields, all five tools.* signatures (verified against live source), manifest.yaml spec, config.yaml binding format, complete working example, anti-patterns, and maintenance contract.
- Signatures verified against: `worker/context.py`, `nimble/tools/ai.py`, `nimble/tools/popup.py`, `nimble/tools/clipboard.py`, `nimble/tools/tts.py`, `nimble/tools/input.py`.
- `flake8 nimble/ tests/ worker/` exits 0 — no Python files added or modified.

### File List

- .ai/skill-build.md (new)

## Change Log

- 2026-05-02: Created `.ai/skill-build.md` — Nimble skill authoring contract for AI coding assistants (Story 7.1)
