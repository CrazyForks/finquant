# API 参考

## 核心 API

### get_kline()

获取K线数据。

```python
get_kline(
    codes: List[str],
    start: str,
    end: str = None,
    adjust: str = "qfq"
) -> pd.DataFrame
```

**参数：**
- `codes` - 股票代码列表
- `start` - 开始日期
- `end` - 结束日期
- `adjust` - 复权类型 ("qfq" 前复权, "hfq" 后复权, "" 不复权)

### bt()

快速回测函数。

```python
bt(
    code: str,
    strategy: str,
    **kwargs
) -> BacktestResult
```

### BacktestEngineV2

V2版本回测引擎。

```python
engine = BacktestEngineV2(
    initial_cash: float = 1_000_000,
    commission: float = 0.0003,
    slip_rate: float = 0.001
)

result = engine.run(data, strategy)
```

## 返回值

### BacktestResult

回测结果对象，包含：

- `summary()` - 汇总统计
- `trades` - 交易记录
- `positions` - 持仓记录
- `equity_curve` - 权益曲线
- `plot()` - 绘图方法
