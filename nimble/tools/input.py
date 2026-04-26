from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class InputTool:
    def ask(self, prompt: str) -> str | None:
        try:
            import tkinter as tk
            from tkinter import simpledialog

            root = tk.Tk()
            root.withdraw()
            try:
                return simpledialog.askstring("Nimble", prompt)
            finally:
                root.destroy()
        except Exception as exc:
            logger.warning("Input dialog (ask) failed", exc_info=True)
            raise RuntimeError(f"Input dialog is not available: {exc}") from exc

    def select(self, prompt: str, choices: list[str]) -> str | None:
        try:
            import tkinter as tk

            root = tk.Tk()
            root.withdraw()
            try:
                return _run_select_dialog(root, prompt, choices)
            finally:
                root.destroy()
        except Exception as exc:
            logger.warning("Input dialog (select) failed", exc_info=True)
            raise RuntimeError(f"Input dialog is not available: {exc}") from exc


def _run_select_dialog(parent: Any, prompt: str, choices: list[str]) -> str | None:
    import tkinter as tk

    result: list[str | None] = [None]

    win = tk.Toplevel(parent)
    win.title("Nimble")
    win.grab_set()

    tk.Label(win, text=prompt).pack(padx=10, pady=(10, 0))

    listbox = tk.Listbox(win, selectmode=tk.SINGLE, height=min(len(choices), 10))
    for item in choices:
        listbox.insert(tk.END, item)
    listbox.pack(padx=10, pady=5)

    def on_ok() -> None:
        sel = listbox.curselection()  # type: ignore[no-untyped-call]
        if sel:
            result[0] = choices[sel[0]]
        win.destroy()

    def on_cancel() -> None:
        win.destroy()

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=(0, 10))
    tk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT)

    win.wait_window()
    return result[0]
