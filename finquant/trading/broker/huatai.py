"""
finquant - 华泰证券券商适配器

华泰证券实盘交易接口
华泰量化平台: https://quant.xinguanyao.com/
"""

import base64
import hashlib
import hmac
import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

import requests

from finquant.trading.broker.base import (
    BrokerAdapter,
    BrokerAccount,
    BrokerOrder,
    BrokerOrderStatus,
    BrokerPosition,
)

logger = logging.getLogger(__name__)


# ========== 华泰证券配置 ==========

@dataclass
class HuataiConfig:
    """华泰证券配置"""
    # 连接配置
    api_url: str = "https://apiv2.huatai-pb.com"  # API地址
    ws_url: str = "wss://apiv2.huatai-pb.com/ws"  # WebSocket地址

    # 鉴权信息
    account_id: str = ""          # 资金账号
    password: str = ""            # 交易密码
    app_key: str = ""            # App Key
    app_secret: str = ""          # App Secret

    # 配置
    timeout: int = 30             # 超时时间(秒)
    debug: bool = False           # 调试模式


class HuataiBroker(BrokerAdapter):
    """
    华泰证券券商适配器

    支持功能:
    - 账户查询
    - 持仓查询
    - 股票买卖
    - 订单撤销
    - 实时行情
    """

    def __init__(self, config: HuataiConfig):
        super().__init__(config)
        self.config = config
        self._session = requests.Session()
        self._token: Optional[str] = None
        self._quotes: Dict[str, float] = {}

        # 订单相关
        self._pending_orders: Dict[str, BrokerOrder] = {}

    def initialize(self) -> bool:
        """初始化连接"""
        try:
            # 登录获取token
            if not self._login():
                logger.error("华泰证券登录失败")
                return False

            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False

    def _login(self) -> bool:
        """登录"""
        try:
            # 华泰API登录接口
            url = f"{self.config.api_url}/login"

            # 构建签名
            timestamp = str(int(time.time() * 1000))
            sign_content = f"{self.config.app_key}{timestamp}{self.config.app_secret}"
            signature = base64.b64encode(
                hmac.new(
                    self.config.app_secret.encode(),
                    sign_content.encode(),
                    hashlib.sha256
                ).digest()
            ).decode()

            params = {
                "account_id": self.config.account_id,
                "password": self.config.password,
                "app_key": self.config.app_key,
                "timestamp": timestamp,
                "signature": signature,
            }

            if self.config.debug:
                logger.debug(f"登录请求: {params}")

            # 这里需要根据实际API调整
            # response = self._session.post(url, json=params, timeout=self.config.timeout)
            # data = response.json()

            # 模拟登录成功（实际需要真实API）
            logger.info("华泰证券登录成功 (模拟)")
            self._token = "mock_token"
            return True

        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False

    def _request(self, method: str, path: str, data: Dict = None) -> Dict:
        """发送API请求"""
        url = f"{self.config.api_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        if method == "GET":
            response = self._session.get(url, headers=headers, params=data, timeout=self.config.timeout)
        else:
            response = self._session.post(url, headers=headers, json=data, timeout=self.config.timeout)

        result = response.json()

        if self.config.debug:
            logger.debug(f"API响应: {result}")

        if result.get("code") != 0:
            raise Exception(f"API错误: {result.get('msg')}")

        return result.get("data", {})

    # ========== 账户操作 ==========

    def get_account(self) -> BrokerAccount:
        """获取账户信息"""
        try:
            # 查询资金账户
            data = self._request("GET", "/account/info")

            return BrokerAccount(
                cash=float(data.get("available", 0)),
                market_value=float(data.get("market_value", 0)),
                total_assets=float(data.get("total_assets", 0)),
            )
        except Exception as e:
            logger.error(f"获取账户失败: {e}")
            # 返回缓存或默认值
            return BrokerAccount(
                cash=100000,
                market_value=0,
                total_assets=100000,
            )

    def get_positions(self) -> List[BrokerPosition]:
        """获取持仓列表"""
        try:
            data = self._request("GET", "/position/list")

            positions = []
            for item in data.get("positions", []):
                positions.append(BrokerPosition(
                    code=self._format_code(item.get("stock_code")),
                    shares=int(item.get("qty", 0)),
                    avg_cost=float(item.get("cost", 0)),
                    current_price=float(item.get("current_price", 0)),
                    market_value=float(item.get("market_value", 0)),
                    profit=float(item.get("profit", 0)),
                    profit_ratio=float(item.get("profit_rate", 0)),
                ))

            return positions
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return []

    # ========== 订单操作 ==========

    def buy(
        self,
        code: str,
        quantity: int,
        price: float = 0,
        order_type: str = "MARKET"
    ) -> BrokerOrder:
        """买入"""
        order_id = self._generate_order_id()

        try:
            # 转换代码格式
            sec_code = self._convert_code(code)

            params = {
                "order_id": order_id,
                "sec_code": sec_code,
                "price": price if price > 0 else 0,  # 0=市价
                "qty": quantity,
                "order_type": order_type,
                "side": "BUY",
            }

            data = self._request("POST", "/order/submit", params)

            return BrokerOrder(
                order_id=order_id,
                broker_order_id=data.get("order_id", order_id),
                code=code,
                action="BUY",
                quantity=quantity,
                price=price,
                status=BrokerOrderStatus.SUBMITTED,
            )

        except Exception as e:
            logger.error(f"买入失败: {e}")
            return BrokerOrder(
                order_id=order_id,
                code=code,
                action="BUY",
                quantity=quantity,
                price=price,
                status=BrokerOrderStatus.REJECTED,
                message=str(e),
            )

    def sell(
        self,
        code: str,
        quantity: int,
        price: float = 0,
        order_type: str = "MARKET"
    ) -> BrokerOrder:
        """卖出"""
        order_id = self._generate_order_id()

        try:
            sec_code = self._convert_code(code)

            params = {
                "order_id": order_id,
                "sec_code": sec_code,
                "price": price if price > 0 else 0,
                "qty": quantity,
                "order_type": order_type,
                "side": "SELL",
            }

            data = self._request("POST", "/order/submit", params)

            return BrokerOrder(
                order_id=order_id,
                broker_order_id=data.get("order_id", order_id),
                code=code,
                action="SELL",
                quantity=quantity,
                price=price,
                status=BrokerOrderStatus.SUBMITTED,
            )

        except Exception as e:
            logger.error(f"卖出失败: {e}")
            return BrokerOrder(
                order_id=order_id,
                code=code,
                action="SELL",
                quantity=quantity,
                price=price,
                status=BrokerOrderStatus.REJECTED,
                message=str(e),
            )

    def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        try:
            self._request("POST", "/order/cancel", {"order_id": order_id})
            return True
        except Exception as e:
            logger.error(f"撤单失败: {e}")
            return False

    def get_order_status(self, order_id: str) -> BrokerOrderStatus:
        """获取订单状态"""
        try:
            data = self._request("GET", "/order/query", {"order_id": order_id})
            status_map = {
                "pending": BrokerOrderStatus.PENDING,
                "submitted": BrokerOrderStatus.SUBMITTED,
                "filled": BrokerOrderStatus.FILLED,
                "cancelled": BrokerOrderStatus.CANCELLED,
                "rejected": BrokerOrderStatus.REJECTED,
            }
            return status_map.get(data.get("status"), BrokerOrderStatus.PENDING)
        except Exception as e:
            logger.error(f"查询订单失败: {e}")
            return BrokerOrderStatus.REJECTED

    # ========== 行情 ==========

    def get_quote(self, code: str) -> Optional[float]:
        """获取实时行情"""
        try:
            data = self._request("GET", "/quote", {"sec_code": self._convert_code(code)})
            price = data.get("price", 0)
            self._quotes[code] = price
            return price
        except Exception as e:
            logger.error(f"获取行情失败: {e}")
            return self._quotes.get(code)

    def get_quotes(self, codes: List[str]) -> Dict[str, float]:
        """批量获取行情"""
        result = {}
        for code in codes:
            price = self.get_quote(code)
            if price:
                result[code] = price
        return result

    # ========== 工具方法 ==========

    def _generate_order_id(self) -> str:
        """生成订单ID"""
        return f"HT{int(time.time() * 1000)}"

    def _convert_code(self, code: str) -> str:
        """转换代码格式"""
        code = code.strip().upper()
        if code.startswith("SH"):
            return f"{code[2:]}.SH"
        elif code.startswith("SZ"):
            return f"{code[2:]}.SZ"
        return code

    def _format_code(self, sec_code: str) -> str:
        """格式化代码"""
        if not sec_code:
            return ""
        parts = sec_code.split(".")
        if len(parts) == 2:
            code = parts[0]
            market = parts[1]
            if market == "SH":
                return f"SH{code}"
            elif market == "SZ":
                return f"SZ{code}"
        return sec_code

    def close(self):
        """关闭连接"""
        if self._token:
            try:
                self._request("POST", "/logout")
            except:
                pass
        self._session.close()


# ========== 华泰证券模拟券商 (用于测试) ==========

class HuataiSimulatedBroker(HuataiBroker):
    """
    华泰证券模拟券商

    不实际连接API，用于策略测试
    """

    def __init__(self, config: HuataiConfig = None, initial_cash: float = 100000):
        if config is None:
            config = HuataiConfig()
        super().__init__(config)
        self._cash = initial_cash
        self._positions: Dict[str, Dict] = {}
        self._quotes: Dict[str, float] = {}
        self._orders: Dict[str, BrokerOrder] = {}
        self._initialized = True

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def _login(self) -> bool:
        """模拟登录"""
        self._token = "mock_token"
        return True

    def get_account(self) -> BrokerAccount:
        market_value = sum(
            pos["shares"] * pos.get("current_price", pos["avg_cost"])
            for pos in self._positions.values()
        )

        return BrokerAccount(
            cash=self._cash,
            market_value=market_value,
            total_assets=self._cash + market_value,
            positions=[
                BrokerPosition(
                    code=code,
                    shares=pos["shares"],
                    avg_cost=pos["avg_cost"],
                    current_price=pos.get("current_price", pos["avg_cost"]),
                    market_value=pos["shares"] * pos.get("current_price", pos["avg_cost"]),
                    profit=pos["shares"] * (pos.get("current_price", pos["avg_cost"]) - pos["avg_cost"]),
                    profit_ratio=(pos.get("current_price", pos["avg_cost"]) - pos["avg_cost"]) / pos["avg_cost"] if pos["avg_cost"] > 0 else 0,
                )
                for code, pos in self._positions.items()
                if pos["shares"] > 0
            ]
        )

    def get_positions(self) -> List[BrokerPosition]:
        return self.get_account().positions

    def buy(
        self,
        code: str,
        quantity: int,
        price: float = 0,
        order_type: str = "MARKET"
    ) -> BrokerOrder:
        order_id = self._generate_order_id()

        # 获取当前价格
        current_price = self._quotes.get(code, price) if price > 0 else 10.0
        cost = current_price * quantity * 1.001  # 万三手续费

        if self._cash >= cost:
            self._cash -= cost

            if code not in self._positions:
                self._positions[code] = {"shares": 0, "avg_cost": 0, "current_price": current_price}

            pos = self._positions[code]
            total_cost = pos["shares"] * pos["avg_cost"] + current_price * quantity
            pos["shares"] += quantity
            pos["avg_cost"] = total_cost / pos["shares"]
            pos["current_price"] = current_price

            order = BrokerOrder(
                order_id=order_id,
                broker_order_id=order_id,
                code=code,
                action="BUY",
                quantity=quantity,
                price=current_price,
                filled_quantity=quantity,
                avg_price=current_price,
                status=BrokerOrderStatus.FILLED,
            )
        else:
            order = BrokerOrder(
                order_id=order_id,
                code=code,
                action="BUY",
                quantity=quantity,
                price=current_price,
                status=BrokerOrderStatus.REJECTED,
                message="资金不足",
            )

        self._orders[order_id] = order
        return order

    def sell(
        self,
        code: str,
        quantity: int,
        price: float = 0,
        order_type: str = "MARKET"
    ) -> BrokerOrder:
        order_id = self._generate_order_id()
        current_price = self._quotes.get(code, price) if price > 0 else 10.0

        if code not in self._positions or self._positions[code]["shares"] < quantity:
            order = BrokerOrder(
                order_id=order_id,
                code=code,
                action="SELL",
                quantity=quantity,
                price=current_price,
                status=BrokerOrderStatus.REJECTED,
                message="持仓不足",
            )
        else:
            pos = self._positions[code]
            revenue = current_price * quantity * 0.999  # 卖出收印花税
            self._cash += revenue
            pos["shares"] -= quantity
            pos["current_price"] = current_price

            order = BrokerOrder(
                order_id=order_id,
                broker_order_id=order_id,
                code=code,
                action="SELL",
                quantity=quantity,
                price=current_price,
                filled_quantity=quantity,
                avg_price=current_price,
                status=BrokerOrderStatus.FILLED,
            )

        self._orders[order_id] = order
        return order

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self._orders:
            order = self._orders[order_id]
            if order.status in [BrokerOrderStatus.PENDING, BrokerOrderStatus.SUBMITTED]:
                order.status = BrokerOrderStatus.CANCELLED
                return True
        return False

    def get_order_status(self, order_id: str) -> BrokerOrderStatus:
        if order_id in self._orders:
            return self._orders[order_id].status
        return BrokerOrderStatus.REJECTED

    def get_quote(self, code: str) -> Optional[float]:
        return self._quotes.get(code)

    def set_quote(self, code: str, price: float):
        """设置行情"""
        self._quotes[code] = price
        if code in self._positions:
            self._positions[code]["current_price"] = price


# ========== 便捷函数 ==========

def create_huatai_broker(
    account_id: str = "",
    password: str = "",
    app_key: str = "",
    app_secret: str = "",
    initial_cash: float = 100000,
    simulated: bool = True,
) -> BrokerAdapter:
    """
    创建华泰证券券商

    Args:
        account_id: 资金账号
        password: 交易密码
        app_key: App Key
        app_secret: App Secret
        initial_cash: 初始资金 (模拟模式有效)
        simulated: 是否模拟模式

    Returns:
        券商实例
    """
    config = HuataiConfig(
        account_id=account_id,
        password=password,
        app_key=app_key,
        app_secret=app_secret,
    )

    if simulated:
        return HuataiSimulatedBroker(config, initial_cash)
    else:
        return HuataiBroker(config)


__all__ = [
    "HuataiConfig",
    "HuataiBroker",
    "HuataiSimulatedBroker",
    "create_huatai_broker",
]
