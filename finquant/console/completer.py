"""
finquant - 命令补全

使用 prompt_toolkit 实现命令补全
"""

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter, NestedCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys


def create_completer():
    """创建命令补全器"""

    # 主命令补全
    main_commands = {
        "help": None,
        "status": None,
        "clear": None,
        "cls": None,
        "exit": None,
        "quit": None,
        "q": None,
        "broker": {
            "list": None,
            "add": None,
            "remove": None,
            "active": None,
        },
        "account": {
            "buy": None,
            "sell": None,
        },
        "position": None,
        "pos": None,
        "market": {
            "SH600519": None,
            "SH601318": None,
            "SH000001": None,
            "SZ399001": None,
            "SZ399006": None,
        },
        "order": {
            "list": None,
            "stats": None,
        },
        "strategy": {
            "list": None,
            "add": None,
            "start": None,
            "stop": None,
        },
        "backtest": {
            "run": None,
            "save": None,
            "show": None,
            "trades": None,
            "help": None,
        },
        "settings": {
            "show": None,
            "auto": {
                "on": None,
                "off": None,
            },
            "set": None,
        },
        "optimize": None,
    }

    # 参数补全
    param_completer = {
        # 策略类型
        "ma_cross": None,
        "rsi": None,
        # 优化指标
        "total_return": None,
        "sharpe": None,
        "max_drawdown": None,
        # 常用股票代码
        "SH600519": None,  # 贵州茅台
        "SH601318": None,  # 中国平安
        "SH600036": None,  # 招商银行
        "SH000001": None,  # 上证指数
        "SZ399001": None,  # 深证成指
        "SZ399006": None,  # 创业板指
        # 日期
        "2023-01-01": None,
        "2023-06-01": None,
        "2023-12-31": None,
        "2024-01-01": None,
        "2024-06-01": None,
        "2024-12-31": None,
        "2025-01-01": None,
    }

    # 合并所有补全词
    all_words = {}
    all_words.update(main_commands)

    # 添加参数到主命令
    for key in param_completer:
        if key not in all_words:
            all_words[key] = None

    completer = NestedCompleter.from_nested_dict(all_words)

    return completer


def create_prompt_session(**kwargs):
    """创建 PromptSession"""
    session = PromptSession(**kwargs)
    return session


# 全局补全器
_completer = None


def get_completer():
    """获取补全器"""
    global _completer
    if _completer is None:
        _completer = create_completer()
    return _completer


def update_completer_stock_codes(codes: list):
    """动态更新股票代码补全"""
    global _completer

    # 获取当前参数补全
    param_completer = {
        "ma_cross": None,
        "rsi": None,
        "total_return": None,
        "sharpe": None,
        "max_drawdown": None,
    }

    # 添加自定义股票代码
    for code in codes:
        param_completer[code] = None

    # 合并
    all_words = {
        "help": None,
        "status": None,
        "clear": None,
        "cls": None,
        "exit": None,
        "quit": None,
        "q": None,
        "broker": {
            "list": None,
            "add": None,
            "remove": None,
            "active": None,
        },
        "account": {
            "buy": None,
            "sell": None,
        },
        "position": None,
        "pos": None,
        "market": None,
        "order": {
            "list": None,
            "stats": None,
        },
        "strategy": {
            "list": None,
            "add": None,
            "start": None,
            "stop": None,
        },
        "backtest": {
            "run": None,
            "save": None,
            "show": None,
            "trades": None,
            "help": None,
        },
        "settings": {
            "show": None,
            "auto": {
                "on": None,
                "off": None,
            },
            "set": None,
        },
        "optimize": None,
    }

    # 更新
    all_words.update(param_completer)

    from prompt_toolkit.completion import NestedCompleter
    _completer = NestedCompleter.from_nested_dict(all_words)

    return _completer


__all__ = [
    "create_completer",
    "create_prompt_session",
    "get_completer",
]
