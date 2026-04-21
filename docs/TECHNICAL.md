# FundPal — 产品技术方案

> 维护人: FundPal Team  
> 最后更新: 2026-04-22  
> 当前版本: v1.2.0 (代码版本) / v3.0 (架构版本)

---

## 一、技术选型

### 1.1 技术栈总览

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|---------|
| Agent 框架 | LangGraph | ≥0.2.0 | 多 Agent DAG 编排，支持条件路由、状态管理 |
| LLM 引擎 | LangChain + OpenAI | ≥0.3.0 | 统一 LLM 调用接口，可切换 DeepSeek/OpenAI |
| 后端框架 | FastAPI | ≥0.115.0 | 异步 API、自动文档、高性能 |
| 定时调度 | APScheduler | ≥3.10.0 | 轻量级应用内调度，无需额外依赖 |
| 行情数据 | AKShare + Efinance | ≥1.14.0 / ≥0.5.5 | 国内基金数据免费、双源容错 |
| 新闻搜索 | Tavily / 博查 / Brave / SerpAPI | — | 4 引擎自动切换，配置任一即可 |
| 前端框架 | React + TypeScript | 18.x | 组件化、类型安全、生态丰富 |
| 构建工具 | Vite | — | 快速开发、HMR、优化构建 |
| 前端存储 | localStorage | — | 零依赖，MVP 阶段够用 |
| 容器化 | Docker + Docker Compose | — | 标准化部署，环境一致 |
| 反向代理 | Nginx | Alpine | HTTPS 终结、静态文件加速 |
| 数据格式 | JSON | — | 简单、零依赖、便于调试 |
| 测试 | pytest | — | Python 标准测试框架 |

### 1.2 LLM 模型配置

| 用途 | 默认模型 | 配置项 | 说明 |
|------|---------|--------|------|
| 文本生成 | deepseek-chat | `TEXT_MODEL` | 简报润色、NLP 解析、诊断分析 |
| 截图识别 | Qwen2.5-VL-72B-Instruct | `VISION_MODEL` | 多模态识别，硅基流动提供 |
| 无 Key 降级 | 规则引擎 | — | 核心功能不依赖 LLM |

### 1.3 关键依赖

```
# requirements.txt
langgraph>=0.2.0              # Agent 编排
langchain>=0.3.0              # LLM 工具链
langchain-openai>=0.2.0       # OpenAI/DeepSeek 接入
fastapi>=0.115.0              # Web 框架
uvicorn>=0.32.0               # ASGI 服务器
akshare>=1.14.0               # 主数据源
efinance>=0.5.5               # 备用数据源
pydantic>=2.9.0               # 数据校验
apscheduler>=3.10.0           # 定时任务
httpx>=0.27.0                 # HTTP 客户端
tavily-python>=0.3.0          # 新闻搜索
google-search-results>=2.4.0  # SerpAPI
```

---

## 二、系统架构

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         入口层                                    │
│    React SPA (web/)          CLI (main.py)          API (/api)  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                       API 网关层 (server.py)                     │
│    FastAPI · CORS · 静态文件 · SPA Fallback · 内存日志           │
│    APScheduler (每日推送 + 10min 估值缓存刷新)                   │
│    配置管理 (白名单 + 脱敏)                                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                    工作流编排层 (src/graph.py)                    │
│                                                                  │
│    ┌─────────────────────────────────────────────────────────┐   │
│    │  Supervisor Router (条件入口)                            │   │
│    │  daily_briefing / new_portfolio → full_analysis 路径    │   │
│    │  fund_diagnosis               → 诊断路径              │   │
│    │  fall_analysis                → 涨跌分析路径          │   │
│    └─────────────────────────────────────────────────────────┘   │
│                               │                                  │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│    │Portfolio │→│ Market   │→│ Briefing │  │  Analysis    │  │
│    │ Agent    │  │  Agent   │  │  Agent   │  │  Agent       │  │
│    └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                         工具层 (src/tools/)                       │
│                                                                  │
│  data_provider.py  — 多源数据获取 + 熔断器                       │
│  market_tools.py   — 行情/板块/估值/历史净值/基金校验             │
│  news_tools.py     — 4 引擎新闻搜索 + 缓存                      │
│  portfolio_tools.py — 持仓 CRUD + 技术指标计算                   │
│  push_tools.py     — 三渠道推送 (Bark/Server酱/企微)            │
│  nlp_input.py      — 自然语言解析 + 意图识别                     │
│  ocr_tools.py      — 截图识别 (Vision LLM + PaddleOCR)          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                        外部服务层                                 │
│  AKShare · Efinance · DeepSeek · Tavily · 博查 · Bark · Server酱│
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心数据流

```
用户输入 (5 种方式: Web UI / CLI / 截图 / 自然语言 / JSON)
  → 统一数据结构 (FundHolding)
    → LangGraph Agent 处理链 (Supervisor 路由)
      → 6 维规则引擎 + LLM 双层决策
        → 三层格式化 (通知 / 卡片 / 报告)
          → 多渠道推送 (Bark / Server酱 / 企微)
```

---

## 三、核心模块设计

### 3.1 LangGraph 工作流 (`src/graph.py`)

**设计模式：** Supervisor Router Pattern — 条件入口路由

**路由规则：**

| Trigger | 路由路径 | 节点链 |
|---------|---------|--------|
| `daily_briefing` | `full_analysis` | Portfolio → Market → Briefing → END |
| `new_portfolio` | `portfolio_only` | Portfolio → Market → Briefing → END |
| `user_query` | `full_analysis` | Portfolio → Market → Briefing → END |
| `fund_diagnosis` | `fund_diagnosis` | fund_diagnosis_agent → END |
| `fall_analysis` | `fall_analysis` | fall_reason_agent → END |

**编排方式：** 当前为顺序执行（Portfolio → Market），后续可升级为 LangGraph fan-out/fan-in 并行执行。

### 3.2 状态管理 (`src/state.py`)

**核心 State：** `AgentState(TypedDict, total=False)`

| 字段 | 类型 | 填充者 | 说明 |
|------|------|--------|------|
| `trigger` | Literal[5 种] | 调用方 | 触发类型 |
| `holdings` | list[FundHolding] | 前端/JSON | 输入持仓 |
| `portfolio` | list[FundHolding] | Portfolio Agent | 增强后的持仓 |
| `market` | MarketData | Market Agent | 市场数据 |
| `briefing` | Briefing | Briefing Agent | 最终简报 |
| `diagnosis` | FundDiagnosis | Analysis Agent | 诊断结果 |
| `fall_analysis` | FallAnalysis | Analysis Agent | 涨跌分析 |
| `error` | str | 任意 Agent | 错误信息 |

**FundHolding 字段（v2 增强）：**

```
基础字段: fund_code, fund_name, cost, cost_nav, current_nav,
          profit_ratio, profit_amount, shares, hold_days, trend_5d
技术指标: ma5, ma10, ma20, ma_status, volatility_5d, deviation_rate
估值数据: est_change, est_nav, est_time
```

### 3.3 决策引擎 (`src/agents/briefing_agent.py`)

**双层架构：** 规则引擎（确定性决策）+ LLM（自然语言润色）

**6 维决策维度：**

1. **盈亏幅度** — profit_ratio
2. **趋势方向** — trend_5d 综合判断
3. **乖离率** — deviation_rate（现价偏离 MA5 %）
4. **均线排列** — ma_status（多头/空头/震荡）
5. **波动率** — volatility_5d（5 日最高-最低）
6. **持有时间** — hold_days

**交易纪律硬规则（最高优先级）：**

| 规则 | 条件 | 结果 | 评分 |
|------|------|------|------|
| 追高检测 | 乖离率 > 3% 且上涨 | 观望 + 追高风险提示 | 35 |
| 空头禁加仓 | 空头排列 且 浮亏 > 5% | 观望 + 趋势未反转 | 30 |
| 止盈不犹豫 | 浮盈 > 15% 且连涨 | 减仓（部分止盈） | 80 |
| 下跌禁补仓 | 连跌 3 天 且 浮亏 > 5% | 观望 + 下跌中勿补仓 | 25 |
| 多头确认做多 | 多头排列 且 浮亏 > 10% 且企稳 | 加仓 | 60 |

**LLM 降级策略：** 无 API Key 或 LLM 调用失败 → 直接使用规则引擎结果，核心功能不受影响。

### 3.4 多源数据获取 (`src/tools/data_provider.py`)

**设计模式：** 策略模式 (Strategy Pattern) + 熔断器 (Circuit Breaker)

**数据源优先级：**

| 数据源 | 优先级 | 类 | 说明 |
|--------|--------|-----|------|
| AKShare | P0 | `AKShareFetcher` | 东方财富，默认首选 |
| Efinance | P1 | `EfinanceFetcher` | 东方财富第二渠道 |
| Mock | P99 | 内置 | 开发测试兜底 |

**熔断器参数：**

```python
class CircuitBreaker:
    failure_threshold = 3    # 连续失败 3 次触发熔断
    cooldown = 300           # 冷却 300 秒（5 分钟）
    # 状态: CLOSED → OPEN → HALF_OPEN → CLOSED
```

**核心函数：**
- `get_fund_nav_multi_source(fund_code)` — 多源获取净值
- `get_fund_estimation_multi_source(fund_code)` — 多源获取估值

### 3.5 新闻搜索 (`src/tools/news_tools.py`)

**4 引擎自动切换：**

| 引擎 | 优先级 | 免费额度 | 特点 |
|------|--------|---------|------|
| Tavily | 1 | 1000 次/月 | 质量最好 |
| 博查 | 2 | 有免费额度 | 中文优化 |
| Brave | 3 | 2000 次/月 | 隐私优先 |
| SerpAPI | 4 | 100 次/月 | Google 兜底 |

**搜索维度：**
- 基金新闻: 最新消息 / 风险排查 / 业绩持仓
- 市场新闻: 大盘热点 / 板块走势

**缓存策略：** TTL 1 小时，LRU 上限 200 条

### 3.6 推送系统 (`src/tools/push_tools.py`)

| 渠道 | 目标 | 内容格式 | 配置项 |
|------|------|---------|--------|
| Bark | iPhone 通知栏 | 短文本 | `BARK_URL` |
| Server酱 | 微信 | Markdown | `SERVERCHAN_KEY` |
| 企业微信 | 企微群 | Markdown | `WECOM_WEBHOOK_URL` |

**配置优先级：** 前端传入 > .env 文件配置

### 3.7 截图识别 (`src/tools/ocr_tools.py`)

**双层降级：**

```
Vision LLM (Qwen-VL-72B) — 优先
  ↓ 失败
PaddleOCR 文字识别 + LLM 结构化解析 — 降级
  ↓ 失败
返回空数组，提示用户手动输入 — 兜底
```

**后处理：**
- 成本净值反算（4 种策略）
- `verify_and_fix_fund()` 基金代码双向校验

### 3.8 前端架构 (`web/src/`)

**技术栈：** React 18 + TypeScript + Vite

**页面结构（4 Tab）：**

| Tab | 组件 | 功能 |
|-----|------|------|
| 持仓 | `PortfolioPage` | 基金卡片列表、排序、加减仓 |
| 简报 | `BriefingPage` | 每日操作建议 |
| 诊断 | `DiagnosisPage` | 基金诊断 + 涨跌分析 |
| 我的 | `ProfilePage` | 配置管理、日志、版本 |

**数据存储：** localStorage-first

| Key | 内容 |
|-----|------|
| `fund_assistant_portfolio` | 持仓列表 |
| `fund_assistant_transactions` | 交易记录 |
| `fund_assistant_auto_invest` | 定投计划 |
| `fund_assistant_config` | 用户配置 |

---

## 四、API 设计

### 4.1 端点总览

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/briefing` | POST | 生成每日简报 |
| `/api/briefing-and-push` | POST | 生成简报并推送 |
| `/api/portfolio` | GET | 获取当前持仓 |
| `/api/portfolio/add-text` | POST | 自然语言录入持仓 |
| `/api/portfolio/add-screenshot` | POST | 截图识别录入持仓 |
| `/api/portfolio/parse-text` | POST | 解析文本（只解析不保存） |
| `/api/portfolio/parse-screenshot` | POST | 解析截图（只解析不保存） |
| `/api/portfolio/refresh` | POST | 刷新持仓净值和市值 |
| `/api/portfolio/{fund_code}` | DELETE | 删除指定持仓 |
| `/api/estimation` | GET/POST | 获取持仓盘中估值 |
| `/api/fund/{fund_code}/nav-history` | GET | 获取基金历史净值 |
| `/api/push/status` | GET/POST | 获取推送渠道状态 |
| `/api/push/test` | POST | 发送测试推送 |
| `/api/config` | GET/POST | 读取/更新配置 |
| `/api/fund-diagnosis` | POST | 基金诊断 |
| `/api/fund-explanation` | POST | 涨跌原因分析 |
| `/api/logs` | GET/DELETE | 查看/清空应用日志 |
| `/api/version` | GET | 获取版本信息 |
| `/api/health` | GET | 健康检查 |

### 4.2 安全设计

| 策略 | 实现 |
|------|------|
| 配置白名单 | `ALLOWED_KEYS` 集合，仅允许修改特定配置 |
| 敏感脱敏 | API Key 显示为 `sk-****xxxx` |
| CORS | 当前全开放（生产环境需收紧） |
| 超时保护 | NLP/OCR 解析 45 秒超时 |
| 内存保护 | 日志环形缓冲区 500 行上限 |

---

## 五、部署架构

### 5.1 Docker 多阶段构建

```dockerfile
# Stage 1: Node.js 20 构建前端
FROM node:20-alpine AS frontend-builder
# npm install → npm run build → dist/

# Stage 2: Python 3.11-slim 运行后端
FROM python:3.11-slim
# pip install → COPY . → COPY --from=frontend-builder dist → uvicorn
```

### 5.2 容器编排 (docker-compose.yml)

| 服务 | 镜像 | 端口 | 职责 |
|------|------|------|------|
| fund-assistant | 自建 | 8000 (内部) | FastAPI 应用 |
| nginx | nginx:alpine | 80, 443 | HTTPS 反向代理 |
| certbot | certbot/certbot | — | SSL 证书管理 |

### 5.3 数据持久化

```
volumes:
  - ./data:/app/data       # 持仓数据
  - ./.env:/app/.env       # 环境变量
```

### 5.4 部署流程

```bash
# 自动化部署（服务器端执行）
ssh root@<IP> "cd ~/agent-practice && bash deploy.sh"
# deploy.sh: git pull → 自签名证书 → docker compose up --build
```

---

## 六、关键技术决策记录

| 决策 | 选择 | 理由 | 替代方案 |
|------|------|------|---------|
| Agent 编排 | LangGraph StateGraph | 原生支持条件路由、状态传递 | CrewAI, AutoGen |
| 数据存储 | JSON 文件 | 零依赖、开箱即用、MVP 够用 | SQLite, PostgreSQL |
| 前端存储 | localStorage | 无需后端数据库、隐私友好 | IndexedDB, 后端 DB |
| 决策模式 | 规则引擎 + LLM | 确定性 + 可解释性 + 无 Key 降级 | 纯 LLM |
| 数据容错 | 熔断器模式 | 自动降级、防雪崩 | 简单重试 |
| 部署方式 | Docker + Nginx | 标准化、HTTPS、易维护 | 直接裸跑 |
| 前端框架 | React + Vite | 组件化、类型安全、快速构建 | Vue, Svelte |
| 推送方式 | 三渠道并行 | 覆盖 iOS + 微信 + 企微 | 自建推送 |

---

## 七、性能指标

| 指标 | 目标值 | 当前实际 |
|------|--------|---------|
| API 响应 (无 LLM) | < 500ms | ~100-500ms |
| 简报生成 (含 LLM) | < 30s | ~10-20s |
| 截图识别 | < 15s | ~5-10s |
| NLP 解析 | < 10s | ~3-5s |
| 估值缓存刷新 | 每 10 分钟 | 每 10 分钟 |
| 持仓数量支持 | 5-20 只 | ~5KB JSON |
| 日志缓冲 | 500 行 | 500 行 |
