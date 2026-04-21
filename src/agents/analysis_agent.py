"""Analysis Agent — 基金诊断分析员

职责：
- 基金买前诊断：是否值得买、风险评估、行业分析
- 涨跌原因分析：为什么涨了、为什么跌了

v2: 参考 daily_stock_analysis 增强：
- 多维度基金评估（收益、波动、规模、持仓）
- 关联新闻情报进行因果分析
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, TEXT_MODEL
from src.state import AgentState
from src.tools.market_tools import (
    get_fund_news,
    get_fund_perf_analysis,
    get_fund_profile,
)

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
    text = re.sub(r"(?<!:)//.*?(?=\n|$)", "", text)
    # 去除多行注释（/* ... */）
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # 去除对象/数组尾逗号（如 {"a": 1,} 或 [1, 2,]）
    text = re.sub(r",\s*([\]}])", r"\1", text)
    return text.strip()


# ============================================
# System Prompts
# ============================================

FUND_DIAGNOSIS_PROMPT = """\
你是一个专业的基金分析师。用户给你一只基金的基本信息，你需要进行诊断分析。

## 分析框架（4 个维度）

1. **收益表现** — 近1年、近3年、近5年回报，与同类基金对比
2. **风险指标** — 最大回撤、波动率、风险等级
3. **规模和持仓** — 基金规模、重仓行业/股票、持仓集中度
4. **基金经理** — 从业经历、历史表现（如果有）

## 输出要求

- 综合评价：优秀/良好/中等/偏弱（简短）
- 优点（最多3条）：实际的优势
- 风险（最多3条）：需要关注的风险
- 是否值得买：可以/谨慎/不建议，加短理由

## 注意

- 语言平易近人，避免过度专业术语
- 不做绝对推荐，只分析客观事实
- 强调"自己的风险承受能力"很重要

请严格按以下 JSON 格式输出：
{"rating": "优秀/良好/中等/偏弱", \
"pros": ["优点1", "优点2", "优点3"], \
"risks": ["风险1", "风险2", "风险3"], \
"buy_recommendation": "可以/谨慎/不建议", \
"buy_reason": "简短理由", \
"summary": "一句话总结"}
"""

FALL_REASON_PROMPT = """\
你是一个专业的基金分析师。用户给你一只基金的涨跌数据和市场背景，你需要分析涨跌原因。

## 分析框架（3 个维度）

1. **板块贡献** — 重仓行业今日是否涨跌、幅度多大
2. **市场情绪** — 大盘、同类基金是否同向波动
3. **基金特有因素** — 重仓股业绩、政策消息、基金操作等

## 输出要求

- 涨跌方向：上涨/下跌
- 主要原因（最多3条）：从大到小排列
- 后市展望：短期可能如何发展

## 注意

- 基于事实分析，避免过度解读
- 强调"不确定性"
- 不预测未来

请严格按以下 JSON 格式输出：
{"direction": "上涨/下跌", \
"change_ratio": 0.0, \
"reasons": ["原因1（权重70%）", "原因2（权重20%）", "原因3（权重10%）"], \
"outlook": "短期可能如何发展的简短判断", \
"summary": "一句话总结涨跌原因"}
"""


# ============================================
# 规则引擎 — 基金诊断打分
# ============================================


def _rate_fund(profile: dict) -> tuple[str, list[str], list[str], str]:
    """基于基金数据进行诊断打分。

    Args:
        profile: {
            "perf_1y": 0-100,        # 近1年收益百分比
            "max_drawdown": -100~0,  # 最大回撤百分比
            "size_billion": 0-9999,  # 基金规模，单位亿元
            "volatility": 0-100,     # 波动率百分比
            "sectors": [...],        # 重仓行业
            "manager_perf": "良好",  # 基金经理表现
        }

    Returns:
        (rating, pros, risks, buy_reason)
    """
    perf_1y = profile.get("perf_1y", 0)
    max_dd = profile.get("max_drawdown", 0)
    vol = profile.get("volatility", 10)
    size = profile.get("size_billion", 0)
    sectors = profile.get("sectors", [])

    pros: list[str] = []
    risks: list[str] = []
    score = 50

    # --- 收益维度 ---
    if perf_1y > 30:
        pros.append(f"近1年收益{perf_1y:.1f}%，明显好于平均水平")
        score += 20
    elif perf_1y > 10:
        pros.append(f"近1年收益{perf_1y:.1f}%，跑赢大盘")
        score += 10
    elif perf_1y < -10:
        risks.append(f"近1年收益{perf_1y:.1f}%，表现欠佳")
        score -= 15

    # --- 回撤维度 ---
    if max_dd > -20:
        pros.append("最大回撤控制良好，风险相对可控")
        score += 10
    elif max_dd < -40:
        risks.append(f"最大回撤{max_dd:.1f}%，波动较大，需谨慎")
        score -= 15

    # --- 波动率维度 ---
    if vol < 10:
        pros.append("波动率低，适合稳健投资者")
        score += 5
    elif vol > 20:
        risks.append(f"波动率{vol:.1f}%，较为激进，对心理素质有要求")
        score -= 10

    # --- 规模维度 ---
    if size > 100:
        pros.append("基金规模>100亿，稳定性好")
        score += 5
    elif size < 5:
        risks.append("基金规模较小，存在清盘风险")
        score -= 10

    # --- 持仓维度 ---
    if len(sectors) >= 3:
        pros.append("行业分散，风险分散合理")
        score += 5
    elif len(sectors) <= 2:
        risks.append("行业持仓集中，板块风险较大")
        score -= 5

    # --- 综合评级 ---
    if score >= 80:
        rating = "优秀"
    elif score >= 65:
        rating = "良好"
    elif score >= 50:
        rating = "中等"
    else:
        rating = "偏弱"

    buy_reason = ""
    if rating in ["优秀", "良好"]:
        buy_reason = "可以关注，建议分批建仓"
    elif rating == "中等":
        buy_reason = "可以，但需评估自己的风险承受能力"
    else:
        buy_reason = "谨慎考虑，建议先了解更多信息"

    return rating, pros, risks, buy_reason


# ============================================
# LangGraph 节点
# ============================================


def fund_diagnosis_node(state: AgentState) -> dict:
    """LangGraph 节点：基金买前诊断。"""
    logger.info("[Analysis Agent] 开始基金诊断分析...")

    fund_code = state.get("query_fund_code", "")
    fund_name = state.get("query_fund_name", "")

    if not fund_code and not fund_name:
        return {
            "error": "未指定基金代码或名称",
            "diagnosis": None,
        }

    try:
        # 获取基金基本信息
        profile = get_fund_profile(fund_code or fund_name)
        if not profile:
            return {
                "error": f"无法获取基金信息: {fund_code or fund_name}",
                "diagnosis": None,
            }

        logger.info("[Analysis Agent] 基金信息: %s", profile)

        # 规则引擎初判
        rating, pros, risks, buy_reason = _rate_fund(profile)

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

            # 构建提示信息
            data_text = f"""
基金信息：
- 代码: {profile.get("code", fund_code)}
- 名称: {profile.get("name", fund_name)}
- 近1年收益: {profile.get("perf_1y", 0):.2f}%
- 最大回撤: {profile.get("max_drawdown", 0):.2f}%
- 基金规模: {profile.get("size_billion", 0):.1f}亿元
- 波动率: {profile.get("volatility", 0):.2f}%
- 重仓行业: {", ".join(profile.get("sectors", []))}
- 基金经理: {profile.get("manager", "未知")}
            """

            response = llm.invoke(
                [
                    SystemMessage(content=FUND_DIAGNOSIS_PROMPT),
                    HumanMessage(content=f"请诊断以下基金是否值得买：\n{data_text}"),
                ]
            )

            import json

            text = response.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            # T-010: 增强 JSON 解析鲁棒性
            text = _clean_json_text(text)
            diagnosis_data = json.loads(text)

            diagnosis = {
                "fund_code": fund_code,
                "fund_name": fund_name,
                "rating": diagnosis_data.get("rating", rating),
                "pros": diagnosis_data.get("pros", pros),
                "risks": diagnosis_data.get("risks", risks),
                "buy_recommendation": diagnosis_data.get("buy_recommendation", "谨慎"),
                "buy_reason": diagnosis_data.get("buy_reason", buy_reason),
                "summary": diagnosis_data.get("summary", ""),
                "profile": profile,
            }
            logger.info("[Analysis Agent] LLM 诊断完成: %s", diagnosis["summary"])

        except Exception as e:
            logger.warning("[Analysis Agent] LLM 调用失败: %s，使用规则引擎结果", e)
            diagnosis = {
                "fund_code": fund_code,
                "fund_name": fund_name,
                "rating": rating,
                "pros": pros,
                "risks": risks,
                "buy_recommendation": "可以"
                if rating in ["优秀", "良好"]
                else ("谨慎" if rating == "中等" else "不建议"),
                "buy_reason": buy_reason,
                "summary": f"综合评价：{rating}。{buy_reason}",
                "profile": profile,
            }

        return {"diagnosis": diagnosis}

    except Exception as e:
        logger.error("[Analysis Agent] 诊断失败: %s", e, exc_info=True)
        return {"error": f"诊断失败: {e}", "diagnosis": None}


def fall_reason_node(state: AgentState) -> dict:
    """LangGraph 节点：分析基金涨跌原因。"""
    logger.info("[Analysis Agent] 开始分析涨跌原因...")

    fund_code = state.get("query_fund_code", "")
    fund_name = state.get("query_fund_name", "")

    if not fund_code and not fund_name:
        return {
            "error": "未指定基金代码或名称",
            "fall_analysis": None,
        }

    try:
        # 获取基金今日数据
        perf_data = get_fund_perf_analysis(fund_code or fund_name)
        if not perf_data:
            return {
                "error": f"无法获取基金今日数据: {fund_code or fund_name}",
                "fall_analysis": None,
            }

        logger.info("[Analysis Agent] 今日数据: %s", perf_data)

        # 获取相关新闻
        news = get_fund_news(fund_name or fund_code, fund_code)

        # 构建分析数据
        data_text = f"""
基金今日表现：
- 代码: {fund_code}
- 名称: {fund_name}
- 今日涨跌: {perf_data.get("today_change", 0):+.2f}%
- 重仓行业: {", ".join(perf_data.get("sectors", []))}
- 行业涨跌: {perf_data.get("sector_change", "+0.00%")}%
- 大盘表现: {perf_data.get("market_change", "+0.00%")}%
- 市场情绪: {perf_data.get("market_sentiment", "中性")}

相关新闻：
{chr(10).join([f"- {n.get('title', '')}" for n in (news or [])[:5]])}
        """

        # 尝试用 LLM 分析
        try:
            if not OPENAI_API_KEY:
                raise ValueError("未配置 OPENAI_API_KEY")

            llm = ChatOpenAI(
                model=TEXT_MODEL,
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_BASE_URL,
                temperature=0.3,
                request_timeout=30,
                max_retries=2,
            )

            response = llm.invoke(
                [
                    SystemMessage(content=FALL_REASON_PROMPT),
                    HumanMessage(content=f"请分析以下基金的涨跌原因：\n{data_text}"),
                ]
            )

            import json

            text = response.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            # T-010: 增强 JSON 解析鲁棒性
            text = _clean_json_text(text)
            analysis_data = json.loads(text)

            fall_analysis = {
                "fund_code": fund_code,
                "fund_name": fund_name,
                "direction": analysis_data.get("direction", "未知"),
                "change_ratio": analysis_data.get("change_ratio", perf_data.get("today_change", 0)),
                "reasons": analysis_data.get("reasons", []),
                "outlook": analysis_data.get("outlook", ""),
                "summary": analysis_data.get("summary", ""),
                "perf_data": perf_data,
            }
            logger.info("[Analysis Agent] LLM 分析完成: %s", fall_analysis["summary"])

        except Exception as e:
            logger.warning("[Analysis Agent] LLM 调用失败: %s，使用规则结果", e)
            today_change = perf_data.get("today_change", 0)
            direction = "上涨" if today_change > 0 else ("下跌" if today_change < 0 else "平盘")
            reasons = [
                f"所属{perf_data.get('sectors', ['行业'])[0]}板块{perf_data.get('sector_change', '+0.00%')}%变化",
                f"大盘{perf_data.get('market_sentiment', '中性')}，行业共振",
            ]
            fall_analysis = {
                "fund_code": fund_code,
                "fund_name": fund_name,
                "direction": direction,
                "change_ratio": today_change,
                "reasons": reasons,
                "outlook": "短期观察市场情绪变化",
                "summary": f"基金今日{direction}，主要受板块和大盘影响",
                "perf_data": perf_data,
            }

        return {"fall_analysis": fall_analysis}

    except Exception as e:
        logger.error("[Analysis Agent] 分析失败: %s", e, exc_info=True)
        return {"error": f"分析失败: {e}", "fall_analysis": None}
