"""
finquant - 订单历史管理

记录和查询订单历史
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from finquant.console.config_store import DEFAULT_CONFIG_DIR
from finquant.trading.broker.base import BrokerOrderStatus

logger = logging.getLogger(__name__)


@dataclass
class OrderRecord:
    """订单记录"""
    order_id: str
    broker_order_id: str
    code: str
    action: str
    quantity: int
    price: float
    filled_quantity: int
    avg_price: float
    status: str
    message: str
    created_at: str
    updated_at: str


class OrderHistory:
    """
    订单历史记录器

    持久化保存订单记录
    """

    def __init__(self, config_dir: str = None):
        if config_dir is None:
            self._config_dir = DEFAULT_CONFIG_DIR
        else:
            self._config_dir = Path(config_dir)

        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._history_file = self._config_dir / "order_history.json"
        self._orders: Dict[str, OrderRecord] = {}
        self._load()

    def _load(self):
        """加载历史记录"""
        if self._history_file.exists():
            try:
                with open(self._history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for order_data in data.get("orders", []):
                        order = OrderRecord(**order_data)
                        self._orders[order.order_id] = order
            except Exception as e:
                logger.error(f"加载订单历史失败: {e}")

    def _save(self):
        """保存历史记录"""
        try:
            data = {
                "version": "1.0",
                "orders": [asdict(o) for o in self._orders.values()],
            }

            with open(self._history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存订单历史失败: {e}")

    def add_order(
        self,
        order_id: str,
        code: str,
        action: str,
        quantity: int,
        price: float,
        broker_order_id: str = "",
        filled_quantity: int = 0,
        avg_price: float = 0,
        status: str = "PENDING",
        message: str = "",
    ):
        """添加订单记录"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        order = OrderRecord(
            order_id=order_id,
            broker_order_id=broker_order_id,
            code=code,
            action=action,
            quantity=quantity,
            price=price,
            filled_quantity=filled_quantity,
            avg_price=avg_price,
            status=status,
            message=message,
            created_at=now,
            updated_at=now,
        )

        self._orders[order_id] = order
        self._save()

        return order

    def update_order(
        self,
        order_id: str,
        filled_quantity: int = None,
        avg_price: float = None,
        status: str = None,
        message: str = None,
    ) -> Optional[OrderRecord]:
        """更新订单"""
        if order_id not in self._orders:
            return None

        order = self._orders[order_id]

        if filled_quantity is not None:
            order.filled_quantity = filled_quantity
        if avg_price is not None:
            order.avg_price = avg_price
        if status is not None:
            order.status = status
        if message is not None:
            order.message = message

        order.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._save()
        return order

    def get_order(self, order_id: str) -> Optional[OrderRecord]:
        """获取订单"""
        return self._orders.get(order_id)

    def get_orders(
        self,
        code: str = None,
        action: str = None,
        status: str = None,
        limit: int = 100,
    ) -> List[OrderRecord]:
        """查询订单"""
        orders = list(self._orders.values())

        # 过滤
        if code:
            orders = [o for o in orders if o.code == code]
        if action:
            orders = [o for o in orders if o.action == action]
        if status:
            orders = [o for o in orders if o.status == status]

        # 按时间倒序
        orders.sort(key=lambda x: x.created_at, reverse=True)

        # 限制数量
        return orders[:limit]

    def get_pending_orders(self) -> List[OrderRecord]:
        """获取待成交订单"""
        pending = [o for o in self._orders.values()
                   if o.status in ["PENDING", "SUBMITTED"]]
        pending.sort(key=lambda x: x.created_at, reverse=True)
        return pending

    def clear_history(self, before_date: str = None):
        """清理历史"""
        if before_date:
            # 删除指定日期之前的记录
            self._orders = {
                oid: order for oid, order in self._orders.items()
                if order.created_at >= before_date
            }
        else:
            # 清空全部
            self._orders = {}

        self._save()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        orders = list(self._orders.values())

        total = len(orders)
        filled = len([o for o in orders if o.status == "FILLED"])
        cancelled = len([o for o in orders if o.status == "CANCELLED"])
        rejected = len([o for o in orders if o.status == "REJECTED"])

        # 交易统计
        buy_count = len([o for o in orders if o.action == "BUY" and o.status == "FILLED"])
        sell_count = len([o for o in orders if o.action == "SELL" and o.status == "FILLED"])

        total_buy_amount = sum(o.filled_quantity * o.avg_price
                               for o in orders if o.action == "BUY" and o.status == "FILLED")
        total_sell_amount = sum(o.filled_quantity * o.avg_price
                                 for o in orders if o.action == "SELL" and o.status == "FILLED")

        return {
            "total_orders": total,
            "filled_orders": filled,
            "cancelled_orders": cancelled,
            "rejected_orders": rejected,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "total_buy_amount": total_buy_amount,
            "total_sell_amount": total_sell_amount,
            "net_position": total_buy_amount - total_sell_amount,
        }


# ========== 便捷函数 ==========

def get_order_history() -> OrderHistory:
    """获取订单历史"""
    return OrderHistory()


__all__ = [
    "OrderHistory",
    "OrderRecord",
    "get_order_history",
]
