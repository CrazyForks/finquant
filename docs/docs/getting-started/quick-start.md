# 快速开始

本指南将帮助你快速上手 FinQuant 量化回测框架。

## 5 分钟快速回测

使用 `bt` 函数进行快速策略验证：

```python
from finquant import bt

# 简单移动平均线交叉策略
result = bt("SH600519", "ma_cross", short=5, long=20)
print(result.summary())
```

## 完整回测流程

### 1. 获取数据

```python
from finquant import get_kline

# 获取历史K线数据
data = get_kline(
    codes=["SH600519", "SH000001"],  # 股票代码
    start="2024-01-01",
    end="2024-12-31",
    adjust="qfq"  # 前复权
)
```

### 2. 定义策略

```python
from finquant.strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def on_bar(self, bar):
        # 获取历史数据
        ma5 = bar.history("close", 5).mean()
        ma20 = bar.history("close", 20).mean()

        # 交易逻辑
        if ma5 > ma20 and not self.position:
            self.buy(bar.close, 100)
        elif ma5 < ma20 and self.position:
            self.sell(bar.close, 100)
```

### 3. 运行回测

```python
from finquant import BacktestEngineV2

# 创建回测引擎
engine = BacktestEngineV2(
    initial_cash=1_000_000,  # 初始资金 100 万
    commission=0.0003,       # 手续费万三
    slip_rate=0.001,          # 滑点千一
)

# 运行回测
result = engine.run(data, MyStrategy)

# 查看结果
print(result.summary())      # 汇总统计
print(result.trades)         # 交易记录
result.plot()                # 绘制权益曲线
```

## 核心 API

| API | 说明 |
|-----|------|
| `get_kline()` | 获取 K 线数据 |
| `bt()` | 快速回测函数 |
| `BacktestEngineV2` | V2 回测引擎 |
| `BacktestResult` | 回测结果对象 |

## 下一步

- [核心概念](/docs/core/concept) - 深入理解框架设计
- [策略开发](/docs/core/strategy) - 学习编写策略
- [参数优化](/docs/advanced/optimization) - 优化策略参数
