from __future__ import annotations

import signal
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from nimble.cli.commands import _collect_config_values, app
from nimble.manifest.installer import InstallError
from nimble.manifest.parser import (
    ConfigError,
    ConfigFieldSpec,
    ManifestError,
    ManifestSpec,
    NimbleConfig,
)

runner = CliRunner()


def test_start_no_existing_daemon(tmp_path: Path) -> None:
    pid_seq = [None, None, 9999]
    running_seq = [True]

    with (
        patch("nimble.cli.commands.state.read_pid", side_effect=pid_seq),
        patch("nimble.cli.commands.state.is_running", side_effect=running_seq),
        patch("nimble.cli.commands.subprocess.Popen"),
    ):
        result = runner.invoke(app, ["start"])

    assert result.exit_code == 0
    assert "9999" in result.output


def test_start_already_running() -> None:
    with (
        patch("nimble.cli.commands.state.read_pid", return_value=12345),
        patch("nimble.cli.commands.state.is_running", return_value=True),
    ):
        result = runner.invoke(app, ["start"])

    assert result.exit_code == 1
    assert "already running" in result.output


def test_start_stale_pid_cleaned_up() -> None:
    pid_seq = [99999, None, 1234]
    running_seq = [False, True]

    with (
        patch("nimble.cli.commands.state.read_pid", side_effect=pid_seq),
        patch("nimble.cli.commands.state.is_running", side_effect=running_seq),
        patch("nimble.cli.commands.state.remove_pid") as mock_remove,
        patch("nimble.cli.commands.subprocess.Popen"),
    ):
        result = runner.invoke(app, ["start"])

    mock_remove.assert_called_once()
    assert result.exit_code == 0


def test_stop_running_daemon() -> None:
    is_running_seq = [True, True, True, False]

    with (
        patch("nimble.cli.commands.state.read_pid", return_value=12345),
        patch("nimble.cli.commands.state.is_running", side_effect=is_running_seq),
        patch("os.kill") as mock_kill,
    ):
        result = runner.invoke(app, ["stop"])

    assert result.exit_code == 0
    assert "stopped" in result.output
    mock_kill.assert_called_once_with(12345, signal.SIGTERM)


def test_stop_no_daemon() -> None:
    with patch("nimble.cli.commands.state.read_pid", return_value=None):
        result = runner.invoke(app, ["stop"])

    assert result.exit_code == 1


def test_restart_calls_stop_then_start() -> None:
    with (
        patch("nimble.cli.commands.state.read_pid", return_value=1234),
        patch("nimble.cli.commands.state.is_running", return_value=True),
        patch("nimble.cli.commands._do_stop", return_value=True) as mock_stop,
        patch("nimble.cli.commands._do_start", return_value=5678) as mock_start,
    ):
        result = runner.invoke(app, ["restart"])

    assert result.exit_code == 0
    mock_stop.assert_called_once()
    mock_start.assert_called_once()
    assert "5678" in result.output


def test_restart_fails_if_stop_fails() -> None:
    with (
        patch("nimble.cli.commands.state.read_pid", return_value=1234),
        patch("nimble.cli.commands.state.is_running", return_value=True),
        patch("nimble.cli.commands._do_stop", return_value=False),
        patch("nimble.cli.commands._do_start") as mock_start,
    ):
        result = runner.invoke(app, ["restart"])

    assert result.exit_code == 1
    mock_start.assert_not_called()


def test_start_fails_if_spawn_raises() -> None:
    with (
        patch("nimble.cli.commands.state.read_pid", return_value=None),
        patch("nimble.cli.commands.subprocess.Popen", side_effect=FileNotFoundError),
    ):
        result = runner.invoke(app, ["start"])

    assert result.exit_code == 1


def test_stop_removes_pid_after_shutdown() -> None:
    is_running_seq = [True, True, False]
    with (
        patch("nimble.cli.commands.state.read_pid", return_value=12345),
        patch("nimble.cli.commands.state.is_running", side_effect=is_running_seq),
        patch("os.kill"),
        patch("nimble.cli.commands.state.remove_pid") as mock_remove,
    ):
        result = runner.invoke(app, ["stop"])

    assert result.exit_code == 0
    mock_remove.assert_called_once()


def test_validate_valid_config() -> None:
    with patch(
        "nimble.manifest.parser.load_config",
        return_value=NimbleConfig(skills=[]),
    ):
        result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "config.yaml is valid" in result.output


def test_validate_invalid_config() -> None:
    with patch(
        "nimble.manifest.parser.load_config",
        side_effect=ConfigError("config.yaml line 3: found character '\\t'"),
    ):
        result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1
    assert "line 3" in result.output


def test_validate_missing_config(tmp_path: Path) -> None:
    with patch(
        "nimble.manifest.parser.load_config",
        side_effect=FileNotFoundError,
    ):
        result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_validate_unreadable_config() -> None:
    with patch(
        "nimble.manifest.parser.load_config",
        side_effect=PermissionError("permission denied"),
    ):
        result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1
    assert "Failed to read config.yaml" in result.output


_SAMPLE_STATE = {
    "pid": 12345,
    "started_at": "2026-05-01T10:00:00+00:00",
    "daemon_version": "1.0.0",
    "skills": [
        {
            "name": "hello-world",
            "source": "local",
            "binding": "ctrl+shift+h",
            "status": "loaded",
            "worker_pid": 12346,
        }
    ],
}


def test_list_shows_skills_when_running() -> None:
    with (
        patch("nimble.cli.commands.state.read_state", return_value=_SAMPLE_STATE),
        patch("nimble.cli.commands.state.is_running", return_value=True),
    ):
        result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "hello-world" in result.output
    assert "ctrl+shift+h" in result.output
    assert "loaded" in result.output


def test_list_no_state_file() -> None:
    with patch("nimble.cli.commands.state.read_state", return_value=None):
        result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "not running" in result.output


def test_list_stale_state_file() -> None:
    with (
        patch("nimble.cli.commands.state.read_state", return_value=_SAMPLE_STATE),
        patch("nimble.cli.commands.state.is_running", return_value=False),
    ):
        result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "not running" in result.output


def test_list_malformed_pid_treated_not_running() -> None:
    data = {**_SAMPLE_STATE, "pid": "abc"}
    with patch("nimble.cli.commands.state.read_state", return_value=data):
        result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "not running" in result.output


def test_list_no_skills() -> None:
    data = {**_SAMPLE_STATE, "skills": []}
    with (
        patch("nimble.cli.commands.state.read_state", return_value=data),
        patch("nimble.cli.commands.state.is_running", return_value=True),
    ):
        result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "No skills loaded" in result.output


def test_status_shows_daemon_and_skills() -> None:
    with (
        patch("nimble.cli.commands.state.read_state", return_value=_SAMPLE_STATE),
        patch("nimble.cli.commands.state.is_running", return_value=True),
    ):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "12345" in result.output
    assert "started_at=" in result.output
    assert "daemon_version=" in result.output
    assert "1.0.0" in result.output
    assert "hello-world" in result.output


def test_status_missing_header_fields_uses_fallbacks() -> None:
    data = {"pid": 12345, "skills": []}
    with (
        patch("nimble.cli.commands.state.read_state", return_value=data),
        patch("nimble.cli.commands.state.is_running", return_value=True),
    ):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "started_at=<unknown>" in result.output
    assert "daemon_version=<unknown>" in result.output


def test_status_failed_skill_marked() -> None:
    data = {
        **_SAMPLE_STATE,
        "skills": [
            {
                "name": "hello-world",
                "source": "local",
                "binding": "ctrl+shift+h",
                "status": "failed",
                "worker_pid": 12346,
            }
        ],
    }
    with (
        patch("nimble.cli.commands.state.read_state", return_value=data),
        patch("nimble.cli.commands.state.is_running", return_value=True),
    ):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "[FAILED]" in result.output


def test_status_malformed_skill_does_not_crash() -> None:
    data = {
        **_SAMPLE_STATE,
        "skills": [123, {"name": "ok-only-name"}],
    }
    with (
        patch("nimble.cli.commands.state.read_state", return_value=data),
        patch("nimble.cli.commands.state.is_running", return_value=True),
    ):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "<invalid>" in result.output
    assert "<unknown>" in result.output


def test_status_not_running() -> None:
    with patch("nimble.cli.commands.state.read_state", return_value=None):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "not running" in result.output


def test_disable_success() -> None:
    with patch("nimble.manifest.parser.disable_skill_in_config"):
        result = runner.invoke(app, ["disable", "hello-world"])
    assert result.exit_code == 0
    assert "disabled" in result.output


def test_disable_skill_not_found() -> None:
    message = "No skill named 'hello-world' found in config.yaml"
    with patch(
        "nimble.manifest.parser.disable_skill_in_config",
        side_effect=ValueError(message),
    ):
        result = runner.invoke(app, ["disable", "hello-world"])
    assert result.exit_code == 1
    assert result.output.strip() == f"{message}"


def test_disable_write_fails() -> None:
    with patch(
        "nimble.manifest.parser.disable_skill_in_config",
        side_effect=OSError("disk full"),
    ):
        result = runner.invoke(app, ["disable", "hello-world"])
    assert result.exit_code == 1
    assert "Failed to update" in result.output


def _make_manifest_spec(**overrides: object) -> ManifestSpec:
    defaults: dict[str, object] = {
        "name": "test-skill",
        "version": "1.0.0",
        "api_version": 1,
        "description": "A test skill",
        "entrypoint": "skill.py",
        "permissions": ["ai", "clipboard"],
        "dependencies": [],
        "author": "Test Author",
        "requires": [],
        "class_name": "TestSkill",
    }
    defaults.update(overrides)
    return ManifestSpec(**defaults)  # type: ignore[arg-type]


def test_add_displays_skill_info_and_aborts_on_no() -> None:
    with patch(
        "nimble.manifest.parser.fetch_remote_manifest",
        return_value=_make_manifest_spec(),
    ):
        result = runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"], input="N\n"
        )
    assert result.exit_code == 0
    assert "test-skill" in result.output
    assert "A test skill" in result.output
    assert "Test Author" in result.output
    assert "cancelled" in result.output


def test_add_displays_permissions_with_descriptions() -> None:
    with patch(
        "nimble.manifest.parser.fetch_remote_manifest",
        return_value=_make_manifest_spec(permissions=["ai", "clipboard"]),
    ):
        result = runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"], input="N\n"
        )
    assert "ai" in result.output
    assert "external LLM" in result.output
    assert "clipboard" in result.output
    assert "clipboard content" in result.output


def test_add_unknown_permission_shows_fallback() -> None:
    with patch(
        "nimble.manifest.parser.fetch_remote_manifest",
        return_value=_make_manifest_spec(permissions=["filesystem"]),
    ):
        result = runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"], input="N\n"
        )
    assert "filesystem" in result.output
    assert "(unknown permission)" in result.output


def test_add_no_permissions_shows_none_declared() -> None:
    with patch(
        "nimble.manifest.parser.fetch_remote_manifest",
        return_value=_make_manifest_spec(permissions=[]),
    ):
        result = runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"], input="N\n"
        )
    assert "(none declared)" in result.output


def test_add_confirms_and_proceeds() -> None:
    spec = _make_manifest_spec()
    fake_root = Path("/tmp/nimble-fake-root")
    with (
        patch(
            "nimble.manifest.parser.fetch_remote_manifest",
            return_value=spec,
        ),
        patch("nimble.cli.commands._repo_root", return_value=fake_root),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv") as mock_install,
        patch("nimble.manifest.parser.append_skill_to_config"),
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        result = runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"], input="y\n"
        )
    assert result.exit_code == 0
    assert "cancelled" not in result.output
    mock_install.assert_called_once_with(spec, fake_root)


def test_add_full_word_yes_aborts() -> None:
    with (
        patch(
            "nimble.manifest.parser.fetch_remote_manifest",
            return_value=_make_manifest_spec(),
        ),
        patch("nimble.manifest.installer.install_skill_venv") as mock_install,
    ):
        result = runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"], input="yes\n"
        )
    assert result.exit_code == 0
    assert "cancelled" in result.output
    mock_install.assert_not_called()


def test_add_manifest_error_aborts() -> None:
    with patch(
        "nimble.manifest.parser.fetch_remote_manifest",
        side_effect=ManifestError("HTTP 404"),
    ):
        result = runner.invoke(app, ["add", "ctrl+shift+d", "github.com/user/missing"])
    assert result.exit_code == 1
    assert "HTTP 404" in result.output


def test_add_default_is_no() -> None:
    with patch(
        "nimble.manifest.parser.fetch_remote_manifest",
        return_value=_make_manifest_spec(),
    ):
        result = runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"], input="\n"
        )
    assert "cancelled" in result.output
    assert result.exit_code == 0


def test_add_uppercase_Y_confirms() -> None:
    spec = _make_manifest_spec()
    fake_root = Path("/tmp/nimble-fake-root")
    with (
        patch(
            "nimble.manifest.parser.fetch_remote_manifest",
            return_value=spec,
        ),
        patch("nimble.cli.commands._repo_root", return_value=fake_root),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv") as mock_install,
        patch("nimble.manifest.parser.append_skill_to_config"),
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        result = runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"], input="Y\n"
        )
    assert result.exit_code == 0
    assert "cancelled" not in result.output
    mock_install.assert_called_once_with(spec, fake_root)


def test_add_install_error_exits_with_code_1() -> None:
    with (
        patch(
            "nimble.manifest.parser.fetch_remote_manifest",
            return_value=_make_manifest_spec(),
        ),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch(
            "nimble.manifest.installer.install_skill_venv",
            side_effect=InstallError("pip failed"),
        ),
    ):
        result = runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"], input="y\n"
        )
    assert result.exit_code == 1
    assert "pip failed" in result.output


def test_add_lock_write_failure_rolls_back_config(tmp_path: Path) -> None:
    import yaml as _yaml

    spec = _make_manifest_spec()
    cfg = tmp_path / "config.yaml"
    cfg.write_text("skills: []\n", encoding="utf-8")
    with (
        patch(
            "nimble.manifest.parser.fetch_remote_manifest",
            return_value=spec,
        ),
        patch("nimble.cli.commands._repo_root", return_value=tmp_path),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv"),
        patch(
            "nimble.manifest.lock.write_lock_entry",
            side_effect=OSError("disk full"),
        ),
    ):
        result = runner.invoke(
            app, ["add", "ctrl+shift+d", "github.com/user/skill"], input="y\n"
        )
    assert result.exit_code == 1
    assert "manifest.lock" in result.output
    assert "removed from config.yaml" in result.output
    data = _yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert data["skills"] == []


def _make_manifest_spec_with_fields(**overrides: object) -> ManifestSpec:
    fields = [
        ConfigFieldSpec(
            key="target_language",
            description="Target language code",
            default="en",
            possible_values=["en", "es", "fr"],
        )
    ]
    return _make_manifest_spec(config_fields=fields, **overrides)


def test_add_prompts_config_fields_after_confirmation() -> None:
    spec = _make_manifest_spec_with_fields()
    fake_root = Path("/tmp/nimble-fake-root")
    with (
        patch("nimble.manifest.parser.fetch_remote_manifest", return_value=spec),
        patch("nimble.cli.commands._repo_root", return_value=fake_root),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv"),
        patch("nimble.manifest.parser.append_skill_to_config"),
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        result = runner.invoke(
            app,
            ["add", "ctrl+shift+d", "github.com/user/skill"],
            input="y\nes\n",
        )
    assert "target_language" in result.output
    assert "Target language code" in result.output
    assert "[en/es/fr]" in result.output
    assert "(default: 'en')" in result.output


def test_add_config_field_enter_uses_default() -> None:
    spec = _make_manifest_spec_with_fields()
    fake_root = Path("/tmp/nimble-fake-root")
    with (
        patch("nimble.manifest.parser.fetch_remote_manifest", return_value=spec),
        patch("nimble.cli.commands._repo_root", return_value=fake_root),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv"),
        patch("nimble.manifest.parser.append_skill_to_config") as mock_append,
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        result = runner.invoke(
            app,
            ["add", "ctrl+shift+d", "github.com/user/skill"],
            input="y\n\n",
        )
    assert result.exit_code == 0
    assert mock_append.called
    call_args = mock_append.call_args
    configuration = (
        call_args.args[5]
        if len(call_args.args) > 5
        else call_args.kwargs.get("configuration")
    )
    assert configuration == {"target_language": "en"}


def test_add_config_field_invalid_value_reprompts() -> None:
    spec = _make_manifest_spec_with_fields()
    fake_root = Path("/tmp/nimble-fake-root")
    with (
        patch("nimble.manifest.parser.fetch_remote_manifest", return_value=spec),
        patch("nimble.cli.commands._repo_root", return_value=fake_root),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv"),
        patch("nimble.manifest.parser.append_skill_to_config"),
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        result = runner.invoke(
            app,
            ["add", "ctrl+shift+d", "github.com/user/skill"],
            input="y\nzh\nes\n",
        )
    assert "Invalid value" in result.output
    assert result.exit_code == 0


def test_add_config_field_required_no_default_reprompts() -> None:
    fields = [ConfigFieldSpec(key="api_key", description="API key")]
    spec = _make_manifest_spec(config_fields=fields)
    fake_root = Path("/tmp/nimble-fake-root")
    with (
        patch("nimble.manifest.parser.fetch_remote_manifest", return_value=spec),
        patch("nimble.cli.commands._repo_root", return_value=fake_root),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv"),
        patch("nimble.manifest.parser.append_skill_to_config"),
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        result = runner.invoke(
            app,
            ["add", "ctrl+shift+d", "github.com/user/skill"],
            input="y\n\nsecret\n",
        )
    assert "'api_key' is required." in result.output
    assert result.exit_code == 0


def test_add_empty_config_fields_no_prompts() -> None:
    spec = _make_manifest_spec(config_fields=[])
    fake_root = Path("/tmp/nimble-fake-root")
    with (
        patch("nimble.manifest.parser.fetch_remote_manifest", return_value=spec),
        patch("nimble.cli.commands._repo_root", return_value=fake_root),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv"),
        patch("nimble.manifest.parser.append_skill_to_config") as mock_append,
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        result = runner.invoke(
            app,
            ["add", "ctrl+shift+d", "github.com/user/skill"],
            input="y\n",
        )
    assert result.exit_code == 0
    call_args = mock_append.call_args
    configuration = (
        call_args.args[5]
        if len(call_args.args) > 5
        else call_args.kwargs.get("configuration", {})
    )
    assert configuration == {}


def test_add_passes_configuration_to_append_skill_to_config() -> None:
    spec = _make_manifest_spec_with_fields()
    fake_root = Path("/tmp/nimble-fake-root")
    with (
        patch("nimble.manifest.parser.fetch_remote_manifest", return_value=spec),
        patch("nimble.cli.commands._repo_root", return_value=fake_root),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv"),
        patch("nimble.manifest.parser.append_skill_to_config") as mock_append,
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        runner.invoke(
            app,
            ["add", "ctrl+shift+d", "github.com/user/skill"],
            input="y\nes\n",
        )
    call_args = mock_append.call_args
    configuration = (
        call_args.args[5]
        if len(call_args.args) > 5
        else call_args.kwargs.get("configuration")
    )
    assert configuration == {"target_language": "es"}


def test_add_config_field_eof_exits_nonzero() -> None:
    fields = [ConfigFieldSpec(key="api_key", description="API key")]
    spec = _make_manifest_spec(config_fields=fields)
    fake_root = Path("/tmp/nimble-fake-root")
    with (
        patch("nimble.manifest.parser.fetch_remote_manifest", return_value=spec),
        patch("nimble.cli.commands._repo_root", return_value=fake_root),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv"),
        patch("nimble.manifest.parser.append_skill_to_config") as mock_append,
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        result = runner.invoke(
            app,
            ["add", "ctrl+shift+d", "github.com/user/skill"],
            input="y\n",
        )
    assert result.exit_code == 1
    assert "Input stream closed while reading 'api_key'." in result.output
    mock_append.assert_not_called()


def test_add_config_field_read_error_exits_nonzero() -> None:
    fields = [ConfigFieldSpec(key="api_key", description="API key")]
    with (
        patch(
            "nimble.cli.commands.sys.stdin.readline",
            side_effect=OSError("stdin failed"),
        ),
        patch("nimble.cli.commands.typer.echo") as mock_echo,
    ):
        try:
            _collect_config_values(fields)
        except Exception as exc:  # click.exceptions.Exit
            assert exc.__class__.__name__ == "Exit"
            assert getattr(exc, "exit_code", None) == 1
        else:
            raise AssertionError("expected click Exit")
    mock_echo.assert_any_call("Failed to read input for 'api_key'.", err=True)


def test_add_config_field_trims_allowed_value_whitespace() -> None:
    spec = _make_manifest_spec_with_fields()
    fake_root = Path("/tmp/nimble-fake-root")
    with (
        patch("nimble.manifest.parser.fetch_remote_manifest", return_value=spec),
        patch("nimble.cli.commands._repo_root", return_value=fake_root),
        patch("nimble.manifest.installer.clone_skill_repo"),
        patch("nimble.manifest.installer.install_skill_venv"),
        patch("nimble.manifest.parser.append_skill_to_config") as mock_append,
        patch("nimble.manifest.lock.write_lock_entry"),
    ):
        result = runner.invoke(
            app,
            ["add", "ctrl+shift+d", "github.com/user/skill"],
            input="y\n es \n",
        )
    assert result.exit_code == 0
    call_args = mock_append.call_args
    configuration = (
        call_args.args[5]
        if len(call_args.args) > 5
        else call_args.kwargs.get("configuration")
    )
    assert configuration == {"target_language": "es"}


def test_remove_happy_path(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".nimble" / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    with (
        patch("nimble.cli.commands._repo_root", return_value=tmp_path),
        patch("nimble.manifest.parser.remove_skill_from_config"),
        patch("nimble.manifest.lock.remove_lock_entry"),
        patch("nimble.cli.commands.state.read_pid", return_value=None),
    ):
        result = runner.invoke(app, ["remove", "my-skill"], input="y\n")
    assert result.exit_code == 0
    assert "removed" in result.output
    assert not skill_dir.exists()


def test_remove_confirmation_declined(tmp_path: Path) -> None:
    with (
        patch("nimble.cli.commands._repo_root", return_value=tmp_path),
        patch(
            "nimble.manifest.parser.remove_skill_from_config"
        ) as mock_rm,
    ):
        result = runner.invoke(app, ["remove", "my-skill"], input="n\n")
    assert result.exit_code == 0
    assert "cancelled" in result.output
    mock_rm.assert_not_called()


def test_remove_confirmation_empty_declines(tmp_path: Path) -> None:
    with (
        patch("nimble.cli.commands._repo_root", return_value=tmp_path),
        patch(
            "nimble.manifest.parser.remove_skill_from_config"
        ) as mock_rm,
    ):
        result = runner.invoke(app, ["remove", "my-skill"], input="\n")
    assert result.exit_code == 0
    assert "cancelled" in result.output
    mock_rm.assert_not_called()


def test_remove_skill_not_in_config(tmp_path: Path) -> None:
    with (
        patch("nimble.cli.commands._repo_root", return_value=tmp_path),
        patch(
            "nimble.manifest.parser.remove_skill_from_config",
            side_effect=ConfigError("Skill 'my-skill' not found in config.yaml"),
        ),
    ):
        result = runner.invoke(app, ["remove", "my-skill"], input="y\n")
    assert result.exit_code == 1
    assert "not found" in result.output


def test_remove_dir_absent_warns_and_succeeds(tmp_path: Path) -> None:
    with (
        patch("nimble.cli.commands._repo_root", return_value=tmp_path),
        patch("nimble.manifest.parser.remove_skill_from_config"),
        patch("nimble.manifest.lock.remove_lock_entry"),
        patch("nimble.cli.commands.state.read_pid", return_value=None),
    ):
        result = runner.invoke(app, ["remove", "my-skill"], input="y\n")
    assert result.exit_code == 0
    assert "directory not found" in result.output
    assert "removed" in result.output


def test_remove_lock_oserror_warns_but_succeeds(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".nimble" / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    with (
        patch("nimble.cli.commands._repo_root", return_value=tmp_path),
        patch("nimble.manifest.parser.remove_skill_from_config"),
        patch(
            "nimble.manifest.lock.remove_lock_entry",
            side_effect=OSError("disk full"),
        ),
        patch("nimble.cli.commands.state.read_pid", return_value=None),
    ):
        result = runner.invoke(app, ["remove", "my-skill"], input="y\n")
    assert result.exit_code == 0
    assert "manifest.lock" in result.output
    assert "removed" in result.output


def test_remove_daemon_running_shows_restart_hint(tmp_path: Path) -> None:
    with (
        patch("nimble.cli.commands._repo_root", return_value=tmp_path),
        patch("nimble.manifest.parser.remove_skill_from_config"),
        patch("nimble.manifest.lock.remove_lock_entry"),
        patch("nimble.cli.commands.state.read_pid", return_value=12345),
        patch("nimble.cli.commands.state.is_running", return_value=True),
    ):
        result = runner.invoke(app, ["remove", "my-skill"], input="y\n")
    assert result.exit_code == 0
    assert "restart" in result.output


def test_terminate_windows_openprocess_failure_raises() -> None:
    fake_kernel32 = MagicMock()
    fake_kernel32.OpenProcess.return_value = 0
    fake_ctypes = MagicMock(windll=MagicMock(kernel32=fake_kernel32))

    with patch.dict("sys.modules", {"ctypes": fake_ctypes}):
        try:
            from nimble.cli.commands import _terminate_windows

            _terminate_windows(1)
        except OSError:
            pass
        else:
            raise AssertionError("expected OSError")
