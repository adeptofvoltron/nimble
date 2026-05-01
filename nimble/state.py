from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path

NIMBLE_DIR: Path = Path.home() / ".nimble"
PID_FILE: Path = NIMBLE_DIR / "nimble.pid"
STATE_FILE: Path = NIMBLE_DIR / "state.json"
_STATE_WRITE_LOCK = threading.Lock()


@dataclass
class SkillState:
    name: str
    source: str
    binding: str
    status: str
    worker_pid: int | None


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


def write_state(
    pid: int,
    started_at: str,
    daemon_version: str,
    skills: list[SkillState],
) -> None:
    NIMBLE_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "pid": pid,
        "started_at": started_at,
        "daemon_version": daemon_version,
        "skills": [
            {
                "name": s.name,
                "source": s.source,
                "binding": s.binding,
                "status": s.status,
                "worker_pid": s.worker_pid,
            }
            for s in skills
        ],
    }
    with _STATE_WRITE_LOCK:
        tmp = STATE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data))
        tmp.rename(STATE_FILE)


def remove_state() -> None:
    try:
        STATE_FILE.unlink()
    except FileNotFoundError:
        pass


def is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
