"""FastAPI 服务 — 基金助手 API + Web UI

Phase B 重构后的精简入口：仅负责 app 初始化、中间件、lifespan。
所有路由拆分到 src/routes/，模型拆分到 src/models/，
调度器拆分到 src/core/scheduler.py，日志拆分到 src/core/logging.py。
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.exceptions import FundPalError
from src.core.logging import setup_logging
from src.core.scheduler import start_scheduler, stop_scheduler
from src.routes import register_routes
from src.routes.system import mount_frontend

# ---- 日志初始化 ----
setup_logging()


@asynccontextmanager
async def lifespan(app_instance):
    """应用启动/关闭生命周期。"""
    load_dotenv()
    from src.config import validate_config
    validate_config()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="基金投资助手", version="0.1.0", lifespan=lifespan)

# ---- CORS ----
_cors_env = os.getenv("CORS_ORIGINS", "")
_cors_origins = (
    [o.strip() for o in _cors_env.split(",") if o.strip()]
    if _cors_env
    else ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"]
)
app.add_middleware(CORSMiddleware, allow_origins=_cors_origins, allow_methods=["*"], allow_headers=["*"])


# ---- 全局异常处理器 ----
@app.exception_handler(FundPalError)
async def fundpal_error_handler(request, exc: FundPalError):
    return JSONResponse(status_code=exc.status, content={"error": exc.message, "code": exc.code})


# ---- 注册路由 + 前端静态文件 ----
register_routes(app)
mount_frontend(app)
