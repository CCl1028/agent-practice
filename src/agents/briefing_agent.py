"""Briefing Agent — 简报撰写员

v2: 参考 daily_stock_analysis 增强决策核心：
- 规则引擎从 2 维扩展为 6 维（盈亏×趋势×乖离率×均线×波动率×持有时间）
- 新增交易纪律硬规则（追高检测、空头排列禁加仓）
- LLM Prompt 注入新闻情报 + 技术指标 + 交易纪律
- 输出结构新增评分、风险提示
"""

from __future__ import annotations

import logging

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, TEXT_MODEL
from src.state import AgentState, Briefing, FundAdvice, FundHolding

logger = logging.getLogger(__name__)


# ============================================
# JSON 解析辅助 — T-010: 增强 LLM JSON 输出解析鲁棒性
# ============================================

def _clean_json_text(text: str) -> str:
    """清理 LLM 输出的 JSON 文本中的常见问题。

    处理：
    - 去除尾逗号（如 {"a": 1,}）
    - 去除 JS 风格注释（// 和 /* */）
    - 去除 BOM 和特殊不可见字符
    """
    import re
    # 去除 BOM
    text = text.lstrip("\ufeff")
    # 去除单行注释（// ...）— 但保留 URL 中的 //
    text = re.sub(r'(?<!:)//.*?(?=\n|$)', '', text)
    # 去除多行注释（/* ... */）
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # 去除对象/数组尾逗号（如 {"a": 1,} 或 [1, 2,]）
    text = re.sub(r',\s*([\]}])', r'\1', text)
    return text.strip()

# ============================================
# System Prompt — v2 升级版
# ============================================

SYSTEM_PROMPT = """\
你是一个专业但说人话的基金投资助手。用户把持仓和市场数据给你，你需要综合分析并给出操作建议。

## 分析框架（5 个维度）
1. **盈亏状态** — 浮盈/浮亏幅度，是否到止盈/止损区间
2. **短期趋势** — 近5日走势方向、强度、波动率
3. **均线信号** — 均线排列状态（多头/空头/震荡）、乖离率
4. **市场环境** — 所属板块强弱、整体市场情绪
5. **新闻情报** — 该基金/行业近期有无重大消息

## 交易纪律（硬规则，必须遵守！）
- 🚫 **严禁追高**：乖离率 > 3% 且连续上涨 → 必须提示追高风险，不可建议加仓
- 🚫 **空头排列禁加仓**：均线空头排列（MA5 < MA10 < MA20）→ 不可建议加仓
- 🚫 **下跌中禁补仓**：浮亏 > 10% 且仍在下跌 → 建议观望等企稳，不可建议加仓
- ✅ **趋势确认才做多**：只有多头排列或震荡企稳才可建议加仓
- ✅ **止盈不犹豫**：浮盈 > 15% 且短期连涨 → 至少建议部分止盈

## 输出要求
- 语言简洁直白，像朋友聊天
- 不要用专业术语轰炸用户
- 结论明确，不模棱两可
- 如果没有明确信号，就说"观望"，别硬编建议
- 如果有风险点，必须在 risk_note 中指出

请严格按以下 JSON 格式输出，不要输出其他内容：
{"summary": "一句话总结(≤15字)", \
"details": [{"fund_name": "基金名", "action": "加仓/减仓/观望/持有", \
"reason": "一两句话理由", "confidence": "高/中/低", "score": 0-100评分, \
"risk_note": "风险提示，无则空字符串"}], \
"market_note": "一两句话市场简评", \
"risk_alerts": ["全局风险提示1", "全局风险提示2"]}
"""


# ============================================
# 增强规则引擎 — v2
# ============================================

def _rule_engine(fund: FundHolding) -> tuple[str, str, int, str]:
    """增强规则引擎：6 维决策。

    维度：盈亏 × 趋势 × 乖离率 × 均线 × 波动率 × 持有时间

    Returns:
        (action, reason, score, risk_note)
    """
    profit = fund.get("profit_ratio", 0)
    trend = fund.get("trend_5d", [])
    hold_days = fund.get("hold_days", 0)
    est_change = fund.get("est_change")
    ma_status = fund.get("ma_status", "数据不足")
    deviation = fund.get("deviation_rate", 0)
    volatility = fund.get("volatility_5d", 0)

    trend_sum = sum(trend) if trend else 0
    is_rising = trend_sum > 1.0
    is_falling = trend_sum < -1.0

    # ---- 交易纪律硬规则（最高优先级）----

    # 规则 1: 追高检测 — 乖离率 > 3% 且上涨趋势
    if deviation > 3.0 and is_rising:
        return (
            "观望",
            f"乖离率{deviation:.1f}%偏高且连涨，存在追高风险，等回踩再考虑",
            35,
            f"⚠️ 追高风险：乖离率{deviation:.1f}%，短期涨幅过大",
        )

    # 规则 2: 空头排列禁加仓
    if ma_status == "空头排列" and profit < -5:
        return (
            "观望",
            f"均线空头排列，趋势向下，浮亏{profit:.1f}%，等待企稳信号",
            30,
            "⚠️ 均线空头排列，趋势未反转，不宜加仓",
        )

    # 规则 3: 止盈提醒 — 浮盈 > 15% 且连涨
    if profit > 15 and is_rising:
        return (
            "减仓",
            f"浮盈{profit:.1f}%且短期连涨，建议至少部分止盈锁定利润",
            80,
            "",
        )

    # ---- 常规规则 ----

    # 浮盈 > 10% 的情况
    if profit > 10:
        if is_rising:
            score = 75 if deviation > 2.0 else 65
            return (
                "减仓",
                f"浮盈{profit:.1f}%且短期连涨，可考虑止盈",
                score,
                f"乖离率{deviation:.1f}%" if deviation > 2.0 else "",
            )
        else:
            return "持有", f"浮盈{profit:.1f}%但涨势放缓，继续持有观察", 55, ""

    # 浮亏 > 10% 的情况
    if profit < -10:
        if is_falling:
            return (
                "观望",
                f"浮亏{profit:.1f}%且仍在下跌，等待企稳信号",
                40,
                "⚠️ 仍在下跌中，切勿补仓",
            )
        elif ma_status == "多头排列" or (not is_falling and not is_rising):
            # 企稳 + 均线转好 → 可以考虑补仓
            if hold_days > 180:
                return (
                    "加仓",
                    f"深度套牢{profit:.1f}%超半年但已企稳，可小额补仓摊低成本",
                    55,
                    "建议小额分批补仓，控制仓位",
                )
            else:
                return "加仓", f"浮亏{profit:.1f}%但已企稳，可考虑补仓", 50, ""
        else:
            return "观望", f"浮亏{profit:.1f}%，趋势不明朗，继续观察", 40, ""

    # 盈亏 ≤ 10% 的情况
    if is_rising and ma_status == "多头排列":
        return "持有", "均线多头排列，短期上涨中，持有为主", 60, ""
    elif is_rising:
        return "观望", "短期上涨但均线未完全转好，持有观察", 50, ""
    elif is_falling:
        return "观望", "盈亏幅度不大，短期回调中，暂不操作", 45, ""

    # 震荡 + 盘中估值辅助
    if est_change is not None:
        if est_change < -2.0:
            return "观望", f"今日估值下跌{est_change:.1f}%，等日内企稳", 40, ""
        elif est_change > 2.0 and profit > 5:
            return "持有", f"今日估值上涨{est_change:.1f}%，短期偏强，继续持有", 55, ""

    # 高波动提醒
    risk = ""
    if volatility > 4.0:
        risk = f"⚠️ 近5日波动率{volatility:.1f}%偏高，注意风险"

    return "观望", "无明显趋势信号，保持观望", 45, risk


# ============================================
# 构建 LLM Prompt 数据
# ============================================

def _build_data_text(state: AgentState) -> str:
    """将 state 数据整理成文本，供 LLM 使用。v2 新增技术指标和新闻。"""
    lines = ["## 持仓数据\n"]
    portfolio = state.get("portfolio", [])
    market = state.get("market", {})
    fund_news = market.get("fund_news", {})

    for f in portfolio:
        action, reason, score, risk = _rule_engine(f)
        est_info = ""
        if f.get("est_change") is not None:
            est_info = f", 今日预估{f['est_change']:+.2f}%（{f.get('est_time', '')}）"

        # 基础数据
        lines.append(
            f"- **{f['fund_name']}**({f['fund_code']}): "
            f"成本{f.get('cost_nav', 0):.2f}, 现价{f['current_nav']:.2f}, "
            f"盈亏{f.get('profit_ratio', 0):+.2f}%, 持有{f.get('hold_days', 0)}天"
        )

        # v2: 技术指标
        lines.append(
            f"  技术指标: MA5={f.get('ma5', 0):.3f} MA10={f.get('ma10', 0):.3f} "
            f"MA20={f.get('ma20', 0):.3f} | 均线:{f.get('ma_status', '?')} | "
            f"乖离率:{f.get('deviation_rate', 0):+.2f}% | "
            f"波动率:{f.get('volatility_5d', 0):.2f}%"
        )

        lines.append(
            f"  近5日趋势: {f.get('trend_5d', [])}{est_info}"
        )
        lines.append(f"  规则初判: {action}({score}分) — {reason}")
        if risk:
            lines.append(f"  ⚠️ 风险: {risk}")

        # v2: 该基金的专属新闻
        news_items = fund_news.get(f["fund_code"], [])
        if news_items:
            lines.append("  📰 相关新闻:")
            for item in news_items[:4]:
                dim_emoji = {"latest": "📰", "risk": "🚨", "performance": "📊"}.get(
                    item.get("dimension", ""), "📰"
                )
                lines.append(f"    {dim_emoji} {item.get('title', '')}")
                snippet = item.get("snippet", "")
                if snippet:
                    lines.append(f"       {snippet[:100]}")
        lines.append("")

    # 市场数据
    lines.append("\n## 市场数据\n")
    lines.append(f"市场情绪: {market.get('market_sentiment', '未知')}")
    for s in market.get("sectors", []):
        lines.append(f"- {s['name']}: {s['change']:+.1f}%")
    lines.append("\n热点新闻:")
    for n in market.get("hot_news", []):
        lines.append(f"- {n}")

    return "\n".join(lines)


# ============================================
# LangGraph 节点
# ============================================

def briefing_node(state: AgentState) -> dict:
    """LangGraph 节点：生成每日简报。"""
    logger.info("[Briefing Agent] 开始生成简报...")

    portfolio = state.get("portfolio", [])
    if not portfolio:
        return {
            "briefing": {
                "summary": "暂无持仓数据",
                "details": [],
                "market_note": "",
                "risk_alerts": [],
            }
        }

    # 先用规则引擎生成基础建议
    details: list[FundAdvice] = []
    global_risks: list[str] = []

    for f in portfolio:
        action, reason, score, risk_note = _rule_engine(f)
        confidence = "高" if score >= 70 else ("中" if score >= 50 else "低")
        details.append({
            "fund_name": f["fund_name"],
            "action": action,
            "reason": reason,
            "confidence": confidence,
            "score": score,
            "risk_note": risk_note,
        })
        if risk_note:
            global_risks.append(f"{f['fund_name']}: {risk_note}")

    # 尝试用 LLM 润色
    try:
        if not OPENAI_API_KEY:
            raise ValueError("未配置 OPENAI_API_KEY，使用规则引擎结果")

        llm = ChatOpenAI(
            model=TEXT_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            temperature=0.3,
            request_timeout=30,
            max_retries=2,
        )

        data_text = _build_data_text(state)
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=(
                f"以下是今日数据，请生成操作建议。\n\n{data_text}"
            )),
        ])

        import json
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        # T-010: 增强 JSON 解析鲁棒性 — 清理常见的 LLM 输出问题
        text = _clean_json_text(text)
        briefing_data = json.loads(text)

        # 解析 LLM 输出，确保结构完整
        llm_details = briefing_data.get("details", [])
        parsed_details = []
        for d in llm_details:
            parsed_details.append({
                "fund_name": d.get("fund_name", ""),
                "action": d.get("action", "观望"),
                "reason": d.get("reason", ""),
                "confidence": d.get("confidence", "中"),
                "score": d.get("score", 50),
                "risk_note": d.get("risk_note", ""),
            })

        briefing: Briefing = {
            "summary": briefing_data.get("summary", "今日建议已生成"),
            "details": parsed_details if parsed_details else details,
            "market_note": briefing_data.get("market_note", ""),
            "risk_alerts": briefing_data.get("risk_alerts", global_risks),
        }
        logger.info("[Briefing Agent] LLM 生成完成: %s", briefing["summary"])

    except Exception as e:
        logger.warning("[Briefing Agent] LLM 调用失败: %s，使用规则引擎结果", e)
        # 降级：用规则引擎结果
        actions = set(d["action"] for d in details)
        if actions == {"观望"}:
            summary = "今天无需操作"
        elif "减仓" in actions:
            summary = "有基金可考虑止盈"
        elif "加仓" in actions:
            summary = "有基金可考虑补仓"
        elif "持有" in actions:
            summary = "继续持有为主"
        else:
            summary = "今日建议观望为主"

        market = state.get("market", {})
        briefing: Briefing = {
            "summary": summary,
            "details": details,
            "market_note": f"市场情绪{market.get('market_sentiment', '未知')}",
            "risk_alerts": global_risks,
        }

    logger.info("[Briefing Agent] 简报生成完成")
    return {"briefing": briefing}
