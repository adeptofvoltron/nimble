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

**Auto-injected attribute — always present, never `None`:**

```python
self.configuration  # dict[str, str] — values from the configuration: block in config.yaml
```

The daemon sets `self.configuration` on every skill instance **before** calling `on_load`. It is available in `on_load`, `run()`, `on_error()`, and `on_unload()`. Defaults to `{}` when no `configuration:` block exists in `config.yaml`. See Section 6 for the full configuration workflow.

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
config_fields:               # list — declares user-configurable parameters; see Section 6
  - key: target_language     # str (required) — YAML key written into the configuration: block
    description: "Target language code"  # str (required) — prompt label shown during nimble add
    default: "en"            # str or null (optional) — used when user presses Enter; must be in possible_values
    possible_values: [en, es, fr]  # list[str] (optional) — constrains valid input; free-text if absent
```

A `ManifestError` is raised in the following cases: `config_fields` is present but not a list; any entry is not a YAML mapping; an entry is missing `key` or `description`; `default` is set to a non-string, non-null value; `default` is not in `possible_values` when both are set; or `possible_values` contains non-string items. Absence of `config_fields` is not an error — `ManifestSpec.config_fields` defaults to `[]`.

**`permissions` values** (shown to users before community-skill install):

| Value | Meaning |
|---|---|
| `ai` | sends text to an external LLM API |
| `clipboard` | reads/writes clipboard content |
| `tts` | uses system text-to-speech |
| `input` | opens a dialog prompting user input |
| `popup` | displays a system notification popup |

**`dependencies`** — pip package names for `nimble add` install. Example: `[anthropic, requests]`

**`api_version`** — must be ≤ `SUPPORTED_API_VERSION` in `nimble/__init__.py` (currently `1`). The daemon refuses skills whose `api_version` exceeds `SUPPORTED_API_VERSION`; skills targeting an earlier version load with a deprecation warning. Increment on every breaking interface change (see Section 9).

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
    configuration:                         # optional — key-value pairs injected as self.configuration; see Section 6
      target_language: es                  # all values stored and delivered as strings

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

## 6. Skill Custom Configuration

Skills can declare named configuration parameters in `manifest.yaml` (`config_fields`). When installed via `nimble add`, the user is prompted for each field interactively; the collected values are written into the `configuration:` block in `config.yaml`. The daemon then injects those values as `self.configuration` (`dict[str, str]`) before `on_load` is called.

### Step 1 — Declare fields in `manifest.yaml`

```yaml
config_fields:
  - key: target_language
    description: "Target language code"
    default: "en"
    possible_values: [en, es, fr]
  - key: api_key
    description: "External API key"    # no default → user must enter a value; no possible_values → free-text
```

### Step 2 — What `nimble add` does

After the user confirms install, `nimble add` prompts for each `config_fields` entry in order:

```
target_language — Target language code [en/es/fr] (default: 'en'): es
api_key — External API key: sk-abc123
```

Prompt rules:
- `[v1/v2/...]` is shown only when `possible_values` is set.
- `(default: 'X')` is shown only when `default` is set. Pressing Enter uses the default.
- When there is no `default`, pressing Enter prints `'<key>' is required.` and re-prompts.
- An invalid value (not in `possible_values`) prints `Invalid value. Choose from: ...` and re-prompts.
- Input is stripped of leading/trailing whitespace before validation. `" es "` is treated as `"es"`.
- If stdin is closed (EOF) or a read error occurs, the CLI prints an error to stderr and exits with code 1.

The `configuration:` block is written only when at least one field was prompted (i.e. `config_fields` is non-empty). Skills with no `config_fields` produce no block.

### Step 3 — The `configuration:` block in `config.yaml`

```yaml
  - name: translator
    source: community
    path: .nimble/skills/translator/skill.py
    class_name: TranslatorSkill
    binding: "ctrl+shift+t"
    configuration:
      target_language: es
      api_key: sk-abc123
```

You can edit this block manually at any time. All values are stored and delivered as strings — YAML integers (e.g. `count: 5`) are coerced to `"5"`. When the block is absent, `self.configuration` defaults to `{}`.

### Step 4 — Access values in skill code

`self.configuration` is available in `on_load`, `run()`, `on_error()`, and `on_unload()`.

```python
class TranslatorSkill:
    def on_load(self, config):
        self._lang = self.configuration.get("target_language", "en")

    def run(self, context, tools):
        text = context.selection or context.clipboard
        if not text:
            tools.popup.show("Select or copy some text first.")
            return
        result = tools.ai.ask(text, prompt=f"Translate to {self._lang} in one sentence.")
        tools.clipboard.set(result)
        tools.popup.show("Translation copied to clipboard.")
```

Caching in `on_load` (as `self._lang` above) avoids repeated dict lookups on every hotkey fire. Accessing `self.configuration` directly in `run()` is equally valid and simpler for one-off reads.

**Canonical access path:** always use `self.configuration`. The `config` dict passed to `on_load` also contains a `"configuration"` key (the raw JSON payload), but `self.configuration` is the documented, str-coerced interface — prefer it over `config.get("configuration")`.

---

## 7. Complete Working Example

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

## 8. Anti-Patterns

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


# WRONG — do not read configuration via the on_load config dict
class BadConfigSkill:
    def on_load(self, config):
        self._lang = config.get("configuration", {}).get("target_language", "en")

# CORRECT — use self.configuration (always set before on_load, str-coerced)
class GoodConfigSkill:
    def on_load(self, config):
        self._lang = self.configuration.get("target_language", "en")
```

---

## 9. Maintenance Contract (for contributors)

`skill-build.md` is a **required PR artifact** (NFR21). Any PR that changes any of the following files **must** update this document in the same PR:

| File changed | What to update here |
|---|---|
| `worker/context.py` — `Context` fields | Section 2 field table |
| `nimble/tools/*.py` — any method signature | Section 3 affected tool |
| `worker/entrypoint.py` — lifecycle invocations / construction | Section 1 lifecycle signatures |
| `nimble/__init__.py` — `SUPPORTED_API_VERSION` | Section 4 `api_version` note |
| `nimble/manifest/parser.py` — `ManifestSpec` fields, required-field set | Section 4 manifest spec |
| `nimble/manifest/parser.py` — `ConfigFieldSpec` fields, `_parse_config_fields` behaviour | Section 4 optional fields, Section 6 |
| `nimble/manifest/parser.py` — `append_skill_to_config` `configuration` parameter | Section 6 Step 2/3 |
| `nimble/skills/runner.py` — api_version refusal, lifecycle phase tracking | Sections 1, 4 |
| `nimble/skills/registry.py` — `SkillConfig` fields | Section 5 config.yaml entry |
| `nimble/cli/commands.py` — `_PERMISSION_DESCRIPTIONS` | Section 4 permissions table |
| `nimble/cli/commands.py` — `_collect_config_values` prompt format or validation | Section 6 Step 2 |

`api_version` in `nimble/__init__.py` must be incremented on every breaking skill interface change (NFR23). The daemon refuses skills whose `api_version` exceeds `SUPPORTED_API_VERSION`.

**Current `api_version`: 1** (`nimble/__init__.py` → `SUPPORTED_API_VERSION = 1`)
