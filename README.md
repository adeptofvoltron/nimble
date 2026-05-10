![Nimble](docs/logo_resized.png)

A lightweight hotkey daemon that fires Python skills on demand — capturing clipboard, selection, active app, and mouse position at the moment you press a key.

## Quick start (< 5 minutes)

```bash
git clone <repository-url>   # your fork or upstream checkout
cd <repository-directory>
pip install -e .
nimble start
```

Right after `nimble start`, you should see a notification titled **Nimble** with the body **Nimble daemon running.** (startup confirmation, FR41).

To stop:

```bash
nimble stop
```

## Write your first skill

Create a Python file anywhere under `skills/`, then add a binding in `config.yaml`. No imports needed — Nimble injects `context` and `tools` at call time.

For full authoring guidance see **[.ai/skill-build.md](.ai/skill-build.md)**.

### Minimal example

```python
# skills/greet/skill.py

class GreetSkill:
    def run(self, context, tools):
        app = context.active_app or "your app"
        tools.popup.show(f"Hello from {app}!")
```

Matching `config.yaml` entry:

```yaml
skills:
  - name: greet
    source: local
    path: skills/greet/skill.py
    class_name: GreetSkill
    binding: "ctrl+shift+g"
```

Restart the daemon (`nimble restart`) and press **`ctrl+shift+g`**.

> **Note:** `context` and `tools` must have **no type annotations** in the method signature — skills run in a subprocess that may not have `nimble` installed.

## Install a community skill

```bash
nimble add ctrl+shift+d https://github.com/user/nimble-log-diagnosis
```

Nimble fetches `manifest.yaml`, displays the declared permissions, and prompts for confirmation before installing anything. Dependencies are isolated in `.nimble/skills/<name>/.venv/`. The binding is appended to `config.yaml` and the daemon picks it up without a restart.

## Security model

- The daemon runs as the current user with no elevated privileges
- Context data is captured only at hotkey-fire time
- No background monitoring of any context field
- No telemetry, usage data, or diagnostic information is transmitted anywhere
- `permissions` in `manifest.yaml` are declarative and displayed at install time (before any installation)

## Autostart

### Linux (systemd)

```bash
# Edit autostart/nimble.service — set <NIMBLE_BIN> and <REPO_ROOT>
# `enable` stores a symlink; pass an absolute unit path so the unit still resolves if you change directories later.
systemctl --user enable "$(realpath autostart/nimble.service)"
systemctl --user start nimble
```

### Windows (Task Scheduler)

```
1. Edit autostart\nimble.xml — set <NIMBLE_BIN> and <REPO_ROOT>
2. Open taskschd.msc → Action → Import Task → select autostart\nimble.xml
```

See `autostart/nimble.service` and `autostart/nimble.xml` for the full setup instructions embedded in those files.
