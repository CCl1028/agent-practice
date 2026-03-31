"""LangGraph 图定义 — 基金助手核心工作流

Supervisor 路由：
  - daily_briefing → Portfolio + Market (并行) → Briefing → 输出
  - new_portfolio  → Portfolio → Briefing → 输出
  - user_query     → (后期迭代)
"""

from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from src.agents.briefing_agent import briefing_node
from src.agents.market_agent import market_node
from src.agents.portfolio_agent import portfolio_node
from src.state import AgentState

logger = logging.getLogger(__name__)


def supervisor_router(state: AgentState) -> str:
    """Supervisor 路由：根据 trigger 类型决定走哪条路径。"""
    trigger = state.get("trigger", "daily_briefing")
    logger.info("[Supervisor] 触发类型: %s", trigger)

    if trigger == "new_portfolio":
        return "portfolio_only"
    elif trigger == "user_query":
        # 后期迭代：解析用户意图，分流
        return "full_analysis"
    else:
        return "full_analysis"


def build_graph() -> StateGraph:
    """构建 LangGraph 工作流。"""

    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("portfolio_agent", portfolio_node)
    graph.add_node("market_agent", market_node)
    graph.add_node("briefing_agent", briefing_node)

    # 入口：Supervisor 路由
    graph.set_conditional_entry_point(
        supervisor_router,
        {
            "full_analysis": "portfolio_agent",
            "portfolio_only": "portfolio_agent",
        },
    )

    # full_analysis: portfolio → market (通过 briefing 节点等待两者)
    # 由于 LangGraph 的 StateGraph 不直接支持 fan-out/fan-in，
    # 我们用顺序执行模拟：portfolio → market → briefing
    # 后续可升级为真正的并行执行
    graph.add_edge("portfolio_agent", "market_agent")
    graph.add_edge("market_agent", "briefing_agent")
    graph.add_edge("briefing_agent", END)

    return graph.compile()


# 预编译的图实例
app = build_graph()
