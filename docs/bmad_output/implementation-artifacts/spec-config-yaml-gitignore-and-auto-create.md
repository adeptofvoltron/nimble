---
title: 'config.yaml: gitignore, example file, and auto-create on nimble add'
type: 'chore'
created: '2026-05-07'
status: 'done'
route: 'one-shot'
---

## Intent

**Problem:** `config.yaml` is tracked by git, exposing local API keys and personal skill bindings; there is also no template for new contributors, and `nimble add` fails if the file doesn't exist yet.

**Approach:** Gitignore `config.yaml`, ship a `config.yaml.example` as the canonical template, and make `append_skill_to_config` bootstrap an empty config rather than raising when the file is absent.

## Suggested Review Order

1. [`.gitignore`](../../../../.gitignore) — new `config.yaml` rule
2. [`config.yaml.example`](../../../../config.yaml.example) — new template file
3. [`nimble/manifest/parser.py`](../../../../nimble/manifest/parser.py) — `append_skill_to_config`: `FileNotFoundError` handled to bootstrap empty config
4. [`nimble/cli/commands.py`](../../../../nimble/cli/commands.py) — `add`: echoes notice when config was created from scratch
