# FundPal 项目规则

## 项目概览

FundPal 是一个基于多 Agent 架构的基金投资助手，使用 LangGraph + FastAPI + React + Docker 构建。核心理念："你的基金，我盯着。有事我叫你，没事别操心。"

## 文档维护规则

### 核心文档清单

本项目维护以下三份核心文档，**每次大规模更新代码或功能时必须同步更新**：

| 文档 | 路径 | 用途 | 何时更新 |
|------|------|------|---------|
| 产品需求迭代计划 | `docs/ROADMAP.md` | 版本历史、功能状态、未来规划 | 新增/完成功能、发布新版本、调整路线图 |
| 产品技术方案 | `docs/TECHNICAL.md` | 技术选型、模块设计、API 设计 | 新增技术组件、变更架构、新增 API |
| 产品架构说明 | `docs/ARCHITECTURE.md` | 架构全景、Agent 协作、数据流、设计模式 | 新增 Agent、变更数据流、新增设计模式 |

### 文档更新触发条件

以下操作**必须**同步更新相关文档：

1. **新增或修改 Agent** (`src/agents/`)
   - 更新 `ARCHITECTURE.md`: Agent 职责矩阵、工作流路径、State 流转
   - 更新 `TECHNICAL.md`: 工作流编排部分
   - 更新 `ROADMAP.md`: 标记功能状态

2. **新增或修改 API 端点** (`server.py`)
   - 更新 `TECHNICAL.md`: API 端点总览
   - 更新 `ARCHITECTURE.md`: 如涉及新数据流

3. **新增或修改工具模块** (`src/tools/`)
   - 更新 `TECHNICAL.md`: 核心模块设计对应部分
   - 更新 `ARCHITECTURE.md`: 工具层列表、外部服务层

4. **修改 State 定义** (`src/state.py`)
   - 更新 `TECHNICAL.md`: 状态管理部分
   - 更新 `ARCHITECTURE.md`: State 流转图

5. **新增前端页面或重大 UI 变更** (`web/src/`)
   - 更新 `TECHNICAL.md`: 前端架构部分
   - 更新 `ARCHITECTURE.md`: 目录结构

6. **变更部署方式** (`Dockerfile`, `docker-compose.yml`, `nginx/`)
   - 更新 `TECHNICAL.md`: 部署架构部分
   - 更新 `ARCHITECTURE.md`: 部署架构图

7. **新增依赖** (`requirements.txt`, `web/package.json`)
   - 更新 `TECHNICAL.md`: 技术栈总览和关键依赖

8. **发布新版本** (`version.json`)
   - 更新 `ROADMAP.md`: 版本发布历史、当前迭代状态
   - 更新 `TECHNICAL.md`: 文件头部版本号
   - 更新 `ARCHITECTURE.md`: 文件头部版本号

### 文档更新格式规范

- 文档头部的 `最后更新` 日期必须更新为当天
- 版本号与 `version.json` 保持一致
- 使用 Markdown 表格展示结构化信息
- 架构图使用 ASCII 文本图
- 新增功能需标注状态：✅ 已完成 / 🚧 进行中 / 📋 待开发

---

## 代码规范

### Python 后端

- Python 3.11+，使用 type hints
- 所有模块使用 `from __future__ import annotations`
- 使用 `logging` 模块记录日志，格式：`logger = logging.getLogger(__name__)`
- Agent 节点函数签名：`def xxx_node(state: AgentState) -> dict`
- 工具函数需要有 docstring 说明入参和返回值
- 配置统一在 `src/config.py`，通过环境变量加载
- 异常处理：每层都有兜底（优雅降级原则）

### React 前端

- React 18 + TypeScript + Vite
- 组件使用函数式组件 + Hooks
- 数据存储使用 localStorage（`store.ts` 统一管理）
- API 调用统一在 `api.ts`
- 类型定义在 `types.ts`
- 移动端优先设计

### 命名规范

- Python: snake_case（函数、变量）、PascalCase（类、TypedDict）
- TypeScript: camelCase（函数、变量）、PascalCase（组件、类型）
- 文件名: snake_case（Python）、PascalCase（React 组件）
- Agent 节点: `xxx_node` 函数名 + `xxx_agent` LangGraph 节点名

### Git 规范

- 版本号遵循语义化版本：`v{主版本}.{次版本}.{修订号}`
- 版本信息维护在 `version.json`
- Docker 构建时自动注入 `build_time` 和 `git_commit`

---

## 架构约束

### 优雅降级原则

系统的每一层都必须有降级方案，确保在外部依赖不可用时核心功能仍可运行：

```
LLM 不可用        → 使用规则引擎结果
AKShare 不可用    → Efinance 备用 → Mock 数据
Vision LLM 失败   → PaddleOCR 降级 → 空数组
新闻 API 无 Key   → 跳过新闻（不阻塞主流程）
推送渠道失败      → 跳过该渠道（不影响其他渠道）
```

### Agent 设计原则

1. **单一职责** — 每个 Agent 只负责一个领域
2. **状态隔离** — 通过 AgentState 传递数据，不直接耦合
3. **工具绑定** — 每个 Agent 使用自己领域的工具
4. **可降级** — 每个 Agent 都有无 LLM 时的降级逻辑

### 扩展点

新增功能时遵循以下扩展模式：

| 扩展类型 | 操作步骤 |
|---------|---------|
| 新增 Agent | ① 实现节点函数 ② graph.add_node() ③ supervisor_router 加路由 ④ add_edge |
| 新增数据源 | ① 继承 BaseFundFetcher ② 实现 get_nav/get_estimation ③ 注册到 fetcher 列表 |
| 新增推送渠道 | ① 实现 push_to_xxx() ② 加入 push_briefing() ③ config.py 加配置 ④ ALLOWED_KEYS 注册 |
| 新增前端页面 | ① pages/ 创建组件 ② App.tsx 注册 ③ TabBar 加 Tab 项 |
| 新增 API | ① server.py 加路由 ② 定义 Pydantic Model ③ 更新文档 |

---

## 测试规范

- 测试文件放在 `tests/` 目录
- 使用 `pytest` 框架
- 命名规范: `test_xxx.py`
- 关键业务逻辑（交易计算、规则引擎）必须有单元测试

---

## 部署规范

- 使用 Docker 多阶段构建（Stage 1: 前端, Stage 2: 后端）
- docker-compose 编排 3 个服务：fund-assistant + nginx + certbot
- 数据卷挂载：`./data` (持仓) + `./.env` (配置)
- 时区设置：`TZ=Asia/Shanghai`
- 自动部署脚本：`deploy.sh`（git pull → 证书检查 → docker compose up）
