"""
finquant - 交互控制台模块

提供实盘交易的交互式命令行界面
"""

from finquant.console.console import (
    TradingConsole,
    start_console,
)

from finquant.console.config_store import (
    ConfigStore,
    BrokerConfigData,
    SettingsData,
    get_config_store,
)

from finquant.console.broker_manager import (
    BrokerManager,
    get_broker_manager,
)

from finquant.console.strategy_manager import (
    StrategyRunner,
    get_strategy_runner,
)

from finquant.console.order_history import (
    OrderHistory,
    get_order_history,
)

from finquant.console.signal_executor import (
    SignalExecutor,
    get_signal_executor,
)

__all__ = [
    # 控制台
    "TradingConsole",
    "start_console",
    # 配置
    "ConfigStore",
    "BrokerConfigData",
    "SettingsData",
    "get_config_store",
    # 券商
    "BrokerManager",
    "get_broker_manager",
    # 策略
    "StrategyRunner",
    "get_strategy_runner",
    # 订单
    "OrderHistory",
    "get_order_history",
    # 信号执行
    "SignalExecutor",
    "get_signal_executor",
]
