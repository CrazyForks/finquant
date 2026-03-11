"""
finquant - 交互式控制台

提供命令行交互界面进行实盘交易
"""

import cmd
import json
import logging
import sys
from typing import Optional

from finquant.console.config_store import ConfigStore
from finquant.console.broker_manager import BrokerManager
from finquant.console.strategy_manager import StrategyRunner, get_strategy_runner
from finquant.console.signal_executor import SignalExecutor, get_signal_executor
from finquant.console.order_history import OrderHistory, get_order_history
from finquant.trading.broker import EastMoneyQuote
from finquant.trading.signal import Signal, Action

logger = logging.getLogger(__name__)


class TradingConsole(cmd.Cmd):
    """
    实盘交易交互控制台

    支持的命令:
    - broker: 券商管理
    - account: 账户操作
    - position: 持仓查询
    - market: 行情查询
    - order: 订单操作
    - strategy: 策略管理
    - backtest: 回测
    - settings: 系统设置
    - help: 帮助
    - exit: 退出
    """

    intro = """
╔═══════════════════════════════════════════════════════════╗
║           finquant 实盘交易控制台 v1.0                     ║
║                                                           ║
║  输入 help 查看可用命令                                    ║
║  输入 exit 退出                                           ║
╚═══════════════════════════════════════════════════════════╝
"""

    prompt = "finquant> "

    def __init__(self):
        super().__init__()

        self.config_store = ConfigStore()
        self.broker_manager = BrokerManager(self.config_store)
        self.strategy_runner = get_strategy_runner(self.broker_manager, self.config_store)
        self.order_history = get_order_history()
        self.signal_executor = get_signal_executor(self.broker_manager, self.config_store)

        # 当前会话状态
        self._current_menu: Optional[str] = None

        # 设置信号处理器
        self._setup_signal_handler()

    def _setup_signal_handler(self):
        """设置信号处理器"""
        def handle_signal(signal: Signal, context: dict):
            """处理信号"""
            print(f"\n[信号] {signal.action.value} {signal.code}")
            print(f"  原因: {signal.reason}")

            # 使用信号执行器处理
            settings = self.config_store.get_settings()
            if settings.auto_execute_signals:
                # 自动执行
                success = self.signal_executor.execute(signal)
                if success:
                    print(f"  -> 自动执行成功")
                else:
                    print(f"  -> 自动执行失败或跳过")
            else:
                print(f"  -> 自动执行未启用 (settings auto_execute_signals=false)")

        self.strategy_runner.subscribe_signal(handle_signal)

    # ========== 通用方法 ==========

    def do_help(self, arg):
        """显示帮助"""
        if arg:
            # 显示特定命令帮助
            self._show_command_help(arg)
        else:
            self._show_main_help()

    def _show_main_help(self):
        """显示主菜单帮助"""
        print("""
可用命令:
  broker     - 券商管理 (添加、删除、切换券商)
  account    - 账户操作 (买入、卖出、查询)
  position   - 持仓查询 (查看当前持仓和盈亏)
  market     - 行情查询 (实时行情)
  order      - 订单操作 (撤单、订单历史)
  strategy   - 策略管理 (添加、启动、停止策略)
  backtest   - 回测功能
  settings   - 系统设置
  status     - 系统状态
  help       - 显示帮助
  exit       - 退出
        """)

    def _show_command_help(self, command: str):
        """显示特定命令帮助"""
        help_text = {
            "broker": """
券商管理:
  broker list              - 列出所有券商
  broker add <type> <name> - 添加券商
  broker remove <id>       - 删除券商
  broker active <id>       - 切换券商

券商类型:
  simulated               - 模拟券商
  huatai                  - 华泰证券

示例:
  broker add simulated 我的模拟账户
  broker add huatai 华泰实盘
  broker active sim_001
            """,
            "account": """
账户操作:
  account                  - 显示账户摘要
  account buy <code> <qty> [price] - 买入
  account sell <code> <qty> [price] - 卖出
  account history          - 订单历史

示例:
  account buy SH600519 100
  account buy SH600519 100 1500.0
  account sell SH600519 50
            """,
            "position": """
持仓查询:
  position                 - 显示所有持仓
  position <code>          - 显示特定持仓

示例:
  position
  position SH600519
            """,
            "market": """
行情查询:
  market <code>            - 查询单只股票行情
  market <code1> <code2>   - 查询多只股票行情
  market watch <code1> <code2> - 持续监视行情 (Ctrl+C 停止)

示例:
  market SH600 SH600519 SZ519
  market000001
            """,
        }

        if command in help_text:
            print(help_text[command])
        else:
            print(f"未知命令: {command}")

    def do_exit(self, arg):
        """退出"""
        print("再见!")
        return True

    def do_quit(self, arg):
        """退出"""
        return self.do_exit(arg)

    def do_EOF(self, arg):
        """Ctrl+D 退出"""
        print()
        return True

    # ========== 状态命令 ==========

    def do_status(self, arg):
        """显示系统状态"""
        print("\n" + "=" * 50)
        print("系统状态")
        print("=" * 50)

        # 券商状态
        brokers = self.broker_manager.list_broker_configs()
        print(f"\n券商数量: {len(brokers)}")

        active = self.config_store.get_active_broker()
        if active:
            print(f"当前券商: {active.name} ({active.broker_type})")

            # 显示账户
            try:
                broker = self.broker_manager.get_active_broker()
                if broker and broker.is_available():
                    account = broker.get_account()
                    print(f"\n账户信息:")
                    print(f"  现金: {account.cash:.2f}")
                    print(f"  持仓市值: {account.market_value:.2f}")
                    print(f"  总资产: {account.total_assets:.2f}")
                    print(f"  持仓数: {len(account.positions)}")
            except Exception as e:
                print(f"  账户查询失败: {e}")
        else:
            print("当前券商: 无")

        print()

    # ========== 券商命令 ==========

    def do_broker(self, arg):
        """券商管理"""
        args = arg.strip().split()

        if not args:
            self._broker_list()
            return

        cmd = args[0]

        if cmd == "list":
            self._broker_list()
        elif cmd == "add":
            self._broker_add(args[1:])
        elif cmd == "remove" or cmd == "del":
            self._broker_remove(args[1:])
        elif cmd == "active" or cmd == "switch":
            self._broker_active(args[1:])
        else:
            print(f"未知命令: broker {cmd}")

    def _broker_list(self):
        """列出券商"""
        brokers = self.broker_manager.list_broker_configs()

        print("\n券商列表:")
        print("-" * 60)
        print(f"{'ID':<20} {'名称':<15} {'类型':<10} {'状态':<10}")
        print("-" * 60)

        for b in brokers:
            status = "✓ 激活" if b.is_active else ""
            print(f"{b.id:<20} {b.name:<15} {b.broker_type:<10} {status:<10}")

        print("-" * 60)

    def _broker_add(self, args):
        """添加券商"""
        if len(args) < 2:
            print("用法: broker add <type> <name> [初始资金]")
            print("类型: simulated, huatai")
            return

        broker_type = args[0]
        name = " ".join(args[1:]) if len(args) > 2 else args[1]
        initial_cash = int(args[2]) if len(args) > 2 else 100000

        if broker_type == "simulated":
            config = {"initial_cash": initial_cash}
        elif broker_type == "huatai":
            print("华泰证券需要配置: account_id, password, app_key, app_secret")
            print("使用 broker add huatai <name> 后会自动提示输入")
            config = {
                "account_id": "",
                "password": "",
                "app_key": "",
                "app_secret": "",
                "simulated": True,
            }
        else:
            print(f"未知类型: {broker_type}")
            return

        broker_id = self.broker_manager.add_broker(name, broker_type, config)
        print(f"\n[成功] 添加券商: {name} (ID: {broker_id})")

    def _broker_remove(self, args):
        """删除券商"""
        if not args:
            print("用法: broker remove <id>")
            return

        broker_id = args[0]
        if self.broker_manager.remove_broker(broker_id):
            print(f"[成功] 删除券商: {broker_id}")
        else:
            print(f"[失败] 券商不存在: {broker_id}")

    def _broker_active(self, args):
        """切换券商"""
        if not args:
            print("用法: broker active <id>")
            return

        broker_id = args[0]
        if self.broker_manager.set_active_broker(broker_id):
            print(f"[成功] 切换到券商: {broker_id}")
        else:
            print(f"[失败] 券商不存在: {broker_id}")

    # ========== 账户命令 ==========

    def do_account(self, arg):
        """账户操作"""
        args = arg.strip().split()

        if not args:
            self._account_summary()
            return

        cmd = args[0]

        if cmd == "buy":
            self._account_buy(args[1:])
        elif cmd == "sell":
            self._account_sell(args[1:])
        elif cmd == "history":
            self._account_history()
        else:
            print(f"未知命令: account {cmd}")

    def _account_summary(self):
        """账户摘要"""
        try:
            broker = self.broker_manager.get_active_broker()
            if not broker:
                print("[错误] 没有激活的券商")
                return

            account = broker.get_account()

            print("\n账户摘要:")
            print("-" * 40)
            print(f"现金:     {account.cash:>12.2f}")
            print(f"持仓市值: {account.market_value:>12.2f}")
            print(f"总资产:   {account.total_assets:>12.2f}")
            print("-" * 40)

            if account.positions:
                print("\n持仓明细:")
                print(f"{'代码':<10} {'股数':>8} {'成本':>10} {'现价':>10} {'盈亏':>12}")
                print("-" * 50)
                for p in account.positions:
                    print(f"{p.code:<10} {p.shares:>8} {p.avg_cost:>10.2f} {p.current_price:>10.2f} {p.profit:>12.2f}")

        except Exception as e:
            print(f"[错误] {e}")

    def _account_buy(self, args):
        """买入"""
        if len(args) < 2:
            print("用法: account buy <code> <quantity> [price]")
            print("示例: account buy SH600519 100")
            print("       account buy SH600519 100 1500.0")
            return

        code = args[0]
        quantity = int(args[1])
        price = float(args[2]) if len(args) > 2 else 0

        # 如果没有指定价格，尝试获取实时行情
        if price == 0:
            quote = EastMoneyQuote.get_quote([code]).get(code, {})
            price = quote.get("price", 0)
            if price > 0:
                print(f"获取到实时价格: {price}")

        try:
            order = self.broker_manager.buy(code, quantity, price)
            print(f"\n[委托成功] 订单号: {order.order_id}")
            print(f"  代码: {order.code}")
            print(f"  数量: {order.quantity}")
            print(f"  价格: {order.price if order.price > 0 else '市价'}")
            print(f"  状态: {order.status.value}")
            if order.message:
                print(f"  备注: {order.message}")
        except Exception as e:
            print(f"[错误] {e}")

    def _account_sell(self, args):
        """卖出"""
        if len(args) < 2:
            print("用法: account sell <code> <quantity> [price]")
            return

        code = args[0]
        quantity = int(args[1])
        price = float(args[2]) if len(args) > 2 else 0

        # 如果没有指定价格，尝试获取实时行情
        if price == 0:
            quote = EastMoneyQuote.get_quote([code]).get(code, {})
            price = quote.get("price", 0)
            if price > 0:
                print(f"获取到实时价格: {price}")

        try:
            order = self.broker_manager.sell(code, quantity, price)
            print(f"\n[委托成功] 订单号: {order.order_id}")
            print(f"  代码: {order.code}")
            print(f"  数量: {order.quantity}")
            print(f"  价格: {order.price if order.price > 0 else '市价'}")
            print(f"  状态: {order.status.value}")
            if order.message:
                print(f"  备注: {order.message}")
        except Exception as e:
            print(f"[错误] {e}")

    def _account_history(self):
        """订单历史"""
        print("订单历史 (暂未实现)")

    # ========== 持仓命令 ==========

    def do_position(self, arg):
        """持仓查询"""
        args = arg.strip().split()

        try:
            if args:
                code = args[0]
                self._position_detail(code)
            else:
                self._position_list()
        except Exception as e:
            print(f"[错误] {e}")

    def _position_list(self):
        """持仓列表"""
        positions = self.broker_manager.get_positions()

        if not positions:
            print("\n当前无持仓")
            return

        print(f"\n持仓 ({len(positions)} 只):")
        print(f"{'代码':<10} {'股数':>8} {'成本':>10} {'现价':>10} {'盈亏':>12} {'盈亏率':>10}")
        print("-" * 70)

        total_profit = 0
        for p in positions:
            profit_ratio = p.profit_ratio * 100 if p.profit_ratio else 0
            print(f"{p.code:<10} {p.shares:>8} {p.avg_cost:>10.2f} {p.current_price:>10.2f} {p.profit:>12.2f} {profit_ratio:>9.2f}%")
            total_profit += p.profit

        print("-" * 70)

        # 账户汇总
        account = self.broker_manager.get_account()
        print(f"\n账户汇总:")
        print(f"  现金: {account.cash:.2f}")
        print(f"  持仓市值: {account.market_value:.2f}")
        print(f"  总资产: {account.total_assets:.2f}")
        print(f"  总盈亏: {total_profit:.2f}")

    def _position_detail(self, code: str):
        """持仓详情"""
        positions = self.broker_manager.get_positions()

        for p in positions:
            if p.code == code:
                print(f"\n{p.code} 持仓详情:")
                print("-" * 40)
                print(f"股数:      {p.shares}")
                print(f"成本:      {p.avg_cost:.2f}")
                print(f"当前价:    {p.current_price:.2f}")
                print(f"市值:      {p.market_value:.2f}")
                print(f"盈亏:      {p.profit:.2f}")
                print(f"盈亏率:    {p.profit_ratio * 100:.2f}%")
                print("-" * 40)
                return

        print(f"无 {code} 的持仓")

    # ========== 行情命令 ==========

    def do_market(self, arg):
        """行情查询"""
        args = arg.strip().split()

        if not args:
            print("用法: market <code> [code2 ...]")
            print("示例: market SH600519")
            print("       market SH600519 SZ000001")
            return

        if args[0] == "watch":
            self._market_watch(args[1:])
        else:
            self._market_quote(args)

    def _market_quote(self, codes: list):
        """查询行情"""
        quotes = EastMoneyQuote.get_quote(codes)

        if not quotes:
            print("获取行情失败")
            return

        print(f"\n行情 ({len(quotes)} 只):")
        print(f"{'代码':<10} {'名称':<12} {'现价':>10} {'涨跌':>10} {'涨跌幅':>10}")
        print("-" * 55)

        for code in codes:
            if code in quotes:
                q = quotes[code]
                change = q.get("change", 0) or 0
                pct = q.get("change_pct", 0) or 0
                print(f"{code:<10} {q.get('name', ''):<12} {q.get('price', 0):>10.2f} {change:>10.2f} {pct:>9.2f}%")

    def _market_watch(self, codes: list):
        """持续监视行情"""
        if not codes:
            print("用法: market watch <code> [code2 ...]")
            return

        print(f"监视行情: {', '.join(codes)}")
        print("按 Ctrl+C 停止\n")

        import time
        try:
            while True:
                quotes = EastMoneyQuote.get_quote(codes)
                print(f"[{time.strftime('%H:%M:%S')}] ", end="")
                for code in codes:
                    if code in quotes:
                        q = quotes[code]
                        pct = q.get("change_pct", 0) or 0
                        print(f"{code}: {q.get('price', 0):.2f} ({pct:+.2f}%) ", end="")
                print()
                time.sleep(3)
        except KeyboardInterrupt:
            print("\n已停止监视")

    # ========== 设置命令 ==========

    def do_settings(self, arg):
        """系统设置"""
        args = arg.strip().split()

        if not args:
            self._settings_show()
            return

        cmd = args[0]

        if cmd == "show":
            self._settings_show()
        elif cmd == "set":
            self._settings_set(args[1:])
        elif cmd == "auto":
            self._settings_auto(args[1:])
        elif cmd == "enable":
            self._settings_enable(args[1:])
        elif cmd == "disable":
            self._settings_disable(args[1:])
        else:
            print(f"未知命令: settings {cmd}")

    def _settings_show(self):
        """显示设置"""
        settings = self.config_store.get_settings()
        auto_status = "✓ 启用" if self.signal_executor.is_enabled() else "✗ 禁用"

        print("\n系统设置:")
        print("=" * 50)
        print("【自动执行】")
        print(f"  自动执行:   {auto_status}")
        print(f"  买入比例:   {settings.auto_buy_ratio * 100:.0f}% (每次买入可用资金比例)")
        print(f"  卖出方式:   {'全卖' if settings.auto_sell_all else '卖一半'}")
        print()
        print("【仓位控制】")
        print(f"  单票最大:   {settings.max_position_pct * 100:.0f}%")
        print(f"  总仓位上限: {settings.max_total_position * 100:.0f}%")
        print(f"  最低现金:   {settings.min_cash_ratio * 100:.0f}%")
        print()
        print("【风控设置】")
        print(f"  止损:      {'启用' if settings.enable_stop_loss else '禁用'} ({settings.stop_loss_pct * 100:.0f}%)")
        print(f"  止盈:      {'启用' if settings.enable_take_profit else '禁用'} ({settings.take_profit_pct * 100:.0f}%)")
        print()
        print("【其他】")
        print(f"  默认委托:   {settings.default_order_type}")
        print(f"  行情刷新:   {settings.quote_refresh_interval}秒")
        print("=" * 50)
        print("\n使用 'settings auto on/off' 开关自动执行")
        print("-" * 40)

    def _settings_set(self, args):
        """设置设置"""
        if len(args) < 2:
            print("用法: settings set <key> <value>")
            print("示例: settings set auto_execute_signals true")
            return

        key = args[0]
        value = args[1]

        # 类型转换
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)
        elif value.replace(".", "").isdigit():
            value = float(value)

        self.config_store.update_settings(**{key: value})
        print(f"[成功] {key} = {value}")

    def _settings_auto(self, args):
        """开关自动执行"""
        if not args:
            status = "启用" if self.signal_executor.is_enabled() else "禁用"
            print(f"自动执行: {status}")
            return

        cmd = args[0].lower()

        if cmd == "on" or cmd == "enable" or cmd == "true":
            self.config_store.update_settings(auto_execute_signals=True)
            self.signal_executor.enable()
            print("[成功] 自动执行已启用")
        elif cmd == "off" or cmd == "disable" or cmd == "false":
            self.config_store.update_settings(auto_execute_signals=False)
            self.signal_executor.disable()
            print("[成功] 自动执行已禁用")
        else:
            print("用法: settings auto on/off")

    def _settings_enable(self, args):
        """启用设置"""
        if not args:
            print("用法: settings enable <option>")
            print("选项: stop_loss, take_profit")
            return

        option = args[0].lower()
        if option == "stop_loss":
            self.config_store.update_settings(enable_stop_loss=True)
            print("[成功] 止损已启用")
        elif option == "take_profit":
            self.config_store.update_settings(enable_take_profit=True)
            print("[成功] 止盈已启用")
        else:
            print(f"未知选项: {option}")

    def _settings_disable(self, args):
        """禁用设置"""
        if not args:
            print("用法: settings disable <option>")
            print("选项: stop_loss, take_profit")
            return

        option = args[0].lower()
        if option == "stop_loss":
            self.config_store.update_settings(enable_stop_loss=False)
            print("[成功] 止损已禁用")
        elif option == "take_profit":
            self.config_store.update_settings(enable_take_profit=False)
            print("[成功] 止盈已禁用")
        else:
            print(f"未知选项: {option}")

    # ========== 别名 ==========

    def do_pos(self, arg):
        """持仓 (position 别名)"""
        self.do_position(arg)

    def do_acc(self, arg):
        """账户 (account 别名)"""
        self.do_account(arg)

    def do_mkt(self, arg):
        """行情 (market 别名)"""
        self.do_market(arg)

    # ========== 策略命令 ==========

    def do_strategy(self, arg):
        """策略管理"""
        args = arg.strip().split()

        if not args:
            self._strategy_list()
            return

        cmd = args[0]

        if cmd == "list":
            self._strategy_list()
        elif cmd == "add":
            self._strategy_add(args[1:])
        elif cmd == "remove":
            self._strategy_remove(args[1:])
        elif cmd == "start":
            self._strategy_start(args[1:])
        elif cmd == "stop":
            self._strategy_stop(args[1:])
        elif cmd == "help":
            self._strategy_help()
        else:
            print(f"未知命令: strategy {cmd}")

    def _strategy_list(self):
        """列出策略"""
        strategies = self.strategy_runner.list_strategies()

        print("\n策略列表:")
        print("-" * 60)
        print(f"{'ID':<20} {'名称':<15} {'类型':<12} {'状态':<10}")
        print("-" * 60)

        if not strategies:
            print("  (无)")
        else:
            for s in strategies:
                status = "运行中" if s.is_running else "已停止"
                print(f"{s.id:<20} {s.name:<15} {s.strategy_type:<12} {status:<10}")

        print("-" * 60)

    def _strategy_add(self, args):
        """添加策略"""
        if len(args) < 2:
            print("用法: strategy add <type> <name> [参数]")
            print("类型: ma_cross, rsi, watch")
            print("示例: strategy add ma_cross 均线策略 codes=SH600519,SH600000 short_period=5 long_period=20")
            return

        strategy_type = args[0]
        name = args[1]

        # 解析参数
        params = {}
        for arg in args[2:]:
            if "=" in arg:
                key, value = arg.split("=", 1)
                # 尝试转换类型
                if value.isdigit():
                    value = int(value)
                elif value.replace(".", "").isdigit():
                    value = float(value)
                elif value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif "," in value:
                    value = value.split(",")
                params[key] = value

        strategy_id = self.strategy_runner.add_strategy(name, strategy_type, params)
        print(f"[成功] 添加策略: {name} (ID: {strategy_id})")

    def _strategy_remove(self, args):
        """删除策略"""
        if not args:
            print("用法: strategy remove <id>")
            return

        strategy_id = args[0]
        if self.strategy_runner.remove_strategy(strategy_id):
            print(f"[成功] 删除策略: {strategy_id}")
        else:
            print(f"[失败] 策略不存在: {strategy_id}")

    def _strategy_start(self, args):
        """启动策略"""
        if not args:
            print("用法: strategy start <id>")
            print("提示: 使用 strategy list 查看策略ID")
            return

        strategy_id = args[0]
        # 尝试完整ID
        if self.strategy_runner.start_strategy(strategy_id):
            print(f"[成功] 策略已启动: {strategy_id}")
            return

        # 尝试部分ID匹配
        strategies = self.strategy_runner.list_strategies()
        matched = [s for s in strategies if s.id.startswith(strategy_id)]

        if len(matched) == 1:
            if self.strategy_runner.start_strategy(matched[0].id):
                print(f"[成功] 策略已启动: {matched[0].name} ({matched[0].id})")
                return

        print(f"[失败] 无法启动策略: {strategy_id}")

    def _strategy_stop(self, args):
        """停止策略"""
        if not args:
            print("用法: strategy stop <id>")
            return

        strategy_id = args[0]
        # 尝试完整ID
        if self.strategy_runner.stop_strategy(strategy_id):
            print(f"[成功] 策略已停止: {strategy_id}")
            return

        # 尝试部分ID匹配
        strategies = self.strategy_runner.list_strategies()
        matched = [s for s in strategies if s.id.startswith(strategy_id)]

        if len(matched) == 1:
            if self.strategy_runner.stop_strategy(matched[0].id):
                print(f"[成功] 策略已停止: {matched[0].name} ({matched[0].id})")
                return

        print(f"[失败] 无法停止策略: {strategy_id}")

    def _strategy_help(self):
        """策略帮助"""
        print("""
strategy list                         - 列出所有策略
strategy add <type> <name> [params]  - 添加策略
strategy remove <id>                  - 删除策略
strategy start <id>                   - 启动策略
strategy stop <id>                    - 停止策略

策略类型:
  ma_cross   - 均线交叉策略
  rsi        - RSI策略
  watch      - 行情监视

示例:
  strategy add ma_cross 均线策略 codes=SH600519 short_period=5 long_period=20
  strategy start strat_xxxxxx
        """)

    # ========== 回测命令 ==========

    def do_backtest(self, arg):
        """回测"""
        args = arg.strip().split()

        if not args:
            self._backtest_help()
            return

        cmd = args[0]

        if cmd == "help":
            self._backtest_help()
        elif cmd == "run":
            self._backtest_run(args[1:])
        else:
            print(f"未知命令: backtest {cmd}")

    def _backtest_help(self):
        """回测帮助"""
        print("""
回测命令:
  backtest run <codes> <start> <end> [params]

参数:
  codes       - 股票代码,多个用逗号分隔
  start       - 开始日期 (YYYYMMDD)
  end         - 结束日期 (YYYYMMDD)
  params      - 策略参数

示例:
  backtest run SH600519 20230101 20231231 short_period=5 long_period=20
  backtest run SH600519,SH600000 20230101 20231231
        """)

    def _backtest_run(self, args):
        """运行回测"""
        if len(args) < 3:
            print("用法: backtest run <codes> <start> <end> [params]")
            return

        codes = args[0].split(",")
        start_date = args[1]
        end_date = args[2]

        # 解析参数
        params = {}
        for arg in args[3:]:
            if "=" in arg:
                key, value = arg.split("=", 1)
                if value.isdigit():
                    value = int(value)
                elif value.replace(".", "").isdigit():
                    value = float(value)
                params[key] = value

        print(f"\n开始回测...")
        print(f"  股票: {', '.join(codes)}")
        print(f"  期间: {start_date} - {end_date}")
        print(f"  参数: {params}")
        print()

        try:
            # 创建模拟券商进行回测
            from finquant.trading.broker import create_simulated_broker
            broker = create_simulated_broker(initial_cash=100000)

            # 运行回测
            results = self.strategy_runner.backtest(
                strategy_type="ma_cross",
                codes=codes,
                start_date=start_date,
                end_date=end_date,
                initial_capital=100000,
                params=params,
            )

            # 显示结果
            for code, result in results.items():
                print(f"\n{code} 回测结果:")
                print("-" * 40)
                if result:
                    print(f"  收益率: {result.get('total_return', 0) * 100:.2f}%")
                    print(f"  胜率: {result.get('win_rate', 0) * 100:.2f}%")
                    print(f"  交易次数: {result.get('total_trades', 0)}")
                else:
                    print("  (无结果)")

        except Exception as e:
            print(f"[错误] 回测失败: {e}")

    # ========== 订单命令 ==========

    def do_order(self, arg):
        """订单操作"""
        args = arg.strip().split()

        if not args:
            self._order_list()
            return

        cmd = args[0]

        if cmd == "list" or cmd == "history":
            self._order_list()
        elif cmd == "pending":
            self._order_pending()
        elif cmd == "stats":
            self._order_stats()
        elif cmd == "clear":
            self._order_clear(args[1:])
        else:
            print(f"未知命令: order {cmd}")

    def _order_list(self):
        """订单列表"""
        orders = self.order_history.get_orders(limit=20)

        if not orders:
            print("\n暂无订单记录")
            return

        print(f"\n订单历史 (最近{len(orders)}条):")
        print(f"{'订单号':<20} {'代码':<8} {'操作':<4} {'数量':>6} {'价格':>8} {'状态':<10}")
        print("-" * 70)

        for o in orders:
            print(f"{o.order_id:<20} {o.code:<8} {o.action:<4} {o.quantity:>6} {o.avg_price:>8.2f} {o.status:<10}")

    def _order_pending(self):
        """待成交订单"""
        orders = self.order_history.get_pending_orders()

        if not orders:
            print("\n无待成交订单")
            return

        print(f"\n待成交订单 ({len(orders)}条):")
        for o in orders:
            print(f"  {o.order_id}: {o.action} {o.code} {o.quantity}股 @ {o.price}")

    def _order_stats(self):
        """订单统计"""
        stats = self.order_history.get_stats()

        print("\n订单统计:")
        print("-" * 40)
        print(f"总订单数: {stats['total_orders']}")
        print(f"已成交:   {stats['filled_orders']}")
        print(f"已撤销:   {stats['cancelled_orders']}")
        print(f"已拒绝:   {stats['rejected_orders']}")
        print(f"买入次数: {stats['buy_count']}")
        print(f"卖出次数: {stats['sell_count']}")
        print(f"买入总额: {stats['total_buy_amount']:.2f}")
        print(f"卖出总额: {stats['total_sell_amount']:.2f}")
        print(f"净买入:   {stats['net_position']:.2f}")
        print("-" * 40)

    def _order_clear(self, args):
        """清空订单历史"""
        confirm = input("确认清空所有订单历史? (y/n): ")
        if confirm.lower() == "y":
            self.order_history.clear_history()
            print("[成功] 订单历史已清空")


# ========== 便捷函数 ==========

def main():
    """CLI 入口点 (简单版本)"""
    start_console()


def start_console():
    """启动交互式控制台"""
    console = TradingConsole()
    console.cmdloop()


__all__ = [
    "TradingConsole",
    "start_console",
]
