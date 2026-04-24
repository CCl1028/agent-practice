"""基金估值 — 实时估值 + 收盘涨跌 + 缓存管理"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from src.tools.common import is_trading_hours

logger = logging.getLogger(__name__)

# ---- 估值缓存 ----
_estimation_cache: dict[str, dict] = {}
_estimation_cache_lock = threading.Lock()
ESTIMATION_CACHE_TTL = 600  # 10 分钟


def get_fund_estimation(fund_code: str) -> dict | None:
    """获取基金估值数据（优先读缓存）。"""
    with _estimation_cache_lock:
        cached = _estimation_cache.get(fund_code)
    if cached:
        age = time.time() - cached.get("cached_at", 0)
        ttl = ESTIMATION_CACHE_TTL if is_trading_hours() else ESTIMATION_CACHE_TTL * 6
        if age < ttl:
            return {k: v for k, v in cached.items() if k != "cached_at"}

    result = _fetch_fund_estimation(fund_code)
    if result:
        with _estimation_cache_lock:
            _estimation_cache[fund_code] = {**result, "cached_at": time.time()}
    return result


def _fetch_fund_estimation(fund_code: str) -> dict | None:
    """实际从 AKShare 获取基金估值。"""
    if is_trading_hours():
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
                else:
                    logger.info("[估值] %s 不在实时估值列表中，回退到收盘数据", fund_code)
                    return _get_last_close_change(fund_code)
        except Exception as e:
            logger.warning("AKShare 获取基金 %s 实时估值失败: %s", fund_code, e)
        return _get_last_close_change(fund_code)

    return _get_last_close_change(fund_code)


def refresh_estimation_cache(fund_codes: list[str]) -> dict[str, dict | None]:
    """批量刷新估值缓存。"""
    results = {}
    bulk_data = {}
    if is_trading_hours():
        try:
            import akshare as ak
            df = ak.fund_value_estimation_em()
            if df is not None and not df.empty:
                for _, r in df.iterrows():
                    code = str(r.get("基金代码", ""))
                    if code:
                        bulk_data[code] = {
                            "est_nav": float(r.get("估算净值", 0) or 0),
                            "est_change": float(r.get("估算涨跌幅", 0) or 0),
                            "est_time": str(r.get("估算时间", "")),
                            "is_live": True,
                        }
        except Exception as e:
            logger.warning("[估值缓存] 批量拉取实时估值失败: %s", e)

    for code in fund_codes:
        est = bulk_data[code] if code in bulk_data else _get_last_close_change(code)
        if est:
            with _estimation_cache_lock:
                _estimation_cache[code] = {**est, "cached_at": time.time()}
        results[code] = est

    logger.info("[估值缓存] 已刷新 %d 只基金估值", len(results))
    return results


def get_estimation_cache_info() -> dict:
    """获取估值缓存状态信息。"""
    with _estimation_cache_lock:
        items = []
        now = time.time()
        for code, data in _estimation_cache.items():
            age = int(now - data.get("cached_at", 0))
            items.append({"fund_code": code, "age_seconds": age})
        return {"cached_count": len(_estimation_cache), "items": items}


def _get_last_close_change(fund_code: str) -> dict | None:
    """根据最近两日净值计算上一交易日收盘涨跌幅。"""
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
                date_str = str(latest["净值日期"])
                try:
                    dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    date_label = dt.strftime("%m-%d")
                except ValueError:
                    date_label = date_str[:10]
                return {"est_nav": nav_now, "est_change": change, "est_time": f"{date_label} 收盘", "is_live": False}
    except Exception as e:
        logger.warning("AKShare 获取基金 %s 收盘净值失败: %s", fund_code, e)

    return _mock_last_close(fund_code)


def _mock_last_close(fund_code: str) -> dict | None:
    """Mock 上一交易日收盘涨跌。"""
    mock_db = {
        "005827": {"current_nav": 2.03, "trend_5d": [-0.3, 0.5, -0.8, 0.2, -1.1]},
        "161725": {"current_nav": 1.85, "trend_5d": [1.2, 0.8, 1.5, -0.3, 0.9]},
        "110011": {"current_nav": 4.52, "trend_5d": [-0.5, -0.2, 0.3, -0.8, -0.4]},
    }
    data = mock_db.get(fund_code)
    if data and data["trend_5d"]:
        return {"est_nav": data["current_nav"], "est_change": data["trend_5d"][-1], "est_time": "最近收盘", "is_live": False}
    return {"est_nav": 0, "est_change": 0.0, "est_time": "暂无数据", "is_live": False}
