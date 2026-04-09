"""Market Agent — 市场观察员

v2: 参考 daily_stock_analysis 增强：
- 接入真实新闻搜索（Tavily/SerpAPI），替代 Mock
- 为每只持仓基金搜索专属新闻（最新消息/风险/业绩）
- 无搜索 Key 时优雅降级为 Mock 新闻
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
    """LangGraph 节点：获取市场数据 + 新闻搜索。"""
    logger.info("[Market Agent] 开始获取市场数据...")

    try:
        sectors_raw = get_sector_performance()
        sentiment = _judge_sentiment(sectors_raw)
        sectors = [{"name": s["name"], "change": s["change"]} for s in sectors_raw]

        # --- v2: 真实新闻搜索 ---
        hot_news = []
        fund_news: dict[str, list[dict]] = {}

        try:
            from src.tools.news_tools import search_market_news, search_fund_news

            # 大盘/行业新闻
            market_news_items = search_market_news()
            if market_news_items:
                hot_news = [item["title"] for item in market_news_items[:6]]
                logger.info("[Market Agent] 获取到 %d 条真实市场新闻", len(hot_news))

            # 每只基金的专属新闻（限制最多搜 5 只，避免 API 耗尽）
            portfolio = state.get("portfolio", [])
            for f in portfolio[:5]:
                fund_code = f.get("fund_code", "")
                fund_name = f.get("fund_name", "")
                if fund_code and fund_name:
                    try:
                        items = search_fund_news(fund_name, fund_code)
                        if items:
                            fund_news[fund_code] = items
                    except Exception as e:
                        logger.warning("[Market Agent] 搜索 %s 新闻失败: %s", fund_name, e)

        except ImportError:
            logger.debug("[Market Agent] news_tools 导入失败，跳过新闻搜索")
        except Exception as e:
            logger.warning("[Market Agent] 新闻搜索出错: %s", e)

        # 兜底：如果没有获取到真实新闻，使用 mock
        if not hot_news:
            hot_news = get_market_news()
            logger.info("[Market Agent] 使用 mock 新闻（未配置搜索 Key 或搜索失败）")

        market: MarketData = {
            "sectors": sectors,
            "market_sentiment": sentiment,
            "hot_news": hot_news,
            "fund_news": fund_news,
        }

        logger.info(
            "[Market Agent] 完成，情绪: %s, 板块: %d 个, 新闻: %d 条, 基金新闻: %d 只",
            sentiment, len(sectors), len(hot_news), len(fund_news),
        )
        return {"market": market}

    except Exception as e:
        logger.error("[Market Agent] 失败: %s", e)
        return {"error": f"Market Agent 出错: {e}"}
