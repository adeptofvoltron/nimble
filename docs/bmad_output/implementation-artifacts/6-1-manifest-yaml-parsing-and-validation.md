# Story 6.1: `manifest.yaml` Parsing and Validation

Status: done

## Story

As the `nimble add` command,
I want to fetch and validate a skill's `manifest.yaml` from a GitHub repository,
So that I have a verified, typed representation of the skill's metadata before touching the filesystem.

## Acceptance Criteria

1. **Given** a valid `manifest.yaml` at a remote repository URL
   **When** `nimble/manifest/parser.py` fetches and parses it
   **Then** it returns a typed `ManifestSpec` dataclass with all required fields: `name`, `version`, `api_version`, `description`, `entrypoint`, `requires`, `permissions`, `dependencies`, `author` (FR27)

2. **Given** the remote `manifest.yaml` is missing a required field (e.g. `entrypoint`)
   **When** parsing is attempted
   **Then** a `ManifestError` is raised identifying the missing field — install is aborted before any filesystem changes

3. **Given** a `manifest.yaml` with `api_version` higher than the daemon supports
   **When** it is parsed
   **Then** a `ManifestError` is raised: `"Skill requires Nimble api_version <N> — upgrade your daemon"` — install is aborted

## Tasks / Subtasks

- [x] Task 1: Add `ManifestError` and `ManifestSpec` to `nimble/manifest/parser.py` (AC: 1)
  - [x] Add `class ManifestError(Exception): pass` — distinct from `ConfigError` (which is for `config.yaml` parse errors)
  - [x] Add `ManifestSpec` dataclass with fields: `name: str`, `version: str`, `api_version: int`, `description: str`, `entrypoint: str`, `permissions: list[str]`, `dependencies: list[str]`, `author: str`, `requires: list[str] = field(default_factory=list)`, `class_name: str = ""`
  - [x] Import `field` from `dataclasses` (already imports `dataclass`)
  - [x] `requires` defaults to `[]` — not all manifests declare required context fields; hello_world does not
  - [x] `class_name` defaults to `""` — optional in the YAML schema; needed in Story 6.5 for config.yaml append

- [x] Task 2: Add `parse_manifest_yaml(content: str, source: str = "<string>") -> ManifestSpec` to `nimble/manifest/parser.py` (AC: 1, 2, 3)
  - [x] Parse YAML with `yaml.safe_load(content)`; on `yaml.YAMLError` raise `ManifestError(f"Invalid manifest.yaml from {source}: {exc}")`
  - [x] Verify parsed value is a `dict`; if not, raise `ManifestError(f"manifest.yaml from {source} must be a YAML mapping")`
  - [x] Required fields check: `{"name", "version", "api_version", "description", "entrypoint", "permissions", "dependencies", "author"}` — on missing fields raise `ManifestError(f"manifest.yaml missing required field(s): {', '.join(sorted(missing))}")`
  - [x] API version check: `from nimble import SUPPORTED_API_VERSION`; if `data["api_version"] > SUPPORTED_API_VERSION` raise `ManifestError(f"Skill requires Nimble api_version {api_version} — upgrade your daemon")` — exact string from AC3
  - [x] Cast all string fields with `str(...)` and lists with `list(...)` — YAML may return unexpected types for short values
  - [x] Return `ManifestSpec(...)` populating all fields; use `data.get("requires", [])` and `data.get("class_name", "")` for optional fields

- [x] Task 3: Add `_github_url_to_raw(repo_url: str) -> str` (private helper) to `nimble/manifest/parser.py` (AC: 1)
  - [x] Strip trailing `/`, strip `.git` suffix if present
  - [x] Strip protocol prefixes: `"https://github.com/"`, `"http://github.com/"`, `"github.com/"`
  - [x] Remaining string must be `"user/repo"` form — extract first two `/`-separated parts; if fewer than 2 parts raise `ManifestError(f"Invalid GitHub URL: {repo_url!r}")`
  - [x] Return `f"https://raw.githubusercontent.com/{user}/{repo}/HEAD/manifest.yaml"` — `HEAD` resolves to any default branch name (avoids `main` vs `master` ambiguity)

- [x] Task 4: Add `fetch_remote_manifest(repo_url: str) -> ManifestSpec` to `nimble/manifest/parser.py` (AC: 1, 2, 3)
  - [x] Call `_github_url_to_raw(repo_url)` to get the raw URL
  - [x] Add `import urllib.request` and `import urllib.error` to the stdlib imports block (top of file, after `import os`)
  - [x] Fetch with `urllib.request.urlopen(raw_url, timeout=30)` — 30s gives enough headroom for slow connections without hanging indefinitely
  - [x] Decode response body as UTF-8: `response.read().decode("utf-8")`
  - [x] Wrap fetch in `try/except`: catch `urllib.error.HTTPError as exc` → raise `ManifestError(f"Could not fetch manifest.yaml from {repo_url}: HTTP {exc.code}")`, catch broad `Exception as exc` → raise `ManifestError(f"Could not fetch manifest.yaml from {repo_url}: {exc}")`
  - [x] Call `parse_manifest_yaml(content, source=repo_url)` and return the result
  - [x] Use context manager: `with urllib.request.urlopen(...) as response:`

- [x] Task 5: Add unit tests to `tests/unit/manifest/test_parser.py` (AC: 1, 2, 3)
  - [x] `test_parse_manifest_yaml_valid()` — parse a complete manifest YAML string; assert all ManifestSpec fields
  - [x] `test_parse_manifest_yaml_missing_required_field()` — omit `entrypoint`; assert `ManifestError` raised, message contains `"entrypoint"`
  - [x] `test_parse_manifest_yaml_api_version_too_high()` — set `api_version: 99`; assert `ManifestError` with message matching `"upgrade your daemon"`
  - [x] `test_parse_manifest_yaml_api_version_equal_supported_ok()` — `api_version` equal to `SUPPORTED_API_VERSION` (currently 1); assert no error
  - [x] `test_parse_manifest_yaml_invalid_yaml()` — pass `"not: valid: yaml: :::"` content; assert `ManifestError` raised
  - [x] `test_parse_manifest_yaml_requires_defaults_to_empty()` — omit `requires` field; assert `ManifestSpec.requires == []`
  - [x] `test_github_url_to_raw_https()` — input `"https://github.com/user/repo"` → assert URL contains `"raw.githubusercontent.com/user/repo/HEAD/manifest.yaml"`
  - [x] `test_github_url_to_raw_without_protocol()` — input `"github.com/user/repo"` → same assertion
  - [x] `test_github_url_to_raw_with_git_suffix()` — input `"https://github.com/user/repo.git"` → same assertion
  - [x] `test_fetch_remote_manifest_success()` — patch `urllib.request.urlopen` to return a mock with `.read()` returning valid YAML bytes; assert `ManifestSpec` returned with correct `name`
  - [x] `test_fetch_remote_manifest_http_error()` — patch `urlopen` to raise `urllib.error.HTTPError(None, 404, "Not Found", {}, None)`; assert `ManifestError` raised with `"HTTP 404"` in message
  - [x] `test_fetch_remote_manifest_network_error()` — patch `urlopen` to raise `OSError("timeout")`; assert `ManifestError` raised

- [x] Task 6: Verify quality gates
  - [x] `.venv/bin/pytest tests/unit/ -q` — all tests pass (baseline 242 + ~12 new = ~254)
  - [x] `.venv/bin/mypy nimble/ tests/ worker/` — exits 0 (pre-existing 3 errors in `test_platform.py` unchanged; 0 new errors in `nimble/`)
  - [x] `.venv/bin/black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

### Review Findings

- [x] [Review][Patch] `api_version` type conversion can raise raw `ValueError`/`TypeError` instead of `ManifestError` [nimble/manifest/parser.py:226]
- [x] [Review][Patch] `permissions` / `dependencies` / `requires` accept malformed scalar or mapping types via `list(...)` coercion [nimble/manifest/parser.py:240]
- [x] [Review][Patch] Invalid domain values for `api_version` (e.g. `true`, `0`, negative) are accepted without validation [nimble/manifest/parser.py:226]

## Dev Notes

### What Already EXISTS — Do NOT Reinvent

**`nimble/manifest/parser.py`** — already has:
- `ConfigError(Exception)` — for `config.yaml` parse errors. Do NOT reuse for manifest errors — they are different concerns
- `atomic_write(path, content)` — write-to-tmp + rename pattern for safe config writes
- `read_skill_manifest(config, base_path)` — reads local on-disk `manifest.yaml` for author skills. Do NOT use for remote community skills — this is the wrong function
- `disable_skill_in_config(config_path, skill_name)` — adds `disabled: true` to config.yaml
- `load_config(config_path)` — parses `config.yaml`; uses `ConfigError`, `NimbleConfig`, `SkillConfig`
- `_parse_skills(raw)` — already skips `disabled: true` entries
- Imports already present: `yaml`, `os`, `tempfile`, `dataclass`, `Path`, `Any`, `logging`

**`nimble/__init__.py`** — exports `SUPPORTED_API_VERSION: int = 1`. Import it as `from nimble import SUPPORTED_API_VERSION` inside `parse_manifest_yaml`.

**`skills/hello_world/manifest.yaml`** — the reference for what a valid manifest looks like:
```yaml
name: hello_world
version: "1.0.0"
api_version: 1
description: "Bundled test skill — fires a notification to confirm the daemon is working"
entrypoint: skill.py
class_name: HelloWorldSkill
permissions: []
dependencies: []
author: "Nimble Template"
```
Note: no `requires` field — this field is optional (defaults to `[]`).

**`tests/unit/manifest/test_parser.py`** — existing test file. Add new tests at the bottom, following the existing `_write_config` helper pattern. File already imports `from nimble.manifest.parser import ...` — add `ManifestError`, `ManifestSpec`, `parse_manifest_yaml`, `fetch_remote_manifest` to the import list.

### `ManifestSpec` and `ManifestError` Implementation

Add immediately after the existing `ManifestError` class (which you're creating) and before `atomic_write`:

```python
class ManifestError(Exception):
    pass


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

**Import change:** Change `from dataclasses import dataclass` to `from dataclasses import dataclass, field`.

**Placement:** Place `ManifestError` and `ManifestSpec` after the existing `ConfigError` class. Keep `AiConfig` and `NimbleConfig` after `ManifestSpec` — they are for config.yaml parsing and should stay grouped logically.

### `parse_manifest_yaml` Implementation

```python
def parse_manifest_yaml(content: str, source: str = "<string>") -> ManifestSpec:
    from nimble import SUPPORTED_API_VERSION

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ManifestError(f"Invalid manifest.yaml from {source}: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestError(f"manifest.yaml from {source} must be a YAML mapping")

    required_fields = {
        "name", "version", "api_version", "description",
        "entrypoint", "permissions", "dependencies", "author",
    }
    missing = required_fields - data.keys()
    if missing:
        raise ManifestError(
            f"manifest.yaml missing required field(s): {', '.join(sorted(missing))}"
        )

    api_version = int(data["api_version"])
    if api_version > SUPPORTED_API_VERSION:
        raise ManifestError(
            f"Skill requires Nimble api_version {api_version} — upgrade your daemon"
        )

    return ManifestSpec(
        name=str(data["name"]),
        version=str(data["version"]),
        api_version=api_version,
        description=str(data["description"]),
        entrypoint=str(data["entrypoint"]),
        permissions=list(data["permissions"]),
        dependencies=list(data["dependencies"]),
        author=str(data["author"]),
        requires=list(data.get("requires", [])),
        class_name=str(data.get("class_name", "")),
    )
```

**Why `from nimble import SUPPORTED_API_VERSION` inside the function:** Avoids circular imports — `nimble/__init__.py` imports nothing from `nimble.manifest.parser`, but placing it at module level could be fragile. The inline import pattern is safe and matches the CLI commands pattern.

**Why `int(data["api_version"])`:** YAML `api_version: 1` parses as `int` in pyyaml, but `api_version: "1"` would be a string. Wrapping with `int()` handles both and fails loudly for non-numeric values (ValueError propagates as a meaningful crash, not a silent wrong comparison).

### `_github_url_to_raw` Implementation

```python
def _github_url_to_raw(repo_url: str) -> str:
    url = repo_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if url.startswith(prefix):
            url = url[len(prefix):]
            break
    parts = url.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ManifestError(f"Invalid GitHub URL: {repo_url!r}")
    user, repo = parts[0], parts[1]
    return f"https://raw.githubusercontent.com/{user}/{repo}/HEAD/manifest.yaml"
```

**Why `HEAD`:** Works for any default branch name (`main`, `master`, or custom). No need to try `main` and fall back to `master`.

### `fetch_remote_manifest` Implementation

```python
def fetch_remote_manifest(repo_url: str) -> ManifestSpec:
    raw_url = _github_url_to_raw(repo_url)
    try:
        with urllib.request.urlopen(raw_url, timeout=30) as response:
            content = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise ManifestError(
            f"Could not fetch manifest.yaml from {repo_url}: HTTP {exc.code}"
        ) from exc
    except Exception as exc:
        raise ManifestError(
            f"Could not fetch manifest.yaml from {repo_url}: {exc}"
        ) from exc
    return parse_manifest_yaml(content, source=repo_url)
```

**Import additions** — add to the stdlib block at the top of `parser.py` (after `import os`, before `import tempfile`):
```python
import urllib.error
import urllib.request
```

**Why broad `except Exception` for the outer catch:** Covers `urllib.error.URLError`, `OSError` (timeout), `UnicodeDecodeError`, and any other network error. The `HTTPError` case is caught first (it subclasses `URLError`) so it gets its own message with the status code. This is the correct ordering — specific before broad.

**mypy note:** `urllib.request.urlopen` return type is `http.client.HTTPResponse` — mypy knows this from stdlib stubs. No `Any` cast needed. The `with` statement is valid.

### Test Implementations

```python
import io
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

from nimble import SUPPORTED_API_VERSION
from nimble.manifest.parser import (
    ...,
    ManifestError,
    ManifestSpec,
    fetch_remote_manifest,
    parse_manifest_yaml,
)


_VALID_MANIFEST_YAML = """\
name: test-skill
version: "1.2.3"
api_version: 1
description: A test skill
entrypoint: skill.py
class_name: TestSkill
permissions:
  - ai
dependencies:
  - anthropic
author: Test Author
"""


def test_parse_manifest_yaml_valid() -> None:
    spec = parse_manifest_yaml(_VALID_MANIFEST_YAML)
    assert spec.name == "test-skill"
    assert spec.version == "1.2.3"
    assert spec.api_version == 1
    assert spec.permissions == ["ai"]
    assert spec.dependencies == ["anthropic"]
    assert spec.class_name == "TestSkill"
    assert spec.requires == []


def test_parse_manifest_yaml_missing_required_field() -> None:
    content = _VALID_MANIFEST_YAML.replace("entrypoint: skill.py\n", "")
    with pytest.raises(ManifestError, match="entrypoint"):
        parse_manifest_yaml(content)


def test_parse_manifest_yaml_api_version_too_high() -> None:
    content = _VALID_MANIFEST_YAML.replace("api_version: 1", "api_version: 99")
    with pytest.raises(ManifestError, match="upgrade your daemon"):
        parse_manifest_yaml(content)


def test_parse_manifest_yaml_api_version_equal_supported_ok() -> None:
    content = _VALID_MANIFEST_YAML.replace("api_version: 1", f"api_version: {SUPPORTED_API_VERSION}")
    spec = parse_manifest_yaml(content)
    assert spec.api_version == SUPPORTED_API_VERSION


def test_parse_manifest_yaml_invalid_yaml() -> None:
    with pytest.raises(ManifestError, match="Invalid manifest"):
        parse_manifest_yaml("not: valid: yaml: :::")


def test_parse_manifest_yaml_requires_defaults_to_empty() -> None:
    spec = parse_manifest_yaml(_VALID_MANIFEST_YAML)
    assert spec.requires == []


def test_github_url_to_raw_https() -> None:
    from nimble.manifest.parser import _github_url_to_raw
    url = _github_url_to_raw("https://github.com/user/my-skill")
    assert url == "https://raw.githubusercontent.com/user/my-skill/HEAD/manifest.yaml"


def test_github_url_to_raw_without_protocol() -> None:
    from nimble.manifest.parser import _github_url_to_raw
    url = _github_url_to_raw("github.com/user/my-skill")
    assert url == "https://raw.githubusercontent.com/user/my-skill/HEAD/manifest.yaml"


def test_github_url_to_raw_with_git_suffix() -> None:
    from nimble.manifest.parser import _github_url_to_raw
    url = _github_url_to_raw("https://github.com/user/my-skill.git")
    assert url == "https://raw.githubusercontent.com/user/my-skill/HEAD/manifest.yaml"


def test_fetch_remote_manifest_success() -> None:
    mock_response = MagicMock()
    mock_response.read.return_value = _VALID_MANIFEST_YAML.encode("utf-8")
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_response):
        spec = fetch_remote_manifest("github.com/user/test-skill")
    assert spec.name == "test-skill"


def test_fetch_remote_manifest_http_error() -> None:
    err = urllib.error.HTTPError(None, 404, "Not Found", {}, None)  # type: ignore[arg-type]
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(ManifestError, match="HTTP 404"):
            fetch_remote_manifest("github.com/user/missing-skill")


def test_fetch_remote_manifest_network_error() -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
        with pytest.raises(ManifestError, match="Could not fetch"):
            fetch_remote_manifest("github.com/user/unreachable-skill")
```

**Import additions for test file:** Add `import io`, `import urllib.error`, `import urllib.request`, `from unittest.mock import MagicMock, patch`, and `from nimble import SUPPORTED_API_VERSION` to the imports at the top. The `from nimble.manifest.parser import ...` line needs `ManifestError`, `ManifestSpec`, `fetch_remote_manifest`, `parse_manifest_yaml` added.

**mypy note:** `urllib.error.HTTPError(None, 404, ...)` — the first arg (`url`) is typed as `str` but mypy accepts `None` in practice; if mypy complains use `# type: ignore[arg-type]` (already shown in the test).

### mypy Compliance

All new functions require full annotation:
```python
def parse_manifest_yaml(content: str, source: str = "<string>") -> ManifestSpec: ...
def _github_url_to_raw(repo_url: str) -> str: ...
def fetch_remote_manifest(repo_url: str) -> ManifestSpec: ...
```

`ManifestSpec` uses `list[str]` (not `List[str]`) — Python 3.10+ built-in generics are correct here and match the existing codebase style.

### Architecture Compliance

- This story adds **purely to `nimble/manifest/parser.py`** — no CLI command yet. The `nimble add` CLI command is assembled in Story 6.5.
- No filesystem operations in this story — install confirmation (Story 6.2), venv creation (Story 6.3), and config append (Story 6.5) are separate stories.
- Uses only stdlib for HTTP (`urllib.request`) — no new pip dependencies, consistent with NFR19 (standard tooling only).
- `ManifestError` vs `ConfigError` — `ConfigError` is for local `config.yaml` parse errors; `ManifestError` is for remote manifest.yaml fetch/parse errors. Keep them distinct.

### Out of Scope for This Story

- `nimble add` CLI command (Story 6.5)
- Permissions display / user confirmation prompt (Story 6.2)
- Venv creation and pip install (Story 6.3)
- Config.yaml append and `manifest.lock` (Story 6.5)
- `.nimble/skills/` directory structure (Story 6.5)
- `nimble/manifest/lock.py` (Story 6.5)

### File List to Touch

- `nimble/manifest/parser.py` — add `ManifestError`, `ManifestSpec` dataclass; add `parse_manifest_yaml`, `_github_url_to_raw`, `fetch_remote_manifest`; add `urllib.request` and `urllib.error` imports; change `from dataclasses import dataclass` to `from dataclasses import dataclass, field`
- `tests/unit/manifest/test_parser.py` — add 12 new tests and required imports

### Baseline (Before This Story)

```
Tests: 242 passed (0 collection errors)
mypy: 3 pre-existing errors in tests/unit/platform/test_platform.py — unchanged; 0 errors in nimble/
black: clean
flake8: clean (nimble/ tests/ worker/ only)
```

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 6.1] — acceptance criteria, FR27
- [Source: docs/bmad_output/planning-artifacts/architecture.md#nimble add flow] — data flow, manifest/parser.py role
- [Source: nimble/__init__.py] — `SUPPORTED_API_VERSION = 1`
- [Source: nimble/manifest/parser.py] — existing `ConfigError`, `atomic_write`, patterns
- [Source: skills/hello_world/manifest.yaml] — reference manifest schema
- [Source: tests/unit/manifest/test_parser.py] — existing parser test patterns
- [Source: docs/bmad_output/implementation-artifacts/5-3-nimble-disable.md] — previous story patterns, `disable_skill_in_config` as example

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Added `ManifestError` exception and `ManifestSpec` dataclass to `nimble/manifest/parser.py` after existing `ConfigError`. Updated `from dataclasses import dataclass` to `from dataclasses import dataclass, field`.
- Added `parse_manifest_yaml()` with YAML parse, dict check, required-field validation, api_version gate, and typed `ManifestSpec` return. Uses inline `from nimble import SUPPORTED_API_VERSION` to avoid circular imports.
- Added `_github_url_to_raw()` private helper supporting https/http/bare github.com URLs and `.git` suffix stripping; uses `HEAD` to avoid main/master ambiguity.
- Added `fetch_remote_manifest()` using `urllib.request.urlopen` with 30s timeout; catches `HTTPError` separately from broad `Exception` for distinct error messages.
- Added 12 unit tests (6 for parse_manifest_yaml, 3 for _github_url_to_raw, 3 for fetch_remote_manifest) with `MagicMock` patching for network calls.
- Fixed pre-existing flake8 E501 in `nimble/cli/commands.py` (from story 5-3) and added `extend-ignore = E203` to `setup.cfg` to resolve black/flake8 slice-notation conflict.
- All quality gates pass: 254 tests, black clean, flake8 clean, 0 new mypy errors in nimble/.

### File List

- nimble/manifest/parser.py
- tests/unit/manifest/test_parser.py
- nimble/cli/commands.py
- setup.cfg

## Change Log

- 2026-05-01: Story created — ready for dev
- 2026-05-01: Implemented all tasks — ManifestError, ManifestSpec, parse_manifest_yaml, _github_url_to_raw, fetch_remote_manifest; 12 new tests; all quality gates pass — status: review
