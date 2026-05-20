"""板块数据 — 板块涨跌"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def get_sector_performance() -> list[dict]:
    """获取主要板块涨跌，失败时返回空列表。"""
    try:
        import akshare as ak
        df = ak.stock_board_industry_name_em()
        if df is not None and not df.empty:
            top = df.head(10)
            return [{"name": row["板块名称"], "change": round(float(row["涨跌幅"]), 2)} for _, row in top.iterrows()]
    except Exception as e:
        logger.warning("AKShare 获取板块数据失败: %s", e)

    return []
