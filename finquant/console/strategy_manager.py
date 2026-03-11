"""
finquant - 策略运行管理

管理策略的加载、启动、停止
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from finquant.console.broker_manager import BrokerManager
from finquant.console.config_store import ConfigStore
from finquant.trading.signal import Signal, Action
from finquant.trading.signal_bus import SignalBus
from finquant.data import get_kline, get_realtime_quote

logger = logging.getLogger(__name__)


@dataclass
class RunningStrategy:
    """运行中的策略"""
    id: str
    name: str
    strategy_type: str  # ma_cross, rsi, custom
    params: Dict[str, Any]
    is_running: bool = False
    started_at: Optional[datetime] = None
    signals_count: int = 0
    trades_count: int = 0


class StrategyRunner:
    """
    策略运行器

    管理策略的加载、启动、停止
    """

    def __init__(
        self,
        broker_manager: BrokerManager,
        config_store: ConfigStore = None,
    ):
        self._broker_manager = broker_manager
        self._config_store = config_store or ConfigStore()
        self._strategies: Dict[str, RunningStrategy] = {}
        self._running_threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}

        # 信号总线
        self._signal_bus = SignalBus()

    # ========== 策略管理 ==========

    def add_strategy(
        self,
        name: str,
        strategy_type: str,
        params: Dict[str, Any] = None,
    ) -> str:
        """添加策略"""
        import uuid
        strategy_id = f"strat_{uuid.uuid4().hex[:8]}"

        strategy = RunningStrategy(
            id=strategy_id,
            name=name,
            strategy_type=strategy_type,
            params=params or {},
        )

        self._strategies[strategy_id] = strategy
        return strategy_id

    def remove_strategy(self, strategy_id: str) -> bool:
        """删除策略"""
        if strategy_id in self._strategies:
            # 如果正在运行，先停止
            if self._strategies[strategy_id].is_running:
                self.stop_strategy(strategy_id)

            del self._strategies[strategy_id]
            return True
        return False

    def get_strategy(self, strategy_id: str) -> Optional[RunningStrategy]:
        """获取策略"""
        return self._strategies.get(strategy_id)

    def list_strategies(self) -> List[RunningStrategy]:
        """列出所有策略"""
        return list(self._strategies.values())

    # ========== 策略运行 ==========

    def start_strategy(self, strategy_id: str) -> bool:
        """启动策略"""
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            logger.error(f"策略不存在: {strategy_id}")
            return False

        if strategy.is_running:
            logger.warning(f"策略已在运行: {strategy_id}")
            return False

        # 创建停止事件
        stop_event = threading.Event()
        self._stop_events[strategy_id] = stop_event

        # 启动策略线程
        thread = threading.Thread(
            target=self._run_strategy,
            args=(strategy_id, stop_event),
            daemon=True,
        )
        thread.start()

        self._running_threads[strategy_id] = thread
        strategy.is_running = True
        strategy.started_at = datetime.now()

        logger.info(f"策略已启动: {strategy.name}")
        return True

    def stop_strategy(self, strategy_id: str) -> bool:
        """停止策略"""
        strategy = self._strategies.get(strategy_id)
        if not strategy or not strategy.is_running:
            return False

        # 发送停止信号
        if strategy_id in self._stop_events:
            self._stop_events[strategy_id].set()

        strategy.is_running = False

        logger.info(f"策略已停止: {strategy.name}")
        return True

    def _run_strategy(self, strategy_id: str, stop_event: threading.Event):
        """运行策略"""
        strategy = self._strategies[strategy_id]

        try:
            if strategy.strategy_type == "ma_cross":
                self._run_ma_cross(strategy, stop_event)
            elif strategy.strategy_type == "rsi":
                self._run_rsi(strategy, stop_event)
            elif strategy.strategy_type == "watch":
                self._run_watch(strategy, stop_event)
            else:
                logger.error(f"未知策略类型: {strategy.strategy_type}")

        except Exception as e:
            logger.error(f"策略运行错误: {e}")

        finally:
            strategy.is_running = False
            if strategy_id in self._running_threads:
                del self._running_threads[strategy_id]
            if strategy_id in self._stop_events:
                del self._stop_events[strategy_id]

    # ========== 内置策略 ==========

    def _run_ma_cross(self, strategy: RunningStrategy, stop_event: threading.Event):
        """均线交叉策略"""
        params = strategy.params
        codes = params.get("codes", ["SH600519"])
        short_period = params.get("short_period", 5)
        long_period = params.get("long_period", 20)
        interval = params.get("interval", 60)  # 秒

        logger.info(f"运行均线交叉策略: 短期={short_period}, 长期={long_period}")

        while not stop_event.is_set():
            try:
                for code in codes:
                    # 获取历史数据
                    df = get_kline(code, days=long_period + 10)

                    if df is None or len(df) < long_period:
                        continue

                    # 计算均线
                    df["ma_short"] = df["close"].rolling(short_period).mean()
                    df["ma_long"] = df["close"].rolling(long_period).mean()

                    # 获取最新信号
                    last = df.iloc[-1]
                    prev = df.iloc[-2]

                    # 金叉买入
                    if prev["ma_short"] <= prev["ma_long"] and last["ma_short"] > last["ma_long"]:
                        signal = Signal(
                            action=Action.BUY,
                            code=code,
                            price=last["close"],
                            reason=f"MA{short_period}金叉MA{long_period}",
                        )
                        self._signal_bus.publish(signal)
                        strategy.signals_count += 1

                    # 死叉卖出
                    elif prev["ma_short"] >= prev["ma_long"] and last["ma_short"] < last["ma_long"]:
                        signal = Signal(
                            action=Action.SELL,
                            code=code,
                            price=last["close"],
                            reason=f"MA{short_period}死叉MA{long_period}",
                        )
                        self._signal_bus.publish(signal)
                        strategy.signals_count += 1

            except Exception as e:
                logger.error(f"策略执行错误: {e}")

            # 等待
            stop_event.wait(interval)

    def _run_rsi(self, strategy: RunningStrategy, stop_event: threading.Event):
        """RSI策略"""
        params = strategy.params
        codes = params.get("codes", ["SH600519"])
        period = params.get("period", 14)
        oversold = params.get("oversold", 30)
        overbought = params.get("overbought", 70)
        interval = params.get("interval", 60)

        logger.info(f"运行RSI策略: 周期={period}, 超卖={oversold}, 超买={overbought}")

        while not stop_event.is_set():
            try:
                for code in codes:
                    df = get_kline(code, days=period + 10)

                    if df is None or len(df) < period:
                        continue

                    # 计算RSI
                    delta = df["close"].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))

                    last_rsi = rsi.iloc[-1]
                    prev_rsi = rsi.iloc[-2]

                    # RSI超卖买入
                    if prev_rsi < oversold and last_rsi >= oversold:
                        signal = Signal(
                            action=Action.BUY,
                            code=code,
                            price=df["close"].iloc[-1],
                            reason=f"RSI从超卖回升",
                        )
                        self._signal_bus.publish(signal)
                        strategy.signals_count += 1

                    # RSI超买卖出
                    elif prev_rsi > overbought and last_rsi <= overbought:
                        signal = Signal(
                            action=Action.SELL,
                            code=code,
                            price=df["close"].iloc[-1],
                            reason=f"RSI从超买回落",
                        )
                        self._signal_bus.publish(signal)
                        strategy.signals_count += 1

            except Exception as e:
                logger.error(f"策略执行错误: {e}")

            stop_event.wait(interval)

    def _run_watch(self, strategy: RunningStrategy, stop_event: threading.Event):
        """监视行情策略"""
        params = strategy.params
        codes = params.get("codes", ["SH600519"])
        interval = params.get("interval", 3)

        logger.info(f"运行监视策略: {codes}")

        while not stop_event.is_set():
            try:
                quotes = get_realtime_quote(codes)

                if quotes:
                    signal = Signal(
                        action=Action.HOLD,
                        code="",
                        reason=f"行情更新",
                    )
                    self._signal_bus.publish(signal)
                    strategy.signals_count += 1

            except Exception as e:
                logger.error(f"策略执行错误: {e}")

            stop_event.wait(interval)

    # ========== 信号处理 ==========

    def get_signal_bus(self) -> SignalBus:
        """获取信号总线"""
        return self._signal_bus

    def subscribe_signal(self, handler):
        """订阅信号"""
        self._signal_bus.subscribe(handler)

    # ========== 回测 ==========

    def backtest(
        self,
        strategy_type: str,
        codes: List[str],
        start_date: str,
        end_date: str,
        initial_capital: float = 100000,
        params: Dict[str, Any] = None,
    ):
        """运行回测"""
        from finquant import BacktestEngineV2, BacktestConfig
        from finquant.strategy import MAStrategy

        params = params or {}

        # 创建策略
        if strategy_type == "ma_cross":
            strategy = MAStrategy(
                short_period=params.get("short_period", 5),
                long_period=params.get("long_period", 20),
            )
        else:
            strategy = MAStrategy()

        # 创建引擎
        config = BacktestConfig(
            initial_capital=initial_capital,
            commission_rate=0.0003,
        )
        engine = BacktestEngineV2(config)

        # 运行回测
        results = {}
        for code in codes:
            engine.set_strategy(strategy)
            result = engine.run(code, start_date, end_date)
            results[code] = result

        return results


# ========== 便捷函数 ==========

def get_strategy_runner(
    broker_manager: BrokerManager = None,
    config_store: ConfigStore = None,
) -> StrategyRunner:
    """获取策略运行器"""
    return StrategyRunner(broker_manager, config_store)


__all__ = [
    "StrategyRunner",
    "RunningStrategy",
    "get_strategy_runner",
]
