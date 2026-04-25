"""简报路由 — /api/briefing, /api/briefing-and-push, /api/briefing/stream"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.core.auth import verify_token
from src.core.rate_limit import strict_rate_limit_dependency
from src.core.exceptions import BriefingTimeoutError
from src.formatter import format_briefing_card, format_full_report, format_push_notification
from src.graph import app as langgraph_app
from src.models.schemas import BriefingResponse, HoldingsInput
from src.tools.portfolio_tools import load_portfolio
from src.tools.push_tools import push_briefing

logger = logging.getLogger(__name__)

router = APIRouter()


def _sse_event(event: str, data: dict) -> str:
    """格式化 SSE 事件。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/api/briefing", response_model=BriefingResponse, dependencies=[Depends(strict_rate_limit_dependency)])
async def generate_briefing(input: Optional[HoldingsInput] = None):
    """生成每日简报（支持接收前端传来的持仓）"""
    holdings = input.holdings if input and input.holdings else load_portfolio()
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(langgraph_app.invoke, {"trigger": "daily_briefing", "holdings": holdings}),
            timeout=120.0,
        )
    except TimeoutError:
        logger.error("[简报生成] 超时（120秒）")
        raise BriefingTimeoutError("简报生成超时，请稍后重试") from None
    briefing = result.get("briefing", {})
    return BriefingResponse(
        notification=format_push_notification(briefing),
        card=format_briefing_card(briefing),
        report=format_full_report(briefing),
        raw=briefing,
    )


@router.post("/api/briefing/stream", dependencies=[Depends(strict_rate_limit_dependency)])
async def stream_briefing(input: Optional[HoldingsInput] = None):
    """SSE 流式简报 — 逐步推送进度和结果"""
    holdings = input.holdings if input and input.holdings else load_portfolio()

    async def event_stream():
        yield _sse_event("progress", {"step": "start", "message": "开始生成简报..."})

        yield _sse_event("progress", {"step": "portfolio", "message": "正在分析持仓数据..."})

        try:
            from src.agents.portfolio_agent import portfolio_node
            from src.agents.market_agent import market_node
            from src.agents.briefing_agent import briefing_node

            state = {"trigger": "daily_briefing", "holdings": holdings}

            # Step 1: Portfolio Agent
            state = await asyncio.wait_for(
                asyncio.to_thread(portfolio_node, state), timeout=60.0
            )
            yield _sse_event("progress", {"step": "market", "message": "正在获取市场行情..."})

            # Step 2: Market Agent
            state = await asyncio.wait_for(
                asyncio.to_thread(market_node, state), timeout=60.0
            )
            yield _sse_event("progress", {"step": "briefing", "message": "AI 正在生成投资建议..."})

            # Step 3: Briefing Agent
            state = await asyncio.wait_for(
                asyncio.to_thread(briefing_node, state), timeout=60.0
            )

            briefing = state.get("briefing", {})
            result = {
                "notification": format_push_notification(briefing),
                "card": format_briefing_card(briefing),
                "report": format_full_report(briefing),
                "raw": briefing,
            }
            yield _sse_event("complete", result)

        except TimeoutError:
            logger.error("[流式简报] 超时")
            yield _sse_event("error", {"message": "简报生成超时，请稍后重试"})
        except Exception as e:
            logger.error("[流式简报] 失败: %s", e)
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/api/briefing-and-push", dependencies=[Depends(verify_token), Depends(strict_rate_limit_dependency)])
async def generate_and_push(input: Optional[HoldingsInput] = None):
    """生成简报并推送"""
    holdings = input.holdings if input and input.holdings else load_portfolio()
    config = input.config if input and input.config else {}
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(langgraph_app.invoke, {"trigger": "daily_briefing", "holdings": holdings}),
            timeout=120.0,
        )
    except TimeoutError:
        logger.error("[简报推送] 超时（120秒）")
        raise BriefingTimeoutError("简报生成超时，请稍后重试") from None
    briefing = result.get("briefing", {})
    push_results = push_briefing(briefing, config=config or None)
    return {
        "notification": format_push_notification(briefing),
        "card": format_briefing_card(briefing),
        "report": format_full_report(briefing),
        "raw": briefing,
        "push_results": push_results,
    }
