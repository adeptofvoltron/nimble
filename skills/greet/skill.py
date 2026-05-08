from __future__ import annotations


class GreetSkill:
    def run(self, context, tools) -> None:
        app = context.active_app or "your app"
        tools.popup.show(f"Hello from {app}!")
