# finshare + finquant：轻量级 Python 量化工具生态

> A 股数据获取 + 回测分析，一站式解决方案

---

## 写在前面

大家好！今天给大家介绍两个我正在维护的开源项目：**finshare**（金融数据获取）和 **finquant**（量化回测工具）。

两个项目都开源在 GitHub，配合使用可以实现 A 股数据的获取到回测分析的全流程。

- finshare: https://github.com/finvfamily/finshare
- finquant: https://github.com/finvfamily/finquant

---

## finshare：纯 Python A 股数据获取

### 特性

- **多数据源支持**：东方财富、腾讯、新浪、通达信、BaoStock
- **自动故障切换**：主数据源失败自动切换备用源
- **统一数据格式**：不同来源数据统一处理
- **纯 Python 脚本**：无需数据库，开箱即用

### 安装

```bash
pip install finshare
```

### 快速开始

```python
from finshare import get_data_manager

# 获取数据管理器
manager = get_data_manager()

# 获取 K 线数据
df = manager.get_historical_data(
    "000001.SZ",
    start="2024-01-01",
    end="2024-12-31"
)

print(df.head())
```

```
       code  trade_date  open_price  high_price  low_price  close_price  volume
0  SZ000001  2024-01-02       9.85       9.93       9.75        9.80  4567890
1  SZ000001  2024-01-03       9.80       9.88       9.75        9.85  3456789
...
```

### 支持的数据类型

| 函数 | 说明 |
|------|------|
| `get_historical_data` | 历史 K 线数据 |
| `get_snapshot_data` | 实时行情快照 |
| `get_batch_snapshots` | 批量实时行情 |

### 股票代码格式

支持多种输入格式，自动转换：

```python
# 这些格式都可以
"000001"        # 纯数字
"000001.SZ"     # 标准格式
"sz.000001"     # 带点格式
```

---

## finquant：轻量级量化回测工具

### 特性

- **纯 Python 脚本**：无需数据库、无需服务端
- **数据源**：使用 finshare 获取实时股票数据
- **内置策略**：均线交叉、RSI、MACD、布林带等
- **仓位控制**：固定仓位、金字塔、倒金字塔、ATR 仓位
- **参数优化**：网格搜索参数优化

### 安装

```bash
git clone https://github.com/finvfamily/finquant.git
cd finquant
pip install -r requirements.txt
pip install -e .
```

### 快速开始

```python
from finquant import get_kline, MACrossStrategy, BacktestEngine

# 获取数据
data = get_kline(["000001", "600000"], start="2024-01-01", end="2025-01-01")

# 创建策略
strategy = MACrossStrategy(short_period=5, long_period=20)

# 运行回测
engine = BacktestEngine(initial_capital=100000)
result = engine.run(data, strategy)

# 查看结果
print(result.summary())
```

输出：

```
========================================
          回测结果摘要
========================================
初始资金: 100,000.00
最终资金: 108,500.00
总收益率: 8.50%
年化收益率: 8.32%
最大回撤: 12.50%
夏普比率: 0.65
胜率: 45.00%
交易次数: 20
========================================
```

### 内置策略

```python
from finquant import (
    MACrossStrategy,   # 均线交叉
    RSIStrategy,       # RSI 策略
    MACDStrategy,      # MACD 策略
    BollStrategy,      # 布林带策略
    DualEMAStrategy,   # 双重 EMA
)

# RSI 策略
strategy = RSIStrategy(period=14, oversold=30, overbought=70)

# MACD 策略
strategy = MACDStrategy(fast_period=12, slow_period=26, signal_period=9)
```

### 仓位控制

```python
from finquant import (
    BacktestEngine,
    PyramidPositionSizer,  # 金字塔仓位
)

# 浮盈加仓策略
engine = BacktestEngine(
    initial_capital=100000,
    position_sizer=PyramidPositionSizer(
        base_ratio=0.2,  # 基础仓位 20%
        max_ratio=1.0,   # 最大仓位 100%
        step=0.1,        # 每 10% 浮盈加仓
    ),
    max_positions=3,
    max_single_position=0.3,
)
```

### 参数优化

```python
from finquant import get_kline, MACrossStrategy
from finquant.optimize import GridSearchOptimizer

data = get_kline(["000001"], start="2023-01-01", end="2024-12-31")

# 定义参数网格
param_grid = {
    "short_period": [3, 5, 7, 10, 15],
    "long_period": [20, 30, 40, 60],
}

# 运行优化
optimizer = GridSearchOptimizer(
    data=data,
    strategy_class=MACrossStrategy,
    param_grid=param_grid,
)

results = optimizer.optimize(objective="sharpe_ratio")

# 获取最佳参数
best_params = optimizer.get_best_params()
print(f"最佳参数: {best_params}")
```

---

## 组合使用示例

完整的数据获取 + 回测流程：

```python
from finshare import get_data_manager
from finquant import get_kline, MACrossStrategy, BacktestEngine

# 1. finshare 获取数据
manager = get_data_manager()
df = manager.get_historical_data("000001.SZ", start="2023-01-01", end="2024-12-31")

# 2. finquant 回测
data = get_kline(["000001"], start="2023-01-01", end="2024-12-31")
engine = BacktestEngine(initial_capital=100000)
result = engine.run(data, MACrossStrategy(5, 20))

print(result.summary())
```

---

## 项目地址

| 项目 | GitHub | 描述 |
|------|--------|------|
| finshare | https://github.com/finvfamily/finshare | A 股数据获取 |
| finquant | https://github.com/finvfamily/finquant | 量化回测工具 |

官方网站：https://meepoquant.com

---

## 写在最后

这两个项目都是纯 Python 实现，无需复杂的依赖，开箱即用。

欢迎 Star、Fork 和 Contribution！

如果有任何问题，欢迎在 GitHub 提 Issue 或者评论区留言。

---

**相关文章**

- [finshare 源码解析：多数据源设计](https://meepoquant.com)
- [量化策略的参数优化实战](https://meepoquant.com)
