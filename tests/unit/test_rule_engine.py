"""规则引擎单元测试 — _rule_engine 全分支覆盖

核心资产：6 维决策引擎（盈亏×趋势×乖离率×均线×波动率×持有时间）
"""

import pytest
from src.agents.briefing_agent import _rule_engine


def _make_fund(**overrides) -> dict:
    """构造测试用 FundHolding"""
    base = {
        "fund_code": "005827",
        "fund_name": "易方达蓝筹精选",
        "cost": 20000,
        "cost_nav": 2.0,
        "current_nav": 2.1,
        "profit_ratio": 5.0,
        "profit_amount": 0,
        "shares": 10000,
        "hold_days": 30,
        "trend_5d": [0.1, -0.2, 0.3, -0.1, 0.2],
        "ma_status": "数据不足",
        "deviation_rate": 0,
        "volatility_5d": 0,
        "est_change": None,
    }
    base.update(overrides)
    return base


class TestHardRules:
    """硬规则：最高优先级，必须严格执行"""

    def test_chase_high_detection(self):
        """追高检测：乖离率 > 3% 且连涨 → 观望"""
        fund = _make_fund(
            deviation_rate=4.0,
            trend_5d=[1.0, 0.5, 0.8, 0.3, 0.6],  # sum > 1.0
        )
        action, reason, score, risk = _rule_engine(fund)
        assert action == "观望"
        assert "追高" in risk
        assert score < 40

    def test_chase_high_not_triggered_low_deviation(self):
        """乖离率 <= 3% 不触发追高"""
        fund = _make_fund(
            deviation_rate=2.5,
            trend_5d=[1.0, 0.5, 0.8, 0.3, 0.6],
        )
        action, _, _, risk = _rule_engine(fund)
        assert "追高" not in risk

    def test_chase_high_not_triggered_falling(self):
        """乖离率高但趋势下跌不触发追高"""
        fund = _make_fund(
            deviation_rate=5.0,
            trend_5d=[-1.0, -0.5, -0.3, 0.1, -0.2],  # sum < -1.0
        )
        action, _, _, risk = _rule_engine(fund)
        assert "追高" not in risk

    def test_bear_no_add(self):
        """空头排列禁加仓：空头 + 浮亏 > 5%"""
        fund = _make_fund(
            ma_status="空头排列",
            profit_ratio=-8.0,
        )
        action, reason, score, risk = _rule_engine(fund)
        assert action == "观望"
        assert "空头" in risk
        assert score <= 30

    def test_bear_not_triggered_small_loss(self):
        """空头但浮亏 <= 5% 不触发"""
        fund = _make_fund(
            ma_status="空头排列",
            profit_ratio=-3.0,
        )
        action, _, _, risk = _rule_engine(fund)
        assert "空头" not in risk

    def test_stop_profit(self):
        """止盈提醒：浮盈 > 15% 且连涨 → 减仓"""
        fund = _make_fund(
            profit_ratio=18.0,
            trend_5d=[1.5, 0.8, 1.2, 0.5, 0.3],  # sum > 1.0
        )
        action, reason, score, risk = _rule_engine(fund)
        assert action == "减仓"
        assert "止盈" in reason
        assert score >= 75

    def test_stop_profit_not_triggered_falling(self):
        """浮盈 > 15% 但下跌中不触发止盈硬规则"""
        fund = _make_fund(
            profit_ratio=18.0,
            trend_5d=[-0.5, -0.3, -0.8, -0.1, -0.5],  # sum < -1.0
        )
        action, _, _, _ = _rule_engine(fund)
        # 走常规规则，浮盈>10% + falling → 持有
        assert action in ("持有", "减仓", "观望")


class TestRegularRules:
    """常规规则：盈亏 > 10% 的分支"""

    def test_profit_over_10_rising_high_deviation(self):
        """浮盈>10% + 涨 + 高乖离 → 减仓(75)"""
        fund = _make_fund(
            profit_ratio=12.0,
            trend_5d=[0.5, 0.3, 0.8, 0.2, 0.5],  # sum > 1.0
            deviation_rate=2.5,
        )
        action, _, score, _ = _rule_engine(fund)
        assert action == "减仓"
        assert score == 75

    def test_profit_over_10_rising_low_deviation(self):
        """浮盈>10% + 涨 + 低乖离 → 减仓(65)"""
        fund = _make_fund(
            profit_ratio=12.0,
            trend_5d=[0.5, 0.3, 0.8, 0.2, 0.5],
            deviation_rate=1.0,
        )
        action, _, score, _ = _rule_engine(fund)
        assert action == "减仓"
        assert score == 65

    def test_profit_over_10_not_rising(self):
        """浮盈>10% + 涨势放缓 → 持有"""
        fund = _make_fund(
            profit_ratio=12.0,
            trend_5d=[0.1, -0.2, 0.3, -0.1, 0.2],  # sum ~0.3
        )
        action, _, score, _ = _rule_engine(fund)
        assert action == "持有"
        assert score == 55

    def test_loss_over_10_still_falling(self):
        """浮亏>10% + 仍在跌 → 观望，不可补仓"""
        fund = _make_fund(
            profit_ratio=-15.0,
            trend_5d=[-0.5, -0.3, -0.8, -0.2, -0.5],  # sum < -1.0
        )
        action, _, _, risk = _rule_engine(fund)
        assert action == "观望"
        assert "补仓" in risk

    def test_loss_over_10_stabilized_bull(self):
        """浮亏>10% + 企稳 + 多头排列 → 可补仓"""
        fund = _make_fund(
            profit_ratio=-12.0,
            trend_5d=[0.1, -0.2, 0.1, -0.1, 0.2],  # sum ~0.1
            ma_status="多头排列",
        )
        action, _, _, _ = _rule_engine(fund)
        assert action == "加仓"

    def test_loss_over_10_stabilized_long_hold(self):
        """深度套牢>半年 + 企稳 → 小额补仓"""
        fund = _make_fund(
            profit_ratio=-15.0,
            trend_5d=[0.1, -0.2, 0.1, -0.1, 0.2],
            ma_status="多头排列",
            hold_days=200,
        )
        action, reason, score, _ = _rule_engine(fund)
        assert action == "加仓"
        assert "半年" in reason
        assert score == 55

    def test_loss_over_10_unclear_trend(self):
        """浮亏>10% + 趋势不明 + 非多头排列也非空头 → 加仓（企稳分支）"""
        fund = _make_fund(
            profit_ratio=-12.0,
            trend_5d=[0.1, -0.2, 0.1, -0.1, 0.2],
            ma_status="震荡",
        )
        action, _, _, _ = _rule_engine(fund)
        # 震荡 = not is_falling and not is_rising → 进入企稳分支 → 加仓
        assert action == "加仓"


class TestNeutralRules:
    """盈亏 <= 10% 的情况"""

    def test_rising_bull(self):
        """涨 + 多头排列 → 持有"""
        fund = _make_fund(
            profit_ratio=5.0,
            trend_5d=[0.5, 0.3, 0.4, 0.2, 0.3],  # sum > 1.0
            ma_status="多头排列",
        )
        action, _, score, _ = _rule_engine(fund)
        assert action == "持有"
        assert score == 60

    def test_rising_no_bull(self):
        """涨但均线未转好 → 观望"""
        fund = _make_fund(
            profit_ratio=5.0,
            trend_5d=[0.5, 0.3, 0.4, 0.2, 0.3],
            ma_status="震荡",
        )
        action, _, _, _ = _rule_engine(fund)
        assert action == "观望"

    def test_falling(self):
        """跌 → 观望"""
        fund = _make_fund(
            profit_ratio=3.0,
            trend_5d=[-0.5, -0.3, -0.4, -0.2, -0.3],  # sum < -1.0
        )
        action, _, _, _ = _rule_engine(fund)
        assert action == "观望"

    def test_est_change_negative(self):
        """盘中估值大跌 → 观望"""
        fund = _make_fund(
            profit_ratio=3.0,
            trend_5d=[0.0, 0.1, -0.1, 0.0, 0.1],
            est_change=-3.0,
        )
        action, reason, _, _ = _rule_engine(fund)
        assert action == "观望"
        assert "估值" in reason

    def test_est_change_positive_with_profit(self):
        """盘中估值大涨 + 浮盈>5% → 持有"""
        fund = _make_fund(
            profit_ratio=6.0,
            trend_5d=[0.0, 0.1, -0.1, 0.0, 0.1],
            est_change=3.0,
        )
        action, _, score, _ = _rule_engine(fund)
        assert action == "持有"
        assert score == 55

    def test_high_volatility_warning(self):
        """高波动率 → 风险提示"""
        fund = _make_fund(
            profit_ratio=3.0,
            trend_5d=[0.0, 0.1, -0.1, 0.0, 0.1],
            volatility_5d=5.0,
        )
        _, _, _, risk = _rule_engine(fund)
        assert "波动率" in risk

    def test_default_no_signal(self):
        """无信号 → 观望"""
        fund = _make_fund(
            profit_ratio=0.0,
            trend_5d=[0.0, 0.0, 0.0, 0.0, 0.0],
        )
        action, _, score, _ = _rule_engine(fund)
        assert action == "观望"
        assert score == 45


class TestEdgeCases:
    """边界情况"""

    def test_empty_trend(self):
        """空趋势数据不崩溃"""
        fund = _make_fund(trend_5d=[])
        action, _, _, _ = _rule_engine(fund)
        assert action in ("观望", "持有", "加仓", "减仓")

    def test_missing_fields(self):
        """缺失字段使用默认值"""
        fund = {"fund_code": "005827", "fund_name": "Test"}
        action, _, _, _ = _rule_engine(fund)
        assert action == "观望"

    def test_extreme_profit(self):
        """极端浮盈 200%"""
        fund = _make_fund(
            profit_ratio=200.0,
            trend_5d=[2.0, 1.5, 1.8, 1.2, 1.0],
        )
        action, _, _, _ = _rule_engine(fund)
        assert action == "减仓"

    def test_extreme_loss(self):
        """极端浮亏 -80%"""
        fund = _make_fund(
            profit_ratio=-80.0,
            trend_5d=[-2.0, -1.5, -1.8, -1.2, -1.0],
        )
        action, _, _, _ = _rule_engine(fund)
        assert action == "观望"

    def test_return_type(self):
        """返回值类型检查"""
        fund = _make_fund()
        result = _rule_engine(fund)
        assert isinstance(result, tuple)
        assert len(result) == 4
        action, reason, score, risk = result
        assert isinstance(action, str)
        assert isinstance(reason, str)
        assert isinstance(score, int)
        assert isinstance(risk, str)
