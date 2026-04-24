"""系统路由 — /api/health, /api/logs, /api/version + SPA 静态文件"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.core.logging import memory_log_handler

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/health")
async def health():
    return {"status": "ok"}


@router.get("/api/logs")
async def get_logs(limit: int = Query(200, ge=1, le=500), level: str = Query(None)):
    """获取最近的应用日志"""
    logs = memory_log_handler.get_logs(limit=limit, level=level)
    return {"logs": logs, "total": len(memory_log_handler.buffer)}


@router.delete("/api/logs")
async def clear_logs():
    """清空日志缓冲区"""
    memory_log_handler.clear()
    return {"ok": True}


@router.get("/api/version")
async def version():
    """获取当前版本信息"""
    version_file = Path(__file__).parents[2] / "version.json"
    if version_file.exists():
        try:
            return json.loads(version_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": "dev", "build_time": "unknown", "git_commit": "unknown"}


def mount_frontend(app) -> None:
    """挂载前端静态文件 + SPA fallback（在所有 API 路由注册之后调用）"""
    _dist_dir = Path(__file__).parents[2] / "web" / "dist"
    _legacy_dir = Path(__file__).parents[2] / "web"
    static_dir = _dist_dir if _dist_dir.exists() else _legacy_dir

    if not static_dir.exists():
        return

    _assets_dir = static_dir / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """SPA fallback: 所有非 API 路由返回 index.html"""
        file_path = static_dir / full_path
        try:
            resolved = file_path.resolve()
            if not resolved.is_relative_to(static_dir.resolve()):
                logger.warning("[安全] 疑似路径穿越: %s", full_path)
                return FileResponse(static_dir / "index.html")
        except (ValueError, OSError):
            return FileResponse(static_dir / "index.html")
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")
