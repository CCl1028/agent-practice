"""持仓管理工具 — 数据存取、盈亏计算、技术指标

v2: 参考 daily_stock_analysis 增强：
- 使用多源数据获取器（自动故障切换 + 熔断）
- 计算均线（MA5/MA10/MA20）、均线排列状态
- 计算乖离率、波动率
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.state import FundHolding

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
    """为每只基金刷新最新净值、盘中估值、计算盈亏和技术指标。

    v2 新增计算：
    - MA5 / MA10 / MA20 均线
    - 均线排列状态（多头/空头/震荡）
    - 乖离率（现价偏离 MA5 的百分比）
    - 5日波动率
    """
    from src.tools.data_provider import get_fund_estimation_multi_source, get_fund_nav_multi_source

    updated = []
    for fund in portfolio:
        nav_data = get_fund_nav_multi_source(fund["fund_code"])
        fund = {**fund}  # shallow copy
        fund["current_nav"] = nav_data["current_nav"]
        fund["trend_5d"] = nav_data["trend_5d"]

        # 盈亏计算
        if fund.get("cost_nav", 0) > 0:
            fund["profit_ratio"] = round((fund["current_nav"] - fund["cost_nav"]) / fund["cost_nav"] * 100, 2)
            # 补算 shares 和 profit_amount
            shares = fund.get("shares", 0)
            if not shares and fund.get("cost", 0) > 0:
                shares = round(fund["cost"] / fund["cost_nav"], 2)
                fund["shares"] = shares
            if shares > 0:
                fund["profit_amount"] = round(shares * (fund["current_nav"] - fund["cost_nav"]), 2)

        # --- v2 新增：技术指标计算 ---
        nav_history = nav_data.get("nav_history", [])
        fund = _compute_technical_indicators(fund, nav_history)

        # 盘中估值（使用多源获取）
        est = get_fund_estimation_multi_source(fund["fund_code"])
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


def _compute_technical_indicators(fund: dict, nav_history: list[float]) -> dict:
    """计算技术指标：均线、乖离率、波动率。"""
    current_nav = fund.get("current_nav", 0)

    # 默认值
    fund.setdefault("ma5", 0)
    fund.setdefault("ma10", 0)
    fund.setdefault("ma20", 0)
    fund.setdefault("ma_status", "数据不足")
    fund.setdefault("deviation_rate", 0)
    fund.setdefault("volatility_5d", 0)

    # 需要至少 5 个历史数据才能算均线
    if len(nav_history) < 5:
        return fund

    # MA5
    ma5 = round(sum(nav_history[-5:]) / 5, 4)
    fund["ma5"] = ma5

    # MA10
    if len(nav_history) >= 10:
        fund["ma10"] = round(sum(nav_history[-10:]) / 10, 4)
    else:
        fund["ma10"] = ma5

    # MA20
    if len(nav_history) >= 20:
        fund["ma20"] = round(sum(nav_history[-20:]) / 20, 4)
    else:
        fund["ma20"] = fund["ma10"]

    # 均线排列状态
    if fund["ma5"] > fund["ma10"] > fund["ma20"]:
        fund["ma_status"] = "多头排列"
    elif fund["ma5"] < fund["ma10"] < fund["ma20"]:
        fund["ma_status"] = "空头排列"
    else:
        fund["ma_status"] = "震荡"

    # 乖离率 = (现价 - MA5) / MA5 * 100
    if ma5 > 0 and current_nav > 0:
        fund["deviation_rate"] = round((current_nav - ma5) / ma5 * 100, 2)

    # 5日波动率（近5日涨跌幅的极差）
    trend = fund.get("trend_5d", [])
    if len(trend) >= 2:
        fund["volatility_5d"] = round(max(trend) - min(trend), 2)

    return fund


def _mock_portfolio() -> list[FundHolding]:
    """Mock 持仓数据 — 开发测试用"""
    return [
        {
            "fund_code": "005827",
            "fund_name": "易方达蓝筹精选",
            "cost": 20000,
            "cost_nav": 2.15,
            "current_nav": 0,  # 待刷新
            "profit_ratio": 0,  # 待计算
            "profit_amount": 0,
            "shares": 9302.33,
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
            "profit_amount": 0,
            "shares": 9375.0,
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
            "profit_amount": 0,
            "shares": 2083.33,
            "hold_days": 365,
            "trend_5d": [],
        },
    ]
