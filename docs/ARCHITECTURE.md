# FundPal — 产品架构说明

> 维护人: FundPal Team  
> 最后更新: 2026-04-22  
> 当前版本: v1.2.0

---

## 一、架构全景

### 1.1 系统全景图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              用户入口层                                  │
│                                                                         │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐              │
│   │  React SPA   │   │  CLI 命令行   │   │  定时触发    │              │
│   │  (web/dist)  │   │  (main.py)   │   │ (APScheduler)│              │
│   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘              │
└──────────┼──────────────────┼──────────────────┼───────────────────────┘
           │                  │                  │
┌──────────▼──────────────────▼──────────────────▼───────────────────────┐
│                          FastAPI API 层                                  │
│                         (server.py, 20+ 端点)                           │
│                                                                         │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │  中间件: CORS · 内存日志 · 配置管理 · 静态文件 · SPA Fallback    │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │
│   │  简报路由  │  │  持仓路由  │  │  分析路由  │  │  系统路由      │  │
│   │/api/briefing│  │/api/portfolio│ │/api/fund-* │  │/api/config,log│  │
│   └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └────────────────┘  │
└─────────┼───────────────┼───────────────┼──────────────────────────────┘
          │               │               │
┌─────────▼───────────────▼───────────────▼──────────────────────────────┐
│                    LangGraph 工作流编排层                                │
│                      (src/graph.py)                                     │
│                                                                         │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │                  Supervisor Router                                │  │
│   │  ┌────────────────────────────────────────────────────────────┐  │  │
│   │  │ daily_briefing / user_query → full_analysis               │  │  │
│   │  │ new_portfolio              → portfolio_only               │  │  │
│   │  │ fund_diagnosis             → fund_diagnosis               │  │  │
│   │  │ fall_analysis              → fall_analysis                │  │  │
│   │  └────────────────────────────────────────────────────────────┘  │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                          │                                              │
│        ┌─────────────────┼────────────────────┐                        │
│        ▼                 ▼                    ▼                        │
│   ┌──────────┐    ┌──────────┐    ┌─────────────────┐                 │
│   │Portfolio │ →  │ Market   │ →  │   Briefing      │ → END           │
│   │ Agent    │    │  Agent   │    │    Agent        │                 │
│   │ 持仓管家  │    │ 市场观察员│    │   简报撰写员    │                 │
│   └──────────┘    └──────────┘    └─────────────────┘                 │
│                                                                        │
│   ┌────────────────────┐    ┌────────────────────┐                    │
│   │ fund_diagnosis     │    │ fall_reason         │                    │
│   │     Agent          │    │     Agent           │                    │
│   │   基金诊断          │    │  涨跌分析           │                    │
│   └────────┬───────────┘    └────────┬───────────┘                    │
│            └─── → END                └─── → END                       │
└────────────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────────────────┐
│                          工具层 (src/tools/)                            │
│                                                                         │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │
│   │ data_provider   │  │  market_tools   │  │   news_tools    │       │
│   │ 多源数据 + 熔断  │  │ 行情/估值/校验  │  │  4 引擎新闻搜索  │       │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘       │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │
│   │ portfolio_tools  │  │   push_tools   │  │    formatter    │       │
│   │ 持仓/技术指标    │  │  三渠道推送    │  │  三层格式化     │       │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘       │
│   ┌─────────────────┐  ┌─────────────────┐                            │
│   │   nlp_input     │  │   ocr_tools    │                            │
│   │ 自然语言解析     │  │  截图识别       │                            │
│   └─────────────────┘  └─────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────────────────┐
│                        外部服务层                                       │
│                                                                         │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│   │ AKShare  │  │ Efinance │  │ DeepSeek │  │  Qwen-VL │             │
│   │ (行情P0) │  │ (行情P1) │  │  (LLM)   │  │  (视觉)  │             │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘             │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│   │ Tavily   │  │ 博查搜索 │  │  Brave   │  │ SerpAPI  │             │
│   │(新闻搜索)│  │(新闻搜索)│  │(新闻搜索)│  │(新闻搜索)│             │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘             │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐                           │
│   │  Bark    │  │ Server酱 │  │  企微    │                           │
│   │(iOS推送) │  │(微信推送)│  │(群推送)  │                           │
│   └──────────┘  └──────────┘  └──────────┘                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 分层职责

| 层级 | 文件 | 职责 |
|------|------|------|
| 入口层 | `web/`, `main.py` | 用户交互入口，React SPA 和 CLI |
| API 层 | `server.py` | HTTP 路由、中间件、定时任务、配置管理 |
| 编排层 | `src/graph.py` | LangGraph DAG，Supervisor 条件路由 |
| Agent 层 | `src/agents/` | 业务逻辑、决策生成、数据处理 |
| 工具层 | `src/tools/` | 数据获取、外部 API 调用、格式化 |
| 存储层 | `data/`, localStorage | 持仓 JSON、前端本地存储 |
| 外部层 | AKShare, LLM, Push | 第三方服务依赖 |

---

## 二、Agent 协作架构

### 2.1 Agent 职责矩阵

| Agent | 输入 | 输出 | 核心逻辑 | 绑定工具 |
|-------|------|------|---------|---------|
| **Portfolio Agent** | holdings (前端/JSON) | portfolio (增强) | 加载持仓 → 刷新净值 → 计算指标 | data_provider, market_tools, portfolio_tools |
| **Market Agent** | portfolio | market | 板块涨跌 → 情绪判断 → 新闻搜索 | market_tools, news_tools |
| **Briefing Agent** | portfolio, market | briefing | 规则引擎 → LLM 润色 → 格式化 | LLM (ChatOpenAI) |
| **Diagnosis Agent** | query_fund_code/name | diagnosis | 基金画像 → 规则评估 → LLM 总结 | market_tools, LLM |
| **FallReason Agent** | query_fund_code/name | fall_analysis | 涨跌数据 → 归因分析 → LLM 总结 | market_tools, news_tools, LLM |

### 2.2 工作流路径

**路径 A — 每日简报 (full_analysis):**

```
                 ┌─────────────┐
    trigger ───→ │  Supervisor  │
                 └──────┬──────┘
                        │ full_analysis
                        ▼
                 ┌─────────────┐
                 │  Portfolio   │  加载持仓 → 刷新净值 → 计算 MA/波动率/乖离率
                 │    Agent     │  填充 state.portfolio
                 └──────┬──────┘
                        ▼
                 ┌─────────────┐
                 │   Market    │  获取板块 → 判断情绪 → 搜索新闻(最多5只基金)
                 │    Agent    │  填充 state.market
                 └──────┬──────┘
                        ▼
                 ┌─────────────┐
                 │  Briefing   │  6维规则引擎 → 交易纪律 → LLM润色 → 三层输出
                 │    Agent    │  填充 state.briefing
                 └──────┬──────┘
                        ▼
                      [END]
```

**路径 B — 基金诊断 (fund_diagnosis):**

```
    trigger ───→ Supervisor ───→ fund_diagnosis_agent ───→ [END]
                                        │
                         基金画像 + 近期表现 + 规则评估 + LLM 总结
```

**路径 C — 涨跌分析 (fall_analysis):**

```
    trigger ───→ Supervisor ───→ fall_reason_agent ───→ [END]
                                        │
                         涨跌数据 + 板块关联 + 新闻归因 + LLM 总结
```

### 2.3 State 流转

```
┌─────────────────┐     ┌─────────────────────────────┐
│ Initial State   │     │ After Portfolio Agent        │
│                 │     │                             │
│ trigger: "..."  │ ──→ │ portfolio: [                │
│ holdings: [...] │     │   {fund_code, current_nav,  │
│                 │     │    profit_ratio, ma5/10/20, │
│                 │     │    ma_status, deviation...} │
│                 │     │ ]                           │
└─────────────────┘     └──────────────┬──────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │ After Market Agent           │
                        │                             │
                        │ market: {                   │
                        │   sectors: [...],           │
                        │   market_sentiment: "...",  │
                        │   hot_news: [...],          │
                        │   fund_news: {code: [...]}  │
                        │ }                           │
                        └──────────────┬──────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │ After Briefing Agent (Final) │
                        │                             │
                        │ briefing: {                 │
                        │   summary: "...",           │
                        │   details: [{               │
                        │     action, score,          │
                        │     reason, risk_note       │
                        │   }],                       │
                        │   market_note: "...",       │
                        │   risk_alerts: [...]        │
                        │ }                           │
                        └─────────────────────────────┘
```

---

## 三、数据流架构

### 3.1 输入通道

```
┌───────────────────────────────────────────────────────────────────┐
│                         5 种输入方式                               │
│                                                                   │
│  ① Web UI 表单输入                                               │
│     用户手动填写 → 前端 store.ts → API                           │
│                                                                   │
│  ② CLI 命令行                                                    │
│     python main.py add --text/--screenshot                       │
│                                                                   │
│  ③ 截图识别 (Vision LLM → PaddleOCR → 空数组)                   │
│     基金App截图 → process_screenshot() → verify_and_fix_fund()   │
│                                                                   │
│  ④ 自然语言 (LLM 提取 + 意图识别)                                │
│     "我买了2万易方达" → parse_natural_language() → 结构化JSON    │
│                                                                   │
│  ⑤ JSON 文件 (data/portfolio.json)                               │
│     定时推送时直接读取 → load_portfolio()                         │
│                                                                   │
│  全部统一为 → list[FundHolding] → AgentState                     │
└───────────────────────────────────────────────────────────────────┘
```

### 3.2 输出通道

```
┌───────────────────────────────────────────────────────────────────┐
│                      三层递进输出                                  │
│                                                                   │
│  第1层: format_push_notification() → ~50字推送通知               │
│         📊 今日持仓：观望为主 ✅                                  │
│                                                                   │
│  第2层: format_briefing_card() → ~200字简报卡片                  │
│         ┌─────────────────────────────────┐                      │
│         │ 易方达蓝筹 👉 观望 ⏸️ (60分)    │                      │
│         │ 招商白酒   👉 减仓 🔴 (78分)    │                      │
│         └─────────────────────────────────┘                      │
│                                                                   │
│  第3层: format_full_report() → ~2000字完整报告                   │
│         每只基金详细分析 + 市场简评 + 风险警报                    │
│                                                                   │
│  分发渠道:                                                        │
│  ├── Bark      → iPhone 通知栏 (第1层)                           │
│  ├── Server酱  → 微信 Markdown (第2+3层)                         │
│  ├── 企业微信  → 群消息 (第2层)                                   │
│  ├── Web UI    → 前端展示 (全部3层)                               │
│  └── API JSON  → 编程调用 (raw briefing)                         │
└───────────────────────────────────────────────────────────────────┘
```

---

## 四、部署架构

### 4.1 容器架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    腾讯云轻量应用服务器                                │
│                    (2核2G, Ubuntu + Docker)                          │
│                                                                      │
│   ┌───────────────────────────────────────────────────────────────┐  │
│   │                    Docker Compose 网络                         │  │
│   │                                                               │  │
│   │   ┌─────────────────────────────────┐                        │  │
│   │   │          nginx 容器              │  端口: 80, 443 (对外)  │  │
│   │   │    HTTP→HTTPS · SSL终结 · 反代  │                        │  │
│   │   └─────────────┬───────────────────┘                        │  │
│   │                 │ proxy_pass :8000                            │  │
│   │   ┌─────────────▼───────────────────┐                        │  │
│   │   │      fund-assistant 容器         │  端口: 8000 (内部)     │  │
│   │   │                                  │                        │  │
│   │   │   FastAPI (uvicorn)              │                        │  │
│   │   │   APScheduler (定时任务)          │                        │  │
│   │   │   React build (web/dist)         │                        │  │
│   │   │                                  │                        │  │
│   │   │   volumes:                       │                        │  │
│   │   │     ./data → /app/data           │                        │  │
│   │   │     ./.env → /app/.env           │                        │  │
│   │   └──────────────────────────────────┘                        │  │
│   │                                                               │  │
│   │   ┌──────────────────────────────────┐                        │  │
│   │   │        certbot 容器              │  SSL 证书管理          │  │
│   │   └──────────────────────────────────┘                        │  │
│   │                                                               │  │
│   └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 构建流水线

```
源代码 → Dockerfile 多阶段构建
         │
         ├── Stage 1: Node.js 20 (前端构建)
         │   npm install → npm run build → dist/
         │
         └── Stage 2: Python 3.11-slim (后端运行)
             pip install → COPY src → COPY dist → 注入版本信息
             │
             └── uvicorn server:app --host 0.0.0.0 --port 8000
```

---

## 五、关键设计模式

### 5.1 优雅降级 (Graceful Degradation)

每一层都有兜底方案，确保系统在任何依赖不可用时仍能运行：

```
LLM 调用失败      → 规则引擎结果直接输出
AKShare 不可用    → Efinance 备用 → Mock 数据
Vision LLM 失败   → PaddleOCR 降级 → 提示手动输入
Tavily 无 Key     → 博查 → Brave → SerpAPI → 无新闻（不影响主流程）
推送渠道失败      → 跳过该渠道，其他渠道正常推送
无任何 API Key    → 规则引擎 + Mock 数据，核心功能正常
```

### 5.2 熔断器模式 (Circuit Breaker)

```
             正常调用
    ┌───────────────────────┐
    │                       │
    ▼                       │ 成功
 ┌──────┐            ┌─────┴─────┐
 │CLOSED│ ──失败──→  │ 计数器 +1 │
 └──┬───┘            └─────┬─────┘
    │                      │ 连续 3 次
    │                      ▼
    │               ┌──────────┐
    │               │  OPEN    │  所有请求直接跳过
    │               └────┬─────┘
    │                    │ 等待 300 秒
    │                    ▼
    │               ┌──────────┐
    │               │HALF_OPEN │  尝试一次请求
    │               └────┬─────┘
    │                ┌───┴───┐
    │             成功│    失败│
    │                ▼       ▼
    │            CLOSED    OPEN
    └────────────────┘
```

### 5.3 策略模式 (Strategy Pattern)

```python
class BaseFundFetcher(ABC):           # 抽象基类
    @abstractmethod
    def get_nav(self, code): ...
    @abstractmethod
    def get_estimation(self, code): ...

class AKShareFetcher(BaseFundFetcher):  # 策略 A: priority=0
class EfinanceFetcher(BaseFundFetcher): # 策略 B: priority=1
```

### 5.4 三级渐进输出 (Progressive Output)

```
信息密度 ↑
    │
    │  第3层: 完整报告 (~2000字)    ← 想了解详情时
    │  第2层: 简报卡片 (~200字)     ← 打开消息快速浏览
    │  第1层: 推送通知 (~50字)      ← 锁屏一眼判断
    │
    └──────────────────────────→ 阅读时间 ↑
```

### 5.5 规则引擎 + LLM 双层决策

```
持仓数据 + 市场数据
    │
    ▼
┌────────────────────────┐
│   6 维规则引擎          │  确定性强、可解释、无需 API Key
│   → action + score     │
│   → reason + risk_note │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│   LLM 深度分析         │  自然语言生成、灰度决策
│   → 增强 prompt        │  包含规则初判结果 + 新闻
│   → JSON 输出          │
└──────────┬─────────────┘
           │
    ┌──────┴──────┐
  成功│          失败│
    ▼              ▼
 使用 LLM 结果   降级为规则引擎结果
```

### 5.6 双向基金校验 (Bidirectional Verification)

```
输入: (fund_code?, fund_name?)
    │
    ├── 有 code → 查 API 获取正确 name → 校验/修正
    ├── 有 name → 本地缓存模糊匹配 → 查 Eastmoney API → 获取 code
    └── 都有   → 交叉验证，code 优先（更可靠）
    │
    ▼
输出: (verified_code, verified_name)
```

---

## 六、目录结构

```
agent-practice/
├── main.py                    # CLI 入口
├── server.py                  # FastAPI 服务 (814行, 20+ API)
├── requirements.txt           # Python 依赖
├── Dockerfile                 # 多阶段构建
├── docker-compose.yml         # 3 容器编排
├── deploy.sh                  # 自动部署脚本
├── init-ssl.sh                # Let's Encrypt 证书
├── init-selfsigned-ssl.sh     # 自签名证书
├── version.json               # 版本信息
├── prd.md                     # 原始 PRD
├── README.md                  # 项目说明
├── IO_DESIGN_ANALYSIS.md      # 输入/输出设计分析
│
├── src/                       # 核心源码
│   ├── config.py              # 全局配置 (API Key, 模型, 推送)
│   ├── state.py               # LangGraph State 定义 (7 个 TypedDict)
│   ├── graph.py               # LangGraph 图 (5 节点, 4 路由)
│   ├── formatter.py           # 三层输出格式化
│   │
│   ├── agents/                # 5 个 Agent 节点
│   │   ├── portfolio_agent.py # 持仓管家 (2KB)
│   │   ├── market_agent.py    # 市场观察员 (3KB)
│   │   ├── briefing_agent.py  # 简报撰写员 (13KB, 含 6 维规则引擎)
│   │   └── analysis_agent.py  # 诊断分析员 (13KB, 诊断+涨跌)
│   │
│   └── tools/                 # 7 个工具模块
│       ├── data_provider.py   # 多源数据 + 熔断器 (10KB)
│       ├── market_tools.py    # 行情/估值/校验 (28KB, 最大)
│       ├── news_tools.py      # 4 引擎新闻搜索 (9KB)
│       ├── portfolio_tools.py # 持仓 CRUD + 技术指标 (6KB)
│       ├── push_tools.py      # 三渠道推送 (9KB)
│       ├── nlp_input.py       # 自然语言解析 (6KB)
│       └── ocr_tools.py       # 截图识别 (14KB)
│
├── data/                      # 数据存储
│   └── portfolio.json         # 持仓数据
│
├── web/                       # React 前端
│   └── src/
│       ├── App.tsx            # 主应用 (16KB)
│       ├── api.ts             # API 调用层 (5KB)
│       ├── store.ts           # 状态管理 (5KB)
│       ├── types.ts           # 类型定义 (2KB)
│       ├── components/        # 11 个组件
│       ├── pages/             # 4 个页面
│       ├── hooks/             # 2 个自定义 Hook
│       └── styles/            # 全局样式 (47KB)
│
├── tests/                     # 测试
│   ├── test_p0_p3_optimizations.py  # P0-P3 优化测试 (17KB)
│   ├── test_p4_confirm_flow.py      # P4 确认流程测试 (11KB)
│   ├── test_trading_logic.py        # 交易逻辑测试 (12KB)
│   └── test_nav_history.py          # 历史净值测试 (3KB)
│
├── docs/                      # 文档
│   ├── ROADMAP.md             # 产品需求迭代计划
│   ├── TECHNICAL.md           # 产品技术方案
│   ├── ARCHITECTURE.md        # 本文档：架构说明
│   ├── design.md              # 技术设计文档 (62KB, 详细)
│   └── plans/                 # 设计方案历史
│       ├── 2026-03-31-fund-assistant-design.md
│       ├── 2026-04-02-trading-and-auto-invest-design.md
│       └── 2026-04-09-input-design.md
│
└── nginx/                     # Nginx 配置
    └── nginx.conf             # HTTPS 反向代理
```

---

## 七、扩展点

### 7.1 新增 Agent

在 `src/graph.py` 中：
1. 实现新的 Agent 节点函数
2. `graph.add_node()` 注册节点
3. 在 `supervisor_router()` 中添加路由规则
4. `graph.add_edge()` 定义边

### 7.2 新增数据源

在 `src/tools/data_provider.py` 中：
1. 继承 `BaseFundFetcher` 抽象类
2. 实现 `get_nav()` 和 `get_estimation()` 方法
3. 注册到 fetcher 列表（设置 priority）

### 7.3 新增推送渠道

在 `src/tools/push_tools.py` 中：
1. 实现 `push_to_xxx()` 函数
2. 在 `push_briefing()` 中添加调用
3. 在 `src/config.py` 添加配置项
4. 在 `server.py` 的 `ALLOWED_KEYS` 中注册

### 7.4 新增前端页面

在 `web/src/` 中：
1. `pages/` 下创建新页面组件
2. `App.tsx` 中注册 Tab
3. `components/TabBar.tsx` 添加 Tab 项
