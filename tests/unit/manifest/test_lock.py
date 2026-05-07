from __future__ import annotations

from pathlib import Path

import yaml

from nimble.manifest.lock import read_lock, remove_lock_entry, write_lock_entry


def test_read_lock_missing_file(tmp_path: Path) -> None:
    result = read_lock(tmp_path / ".nimble" / "manifest.lock")
    assert result == {}


def test_read_lock_empty_skills(tmp_path: Path) -> None:
    lock_path = tmp_path / "manifest.lock"
    lock_path.write_text("skills: {}\n", encoding="utf-8")
    result = read_lock(lock_path)
    assert result == {}


def test_write_lock_entry_creates_file(tmp_path: Path) -> None:
    lock_path = tmp_path / "manifest.lock"
    write_lock_entry(
        lock_path, "log-diagnosis", "https://github.com/u/log-diagnosis", "1.0.0"
    )
    data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    assert (
        data["skills"]["log-diagnosis"]["installed_from"]
        == "https://github.com/u/log-diagnosis"
    )
    assert data["skills"]["log-diagnosis"]["version"] == "1.0.0"


def test_write_lock_entry_overwrites_existing(tmp_path: Path) -> None:
    lock_path = tmp_path / "manifest.lock"
    write_lock_entry(lock_path, "my-skill", "https://github.com/u/my-skill", "1.0.0")
    write_lock_entry(lock_path, "my-skill", "https://github.com/u/my-skill", "2.0.0")
    data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    assert data["skills"]["my-skill"]["version"] == "2.0.0"
    assert len(data["skills"]) == 1


def test_write_lock_entry_preserves_other_entries(tmp_path: Path) -> None:
    lock_path = tmp_path / "manifest.lock"
    write_lock_entry(lock_path, "skill-a", "https://github.com/u/a", "1.0.0")
    write_lock_entry(lock_path, "skill-b", "https://github.com/u/b", "2.0.0")
    write_lock_entry(lock_path, "skill-a", "https://github.com/u/a", "1.1.0")
    data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    assert data["skills"]["skill-a"]["version"] == "1.1.0"
    assert data["skills"]["skill-b"]["version"] == "2.0.0"


def test_write_lock_entry_creates_nimble_dir(tmp_path: Path) -> None:
    lock_path = tmp_path / ".nimble" / "manifest.lock"
    assert not lock_path.parent.exists()
    write_lock_entry(lock_path, "my-skill", "https://github.com/u/s", "1.0.0")
    assert lock_path.exists()
    data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    assert "my-skill" in data["skills"]


def test_remove_lock_entry_removes_named_key(tmp_path: Path) -> None:
    lock_path = tmp_path / "manifest.lock"
    write_lock_entry(lock_path, "skill-a", "https://github.com/u/a", "1.0.0")
    write_lock_entry(lock_path, "skill-b", "https://github.com/u/b", "2.0.0")
    remove_lock_entry(lock_path, "skill-a")
    data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    assert "skill-a" not in data["skills"]
    assert "skill-b" in data["skills"]


def test_remove_lock_entry_missing_key_is_noop(tmp_path: Path) -> None:
    lock_path = tmp_path / "manifest.lock"
    write_lock_entry(lock_path, "skill-b", "https://github.com/u/b", "2.0.0")
    remove_lock_entry(lock_path, "skill-a")
    data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    assert "skill-b" in data["skills"]


def test_remove_lock_entry_missing_file_is_noop(tmp_path: Path) -> None:
    lock_path = tmp_path / "manifest.lock"
    assert not lock_path.exists()
    remove_lock_entry(lock_path, "skill-a")
    assert not lock_path.exists()
