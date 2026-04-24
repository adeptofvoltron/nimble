from __future__ import annotations

import os
from pathlib import Path

NIMBLE_DIR: Path = Path.home() / ".nimble"
PID_FILE: Path = NIMBLE_DIR / "nimble.pid"


def write_pid(pid: int) -> None:
    NIMBLE_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(pid))


def read_pid() -> int | None:
    try:
        return int(PID_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def remove_pid() -> None:
    try:
        PID_FILE.unlink()
    except FileNotFoundError:
        pass


def is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
