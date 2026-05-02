# Nimble Skill Authoring Contract

This document is the complete interface contract for writing Nimble skills. Read it before scaffolding a skill. It is kept in sync with the live codebase — if anything here contradicts the source, this file is wrong and should be updated.

**What is Nimble?** A cross-platform Python hotkey daemon. When a hotkey fires, Nimble runs your skill class in a subprocess and passes it the `context` and `tools` objects described here. Skills are plain Python — no framework imports required.

---

## 1. Skill Class Structure

**Required method — implement this:**

```python
def run(self, context, tools):
    # called every time the bound hotkey fires
    pass
```

**Optional lifecycle methods — implement only if needed:**

```python
def on_load(self, config):
    # called once at daemon startup before the first hotkey fires
    # config is a dict from the skill's config.yaml entry
    # raising here disables the skill until daemon restart
    pass

def on_error(self, exc):
    # called when run() raises an unhandled exception
    # may inspect or log; raising here is caught and logged but NOT propagated
    # the original exception is reported to the daemon regardless
    pass

def on_unload(self):
    # called on graceful shutdown (stdin EOF) or when the skill is disabled
    # SIGKILL or unhandled signals may bypass this — do not rely on it for critical cleanup
    # use for: closing files, connections, etc.
    pass
```

**Minimal skeleton (start here):**

```python
class MySkill:
    def run(self, context, tools):
        pass
```

**Type annotation rule:** Skills execute in a subprocess that may not have `nimble` installed. Do NOT annotate `context` or `tools` with `nimble.*` types. Use bare `object` or omit annotations entirely. The daemon injects the correctly-typed objects at runtime.

---

## 2. The `context` Object

Captured once at hotkey-fire time — not a live view. All four fields are always present and never `None`.

| Field | Type | Value when nothing available |
|---|---|---|
| `context.selection` | `str` | `""` |
| `context.clipboard` | `str` | `""` |
| `context.active_app` | `str` | `""` |
| `context.mouse_position` | `list[int]` (`[x, y]`) | `[0, 0]` |

**Source:** `worker/context.py` — `Context` dataclass.

Accessing any field not in the table above raises `AttributeError` listing the four valid fields (e.g. `Context has no field 'selected_text'. Valid fields: selection, clipboard, active_app, mouse_position.`). There is no `context.selected_text`, `context.text`, or `context.window`.

---

## 3. The `tools` Object

`tools` is a `ToolRegistry` dataclass (`nimble/tools/__init__.py`) with five sub-tools.

### `tools.ai` — query configured LLM

```python
tools.ai.ask(text: str, prompt: str | None = None) -> str
```

- `text`: user/input text to send to the model
- `prompt`: optional system prompt (`system` param for Anthropic; `system` role message for OpenAI)
- Returns: LLM response as a string
- Raises `RuntimeError` if the `ai` block is absent from `config.yaml`
- Raises `RuntimeError` if the API key env var is unset
- Supported providers: `anthropic`, `openai` (configured in `config.yaml`)
- Requires the provider SDK as a `manifest.yaml` dependency (e.g. `anthropic` or `openai`)

### `tools.popup` — native system notification

```python
tools.popup.show(text: str) -> None
```

- Shows a system notification with title "Nimble" and `text` as the body
- Never raises (logs a warning on failure)

### `tools.clipboard` — read/write clipboard

```python
tools.clipboard.get() -> str
tools.clipboard.set(text: str) -> None
```

- `get()` returns clipboard content; returns `""` on failure (never raises)
- `set()` writes to clipboard; never raises (logs a warning on failure)

### `tools.tts` — text-to-speech

```python
tools.tts.speak(text: str) -> None
```

- Speaks `text` aloud via the system TTS engine
- Raises `RuntimeError` if TTS is not available on this system

### `tools.input` — interactive dialogs

```python
tools.input.ask(prompt: str) -> str | None
tools.input.select(prompt: str, choices: list[str]) -> str | None
```

- `ask()`: text input dialog; returns the entered string (may be `""` if the user pressed OK with an empty field), or `None` if dismissed/cancelled. Use `if result is None:` to distinguish dismissal from empty input — `if result:` will mishandle empty-OK as cancellation.
- `select()`: selection dialog with `choices`; returns the selected string, or `None` if dismissed
- Both raise `RuntimeError` if the dialog system is unavailable
- **Threading constraint:** the underlying tkinter dialog must run on the process main thread. Calling `ask()`/`select()` from a non-main thread produces a `RuntimeError` (the wrapped tkinter error message is misleading). One worker = one main thread, so this is normally fine.

---

## 4. `manifest.yaml` Spec

Every skill directory must contain a `manifest.yaml`. The following fields are **required** (parser raises `ManifestError` if missing):

```yaml
name: my-skill               # str — unique, single path segment, no slashes
version: "1.0.0"             # str — semver recommended
api_version: 1               # int — must be ≤ SUPPORTED_API_VERSION (currently 1)
description: "What it does"  # str — human-readable
entrypoint: skill.py         # str — Python file containing the skill class
permissions: []              # list[str] — declared permissions shown at install time
dependencies: []             # list[str] — pip packages installed into skill's venv
author: "Your Name"          # str
```

Optional fields:

```yaml
class_name: MySkill          # str — class name inside entrypoint. Required for community-skill install
                             # (nimble add); optional for local skills (the config.yaml entry's class_name
                             # is used at runtime).
requires: []                 # list[str] — reserved for future inter-skill dependencies; parsed but not
                             # currently enforced by the daemon. Safe to omit.
```

**`permissions` values** (shown to users before community-skill install):

| Value | Meaning |
|---|---|
| `ai` | sends text to an external LLM API |
| `clipboard` | reads/writes clipboard content |
| `tts` | uses system text-to-speech |
| `input` | opens a dialog prompting user input |
| `popup` | displays a system notification popup |

**`dependencies`** — pip package names for `nimble add` install. Example: `[anthropic, requests]`

**`api_version`** — must be ≤ `SUPPORTED_API_VERSION` in `nimble/__init__.py` (currently `1`). The daemon refuses skills whose `api_version` exceeds `SUPPORTED_API_VERSION`; skills targeting an earlier version load with a deprecation warning. Increment on every breaking interface change (see Section 8).

---

## 5. `config.yaml` Binding Format

To bind an author-written (local) skill, add an entry under `skills:` in `config.yaml` at repo root:

```yaml
skills:
  - name: my_skill                        # skill identifier (matches the manifest.yaml `name`)
    source: local                          # "local" or "community" — other values raise ConfigError
    path: skills/my_skill/skill.py        # relative to repo root
    class_name: MySkill                   # class name inside skill.py
    binding: "ctrl+shift+m"               # hotkey — pynput format, case-insensitive
    disabled: false                        # optional — set true to skip-load this skill (set by `nimble disable`)

ai:
  provider: anthropic                     # anthropic | openai
  model: claude-sonnet-4-6
  api_key_env: ANTHROPIC_API_KEY
```

**Note:** Community-skill installs (`nimble add`) also write `installed_from` (repo URL) and `version` fields to the entry. These are managed by the installer and not authored by hand.

**Skill directory layout:**
- Author skills → `skills/<name>/` (committed to your fork)
- Community skills installed via `nimble add` → `.nimble/skills/<name>/` (gitignored except `manifest.lock`)

**Binding format:** `ctrl+shift+<key>`, `alt+<key>`, etc. — pynput key names, case-insensitive.

---

## 6. Complete Working Example

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
permissions: [ai, clipboard, popup]
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

## 7. Anti-Patterns

```python
# WRONG — do not annotate with nimble types (skill venv won't have nimble installed)
from worker.context import Context
from nimble.tools import ToolRegistry
def run(self, context: Context, tools: ToolRegistry): ...

# CORRECT — no annotations, or use bare object
def run(self, context, tools): ...


# WRONG — these context fields do not exist
context.selected_text   # AttributeError
context.text            # AttributeError
context.window          # AttributeError

# CORRECT — only these four fields exist
context.selection       # str
context.clipboard       # str
context.active_app      # str
context.mouse_position  # list[int] ([x, y])


# WRONG — do not invent tools methods
tools.browser.open(url)     # does not exist
tools.notify(text)          # does not exist
tools.ai.complete(text)     # does not exist — use tools.ai.ask

# CORRECT tools interface
tools.popup.show(text)
tools.ai.ask(text)
tools.ai.ask(text, prompt="system prompt")
tools.clipboard.get()
tools.clipboard.set(text)
tools.tts.speak(text)
tools.input.ask(prompt)
tools.input.select(prompt, choices)


# WRONG — class-level mutable state is not thread-safe
class BadSkill:
    results = []           # class-level mutable — dangerous
    def run(self, context, tools):
        self.results.append(...)

# CORRECT — instance state initialised in on_load
class GoodSkill:
    def on_load(self, config):
        self._count = 0
    def run(self, context, tools):
        self._count += 1   # instance state is fine (one worker process per skill)
```

---

## 8. Maintenance Contract (for contributors)

`skill-build.md` is a **required PR artifact** (NFR21). Any PR that changes any of the following files **must** update this document in the same PR:

| File changed | What to update here |
|---|---|
| `worker/context.py` — `Context` fields | Section 2 field table |
| `nimble/tools/*.py` — any method signature | Section 3 affected tool |
| `worker/entrypoint.py` — lifecycle invocations / construction | Section 1 lifecycle signatures |
| `nimble/__init__.py` — `SUPPORTED_API_VERSION` | Section 4 `api_version` note |
| `nimble/manifest/parser.py` — `ManifestSpec` fields, required-field set | Section 4 manifest spec |
| `nimble/skills/runner.py` — api_version refusal, lifecycle phase tracking | Sections 1, 4 |
| `nimble/skills/registry.py` — `SkillConfig` fields | Section 5 config.yaml entry |
| `nimble/cli/commands.py` — `_PERMISSION_DESCRIPTIONS` | Section 4 permissions table |

`api_version` in `nimble/__init__.py` must be incremented on every breaking skill interface change (NFR23). The daemon refuses skills whose `api_version` exceeds `SUPPORTED_API_VERSION`.

**Current `api_version`: 1** (`nimble/__init__.py` → `SUPPORTED_API_VERSION = 1`)
