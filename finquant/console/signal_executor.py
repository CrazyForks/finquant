"""
finquant - 信号执行器

实现信号的自动执行逻辑
"""

import logging
import threading
import time
from typing import Callable, Dict, List, Optional

from finquant.console.broker_manager import BrokerManager
from finquant.console.config_store import ConfigStore
from finquant.trading.broker import EastMoneyQuote
from finquant.trading.signal import Signal, Action

logger = logging.getLogger(__name__)


class SignalExecutor:
    """
    信号执行器

    负责:
    - 接收信号
    - 风控检查
    - 订单执行
    - 记录日志
    """

    def __init__(
        self,
        broker_manager: BrokerManager,
        config_store: ConfigStore = None,
    ):
        self._broker_manager = broker_manager
        self._config_store = config_store
        self._enabled = False
        self._order_callbacks: List[Callable] = []
        self._trade_log: List[Dict] = []

        # 交易锁
        self._lock = threading.Lock()

    def enable(self):
        """启用自动执行"""
        self._enabled = True
        logger.info("信号执行器已启用")

    def disable(self):
        """禁用自动执行"""
        self._enabled = False
        logger.info("信号执行器已禁用")

    def is_enabled(self) -> bool:
        """是否启用"""
        return self._enabled

    def execute(self, signal: Signal) -> bool:
        """
        执行信号

        Args:
            signal: 交易信号

        Returns:
            是否执行成功
        """
        if not self._enabled:
            logger.debug("信号执行器未启用，跳过")
            return False

        if not signal or signal.action == Action.HOLD:
            return False

        with self._lock:
            try:
                return self._execute_signal(signal)
            except Exception as e:
                logger.error(f"执行信号失败: {e}")
                return False

    def _execute_signal(self, signal: Signal) -> bool:
        """执行信号（内部方法）"""
        settings = self._config_store.get_settings() if self._config_store else None

        # 获取券商
        broker = self._broker_manager.get_active_broker()
        if not broker:
            logger.error("没有激活的券商")
            return False

        # 获取当前价格
        price = signal.price
        if not price or price <= 0:
            quote = EastMoneyQuote.get_quote([signal.code]).get(signal.code, {})
            price = quote.get("price", 0)

        if price <= 0:
            logger.error(f"无法获取 {signal.code} 的价格")
            return False

        # 获取账户信息
        account = broker.get_account()

        # 风控检查
        if not self._check_risk(signal, account, price, settings):
            return False

        # 执行订单
        order = None

        if signal.action == Action.BUY:
            order = self._execute_buy(broker, account, signal, price, settings)
        elif signal.action == Action.SELL:
            order = self._execute_sell(broker, account, signal, price, settings)

        # 记录日志
        if order:
            self._log_trade(signal, order)

            # 回调
            for callback in self._order_callbacks:
                try:
                    callback(order, signal)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")

            return True

        return False

    def _execute_buy(
        self,
        broker,
        account,
        signal: Signal,
        price: float,
        settings,
    ) -> Optional:
        """执行买入"""
        # 计算买入数量
        available_cash = account.cash

        # 检查最低现金
        if settings:
            min_cash = account.total_assets * settings.min_cash_ratio
            available_cash = max(0, available_cash - min_cash)

        # 计算买入金额
        buy_ratio = settings.auto_buy_ratio if settings else 0.2
        buy_amount = available_cash * buy_ratio

        # 计算买入数量（100股整数倍）
        quantity = int(buy_amount / price / 100) * 100

        if quantity <= 0:
            logger.warning(f"资金不足，无法买入 {signal.code}")
            return None

        # 提交订单
        try:
            order = broker.buy(signal.code, quantity, price)
            logger.info(f"买入 {signal.code}: {quantity}股 @ {price}")
            return order
        except Exception as e:
            logger.error(f"买入失败: {e}")
            return None

    def _execute_sell(
        self,
        broker,
        account,
        signal: Signal,
        price: float,
        settings,
    ) -> Optional:
        """执行卖出"""
        # 获取持仓
        positions = broker.get_positions()

        for pos in positions:
            if pos.code == signal.code and pos.shares > 0:
                # 决定卖出数量
                sell_all = settings.auto_sell_all if settings else True
                quantity = pos.shares if sell_all else pos.shares // 2

                # 提交订单
                try:
                    order = broker.sell(signal.code, quantity, price)
                    logger.info(f"卖出 {signal.code}: {quantity}股 @ {price}")
                    return order
                except Exception as e:
                    logger.error(f"卖出失败: {e}")
                    return None

        logger.warning(f"无持仓，无需卖出 {signal.code}")
        return None

    def _check_risk(
        self,
        signal: Signal,
        account,
        price: float,
        settings,
    ) -> bool:
        """风控检查"""
        if not settings:
            return True

        # 买入风控
        if signal.action == Action.BUY:
            # 检查总仓位
            if account.total_assets > 0:
                current_position_ratio = account.market_value / account.total_assets
                if current_position_ratio >= settings.max_total_position:
                    logger.warning(f"总仓位已达上限 {settings.max_total_position * 100}%")
                    return False

            # 检查单票仓位
            positions = account.positions
            for pos in positions:
                if pos.code == signal.code:
                    if pos.market_value / account.total_assets >= settings.max_position_pct:
                        logger.warning(f"{signal.code} 仓位已达上限")
                        return False

        # 卖出风控 - 检查是否触发止损/止盈
        if signal.action == Action.SELL and settings.enable_stop_loss:
            for pos in account.positions:
                if pos.code == signal.code:
                    # 止损检查
                    if settings.enable_stop_loss:
                        loss_ratio = (price - pos.avg_cost) / pos.avg_cost
                        if loss_ratio <= -settings.stop_loss_pct:
                            logger.info(f"{signal.code} 触发止损: {loss_ratio * 100:.2f}%")
                            return True

                    # 止盈检查
                    if settings.enable_take_profit:
                        profit_ratio = (price - pos.avg_cost) / pos.avg_cost
                        if profit_ratio >= settings.take_profit_pct:
                            logger.info(f"{signal.code} 触发止盈: {profit_ratio * 100:.2f}%")
                            return True

                    # 如果不是风控触发，检查是否已有持仓不卖出
                    if settings.auto_sell_all is False:
                        return False

        return True

    def _log_trade(self, signal: Signal, order):
        """记录交易"""
        import datetime
        self._trade_log.append({
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "signal": signal.action.value,
            "code": signal.code,
            "quantity": order.quantity if order else 0,
            "price": order.avg_price if order else 0,
            "status": order.status.value if order else "UNKNOWN",
            "reason": signal.reason,
        })

        # 保留最近1000条
        if len(self._trade_log) > 1000:
            self._trade_log = self._trade_log[-1000:]

    def get_trade_log(self, limit: int = 50) -> List[Dict]:
        """获取交易日志"""
        return self._trade_log[-limit:]

    def on_order(self, callback: Callable):
        """订单回调"""
        self._order_callbacks.append(callback)

    def clear_log(self):
        """清空日志"""
        self._trade_log.clear()


# ========== 便捷函数 ==========

def get_signal_executor(
    broker_manager: BrokerManager,
    config_store: ConfigStore = None,
) -> SignalExecutor:
    """获取信号执行器"""
    return SignalExecutor(broker_manager, config_store)


__all__ = [
    "SignalExecutor",
    "get_signal_executor",
]
