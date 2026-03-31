# 基金投资助手 🎯

> "你的基金，我盯着。有事我叫你，没事别操心。"

一个基于多 Agent 架构的基金投资助手 MVP，帮你盯盘、判断、只在该说话时说话。

## 核心特点

- **极度懒人设计** — 不需要主动打开、不需要看懂数据、不需要自己判断
- **三层递进输出** — 推送通知(1秒) → 简报卡片(10秒) → 完整报告(按需)
- **多 Agent 协作** — Supervisor 调度 + Portfolio/Market/Briefing 三个专业 Agent

## 架构

```
Supervisor → Portfolio Agent (持仓管家)
           → Market Agent   (市场观察员)    → Briefing Agent (简报撰写员)
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY
```

### 3. 运行每日简报

```bash
python main.py
```

> 无 OpenAI Key 也能运行，会降级使用规则引擎生成建议。

### 4. 启动 API 服务

```bash
uvicorn server:app --reload
```

访问 `http://localhost:8000/docs` 查看 API 文档。

## 项目结构

```
src/
├── state.py              # LangGraph State 定义
├── config.py             # 全局配置
├── graph.py              # LangGraph 图定义（核心）
├── formatter.py          # 输出格式化（三层递进）
├── agents/
│   ├── portfolio_agent.py  # 持仓管家
│   ├── market_agent.py     # 市场观察员
│   └── briefing_agent.py   # 简报撰写员
└── tools/
    ├── market_tools.py     # 市场数据工具
    └── portfolio_tools.py  # 持仓管理工具
```

## 技术栈

| 组件 | 选型 |
|------|------|
| Agent 框架 | LangGraph |
| 后端 | FastAPI |
| 模型 | GPT-4o-mini (文本) / GPT-4o (截图识别) |
| 数据源 | AKShare + mock 兜底 |
| 存储 | SQLite (后期) / JSON (MVP) |

## 开发计划

- [x] 第1周：核心 Agent 链路跑通
- [ ] 第2周：截图识别 + 自然语言录入
- [ ] 第3周：Streamlit UI + 微信推送
- [ ] 后期：Chat 对话入口
