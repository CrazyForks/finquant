"""
finquant - 回测结果可视化

在控制台中显示回测结果的图表
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BacktestVisualizer:
    """
    回测结果可视化

    使用 ASCII 字符在控制台中绘制图表
    """

    # 图表字符
    BAR_CHARS = ["▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]

    def __init__(self):
        self.width = 50  # 图表宽度

    def print_equity_curve(self, equity: List[float], title: str = "权益曲线"):
        """
        打印权益曲线

        Args:
            equity: 权益列表
            title: 标题
        """
        if not equity or len(equity) < 2:
            print("  数据不足")
            return

        # 归一化到 0-10 的范围
        min_val = min(equity)
        max_val = max(equity)
        range_val = max_val - min_val

        if range_val == 0:
            range_val = 1

        # 构建图表
        lines = []
        for i in range(10, -1, -1):
            threshold = min_val + (range_val * i / 10)
            line = ""
            for val in equity:
                if val >= threshold:
                    line += "█"
                else:
                    line += " "
            lines.append(line)

        # 打印
        print()
        print(f"  {title}")
        print("  " + "─" * (self.width + 2))

        for i, line in enumerate(lines):
            y_label = f"{max_val - (range_val * i / 10):,.0f}"
            print(f"  {y_label:>12} │{line}│")

        print("  " + " " * 12 + "└" + "─" * self.width + "┘")
        print("  " + " " * 12 + f"起始: {equity[0]:,.0f}  结束: {equity[-1]:,.0f}")

    def print_returns_bar(self, returns: List[float], title: str = "月度收益"):
        """
        打印收益柱状图

        Args:
            returns: 收益列表
            title: 标题
        """
        if not returns:
            print("  无数据")
            return

        max_return = max(abs(r) for r in returns)
        if max_return == 0:
            max_return = 1

        print()
        print(f"  {title}")
        print("  " + "─" * (self.width + 2))

        for r in returns:
            bar_len = int(abs(r) / max_return * self.width)
            if r >= 0:
                bar = " " * (self.width - bar_len) + "█" * bar_len
                print(f"  +{r*100:>6.2f}% │{bar}│")
            else:
                bar = "█" * bar_len + " " * (self.width - bar_len)
                print(f"  {r*100:>7.2f}% │{bar}│")

    def print_summary(self, result) -> str:
        """
        打印回测结果摘要

        Args:
            result: BacktestResult 对象

        Returns:
            摘要字符串
        """
        if not hasattr(result, 'final_capital') or result.final_capital == 0:
            return "无结果"

        from finquant.console.rich_console import c, Color

        total_return = result.total_return or 0
        annual_return = getattr(result, 'annual_return', 0) or 0
        max_drawdown = getattr(result, 'max_drawdown', 0) or 0
        sharpe = getattr(result, 'sharpe_ratio', 0) or 0
        win_rate = getattr(result, 'win_rate', 0) or 0
        total_trades = getattr(result, 'total_trades', 0) or 0

        return_color = Color.GREEN if total_return >= 0 else Color.RED

        summary = f"""
  {c(Color.CYAN, '═══ 回测摘要 ═══')}

  {c(Color.BRIGHT_BLACK, '收益指标:')}
    {c(Color.WHITE, '总收益率:')}   {c(return_color, f'{total_return*100:+.2f}%')}
    {c(Color.WHITE, '年化收益率:')}  {c(return_color, f'{annual_return*100:+.2f}%')}
    {c(Color.WHITE, '夏普比率:')}   {c(Color.CYAN, f'{sharpe:.2f}')}

  {c(Color.BRIGHT_BLACK, '风险指标:')}
    {c(Color.WHITE, '最大回撤:')}   {c(Color.RED, f'{max_drawdown*100:.2f}%')}

  {c(Color.BRIGHT_BLACK, '交易统计:')}
    {c(Color.WHITE, '交易次数:')}   {c(Color.CYAN, f'{total_trades}')}
    {c(Color.WHITE, '胜率:')}       {c(Color.CYAN, f'{win_rate*100:.2f}%')}

  {c(Color.CYAN, '═══════════════════')}
"""
        print(summary)
        return summary

    def print_trades(self, trades: List[Dict], limit: int = 10):
        """
        打印交易记录

        Args:
            trades: 交易列表
            limit: 显示数量
        """
        if not trades:
            print("  无交易记录")
            return

        from finquant.console.rich_console import c, Color

        print()
        print(f"  {'日期':<12} {'代码':<8} {'方向':<4} {'数量':<6} {'价格':<8} {'盈亏':<10}")
        print("  " + "─" * 60)

        for trade in trades[:limit]:
            date = trade.get('date', '')[:10]
            code = trade.get('code', '')
            action = trade.get('action', '')
            quantity = trade.get('quantity', 0)
            price = trade.get('price', 0)
            profit = trade.get('profit', 0)

            profit_str = f"{profit:+.2f}"
            profit_color = Color.GREEN if profit >= 0 else Color.RED

            action_color = Color.GREEN if action == 'BUY' else Color.RED

            print(f"  {date:<12} {code:<8} {c(action_color, action):<4} {quantity:<6} {price:<8.2f} {c(profit_color, profit_str):<10}")

        if len(trades) > limit:
            print(f"  ... 还有 {len(trades) - limit} 条记录")

    def plot_simple_line(self, data: List[float], height: int = 10) -> str:
        """
        绘制简单的折线图

        Args:
            data: 数据
            height: 高度

        Returns:
            图表字符串
        """
        if not data:
            return ""

        min_val = min(data)
        max_val = max(data)
        range_val = max_val - min_val

        if range_val == 0:
            range_val = 1

        result = []
        for i in range(height, 0, -1):
            threshold = min_val + (range_val * i / height)
            line = ""
            for val in data:
                normalized = (val - min_val) / range_val * height
                if normalized >= i:
                    line += "█"
                elif normalized >= i - 0.5:
                    line += "▄"
                else:
                    line += " "
            result.append(line)

        return '\n'.join(result)


# ========== 便捷函数 ==========

def get_visualizer() -> BacktestVisualizer:
    """获取可视化器"""
    return BacktestVisualizer()


__all__ = [
    "BacktestVisualizer",
    "get_visualizer",
]
