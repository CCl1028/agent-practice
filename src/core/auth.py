"""API 认证 — 支持两种认证方式

1. 静态 API_TOKEN（旧方式，兼容部署 token）
2. JWT 用户 token（新方式，用户登录后自动使用）

认证逻辑：
- API_TOKEN 未配置 → 只验证 JWT（有则验证，无则跳过）
- API_TOKEN 已配置 → Bearer token 匹配 API_TOKEN 或 有效 JWT 均可通过
"""

from __future__ import annotations

import logging
import os

from fastapi import Depends, HTTPException, Header

logger = logging.getLogger(__name__)


async def verify_token(authorization: str = Header(None)) -> None:
    """认证依赖 — 支持 API_TOKEN 或 JWT。

    通过条件（满足任一即可）：
    1. API_TOKEN 未配置（开发模式，完全跳过）
    2. Bearer token == API_TOKEN（静态 token 认证）
    3. Bearer token 是有效的 JWT（用户登录认证）
    """
    expected_api_token = os.getenv("API_TOKEN", "")

    # 没配 API_TOKEN → 只验证 JWT 是否有效（如果传了的话）
    if not expected_api_token:
        # 开发模式：有 JWT 就验证（防止伪造），没有也放行
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
            if _is_valid_jwt(token):
                return
        return  # 开发模式放行

    # 有 API_TOKEN 配置 → 必须携带有效认证
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权：缺少 Bearer Token")

    token = authorization[7:]

    # 方式 1: 匹配静态 API_TOKEN
    if token == expected_api_token:
        return

    # 方式 2: 验证 JWT
    if _is_valid_jwt(token):
        return

    raise HTTPException(status_code=401, detail="未授权：Token 无效")


def _is_valid_jwt(token: str) -> bool:
    """检查 token 是否是有效的 JWT。"""
    try:
        from src.core.user_auth import decode_token
        payload = decode_token(token)
        return payload is not None
    except Exception:
        return False


# 便捷依赖
require_auth = Depends(verify_token)
