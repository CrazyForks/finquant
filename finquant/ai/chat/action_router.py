"""
finquant - 动作路由器

根据意图执行相应操作
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass

from finquant.ai.chat.intent_parser import Intent

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """动作执行结果"""
    success: bool
    message: str = ""
    data: Dict = None
    suggestions: list = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.suggestions is None:
            self.suggestions = []


class ActionRouter:
    """动作路由器"""

    def __init__(self, broker_manager=None, backtest_runner=None):
        self.broker_manager = broker_manager
        self.backtest_runner = backtest_runner

    def execute(self, intent: Intent) -> ActionResult:
        """执行动作"""
        handlers = {
            # 行情/分析
            "query_price": self._handle_query_price,
            "query_trend": self._handle_query_trend,
            "recommend": self._handle_recommend,

            # 交易
            "trade_buy": self._handle_trade_buy,
            "trade_sell": self._handle_trade_sell,

            # 查询
            "query_position": self._handle_query_position,
            "query_order": self._handle_query_order,
            "query_account": self._handle_query_account,
            "query_stats": self._handle_query_stats,

            # 策略
            "strategy_list": self._handle_strategy_list,
            "strategy_start": self._handle_strategy_start,
            "strategy_stop": self._handle_strategy_stop,

            # 设置
            "settings_show": self._handle_settings_show,
            "settings_auto_on": self._handle_settings_auto_on,
            "settings_auto_off": self._handle_settings_auto_off,

            # 优化
            "optimize": self._handle_optimize,
            "backtest": self._handle_backtest,

            # 系统
            "help": self._handle_help,
            "system_clear": self._handle_system_clear,
            "system_exit": self._handle_system_exit,
        }

        handler = handlers.get(intent.type)
        if handler:
            return handler(intent)

        return ActionResult(
            success=False,
            message=f"未知意图: {intent.type}"
        )

    def _handle_query_price(self, intent: Intent) -> ActionResult:
        """查询行情"""
        code = intent.entities.get("code")

        if not code:
            return ActionResult(
                success=False,
                message="请指定股票代码，如: 帮我看看茅台 或 market SH600519"
            )

        try:
            from finquant.trading.broker import EastMoneyQuote
            quotes = EastMoneyQuote.get_quote([code])

            if code not in quotes or not quotes[code].get("price"):
                return ActionResult(
                    success=False,
                    message=f"未找到 {code} 的行情数据"
                )

            q = quotes[code]
            price = q.get("price", 0)
            change = q.get("change_pct", 0) or 0
            name = q.get("name", code)

            # 生成建议
            suggestion = self._generate_price_suggestion(code, price, change)

            return ActionResult(
                success=True,
                message=f"{name} ({code})\n价格: ¥{price:.2f}\n涨跌: {change:+.2f}%\n\n{suggestion}",
                data={"price": price, "change": change, "name": name},
                suggestions=[f"market {code}"]
            )

        except Exception as e:
            logger.error(f"查询行情失败: {e}")
            return ActionResult(success=False, message=f"查询失败: {e}")

    def _handle_query_trend(self, intent: Intent) -> ActionResult:
        """查询走势/分析"""
        code = intent.entities.get("code")

        if not code:
            return ActionResult(
                success=False,
                message="请指定股票代码"
            )

        try:
            from finquant.trading.broker import EastMoneyQuote
            from finquant.data import get_kline

            # 获取行情
            quotes = EastMoneyQuote.get_quote([code])
            if code not in quotes:
                return ActionResult(success=False, message=f"未找到 {code}")

            q = quotes[code]
            price = q.get("price", 0)
            change = q.get("change_pct", 0) or 0

            # 获取K线数据做技术分析
            data = get_kline(code, start="2023-01-01")
            if data is not None and len(data) > 0:
                analysis = self._analyze_technical(data, price)
            else:
                analysis = "数据不足，无法分析"

            return ActionResult(
                success=True,
                message=f"{q.get('name', code)} 分析:\n\n当前价格: ¥{price:.2f} ({change:+.2f}%)\n{analysis}",
                data={"analysis": analysis},
                suggestions=[f"market {code}", f"backtest run {code} 2023-01-01 2023-12-31"]
            )

        except Exception as e:
            logger.error(f"分析失败: {e}")
            return ActionResult(success=False, message=f"分析失败: {e}")

    def _handle_recommend(self, intent: Intent) -> ActionResult:
        """推荐股票"""
        try:
            from finquant.trading.broker import EastMoneyQuote

            # 简单推荐：涨幅前几的指数
            codes = ["SH000001", "SZ399001", "SZ399006"]
            quotes = EastMoneyQuote.get_quote(codes)

            if not quotes:
                return ActionResult(success=False, message="获取推荐失败")

            # 按涨幅排序
            sorted_quotes = sorted(
                [(code, q) for code, q in quotes.items() if q.get("change_pct")],
                key=lambda x: x[1].get("change_pct", 0),
                reverse=True
            )

            lines = ["📈 今日行情:\n"]
            for code, q in sorted_quotes[:3]:
                change = q.get("change_pct", 0) or 0
                lines.append(f"{q.get('name', code)}: {change:+.2f}%")

            lines.append("\n💡 可用命令:")
            lines.append("  market SH600519  # 查看具体股票")

            return ActionResult(
                success=True,
                message="\n".join(lines),
                suggestions=["market SH600519", "market SH000001"]
            )

        except Exception as e:
            logger.error(f"推荐失败: {e}")
            return ActionResult(success=False, message=f"推荐失败: {e}")

    def _handle_trade_buy(self, intent: Intent) -> ActionResult:
        """买入"""
        code = intent.entities.get("code")
        quantity = intent.entities.get("quantity")
        price = intent.entities.get("price")

        if not code:
            return ActionResult(
                success=False,
                message="请指定股票代码，如: 帮我买100股茅台",
                suggestions=["market SH600519"]
            )

        if not quantity:
            return ActionResult(
                success=False,
                message="请指定数量，如: 帮我买100股",
            )

        # 构建命令
        cmd = f"account buy {code} {quantity}"
        if price and price > 0:
            cmd += f" {price}"

        return ActionResult(
            success=True,
            message=f"买入 {code} {quantity}股",
            data={"action": "buy", "code": code, "quantity": quantity},
            suggestions=[cmd]
        )

    def _handle_trade_sell(self, intent: Intent) -> ActionResult:
        """卖出"""
        code = intent.entities.get("code")
        quantity = intent.entities.get("quantity")

        if not code:
            # 查看持仓
            return ActionResult(
                success=True,
                message="请指定要卖出的股票",
                suggestions=["position"]
            )

        cmd = f"account sell {code}"
        if quantity:
            cmd += f" {quantity}"

        return ActionResult(
            success=True,
            message=f"卖出 {code}",
            data={"action": "sell", "code": code},
            suggestions=[cmd]
        )

    def _handle_optimize(self, intent: Intent) -> ActionResult:
        """优化参数"""
        # 支持多个股票代码
        codes = intent.entities.get("codes", [])
        if not codes or codes[0] is None:
            codes = [intent.entities.get("code")]

        if not codes or codes[0] is None:
            return ActionResult(
                success=True,
                message="""📈 参数优化

自动搜索最优策略参数

用法: optimize <codes> <start> <end> [strategy] [metric]
示例:
  optimize SH600519 2023-01-01 2023-12-31 ma_cross total_return
  optimize SH600519 2023-01-01 2023-12-31 rsi sharpe
  optimize SH600519 2023-01-01 2023-12-31 ma_cross max_drawdown

策略类型:
  ma_cross - 均线交叉策略 (默认)
  rsi - RSI 策略

指标说明:
  total_return - 总收益率 (默认)
  sharpe - 夏普比率
  max_drawdown - 最大回撤
""",
                suggestions=[
                    "optimize SH600519 2023-01-01 2023-12-31 ma_cross",
                    "optimize SH600519 2023-01-01 2023-12-31 rsi sharpe"
                ]
            )

        # 获取参数
        period = intent.entities.get("period", "recent")
        start_date, end_date = self._get_date_range(period)

        # 优化指标 (从意图中获取)
        metric = intent.entities.get("metric") or "total_return"

        # 策略类型
        strategy_type = intent.entities.get("strategy") or "ma_cross"

        try:
            from finquant.ai.optimize import get_optimizer

            optimizer = get_optimizer(self.broker_manager)

            # 只优化第一个代码
            code = codes[0]

            print(f"  正在优化 {code} 的 {strategy_type} 策略参数...")
            print(f"  回测区间: {start_date} - {end_date}")
            print(f"  策略类型: {strategy_type}")
            print(f"  优化指标: {metric}")
            print()

            # 根据策略类型选择优化方法
            if strategy_type == "ma_cross":
                result = optimizer.optimize_ma_cross(
                    code=code,
                    start_date=start_date,
                    end_date=end_date,
                    short_range=(3, 20),
                    long_range=(10, 60),
                    metric=metric,
                )
            elif strategy_type == "rsi":
                result = optimizer.optimize_rsi(
                    code=code,
                    start_date=start_date,
                    end_date=end_date,
                    period_range=(5, 30),
                )

            # 格式化结果
            best = result.best_params
            score = result.best_score

            lines = [
                f"✅ 优化完成!",
                f"",
                f"最优参数:",
            ]

            for k, v in best.items():
                lines.append(f"  • {k}: {v}")

            lines.append("")
            lines.append(f"得分: {score:.4f}")
            lines.append(f"耗时: {result.elapsed_time:.2f}秒")
            lines.append("")

            # 生成回测命令
            cmd = f"backtest run {code} {start_date.replace('-','')} {end_date.replace('-','')}"
            for k, v in best.items():
                cmd += f" {k}={v}"

            lines.append(f"💡 验证命令:")
            lines.append(f"  {cmd}")

            return ActionResult(
                success=True,
                message="\n".join(lines),
                suggestions=[cmd]
            )

        except Exception as e:
            logger.error(f"优化失败: {e}")
            import traceback
            traceback.print_exc()
            return ActionResult(
                success=False,
                message=f"优化失败: {e}"
            )

    def _get_date_range(self, period: str) -> tuple:
        """获取日期范围"""
        from datetime import datetime, timedelta

        end_date = datetime.now().strftime("%Y-%m-%d")

        if period == "recent" or period == "1m":
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        elif period == "3m":
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        elif period == "6m":
            start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
        elif period == "1y":
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        else:
            start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

        return start_date, end_date

    def _handle_help(self, intent: Intent) -> ActionResult:
        """帮助"""
        return ActionResult(
            success=True,
            message="""📖 AI 对话助手

支持的操作:
• "帮我看看茅台" - 查询行情
• "茅台走势怎么样" - 技术分析
• "推荐几只股票" - 股票推荐
• "帮我买100股茅台" - 买入股票
• "帮我卖100股" - 卖出股票
• "看看我有什么持仓" - 查询持仓
• "看看我的订单" - 查询订单
• "看看我有多少钱" - 查询账户
• "看看策略" - 查询策略
• "开启自动交易" - 开启自动执行
• "帮我优化参数" - 参数优化

💡 也可以使用命令:
  market SH600519 - 查行情
  position - 查看持仓
  backtest run - 运行回测
""",
            suggestions=["help"]
        )

    def _handle_query_position(self, intent: Intent) -> ActionResult:
        """查询持仓"""
        return ActionResult(
            success=True,
            message="查看持仓",
            suggestions=["position"]
        )

    def _handle_query_order(self, intent: Intent) -> ActionResult:
        """查询订单"""
        return ActionResult(
            success=True,
            message="查看订单",
            suggestions=["order list"]
        )

    def _handle_query_account(self, intent: Intent) -> ActionResult:
        """查询账户"""
        return ActionResult(
            success=True,
            message="查看账户",
            suggestions=["status"]
        )

    def _handle_query_stats(self, intent: Intent) -> ActionResult:
        """查询统计"""
        return ActionResult(
            success=True,
            message="交易统计",
            suggestions=["order stats"]
        )

    def _handle_strategy_list(self, intent: Intent) -> ActionResult:
        """策略列表"""
        return ActionResult(
            success=True,
            message="查看策略列表",
            suggestions=["strategy list"]
        )

    def _handle_strategy_start(self, intent: Intent) -> ActionResult:
        """启动策略"""
        code = intent.entities.get("code")
        if code:
            return ActionResult(
                success=True,
                message=f"启动策略: {code}",
                suggestions=[f"strategy start {code}"]
            )
        return ActionResult(
            success=True,
            message="启动策略",
            suggestions=["strategy list", "strategy start <id>"]
        )

    def _handle_strategy_stop(self, intent: Intent) -> ActionResult:
        """停止策略"""
        code = intent.entities.get("code")
        if code:
            return ActionResult(
                success=True,
                message=f"停止策略: {code}",
                suggestions=[f"strategy stop {code}"]
            )
        return ActionResult(
            success=True,
            message="停止策略",
            suggestions=["strategy list", "strategy stop <id>"]
        )

    def _handle_settings_show(self, intent: Intent) -> ActionResult:
        """显示设置"""
        return ActionResult(
            success=True,
            message="查看系统设置",
            suggestions=["settings show"]
        )

    def _handle_settings_auto_on(self, intent: Intent) -> ActionResult:
        """开启自动交易"""
        return ActionResult(
            success=True,
            message="开启自动交易",
            suggestions=["settings auto on"]
        )

    def _handle_settings_auto_off(self, intent: Intent) -> ActionResult:
        """关闭自动交易"""
        return ActionResult(
            success=True,
            message="关闭自动交易",
            suggestions=["settings auto off"]
        )

    def _handle_backtest(self, intent: Intent) -> ActionResult:
        """回测"""
        code = intent.entities.get("code")
        if code:
            return ActionResult(
                success=True,
                message=f"回测 {code}",
                suggestions=[f"backtest run {code} 2023-01-01 2023-12-31"]
            )
        return ActionResult(
            success=True,
            message="运行回测",
            suggestions=["backtest run SH600519 2023-01-01 2023-12-31"]
        )

    def _handle_system_clear(self, intent: Intent) -> ActionResult:
        """清屏"""
        import os
        os.system("clear" if os.name == "posix" else "cls")
        return ActionResult(
            success=True,
            message="已清屏"
        )

    def _handle_system_exit(self, intent: Intent) -> ActionResult:
        """退出"""
        return ActionResult(
            success=True,
            message="退出系统",
            suggestions=["exit"]
        )

    def _analyze_technical(self, data, price: float) -> str:
        """技术分析"""
        try:
            import pandas as pd

            if len(data) < 20:
                return "数据不足"

            # 计算均线
            close = data['close']
            ma5 = close.tail(5).mean()
            ma20 = close.tail(20).mean()

            # 计算趋势
            if ma5 > ma20:
                trend = "📈 上升趋势 (MA5 > MA20)"
            elif ma5 < ma20:
                trend = "📉 下降趋势 (MA5 < MA20)"
            else:
                trend = "➡️ 横盘整理"

            # 计算RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]

            if current_rsi > 70:
                rsi_status = "⚠️ 超买区域"
            elif current_rsi < 30:
                rsi_status = "⚠️ 超卖区域"
            else:
                rsi_status = "➡️ 正常区域"

            return f"{trend}\n均线: MA5={ma5:.2f}, MA20={ma20:.2f}\nRSI: {current_rsi:.1f} ({rsi_status})"

        except Exception as e:
            logger.error(f"技术分析失败: {e}")
            return "技术分析失败"

    def _generate_price_suggestion(self, code: str, price: float, change: float) -> str:
        """生成价格建议"""
        if change > 3:
            return "涨幅较大，追高需谨慎"
        elif change < -3:
            return "跌幅较大，注意风险"
        elif change > 0:
            return "建议关注支撑位"
        else:
            return "建议观望"


__all__ = ["ActionRouter", "ActionResult"]
