"""输出格式化 — 三层递进展示

v2: 适配新字段（评分/风险提示/持有操作/risk_alerts）
"""

from __future__ import annotations

from src.state import Briefing

# 操作 → emoji 映射
ACTION_EMOJI = {
    "加仓": "🟢",
    "减仓": "🔴",
    "观望": "⏸️",
    "持有": "🔵",
}


def format_push_notification(briefing: Briefing) -> str:
    """第一层：推送通知 — 1秒看完"""
    summary = briefing.get("summary", "暂无建议")
    has_action = any(
        d["action"] not in ("观望", "持有") for d in briefing.get("details", [])
    )
    has_risk = bool(briefing.get("risk_alerts"))
    if has_risk:
        emoji = "⚠️"
    elif has_action:
        emoji = "⚡"
    else:
        emoji = "✅"
    return f"📊 今日持仓：{summary} {emoji}"


def format_briefing_card(briefing: Briefing) -> str:
    """第二层：简报卡片 — 10秒看完"""
    lines = ["┌─────────────────────────────────────┐"]

    for d in briefing.get("details", []):
        emoji = ACTION_EMOJI.get(d["action"], "⏸️")
        score = d.get("score", 0)
        score_str = f" ({score}分)" if score else ""
        lines.append(f"│  {d['fund_name']}  👉 {d['action']} {emoji}{score_str}")

    lines.append("│")

    # 风险提示
    risk_alerts = briefing.get("risk_alerts", [])
    if risk_alerts:
        lines.append("│  ⚠️ 风险提示:")
        for alert in risk_alerts[:3]:
            lines.append(f"│    · {alert}")
        lines.append("│")

    market_note = briefing.get("market_note", "")
    if market_note:
        lines.append(f"│  市场：{market_note}")

    summary = briefing.get("summary", "")
    if summary:
        lines.append(f"│  💡 {summary}")

    lines.append("└─────────────────────────────────────┘")
    return "\n".join(lines)


def format_full_report(briefing: Briefing) -> str:
    """第三层：完整报告"""
    lines = ["=" * 40, "📋 今日投资简报", "=" * 40, ""]

    # 总结
    lines.append(f"📌 总结：{briefing.get('summary', '')}")
    lines.append("")

    # 全局风险提示
    risk_alerts = briefing.get("risk_alerts", [])
    if risk_alerts:
        lines.append("🚨 风险提示：")
        for alert in risk_alerts:
            lines.append(f"   · {alert}")
        lines.append("")

    # 每只基金详情
    lines.append("📊 持仓建议：")
    lines.append("-" * 40)
    for d in briefing.get("details", []):
        emoji = ACTION_EMOJI.get(d["action"], "⏸️")
        score = d.get("score", 0)
        lines.append(f"\n{emoji} {d['fund_name']}")
        lines.append(f"   操作：{d['action']}（置信度：{d.get('confidence', '中')} | 评分：{score}）")
        lines.append(f"   理由：{d.get('reason', '暂无')}")
        risk_note = d.get("risk_note", "")
        if risk_note:
            lines.append(f"   ⚠️ {risk_note}")

    lines.append("")
    lines.append("-" * 40)

    # 市场简评
    market_note = briefing.get("market_note", "")
    if market_note:
        lines.append(f"\n🌐 市场简评：{market_note}")

    lines.append("\n" + "=" * 40)
    return "\n".join(lines)


def format_all(briefing: Briefing) -> str:
    """输出所有三层格式"""
    return "\n\n".join([
        "【推送通知】",
        format_push_notification(briefing),
        "",
        "【简报卡片】",
        format_briefing_card(briefing),
        "",
        "【完整报告】",
        format_full_report(briefing),
    ])
