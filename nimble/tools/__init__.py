from __future__ import annotations

from dataclasses import dataclass

from nimble.tools.ai import AiTool
from nimble.tools.clipboard import ClipboardTool
from nimble.tools.popup import PopupTool


@dataclass
class ToolRegistry:
    ai: AiTool
    popup: PopupTool
    clipboard: ClipboardTool
