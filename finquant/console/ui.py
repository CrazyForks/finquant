"""
finquant - Claude Code 风格界面

参考 Claude Code 的界面设计
"""

import os
import socket
import getpass
from datetime import datetime


# ========== 界面组件 ==========

class UI:
    """界面渲染"""

    # 颜色
    C = {
        "cyan": "\033[36m",
        "magenta": "\033[35m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "red": "\033[31m",
        "blue": "\033[34m",
        "white": "\033[37m",
        "bright_black": "\033[90m",
        "bright_cyan": "\033[96m",
        "bright_magenta": "\033[95m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
    }

    @classmethod
    def banner(cls, **kwargs):
        """顶部横幅"""
        # 获取实际信息
        username = getpass.getuser()
        hostname = socket.gethostname()
        cwd = os.getcwd().replace(os.path.expanduser("~"), "~")

        # 从 kwargs 获取动态信息
        broker_name = kwargs.get("broker_name", "")
        auto_enabled = kwargs.get("auto_enabled", False)
        version = kwargs.get("version", "1.0.0")

        # 装饰图案
        patterns = [
            ["▗", "▗", "▖", "▖"],
            ["▘", "▘", "▝", "▝"],
        ]

        pattern_lines = []
        for row in patterns:
            pattern_lines.append("".join(row))

        # 左侧图案
        left_pattern = "\n".join([
            cls.C["bright_cyan"] + pattern_lines[0] + cls.C["reset"],
            cls.C["bright_cyan"] + pattern_lines[1] + cls.C["reset"],
        ])

        # 顶部框
        width = 80

        # 顶部
        print()
        print(cls.C["bright_cyan"] + "╭" + "─" * (width - 2) + "╮" + cls.C["reset"])

        # 左侧图案 + 欢迎信息
        print(cls.C["bright_cyan"] + "│" + cls.C["reset"], end="")
        print(f"  {pattern_lines[0]}                              ", end="")
        print(cls.C["bright_cyan"] + "│" + cls.C["reset"], end="")
        print(f"  {cls.C['bright_black']}Tips for getting started{cls.C['reset']}")

        print(cls.C["bright_cyan"] + "│" + cls.C["reset"], end="")
        print(f"  {pattern_lines[1]}   ", end="")
        print(cls.C["bright_cyan"] + "│" + cls.C["reset"], end="")
        print(f"  {cls.C['dim']}Run 'help' to see available commands{cls.C['reset']}")

        # 用户信息行
        cwd = os.getcwd().replace(os.path.expanduser("~"), "~")
        user_info = f"{username}@{hostname}"

        # slogan
        slogan = kwargs.get("slogan", "智能量化交易平台")

        # 版本
        version = kwargs.get("version", "v1.0.0")

        print(cls.C["bright_cyan"] + "│" + cls.C["reset"], end="")
        print(f"  {cls.C['white']}{slogan} · {cls.C['dim']}{version}{cls.C['reset']} · ", end="")
        print(cls.C["bright_cyan"] + "│" + cls.C["reset"], end="")
        print(f"  {cls.C['bright_black']}{cwd}{cls.C['reset']}")

        # 装饰线
        print(cls.C["bright_cyan"] + "│" + " " * (width - 2) + "│" + cls.C["reset"])

        # 快捷键提示
        print(cls.C["bright_cyan"] + "│" + cls.C["reset"], end="")
        shortcuts = [
            ("help", "帮助"),
            ("status", "状态"),
            ("clear", "清屏"),
        ]
        shortcut_text = " · ".join([f"{k}:{v}" for k, v in shortcuts])
        print(f"  {cls.C['dim']}{shortcut_text}" + " " * (width - len(shortcut_text) - 4) + cls.C["bright_cyan"] + "│" + cls.C["reset"])

        print(cls.C["bright_cyan"] + "╰" + "─" * (width - 2) + "╯" + cls.C["reset"])
        print()

    @classmethod
    def prompt(cls, broker_name: str = None, auto: bool = False) -> str:
        """生成提示符

        Args:
            broker_name: 券商名称
            auto: 是否自动执行
        """
        # 提示符
        p = cls.C["cyan"] + "➜" + cls.C["reset"] + " "

        # 券商名称
        if broker_name:
            p += cls.C["magenta"] + f" {broker_name}" + cls.C["reset"]

        # 自动执行状态
        if auto:
            p += cls.C["green"] + " ◉" + cls.C["reset"]

        p += cls.C["bright_black"] + " │ " + cls.C["reset"]

        return p

    @classmethod
    def separator(cls, text: str = ""):
        """分隔线"""
        if text:
            print(f"\n{cls.C['cyan']}───────────────────────────────────────────────────────────────────────────────{cls.C['reset']} {text}")
        else:
            print(f"\n{cls.C['bright_black']}───────────────────────────────────────────────────────────────────────────────{cls.C['reset']}")

    @classmethod
    def error(cls, text: str):
        """错误信息"""
        print(f"{cls.C['red']}Error: {text}{cls.C['reset']}")

    @classmethod
    def success(cls, text: str):
        """成功信息"""
        print(f"{cls.C['green']}✓ {text}{cls.C['reset']}")

    @classmethod
    def warning(cls, text: str):
        """警告信息"""
        print(f"{cls.C['yellow']}⚠ {text}{cls.C['reset']}")

    @classmethod
    def info(cls, text: str):
        """信息"""
        print(f"{cls.C['bright_black']}{text}{cls.C['reset']}")

    @classmethod
    def header(cls, text: str):
        """标题"""
        print(f"\n{cls.C['cyan']}{text}{cls.C['reset']}")

    @classmethod
    def table(cls, headers: list, rows: list, widths: list = None):
        """表格"""
        if not widths:
            widths = [20] * len(headers)

        # 表头
        header_line = "  "
        for i, h in enumerate(headers):
            header_line += f"{h:<{widths[i]}}  "
        print(cls.C["bright_black"] + header_line + cls.C["reset"])

        # 分隔线
        sep = "  " + "─" * (sum(widths) + len(widths) * 2)
        print(cls.C["dim"] + sep + cls.C["reset"])

        # 行
        for row in rows:
            line = "  "
            for i, cell in enumerate(row):
                line += f"{str(cell):<{widths[i]}}  "
            print(line)

    @classmethod
    def item(cls, label: str, value: str, status: str = None):
        """列表项"""
        if status == "success":
            value = cls.C["green"] + "✓ " + value
        elif status == "error":
            value = cls.C["red"] + "✗ " + value
        elif status == "warning":
            value = cls.C["yellow"] + "⚠ " + value
        elif value.lower() in ["true", "on", "yes", "enabled"]:
            value = cls.C["green"] + "✓ " + value
        elif value.lower() in ["false", "off", "no", "disabled"]:
            value = cls.C["dim"] + "○ " + value

        print(f"  {cls.C['cyan']}{label}:{cls.C['reset']} {value}{cls.C['reset']}")


# ========== 测试 ==========

if __name__ == "__main__":
    import sys
    os.system("clear" if os.name == "posix" else "cls")

    UI.banner()
    print(UI.prompt("我的券商", auto=True) + "help")

    print()
    UI.header("系统状态")
    UI.item("当前券商", "我的券商 (simulated)", "success")
    UI.item("自动执行", "启用")

    print()
    UI.header("可用命令")
    UI.table(
        ["命令", "功能", "示例"],
        [
            ["broker add", "添加券商", "broker add simulated xxx"],
            ["account buy", "买入股票", "account buy SH600519 100"],
            ["position", "查看持仓", "position"],
            ["market", "查看行情", "market SH600519"],
            ["backtest run", "运行回测", "backtest run SH600519 20230101 20231231"],
        ],
        [15, 20, 40]
    )

    print()
    UI.separator()
    print(UI.prompt("test") + "exit")
