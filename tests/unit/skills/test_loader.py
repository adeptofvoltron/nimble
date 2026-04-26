from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nimble.manifest.parser import ConfigError, load_config
from nimble.skills.loader import validate_skill_paths
from nimble.skills.registry import SkillConfig, SkillRegistry
from nimble.skills.runner import SkillRunner


def _make_config(name: str, path: str, source: str = "local") -> SkillConfig:
    return SkillConfig(
        name=name,
        source=source,  # type: ignore[arg-type]
        binding="ctrl+shift+x",
        path=path,
        class_name="SomeSkill",
    )


def test_validate_all_paths_exist(tmp_path: Path) -> None:
    skill_file = tmp_path / "skill.py"
    skill_file.write_text("class SomeSkill:\n    pass\n")
    configs = [_make_config("test-skill", "skill.py")]
    result = validate_skill_paths(configs, tmp_path)
    assert result is configs


def test_validate_missing_path_raises_config_error(tmp_path: Path) -> None:
    configs = [_make_config("missing-skill", "does_not_exist.py")]
    with pytest.raises(ConfigError) as exc_info:
        validate_skill_paths(configs, tmp_path)
    assert "missing-skill" in str(exc_info.value)


def test_validate_multiple_skills_first_missing_raises(tmp_path: Path) -> None:
    present_file = tmp_path / "present.py"
    present_file.write_text("class SomeSkill:\n    pass\n")
    configs = [
        _make_config("first-missing", "nope.py"),
        _make_config("second-present", "present.py"),
    ]
    with pytest.raises(ConfigError) as exc_info:
        validate_skill_paths(configs, tmp_path)
    assert "first-missing" in str(exc_info.value)


def test_full_chain_parser_loader_registry(tmp_path: Path) -> None:
    skill_file = tmp_path / "skills" / "hello.py"
    skill_file.parent.mkdir()
    skill_file.write_text("class HelloSkill:\n    pass\n")

    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text(
        "skills:\n"
        "  - name: hello\n"
        "    source: local\n"
        "    path: skills/hello.py\n"
        "    class_name: HelloSkill\n"
        "    binding: ctrl+shift+h\n"
    )

    nimble_config = load_config(config_yaml)
    validated = validate_skill_paths(nimble_config.skills, tmp_path)

    import json as _json

    registry = SkillRegistry()
    fake_proc = MagicMock()
    fake_proc.poll.return_value = None
    fake_proc.stdin = MagicMock()
    fake_proc.stdout = MagicMock()
    fake_proc.stdout.readline.return_value = (
        _json.dumps({"invocation_id": "", "status": "ok", "error": None}) + "\n"
    ).encode("utf-8")
    fake_proc.stderr = MagicMock()

    with patch("subprocess.Popen", return_value=fake_proc):
        runner = SkillRunner(
            registry=registry, notifier=MagicMock(), repo_root=tmp_path
        )
        runner.spawn_workers(validated)

    worker = registry.get("hello")
    assert worker is not None
    assert worker.config.source == "local"
    assert worker.config.binding == "ctrl+shift+h"
    assert worker.status == "loaded"
