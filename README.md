# FundPal — 智能基金投顾助手 📊

一个基于多 Agent 架构的基金投资助手，帮你盯盘、判断、只在该说话时说话。

## ✨ 核心特点

- **极度懒人设计** — 不需要主动打开、不需要看懂数据、不需要自己判断
- **三层递进输出** — 推送通知(1秒) → 简报卡片(10秒) → 完整报告(按需)
- **多 Agent 协作** — Supervisor 调度 + Portfolio / Market / Briefing 三个专业 Agent
- **多渠道推送** — Bark / Server酱 / 企业微信，每日简报自动推送到手机
- **智能录入** — 截图识别 + 自然语言，30秒完成持仓录入
- **交易管理** — 加仓 / 减仓 / 定投计划，交易记录全留痕
- **无 Key 也能跑** — 无 LLM API Key 时降级为规则引擎，核心功能照常运行

## 🏗️ 架构

```
用户入口 (Web UI / CLI)
  → FastAPI API 层 (server.py)
    → LangGraph 工作流 (Supervisor 路由)
      → Portfolio Agent (持仓管家) — 加载持仓、刷新净值、计算盈亏
      → Market Agent   (市场观察员) — 板块涨跌、市场情绪、热点新闻
      → Briefing Agent (简报撰写员) — 规则引擎 + LLM 润色生成建议
    → 格式化输出 (三层递进)
    → 多渠道推送 (Bark / Server酱 / 企业微信)
```

## 📸 功能一览

### 🎯 每日操作简报

Agent 综合持仓盈亏、近期趋势、市场情绪，为每只基金生成 **加仓 / 减仓 / 观望** 建议，并附简短理由。

### 📱 智能持仓录入

| 方式 | 说明 |
|------|------|
| 📸 截图识别 | 上传基金 App 截图，多模态 LLM 自动提取持仓信息 |
| 💬 自然语言 | 输入"我买了2万易方达蓝筹"，LLM 解析并自动补全基金代码 |

### 💰 交易管理

- **加仓 / 减仓** — 卡片按钮 + 自然语言两种方式
- **定投计划** — 支持每天 / 每周 / 每两周 / 每月定投
- **自动执行** — 打开页面自动检查待执行定投，支持按历史净值补执行
- **交易记录** — 每笔交易留痕，累积持仓自动计算

### 📡 多渠道推送

| 渠道 | 推送目标 | 配置项 |
|------|---------|--------|
| Bark | iPhone 通知栏 | `BARK_URL` |
| Server酱 | 微信 | `SERVERCHAN_KEY` |
| 企业微信 | 企微群 | `WECOM_WEBHOOK_URL` |

### 📈 盘中估值

- 交易时段（9:30-15:00）显示实时估值
- 非交易时段显示上一交易日收盘涨跌
- 后台每 10 分钟自动刷新缓存

### ⚙️ Web 端设置

- 在线配置推送渠道和 AI 模型（无需编辑 .env）
- 发送测试推送验证配置
- 查看应用日志排查问题
- 显示版本信息

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入以下配置
```

| 变量 | 必须 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | 否 | 无 Key 也能跑，降级为规则引擎 |
| `OPENAI_BASE_URL` | 否 | 默认 DeepSeek，可换 OpenAI |
| `TEXT_MODEL` | 否 | 文本模型，默认 `deepseek-chat` |
| `VISION_MODEL` | 否 | 视觉模型（截图识别），默认 `deepseek-chat` |
| `VISION_API_KEY` | 否 | 视觉模型 Key，默认复用 `OPENAI_API_KEY` |
| `VISION_BASE_URL` | 否 | 视觉模型地址，默认复用 `OPENAI_BASE_URL` |
| `BARK_URL` | 否 | Bark 推送 URL |
| `SERVERCHAN_KEY` | 否 | Server酱 SendKey，[获取地址](https://sct.ftqq.com) |
| `WECOM_WEBHOOK_URL` | 否 | 企业微信群机器人 Webhook URL |
| `PUSH_TIME` | 否 | 每日推送时间，默认 `14:30` |

### 3. 运行每日简报（CLI）

```bash
python main.py
```

> 生成简报后自动推送到已配置的渠道。

其他 CLI 命令：

```bash
# 截图识别录入持仓
python main.py add --screenshot photo.jpg

# 自然语言录入持仓
python main.py add --text "我买了2万易方达蓝筹"
```

### 4. 启动 API + Web 服务

```bash
uvicorn server:app --reload
```

- 访问 `http://localhost:8000` 打开 Web 页面
- 访问 `http://localhost:8000/docs` 查看 API 文档

### 5. Docker 一键部署（推荐）

```bash
# 先配置 .env
cp .env.example .env && vim .env

# 一键启动（含 Nginx HTTPS 反向代理）
docker compose up -d --build
```

### 6. 云服务器部署

以腾讯云轻量应用服务器为例：

**首次部署：**

```bash
# 1. 将项目上传到服务器
rsync -avz --exclude='__pycache__' --exclude='.git' \
  ./ root@<服务器IP>:/root/fund-assistant/

# 2. SSH 登录服务器
ssh root@<服务器IP>

# 3. 配置环境变量
cd /root/fund-assistant
vim .env

# 4. 构建并启动
docker compose up -d --build
```

**更新代码：**

```bash
# 1. 上传最新代码
rsync -avz --exclude='__pycache__' --exclude='.git' \
  ./ root@<服务器IP>:/root/fund-assistant/

# 2. 在服务器上重建并重启容器
ssh root@<服务器IP> "cd /root/fund-assistant && docker compose up -d --build"
```

**自动化部署脚本：**

```bash
# 在服务器上使用 deploy.sh 一键拉取最新代码并部署
ssh root@<服务器IP> "cd ~/agent-practice && bash deploy.sh"
```

**SSL 证书：**

```bash
# 方式1：自签名证书（无需域名，IP 直接访问）
bash init-selfsigned-ssl.sh

# 方式2：Let's Encrypt 免费证书（需要域名）
bash init-ssl.sh your-domain.com
```

**服务器要求：**

- 推荐配置：2 核 2G 及以上
- 系统镜像：Ubuntu 22.04 + Docker
- 需要在安全组/防火墙开放 **80** 和 **443** 端口

> **提示**：如果只改了 Python 代码（没改 `requirements.txt`），Docker 会利用缓存，重建只需几秒。如果改了依赖，会重新 pip install，大约需要 1-2 分钟。

## 📁 项目结构

```
agent-practice/
├── main.py                    # CLI 入口（每日简报 / 截图录入 / 文本录入）
├── server.py                  # FastAPI 服务（API + Web UI + 定时任务）
├── requirements.txt           # Python 依赖
├── Dockerfile                 # 容器化配置
├── docker-compose.yml         # Docker Compose（应用 + Nginx）
├── deploy.sh                  # 服务器自动部署脚本
├── init-ssl.sh                # Let's Encrypt SSL 证书初始化
├── init-selfsigned-ssl.sh     # 自签名 SSL 证书初始化
├── prd.md                     # 产品需求文档
│
├── src/                       # 核心源码
│   ├── config.py              # 全局配置（API Key、模型、推送等）
│   ├── state.py               # LangGraph State 类型定义
│   ├── graph.py               # LangGraph 图定义（核心工作流编排）
│   ├── formatter.py           # 输出格式化（三层递进展示）
│   │
│   ├── agents/                # Agent 实现
│   │   ├── portfolio_agent.py # 持仓管家 — 加载持仓、刷新净值、计算盈亏
│   │   ├── market_agent.py    # 市场观察员 — 板块涨跌、情绪判断、新闻
│   │   └── briefing_agent.py  # 简报撰写员 — 规则引擎 + LLM 生成建议
│   │
│   └── tools/                 # 工具函数
│       ├── market_tools.py    # 行情/板块/新闻/估值（AKShare + Mock 兜底）
│       ├── portfolio_tools.py # 持仓存取/盈亏计算
│       ├── push_tools.py      # 推送（Bark / Server酱 / 企业微信）
│       ├── nlp_input.py       # 自然语言持仓解析（含意图识别）
│       └── ocr_tools.py       # 截图识别（多模态 LLM + PaddleOCR 兜底）
│
├── data/                      # 数据存储
│   └── portfolio.json         # 持仓数据（JSON 格式）
│
├── web/                       # 前端
│   └── index.html             # SPA 单页应用（移动端优先）
│
├── nginx/                     # Nginx 配置
│   └── nginx.conf             # HTTPS 反向代理配置
│
├── tests/                     # 测试
│   ├── test_nav_history.py    # 历史净值接口测试
│   └── test_trading_logic.py  # 交易记录 & 定投计算逻辑测试
│
└── docs/                      # 文档
    ├── design.md              # 技术设计文档（完整架构详解）
    └── plans/                 # 设计方案
        ├── 2026-03-31-fund-assistant-design.md   # MVP 设计方案
        └── 2026-04-02-trading-and-auto-invest-design.md  # 交易 & 定投设计
```

## 🔌 API 端点

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
| `/api/logs` | GET/DELETE | 查看/清空应用日志 |
| `/api/version` | GET | 获取版本信息 |
| `/api/health` | GET | 健康检查 |

## 🛠️ 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| Agent 框架 | LangGraph | 多 Agent DAG 编排，支持条件路由 |
| 后端 | FastAPI | 异步 API 服务 + 定时任务调度 |
| LLM 模型 | DeepSeek-chat（可切换 OpenAI） | 文本生成 + 截图识别 |
| 数据源 | AKShare | 基金净值、板块行情、实时估值，失败时 Mock 兜底 |
| 推送 | Bark / Server酱 / 企业微信 Webhook | 三渠道零成本推送 |
| 定时任务 | APScheduler | 每日推送 + 估值缓存刷新 |
| 前端存储 | localStorage | 持仓、交易记录、定投计划、配置 |
| 部署 | Docker + Nginx + SSL | 容器化部署，HTTPS 反向代理 |
| 测试 | pytest | 交易逻辑 + 净值接口单元测试 |

## 🧠 决策引擎

Briefing Agent 采用 **规则引擎 + LLM 润色** 的双层策略：

| 条件 | 趋势上涨 | 趋势下跌 | 震荡 |
|------|---------|---------|------|
| **浮盈 > 10%** | 🔴 减仓（止盈） | ⏸️ 观望 | ⏸️ 观望 |
| **浮亏 > 10%** | ⏸️ 观望 | ⏸️ 观望（等企稳） | 🟢 加仓（补仓） |
| **盈亏 ≤ 10%** | ⏸️ 观望 | ⏸️ 观望 | ⏸️ 观望 |

> 规则引擎保底 → LLM 润色输出自然语言建议。无 API Key 时完全靠规则引擎运行。

## 🧪 运行测试

```bash
pytest tests/ -v
```

## 🏷️ 版本管理

采用 [语义化版本](https://semver.org/lang/zh-CN/) 规范：`v{主版本}.{次版本}.{修订号}`

| 版本 | 发布日期 | 主要功能 |
|------|---------|---------|
| v1.0.0 | 2026-03 | MVP：持仓管理 + 每日简报 + 三渠道推送 |
| v1.1.0 | 2026-04 | 交易记录 + 定投计划（自动执行、补执行） |
| v1.2.0 | 2026-04 | 盘中估值 + Web 设置面板 + 在线配置 |

**版本文件**：`version.json`

```json
{
  "version": "1.2.0",
  "name": "FundPal",
  "codename": "智能投顾",
  "build_time": "2026-04-03",
  "git_commit": "local"
}
```

> Docker 构建时会自动注入 `build_time` 和 `git_commit`，设置弹窗中显示格式：`v1.2.0 · 智能投顾 · 2026-04-03`

## 📋 开发计划

- [x] 核心 Agent 链路（Portfolio → Market → Briefing）
- [x] 截图识别 + 自然语言录入
- [x] Web 页面（移动端优先 SPA）
- [x] 多渠道推送（Bark / Server酱 / 企业微信）
- [x] Docker + Nginx 部署配置
- [x] 盘中估值（实时 + 缓存）
- [x] 加仓 / 减仓 / 交易记录
- [x] 定投计划（自动执行 + 补执行）
- [x] Web 端在线配置管理
- [x] 基金代码/名称双向校验修正
- [ ] Chat 对话入口
- [ ] 基金买前诊断
- [ ] 涨跌原因分析
- [ ] 智能定投（根据估值调整金额）
- [ ] 多用户支持

## 📄 License

MIT
