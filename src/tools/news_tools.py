"""新闻搜索工具 — 4 引擎 + 多维度

支持 4 个搜索引擎（按优先级自动切换，任一成功即返回）：
1. Tavily  — 推荐首选，免费 1000 次/月，注册: https://tavily.com/
2. 博查搜索 — 中文搜索优化，支持 AI 摘要，注册: https://open.bocha.cn/
3. Brave    — 隐私优先，海外基金/美股优化，注册: https://brave.com/search/api/
4. SerpAPI  — Google 搜索 API，兜底，注册: https://serpapi.com/

搜索维度：
- 基金新闻：最新消息 / 风险排查 / 业绩持仓（3 维度）
- 市场新闻：大盘热点 / 板块走势（2 维度）

无搜索 Key 时优雅降级为空列表（不影响主流程）。
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# 简易搜索结果缓存 {cache_key: {"results": [...], "cached_at": float}}
_search_cache: dict[str, dict] = {}
_CACHE_TTL = 3600  # 1 小时


def search_fund_news(fund_name: str, fund_code: str) -> list[dict]:
    """搜索基金相关新闻。

    搜索维度：
    1. 最新消息 — 该基金近期有什么新闻
    2. 风险排查 — 有没有利空/赎回/下跌相关消息
    3. 业绩持仓 — 业绩表现、调仓换股信息

    Args:
        fund_name: 基金名称
        fund_code: 基金代码

    Returns:
        [{"title", "snippet", "url", "source", "dimension"}]
    """
    queries = [
        (f"{fund_name} {fund_code} 最新消息 基金", "latest"),
        (f"{fund_name} 风险 利空 赎回 下跌", "risk"),
        (f"{fund_name} 业绩 持仓 调仓 规模", "performance"),
    ]

    results = []
    for query, dimension in queries:
        items = _search_with_cache(query, max_results=3)
        for item in items:
            item["dimension"] = dimension
        results.extend(items)

    logger.info("[新闻搜索] %s(%s) 共获取 %d 条新闻", fund_name, fund_code, len(results))
    return results


def search_market_news() -> list[dict]:
    """搜索大盘/行业热点新闻。

    Returns:
        [{"title", "snippet", "url", "source", "dimension"}]
    """
    today = datetime.now().strftime("%Y年%m月%d日")
    queries = [
        (f"A股 {today} 市场 热点 涨跌", "market"),
        (f"基金 行业 板块 走势 {today}", "sector"),
    ]

    results = []
    for query, dimension in queries:
        items = _search_with_cache(query, max_results=4)
        for item in items:
            item["dimension"] = dimension
        results.extend(items)

    logger.info("[新闻搜索] 市场新闻共获取 %d 条", len(results))
    return results


def format_news_for_prompt(news_items: list[dict]) -> str:
    """将新闻列表格式化为 Prompt 文本。"""
    if not news_items:
        return "暂无相关新闻"

    lines = []
    for item in news_items:
        dim_label = {
            "latest": "📰",
            "risk": "🚨",
            "performance": "📊",
            "market": "🌐",
            "sector": "📈",
        }.get(item.get("dimension", ""), "📰")
        lines.append(f"{dim_label} {item['title']}")
        if item.get("snippet"):
            lines.append(f"   {item['snippet'][:120]}")
    return "\n".join(lines)


# ---- 内部实现 ----

def _search_with_cache(query: str, max_results: int = 3) -> list[dict]:
    """带缓存的搜索入口。"""
    cache_key = f"{query}:{max_results}"

    # 检查缓存
    cached = _search_cache.get(cache_key)
    if cached and time.time() - cached["cached_at"] < _CACHE_TTL:
        return cached["results"]

    results = _search(query, max_results)

    # 写入缓存
    _search_cache[cache_key] = {"results": results, "cached_at": time.time()}

    # 缓存淘汰（超过 200 条时清理最老的一半）
    if len(_search_cache) > 200:
        sorted_keys = sorted(_search_cache, key=lambda k: _search_cache[k]["cached_at"])
        for k in sorted_keys[: len(sorted_keys) // 2]:
            del _search_cache[k]

    return results


def _search(query: str, max_results: int = 3) -> list[dict]:
    """按优先级尝试 4 个搜索引擎，任一成功即返回。

    优先级：
    1. Tavily  — 推荐，免费 1000 次/月，质量最好
    2. 博查搜索 — 中文搜索优化，支持 AI 摘要
    3. Brave    — 隐私优先，美股/海外基金优化
    4. SerpAPI  — Google 搜索 API，兜底
    """

    # 1. Tavily（推荐，免费 1000 次/月）
    tavily_keys = os.getenv("TAVILY_API_KEY", "") or os.getenv("TAVILY_API_KEYS", "")
    if tavily_keys:
        key = tavily_keys.split(",")[0].strip()
        try:
            return _search_tavily(query, key, max_results)
        except Exception as e:
            logger.warning("[Tavily] 搜索失败: %s", e)

    # 2. 博查搜索（中文优化）
    bocha_keys = os.getenv("BOCHA_API_KEY", "") or os.getenv("BOCHA_API_KEYS", "")
    if bocha_keys:
        key = bocha_keys.split(",")[0].strip()
        try:
            return _search_bocha(query, key, max_results)
        except Exception as e:
            logger.warning("[Bocha] 搜索失败: %s", e)

    # 3. Brave Search（隐私优先）
    brave_keys = os.getenv("BRAVE_API_KEY", "") or os.getenv("BRAVE_API_KEYS", "")
    if brave_keys:
        key = brave_keys.split(",")[0].strip()
        try:
            return _search_brave(query, key, max_results)
        except Exception as e:
            logger.warning("[Brave] 搜索失败: %s", e)

    # 4. SerpAPI（兜底）
    serp_keys = os.getenv("SERPAPI_API_KEY", "") or os.getenv("SERPAPI_API_KEYS", "")
    if serp_keys:
        key = serp_keys.split(",")[0].strip()
        try:
            return _search_serpapi(query, key, max_results)
        except Exception as e:
            logger.warning("[SerpAPI] 搜索失败: %s", e)

    # 全部未配置或全部失败
    logger.debug("[新闻搜索] 无可用搜索引擎，请配置至少一个: TAVILY_API_KEY / BOCHA_API_KEY / BRAVE_API_KEY / SERPAPI_API_KEY")
    return []


# ---- 各搜索引擎实现 ----

def _search_tavily(query: str, api_key: str, max_results: int) -> list[dict]:
    """Tavily 搜索 — https://tavily.com/ 免费 1000 次/月。"""
    from tavily import TavilyClient

    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, max_results=max_results, search_depth="basic")
    return [
        {
            "title": r.get("title", ""),
            "snippet": (r.get("content", "") or "")[:200],
            "url": r.get("url", ""),
            "source": "tavily",
        }
        for r in response.get("results", [])
    ]


def _search_bocha(query: str, api_key: str, max_results: int) -> list[dict]:
    """博查搜索 — https://open.bocha.cn/ 中文搜索优化，支持 AI 摘要。"""
    import httpx

    resp = httpx.post(
        "https://api.bochaai.com/v1/web-search",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"query": query, "count": max_results, "summary": True},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("web_results", data.get("results", []))[:max_results]:
        results.append({
            "title": item.get("title", ""),
            "snippet": (item.get("summary", "") or item.get("description", "") or "")[:200],
            "url": item.get("url", ""),
            "source": "bocha",
        })
    return results


def _search_brave(query: str, api_key: str, max_results: int) -> list[dict]:
    """Brave Search — https://brave.com/search/api/ 隐私优先，海外基金/美股优化。"""
    import httpx

    resp = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
        params={"q": query, "count": max_results, "search_lang": "zh-hans"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("web", {}).get("results", [])[:max_results]:
        results.append({
            "title": item.get("title", ""),
            "snippet": (item.get("description", "") or "")[:200],
            "url": item.get("url", ""),
            "source": "brave",
        })
    return results


def _search_serpapi(query: str, api_key: str, max_results: int) -> list[dict]:
    """SerpAPI (Google Search) — https://serpapi.com/ 兜底搜索。"""
    from serpapi import GoogleSearch

    params = {
        "q": query,
        "api_key": api_key,
        "num": max_results,
        "hl": "zh-cn",
        "gl": "cn",
    }
    search = GoogleSearch(params)
    results = search.get_dict().get("organic_results", [])
    return [
        {
            "title": r.get("title", ""),
            "snippet": (r.get("snippet", "") or "")[:200],
            "url": r.get("link", ""),
            "source": "serpapi",
        }
        for r in results[:max_results]
    ]
