"""
finquant - 参数优化模块

贝叶斯优化 / 网格搜索 / 随机搜索
"""

import logging
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from itertools import product
import random

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """优化结果"""
    best_params: Dict[str, Any]
    best_score: float
    all_results: List[Dict]
    elapsed_time: float


class ParamSpace:
    """参数空间"""

    def __init__(self):
        self.params = {}

    def add_int(self, name: str, min_val: int, max_val: int, step: int = 1):
        """添加整数参数"""
        values = list(range(min_val, max_val + 1, step))
        self.params[name] = values
        return self

    def add_float(self, name: str, min_val: float, max_val: float, step: float = 0.01):
        """添加浮点数参数"""
        values = []
        current = min_val
        while current <= max_val:
            values.append(round(current, 2))
            current += step
        self.params[name] = values
        return self

    def add_choice(self, name: str, choices: List[Any]):
        """添加离散选项"""
        self.params[name] = choices
        return self

    def get_grid(self) -> List[Dict]:
        """获取所有参数组合"""
        keys = list(self.params.keys())
        values = list(self.params.values())
        combinations = list(product(*values))
        return [dict(zip(keys, combo)) for combo in combinations]


class Optimizer:
    """参数优化器"""

    def __init__(self):
        self.results = []

    def grid_search(
        self,
        param_space: ParamSpace,
        objective_fn: Callable[[Dict], float],
        maximize: bool = True,
        max_combinations: int = 100,
    ) -> OptimizationResult:
        """
        网格搜索

        Args:
            param_space: 参数空间
            objective_fn: 目标函数，参数 -> 分数
            maximize: 是否最大化分数
            max_combinations: 最大组合数

        Returns:
            优化结果
        """
        import time
        start_time = time.time()

        # 获取参数组合
        all_params = param_space.get_grid()

        # 限制组合数量
        if len(all_params) > max_combinations:
            logger.warning(f"参数组合过多 ({len(all_params)})，随机采样 {max_combinations} 个")
            all_params = random.sample(all_params, max_combinations)

        logger.info(f"网格搜索: {len(all_params)} 个参数组合")

        results = []
        best_score = float('-inf') if maximize else float('inf')
        best_params = None

        for i, params in enumerate(all_params):
            try:
                score = objective_fn(params)

                results.append({
                    "params": params.copy(),
                    "score": score,
                })

                if maximize and score > best_score:
                    best_score = score
                    best_params = params.copy()
                elif not maximize and score < best_score:
                    best_score = score
                    best_params = params.copy()

                if (i + 1) % 10 == 0:
                    logger.info(f"进度: {i + 1}/{len(all_params)}, 当前最佳: {best_score:.4f}")

            except Exception as e:
                logger.warning(f"参数 {params} 执行失败: {e}")

        elapsed_time = time.time() - start_time
        logger.info(f"优化完成! 最佳分数: {best_score:.4f}, 耗时: {elapsed_time:.2f}秒")

        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_results=results,
            elapsed_time=elapsed_time,
        )

    def random_search(
        self,
        param_space: ParamSpace,
        objective_fn: Callable[[Dict], float],
        n_iter: int = 50,
        maximize: bool = True,
    ) -> OptimizationResult:
        """
        随机搜索

        Args:
            param_space: 参数空间
            objective_fn: 目标函数
            n_iter: 迭代次数
            maximize: 是否最大化分数

        Returns:
            优化结果
        """
        import time
        start_time = time.time()

        all_params = param_space.get_grid()
        n_iter = min(n_iter, len(all_params))

        logger.info(f"随机搜索: {n_iter} 次迭代")

        results = []
        best_score = float('-inf') if maximize else float('inf')
        best_params = None

        for i in range(n_iter):
            params = random.choice(all_params)
            all_params.remove(params)  # 不重复

            try:
                score = objective_fn(params)

                results.append({
                    "params": params.copy(),
                    "score": score,
                })

                if maximize and score > best_score:
                    best_score = score
                    best_params = params.copy()
                elif not maximize and score < best_score:
                    best_score = score
                    best_params = params.copy()

                if (i + 1) % 10 == 0:
                    logger.info(f"进度: {i + 1}/{n_iter}, 当前最佳: {best_score:.4f}")

            except Exception as e:
                logger.warning(f"参数 {params} 执行失败: {e}")

        elapsed_time = time.time() - start_time
        logger.info(f"优化完成! 最佳分数: {best_score:.4f}, 耗时: {elapsed_time:.2f}秒")

        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_results=results,
            elapsed_time=elapsed_time,
        )


class StrategyOptimizer:
    """策略参数优化器"""

    def __init__(self, broker_manager=None):
        self.broker_manager = broker_manager
        self.optimizer = Optimizer()

    def optimize_ma_cross(
        self,
        code: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000,
        short_range: tuple = (3, 20),
        long_range: tuple = (10, 60),
        metric: str = "total_return",
    ) -> OptimizationResult:
        """
        优化均线交叉策略参数

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            short_range: 短期均线范围
            long_range: 长期均线范围
            metric: 优化指标 (total_return, sharpe, max_drawdown)

        Returns:
            优化结果
        """
        from finquant import backtest

        # 构建参数空间
        param_space = ParamSpace()
        param_space.add_int("short_period", short_range[0], short_range[1], step=1)
        param_space.add_int("long_period", long_range[0], long_range[1], step=1)

        def objective_fn(params):
            # 确保 short < long
            if params["short_period"] >= params["long_period"]:
                return float('-inf')

            # 运行回测
            result = backtest(
                code,
                "ma_cross",
                initial_capital=initial_capital,
                start=start_date,
                end=end_date,
                short_period=params["short_period"],
                long_period=params["long_period"],
            )

            # 获取目标指标
            if metric == "total_return":
                return result.total_return or 0
            elif metric == "sharpe":
                return getattr(result, 'sharpe_ratio', 0) or 0
            elif metric == "max_drawdown":
                return -(getattr(result, 'max_drawdown', 0) or 0)  # 最小化回撤
            else:
                return result.total_return or 0

        # 运行优化
        return self.optimizer.grid_search(param_space, objective_fn, maximize=(metric != "max_drawdown"))

    def optimize_rsi(
        self,
        code: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000,
        period_range: tuple = (5, 30),
        overbought_range: tuple = (60, 90),
        oversold_range: tuple = (10, 40),
    ) -> OptimizationResult:
        """优化 RSI 策略参数"""
        from finquant import backtest

        param_space = ParamSpace()
        param_space.add_int("period", period_range[0], period_range[1])
        param_space.add_int("overbought", overbought_range[0], overbought_range[1])
        param_space.add_int("oversold", oversold_range[0], oversold_range[1])

        def objective_fn(params):
            if params["oversold"] >= params["overbought"]:
                return float('-inf')

            result = backtest(
                code,
                "rsi",
                initial_capital=initial_capital,
                start=start_date,
                end=end_date,
                period=params["period"],
                overbought=params["overbought"],
                oversold=params["oversold"],
            )

            return result.total_return or 0

        return self.optimizer.grid_search(param_space, objective_fn)


def get_optimizer(broker_manager=None) -> StrategyOptimizer:
    """获取优化器"""
    return StrategyOptimizer(broker_manager)


__all__ = [
    "ParamSpace",
    "Optimizer",
    "StrategyOptimizer",
    "OptimizationResult",
    "get_optimizer",
]
