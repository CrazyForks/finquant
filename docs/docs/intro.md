---
sidebar_position: 1
slug: /
---

import Link from '@docusaurus/Link';
import CodeBlock from '@docusaurus/theme-classic/lib/theme/CodeBlock';

# 欢迎使用 FinQuant

<p align="center">
  <img src="/img/finquant-logo.svg" width="200" alt="FinQuant Logo" />
</p>

<p align="center">
  <strong>轻量级 Python 量化回测工具</strong>
</p>

<p align="center">
  纯 Python 脚本，无需服务端和数据缓存
</p>

---

## 特性

<div className="grid-cards">

| 特性 | 描述 |
|------|------|
| 🚀 **事件驱动架构** | 解耦策略与引擎，支持多策略组合 |
| 💾 **本地缓存** | Parquet 格式缓存，支持增量更新 |
| 🛡️ **完整风控** | 止损止盈、最大回撤控制、仓位管理 |
| 📊 **执行精度模拟** | 滑点、部分成交、市场冲击建模 |
| ⚡ **参数优化** | 贝叶斯优化、Walk-Forward、敏感性分析 |
| 🌐 **多资产支持** | 股票、ETF、LOF、科创板混合回测 |

</div>

## 快速开始

```python
from finquant import bt

# 快速回测
result = bt("SH600519", "ma_cross", short=5, long=20)
```

```python
# 完整回测
from finquant import BacktestEngineV2, get_kline
from finquant.strategy import MaCross

# 获取数据
data = get_kline("SH600519", start="2024-01-01")

# 创建引擎
engine = BacktestEngineV2(initial_cash=1000000)

# 运行回测
result = engine.run(data, MaCross)
```

## 安装

```bash
pip install finquant
```

## 链接

<Link className="button button--primary button--lg" to="/docs/getting-started/installation">
  开始使用 →
</Link>

<Link className="button button--secondary button--lg" to="https://github.com/meepo-quant/finquant">
  GitHub →
</Link>
