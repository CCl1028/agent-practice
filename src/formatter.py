"""输出格式化 — 三层递进展示"""

from __future__ import annotations

from src.state import Briefing

# 操作 → emoji 映射
ACTION_EMOJI = {
    "加仓": "🟢",
    "减仓": "🔴",
    "观望": "⏸️",
}


def format_push_notification(briefing: Briefing) -> str:
    """第一层：推送通知 — 1秒看完"""
    summary = briefing.get("summary", "暂无建议")
    has_action = any(
        d["action"] != "观望" for d in briefing.get("details", [])
    )
    emoji = "⚡" if has_action else "✅"
    return f"📊 今日持仓：{summary} {emoji}"


def format_briefing_card(briefing: Briefing) -> str:
    """第二层：简报卡片 — 10秒看完"""
    lines = ["┌─────────────────────────────────────┐"]

    for d in briefing.get("details", []):
        emoji = ACTION_EMOJI.get(d["action"], "⏸️")
        # 找到 profit_ratio 需要从外部传入，这里先只显示 action
        lines.append(f"│  {d['fund_name']}  👉 {d['action']} {emoji}")

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

    # 每只基金详情
    lines.append("📊 持仓建议：")
    lines.append("-" * 40)
    for d in briefing.get("details", []):
        emoji = ACTION_EMOJI.get(d["action"], "⏸️")
        lines.append(f"\n{emoji} {d['fund_name']}")
        lines.append(f"   操作：{d['action']}（置信度：{d.get('confidence', '中')}）")
        lines.append(f"   理由：{d.get('reason', '暂无')}")

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
