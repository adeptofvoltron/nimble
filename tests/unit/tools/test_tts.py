from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from nimble.tools.tts import TtsTool


def test_speak_calls_plyer_tts_speak() -> None:
    tool = TtsTool()
    mock_tts = MagicMock()
    with patch.dict("sys.modules", {"plyer": MagicMock(tts=mock_tts)}):
        tool.speak("hello")
    mock_tts.speak.assert_called_once_with("hello")


def test_speak_raises_runtime_error_when_tts_fails() -> None:
    tool = TtsTool()
    mock_tts = MagicMock()
    mock_tts.speak.side_effect = RuntimeError("espeak not found")
    with patch.dict("sys.modules", {"plyer": MagicMock(tts=mock_tts)}):
        with pytest.raises(RuntimeError, match="TTS is not available"):
            tool.speak("hello")


def test_speak_raises_runtime_error_on_import_failure() -> None:
    tool = TtsTool()
    with patch.dict("sys.modules", {"plyer": None}):
        with pytest.raises(RuntimeError):
            tool.speak("hello")


def test_speak_error_message_is_descriptive() -> None:
    tool = TtsTool()
    mock_tts = MagicMock()
    mock_tts.speak.side_effect = Exception("espeak not found")
    with patch.dict("sys.modules", {"plyer": MagicMock(tts=mock_tts)}):
        with pytest.raises(RuntimeError) as exc_info:
            tool.speak("hello")
    assert "TTS is not available:" in str(exc_info.value)


def test_speak_raises_not_returns_silently() -> None:
    tool = TtsTool()
    mock_tts = MagicMock()
    mock_tts.speak.side_effect = OSError("no tts engine")
    with patch.dict("sys.modules", {"plyer": MagicMock(tts=mock_tts)}):
        with pytest.raises(RuntimeError):
            tool.speak("should fail loudly")
