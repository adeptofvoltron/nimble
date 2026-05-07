from __future__ import annotations

from pathlib import Path

import yaml

from nimble.manifest.parser import atomic_write


def read_lock(lock_path: Path) -> dict[str, dict[str, str]]:
    if not lock_path.exists():
        return {}
    try:
        with lock_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return {}
        skills = data.get("skills", {})
        if not isinstance(skills, dict):
            return {}
        return {k: v for k, v in skills.items() if isinstance(v, dict)}
    except Exception:
        return {}


def write_lock_entry(
    lock_path: Path, name: str, installed_from: str, version: str
) -> None:
    skills = read_lock(lock_path)
    skills[name] = {"installed_from": installed_from, "version": version}
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    content = yaml.dump(
        {"skills": skills}, default_flow_style=False, allow_unicode=True
    )
    atomic_write(lock_path, content)


def remove_lock_entry(lock_path: Path, skill_name: str) -> None:
    skills = read_lock(lock_path)
    if skill_name not in skills:
        return
    del skills[skill_name]
    atomic_write(
        lock_path,
        yaml.dump({"skills": skills}, default_flow_style=False, allow_unicode=True),
    )
