"""持仓管理工具 — 数据存取、盈亏计算"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from src.state import FundHolding
from src.tools.market_tools import get_fund_estimation, get_fund_nav

logger = logging.getLogger(__name__)

DB_PATH = Path("data/portfolio.json")


def load_portfolio() -> list[FundHolding]:
    """从本地存储加载持仓，无数据时返回 mock。"""
    if DB_PATH.exists():
        try:
            data = json.loads(DB_PATH.read_text(encoding="utf-8"))
            return data
        except Exception as e:
            logger.warning("读取持仓失败: %s，使用 mock", e)

    return _mock_portfolio()


def save_portfolio(portfolio: list[FundHolding]) -> None:
    """保存持仓到本地文件。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(json.dumps(portfolio, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_metrics(portfolio: list[FundHolding]) -> list[FundHolding]:
    """为每只基金刷新最新净值、盘中估值、计算盈亏。"""
    updated = []
    for fund in portfolio:
        nav_data = get_fund_nav(fund["fund_code"])
        fund = {**fund}  # shallow copy
        fund["current_nav"] = nav_data["current_nav"]
        fund["trend_5d"] = nav_data["trend_5d"]
        if fund["cost_nav"] > 0:
            fund["profit_ratio"] = round(
                (fund["current_nav"] - fund["cost_nav"]) / fund["cost_nav"] * 100, 2
            )

        # 盘中估值
        est = get_fund_estimation(fund["fund_code"])
        if est:
            fund["est_change"] = est["est_change"]
            fund["est_nav"] = est["est_nav"]
            fund["est_time"] = est["est_time"]
        else:
            fund["est_change"] = None
            fund["est_nav"] = None
            fund["est_time"] = None

        updated.append(fund)
    return updated


def _mock_portfolio() -> list[FundHolding]:
    """Mock 持仓数据 — 开发测试用"""
    return [
        {
            "fund_code": "005827",
            "fund_name": "易方达蓝筹精选",
            "cost": 20000,
            "cost_nav": 2.15,
            "current_nav": 0,   # 待刷新
            "profit_ratio": 0,  # 待计算
            "hold_days": 280,
            "trend_5d": [],
        },
        {
            "fund_code": "161725",
            "fund_name": "招商中证白酒",
            "cost": 15000,
            "cost_nav": 1.60,
            "current_nav": 0,
            "profit_ratio": 0,
            "hold_days": 180,
            "trend_5d": [],
        },
        {
            "fund_code": "110011",
            "fund_name": "易方达中小盘",
            "cost": 10000,
            "cost_nav": 4.80,
            "current_nav": 0,
            "profit_ratio": 0,
            "hold_days": 365,
            "trend_5d": [],
        },
    ]
