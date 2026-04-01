"""Briefing Agent — 简报撰写员

职责：综合持仓和市场数据，生成结构化操作建议。
MVP 策略：规则引擎初筛 + LLM 润色输出。
"""

from __future__ import annotations

import logging

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, TEXT_MODEL
from src.state import AgentState, Briefing, FundAdvice, FundHolding

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
你是一个专业但说人话的基金投资助手。用户把持仓和市场数据给你，你需要：

1. 对每只基金给出操作建议（加仓/减仓/观望）
2. 给出简短理由（一两句话）
3. 最后生成一句话总结（≤15字）和市场简评

要求：
- 语言简洁直白，像朋友聊天
- 不要用专业术语轰炸用户
- 结论明确，不模棱两可
- 如果没有明确信号，就说"观望"，别硬编建议
"""


def _rule_engine(fund: FundHolding) -> tuple[str, str]:
    """规则引擎：根据盈亏和趋势给出初步建议。"""
    profit = fund.get("profit_ratio", 0)
    trend = fund.get("trend_5d", [])

    # 计算近5日趋势方向
    trend_sum = sum(trend) if trend else 0
    is_rising = trend_sum > 1.0
    is_falling = trend_sum < -1.0

    if profit > 10 and is_rising:
        return "减仓", f"浮盈{profit:.1f}%且短期连涨，可考虑止盈"
    elif profit > 10 and not is_rising:
        return "观望", f"浮盈{profit:.1f}%但涨势放缓，继续观察"
    elif profit < -10 and not is_falling:
        return "加仓", f"浮亏{profit:.1f}%但已企稳，可考虑补仓摊低成本"
    elif profit < -10 and is_falling:
        return "观望", f"浮亏{profit:.1f}%且仍在下跌，等待企稳信号"
    elif abs(profit) <= 10 and is_rising:
        return "观望", "盈亏幅度不大，短期上涨中，持有观察"
    elif abs(profit) <= 10 and is_falling:
        return "观望", "盈亏幅度不大，短期回调中，暂不操作"
    else:
        return "观望", "无明显趋势信号，保持观望"


def _build_data_text(state: AgentState) -> str:
    """将 state 数据整理成文本，供 LLM 使用。"""
    lines = ["## 持仓数据\n"]
    portfolio = state.get("portfolio", [])
    for f in portfolio:
        action, reason = _rule_engine(f)
        est_info = ""
        if f.get("est_change") is not None:
            est_info = f", 今日预估{f['est_change']:+.2f}%（{f.get('est_time', '')}）"
        lines.append(
            f"- {f['fund_name']}({f['fund_code']}): "
            f"成本{f['cost_nav']:.2f}, 现价{f['current_nav']:.2f}, "
            f"盈亏{f['profit_ratio']:+.2f}%, 持有{f['hold_days']}天, "
            f"近5日趋势{f.get('trend_5d', [])}{est_info}\n"
            f"  规则初判: {action} — {reason}"
        )

    lines.append("\n## 市场数据\n")
    market = state.get("market", {})
    lines.append(f"市场情绪: {market.get('market_sentiment', '未知')}")
    for s in market.get("sectors", []):
        lines.append(f"- {s['name']}: {s['change']:+.1f}%")
    lines.append("\n热点新闻:")
    for n in market.get("hot_news", []):
        lines.append(f"- {n}")

    return "\n".join(lines)


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
            }
        }

    # 先用规则引擎生成基础建议
    details: list[FundAdvice] = []
    for f in portfolio:
        action, reason = _rule_engine(f)
        details.append({
            "fund_name": f["fund_name"],
            "action": action,
            "reason": reason,
            "confidence": "中",
        })

    # 尝试用 LLM 润色
    try:
        if not OPENAI_API_KEY:
            raise ValueError("未配置 OPENAI_API_KEY，使用规则引擎结果")

        llm = ChatOpenAI(
            model=TEXT_MODEL,
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            temperature=0.3,
        )

        data_text = _build_data_text(state)
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=(
                f"以下是今日数据，请生成操作建议。\n\n{data_text}\n\n"
                "请严格按以下 JSON 格式输出，不要输出其他内容：\n"
                '{"summary": "一句话总结(≤15字)", '
                '"details": [{"fund_name": "基金名", "action": "加仓/减仓/观望", '
                '"reason": "一两句话理由", "confidence": "高/中/低"}], '
                '"market_note": "一两句话市场简评"}'
            )),
        ])

        import json
        text = response.content.strip()
        # 处理可能的 markdown 包裹
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        briefing_data = json.loads(text)

        briefing: Briefing = {
            "summary": briefing_data.get("summary", "今日建议已生成"),
            "details": briefing_data.get("details", details),
            "market_note": briefing_data.get("market_note", ""),
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
        else:
            summary = "今日建议观望为主"

        market = state.get("market", {})
        briefing: Briefing = {
            "summary": summary,
            "details": details,
            "market_note": f"市场情绪{market.get('market_sentiment', '未知')}",
        }

    logger.info("[Briefing Agent] 简报生成完成")
    return {"briefing": briefing}
