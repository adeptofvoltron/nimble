# WaylandXWaylandAdapter Design

**Goal:** Make Nimble's global hotkeys work out-of-the-box on Ubuntu Wayland (with XWayland) without any extra user setup or permissions.

**Problem:** On a Wayland session with XWayland, pynput's X11 RECORD extension only sees keyboard events when at least one X11 window is active. With no X11 app focused, physical keypresses never flow through XWayland's X11 event queue and pynput hears nothing.

**Solution:** At daemon startup, create an invisible `InputOnly` X11 window that keeps XWayland's X11 routing active. This is enough for pynput to capture all global keypresses regardless of which Wayland app has focus.

---

## Architecture

One new file, two small edits:

```
nimble/hotkeys/
    __init__.py   ← update factory detection (5 lines)
    base.py       ← unchanged
    x11.py        ← unchanged
    wayland.py    ← NEW: WaylandXWaylandAdapter
    windows.py    ← unchanged

tests/unit/hotkeys/
    test_factory.py   ← add 2 new factory cases
    test_wayland.py   ← NEW: WaylandXWaylandAdapter unit tests
```

## Components

### `nimble/hotkeys/wayland.py` — WaylandXWaylandAdapter

Extends `X11HotkeyAdapter`. Inherits `register()` and all pynput GlobalHotKeys logic unchanged.

Overrides:

**`start()`**
1. Open an Xlib connection to `DISPLAY`
2. Create a 1×1 `InputOnly` window on the root, map it
3. Flush the connection
4. Call `super().start()` (pynput listener)

**`stop()`**
1. Call `super().stop()` (pynput listener teardown)
2. Destroy the window
3. Close the Xlib connection

The window uses `X.InputOnly` window class — no visual pixels, no decorations, invisible to the user. Its sole purpose is keeping XWayland's X11 event routing active.

### `nimble/hotkeys/__init__.py` — factory update

| Environment | Adapter selected |
|---|---|
| `DISPLAY` set, `WAYLAND_DISPLAY` absent | `X11HotkeyAdapter` |
| `DISPLAY` set, `WAYLAND_DISPLAY` set | `WaylandXWaylandAdapter` |
| `WAYLAND_DISPLAY` set, `DISPLAY` absent | `RuntimeError` — pure Wayland without XWayland is unsupported |
| Windows | `WindowsHotkeyAdapter` (unchanged) |

Detection uses `os.environ.get()` on `DISPLAY` and `WAYLAND_DISPLAY`. No config option needed.

## Data Flow

```
nimble start
  └─ get_adapter()
       └─ detects WAYLAND_DISPLAY + DISPLAY → WaylandXWaylandAdapter

adapter.start()
  ├─ Xlib: open display, create InputOnly window, map, flush
  └─ pynput GlobalHotKeys.start()  (inherited from X11HotkeyAdapter)

[user presses hotkey]
  └─ X11 routing active → pynput RECORD fires callback
       └─ daemon dispatches skill → worker runs → popup notification

adapter.stop()
  ├─ pynput listener.stop() + join()  (inherited)
  └─ Xlib: window.destroy(), display.close()
```

## Error Handling

| Failure point | Behaviour |
|---|---|
| Xlib cannot connect at `start()` | Raise `RuntimeError` — daemon aborts with message |
| Window creation fails at `start()` | Raise `RuntimeError` — daemon aborts before pynput starts |
| Window destroy fails at `stop()` | Log warning, do not raise — daemon is shutting down |

This matches the existing pattern in `X11HotkeyAdapter.start()`.

## Testing

### `tests/unit/hotkeys/test_wayland.py`

All Xlib calls mocked (same mock pattern as `test_x11.py`):

- `start()` creates an `InputOnly` window and maps it before starting the pynput listener
- `stop()` destroys the window after stopping the listener
- `register()` translates shortcut strings to pynput format correctly
- Registering a duplicate shortcut raises `ValueError`
- Xlib connection failure at `start()` raises `RuntimeError`

### `tests/unit/hotkeys/test_factory.py` additions

- `DISPLAY` set + `WAYLAND_DISPLAY` set → factory returns `WaylandXWaylandAdapter`
- `WAYLAND_DISPLAY` set, `DISPLAY` absent → factory raises `RuntimeError`

## Behaviour

Uses pynput RECORD (passive observation). Both the focused app and Nimble receive the key event — no key stealing. Choosing shortcuts not used by common apps avoids visible double-handling.

## Out of scope

- Pure Wayland without XWayland (no `DISPLAY`) — raises a clear error
- macOS support — separate concern
- XDG Global Shortcuts portal — future enhancement if pure-Wayland support is needed
