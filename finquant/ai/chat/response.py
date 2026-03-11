"""
finquant - 响应格式化器

格式化 AI 响应输出
"""

from finquant.ai.chat.action_router import ActionResult
from finquant.console.ui import UI


class ResponseFormatter:
    """响应格式化器"""

    @classmethod
    def format(cls, result: ActionResult) -> str:
        """格式化响应"""
        if not result.success:
            return f"{UI.C['red']}Error: {result.message}{UI.C['reset']}"

        # 响应内容
        lines = [
            "",
            f"{UI.C['cyan']}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{UI.C['reset']}",
            f"{UI.C['yellow']}[AI] {result.message}{UI.C['reset']}",
            f"{UI.C['cyan']}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{UI.C['reset']}",
        ]

        # 添加建议
        if result.suggestions:
            lines.append("")
            lines.append(f"{UI.C['dim']}💡 可执行命令:{UI.C['reset']}")
            for suggestion in result.suggestions:
                lines.append(f"  {UI.C['cyan']}{suggestion}{UI.C['reset']}")

        lines.append("")

        return "\n".join(lines)


__all__ = ["ResponseFormatter"]
