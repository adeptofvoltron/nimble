from __future__ import annotations


class QuickClipSkill:
    def run(self, context, tools) -> None:
        text = (context.clipboard or "").strip()
        tools.popup.show(text if text else "(clipboard is empty)")
