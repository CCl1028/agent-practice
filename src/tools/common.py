"""公共工具函数 — 跨模块共享"""

from __future__ import annotations

from datetime import datetime


def is_trading_hours() -> bool:
    """判断当前是否在交易时段（工作日 9:30-15:00）。"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.hour * 100 + now.minute
    return 930 <= t <= 1500
