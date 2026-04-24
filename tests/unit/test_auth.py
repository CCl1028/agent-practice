"""认证模块单元测试 — Bearer Token 校验"""

import asyncio
import pytest
from fastapi import HTTPException
from src.core.auth import verify_token


def _run(coro):
    """同步运行异步函数"""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestVerifyToken:
    """verify_token 依赖测试"""

    def test_no_token_configured_passes(self, monkeypatch):
        """未配置 API_TOKEN → 跳过认证"""
        monkeypatch.delenv("API_TOKEN", raising=False)
        result = _run(verify_token(authorization=None))
        assert result is None

    def test_empty_token_configured_passes(self, monkeypatch):
        """API_TOKEN 为空 → 跳过认证"""
        monkeypatch.setenv("API_TOKEN", "")
        result = _run(verify_token(authorization=None))
        assert result is None

    def test_valid_token(self, monkeypatch):
        """有效 Token → 通过"""
        monkeypatch.setenv("API_TOKEN", "my-secret")
        result = _run(verify_token(authorization="Bearer my-secret"))
        assert result is None

    def test_missing_header(self, monkeypatch):
        """配置了 Token 但未携带 → 401"""
        monkeypatch.setenv("API_TOKEN", "my-secret")
        with pytest.raises(HTTPException) as exc_info:
            _run(verify_token(authorization=None))
        assert exc_info.value.status_code == 401

    def test_wrong_token(self, monkeypatch):
        """错误 Token → 401"""
        monkeypatch.setenv("API_TOKEN", "my-secret")
        with pytest.raises(HTTPException) as exc_info:
            _run(verify_token(authorization="Bearer wrong-token"))
        assert exc_info.value.status_code == 401

    def test_no_bearer_prefix(self, monkeypatch):
        """缺少 Bearer 前缀 → 401"""
        monkeypatch.setenv("API_TOKEN", "my-secret")
        with pytest.raises(HTTPException) as exc_info:
            _run(verify_token(authorization="my-secret"))
        assert exc_info.value.status_code == 401

    def test_basic_auth_rejected(self, monkeypatch):
        """Basic Auth 格式 → 401"""
        monkeypatch.setenv("API_TOKEN", "my-secret")
        with pytest.raises(HTTPException) as exc_info:
            _run(verify_token(authorization="Basic dXNlcjpwYXNz"))
        assert exc_info.value.status_code == 401
