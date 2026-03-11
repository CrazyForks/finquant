"""
finquant - 意图解析器

识别用户意图和提取关键实体
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Intent:
    """意图"""
    type: str  # query_price, query_trend, recommend, trade, optimize, system
    confidence: float = 1.0
    entities: Dict = None
    original_text: str = ""

    def __post_init__(self):
        if self.entities is None:
            self.entities = {}


class IntentParser:
    """意图解析器"""

    # 意图关键词映射
    INTENT_KEYWORDS = {
        # 行情/分析
        "query_price": ["看看", "行情", "价格", "走势", "多少", "现在", "当前"],
        "query_trend": ["趋势", "怎么样", "分析", "评估", "判断"],
        "recommend": ["推荐", "哪些", "选股", "有什么好", "有什么好"],

        # 交易
        "trade_buy": ["买", "买入", "建仓", "增持", "购入"],
        "trade_sell": ["卖", "卖出", "清仓", "减持", "抛售"],

        # 查询
        "query_position": ["持仓", "有什么", "持有", "仓位", "手里"],
        "query_order": ["订单", "委托", "成交", "挂单"],
        "query_account": ["账户", "钱", "资金", "余额", "总资产"],
        "query_stats": ["统计", "收益", "赚了多少", "盈亏"],

        # 策略
        "strategy_list": ["策略", "有哪些策略", "策略列表"],
        "strategy_start": ["启动策略", "开始策略", "运行策略"],
        "strategy_stop": ["停止策略", "暂停策略", "结束策略"],

        # 设置
        "settings_show": ["设置", "配置", "参数"],
        "settings_auto_on": ["开启自动", "启用自动", "打开自动"],
        "settings_auto_off": ["关闭自动", "禁用自动", "关闭自动"],

        # 优化/回测
        "optimize": ["优化", "调参", "参数", "最好的"],
        "backtest": ["回测", "历史测试"],

        # 系统
        "help": ["帮助", "help", "怎么", "如何"],
        "system_clear": ["清屏", "清除", "刷新"],
        "system_exit": ["退出", "结束", "关闭"],
    }

    # 命令前缀 (强制命令模式)
    COMMAND_PREFIXES = ["/", "!", "ai "]

    # 已知命令关键词
    COMMAND_KEYWORDS = [
        "broker", "account", "position", "market", "order",
        "strategy", "backtest", "settings", "status", "help",
        "exit", "clear", "cls"
    ]

    def __init__(self):
        self.known_codes = self._load_known_codes()

    def _load_known_codes(self) -> Dict[str, str]:
        """加载已知股票代码映射"""
        return {
            "茅台": "SH600519",
            "贵州茅台": "SH600519",
            "平安": "SH601318",
            "中国平安": "SH601318",
            "招商银行": "SH600036",
            "银行": "SH600036",
            "宁德": "SZ300750",
            "比亚迪": "SZ002594",
            "特斯拉": "TSLA",
            "苹果": "AAPL",
            "上证": "SH000001",
            "深证": "SZ399001",
            "创业板": "SZ399006",
        }

    def is_ai_request(self, text: str) -> bool:
        """判断是否为 AI 请求"""
        text = text.strip()

        # 1. 命令前缀
        for prefix in self.COMMAND_PREFIXES:
            if text.startswith(prefix):
                return True

        # 2. 已知命令
        text_lower = text.lower().split()[0] if text else ""
        if text_lower in self.COMMAND_KEYWORDS:
            return False

        # 3. 中文关键词
        for keywords in self.INTENT_KEYWORDS.values():
            for keyword in keywords:
                if keyword in text:
                    return True

        # 4. 纯数字/字母可能是命令
        if re.match(r"^[a-zA-Z0-9_]+$", text):
            return False

        # 5. 包含空格但不是已知命令
        if " " in text and not text_lower in self.COMMAND_KEYWORDS:
            return True

        return False

    # 系统意图 (不需要提取股票代码)
    SYSTEM_INTENTS = [
        "query_position", "query_order", "query_account", "query_stats",
        "strategy_list", "strategy_start", "strategy_stop",
        "settings_show", "settings_auto_on", "settings_auto_off",
        "system_clear", "system_exit", "help",
    ]

    # 需要股票代码的意图
    CODE_INTENTS = [
        "query_price", "query_trend", "trade_buy", "trade_sell",
        "recommend", "backtest", "optimize"
    ]

    def parse(self, text: str) -> Intent:
        """解析用户输入"""
        text = text.strip()

        # 解析意图
        intent_type, confidence = self._parse_intent(text)

        # 解析实体
        entities = self._extract_entities(text, intent_type)

        return Intent(
            type=intent_type,
            confidence=confidence,
            entities=entities,
            original_text=text
        )

    def _parse_intent(self, text: str) -> Tuple[str, float]:
        """解析意图类型"""
        text_lower = text.lower()

        # 1. 优先检测系统/查询意图 (更精确)
        system_intents = [
            "query_position", "query_order", "query_account", "query_stats",
            "strategy_list", "strategy_start", "strategy_stop",
            "settings_show", "settings_auto_on", "settings_auto_off",
            "system_clear", "system_exit", "help", "optimize", "backtest"
        ]

        for intent_type in system_intents:
            if intent_type in self.INTENT_KEYWORDS:
                for keyword in self.INTENT_KEYWORDS[intent_type]:
                    if keyword in text:
                        return intent_type, 0.9

        # 2. 检测交易意图
        for keyword in self.INTENT_KEYWORDS["trade_buy"]:
            if keyword in text:
                return "trade_buy", 0.9

        for keyword in self.INTENT_KEYWORDS["trade_sell"]:
            if keyword in text:
                return "trade_sell", 0.9

        # 3. 其他意图
        for intent_type, keywords in self.INTENT_KEYWORDS.items():
            if intent_type not in system_intents:
                for keyword in keywords:
                    if keyword in text:
                        return intent_type, 0.8

        # 默认意图
        return "query_price", 0.5

    def _extract_entities(self, text: str, intent_type: str = None) -> Dict:
        """提取实体

        Args:
            text: 用户输入
            intent_type: 意图类型，系统意图不提取股票代码
        """
        entities = {}

        # 系统意图不需要提取股票代码
        # 需要股票代码的意图才提取
        if intent_type and intent_type in self.CODE_INTENTS:
            # 1. 股票代码 (单个)
            entities["code"] = self._extract_stock_code(text)
            # 2. 股票代码列表 (多个)
            entities["codes"] = self._extract_stock_codes(text)
        else:
            entities["code"] = None
            entities["codes"] = []

        # 2. 数量
        entities["quantity"] = self._extract_quantity(text)

        # 3. 价格
        entities["price"] = self._extract_price(text)

        # 4. 时间
        entities["period"] = self._extract_period(text)

        # 5. 优化指标
        entities["metric"] = self._extract_metric(text)

        # 6. 策略类型
        entities["strategy"] = self._extract_strategy(text)

        return entities

    def _extract_stock_code(self, text: str) -> Optional[str]:
        """提取股票代码 (单个)"""
        # 1. 精确代码 SH/SZ + 数字
        match = re.search(r"(SH|SZ)(\d{6})", text.upper())
        if match:
            return match.group(1) + match.group(2)

        # 2. 中文名称映射
        for name, code in self.known_codes.items():
            if name in text:
                return code

        return None

    def _extract_stock_codes(self, text: str) -> List[str]:
        """提取股票代码列表 (支持多个，逗号分隔)"""
        codes = []

        # 1. 提取所有 SH/SZ 代码
        matches = re.findall(r"(SH|SZ)(\d{6})", text.upper())
        for m in matches:
            codes.append(m[0] + m[1])

        # 2. 中文名称映射
        for name, code in self.known_codes.items():
            if name in text:
                if code not in codes:
                    codes.append(code)

        return codes if codes else [None]

    def _extract_quantity(self, text: str) -> Optional[int]:
        """提取数量"""
        # "100股" / "100手" / "100"
        match = re.search(r"(\d+)\s*[股|手]", text)
        if match:
            qty = int(match.group(1))
            if "手" in text:
                qty *= 100  # 手 -> 股
            return qty

        # 纯数字
        match = re.search(r"(\d+)", text)
        if match:
            return int(match.group(1))

        return None

    def _extract_price(self, text: str) -> Optional[float]:
        """提取价格"""
        # "100块" / "100元" / "价格100"
        match = re.search(r"[价格|@|在]?\s*(\d+\.?\d*)\s*[块|元]", text)
        if match:
            return float(match.group(1))

        return None

    def _extract_period(self, text: str) -> Optional[str]:
        """提取时间周期"""
        if "最近" in text or "这" in text:
            return "recent"
        elif "一个月" in text:
            return "1m"
        elif "三个月" in text:
            return "3m"
        elif "半年" in text:
            return "6m"
        elif "一年" in text:
            return "1y"

        return None

    def _extract_metric(self, text: str) -> Optional[str]:
        """提取优化指标"""
        text_lower = text.lower()

        if "sharpe" in text_lower:
            return "sharpe"
        elif "max_drawdown" in text_lower or "回撤" in text:
            return "max_drawdown"
        elif "total_return" in text_lower or "收益" in text:
            return "total_return"

        return None

    def _extract_strategy(self, text: str) -> Optional[str]:
        """提取策略类型"""
        text_lower = text.lower()

        # 均线策略
        if "ma_cross" in text_lower or "均线" in text:
            return "ma_cross"
        # RSI 策略
        elif "rsi" in text_lower:
            return "rsi"
        # 动量策略
        elif "momentum" in text_lower or "动量" in text:
            return "momentum"

        return None
