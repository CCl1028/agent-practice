"""持仓合并工具 — 统一的按 fund_code 去重合并逻辑

T-017: 消除 server.py / main.py / portfolio_agent.py 中 4+ 处重复的持仓合并代码
"""

from __future__ import annotations

import logging

from src.state import FundHolding

logger = logging.getLogger(__name__)


def merge_holdings(
    existing: list[FundHolding],
    new_holdings: list[FundHolding],
) -> list[FundHolding]:
    """将新持仓合并到现有持仓中（按 fund_code 去重，新的覆盖旧的）。

    Args:
        existing: 现有持仓列表
        new_holdings: 新录入的持仓列表

    Returns:
        合并后的持仓列表（去重）
    """
    existing_map: dict[str, FundHolding] = {f["fund_code"]: f for f in existing if f.get("fund_code")}
    for h in new_holdings:
        if h.get("fund_code"):
            existing_map[h["fund_code"]] = h
    merged = list(existing_map.values())
    logger.debug(
        "[持仓合并] 现有 %d + 新增 %d → 合并后 %d",
        len(existing),
        len(new_holdings),
        len(merged),
    )
    return merged
