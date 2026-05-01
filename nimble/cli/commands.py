from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path

import typer

import nimble.state as state
from nimble.platform import is_windows

app = typer.Typer(help="Nimble — cross-platform Python hotkey daemon.")


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


if __name__ == "__main__":
    app()
