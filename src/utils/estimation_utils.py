"""估值结果构建工具 — 统一 GET/POST /api/estimation 的结果构建逻辑

T-018: 消除 server.py 中 POST 和 GET 估值接口的重复代码
"""

from __future__ import annotations

import logging

from src.state import FundHolding

logger = logging.getLogger(__name__)


def build_estimation_results(
    holdings: list[FundHolding],
) -> tuple[bool, list[dict]]:
    """为持仓列表构建估值结果。

    Args:
        holdings: 持仓列表

    Returns:
        (is_trading_hours, results) 元组
        results 中每项: {fund_code, fund_name, est_change, est_nav, est_time, is_live}
    """
    from src.tools.market_tools import get_fund_estimation, is_trading_hours

    trading = is_trading_hours()
    results: list[dict] = []
    for h in holdings:
        est = get_fund_estimation(h.get("fund_code", ""))
        results.append(
            {
                "fund_code": h.get("fund_code", ""),
                "fund_name": h.get("fund_name", ""),
                "est_change": est["est_change"] if est else None,
                "est_nav": est["est_nav"] if est else None,
                "est_time": est["est_time"] if est else None,
                "is_live": est.get("is_live", False) if est else None,
            }
        )
    return trading, results
