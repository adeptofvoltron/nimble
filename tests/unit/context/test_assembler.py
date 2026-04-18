import json
from unittest.mock import MagicMock, patch

from nimble.context.assembler import (
    _get_active_app,
    _get_clipboard,
    _get_mouse_position,
    _get_selection,
    build_context,
)


def _mock_run(returncode: int, stdout: str) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


def test_build_context_returns_required_keys() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(0, "text")
    ):
        with patch(
            "nimble.context.assembler._get_mouse_position", return_value=[100, 200]
        ):
            ctx = build_context()
    assert set(ctx.keys()) == {"selection", "clipboard", "active_app", "mouse_position"}


def test_build_context_correct_types() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(0, "hello")
    ):
        with patch(
            "nimble.context.assembler._get_mouse_position", return_value=[10, 20]
        ):
            ctx = build_context()
    assert isinstance(ctx["selection"], str)
    assert isinstance(ctx["clipboard"], str)
    assert isinstance(ctx["active_app"], str)
    assert isinstance(ctx["mouse_position"], list)
    assert len(ctx["mouse_position"]) == 2
    assert all(isinstance(v, int) for v in ctx["mouse_position"])


def test_selection_empty_on_subprocess_failure() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(1, "")
    ):
        assert _get_selection() == ""


def test_selection_empty_on_success_with_empty_stdout() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(0, "")
    ):
        assert _get_selection() == ""


def test_clipboard_empty_on_subprocess_failure() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(1, "")
    ):
        assert _get_clipboard() == ""


def test_active_app_empty_on_subprocess_failure() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(1, "")
    ):
        assert _get_active_app() == ""


def test_mouse_position_happy_path() -> None:
    mock_mouse = MagicMock()
    mock_mouse.Controller.return_value.position = (1920, 1080)
    fake_modules = {"pynput": MagicMock(mouse=mock_mouse), "pynput.mouse": mock_mouse}
    with patch.dict("sys.modules", fake_modules):
        result = _get_mouse_position()
    assert result == [1920, 1080]
    assert all(isinstance(v, int) for v in result)


def test_mouse_position_fallback_on_exception() -> None:
    mock_mouse = MagicMock()
    mock_mouse.Controller.side_effect = RuntimeError("no display server")
    fake_modules = {"pynput": MagicMock(mouse=mock_mouse), "pynput.mouse": mock_mouse}
    with patch.dict("sys.modules", fake_modules):
        result = _get_mouse_position()
    assert result == [0, 0]


def test_build_context_json_round_trip() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(0, "selected")
    ):
        with patch(
            "nimble.context.assembler._get_mouse_position", return_value=[800, 600]
        ):
            ctx = build_context()
    deserialized = json.loads(json.dumps(ctx))
    assert deserialized == ctx
    assert deserialized["mouse_position"] == [800, 600]
    assert isinstance(deserialized["mouse_position"][0], int)
