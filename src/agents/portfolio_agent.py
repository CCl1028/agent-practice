"""Portfolio Agent — 持仓管家

职责：管理用户持仓数据，计算最新盈亏状态。
支持：截图识别录入、自然语言录入、已有持仓加载。
"""

from __future__ import annotations

import logging

from src.state import AgentState
from src.tools.portfolio_tools import compute_metrics, load_portfolio, save_portfolio
from src.utils.holdings_utils import merge_holdings

logger = logging.getLogger(__name__)


def portfolio_node(state: AgentState) -> dict:
    """LangGraph 节点：加载持仓并刷新指标。"""
    logger.info("[Portfolio Agent] 开始加载持仓数据...")

    try:
        # 优先使用前端传入的 holdings（localStorage 中的用户数据）
        holdings_from_frontend = state.get("holdings", [])
        if holdings_from_frontend:
            logger.info("[Portfolio Agent] 使用前端传入的 %d 只基金", len(holdings_from_frontend))
            portfolio = holdings_from_frontend
        else:
            # 如果 state 中已有新录入的持仓（从截图/自然语言解析来的），合并保存
            new_holdings = state.get("portfolio", [])
            if new_holdings:
                logger.info("[Portfolio Agent] 检测到新录入的 %d 只基金，合并保存", len(new_holdings))
                existing = load_portfolio()
                merged = merge_holdings(existing, new_holdings)
                save_portfolio(merged)
                portfolio = merged
            else:
                portfolio = load_portfolio()

        portfolio = compute_metrics(portfolio)

        logger.info("[Portfolio Agent] 完成，共 %d 只基金", len(portfolio))
        for f in portfolio:
            logger.info(
                "  %s (%s): 成本 %.2f → 现价 %.2f, 盈亏 %.2f%%",
                f["fund_name"],
                f["fund_code"],
                f["cost_nav"],
                f["current_nav"],
                f["profit_ratio"],
            )

        return {"portfolio": portfolio}

    except Exception as e:
        logger.error("[Portfolio Agent] 失败: %s", e)
        return {"error": f"Portfolio Agent 出错: {e}"}
