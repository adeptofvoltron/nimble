from __future__ import annotations

import logging
import os
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from nimble.skills.registry import SkillConfig

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    pass


class ManifestError(Exception):
    pass


@dataclass
class ConfigFieldSpec:
    key: str
    description: str
    default: str | None = None
    possible_values: list[str] | None = None


@dataclass
class ManifestSpec:
    name: str
    version: str
    api_version: int
    description: str
    entrypoint: str
    permissions: list[str]
    dependencies: list[str]
    author: str
    requires: list[str] = field(default_factory=list)
    class_name: str = ""
    config_fields: list[ConfigFieldSpec] = field(default_factory=list)


def _validate_manifest_skill_name(raw: object, source: str) -> str:
    """Ensure skill name is safe for use as a single filesystem directory segment."""
    name = str(raw)
    if not name:
        raise ManifestError(
            f"manifest.yaml from {source} field 'name' must be a non-empty string"
        )
    if name.strip() != name:
        raise ManifestError(
            f"manifest.yaml from {source} field 'name'"
            " must not have leading or trailing whitespace"
        )
    if "\x00" in name:
        raise ManifestError(
            f"manifest.yaml from {source} field 'name' contains invalid characters"
        )
    if "/" in name or "\\" in name:
        raise ManifestError(
            f"manifest.yaml from {source} field 'name'"
            f" must be a single path segment (got {name!r})"
        )
    parts = PurePosixPath(name).parts
    if len(parts) != 1:
        raise ManifestError(
            f"manifest.yaml from {source} field 'name'"
            f" must be a single path segment (got {name!r})"
        )
    segment = parts[0]
    if segment in (".", ".."):
        raise ManifestError(
            f"manifest.yaml from {source} field 'name' must not be {segment!r}"
        )
    return name


def _parse_manifest_string_list(
    data: dict[str, Any], field_name: str, source: str
) -> list[str]:
    raw = data.get(field_name)
    if raw is None:
        return []
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise ManifestError(
            f"manifest.yaml from {source} field '{field_name}'"
            " must be a list of strings"
        )
    return raw


def _require_non_empty_str(
    entry: dict[str, Any], field_name: str, i: int, source: str
) -> str:
    if field_name not in entry:
        raise ManifestError(
            f"manifest.yaml from {source} config_fields[{i}]"
            f" missing required field '{field_name}'"
        )
    value = entry[field_name]
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(
            f"manifest.yaml from {source} config_fields[{i}]"
            f" field '{field_name}' must be a non-empty string"
        )
    return value


def _parse_config_field_default(
    entry: dict[str, Any], i: int, source: str
) -> str | None:
    if "default" not in entry:
        return None
    raw = entry["default"]
    if raw is None or isinstance(raw, str):
        return raw
    raise ManifestError(
        f"manifest.yaml from {source} config_fields[{i}]"
        " field 'default' must be a string or null"
    )


def _parse_config_field_possible_values(
    entry: dict[str, Any], i: int, source: str
) -> list[str] | None:
    raw = entry.get("possible_values")
    if raw is None:
        return None
    if not isinstance(raw, list) or any(not isinstance(v, str) for v in raw):
        raise ManifestError(
            f"manifest.yaml from {source} config_fields[{i}]"
            " 'possible_values' must be a list of strings"
        )
    return raw


def _parse_config_field_entry(entry: Any, i: int, source: str) -> ConfigFieldSpec:
    if not isinstance(entry, dict):
        raise ManifestError(
            f"manifest.yaml from {source} config_fields[{i}] must be a mapping"
        )
    key = _require_non_empty_str(entry, "key", i, source)
    description = _require_non_empty_str(entry, "description", i, source)
    default = _parse_config_field_default(entry, i, source)
    possible_values = _parse_config_field_possible_values(entry, i, source)
    if (
        default is not None
        and possible_values is not None
        and default not in possible_values
    ):
        raise ManifestError(
            f"manifest.yaml from {source} config_fields[{i}]"
            " field 'default' must be one of 'possible_values'"
        )
    return ConfigFieldSpec(
        key=key,
        description=description,
        default=default,
        possible_values=possible_values,
    )


def _parse_config_fields(data: dict[str, Any], source: str) -> list[ConfigFieldSpec]:
    raw = data.get("config_fields")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ManifestError(
            f"manifest.yaml from {source} field 'config_fields' must be a list"
        )
    return [_parse_config_field_entry(entry, i, source) for i, entry in enumerate(raw)]


@dataclass
class AiConfig:
    provider: str
    model: str
    api_key_env: str


@dataclass
class NimbleConfig:
    skills: list[SkillConfig]
    ai: AiConfig | None = None


def atomic_write(path: Path, content: str) -> None:
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f"{path.name}.",
        suffix=".tmp",
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def disable_skill_in_config(config_path: Path, skill_name: str) -> None:
    try:
        with config_path.open() as f:
            raw = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as exc:
        raise OSError(f"Failed to read config.yaml: {exc}") from exc

    if raw is None:
        raw = {}

    skills = raw.get("skills", [])
    if not isinstance(skills, list):
        raise OSError("config.yaml 'skills' is not a list")

    for entry in skills:
        if isinstance(entry, dict) and entry.get("name") == skill_name:
            entry["disabled"] = True
            content = yaml.dump(raw, default_flow_style=False, allow_unicode=True)
            atomic_write(config_path, content)
            return

    raise ValueError(f"No skill named '{skill_name}' found in config.yaml")


def append_skill_to_config(
    config_path: Path,
    spec: ManifestSpec,
    binding: str,
    repo_url: str,
    repo_root: Path,
) -> None:
    if not (spec.class_name or "").strip():
        raise ConfigError(
            "manifest.yaml must declare 'class_name' for community skill installation"
        )
    try:
        with config_path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Failed to read config.yaml: {exc}") from exc

    if raw is None:
        raw = {}

    skills = raw.get("skills", [])
    if not isinstance(skills, list):
        raise ConfigError("config.yaml 'skills' must be a list")

    rel_path = str(Path(".nimble") / "skills" / spec.name / spec.entrypoint)
    entry: dict[str, Any] = {
        "name": spec.name,
        "source": "community",
        "path": rel_path,
        "class_name": spec.class_name,
        "binding": binding,
        "installed_from": repo_url,
        "version": spec.version,
    }
    skills.append(entry)
    raw["skills"] = skills
    atomic_write(
        config_path, yaml.dump(raw, default_flow_style=False, allow_unicode=True)
    )


def remove_skill_entry_from_config(config_path: Path, skill_name: str) -> None:
    """Remove the last skills[] entry whose name matches (rollback helper)."""
    try:
        with config_path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Failed to read config.yaml: {exc}") from exc

    if raw is None:
        raise ConfigError("Rollback failed: config.yaml is empty")

    skills = raw.get("skills", [])
    if not isinstance(skills, list):
        raise ConfigError("Rollback failed: config.yaml 'skills' is not a list")

    for i in range(len(skills) - 1, -1, -1):
        entry = skills[i]
        if isinstance(entry, dict) and entry.get("name") == skill_name:
            del skills[i]
            atomic_write(
                config_path,
                yaml.dump(raw, default_flow_style=False, allow_unicode=True),
            )
            return

    raise ConfigError(
        f"Rollback failed: no skill named {skill_name!r} found in config.yaml"
    )


def read_skill_manifest(config: SkillConfig, base_path: Path) -> dict[str, Any] | None:
    base_root = base_path.resolve()
    skill_path = Path(config.path)
    if skill_path.is_absolute():
        logger.warning(
            "Ignoring manifest for skill %s: absolute path is not allowed",
            config.name,
        )
        return None

    manifest_path = (base_root / skill_path.parent / "manifest.yaml").resolve()
    try:
        manifest_path.relative_to(base_root)
    except ValueError:
        logger.warning(
            "Ignoring manifest for skill %s: path escapes repository root",
            config.name,
        )
        return None

    if not manifest_path.is_file():
        return None
    try:
        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else None
    except (yaml.YAMLError, OSError, UnicodeDecodeError):
        logger.warning("Could not read manifest.yaml for skill %s", config.name)
        return None


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
    for key in ("provider", "model", "api_key_env"):
        if key not in raw:
            raise ConfigError(f"'ai' block missing required field: '{key}'")
    return AiConfig(
        provider=raw["provider"],
        model=raw["model"],
        api_key_env=raw["api_key_env"],
    )


def _parse_skill_configuration(
    entry: dict[str, Any], i: int
) -> dict[str, str]:
    raw = entry.get("configuration")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(
            f"Skill entry at index {i} 'configuration' must be a mapping"
        )
    result: dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            raise ConfigError(
                f"Skill entry at index {i} 'configuration' keys must be strings"
            )
        result[k] = str(v)
    return result


def _parse_skills(raw: Any) -> list[SkillConfig]:
    if not isinstance(raw, list):
        raise ConfigError("'skills' must be a list")

    skills: list[SkillConfig] = []
    required_fields = {"name", "source", "path", "class_name", "binding"}

    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ConfigError(f"Skill entry at index {i} must be a mapping")

        if entry.get("disabled"):
            continue

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
                configuration=_parse_skill_configuration(entry, i),
            )
        )

    return skills


def parse_manifest_yaml(content: str, source: str = "<string>") -> ManifestSpec:
    from nimble import SUPPORTED_API_VERSION

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ManifestError(f"Invalid manifest.yaml from {source}: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestError(f"manifest.yaml from {source} must be a YAML mapping")

    required_fields = {
        "name",
        "version",
        "api_version",
        "description",
        "entrypoint",
        "permissions",
        "dependencies",
        "author",
    }
    missing = required_fields - data.keys()
    if missing:
        raise ManifestError(
            f"manifest.yaml missing required field(s): {', '.join(sorted(missing))}"
        )

    raw_api_version = data["api_version"]
    try:
        api_version = int(raw_api_version)
    except (TypeError, ValueError) as exc:
        raise ManifestError(
            f"manifest.yaml from {source} field 'api_version'"
            " must be a positive integer"
        ) from exc
    if isinstance(raw_api_version, bool) or api_version < 1:
        raise ManifestError(
            f"manifest.yaml from {source} field 'api_version'"
            " must be a positive integer"
        )
    if api_version > SUPPORTED_API_VERSION:
        raise ManifestError(
            f"Skill requires Nimble api_version {api_version} — upgrade your daemon"
        )

    skill_name = _validate_manifest_skill_name(data["name"], source)
    config_fields = _parse_config_fields(data, source)

    return ManifestSpec(
        name=skill_name,
        version=str(data["version"]),
        api_version=api_version,
        description=str(data["description"]),
        entrypoint=str(data["entrypoint"]),
        permissions=_parse_manifest_string_list(data, "permissions", source),
        dependencies=_parse_manifest_string_list(data, "dependencies", source),
        author=str(data["author"]),
        requires=_parse_manifest_string_list(data, "requires", source),
        class_name=str(data.get("class_name", "")),
        config_fields=config_fields,
    )


def _github_url_to_raw(repo_url: str) -> str:
    url = repo_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if url.startswith(prefix):
            url = url[len(prefix) :]
            break
    parts = url.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ManifestError(f"Invalid GitHub URL: {repo_url!r}")
    user, repo = parts[0], parts[1]
    return f"https://raw.githubusercontent.com/{user}/{repo}/HEAD/manifest.yaml"


def fetch_remote_manifest(repo_url: str) -> ManifestSpec:
    raw_url = _github_url_to_raw(repo_url)
    try:
        with urllib.request.urlopen(raw_url, timeout=30) as response:
            content = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise ManifestError(
            f"Could not fetch manifest.yaml from {repo_url}: HTTP {exc.code}"
        ) from exc
    except Exception as exc:
        raise ManifestError(
            f"Could not fetch manifest.yaml from {repo_url}: {exc}"
        ) from exc
    return parse_manifest_yaml(content, source=repo_url)
