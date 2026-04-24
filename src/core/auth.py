"""API 认证 — Bearer Token 校验

未配置 API_TOKEN 时自动跳过认证（本地开发友好）。
配置后，所有写操作路由需携带 Authorization: Bearer <token> 请求头。
"""

from __future__ import annotations

import logging
import os

from fastapi import Depends, HTTPException, Request, Header

logger = logging.getLogger(__name__)


async def verify_token(authorization: str = Header(None)) -> None:
    """Bearer Token 认证依赖。

    - 环境变量 API_TOKEN 未设置或为空 → 跳过认证（本地开发模式）
    - 设置后 → 必须携带有效的 Bearer Token
    """
    expected = os.getenv("API_TOKEN", "")
    if not expected:
        return  # 未配置 token 则跳过（本地开发）

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权：缺少 Bearer Token")

    token = authorization[7:]
    if token != expected:
        raise HTTPException(status_code=401, detail="未授权：Token 无效")


# 便捷依赖 — 用于路由装饰器 dependencies=[Depends(require_auth)]
require_auth = Depends(verify_token)
