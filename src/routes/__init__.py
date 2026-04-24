"""路由注册 — 将所有路由挂载到 FastAPI app"""

from __future__ import annotations

from fastapi import FastAPI

from src.routes.briefing import router as briefing_router
from src.routes.portfolio import router as portfolio_router
from src.routes.estimation import router as estimation_router
from src.routes.diagnosis import router as diagnosis_router
from src.routes.push import router as push_router
from src.routes.config import router as config_router
from src.routes.system import router as system_router


def register_routes(app: FastAPI) -> None:
    """将所有路由注册到 app。"""
    app.include_router(briefing_router)
    app.include_router(portfolio_router)
    app.include_router(estimation_router)
    app.include_router(diagnosis_router)
    app.include_router(push_router)
    app.include_router(config_router)
    app.include_router(system_router)
