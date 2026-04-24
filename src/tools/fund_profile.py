"""基金画像 — 诊断数据 + 涨跌分析"""

from __future__ import annotations

import logging

from src.tools.fund_name import get_fund_code_by_name, get_fund_name_by_code
from src.tools.fund_nav import get_fund_nav
from src.tools.sector import get_sector_performance

logger = logging.getLogger(__name__)


def get_fund_profile(fund_code_or_name: str) -> dict | None:
    """获取基金基本信息用于诊断分析。"""
    fund_code = fund_code_or_name
    if not fund_code or len(fund_code) != 6:
        fund_code = get_fund_code_by_name(fund_code_or_name)

    if not fund_code or len(fund_code) != 6:
        logger.warning("[基金诊断] 无法解析基金代码: %s", fund_code_or_name)
        return None

    try:
        import akshare as ak
        df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="基本信息")
        if df is None or df.empty:
            raise ValueError("API returned empty data")

        row = df.iloc[0]
        fund_name = get_fund_name_by_code(fund_code) or row.get("基金名称", "")

        perf_1y = _parse_percentage(row.get("近1年", "0%"))
        perf_3y = _parse_percentage(row.get("近3年", "0%"))
        max_dd = _parse_percentage(row.get("最大回撤", "0%"))

        size_str = str(row.get("基金规模", "0")).strip()
        try:
            size_billion = float(size_str) if size_str and size_str != "0" else 50.0
        except ValueError:
            size_billion = 50.0

        volatility = _parse_percentage(row.get("波动率", "10%")) or 10.0
        sectors = _get_mock_sectors(fund_code)
        manager = row.get("基金经理", "未知")

        result = {
            "code": fund_code,
            "name": fund_name,
            "perf_1y": perf_1y or 0,
            "perf_3y": perf_3y or 0,
            "max_drawdown": max_dd or -15.0,
            "volatility": abs(volatility),
            "size_billion": size_billion,
            "sectors": sectors,
            "manager": manager,
            "manager_perf": "良好" if perf_1y and perf_1y > 10 else ("一般" if perf_1y and perf_1y > 0 else "较弱"),
        }

        logger.info("[基金诊断] 获取 %s(%s) 信息成功", fund_name, fund_code)
        return result

    except Exception as e:
        logger.warning("[基金诊断] 获取基金 %s 信息失败: %s，使用 mock", fund_code, e)
        return _mock_fund_profile(fund_code)


def get_fund_perf_analysis(fund_code_or_name: str) -> dict | None:
    """获取基金今日涨跌分析数据。"""
    fund_code = fund_code_or_name
    if not fund_code or len(fund_code) != 6:
        fund_code = get_fund_code_by_name(fund_code_or_name)

    if not fund_code or len(fund_code) != 6:
        logger.warning("[涨跌分析] 无法解析基金代码: %s", fund_code_or_name)
        return _mock_perf_analysis(fund_code_or_name)

    try:
        nav_data = get_fund_nav(fund_code)
        today_change = nav_data.get("trend_5d", [0])[-1] if nav_data.get("trend_5d") else 0

        sectors = _get_mock_sectors(fund_code)
        sector_perf = get_sector_performance()
        sector_change = sum(s["change"] for s in sector_perf if s["name"] in sectors) / len(sectors) if sectors else 0

        market_perf = get_sector_performance()
        market_change = market_perf[0]["change"] if market_perf else 0
        market_sentiment = _judge_sentiment(market_perf)

        result = {
            "code": fund_code,
            "name": get_fund_name_by_code(fund_code) or "未知基金",
            "today_change": today_change,
            "sectors": sectors,
            "sector_change": round(sector_change, 2),
            "market_change": market_change,
            "market_sentiment": market_sentiment,
        }

        logger.info("[涨跌分析] %s 今日涨跌 %+.2f%%", result["name"], today_change)
        return result

    except Exception as e:
        logger.warning("[涨跌分析] 获取基金 %s 今日数据失败: %s", fund_code, e)
        return _mock_perf_analysis(fund_code)


# ---- 辅助函数 ----

def _parse_percentage(s) -> float | None:
    if isinstance(s, (int, float)):
        return float(s)
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return float(s.replace("%", "").strip())
    except ValueError:
        return None


def _judge_sentiment(sectors: list[dict]) -> str:
    if not sectors:
        return "中性"
    avg = sum(s["change"] for s in sectors) / len(sectors)
    if avg > 0.5:
        return "偏乐观"
    elif avg < -0.5:
        return "偏谨慎"
    return "中性震荡"


def _get_mock_sectors(fund_code: str) -> list[str]:
    mock_sectors = {
        "005827": ["消费", "制造业", "医药"],
        "161725": ["电子", "计算机", "通讯"],
        "110011": ["银行", "地产", "汽车"],
    }
    return mock_sectors.get(fund_code, ["消费", "科技", "医药"])


def _mock_fund_profile(fund_code: str) -> dict:
    return {
        "code": fund_code,
        "name": get_fund_name_by_code(fund_code) or "示例基金",
        "perf_1y": 15.2, "perf_3y": 25.5, "max_drawdown": -12.3,
        "volatility": 9.5, "size_billion": 85.5,
        "sectors": ["消费", "制造业", "医药"],
        "manager": "示例经理", "manager_perf": "良好",
    }


def _mock_perf_analysis(fund_code: str) -> dict:
    return {
        "code": fund_code,
        "name": get_fund_name_by_code(fund_code) or "示例基金",
        "today_change": 1.23, "sectors": ["消费", "制造业"],
        "sector_change": 0.85, "market_change": 0.52, "market_sentiment": "偏乐观",
    }
