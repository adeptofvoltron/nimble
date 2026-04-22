from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Context:
    selection: str
    clipboard: str
    active_app: str
    mouse_position: list[int]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Context:
        return cls(
            selection=data["selection"],
            clipboard=data["clipboard"],
            active_app=data["active_app"],
            mouse_position=data["mouse_position"],
        )

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(
            f"Context has no field '{name}'. "
            f"Valid fields: selection, clipboard, active_app, mouse_position."
        )
