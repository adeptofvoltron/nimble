# Sprint Change Proposal — 2026-05-04

**Project:** pixi (Nimble)
**Author:** Bernard
**Scope:** Minor — new Epic 8 added; no existing epics or stories modified
**Handoff:** Developer agent (direct implementation)

---

## Section 1: Issue Summary

**Change type:** New feature requirement

**Problem statement:** Skills have no way to accept user-defined parameters without hardcoding them. There is no mechanism for a skill author to declare "this skill needs a target language" or "this skill needs an API key" and have that value flow from the user's `config.yaml` into the skill at runtime.

**Discovery context:** Identified as a product gap after all 7 core epics were completed. The `nimble add` community install flow is complete but currently produces a static, unconfigurable skill entry in `config.yaml`. The `on_load(self, config)` hook exists and already receives a config dict — the passthrough infrastructure is ~60% built; it just carries skill metadata, not user values.

**Evidence of the gap:** The `translate` community skill hardcodes language prompting at runtime via `tools.input.ask()`. If the user always wants the same target language, they must answer the prompt every time. With skill configuration, the target language could be set once at install time and read from `self.configuration["target_language"]` in `run()`.

---

## Section 2: Impact Analysis

### Epic Impact

All existing epics 1–7 are complete and unaffected. No stories are modified, reverted, or invalidated.

**New epic required:** Epic 8 — Skill Configuration.

### Story Impact

No existing story files require changes. Three new stories are added under Epic 8.

### Artifact Conflicts

| Artifact | Impact | Change type |
|---|---|---|
| `nimble/skills/registry.py` | `SkillConfig` dataclass — add `configuration` field | Additive |
| `nimble/manifest/parser.py` | New `ConfigFieldSpec` dataclass; `ManifestSpec` gains `config_fields`; `_parse_skills()` reads `configuration`; `append_skill_to_config()` writes `configuration` block | Additive |
| `nimble/skills/runner.py` | `skill_config_json` includes `configuration` dict | Additive |
| `worker/entrypoint.py` | Inject `self.configuration` on skill instance before `on_load` and `run()` | Additive, non-breaking |
| `nimble/cli/commands.py` | `add` command prompts for `config_fields` after confirmation | Additive |
| `architecture.md` | `NIMBLE_SKILL_CONFIG` payload schema + `config.yaml` schema examples | Documentation update |
| `epics.md` | Add Epic 8 + 3 stories | Additive |
| `prd.md` | Add FR46–FR48 | Additive |
| `.ai/skill-build.md` | Document `self.configuration` access pattern | Documentation update |

### Technical Impact

**Worker IPC protocol:** No change to the stdin/stdout JSON schema. `configuration` is injected once at worker startup via the existing `NIMBLE_SKILL_CONFIG` env var — it does not travel on every invocation payload.

**`run()` signature:** Unchanged — `run(self, context, tools)`. The `configuration` dict is made available as `self.configuration` (injected by the worker entrypoint as an instance attribute), keeping the API fully backward compatible.

**`on_load(self, config)` signature:** Unchanged. The `config` dict already passes through; it now includes a `configuration` key with the user-set values in addition to the existing `name`, `source`, `binding`, `path`, `class_name` keys.

**Local skills:** Fully supported — `configuration` in `config.yaml` is read regardless of `source: local` or `source: community`.

---

## Section 3: Recommended Approach

**Option 1 (Direct Adjustment) — Selected**

Add Epic 8 with 3 focused stories. Effort: Low. Risk: Low. Timeline impact: None on existing work.

**Rationale:**
- The passthrough infrastructure already exists in `worker/entrypoint.py` and `runner.py` — this is largely wiring and schema work
- No existing story is broken or reverted — purely additive
- The 3-story split mirrors the natural separation: schema (8-1), passthrough (8-2), CLI prompting (8-3)
- All changes are backward compatible — existing skills with no `config_fields` and no `configuration` in `config.yaml` continue working identically

---

## Section 4: Detailed Change Proposals

### 4.1 New FR additions to `prd.md`

**OLD:** FR45 is the last functional requirement.

**NEW:** Append to the Functional Requirements list:

```
FR46: Skills can declare named configuration fields in manifest.yaml, each with a key,
      description, optional default value, and optional enumerated possible values.
FR47: The daemon can read a per-skill `configuration` key-value block from config.yaml
      and make those values available to the skill as `self.configuration` in both
      on_load(self, config) and run(self, context, tools).
FR48: The `nimble add` command prompts the user for each declared config field at install
      time and writes the collected values into the skill entry in config.yaml.
```

---

### 4.2 New `ManifestSpec` config_fields schema

**File:** `nimble/manifest/parser.py`

**NEW dataclass** (add alongside existing dataclasses):

```python
@dataclass
class ConfigFieldSpec:
    key: str
    description: str
    default: str | None = None
    possible_values: list[str] | None = None
```

**OLD `ManifestSpec`:**
```python
@dataclass
class ManifestSpec:
    name: str
    version: str
    api_version: int
    description: str
    entrypoint: str
    permissions: list[str]
    dependencies: list[str]
    author: str
    requires: list[str] = field(default_factory=list)
    class_name: str = ""
```

**NEW `ManifestSpec`** (add one field):
```python
    config_fields: list[ConfigFieldSpec] = field(default_factory=list)
```

---

### 4.3 `SkillConfig` configuration field

**File:** `nimble/skills/registry.py`

**OLD `SkillConfig`:**
```python
@dataclass
class SkillConfig:
    name: str
    source: SkillSource
    binding: str
    path: str
    class_name: str
```

**NEW `SkillConfig`:**
```python
@dataclass
class SkillConfig:
    name: str
    source: SkillSource
    binding: str
    path: str
    class_name: str
    configuration: dict[str, str] = field(default_factory=dict)
```

---

### 4.4 `config.yaml` schema — new `configuration` block per skill

**OLD** (example skill entry in `config.yaml`):
```yaml
skills:
  - name: translate
    source: community
    path: .nimble/skills/translate/skill.py
    class_name: TranslateSkill
    binding: ctrl+t+r
    installed_from: https://github.com/...
    version: 1.0.0
```

**NEW** (with configuration):
```yaml
skills:
  - name: translate
    source: community
    path: .nimble/skills/translate/skill.py
    class_name: TranslateSkill
    binding: ctrl+t+r
    installed_from: https://github.com/...
    version: 1.0.0
    configuration:
      target_language: es
```

**Rules:**
- `configuration` is optional — absent means `{}` (empty dict)
- All keys and values are strings
- The block is written by `nimble add` and can be manually edited
- The daemon's file watcher picks up manual edits and reloads the affected worker

---

### 4.5 `manifest.yaml` schema — new `config_fields` block

**NEW** (example with config_fields):
```yaml
name: translate
version: "1.0.0"
api_version: 1
description: "Translates selected text"
entrypoint: skill.py
class_name: TranslateSkill
permissions:
  - clipboard
config_fields:
  - key: target_language
    description: "Default target language code (e.g. 'es', 'fr', 'de')"
    default: "en"
    possible_values:
      - en
      - es
      - fr
      - de
  - key: api_key
    description: "API key for translation service"
    # no default, no possible_values = required free-form field
```

**Rules:**
- `config_fields` is optional — absent means no configuration fields
- Each field must have `key` and `description`
- `default` is optional — absent means required (user must provide value during `nimble add`)
- `possible_values` is optional — absent means free-form (any string accepted)
- `possible_values` with entries restricts accepted values; default must be in `possible_values` if both declared

---

### 4.6 Worker entrypoint — inject `self.configuration`

**File:** `worker/entrypoint.py`

**OLD** (relevant section):
```python
skill_config: dict[str, object] = {}
raw_skill_config = json.loads(os.environ.get("NIMBLE_SKILL_CONFIG", "") or "{}")
if isinstance(raw_skill_config, dict):
    skill_config = raw_skill_config

# ... later ...
if hasattr(skill, "on_load"):
    skill.on_load(skill_config)
```

**NEW**:
```python
skill_config: dict[str, object] = {}
raw_skill_config = json.loads(os.environ.get("NIMBLE_SKILL_CONFIG", "") or "{}")
if isinstance(raw_skill_config, dict):
    skill_config = raw_skill_config

# Inject configuration as instance attribute so run() can access self.configuration
skill.configuration: dict[str, str] = {}
raw_config = skill_config.get("configuration")
if isinstance(raw_config, dict):
    skill.configuration = {str(k): str(v) for k, v in raw_config.items()}

# ... later ...
if hasattr(skill, "on_load"):
    skill.on_load(skill_config)  # skill_config now includes "configuration" key
```

---

### 4.7 `runner.py` — include `configuration` in env payload

**File:** `nimble/skills/runner.py`

**OLD** `skill_config_json` build:
```python
skill_config_json = json.dumps(
    {
        "name": config.name,
        "source": config.source,
        "binding": config.binding,
        "path": config.path,
        "class_name": config.class_name,
    }
)
```

**NEW**:
```python
skill_config_json = json.dumps(
    {
        "name": config.name,
        "source": config.source,
        "binding": config.binding,
        "path": config.path,
        "class_name": config.class_name,
        "configuration": config.configuration,
    }
)
```

---

### 4.8 `nimble add` — interactive config prompting

**File:** `nimble/cli/commands.py` — `add` command

**NEW** (insert between install confirmation and `append_skill_to_config` call):

```python
# Collect configuration values from user
skill_configuration: dict[str, str] = {}
if spec.config_fields:
    typer.echo("Skill configuration:")
    for field in spec.config_fields:
        prompt_text = f"  {field.key} — {field.description}"
        if field.possible_values:
            prompt_text += f" [{'/'.join(field.possible_values)}]"
        if field.default is not None:
            prompt_text += f" (default: {field.default!r})"
        prompt_text += ": "
        while True:
            value = typer.prompt(prompt_text, default=field.default or "")
            if not value and field.default is None:
                typer.echo(f"  '{field.key}' is required.")
                continue
            if field.possible_values and value not in field.possible_values:
                typer.echo(
                    f"  Invalid value. Choose from: {', '.join(field.possible_values)}"
                )
                continue
            skill_configuration[field.key] = value or (field.default or "")
            break
```

Then pass `skill_configuration` to `append_skill_to_config()`.

---

### 4.9 `skill-build.md` — document configuration access

**Add section** (after the `on_load` documentation):

```markdown
## Skill Configuration

Skills can declare configuration fields in `manifest.yaml` under `config_fields`.
The daemon reads values from `config.yaml` and injects them as `self.configuration`
(a `dict[str, str]`) on the skill instance before `on_load` is called.

Access configuration in `on_load`:
```python
def on_load(self, config: dict) -> None:
    self.lang = self.configuration.get("target_language", "en")
```

Access in `run()` (same attribute, already set by on_load time):
```python
def run(self, context: Context, tools: ToolRegistry) -> None:
    lang = self.configuration.get("target_language", "en")
```

`self.configuration` is always a `dict[str, str]` — never `None`.
```

---

## Section 5: Implementation Handoff

**Scope classification:** Minor — Developer agent can implement directly.

**Handoff:** Developer agent via `dev-story` on stories 8-1 → 8-2 → 8-3 in sequence (8-2 depends on 8-1 types; 8-3 depends on 8-1 types).

**Success criteria:**
- A skill's `manifest.yaml` with `config_fields` parses correctly; missing required fields during `nimble add` re-prompt; invalid `possible_values` entries re-prompt
- `self.configuration` is available in both `on_load` and `run()` and matches what is in `config.yaml`
- Existing skills with no `config_fields` and no `configuration` in `config.yaml` continue to work identically (regression guard)
- `nimble validate` accepts `config.yaml` entries with and without a `configuration` block

---

## Section 6: Epic 8 Story Definitions

### Epic 8: Skill Configuration — Pass Parameters from `config.yaml` to Skills

Skills can declare named configuration fields in `manifest.yaml`; users set values in `config.yaml`; `nimble add` prompts interactively at install time; values are injected as `self.configuration` on the skill instance, accessible in both `on_load` and `run()`.

**FRs covered:** FR46, FR47, FR48

---

### Story 8.1: `config_fields` Schema in `manifest.yaml` and Parsing

As a skill author,
I want to declare named configuration fields in my `manifest.yaml` with descriptions, optional defaults, and optional value constraints,
So that users and `nimble add` know exactly what to provide when installing or configuring my skill.

**Acceptance Criteria:**

**Given** a `manifest.yaml` with a `config_fields` block containing a field with `key`, `description`, and `default`
**When** `parse_manifest_yaml()` parses it
**Then** it returns a `ManifestSpec` with a populated `config_fields: list[ConfigFieldSpec]` containing the correct values

**Given** a `config_fields` entry with `possible_values: [en, es, fr]` and `default: en`
**When** parsed
**Then** `ConfigFieldSpec.possible_values == ["en", "es", "fr"]` and `ConfigFieldSpec.default == "en"`

**Given** a `config_fields` entry with no `possible_values`
**When** parsed
**Then** `ConfigFieldSpec.possible_values is None` — the field accepts any string value

**Given** a `manifest.yaml` with no `config_fields` key
**When** parsed
**Then** `ManifestSpec.config_fields == []` — absence is not an error

**Given** a `config_fields` entry missing the required `key` or `description` field
**When** parsed
**Then** a `ManifestError` is raised identifying the missing field — install is aborted

---

### Story 8.2: `configuration` in `config.yaml` + Worker Injection

As a skill author,
I want my skill to receive user-defined configuration values as `self.configuration` in both `on_load` and `run()`,
So that I can parameterise my skill's behaviour without hardcoding values or prompting the user on every invocation.

**Acceptance Criteria:**

**Given** a skill entry in `config.yaml` with a `configuration: {target_language: es}` block
**When** `_parse_skills()` parses it
**Then** the resulting `SkillConfig.configuration == {"target_language": "es"}`

**Given** a skill entry with no `configuration` key
**When** parsed
**Then** `SkillConfig.configuration == {}` — absence is not an error

**Given** a `SkillConfig` with a non-empty `configuration` dict
**When** `runner.py` builds `skill_config_json`
**Then** it includes `"configuration": {"target_language": "es"}` in the JSON payload

**Given** the worker subprocess starts and `NIMBLE_SKILL_CONFIG` contains `"configuration": {...}`
**When** the worker initialises the skill instance
**Then** `skill.configuration` is set to the dict before `on_load` is called

**Given** a skill's `run()` method accesses `self.configuration["target_language"]`
**When** `run()` is called
**Then** it returns the value from `config.yaml` — `self.configuration` is available without `on_load` being defined

**Given** a skill with no `configuration` in `config.yaml`
**When** `self.configuration` is accessed
**Then** it returns `{}` — never raises `AttributeError`

**Given** an existing skill that defines `on_load(self, config)` and reads `config["name"]`
**When** the worker calls `on_load`
**Then** `config["name"]` still works — the `configuration` key is additive, not replacing existing keys

---

### Story 8.3: Interactive Config Prompting in `nimble add`

As a user installing a community skill,
I want to be prompted for each declared configuration field during `nimble add`,
So that my `config.yaml` is fully populated with skill parameters without any manual editing.

**Acceptance Criteria:**

**Given** a skill's `ManifestSpec.config_fields` contains one field with `key: target_language`, `description: "Target language code"`, `default: "en"`, `possible_values: [en, es, fr]`
**When** `nimble add` runs after the user confirms install
**Then** the CLI prompts: `target_language — Target language code [en/es/fr] (default: 'en'):`

**Given** the user presses Enter without typing a value and a default exists
**When** the prompt is processed
**Then** the default value is used — the user is not re-prompted

**Given** the user enters a value not in `possible_values`
**When** the prompt is processed
**Then** the CLI prints an error and re-prompts until a valid value is entered

**Given** a field with no `default` and no `possible_values`
**When** the user presses Enter without typing
**Then** the CLI prints `'<key>' is required.` and re-prompts until a non-empty value is entered

**Given** all config fields have been collected
**When** `append_skill_to_config()` writes the skill entry
**Then** the entry includes a `configuration:` block with all collected key-value pairs

**Given** a skill's `ManifestSpec.config_fields` is empty
**When** `nimble add` runs
**Then** no configuration prompts appear and no `configuration:` block is written to `config.yaml`
