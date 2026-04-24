"""内存日志收集器 — 环形缓冲区，供前端查看"""

from __future__ import annotations

import collections
import logging
import traceback
from datetime import datetime

MAX_LOG_LINES = 500


class MemoryLogHandler(logging.Handler):
    """将日志存入内存环形缓冲区，供前端查看。"""

    def __init__(self, maxlen: int = MAX_LOG_LINES):
        super().__init__()
        self.buffer: collections.deque[dict] = collections.deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord):
        try:
            entry = {
                "ts": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "msg": self.format(record),
            }
            if record.exc_info and record.exc_info[0]:
                entry["msg"] += "\n" + "".join(traceback.format_exception(*record.exc_info))
            self.buffer.append(entry)
        except Exception:
            pass

    def get_logs(self, limit: int = 200, level: str | None = None) -> list[dict]:
        logs = list(self.buffer)
        if level:
            level_upper = level.upper()
            logs = [entry for entry in logs if entry["level"] == level_upper]
        return logs[-limit:]

    def clear(self):
        self.buffer.clear()


# 全局单例
memory_log_handler = MemoryLogHandler(maxlen=MAX_LOG_LINES)
memory_log_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s", datefmt="%H:%M:%S")
)


def setup_logging():
    """配置全局日志（仅调用一次）。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger().addHandler(memory_log_handler)
