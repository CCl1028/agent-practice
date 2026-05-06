"""用户认证 — JWT + bcrypt 密码哈希

注册/登录流程：
1. 注册：username + password → bcrypt hash → 存 DB
2. 登录：验证密码 → 签发 JWT → 返回 token
3. 认证：请求头 Authorization: Bearer <jwt> → 解析 user_id
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request

from src.database.engine import get_session
from src.database.models import User

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "fundpal-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 7 * 24  # 7 天过期


def hash_password(password: str) -> str:
    """密码哈希（bcrypt）"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: int, username: str) -> str:
    """签发 JWT"""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": int(time.time()) + JWT_EXPIRE_HOURS * 3600,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """解析 JWT，失败返回 None"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_current_user(request: Request) -> dict:
    """FastAPI 依赖 — 从 Authorization 头解析当前用户。

    返回 {"user_id": int, "username": str}
    未登录时抛 401。
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录，请先登录")

    token = auth_header[7:]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    return {"user_id": payload["user_id"], "username": payload["username"]}


def get_optional_user(request: Request) -> Optional[dict]:
    """FastAPI 依赖 — 可选认证（未登录返回 None，不报错）。

    用于兼容旧接口：登录用户走数据隔离，未登录走默认 user_id=0。
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    return decode_token(token)


# ---- 用户 CRUD ----

def register_user(username: str, password: str, nickname: str = "") -> dict:
    """注册用户，返回用户信息。username 重复抛异常。"""
    with get_session() as s:
        existing = s.query(User).filter_by(username=username).first()
        if existing:
            raise HTTPException(status_code=409, detail="用户名已存在")

        user = User(
            username=username,
            password_hash=hash_password(password),
            nickname=nickname or username,
        )
        s.add(user)
        s.commit()
        s.refresh(user)
        return {"user_id": user.id, "username": user.username, "nickname": user.nickname}


def login_user(username: str, password: str) -> dict:
    """登录验证，返回 token + 用户信息。"""
    with get_session() as s:
        user = s.query(User).filter_by(username=username).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        s.commit()

        token = create_token(user.id, user.username)
        return {
            "token": token,
            "user": {
                "user_id": user.id,
                "username": user.username,
                "nickname": user.nickname,
            },
        }
