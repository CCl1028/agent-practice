"""市场数据工具 — 兼容层（re-export）

Phase B 重构：原 815 行已拆分为 6 个独立模块。
此文件保留所有原有的公开函数名，通过 re-export 保持向后兼容。
后续可逐步将调用方迁移到具体模块，最终删除此文件。
"""

# 基金名称映射
from src.tools.fund_name import (  # noqa: F401
    get_fund_name_by_code,
    get_fund_code_by_name,
    verify_and_fix_fund,
)

# 基金净值
from src.tools.fund_nav import (  # noqa: F401
    get_fund_nav,
    get_fund_nav_history,
    _mock_fund_nav,
)

# 基金估值
from src.tools.fund_estimation import (  # noqa: F401
    get_fund_estimation,
    refresh_estimation_cache,
    get_estimation_cache_info,
    _get_last_close_change,
)

# 基金画像
from src.tools.fund_profile import (  # noqa: F401
    get_fund_profile,
    get_fund_perf_analysis,
)

# 板块 & 新闻
from src.tools.sector import (  # noqa: F401
    get_sector_performance,
    get_market_news,
)

# 公共工具
from src.tools.common import is_trading_hours  # noqa: F401

# 基金新闻（保持原位，未拆分）
from src.tools.news_tools import search_fund_news as _search_fund_news  # noqa: F401

import logging

logger = logging.getLogger(__name__)


def get_fund_news(fund_name: str, fund_code: str = "") -> list[dict]:
    """获取基金相关新闻。"""
    try:
        news = _search_fund_news(fund_name, fund_code)
        logger.info("[基金新闻] 获取 %s(%s) 共 %d 条新闻", fund_name, fund_code, len(news))
        return news
    except Exception as e:
        logger.warning("[基金新闻] 获取失败: %s", e)
        return []
