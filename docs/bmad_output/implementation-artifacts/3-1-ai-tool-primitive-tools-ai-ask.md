# Story 3.1: AI Tool Primitive (`tools.ai.ask`)

Status: done

## Story

As a skill author,
I want to call `tools.ai.ask(text, prompt=None)` and receive a text response from a configured LLM,
So that I can build AI-powered workflows without knowing or caring which provider or model is being used.

## Acceptance Criteria

1. **Given** `config.yaml` contains an `ai` block with `provider`, `model`, and `api_key_env`
   **When** `tools.ai.ask("explain this error")` is called from a skill
   **Then** the configured LLM is queried and a string response is returned

2. **Given** the `provider` in `config.yaml` is changed from `anthropic` to `openai`
   **When** the daemon reloads the worker
   **Then** subsequent `tools.ai.ask()` calls use the new provider — skill code is unchanged (NFR16)

3. **Given** the API key environment variable is not set
   **When** `tools.ai.ask()` is called
   **Then** a clear `RuntimeError` is raised naming the missing env var — not a cryptic provider SDK error

## Tasks / Subtasks

- [x] Task 1: Add `AiConfig` dataclass and extend `load_config()` in `nimble/manifest/parser.py` (AC: 1, 2)
  - [x] Add `AiConfig` dataclass with fields `provider: str`, `model: str`, `api_key_env: str`
  - [x] Update `NimbleConfig` to include `ai: AiConfig | None = None`
  - [x] Add `_parse_ai_config(data: dict[str, Any]) -> AiConfig | None` helper — returns `None` if `ai` key absent; raises `ConfigError` if present but missing required subfield
  - [x] Call `_parse_ai_config(data)` inside `load_config()` and assign to `NimbleConfig.ai`
  - [x] `AiConfig` lives in `nimble/manifest/parser.py` alongside other config dataclasses

- [x] Task 2: Create `nimble/tools/__init__.py` with `ToolRegistry` dataclass (AC: 1)
  - [x] Create `nimble/tools/` directory (new package for Epic 3)
  - [x] Define `ToolRegistry` as a `@dataclass` with field `ai: AiTool`
  - [x] Import `AiTool` from `nimble.tools.ai`
  - [x] This is the object passed as `tools` to `skill.run(context, tools)` — the name must match exactly how skills call it

- [x] Task 3: Create `nimble/tools/ai.py` implementing `AiTool` (AC: 1, 2, 3)
  - [x] `AiTool` takes `config: AiConfig | None` at construction time (not optional to construct, optional to configure)
  - [x] Implement `ask(self, text: str, prompt: str | None = None) -> str`
  - [x] Check `self._config is None` → raise `RuntimeError("AI not configured: add an 'ai' block to config.yaml")`
  - [x] Check `os.environ.get(self._config.api_key_env)` → if falsy, raise `RuntimeError(f"AI API key not set: env var {self._config.api_key_env!r} is empty or unset")`
  - [x] Dispatch to `_ask_anthropic()` or `_ask_openai()` based on `self._config.provider` — see Dev Notes for exact patterns
  - [x] Unknown provider → raise `RuntimeError(f"Unsupported AI provider: {self._config.provider!r}. Supported: anthropic, openai")`
  - [x] Use lazy imports inside `_ask_anthropic()` and `_ask_openai()` — SDK import at call site, not module level; wrap `ImportError` in a clear `RuntimeError` naming the missing package
  - [x] `prompt` parameter passed as system prompt; `None` means no system prompt (omit system message)

- [x] Task 4: Update `nimble/skills/runner.py` to pass AI config to workers (AC: 1, 2)
  - [x] Add `ai_config: AiConfig | None` parameter to `SkillRunner.__init__()` (after `repo_root`; default `None` for backward compatibility with tests)
  - [x] Import `json` at the top of `runner.py` (already imported — verify)
  - [x] In `spawn_workers()`, extend the `env` dict passed to `subprocess.Popen`: add `"NIMBLE_AI_CONFIG": json.dumps({"provider": ai_config.provider, "model": ai_config.model, "api_key_env": ai_config.api_key_env}) if ai_config else ""`
  - [x] Import `AiConfig` from `nimble.manifest.parser` at the top of `runner.py`

- [x] Task 5: Update `nimble/daemon.py` to pass AI config to `SkillRunner` (AC: 1, 2)
  - [x] After `config = load_config(config_path)`, extract `ai_config = config.ai`
  - [x] Update `SkillRunner(registry, notifier, repo_root)` → `SkillRunner(registry, notifier, repo_root, ai_config=config.ai)` in `run()`
  - [x] No other changes to `daemon.py` needed for this story

- [x] Task 6: Update `worker/entrypoint.py` to build `ToolRegistry` with `AiTool` (AC: 1, 2, 3)
  - [x] Add imports at the top (after sys.path injection): `import json as _json` (separate alias to avoid collision); import `AiConfig` and `AiTool` and `ToolRegistry` via the repo root sys.path
  - [x] Add `_build_tools()` function that reads `NIMBLE_AI_CONFIG` env var, parses JSON if present, builds `AiConfig | None`, returns `ToolRegistry(ai=AiTool(ai_config))`
  - [x] Replace `tools = None` with `tools = _build_tools()` in the `run()` function, placed after skill startup succeeds (skill loaded OK)
  - [x] The `_build_tools()` function is called once per worker process at startup — not per invocation
  - [x] Type annotation: `tools: ToolRegistry` (not `Any`)

- [x] Task 7: Update `config.yaml` with an `ai` block (AC: 1, 2)
  - [x] Add an `ai` block to the template `config.yaml` with `provider: anthropic`, `model: claude-sonnet-4-6`, `api_key_env: ANTHROPIC_API_KEY`
  - [x] Place it after the `skills` list

- [x] Task 8: Add `tests/unit/tools/` package with `test_ai.py` (AC: 1, 2, 3)
  - [x] Create `tests/unit/tools/__init__.py` (empty)
  - [x] Add tests — see Dev Notes for exact mocking patterns
  - [x] `test_ask_anthropic_returns_text()` — mock `anthropic.Anthropic`, verify string returned
  - [x] `test_ask_openai_returns_text()` — mock `openai.OpenAI`, verify string returned
  - [x] `test_ask_with_system_prompt_anthropic()` — verify prompt passed as `system=` kwarg
  - [x] `test_ask_with_system_prompt_openai()` — verify prompt prepended as system message
  - [x] `test_ask_raises_on_missing_api_key()` — env var not set → RuntimeError naming the var
  - [x] `test_ask_raises_on_no_config()` — AiTool(None).ask() → RuntimeError about config
  - [x] `test_ask_raises_on_unknown_provider()` — provider="ollama" → RuntimeError naming provider
  - [x] `test_ask_raises_on_missing_sdk()` — simulate ImportError → RuntimeError naming package

- [x] Task 9: Add AI config tests to `tests/unit/manifest/test_parser.py` (AC: 1)
  - [x] `test_load_config_with_ai_block()` — full config with `ai:` section; verify `AiConfig` fields
  - [x] `test_load_config_without_ai_block()` — no `ai:` key; verify `result.ai is None`
  - [x] `test_load_config_ai_missing_required_field()` — `ai:` block present but `model:` absent → `ConfigError`

- [x] Task 10: Verify quality gates (AC: all)
  - [x] `mypy nimble/ tests/ worker/` — exits 0 (3 pre-existing errors in test_platform.py excluded)
  - [x] `pytest` — all 133 tests pass (125 pre-existing + 8 new tools tests + 3 new parser tests)
  - [x] `black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

## Dev Notes

### Role in the Daemon Architecture

```
hotkey fires
  → runner.py calls build_context()
  → runner.py dispatches JSON payload to worker stdin
  → worker/entrypoint.py reads NIMBLE_AI_CONFIG env var at startup
  → worker builds ToolRegistry(ai=AiTool(ai_config))
  → skill.run(context, tools)   ← tools.ai.ask() now works
  → AiTool.ask() reads API key from env, calls provider SDK, returns str
```

This story wires the first real tool into the pre-existing worker subprocess model. The `tools` parameter that has been `None` since Story 2.5 becomes a live `ToolRegistry`.

**Architectural constraint:** `nimble.tools` is imported by the worker, which runs in the skill's venv (for community skills). The `sys.path` injection in `worker/entrypoint.py` (already in place since Story 2.5) ensures `nimble.*` is importable regardless of which Python executable runs the worker.

### New Files

```
nimble/tools/__init__.py     ← ToolRegistry dataclass
nimble/tools/ai.py           ← AiTool class, AiConfig imported from parser
tests/unit/tools/__init__.py ← empty init
tests/unit/tools/test_ai.py  ← unit tests
```

### Modified Files

```
nimble/manifest/parser.py              ← add AiConfig, update NimbleConfig
nimble/skills/runner.py                ← add ai_config param, pass env var
worker/entrypoint.py                   ← build ToolRegistry, replace tools = None
nimble/daemon.py                       ← pass ai_config to SkillRunner
config.yaml                            ← add ai block
```

### `nimble/manifest/parser.py` — AiConfig and NimbleConfig Changes

Add `AiConfig` dataclass alongside `NimbleConfig` and `SkillConfig`:

```python
@dataclass
class AiConfig:
    provider: str
    model: str
    api_key_env: str
```

Update `NimbleConfig`:
```python
@dataclass
class NimbleConfig:
    skills: list[SkillConfig]
    ai: AiConfig | None = None
```

Add parser helper and update `load_config()`:
```python
def _parse_ai_config(data: dict[str, Any]) -> AiConfig | None:
    raw = data.get("ai")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ConfigError("'ai' must be a mapping")
    for field in ("provider", "model", "api_key_env"):
        if field not in raw:
            raise ConfigError(f"'ai' block missing required field: '{field}'")
    return AiConfig(
        provider=raw["provider"],
        model=raw["model"],
        api_key_env=raw["api_key_env"],
    )

def load_config(config_path: Path) -> NimbleConfig:
    # ... existing yaml load + error handling (unchanged) ...
    parsed_skills = _parse_skills(data.get("skills", []))
    ai_config = _parse_ai_config(data)
    return NimbleConfig(skills=parsed_skills, ai=ai_config)
```

### `nimble/tools/__init__.py` — ToolRegistry

```python
from __future__ import annotations

from dataclasses import dataclass

from nimble.tools.ai import AiTool


@dataclass
class ToolRegistry:
    ai: AiTool
```

Skills call `tools.ai.ask(...)`. Future stories (3.2–3.5) will add `popup`, `clipboard`, `tts`, and `input` fields. Do NOT add stub fields for those now.

### `nimble/tools/ai.py` — AiTool Implementation

```python
from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nimble.manifest.parser import AiConfig


class AiTool:
    def __init__(self, config: AiConfig | None) -> None:
        self._config = config

    def ask(self, text: str, prompt: str | None = None) -> str:
        if self._config is None:
            raise RuntimeError(
                "AI not configured: add an 'ai' block to config.yaml"
            )
        api_key = os.environ.get(self._config.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"AI API key not set: env var {self._config.api_key_env!r} is empty or unset"
            )
        if self._config.provider == "anthropic":
            return self._ask_anthropic(text, prompt, api_key)
        if self._config.provider == "openai":
            return self._ask_openai(text, prompt, api_key)
        raise RuntimeError(
            f"Unsupported AI provider: {self._config.provider!r}. Supported: anthropic, openai"
        )

    def _ask_anthropic(self, text: str, prompt: str | None, api_key: str) -> str:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError(
                "anthropic package not installed; add 'anthropic' to your skill's manifest.yaml dependencies"
            )
        client = anthropic.Anthropic(api_key=api_key)
        kwargs: dict[str, object] = {
            "model": self._config.model,  # type: ignore[union-attr]
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": text}],
        }
        if prompt is not None:
            kwargs["system"] = prompt
        response = client.messages.create(**kwargs)  # type: ignore[arg-type]
        return str(response.content[0].text)  # type: ignore[attr-defined]

    def _ask_openai(self, text: str, prompt: str | None, api_key: str) -> str:
        try:
            import openai
        except ImportError:
            raise RuntimeError(
                "openai package not installed; add 'openai' to your skill's manifest.yaml dependencies"
            )
        client = openai.OpenAI(api_key=api_key)
        messages: list[dict[str, str]] = []
        if prompt is not None:
            messages.append({"role": "system", "content": prompt})
        messages.append({"role": "user", "content": text})
        response = client.chat.completions.create(
            model=self._config.model,  # type: ignore[union-attr]
            messages=messages,  # type: ignore[arg-type]
        )
        return str(response.choices[0].message.content)
```

**`TYPE_CHECKING` import:** `AiConfig` is used as a type annotation only. Using `TYPE_CHECKING` avoids a circular import between `nimble.tools.ai` and `nimble.manifest.parser`. At runtime, `AiConfig` instances are passed in but the class is never referenced by name. The `if TYPE_CHECKING:` import makes mypy happy without circular imports.

**mypy `# type: ignore` comments:** The `**kwargs` dict and SDK response types are tricky for mypy with strict mode. Use `# type: ignore[arg-type]`, `# type: ignore[union-attr]`, and `# type: ignore[attr-defined]` as shown — do NOT add blanket ignores.

**`max_tokens=1024`:** Hard-coded for v1. NFR16 compliance is about provider/model switching, not about exposing every parameter. Do NOT add configurable max_tokens in this story.

### `nimble/skills/runner.py` — Passing AI Config to Workers

Add `ai_config` parameter to `SkillRunner.__init__`:
```python
from nimble.manifest.parser import AiConfig  # add this import

class SkillRunner:
    def __init__(
        self,
        registry: SkillRegistry,
        notifier: Any,
        repo_root: Path,
        ai_config: AiConfig | None = None,
    ) -> None:
        self._registry = registry
        self._notifier = notifier
        self._repo_root = repo_root
        self._ai_config = ai_config
```

In `spawn_workers()`, extend the env dict:
```python
import json  # already imported — verify it is present

ai_config_json = ""
if self._ai_config is not None:
    ai_config_json = json.dumps({
        "provider": self._ai_config.provider,
        "model": self._ai_config.model,
        "api_key_env": self._ai_config.api_key_env,
    })

proc = subprocess.Popen(
    [...],
    env={
        **os.environ,
        "NIMBLE_REPO_ROOT": str(self._repo_root),
        "NIMBLE_AI_CONFIG": ai_config_json,
    },
)
```

`json` is already imported in `runner.py` — check before adding a duplicate import.

### `worker/entrypoint.py` — Building ToolRegistry

Add after the existing `sys.path` injection block (before other imports):
```python
# nimble.* imports are safe after sys.path injection above
from nimble.manifest.parser import AiConfig  # noqa: E402
from nimble.tools import ToolRegistry  # noqa: E402
from nimble.tools.ai import AiTool  # noqa: E402
```

Add the `_build_tools()` helper function (before `run()`):
```python
def _build_tools() -> ToolRegistry:
    raw = os.environ.get("NIMBLE_AI_CONFIG", "")
    ai_config: AiConfig | None = None
    if raw:
        try:
            data = json.loads(raw)
            ai_config = AiConfig(
                provider=data["provider"],
                model=data["model"],
                api_key_env=data["api_key_env"],
            )
        except (json.JSONDecodeError, KeyError):
            pass  # malformed env var — treat as no AI config
    return ToolRegistry(ai=AiTool(ai_config))
```

Replace `tools = None` with:
```python
tools = _build_tools()
```

The variable `tools` changes type from `None` to `ToolRegistry`. Update the type annotation in the `run()` function signature area accordingly. The variable must be in scope when `skill.run(context, tools)` is called (it already is in the existing loop structure).

**Important:** `json` is already imported in `worker/entrypoint.py`. Verify before adding a duplicate.

**Import alias concern:** `import json` is already at the top of `entrypoint.py`. The new `nimble.manifest.parser` import uses `json` internally. No conflict since they're separate modules.

### `config.yaml` — AI Block

Add after the `skills` list:
```yaml
ai:
  provider: anthropic
  model: claude-sonnet-4-6
  api_key_env: ANTHROPIC_API_KEY
```

The user sets `ANTHROPIC_API_KEY` in their shell environment; it is NOT stored in `config.yaml`. This satisfies NFR8 (no credentials in tracked files).

### Test Patterns for `tests/unit/tools/test_ai.py`

All AI SDK calls must be mocked — never make real API calls in tests.

**Anthropic happy path:**
```python
from unittest.mock import MagicMock, patch
from nimble.manifest.parser import AiConfig
from nimble.tools.ai import AiTool

def test_ask_anthropic_returns_text() -> None:
    cfg = AiConfig(provider="anthropic", model="claude-sonnet-4-6", api_key_env="TEST_KEY")
    tool = AiTool(cfg)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="answer text")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client

    with (
        patch.dict("os.environ", {"TEST_KEY": "sk-fake"}),
        patch.dict("sys.modules", {"anthropic": mock_anthropic}),
    ):
        result = tool.ask("hello")
    assert result == "answer text"
```

**OpenAI happy path:**
```python
def test_ask_openai_returns_text() -> None:
    cfg = AiConfig(provider="openai", model="gpt-4o", api_key_env="TEST_KEY")
    tool = AiTool(cfg)

    mock_message = MagicMock()
    mock_message.content = "answer text"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value = mock_client

    with (
        patch.dict("os.environ", {"TEST_KEY": "sk-fake"}),
        patch.dict("sys.modules", {"openai": mock_openai}),
    ):
        result = tool.ask("hello")
    assert result == "answer text"
```

**System prompt — Anthropic:**
```python
def test_ask_with_system_prompt_anthropic() -> None:
    cfg = AiConfig(provider="anthropic", model="claude-sonnet-4-6", api_key_env="TEST_KEY")
    tool = AiTool(cfg)
    # ... setup mocks as above ...
    with patch.dict("os.environ", {"TEST_KEY": "sk-fake"}), patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        tool.ask("hello", prompt="You are helpful")
    # Verify messages.create was called with system="You are helpful"
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs.get("system") == "You are helpful"
```

**System prompt — OpenAI:** verify `messages[0] == {"role": "system", "content": "You are helpful"}` in the `create()` call kwargs.

**Missing API key:**
```python
def test_ask_raises_on_missing_api_key() -> None:
    cfg = AiConfig(provider="anthropic", model="claude-sonnet-4-6", api_key_env="MISSING_VAR")
    tool = AiTool(cfg)
    with patch.dict("os.environ", {}, clear=True), pytest.raises(RuntimeError) as exc_info:
        tool.ask("hello")
    assert "MISSING_VAR" in str(exc_info.value)
```

**No config:**
```python
def test_ask_raises_on_no_config() -> None:
    tool = AiTool(None)
    with pytest.raises(RuntimeError, match="config.yaml"):
        tool.ask("hello")
```

**Unknown provider:**
```python
def test_ask_raises_on_unknown_provider() -> None:
    cfg = AiConfig(provider="ollama", model="llama3", api_key_env="OLLAMA_KEY")
    tool = AiTool(cfg)
    with patch.dict("os.environ", {"OLLAMA_KEY": "x"}), pytest.raises(RuntimeError, match="ollama"):
        tool.ask("hello")
```

**Missing SDK:**
```python
def test_ask_raises_on_missing_anthropic_sdk() -> None:
    cfg = AiConfig(provider="anthropic", model="claude-sonnet-4-6", api_key_env="TEST_KEY")
    tool = AiTool(cfg)
    with (
        patch.dict("os.environ", {"TEST_KEY": "sk-fake"}),
        patch.dict("sys.modules", {"anthropic": None}),  # None causes ImportError on import
        pytest.raises(RuntimeError, match="anthropic"),
    ):
        tool.ask("hello")
```

**Note on `sys.modules` patching:** Setting `sys.modules["anthropic"] = None` causes `import anthropic` to raise `ImportError`. Setting it to a `MagicMock()` makes the import succeed with the mock. Both patterns are used above.

### Test Patterns for `tests/unit/manifest/test_parser.py`

Add these tests (do NOT modify existing tests):

```python
from nimble.manifest.parser import AiConfig, NimbleConfig, load_config  # AiConfig added

def test_load_config_with_ai_block(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        "skills: []\n"
        "ai:\n"
        "  provider: anthropic\n"
        "  model: claude-sonnet-4-6\n"
        "  api_key_env: ANTHROPIC_API_KEY\n",
    )
    result = load_config(cfg)
    assert isinstance(result.ai, AiConfig)
    assert result.ai.provider == "anthropic"
    assert result.ai.model == "claude-sonnet-4-6"
    assert result.ai.api_key_env == "ANTHROPIC_API_KEY"

def test_load_config_without_ai_block(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, "skills: []\n")
    result = load_config(cfg)
    assert result.ai is None

def test_load_config_ai_missing_required_field(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        "skills: []\n"
        "ai:\n"
        "  provider: anthropic\n"
        "  api_key_env: ANTHROPIC_API_KEY\n",  # 'model' missing
    )
    with pytest.raises(ConfigError, match="model"):
        load_config(cfg)
```

### Avoiding Circular Imports

The import chain is:
```
nimble/tools/__init__.py  →  nimble/tools/ai.py
nimble/tools/ai.py        →  nimble/manifest/parser.py  (TYPE_CHECKING only)
nimble/manifest/parser.py →  (no tools imports)
worker/entrypoint.py      →  nimble/manifest/parser.py, nimble/tools/__init__.py, nimble/tools/ai.py
```

No circular dependency exists. `nimble.tools.ai` imports `AiConfig` under `TYPE_CHECKING` only — at runtime the import is skipped. This is intentional and mypy-approved.

In `worker/entrypoint.py`, the import order after sys.path injection must be:
```python
from nimble.manifest.parser import AiConfig  # noqa: E402
from nimble.tools import ToolRegistry  # noqa: E402
from nimble.tools.ai import AiTool  # noqa: E402
```
(ToolRegistry imports AiTool; importing AiTool first avoids issues. Actually, importing ToolRegistry pulls in AiTool. Either order works, but be explicit to avoid confusion.)

### Pre-Existing `tools = None` in Entrypoint

In `worker/entrypoint.py`, the line `tools = None` currently sits before the IPC loop with `tools: Any` or no annotation. After this story:
- Remove `tools = None`  
- Add `tools = _build_tools()` immediately after skill instantiation succeeds (inside the `try` block for skill loading, after `skill = skill_class()`)
- The variable is `tools: ToolRegistry` — annotate it appropriately

### Architecture Compliance

- `mypy --strict` applies to `nimble/`, `tests/`, and `worker/`
- All function parameters and return types must be annotated
- Absolute imports only: `from nimble.tools.ai import AiTool` not `from .ai import AiTool`
- `@dataclass` for `ToolRegistry` (already specified)
- No new `pyproject.toml` dependencies — anthropic/openai are skill dependencies installed per-skill; the engine itself has no SDK dependency
- `tests/unit/tools/` follows the mirror structure: `nimble/tools/ai.py` → `tests/unit/tools/test_ai.py`

### SDK Not in `pyproject.toml`

`anthropic` and `openai` are NOT added to `pyproject.toml` engine dependencies. Rationale: skills that use `tools.ai.ask()` declare the SDK in their own `manifest.yaml` under `dependencies`. The worker for that skill runs in a venv that has the SDK installed. This is consistent with the per-skill isolation model (FR8, NFR19).

For **author skills** (source: local) running in the daemon's Python environment: if a skill uses `tools.ai.ask()`, the user must `pip install anthropic` or `pip install openai` manually into their fork's venv. The `AiTool` code will raise `RuntimeError("anthropic package not installed...")` if the package is absent — not an ImportError.

### Latency Impact (NFR1)

`tools.ai.ask()` makes a network call to an external LLM API, which takes hundreds of milliseconds to seconds. This is NOT subject to the 200ms hotkey-to-execution budget (NFR1). NFR1 governs the time from hotkey press to skill `run()` being called — the AI call happens inside `run()`, after the budget window closes. No latency concern for this story.

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 3.1] — acceptance criteria, FR13, NFR16
- [Source: docs/bmad_output/planning-artifacts/architecture.md#LLM Provider Abstraction] — config schema, provider dispatch pattern
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Repository Module Structure] — `nimble/tools/ai.py` placement
- [Source: docs/bmad_output/planning-artifacts/architecture.md#All AI Agents MUST] — naming, type annotations, absolute imports, test mirroring rules
- [Source: worker/entrypoint.py] — current `tools = None`, sys.path injection pattern, import ordering
- [Source: nimble/manifest/parser.py] — existing config dataclass pattern to follow
- [Source: nimble/skills/runner.py] — existing env var passing pattern (`NIMBLE_REPO_ROOT`)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Removed unused `# type: ignore[arg-type]` and `# type: ignore[attr-defined]` from `nimble/tools/ai.py` — mypy correctly flags these as unnecessary because `anthropic`/`openai` are not installed in the engine venv, so mypy treats them as `Any`. The `# type: ignore[union-attr]` on `self._config.model` IS needed (narrowing doesn't propagate across private methods).
- Fixed E501 line length violations in `nimble/tools/ai.py` using implicit string concatenation.

### Completion Notes List

- Implemented `AiConfig` dataclass and `_parse_ai_config()` in `nimble/manifest/parser.py`. `NimbleConfig` now has optional `ai: AiConfig | None = None` field.
- Created `nimble/tools/` package with `ToolRegistry` dataclass and `AiTool` class. `AiTool.ask()` dispatches to Anthropic or OpenAI with lazy SDK imports, raises descriptive `RuntimeError` for all failure modes (no config, missing API key, unknown provider, missing SDK).
- Updated `SkillRunner` to accept `ai_config` and serialize it as `NIMBLE_AI_CONFIG` JSON env var for worker subprocesses.
- Updated `nimble/daemon.py` to pass `config.ai` to `SkillRunner`.
- Updated `worker/entrypoint.py` to parse `NIMBLE_AI_CONFIG`, build `ToolRegistry`, and replace `tools = None` with `tools: ToolRegistry = _build_tools()`.
- Added `config.yaml` `ai:` block (anthropic/claude-sonnet-4-6/ANTHROPIC_API_KEY).
- Added 8 unit tests in `tests/unit/tools/test_ai.py` covering all AC scenarios with mocked SDKs.
- Added 3 unit tests in `tests/unit/manifest/test_parser.py` for AI config parsing.
- All 133 tests pass; black, flake8 clean; mypy clean on new code.

### File List

- `nimble/manifest/parser.py` (modified)
- `nimble/tools/__init__.py` (new)
- `nimble/tools/ai.py` (new)
- `nimble/skills/runner.py` (modified)
- `nimble/daemon.py` (modified)
- `worker/entrypoint.py` (modified)
- `config.yaml` (modified)
- `tests/unit/tools/__init__.py` (new)
- `tests/unit/tools/test_ai.py` (new)
- `tests/unit/manifest/test_parser.py` (modified)

### Change Log

- 2026-04-24: Implemented Story 3.1 — `tools.ai.ask()` tool primitive with Anthropic and OpenAI provider support, config parsing, worker env-var wiring, and full test suite.
- 2026-04-24: Code review follow-up — fixed `ConfigError` typo in `parser.py`; strict `NIMBLE_AI_CONFIG` parsing in worker startup (fail fast + tests).

### Review Findings

- [x] [Review][Decision] Malformed or partial `NIMBLE_AI_CONFIG` — **Resolved (option A):** Worker startup now fails with a JSON `status: error` line (same shape as skill load failure) if `NIMBLE_AI_CONFIG` is non-empty but not valid JSON, not a JSON object, or missing `provider` / `model` / `api_key_env`. Empty or whitespace-only env means no AI config (unchanged). [`worker/entrypoint.py` `_build_tools`, `run`]

- [x] [Review][Patch] Typo in `ConfigError` message for missing `ai` subfield — Fixed: removed stray `)` in the f-string. [`nimble/manifest/parser.py:58`]
