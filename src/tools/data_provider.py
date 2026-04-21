"""多源基金数据获取器 — 策略模式 + 熔断机制

参考 daily_stock_analysis 的设计：
- 多数据源按优先级排序
- 熔断器：连续失败 N 次后自动冷却，避免反复请求不可用的数据源
- 自动故障切换：当前数据源失败时自动尝试下一个
- 所有数据源都失败时降级为 Mock 数据
"""

from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ============================================
# 熔断器（T-004: 添加线程安全锁）
# ============================================

class CircuitBreaker:
    """数据源熔断器 — 管理各数据源的熔断/冷却状态（线程安全）

    状态机：
    CLOSED（正常）→ 连续失败 N 次 → OPEN（熔断）→ 冷却时间到 → 试探请求
    """

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 300.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._states: dict[str, dict] = {}
        self._lock = threading.Lock()

    def is_available(self, source: str) -> bool:
        """检查数据源是否可用（线程安全）。"""
        with self._lock:
            state = self._states.get(source)
            if not state:
                return True
            if state["failures"] < self.failure_threshold:
                return True
            # 已熔断，检查冷却
            if time.time() - state["last_failure"] >= self.cooldown_seconds:
                state["failures"] = 0  # 冷却完成，重置
                logger.info("[熔断器] %s 冷却完成，恢复可用", source)
                return True
            remaining = self.cooldown_seconds - (time.time() - state["last_failure"])
            logger.debug("[熔断器] %s 熔断中，剩余冷却 %.0fs", source, remaining)
            return False

    def record_success(self, source: str) -> None:
        """记录成功，重置计数（线程安全）。"""
        with self._lock:
            self._states[source] = {"failures": 0, "last_failure": 0}

    def record_failure(self, source: str) -> None:
        """记录失败（线程安全）。"""
        with self._lock:
            state = self._states.setdefault(source, {"failures": 0, "last_failure": 0})
            state["failures"] += 1
            state["last_failure"] = time.time()
            if state["failures"] >= self.failure_threshold:
                logger.warning(
                    "[熔断器] %s 连续失败 %d 次，进入熔断（冷却 %.0fs）",
                    source, state["failures"], self.cooldown_seconds,
                )

    def get_status(self) -> dict[str, str]:
        """获取所有数据源状态（线程安全）。"""
        with self._lock:
            result = {}
            for source, state in self._states.items():
                if state["failures"] >= self.failure_threshold:
                    if time.time() - state["last_failure"] < self.cooldown_seconds:
                        result[source] = "open"  # 熔断中
                    else:
                        result[source] = "half_open"  # 冷却完成
                else:
                    result[source] = "closed"  # 正常
            return result


# 全局熔断器实例
_nav_breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=300)
_estimation_breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=300)


# ============================================
# 数据源抽象基类
# ============================================

class BaseFundFetcher(ABC):
    """基金数据源抽象基类。"""

    name: str = "base"
    priority: int = 99

    @abstractmethod
    def get_fund_nav(self, fund_code: str) -> dict | None:
        """获取基金净值。

        Returns:
            {"current_nav", "date", "trend_5d", "nav_history"} 或 None
        """
        pass

    @abstractmethod
    def get_fund_estimation(self, fund_code: str) -> dict | None:
        """获取基金估值。

        Returns:
            {"est_nav", "est_change", "est_time", "is_live"} 或 None
        """
        pass


# ============================================
# AKShare 数据源
# ============================================

class AKShareFetcher(BaseFundFetcher):
    """AKShare 数据源 — 东方财富。"""

    name = "akshare"
    priority = 0

    def get_fund_nav(self, fund_code: str) -> dict | None:
        import akshare as ak

        df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
        if df is None or df.empty:
            return None

        hist = df.tail(25)  # 取最近 25 天，足够算 20 日均线
        navs = hist["单位净值"].astype(float).tolist()

        trend_5d = []
        for i in range(max(1, len(navs) - 5), len(navs)):
            if navs[i - 1] > 0:
                change = round((navs[i] - navs[i - 1]) / navs[i - 1] * 100, 2)
                trend_5d.append(change)

        return {
            "current_nav": navs[-1] if navs else 0,
            "date": str(df.iloc[-1]["净值日期"]),
            "trend_5d": trend_5d[-5:],
            "nav_history": navs,
        }

    def get_fund_estimation(self, fund_code: str) -> dict | None:
        import akshare as ak
        from src.tools.market_tools import is_trading_hours

        if is_trading_hours():
            df = ak.fund_value_estimation_em()
            if df is not None and not df.empty:
                row = df[df["基金代码"] == fund_code]
                if not row.empty:
                    r = row.iloc[0]
                    return {
                        "est_nav": float(r.get("估算净值", 0) or 0),
                        "est_change": float(r.get("估算涨跌幅", 0) or 0),
                        "est_time": str(r.get("估算时间", "")),
                        "is_live": True,
                    }
        return None


# ============================================
# Efinance 数据源（备用）
# ============================================

class EfinanceFetcher(BaseFundFetcher):
    """Efinance 数据源 — 东方财富（第二渠道）。"""

    name = "efinance"
    priority = 1

    def get_fund_nav(self, fund_code: str) -> dict | None:
        try:
            import efinance as ef
        except ImportError:
            return None

        df = ef.fund.get_quote_history(fund_code)
        if df is None or df.empty:
            return None

        # efinance 返回的列名可能不同，做兼容处理
        nav_col = None
        for col_name in ["单位净值", "净值", "nav"]:
            if col_name in df.columns:
                nav_col = col_name
                break
        if not nav_col:
            return None

        navs = df[nav_col].astype(float).tail(25).tolist()
        trend_5d = []
        for i in range(max(1, len(navs) - 5), len(navs)):
            if navs[i - 1] > 0:
                change = round((navs[i] - navs[i - 1]) / navs[i - 1] * 100, 2)
                trend_5d.append(change)

        date_col = None
        for col_name in ["净值日期", "日期", "date"]:
            if col_name in df.columns:
                date_col = col_name
                break

        return {
            "current_nav": navs[-1] if navs else 0,
            "date": str(df.iloc[-1][date_col]) if date_col else "",
            "trend_5d": trend_5d[-5:],
            "nav_history": navs,
        }

    def get_fund_estimation(self, fund_code: str) -> dict | None:
        # efinance 暂不支持基金估值，返回 None
        return None


# ============================================
# 统一管理器
# ============================================

def _init_fetchers() -> list[BaseFundFetcher]:
    """初始化并按优先级排序的数据源列表。"""
    fetchers: list[BaseFundFetcher] = [AKShareFetcher()]

    # 尝试加载 efinance
    try:
        import efinance  # noqa: F401
        fetchers.append(EfinanceFetcher())
    except ImportError:
        logger.debug("[数据源] efinance 未安装，跳过")

    fetchers.sort(key=lambda f: f.priority)
    names = ", ".join(f"{f.name}(P{f.priority})" for f in fetchers)
    logger.info("[数据源] 已初始化 %d 个数据源: %s", len(fetchers), names)
    return fetchers


_fetchers: list[BaseFundFetcher] | None = None


def _get_fetchers() -> list[BaseFundFetcher]:
    """延迟初始化数据源列表。"""
    global _fetchers
    if _fetchers is None:
        _fetchers = _init_fetchers()
    return _fetchers


def get_fund_nav_multi_source(fund_code: str) -> dict:
    """多源获取基金净值 — 自动故障切换 + 熔断。

    Returns:
        {"current_nav", "date", "trend_5d", "nav_history"}
    """
    for fetcher in _get_fetchers():
        if not _nav_breaker.is_available(fetcher.name):
            continue
        try:
            result = fetcher.get_fund_nav(fund_code)
            if result and result.get("current_nav", 0) > 0:
                _nav_breaker.record_success(fetcher.name)
                logger.info("[%s] 获取 %s 净值成功", fetcher.name, fund_code)
                return result
        except Exception as e:
            logger.warning("[%s] 获取 %s 净值失败: %s", fetcher.name, fund_code, e)
            _nav_breaker.record_failure(fetcher.name)

    logger.error("[数据源] 所有数据源获取 %s 净值失败，使用 mock", fund_code)
    from src.tools.market_tools import _mock_fund_nav
    return _mock_fund_nav(fund_code)


def get_fund_estimation_multi_source(fund_code: str) -> dict | None:
    """多源获取基金估值 — 自动故障切换 + 熔断。

    Returns:
        {"est_nav", "est_change", "est_time", "is_live"} 或 None
    """
    for fetcher in _get_fetchers():
        if not _estimation_breaker.is_available(fetcher.name):
            continue
        try:
            result = fetcher.get_fund_estimation(fund_code)
            if result:
                _estimation_breaker.record_success(fetcher.name)
                return result
        except Exception as e:
            logger.warning("[%s] 获取 %s 估值失败: %s", fetcher.name, fund_code, e)
            _estimation_breaker.record_failure(fetcher.name)

    # 所有数据源都失败，回退到收盘净值计算
    from src.tools.market_tools import _get_last_close_change
    return _get_last_close_change(fund_code)


def get_breaker_status() -> dict:
    """获取熔断器状态（调试用）。"""
    return {
        "nav": _nav_breaker.get_status(),
        "estimation": _estimation_breaker.get_status(),
    }
