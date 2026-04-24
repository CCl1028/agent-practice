"""配置 API 集成测试 — /api/config"""

from pathlib import Path
from unittest.mock import patch


class TestGetConfigAPI:
    def test_get_config(self, client):
        """获取配置返回白名单字段"""
        # Mock ENV_PATH 指向一个临时文件
        with patch("src.routes.config.ENV_PATH", Path("/nonexistent/.env")):
            r = client.get("/api/config")
        assert r.status_code == 200
        data = r.json()
        assert "OPENAI_API_KEY" in data
        assert "BARK_URL" in data
        # 每个字段应有 value/has_value/sensitive
        for key, info in data.items():
            assert "has_value" in info
            assert "sensitive" in info

    def test_sensitive_fields_masked(self, client, tmp_path):
        """敏感字段脱敏"""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=sk-abcdef1234567890abcdef\n", encoding="utf-8")

        with patch("src.routes.config.ENV_PATH", env_file):
            r = client.get("/api/config")
        assert r.status_code == 200
        api_key_info = r.json()["OPENAI_API_KEY"]
        assert api_key_info["has_value"] is True
        assert api_key_info["sensitive"] is True
        # 应该被脱敏（不完整显示）
        assert "****" in api_key_info["value"]


class TestUpdateConfigAPI:
    def test_update_allowed_key(self, client, tmp_path):
        """更新白名单 key"""
        env_file = tmp_path / ".env"
        env_file.write_text("", encoding="utf-8")

        with patch("src.routes.config.ENV_PATH", env_file):
            r = client.post("/api/config", json={"key": "BARK_URL", "value": "https://test.bark"})
        assert r.status_code == 200
        assert r.json()["ok"] is True

        # 验证写入
        content = env_file.read_text()
        assert "BARK_URL=https://test.bark" in content

    def test_update_disallowed_key(self, client, tmp_path):
        """非白名单 key → 400"""
        env_file = tmp_path / ".env"
        env_file.write_text("", encoding="utf-8")

        with patch("src.routes.config.ENV_PATH", env_file):
            r = client.post("/api/config", json={"key": "DANGEROUS_KEY", "value": "hacked"})
        assert r.status_code == 400
        assert "不允许" in r.json()["error"]

    def test_update_config_needs_auth(self, client, monkeypatch):
        """配置更新需要认证"""
        monkeypatch.setenv("API_TOKEN", "secret")
        r = client.post("/api/config", json={"key": "BARK_URL", "value": "test"})
        assert r.status_code == 401

    def test_clear_config_value(self, client, tmp_path):
        """清空配置值"""
        env_file = tmp_path / ".env"
        env_file.write_text("BARK_URL=https://old\n", encoding="utf-8")

        with patch("src.routes.config.ENV_PATH", env_file):
            r = client.post("/api/config", json={"key": "BARK_URL", "value": ""})
        assert r.status_code == 200

        content = env_file.read_text()
        assert "BARK_URL" not in content
