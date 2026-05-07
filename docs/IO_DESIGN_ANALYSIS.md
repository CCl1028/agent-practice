# FundPal: 深度输入/输出设计分析 📊

## 一、项目概览

**项目名**: FundPal（智能基金投顾助手）  
**核心价值主张**: 一个基于多 Agent 架构的基金投资助手，帮助用户盯盘、判断和决策  
**技术栈**: FastAPI + LangGraph + DeepSeek/OpenAI + AKShare + Bark/Server酱  
**用户类型**: 被动基金投资者（希望减少决策负担）

---

## 二、系统数据流全景图

```
                     ┌─────────────────────────────────────┐
                     │      用户输入入口 (多渠道)            │
                     └─────────────────────────────────────┘
                              ▼
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
      ┌─────────┐          ┌─────────┐          ┌─────────┐
      │  Web UI │          │   CLI   │          │  API    │
      │ 前端交互 │          │ 命令行  │          │ 编程    │
      └────┬────┘          └────┬────┘          └────┬────┘
           │                    │                    │
           └────────────────────┼────────────────────┘
                                ▼
                     ┌──────────────────────┐
                     │  FastAPI 应用服务器   │
                     │  (server.py)         │
                     └──────────┬───────────┘
                                ▼
                     ┌──────────────────────┐
                     │  LangGraph 编排引擎   │
                     │  (Supervisor 路由)   │
                     └──────────┬───────────┘
                     /          │          \
                    /           │           \
         ┌──────────────┐  ┌─────────────┐  ┌──────────────┐
         │ Portfolio    │  │ Market      │  │ Analysis     │
         │ Agent        │  │ Agent       │  │ Agent        │
         └──────┬───────┘  └──────┬──────┘  └──────┬───────┘
                │                 │                │
         ┌──────▼──────────────────▼────────────────▼──────┐
         │         Briefing Agent (最终决策节点)            │
         └──────────────────┬─────────────────────────────┘
                            ▼
         ┌──────────────────────────────────────┐
         │  三层递进输出格式化                   │
         │  1. 推送通知 (1秒)                   │
         │  2. 卡片 (10秒)                      │
         │  3. 完整报告 (按需)                  │
         └──────┬───────────────────────────────┘
                ▼
         ┌──────────────────────────────────────┐
         │  多渠道推送 & 响应                    │
         │  Bark / Server酱 / 企业微信           │
         │  Web 界面更新 / API 响应              │
         └──────────────────────────────────────┘
```

---

## 三、详细输入流分析

### 3.1 用户数据来源 (5 大类)

| 来源 | 方式 | 数据形式 | 处理流程 | 实现位置 |
|------|------|--------|--------|--------|
| **Web UI** | 手动输入表单 | 文本字段 | 前端表单验证 → API POST | `web/index.html` + `server.py` |
| **CLI** | 命令行参数 | 文本字符串 | 参数解析 → NLP/OCR处理 | `main.py` |
| **截图识别** | 上传基金App图片 | JPEG/PNG | Vision LLM 或 PaddleOCR → JSON | `server.py:/api/portfolio/add-screenshot` |
| **自然语言输入** | 文字描述（自由格式） | 中文文本 | LLM 意图识别 + 实体提取 | `nlp_input.py` |
| **历史持仓** | 从 JSON 加载 | `portfolio.json` | 直接反序列化 | `portfolio_tools.py` |

### 3.2 输入数据结构定义

#### **FundHolding 持仓对象** (src/state.py:14-37)

```python
class FundHolding(TypedDict):
    """单只基金持仓"""
    # 基础标识
    fund_code: str           # 基金代码（6位数字，如 "005827"）
    fund_name: str           # 基金名称（如 "易方达蓝筹精选"）
    
    # 成本信息
    cost: float              # 持仓金额（元，如 20000）
    cost_nav: float          # 成本净值（买入时单位净值，如 2.15）
    
    # 当前状态
    current_nav: float       # 当前净值（实时从 API 获取）
    profit_ratio: float      # 盈亏比例 (%)，如 -5.6% 表示亏损
    hold_days: int           # 持有天数
    trend_5d: list[float]    # 近5日涨跌幅 %
    
    # v2 技术指标
    ma5: float               # 5日均线净值
    ma10: float              # 10日均线净值
    ma20: float              # 20日均线净值
    ma_status: str           # "多头排列" / "空头排列" / "震荡"
    
    # v2 估值数据
    est_change: float | None # 盘中估值涨跌幅 %
    est_nav: float | None    # 估算净值
    est_time: str | None     # 估值时间
```

**示例数据**:
```json
{
  "fund_code": "005827",
  "fund_name": "易方达蓝筹精选",
  "cost": 20000,
  "cost_nav": 2.15,
  "current_nav": 2.03,
  "profit_ratio": -5.6,
  "hold_days": 280,
  "trend_5d": [-0.5, 1.2, -0.8, 0.3, 2.1],
  "ma5": 2.05,
  "ma_status": "震荡"
}
```

---

## 四、详细输入渠道分析

### 4.1 Web UI 表单输入

**入口**: `http://localhost:8000/` 前端界面

**用户交互流程**:
```
用户访问 Web → 填写持仓表单 → 点击"添加" 
→ 前端 JS 收集表单数据 → POST /api/portfolio/add-text 或 add-screenshot 
→ 后端处理 → 前端显示结果
```

**前端表单字段**（从 `web/index.html` 推断）:
- 基金代码或名称 (auto-complete)
- 持仓金额 (currency input)
- 成本净值 (optional)
- 持有时长 (date picker)

**数据校验**: 前端轻量级验证，后端完整校验

---

### 4.2 CLI 命令行输入

**命令格式** (main.py:135-159):

```bash
# 截图识别录入
python main.py add --screenshot /path/to/photo.jpg

# 自然语言录入
python main.py add --text "我买了2万易方达蓝筹"

# 生成每日简报
python main.py  # 默认触发 daily_briefing
```

**流程**:
```
命令解析 → 获取参数 → 调用对应函数 → 处理 → 输出结果
```

---

### 4.3 截图识别输入 (OCR Pipeline)

**入口 API**: `POST /api/portfolio/add-screenshot` (server.py:283-312)

**处理流程** (ocr_tools.py:207-238):

```
上传图片 (JPG/PNG)
    ▼
┌─────────────────────────────┐
│ 方案1: Vision LLM 直接识别   │  ← 优先使用
│ (DeepSeek/OpenAI多模态)     │
└────────┬────────────────────┘
         │ 失败则转向方案2
         ▼
┌─────────────────────────────┐
│ 方案2: PaddleOCR 文字识别    │
│ → LLM 结构化解析             │
└────────┬────────────────────┘
         ▼
┌─────────────────────────────┐
│ 字段补全 & 基金校正          │
│ verify_and_fix_fund()        │
└────────┬────────────────────┘
         ▼
JSON 结构化持仓数据
```

**识别字段**:
```python
# ocr_tools.py:25-30
- fund_code: 基金代码（6位数字）
- fund_name: 基金名称
- cost: 持有金额（元）
- cost_nav: 成本净值
- current_nav: 最新净值
- profit_ratio: 持有收益率（%）
- hold_days: 持有天数
```

**LLM Prompt 设计**:
- Vision LLM: "请从截图中识别出持仓信息，返回 JSON 数组"
- PaddleOCR: 先识别文字，再用 LLM 结构化解析

**错误处理**: 
- Vision LLM 失败 → 回退 PaddleOCR
- 所有方案失败 → 返回空数组，提示用户手动输入

---

### 4.4 自然语言输入 (NLP Pipeline)

**入口 API**: `POST /api/portfolio/add-text` (server.py:236-256)

**处理流程** (nlp_input.py:48-124):

```
用户输入文本（自由格式）
    ▼
┌──────────────────────────────────────┐
│ 使用 LLM 提取结构化信息              │
│ - 意图识别 (intent)                 │
│ - 实体提取 (基金名/代码/金额/操作) │
└────────┬─────────────────────────────┘
         ▼
┌──────────────────────────────────────┐
│ JSON 数组输出（包含多只基金）        │
└────────┬─────────────────────────────┘
         ▼
┌──────────────────────────────────────┐
│ 双向校验: fund_code ↔ fund_name     │
│ (verify_and_fix_fund)                │
└────────┬─────────────────────────────┘
         ▼
纠正后的持仓数据
```

**LLM 提示词结构** (nlp_input.py:16-44):

```python
EXTRACT_PROMPT = """
你是一个基金持仓信息提取助手。用户会用自然语言描述自己的基金持仓或操作。

提取以下字段：
- intent: "add_holding" / "buy" / "sell"
- fund_code: 基金代码（不确定填空）
- fund_name: 基金名称（必填）
- cost: 持有金额（元）
- amount: 交易金额（仅当 intent 为 buy/sell 时）
- profit_ratio: 收益率(%)
- hold_days: 持有天数

当前日期: {today}
严格按 JSON 数组格式输出
"""
```

**示例输入与解析**:

| 用户输入 | 解析结果 |
|--------|--------|
| "我买了2万易方达蓝筹" | `[{intent:"buy", fund_name:"易方达蓝筹精选", amount:20000, ...}]` |
| "去年6月以2.15买了10000元易方达" | `[{fund_code:"005827", cost:10000, cost_nav:2.15, hold_days:~280}]` |
| "减仓5000块白酒基金" | `[{intent:"sell", fund_name:"招商中证白酒", amount:5000}]` |

**即时问题**: 
- 需要 API Key（无 Key 时无法调用 LLM）
- 有 30s 超时限制，降低长连接阻塞风险

---

### 4.5 API 编程输入

**直接调用 API**（适合集成者）:

```bash
# 自然语言解析（只解析不保存）
curl -X POST http://localhost:8000/api/portfolio/parse-text \
  -H "Content-Type: application/json" \
  -d '{"text": "我买了2万易方达"}'

# 截图解析（只解析不保存）
curl -X POST http://localhost:8000/api/portfolio/parse-screenshot \
  -F "file=@screenshot.jpg"

# 添加持仓（保存到数据库）
curl -X POST http://localhost:8000/api/portfolio/add-text \
  -d '{"text": "..."}'
```

---

## 五、数据验证与校正机制

### 5.1 双向校验流程

**问题**: LLM 可能识别出错（如将基金名"易方达蓝筹"误识别为"易方达蓝筹精选"）

**解决**: `verify_and_fix_fund()` 函数 (market_tools.py)

```python
# 伪代码
def verify_and_fix_fund(code: str, name: str) -> tuple[str, str]:
    """
    1. 如果给了代码，从 API 查询对应的正确名称
    2. 如果只给了名称，从本地基金库或 API 模糊匹配代码
    3. 若代码和名称不匹配，优先保留代码（更可靠）
    4. 如果都不匹配，保留用户输入
    """
```

**调用位置**:
- `ocr_tools.py:174-204` (截图识别后)
- `nlp_input.py:93-117` (NLP 解析后)

---

## 六、详细输出流分析

### 6.1 输出层级结构

```
Agent State (内部数据结构)
    ▼
┌────────────────────────────────────┐
│ Briefing 对象 (state.py:63-68)    │
├────────────────────────────────────┤
│ - summary: 一句话结论             │
│ - details: 每只基金建议列表       │
│ - market_note: 市场简评           │
│ - risk_alerts: 风险提示           │
└────────┬─────────────────────────┘
         ▼
┌────────────────────────────────────┐
│ 三层递进格式化 (formatter.py)     │
├────────────────────────────────────┤
│ 1. format_push_notification()     │
│    → 推送通知 (~50字)             │
│                                   │
│ 2. format_briefing_card()         │
│    → 卡片展示 (~200字)            │
│                                   │
│ 3. format_full_report()           │
│    → 完整报告 (~2000字)           │
└────────┬─────────────────────────┘
         ▼
┌────────────────────────────────────┐
│ 多渠道输出                         │
├────────────────────────────────────┤
│ • Bark 推送 (iOS 通知)            │
│ • Server酱 (微信)                 │
│ • 企业微信 Webhook                 │
│ • Web 界面实时更新                │
│ • API JSON 响应                   │
└────────────────────────────────────┘
```

### 6.2 Briefing 输出数据结构 (state.py:63-68)

```python
class Briefing(TypedDict):
    """最终简报输出"""
    summary: str               # 一句话结论 (≤15字)
    # 示例: "观望为主，布局优质基金"
    
    details: list[FundAdvice]  # 每只基金的建议
    # [{
    #   "fund_name": "易方达蓝筹精选",
    #   "action": "加仓",
    #   "reason": "短期上涨趋势确认，且当前处于低估",
    #   "confidence": "高",
    #   "score": 85,
    #   "risk_note": "需关注中概股波动"
    # }]
    
    market_note: str           # 市场简评 (~100字)
    # "沪深两市小幅震荡，权重股走势分化..."
    
    risk_alerts: list[str]     # 全局风险提示
    # ["地缘政治风险升温", "流动性收紧预期"]
```

**示例完整输出**:
```json
{
  "summary": "观望为主，关注回调机会",
  "details": [
    {
      "fund_name": "易方达蓝筹精选",
      "action": "观望",
      "reason": "处于成本附近，短期无明确方向",
      "confidence": "中",
      "score": 60,
      "risk_note": "消费板块压力较大"
    },
    {
      "fund_name": "招商中证白酒",
      "action": "减仓",
      "reason": "浮盈12%，短期涨幅过大，建议止盈",
      "confidence": "高",
      "score": 78,
      "risk_note": "白酒板块估值风险"
    }
  ],
  "market_note": "A股市场虽然整体向上，但权重股压力较大。建议密切关注中国国债收益率走势，可能影响后市方向...",
  "risk_alerts": ["权重股压力", "中概股波动风险"]
}
```

---

### 6.3 三层递进格式化示例

**第1层：推送通知** (1-2秒内发出)
```
📊 今日基金简报：观望为主
✓ 易方达蓝筹(观望) ✓ 白酒基金(减仓)
🔔 点击查看完整分析
```

**第2层：卡片** (10秒左右)
```
【今日基金简报】

📈 核心建议
观望为主，关注回调

基金分析
① 易方达蓝筹精选 — 观望
   理由：处于成本附近，短期无方向
   
② 招商中证白酒 — 减仓 ⚠️
   理由：浮盈12%，短期涨幅过大

⚠️ 风险提示: 权重股压力, 中概股波动
```

**第3层：完整报告** (按需查看，2000+字)
```markdown
# 【2026-04-09】基金投资简报

## 市场综述
A股市场整体向上，但权重股压力较大...

## 个基分析

### 1. 易方达蓝筹精选 (005827)
- 持仓: 20000元 | 成本净值: 2.15 | 当前: 2.03
- 盈亏: -5.6% | 持有: 280天

**决策**: 建议观望
**理由**:
1. 短期处于成本附近，无明确趋势
2. 近5日震荡，缺乏动能
3. 所属大盘板块压力暂未缓解

**建议操作**:
- 暂不加仓，等待回调确认
- 若回调至成本下方，可考虑加仓

---

[详细分析...]

## 全局风险提示
- ⚠️ 权重股压力持续
- ⚠️ 流动性可能收紧
- ⚠️ 中概股波动加大
```

---

### 6.4 多渠道推送实现 (push_tools.py)

| 渠道 | 入口 | 实现 | 推送内容 |
|------|------|------|--------|
| **Bark** | `BARK_URL` | HTTP POST | 推送通知 + 简报卡片 |
| **Server酱** | `SERVERCHAN_KEY` | HTTP POST to sct.ftqq.com | Markdown 格式完整报告 |
| **企业微信** | `WECOM_WEBHOOK_URL` | HTTP POST | 卡片格式（支持交互按钮） |
| **Web 实时更新** | WebSocket/HTTP | 前端轮询 /api/briefing | JSON 响应 |
| **API 响应** | REST API | JSON | 完整 Briefing 对象 |

---

## 七、API 端点完整清单

### 7.1 持仓管理端点

| 端点 | 方法 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| `/api/portfolio` | GET | — | `{"holdings": [...], "count": N}` | 获取当前持仓 |
| `/api/portfolio/add-text` | POST | `{"text": "..."}` | `{"added": [...], "total": N}` | 自然语言录入（保存） |
| `/api/portfolio/parse-text` | POST | `{"text": "..."}` | `{"parsed": [...]}` | 自然语言解析（只解析） |
| `/api/portfolio/add-screenshot` | POST | `file: (binary)` | `{"added": [...], "total": N}` | 截图识别（保存） |
| `/api/portfolio/parse-screenshot` | POST | `file: (binary)` | `{"parsed": [...]}` | 截图识别（只解析） |
| `/api/portfolio/{fund_code}` | DELETE | — | `{"deleted": "...", "remaining": N}` | 删除持仓 |
| `/api/portfolio/refresh` | POST | `{"holdings": [...]}` | `{"holdings": [...]}` | 刷新净值和收益率 |

### 7.2 分析输出端点

| 端点 | 方法 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| `/api/briefing` | POST | `{"holdings": [...]}` | `BriefingResponse` | 生成简报（不推送） |
| `/api/briefing-and-push` | POST | `{"holdings": [...]}` | 简报 + 推送结果 | 生成简报并推送 |
| `/api/fund-diagnosis` | POST | `{"fund_code": "..."}` | `FundDiagnosisResponse` | 基金诊断 |
| `/api/fund-explanation` | POST | `{"fund_code": "..."}` | `FundExplanationResponse` | 涨跌原因分析 |
| `/api/estimation` | GET/POST | — / `{"holdings": [...]}` | 实时估值数据 | 盘中估值 |
| `/api/fund/{fund_code}/nav-history` | GET | `?start=...&end=...` | `{"nav_list": [...]}` | 历史净值 |

### 7.3 系统管理端点

| 端点 | 方法 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| `/api/config` | GET/POST | `{key, value}` | 配置信息 | 获取/更新配置 |
| `/api/push/status` | GET/POST | — / `{config}` | 推送渠道状态 | 检查推送配置 |
| `/api/push/test` | POST | `{config}` | 推送结果 | 测试推送 |
| `/api/logs` | GET/DELETE | `?limit=200&level=...` | 日志列表 | 查看/清空日志 |
| `/api/version` | GET | — | 版本信息 | 获取版本 |
| `/api/health` | GET | — | `{"status": "ok"}` | 健康检查 |

---

## 八、数据持久化机制

### 8.1 存储结构

```
project/
├── data/
│   └── portfolio.json          # 持仓数据（JSON 格式）
│
└── .env                         # 环境配置（推送 Key、API 配置）
```

### 8.2 portfolio.json 格式

```json
[
  {
    "fund_code": "005827",
    "fund_name": "易方达蓝筹精选",
    "cost": 20000,
    "cost_nav": 2.15,
    "current_nav": 2.03,
    "profit_ratio": -5.6,
    "hold_days": 280,
    "trend_5d": [-0.5, 1.2, -0.8, 0.3, 2.1],
    "ma5": 2.05,
    "ma10": 2.08,
    "ma_status": "震荡"
  },
  {...}
]
```

### 8.3 加载与保存

```python
# portfolio_tools.py
load_portfolio() → list[FundHolding]
save_portfolio(portfolio) → None

# 示例
holdings = load_portfolio()       # 从 JSON 读取
holdings[0]['cost'] = 25000       # 修改
save_portfolio(holdings)          # 写回 JSON
```

---

## 九、决策引擎工作原理

### 9.1 规则引擎 + LLM 双层策略

```
持仓数据 + 市场数据
    ▼
┌─────────────────────────────────────┐
│ 规则引擎（确定性决策）              │
├─────────────────────────────────────┤
│ IF 浮盈 > 10% & 趋势上涨             │
│   → action = "减仓" (止盈)          │
│                                     │
│ IF 浮亏 > 10% & 企稳 & 低波动        │
│   → action = "加仓" (补仓)          │
│                                     │
│ ELSE                                │
│   → action = "观望"                 │
└────────┬────────────────────────────┘
         ▼
┌─────────────────────────────────────┐
│ LLM 润色（自然语言生成）             │
├─────────────────────────────────────┤
│ "根据规则结果和市场背景，生成     │
│  自然、专业的建议和理由"           │
└────────┬────────────────────────────┘
         ▼
FundAdvice 对象 (含 action, reason, confidence)
```

### 9.2 决策规则矩阵

| 浮盈/亏 | 趋势上涨 | 趋势下跌 | 震荡 |
|--------|--------|--------|------|
| **浮盈 > 10%** | 🔴 减仓 | ⏸️ 观望 | ⏸️ 观望 |
| **浮亏 > 10%** | ⏸️ 观望 | ⏸️ 观望（等企稳） | 🟢 加仓 |
| **盈亏 ≤ 10%** | ⏸️ 观望 | ⏸️ 观望 | ⏸️ 观望 |

---

## 十、端到端工作流示例

### 10.1 场景1：新用户通过 Web UI 录入持仓

```
1. 用户打开 http://localhost:8000
   ↓
2. 前端显示"新增持仓"表单
   ↓
3. 用户输入：
   - 基金：易方达蓝筹精选
   - 金额：20000元
   - 成本净值：2.15
   ↓
4. 点击"添加"按钮
   ↓
5. 前端 POST /api/portfolio/add-text
   {
     "text": "易方达蓝筹精选 20000元 成本2.15",
     "config": {}
   }
   ↓
6. 后端处理：
   - nlp_input.parse_natural_language() 解析
   - verify_and_fix_fund() 校正基金代码
   - 合并到 portfolio.json
   ↓
7. 自动调用 /api/briefing 生成建议
   ↓
8. 前端显示：
   - 添加成功提示
   - 今日操作建议卡片
   ↓
9. 用户可选择推送到手机
```

### 10.2 场景2：截图识别并自动生成简报

```
1. 用户打开 Web → 点击"截图识别"
   ↓
2. 前端打开文件上传窗口
   ↓
3. 用户选择基金App截图
   ↓
4. 前端 POST /api/portfolio/add-screenshot
   (multipart form-data 含图片二进制)
   ↓
5. 后端处理：
   a. 保存临时文件
   b. ocr_tools.process_screenshot()
      - Vision LLM 直接识别 OR PaddleOCR 回退
      - 识别：基金名、持仓金额、收益率
   c. verify_and_fix_fund() 校正代码
   d. 加载旧持仓 → 合并新数据 → 保存
   ↓
6. API 响应识别结果
   ↓
7. 前端显示"识别到X只基金"
   ↓
8. 自动调用 LangGraph 生成简报
   ↓
9. 推送到 Bark / Server酱 / 企业微信
```

### 10.3 场景3：定时每日简报推送

```
1. 系统启动时：
   - 读取 .env 中的 PUSH_TIME (默认 14:30)
   - APScheduler 注册定时任务
   ↓
2. 每天 14:30 触发 _scheduled_push():
   a. 调用 langgraph_app.invoke({"trigger": "daily_briefing"})
   b. 执行 Portfolio Agent (加载持仓、刷新净值)
   c. 执行 Market Agent (获取板块数据、市场情绪)
   d. 执行 Briefing Agent (生成建议)
   ↓
3. 格式化输出：
   - 推送通知 (50字)
   - 卡片 (200字)
   - 完整报告 (2000字)
   ↓
4. 推送到所有已配置渠道：
   - Bark: 发送通知
   - Server酱: 发送 Markdown
   - 企业微信: 发送交互卡片
   ↓
5. 日志记录成功/失败状态
```

---

## 十一、用户数据流安全考量

### 11.1 敏感信息处理

```
配置项              是否敏感   处理方式
────────────────────────────────────────
OPENAI_API_KEY      是        前端显示 sk-****[后4位]
SERVERCHAN_KEY      是        前端显示 ****[后4位]
BARK_URL            否        明文显示
持仓数据            否        本地存储 (data/portfolio.json)
推送记录            否        内存日志 (500行)
```

### 11.2 API 安全特性

- **CORS 开放**: 允许所有来源（生产环境需改进）
- **白名单配置**: 只允许修改特定环保变量 (ALLOWED_KEYS)
- **脱敏显示**: `/api/config` 返回时自动脱敏敏感键值
- **日志收集**: 内存环形缓冲 (500 行)，防止日志爆炸

---

## 十二、性能与可扩展性

### 12.1 数据量级

```
典型用户:
- 持仓数量: 5-20只
- portfolio.json 大小: ~5KB
- API 响应时间: 100-500ms

高并发应对:
- FastAPI 异步处理
- 估值缓存 (每10分钟刷新一次)
- LLM 调用超时: 30-45秒
```

### 12.2 瓶颈分析

| 操作 | 瓶颈 | 优化方向 |
|------|------|--------|
| 截图识别 | Vision LLM API 调用 (5-10s) | 加缓存、本地模型 |
| 自然语言解析 | NLP LLM 调用 (3-5s) | prompt 缓存、更快的模型 |
| 市场数据 | AKShare API 调用 (1-3s) | 本地数据库 + 定时预热 |
| 简报生成 | LLM 文本生成 (5-10s) | prompt 优化、流式响应 |

---

## 十三、项目代码统计

```
src/tools/        11 个工具模块 (~900 行)
src/agents/       3-4 个 Agent (~800 行)
src/              核心模块 (~400 行)
server.py         FastAPI 应用 (~800 行)
web/index.html    前端单页应用 (~2000 行)
────────────────────────────
总计             ~5800 行代码
```

---

## 十四、关键设计决策

### 14.1 为什么采用三层递进输出？

```
推送通知 (50字)    ← 1秒内响应，吸引用户点击
      ↓
卡片展示 (200字)   ← 关键信息 + 行动号召
      ↓
完整报告 (2000字)  ← 深度分析，满足专业用户
```

**好处**:
- 懒人设计：多数用户只看推送
- 渐进式交互：感兴趣才看详情
- 兼容多渠道：Bark/Server酱/企微各有最优形式

### 14.2 为什么用规则引擎 + LLM？

```
规则引擎:
✓ 确定性强，可解释
✓ 无 API Key 时也能跑
✗ 过于机械，输出不自然

+ LLM 润色:
✓ 生成自然语言解释
✓ 规则无法覆盖的灰度决策
✗ 需要 API 调用，有成本
```

**折衷**: 规则决策 → LLM 生成理由

### 14.3 为什么 portfolio.json 而不是数据库？

```
JSON:
✓ 零依赖，开箱即用
✓ 便于版本控制、备份
✓ 小型项目足够
✗ 并发写入有风险

→ MVP 阶段够用，后期可升级为 SQLite / PostgreSQL
```

---

## 十五、总结与建议

### 核心数据流

```
用户输入 (5种方式) 
  → 统一数据结构 (FundHolding)
    → Agent 处理链 (LangGraph)
      → 决策引擎 (规则 + LLM)
        → 三层输出 (通知 / 卡片 / 报告)
          → 多渠道推送 (Bark / Server酱 / 企微)
```

### 用户获得的数据

| 数据类型 | 格式 | 实时性 | 获取方式 |
|--------|------|-------|--------|
| **持仓汇总** | JSON | 实时 | `/api/portfolio` |
| **操作建议** | 结构化文本 | 每日定时 | `/api/briefing` |
| **盘中估值** | JSON | 10分钟 | `/api/estimation` |
| **历史净值** | 数组 | 历史 | `/api/fund/.../nav-history` |
| **风险提示** | 列表 | 实时 | Briefing 中 |

### 下一步优化方向

1. **多用户支持**: 当前单用户，需加用户认证 + 隔离
2. **Chat 入口**: 开放对话 API，支持自由问答
3. **智能定投**: 根据估值动态调整投资金额
4. **历史分析**: 记录建议执行效果，改进算法
5. **本地 LLM**: 离线模型替代 API 调用

