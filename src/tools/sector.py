"""板块数据 — 板块涨跌 + 市场新闻"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_sector_performance() -> list[dict]:
    """获取主要板块涨跌。"""
    try:
        import akshare as ak
        df = ak.stock_board_industry_name_em()
        if df is not None and not df.empty:
            top = df.head(10)
            return [{"name": row["板块名称"], "change": round(float(row["涨跌幅"]), 2)} for _, row in top.iterrows()]
    except Exception as e:
        logger.warning("AKShare 获取板块数据失败: %s，使用 mock 数据", e)

    return _mock_sector_performance()


def get_market_news() -> list[str]:
    """获取市场热点新闻摘要。"""
    today = datetime.now().strftime("%m月%d日")
    return [
        f"{today} A股三大指数震荡整理",
        "科技板块午后回调，半导体领跌",
        "消费板块表现强势，白酒股集体上涨",
        "北向资金今日净流入约15亿元",
    ]


def _mock_sector_performance() -> list[dict]:
    return [
        {"name": "白酒", "change": 2.1},
        {"name": "新能源", "change": 0.8},
        {"name": "医药", "change": 0.3},
        {"name": "半导体", "change": -1.5},
        {"name": "房地产", "change": -0.9},
        {"name": "银行", "change": 0.2},
    ]
