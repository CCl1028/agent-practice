"""简报路由 — /api/briefing, /api/briefing-and-push"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends

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
