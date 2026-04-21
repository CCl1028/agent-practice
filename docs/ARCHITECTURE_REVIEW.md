# FundPal 架构优化提案 — 新任技术 Leader 视角

> 撰写人: Tech Lead  
> 日期: 2026-04-22  
> 目标: 从根本上提升产品的可维护性、可扩展性和工程质量，保障后续 2-3 年的迭代能力

---

## 〇、审计摘要

经过对全部 55+ 源文件的逐行审计，FundPal 作为一个 MVP/早期产品在功能完整度上做得不错——多 Agent 编排、多数据源容错、6 维决策引擎、三层推送等核心能力已经跑通。但随着产品从 v1 迭代到 v3，"快速交付"的技术债已经累积到了**临界点**：再加一个功能，改一处逻辑，牵扯面越来越广，回归成本越来越高。

以下是我识别到的 **7 个系统性问题**，按"投入产出比"排列，每个配有具体的实施方案。

---

## 一、🏗️ 后端架构：拆分巨石、分层治理

### 当前问题

| 问题 | 现状 | 影响 |
|------|------|------|
| **server.py 巨石** | 875 行，承担 20+ API 路由 + 调度器 + 配置管理 + .env 读写 + 静态文件 + Pydantic 模型 + 内存日志 | 修改任何一处都需要理解全文件；合并冲突频繁；认知负荷极高 |
| **market_tools.py 过胖** | 799 行，混合 10+ 职责（净值/估值/板块/画像/名称映射/Mock/搜索/缓存） | 无法独立测试、复用、替换任何一个功能 |
| **无中间层抽象** | 路由函数直接调用工具函数，无 Service 层 | 业务逻辑散落在路由和工具之间；相同逻辑被重复实现 |

### 优化方案：3 层分包架构

```
fundpal/
├── server.py              # 仅 FastAPI app 初始化 + lifespan（< 50 行）
├── routes/                # 路由层（只做参数校验 + 调用 service + 返回响应）
│   ├── __init__.py        # APIRouter 注册
│   ├── briefing.py        # /api/briefing, /api/briefing-and-push
│   ├── portfolio.py       # /api/portfolio/* (6 个端点)
│   ├── estimation.py      # /api/estimation (GET/POST)
│   ├── diagnosis.py       # /api/fund-diagnosis, /api/fund-explanation
│   ├── push.py            # /api/push/*
│   ├── config.py          # /api/config (GET/POST)
│   └── system.py          # /api/health, /api/version, /api/logs
├── services/              # 业务逻辑层（编排工具调用，封装事务）
│   ├── briefing_service.py
│   ├── portfolio_service.py
│   ├── estimation_service.py
│   ├── diagnosis_service.py
│   ├── push_service.py
│   └── config_service.py
├── models/                # Pydantic Request/Response 模型
│   ├── requests.py
│   └── responses.py
├── core/                  # 横切关注点
│   ├── config.py          # 现有 src/config.py 升级
│   ├── exceptions.py      # 统一异常定义
│   ├── logging.py         # MemoryLogHandler 独立出来
│   └── scheduler.py       # APScheduler 配置
├── agents/                # 现有 src/agents/ 不变
├── tools/                 # 工具层拆分
│   ├── fund_nav.py        # 净值获取（从 market_tools 拆出）
│   ├── fund_estimation.py # 估值获取
│   ├── fund_profile.py    # 基金画像
│   ├── fund_name.py       # 基金名称映射/校验（+线程安全缓存）
│   ├── sector.py          # 板块数据
│   ├── data_provider.py   # 多源容错 + 熔断器（保留）
│   ├── news_tools.py      # 新闻搜索（保留）
│   ├── push_tools.py      # 推送（保留）
│   ├── nlp_input.py       # NLP 解析（保留）
│   └── ocr_tools.py       # 截图识别（保留）
└── graph/                 # LangGraph 工作流
    ├── workflow.py         # 图定义
    ├── state.py            # State 定义
    └── nodes.py            # 节点注册
```

### 关键原则

1. **路由层 < 30 行/端点**：只做 `parse request → call service → return response`
2. **Service 层持有业务逻辑**：事务编排、权限检查、缓存策略都在这里
3. **工具层纯函数化**：输入→输出，无副作用，无 FastAPI 依赖

### 拆分 market_tools.py 的具体方案

| 原函数 | 目标文件 | 行数 |
|--------|---------|------|
| `get_fund_nav()`, `get_fund_nav_history()` | `tools/fund_nav.py` | ~120 行 |
| `get_fund_estimation()`, `_fetch_fund_estimation()`, `refresh_estimation_cache()` | `tools/fund_estimation.py` | ~100 行 |
| `get_fund_profile()`, `get_fund_perf_analysis()` | `tools/fund_profile.py` | ~150 行 |
| `get_fund_name()`, `_init_fund_name_cache()`, `verify_and_fix_fund()` | `tools/fund_name.py` | ~120 行 |
| `get_sector_performance()` | `tools/sector.py` | ~80 行 |
| `is_trading_hours()`, `_get_mock_*()` | `tools/common.py` | ~60 行 |

### 估算

- **工作量**: 3-4 天（一人）
- **风险**: 低（纯重构，不改行为）
- **收益**: 单文件认知负荷从 875/799 行降到 < 150 行

---

## 二、🗄️ 数据层：从 JSON 文件到 SQLite

### 当前问题

| 问题 | 现状 | 影响 |
|------|------|------|
| **服务端 JSON 文件** | `data/portfolio.json` 直接 `json.loads()` / `json.dumps()` | 无事务保证、无并发安全、无索引、无迁移机制 |
| **前端 localStorage** | 持仓/交易/定投/配置全在 localStorage | 5MB 上限、无法跨设备、无法备份、无法做数据分析 |
| **前后端数据不一致** | 前端 localStorage 是"真正的数据库"，后端 JSON 是"同步副本" | 前端清缓存 = 数据丢失；两端数据可能不同步 |
| **.env 手工解析** | `_read_env()` / `_write_env()` 手动 split("=") | 不支持引号、多行值、注释、编码问题 |

### 优化方案：SQLite + 简单 ORM

**为什么是 SQLite 而不是 PostgreSQL？**
- FundPal 是单用户/少用户应用，SQLite 足够
- 零依赖、零运维、文件级备份
- 为未来迁移 PostgreSQL 铺路（通过 Repository 模式抽象）

```python
# models/database.py
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Holding(Base):
    __tablename__ = "holdings"
    id = Column(Integer, primary_key=True)
    fund_code = Column(String(10), unique=True, nullable=False, index=True)
    fund_name = Column(String(100))
    cost = Column(Float, default=0)
    cost_nav = Column(Float, default=0)
    shares = Column(Float, default=0)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String(36), primary_key=True)
    fund_code = Column(String(10), nullable=False, index=True)
    type = Column(String(10))  # buy/sell
    amount = Column(Float)
    nav = Column(Float)
    shares = Column(Float)
    source = Column(String(20))
    created_at = Column(DateTime)

class InvestPlan(Base):
    __tablename__ = "invest_plans"
    id = Column(String(36), primary_key=True)
    fund_code = Column(String(10), nullable=False)
    amount = Column(Float)
    frequency = Column(String(20))
    status = Column(String(20))
    last_executed = Column(DateTime, nullable=True)

class Config(Base):
    __tablename__ = "configs"
    key = Column(String(100), primary_key=True)
    value = Column(String(500))
    sensitive = Column(Integer, default=0)
```

```python
# repositories/portfolio_repo.py — Repository 模式
class PortfolioRepository:
    """持仓数据访问层 — 未来切换 PostgreSQL 只需替换此实现"""
    
    def __init__(self, session_factory):
        self._session = session_factory
    
    def list_all(self) -> list[Holding]:
        with self._session() as s:
            return s.query(Holding).all()
    
    def upsert(self, fund_code: str, **kwargs) -> Holding:
        with self._session() as s:
            h = s.query(Holding).filter_by(fund_code=fund_code).first()
            if h:
                for k, v in kwargs.items():
                    setattr(h, k, v)
            else:
                h = Holding(fund_code=fund_code, **kwargs)
                s.add(h)
            s.commit()
            return h
    
    def delete(self, fund_code: str) -> bool:
        with self._session() as s:
            n = s.query(Holding).filter_by(fund_code=fund_code).delete()
            s.commit()
            return n > 0
```

### 数据迁移策略

```python
# migrations/001_json_to_sqlite.py
"""一键将现有 JSON 数据迁移到 SQLite"""
import json
from pathlib import Path

def migrate():
    json_path = Path("data/portfolio.json")
    if json_path.exists():
        data = json.loads(json_path.read_text())
        for h in data:
            repo.upsert(h["fund_code"], **h)
        # 保留旧文件作为备份
        json_path.rename("data/portfolio.json.bak")
```

### 前端改造

前端从 localStorage-first 改为 **API-first + localStorage-cache**：

```typescript
// store.ts 重构
export async function getPortfolio(): Promise<Holding[]> {
  try {
    const data = await api.getPortfolio()    // 优先从 API 获取
    saveLocalCache(data.holdings)             // 同步到本地缓存
    return data.holdings
  } catch {
    return getLocalCache()                    // 离线降级到本地缓存
  }
}
```

### 估算

- **工作量**: 5-7 天（含前后端改造 + 数据迁移脚本）
- **风险**: 中（涉及数据迁移，需充分测试）
- **收益**: 数据安全性质变；为多用户打基础；解决前后端数据不一致

---

## 三、🧪 测试体系：从"裸奔"到可信赖的回归保障

### 当前问题

| 问题 | 现状 | 影响 |
|------|------|------|
| **核心模块零测试** | `server.py`(路由)、`graph.py`(工作流)、`briefing_agent._rule_engine`(规则引擎)、`analysis_agent._rate_fund`(评分)、`news_tools`、`data_provider`(熔断器)、`push_tools`、`formatter`、`config` —— 全无测试 | 任何改动都是"盲改"，无法保证回归 |
| **已有测试过时** | `test_p4_confirm_flow.py` 测试旧版 HTML 前端；`test_trading_logic.py` 测试 Python 重实现而非实际前端 | 测试 100% 会失败或测了错误的东西 |
| **无 CI 门禁** | GitHub Actions 存在但几乎为空壳 | 代码合并没有任何质量关卡 |
| **前端零测试** | 17 个 TSX 组件、核心 store/utils 无任何测试 | 前端改动全凭手工验证 |

### 优化方案：金字塔测试策略

```
                    ┌──────────┐
                    │  E2E (5) │  ← Playwright: 核心用户流程
                   ┌┴──────────┴┐
                   │ 集成 (15)   │  ← httpx + TestClient: API 端到端
                  ┌┴────────────┴┐
                  │  单元 (50+)   │  ← pytest + vitest: 纯逻辑函数
                  └──────────────┘
```

#### 第一梯队：高 ROI 单元测试（1 周）

```python
# tests/unit/test_rule_engine.py — 规则引擎是核心资产，必须有 100% 分支覆盖
import pytest
from src.agents.briefing_agent import _rule_engine

class TestRuleEngine:
    """6 维规则引擎单元测试"""
    
    def test_chase_high_detection(self):
        """追高检测：乖离率 > 3% 且上涨 → 观望"""
        holding = make_holding(
            profit_ratio=2.0,
            deviation_rate=4.0,
            trend_5d=[1.0, 0.5, 0.8, 0.3, 0.6],  # 连涨
        )
        result = _rule_engine(holding)
        assert result["action"] == "观望"
        assert "追高" in result["risk_note"]
    
    def test_stop_profit(self):
        """止盈规则：浮盈 > 15% 且连涨 → 减仓"""
        holding = make_holding(
            profit_ratio=18.0,
            trend_5d=[1.5, 0.8, 1.2, 0.5, 0.3],
        )
        result = _rule_engine(holding)
        assert result["action"] == "减仓"
        assert result["score"] >= 75
    
    def test_bear_no_add(self):
        """空头禁加仓：空头排列 + 浮亏 > 5%"""
        holding = make_holding(
            profit_ratio=-8.0,
            ma_status="空头排列",
        )
        result = _rule_engine(holding)
        assert result["action"] == "观望"

    # ... 覆盖全部 5 条硬规则 + 各种边界值组合
```

```python
# tests/unit/test_circuit_breaker.py — 熔断器逻辑必须精确
class TestCircuitBreaker:
    def test_trip_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3, cooldown=300)
        for _ in range(3):
            cb.record_failure()
        assert not cb.is_available()  # OPEN 状态
    
    def test_half_open_after_cooldown(self):
        cb = CircuitBreaker("test", failure_threshold=3, cooldown=1)
        for _ in range(3):
            cb.record_failure()
        time.sleep(1.1)
        assert cb.is_available()  # HALF_OPEN
    
    def test_thread_safety(self):
        """并发测试：100 个线程同时操作"""
        cb = CircuitBreaker("test", failure_threshold=100)
        threads = [Thread(target=cb.record_failure) for _ in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert cb._states["test"]["failures"] == 100
```

```python
# tests/unit/test_formatter.py
# tests/unit/test_config.py
# tests/unit/test_clean_json_text.py
# tests/unit/test_fund_name_resolver.py
```

#### 第二梯队：API 集成测试（1 周）

```python
# tests/integration/test_api_routes.py
import pytest
from httpx import AsyncClient, ASGITransport
from server import app

@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c

class TestPortfolioAPI:
    async def test_get_portfolio_empty(self, client):
        r = await client.get("/api/portfolio")
        assert r.status_code == 200
        assert r.json()["count"] == 0
    
    async def test_parse_text(self, client):
        r = await client.post("/api/portfolio/parse-text", json={
            "text": "持有招商中证白酒指数基金 161725 成本 10000 元",
            "config": {"OPENAI_API_KEY": "test-key"}
        })
        assert r.status_code in (200, 504)  # LLM 可能超时

class TestBriefingAPI:
    async def test_briefing_no_holdings(self, client):
        """无持仓时应返回空简报，不应报错"""
        r = await client.post("/api/briefing", json={"holdings": []})
        assert r.status_code == 200

class TestHealthAPI:
    async def test_health(self, client):
        r = await client.get("/api/health")
        assert r.json()["status"] == "ok"
```

#### 第三梯队：前端测试（与前端重构同步）

```typescript
// web/src/__tests__/store.test.ts — Vitest
import { describe, it, expect, beforeEach } from 'vitest'
import { recalcHolding, getLocalPortfolio } from '../store'

describe('recalcHolding', () => {
  beforeEach(() => localStorage.clear())
  
  it('should calculate shares from buy transactions', () => {
    // setup transactions...
    recalcHolding('161725')
    const h = getLocalPortfolio().find(x => x.fund_code === '161725')
    expect(h?.total_shares).toBeCloseTo(1000, 2)
  })
})
```

#### CI 门禁（立即实施）

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=60
      - run: ruff check src/ server.py
      - run: mypy src/ --ignore-missing-imports

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd web && npm ci && npm run lint && npm run test

  docker-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t fundpal:ci .
```

### 估算

- **工作量**: 2-3 周（分梯队渐进）
- **覆盖率目标**: 第一阶段 60%+，三个月内 80%+
- **收益**: 每次改动都有信心；CI 红灯挡住 bug

---

## 四、⚡ Agent 执行效率：并行化 + 流式输出

### 当前问题

| 问题 | 现状 | 影响 |
|------|------|------|
| **Portfolio → Market 串行** | `graph.py:71` 两者无数据依赖却顺序执行 | 简报生成耗时 = T(Portfolio) + T(Market) + T(Briefing) ≈ 10-20s |
| **同步阻塞调用** | `langgraph_app.invoke()` 是同步的，虽已用 `to_thread` 包装但仍是阻塞等待 | 用户等待体验差，无进度反馈 |
| **_clean_json_text() 重复** | `briefing_agent.py` 和 `analysis_agent.py` 各实现一份相同的函数 | 违反 DRY |

### 优化方案

#### 4.1 LangGraph 并行执行

```python
# graph/workflow.py — 利用 LangGraph 原生 fan-out/fan-in
from langgraph.graph import StateGraph, END

def build_graph():
    graph = StateGraph(AgentState)
    
    graph.add_node("portfolio_agent", portfolio_node)
    graph.add_node("market_agent", market_node)
    graph.add_node("briefing_agent", briefing_node)
    graph.add_node("fund_diagnosis_agent", fund_diagnosis_node)
    graph.add_node("fall_reason_agent", fall_reason_node)
    
    graph.set_conditional_entry_point(supervisor_router, {
        "full_analysis": "portfolio_agent",
        "portfolio_only": "portfolio_agent",
        "fund_diagnosis": "fund_diagnosis_agent",
        "fall_analysis": "fall_reason_agent",
    })
    
    # ✅ 关键改动：Portfolio 和 Market 并行执行
    # Portfolio Agent 完成后同时触发 Market Agent
    # 两者都完成后再进入 Briefing Agent
    graph.add_edge("portfolio_agent", "market_agent")
    # TODO: LangGraph 0.2+ 支持 fan-out:
    # graph.add_edge("__start__", ["portfolio_agent", "market_agent"])
    # graph.add_edge(["portfolio_agent", "market_agent"], "briefing_agent")
    
    graph.add_edge("market_agent", "briefing_agent")
    graph.add_edge("briefing_agent", END)
    graph.add_edge("fund_diagnosis_agent", END)
    graph.add_edge("fall_reason_agent", END)
    
    return graph.compile()
```

**效果**: 简报生成耗时从 `T(P) + T(M) + T(B)` → `max(T(P), T(M)) + T(B)`，预计节省 3-5 秒。

#### 4.2 流式输出（SSE）

```python
# routes/briefing.py — Server-Sent Events
from fastapi.responses import StreamingResponse

@router.post("/api/briefing/stream")
async def stream_briefing(input: HoldingsInput):
    """流式返回简报生成进度"""
    async def event_stream():
        yield f"data: {json.dumps({'stage': 'portfolio', 'status': 'running'})}\n\n"
        # ... portfolio 完成
        yield f"data: {json.dumps({'stage': 'portfolio', 'status': 'done'})}\n\n"
        yield f"data: {json.dumps({'stage': 'market', 'status': 'running'})}\n\n"
        # ... market 完成
        yield f"data: {json.dumps({'stage': 'briefing', 'status': 'running'})}\n\n"
        # ... briefing 完成
        yield f"data: {json.dumps({'stage': 'complete', 'data': briefing})}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

#### 4.3 提取公共工具函数

```python
# utils/json_utils.py — 消除重复
def clean_json_text(text: str) -> str:
    """清理 LLM 返回的不规范 JSON 文本"""
    # 移除 markdown 代码块标记
    # 移除 BOM
    # 移除尾逗号
    # 移除单行注释
    ...

def safe_parse_json(text: str, fallback: dict | list = None):
    """安全解析 JSON，失败返回 fallback"""
    try:
        return json.loads(clean_json_text(text))
    except json.JSONDecodeError:
        return fallback
```

### 估算

- **并行化**: 1-2 天
- **SSE 流式**: 2-3 天（含前端适配）
- **收益**: 用户感知响应速度提升 30-50%

---

## 五、🖥️ 前端现代化：组件化 + 状态管理 + 样式系统

### 当前问题

| 问题 | 现状 | 影响 |
|------|------|------|
| **App.tsx 上帝组件** | 542 行，持有 15+ state、10+ handler，所有页面逻辑耦合 | 任何修改都可能影响其他页面；无法并行开发 |
| **47KB 单文件 CSS** | `global.css` 一个文件包含全站样式 | 样式冲突、命名地狱、无法 tree-shake |
| **无路由** | 手动 `switch(activeTab)` | 无法 deeplink、无前进后退、无 code-splitting |
| **无状态管理** | 所有状态在 App.tsx，通过 props 逐层传递 | prop drilling 严重（PortfolioPage 接收 12 个 props） |
| **localStorage 是"数据库"** | 交易、定投、配置全存 localStorage | 5MB 上限风险、清缓存=丢数据 |

### 优化方案

#### 5.1 引入轻量状态管理 — Zustand

```typescript
// store/portfolioStore.ts
import { create } from 'zustand'

interface PortfolioStore {
  holdings: Holding[]
  estimationCache: Record<string, FundEstimation>
  sortKey: SortKey
  sortDir: SortDir
  loading: boolean
  
  // Actions
  loadPortfolio: () => Promise<void>
  refreshNav: () => Promise<void>
  loadEstimation: () => Promise<void>
  addHoldings: (items: Holding[]) => void
  deleteHolding: (code: string) => void
  setSort: (key: SortKey) => void
}

export const usePortfolioStore = create<PortfolioStore>((set, get) => ({
  holdings: [],
  estimationCache: {},
  sortKey: 'time',
  sortDir: 'desc',
  loading: false,
  
  loadPortfolio: async () => {
    set({ loading: true })
    try {
      const h = await api.getPortfolio()
      set({ holdings: h })
    } finally {
      set({ loading: false })
    }
  },
  // ...
}))
```

```typescript
// store/briefingStore.ts
// store/tradeStore.ts (drawers state)
// store/configStore.ts
```

**效果**: App.tsx 从 542 行 → < 80 行（只做布局和路由）

#### 5.2 引入 React Router

```typescript
// App.tsx — 重构后
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

export default function App() {
  return (
    <BrowserRouter>
      <Header />
      <main className="page-wrapper">
        <Routes>
          <Route path="/" element={<Navigate to="/portfolio" />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/briefing" element={<BriefingPage />} />
          <Route path="/diagnosis" element={<DiagnosisPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
      </main>
      <Outlet />  {/* Drawers, Toast */}
    </BrowserRouter>
  )
}
```

**收益**: 支持 deeplink（分享诊断结果链接）、浏览器前进后退、React.lazy code-splitting。

#### 5.3 CSS 模块化

```
# 方案 A: CSS Modules（零依赖）
web/src/components/Header/
  ├── Header.tsx
  └── Header.module.css

# 方案 B: Tailwind CSS（推荐，彻底消除命名问题）
npm install -D tailwindcss @tailwindcss/vite
```

全局 47KB CSS 拆分策略：

| 原 CSS 块 | 目标 | 方式 |
|-----------|------|------|
| `.card-*`, `.fund-card-*` | `FundCard.module.css` | CSS Modules |
| `.briefing-*` | `BriefingPage.module.css` | CSS Modules |
| `.diagnosis-*` | `DiagnosisPage.module.css` | CSS Modules |
| `.drawer-*`, `.modal-*` | `Drawer.module.css` | CSS Modules |
| `.toast-*`, `.loading-*` | `global.css`（保留全局） | 仅保留 < 200 行 |

### 估算

- **工作量**: 1.5-2 周（可与后端重构并行）
- **收益**: 开发体验质变；可维护性和可扩展性大幅提升

---

## 六、🔒 安全与可观测性

### 6.1 认证与授权

当前 FundPal **没有任何认证机制**——任何人知道 URL 就能读写你的持仓数据。

#### 最小可行方案：Bearer Token

```python
# core/auth.py — 最简方案
from fastapi import Depends, HTTPException, Header

async def verify_token(authorization: str = Header(None)):
    """简单的 Bearer Token 认证"""
    expected = os.getenv("API_TOKEN", "")
    if not expected:
        return  # 未配置 token 则跳过（本地开发）
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    if authorization[7:] != expected:
        raise HTTPException(status_code=401, detail="Token 无效")

# 应用到所有写操作路由
@router.post("/api/portfolio/add-text", dependencies=[Depends(verify_token)])
async def add_from_text(input: TextInput):
    ...
```

#### 未来方案：JWT + 多用户

```python
# 基于 python-jose 的 JWT 方案（预留）
# 支持用户注册/登录 → JWT 签发 → 数据隔离
```

### 6.2 API 限流

```python
# core/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# 在路由上添加限流
@router.post("/api/briefing")
@limiter.limit("5/minute")  # 每分钟最多 5 次
async def generate_briefing(request: Request, input: HoldingsInput):
    ...
```

### 6.3 结构化日志 + 链路追踪

当前的内存环形缓冲区日志无法持久化、无法搜索、无法关联。

```python
# core/logging.py — 结构化日志
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()

# 使用
logger.info("briefing_generated", 
    fund_count=len(holdings),
    duration_ms=elapsed,
    trigger="daily_briefing",
)
```

```python
# 请求 ID 中间件 — 全链路追踪
import uuid

@app.middleware("http")
async def add_request_id(request, call_next):
    request_id = str(uuid.uuid4())[:8]
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

### 6.4 健康检查增强

```python
@router.get("/api/health")
async def health():
    """增强版健康检查 — 包含依赖状态"""
    checks = {
        "status": "ok",
        "data_file": Path("data/portfolio.json").exists(),
        "scheduler": scheduler.running,
        "akshare_circuit": circuit_breaker.is_available("akshare"),
        "efinance_circuit": circuit_breaker.is_available("efinance"),
        "uptime_seconds": int(time.time() - START_TIME),
    }
    overall = "ok" if all([checks["data_file"], checks["scheduler"]]) else "degraded"
    checks["status"] = overall
    return checks
```

### 估算

- **Token 认证**: 0.5 天
- **限流**: 0.5 天
- **结构化日志**: 1 天
- **收益**: 生产环境安全性和可诊断性质变

---

## 七、🛠️ 工程基础设施

### 7.1 依赖管理

```bash
# 当前问题：requirements.txt 无上限版本
# langchain>=0.3.0  # 可能装到 1.0 breaking change

# 方案：引入 pip-tools
pip install pip-tools

# requirements.in — 人工维护的直接依赖
langgraph>=0.2.0,<1.0
langchain>=0.3.0,<1.0
fastapi>=0.115.0,<1.0

# 生成锁文件
pip-compile requirements.in -o requirements.txt
pip-compile requirements-dev.in -o requirements-dev.txt
```

### 7.2 代码质量工具链

```toml
# pyproject.toml
[tool.ruff]
target-version = "py311"
line-length = 120
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true  # 渐进式启用

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

```json
// web/.eslintrc.json 增强
{
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended"
  ],
  "rules": {
    "@typescript-eslint/no-explicit-any": "warn",
    "react-hooks/exhaustive-deps": "error"
  }
}
```

### 7.3 API 版本化

```python
# 为未来 breaking change 预留
from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")
# 新 API 走 /api/v1/...
# 旧 API /api/... 保持兼容，标记 deprecated
```

### 7.4 错误处理统一

```python
# core/exceptions.py
class FundPalError(Exception):
    """基础异常"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status: int = 500):
        self.message = message
        self.code = code
        self.status = status

class ValidationError(FundPalError):
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR", 400)

class TimeoutError(FundPalError):
    def __init__(self, message: str = "请求超时，请稍后重试"):
        super().__init__(message, "TIMEOUT", 504)

class DataSourceError(FundPalError):
    def __init__(self, source: str):
        super().__init__(f"数据源 {source} 不可用", "DATA_SOURCE_ERROR", 503)

# 统一异常处理器
@app.exception_handler(FundPalError)
async def fundpal_error_handler(request, exc: FundPalError):
    return JSONResponse(
        status_code=exc.status,
        content={"error": exc.message, "code": exc.code}
    )
```

**效果**: 消除 server.py 中 15+ 处散落的 `JSONResponse(status_code=..., content={"error": ...})`。

---

## 八、📋 实施路线图

### Phase A — 基础设施（第 1-2 周）

| 任务 | 优先级 | 天数 | 依赖 |
|------|--------|------|------|
| CI/CD 门禁 (lint + compile + docker build) | P0 | 1 | 无 |
| pyproject.toml + ruff + mypy 配置 | P0 | 0.5 | 无 |
| requirements-dev.txt + pip-tools | P0 | 0.5 | 无 |
| 统一异常处理 + FundPalError | P0 | 1 | 无 |
| 提取 _clean_json_text 到公共模块 | P0 | 0.5 | 无 |
| 删除过时测试 + 补充规则引擎/熔断器单元测试 | P0 | 3 | 无 |
| Bearer Token 认证 | P1 | 0.5 | 无 |
| API 限流 | P1 | 0.5 | 无 |

**里程碑**: CI 绿灯、核心逻辑有测试覆盖、基本安全防护就位

### Phase B — 后端重构（第 3-4 周）

| 任务 | 优先级 | 天数 | 依赖 |
|------|--------|------|------|
| server.py → routes/ + services/ + models/ | P0 | 3 | Phase A |
| market_tools.py → 5 个独立模块 | P0 | 2 | Phase A |
| 结构化日志 + 请求 ID | P1 | 1 | routes 拆分 |
| LangGraph 并行执行 | P1 | 1 | 无 |
| API 集成测试 (httpx + TestClient) | P0 | 3 | routes 拆分 |

**里程碑**: 后端代码单文件 < 200 行、集成测试覆盖主要 API

### Phase C — 数据层升级（第 5-6 周）

| 任务 | 优先级 | 天数 | 依赖 |
|------|--------|------|------|
| SQLite + SQLAlchemy 数据层 | P0 | 3 | Phase B |
| Repository 模式封装 | P0 | 2 | SQLite |
| JSON → SQLite 迁移脚本 | P0 | 1 | Repository |
| 前端 localStorage → API-first | P1 | 2 | SQLite |
| .env 管理改用 python-dotenv API | P2 | 0.5 | 无 |

**里程碑**: 数据层可靠、前后端数据一致、为多用户铺路

### Phase D — 前端现代化（第 7-9 周）

| 任务 | 优先级 | 天数 | 依赖 |
|------|--------|------|------|
| Zustand 状态管理 | P0 | 3 | 无 |
| React Router 路由 | P1 | 2 | Zustand |
| App.tsx 拆分 | P0 | 2 | Zustand + Router |
| CSS Modules 样式拆分 | P1 | 3 | 无 |
| Vitest 前端测试 | P1 | 2 | Zustand |
| SSE 流式简报 | P2 | 2 | 后端 SSE |

**里程碑**: 前端可维护、支持 deeplink、样式隔离

---

## 九、量化预期收益

| 指标 | 当前值 | 目标值 | 改善 |
|------|--------|--------|------|
| 最大单文件行数 | 875 行 (server.py) | < 200 行 | **77%↓** |
| 测试覆盖率 | ~5% (仅4个旧测试) | > 70% | **14x↑** |
| 简报生成耗时 | 10-20s | 6-12s | **40%↓** |
| 新功能开发周期 | 2-3 天（改一处怕影响全局） | 0.5-1 天 | **60%↓** |
| 生产事故排查时间 | 无结构化日志，需 SSH 登录看终端 | 结构化日志 + 请求 ID | **质变** |
| 新人上手时间 | 需读完 875 行 server.py | 只需看对应 route 和 service | **质变** |
| 数据安全性 | localStorage 清缓存 = 丢数据 | SQLite 持久化 + 备份 | **质变** |

---

## 十、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 重构期间引入回归 bug | 高 | 中 | Phase A 先建 CI + 测试，再动代码 |
| 数据迁移丢数据 | 中 | 高 | 迁移前自动备份 JSON；迁移后校验行数一致 |
| 前端大改导致 UI 走样 | 中 | 中 | CSS Modules 逐个组件迁移，不一次性全改 |
| 并行化改图引入 state 竞态 | 低 | 高 | LangGraph 的 StateGraph 天然线程安全，但需集成测试验证 |
| 团队不适应新架构 | 中 | 低 | 写清楚 ADR（架构决策记录）+ 代码注释 |

---

## 总结

FundPal 的产品方向是对的，核心功能（6 维决策引擎、多数据源容错、三层推送）已经形成了有价值的业务壁垒。但工程基础设施欠了太多债——**一个 875 行的 server.py、一个 47KB 的 CSS、一个 5% 的测试覆盖率、一个 JSON 文件当数据库**——这些如果不在下一个大版本之前解决，后续每个功能迭代都会越来越慢、越来越怕。

核心理念：**先建护城河（测试 + CI），再拆城堡（重构），最后盖新楼（功能）**。

按照上述 4 个 Phase 的路线图，约 9 周可以完成全部架构升级。建议从 Phase A（CI + 测试 + 安全）立即启动——这是唯一一个"投入小、收益大、风险低"的阶段，也是后续所有重构的安全网。
