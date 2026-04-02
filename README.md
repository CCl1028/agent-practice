# 基金投资助手 🎯

一个基于多 Agent 架构的基金投资助手 MVP，帮你盯盘、判断、只在该说话时说话。

## 核心特点

- **极度懒人设计** — 不需要主动打开、不需要看懂数据、不需要自己判断
- **三层递进输出** — 推送通知(1秒) → 简报卡片(10秒) → 完整报告(按需)
- **多 Agent 协作** — Supervisor 调度 + Portfolio/Market/Briefing 三个专业 Agent
- **微信推送** — 每日简报自动推送到微信，打开手机就能看

## 架构

```
Supervisor → Portfolio Agent (持仓管家)
           → Market Agent   (市场观察员)    → Briefing Agent (简报撰写员)
                                                     ↓
                                              微信推送 / Web 页面
```

## 快速开始

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
| `SERVERCHAN_KEY` | 否 | Server酱 SendKey，推送到微信。[获取地址](https://sct.ftqq.com) |
| `WECOM_WEBHOOK_URL` | 否 | 企业微信群机器人 Webhook URL |

### 3. 运行每日简报（自动推送）

```bash
python main.py
```

> 生成简报后会自动推送到已配置的渠道（Server酱/企业微信）。

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

# 一键启动（含每日 8:00 自动推送）
docker-compose up -d
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

> **提示**：如果只改了 Python 代码（没改 `requirements.txt`），Docker 会利用缓存，重建只需几秒。如果改了依赖，会重新 pip install，大约需要 1-2 分钟。

**服务器要求：**

- 推荐配置：2 核 2G 及以上
- 系统镜像：Ubuntu 22.04 + Docker
- 需要在安全组/防火墙开放 **8000** 端口

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
    ├── portfolio_tools.py  # 持仓管理工具
    └── push_tools.py       # 推送工具（Server酱/企业微信）
web/
└── index.html            # Web 前端页面
Dockerfile                # 容器化部署
docker-compose.yml        # 一键部署配置
```

## 技术栈

| 组件 | 选型 |
|------|------|
| Agent 框架 | LangGraph |
| 后端 | FastAPI |
| 模型 | DeepSeek-chat（可切换 OpenAI） |
| 数据源 | AKShare + mock 兜底 |
| 推送 | Server酱 / 企业微信 Webhook |
| 部署 | Docker + cron 定时任务 |
| 存储 | JSON (MVP) |

## 开发计划

- [x] 第1周：核心 Agent 链路跑通
- [x] 截图识别 + 自然语言录入
- [x] Web 页面 + 微信推送
- [x] Docker 部署配置
- [ ] 后期：Chat 对话入口
