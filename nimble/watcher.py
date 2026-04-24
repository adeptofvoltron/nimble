from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from watchdog.events import (
    DirCreatedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    FileCreatedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class _ConfigEventHandler(FileSystemEventHandler):
    def __init__(self, config_path: Path, reload_fn: Callable[[Path], None]) -> None:
        super().__init__()
        self._config_path = config_path.resolve()
        self._reload_fn = reload_fn

    def _normalize_path(self, raw_path: str | bytes) -> Path:
        return Path(os.fsdecode(raw_path)).resolve()

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent) -> None:
        if self._normalize_path(event.src_path) == self._config_path:
            self._reload_fn(self._config_path)

    def on_created(self, event: DirCreatedEvent | FileCreatedEvent) -> None:
        if self._normalize_path(event.src_path) == self._config_path:
            self._reload_fn(self._config_path)

    def on_moved(self, event: DirMovedEvent | FileMovedEvent) -> None:
        if self._normalize_path(event.dest_path) == self._config_path:
            self._reload_fn(self._config_path)


class ConfigWatcher:
    def __init__(self, config_path: Path, reload_fn: Callable[[Path], None]) -> None:
        self._config_path = config_path
        self._handler = _ConfigEventHandler(config_path, reload_fn)
        self._observer: Any = Observer()

    def start(self) -> None:
        self._observer.schedule(
            self._handler, str(self._config_path.parent), recursive=False
        )
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
