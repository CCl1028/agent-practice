"""Repository 模式 — 数据访问层

通过 Repository 抽象数据访问，未来切换 PostgreSQL 只需替换实现。
当前后端仍使用 portfolio_tools.load_portfolio/save_portfolio，
Repository 作为新接口逐步替换。
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

    def list_all(self) -> list[dict]:
        """获取所有持仓（返回 FundHolding 兼容 dict）。"""
        with get_session() as s:
            holdings = s.query(Holding).all()
            return [h.to_dict() for h in holdings]

    def get_by_code(self, fund_code: str) -> Optional[dict]:
        """按基金代码查找。"""
        with get_session() as s:
            h = s.query(Holding).filter_by(fund_code=fund_code).first()
            return h.to_dict() if h else None

    def upsert(self, fund_code: str, **kwargs) -> dict:
        """插入或更新持仓。"""
        with get_session() as s:
            h = s.query(Holding).filter_by(fund_code=fund_code).first()
            if h:
                for k, v in kwargs.items():
                    if hasattr(h, k):
                        setattr(h, k, v)
                h.updated_at = datetime.utcnow()
            else:
                h = Holding(fund_code=fund_code, **{
                    k: v for k, v in kwargs.items() if hasattr(Holding, k)
                })
                s.add(h)
            s.flush()
            return h.to_dict()

    def upsert_many(self, holdings: list[dict]) -> int:
        """批量 upsert 持仓。返回处理数量。"""
        count = 0
        for data in holdings:
            fund_code = data.get("fund_code", "")
            if not fund_code:
                continue
            self.upsert(
                fund_code=fund_code,
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

    def delete(self, fund_code: str) -> bool:
        """删除持仓。"""
        with get_session() as s:
            n = s.query(Holding).filter_by(fund_code=fund_code).delete()
            return n > 0

    def count(self) -> int:
        """持仓数量。"""
        with get_session() as s:
            return s.query(Holding).count()

    def delete_all(self) -> int:
        """清空所有持仓（测试用）。"""
        with get_session() as s:
            n = s.query(Holding).delete()
            return n


class TransactionRepository:
    """交易记录数据访问层"""

    def add(self, **kwargs) -> dict:
        with get_session() as s:
            t = Transaction(**{k: v for k, v in kwargs.items() if hasattr(Transaction, k)})
            s.add(t)
            s.flush()
            return {"id": t.id, "fund_code": t.fund_code, "type": t.type}

    def list_by_fund(self, fund_code: str) -> list[dict]:
        with get_session() as s:
            txns = s.query(Transaction).filter_by(fund_code=fund_code).order_by(Transaction.created_at).all()
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
