from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from nimble.manifest.parser import ConfigFieldSpec

import nimble.state as state
from nimble.platform import is_windows

app = typer.Typer(help="Nimble — cross-platform Python hotkey daemon.")


_PERMISSION_DESCRIPTIONS: dict[str, str] = {
    "ai": "may send text to an external LLM API",
    "clipboard": "reads clipboard content at hotkey-fire time",
    "popup": "displays a system notification popup",
    "tts": "speaks text aloud via the system TTS engine",
    "input": "prompts the user for text input or a selection dialog",
}


def _prompt_install_confirm_y_only() -> bool:
    """Return True only if the user enters exactly ``y`` or ``Y`` (AC3)."""
    typer.echo("Install anyway? [y/N]: ", nl=False)
    try:
        line = sys.stdin.readline()
    except (OSError, UnicodeDecodeError):
        return False
    return line.rstrip("\r\n") in ("y", "Y")


def _collect_config_values(
    config_fields: list[ConfigFieldSpec],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for cf in config_fields:
        while True:
            if cf.possible_values:
                choices = "/".join(cf.possible_values)
                prompt = f"{cf.key} — {cf.description} [{choices}]"
            else:
                prompt = f"{cf.key} — {cf.description}"
            if cf.default is not None:
                prompt += f" (default: '{cf.default}')"
            prompt += ": "
            typer.echo(prompt, nl=False)
            try:
                raw = sys.stdin.readline()
            except (OSError, UnicodeDecodeError):
                typer.echo(
                    f"Failed to read input for '{cf.key}'.",
                    err=True,
                )
                raise typer.Exit(1)
            if raw == "":
                typer.echo(
                    f"Input stream closed while reading '{cf.key}'.",
                    err=True,
                )
                raise typer.Exit(1)
            value = raw.rstrip("\r\n").strip()
            if value == "":
                if cf.default is not None:
                    result[cf.key] = cf.default
                    break
                typer.echo(f"'{cf.key}' is required.")
                continue
            if cf.possible_values and value not in cf.possible_values:
                joined = ", ".join(cf.possible_values)
                typer.echo(f"Invalid value. Choose from: {joined}")
                continue
            result[cf.key] = value
            break
    return result


def _running_pid_or_none(data: object) -> int | None:
    if not isinstance(data, dict):
        return None
    raw_pid = data.get("pid")

    if raw_pid is None:
        return None

    try:
        pid = int(raw_pid)
    except (TypeError, ValueError):
        return None
    if pid <= 0 or not state.is_running(pid):
        return None
    return pid


def _skill_columns(
    skill: object, failed_marker: bool = False
) -> tuple[str, str, str, str]:
    if not isinstance(skill, dict):
        return ("<invalid>", "<invalid>", "<invalid>", "<invalid>")

    name = str(skill.get("name", "<unknown>"))
    source = str(skill.get("source", "<unknown>"))
    binding = str(skill.get("binding", "<unknown>"))
    status = str(skill.get("status", "<unknown>"))
    if failed_marker and status == "failed":
        status = "[FAILED]"
    return (name, source, binding, status)


def _repo_root() -> Path:
    # commands.py lives at nimble/cli/commands.py — 3 levels below repo root
    return Path(__file__).resolve().parent.parent.parent


def _terminate_windows(pid: int) -> None:
    import ctypes

    PROCESS_TERMINATE = 0x0001
    handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
        PROCESS_TERMINATE, False, pid
    )
    if handle == 0:
        raise OSError(f"Unable to open process {pid} for termination")
    ctypes.windll.kernel32.TerminateProcess(handle, 0)  # type: ignore[attr-defined]
    ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]


def _do_stop() -> bool:
    pid = state.read_pid()
    if pid is None or not state.is_running(pid):
        return False

    if is_windows():
        try:
            _terminate_windows(pid)
        except OSError as exc:
            typer.echo(f"Nimble failed to stop process {pid}: {exc}", err=True)
            return False
    else:
        import os

        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            state.remove_pid()
            return True
        except PermissionError:
            typer.echo(
                f"Nimble failed to stop process {pid}: permission denied", err=True
            )
            return False

    for _ in range(100):
        time.sleep(0.1)
        if not state.is_running(pid):
            state.remove_pid()
            return True

    typer.echo("Nimble did not stop in time", err=True)
    return False


def _do_start(repo_root: Path, debug: bool) -> int | None:
    config_path = repo_root / "config.yaml"
    if not config_path.exists():
        import yaml

        from nimble.manifest.parser import atomic_write

        try:
            atomic_write(
                config_path,
                yaml.dump(
                    {"skills": []}, default_flow_style=False, allow_unicode=True
                ),
            )
        except OSError as exc:
            typer.echo(f"Failed to create config.yaml: {exc}", err=True)
            raise typer.Exit(1)
        typer.echo("config.yaml not found — created a new one.")

    nimble_bin = Path(sys.executable).parent / (
        "nimble.exe" if is_windows() else "nimble"
    )
    try:
        subprocess.Popen(
            [str(nimble_bin), "_run", str(repo_root), *(["--debug"] if debug else [])],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=(not is_windows()),
        )
    except (FileNotFoundError, PermissionError, OSError) as exc:
        typer.echo(f"Nimble failed to launch daemon: {exc}", err=True)
        return None

    for _ in range(50):
        time.sleep(0.1)
        new_pid = state.read_pid()
        if new_pid is not None and state.is_running(new_pid):
            return new_pid

    return None


@app.command(name="_run", hidden=True)
def _run(
    repo_root: Path = typer.Argument(...),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    from nimble.daemon import run

    run(repo_root=repo_root, debug=debug)


@app.command()
def start(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Start the Nimble daemon."""
    repo_root = _repo_root()

    pid = state.read_pid()
    if pid is not None:
        if state.is_running(pid):
            typer.echo("Nimble is already running", err=True)
            raise typer.Exit(1)
        else:
            import logging

            logging.getLogger(__name__).warning("Stale PID file found, removing")
            state.remove_pid()

    new_pid = _do_start(repo_root, debug)
    if new_pid is None:
        typer.echo("Nimble failed to start (timeout waiting for PID file)", err=True)
        raise typer.Exit(1)

    typer.echo(f"Nimble started (PID {new_pid})")


@app.command()
def stop() -> None:
    """Stop the Nimble daemon."""
    pid = state.read_pid()
    if pid is None or not state.is_running(pid):
        typer.echo("Nimble is not running", err=True)
        raise typer.Exit(1)

    stopped = _do_stop()
    if stopped:
        typer.echo("Nimble stopped")
    else:
        raise typer.Exit(1)


@app.command()
def restart(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Restart the Nimble daemon."""
    repo_root = _repo_root()
    pid = state.read_pid()
    if pid is not None and state.is_running(pid):
        if not _do_stop():
            typer.echo("Nimble failed to stop for restart", err=True)
            raise typer.Exit(1)
    elif pid is not None:
        state.remove_pid()

    new_pid = _do_start(repo_root, debug)
    if new_pid is None:
        typer.echo("Nimble failed to start after restart", err=True)
        raise typer.Exit(1)
    typer.echo(f"Nimble restarted (PID {new_pid})")


@app.command()
def validate() -> None:
    """Validate config.yaml without starting the daemon."""
    from nimble.manifest.parser import ConfigError, load_config

    config_path = _repo_root() / "config.yaml"
    try:
        load_config(config_path)
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    except FileNotFoundError:
        typer.echo(f"config.yaml not found at {config_path}", err=True)
        raise typer.Exit(1)
    except OSError as exc:
        typer.echo(f"Failed to read config.yaml: {exc}", err=True)
        raise typer.Exit(1)
    typer.echo("config.yaml is valid")


@app.command()
def disable(
    skill_name: str = typer.Argument(
        ..., help="Name of the skill to disable during current runtime"
    ),
) -> None:
    """Disable a skill without editing config.yaml manually."""
    from nimble.manifest.parser import disable_skill_in_config

    config_path = _repo_root() / "config.yaml"
    try:
        disable_skill_in_config(config_path, skill_name)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    except OSError as exc:
        typer.echo(f"Failed to update config.yaml: {exc}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Skill '{skill_name}' disabled")


@app.command(name="list")
def list_skills() -> None:
    """List all configured skills and their status."""
    data = state.read_state()
    if data is None or _running_pid_or_none(data) is None:
        typer.echo("Nimble daemon is not running")
        return

    raw_skills = data.get("skills", [])
    skills = raw_skills if isinstance(raw_skills, list) else []
    if len(skills) == 0:
        typer.echo("No skills loaded")
        return

    for skill in skills:
        name, source, binding, status = _skill_columns(skill)
        typer.echo(f"{name:<20} {source:<12}" f" {binding:<20} {status}")


@app.command()
def status() -> None:
    """Show daemon health and per-skill status."""
    data = state.read_state()
    pid = None if data is None else _running_pid_or_none(data)
    if data is None or pid is None:
        typer.echo("Nimble daemon is not running")
        return

    started_at = str(data.get("started_at", "<unknown>"))
    daemon_version = str(data.get("daemon_version", "<unknown>"))
    typer.echo(
        f"Daemon: pid={pid}  started_at={started_at}"
        f"  daemon_version={daemon_version}"
    )
    typer.echo("")
    typer.echo("Skills:")

    raw_skills = data.get("skills", [])
    skills = raw_skills if isinstance(raw_skills, list) else []
    for skill in skills:
        name, source, binding, status_display = _skill_columns(
            skill, failed_marker=True
        )
        typer.echo(f"  {name:<20} {source:<12}" f" {binding:<20} {status_display}")


@app.command()
def add(
    shortcut: str = typer.Argument(
        ..., help="Keyboard shortcut to bind (e.g. ctrl+shift+d)"
    ),
    repo_url: str = typer.Argument(..., help="GitHub repository URL of the skill"),
) -> None:
    """Install a community skill from a GitHub repository."""
    from nimble.manifest.parser import ManifestError, fetch_remote_manifest

    try:
        spec = fetch_remote_manifest(repo_url)
    except ManifestError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)

    typer.echo(f"Skill:       {spec.name}")
    typer.echo(f"Description: {spec.description}")
    typer.echo(f"Author:      {spec.author}")
    typer.echo("")
    typer.echo("Permissions:")
    if spec.permissions:
        for perm in spec.permissions:
            desc = _PERMISSION_DESCRIPTIONS.get(perm, "(unknown permission)")
            typer.echo(f"  - {perm:<12} ({desc})")
    else:
        typer.echo("  (none declared)")
    typer.echo("")

    if not _prompt_install_confirm_y_only():
        typer.echo("Installation cancelled.")
        raise typer.Exit(0)

    configuration = _collect_config_values(spec.config_fields)

    import shutil

    from nimble.manifest.installer import (
        InstallError,
        clone_skill_repo,
        install_skill_venv,
    )
    from nimble.manifest.lock import write_lock_entry
    from nimble.manifest.parser import (
        ConfigError,
        append_skill_to_config,
        remove_skill_entry_from_config,
    )

    typer.echo(f"Installing '{spec.name}'...")
    repo_root = _repo_root()
    skill_dir = repo_root / ".nimble" / "skills" / spec.name

    try:
        clone_skill_repo(repo_url, skill_dir)
    except InstallError as exc:
        shutil.rmtree(skill_dir, ignore_errors=True)
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)

    try:
        install_skill_venv(spec, repo_root)
    except InstallError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)

    config_path = repo_root / "config.yaml"
    config_is_new = not config_path.exists()
    try:
        append_skill_to_config(
            config_path, spec, shortcut, repo_url, repo_root, configuration
        )
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)

    lock_path = repo_root / ".nimble" / "manifest.lock"
    try:
        write_lock_entry(lock_path, spec.name, repo_url, spec.version)
    except Exception as exc:
        try:
            remove_skill_entry_from_config(config_path, spec.name)
        except ConfigError as rb_exc:
            typer.echo(
                f"Failed to update manifest.lock ({exc}). "
                f"Could not roll back config.yaml: {rb_exc}",
                err=True,
            )
            raise typer.Exit(1)
        typer.echo(
            f"Failed to update manifest.lock ({exc}). "
            "The new skill entry was removed from config.yaml.",
            err=True,
        )
        raise typer.Exit(1)

    if config_is_new:
        typer.echo("config.yaml not found — created a new one.")
    typer.echo(f"Skill '{spec.name}' installed and bound to {shortcut}.")


@app.command()
def remove(
    skill_name: str = typer.Argument(..., help="Name of the skill to remove"),
) -> None:
    """Remove a skill installed via nimble add."""
    from nimble.manifest.lock import remove_lock_entry
    from nimble.manifest.parser import ConfigError, remove_skill_from_config

    typer.echo(f"Remove skill '{skill_name}'? [y/N]: ", nl=False)
    try:
        line = sys.stdin.readline()
    except (OSError, UnicodeDecodeError):
        typer.echo("Removal cancelled.")
        raise typer.Exit(0)
    if line.rstrip("\r\n") not in ("y", "Y"):
        typer.echo("Removal cancelled.")
        raise typer.Exit(0)

    repo_root = _repo_root()
    config_path = repo_root / "config.yaml"
    lock_path = repo_root / ".nimble" / "manifest.lock"
    skill_dir = repo_root / ".nimble" / "skills" / skill_name

    try:
        remove_skill_from_config(config_path, skill_name)
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    except OSError as exc:
        typer.echo(f"Failed to update config.yaml: {exc}", err=True)
        raise typer.Exit(1)

    try:
        remove_lock_entry(lock_path, skill_name)
    except OSError as exc:
        typer.echo(f"Warning: failed to update manifest.lock: {exc}", err=True)

    if skill_dir.exists():
        import shutil

        try:
            shutil.rmtree(skill_dir)
        except OSError as exc:
            typer.echo(f"Warning: failed to delete skill directory: {exc}", err=True)
    else:
        typer.echo("Skill directory not found — skipping.")

    typer.echo(f"Skill '{skill_name}' removed.")

    pid = state.read_pid()
    if pid is not None and state.is_running(pid):
        typer.echo(
            "Nimble is running — restart with 'nimble restart' to apply changes."
        )


if __name__ == "__main__":
    app()
