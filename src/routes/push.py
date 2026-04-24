"""推送路由 — /api/push/*"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from src.core.auth import verify_token
from src.core.rate_limit import rate_limit_dependency
from src.models.schemas import PushTestInput
from src.tools.push_tools import get_push_status, push_briefing

router = APIRouter()


@router.post("/api/push/status")
async def push_status_post(input: Optional[PushTestInput] = None):
    """获取推送渠道配置状态（POST）"""
    config = input.config if input else {}
    return get_push_status(config=config or None)


@router.get("/api/push/status")
async def push_status():
    """获取推送渠道配置状态（GET，兼容旧版）"""
    return get_push_status()


@router.post("/api/push/test", dependencies=[Depends(verify_token), Depends(rate_limit_dependency)])
async def test_push(input: Optional[PushTestInput] = None):
    """测试推送"""
    config = input.config if input else {}
    test_briefing = {
        "summary": "这是一条推送测试",
        "details": [
            {
                "fund_name": "测试基金",
                "action": "观望",
                "reason": "推送功能测试中",
                "confidence": "高",
            }
        ],
        "market_note": "推送测试 — 如果你收到了这条消息，说明推送配置成功！",
    }
    results = push_briefing(test_briefing, config=config or None)
    return {"push_results": results}
