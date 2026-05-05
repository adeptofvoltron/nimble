from __future__ import annotations

import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nimble import SUPPORTED_API_VERSION
from nimble.manifest.parser import (
    AiConfig,
    ConfigError,
    ConfigFieldSpec,
    ManifestError,
    ManifestSpec,
    NimbleConfig,
    append_skill_to_config,
    atomic_write,
    remove_skill_entry_from_config,
    disable_skill_in_config,
    fetch_remote_manifest,
    load_config,
    parse_manifest_yaml,
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


def test_read_skill_manifest_returns_none_for_absolute_skill_path(
    tmp_path: Path,
) -> None:
    skill_dir = tmp_path / "skills" / "my_skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "manifest.yaml").write_text("api_version: 1\n")
    config = _make_skill_config(path="/tmp/my_skill/skill.py")
    result = read_skill_manifest(config, tmp_path)
    assert result is None


def test_atomic_write_creates_file_with_correct_content(tmp_path: Path) -> None:
    target = tmp_path / "config.yaml"
    atomic_write(target, "hello: world\n")
    assert target.read_text(encoding="utf-8") == "hello: world\n"


def test_atomic_write_no_tmp_file_left_on_success(tmp_path: Path) -> None:
    target = tmp_path / "config.yaml"
    atomic_write(target, "data: 1\n")
    assert list(tmp_path.glob("config.yaml*.tmp")) == []


def test_atomic_write_preserves_original_on_failure(tmp_path: Path) -> None:
    target = tmp_path / "config.yaml"
    target.write_text("original", encoding="utf-8")

    with patch.object(Path, "replace", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            atomic_write(target, "new content")

    assert target.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.glob("config.yaml*.tmp")) == []


def test_atomic_write_uses_same_directory_for_tmp(tmp_path: Path) -> None:
    target = tmp_path / "config.yaml"
    captured_dir: Path | None = None
    original_mkstemp = tempfile.mkstemp

    def capturing_mkstemp(*args: object, **kwargs: object) -> tuple[int, str]:
        nonlocal captured_dir
        captured_dir_value = kwargs.get("dir")
        if captured_dir_value is not None:
            captured_dir = Path(captured_dir_value)
        return original_mkstemp(*args, **kwargs)  # type: ignore[arg-type]

    with patch("tempfile.mkstemp", side_effect=capturing_mkstemp):
        atomic_write(target, "content")

    assert captured_dir == tmp_path


def test_disable_skill_sets_disabled_flag(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "skills:\n"
        "  - name: hello-world\n"
        "    source: local\n"
        "    path: skills/hello_world/skill.py\n"
        "    class_name: HelloWorldSkill\n"
        "    binding: ctrl+shift+h\n"
    )
    disable_skill_in_config(cfg, "hello-world")
    import yaml

    data = yaml.safe_load(cfg.read_text())
    assert data["skills"][0].get("disabled") is True


def test_disable_skill_not_found_raises(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "skills:\n"
        "  - name: foo\n"
        "    source: local\n"
        "    path: p\n"
        "    class_name: C\n"
        "    binding: b\n"
    )
    original = cfg.read_text()
    with pytest.raises(ValueError, match="No skill named 'bar'"):
        disable_skill_in_config(cfg, "bar")
    assert cfg.read_text() == original


def test_disable_skill_preserves_other_fields(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "skills:\n"
        "  - name: hello-world\n"
        "    source: local\n"
        "    path: skills/hello_world/skill.py\n"
        "    class_name: HelloWorldSkill\n"
        "    binding: ctrl+shift+h\n"
    )
    disable_skill_in_config(cfg, "hello-world")
    import yaml

    skill = yaml.safe_load(cfg.read_text())["skills"][0]
    assert skill["name"] == "hello-world"
    assert skill["binding"] == "ctrl+shift+h"
    assert skill["path"] == "skills/hello_world/skill.py"


def test_parse_skills_skips_disabled_entries(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "skills:\n"
        "  - name: active-skill\n"
        "    source: local\n"
        "    path: skills/active/skill.py\n"
        "    class_name: ActiveSkill\n"
        "    binding: ctrl+shift+a\n"
        "  - name: disabled-skill\n"
        "    source: local\n"
        "    path: skills/disabled/skill.py\n"
        "    class_name: DisabledSkill\n"
        "    binding: ctrl+shift+d\n"
        "    disabled: true\n"
    )
    result = load_config(cfg)
    assert len(result.skills) == 1
    assert result.skills[0].name == "active-skill"


def test_read_skill_manifest_returns_none_for_path_traversal(tmp_path: Path) -> None:
    outside_manifest = tmp_path.parent / "manifest.yaml"
    outside_manifest.write_text("api_version: 999\n")
    config = _make_skill_config(path="../outside/skill.py")
    result = read_skill_manifest(config, tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# parse_manifest_yaml tests
# ---------------------------------------------------------------------------

_VALID_MANIFEST_YAML = """\
name: test-skill
version: "1.2.3"
api_version: 1
description: A test skill
entrypoint: skill.py
class_name: TestSkill
permissions:
  - ai
dependencies:
  - anthropic
author: Test Author
"""


def test_parse_manifest_yaml_valid() -> None:
    spec = parse_manifest_yaml(_VALID_MANIFEST_YAML)
    assert spec.name == "test-skill"
    assert spec.version == "1.2.3"
    assert spec.api_version == 1
    assert spec.permissions == ["ai"]
    assert spec.dependencies == ["anthropic"]
    assert spec.class_name == "TestSkill"
    assert spec.requires == []


def test_parse_manifest_yaml_name_rejects_path_with_slash() -> None:
    content = _VALID_MANIFEST_YAML.replace("name: test-skill", "name: evil/nested")
    with pytest.raises(ManifestError, match="single path segment"):
        parse_manifest_yaml(content)


def test_parse_manifest_yaml_name_rejects_dotdot() -> None:
    content = _VALID_MANIFEST_YAML.replace("name: test-skill", "name: ..")
    with pytest.raises(ManifestError, match="must not be"):
        parse_manifest_yaml(content)


def test_parse_manifest_yaml_name_rejects_leading_trailing_space() -> None:
    content = _VALID_MANIFEST_YAML.replace("name: test-skill", "name: ' bad '")
    with pytest.raises(ManifestError, match="leading or trailing whitespace"):
        parse_manifest_yaml(content)


def test_parse_manifest_yaml_missing_required_field() -> None:
    content = _VALID_MANIFEST_YAML.replace("entrypoint: skill.py\n", "")
    with pytest.raises(ManifestError, match="entrypoint"):
        parse_manifest_yaml(content)


def test_parse_manifest_yaml_api_version_too_high() -> None:
    content = _VALID_MANIFEST_YAML.replace("api_version: 1", "api_version: 99")
    with pytest.raises(ManifestError, match="upgrade your daemon"):
        parse_manifest_yaml(content)


def test_parse_manifest_yaml_api_version_equal_supported_ok() -> None:
    replacement = f"api_version: {SUPPORTED_API_VERSION}"
    content = _VALID_MANIFEST_YAML.replace("api_version: 1", replacement)
    spec = parse_manifest_yaml(content)
    assert spec.api_version == SUPPORTED_API_VERSION


def test_parse_manifest_yaml_invalid_yaml() -> None:
    with pytest.raises(ManifestError, match="Invalid manifest"):
        parse_manifest_yaml("not: valid: yaml: :::")


def test_parse_manifest_yaml_non_numeric_api_version() -> None:
    content = _VALID_MANIFEST_YAML.replace("api_version: 1", 'api_version: "v1"')
    with pytest.raises(ManifestError, match="api_version"):
        parse_manifest_yaml(content)


def test_parse_manifest_yaml_non_positive_api_version() -> None:
    content = _VALID_MANIFEST_YAML.replace("api_version: 1", "api_version: 0")
    with pytest.raises(ManifestError, match="positive integer"):
        parse_manifest_yaml(content)


def test_parse_manifest_yaml_bool_api_version_rejected() -> None:
    content = _VALID_MANIFEST_YAML.replace("api_version: 1", "api_version: true")
    with pytest.raises(ManifestError, match="positive integer"):
        parse_manifest_yaml(content)


def test_parse_manifest_yaml_requires_defaults_to_empty() -> None:
    spec = parse_manifest_yaml(_VALID_MANIFEST_YAML)
    assert spec.requires == []


def test_parse_manifest_yaml_permissions_rejects_scalar() -> None:
    content = _VALID_MANIFEST_YAML.replace(
        "permissions:\n  - ai\n", "permissions: ai\n"
    )
    with pytest.raises(ManifestError, match="permissions"):
        parse_manifest_yaml(content)


def test_parse_manifest_yaml_dependencies_rejects_scalar() -> None:
    content = _VALID_MANIFEST_YAML.replace(
        "dependencies:\n  - anthropic\n", "dependencies: anthropic\n"
    )
    with pytest.raises(ManifestError, match="dependencies"):
        parse_manifest_yaml(content)


def test_parse_manifest_yaml_requires_rejects_scalar() -> None:
    content = _VALID_MANIFEST_YAML + "requires: context.md\n"
    with pytest.raises(ManifestError, match="requires"):
        parse_manifest_yaml(content)


# ---------------------------------------------------------------------------
# _github_url_to_raw tests
# ---------------------------------------------------------------------------


def test_github_url_to_raw_https() -> None:
    from nimble.manifest.parser import _github_url_to_raw

    url = _github_url_to_raw("https://github.com/user/my-skill")
    assert url == "https://raw.githubusercontent.com/user/my-skill/HEAD/manifest.yaml"


def test_github_url_to_raw_without_protocol() -> None:
    from nimble.manifest.parser import _github_url_to_raw

    url = _github_url_to_raw("github.com/user/my-skill")
    assert url == "https://raw.githubusercontent.com/user/my-skill/HEAD/manifest.yaml"


def test_github_url_to_raw_with_git_suffix() -> None:
    from nimble.manifest.parser import _github_url_to_raw

    url = _github_url_to_raw("https://github.com/user/my-skill.git")
    assert url == "https://raw.githubusercontent.com/user/my-skill/HEAD/manifest.yaml"


# ---------------------------------------------------------------------------
# fetch_remote_manifest tests
# ---------------------------------------------------------------------------


def test_fetch_remote_manifest_success() -> None:
    mock_response = MagicMock()
    mock_response.read.return_value = _VALID_MANIFEST_YAML.encode("utf-8")
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_response):
        spec = fetch_remote_manifest("github.com/user/test-skill")
    assert spec.name == "test-skill"


def test_fetch_remote_manifest_http_error() -> None:
    err = urllib.error.HTTPError(
        None, 404, "Not Found", {}, None  # type: ignore[arg-type]
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(ManifestError, match="HTTP 404"):
            fetch_remote_manifest("github.com/user/missing-skill")


def test_fetch_remote_manifest_network_error() -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
        with pytest.raises(ManifestError, match="Could not fetch"):
            fetch_remote_manifest("github.com/user/unreachable-skill")


# ---------------------------------------------------------------------------
# append_skill_to_config tests
# ---------------------------------------------------------------------------


def _make_manifest_spec(**overrides: object) -> ManifestSpec:
    defaults: dict[str, object] = {
        "name": "log-diagnosis",
        "version": "1.0.0",
        "api_version": 1,
        "description": "A log diagnosis skill",
        "entrypoint": "skill.py",
        "permissions": [],
        "dependencies": [],
        "author": "Test Author",
        "class_name": "LogDiagnosisSkill",
    }
    defaults.update(overrides)
    return ManifestSpec(**defaults)  # type: ignore[arg-type]


def test_append_skill_to_config_adds_entry(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("skills: []\n", encoding="utf-8")
    spec = _make_manifest_spec()
    append_skill_to_config(
        cfg, spec, "ctrl+shift+d", "https://github.com/u/log-diagnosis", tmp_path
    )
    import yaml as _yaml

    data = _yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert len(data["skills"]) == 1
    entry = data["skills"][0]
    assert entry["name"] == "log-diagnosis"
    assert entry["source"] == "community"
    assert entry["path"] == ".nimble/skills/log-diagnosis/skill.py"
    assert entry["class_name"] == "LogDiagnosisSkill"
    assert entry["binding"] == "ctrl+shift+d"
    assert entry["installed_from"] == "https://github.com/u/log-diagnosis"
    assert entry["version"] == "1.0.0"


def test_append_skill_to_config_preserves_existing(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "skills:\n"
        "  - name: hello-world\n"
        "    source: local\n"
        "    path: skills/hello_world/skill.py\n"
        "    class_name: HelloWorldSkill\n"
        "    binding: ctrl+l\n",
        encoding="utf-8",
    )
    spec = _make_manifest_spec()
    append_skill_to_config(
        cfg, spec, "ctrl+shift+d", "https://github.com/u/log-diagnosis", tmp_path
    )
    import yaml as _yaml

    data = _yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert len(data["skills"]) == 2
    assert data["skills"][0]["name"] == "hello-world"
    assert data["skills"][1]["name"] == "log-diagnosis"


def test_append_skill_to_config_empty_class_name_raises(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("skills: []\n", encoding="utf-8")
    spec = _make_manifest_spec(class_name="")
    original = cfg.read_text(encoding="utf-8")
    with pytest.raises(ConfigError, match="class_name"):
        append_skill_to_config(
            cfg, spec, "ctrl+shift+d", "https://github.com/u/s", tmp_path
        )
    assert cfg.read_text(encoding="utf-8") == original


def test_append_skill_to_config_uses_atomic_write(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("skills: []\n", encoding="utf-8")
    spec = _make_manifest_spec()
    with patch("nimble.manifest.parser.atomic_write") as mock_aw:
        append_skill_to_config(
            cfg, spec, "ctrl+shift+d", "https://github.com/u/s", tmp_path
        )
    mock_aw.assert_called_once()


def test_append_skill_to_config_skills_must_be_list(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("skills: {}\n", encoding="utf-8")
    spec = _make_manifest_spec()
    with pytest.raises(ConfigError, match="skills.*list"):
        append_skill_to_config(
            cfg, spec, "ctrl+shift+d", "https://github.com/u/s", tmp_path
        )


def test_append_skill_to_config_whitespace_class_name_raises(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("skills: []\n", encoding="utf-8")
    spec = _make_manifest_spec(class_name="   ")
    with pytest.raises(ConfigError, match="class_name"):
        append_skill_to_config(
            cfg, spec, "ctrl+shift+d", "https://github.com/u/s", tmp_path
        )


def test_remove_skill_entry_from_config_removes_last_match(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "skills:\n"
        "  - name: log-diagnosis\n"
        "    source: community\n"
        "    binding: a\n"
        "  - name: log-diagnosis\n"
        "    source: community\n"
        "    binding: b\n",
        encoding="utf-8",
    )
    remove_skill_entry_from_config(cfg, "log-diagnosis")
    import yaml as _yaml

    data = _yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert len(data["skills"]) == 1
    assert data["skills"][0]["binding"] == "a"


def test_remove_skill_entry_from_config_not_found_raises(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("skills: []\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="Rollback failed"):
        remove_skill_entry_from_config(cfg, "missing")


def test_remove_skill_entry_from_config_skills_not_list_raises(
    tmp_path: Path,
) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("skills: {}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="Rollback failed"):
        remove_skill_entry_from_config(cfg, "x")


# ---------------------------------------------------------------------------
# config_fields tests (AC 1–5)
# ---------------------------------------------------------------------------

_VALID_MANIFEST_WITH_CONFIG_FIELDS = (
    _VALID_MANIFEST_YAML
    + "config_fields:\n"
    "  - key: target_language\n"
    "    description: Target language code\n"
    "    default: en\n"
    "    possible_values:\n"
    "      - en\n"
    "      - es\n"
    "      - fr\n"
)


def test_parse_manifest_config_fields_populated() -> None:
    spec = parse_manifest_yaml(_VALID_MANIFEST_WITH_CONFIG_FIELDS)
    assert len(spec.config_fields) == 1
    cf = spec.config_fields[0]
    assert isinstance(cf, ConfigFieldSpec)
    assert cf.key == "target_language"
    assert cf.description == "Target language code"
    assert cf.default == "en"


def test_parse_manifest_config_fields_possible_values_parsed() -> None:
    spec = parse_manifest_yaml(_VALID_MANIFEST_WITH_CONFIG_FIELDS)
    assert spec.config_fields[0].possible_values == ["en", "es", "fr"]


def test_parse_manifest_config_fields_no_possible_values_is_none() -> None:
    content = (
        _VALID_MANIFEST_YAML
        + "config_fields:\n"
        "  - key: output_format\n"
        "    description: Output format\n"
    )
    spec = parse_manifest_yaml(content)
    assert spec.config_fields[0].possible_values is None


def test_parse_manifest_no_config_fields_defaults_to_empty() -> None:
    spec = parse_manifest_yaml(_VALID_MANIFEST_YAML)
    assert spec.config_fields == []


def test_parse_manifest_config_fields_missing_key_raises() -> None:
    content = (
        _VALID_MANIFEST_YAML
        + "config_fields:\n"
        "  - description: No key field here\n"
    )
    with pytest.raises(ManifestError, match="missing required field 'key'"):
        parse_manifest_yaml(content)


def test_parse_manifest_config_fields_missing_description_raises() -> None:
    content = (
        _VALID_MANIFEST_YAML
        + "config_fields:\n"
        "  - key: some_key\n"
    )
    with pytest.raises(ManifestError, match="missing required field 'description'"):
        parse_manifest_yaml(content)


def test_parse_manifest_config_fields_not_list_raises() -> None:
    content = _VALID_MANIFEST_YAML + "config_fields: bad\n"
    with pytest.raises(ManifestError, match="field 'config_fields' must be a list"):
        parse_manifest_yaml(content)


def test_parse_manifest_config_fields_entry_not_mapping_raises() -> None:
    content = _VALID_MANIFEST_YAML + "config_fields:\n  - hello\n"
    with pytest.raises(ManifestError, match="must be a mapping"):
        parse_manifest_yaml(content)


def test_parse_manifest_config_fields_default_non_string_raises() -> None:
    content = (
        _VALID_MANIFEST_YAML
        + "config_fields:\n"
        "  - key: target_language\n"
        "    description: Target language code\n"
        "    default: 42\n"
    )
    with pytest.raises(
        ManifestError, match="field 'default' must be a string or null"
    ):
        parse_manifest_yaml(content)


def test_parse_manifest_config_fields_possible_values_items_must_be_strings() -> None:
    content = (
        _VALID_MANIFEST_YAML
        + "config_fields:\n"
        "  - key: target_language\n"
        "    description: Target language code\n"
        "    possible_values:\n"
        "      - en\n"
        "      - 2\n"
    )
    match = "'possible_values' must be a list of strings"
    with pytest.raises(ManifestError, match=match):
        parse_manifest_yaml(content)


def test_parse_manifest_config_fields_key_must_be_non_empty_string() -> None:
    content = (
        _VALID_MANIFEST_YAML
        + "config_fields:\n"
        "  - key: \"   \"\n"
        "    description: Target language code\n"
    )
    with pytest.raises(ManifestError, match="field 'key' must be a non-empty string"):
        parse_manifest_yaml(content)


def test_parse_manifest_config_fields_description_must_be_non_empty_string() -> None:
    content = (
        _VALID_MANIFEST_YAML
        + "config_fields:\n"
        "  - key: target_language\n"
        "    description: \"\"\n"
    )
    with pytest.raises(
        ManifestError, match="field 'description' must be a non-empty string"
    ):
        parse_manifest_yaml(content)


def test_parse_manifest_config_fields_default_must_be_in_possible_values() -> None:
    content = (
        _VALID_MANIFEST_YAML
        + "config_fields:\n"
        "  - key: target_language\n"
        "    description: Target language code\n"
        "    default: de\n"
        "    possible_values:\n"
        "      - en\n"
        "      - es\n"
    )
    with pytest.raises(
        ManifestError, match="field 'default' must be one of 'possible_values'"
    ):
        parse_manifest_yaml(content)
