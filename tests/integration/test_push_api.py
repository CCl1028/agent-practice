"""推送 API 集成测试 — /api/push/*"""

from unittest.mock import patch


class TestPushStatusAPI:
    def test_get_push_status(self, client):
        r = client.get("/api/push/status")
        assert r.status_code == 200

    def test_post_push_status(self, client):
        r = client.post("/api/push/status", json={"config": {}})
        assert r.status_code == 200

    def test_post_push_status_with_config(self, client):
        r = client.post("/api/push/status", json={"config": {"BARK_URL": "https://test"}})
        assert r.status_code == 200


class TestPushTestAPI:
    def test_push_test(self, client):
        """测试推送（mock push_briefing）"""
        with patch("src.routes.push.push_briefing", return_value={"bark": True}):
            r = client.post("/api/push/test", json={"config": {"BARK_URL": "https://test"}})
        assert r.status_code == 200
        assert "push_results" in r.json()

    def test_push_test_needs_auth(self, client, monkeypatch):
        """推送测试需要认证"""
        monkeypatch.setenv("API_TOKEN", "secret")
        r = client.post("/api/push/test", json={})
        assert r.status_code == 401
