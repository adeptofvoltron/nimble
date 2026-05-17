---
title: 'Fix hotkey adapter routing: prefer X11 when DISPLAY is set'
type: 'bugfix'
created: '2026-05-12'
status: 'done'
route: 'one-shot'
---

## Intent

**Problem:** On Wayland sessions with XWayland running (both `WAYLAND_DISPLAY` and `DISPLAY` set), `get_adapter()` routed to `EvdevAdapter`, which requires the user to be in the `input` group. Users not in that group got a silent empty device list and a startup failure.

**Approach:** Prioritise `DISPLAY` in the routing decision. When `DISPLAY` is set (X11 or XWayland), use `X11HotkeyAdapter` (pynput). Fall back to `EvdevAdapter` only for pure Wayland (no `DISPLAY`) or headless sessions.

## Suggested Review Order

- [`nimble/hotkeys/__init__.py`](../../nimble/hotkeys/__init__.py) — routing condition, the core change
- [`tests/unit/hotkeys/test_factory.py:25`](../../tests/unit/hotkeys/test_factory.py) — renamed + updated XWayland test assertion
