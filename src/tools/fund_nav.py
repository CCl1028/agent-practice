"""基金净值获取 — 最新净值 + 历史净值"""

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
            hist = df.tail(6)
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


def get_fund_nav_history(fund_code: str, start: str = "", end: str = "") -> list[dict]:
    """获取基金历史净值列表。"""
    try:
        import akshare as ak
        df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
        if df is not None and not df.empty:
            result = []
            for _, row in df.iterrows():
                date_str = str(row["净值日期"])[:10]
                nav = float(row["单位净值"])
                if start and date_str < start:
                    continue
                if end and date_str > end:
                    continue
                result.append({"date": date_str, "nav": nav})
            return result
    except Exception as e:
        logger.warning("AKShare 获取基金 %s 历史净值失败: %s", fund_code, e)
    return []


def _mock_fund_nav(fund_code: str) -> dict:
    """Mock 基金净值数据"""
    mock_db = {
        "005827": {"current_nav": 2.03, "trend_5d": [-0.3, 0.5, -0.8, 0.2, -1.1]},
        "161725": {"current_nav": 1.85, "trend_5d": [1.2, 0.8, 1.5, -0.3, 0.9]},
        "110011": {"current_nav": 4.52, "trend_5d": [-0.5, -0.2, 0.3, -0.8, -0.4]},
    }
    data = mock_db.get(fund_code, {"current_nav": 1.50, "trend_5d": [0.1, -0.2, 0.3, -0.1, 0.2]})
    data["date"] = datetime.now().strftime("%Y-%m-%d")
    return data
