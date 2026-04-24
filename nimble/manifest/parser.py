from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from nimble.skills.registry import SkillConfig

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    pass


@dataclass
class AiConfig:
    provider: str
    model: str
    api_key_env: str


@dataclass
class NimbleConfig:
    skills: list[SkillConfig]
    ai: AiConfig | None = None


def load_config(config_path: Path) -> NimbleConfig:
    try:
        with config_path.open() as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = (mark.line + 1) if mark else "?"
        problem = getattr(exc, "problem", str(exc))
        raise ConfigError(f"config.yaml line {line}: {problem}") from exc

    if data is None:
        data = {}

    parsed_skills = _parse_skills(data.get("skills", []))
    ai_config = _parse_ai_config(data)
    return NimbleConfig(skills=parsed_skills, ai=ai_config)


def _parse_ai_config(data: dict[str, Any]) -> AiConfig | None:
    raw = data.get("ai")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ConfigError("'ai' must be a mapping")
    for field in ("provider", "model", "api_key_env"):
        if field not in raw:
            raise ConfigError(f"'ai' block missing required field: '{field}')")
    return AiConfig(
        provider=raw["provider"],
        model=raw["model"],
        api_key_env=raw["api_key_env"],
    )


def _parse_skills(raw: Any) -> list[SkillConfig]:
    if not isinstance(raw, list):
        raise ConfigError("'skills' must be a list")

    skills: list[SkillConfig] = []
    required_fields = {"name", "source", "path", "class_name", "binding"}

    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ConfigError(f"Skill entry at index {i} must be a mapping")

        missing = required_fields - entry.keys()
        if missing:
            raise ConfigError(
                f"Skill entry at index {i} missing required fields: {sorted(missing)}"
            )

        source = entry["source"]
        if source not in {"local", "community"}:
            raise ConfigError(
                f"Skill entry at index {i} has invalid source {source!r}; "
                "must be 'local' or 'community'"
            )

        skills.append(
            SkillConfig(
                name=entry["name"],
                source=source,
                binding=entry["binding"],
                path=entry["path"],
                class_name=entry["class_name"],
            )
        )

    return skills
