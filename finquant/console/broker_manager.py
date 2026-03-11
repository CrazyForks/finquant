"""
finquant - 券商管理

管理券商适配器的创建、切换、初始化
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from finquant.console.config_store import ConfigStore, BrokerConfigData
from finquant.trading.broker import (
    BrokerAdapter,
    BacktestBroker,
    SimulatedLiveBroker,
    EastMoneyQuote,
    HuataiConfig,
    HuataiSimulatedBroker,
    create_huatai_broker,
    create_simulated_broker,
    BrokerConfig,
)

logger = logging.getLogger(__name__)


# 券商类型映射
BROKER_FACTORIES = {}


def register_broker_factory(broker_type: str, factory):
    """注册券商工厂"""
    BROKER_FACTORIES[broker_type] = factory


# 注册默认券商
register_broker_factory("simulated", lambda config: create_simulated_broker(
    initial_cash=config.get("initial_cash", 100000)
))

register_broker_factory("huatai", lambda config: create_huatai_broker(
    account_id=config.get("account_id", ""),
    password=config.get("password", ""),
    app_key=config.get("app_key", ""),
    app_secret=config.get("app_secret", ""),
    initial_cash=config.get("initial_cash", 100000),
    simulated=config.get("simulated", True),
))


class BrokerManager:
    """
    券商管理器

    负责:
    - 券商配置管理
    - 券商实例创建
    - 券商切换
    """

    def __init__(self, config_store: ConfigStore = None):
        self._config_store = config_store or ConfigStore()
        self._brokers: Dict[str, BrokerAdapter] = {}
        self._active_broker: Optional[BrokerAdapter] = None

    # ========== 券商配置管理 ==========

    def add_broker(
        self,
        name: str,
        broker_type: str,
        config: Dict[str, Any] = None,
        set_active: bool = True,
    ) -> str:
        """
        添加券商

        Args:
            name: 券商名称
            broker_type: 券商类型 (simulated, huatai, eastmoney)
            config: 券商配置
            set_active: 是否设为当前券商

        Returns:
            券商ID
        """
        config = config or {}

        # 添加到配置存储
        broker_id = self._config_store.add_broker(
            name=name,
            broker_type=broker_type,
            config=config,
        )

        if set_active:
            self.set_active_broker(broker_id)

        return broker_id

    def remove_broker(self, broker_id: str) -> bool:
        """删除券商"""
        # 清理实例缓存
        if broker_id in self._brokers:
            del self._brokers[broker_id]

        # 如果删除的是当前激活的券商
        if self._config_store.get_active_broker() and \
           self._config_store.get_active_broker().id == broker_id:
            self._active_broker = None

        return self._config_store.remove_broker(broker_id)

    def update_broker(self, broker_id: str, **kwargs) -> bool:
        """更新券商配置"""
        return self._config_store.update_broker(broker_id, **kwargs)

    def set_active_broker(self, broker_id: str) -> bool:
        """切换券商"""
        result = self._config_store.set_active_broker(broker_id)
        if result:
            self._active_broker = None  # 清除缓存，强制重新创建
        return result

    # ========== 券商实例管理 ==========

    def _create_broker_instance(self, broker_config: BrokerConfigData) -> BrokerAdapter:
        """创建券商实例"""
        broker_type = broker_config.broker_type
        config = broker_config.config

        # 使用工厂创建
        if broker_type in BROKER_FACTORIES:
            broker = BROKER_FACTORIES[broker_type](config)
        else:
            logger.warning(f"未知券商类型: {broker_type}，使用模拟券商")
            broker = create_simulated_broker(
                initial_cash=config.get("initial_cash", 100000)
            )

        return broker

    def get_broker(self, broker_id: str = None) -> Optional[BrokerAdapter]:
        """
        获取券商实例

        Args:
            broker_id: 券商ID，None 表示获取当前券商

        Returns:
            券商实例
        """
        # 如果没有指定，使用激活的券商
        if broker_id is None:
            if self._active_broker:
                return self._active_broker

            broker_config = self._config_store.get_active_broker()
            if not broker_config:
                return None
        else:
            broker_config = self._config_store.get_broker(broker_id)
            if not broker_config:
                return None

        # 检查缓存
        if broker_id and broker_id in self._brokers:
            return self._brokers[broker_id]

        # 创建新实例
        broker = self._create_broker_instance(broker_config)
        broker.initialize()

        # 缓存
        if broker_id:
            self._brokers[broker_id] = broker
        else:
            self._active_broker = broker

        return broker

    def get_active_broker(self) -> Optional[BrokerAdapter]:
        """获取当前激活的券商"""
        return self.get_broker()

    # ========== 列表查询 ==========

    def list_broker_configs(self) -> List[BrokerConfigData]:
        """列出券商配置"""
        return self._config_store.list_brokers()

    def get_broker_info(self, broker_id: str = None) -> Optional[Dict]:
        """获取券商信息"""
        config = self._config_store.get_active_broker() if broker_id is None \
            else self._config_store.get_broker(broker_id)

        if not config:
            return None

        broker = self.get_broker(config.id)

        return {
            "id": config.id,
            "name": config.name,
            "type": config.broker_type,
            "is_active": config.is_active,
            "created_at": config.created_at,
            "available": broker.is_available() if broker else False,
        }

    # ========== 便捷方法 ==========

    def buy(self, code: str, quantity: int, price: float = 0, order_type: str = "MARKET"):
        """买入"""
        broker = self.get_active_broker()
        if not broker:
            raise RuntimeError("没有激活的券商")
        return broker.buy(code, quantity, price, order_type)

    def sell(self, code: str, quantity: int, price: float = 0, order_type: str = "MARKET"):
        """卖出"""
        broker = self.get_active_broker()
        if not broker:
            raise RuntimeError("没有激活的券商")
        return broker.sell(code, quantity, price, order_type)

    def get_account(self):
        """获取账户"""
        broker = self.get_active_broker()
        if not broker:
            raise RuntimeError("没有激活的券商")
        return broker.get_account()

    def get_positions(self):
        """获取持仓"""
        broker = self.get_active_broker()
        if not broker:
            raise RuntimeError("没有激活的券商")
        return broker.get_positions()

    def get_quote(self, code: str) -> Optional[float]:
        """获取行情"""
        return EastMoneyQuote.get_quote([code]).get(code, {}).get("price")


# ========== 便捷函数 ==========

def get_broker_manager() -> BrokerManager:
    """获取券商管理器"""
    return BrokerManager()


__all__ = [
    "BrokerManager",
    "get_broker_manager",
    "register_broker_factory",
]
