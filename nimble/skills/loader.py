from __future__ import annotations

import logging
from pathlib import Path

from nimble.manifest.parser import ConfigError
from nimble.skills.registry import SkillConfig

logger = logging.getLogger(__name__)


def validate_skill_paths(
    configs: list[SkillConfig], base_path: Path
) -> list[SkillConfig]:
    for config in configs:
        skill_path = base_path / config.path
        if not skill_path.exists():
            raise ConfigError(
                f"Skill '{config.name}': path '{config.path}' does not exist"
            )
    return configs
