# Running Nimble on Wayland

Nimble uses the Linux kernel's input layer (`/dev/input/event*`) to capture global hotkeys.
This works on any session type — Wayland-native apps, XWayland, or pure X11 — without any
extra configuration beyond a one-time group membership step.

## One-time setup

Keyboard input devices are owned by the `input` group. Add your user once:

```bash
sudo usermod -aG input $USER
```

Then **log out and log back in** (or reboot). The change is permanent — you only do this once.

Verify it worked:

```bash
groups | grep input
```

If `input` appears in the output, Nimble can read keyboard events.

## Why this is needed

On Wayland, there is no display-server-level API that lets unprivileged processes observe
global keypresses (the way X11's RECORD extension worked). The only reliable cross-session
approach is to read directly from the kernel input devices at `/dev/input/event*`.

These device files are owned by root with group `input`. Granting your user membership in
`input` gives Nimble read access without requiring `sudo` or `setuid`.

## What happens without it

If the daemon starts without `input` group access, it exits immediately with:

```
RuntimeError: Permission denied opening /dev/input/eventN.
Add your user to the 'input' group and log out/in:
    sudo usermod -aG input $USER
```

## Security note

Membership in `input` gives read access to all input devices (keyboard, mouse, touchpad).
Any process running as your user can also read these devices. This is the standard trade-off
for global hotkey daemons on Wayland — the same access level used by tools like `evtest`,
`keyd`, and `interception-tools`.
