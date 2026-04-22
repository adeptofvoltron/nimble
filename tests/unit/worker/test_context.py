import pytest

from worker.context import Context


def test_from_dict_valid_payload() -> None:
    data = {
        "selection": "hello",
        "clipboard": "world",
        "active_app": "Terminal",
        "mouse_position": [100, 200],
    }
    ctx = Context.from_dict(data)
    assert ctx.selection == "hello"
    assert ctx.clipboard == "world"
    assert ctx.active_app == "Terminal"
    assert ctx.mouse_position == [100, 200]


def test_from_dict_mouse_position_preserved() -> None:
    data = {
        "selection": "",
        "clipboard": "",
        "active_app": "",
        "mouse_position": [1920, 1080],
    }
    ctx = Context.from_dict(data)
    assert ctx.mouse_position == [1920, 1080]


def test_access_selection_field() -> None:
    ctx = Context(selection="text", clipboard="", active_app="", mouse_position=[0, 0])
    assert ctx.selection == "text"


def test_access_deprecated_selected_text_raises() -> None:
    ctx = Context(selection="text", clipboard="", active_app="", mouse_position=[0, 0])
    with pytest.raises(AttributeError, match="selected_text"):
        _ = getattr(ctx, "selected_text")


def test_access_unknown_field_raises() -> None:
    ctx = Context(selection="text", clipboard="", active_app="", mouse_position=[0, 0])
    with pytest.raises(AttributeError, match="unknown_field"):
        _ = getattr(ctx, "unknown_field")


def test_from_dict_missing_field_raises() -> None:
    data = {"selection": "text", "clipboard": "cb", "active_app": "app"}
    with pytest.raises(KeyError):
        Context.from_dict(data)
