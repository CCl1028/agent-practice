"""LangGraph State 定义 — 基金助手核心数据结构"""

from __future__ import annotations

from typing import Literal, TypedDict


class FundHolding(TypedDict):
    """单只基金持仓"""
    fund_code: str
    fund_name: str
    cost: float            # 持仓金额
    cost_nav: float        # 成本净值
    current_nav: float     # 当前净值
    profit_ratio: float    # 盈亏比例 %
    hold_days: int         # 持有天数
    trend_5d: list[float]  # 近5日涨跌幅 %


class SectorData(TypedDict):
    """板块涨跌"""
    name: str
    change: float  # 涨跌幅 %


class MarketData(TypedDict):
    """市场数据"""
    sectors: list[SectorData]
    market_sentiment: str
    hot_news: list[str]


class FundAdvice(TypedDict):
    """单只基金的建议"""
    fund_name: str
    action: Literal["加仓", "减仓", "观望"]
    reason: str
    confidence: Literal["高", "中", "低"]


class Briefing(TypedDict):
    """最终简报输出"""
    summary: str               # 一句话结论 ≤15字
    details: list[FundAdvice]  # 每只基金的建议
    market_note: str           # 市场简评


class AgentState(TypedDict, total=False):
    """LangGraph 全局 State"""
    # 触发上下文
    trigger: Literal["daily_briefing", "user_query", "new_portfolio"]
    user_query: str

    # 持仓数据 (Portfolio Agent 填充)
    portfolio: list[FundHolding]

    # 市场数据 (Market Agent 填充)
    market: MarketData

    # 最终输出 (Briefing Agent 填充)
    briefing: Briefing

    # 错误信息
    error: str
