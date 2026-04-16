---
stepsCompleted: [1, 2, 3, 4]
session_topic: 'Nimble template repository — core design, bundled content, and structure'
session_goals: 'List of potential features and blockers for the template'
selected_approach: 'ai-recommended'
techniques_used: ['first-principles-thinking', 'scamper', 'reverse-brainstorming']
ideas_generated: 14
context_file: 'docs/bmad_output/planning-artifacts/product-brief-nimble.md'
session_active: false
workflow_completed: true
---

# Brainstorming Session — Nimble Template Design

**Date:** 2026-04-16
**Topic:** What main template will serve and how to build it
**Goals:** List of potential features and blockers
**Approach:** AI-Recommended — First Principles Thinking → SCAMPER → Reverse Brainstorming

---

## Session Overview

**Topic:** Nimble template repository — core design, structure, and bundled content
**Goals:** Feature list for the template + surface blockers before build

### Session Setup

Two distinct user paths identified as the template's core design constraint:

- **Path A — Consumer:** forks Nimble, installs a community skill via `nimble add ctrl+e github.com/path/to/skill`, done
- **Path B — Builder:** forks Nimble, describes intent to Claude using `skill-build.md`, gets a scaffolded skill

These paths are not independent — builders become the supply that consumers need. The template must serve both from day one for the ecosystem to bootstrap.

---

## Technique Selection

**Approach:** AI-Recommended Techniques
**Analysis Context:** Developer tool template with concrete design decisions and known failure modes

**Recommended Techniques:**
- **First Principles Thinking:** Strip inherited assumptions about template repos, rebuild from what a Python developer actually needs in the first 10 minutes
- **SCAMPER Method:** Systematically generate features across 7 lenses applied to template components
- **Reverse Brainstorming:** Surface blockers by asking how the template could fail its users

---

## Phase 1: First Principles Thinking

### Foundations Established

**[Foundation #1]: Two-Sided Template**
_Concept:_ The template must serve both skill consumers (install via `nimble add`) and skill builders (develop with AI assistance) from day one. These aren't separate features — builders become the supply that consumers need, so both paths must be frictionless for the ecosystem to self-sustain.
_Novelty:_ Most tool templates optimise for one persona. Nimble's template is a bootstrapping mechanism for a two-sided community, which changes what "done" means.

**[Foundation #2]: Package Manager as Future Distribution Layer**
_Concept:_ `nimble add <url>` CLI is the v1 distribution primitive, but the discovery layer (how do you find that URL?) is deferred to a future package registry or index.
_Novelty:_ Explicitly deferring this avoids over-engineering v1 while naming the gap — the template's README needs a placeholder for "find skills here" even if it's just a GitHub topic tag for now.

**[Foundation #3]: `skill-build.md` as Interface Contract**
_Concept:_ The AI authoring file contains the skill interface requirements (class structure, method signatures, context object shape, tool primitive APIs) plus good practices (error handling patterns, when to use which tool). It's the contract Claude reads to scaffold correctly.
_Novelty:_ Makes the AI not a chatbot you explain things to, but a contributor who's already been onboarded — the file does the briefing so the developer just describes intent.

**[Foundation #4]: Exception-as-Signal Contract**
_Concept:_ Skills are non-blocking by design. The daemon's global error handler catches any unhandled exception from a skill and surfaces it as a system notification. Skills must not swallow exceptions or build retry logic — let it fail loudly and let the daemon handle it.
_Novelty:_ Most tool frameworks push error handling into the tool. Nimble inverts this — the skill stays clean, the daemon owns failure recovery. Claude needs to know this or it will generate defensive try/except blocks that mask real bugs.

**[Foundation #5]: Context Object Shape**
_Concept:_ The context snapshot at hotkey-fire contains: `active_app`, `mouse_position`, `clipboard`, `selection` (marked text). Designed to be extensible — new fields added without breaking existing skills.
_Novelty:_ `mouse_position` is underrated — it unlocks positional popups and app-zone-aware skills ("only run if I'm in VS Code").

**[Foundation #6]: Skills Own Their Preconditions**
_Concept:_ The daemon has no knowledge of what a skill requires from context — it just fires and handles exceptions. Skills are responsible for validating their own inputs (`if not context.selection: raise ValueError("No text selected")`).
_Novelty:_ Keeps the YAML config minimal and the daemon dumb-and-stable. Adding a new skill never requires teaching Nimble about new preconditions.

---

## Phase 2: SCAMPER Method

### S — Substitute

**[Feature #7]: Skill Chaining**
_Concept:_ YAML config allows a shortcut to map to a sequence of skills where the output of one becomes input to the next. Each skill in the chain receives the previous skill's return value as an additional context field (`context.previous_step_out`).
_Novelty:_ Turns atomic skills into composable pipelines without any skill needing to know about the others. A library of 10 skills becomes dozens of useful combinations.

**[Feature #8]: Declarative Skill Chaining with Pipe Syntax**
_Concept:_ Bindings support a pipe syntax (`skillA | {field_mapping} | skillB`) where skills declare their `inputFrom` in config and the pipe connector maps output fields explicitly. Skills return a named dict (`{"translation": result}`) making output self-documenting and multi-field capable. Skills that don't return a value pass original context forward.

```yaml
skills:
  translateSkill:
    path: 'path/to/translateSkill'
    config:
      inputFrom: 'context.selected'
  voiceTalk:
    path: 'path/to/voiceSkill'
    config:
      inputFrom: 'context.previous_step_out'

bindings:
  - binding: 'ctrl+shift+t'
    skill: 'translateSkill | {previous_step_out: output.translation} | voiceTalk'
```

_Novelty:_ The explicit field mapping means skills don't need to agree on field names — the YAML is the adapter layer. Skills stay decoupled and reusable in different chains.

### C — Combine

**[Feature #9]: Skill Metadata in YAML**
_Concept:_ Each skill definition in the YAML carries metadata fields — `description`, `author`, `requires`, `version` — alongside `path` and `config`. Powers `nimble list`, `nimble info <skill>`, and future tooling without parsing Python.
_Novelty:_ The YAML becomes the single source of truth for the skill registry — not just a config file but a discoverable manifest. Also quietly enables v2 package manager indexing by establishing the metadata contract in v1.

### A — Adapt

**[Feature #10]: Per-Project `.nimble/` Folder**
_Concept:_ A `.nimble/` directory in any project folder contains a local `config.yaml` that defines project-specific bindings and skills. When the active app + working directory matches a project, Nimble layers these local bindings on top of global ones.
_Novelty:_ Hotkeys become context-aware without any skill needing to know about project context. Same shortcut does different things in different projects.

**[Feature #11]: Skill Lifecycle Hooks**
_Concept:_ Skills can optionally implement lifecycle methods alongside `run()`:
- `on_load(config)` — fires when daemon starts; validate config, check API keys, warn early
- `on_error(exception)` — fires before global handler; enrich error messages or handle specific exceptions before re-raising
- `on_unload()` — fires on daemon stop; cleanup resources

_Novelty:_ Moves skill validation from runtime failure to startup — a misconfigured skill fails loudly at `nimble start` with a clear message, not silently at runtime.

### M — Modify

**[Feature #12]: Per-Skill `manifest.yaml`**
_Concept:_ Every skill ships with its own `manifest.yaml` alongside the skill file. Contains both metadata and required fields:

```yaml
name: translate
version: 1.0.0
description: Translates selected text using AI
entrypoint: skill.py::run        # file::function OR file::ClassName
requires: [selection]
permissions: [ai, popup]
dependencies: [anthropic]
author: github.com/user
```

`nimble add` reads the manifest to register the skill. The manifest is the contract between skill author and Nimble runtime.
_Novelty:_ Decouples skill identity from the main app config. A community skill becomes a self-describing unit — portable, discoverable, and future-proof for a package manager.

**[Feature #13]: Function-Style Skills**
_Concept:_ Nimble accepts both class-based skills (`class TranslateSkill`) and function-style skills (`def run(context, tools)`). The manifest `entrypoint` field tells Nimble which to expect.
_Novelty:_ Lowers the contribution barrier significantly. A 5-line function + manifest is a complete, distributable skill.

### E — Eliminate

**[Feature #14]: `nimble add` Generates Config YAML Automatically**
_Concept:_ `nimble add <shortcut> <repo-url>` downloads the skill, reads its `manifest.yaml`, installs pip dependencies, and appends the binding and skill entry to config YAML automatically. Users never hand-write YAML for installed community skills.

Flow:
1. Clone/download skill folder
2. Read `manifest.yaml` — entrypoint, description, dependencies
3. Install declared pip dependencies
4. Append to config YAML with description from manifest
5. Print confirmation with restart instruction

_Novelty:_ Eliminates the biggest friction point for Path A consumers. Install a skill, get a working binding, done.

### P — Put to Other Uses *(deferred v2)*

- Local `~/.nimble/history.log` — usage analytics, fully local
- `skill-build.md` as contribution guide (dual audience: Claude + human contributors)
- Conditional pipe branching with `if` expressions

### R — Reverse *(deferred v2)*

- `nimble capture` — record intent before writing skill
- `nimble publish` — package and push skill to GitHub
- Intent-driven generation — natural language in YAML, Claude scaffolds the skill

---

## Phase 3: Reverse Brainstorming — Blockers

**[Blocker #1]: Binding Must Live in User Config, Never in Skill**
_Concept:_ Shortcuts are personal — two users of the same community skill will bind it to different keys. Any pattern that embeds binding in the skill file creates a conflict the user must override. YAML config is the only correct home for bindings.
_Rule for `skill-build.md`:_ "Skills must never declare their own bindings. Bindings belong to the user's config. A skill is a capability, not a shortcut."

**[Blocker #2]: Cold Start — No Community Skills on Day One**
_Concept:_ On day one the template ships with zero community skills. Path A consumers hit a dead end immediately. Mitigated by v1 targeting a known audience (friends/early adopters) who are Path B builders. Bundled example skills deferred to v2.
_Status:_ Accepted risk for v1. Revisit when community bootstrapping begins.

**[Blocker #3]: Scope Creep Risk**
_Concept:_ V1 ships the core template structure — daemon, config, primitives, `skill-build.md`, `manifest.yaml` spec. Bundled example skills, discovery layer, and advanced CLI features are v2.
_Rule:_ Any feature that doesn't serve the two core paths (install + build) is v2.

**[Blocker #4]: `skill-build.md` Drift**
_Concept:_ `skill-build.md` goes stale as the codebase evolves — tool primitive signatures change, new context fields are added, good practices get updated. Generated skills silently use the old API.
_Mitigation:_ Treat `skill-build.md` as a first-class artifact. Any PR changing tool primitives or context shape must include a `skill-build.md` update — enforce via PR checklist or CI.

---

## Idea Organisation and Prioritisation

### Themes

| Theme | Ideas |
|---|---|
| Skill Architecture | Function-style skills, `manifest.yaml`, lifecycle hooks, exception-as-signal, precondition ownership |
| Developer Experience | `skill-build.md` contract, context object shape, `nimble add` config generation, two-sided template |
| Composability | Skill chaining, pipe syntax with field mapping |
| Configuration & Context | Metadata in YAML, per-project `.nimble/`, binding ownership rule |

### V1 Prioritisation

| Priority | Item | Rationale |
|---|---|---|
| Must-have | `manifest.yaml` spec | Everything else depends on it |
| Must-have | `skill-build.md` contract | Core DX for builders |
| Must-have | Exception-as-signal + lifecycle hooks | Foundation of reliability |
| Must-have | `nimble add` generates config | Eliminates biggest friction for consumers |
| High | Function-style skills | Lowers contribution barrier significantly |
| High | Skill chaining + pipe syntax | Multiplies value of small skill library |
| Medium | Per-project `.nimble/` | Powerful but not day-one critical |
| v2 | Bundled example skills | Cold start fix when community begins |
| v2 | Conditional pipes, publish, capture, intent-driven generation | Requires ecosystem to exist first |

### `skill-build.md` Good Practices Captured

1. **Do not catch exceptions in your skill.** If something goes wrong, raise — the daemon will notify the user.
2. **Always validate context inputs early.** Check required fields at the top and raise a descriptive exception — the user will see your message as a notification.
3. **If your skill produces output for chaining, return a dict with descriptive keys.** Bare returns are valid but chain-incompatible.
4. **Implement `on_load` for any skill with external dependencies.** Check API keys, test connectivity, validate config — fail fast at startup, not at hotkey-fire time.
5. **Skills must never declare their own bindings.** Bindings belong to the user's config. A skill is a capability, not a shortcut.

---

## Session Summary

**Techniques used:** First Principles Thinking, SCAMPER (all 7 lenses), Reverse Brainstorming
**Total ideas generated:** 14 features/foundations + 4 blockers
**Key breakthrough:** The `manifest.yaml` per-skill spec unifies skill architecture, metadata, chaining, and future distribution into a single artifact — it's the keystone of the whole template design.
**Scope discipline:** 8 ideas explicitly deferred to v2, keeping v1 focused on core template and two primary user paths.

### Recommended Next Step

Run `/bmad-create-prd` — the foundations and feature list from this session provide strong grounding for the Product Requirements Document.
