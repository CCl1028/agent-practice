"""测试 get_fund_nav_history 函数"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from src.tools.market_tools import get_fund_nav_history


def _mock_df():
    """构造模拟的净值 DataFrame"""
    return pd.DataFrame({
        "净值日期": ["2026-03-25", "2026-03-26", "2026-03-27", "2026-03-28", "2026-03-31", "2026-04-01", "2026-04-02"],
        "单位净值": [1.8200, 1.8310, 1.8250, 1.8400, 1.8350, 1.8500, 1.8520],
    })


@pytest.fixture(autouse=True)
def mock_akshare(monkeypatch):
    """Mock akshare.fund_open_fund_info_em 在所有测试中"""
    mock_ak = MagicMock()
    mock_ak.fund_open_fund_info_em.return_value = _mock_df()
    monkeypatch.setitem(__import__('sys').modules, 'akshare', mock_ak)
    return mock_ak


class TestGetFundNavHistory:
    """get_fund_nav_history 单元测试"""

    def test_basic_query(self, mock_akshare):
        """无日期过滤时返回全部"""
        result = get_fund_nav_history("005827")
        assert len(result) == 7
        assert result[0]["date"] == "2026-03-25"
        assert result[0]["nav"] == 1.82

    def test_date_range_filter(self, mock_akshare):
        """按日期范围过滤"""
        result = get_fund_nav_history("005827", start="2026-03-27", end="2026-04-01")
        dates = [r["date"] for r in result]
        assert "2026-03-25" not in dates
        assert "2026-03-27" in dates
        assert "2026-04-01" in dates
        assert "2026-04-02" not in dates

    def test_start_only(self, mock_akshare):
        """只指定 start"""
        result = get_fund_nav_history("005827", start="2026-04-01")
        assert len(result) == 2
        assert result[0]["date"] == "2026-04-01"

    def test_end_only(self, mock_akshare):
        """只指定 end"""
        result = get_fund_nav_history("005827", end="2026-03-26")
        assert len(result) == 2
        assert result[-1]["date"] == "2026-03-26"

    def test_akshare_failure_returns_empty(self, mock_akshare):
        """AKShare 抛异常时返回空列表"""
        mock_akshare.fund_open_fund_info_em.side_effect = Exception("network error")
        result = get_fund_nav_history("005827")
        assert result == []

    def test_empty_dataframe(self, mock_akshare):
        """AKShare 返回空 DataFrame"""
        mock_akshare.fund_open_fund_info_em.return_value = pd.DataFrame()
        result = get_fund_nav_history("005827")
        assert result == []

    def test_nav_values_are_float(self, mock_akshare):
        """返回的 nav 应为 float 类型"""
        result = get_fund_nav_history("005827")
        for item in result:
            assert isinstance(item["nav"], float)
            assert isinstance(item["date"], str)
