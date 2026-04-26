import logging
import logging.handlers
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nimble.logging_setup import configure_logging


@pytest.fixture(autouse=True)
def _restore_root_logger() -> Iterator[None]:
    root = logging.getLogger()
    original_level = root.level
    original_handlers = root.handlers[:]
    yield
    root.setLevel(original_level)
    for h in root.handlers[:]:
        if h not in original_handlers:
            root.removeHandler(h)


def test_rotating_handler_configured(tmp_path: Path) -> None:
    log_path = tmp_path / "nimble.log"
    mock_handler = MagicMock()
    with patch(
        "logging.handlers.RotatingFileHandler", return_value=mock_handler
    ) as mock_cls:
        configure_logging(log_path, debug=False)
    mock_cls.assert_called_once_with(log_path, maxBytes=5 * 1024 * 1024, backupCount=3)


def test_debug_flag_sets_debug_level(tmp_path: Path) -> None:
    log_path = tmp_path / "nimble.log"
    with patch("logging.handlers.RotatingFileHandler", return_value=MagicMock()):
        configure_logging(log_path, debug=True)
    assert logging.getLogger().level == logging.DEBUG


def test_default_level_is_info(tmp_path: Path) -> None:
    log_path = tmp_path / "nimble.log"
    with patch("logging.handlers.RotatingFileHandler", return_value=MagicMock()):
        configure_logging(log_path, debug=False)
    assert logging.getLogger().level == logging.INFO
