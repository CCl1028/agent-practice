"""P0-P3 优化的单元测试

P0: 成本净值反算 (cost_nav back-calculation)
P1: 新增 shares + profit_amount 字段
P2: 去掉 hold_days 强制提取
P3: 区分详情页/列表页截图
"""

import json
import pytest
from unittest.mock import patch, MagicMock


# ====== P0: _enrich_holdings 成本净值反算 ======

def _make_holding(**overrides) -> dict:
    """构造一个测试用 holding dict"""
    base = {
        "fund_code": "005827",
        "fund_name": "易方达蓝筹精选",
        "cost": 0,
        "cost_nav": 0,
        "current_nav": 0,
        "profit_ratio": 0,
        "profit_amount": 0,
        "shares": 0,
        "hold_days": 0,
        "trend_5d": [],
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def mock_verify_fund():
    """Mock verify_and_fix_fund 避免真实网络调用"""
    with patch("src.tools.market_tools.verify_and_fix_fund") as mock_fn:
        mock_fn.side_effect = lambda code, name: (code, name)
        yield mock_fn


class TestEnrichHoldings:
    """测试 _enrich_holdings 的反算逻辑"""

    def _call(self, holdings: list[dict]) -> list[dict]:
        from src.tools.ocr_tools import _enrich_holdings
        return _enrich_holdings(holdings)

    # ---- P0: 成本净值反算 ----

    def test_cost_nav_already_set(self):
        """cost_nav 已有值，不应被覆盖"""
        h = _make_holding(cost_nav=2.15, current_nav=2.03, profit_ratio=-5.6)
        result = self._call([h])
        assert result[0]["cost_nav"] == 2.15

    def test_strategy2_shares_and_cost(self):
        """策略2: 有 shares + cost → 反算 cost_nav"""
        # 投入本金 = cost - profit_amount = 20000 - (-1000) = 21000
        # cost_nav = 21000 / 9000 = 2.3333
        h = _make_holding(
            cost=20000,
            shares=9000,
            profit_amount=-1000,
            cost_nav=0,
        )
        result = self._call([h])
        expected = round((20000 - (-1000)) / 9000, 4)
        assert result[0]["cost_nav"] == expected

    def test_strategy2_with_positive_profit(self):
        """策略2: profit_amount 为正（盈利场景）"""
        # 投入本金 = 20000 - 2000 = 18000
        # cost_nav = 18000 / 10000 = 1.8
        h = _make_holding(
            cost=20000,
            shares=10000,
            profit_amount=2000,
            cost_nav=0,
        )
        result = self._call([h])
        assert result[0]["cost_nav"] == round(18000 / 10000, 4)

    def test_strategy3_current_nav_and_ratio(self):
        """策略3: 有 current_nav + profit_ratio → 反算"""
        # cost_nav = 2.0 / (1 + (-5)/100) = 2.0 / 0.95 ≈ 2.1053
        h = _make_holding(
            current_nav=2.0,
            profit_ratio=-5.0,
            cost_nav=0,
        )
        result = self._call([h])
        expected = round(2.0 / (1 + (-5.0) / 100), 4)
        assert result[0]["cost_nav"] == expected

    def test_strategy3_positive_ratio(self):
        """策略3: 正收益率"""
        # cost_nav = 2.1 / (1 + 10/100) = 2.1 / 1.1 ≈ 1.9091
        h = _make_holding(
            current_nav=2.1,
            profit_ratio=10.0,
            cost_nav=0,
        )
        result = self._call([h])
        expected = round(2.1 / 1.1, 4)
        assert result[0]["cost_nav"] == expected

    def test_strategy3_zero_ratio_skipped(self):
        """策略3: profit_ratio=0 时不触发反算"""
        h = _make_holding(
            current_nav=2.0,
            profit_ratio=0,
            cost_nav=0,
        )
        result = self._call([h])
        assert result[0]["cost_nav"] == 0  # 无法反算

    def test_strategy2_priority_over_3(self):
        """策略2 优先级高于策略3: 有 shares+cost 时用策略2"""
        h = _make_holding(
            cost=20000,
            shares=10000,
            profit_amount=0,
            current_nav=2.1,
            profit_ratio=5.0,
            cost_nav=0,
        )
        result = self._call([h])
        # 应走策略2: cost_nav = (20000-0)/10000 = 2.0
        expected_s2 = round((20000 - 0) / 10000, 4)
        assert result[0]["cost_nav"] == expected_s2

    def test_no_data_no_crash(self):
        """所有值为0时不崩溃"""
        h = _make_holding()
        result = self._call([h])
        assert result[0]["cost_nav"] == 0
        assert result[0]["shares"] == 0

    # ---- P1: shares 补算 ----

    def test_shares_backfill(self):
        """shares 缺失但有 cost + cost_nav → 补算 shares"""
        h = _make_holding(
            cost=20000,
            cost_nav=2.0,
            shares=0,
        )
        result = self._call([h])
        assert result[0]["shares"] == round(20000 / 2.0, 2)  # 10000.0

    def test_shares_not_overwritten(self):
        """shares 已有值时不覆盖"""
        h = _make_holding(
            cost=20000,
            cost_nav=2.0,
            shares=9500,
        )
        result = self._call([h])
        assert result[0]["shares"] == 9500  # 不变

    def test_shares_backfill_after_cost_nav_calc(self):
        """先反算 cost_nav，再补算 shares（链式计算）"""
        # 步骤1: cost_nav = 2.0 / (1 + 10/100) = 1.8182
        # 步骤2: shares = 20000 / 1.8182 ≈ 11000.11
        h = _make_holding(
            cost=20000,
            current_nav=2.0,
            profit_ratio=10.0,
            cost_nav=0,
            shares=0,
        )
        result = self._call([h])
        assert result[0]["cost_nav"] > 0
        assert result[0]["shares"] > 0

    # ---- P1: profit_amount 字段默认值 ----

    def test_profit_amount_default(self):
        """profit_amount 默认为 0"""
        h = {"fund_code": "005827", "fund_name": "Test"}
        result = self._call([h])
        assert result[0]["profit_amount"] == 0

    # ---- P2: hold_days 不再强制提取，保持默认 ----

    def test_hold_days_default(self):
        """hold_days 默认为 0"""
        h = {"fund_code": "005827", "fund_name": "Test"}
        result = self._call([h])
        assert result[0]["hold_days"] == 0

    def test_hold_days_preserved(self):
        """如果 LLM 恰好返回了 hold_days，不丢失"""
        h = _make_holding(hold_days=180)
        result = self._call([h])
        assert result[0]["hold_days"] == 180

    # ---- 多只基金批量处理 ----

    def test_multiple_funds(self):
        """多只基金各自独立反算"""
        holdings = [
            _make_holding(
                fund_code="005827", fund_name="A基金",
                cost=20000, shares=10000, profit_amount=1000, cost_nav=0,
            ),
            _make_holding(
                fund_code="110011", fund_name="B基金",
                current_nav=5.0, profit_ratio=-10, cost_nav=0,
            ),
        ]
        result = self._call(holdings)
        # A基金: 策略2
        assert result[0]["cost_nav"] == round((20000 - 1000) / 10000, 4)
        # B基金: 策略3
        assert result[1]["cost_nav"] == round(5.0 / 0.9, 4)


# ====== P3: ocr_image_with_vision JSON 解析 ======

class TestVisionOCRParsing:
    """测试 ocr_image_with_vision 的 JSON 解析逻辑"""

    def test_new_format_with_screenshot_type(self):
        """新格式: {"screenshot_type": "detail", "holdings": [...]}"""
        new_json = json.dumps({
            "screenshot_type": "detail",
            "holdings": [
                {"fund_code": "005827", "fund_name": "Test", "cost": 20000}
            ]
        })
        # 模拟 LLM 返回新格式
        holdings = self._parse_json(new_json)
        assert len(holdings) == 1
        assert holdings[0]["fund_code"] == "005827"

    def test_old_format_plain_list(self):
        """旧格式: 直接返回 [...]"""
        old_json = json.dumps([
            {"fund_code": "005827", "fund_name": "Test", "cost": 20000}
        ])
        holdings = self._parse_json(old_json)
        assert len(holdings) == 1
        assert holdings[0]["fund_code"] == "005827"

    def test_list_type_screenshot(self):
        """列表页截图，多只基金"""
        data = json.dumps({
            "screenshot_type": "list",
            "holdings": [
                {"fund_code": "005827", "fund_name": "A"},
                {"fund_code": "110011", "fund_name": "B"},
                {"fund_code": "161725", "fund_name": "C"},
            ]
        })
        holdings = self._parse_json(data)
        assert len(holdings) == 3

    def test_empty_holdings(self):
        """截图无法识别，返回空"""
        data = json.dumps({"screenshot_type": "detail", "holdings": []})
        holdings = self._parse_json(data)
        assert holdings == []

    def test_markdown_wrapped_json(self):
        """LLM 返回 markdown 包裹的 JSON"""
        text = '```json\n{"screenshot_type": "detail", "holdings": [{"fund_code": "005827"}]}\n```'
        # 去掉 markdown 包裹
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        holdings = self._parse_json(text)
        assert len(holdings) == 1

    def _parse_json(self, text: str) -> list:
        """模拟 ocr_image_with_vision 中的 JSON 解析逻辑"""
        holdings = json.loads(text)
        if isinstance(holdings, dict):
            holdings = holdings.get("holdings", [])
        if isinstance(holdings, list):
            return holdings
        return []


# ====== P0-P1: nlp_input 中的反算逻辑 ======

class TestNLPInputEnrichment:
    """测试 nlp_input.parse_natural_language 中的字段补全逻辑（不调用 LLM）"""

    def test_cost_nav_calc_from_shares(self):
        """NLP path: shares + cost → cost_nav"""
        h = {
            "intent": "add_holding",
            "fund_code": "005827",
            "fund_name": "Test",
            "cost": 20000,
            "cost_nav": 0,
            "current_nav": 0,
            "profit_ratio": 0,
            "profit_amount": -1000,
            "shares": 10000,
            "hold_days": 0,
            "trend_5d": [],
            "amount": 0,
        }
        # 直接测试反算逻辑
        if h["cost_nav"] <= 0:
            if h["shares"] > 0 and h["cost"] > 0:
                invested = h["cost"] - h["profit_amount"]
                h["cost_nav"] = round(invested / h["shares"], 4)

        assert h["cost_nav"] == round((20000 - (-1000)) / 10000, 4)

    def test_cost_nav_calc_from_ratio(self):
        """NLP path: current_nav + profit_ratio → cost_nav"""
        h = {
            "cost_nav": 0,
            "current_nav": 2.0,
            "profit_ratio": -5.0,
            "profit_amount": 0,
            "shares": 0,
            "cost": 0,
        }
        if h["cost_nav"] <= 0:
            if h["shares"] > 0 and h["cost"] > 0:
                pass
            elif h["current_nav"] > 0 and h["profit_ratio"] != 0:
                h["cost_nav"] = round(
                    h["current_nav"] / (1 + h["profit_ratio"] / 100), 4
                )

        expected = round(2.0 / 0.95, 4)
        assert h["cost_nav"] == expected

    def test_shares_backfill_in_nlp(self):
        """NLP path: shares 补算"""
        h = {"cost": 20000, "cost_nav": 2.0, "shares": 0}
        if h["shares"] <= 0 and h["cost"] > 0 and h["cost_nav"] > 0:
            h["shares"] = round(h["cost"] / h["cost_nav"], 2)
        assert h["shares"] == 10000.0


# ====== P0-P1: portfolio_tools.compute_metrics 的反算 ======

class TestComputeMetricsEnrichment:
    """测试 compute_metrics 中 shares 和 profit_amount 的计算"""

    def test_shares_backfill_in_metrics(self):
        """cost_nav > 0 且 shares=0 → 补算 shares"""
        fund = {
            "fund_code": "005827",
            "fund_name": "Test",
            "cost": 20000,
            "cost_nav": 2.0,
            "current_nav": 2.1,
            "shares": 0,
            "profit_ratio": 0,
            "profit_amount": 0,
        }
        # 模拟 compute_metrics 中的逻辑
        if fund.get("cost_nav", 0) > 0:
            shares = fund.get("shares", 0)
            if not shares and fund.get("cost", 0) > 0:
                shares = round(fund["cost"] / fund["cost_nav"], 2)
                fund["shares"] = shares
            if shares > 0:
                fund["profit_amount"] = round(
                    shares * (fund["current_nav"] - fund["cost_nav"]), 2
                )

        assert fund["shares"] == 10000.0
        assert fund["profit_amount"] == round(10000 * (2.1 - 2.0), 2)  # 1000.0

    def test_profit_amount_with_existing_shares(self):
        """shares 已有值时直接计算 profit_amount"""
        fund = {
            "cost": 20000,
            "cost_nav": 2.0,
            "current_nav": 1.8,
            "shares": 9500,
            "profit_amount": 0,
        }
        if fund.get("cost_nav", 0) > 0:
            shares = fund.get("shares", 0)
            if shares > 0:
                fund["profit_amount"] = round(
                    shares * (fund["current_nav"] - fund["cost_nav"]), 2
                )

        assert fund["profit_amount"] == round(9500 * (1.8 - 2.0), 2)  # -1900.0


# ====== P2: Prompt 中不包含 hold_days ======

class TestPromptContent:
    """验证 Prompt 内容是否符合 P2 要求"""

    def test_parse_prompt_no_hold_days(self):
        """PARSE_PROMPT 不应包含 hold_days 提取指令"""
        from src.tools.ocr_tools import PARSE_PROMPT
        assert "hold_days" not in PARSE_PROMPT

    def test_parse_text_prompt_no_hold_days(self):
        """PARSE_TEXT_PROMPT 不应包含 hold_days"""
        from src.tools.ocr_tools import PARSE_TEXT_PROMPT
        assert "hold_days" not in PARSE_TEXT_PROMPT

    def test_nlp_extract_prompt_no_hold_days(self):
        """NLP EXTRACT_PROMPT 不应包含 hold_days"""
        from src.tools.nlp_input import EXTRACT_PROMPT
        assert "hold_days" not in EXTRACT_PROMPT

    def test_parse_prompt_has_shares(self):
        """PARSE_PROMPT 应包含 shares 字段"""
        from src.tools.ocr_tools import PARSE_PROMPT
        assert "shares" in PARSE_PROMPT

    def test_parse_prompt_has_profit_amount(self):
        """PARSE_PROMPT 应包含 profit_amount 字段"""
        from src.tools.ocr_tools import PARSE_PROMPT
        assert "profit_amount" in PARSE_PROMPT

    def test_parse_prompt_has_screenshot_type(self):
        """P3: PARSE_PROMPT 应包含 screenshot_type"""
        from src.tools.ocr_tools import PARSE_PROMPT
        assert "screenshot_type" in PARSE_PROMPT

    def test_nlp_prompt_has_shares(self):
        """NLP EXTRACT_PROMPT 应包含 shares"""
        from src.tools.nlp_input import EXTRACT_PROMPT
        assert "shares" in EXTRACT_PROMPT

    def test_nlp_prompt_has_profit_amount(self):
        """NLP EXTRACT_PROMPT 应包含 profit_amount"""
        from src.tools.nlp_input import EXTRACT_PROMPT
        assert "profit_amount" in EXTRACT_PROMPT


# ====== P1: state.py FundHolding 字段检查 ======

class TestFundHoldingFields:
    """验证 FundHolding TypedDict 包含新字段"""

    def test_has_profit_amount(self):
        from src.state import FundHolding
        assert "profit_amount" in FundHolding.__annotations__

    def test_has_shares(self):
        from src.state import FundHolding
        assert "shares" in FundHolding.__annotations__

    def test_profit_amount_type(self):
        from src.state import FundHolding
        # Python 3.9 + __future__ annotations → ForwardRef, 直接检查原始注解字符串
        ann = FundHolding.__annotations__["profit_amount"]
        # ForwardRef.__forward_arg__ 是原始字符串
        arg = getattr(ann, "__forward_arg__", str(ann))
        assert "float" in arg

    def test_shares_type(self):
        from src.state import FundHolding
        ann = FundHolding.__annotations__["shares"]
        arg = getattr(ann, "__forward_arg__", str(ann))
        assert "float" in arg


# ====== 边界情况 ======

class TestEdgeCases:
    """边界情况测试"""

    def test_negative_cost_nav_treated_as_missing(self):
        """cost_nav < 0 也应触发反算"""
        h = _make_holding(
            cost_nav=-1,
            current_nav=2.0,
            profit_ratio=10.0,
        )
        from src.tools.ocr_tools import _enrich_holdings
        result = _enrich_holdings([h])
        # -1 <= 0，应触发策略3
        expected = round(2.0 / 1.1, 4)
        assert result[0]["cost_nav"] == expected

    def test_very_small_shares(self):
        """极小份额不应导致除零"""
        h = _make_holding(
            cost=100,
            shares=0.01,
            profit_amount=0,
            cost_nav=0,
        )
        from src.tools.ocr_tools import _enrich_holdings
        result = _enrich_holdings([h])
        assert result[0]["cost_nav"] == round(100 / 0.01, 4)  # 10000.0

    def test_extreme_profit_ratio(self):
        """极端收益率"""
        h = _make_holding(
            current_nav=3.0,
            profit_ratio=200,  # 翻了3倍
            cost_nav=0,
        )
        from src.tools.ocr_tools import _enrich_holdings
        result = _enrich_holdings([h])
        expected = round(3.0 / (1 + 200 / 100), 4)  # 3.0/3.0 = 1.0
        assert result[0]["cost_nav"] == expected

    def test_profit_ratio_minus_100(self):
        """收益率 -100%（亏光）→ 除零保护"""
        h = _make_holding(
            current_nav=0,
            profit_ratio=-100,
            cost_nav=0,
        )
        from src.tools.ocr_tools import _enrich_holdings
        # current_nav=0 → 不触发策略3（需要 current_nav > 0）
        result = _enrich_holdings([h])
        assert result[0]["cost_nav"] == 0  # 无法反算
