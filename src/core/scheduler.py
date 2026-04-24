"""定时任务调度器 — 推送 + 估值缓存刷新"""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

PUSH_JOB_ID = "daily_push"
ESTIMATION_JOB_ID = "estimation_refresh"
DEFAULT_PUSH_TIME = "14:30"


def _scheduled_push():
    """定时任务：生成简报并推送。"""
    from src.graph import app as langgraph_app
    from src.tools.push_tools import push_briefing

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
    from src.tools.portfolio_tools import load_portfolio

    try:
        holdings = load_portfolio()
        codes = [h.get("fund_code", "") for h in holdings if h.get("fund_code")]
        if not codes:
            return
        refresh_estimation_cache(codes)
    except Exception as e:
        logger.error("[估值缓存] 定时刷新失败: %s", e, exc_info=True)


def get_push_time() -> str:
    """从 .env 读取推送时间，格式 HH:MM。"""
    load_dotenv(override=True)
    return os.getenv("PUSH_TIME", DEFAULT_PUSH_TIME)


def update_scheduler(time_str: str | None = None):
    """根据时间字符串更新定时任务。传 None 或空字符串则关闭定时推送。"""
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


def start_scheduler():
    """启动调度器（定时推送 + 估值缓存刷新）。"""
    import threading

    push_time = get_push_time()
    update_scheduler(push_time)

    scheduler.add_job(
        _scheduled_estimation_refresh,
        trigger=IntervalTrigger(minutes=10),
        id=ESTIMATION_JOB_ID,
        replace_existing=True,
    )

    scheduler.start()
    logger.info("[调度器] 已启动（定时推送 + 估值缓存 10min 刷新）")

    # 启动时立即预热一次估值缓存
    threading.Thread(target=_scheduled_estimation_refresh, daemon=True).start()


def stop_scheduler():
    """关闭调度器。"""
    scheduler.shutdown(wait=False)
    logger.info("[调度器] 已关闭")
