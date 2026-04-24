from __future__ import annotations

import logging
import os
import signal
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from nimble.context.assembler import build_context
from nimble.hotkeys import get_adapter
from nimble.manifest.parser import ConfigError, load_config
from nimble.notifier import Notifier
from nimble.skills.loader import validate_skill_paths
from nimble.skills.registry import SkillConfig, SkillRegistry
from nimble.skills.runner import SkillRunner
from nimble.state import remove_pid, write_pid
from nimble.watcher import ConfigWatcher

logger = logging.getLogger(__name__)


def run(repo_root: Path, debug: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    notifier = Notifier()
    registry = SkillRegistry()
    adapter = get_adapter()
    runner = SkillRunner(registry, notifier, repo_root)

    config_path = repo_root / "config.yaml"
    watcher: ConfigWatcher | None = None
    started = False

    try:
        config = load_config(config_path)
        validated = validate_skill_paths(config.skills, repo_root)
    except ConfigError as exc:
        logger.error("Config error on startup: %s", exc)
        sys.exit(1)

    runner.spawn_workers(validated)

    for skill in validated:
        adapter.register(skill.binding, _make_callback(skill.name, runner, notifier))

    stop_event = threading.Event()

    def _signal_handler(signum: int, frame: Any) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    adapter.start()
    write_pid(os.getpid())
    started = True

    notifier.send("Nimble", "Nimble daemon running.")  # FR41

    def _shutdown_worker(name: str) -> None:
        worker = registry.get(name)
        if worker is None:
            return
        worker.process.terminate()
        try:
            worker.process.wait(timeout=5.0)
        except Exception:
            worker.process.kill()
        registry.disable(name)

    def _reload_config(cfg_path: Path) -> None:
        try:
            new_config = load_config(cfg_path)
            new_validated = validate_skill_paths(new_config.skills, repo_root)
        except ConfigError as exc:
            logger.error("Config reload error (keeping current state): %s", exc)
            return

        current: dict[str, SkillConfig] = {
            w.config.name: w.config for w in registry.all() if w.status != "failed"
        }
        incoming: dict[str, SkillConfig] = {s.name: s for s in new_validated}

        to_remove = [
            name
            for name, cfg in current.items()
            if name not in incoming or incoming[name] != cfg
        ]
        to_add = [
            cfg
            for cfg in new_validated
            if cfg.name not in current or current[cfg.name] != cfg
        ]
        unchanged = [
            cfg
            for cfg in new_validated
            if cfg.name in current and current[cfg.name] == cfg
        ]

        for name in to_remove:
            _shutdown_worker(name)

        runner.spawn_workers(to_add)

        for skill in to_add:
            adapter.register(
                skill.binding, _make_callback(skill.name, runner, notifier)
            )

        logger.info(
            "Config reloaded: +%d added, -%d removed, =%d unchanged",
            len(to_add),
            len(to_remove),
            len(unchanged),
        )

    watcher = ConfigWatcher(config_path, _reload_config)
    watcher.start()

    try:
        stop_event.wait()
    finally:
        if watcher is not None:
            watcher.stop()
        if started:
            runner.shutdown()
            adapter.stop()
            remove_pid()
            logger.info("Nimble daemon stopped")


def _make_callback(
    skill_name: str, runner: SkillRunner, notifier: Notifier
) -> Callable[[], None]:
    def _callback() -> None:
        threading.Thread(
            target=_dispatch, args=(skill_name, runner, notifier), daemon=True
        ).start()

    return _callback


def _dispatch(skill_name: str, runner: SkillRunner, notifier: Notifier) -> None:
    context = build_context()
    result = runner.dispatch(skill_name, context)
    if result.status == "error" and result.error is not None:
        error = result.error
        notifier.send(
            title=f"Nimble — {skill_name}",
            body=(
                f"{error.type}: {error.message}"
                f" in {error.skill_file} line {error.line}"
            ),
        )
        logger.error(
            "Skill %s dispatch error: %s: %s in %s line %d",
            skill_name,
            error.type,
            error.message,
            error.skill_file,
            error.line,
        )
