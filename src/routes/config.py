"""配置管理路由 — /api/config"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Depends

from src.core.auth import verify_token
from src.core.exceptions import ConfigError
from src.models.schemas import ConfigUpdate

logger = logging.getLogger(__name__)

router = APIRouter()

ENV_PATH = Path(__file__).parents[2] / ".env"

ALLOWED_KEYS = {
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "BARK_URL",
    "SERVERCHAN_KEY",
    "WECOM_WEBHOOK_URL",
    "API_TOKEN",
}

SENSITIVE_KEYS = {"OPENAI_API_KEY", "SERVERCHAN_KEY", "API_TOKEN"}


def _read_env() -> dict[str, str]:
    """读取 .env 文件为 dict（仅白名单 key）。"""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                if k in ALLOWED_KEYS:
                    env[k] = v.strip()
    return env


def _read_env_all() -> dict[str, str]:
    """读取 .env 文件所有键值对。"""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _write_env(env: dict[str, str]) -> None:
    """将 dict 写回 .env 文件（仅白名单 key）。"""
    all_env = _read_env_all()
    for k in ALLOWED_KEYS:
        if env.get(k):
            all_env[k] = env[k]
        else:
            all_env.pop(k, None)
    lines = [f"{k}={v}" for k, v in all_env.items() if v]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _mask(value: str) -> str:
    """脱敏：只显示前4位和后4位。"""
    if len(value) <= 10:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


@router.get("/api/config")
async def get_config():
    """获取当前配置（敏感字段脱敏）"""
    env = _read_env()
    result = {}
    for k in ALLOWED_KEYS:
        v = env.get(k, "")
        result[k] = {
            "value": _mask(v) if (v and k in SENSITIVE_KEYS) else v,
            "has_value": bool(v),
            "sensitive": k in SENSITIVE_KEYS,
        }
    return result


@router.post("/api/config", dependencies=[Depends(verify_token)])
async def update_config(item: ConfigUpdate):
    """更新单个配置项"""
    if item.key not in ALLOWED_KEYS:
        raise ConfigError(f"不允许修改 {item.key}")

    env = _read_env()
    if item.value:
        env[item.key] = item.value
    else:
        env.pop(item.key, None)
    _write_env(env)

    load_dotenv(str(ENV_PATH), override=True)
    return {"ok": True, "key": item.key}
