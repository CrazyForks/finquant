"""
finquant - 回测功能

在控制台中运行回测
"""

import logging
from typing import Dict, List, Optional

from finquant.console.config_store import ConfigStore
from finquant.console.broker_manager import BrokerManager

logger = logging.getLogger(__name__)


class BacktestRunner:
    """
    回测运行器

    在控制台中运行回测并显示结果
    """

    def __init__(
        self,
        broker_manager: BrokerManager,
        config_store: ConfigStore = None,
    ):
        self._broker_manager = broker_manager
        self._config_store = config_store
        self._visualizer = None
        self._last_results = {}

    def run(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        strategy_type: str = "ma_cross",
        initial_capital: float = 100000,
        params: Dict = None,
    ) -> Dict:
        """
        运行回测

        Args:
            codes: 股票代码列表
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            strategy_type: 策略类型
            initial_capital: 初始资金
            params: 策略参数

        Returns:
            回测结果
        """
        params = params or {}

        try:
            from finquant import backtest

            # 运行回测
            results = {}
            for code in codes:
                print(f"  回测 {code}...")

                # 使用 backtest 函数
                result = backtest(
                    code,
                    strategy_type,
                    initial_capital=initial_capital,
                    start=start_date,
                    end=end_date,
                    **params
                )
                results[code] = result

            # 保存结果供可视化使用
            self._last_results = results

            return results

        except Exception as e:
            logger.error(f"回测失败: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def show_chart(self, code: str = None):
        """显示图表"""
        if not self._last_results:
            print("  请先运行回测")
            return

        if self._visualizer is None:
            from finquant.console.backtest_visualizer import get_visualizer
            self._visualizer = get_visualizer()

        if code:
            if code in self._last_results:
                result = self._last_results[code]
                self._visualizer.print_summary(result)
            else:
                print(f"  未找到 {code} 的回测结果")
        else:
            # 显示第一个结果
            for code, result in self._last_results.items():
                self._visualizer.print_summary(result)
                break

    def show_trades(self, code: str = None, limit: int = 10):
        """显示交易记录"""
        if not self._last_results:
            print("  请先运行回测")
            return

        if self._visualizer is None:
            from finquant.console.backtest_visualizer import get_visualizer
            self._visualizer = get_visualizer()

        if code and code in self._last_results:
            result = self._last_results[code]
            if hasattr(result, 'trades'):
                self._visualizer.print_trades(result.trades, limit)
        else:
            for code, result in self._last_results.items():
                print(f"\n  {code} 交易记录:")
                if hasattr(result, 'trades'):
                    self._visualizer.print_trades(result.trades, limit)
                break

    def print_results(self, results: Dict):
        """打印回测结果"""
        if not results:
            print("  无回测结果")
            return

        print()
        print(f"  {'代码':<10} {'收益率':<12} {'年化收益':<12} {'最大回撤':<12} {'胜率':<10} {'交易次数':<10}")
        print("  " + "─" * 66)

        for code, result in results.items():
            if result and hasattr(result, 'final_capital') and result.final_capital > 0:
                total_return = result.total_return or 0
                annual_return = getattr(result, 'annual_return', 0) or 0
                max_drawdown = getattr(result, 'max_drawdown', 0) or 0
                win_rate = getattr(result, 'win_rate', 0) or 0
                total_trades = getattr(result, 'total_trades', 0) or 0

                # 颜色
                from finquant.console.ui import UI
                color = UI.C["green"] if total_return >= 0 else UI.C["red"]
                reset = UI.C["reset"]

                print(f"  {code:<10} {color}{total_return*100:+.2f}%{reset} {annual_return*100:>10.2f}% {max_drawdown*100:>10.2f}% {win_rate*100:>9.2f}% {total_trades:>10}")
            else:
                print(f"  {code:<10} {'无结果':<12}")

        print()


# ========== 便捷函数 ==========

def get_backtest_runner(
    broker_manager: BrokerManager,
    config_store: ConfigStore = None,
) -> BacktestRunner:
    """获取回测运行器"""
    return BacktestRunner(broker_manager, config_store)


__all__ = [
    "BacktestRunner",
    "get_backtest_runner",
]
