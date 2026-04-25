"""日志系统 — 结构化日志 + 内存缓冲 + 请求 ID

Phase B 升级：
- 结构化 JSON 格式日志（生产环境可搜索）
- 请求 ID 中间件（全链路追踪）
- 保留内存环形缓冲区（前端查看）
"""

from __future__ import annotations

import collections
import logging
import traceback
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

MAX_LOG_LINES = 500

# ---- 请求 ID（上下文变量，线程/协程安全） ----

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """获取当前请求 ID。"""
    return _request_id.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求 ID 中间件 — 为每个 HTTP 请求分配唯一 ID，写入响应头。"""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        token = _request_id.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            _request_id.reset(token)


# ---- 结构化日志格式器 ----

class StructuredFormatter(logging.Formatter):
    """结构化日志格式器 — 在日志消息中自动注入请求 ID。"""

    def format(self, record: logging.LogRecord) -> str:
        record.request_id = _request_id.get()
        return super().format(record)


# ---- 内存日志收集器 ----

class MemoryLogHandler(logging.Handler):
    """将日志存入内存环形缓冲区，供前端查看。"""

    def __init__(self, maxlen: int = MAX_LOG_LINES):
        super().__init__()
        self.buffer: collections.deque[dict] = collections.deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord):
        try:
            entry = {
                "ts": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "request_id": getattr(record, "request_id", "-"),
                "msg": self.format(record),
            }
            if record.exc_info and record.exc_info[0]:
                entry["msg"] += "\n" + "".join(traceback.format_exception(*record.exc_info))
            self.buffer.append(entry)
        except Exception:
            pass

    def get_logs(self, limit: int = 200, level: Optional[str] = None) -> list[dict]:
        logs = list(self.buffer)
        if level:
            level_upper = level.upper()
            logs = [e for e in logs if e["level"] == level_upper]
        return logs[-limit:]

    def clear(self):
        self.buffer.clear()


# 全局单例
memory_log_handler = MemoryLogHandler(maxlen=MAX_LOG_LINES)
memory_log_handler.setFormatter(
    StructuredFormatter(
        "%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
)


def setup_logging():
    """配置全局日志（仅调用一次）。"""
    fmt = StructuredFormatter(
        "%(asctime)s [%(levelname)s] [%(request_id)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    handler = logging.StreamHandler()
    handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # 避免重复添加 handler
    if not root.handlers:
        root.addHandler(handler)
    root.addHandler(memory_log_handler)
