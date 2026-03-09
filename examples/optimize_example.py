"""
finquant - 策略优化示例
展示如何使用网格搜索优化策略参数
"""

from datetime import date, timedelta
from finquant.data import get_kline
from finquant.strategies import MACrossStrategy, RSIStrategy, MACDStrategy
from finquant.engine import BacktestEngine
from finquant.optimize import GridSearchOptimizer


def optimize_ma_cross():
    """优化均线交叉策略参数"""
    print("=" * 60)
    print("策略优化示例: 均线交叉策略")
    print("=" * 60)

    # 获取数据
    codes = ["000001"]  # 平安银行
    start_date = (date.today() - timedelta(days=730)).strftime("%Y-%m-%d")
    end_date = date.today().strftime("%Y-%m-%d")

    print(f"获取数据: {codes}")
    print(f"时间范围: {start_date} ~ {end_date}")

    data = get_kline(codes, start=start_date, end=end_date)
    print(f"获取到 {len(data)} 条数据\n")

    # 定义参数网格
    param_grid = {
        "short_period": [3, 5, 7, 10, 15],
        "long_period": [20, 30, 40, 60],
    }

    print(f"参数网格: {param_grid}")
    print(f"共 {len(param_grid['short_period']) * len(param_grid['long_period'])} 组参数\n")

    # 创建优化器
    optimizer = GridSearchOptimizer(
        data=data,
        strategy_class=MACrossStrategy,
        param_grid=param_grid,
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000,
    )

    # 运行优化
    print("开始优化...\n")
    results = optimizer.optimize(objective="sharpe_ratio")

    # 显示前10个最佳结果
    print("\n" + "=" * 60)
    print("优化结果 (按夏普比率排序 TOP 10)")
    print("=" * 60)

    display_cols = ["short_period", "long_period", "total_return", "annual_return", "max_drawdown", "sharpe_ratio", "win_rate", "total_trades"]
    print(results[display_cols].head(10).to_string(index=False))

    # 获取最佳参数
    best_params = optimizer.get_best_params()
    print(f"\n最佳参数: {best_params}")

    # 使用最佳参数运行回测
    print("\n" + "=" * 60)
    print("使用最佳参数回测")
    print("=" * 60)

    best_strategy = MACrossStrategy(**best_params)
    engine = BacktestEngine(initial_capital=100000)
    result = engine.run(data, best_strategy, start_date, end_date)
    result.backtest_id = "最佳参数"

    print(result.summary())

    return results


def optimize_rsi():
    """优化 RSI 策略参数"""
    print("\n" + "=" * 60)
    print("策略优化示例: RSI 策略")
    print("=" * 60)

    codes = ["000001"]
    start_date = (date.today() - timedelta(days=730)).strftime("%Y-%m-%d")
    end_date = date.today().strftime("%Y-%m-%d")

    data = get_kline(codes, start=start_date, end=end_date)

    # RSI 参数网格
    param_grid = {
        "period": [7, 14, 21],
        "oversold": [20, 25, 30, 35],
        "overbought": [65, 70, 75, 80],
    }

    print(f"参数网格: {param_grid}")

    optimizer = GridSearchOptimizer(
        data=data,
        strategy_class=RSIStrategy,
        param_grid=param_grid,
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000,
    )

    results = optimizer.optimize(objective="sharpe_ratio")

    print("\n优化结果 (TOP 5):")
    display_cols = ["period", "oversold", "overbought", "total_return", "sharpe_ratio", "win_rate"]
    print(results[display_cols].head(5).to_string(index=False))

    best_params = optimizer.get_best_params()
    print(f"\n最佳参数: {best_params}")

    return results


def optimize_macd():
    """优化 MACD 策略参数"""
    print("\n" + "=" * 60)
    print("策略优化示例: MACD 策略")
    print("=" * 60)

    codes = ["000001"]
    start_date = (date.today() - timedelta(days=730)).strftime("%Y-%m-%d")
    end_date = date.today().strftime("%Y-%m-%d")

    data = get_kline(codes, start=start_date, end=end_date)

    # MACD 参数网格
    param_grid = {
        "fast_period": [8, 12, 16],
        "slow_period": [20, 26, 32],
        "signal_period": [6, 9, 12],
    }

    print(f"参数网格: {param_grid}")

    optimizer = GridSearchOptimizer(
        data=data,
        strategy_class=MACDStrategy,
        param_grid=param_grid,
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000,
    )

    results = optimizer.optimize(objective="sharpe_ratio")

    print("\n优化结果 (TOP 5):")
    display_cols = ["fast_period", "slow_period", "signal_period", "total_return", "sharpe_ratio", "win_rate"]
    print(results[display_cols].head(5).to_string(index=False))

    best_params = optimizer.get_best_params()
    print(f"\n最佳参数: {best_params}")

    return results


def compare_optimization_objectives():
    """比较不同优化目标"""
    print("\n" + "=" * 60)
    print("比较不同优化目标")
    print("=" * 60)

    codes = ["000001"]
    start_date = (date.today() - timedelta(days=730)).strftime("%Y-%m-%d")
    end_date = date.today().strftime("%Y-%m-%d")

    data = get_kline(codes, start=start_date, end=end_date)

    param_grid = {
        "short_period": [5, 7, 10],
        "long_period": [20, 30, 40],
    }

    objectives = ["sharpe_ratio", "total_return", "win_rate"]

    for obj in objectives:
        print(f"\n--- 优化目标: {obj} ---")

        optimizer = GridSearchOptimizer(
            data=data,
            strategy_class=MACrossStrategy,
            param_grid=param_grid,
            start_date=start_date,
            end_date=end_date,
        )

        results = optimizer.optimize(objective=obj)
        best = results.iloc[0]

        print(f"最佳参数: short_period={best['short_period']}, long_period={best['long_period']}")
        print(f"总收益: {best['total_return']*100:.2f}%, 夏普: {best['sharpe_ratio']:.2f}, 胜率: {best['win_rate']*100:.2f}%")


def multi_stock_optimization():
    """多股票组合优化"""
    print("\n" + "=" * 60)
    print("多股票组合优化")
    print("=" * 60)

    # 多只股票
    codes = ["000001", "600000", "600036"]  # 平安银行, 浦发银行, 招商银行
    start_date = (date.today() - timedelta(days=730)).strftime("%Y-%m-%d")
    end_date = date.today().strftime("%Y-%m-%d")

    print(f"获取数据: {codes}")
    data = get_kline(codes, start=start_date, end=end_date)
    print(f"获取到 {len(data)} 条数据\n")

    param_grid = {
        "short_period": [5, 10, 15],
        "long_period": [20, 30],
    }

    optimizer = GridSearchOptimizer(
        data=data,
        strategy_class=MACrossStrategy,
        param_grid=param_grid,
        start_date=start_date,
        end_date=end_date,
    )

    results = optimizer.optimize(objective="sharpe_ratio")

    print("优化结果 (TOP 5):")
    display_cols = ["short_period", "long_period", "total_return", "sharpe_ratio", "total_trades"]
    print(results[display_cols].head(5).to_string(index=False))

    best_params = optimizer.get_best_params()
    print(f"\n最佳参数: {best_params}")


if __name__ == "__main__":
    # 1. 优化均线交叉策略
    optimize_ma_cross()

    # 2. 优化 RSI 策略 (可选)
    # optimize_rsi()

    # 3. 优化 MACD 策略 (可选)
    # optimize_macd()

    # 4. 比较不同优化目标 (可选)
    # compare_optimization_objectives()

    # 5. 多股票组合优化 (可选)
    # multi_stock_optimization()

    print("\n" + "=" * 60)
    print("优化完成!")
    print("=" * 60)
