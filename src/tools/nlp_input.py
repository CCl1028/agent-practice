"""自然语言持仓录入 — 从用户描述中提取持仓信息"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, TEXT_MODEL

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """\
你是一个基金持仓信息提取助手。用户会用自然语言描述自己的基金持仓或操作，你需要从中提取结构化信息。

提取以下字段：
- intent: 操作意图，必须是以下之一：
  - "add_holding" — 新增/描述持仓（默认）
  - "buy" — 加仓/买入操作
  - "sell" — 减仓/卖出操作
- fund_code: 基金代码（6位数字），如果用户只说了名字，根据你的知识补全代码
- fund_name: 基金名称
- cost: 持有金额（元），如果用户说"2万"就是20000
- cost_nav: 成本净值，如果用户没说，填0
- profit_ratio: 收益率（%），如果用户说"亏了5个点"就是-5，找不到就填0
- hold_days: 持有天数，如果用户说"去年6月买的"，请根据当前日期估算天数
- amount: 交易金额（元），仅当 intent 为 buy 或 sell 时需要

判断 intent 的规则：
- 用户说"加仓"、"买入"、"追加"、"定投" → intent: "buy"
- 用户说"减仓"、"卖出"、"赎回" → intent: "sell"
- 其他情况（描述持仓、报基金名等） → intent: "add_holding"

注意：
- 用户可能一次描述多只基金
- 用户表述可能很模糊，尽量合理推断
- 基金代码不确定的话填空字符串，但基金名称一定要有
- 当前日期是 {today}

严格按 JSON 数组格式输出，不要输出其他内容：
[{{"intent": "buy", "fund_code": "005827", "fund_name": "易方达蓝筹精选", "amount": 5000, "cost": 20000, "cost_nav": 0, "profit_ratio": -5, "hold_days": 280}}]
"""


def parse_natural_language(user_text: str) -> list[dict]:
    """从自然语言描述中提取持仓信息。"""
    if not user_text.strip():
        return []

    llm = ChatOpenAI(
        model=TEXT_MODEL,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        temperature=0,
    )

    today = datetime.now().strftime("%Y年%m月%d日")
    response = llm.invoke([
        SystemMessage(content=EXTRACT_PROMPT.format(today=today)),
        HumanMessage(content=user_text),
    ])

    text = response.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        holdings = json.loads(text)
        if isinstance(holdings, list):
            from src.tools.market_tools import get_fund_name_by_code

            for h in holdings:
                h.setdefault("intent", "add_holding")
                h.setdefault("fund_code", "")
                h.setdefault("fund_name", "未知基金")
                h.setdefault("cost", 0)
                h.setdefault("cost_nav", 0)
                h.setdefault("current_nav", 0)
                h.setdefault("profit_ratio", 0)
                h.setdefault("hold_days", 0)
                h.setdefault("trend_5d", [])
                h.setdefault("amount", 0)

                # 用真实 API 校正基金名称，防止 LLM 猜错
                if h["fund_code"]:
                    real_name = get_fund_name_by_code(h["fund_code"])
                    if real_name:
                        if real_name != h["fund_name"]:
                            logger.info(
                                "[NLP Input] 校正基金名称: %s → %s (代码 %s)",
                                h["fund_name"], real_name, h["fund_code"],
                            )
                        h["fund_name"] = real_name

            logger.info("[NLP Input] 从描述中解析出 %d 只基金", len(holdings))
            return holdings
    except json.JSONDecodeError as e:
        logger.error("[NLP Input] JSON 解析失败: %s", e)

    return []
