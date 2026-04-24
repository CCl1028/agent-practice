"""配置模块单元测试 — 函数式获取 + 验证"""

import os
import pytest


class TestConfigGetters:
    """函数式配置获取"""

    def test_get_openai_api_key_default(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from src.config import get_openai_api_key
        assert get_openai_api_key() == ""

    def test_get_openai_api_key_set(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from src.config import get_openai_api_key
        assert get_openai_api_key() == "sk-test"

    def test_get_openai_base_url_default(self, monkeypatch):
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        from src.config import get_openai_base_url
        assert get_openai_base_url() == "https://api.openai.com/v1"

    def test_get_api_token(self, monkeypatch):
        monkeypatch.setenv("API_TOKEN", "my-secret")
        from src.config import get_api_token
        assert get_api_token() == "my-secret"

    def test_vision_api_key_fallback(self, monkeypatch):
        """VISION_API_KEY 未设置时回退到 OPENAI_API_KEY"""
        monkeypatch.delenv("VISION_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-main")
        from src.config import get_vision_api_key
        assert get_vision_api_key() == "sk-main"


class TestConfigCompat:
    """兼容层：模块级属性访问"""

    def test_attr_access(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-compat")
        import src.config as cfg
        assert cfg.OPENAI_API_KEY == "sk-compat"

    def test_attr_not_exist(self):
        import src.config as cfg
        with pytest.raises(AttributeError):
            _ = cfg.NONEXISTENT_KEY


class TestValidateConfig:
    """配置验证"""

    def test_all_ok(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("BARK_URL", "https://api.day.app/xxx")
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-xxx")
        from src.config import validate_config
        warnings = validate_config()
        assert warnings == []

    def test_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("BARK_URL", "https://x")
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-x")
        from src.config import validate_config
        warnings = validate_config()
        assert any("OPENAI_API_KEY" in w for w in warnings)

    def test_missing_push(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("BARK_URL", raising=False)
        monkeypatch.delenv("SERVERCHAN_KEY", raising=False)
        monkeypatch.delenv("WECOM_WEBHOOK_URL", raising=False)
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-x")
        from src.config import validate_config
        warnings = validate_config()
        assert any("推送" in w for w in warnings)

    def test_invalid_base_url(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("OPENAI_BASE_URL", "ftp://invalid")
        monkeypatch.setenv("BARK_URL", "https://x")
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-x")
        from src.config import validate_config
        warnings = validate_config()
        assert any("格式无效" in w for w in warnings)
