"""SQLAlchemy ORM 模型 — 用户、持仓、交易、定投、配置

用户系统 + 数据隔离：所有业务表通过 user_id 隔离。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    nickname = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class Holding(Base):
    """持仓表 — 按 user_id 隔离"""
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=0, index=True)
    fund_code = Column(String(10), nullable=False, index=True)
    fund_name = Column(String(100), default="")
    cost = Column(Float, default=0)
    cost_nav = Column(Float, default=0)
    shares = Column(Float, default=0)
    profit_ratio = Column(Float, default=0)
    profit_amount = Column(Float, default=0)
    hold_days = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "fund_code", name="uq_user_fund"),
    )

    def to_dict(self) -> dict:
        """转为 FundHolding 兼容的 dict。"""
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
    user_id = Column(Integer, nullable=False, default=0, index=True)
    fund_code = Column(String(10), nullable=False, index=True)
    type = Column(String(10))  # buy / sell
    amount = Column(Float, default=0)
    nav = Column(Float, default=0)
    shares = Column(Float, default=0)
    source = Column(String(20), default="manual")
    created_at = Column(DateTime, default=datetime.utcnow)


class InvestPlan(Base):
    """定投计划表"""
    __tablename__ = "invest_plans"

    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, nullable=False, default=0, index=True)
    fund_code = Column(String(10), nullable=False, index=True)
    amount = Column(Float, default=0)
    frequency = Column(String(20), default="monthly")
    day = Column(Integer, default=1)
    status = Column(String(20), default="active")
    last_executed = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Config(Base):
    """配置表"""
    __tablename__ = "configs"

    key = Column(String(100), primary_key=True)
    value = Column(String(500), default="")
    sensitive = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
