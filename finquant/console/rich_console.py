"""
finquant - 美化控制台界面

参考 Claude Code 风格
"""

import os
import sys
from datetime import datetime
from typing import Optional

from finquant.console.ui import UI


# ========== 主控制台类 ==========

class RichConsole:
    """
    美化控制台

    类似 Claude Code 的交互界面
    """

    def __init__(self):
        from finquant.console.config_store import ConfigStore
        from finquant.console.broker_manager import BrokerManager
        from finquant.console.strategy_manager import get_strategy_runner
        from finquant.console.signal_executor import get_signal_executor
        from finquant.console.order_history import get_order_history
        from finquant.console.command_history import get_command_history
        from finquant.console.backtest_runner import get_backtest_runner

        self.config_store = ConfigStore()
        self.broker_manager = BrokerManager(self.config_store)
        self.strategy_runner = get_strategy_runner(self.broker_manager, self.config_store)
        self.order_history = get_order_history()
        self.signal_executor = get_signal_executor(self.broker_manager, self.config_store)
        self.command_history = get_command_history()
        self.backtest_runner = get_backtest_runner(self.broker_manager, self.config_store)

        # AI 模块
        from finquant.ai.chat.intent_parser import IntentParser
        from finquant.ai.chat.action_router import ActionRouter
        from finquant.ai.chat.response import ResponseFormatter

        self.intent_parser = IntentParser()
        self.action_router = ActionRouter(self.broker_manager, self.backtest_runner)
        self.response_formatter = ResponseFormatter()

        # 命令补全
        try:
            from finquant.console.completer import get_completer
            from prompt_toolkit import PromptSession
            from prompt_toolkit.styles import Style

            self._completer = get_completer()
            self._prompt_style = Style.from_dict({
                'prompt': 'fg:ansicyan',
            })
            self._prompt_session = None
        except ImportError:
            self._completer = None
            self._prompt_session = None

        self._running = True

    def print_welcome(self):
        """打印欢迎界面"""
        # 清屏
        os.system("clear" if os.name == "posix" else "cls")

        # 使用新的 UI
        UI.banner()

    def run(self):
        """运行交互式控制台"""
        self.print_welcome()

        # 交互循环
        while self._running:
            try:
                # 获取自动执行状态
                settings = self.config_store.get_settings()
                auto_enabled = settings.auto_execute_signals

                # 提示符
                active = self.config_store.get_active_broker()
                broker_name = active.name if active else None
                prompt_text = UI.prompt(broker_name, auto_enabled)

                # 使用 prompt_toolkit 获取输入 (支持 Tab 补全)
                if self._completer:
                    try:
                        from prompt_toolkit import PromptSession
                        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

                        # 创建纯文本提示符 (避免 ANSI 颜色问题)
                        # prompt_toolkit 会自动美化显示
                        plain_prompt = "➜ "
                        if broker_name:
                            plain_prompt += f"{broker_name} "
                        if auto_enabled:
                            plain_prompt += "◉ "
                        plain_prompt += "│ "

                        session = PromptSession(
                            message=plain_prompt,
                            completer=self._completer,
                            style=self._prompt_style,
                            enable_history_search=True,
                            auto_suggest=AutoSuggestFromHistory(),
                            complete_while_typing=True,
                        )
                        command = session.prompt()
                    except Exception as e:
                        print(f"Warning: PromptSession failed: {e}")
                        command = input(prompt_text).strip()
                else:
                    command = input(prompt_text).strip()

                if not command:
                    continue

                # 保存命令历史
                self.command_history.add(command)

                # 检测 AI 请求 (智能融合)
                if self._is_ai_request(command):
                    self._handle_ai_request(command)
                    continue

                # 解析命令
                parts = command.split()
                cmd = parts[0].lower()
                args = parts[1:]

                # 执行命令
                self._execute_command(cmd, args)

            except KeyboardInterrupt:
                print("\n" + UI.C["bright_black"] + "  Use 'exit' to quit" + UI.C["reset"])
            except EOFError:
                break
            except Exception as e:
                UI.error(str(e))

        print(UI.C["bright_black"] + "\n  Goodbye!\n" + UI.C["reset"])

    def _is_ai_request(self, text: str) -> bool:
        """检测是否为 AI 请求"""
        # 去除 / 前缀
        text = text.lstrip("/")

        # 使用 IntentParser 检测
        return self.intent_parser.is_ai_request(text)

    def _handle_ai_request(self, command: str):
        """处理 AI 请求"""
        # 去除 / 前缀
        command = command.lstrip("/")

        # 解析意图
        intent = self.intent_parser.parse(command)

        # 执行动作
        result = self.action_router.execute(intent)

        # 格式化输出
        print(self.response_formatter.format(result))

    def _show_command_hint(self, cmd: str):
        """显示命令使用提示 - 一行真实示例，用户可直接复制使用"""
        examples = {
            "broker": "例如: broker add simulated 我的账户",
            "account": "例如: account buy SH600519 100 或 account sell SH600519 50 180.50",
            "position": "例如: position",
            "market": "例如: market SH600519 SH000001",
            "order": "例如: order list 或 order stats",
            "strategy": "例如: strategy add ma_cross 均线策略 或 strategy start xxx",
            "backtest": "例如: backtest run SH600519,SH000001 2023-01-01 2023-12-31 strategy=ma_cross short_period=5 long_period=20",
            "settings": "例如: settings auto on 或 settings set max_position_pct 0.3",
            "status": "例如: status",
            "help": "例如: help 或 help broker",
            "optimize": "例如: optimize SH600519,SH000001 2023-01-01 2023-12-31 total_return",
        }

        if cmd in examples:
            print(f"\n{UI.C['dim']}│ {examples[cmd]}{UI.C['reset']}")

    def _execute_command(self, cmd: str, args: list):
        """执行命令"""
        if cmd == "help" or cmd == "?":
            if not args:
                self._show_help()
            else:
                self._execute_command(args[0], args[1:])

        elif cmd == "exit" or cmd == "quit" or cmd == "q":
            self._running = False

        elif cmd == "clear" or cmd == "cls":
            os.system("clear" if os.name == "posix" else "cls")
            self.print_welcome()

        elif cmd == "status":
            if not args:
                self._show_status()
            else:
                self._show_command_hint("status")

        elif cmd == "broker":
            if not args:
                self._broker_list()
                self._show_command_hint("broker")
            else:
                self._broker_command(args)

        elif cmd == "account":
            if not args:
                self._show_status()
            else:
                self._account_command(args)

        elif cmd == "position" or cmd == "pos":
            self._show_positions()

        elif cmd == "market" or cmd == "mkt":
            if not args:
                self._show_command_hint("market")
            else:
                self._show_market(args)

        elif cmd == "order":
            if not args:
                self._order_command(args)
            else:
                self._order_command(args)

        elif cmd == "strategy":
            if not args:
                self._strategy_command([])
                self._show_command_hint("strategy")
            else:
                self._strategy_command(args)

        elif cmd == "settings":
            if not args:
                self._show_settings()
                self._show_command_hint("settings")
            else:
                self._settings_command(args)

        elif cmd == "backtest":
            if not args:
                self._backtest_command(["help"])
                self._show_command_hint("backtest")
            else:
                self._backtest_command(args)

        elif cmd == "optimize":
            # 使用 AI 处理优化请求
            if not args:
                self._handle_ai_request("优化")
            else:
                # 添加 "优化" 前缀，让意图解析器能正确识别
                self._handle_ai_request("优化 " + " ".join(args))

        else:
            UI.warning(f"Unknown command: {cmd}")

    def _show_help(self):
        """显示帮助"""
        UI.separator()
        UI.header("Available Commands")

        commands = [
            ("broker", "券商管理", "add, list, remove, active"),
            ("account", "账户操作", "buy, sell"),
            ("position", "持仓查询", "view positions"),
            ("market", "行情查询", "get quotes"),
            ("order", "订单操作", "list, stats"),
            ("strategy", "策略管理", "add, start, stop"),
            ("backtest", "回测功能", "run, save, show"),
            ("settings", "系统设置", "show, auto"),
            ("status", "系统状态", "view status"),
            ("exit", "退出", "quit"),
        ]

        UI.table(["Command", "Description", "Usage"], commands, [12, 18, 35])

    def _show_status(self):
        """显示状态"""
        UI.separator("Status")

        # 券商
        active = self.config_store.get_active_broker()
        if active:
            UI.item("Broker", f"{active.name} ({active.broker_type})", "success")

            try:
                broker = self.broker_manager.get_active_broker()
                if broker and broker.is_available():
                    account = broker.get_account()
                    UI.item("Cash", f"¥{account.cash:,.2f}")
                    UI.item("Market Value", f"¥{account.market_value:,.2f}")
                    UI.item("Total Assets", f"¥{account.total_assets:,.2f}")
            except:
                pass
        else:
            UI.item("Broker", "None configured", "warning")

        # 策略
        strategies = self.strategy_runner.list_strategies()
        running = sum(1 for s in strategies if s.is_running)
        UI.item("Strategies", f"{running}/{len(strategies)} running")

        # 自动执行
        settings = self.config_store.get_settings()
        UI.item("Auto Execute", "Enabled" if settings.auto_execute_signals else "Disabled")

    def _broker_command(self, args: list):
        """券商命令"""
        if not args:
            self._broker_list()
            return

        sub_cmd = args[0].lower()

        if sub_cmd == "list":
            self._broker_list()
        elif sub_cmd == "add":
            self._broker_add(args[1:])
        elif sub_cmd == "remove" or sub_cmd == "del":
            self._broker_remove(args[1:])
        elif sub_cmd == "active" or sub_cmd == "switch":
            self._broker_active(args[1:])
        else:
            UI.warning(f"Unknown subcommand: {sub_cmd}")

    def _broker_list(self):
        """券商列表"""
        brokers = self.broker_manager.list_broker_configs()

        if not brokers:
            UI.info("  No brokers. Use 'broker add' to add one.")
            return

        UI.header("Brokers")
        rows = [[b.id[:18], b.name, b.broker_type, "✓" if b.is_active else ""] for b in brokers]
        UI.table(["ID", "Name", "Type", "Active"], rows, [20, 15, 12, 8])

    def _broker_add(self, args: list):
        """添加券商"""
        if len(args) < 2:
            UI.info("  Usage: broker add <type> <name>")
            UI.info("  Types: simulated, huatai")
            return

        broker_type = args[0]
        name = " ".join(args[1:])

        if broker_type == "simulated":
            config = {"initial_cash": 100000}
        elif broker_type == "huatai":
            config = {"account_id": "", "password": "", "simulated": True}
        else:
            UI.error(f"Unknown type: {broker_type}")
            return

        broker_id = self.broker_manager.add_broker(name, broker_type, config)
        UI.success(f"Added broker: {name} ({broker_id})")

    def _broker_remove(self, args: list):
        """删除券商"""
        if not args:
            UI.info("  Usage: broker remove <id>")
            return

        if self.broker_manager.remove_broker(args[0]):
            UI.success("Broker removed")
        else:
            UI.error("Broker not found")

    def _broker_active(self, args: list):
        """切换券商"""
        if not args:
            UI.info("  Usage: broker active <id>")
            return

        if self.broker_manager.set_active_broker(args[0]):
            UI.success("Switched broker")
        else:
            UI.error("Broker not found")

    def _account_command(self, args: list):
        """账户命令"""
        if not args:
            self._show_status()
            return

        sub_cmd = args[0].lower()

        if sub_cmd == "buy":
            self._account_buy(args[1:])
        elif sub_cmd == "sell":
            self._account_sell(args[1:])
        else:
            UI.warning(f"Unknown subcommand: {sub_cmd}")

    def _account_buy(self, args: list):
        """买入"""
        if len(args) < 2:
            UI.info("  Usage: account buy <code> <quantity> [price]")
            return

        code = args[0]
        quantity = int(args[1])
        price = float(args[2]) if len(args) > 2 else 0

        # 获取实时价格
        if price == 0:
            from finquant.trading.broker import EastMoneyQuote
            quote = EastMoneyQuote.get_quote([code]).get(code, {})
            price = quote.get("price", 0)
            if price > 0:
                UI.info(f"  Got real-time price: ¥{price}")

        try:
            order = self.broker_manager.buy(code, quantity, price)
            if order.status.value == "FILLED":
                UI.success(f"Bought {code}: {quantity} @ ¥{order.avg_price}")
            else:
                UI.error(f"Buy failed: {order.message}")
        except Exception as e:
            UI.error(str(e))

    def _account_sell(self, args: list):
        """卖出"""
        if len(args) < 2:
            UI.info("  Usage: account sell <code> <quantity> [price]")
            return

        code = args[0]
        quantity = int(args[1])
        price = float(args[2]) if len(args) > 2 else 0

        try:
            order = self.broker_manager.sell(code, quantity, price)
            if order.status.value == "FILLED":
                UI.success(f"Sold {code}: {quantity} @ ¥{order.avg_price}")
            else:
                UI.error(f"Sell failed: {order.message}")
        except Exception as e:
            UI.error(str(e))

    def _show_positions(self):
        """显示持仓"""
        try:
            broker = self.broker_manager.get_active_broker()
            if not broker:
                UI.warning("No active broker")
                return

            positions = broker.get_positions()

            if not positions:
                UI.info("  No positions")
                return

            UI.header("Positions")
            rows = []
            for p in positions:
                profit = p.profit
                profit_pct = p.profit_ratio * 100 if p.profit_ratio else 0
                status = "success" if profit >= 0 else "error"
                rows.append([p.code, str(p.shares), f"¥{p.avg_cost:.2f}", f"¥{p.current_price:.2f}", f"{profit:+.2f} ({profit_pct:+.2f}%)", status])

            UI.table(["Code", "Shares", "Cost", "Price", "P/L", ""], rows, [10, 8, 10, 10, 18, 0])

            # 汇总
            account = broker.get_account()
            UI.item("Cash", f"¥{account.cash:,.2f}")
            UI.item("Market Value", f"¥{account.market_value:,.2f}")
            UI.item("Total", f"¥{account.total_assets:,.2f}")

        except Exception as e:
            UI.error(str(e))

    def _show_market(self, codes: list):
        """显示行情"""
        if not codes:
            UI.info("  Usage: market <code> [code2 ...]")
            return

        from finquant.trading.broker import EastMoneyQuote
        quotes = EastMoneyQuote.get_quote(codes)

        if not quotes:
            UI.error("Failed to get quotes")
            return

        UI.header("Quotes")
        rows = []
        for code in codes:
            if code in quotes:
                q = quotes[code]
                price = q.get("price", 0)
                change = q.get("change_pct", 0) or 0
                status = "success" if change >= 0 else "error"
                rows.append([code, q.get("name", "")[:8], f"¥{price:.2f}", f"{change:+.2f}%", status])

        UI.table(["Code", "Name", "Price", "Change", ""], rows, [10, 10, 10, 10, 0])

    def _order_command(self, args: list):
        """订单命令"""
        if not args or args[0] == "list":
            orders = self.order_history.get_orders(limit=10)
            if not orders:
                UI.info("  No orders")
                return

            UI.header("Orders")
            rows = [[o.order_id[:16], o.code, o.action, str(o.quantity), f"¥{o.avg_price:.2f}", o.status] for o in orders]
            UI.table(["Order ID", "Code", "Action", "Qty", "Price", "Status"], rows, [18, 8, 6, 8, 10, 10])

        elif args[0] == "stats":
            stats = self.order_history.get_stats()
            UI.header("Order Stats")
            UI.item("Total Orders", str(stats["total_orders"]))
            UI.item("Filled", str(stats["filled_orders"]))
            UI.item("Buy Amount", f"¥{stats['total_buy_amount']:,.2f}")
            UI.item("Sell Amount", f"¥{stats['total_sell_amount']:,.2f}")

    def _strategy_command(self, args: list):
        """策略命令"""
        if not args:
            strategies = self.strategy_runner.list_strategies()
            if not strategies:
                UI.info("  No strategies")
                return

            UI.header("Strategies")
            rows = [[s.id[:16], s.name, s.strategy_type, "Running" if s.is_running else "Stopped"] for s in strategies]
            UI.table(["ID", "Name", "Type", "Status"], rows, [18, 15, 12, 10])
            return

        sub_cmd = args[0].lower()

        if sub_cmd == "list":
            self._strategy_command([])
        elif sub_cmd == "add":
            if len(args) < 3:
                UI.info("  Usage: strategy add <type> <name> [params]")
                return
            strategy_id = self.strategy_runner.add_strategy(args[2], args[1], {})
            UI.success(f"Added strategy: {args[2]} ({strategy_id})")
        elif sub_cmd == "start":
            if len(args) < 2:
                UI.info("  Usage: strategy start <id>")
                return
            if self.strategy_runner.start_strategy(args[1]):
                UI.success("Strategy started")
            else:
                UI.error("Failed to start strategy")
        elif sub_cmd == "stop":
            if len(args) < 2:
                UI.info("  Usage: strategy stop <id>")
                return
            if self.strategy_runner.stop_strategy(args[1]):
                UI.success("Strategy stopped")
            else:
                UI.error("Failed to stop strategy")

    def _settings_command(self, args: list):
        """设置命令"""
        if not args:
            self._show_settings()
            return

        sub_cmd = args[0].lower()

        if sub_cmd == "show":
            self._show_settings()
        elif sub_cmd == "auto":
            if len(args) < 2:
                settings = self.config_store.get_settings()
                UI.info(f"  Auto execute: {'Enabled' if settings.auto_execute_signals else 'Disabled'}")
                return

            if args[1].lower() in ["on", "enable", "true"]:
                self.config_store.update_settings(auto_execute_signals=True)
                self.signal_executor.enable()
                UI.success("Auto execute enabled")
            else:
                self.config_store.update_settings(auto_execute_signals=False)
                self.signal_executor.disable()
                UI.success("Auto execute disabled")
        elif sub_cmd == "set":
            if len(args) < 3:
                UI.info("  Usage: settings set <key> <value>")
                return
            key, value = args[1], args[2]
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.isdigit():
                value = int(value)
            elif value.replace(".", "", 1).isdigit():
                value = float(value)
            self.config_store.update_settings(**{key: value})
            UI.success(f"{key} = {value}")

    def _show_settings(self):
        """显示设置"""
        settings = self.config_store.get_settings()

        UI.header("Settings")

        UI.item("Auto Execute", "Enabled" if settings.auto_execute_signals else "Disabled")
        UI.item("Buy Ratio", f"{settings.auto_buy_ratio * 100:.0f}%")
        UI.item("Sell All", "Yes" if settings.auto_sell_all else "No")
        UI.item("Max Position", f"{settings.max_position_pct * 100:.0f}%")
        UI.item("Max Total", f"{settings.max_total_position * 100:.0f}%")
        UI.item("Stop Loss", f"{'Enabled' if settings.enable_stop_loss else 'Disabled'} ({settings.stop_loss_pct * 100:.0f}%)")
        UI.item("Take Profit", f"{'Enabled' if settings.enable_take_profit else 'Disabled'} ({settings.take_profit_pct * 100:.0f}%)")

    def _backtest_command(self, args: list):
        """回测命令"""
        if not args or args[0] == "help":
            UI.header("Backtest Commands")
            UI.info("  backtest run <codes> <start> <end> [params]")
            UI.info("  backtest save <name> <codes> <start> <end> [params]")
            UI.info("  backtest show [code]")
            UI.info("  backtest trades [code]")
            return

        sub_cmd = args[0].lower()

        if sub_cmd == "run":
            self._backtest_run(args[1:])
        elif sub_cmd == "save":
            self._backtest_save(args[1:])
        elif sub_cmd == "show":
            code = args[1] if len(args) > 1 else None
            self.backtest_runner.show_chart(code)
        elif sub_cmd == "trades":
            code = args[1] if len(args) > 1 else None
            self.backtest_runner.show_trades(code)

    def _backtest_run(self, args: list):
        """运行回测

        用法: backtest run <codes> <start> <end> [params]
        示例: backtest run SH600519 2023-01-01 2023-12-31 strategy=ma_cross short_period=5 long_period=20 initial_capital=100000
        """
        if len(args) < 3:
            UI.info("  Usage: backtest run <codes> <start> <end> [params]")
            UI.info("  示例: backtest run SH600519 2023-01-01 2023-12-31 strategy=ma_cross short_period=5 long_period=20")
            return

        codes = args[0].split(",")
        start_date = args[1]
        end_date = args[2]

        # 自动转换日期格式 YYYYMMDD -> YYYY-MM-DD
        if len(start_date) == 8 and start_date.isdigit():
            start_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        if len(end_date) == 8 and end_date.isdigit():
            end_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

        # 解析参数
        strategy_type = "ma_cross"  # 默认策略
        initial_capital = 100000    # 默认初始资金
        params = {}

        for arg in args[3:]:
            if "=" in arg:
                key, value = arg.split("=", 1)
                # 提取特殊参数
                if key == "strategy":
                    strategy_type = value
                elif key == "initial_capital":
                    initial_capital = float(value)
                else:
                    # 策略参数
                    if value.isdigit():
                        value = int(value)
                    elif value.replace(".", "").isdigit():
                        value = float(value)
                    params[key] = value

        UI.info(f"  Running backtest for {', '.join(codes)}...")
        UI.info(f"  Period: {start_date} - {end_date}")
        UI.info(f"  Strategy: {strategy_type}, Capital: {initial_capital}, Params: {params}")

        try:
            results = self.backtest_runner.run(
                codes, start_date, end_date,
                strategy_type=strategy_type,
                initial_capital=initial_capital,
                params=params
            )
            self.backtest_runner.print_results(results)
        except Exception as e:
            UI.error(f"Backtest failed: {e}")

    def _backtest_save(self, args: list):
        """保存策略配置"""
        if len(args) < 5:
            UI.info("  Usage: backtest save <name> <codes> <start> <end> [params]")
            return

        name = args[0]
        codes = args[1]
        start_date = args[2]
        end_date = args[3]

        params = {"_codes": codes, "_start_date": start_date, "_end_date": end_date}

        for arg in args[4:]:
            if "=" in arg:
                key, value = arg.split("=", 1)
                if value.isdigit():
                    value = int(value)
                elif value.replace(".", "").isdigit():
                    value = float(value)
                params[key] = value

        strategy_id = self.config_store.add_strategy_config(name, "ma_cross", params)
        UI.success(f"Saved strategy config: {name} ({strategy_id})")


# ========== 入口函数 ==========

def main():
    """CLI 入口点"""
    start_rich_console()


def start_rich_console():
    """启动美化控制台"""
    console = RichConsole()
    console.run()


__all__ = [
    "RichConsole",
    "start_rich_console",
]
