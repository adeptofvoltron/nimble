from __future__ import annotations


class HelloWorldSkill:
    def run(self, context: object, tools: object) -> None:
        tools.popup.show("Hello from Nimble! The daemon is working.")
