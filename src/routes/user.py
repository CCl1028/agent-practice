"""用户路由 — /api/user/register, /api/user/login, /api/user/me"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.core.user_auth import get_current_user, login_user, register_user

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    nickname: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/api/user/register")
async def api_register(req: RegisterRequest):
    """用户注册"""
    user = register_user(req.username, req.password, req.nickname)
    return {"ok": True, "user": user}


@router.post("/api/user/login")
async def api_login(req: LoginRequest):
    """用户登录 — 返回 JWT token"""
    result = login_user(req.username, req.password)
    return result


@router.get("/api/user/me")
async def api_me(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user
