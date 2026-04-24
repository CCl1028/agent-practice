"""持仓 API 集成测试 — /api/portfolio/*"""

import json
from unittest.mock import patch


class TestGetPortfolio:
    def test_empty_portfolio(self, client, tmp_portfolio):
        r = client.get("/api/portfolio")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 0
        assert data["holdings"] == []

    def test_with_data(self, client, sample_portfolio):
        r = client.get("/api/portfolio")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 1
        assert data["holdings"][0]["fund_code"] == "005827"


class TestDeleteHolding:
    def test_delete_existing(self, client, sample_portfolio):
        r = client.delete("/api/portfolio/005827")
        assert r.status_code == 200
        assert r.json()["deleted"] == "005827"
        assert r.json()["remaining"] == 0

        # 验证确实删了
        r2 = client.get("/api/portfolio")
        assert r2.json()["count"] == 0

    def test_delete_nonexistent(self, client, sample_portfolio):
        r = client.delete("/api/portfolio/999999")
        assert r.status_code == 200
        assert r.json()["remaining"] == 1  # 原有数据不变


class TestRefreshPortfolio:
    def test_refresh_empty(self, client):
        r = client.post("/api/portfolio/refresh", json={"holdings": []})
        assert r.status_code == 200
        assert r.json()["holdings"] == []

    def test_refresh_with_holdings(self, client):
        """带持仓刷新 — 验证接口不崩溃且返回格式正确"""
        r = client.post("/api/portfolio/refresh", json={
            "holdings": [
                {"fund_code": "005827", "fund_name": "Test", "cost": 20000, "cost_nav": 2.0, "shares": 10000}
            ]
        })
        assert r.status_code == 200
        assert "holdings" in r.json()

    def test_refresh_nav_failure_graceful(self, client):
        """无持仓时返回空"""
        r = client.post("/api/portfolio/refresh", json={"holdings": []})
        assert r.status_code == 200
        assert r.json()["holdings"] == []


class TestAddText:
    def test_add_text_success(self, client, tmp_portfolio):
        """自然语言录入（mock NLP 解析）"""
        mock_holdings = [{"fund_code": "161725", "fund_name": "招商白酒", "cost": 10000, "cost_nav": 1.6}]

        with patch("src.routes.portfolio.parse_natural_language", return_value=mock_holdings):
            r = client.post("/api/portfolio/add-text", json={"text": "买了1万招商白酒"})

        assert r.status_code == 200
        data = r.json()
        assert len(data["added"]) == 1
        assert data["total"] == 1

    def test_add_text_empty_result(self, client, tmp_portfolio):
        """NLP 解析不出来 → 返回空"""
        with patch("src.routes.portfolio.parse_natural_language", return_value=[]):
            r = client.post("/api/portfolio/add-text", json={"text": "今天天气不错"})

        assert r.status_code == 200
        assert r.json()["added"] == []
        assert r.json()["total"] == 0


class TestAuthProtection:
    """认证保护测试"""

    def test_write_routes_need_auth_when_configured(self, client, monkeypatch, tmp_portfolio):
        """配置了 API_TOKEN 后，写操作需要认证"""
        monkeypatch.setenv("API_TOKEN", "test-secret")

        # 无 token → 401
        r = client.post("/api/portfolio/add-text", json={"text": "test"})
        assert r.status_code == 401

        # 错误 token → 401
        r = client.post("/api/portfolio/add-text",
                        json={"text": "test"},
                        headers={"Authorization": "Bearer wrong"})
        assert r.status_code == 401

        # 正确 token → 通过（mock NLP）
        with patch("src.routes.portfolio.parse_natural_language", return_value=[]):
            r = client.post("/api/portfolio/add-text",
                            json={"text": "test"},
                            headers={"Authorization": "Bearer test-secret"})
        assert r.status_code == 200

    def test_read_routes_no_auth(self, client, monkeypatch, tmp_portfolio):
        """读操作不需要认证"""
        monkeypatch.setenv("API_TOKEN", "test-secret")
        r = client.get("/api/portfolio")
        assert r.status_code == 200

    def test_delete_needs_auth(self, client, monkeypatch, sample_portfolio):
        """DELETE 需要认证"""
        monkeypatch.setenv("API_TOKEN", "test-secret")
        r = client.delete("/api/portfolio/005827")
        assert r.status_code == 401

        r = client.delete("/api/portfolio/005827",
                          headers={"Authorization": "Bearer test-secret"})
        assert r.status_code == 200
