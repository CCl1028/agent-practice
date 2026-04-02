"""市场数据工具 — 获取行情、板块、新闻、估值"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ---- 基金代码 → 名称查询 ----

_fund_name_cache: dict[str, str] = {}


def get_fund_name_by_code(fund_code: str) -> str | None:
    """通过基金代码查询真实基金名称（AKShare），带内存缓存。

    Returns:
        基金名称字符串，查询失败返回 None。
    """
    if not fund_code or len(fund_code) != 6:
        return None

    # 命中缓存直接返回
    if fund_code in _fund_name_cache:
        return _fund_name_cache[fund_code]

    try:
        import akshare as ak
        # fund_name_em 返回所有基金的代码+名称列表
        df = ak.fund_name_em()
        if df is not None and not df.empty:
            # 构建完整缓存（一次加载，后续所有查询都命中缓存）
            for _, row in df.iterrows():
                code = str(row.get("基金代码", "")).strip()
                name = str(row.get("基金简称", "")).strip()
                if code and name:
                    _fund_name_cache[code] = name

            if fund_code in _fund_name_cache:
                logger.info("[基金名称] %s → %s", fund_code, _fund_name_cache[fund_code])
                return _fund_name_cache[fund_code]
    except Exception as e:
        logger.warning("[基金名称] AKShare 查询基金 %s 名称失败: %s", fund_code, e)

    return None


def is_trading_hours() -> bool:
    """判断当前是否在交易时段（工作日 9:30-15:00）。"""
    now = datetime.now()
    if now.weekday() >= 5:  # 周六日
        return False
    t = now.hour * 100 + now.minute
    return 930 <= t <= 1500


def get_fund_estimation(fund_code: str) -> dict | None:
    """获取基金估值数据。

    交易时段：返回盘中实时估值（AKShare）。
    非交易时段：根据最近两日净值计算上一交易日收盘涨跌幅。

    Returns:
        {
            "est_nav": 2.05,
            "est_change": -0.85,
            "est_time": "15:00" 或 "03-31 收盘",
            "is_live": True/False,
        }
        或 None
    """
    if is_trading_hours():
        # 交易时段：尝试获取实时估值
        try:
            import akshare as ak
            df = ak.fund_value_estimation_em()
            if df is not None and not df.empty:
                row = df[df["基金代码"] == fund_code]
                if not row.empty:
                    r = row.iloc[0]
                    return {
                        "est_nav": float(r.get("估算净值", 0) or 0),
                        "est_change": float(r.get("估算涨跌幅", 0) or 0),
                        "est_time": str(r.get("估算时间", "")),
                        "is_live": True,
                    }
        except Exception as e:
            logger.warning("AKShare 获取基金 %s 实时估值失败: %s", fund_code, e)
        return None

    # 非交易时段：从净值历史计算上一交易日收盘涨跌
    return _get_last_close_change(fund_code)


def _get_last_close_change(fund_code: str) -> dict | None:
    """根据最近两个交易日净值，计算上一交易日收盘涨跌幅。"""
    try:
        import akshare as ak
        df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
        if df is not None and not df.empty and len(df) >= 2:
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            nav_now = float(latest["单位净值"])
            nav_prev = float(prev["单位净值"])
            if nav_prev > 0:
                change = round((nav_now - nav_prev) / nav_prev * 100, 2)
                # 格式化日期为 MM-DD
                date_str = str(latest["净值日期"])
                try:
                    dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    date_label = dt.strftime("%m-%d")
                except ValueError:
                    date_label = date_str[:10]
                return {
                    "est_nav": nav_now,
                    "est_change": change,
                    "est_time": f"{date_label} 收盘",
                    "is_live": False,
                }
    except Exception as e:
        logger.warning("AKShare 获取基金 %s 收盘净值失败: %s，使用 mock 数据", fund_code, e)

    # AKShare 不可用时，用 mock 净值的 trend_5d 最后一天作为收盘涨跌
    return _mock_last_close(fund_code)


def _mock_last_close(fund_code: str) -> dict | None:
    """Mock 上一交易日收盘涨跌（AKShare 不可用时兜底）。"""
    mock_db = {
        "005827": {"current_nav": 2.03, "trend_5d": [-0.3, 0.5, -0.8, 0.2, -1.1]},
        "161725": {"current_nav": 1.85, "trend_5d": [1.2, 0.8, 1.5, -0.3, 0.9]},
        "110011": {"current_nav": 4.52, "trend_5d": [-0.5, -0.2, 0.3, -0.8, -0.4]},
    }
    data = mock_db.get(fund_code)
    if data and data["trend_5d"]:
        return {
            "est_nav": data["current_nav"],
            "est_change": data["trend_5d"][-1],
            "est_time": "最近收盘",
            "is_live": False,
        }
    # 完全未知的基金，返回 0 涨跌而非随机数
    return {
        "est_nav": 0,
        "est_change": 0.0,
        "est_time": "暂无数据",
        "is_live": False,
    }


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
