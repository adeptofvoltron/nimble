# Story 1.1: Repository Scaffold with Wired Dev Toolchain

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a contributor,
I want a correctly structured repository with all core and dev dependencies configured and installable via `pip install -e ".[dev]"`,
so that I can immediately run linting, typechecking, formatting, and tests — and resolve the `nimble` CLI entry point — without any manual setup.

## Acceptance Criteria

1. **Given** the repository is cloned on a machine with Python 3.10+, **when** `pip install -e ".[dev]"` is run, **then** all core dependencies (typer, pynput, pyyaml, plyer) and dev dependencies (black, flake8, mypy, pytest) are installed without errors, **and** running `nimble --help` resolves to the Typer app and prints help text.

2. **Given** a Python file exists in the `nimble/` package, **when** `black --check nimble/` is run, **then** black validates formatting using `line-length=88` and `target-version=["py310"]`.

3. **Given** the `nimble/` package exists, **when** `mypy nimble/` is run, **then** mypy applies `--strict` mode with `python_version = "3.10"` and `ignore_missing_imports = true`.

4. **Given** the `tests/` directory exists, **when** `pytest` is run, **then** pytest discovers `testpaths = ["tests"]` and exits cleanly (zero failures, even on an empty suite).

## Tasks / Subtasks

- [ ] Task 1: Create `pyproject.toml` with exact pinned versions and tool configuration (AC: 1, 2, 3, 4)
  - [ ] `[build-system]` block: hatchling 1.29.0
  - [ ] `[project]` block: name, version, requires-python, all core deps at correct versions
  - [ ] `[project.optional-dependencies]` block: `dev` group with black, flake8, mypy, pytest
  - [ ] `[project.scripts]` block: `nimble = "nimble.cli.commands:app"`
  - [ ] `[tool.hatch.build.targets.wheel]` block: `packages = ["nimble"]`
  - [ ] `[tool.black]` block: `line-length = 88`, `target-version = ["py310"]`
  - [ ] `[tool.mypy]` block: `python_version = "3.10"`, `strict = true`, `ignore_missing_imports = true`
  - [ ] `[tool.pytest.ini_options]` block: `testpaths = ["tests"]`

- [ ] Task 2: Scaffold the `nimble/` package (AC: 1, 2, 3)
  - [ ] `nimble/__init__.py` — package metadata (version string, no logic)
  - [ ] `nimble/cli/__init__.py` — empty module init
  - [ ] `nimble/cli/commands.py` — minimal Typer `app` object with a placeholder command that makes `nimble --help` print help text

- [ ] Task 3: Scaffold the `worker/` package (AC: 1)
  - [ ] `worker/__init__.py` — empty init (this is a top-level package that runs as a script, not installed via pyproject)

- [ ] Task 4: Scaffold the `tests/` directory (AC: 4)
  - [ ] `tests/__init__.py` — empty (enables pytest discovery)
  - [ ] `tests/unit/__init__.py` — empty
  - [ ] `tests/integration/__init__.py` — empty
  - [ ] Verify `pytest` exits 0 with zero tests collected

- [ ] Task 5: Create `config.yaml` at repo root (AC: 1)
  - [ ] Minimal valid content: `skills: []\nbindings: []\n`
  - [ ] This is the user's hotkey config committed to the fork

- [ ] Task 6: Create `.gitignore` (AC: 1)
  - [ ] Must include `.nimble/` (tool-managed runtime dir)
  - [ ] Must include standard Python entries: `__pycache__/`, `*.pyc`, `*.egg-info/`, `dist/`, `build/`, `.venv/`, `*.egg`
  - [ ] Must NOT gitignore `manifest.lock` (it lives inside `.nimble/` but must be committed)

- [ ] Task 7: Verify all AC with local commands (AC: 1–4)
  - [ ] `pip install -e ".[dev]"` — no errors
  - [ ] `nimble --help` — prints Typer-generated help
  - [ ] `black --check nimble/` — exits 0
  - [ ] `mypy nimble/` — exits 0 (or only reports "Success: no issues found")
  - [ ] `pytest` — exits 0, `0 failed`
  - [ ] `flake8 nimble/` — exits 0

## Dev Notes

### pyproject.toml — Exact Required Content

This is the canonical scaffold from the architecture. Do not alter versions without a documented reason.

```toml
[build-system]
requires = ["hatchling==1.29.0"]
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
    "plyer>=2.1",
]

[project.optional-dependencies]
dev = [
    "black==26.3.1",
    "flake8==7.3.0",
    "mypy==1.20.1",
    "pytest",
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

**Critical:** `hatchling` itself is pinned to `1.29.0` in `requires`. The `nimble` package deps use `>=` floor pins — this is intentional (pyproject.toml pattern for a template repo, not a locked application). Dev deps are exact pins to ensure reproducible tool behaviour.

**`watchdog` is NOT in the initial dependency list** — it is listed in the epics as "version to confirm at implementation time" and belongs to Story 2.8 (daemon main loop). Do not add it here.

### `nimble/cli/commands.py` — Minimal Typer App

The CLI entry point must exist and be importable immediately. It will grow across Epics 2–6 but must satisfy `nimble --help` right now.

```python
import typer

app = typer.Typer(help="Nimble — cross-platform Python hotkey daemon.")


@app.command()
def placeholder() -> None:
    """Placeholder — daemon commands added in Epic 2."""
    typer.echo("Use 'nimble --help' to see available commands.")


if __name__ == "__main__":
    app()
```

**mypy --strict compliance:** all function parameters and return types must be annotated even in this stub. The `-> None` on `placeholder()` is required.

**No relative imports:** use `import typer` (stdlib/third-party), never `from . import ...` within `nimble/cli/commands.py`.

### File and Directory Structure This Story Creates

```
nimble/                      ← repo root
├── nimble/
│   ├── __init__.py          ← version metadata only
│   └── cli/
│       ├── __init__.py
│       └── commands.py      ← Typer app object
├── worker/
│   └── __init__.py          ← empty; not installed via wheel
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   └── __init__.py
│   └── integration/
│       └── __init__.py
├── config.yaml              ← skills: []\nbindings: []\n
├── pyproject.toml
└── .gitignore
```

**Not created in this story** (deferred to Story 1.2 and later):
- `tests/conftest.py` — shared fixtures (`fake_adapter`, `tmp_config`, `fake_notifier`)
- `tests/unit/hotkeys/fake_adapter.py` — `FakeHotkeyAdapter`
- `nimble/hotkeys/` — HotkeyAdapter ABC and implementations
- `nimble/context/`, `nimble/skills/`, `nimble/tools/`, `nimble/manifest/` etc.

### Architecture Guardrails

| Rule | Enforcement |
|---|---|
| `mypy --strict` across all `nimble/` code | Configured in `[tool.mypy]` |
| Absolute imports only — no relative imports | Enforced by flake8 + code review |
| snake_case for all Python identifiers | Enforced by flake8 + black |
| All function params and return types annotated | mypy --strict |
| No platform-specific code in `nimble/cli/commands.py` | N/A this story — but establish the pattern |

### `.gitignore` Must Contain

```
# Tool-managed runtime dir — gitignored EXCEPT manifest.lock
.nimble/
!.nimble/manifest.lock

# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
*.egg
```

**Critical:** `.nimble/` is gitignored but `manifest.lock` inside it is NOT. The `!.nimble/manifest.lock` negation pattern is required to allow reproducible installs across machines (FR26).

### Anti-Patterns to Avoid

- **Do NOT add `worker/` to `[tool.hatch.build.targets.wheel] packages`** — `worker/` is an independent subprocess script, not an installed package. It imports from `nimble.*` via `sys.path` injection at runtime.
- **Do NOT pin pytest** in dev deps — patch version differences don't matter and pinning causes unnecessary friction in forks. Use an unversioned `"pytest"` dep.
- **Do NOT create `nimble/daemon.py` yet** — that is Epic 2 work. This story is strictly toolchain scaffolding.
- **Do NOT add any business logic to `nimble/__init__.py`** — it should only contain the version string (e.g. `__version__ = "1.0.0"`).

### Cross-Story Context

- **Story 1.2** builds on this scaffold to add `tests/conftest.py` shared fixtures and `tests/unit/hotkeys/fake_adapter.py` — do not pre-empt this work.
- **Story 1.3** adds `.github/workflows/ci.yml` — do not create it here.
- **Story 2.1** adds `nimble/hotkeys/base.py` (`HotkeyAdapter` ABC) — the architecture references `FakeHotkeyAdapter` as existing "from Story 1 (or the infrastructure story)". This is Story 1.2's responsibility, not 1.1.

### Testing Requirements

- `pytest` should exit 0 with zero tests collected (empty suite is valid).
- No `conftest.py` needed in this story — that is Story 1.2.
- Verify `pytest` can discover the `tests/` directory without errors.

### Project Structure Notes

- `config.yaml` lives at repo root (not inside `nimble/`) — this is the user's committed hotkey config per architecture decision.
- `worker/` lives at repo root (not inside `nimble/`) — it is a sibling package, not part of the installed `nimble` wheel. This placement is intentional: community skill workers run under an isolated venv Python that doesn't have `nimble` installed, but can resolve `worker/entrypoint.py` via the script path.

### References

- pyproject.toml exact content: [Source: docs/bmad_output/planning-artifacts/architecture.md#Starter Template Evaluation / pyproject.toml Scaffold]
- Tooling versions: [Source: docs/bmad_output/planning-artifacts/architecture.md#Tooling Stack]
- Repository structure: [Source: docs/bmad_output/planning-artifacts/architecture.md#Complete Project Directory Structure]
- `worker/` sys.path injection rationale: [Source: docs/bmad_output/planning-artifacts/architecture.md#Per-Skill Venv Activation]
- `.gitignore` manifest.lock exception: [Source: docs/bmad_output/planning-artifacts/epics.md#Story 6.5 / FR26, FR43]
- Epic 1 overview: [Source: docs/bmad_output/planning-artifacts/epics.md#Epic 1: Project Foundation & Dev Toolchain]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List
