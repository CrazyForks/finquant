#!/usr/bin/env python
"""
finquant 交互式控制台入口

使用方法:
    python run_console.py           # 默认美化版本
    python run_console.py --simple  # 简单版本
"""

import sys

# 选择控制台版本
if "--simple" in sys.argv:
    from finquant.console import start_console
    start_console()
else:
    try:
        from finquant.console.rich_console import start_rich_console
        start_rich_console()
    except ImportError:
        print("提示: 安装 prompt_toolkit 获取更好体验: pip install prompt_toolkit")
        print()
        from finquant.console import start_console
        start_console()
