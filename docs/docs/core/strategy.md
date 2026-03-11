# 策略开发

## 基础策略

```python
from finquant.strategy import BaseStrategy

class MaCrossStrategy(BaseStrategy):
    """移动平均线交叉策略"""

    def __init__(self, short=5, long=20):
        super().__init__()
        self.short = short
        self.long = long

    def on_bar(self, bar):
        # 计算移动平均
        ma_short = bar.history("close", self.short).mean()
        ma_long = bar.history("close", self.long).mean()

        # 金叉买入
        if ma_short > ma_long and not self.position:
            self.buy(bar.close, 100)

        # 死叉卖出
        elif ma_short < ma_long and self.position:
            self.sell(bar.close, self.position)
```

## 策略模板

```python
from finquant.strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def initialize(self):
        """初始化，只调用一次"""
        pass

    def on_bar(self, bar):
        """每根K线调用一次"""
        pass

    def on_trade(self, trade):
        """成交时调用"""
        pass

    def on_order(self, order):
        """订单状态变化时调用"""
        pass
```

## 使用内置策略

```python
from finquant.strategy import MaCross, RsiStrategy

# 移动平均线策略
result = bt("SH600519", "ma_cross", short=5, long=20)

# RSI策略
result = bt("SH600519", "rsi", period=14, overbought=70, oversold=30)
```
