"""用户注册/登录/JWT 单元测试"""

import os
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.user_auth import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


@pytest.fixture(scope="module")
def client():
    """创建测试客户端（每个模块新建临时数据库）"""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp.name}"

    from src.database.engine import init_db, reset_engine
    from src.routes.user import router

    reset_engine()  # 确保使用新的 DATABASE_URL

    app = FastAPI()
    app.include_router(router)
    init_db()
    yield TestClient(app, raise_server_exceptions=False)

    # Cleanup
    reset_engine()
    os.unlink(tmp.name)
    del os.environ["DATABASE_URL"]


class TestPasswordHashing:
    def test_hash_and_verify(self):
        h = hash_password("hello123")
        assert verify_password("hello123", h)
        assert not verify_password("wrong", h)

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt salt ensures different hashes


class TestJWT:
    def test_create_and_decode(self):
        token = create_token(42, "alice")
        payload = decode_token(token)
        assert payload is not None
        assert payload["user_id"] == 42
        assert payload["username"] == "alice"

    def test_invalid_token(self):
        assert decode_token("garbage.token.here") is None

    def test_expired_token(self):
        import time
        import jwt as pyjwt
        payload = {"user_id": 1, "username": "x", "exp": int(time.time()) - 100}
        token = pyjwt.encode(payload, "fundpal-dev-secret-change-in-production", algorithm="HS256")
        assert decode_token(token) is None


class TestUserAPI:
    def test_register_success(self, client):
        r = client.post("/api/user/register", json={
            "username": "testuser",
            "password": "pass123456",
            "nickname": "Tester",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["user"]["username"] == "testuser"
        assert data["user"]["nickname"] == "Tester"

    def test_register_duplicate(self, client):
        r = client.post("/api/user/register", json={
            "username": "testuser",
            "password": "another",
        })
        assert r.status_code == 409

    def test_register_short_password(self, client):
        r = client.post("/api/user/register", json={
            "username": "short",
            "password": "123",
        })
        assert r.status_code == 422  # Pydantic validation

    def test_login_success(self, client):
        r = client.post("/api/user/login", json={
            "username": "testuser",
            "password": "pass123456",
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert data["user"]["username"] == "testuser"

    def test_login_wrong_password(self, client):
        r = client.post("/api/user/login", json={
            "username": "testuser",
            "password": "wrongpass",
        })
        assert r.status_code == 401

    def test_login_nonexistent_user(self, client):
        r = client.post("/api/user/login", json={
            "username": "nobody",
            "password": "pass123",
        })
        assert r.status_code == 401

    def test_me_authenticated(self, client):
        # Login first
        login_r = client.post("/api/user/login", json={
            "username": "testuser",
            "password": "pass123456",
        })
        token = login_r.json()["token"]

        r = client.get("/api/user/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["username"] == "testuser"

    def test_me_no_token(self, client):
        r = client.get("/api/user/me")
        assert r.status_code == 401

    def test_me_invalid_token(self, client):
        r = client.get("/api/user/me", headers={"Authorization": "Bearer invalid.token"})
        assert r.status_code == 401
