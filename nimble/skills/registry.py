from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

SkillSource = Literal["local", "community"]
SkillStatus = Literal["loaded", "disabled", "failed"]


@dataclass
class SkillConfig:
    name: str
    source: SkillSource
    binding: str
    path: str
    class_name: str


@dataclass
class SkillWorker:
    config: SkillConfig
    process: subprocess.Popen[bytes]
    status: SkillStatus
    python_executable: str


class SkillRegistry:
    def __init__(self) -> None:
        self._workers: dict[str, SkillWorker] = {}

    def register(self, worker: SkillWorker) -> None:
        self._workers[worker.config.name] = worker

    def get(self, name: str) -> SkillWorker | None:
        return self._workers.get(name)

    def all(self) -> list[SkillWorker]:
        return list(self._workers.values())

    def disable(self, name: str) -> None:
        worker = self._workers.get(name)
        if worker is not None:
            worker.status = "failed"
            logger.error(
                "Worker for skill %s died (exit code %s). Skill disabled.",
                name,
                worker.process.poll(),
            )
