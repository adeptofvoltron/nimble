from __future__ import annotations

import logging
import os
import select
import threading
from collections.abc import Callable
from typing import Any

from nimble.hotkeys.base import HotkeyAdapter, _MODIFIERS

logger = logging.getLogger(__name__)


def _evdev() -> Any:
    import evdev
    return evdev


def _build_modifier_map() -> dict[int, str]:
    ec = _evdev().ecodes
    return {
        ec.KEY_LEFTCTRL: "ctrl", ec.KEY_RIGHTCTRL: "ctrl",
        ec.KEY_LEFTSHIFT: "shift", ec.KEY_RIGHTSHIFT: "shift",
        ec.KEY_LEFTALT: "alt", ec.KEY_RIGHTALT: "alt",
        ec.KEY_LEFTMETA: "super", ec.KEY_RIGHTMETA: "super",
    }


def _shortcut_token_to_ecode(token: str) -> int:
    ec = _evdev().ecodes
    if len(token) == 1 and token.isalpha():
        name = f"KEY_{token.upper()}"
        if name in ec.ecodes:
            return ec.ecodes[name]
    if len(token) == 1 and token.isdigit():
        name = f"KEY_{token}"
        if name in ec.ecodes:
            return ec.ecodes[name]
    if token.startswith("f") and token[1:].isdigit():
        name = f"KEY_{token.upper()}"
        if name in ec.ecodes:
            return ec.ecodes[name]
    _special = {
        "space": "KEY_SPACE", "enter": "KEY_ENTER", "return": "KEY_ENTER",
        "backspace": "KEY_BACKSPACE", "tab": "KEY_TAB", "esc": "KEY_ESC",
        "escape": "KEY_ESC", "delete": "KEY_DELETE", "del": "KEY_DELETE",
        "insert": "KEY_INSERT", "home": "KEY_HOME", "end": "KEY_END",
        "pageup": "KEY_PAGEUP", "pagedown": "KEY_PAGEDOWN",
        "up": "KEY_UP", "down": "KEY_DOWN", "left": "KEY_LEFT", "right": "KEY_RIGHT",
        "minus": "KEY_MINUS", "equal": "KEY_EQUAL", "semicolon": "KEY_SEMICOLON",
        "comma": "KEY_COMMA", "dot": "KEY_DOT", "period": "KEY_DOT", "slash": "KEY_SLASH",
    }
    if token in _special:
        name = _special[token]
        if name in ec.ecodes:
            return ec.ecodes[name]
    raise ValueError(f"Cannot map shortcut token {token!r} to an evdev key code.")


def _parse_shortcut(shortcut: str) -> tuple[frozenset[str], int]:
    parts = shortcut.lower().split("+")
    mods = frozenset(p for p in parts if p in _MODIFIERS)
    non_mods = [p for p in parts if p not in _MODIFIERS]
    if len(non_mods) != 1:
        raise ValueError(
            f"Shortcut {shortcut!r} must have exactly one non-modifier key."
        )
    return mods, _shortcut_token_to_ecode(non_mods[0])


class EvdevAdapter(HotkeyAdapter):
    def __init__(self) -> None:
        self._hotkeys: dict[str, tuple[frozenset[str], int, Callable[[], None]]] = {}
        self._thread: threading.Thread | None = None
        self._pipe_r: int | None = None
        self._pipe_w: int | None = None
        self._current_modifiers: set[str] = set()
        self._lock = threading.Lock()

    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        if shortcut in self._hotkeys:
            raise ValueError(f"Hotkey already registered: {shortcut!r}")
        mods, trigger_ecode = _parse_shortcut(shortcut)
        self._hotkeys[shortcut] = (mods, trigger_ecode, callback)

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("EvdevAdapter is already started; call stop() first.")
        evdev = _evdev()
        devices = self._open_keyboard_devices(evdev)
        if not devices:
            raise RuntimeError("No keyboard devices found in /dev/input/.")
        self._pipe_r, self._pipe_w = os.pipe()
        self._current_modifiers = set()
        modifier_map = _build_modifier_map()
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(devices, modifier_map),
            daemon=True,
            name="nimble-evdev-loop",
        )
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        if self._pipe_w is not None:
            try:
                os.write(self._pipe_w, b"\x00")
            except OSError:
                pass
        self._thread.join()
        self._thread = None
        for fd in (self._pipe_r, self._pipe_w):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        self._pipe_r = None
        self._pipe_w = None

    def _open_keyboard_devices(self, evdev: Any) -> list[Any]:
        paths = evdev.list_devices()
        if not paths:
            return []
        devices: list[Any] = []
        for path in paths:
            try:
                dev = evdev.InputDevice(path)
            except PermissionError:
                raise RuntimeError(
                    f"Permission denied opening {path}. "
                    "Add your user to the 'input' group and log out/in:\n"
                    "    sudo usermod -aG input $USER\n"
                    "Then log out and log back in (or reboot)."
                ) from None
            except OSError as exc:
                logger.debug("Skipping %s: %s", path, exc)
                continue
            caps = dev.capabilities()
            if evdev.ecodes.EV_KEY in caps:
                devices.append(dev)
            else:
                dev.close()
        return devices

    def _run_loop(self, devices: list[Any], modifier_map: dict[int, str]) -> None:
        evdev = _evdev()
        EV_KEY = evdev.ecodes.EV_KEY
        KEY_DOWN = evdev.events.KeyEvent.key_down
        KEY_UP = evdev.events.KeyEvent.key_up
        pipe_r = self._pipe_r
        fds = {dev.fd: dev for dev in devices}
        all_fds = list(fds.keys()) + [pipe_r]
        try:
            while True:
                try:
                    readable, _, _ = select.select(all_fds, [], [])
                except (ValueError, OSError):
                    break
                for fd in readable:
                    if fd == pipe_r:
                        return
                    dev = fds[fd]
                    try:
                        for event in dev.read():
                            if event.type != EV_KEY:
                                continue
                            code = event.code
                            value = event.value
                            if code in modifier_map:
                                mod = modifier_map[code]
                                with self._lock:
                                    if value == KEY_DOWN:
                                        self._current_modifiers.add(mod)
                                    elif value == KEY_UP:
                                        self._current_modifiers.discard(mod)
                            elif value == KEY_DOWN:
                                with self._lock:
                                    active_mods = frozenset(self._current_modifiers)
                                for _shortcut, (req_mods, trigger_ecode, cb) in self._hotkeys.items():
                                    if code == trigger_ecode and active_mods == req_mods:
                                        threading.Thread(
                                            target=cb,
                                            daemon=True,
                                            name=f"nimble-hotkey-{_shortcut}",
                                        ).start()
                    except BlockingIOError:
                        pass
                    except OSError as exc:
                        logger.warning("Error reading from %s: %s", dev.path, exc)
                        all_fds.remove(fd)
                        del fds[fd]
                        if not fds:
                            return
        finally:
            for dev in devices:
                try:
                    dev.close()
                except OSError:
                    pass
