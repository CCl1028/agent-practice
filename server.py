"""FastAPI 服务 — 基金助手 API + Web UI"""

from __future__ import annotations

import collections
import logging
import os
import shutil
import tempfile
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from fastapi import FastAPI, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.formatter import format_briefing_card, format_full_report, format_push_notification
from src.graph import app as langgraph_app
from src.tools.nlp_input import parse_natural_language
from src.tools.portfolio_tools import load_portfolio, save_portfolio
from src.tools.push_tools import get_push_status, push_briefing

# ---- 内存日志收集器 ----
MAX_LOG_LINES = 500

class _MemoryLogHandler(logging.Handler):
    """将日志存入内存环形缓冲区，供前端查看。"""
    def __init__(self, maxlen: int = MAX_LOG_LINES):
        super().__init__()
        self.buffer: collections.deque[dict] = collections.deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord):
        try:
            entry = {
                "ts": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "msg": self.format(record),
            }
            if record.exc_info and record.exc_info[0]:
                entry["msg"] += "\n" + "".join(traceback.format_exception(*record.exc_info))
            self.buffer.append(entry)
        except Exception:
            pass

    def get_logs(self, limit: int = 200, level: str | None = None) -> list[dict]:
        logs = list(self.buffer)
        if level:
            level_upper = level.upper()
            logs = [l for l in logs if l["level"] == level_upper]
        return logs[-limit:]

    def clear(self):
        self.buffer.clear()

memory_log_handler = _MemoryLogHandler(maxlen=MAX_LOG_LINES)
memory_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s", datefmt="%H:%M:%S"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
# 把内存 handler 挂到 root logger，捕获所有模块日志
logging.getLogger().addHandler(memory_log_handler)

logger = logging.getLogger(__name__)

# ---- 定时推送调度器 ----

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

PUSH_JOB_ID = "daily_push"
ESTIMATION_JOB_ID = "estimation_refresh"
DEFAULT_PUSH_TIME = "14:30"  # 默认下午两点半


def _scheduled_push():
    """定时任务：生成简报并推送。"""
    logger.info("[定时推送] 开始执行...")
    try:
        result = langgraph_app.invoke({"trigger": "daily_briefing"})
        briefing = result.get("briefing", {})
        push_results = push_briefing(briefing)
        for channel, status in push_results.items():
            if status is True:
                logger.info("[定时推送] %s 推送成功", channel)
            elif status is False:
                logger.warning("[定时推送] %s 推送失败", channel)
        logger.info("[定时推送] 执行完成")
    except Exception as e:
        logger.error("[定时推送] 执行失败: %s", e, exc_info=True)


def _scheduled_estimation_refresh():
    """定时任务：每 10 分钟刷新持仓估值缓存。"""
    from src.tools.market_tools import refresh_estimation_cache
    try:
        holdings = load_portfolio()
        codes = [h.get("fund_code", "") for h in holdings if h.get("fund_code")]
        if not codes:
            return
        refresh_estimation_cache(codes)
    except Exception as e:
        logger.error("[估值缓存] 定时刷新失败: %s", e, exc_info=True)


def _get_push_time() -> str:
    """从 .env 读取推送时间，格式 HH:MM。"""
    load_dotenv(override=True)
    return os.getenv("PUSH_TIME", DEFAULT_PUSH_TIME)


def _update_scheduler(time_str: str | None = None):
    """根据时间字符串更新定时任务。传 None 或空字符串则关闭定时推送。"""
    # 先移除旧任务
    if scheduler.get_job(PUSH_JOB_ID):
        scheduler.remove_job(PUSH_JOB_ID)

    if not time_str:
        logger.info("[定时推送] 已关闭定时推送")
        return

    try:
        hour, minute = [int(x) for x in time_str.split(":")]
        scheduler.add_job(
            _scheduled_push,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=PUSH_JOB_ID,
            replace_existing=True,
        )
        logger.info("[定时推送] 已设置每日 %02d:%02d 推送", hour, minute)
    except Exception as e:
        logger.error("[定时推送] 设置失败: %s", e)


@asynccontextmanager
async def lifespan(app_instance):
    """应用启动/关闭生命周期。"""
    push_time = _get_push_time()
    _update_scheduler(push_time)

    # 每 10 分钟刷新估值缓存
    from apscheduler.triggers.interval import IntervalTrigger
    scheduler.add_job(
        _scheduled_estimation_refresh,
        trigger=IntervalTrigger(minutes=10),
        id=ESTIMATION_JOB_ID,
        replace_existing=True,
    )

    scheduler.start()
    logger.info("[调度器] 已启动（定时推送 + 估值缓存 10min 刷新）")

    # 启动时立即预热一次估值缓存
    import threading
    threading.Thread(target=_scheduled_estimation_refresh, daemon=True).start()

    yield
    scheduler.shutdown(wait=False)
    logger.info("[调度器] 已关闭")


app = FastAPI(title="基金投资助手", version="0.1.0", lifespan=lifespan)

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


class HoldingsInput(BaseModel):
    holdings: list[dict] = []


class PortfolioResponse(BaseModel):
    holdings: list[dict]
    count: int


class AddResult(BaseModel):
    added: list[dict]
    total: int


class ParseResult(BaseModel):
    parsed: list[dict]


# ---- API Routes ----

@app.post("/api/briefing", response_model=BriefingResponse)
async def generate_briefing(input: HoldingsInput = None):
    """生成每日简报（支持接收前端传来的持仓）"""
    holdings = input.holdings if input and input.holdings else load_portfolio()
    result = langgraph_app.invoke({"trigger": "daily_briefing", "holdings": holdings})
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


@app.post("/api/portfolio/parse-text", response_model=ParseResult)
async def parse_text(input: TextInput):
    """解析自然语言持仓描述（只解析不保存）"""
    try:
        new_holdings = parse_natural_language(input.text)
        return ParseResult(parsed=new_holdings or [])
    except Exception as e:
        logger.error("parse-text 失败: %s", e)
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


@app.post("/api/portfolio/parse-screenshot", response_model=ParseResult)
async def parse_screenshot(file: UploadFile = File(...)):
    """截图识别持仓（只解析不保存）"""
    try:
        from src.tools.ocr_tools import process_screenshot

        suffix = Path(file.filename or "img.jpg").suffix
        contents = await file.read()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        new_holdings = process_screenshot(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)

        return ParseResult(parsed=new_holdings or [])
    except Exception as e:
        logger.error("parse-screenshot 失败: %s", e, exc_info=True)
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


# ---- 日志查看 ----

@app.get("/api/logs")
async def get_logs(limit: int = Query(200, ge=1, le=500), level: str = Query(None)):
    """获取最近的应用日志"""
    logs = memory_log_handler.get_logs(limit=limit, level=level)
    return {"logs": logs, "total": len(memory_log_handler.buffer)}


@app.delete("/api/logs")
async def clear_logs():
    """清空日志缓冲区"""
    memory_log_handler.clear()
    return {"ok": True}


@app.get("/api/version")
async def version():
    """获取当前版本信息"""
    import json
    version_file = Path(__file__).parent / "version.json"
    if version_file.exists():
        try:
            return json.loads(version_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": "dev", "build_time": "unknown", "git_commit": "unknown"}


# ---- 持仓刷新（根据最新净值更新市值和收益率） ----

@app.post("/api/portfolio/refresh")
async def refresh_portfolio(input: HoldingsInput = None):
    """根据最新净值，为每只基金计算当前市值和收益率。

    前端传入持仓列表（含 cost / cost_nav），后端查最新净值后返回更新后的持仓。
    不会修改服务器存储。
    """
    from src.tools.market_tools import get_fund_nav

    holdings = input.holdings if input and input.holdings else []
    updated = []
    for h in holdings:
        fund_code = h.get("fund_code", "")
        if not fund_code:
            updated.append(h)
            continue

        item = {**h}  # shallow copy
        try:
            nav_data = get_fund_nav(fund_code)
            current_nav = nav_data.get("current_nav", 0)
            item["current_nav"] = current_nav
            item["trend_5d"] = nav_data.get("trend_5d", [])

            cost_nav = h.get("cost_nav", 0)
            cost = h.get("cost", 0)

            if cost_nav and cost_nav > 0 and current_nav > 0:
                # 有成本净值：精确计算收益率和当前市值
                item["profit_ratio"] = round(
                    (current_nav - cost_nav) / cost_nav * 100, 2
                )
                if cost > 0:
                    shares = cost / cost_nav  # 持有份额
                    item["market_value"] = round(shares * current_nav, 2)
                else:
                    item["market_value"] = 0
            elif cost > 0 and current_nav > 0:
                # 没有成本净值但有成本金额：用估值涨跌近似
                old_ratio = h.get("profit_ratio", 0) or 0
                item["market_value"] = round(cost * (1 + old_ratio / 100), 2)
            else:
                item["market_value"] = h.get("cost", 0)
        except Exception as e:
            logger.warning("[持仓刷新] %s 获取净值失败: %s", fund_code, e)
            item["market_value"] = h.get("cost", 0)

        updated.append(item)

    return {"holdings": updated}


# ---- 盘中估值 ----

@app.post("/api/estimation")
async def post_estimation(input: HoldingsInput = None):
    """获取持仓的估值（POST 方式，接收前端传来的持仓）"""
    from src.tools.market_tools import get_fund_estimation, is_trading_hours

    holdings = input.holdings if input and input.holdings else load_portfolio()
    results = []
    for h in holdings:
        est = get_fund_estimation(h.get("fund_code", ""))
        results.append({
            "fund_code": h.get("fund_code", ""),
            "fund_name": h.get("fund_name", ""),
            "est_change": est["est_change"] if est else None,
            "est_nav": est["est_nav"] if est else None,
            "est_time": est["est_time"] if est else None,
            "is_live": est.get("is_live", False) if est else None,
        })
    return {
        "trading_hours": is_trading_hours(),
        "funds": results,
    }


@app.get("/api/estimation")
async def get_estimation():
    """获取所有持仓的估值（GET 方式，兼容旧版，从服务器读取）"""
    from src.tools.market_tools import get_fund_estimation, is_trading_hours

    holdings = load_portfolio()
    results = []
    for h in holdings:
        est = get_fund_estimation(h.get("fund_code", ""))
        results.append({
            "fund_code": h.get("fund_code", ""),
            "fund_name": h.get("fund_name", ""),
            "est_change": est["est_change"] if est else None,
            "est_nav": est["est_nav"] if est else None,
            "est_time": est["est_time"] if est else None,
            "is_live": est.get("is_live", False) if est else None,
        })
    return {
        "trading_hours": is_trading_hours(),
        "funds": results,
    }


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
async def generate_and_push(input: HoldingsInput = None):
    """生成简报并推送"""
    holdings = input.holdings if input and input.holdings else load_portfolio()
    result = langgraph_app.invoke({"trigger": "daily_briefing", "holdings": holdings})
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
    """读取 .env 文件所有键值对（含注释外的所有行）。"""
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
        if k in env and env[k]:
            all_env[k] = env[k]
        else:
            all_env.pop(k, None)
    _write_env_all(all_env)


def _write_env_all(env: dict[str, str]) -> None:
    """将完整 dict 写回 .env 文件。"""
    lines = []
    for k, v in env.items():
        if v:
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
