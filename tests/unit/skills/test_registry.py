from unittest.mock import MagicMock

from nimble.skills.registry import SkillConfig, SkillRegistry, SkillWorker


def _make_config(name: str = "my-skill") -> SkillConfig:
    return SkillConfig(
        name=name,
        source="local",
        binding="ctrl+shift+a",
        path="/path/to/skill.py",
        class_name="MySkill",
    )


def _make_worker(name: str = "my-skill") -> SkillWorker:
    proc = MagicMock()
    proc.poll.return_value = None
    return SkillWorker(
        config=_make_config(name),
        process=proc,
        status="loaded",
        python_executable="/usr/bin/python3",
    )


def test_register_and_get() -> None:
    registry = SkillRegistry()
    worker = _make_worker()
    registry.register(worker)
    assert registry.get("my-skill") is worker


def test_get_unknown_returns_none() -> None:
    registry = SkillRegistry()
    assert registry.get("nonexistent") is None


def test_all_returns_all_registered() -> None:
    registry = SkillRegistry()
    registry.register(_make_worker("skill-a"))
    registry.register(_make_worker("skill-b"))
    assert len(registry.all()) == 2


def test_disable_sets_status_failed() -> None:
    registry = SkillRegistry()
    worker = _make_worker()
    registry.register(worker)
    registry.disable("my-skill")
    assert registry.get("my-skill").status == "failed"  # type: ignore[union-attr]


def test_disable_unknown_does_not_raise() -> None:
    registry = SkillRegistry()
    registry.disable("nonexistent")  # should not raise
