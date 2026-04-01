"""FastAPI 服务 — 基金助手 API + Web UI"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.formatter import format_briefing_card, format_full_report, format_push_notification
from src.graph import app as langgraph_app
from src.tools.nlp_input import parse_natural_language
from src.tools.portfolio_tools import load_portfolio, save_portfolio
from src.tools.push_tools import get_push_status, push_briefing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="基金投资助手", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Models ----

class BriefingResponse(BaseModel):
    notification: str
    card: str
    report: str
    raw: dict


class TextInput(BaseModel):
    text: str


class PortfolioResponse(BaseModel):
    holdings: list[dict]
    count: int


class AddResult(BaseModel):
    added: list[dict]
    total: int


# ---- API Routes ----

@app.post("/api/briefing", response_model=BriefingResponse)
async def generate_briefing():
    """生成每日简报"""
    result = langgraph_app.invoke({"trigger": "daily_briefing"})
    briefing = result.get("briefing", {})
    return BriefingResponse(
        notification=format_push_notification(briefing),
        card=format_briefing_card(briefing),
        report=format_full_report(briefing),
        raw=briefing,
    )


@app.get("/api/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """获取当前持仓"""
    holdings = load_portfolio()
    return PortfolioResponse(holdings=holdings, count=len(holdings))


@app.post("/api/portfolio/add-text", response_model=AddResult)
async def add_from_text(input: TextInput):
    """自然语言录入持仓"""
    try:
        new_holdings = parse_natural_language(input.text)
        if not new_holdings:
            return AddResult(added=[], total=0)

        existing = load_portfolio()
        existing_map = {f["fund_code"]: f for f in existing if f.get("fund_code")}
        for h in new_holdings:
            if h.get("fund_code"):
                existing_map[h["fund_code"]] = h
        merged = list(existing_map.values())
        save_portfolio(merged)
        return AddResult(added=new_holdings, total=len(merged))
    except Exception as e:
        logger.error("add-text 失败: %s", e)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/portfolio/add-screenshot", response_model=AddResult)
async def add_from_screenshot(file: UploadFile = File(...)):
    """截图识别录入持仓"""
    try:
        from src.tools.ocr_tools import process_screenshot

        suffix = Path(file.filename or "img.jpg").suffix
        contents = await file.read()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        new_holdings = process_screenshot(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)

        if not new_holdings:
            return AddResult(added=[], total=0)

        existing = load_portfolio()
        existing_map = {f["fund_code"]: f for f in existing if f.get("fund_code")}
        for h in new_holdings:
            if h.get("fund_code"):
                existing_map[h["fund_code"]] = h
        merged = list(existing_map.values())
        save_portfolio(merged)
        return AddResult(added=new_holdings, total=len(merged))
    except Exception as e:
        logger.error("add-screenshot 失败: %s", e, exc_info=True)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/portfolio/{fund_code}")
async def delete_holding(fund_code: str):
    """删除一只持仓"""
    existing = load_portfolio()
    filtered = [f for f in existing if f.get("fund_code") != fund_code]
    save_portfolio(filtered)
    return {"deleted": fund_code, "remaining": len(filtered)}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ---- 推送相关 ----

@app.get("/api/push/status")
async def push_status():
    """获取推送渠道配置状态"""
    return get_push_status()


@app.post("/api/push/test")
async def test_push():
    """测试推送（发送一条测试消息）"""
    test_briefing = {
        "summary": "这是一条推送测试",
        "details": [
            {
                "fund_name": "测试基金",
                "action": "观望",
                "reason": "推送功能测试中",
                "confidence": "高",
            }
        ],
        "market_note": "推送测试 — 如果你收到了这条消息，说明推送配置成功！",
    }
    results = push_briefing(test_briefing)
    return {"push_results": results}


@app.post("/api/briefing-and-push")
async def generate_and_push():
    """生成简报并推送"""
    result = langgraph_app.invoke({"trigger": "daily_briefing"})
    briefing = result.get("briefing", {})
    push_results = push_briefing(briefing)
    return {
        "notification": format_push_notification(briefing),
        "card": format_briefing_card(briefing),
        "report": format_full_report(briefing),
        "raw": briefing,
        "push_results": push_results,
    }


# ---- 配置管理 ----

ENV_PATH = Path(__file__).parent / ".env"

# 允许通过网页配置的 key（白名单，防止注入危险配置）
ALLOWED_KEYS = {
    "OPENAI_API_KEY", "OPENAI_BASE_URL",
    "BARK_URL", "SERVERCHAN_KEY", "WECOM_WEBHOOK_URL",
}

# 需要脱敏显示的 key
SENSITIVE_KEYS = {"OPENAI_API_KEY", "SERVERCHAN_KEY"}


def _read_env() -> dict[str, str]:
    """读取 .env 文件为 dict。"""
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


def _write_env(env: dict[str, str]) -> None:
    """将 dict 写回 .env 文件。"""
    lines = []
    for k, v in env.items():
        if k in ALLOWED_KEYS and v:
            lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _mask(value: str) -> str:
    """脱敏：只显示前4位和后4位。"""
    if len(value) <= 10:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


class ConfigUpdate(BaseModel):
    key: str
    value: str


@app.get("/api/config")
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


@app.post("/api/config")
async def update_config(item: ConfigUpdate):
    """更新单个配置项"""
    if item.key not in ALLOWED_KEYS:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"error": f"不允许修改 {item.key}"})

    env = _read_env()
    if item.value:
        env[item.key] = item.value
    else:
        env.pop(item.key, None)
    _write_env(env)

    # 让配置立即生效
    load_dotenv(str(ENV_PATH), override=True)

    return {"ok": True, "key": item.key}


# ---- 静态文件 & 前端 ----

static_dir = Path(__file__).parent / "web"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """SPA fallback: 所有非 API 路由返回 index.html"""
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")
