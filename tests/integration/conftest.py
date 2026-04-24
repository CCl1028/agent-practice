"""集成测试 fixtures — 测试用 FastAPI 客户端

使用 httpx + ASGITransport 直接测试路由，不启动真实服务器。
跳过 lifespan（不启动调度器），mock 外部依赖。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from src.core.exceptions import FundPalError
from src.routes import register_routes


@pytest.fixture
def test_app():
    """创建测试用 FastAPI app（无 lifespan，无调度器）"""
    app = FastAPI(title="FundPal Test")

    @app.exception_handler(FundPalError)
    async def _handler(request, exc: FundPalError):
        return JSONResponse(status_code=exc.status, content={"error": exc.message, "code": exc.code})

    register_routes(app)
    return app


@pytest.fixture
def client(test_app):
    """FastAPI TestClient（同步）"""
    return TestClient(test_app, raise_server_exceptions=False)


@pytest.fixture
def tmp_portfolio(tmp_path):
    """临时持仓文件，测试结束自动清理"""
    portfolio_file = tmp_path / "portfolio.json"
    portfolio_file.write_text("[]", encoding="utf-8")
    with patch("src.tools.portfolio_tools.DB_PATH", portfolio_file):
        yield portfolio_file


@pytest.fixture
def sample_portfolio(tmp_path):
    """带示例数据的临时持仓文件"""
    portfolio_file = tmp_path / "portfolio.json"
    data = [
        {
            "fund_code": "005827",
            "fund_name": "易方达蓝筹精选",
            "cost": 20000,
            "cost_nav": 2.15,
            "current_nav": 2.03,
            "profit_ratio": -5.58,
            "profit_amount": -1116.28,
            "shares": 9302.33,
            "hold_days": 280,
            "trend_5d": [-0.3, 0.5, -0.8, 0.2, -1.1],
        },
    ]
    portfolio_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with patch("src.tools.portfolio_tools.DB_PATH", portfolio_file):
        yield portfolio_file


@pytest.fixture(autouse=True)
def no_api_token(monkeypatch):
    """默认不配置 API_TOKEN（跳过认证）"""
    monkeypatch.delenv("API_TOKEN", raising=False)
