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

# ---- 基金代码 → 名称查询（T-005: 添加线程安全锁） ----

_fund_name_cache: dict[str, str] = {}
_fund_name_cache_write_lock = threading.Lock()


def get_fund_name_by_code(fund_code: str) -> str | None:
    """通过基金代码查询真实基金名称（AKShare），带内存缓存。

    Returns:
        基金名称字符串，查询失败返回 None。
    """
    if not fund_code or len(fund_code) != 6:
        return None

    # 命中缓存直接返回（读取 dict 是线程安全的）
    if fund_code in _fund_name_cache:
        return _fund_name_cache[fund_code]

    try:
        import akshare as ak

        # fund_name_em 返回所有基金的代码+名称列表
        df = ak.fund_name_em()
        if df is not None and not df.empty:
            # 构建完整缓存（加锁保护写入，防止多线程重复加载）
            with _fund_name_cache_write_lock:
                if fund_code not in _fund_name_cache:
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


_name_cache_loading = False
_name_cache_lock = threading.Lock()


def _ensure_name_cache(timeout: float = 10.0) -> None:
    """确保基金名称缓存已加载（供反向查找使用）。

    Args:
        timeout: 加载超时时间（秒），超时后直接返回，不阻塞调用方
    """
    global _name_cache_loading

    if _fund_name_cache:
        return

    # 防止多线程重复加载
    with _name_cache_lock:
        if _fund_name_cache or _name_cache_loading:
            return
        _name_cache_loading = True

    def _load_cache():
        global _name_cache_loading
        try:
            import akshare as ak

            df = ak.fund_name_em()
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    code = str(row.get("基金代码", "")).strip()
                    name = str(row.get("基金简称", "")).strip()
                    if code and name:
                        _fund_name_cache[code] = name
                logger.info("[基金名称] 已加载 %d 只基金到缓存", len(_fund_name_cache))
        except Exception as e:
            logger.warning("[基金名称] AKShare 加载基金列表失败: %s", e)
        finally:
            _name_cache_loading = False

    # 使用线程加载，设置超时
    load_thread = threading.Thread(target=_load_cache, daemon=True)
    load_thread.start()
    load_thread.join(timeout=timeout)

    if load_thread.is_alive():
        logger.warning("[基金名称] 加载基金列表超时（%.1fs），跳过校验", timeout)


def get_fund_code_by_name(fund_name: str) -> str | None:
    """通过基金名称反向查找基金代码（模糊匹配）。

    匹配策略（按优先级）：
    1. 精确匹配
    2. 名称包含查询词（如 "易方达蓝筹" 匹配 "易方达蓝筹精选混合"）
    3. 查询词包含基金名称
    4. 去掉后缀（混合/A/C/LOF等）后匹配
    5. 天天基金在线搜索 API（本地匹配全部失败时的 fallback）

    Returns:
        基金代码字符串，匹配失败返回 None。
    """
    if not fund_name or fund_name == "未知基金":
        return None

    _ensure_name_cache()

    query = fund_name.strip()

    # Only try local cache matching if cache is loaded
    if _fund_name_cache:
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

        cleaned = re.sub(
            r"(混合|股票|债券|指数|联接|增强|优选|精选|成长|价值|平衡|稳健|灵活配置|LOF|ETF|QDII|FOF)[A-Ca-c]?$",
            "",
            query,
        ).strip()
        if cleaned and cleaned != query:
            for code, name in _fund_name_cache.items():
                if cleaned in name or name.startswith(cleaned):
                    logger.info("[基金反查] 清洗后匹配: %s → %s → %s (%s)", query, cleaned, code, name)
                    return code

    # 4. 本地匹配全部失败，尝试天天基金在线搜索 API
    online_result = _search_fund_online(query)
    if online_result:
        code, name = online_result
        # Cache the result for future lookups
        _fund_name_cache[code] = name
        logger.info("[基金反查] 在线搜索匹配: %s → %s (%s)", query, code, name)
        return code

    logger.info("[基金反查] 未找到匹配: %s", query)
    return None


def _search_fund_online(fund_name: str) -> tuple[str, str] | None:
    """通过天天基金搜索 API 在线模糊搜索基金代码。

    Args:
        fund_name: 基金名称关键词

    Returns:
        (fund_code, fund_name) 元组，搜索失败返回 None。
    """
    import json as json_mod
    import urllib.parse
    import urllib.request

    try:
        encoded = urllib.parse.quote(fund_name)
        url = f"https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx?m=1&key={encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json_mod.loads(resp.read().decode("utf-8"))

        if data.get("ErrCode") != 0 or not data.get("Datas"):
            return None

        # Filter to fund category only (CATEGORY=700)
        funds = [d for d in data["Datas"] if d.get("CATEGORY") == 700]
        if not funds:
            return None

        # Return the first (best) match
        best = funds[0]
        code = best.get("CODE", "")
        name = best.get("NAME", "").strip()
        if code and len(code) == 6:
            return code, name

    except Exception as e:
        logger.warning("[基金反查] 在线搜索失败: %s", e)

    return None


def verify_and_fix_fund(fund_code: str, fund_name: str, timeout: float = 5.0) -> tuple[str, str]:
    """验证基金代码与名称是否匹配，不匹配时尝试修正。

    Args:
        fund_code: 基金代码
        fund_name: 基金名称
        timeout: 缓存加载超时时间（秒）

    Returns:
        (corrected_code, corrected_name)
    """
    if not fund_code and not fund_name:
        return fund_code, fund_name

    _ensure_name_cache(timeout=timeout)

    # 情况1: 有代码，验证代码对应的名称
    if fund_code and len(fund_code) == 6:
        real_name = _fund_name_cache.get(fund_code)
        if real_name:
            # 代码有效，检查名称是否大致匹配
            if fund_name and fund_name != "未知基金" and fund_name not in real_name and real_name not in fund_name:
                # 名称完全不相关 → 代码可能是 LLM 猜错的，用名称反查正确代码
                correct_code = get_fund_code_by_name(fund_name)
                if correct_code:
                    correct_name = _fund_name_cache.get(correct_code, fund_name)
                    logger.info(
                        "[基金校正] 代码名称不匹配！代码 %s→%s 名称 %s→%s",
                        fund_code,
                        correct_code,
                        real_name,
                        correct_name,
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
                        fund_code,
                        fund_name,
                        correct_code,
                        correct_name,
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
            return [{"name": row["板块名称"], "change": round(float(row["涨跌幅"]), 2)} for _, row in top.iterrows()]
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
    data = mock_db.get(
        fund_code,
        {
            "current_nav": 1.50,
            "trend_5d": [0.1, -0.2, 0.3, -0.1, 0.2],
        },
    )
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


# ---- 新增: 基金诊断数据获取 ----


def get_fund_profile(fund_code_or_name: str) -> dict | None:
    """获取基金基本信息用于诊断分析。

    Returns:
        {
            "code": "005827",
            "name": "易方达蓝筹精选",
            "perf_1y": 15.5,          # 近1年收益百分比
            "perf_3y": 25.0,          # 近3年收益百分比
            "max_drawdown": -15.2,    # 最大回撤百分比
            "volatility": 8.5,        # 波动率百分比
            "size_billion": 120.5,    # 基金规模，单位亿元
            "sectors": ["消费", "制造业", "电子"],  # 重仓行业Top 3
            "manager": "李斌",
            "manager_perf": "良好",
        }
    """
    # 尝试如果输入是名称，则转换为代码
    fund_code = fund_code_or_name
    if not fund_code or len(fund_code) != 6:
        fund_code = get_fund_code_by_name(fund_code_or_name)

    if not fund_code or len(fund_code) != 6:
        logger.warning("[基金诊断] 无法解析基金代码: %s", fund_code_or_name)
        return None

    try:
        import akshare as ak

        # 获取基金基本信息
        df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="基本信息")
        if df is None or df.empty:
            raise ValueError("API returned empty data")

        row = df.iloc[0]
        fund_name = get_fund_name_by_code(fund_code) or row.get("基金名称", "")

        # 解析数据
        perf_1y = _parse_percentage(row.get("近1年", "0%"))
        perf_3y = _parse_percentage(row.get("近3年", "0%"))
        max_dd = _parse_percentage(row.get("最大回撤", "0%"))

        # 获取规模（单位：亿元）
        size_str = str(row.get("基金规模", "0")).strip()
        try:
            size_billion = float(size_str) if size_str and size_str != "0" else 50.0
        except ValueError:
            size_billion = 50.0

        # 获取波动率
        volatility = _parse_percentage(row.get("波动率", "10%")) or 10.0

        # Mock 重仓行业（实际可从 AKShare 的持仓接口获取）
        sectors = _get_mock_sectors(fund_code)

        # Mock 基金经理信息
        manager = row.get("基金经理", "未知")

        result = {
            "code": fund_code,
            "name": fund_name,
            "perf_1y": perf_1y or 0,
            "perf_3y": perf_3y or 0,
            "max_drawdown": max_dd or -15.0,
            "volatility": abs(volatility),  # 波动率取正
            "size_billion": size_billion,
            "sectors": sectors,
            "manager": manager,
            "manager_perf": "良好" if perf_1y and perf_1y > 10 else ("一般" if perf_1y and perf_1y > 0 else "较弱"),
        }

        logger.info("[基金诊断] 获取 %s(%s) 信息成功", fund_name, fund_code)
        return result

    except Exception as e:
        logger.warning("[基金诊断] 获取基金 %s 信息失败: %s，使用 mock", fund_code, e)
        return _mock_fund_profile(fund_code)


def get_fund_perf_analysis(fund_code_or_name: str) -> dict | None:
    """获取基金今日涨跌分析数据。

    Returns:
        {
            "code": "005827",
            "name": "易方达蓝筹精选",
            "today_change": 1.23,      # 今日涨跌百分比
            "sectors": ["消费", "制造业"],  # 重仓行业
            "sector_change": 0.85,      # 重仓行业平均涨跌
            "market_change": 0.52,      # 大盘涨跌
            "market_sentiment": "偏乐观",  # 市场情绪
        }
    """
    # 同上，解析基金代码
    fund_code = fund_code_or_name
    if not fund_code or len(fund_code) != 6:
        fund_code = get_fund_code_by_name(fund_code_or_name)

    if not fund_code or len(fund_code) != 6:
        logger.warning("[涨跌分析] 无法解析基金代码: %s", fund_code_or_name)
        return _mock_perf_analysis(fund_code_or_name)  # 使用 mock 数据

    try:
        # 获取今日估值
        nav_data = get_fund_nav(fund_code)
        today_change = nav_data.get("trend_5d", [0])[-1] if nav_data.get("trend_5d") else 0

        # 获取板块信息
        sectors = _get_mock_sectors(fund_code)
        sector_perf = get_sector_performance()
        sector_change = sum(s["change"] for s in sector_perf if s["name"] in sectors) / len(sectors) if sectors else 0

        # 大盘表现
        market_perf = get_sector_performance()
        market_change = market_perf[0]["change"] if market_perf else 0

        # 市场情绪
        market_sentiment = _judge_sentiment(market_perf)

        result = {
            "code": fund_code,
            "name": get_fund_name_by_code(fund_code) or "未知基金",
            "today_change": today_change,
            "sectors": sectors,
            "sector_change": round(sector_change, 2),
            "market_change": market_change,
            "market_sentiment": market_sentiment,
        }

        logger.info("[涨跌分析] %s 今日涨跌 %+.2f%%", result["name"], today_change)
        return result

    except Exception as e:
        logger.warning("[涨跌分析] 获取基金 %s 今日数据失败: %s", fund_code, e)
        return _mock_perf_analysis(fund_code)


# ---- 辅助函数 ----


def _parse_percentage(s: str | float) -> float | None:
    """将字符串百分比转换为浮点数。

    Examples:
        "15.5%" → 15.5
        "15.50" → 15.50
        15.5 → 15.5
    """
    if isinstance(s, (int, float)):
        return float(s)

    if not isinstance(s, str):
        return None

    s = s.strip()
    if not s:
        return None

    try:
        s = s.replace("%", "").strip()
        return float(s)
    except ValueError:
        return None


def _judge_sentiment(sectors: list[dict]) -> str:
    """根据板块涨跌判断市场情绪。"""
    if not sectors:
        return "中性"
    avg = sum(s["change"] for s in sectors) / len(sectors)
    if avg > 0.5:
        return "偏乐观"
    elif avg < -0.5:
        return "偏谨慎"
    return "中性震荡"


def _get_mock_sectors(fund_code: str) -> list[str]:
    """Mock 获取基金的重仓行业。"""
    mock_sectors = {
        "005827": ["消费", "制造业", "医药"],
        "161725": ["电子", "计算机", "通讯"],
        "110011": ["银行", "地产", "汽车"],
    }
    return mock_sectors.get(fund_code, ["消费", "科技", "医药"])


def _mock_fund_profile(fund_code: str) -> dict:
    """Mock 基金诊断数据"""
    return {
        "code": fund_code,
        "name": get_fund_name_by_code(fund_code) or "示例基金",
        "perf_1y": 15.2,
        "perf_3y": 25.5,
        "max_drawdown": -12.3,
        "volatility": 9.5,
        "size_billion": 85.5,
        "sectors": ["消费", "制造业", "医药"],
        "manager": "示例经理",
        "manager_perf": "良好",
    }


def _mock_perf_analysis(fund_code: str) -> dict:
    """Mock 涨跌分析数据"""
    return {
        "code": fund_code,
        "name": get_fund_name_by_code(fund_code) or "示例基金",
        "today_change": 1.23,
        "sectors": ["消费", "制造业"],
        "sector_change": 0.85,
        "market_change": 0.52,
        "market_sentiment": "偏乐观",
    }


def get_fund_news(fund_name: str, fund_code: str = "") -> list[dict]:
    """获取基金相关新闻（集成多个搜索引擎）。

    Args:
        fund_name: 基金名称
        fund_code: 基金代码（可选）

    Returns:
        新闻列表，每项包含 title, snippet, url, source
    """
    from src.tools.news_tools import search_fund_news

    try:
        news = search_fund_news(fund_name, fund_code)
        logger.info("[基金新闻] 获取 %s(%s) 共 %d 条新闻", fund_name, fund_code, len(news))
        return news
    except Exception as e:
        logger.warning("[基金新闻] 获取失败: %s", e)
        # 降级：返回空列表或 mock 数据
        return []
