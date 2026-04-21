"""FundPal 统一异常定义

T-022: 统一异常处理 — 定义业务异常基类 + 子类
所有业务异常继承 FundPalError，由 server.py 全局异常处理器统一转换为 JSON 响应。
"""

from __future__ import annotations


class FundPalError(Exception):
    """FundPal 业务异常基类。

    Attributes:
        message: 用户可见的错误描述
        code: 机器可读的错误码（如 VALIDATION_ERROR）
        status: HTTP 状态码
    """

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status: int = 500,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


class ValidationError(FundPalError):
    """请求参数校验失败（400）。"""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR", 400)


class NotFoundError(FundPalError):
    """资源未找到（404）。"""

    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, "NOT_FOUND", 404)


class BriefingTimeoutError(FundPalError):
    """简报/诊断/分析等 LLM 调用超时（504）。"""

    def __init__(self, message: str = "请求超时，请稍后重试"):
        super().__init__(message, "TIMEOUT", 504)


class DataSourceError(FundPalError):
    """外部数据源不可用（503）。"""

    def __init__(self, source: str):
        super().__init__(f"数据源 {source} 不可用", "DATA_SOURCE_ERROR", 503)


class ConfigError(FundPalError):
    """配置相关错误（400）。"""

    def __init__(self, message: str):
        super().__init__(message, "CONFIG_ERROR", 400)
