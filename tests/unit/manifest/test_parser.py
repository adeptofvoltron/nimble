from __future__ import annotations

from pathlib import Path

import pytest

from nimble.manifest.parser import (
    AiConfig,
    ConfigError,
    NimbleConfig,
    load_config,
    read_skill_manifest,
)
from nimble.skills.registry import SkillConfig


def _make_skill_config(path: str = "skills/my_skill/skill.py") -> SkillConfig:
    return SkillConfig(
        name="my_skill",
        source="local",
        binding="ctrl+x",
        path=path,
        class_name="MySkill",
    )


def _write_config(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(content)
    return p


def test_load_single_local_skill(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        "skills:\n"
        "  - name: hello-world\n"
        "    source: local\n"
        "    path: skills/hello_world/skill.py\n"
        "    class_name: HelloWorldSkill\n"
        "    binding: ctrl+shift+h\n",
    )
    result = load_config(cfg)
    assert isinstance(result, NimbleConfig)
    assert len(result.skills) == 1
    skill = result.skills[0]
    assert skill.name == "hello-world"
    assert skill.source == "local"
    assert skill.path == "skills/hello_world/skill.py"
    assert skill.class_name == "HelloWorldSkill"
    assert skill.binding == "ctrl+shift+h"


def test_load_empty_skills_list(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, "skills: []\n")
    result = load_config(cfg)
    assert result == NimbleConfig(skills=[])


def test_load_missing_skills_key(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, "bindings: []\n")
    result = load_config(cfg)
    assert result == NimbleConfig(skills=[])


def test_load_syntax_error_raises_config_error_with_line(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("skills:\n\t- name: oops\n")
    with pytest.raises(ConfigError) as exc_info:
        load_config(cfg)
    assert "line" in str(exc_info.value)


def test_load_missing_required_field_raises_config_error(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        "skills:\n"
        "  - name: broken\n"
        "    source: local\n"
        "    path: skills/broken/skill.py\n"
        "    binding: ctrl+shift+b\n",
        # class_name is missing
    )
    with pytest.raises(ConfigError):
        load_config(cfg)


def test_load_invalid_source_raises_config_error(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        "skills:\n"
        "  - name: bad\n"
        "    source: invalid\n"
        "    path: skills/bad/skill.py\n"
        "    class_name: BadSkill\n"
        "    binding: ctrl+shift+b\n",
    )
    with pytest.raises(ConfigError):
        load_config(cfg)


def test_load_community_skill_parsed_correctly(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        "skills:\n"
        "  - name: log-diagnosis\n"
        "    source: community\n"
        "    path: skills/log_diagnosis/skill.py\n"
        "    class_name: LogDiagnosisSkill\n"
        "    binding: ctrl+shift+d\n",
    )
    result = load_config(cfg)
    assert result.skills[0].source == "community"


def test_load_config_with_ai_block(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        "skills: []\n"
        "ai:\n"
        "  provider: anthropic\n"
        "  model: claude-sonnet-4-6\n"
        "  api_key_env: ANTHROPIC_API_KEY\n",
    )
    result = load_config(cfg)
    assert isinstance(result.ai, AiConfig)
    assert result.ai.provider == "anthropic"
    assert result.ai.model == "claude-sonnet-4-6"
    assert result.ai.api_key_env == "ANTHROPIC_API_KEY"


def test_load_config_without_ai_block(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, "skills: []\n")
    result = load_config(cfg)
    assert result.ai is None


def test_load_config_ai_missing_required_field(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        "skills: []\n"
        "ai:\n"
        "  provider: anthropic\n"
        "  api_key_env: ANTHROPIC_API_KEY\n",  # 'model' missing
    )
    with pytest.raises(ConfigError, match="model"):
        load_config(cfg)


# ---------------------------------------------------------------------------
# read_skill_manifest tests
# ---------------------------------------------------------------------------


def test_read_skill_manifest_returns_none_when_no_manifest(tmp_path: Path) -> None:
    config = _make_skill_config()
    result = read_skill_manifest(config, tmp_path)
    assert result is None


def test_read_skill_manifest_returns_dict_when_manifest_exists(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills" / "my_skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "manifest.yaml").write_text("api_version: 1\nname: my_skill\n")
    config = _make_skill_config()
    result = read_skill_manifest(config, tmp_path)
    assert result == {"api_version": 1, "name": "my_skill"}


def test_read_skill_manifest_returns_none_on_invalid_yaml(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills" / "my_skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "manifest.yaml").write_text("key: [\ninvalid yaml")
    config = _make_skill_config()
    result = read_skill_manifest(config, tmp_path)
    assert result is None


def test_read_skill_manifest_returns_none_when_not_dict(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills" / "my_skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "manifest.yaml").write_text("just a string\n")
    config = _make_skill_config()
    result = read_skill_manifest(config, tmp_path)
    assert result is None


def test_read_skill_manifest_returns_none_for_absolute_skill_path(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills" / "my_skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "manifest.yaml").write_text("api_version: 1\n")
    config = _make_skill_config(path="/tmp/my_skill/skill.py")
    result = read_skill_manifest(config, tmp_path)
    assert result is None


def test_read_skill_manifest_returns_none_for_path_traversal(tmp_path: Path) -> None:
    outside_manifest = tmp_path.parent / "manifest.yaml"
    outside_manifest.write_text("api_version: 999\n")
    config = _make_skill_config(path="../outside/skill.py")
    result = read_skill_manifest(config, tmp_path)
    assert result is None
