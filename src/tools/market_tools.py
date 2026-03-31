"""市场数据工具 — 获取行情、板块、新闻"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_fund_nav(fund_code: str) -> dict:
    """获取基金最新净值，优先 AKShare，失败则 mock。"""
    try:
        import akshare as ak
        df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            hist = df.tail(6)  # 取最近6天，算5日涨跌
            navs = hist["单位净值"].astype(float).tolist()
            trend_5d = []
            for i in range(1, len(navs)):
                change = round((navs[i] - navs[i - 1]) / navs[i - 1] * 100, 2)
                trend_5d.append(change)
            return {
                "current_nav": float(latest["单位净值"]),
                "date": str(latest["净值日期"]),
                "trend_5d": trend_5d[-5:],
            }
    except Exception as e:
        logger.warning("AKShare 获取基金 %s 净值失败: %s，使用 mock 数据", fund_code, e)

    return _mock_fund_nav(fund_code)


def get_sector_performance() -> list[dict]:
    """获取主要板块涨跌，优先 AKShare，失败则 mock。"""
    try:
        import akshare as ak
        df = ak.stock_board_industry_name_em()
        if df is not None and not df.empty:
            top = df.head(10)
            return [
                {"name": row["板块名称"], "change": round(float(row["涨跌幅"]), 2)}
                for _, row in top.iterrows()
            ]
    except Exception as e:
        logger.warning("AKShare 获取板块数据失败: %s，使用 mock 数据", e)

    return _mock_sector_performance()


def get_market_news() -> list[str]:
    """获取市场热点新闻摘要（MVP 使用 mock）。"""
    today = datetime.now().strftime("%m月%d日")
    return [
        f"{today} A股三大指数震荡整理",
        "科技板块午后回调，半导体领跌",
        "消费板块表现强势，白酒股集体上涨",
        "北向资金今日净流入约15亿元",
    ]


# ---- Mock 数据 ----

def _mock_fund_nav(fund_code: str) -> dict:
    """Mock 基金净值数据"""
    mock_db = {
        "005827": {"current_nav": 2.03, "trend_5d": [-0.3, 0.5, -0.8, 0.2, -1.1]},
        "161725": {"current_nav": 1.85, "trend_5d": [1.2, 0.8, 1.5, -0.3, 0.9]},
        "110011": {"current_nav": 4.52, "trend_5d": [-0.5, -0.2, 0.3, -0.8, -0.4]},
    }
    data = mock_db.get(fund_code, {
        "current_nav": 1.50,
        "trend_5d": [0.1, -0.2, 0.3, -0.1, 0.2],
    })
    data["date"] = datetime.now().strftime("%Y-%m-%d")
    return data


def _mock_sector_performance() -> list[dict]:
    """Mock 板块数据"""
    return [
        {"name": "白酒", "change": 2.1},
        {"name": "新能源", "change": 0.8},
        {"name": "医药", "change": 0.3},
        {"name": "半导体", "change": -1.5},
        {"name": "房地产", "change": -0.9},
        {"name": "银行", "change": 0.2},
    ]
