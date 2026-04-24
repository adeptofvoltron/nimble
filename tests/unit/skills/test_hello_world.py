from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any
from unittest.mock import patch

_REPO_ROOT = Path(__file__).parents[3]


def _load_skill() -> Any:
    spec = importlib.util.spec_from_file_location(
        "hello_world_skill",
        _REPO_ROOT / "skills" / "hello_world" / "skill.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.HelloWorldSkill


def test_hello_world_run_fires_notification() -> None:
    skill = _load_skill()()
    with patch("plyer.notification.notify") as mock_notify:
        skill.run(object(), None)
    mock_notify.assert_called_once_with(
        title="Nimble",
        message="Hello from Nimble! The daemon is working.",
        app_name="Nimble",
    )


def test_hello_world_run_swallows_plyer_exception() -> None:
    skill = _load_skill()()
    with patch("plyer.notification.notify", side_effect=Exception("plyer broken")):
        skill.run(object(), None)
