"""Repository 模式 — 数据访问层（支持 user_id 隔离）

所有方法都接受 user_id 参数：
- user_id=0 表示未登录用户（兼容旧数据）
- user_id>0 表示已登录用户，数据完全隔离
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from src.database.engine import get_session
from src.database.models import Config, Holding, InvestPlan, Transaction

logger = logging.getLogger(__name__)


class PortfolioRepository:
    """持仓数据访问层"""

    def list_all(self, user_id: int = 0) -> list[dict]:
        """获取用户的所有持仓。"""
        with get_session() as s:
            holdings = s.query(Holding).filter_by(user_id=user_id).all()
            return [h.to_dict() for h in holdings]

    def get_by_code(self, fund_code: str, user_id: int = 0) -> Optional[dict]:
        """按基金代码查找。"""
        with get_session() as s:
            h = s.query(Holding).filter_by(user_id=user_id, fund_code=fund_code).first()
            return h.to_dict() if h else None

    def upsert(self, fund_code: str, user_id: int = 0, **kwargs) -> dict:
        """插入或更新持仓。"""
        with get_session() as s:
            h = s.query(Holding).filter_by(user_id=user_id, fund_code=fund_code).first()
            if h:
                for k, v in kwargs.items():
                    if hasattr(h, k) and k not in ("user_id", "fund_code"):
                        setattr(h, k, v)
                h.updated_at = datetime.utcnow()
            else:
                h = Holding(
                    user_id=user_id,
                    fund_code=fund_code,
                    **{k: v for k, v in kwargs.items() if hasattr(Holding, k) and k not in ("user_id", "fund_code")},
                )
                s.add(h)
            s.flush()
            return h.to_dict()

    def upsert_many(self, holdings: list[dict], user_id: int = 0) -> int:
        """批量 upsert 持仓。"""
        count = 0
        for data in holdings:
            fund_code = data.get("fund_code", "")
            if not fund_code:
                continue
            self.upsert(
                fund_code=fund_code,
                user_id=user_id,
                fund_name=data.get("fund_name", ""),
                cost=data.get("cost", 0),
                cost_nav=data.get("cost_nav", 0),
                shares=data.get("shares", 0),
                profit_ratio=data.get("profit_ratio", 0),
                profit_amount=data.get("profit_amount", 0),
                hold_days=data.get("hold_days", 0),
            )
            count += 1
        return count

    def delete(self, fund_code: str, user_id: int = 0) -> bool:
        """删除持仓。"""
        with get_session() as s:
            n = s.query(Holding).filter_by(user_id=user_id, fund_code=fund_code).delete()
            return n > 0

    def count(self, user_id: int = 0) -> int:
        """持仓数量。"""
        with get_session() as s:
            return s.query(Holding).filter_by(user_id=user_id).count()

    def delete_all(self, user_id: int = 0) -> int:
        """清空用户所有持仓。"""
        with get_session() as s:
            n = s.query(Holding).filter_by(user_id=user_id).delete()
            return n


class TransactionRepository:
    """交易记录数据访问层"""

    def add(self, user_id: int = 0, **kwargs) -> dict:
        with get_session() as s:
            t = Transaction(
                user_id=user_id,
                **{k: v for k, v in kwargs.items() if hasattr(Transaction, k) and k != "user_id"},
            )
            s.add(t)
            s.flush()
            return {"id": t.id, "fund_code": t.fund_code, "type": t.type}

    def list_by_fund(self, fund_code: str, user_id: int = 0) -> list[dict]:
        with get_session() as s:
            txns = (
                s.query(Transaction)
                .filter_by(user_id=user_id, fund_code=fund_code)
                .order_by(Transaction.created_at)
                .all()
            )
            return [
                {
                    "id": t.id, "fund_code": t.fund_code, "type": t.type,
                    "amount": t.amount, "nav": t.nav, "shares": t.shares,
                    "source": t.source, "created_at": str(t.created_at),
                }
                for t in txns
            ]


class ConfigRepository:
    """配置数据访问层"""

    def get(self, key: str) -> Optional[str]:
        with get_session() as s:
            c = s.query(Config).filter_by(key=key).first()
            return c.value if c else None

    def set(self, key: str, value: str, sensitive: bool = False) -> None:
        with get_session() as s:
            c = s.query(Config).filter_by(key=key).first()
            if c:
                c.value = value
                c.sensitive = 1 if sensitive else 0
                c.updated_at = datetime.utcnow()
            else:
                c = Config(key=key, value=value, sensitive=1 if sensitive else 0)
                s.add(c)

    def get_all(self) -> dict[str, str]:
        with get_session() as s:
            configs = s.query(Config).all()
            return {c.key: c.value for c in configs}

    def delete(self, key: str) -> bool:
        with get_session() as s:
            n = s.query(Config).filter_by(key=key).delete()
            return n > 0
