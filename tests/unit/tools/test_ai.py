from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nimble.manifest.parser import AiConfig
from nimble.tools.ai import AiTool


def _make_anthropic_mock(response_text: str) -> MagicMock:
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=response_text)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    return mock_anthropic


def _make_openai_mock(response_text: str) -> MagicMock:
    mock_message = MagicMock()
    mock_message.content = response_text
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value = mock_client
    return mock_openai


def test_ask_anthropic_returns_text() -> None:
    cfg = AiConfig(
        provider="anthropic", model="claude-sonnet-4-6", api_key_env="TEST_KEY"
    )
    tool = AiTool(cfg)
    mock_anthropic = _make_anthropic_mock("answer text")

    with (
        patch.dict("os.environ", {"TEST_KEY": "sk-fake"}),
        patch.dict("sys.modules", {"anthropic": mock_anthropic}),
    ):
        result = tool.ask("hello")
    assert result == "answer text"


def test_ask_openai_returns_text() -> None:
    cfg = AiConfig(provider="openai", model="gpt-4o", api_key_env="TEST_KEY")
    tool = AiTool(cfg)
    mock_openai = _make_openai_mock("answer text")

    with (
        patch.dict("os.environ", {"TEST_KEY": "sk-fake"}),
        patch.dict("sys.modules", {"openai": mock_openai}),
    ):
        result = tool.ask("hello")
    assert result == "answer text"


def test_ask_with_system_prompt_anthropic() -> None:
    cfg = AiConfig(
        provider="anthropic", model="claude-sonnet-4-6", api_key_env="TEST_KEY"
    )
    tool = AiTool(cfg)
    mock_anthropic = _make_anthropic_mock("ok")
    mock_client = mock_anthropic.Anthropic.return_value

    with (
        patch.dict("os.environ", {"TEST_KEY": "sk-fake"}),
        patch.dict("sys.modules", {"anthropic": mock_anthropic}),
    ):
        tool.ask("hello", system_prompt="You are helpful")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs.get("system") == "You are helpful"


def test_ask_with_system_prompt_openai() -> None:
    cfg = AiConfig(provider="openai", model="gpt-4o", api_key_env="TEST_KEY")
    tool = AiTool(cfg)
    mock_openai = _make_openai_mock("ok")
    mock_client = mock_openai.OpenAI.return_value

    with (
        patch.dict("os.environ", {"TEST_KEY": "sk-fake"}),
        patch.dict("sys.modules", {"openai": mock_openai}),
    ):
        tool.ask("hello", system_prompt="You are helpful")

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert messages[0] == {"role": "system", "content": "You are helpful"}


def test_ask_raises_on_missing_api_key() -> None:
    cfg = AiConfig(
        provider="anthropic", model="claude-sonnet-4-6", api_key_env="MISSING_VAR"
    )
    tool = AiTool(cfg)
    with (
        patch.dict("os.environ", {}, clear=True),
        pytest.raises(RuntimeError) as exc_info,
    ):
        tool.ask("hello")
    assert "MISSING_VAR" in str(exc_info.value)


def test_ask_raises_on_no_config() -> None:
    tool = AiTool(None)
    with pytest.raises(RuntimeError, match="config.yaml"):
        tool.ask("hello")


def test_ask_raises_on_unknown_provider() -> None:
    cfg = AiConfig(provider="ollama", model="llama3", api_key_env="OLLAMA_KEY")
    tool = AiTool(cfg)
    with (
        patch.dict("os.environ", {"OLLAMA_KEY": "x"}),
        pytest.raises(RuntimeError, match="ollama"),
    ):
        tool.ask("hello")


def test_ask_raises_on_missing_anthropic_sdk() -> None:
    cfg = AiConfig(
        provider="anthropic", model="claude-sonnet-4-6", api_key_env="TEST_KEY"
    )
    tool = AiTool(cfg)
    with (
        patch.dict("os.environ", {"TEST_KEY": "sk-fake"}),
        patch.dict("sys.modules", {"anthropic": None}),
        pytest.raises(RuntimeError, match="anthropic"),
    ):
        tool.ask("hello")
