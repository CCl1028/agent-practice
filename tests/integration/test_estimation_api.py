"""估值 API 集成测试 — /api/estimation"""

from unittest.mock import patch


class TestEstimationAPI:
    def test_post_estimation_empty(self, client):
        """空持仓估值"""
        with patch("src.routes.estimation.load_portfolio", return_value=[]):
            r = client.post("/api/estimation", json={"holdings": []})
        assert r.status_code == 200
        data = r.json()
        assert "trading_hours" in data
        assert "funds" in data
        assert data["funds"] == []

    def test_post_estimation_with_holdings(self, client):
        """带持仓估值"""
        mock_holdings = [{"fund_code": "005827", "fund_name": "Test"}]
        with patch("src.routes.estimation.build_estimation_results", return_value=(False, [{"fund_code": "005827", "est_change": -0.5}])):
            r = client.post("/api/estimation", json={"holdings": mock_holdings})
        assert r.status_code == 200
        assert len(r.json()["funds"]) == 1

    def test_get_estimation(self, client, sample_portfolio):
        """GET 估值（读服务器持仓）"""
        with patch("src.routes.estimation.build_estimation_results", return_value=(False, [])):
            r = client.get("/api/estimation")
        assert r.status_code == 200


class TestNavHistoryAPI:
    def test_nav_history(self, client):
        """历史净值"""
        mock_navs = [{"date": "2026-04-20", "nav": 2.03}, {"date": "2026-04-21", "nav": 2.05}]
        with patch("src.tools.market_tools.get_fund_nav_history", return_value=mock_navs):
            r = client.get("/api/fund/005827/nav-history?start=2026-04-20&end=2026-04-21")
        assert r.status_code == 200
        data = r.json()
        assert data["fund_code"] == "005827"
        assert len(data["nav_list"]) == 2

    def test_nav_history_empty(self, client):
        """无数据返回空列表"""
        with patch("src.tools.market_tools.get_fund_nav_history", return_value=[]):
            r = client.get("/api/fund/999999/nav-history")
        assert r.status_code == 200
        assert r.json()["nav_list"] == []
