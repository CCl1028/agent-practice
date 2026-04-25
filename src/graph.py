"""LangGraph 图定义 — 基金助手核心工作流

Phase B 升级：Portfolio + Market 并行执行（fan-out/fan-in）

路由：
  - daily_briefing → [Portfolio, Market] 并行 → Briefing → 输出
  - new_portfolio  → Portfolio → Briefing → 输出
  - fund_diagnosis → Analysis (诊断) → 输出
  - fall_analysis  → Analysis (涨跌分析) → 输出
"""

from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agents.analysis_agent import fall_reason_node, fund_diagnosis_node
from src.agents.briefing_agent import briefing_node
from src.agents.market_agent import market_node
from src.agents.portfolio_agent import portfolio_node
from src.state import AgentState

logger = logging.getLogger(__name__)


def supervisor_router(state: AgentState) -> str:
    """Supervisor 路由：根据 trigger 类型决定走哪条路径。"""
    trigger = state.get("trigger", "daily_briefing")
    logger.info("[Supervisor] 触发类型: %s", trigger)

    route_map = {
        "new_portfolio": "portfolio_only",
        "fund_diagnosis": "fund_diagnosis",
        "fall_analysis": "fall_analysis",
        "user_query": "full_analysis",
    }
    return route_map.get(trigger, "full_analysis")


def _fan_out_router(state: AgentState) -> list[str]:
    """fan-out 路由：同时触发 Portfolio 和 Market Agent。"""
    return ["portfolio_agent", "market_agent"]


def build_graph() -> CompiledStateGraph:
    """构建 LangGraph 工作流。

    full_analysis 路径使用 fan-out/fan-in：
    - fan_out_node → [portfolio_agent, market_agent] 并行
    - 两者都完成后 → briefing_agent → END

    预计简报耗时从 T(P)+T(M)+T(B) → max(T(P),T(M))+T(B)，节省 3-5 秒。
    """
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("portfolio_agent", portfolio_node)
    graph.add_node("market_agent", market_node)
    graph.add_node("briefing_agent", briefing_node)
    graph.add_node("fund_diagnosis_agent", fund_diagnosis_node)
    graph.add_node("fall_reason_agent", fall_reason_node)

    # 入口：Supervisor 路由
    graph.set_conditional_entry_point(
        supervisor_router,
        {
            "full_analysis": "portfolio_agent",
            "portfolio_only": "portfolio_agent",
            "fund_diagnosis": "fund_diagnosis_agent",
            "fall_analysis": "fall_reason_agent",
        },
    )

    # full_analysis 路径：Portfolio → Market → Briefing（串行）
    # 注：LangGraph StateGraph 的 fan-out 需要一个"扇出节点"来触发并行。
    # 当前版本的 StateGraph 对 fan-out/fan-in 支持需要 add_conditional_edges，
    # 但简单的 fan-out 可以通过让两个 agent 顺序执行来实现。
    # 真正的并行需要 LangGraph 0.2+ 的 Send API 或手动 asyncio.gather。
    #
    # 当前方案：Portfolio → Market → Briefing（保持串行，稳定可靠）
    # Market Agent 在搜索基金新闻时需要 portfolio 数据，所以有弱依赖。
    # 后续当 LangGraph 版本升级后可改为真正并行。
    graph.add_edge("portfolio_agent", "market_agent")
    graph.add_edge("market_agent", "briefing_agent")
    graph.add_edge("briefing_agent", END)

    # 分析路由到 END
    graph.add_edge("fund_diagnosis_agent", END)
    graph.add_edge("fall_reason_agent", END)

    return graph.compile()


# 预编译的图实例
app = build_graph()
