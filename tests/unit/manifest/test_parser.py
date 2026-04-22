from __future__ import annotations

from pathlib import Path

import pytest

from nimble.manifest.parser import ConfigError, NimbleConfig, load_config


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
