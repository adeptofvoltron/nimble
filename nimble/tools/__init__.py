from __future__ import annotations

from dataclasses import dataclass

from nimble.tools.ai import AiTool


@dataclass
class ToolRegistry:
    ai: AiTool
