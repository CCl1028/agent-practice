"""基金名称映射 — 代码↔名称双向查找 + 校验修正"""

from __future__ import annotations

import logging
import re
import json as json_mod
import threading
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

# ---- 基金代码 → 名称缓存（线程安全） ----

_fund_name_cache: dict[str, str] = {}
_fund_name_cache_write_lock = threading.Lock()
_name_cache_loading = False
_name_cache_lock = threading.Lock()


def get_fund_name_by_code(fund_code: str) -> str | None:
    """通过基金代码查询真实基金名称（AKShare），带内存缓存。"""
    if not fund_code or len(fund_code) != 6:
        return None

    if fund_code in _fund_name_cache:
        return _fund_name_cache[fund_code]

    try:
        import akshare as ak
        df = ak.fund_name_em()
        if df is not None and not df.empty:
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


def _ensure_name_cache(timeout: float = 10.0) -> None:
    """确保基金名称缓存已加载。"""
    global _name_cache_loading

    if _fund_name_cache:
        return

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

    load_thread = threading.Thread(target=_load_cache, daemon=True)
    load_thread.start()
    load_thread.join(timeout=timeout)
    if load_thread.is_alive():
        logger.warning("[基金名称] 加载基金列表超时（%.1fs），跳过校验", timeout)


def get_fund_code_by_name(fund_name: str) -> str | None:
    """通过基金名称反向查找基金代码（模糊匹配）。"""
    if not fund_name or fund_name == "未知基金":
        return None

    _ensure_name_cache()
    query = fund_name.strip()

    if _fund_name_cache:
        # 1. 精确匹配
        for code, name in _fund_name_cache.items():
            if name == query:
                logger.info("[基金反查] 精确匹配: %s → %s", query, code)
                return code

        # 2. 模糊匹配
        candidates = []
        for code, name in _fund_name_cache.items():
            if query in name or name in query:
                candidates.append((code, name, abs(len(name) - len(query))))
        if candidates:
            candidates.sort(key=lambda x: x[2])
            best_code, best_name, _ = candidates[0]
            logger.info("[基金反查] 模糊匹配: %s → %s (%s)", query, best_code, best_name)
            return best_code

        # 3. 去掉常见后缀后再试
        cleaned = re.sub(
            r"(混合|股票|债券|指数|联接|增强|优选|精选|成长|价值|平衡|稳健|灵活配置|LOF|ETF|QDII|FOF)[A-Ca-c]?$",
            "", query,
        ).strip()
        if cleaned and cleaned != query:
            for code, name in _fund_name_cache.items():
                if cleaned in name or name.startswith(cleaned):
                    logger.info("[基金反查] 清洗后匹配: %s → %s → %s (%s)", query, cleaned, code, name)
                    return code

    # 4. 在线搜索 fallback
    online_result = _search_fund_online(query)
    if online_result:
        code, name = online_result
        _fund_name_cache[code] = name
        logger.info("[基金反查] 在线搜索匹配: %s → %s (%s)", query, code, name)
        return code

    logger.info("[基金反查] 未找到匹配: %s", query)
    return None


def _search_fund_online(fund_name: str) -> tuple[str, str] | None:
    """通过天天基金搜索 API 在线模糊搜索基金代码。"""
    try:
        encoded = urllib.parse.quote(fund_name)
        url = f"https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx?m=1&key={encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json_mod.loads(resp.read().decode("utf-8"))

        if data.get("ErrCode") != 0 or not data.get("Datas"):
            return None

        funds = [d for d in data["Datas"] if d.get("CATEGORY") == 700]
        if not funds:
            return None

        best = funds[0]
        code = best.get("CODE", "")
        name = best.get("NAME", "").strip()
        if code and len(code) == 6:
            return code, name
    except Exception as e:
        logger.warning("[基金反查] 在线搜索失败: %s", e)
    return None


def verify_and_fix_fund(fund_code: str, fund_name: str, timeout: float = 5.0) -> tuple[str, str]:
    """验证基金代码与名称是否匹配，不匹配时尝试修正。"""
    if not fund_code and not fund_name:
        return fund_code, fund_name

    _ensure_name_cache(timeout=timeout)

    # 情况1: 有代码
    if fund_code and len(fund_code) == 6:
        real_name = _fund_name_cache.get(fund_code)
        if real_name:
            if fund_name and fund_name != "未知基金" and fund_name not in real_name and real_name not in fund_name:
                correct_code = get_fund_code_by_name(fund_name)
                if correct_code:
                    correct_name = _fund_name_cache.get(correct_code, fund_name)
                    logger.info("[基金校正] 代码名称不匹配！%s→%s %s→%s", fund_code, correct_code, real_name, correct_name)
                    return correct_code, correct_name
            return fund_code, real_name
        else:
            if fund_name and fund_name != "未知基金":
                correct_code = get_fund_code_by_name(fund_name)
                if correct_code:
                    correct_name = _fund_name_cache.get(correct_code, fund_name)
                    logger.info("[基金校正] 无效代码 %s，反查到 %s (%s)", fund_code, correct_code, correct_name)
                    return correct_code, correct_name
            return fund_code, fund_name

    # 情况2: 无代码
    if fund_name and fund_name != "未知基金":
        correct_code = get_fund_code_by_name(fund_name)
        if correct_code:
            correct_name = _fund_name_cache.get(correct_code, fund_name)
            logger.info("[基金校正] 无代码，反查到 %s (%s)", correct_code, correct_name)
            return correct_code, correct_name

    return fund_code or "", fund_name or "未知基金"
