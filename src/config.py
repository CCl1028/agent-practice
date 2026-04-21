"""全局配置 — 函数式获取（支持热更新）

Tech Phase 1 重构:
- T-001: 改为函数式获取，每次调用读 os.getenv()，支持运行时热更新
- T-002: 移除 load_dotenv()，统一由 server.py 启动时调用一次
- T-003: 新增配置验证函数，启动时检查必要配置
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


# ============================================
# 函数式配置获取（支持热更新）
# ============================================


def get_openai_api_key() -> str:
    """获取 OpenAI API Key（每次调用读最新环境变量）。"""
    return os.getenv("OPENAI_API_KEY", "")


def get_openai_base_url() -> str:
    """获取 OpenAI Base URL。"""
    return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


def get_text_model() -> str:
    """获取文本模型名称。"""
    return os.getenv("TEXT_MODEL", "deepseek-chat")


def get_vision_model() -> str:
    """获取视觉模型名称。"""
    return os.getenv("VISION_MODEL", "Qwen/Qwen2.5-VL-72B-Instruct")


def get_vision_api_key() -> str:
    """获取视觉 API Key（优先专用 Key，否则复用 OpenAI Key）。"""
    return os.getenv("VISION_API_KEY") or get_openai_api_key()


def get_vision_base_url() -> str:
    """获取视觉 API Base URL。"""
    return os.getenv("VISION_BASE_URL", "https://api.siliconflow.cn/v1")


def get_serverchan_key() -> str:
    """获取 Server酱 推送 Key。"""
    return os.getenv("SERVERCHAN_KEY", "")


def get_wecom_webhook_url() -> str:
    """获取企业微信 Webhook URL。"""
    return os.getenv("WECOM_WEBHOOK_URL", "")


def get_bark_url() -> str:
    """获取 Bark 推送 URL。"""
    return os.getenv("BARK_URL", "")


def get_tavily_api_key() -> str:
    """获取 Tavily 搜索 API Key。"""
    return os.getenv("TAVILY_API_KEY", "")


def get_bocha_api_key() -> str:
    """获取博查搜索 API Key。"""
    return os.getenv("BOCHA_API_KEY", "")


def get_brave_api_key() -> str:
    """获取 Brave 搜索 API Key。"""
    return os.getenv("BRAVE_API_KEY", "")


def get_serpapi_api_key() -> str:
    """获取 SerpAPI Key。"""
    return os.getenv("SERPAPI_API_KEY", "")


# ============================================
# 兼容层 — 保持旧代码可运行（逐步迁移后删除）
# ============================================

# 以下属性通过模块级 __getattr__ 动态代理到函数式获取
# 这样 `from src.config import OPENAI_API_KEY` 仍然可用，
# 但每次访问都会读取最新环境变量

_ATTR_MAP = {
    "OPENAI_API_KEY": get_openai_api_key,
    "OPENAI_BASE_URL": get_openai_base_url,
    "TEXT_MODEL": get_text_model,
    "VISION_MODEL": get_vision_model,
    "VISION_API_KEY": get_vision_api_key,
    "VISION_BASE_URL": get_vision_base_url,
    "SERVERCHAN_KEY": get_serverchan_key,
    "WECOM_WEBHOOK_URL": get_wecom_webhook_url,
    "BARK_URL": get_bark_url,
    "TAVILY_API_KEY": get_tavily_api_key,
    "BOCHA_API_KEY": get_bocha_api_key,
    "BRAVE_API_KEY": get_brave_api_key,
    "SERPAPI_API_KEY": get_serpapi_api_key,
}


def __getattr__(name: str):
    """模块级 __getattr__：拦截旧式常量访问，动态读取环境变量。"""
    if name in _ATTR_MAP:
        return _ATTR_MAP[name]()
    raise AttributeError(f"module 'src.config' has no attribute {name!r}")


# ============================================
# 配置验证（启动时调用）
# ============================================


def validate_config() -> list[str]:
    """验证配置完整性，返回警告信息列表。

    不会阻止启动，但会在日志中输出警告。
    """
    warnings: list[str] = []

    # 检查 OpenAI 配置
    api_key = get_openai_api_key()
    base_url = get_openai_base_url()

    if not api_key:
        warnings.append("OPENAI_API_KEY 未配置 — LLM 功能将降级为规则引擎模式")

    if base_url and not base_url.startswith(("http://", "https://")):
        warnings.append(f"OPENAI_BASE_URL 格式无效: {base_url!r}（应以 http:// 或 https:// 开头）")

    # 检查推送配置
    has_push = any(
        [
            get_serverchan_key(),
            get_wecom_webhook_url(),
            get_bark_url(),
        ]
    )
    if not has_push:
        warnings.append("未配置任何推送渠道（SERVERCHAN_KEY / WECOM_WEBHOOK_URL / BARK_URL）— 推送功能不可用")

    # 检查搜索配置
    has_search = any(
        [
            get_tavily_api_key(),
            get_bocha_api_key(),
            get_brave_api_key(),
            get_serpapi_api_key(),
        ]
    )
    if not has_search:
        warnings.append("未配置搜索引擎 API Key — 新闻搜索功能将不可用")

    # 输出所有警告
    for w in warnings:
        logger.warning("[配置检查] %s", w)

    if not warnings:
        logger.info("[配置检查] 所有配置项校验通过")

    return warnings
