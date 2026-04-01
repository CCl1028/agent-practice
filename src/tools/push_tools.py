"""推送工具 — Bark / Server酱 / 企业微信 Webhook

支持三种推送渠道，都是零成本：
- Bark：推送到 iPhone 通知栏（最快最简单）
- Server酱（sct.ftqq.com）：推送到微信
- 企业微信 Webhook：推送到企业微信群
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _get_config():
    """每次调用时重新读取 .env，确保配置实时生效。"""
    load_dotenv(override=True)
    return {
        "bark_url": os.getenv("BARK_URL", ""),
        "serverchan_key": os.getenv("SERVERCHAN_KEY", ""),
        "wecom_webhook_url": os.getenv("WECOM_WEBHOOK_URL", ""),
    }


# ---- Bark ----

def push_to_bark(title: str, body: str, group: str = "基金管家") -> bool:
    """通过 Bark 推送消息到 iPhone。"""
    cfg = _get_config()
    bark_url = cfg["bark_url"]
    if not bark_url:
        logger.warning("[推送] 未配置 BARK_URL，跳过 Bark 推送")
        return False

    base_url = bark_url.rstrip("/")
    payload = {
        "title": title,
        "body": body,
        "group": group,
        "icon": "https://em-content.zobj.net/source/apple/391/chart-increasing_1f4c8.png",
        "sound": "minuet",
    }

    try:
        resp = httpx.post(f"{base_url}/", json=payload, timeout=10)
        data = resp.json()
        if data.get("code") == 200:
            logger.info("[推送] Bark 推送成功: %s", title)
            return True
        else:
            logger.error("[推送] Bark 返回错误: %s", data)
            return False
    except Exception as e:
        logger.error("[推送] Bark 推送失败: %s", e)
        return False


# ---- Server酱 ----

def push_to_serverchan(title: str, content: str = "") -> bool:
    """通过 Server酱 推送消息到微信。"""
    cfg = _get_config()
    key = cfg["serverchan_key"]
    if not key:
        logger.warning("[推送] 未配置 SERVERCHAN_KEY，跳过 Server酱 推送")
        return False

    url = f"https://sctapi.ftqq.com/{key}.send"
    try:
        resp = httpx.post(url, data={"title": title, "desp": content}, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            logger.info("[推送] Server酱 推送成功: %s", title)
            return True
        else:
            logger.error("[推送] Server酱 返回错误: %s", data)
            return False
    except Exception as e:
        logger.error("[推送] Server酱 推送失败: %s", e)
        return False


# ---- 企业微信 ----

def push_to_wecom(content: str) -> bool:
    """通过企业微信 Webhook 推送消息到群。"""
    cfg = _get_config()
    webhook_url = cfg["wecom_webhook_url"]
    if not webhook_url:
        logger.warning("[推送] 未配置 WECOM_WEBHOOK_URL，跳过企业微信推送")
        return False

    payload = {
        "msgtype": "markdown",
        "markdown": {"content": content},
    }
    try:
        resp = httpx.post(webhook_url, json=payload, timeout=10)
        data = resp.json()
        if data.get("errcode") == 0:
            logger.info("[推送] 企业微信推送成功")
            return True
        else:
            logger.error("[推送] 企业微信返回错误: %s", data)
            return False
    except Exception as e:
        logger.error("[推送] 企业微信推送失败: %s", e)
        return False


# ---- 格式化 ----

def format_briefing_for_push(briefing: dict) -> tuple[str, str]:
    """将简报数据格式化为推送内容。"""
    summary = briefing.get("summary", "暂无建议")
    details = briefing.get("details", [])
    market_note = briefing.get("market_note", "")
    today = datetime.now().strftime("%m月%d日")

    has_action = any(d.get("action") != "观望" for d in details)
    emoji = "⚡" if has_action else "✅"

    title = f"📊 {today}持仓简报：{summary} {emoji}"

    lines = [f"# {title}", ""]
    if details:
        lines.append("## 持仓建议")
        lines.append("")
        for d in details:
            action = d.get("action", "观望")
            action_emoji = {"加仓": "🟢", "减仓": "🔴", "观望": "⏸️"}.get(action, "⏸️")
            lines.append(f"**{d.get('fund_name', '未知')}** {action_emoji} {action}")
            reason = d.get("reason", "")
            if reason:
                lines.append(f"> {reason}")
            lines.append("")

    if market_note:
        lines.append("## 市场简评")
        lines.append(f"{market_note}")
        lines.append("")

    lines.append("---")
    lines.append(f"*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    return title, "\n".join(lines)


def format_briefing_for_bark(briefing: dict) -> tuple[str, str]:
    """格式化为 Bark 推送内容（简短，适合通知栏阅读）。"""
    summary = briefing.get("summary", "暂无建议")
    details = briefing.get("details", [])
    market_note = briefing.get("market_note", "")
    today = datetime.now().strftime("%m月%d日")

    has_action = any(d.get("action") != "观望" for d in details)
    emoji = "⚡" if has_action else "✅"

    title = f"{today} {summary} {emoji}"

    body_parts = []
    for d in details:
        action = d.get("action", "观望")
        action_emoji = {"加仓": "🟢", "减仓": "🔴", "观望": "⏸️"}.get(action, "⏸️")
        line = f"{action_emoji} {d.get('fund_name', '')} → {action}"
        reason = d.get("reason", "")
        if reason:
            line += f"（{reason}）"
        body_parts.append(line)

    if market_note:
        body_parts.append(f"\n📰 {market_note}")

    return title, "\n".join(body_parts)


def format_briefing_for_wecom(briefing: dict) -> str:
    """格式化为企业微信 Markdown。"""
    summary = briefing.get("summary", "暂无建议")
    details = briefing.get("details", [])
    market_note = briefing.get("market_note", "")
    today = datetime.now().strftime("%m月%d日")

    lines = [f"## 📊 {today} 基金简报", f"**{summary}**", ""]
    for d in details:
        action = d.get("action", "观望")
        action_emoji = {"加仓": "🟢", "减仓": "🔴", "观望": "⏸️"}.get(action, "⏸️")
        lines.append(f">{action_emoji} **{d.get('fund_name', '')}** — {action}")
        reason = d.get("reason", "")
        if reason:
            lines.append(f">{reason}")

    if market_note:
        lines.append(f"\n📰 {market_note}")

    return "\n".join(lines)


# ---- 统一推送 ----

def push_briefing(briefing: dict) -> dict:
    """推送简报到所有已配置的渠道。"""
    cfg = _get_config()
    title, content = format_briefing_for_push(briefing)
    results = {}

    # Bark
    if cfg["bark_url"]:
        bark_title, bark_body = format_briefing_for_bark(briefing)
        results["bark"] = push_to_bark(bark_title, bark_body)
    else:
        results["bark"] = None

    # Server酱
    if cfg["serverchan_key"]:
        results["serverchan"] = push_to_serverchan(title, content)
    else:
        results["serverchan"] = None

    # 企业微信
    if cfg["wecom_webhook_url"]:
        wecom_content = format_briefing_for_wecom(briefing)
        results["wecom"] = push_to_wecom(wecom_content)
    else:
        results["wecom"] = None

    return results


def get_push_status() -> dict:
    """获取推送渠道配置状态（实时读取 .env）。"""
    cfg = _get_config()
    return {
        "bark": {
            "configured": bool(cfg["bark_url"]),
            "name": "Bark（iPhone 推送）",
            "help": "App Store 下载 Bark，打开复制推送 URL",
        },
        "serverchan": {
            "configured": bool(cfg["serverchan_key"]),
            "name": "Server酱（微信推送）",
            "help": "访问 https://sct.ftqq.com 获取 SendKey",
        },
        "wecom": {
            "configured": bool(cfg["wecom_webhook_url"]),
            "name": "企业微信 Webhook",
            "help": "在企业微信群中添加群机器人获取 Webhook URL",
        },
    }
