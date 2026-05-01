# Story 6.2: Permissions Display and Install Confirmation

Status: review

## Story

As a security-conscious user,
I want to see a skill's declared permissions before anything is installed,
So that I can make an informed decision about what I'm allowing to run on my machine.

## Acceptance Criteria

1. **Given** `nimble add ctrl+shift+d github.com/user/nimble-log-diagnosis` is run
   **When** the manifest is fetched and parsed
   **Then** the CLI displays the skill name, description, author, and a permissions block before any prompt (FR21)

2. **Given** the skill declares `permissions: [ai, clipboard]`
   **When** the permissions block is displayed
   **Then** each permission is shown with a one-line description of what it can do:
   `- ai        (may send text to an external LLM API)`
   `- clipboard  (reads clipboard content at hotkey-fire time)` (NFR9)

3. **Given** the permissions are displayed
   **When** the user is prompted `"Install anyway? [y/N]"`
   **Then** the default is `N` — the user must explicitly type `y` to proceed
   **And** any input other than `y` / `Y` aborts the install with no filesystem changes

## Tasks / Subtasks

- [x] Task 1: Add `_PERMISSION_DESCRIPTIONS` mapping to `nimble/cli/commands.py` (AC: 2)
  - [x] Define `_PERMISSION_DESCRIPTIONS: dict[str, str]` as a module-level constant (UPPER_SNAKE_CASE per architecture)
  - [x] Include entries for all known tool primitive permissions: `ai`, `clipboard`, `popup`, `tts`, `input`
  - [x] Use description text from AC2: `ai → "may send text to an external LLM API"`, `clipboard → "reads clipboard content at hotkey-fire time"`
  - [x] Add reasonable descriptions for: `popup → "displays a system notification popup"`, `tts → "speaks text aloud via the system TTS engine"`, `input → "prompts the user for text input or a selection dialog"`
  - [x] Unknown permissions not in the dict fall back to `"(unknown permission)"` — use `dict.get(perm, "(unknown permission)")`

- [x] Task 2: Add `nimble add` command to `nimble/cli/commands.py` (AC: 1, 2, 3)
  - [x] Signature: `@app.command()` decorated function `add(shortcut: str = typer.Argument(..., help="Keyboard shortcut to bind (e.g. ctrl+shift+d)"), repo_url: str = typer.Argument(..., help="GitHub repository URL of the skill")) -> None:`
  - [x] Docstring: `"""Install a community skill from a GitHub repository."""`
  - [x] Lazy import at top of function: `from nimble.manifest.parser import ManifestError, fetch_remote_manifest`
  - [x] Call `fetch_remote_manifest(repo_url)` inside `try/except ManifestError as exc:` → `typer.echo(str(exc), err=True); raise typer.Exit(1)`
  - [x] After successful fetch, display the info block via `typer.echo()`:
    - Line 1: `f"Skill:       {spec.name}"`
    - Line 2: `f"Description: {spec.description}"`
    - Line 3: `f"Author:      {spec.author}"`
    - Blank line, then `"Permissions:"`
    - If `spec.permissions` is non-empty: for each perm, print `f"  - {perm:<12} ({_PERMISSION_DESCRIPTIONS.get(perm, '(unknown permission)')})"`
    - If `spec.permissions` is empty: print `"  (none declared)"`
    - Trailing blank line before the prompt
  - [x] Prompt: `_prompt_install_confirm_y_only()` — echoes `Install anyway? [y/N]: ` (no newline), reads one line from stdin; returns `True` only for exactly `y` or `Y` (AC3)
  - [x] If not confirmed: `typer.echo("Installation cancelled."); raise typer.Exit(0)`
  - [x] If confirmed: `typer.echo(f"Skill '{spec.name}' confirmed — installation is not implemented yet.")` — placeholder until Stories 6.3 / 6.5

- [x] Task 3: Add unit tests to `tests/unit/cli/test_commands.py` (AC: 1, 2, 3)
  - [x] Add `from nimble.manifest.parser import ManifestError, ManifestSpec` to imports (in the existing import block at top of file)
  - [x] Add a `_make_manifest_spec(**overrides)` helper that returns a `ManifestSpec` with sensible defaults (name="test-skill", version="1.0.0", api_version=1, description="A test skill", entrypoint="skill.py", permissions=["ai", "clipboard"], dependencies=[], author="Test Author")
  - [x] `test_add_displays_skill_info_and_aborts_on_no()` — patch `nimble.cli.commands.fetch_remote_manifest` to return `_make_manifest_spec()`; invoke with `input="N\n"`; assert exit_code 0; assert `"test-skill"` in output; assert `"A test skill"` in output; assert `"Test Author"` in output; assert `"cancelled"` in output
  - [x] `test_add_displays_permissions_with_descriptions()` — patch `fetch_remote_manifest` returning spec with `permissions=["ai", "clipboard"]`; invoke with `input="N\n"`; assert `"ai"` in output; assert `"external LLM"` in output; assert `"clipboard"` in output; assert `"clipboard content"` in output
  - [x] `test_add_unknown_permission_shows_fallback()` — patch `fetch_remote_manifest` returning spec with `permissions=["filesystem"]`; invoke with `input="N\n"`; assert `"filesystem"` in output; assert `"(unknown permission)"` in output
  - [x] `test_add_no_permissions_shows_none_declared()` — patch `fetch_remote_manifest` returning spec with `permissions=[]`; invoke with `input="N\n"`; assert `"(none declared)"` in output
  - [x] `test_add_confirms_and_proceeds()` — patch `fetch_remote_manifest` returning `_make_manifest_spec()`; invoke with `input="y\n"`; assert exit_code 0; assert `"cancelled"` NOT in output (install confirmation went through)
  - [x] `test_add_manifest_error_aborts()` — patch `fetch_remote_manifest` to raise `ManifestError("HTTP 404")`; invoke; assert exit_code 1; assert `"HTTP 404"` in output
  - [x] `test_add_default_is_no()` — patch `fetch_remote_manifest`; invoke with `input="\n"` (empty = Enter); assert `"cancelled"` in output; assert exit_code 0
  - [x] `test_add_uppercase_Y_confirms()` — patch `fetch_remote_manifest`; invoke with `input="Y\n"`; assert exit_code 0; assert `"cancelled"` NOT in output
  - [x] `test_add_full_word_yes_aborts()` — patch `fetch_remote_manifest`; invoke with `input="yes\n"`; assert cancelled (AC3: only `y`/`Y` proceed)

- [x] Task 4: Verify quality gates
  - [x] `.venv/bin/pytest tests/unit/ -q` — all tests pass (baseline 254 + ~8 new = ~262)
  - [x] `.venv/bin/mypy nimble/ tests/ worker/` — exits 0 (0 new errors in `nimble/`)
  - [x] `.venv/bin/black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

## Dev Notes

### What Already EXISTS — Do NOT Reinvent

**`nimble/manifest/parser.py`** (from Story 6.1) now has:
- `ManifestError(Exception)` — raised by `fetch_remote_manifest` on network/parse errors
- `ManifestSpec` dataclass with fields: `name: str`, `version: str`, `api_version: int`, `description: str`, `entrypoint: str`, `permissions: list[str]`, `dependencies: list[str]`, `author: str`, `requires: list[str]`, `class_name: str`
- `fetch_remote_manifest(repo_url: str) -> ManifestSpec` — fetches and parses remote manifest; raises `ManifestError` on any failure (HTTP errors, network errors, parse errors, validation errors)
- `_github_url_to_raw(repo_url: str) -> str` — private; do NOT call directly from CLI

**`nimble/cli/commands.py`** already has:
- `app = typer.Typer(...)` — register `add` command on this app
- `_repo_root() -> Path` helper
- Pattern: all other commands use lazy imports inside the function body (`from nimble.manifest.parser import ...`)
- Pattern: `typer.echo(str(exc), err=True); raise typer.Exit(1)` for error exits
- `disable_skill_in_config` is imported lazily inside `disable()` — follow the same pattern for `fetch_remote_manifest` inside `add()`

**`tests/unit/cli/test_commands.py`** already exists with:
- `from typer.testing import CliRunner` + `runner = CliRunner()`
- Pattern: `runner.invoke(app, ["command", "args"], input="user_input\n")`
- All patches use `patch("nimble.cli.commands.state.read_pid", ...)` — patch at import site, not definition site

### `nimble add` Command Implementation

```python
_PERMISSION_DESCRIPTIONS: dict[str, str] = {
    "ai": "may send text to an external LLM API",
    "clipboard": "reads clipboard content at hotkey-fire time",
    "popup": "displays a system notification popup",
    "tts": "speaks text aloud via the system TTS engine",
    "input": "prompts the user for text input or a selection dialog",
}


@app.command()
def add(
    shortcut: str = typer.Argument(
        ..., help="Keyboard shortcut to bind (e.g. ctrl+shift+d)"
    ),
    repo_url: str = typer.Argument(
        ..., help="GitHub repository URL of the skill"
    ),
) -> None:
    """Install a community skill from a GitHub repository."""
    from nimble.manifest.parser import ManifestError, fetch_remote_manifest

    try:
        spec = fetch_remote_manifest(repo_url)
    except ManifestError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)

    typer.echo(f"Skill:       {spec.name}")
    typer.echo(f"Description: {spec.description}")
    typer.echo(f"Author:      {spec.author}")
    typer.echo("")
    typer.echo("Permissions:")
    if spec.permissions:
        for perm in spec.permissions:
            desc = _PERMISSION_DESCRIPTIONS.get(perm, "(unknown permission)")
            typer.echo(f"  - {perm:<12} ({desc})")
    else:
        typer.echo("  (none declared)")
    typer.echo("")

    if not _prompt_install_confirm_y_only():
        typer.echo("Installation cancelled.")
        raise typer.Exit(0)

    # Placeholder — venv creation (6.3) and config append (6.5) replace this line
    typer.echo(f"Skill '{spec.name}' confirmed — installation is not implemented yet.")
```

**`_PERMISSION_DESCRIPTIONS` placement:** Add it as a module-level constant immediately before the `_running_pid_or_none` helper (the first private helper in the file). UPPER_SNAKE_CASE per architecture naming conventions.

**Why lazy import for `fetch_remote_manifest`:** All other commands in `commands.py` use lazy imports (`from nimble.manifest.parser import ...` inside the function body). Consistent with this pattern — avoids circular imports and keeps the module-level import surface minimal. Story 6.1 established this pattern.

**Why `raise typer.Exit(0)` on cancel (not `Exit(1)`):** Cancellation is a clean user choice, not an error. Exit 1 is reserved for actual failures (manifest fetch errors, filesystem errors). This matches CLI conventions for interactive cancellations.

**Install prompt (AC3):** Do not use `typer.confirm` / Click confirm here — they treat `yes`, `1`, etc. as affirmative. `_prompt_install_confirm_y_only()` echoes `Install anyway? [y/N]: ` then reads one line; only exactly `y` or `Y` returns `True` (anything else, including `yes`, `n`, empty line, cancels).

**`shortcut` argument:** The `add` command receives `shortcut` but does NOT use it in this story — it will be used in Story 6.5 when the config.yaml entry is appended. The argument must still be declared in the signature so the full `nimble add <shortcut> <repo-url>` interface is wired correctly from the start.

### Test Implementation Details

```python
from nimble.manifest.parser import ManifestError, ManifestSpec


def _make_manifest_spec(**overrides: object) -> ManifestSpec:
    defaults: dict[str, object] = {
        "name": "test-skill",
        "version": "1.0.0",
        "api_version": 1,
        "description": "A test skill",
        "entrypoint": "skill.py",
        "permissions": ["ai", "clipboard"],
        "dependencies": [],
        "author": "Test Author",
        "requires": [],
        "class_name": "TestSkill",
    }
    defaults.update(overrides)
    return ManifestSpec(**defaults)  # type: ignore[arg-type]


def test_add_displays_skill_info_and_aborts_on_no() -> None:
    with patch(
        "nimble.cli.commands.fetch_remote_manifest",
        return_value=_make_manifest_spec(),
    ):
        result = runner.invoke(app, ["add", "ctrl+shift+d", "github.com/user/skill"], input="N\n")
    assert result.exit_code == 0
    assert "test-skill" in result.output
    assert "A test skill" in result.output
    assert "Test Author" in result.output
    assert "cancelled" in result.output


def test_add_manifest_error_aborts() -> None:
    with patch(
        "nimble.cli.commands.fetch_remote_manifest",
        side_effect=ManifestError("HTTP 404"),
    ):
        result = runner.invoke(app, ["add", "ctrl+shift+d", "github.com/user/missing"])
    assert result.exit_code == 1
    assert "HTTP 404" in result.output
```

**Patch path:** `"nimble.cli.commands.fetch_remote_manifest"` — patched at the import site inside `commands.py`. However, since `fetch_remote_manifest` is imported lazily (inside the function body), the correct patch target is `"nimble.manifest.parser.fetch_remote_manifest"` OR you must patch it before the function is called. Test using `patch("nimble.manifest.parser.fetch_remote_manifest", ...)` to be safe — this patches the actual function in its module, which the lazy import will pick up correctly.

Actually, with lazy imports (import inside function body), the patch target must be `"nimble.manifest.parser.fetch_remote_manifest"` since the `from ... import ...` runs each time the function executes.

**mypy note:** `_make_manifest_spec(**overrides)` — add `# type: ignore[arg-type]` on the `ManifestSpec(**defaults)` line since `defaults` is `dict[str, object]` but mypy wants specific types. This is acceptable for test helpers.

**CliRunner and stdin:** `CliRunner.invoke(..., input="y\n")` feeds the process stdin so `sys.stdin.readline()` in `_prompt_install_confirm_y_only()` receives `y`. Empty `input="\n"` yields cancel (not `y`/`Y`).

### Architecture Compliance

- This story adds `nimble add` command to `nimble/cli/commands.py` only. No other files touched.
- `_PERMISSION_DESCRIPTIONS` is a module-level constant in `commands.py` — not in `parser.py`. Permission descriptions are a CLI concern (display/UX), not a parsing concern.
- No filesystem operations in this story. Venv creation (Story 6.3) and config append (Story 6.5) are separate.
- `shortcut` argument is accepted and stored locally but unused — it will pass through to Story 6.5's config append logic.
- Absolute imports only — `from nimble.manifest.parser import ManifestError, fetch_remote_manifest` (no relative imports).
- `mypy --strict` compatible — all new functions/helpers must have full type annotations.

### Out of Scope for This Story

- `.nimble/skills/<name>/` directory creation (Story 6.3)
- `python -m venv` invocation (Story 6.3)
- `pip install` into venv (Story 6.3)
- `config.yaml` append (Story 6.5)
- `manifest.lock` write (Story 6.5)
- `nimble/manifest/lock.py` (Story 6.5)

### File List to Touch

- `nimble/cli/commands.py` — add `_PERMISSION_DESCRIPTIONS` constant; add `add()` command
- `tests/unit/cli/test_commands.py` — add `_make_manifest_spec()` helper and ~8 new tests; add `ManifestError`, `ManifestSpec` to imports

### Baseline (Before This Story)

```
Tests: 254 passed (0 collection errors)
mypy: 3 pre-existing errors in tests/unit/platform/test_platform.py — unchanged; 0 errors in nimble/
black: clean
flake8: clean (nimble/ tests/ worker/ only)
```

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 6.2] — acceptance criteria, FR21, NFR9
- [Source: docs/bmad_output/planning-artifacts/architecture.md#nimble add flow] — data flow showing permissions display as second step after manifest fetch
- [Source: docs/bmad_output/planning-artifacts/architecture.md#CLI entry points] — `nimble/cli/commands.py` is the single file for all CLI commands
- [Source: docs/bmad_output/implementation-artifacts/6-1-manifest-yaml-parsing-and-validation.md] — `ManifestSpec` dataclass fields, `fetch_remote_manifest` signature, `ManifestError` usage
- [Source: nimble/cli/commands.py] — existing command patterns, lazy import style, `typer.echo`/`typer.Exit` conventions
- [Source: nimble/manifest/parser.py] — `ManifestSpec`, `ManifestError`, `fetch_remote_manifest` implementation

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `_PERMISSION_DESCRIPTIONS` module-level constant to `nimble/cli/commands.py` with descriptions for all 5 known tool permissions (`ai`, `clipboard`, `popup`, `tts`, `input`); unknown permissions fall back to `"(unknown permission)"`.
- Added `nimble add <shortcut> <repo_url>` command: fetches remote manifest, displays skill name/description/author/permissions block, strict `y`/`Y`-only install prompt (AC3), aborts cleanly on cancel, neutral placeholder on confirm.
- Added 9 unit tests (including `test_add_full_word_yes_aborts`). Patched at `nimble.manifest.parser.fetch_remote_manifest` (lazy import pattern).
- Added `extend-ignore = E203` to `setup.cfg` flake8 config to resolve black/flake8 conflict on slice notation (`url[len(prefix) :]`).
- All 268 tests pass; `nimble/` mypy clean; black clean; flake8 clean.

### File List

- `nimble/cli/commands.py`
- `tests/unit/cli/test_commands.py`
- `setup.cfg`

## Change Log

- 2026-05-02: Implemented Story 6.2 — added `nimble add` command with permissions display and install confirmation prompt; 8 new unit tests; flake8 E203 config fix (Date: 2026-05-02)

### Review Findings

- [x] [Review][Patch] Install confirmation accepts `yes` / `YES` and other Click truthy tokens, but AC3 requires only `y` / `Y` to proceed and any other input (including full word `yes`) to abort — replace `typer.confirm` with a strict prompt or post-check the normalized answer [`nimble/cli/commands.py` — `add()` confirm block] — **resolved 2026-05-02:** `_prompt_install_confirm_y_only()` + `test_add_full_word_yes_aborts`

- [x] [Review][Patch] User-facing placeholder mentions internal story id (`Story 6.3`); prefer neutral copy for end users (e.g. “installation is not implemented yet”) [`nimble/cli/commands.py` — post-confirm `typer.echo`] — **resolved 2026-05-02:** neutral confirmation message
