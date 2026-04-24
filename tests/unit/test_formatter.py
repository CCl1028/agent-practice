"""格式化输出单元测试 — 三层递进展示"""

import pytest
from src.formatter import (
    format_push_notification,
    format_briefing_card,
    format_full_report,
    format_all,
    ACTION_EMOJI,
)


def _make_briefing(**overrides) -> dict:
    base = {
        "summary": "今日建议观望",
        "details": [
            {
                "fund_name": "易方达蓝筹",
                "action": "观望",
                "reason": "趋势不明朗",
                "confidence": "中",
                "score": 50,
                "risk_note": "",
            }
        ],
        "market_note": "市场情绪偏弱",
        "risk_alerts": [],
    }
    base.update(overrides)
    return base


class TestPushNotification:
    """推送通知（第一层）"""

    def test_basic_format(self):
        b = _make_briefing()
        result = format_push_notification(b)
        assert "今日持仓" in result
        assert "今日建议观望" in result

    def test_has_action_emoji(self):
        """有操作建议 → ⚡"""
        b = _make_briefing(details=[
            {"fund_name": "A", "action": "减仓", "reason": "", "confidence": "高", "score": 80, "risk_note": ""}
        ])
        result = format_push_notification(b)
        assert "⚡" in result

    def test_has_risk_emoji(self):
        """有风险 → ⚠️"""
        b = _make_briefing(risk_alerts=["追高风险"])
        result = format_push_notification(b)
        assert "⚠️" in result

    def test_no_action_no_risk(self):
        """无操作无风险 → ✅"""
        b = _make_briefing()
        result = format_push_notification(b)
        assert "✅" in result

    def test_empty_briefing(self):
        """空简报不崩溃"""
        result = format_push_notification({})
        assert "今日持仓" in result


class TestBriefingCard:
    """简报卡片（第二层）"""

    def test_contains_fund_name(self):
        b = _make_briefing()
        result = format_briefing_card(b)
        assert "易方达蓝筹" in result

    def test_contains_action(self):
        b = _make_briefing()
        result = format_briefing_card(b)
        assert "观望" in result

    def test_contains_score(self):
        b = _make_briefing()
        result = format_briefing_card(b)
        assert "50分" in result

    def test_risk_alerts_shown(self):
        b = _make_briefing(risk_alerts=["追高风险", "均线空头"])
        result = format_briefing_card(b)
        assert "追高风险" in result

    def test_market_note_shown(self):
        b = _make_briefing()
        result = format_briefing_card(b)
        assert "市场情绪偏弱" in result


class TestFullReport:
    """完整报告（第三层）"""

    def test_contains_header(self):
        b = _make_briefing()
        result = format_full_report(b)
        assert "投资简报" in result

    def test_contains_detail(self):
        b = _make_briefing()
        result = format_full_report(b)
        assert "易方达蓝筹" in result
        assert "观望" in result

    def test_risk_note_shown(self):
        b = _make_briefing(details=[
            {"fund_name": "A", "action": "观望", "reason": "x", "confidence": "低", "score": 30, "risk_note": "波动大"}
        ])
        result = format_full_report(b)
        assert "波动大" in result


class TestFormatAll:
    """完整输出"""

    def test_contains_three_layers(self):
        b = _make_briefing()
        result = format_all(b)
        assert "推送通知" in result
        assert "简报卡片" in result
        assert "完整报告" in result


class TestActionEmoji:
    """emoji 映射"""

    def test_all_actions_have_emoji(self):
        for action in ["加仓", "减仓", "观望", "持有"]:
            assert action in ACTION_EMOJI
