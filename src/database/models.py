"""SQLAlchemy ORM 模型 — 持仓、交易、定投、配置

Phase C: 从 JSON 文件迁移到 SQLite，通过 Repository 模式抽象，
未来切换 PostgreSQL 只需替换 Repository 实现。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


class Holding(Base):
    """持仓表"""
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(10), unique=True, nullable=False, index=True)
    fund_name = Column(String(100), default="")
    cost = Column(Float, default=0)
    cost_nav = Column(Float, default=0)
    shares = Column(Float, default=0)
    profit_ratio = Column(Float, default=0)
    profit_amount = Column(Float, default=0)
    hold_days = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        """转为 FundHolding 兼容的 dict（保持与旧 JSON 格式兼容）。"""
        return {
            "fund_code": self.fund_code,
            "fund_name": self.fund_name,
            "cost": self.cost,
            "cost_nav": self.cost_nav,
            "shares": self.shares,
            "profit_ratio": self.profit_ratio,
            "profit_amount": self.profit_amount,
            "hold_days": self.hold_days,
            "current_nav": 0,
            "trend_5d": [],
        }


class Transaction(Base):
    """交易记录表"""
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True)
    fund_code = Column(String(10), nullable=False, index=True)
    type = Column(String(10))  # buy / sell
    amount = Column(Float, default=0)
    nav = Column(Float, default=0)
    shares = Column(Float, default=0)
    source = Column(String(20), default="manual")  # manual / auto_invest
    created_at = Column(DateTime, default=datetime.utcnow)


class InvestPlan(Base):
    """定投计划表"""
    __tablename__ = "invest_plans"

    id = Column(String(36), primary_key=True)
    fund_code = Column(String(10), nullable=False, index=True)
    amount = Column(Float, default=0)
    frequency = Column(String(20), default="monthly")  # daily/weekly/biweekly/monthly
    day = Column(Integer, default=1)  # 周几或几号
    status = Column(String(20), default="active")  # active / paused
    last_executed = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Config(Base):
    """配置表 — 替代 .env 手工解析"""
    __tablename__ = "configs"

    key = Column(String(100), primary_key=True)
    value = Column(String(500), default="")
    sensitive = Column(Integer, default=0)  # 1=需要脱敏
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
