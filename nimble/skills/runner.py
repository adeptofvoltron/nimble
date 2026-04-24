from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from nimble.manifest.parser import AiConfig
from nimble.platform import is_windows
from nimble.skills.registry import SkillConfig, SkillRegistry, SkillWorker

logger = logging.getLogger(__name__)


@dataclass
class SkillError:
    type: str
    message: str
    skill_file: str
    line: int


@dataclass
class DispatchResult:
    invocation_id: str
    status: Literal["ok", "error"]
    error: SkillError | None = field(default=None)


def _get_python_executable(config: SkillConfig) -> str:
    if config.source == "local":
        return sys.executable
    base = Path.home() / ".nimble" / "skills" / config.name / ".venv"
    if is_windows():
        return str(base / "Scripts" / "python.exe")
    return str(base / "bin" / "python")


class SkillRunner:
    def __init__(
        self,
        registry: SkillRegistry,
        notifier: Any,
        repo_root: Path,
        ai_config: AiConfig | None = None,
    ) -> None:
        self._registry = registry
        self._notifier = notifier
        self._repo_root = repo_root
        self._ai_config = ai_config

    def spawn_workers(self, configs: list[SkillConfig]) -> None:
        spawned_workers: list[SkillWorker] = []
        try:
            for config in configs:
                python_executable = _get_python_executable(config)
                ai_config_json = ""
                if self._ai_config is not None:
                    ai_config_json = json.dumps(
                        {
                            "provider": self._ai_config.provider,
                            "model": self._ai_config.model,
                            "api_key_env": self._ai_config.api_key_env,
                        }
                    )
                proc = subprocess.Popen(
                    [
                        python_executable,
                        str(self._repo_root / "worker" / "entrypoint.py"),
                        config.path,
                        config.class_name,
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={
                        **os.environ,
                        "NIMBLE_REPO_ROOT": str(self._repo_root),
                        "NIMBLE_AI_CONFIG": ai_config_json,
                    },
                )
                worker = SkillWorker(
                    config=config,
                    process=proc,
                    status="loaded",
                    python_executable=python_executable,
                )
                # Catch workers that crash immediately during startup.
                if proc.poll() is not None:
                    raise RuntimeError(
                        f"Worker for skill {config.name!r} exited during startup "
                        f"(exit code {proc.poll()!r})"
                    )
                self._registry.register(worker)
                spawned_workers.append(worker)
                logger.info(
                    "Skill %s loaded (source=%s, binding=%s)",
                    config.name,
                    config.source,
                    config.binding,
                )
        except Exception:
            self._shutdown_workers(spawned_workers)
            raise

    def dispatch(self, skill_name: str, context: dict[str, Any]) -> DispatchResult:
        worker = self._registry.get(skill_name)
        if worker is None:
            raise RuntimeError(f"No worker registered for skill {skill_name!r}")

        if worker.process.poll() is not None:
            self._disable_dead_worker(worker)
            raise RuntimeError(f"Worker for skill {skill_name!r} is not running")

        invocation_id = str(uuid.uuid4())
        payload = {"invocation_id": invocation_id, "context": context}
        payload_bytes = (json.dumps(payload) + "\n").encode("utf-8")
        start_time = time.perf_counter()

        try:
            worker.process.stdin.write(payload_bytes)  # type: ignore[union-attr]
            worker.process.stdin.flush()  # type: ignore[union-attr]
        except (BrokenPipeError, OSError) as exc:
            self._disable_dead_worker(worker)
            raise RuntimeError(
                f"Worker for {skill_name!r} died during dispatch write"
            ) from exc

        line = worker.process.stdout.readline()  # type: ignore[union-attr]
        if not line:
            self._disable_dead_worker(worker)
            raise RuntimeError(f"Worker for {skill_name!r} died during dispatch")

        try:
            result = json.loads(line.decode("utf-8"))
        except Exception as exc:
            return DispatchResult(
                invocation_id=invocation_id,
                status="error",
                error=SkillError(
                    type=type(exc).__name__,
                    message=str(exc),
                    skill_file="",
                    line=0,
                ),
            )

        error: SkillError | None = None
        if result.get("error") is not None:
            err_data = result["error"]
            if not isinstance(err_data, dict):
                return DispatchResult(
                    invocation_id=invocation_id,
                    status="error",
                    error=SkillError(
                        type="ProtocolError",
                        message="Worker returned malformed error payload",
                        skill_file="",
                        line=0,
                    ),
                )
            error = SkillError(
                type=err_data.get("type", ""),
                message=err_data.get("message", ""),
                skill_file=err_data.get("skill_file", ""),
                line=err_data.get("line", 0),
            )

        status = result.get("status", "error")
        if status not in {"ok", "error"}:
            return DispatchResult(
                invocation_id=invocation_id,
                status="error",
                error=SkillError(
                    type="ProtocolError",
                    message=f"Worker returned invalid status {status!r}",
                    skill_file="",
                    line=0,
                ),
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.debug("Skill %s dispatch completed in %.1fms", skill_name, elapsed_ms)

        return DispatchResult(
            invocation_id=result.get("invocation_id", invocation_id),
            status=status,
            error=error,
        )

    def check_for_dead_workers(self) -> None:
        for worker in self._registry.all():
            if worker.status == "failed":
                continue
            if worker.process.poll() is not None:
                self._disable_dead_worker(worker)

    def _disable_dead_worker(self, worker: SkillWorker) -> None:
        self._registry.disable(worker.config.name)
        try:
            self._notifier.send(
                title=f"Nimble — {worker.config.name}",
                body="Worker process died unexpectedly. Skill disabled.",
            )
        except Exception:
            logger.exception(
                "Notifier failed while disabling skill %s", worker.config.name
            )

    def shutdown(self) -> None:
        self._shutdown_workers(self._registry.all())

    def _shutdown_workers(self, workers: list[SkillWorker]) -> None:
        for worker in workers:
            worker.process.terminate()
            try:
                worker.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                worker.process.kill()
