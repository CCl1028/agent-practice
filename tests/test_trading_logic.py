"""测试交易记录累积持仓计算 和 定投周期计算的纯逻辑

这些逻辑在前端 JS 中，这里用 Python 等价实现来验证算法正确性。
"""

import pytest
from datetime import datetime, timedelta


# ====== 累积持仓计算（等价于前端 recalcHolding） ======

def recalc_holding(transactions: list[dict]) -> dict:
    """从交易流水重新计算累积持仓。
    
    transactions 按时间正序排列。
    返回 {total_shares, total_cost, avg_nav}
    """
    total_shares = 0.0
    total_cost = 0.0

    for t in transactions:
        if t["type"] == "buy":
            total_shares += t.get("shares", 0)
            total_cost += t.get("amount", 0)
        elif t["type"] == "sell":
            sell_shares = t.get("shares", 0)
            if total_shares > 0:
                cost_per_share = total_cost / total_shares
                total_cost -= cost_per_share * sell_shares
                total_shares -= sell_shares

    total_shares = max(0, total_shares)
    total_cost = max(0, total_cost)
    avg_nav = total_cost / total_shares if total_shares > 0 else 0

    return {
        "total_shares": round(total_shares, 2),
        "total_cost": round(total_cost, 2),
        "avg_nav": round(avg_nav, 4),
    }


class TestRecalcHolding:
    """累积持仓计算测试"""

    def test_single_buy(self):
        """单笔买入"""
        txs = [{"type": "buy", "amount": 5000, "shares": 2700, "nav": 1.8519}]
        r = recalc_holding(txs)
        assert r["total_shares"] == 2700
        assert r["total_cost"] == 5000
        assert r["avg_nav"] == round(5000 / 2700, 4)

    def test_multiple_buys(self):
        """多笔买入，平均成本"""
        txs = [
            {"type": "buy", "amount": 5000, "shares": 2500, "nav": 2.0},
            {"type": "buy", "amount": 3000, "shares": 2000, "nav": 1.5},
        ]
        r = recalc_holding(txs)
        assert r["total_shares"] == 4500
        assert r["total_cost"] == 8000
        assert r["avg_nav"] == round(8000 / 4500, 4)

    def test_buy_then_sell(self):
        """买入后部分卖出"""
        txs = [
            {"type": "buy", "amount": 10000, "shares": 5000, "nav": 2.0},
            {"type": "sell", "amount": 4000, "shares": 2000, "nav": 2.0},
        ]
        r = recalc_holding(txs)
        assert r["total_shares"] == 3000
        # 卖出 2000 份，成本 = (10000/5000) * 2000 = 4000
        assert r["total_cost"] == 6000
        assert r["avg_nav"] == round(6000 / 3000, 4)  # = 2.0

    def test_sell_all(self):
        """全部卖出"""
        txs = [
            {"type": "buy", "amount": 5000, "shares": 2500, "nav": 2.0},
            {"type": "sell", "amount": 5000, "shares": 2500, "nav": 2.0},
        ]
        r = recalc_holding(txs)
        assert r["total_shares"] == 0
        assert r["total_cost"] == 0
        assert r["avg_nav"] == 0

    def test_multiple_buys_and_sells(self):
        """多笔买卖交替"""
        txs = [
            {"type": "buy", "amount": 10000, "shares": 5000, "nav": 2.0},  # 5000份, 成本10000
            {"type": "sell", "amount": 2000, "shares": 1000, "nav": 2.0},  # 卖1000份
            {"type": "buy", "amount": 3000, "shares": 2000, "nav": 1.5},   # 再买2000份
            {"type": "sell", "amount": 3000, "shares": 2000, "nav": 1.5},  # 再卖2000份
        ]
        r = recalc_holding(txs)
        # 第1步: 5000份, 成本10000
        # 第2步: 4000份, 成本 10000-2000=8000
        # 第3步: 6000份, 成本 8000+3000=11000
        # 第4步: 4000份, 成本 11000 - (11000/6000)*2000 = 11000 - 3666.67 = 7333.33
        assert r["total_shares"] == 4000
        assert r["total_cost"] == round(11000 - (11000 / 6000) * 2000, 2)

    def test_empty_transactions(self):
        """无交易记录"""
        r = recalc_holding([])
        assert r["total_shares"] == 0
        assert r["total_cost"] == 0
        assert r["avg_nav"] == 0

    def test_oversell_protection(self):
        """卖出超过持有份额时不应为负"""
        txs = [
            {"type": "buy", "amount": 1000, "shares": 500, "nav": 2.0},
            {"type": "sell", "amount": 2000, "shares": 1000, "nav": 2.0},
        ]
        r = recalc_holding(txs)
        assert r["total_shares"] >= 0
        assert r["total_cost"] >= 0

    def test_sell_exactly_all_shares(self):
        """精确卖出全部份额，结果归零"""
        txs = [
            {"type": "buy", "amount": 5000, "shares": 2500, "nav": 2.0},
            {"type": "sell", "amount": 5000, "shares": 2500, "nav": 2.0},
        ]
        r = recalc_holding(txs)
        assert r["total_shares"] == 0
        assert r["total_cost"] == 0
        assert r["avg_nav"] == 0

    def test_sell_more_than_held_clamps_to_zero(self):
        """卖出份额超过持有量，应被 clamp 到 0"""
        txs = [
            {"type": "buy", "amount": 1000, "shares": 500, "nav": 2.0},
            {"type": "sell", "amount": 3000, "shares": 1500, "nav": 2.0},
        ]
        r = recalc_holding(txs)
        assert r["total_shares"] == 0
        assert r["total_cost"] == 0

    def test_auto_invest_source(self):
        """定投产生的交易和手动交易一视同仁"""
        txs = [
            {"type": "buy", "amount": 500, "shares": 270, "nav": 1.852, "source": "auto_invest"},
            {"type": "buy", "amount": 5000, "shares": 2700, "nav": 1.852, "source": "manual"},
        ]
        r = recalc_holding(txs)
        assert r["total_shares"] == 2970
        assert r["total_cost"] == 5500

    def test_different_navs_avg_cost(self):
        """不同净值买入，验证加权平均成本"""
        txs = [
            {"type": "buy", "amount": 2000, "shares": 1000, "nav": 2.0},
            {"type": "buy", "amount": 1500, "shares": 1000, "nav": 1.5},
        ]
        r = recalc_holding(txs)
        assert r["total_shares"] == 2000
        assert r["total_cost"] == 3500
        assert r["avg_nav"] == round(3500 / 2000, 4)  # 1.75


# ====== 定投周期计算（等价于前端 getPendingPeriods + getNextInvestDate） ======

def get_next_invest_date(frequency: str, day: int, from_date: datetime) -> datetime:
    """计算下一个定投执行日期。"""
    d = from_date

    if frequency == "daily":
        d = d + timedelta(days=1)
    elif frequency == "monthly":
        # 下个月的目标日
        month = d.month + 1
        year = d.year
        if month > 12:
            month = 1
            year += 1
        target_day = min(day, 28)
        d = datetime(year, month, target_day, 12, 0, 0)
    elif frequency == "biweekly":
        d = d + timedelta(days=14)
        # 调整到目标周几 (day: 1=周一...5=周五)
        current_weekday = d.isoweekday()  # 1=Mon...7=Sun
        diff = (day - current_weekday + 7) % 7
        if diff > 0:
            d = d + timedelta(days=diff)
    else:
        # weekly: 往后推到下一个目标周几
        d = d + timedelta(days=1)  # 至少往后一天
        while d.isoweekday() != day:
            d = d + timedelta(days=1)

    # 跳过周末
    while d.weekday() >= 5:  # 5=Sat, 6=Sun
        d = d + timedelta(days=1)

    return d.replace(hour=12, minute=0, second=0, microsecond=0)


def get_pending_periods(frequency: str, day: int, last_executed: datetime, now: datetime, max_periods: int = 10) -> list[str]:
    """计算从上次执行到现在有几期未执行。返回日期列表。"""
    periods = []
    from_date = last_executed
    next_date = get_next_invest_date(frequency, day, from_date)

    count = 0
    while next_date <= now and count < max_periods:
        periods.append(next_date.strftime("%Y-%m-%d"))
        from_date = next_date
        next_date = get_next_invest_date(frequency, day, from_date)
        count += 1

    return periods


class TestInvestSchedule:
    """定投周期计算测试"""

    def test_weekly_basic(self):
        """每周三定投，上次周三执行，下次应是下周三"""
        last = datetime(2026, 3, 25, 12, 0)  # 周三
        nxt = get_next_invest_date("weekly", 3, last)  # day=3=周三
        assert nxt.isoweekday() == 3
        assert nxt > last
        assert (nxt - last).days == 7

    def test_weekly_skips_weekend(self):
        """如果目标日是周六/日，应顺延到周一"""
        # 周五出发，目标是周六(day=6) → 应该顺延到下周一
        last = datetime(2026, 3, 27, 12, 0)  # 周五
        nxt = get_next_invest_date("weekly", 6, last)
        assert nxt.weekday() < 5  # 不是周末

    def test_monthly_basic(self):
        """每月15号"""
        last = datetime(2026, 3, 15, 12, 0)
        nxt = get_next_invest_date("monthly", 15, last)
        assert nxt.month == 4
        assert nxt.day == 15

    def test_monthly_day_28_max(self):
        """每月30号 → 截断到28号"""
        last = datetime(2026, 1, 28, 12, 0)
        nxt = get_next_invest_date("monthly", 30, last)
        assert nxt.day <= 28

    def test_biweekly(self):
        """每两周周三"""
        last = datetime(2026, 3, 19, 12, 0)  # 周三
        nxt = get_next_invest_date("biweekly", 3, last)
        assert nxt.isoweekday() == 3
        diff = (nxt - last).days
        assert diff >= 14

    def test_pending_zero_periods(self):
        """刚执行过，没有待执行"""
        now = datetime(2026, 4, 2, 12, 0)  # 周三
        last = datetime(2026, 4, 2, 10, 0)  # 今天刚执行
        periods = get_pending_periods("weekly", 3, last, now)
        assert len(periods) == 0

    def test_pending_one_period(self):
        """过了一个周期"""
        last = datetime(2026, 3, 26, 12, 0)  # 上周三
        now = datetime(2026, 4, 2, 14, 0)   # 本周三下午
        periods = get_pending_periods("weekly", 3, last, now)
        assert len(periods) == 1

    def test_pending_multiple_periods(self):
        """过了多个周期（用户多周没打开）"""
        last = datetime(2026, 3, 5, 12, 0)   # 很久前
        now = datetime(2026, 4, 2, 14, 0)    # 4周后
        periods = get_pending_periods("weekly", 3, last, now)
        assert len(periods) >= 3

    def test_pending_max_10(self):
        """补执行最多10期"""
        last = datetime(2025, 1, 1, 12, 0)
        now = datetime(2026, 4, 2, 14, 0)
        periods = get_pending_periods("weekly", 3, last, now)
        assert len(periods) <= 10

    def test_monthly_pending(self):
        """月定投：3个月没打开应有3期"""
        last = datetime(2025, 12, 15, 12, 0)
        now = datetime(2026, 4, 2, 14, 0)
        periods = get_pending_periods("monthly", 15, last, now)
        assert len(periods) >= 3  # 1月15、2月15、3月15

    def test_next_date_never_on_weekend(self):
        """所有频率的下次执行日都不应在周末"""
        for freq in ["daily", "weekly", "biweekly", "monthly"]:
            for day in range(1, 6):
                for offset in range(0, 30):
                    base = datetime(2026, 3, 1, 12, 0) + timedelta(days=offset)
                    nxt = get_next_invest_date(freq, day if freq != "monthly" else 15, base)
                    assert nxt.weekday() < 5, f"{freq} day={day} from={base} → {nxt} is weekend!"

    def test_daily_basic(self):
        """每天定投：周三→周四"""
        last = datetime(2026, 4, 1, 12, 0)  # 周三
        nxt = get_next_invest_date("daily", 0, last)
        assert nxt.date() == datetime(2026, 4, 2).date()  # 周四

    def test_daily_skips_weekend(self):
        """每天定投：周五→下周一"""
        last = datetime(2026, 4, 3, 12, 0)  # 周五
        nxt = get_next_invest_date("daily", 0, last)
        assert nxt.weekday() == 0  # 周一
        assert nxt.date() == datetime(2026, 4, 6).date()

    def test_daily_pending_one_week(self):
        """每天定投：一周没打开应有5期（跳过周末）"""
        last = datetime(2026, 3, 27, 12, 0)  # 周五
        now = datetime(2026, 4, 4, 14, 0)    # 下周五
        periods = get_pending_periods("daily", 0, last, now)
        # 3/30周一, 3/31周二, 4/1周三, 4/2周四, 4/3周五 = 5期
        assert len(periods) == 5
        # 所有日期都不在周末
        for p in periods:
            d = datetime.strptime(p, "%Y-%m-%d")
            assert d.weekday() < 5
