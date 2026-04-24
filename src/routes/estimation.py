"""估值路由 — /api/estimation, /api/fund/*/nav-history"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from src.core.exceptions import FundPalError
from src.models.schemas import HoldingsInput
from src.tools.portfolio_tools import load_portfolio
from src.utils.estimation_utils import build_estimation_results

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/estimation")
async def post_estimation(input: HoldingsInput | None = None):
    """获取持仓的估值（POST）"""
    holdings = input.holdings if input and input.holdings else load_portfolio()
    trading, results = build_estimation_results(holdings)
    return {"trading_hours": trading, "funds": results}


@router.get("/api/estimation")
async def get_estimation():
    """获取所有持仓的估值（GET，兼容旧版）"""
    holdings = load_portfolio()
    trading, results = build_estimation_results(holdings)
    return {"trading_hours": trading, "funds": results}


@router.get("/api/fund/{fund_code}/nav-history")
async def get_nav_history(fund_code: str, start: str = Query(""), end: str = Query("")):
    """获取基金历史净值"""
    from src.tools.market_tools import get_fund_nav_history

    try:
        nav_list = get_fund_nav_history(fund_code, start, end)
        return {"fund_code": fund_code, "nav_list": nav_list}
    except Exception as e:
        logger.error("获取历史净值失败: %s", e)
        raise FundPalError(f"获取历史净值失败: {e}") from e
