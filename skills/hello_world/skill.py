from __future__ import annotations


class HelloWorldSkill:
    def run(self, context: object, tools: object) -> None:
        try:
            from plyer import notification

            notification.notify(
                title="Nimble",
                message="Hello from Nimble! The daemon is working.",
                app_name="Nimble",
            )
        except Exception:
            pass
