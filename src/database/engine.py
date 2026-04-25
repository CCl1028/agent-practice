"""数据库引擎 — SQLite 连接 + 表初始化

用法：
    from src.database.engine import get_session, init_db

    # 启动时调用一次
    init_db()

    # 在 Repository 中使用
    with get_session() as session:
        session.query(Holding).all()
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Base

logger = logging.getLogger(__name__)

# 数据库文件路径
DB_DIR = Path("data")
DB_PATH = DB_DIR / "fundpal.db"

# 延迟初始化
_engine = None
_SessionFactory = None


def _get_engine():
    global _engine
    if _engine is None:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{DB_PATH}",
            echo=False,
            connect_args={"check_same_thread": False},  # SQLite 多线程支持
        )
    return _engine


def _get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=_get_engine(), expire_on_commit=False)
    return _SessionFactory


def init_db() -> None:
    """初始化数据库 — 创建所有表（如果不存在）。"""
    engine = _get_engine()
    Base.metadata.create_all(engine)
    logger.info("[数据库] SQLite 初始化完成: %s", DB_PATH)


@contextmanager
def get_session():
    """获取数据库 Session（上下文管理器，自动 commit/rollback）。"""
    factory = _get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
