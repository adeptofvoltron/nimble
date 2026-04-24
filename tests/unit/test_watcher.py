from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileMovedEvent

from nimble.watcher import ConfigWatcher


def test_reload_fn_called_on_config_modification(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.touch()
    reload_fn = MagicMock()
    watcher = ConfigWatcher(config_path, reload_fn)
    event = FileModifiedEvent(str(config_path))
    watcher._handler.on_modified(event)
    reload_fn.assert_called_once_with(config_path)


def test_reload_fn_not_called_for_other_files(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.touch()
    other_path = tmp_path / "other.yaml"
    other_path.touch()
    reload_fn = MagicMock()
    watcher = ConfigWatcher(config_path, reload_fn)
    event = FileModifiedEvent(str(other_path))
    watcher._handler.on_modified(event)
    reload_fn.assert_not_called()


def test_start_stop_does_not_crash(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.touch()
    watcher = ConfigWatcher(config_path, lambda p: None)
    watcher.start()
    watcher.stop()


def test_reload_fn_called_on_config_create(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.touch()
    reload_fn = MagicMock()
    watcher = ConfigWatcher(config_path, reload_fn)
    event = FileCreatedEvent(str(config_path))
    watcher._handler.on_created(event)
    reload_fn.assert_called_once_with(config_path)


def test_reload_fn_called_on_config_move(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.touch()
    reload_fn = MagicMock()
    watcher = ConfigWatcher(config_path, reload_fn)
    event = FileMovedEvent(str(tmp_path / "tmp.yaml"), str(config_path))
    watcher._handler.on_moved(event)
    reload_fn.assert_called_once_with(config_path)
