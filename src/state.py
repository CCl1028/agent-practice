"""LangGraph State 定义 — 基金助手核心数据结构

v2: 参考 daily_stock_analysis 扩展分析维度
- FundHolding 新增技术指标（均线/乖离率/波动率）
- FundAdvice 新增评分/风险提示/持有建议
- MarketData 新增基金专属新闻
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


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

    # --- v2 新增：技术指标 ---
    ma5: float             # 5日均线净值
    ma10: float            # 10日均线净值
    ma20: float            # 20日均线净值
    ma_status: str         # "多头排列" / "空头排列" / "震荡"
    volatility_5d: float   # 5日波动率 (最大值 - 最小值)
    deviation_rate: float  # 乖离率: (现价 - MA5) / MA5 * 100

    # --- v2 新增：估值数据 ---
    est_change: float | None   # 盘中估值涨跌幅 %
    est_nav: float | None      # 估算净值
    est_time: str | None       # 估值时间


class SectorData(TypedDict):
    """板块涨跌"""
    name: str
    change: float  # 涨跌幅 %


class MarketData(TypedDict):
    """市场数据"""
    sectors: list[SectorData]
    market_sentiment: str
    hot_news: list[str]
    fund_news: dict[str, list[dict]]  # v2 新增: {fund_code: [news_items]}


class FundAdvice(TypedDict):
    """单只基金的建议"""
    fund_name: str
    action: Literal["加仓", "减仓", "观望", "持有"]  # v2 新增"持有"
    reason: str
    confidence: Literal["高", "中", "低"]
    score: int         # v2 新增: 0-100 置信度评分
    risk_note: str     # v2 新增: 风险提示（可为空）


class Briefing(TypedDict):
    """最终简报输出"""
    summary: str               # 一句话结论 ≤15字
    details: list[FundAdvice]  # 每只基金的建议
    market_note: str           # 市场简评
    risk_alerts: list[str]     # v2 新增: 全局风险提示


# --- v3 新增: 基金诊断分析 ---

class FundDiagnosis(TypedDict):
    """基金诊断分析结果"""
    fund_code: str
    fund_name: str
    rating: str        # "优秀" / "良好" / "中等" / "偏弱"
    pros: list[str]    # 优点列表
    risks: list[str]   # 风险列表
    buy_recommendation: str  # "可以" / "谨慎" / "不建议"
    buy_reason: str    # 购买理由
    summary: str       # 一句话总结
    profile: dict      # 基金基本信息


class FallAnalysis(TypedDict):
    """涨跌原因分析结果"""
    fund_code: str
    fund_name: str
    direction: str     # "上涨" / "下跌" / "平盘"
    change_ratio: float  # 涨跌幅百分比
    reasons: list[str]  # 原因列表（带权重）
    outlook: str       # 后市展望
    summary: str       # 一句话总结
    perf_data: dict    # 今日表现数据


class AgentState(TypedDict, total=False):
    """LangGraph 全局 State"""
    # 触发上下文
    trigger: Literal["daily_briefing", "user_query", "new_portfolio", "fund_diagnosis", "fall_analysis"]
    user_query: str

    # 前端传入的持仓数据（可选，若有则优先使用）
    holdings: list[FundHolding]

    # 持仓数据 (Portfolio Agent 填充)
    portfolio: list[FundHolding]

    # 市场数据 (Market Agent 填充)
    market: MarketData

    # 最终输出 (Briefing Agent 填充)
    briefing: Briefing

    # --- v3 新增: 基金分析查询字段 ---
    # 查询的基金代码和名称
    query_fund_code: str
    query_fund_name: str

    # 诊断分析结果 (Analysis Agent 填充)
    diagnosis: FundDiagnosis
    fall_analysis: FallAnalysis

    # 错误信息
    error: str
