"""市场数据工具 — 获取行情、板块、新闻、估值"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# ---- 估值缓存 ----
# key: fund_code, value: {"est_nav", "est_change", "est_time", "is_live", "cached_at"}
_estimation_cache: dict[str, dict] = {}
_estimation_cache_lock = threading.Lock()
ESTIMATION_CACHE_TTL = 600  # 10 分钟

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


def _ensure_name_cache() -> None:
    """确保基金名称缓存已加载（供反向查找使用）。"""
    if _fund_name_cache:
        return
    try:
        import akshare as ak
        df = ak.fund_name_em()
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                code = str(row.get("基金代码", "")).strip()
                name = str(row.get("基金简称", "")).strip()
                if code and name:
                    _fund_name_cache[code] = name
    except Exception as e:
        logger.warning("[基金名称] AKShare 加载基金列表失败: %s", e)


def get_fund_code_by_name(fund_name: str) -> str | None:
    """通过基金名称反向查找基金代码（模糊匹配）。

    匹配策略（按优先级）：
    1. 精确匹配
    2. 名称包含查询词（如 "易方达蓝筹" 匹配 "易方达蓝筹精选混合"）
    3. 查询词包含基金名称
    4. 去掉后缀（混合/A/C/LOF等）后匹配

    Returns:
        基金代码字符串，匹配失败返回 None。
    """
    if not fund_name or fund_name == "未知基金":
        return None

    _ensure_name_cache()
    if not _fund_name_cache:
        return None

    query = fund_name.strip()

    # 1. 精确匹配
    for code, name in _fund_name_cache.items():
        if name == query:
            logger.info("[基金反查] 精确匹配: %s → %s", query, code)
            return code

    # 2. 基金名称包含查询词 或 查询词包含基金名称
    candidates = []
    for code, name in _fund_name_cache.items():
        if query in name or name in query:
            candidates.append((code, name, abs(len(name) - len(query))))

    if candidates:
        # 选择长度最接近的匹配
        candidates.sort(key=lambda x: x[2])
        best_code, best_name, _ = candidates[0]
        logger.info("[基金反查] 模糊匹配: %s → %s (%s)", query, best_code, best_name)
        return best_code

    # 3. 去掉常见后缀后再试
    import re
    cleaned = re.sub(r'(混合|股票|债券|指数|联接|增强|优选|精选|成长|价值|平衡|稳健|灵活配置|LOF|ETF|QDII|FOF)[A-Ca-c]?$', '', query).strip()
    if cleaned and cleaned != query:
        for code, name in _fund_name_cache.items():
            if cleaned in name or name.startswith(cleaned):
                logger.info("[基金反查] 清洗后匹配: %s → %s → %s (%s)", query, cleaned, code, name)
                return code

    logger.info("[基金反查] 未找到匹配: %s", query)
    return None


def verify_and_fix_fund(fund_code: str, fund_name: str) -> tuple[str, str]:
    """验证基金代码与名称是否匹配，不匹配时尝试修正。

    Returns:
        (corrected_code, corrected_name)
    """
    if not fund_code and not fund_name:
        return fund_code, fund_name

    _ensure_name_cache()

    # 情况1: 有代码，验证代码对应的名称
    if fund_code and len(fund_code) == 6:
        real_name = _fund_name_cache.get(fund_code)
        if real_name:
            # 代码有效，检查名称是否大致匹配
            if fund_name and fund_name != "未知基金":
                # 名称完全不相关 → 代码可能是 LLM 猜错的
                if fund_name not in real_name and real_name not in fund_name:
                    # 用名称反查正确代码
                    correct_code = get_fund_code_by_name(fund_name)
                    if correct_code:
                        correct_name = _fund_name_cache.get(correct_code, fund_name)
                        logger.info(
                            "[基金校正] 代码名称不匹配！代码 %s→%s 名称 %s→%s",
                            fund_code, correct_code, real_name, correct_name,
                        )
                        return correct_code, correct_name
            # 代码有效且名称匹配（或无名称可比对），用真实名称
            return fund_code, real_name
        else:
            # 代码无效（不存在），用名称反查
            if fund_name and fund_name != "未知基金":
                correct_code = get_fund_code_by_name(fund_name)
                if correct_code:
                    correct_name = _fund_name_cache.get(correct_code, fund_name)
                    logger.info(
                        "[基金校正] 无效代码 %s，通过名称 %s 反查到 %s (%s)",
                        fund_code, fund_name, correct_code, correct_name,
                    )
                    return correct_code, correct_name
            return fund_code, fund_name

    # 情况2: 无代码，只有名称
    if fund_name and fund_name != "未知基金":
        correct_code = get_fund_code_by_name(fund_name)
        if correct_code:
            correct_name = _fund_name_cache.get(correct_code, fund_name)
            logger.info("[基金校正] 无代码，通过名称 %s 查到 %s (%s)", fund_name, correct_code, correct_name)
            return correct_code, correct_name

    return fund_code or "", fund_name or "未知基金"


def is_trading_hours() -> bool:
    """判断当前是否在交易时段（工作日 9:30-15:00）。"""
    now = datetime.now()
    if now.weekday() >= 5:  # 周六日
        return False
    t = now.hour * 100 + now.minute
    return 930 <= t <= 1500


def get_fund_estimation(fund_code: str) -> dict | None:
    """获取基金估值数据（优先读缓存）。

    交易时段：返回盘中实时估值（AKShare），缓存 10 分钟。
    非交易时段：根据最近两日净值计算上一交易日收盘涨跌幅，缓存更久。

    Returns:
        {
            "est_nav": 2.05,
            "est_change": -0.85,
            "est_time": "15:00" 或 "03-31 收盘",
            "is_live": True/False,
        }
        或 None
    """
    # 先查缓存
    with _estimation_cache_lock:
        cached = _estimation_cache.get(fund_code)
    if cached:
        age = time.time() - cached.get("cached_at", 0)
        ttl = ESTIMATION_CACHE_TTL if is_trading_hours() else ESTIMATION_CACHE_TTL * 6
        if age < ttl:
            return {k: v for k, v in cached.items() if k != "cached_at"}

    result = _fetch_fund_estimation(fund_code)

    # 写缓存
    if result:
        with _estimation_cache_lock:
            _estimation_cache[fund_code] = {**result, "cached_at": time.time()}

    return result


def _fetch_fund_estimation(fund_code: str) -> dict | None:
    """实际从 AKShare 获取基金估值（不读缓存）。"""
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
                else:
                    # 该基金不在估值列表中（如 QDII），回退到收盘净值
                    logger.info("[估值] %s 不在实时估值列表中（可能是QDII/LOF），回退到收盘数据", fund_code)
                    return _get_last_close_change(fund_code)
        except Exception as e:
            logger.warning("AKShare 获取基金 %s 实时估值失败: %s", fund_code, e)
        return _get_last_close_change(fund_code)

    # 非交易时段：从净值历史计算上一交易日收盘涨跌
    return _get_last_close_change(fund_code)


def refresh_estimation_cache(fund_codes: list[str]) -> dict[str, dict | None]:
    """批量刷新估值缓存（供后台定时任务调用）。

    Returns: {fund_code: estimation_dict}
    """
    results = {}
    # 交易时段可以一次性拉取全量估值表，减少重复请求
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
        if code in bulk_data:
            est = bulk_data[code]
        else:
            # QDII 等不在估值列表中的，逐个拉取收盘数据
            est = _get_last_close_change(code)
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


def get_fund_nav_history(fund_code: str, start: str = "", end: str = "") -> list[dict]:
    """获取基金历史净值列表（用于定投补执行按历史净值计算）。

    Args:
        fund_code: 基金代码
        start: 起始日期 YYYY-MM-DD（可选）
        end: 截止日期 YYYY-MM-DD（可选）

    Returns:
        [{"date": "2026-03-26", "nav": 1.8310}, ...]
    """
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

    # fallback: 返回空列表
    return []


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
