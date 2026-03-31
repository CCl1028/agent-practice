"""Market Agent — 市场观察员

职责：获取实时行情、行业动态、市场新闻。
"""

from __future__ import annotations

import logging

from src.state import AgentState, MarketData
from src.tools.market_tools import get_market_news, get_sector_performance

logger = logging.getLogger(__name__)


def _judge_sentiment(sectors: list[dict]) -> str:
    """根据板块涨跌简单判断市场情绪。"""
    if not sectors:
        return "中性"
    avg = sum(s["change"] for s in sectors) / len(sectors)
    if avg > 0.5:
        return "偏乐观"
    elif avg < -0.5:
        return "偏谨慎"
    return "中性震荡"


def market_node(state: AgentState) -> dict:
    """LangGraph 节点：获取市场数据。"""
    logger.info("[Market Agent] 开始获取市场数据...")

    try:
        sectors_raw = get_sector_performance()
        news = get_market_news()
        sentiment = _judge_sentiment(sectors_raw)

        sectors = [{"name": s["name"], "change": s["change"]} for s in sectors_raw]

        market: MarketData = {
            "sectors": sectors,
            "market_sentiment": sentiment,
            "hot_news": news,
        }

        logger.info("[Market Agent] 完成，情绪: %s, 板块: %d 个", sentiment, len(sectors))
        return {"market": market}

    except Exception as e:
        logger.error("[Market Agent] 失败: %s", e)
        return {"error": f"Market Agent 出错: {e}"}
