"""API 限流 — 基于内存的简单速率限制

轻量实现，无需 Redis 等外部依赖。适用于单实例部署。
"""

from __future__ import annotations

import time
import logging
from collections import defaultdict
from functools import wraps

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# 存储每个 IP 的请求时间戳列表
_request_log: dict[str, list[float]] = defaultdict(list)


def _get_client_ip(request: Request) -> str:
    """获取客户端 IP，支持反向代理。"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _cleanup_old_entries(ip: str, window: int) -> None:
    """清理过期的请求记录。"""
    now = time.time()
    cutoff = now - window
    _request_log[ip] = [t for t in _request_log[ip] if t > cutoff]


def check_rate_limit(request: Request, max_requests: int = 30, window: int = 60) -> None:
    """检查请求是否超过速率限制。

    Args:
        request: FastAPI Request 对象
        max_requests: 时间窗口内允许的最大请求数
        window: 时间窗口（秒）
    """
    ip = _get_client_ip(request)
    _cleanup_old_entries(ip, window)

    if len(_request_log[ip]) >= max_requests:
        logger.warning("[限流] IP %s 在 %ds 内请求 %d 次，已限流", ip, window, max_requests)
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，请 {window} 秒后重试",
            headers={"Retry-After": str(window)},
        )

    _request_log[ip].append(time.time())


async def rate_limit_dependency(request: Request) -> None:
    """通用限流依赖 — 30 次/分钟。"""
    check_rate_limit(request, max_requests=30, window=60)


async def strict_rate_limit_dependency(request: Request) -> None:
    """严格限流依赖 — 5 次/分钟（用于 LLM 调用等重操作）。"""
    check_rate_limit(request, max_requests=5, window=60)
