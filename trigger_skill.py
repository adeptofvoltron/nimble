#!/usr/bin/env python3
"""Simulate a hotkey press to trigger a Nimble skill for testing."""
import sys
import time
import os

os.environ.setdefault("DISPLAY", ":0")

from Xlib import display, X
from Xlib.ext import xtest

KEYCODES = {
    "ctrl": 37,
    "shift": 50,
    "alt": 64,
    "l": 46,
    "space": 65,
}

shortcut = sys.argv[1] if len(sys.argv) > 1 else "ctrl+l"
parts = shortcut.lower().split("+")
codes = [KEYCODES[p] for p in parts if p in KEYCODES]

if not codes:
    print(f"Unknown keys in shortcut: {shortcut}")
    sys.exit(1)

d = display.Display(":0")
for kc in codes:
    xtest.fake_input(d, X.KeyPress, kc)
    d.flush()
    time.sleep(0.05)
for kc in reversed(codes):
    xtest.fake_input(d, X.KeyRelease, kc)
    d.flush()
    time.sleep(0.05)
d.close()
print(f"Triggered: {shortcut}")
