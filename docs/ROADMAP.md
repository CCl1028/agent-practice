# FundPal — 产品需求迭代计划

> 维护人: FundPal Team  
> 最后更新: 2026-04-22  
> 当前版本: v1.2.0

---

## 一、产品愿景

> "你的基金，我盯着。有事我叫你，没事别操心。"

一个基于多 Agent 架构的基金投资助手，帮用户盯盘、判断、只在该说话时说话。从"用户主动查"变成"系统主动推"，让投资决策变得简单。

---

## 二、版本发布历史

### v1.0.0 — MVP（2026-03，已发布 ✅）

**主题：** 跑通核心 Agent 链路

| 功能 | 描述 | 状态 |
|------|------|------|
| 多 Agent 工作流 | Supervisor → Portfolio → Market → Briefing 串行编排 | ✅ |
| 持仓管理 | JSON 文件存取，CLI 录入 | ✅ |
| 每日简报 | 规则引擎（2 维：盈亏×趋势）+ LLM 润色 | ✅ |
| 三层递进输出 | 推送通知（50字）→ 卡片（200字）→ 报告（2000字） | ✅ |
| 多渠道推送 | Bark / Server酱 / 企业微信 | ✅ |
| 截图识别 | Vision LLM + PaddleOCR 降级 | ✅ |
| 自然语言录入 | LLM 意图识别 + 实体提取 | ✅ |
| Web UI | 移动端优先的 SPA 页面 | ✅ |
| Docker 部署 | 多阶段构建 + Nginx HTTPS 反向代理 | ✅ |
| APScheduler | 每日定时推送 | ✅ |

---

### v1.1.0 — 交易管理（2026-04-02，已发布 ✅）

**主题：** 交易记录全留痕 + 定投自动化

| 功能 | 描述 | 状态 |
|------|------|------|
| 加仓/减仓 | 卡片按钮 + 自然语言两种方式 | ✅ |
| 交易记录 | Transaction 数据模型，每笔交易留痕 | ✅ |
| 定投计划 | 每天/每周/每两周/每月定投 | ✅ |
| 自动执行 | 打开页面自动检查待执行定投 | ✅ |
| 补执行 | 按历史净值逐笔补执行 | ✅ |
| 累积持仓 | 根据交易记录自动计算真实成本和收益 | ✅ |
| 历史净值 API | `GET /api/fund/{code}/nav-history` | ✅ |
| NLP 意图扩展 | 识别 buy/sell intent | ✅ |

---

### v1.2.0 — 盘中估值 & Web 设置（2026-04-03，已发布 ✅）

**主题：** 实时估值 + 在线配置管理

| 功能 | 描述 | 状态 |
|------|------|------|
| 盘中估值 | 交易时段实时估值，非交易时段收盘涨跌 | ✅ |
| 估值缓存 | 后台每 10 分钟自动刷新 | ✅ |
| Web 配置面板 | 在线配置推送渠道和 AI 模型 | ✅ |
| 测试推送 | 配置后发送测试消息验证 | ✅ |
| 应用日志 | 内存环形缓冲区，Web 端查看 | ✅ |
| 基金校验 | fund_code ↔ fund_name 双向校验修正 | ✅ |
| 版本信息 | Docker 构建时注入版本号和 commit | ✅ |

---

### v2.0.0 — 决策引擎升级（2026-04-09，已发布 ✅）

**主题：** 6 维决策引擎 + 多源数据 + 新闻情报

| 功能 | 描述 | 状态 |
|------|------|------|
| 6 维决策引擎 | 盈亏×趋势×乖离率×均线×波动率×持有时间 | ✅ |
| 交易纪律硬规则 | 追高检测、空头禁加仓、止盈不犹豫 | ✅ |
| 置信度评分 | 0-100 分量化评分 | ✅ |
| 风险提示 | 每基金独立风险 + 全局风险警报 | ✅ |
| 多源数据获取 | AKShare(P0) + Efinance(P1) 自动切换 | ✅ |
| 熔断机制 | 连续失败 3 次→冷却 5 分钟→自动恢复 | ✅ |
| 4 引擎新闻搜索 | Tavily / 博查 / Brave / SerpAPI | ✅ |
| 搜索缓存 | TTL 1 小时，LRU 上限 200 条 | ✅ |
| 技术指标 | MA5/MA10/MA20、均线排列、乖离率、波动率 | ✅ |
| "持有"操作 | 新增第 4 种操作类型 | ✅ |

---

### v3.0.0 — 基金分析（2026-04-10，已发布 ✅）

**主题：** 基金诊断 + 涨跌原因分析

| 功能 | 描述 | 状态 |
|------|------|------|
| 基金诊断 Agent | `fund_diagnosis_node` — 这只基金值不值得买？ | ✅ |
| 涨跌分析 Agent | `fall_reason_node` — 今天为什么涨/跌？ | ✅ |
| LangGraph 新路由 | `fund_diagnosis` / `fall_analysis` 两条新路径 | ✅ |
| 诊断 API | `POST /api/fund-diagnosis` | ✅ |
| 涨跌 API | `POST /api/fund-explanation` | ✅ |
| 诊断页面 | DiagnosisPage 前端页面 | ✅ |
| 数据结构 | FundDiagnosis / FallAnalysis TypedDict | ✅ |

---

## 三、当前迭代（进行中）

### v3.1.0 — 体验优化（规划中 🚧）

| 功能 | 描述 | 优先级 | 状态 |
|------|------|--------|------|
| Chat 对话入口 | 自然语言查询："我的基金怎么样了？" | P0 | 🚧 待开发 |
| 智能定投 | 根据估值百分位动态调整定投金额 | P1 | 🚧 待开发 |
| 持仓净值刷新优化 | 前端主动触发净值刷新时增加 loading 状态 | P1 | 🚧 待开发 |
| 多用户支持 | 用户认证 + 数据隔离 | P2 | 🚧 待开发 |

---

## 四、技术优化需求（Tech Debt & Optimization）

> 以下为代码分析中识别出的技术债务和优化点，按优先级分 Phase 规划。

### Tech Phase 1 — 🔴 高优先级（阻塞稳定性）✅ 已完成

#### T1.1 配置系统重构 ✅

| 编号 | 问题 | 影响 | 方案 | 状态 |
|------|------|------|------|------|
| T-001 | `config.py` 配置不可热更新：模块加载时快照 `os.getenv()`，Web UI 修改 API Key 后不生效（直到重启） | **严重**：用户以为配置成功实际无效 | 改为函数式获取 + `__getattr__` 兼容层，每次访问读 `os.getenv()` | ✅ |
| T-002 | 多处 `load_dotenv()` 执行顺序不确定（`config.py`、`news_tools.py`、`push_tools.py` 各调一次） | 配置值可能不一致 | 统一由 `server.py` 启动时调用一次 `load_dotenv()`，其他模块已移除 | ✅ |
| T-003 | 无配置验证：无效 URL、空 API Key 等不会在启动时发现 | 运行时才报错，排查困难 | 新增 `validate_config()` 函数，启动时校验并输出 warning 日志 | ✅ |

#### T1.2 并发安全修复 ✅

| 编号 | 问题 | 影响 | 方案 | 状态 |
|------|------|------|------|------|
| T-004 | `CircuitBreaker._states` 无锁保护（`data_provider.py`） | 多线程竞态导致熔断状态不一致 | 添加 `threading.Lock`，`is_available`/`record_failure`/`record_success` 全部加锁 | ✅ |
| T-005 | `_fund_name_cache` 无锁保护（`market_tools.py`），多线程首次调用可能重复加载全量数据 | 数据竞争、重复请求 | 新增 `_fund_name_cache_write_lock`，写入操作加锁保护 | ✅ |
| T-006 | `_search_cache` 无线程安全（`news_tools.py`），缓存淘汰时 `del` 非原子操作 | 并发读写可能 `RuntimeError` | 新增 `_search_cache_lock`，读写和淘汰全部加锁 | ✅ |

#### T1.3 LLM 调用健壮性 ✅

| 编号 | 问题 | 影响 | 方案 | 状态 |
|------|------|------|------|------|
| T-007 | `ChatOpenAI` 未配置 `request_timeout` 和 `max_retries` | LLM 服务不可用时请求无限期挂起 | 所有 `ChatOpenAI` 添加 `request_timeout=30` 和 `max_retries=2` | ✅ |
| T-008 | `langgraph_app.invoke()` 同步阻塞在 `async def` 路由中 | 阻塞 FastAPI 事件循环，影响所有并发请求 | 所有 4 个阻塞调用点使用 `asyncio.to_thread()` 包裹 | ✅ |
| T-009 | 整个工作流无全局超时控制 | 任一 Agent 卡住导致整个请求无限期挂起 | 所有 `asyncio.to_thread` 包裹 `asyncio.wait_for(timeout)` — 简报 120s / 诊断 60s | ✅ |
| T-010 | LLM JSON 解析脆弱：仅去除 markdown 代码块后 `json.loads()` | LLM 返回带注释/尾逗号/不完整 JSON 时全降级 | 新增 `_clean_json_text()` 辅助函数，清理尾逗号/注释/BOM | ✅ |

#### T1.4 安全加固 ✅

| 编号 | 问题 | 影响 | 方案 | 状态 |
|------|------|------|------|------|
| T-011 | CORS `allow_origins=["*"]`（`server.py`） | 任意网站可调用 API | 改为通过 `CORS_ORIGINS` 环境变量配置，默认只允许 localhost | ✅ |
| T-012 | Docker 容器以 root 用户运行（`Dockerfile`） | 容器内安全风险 | 添加 `appuser` 非 root 用户 + `USER appuser` + HEALTHCHECK | ✅ |
| T-013 | SPA fallback 未验证文件路径是否在 `static_dir` 内 | 理论上存在路径穿越风险 | 添加 `resolved.is_relative_to(static_dir.resolve())` 检查 | ✅ |

---

### Tech Phase 2 — 🟡 中优先级（改善可维护性）

#### T2.1 代码拆分重构

| 编号 | 问题 | 影响 | 方案 |
|------|------|------|------|
| T-014 | `server.py` 单文件 814 行，路由/调度/配置/静态文件全混在一起 | 职责混杂，难以维护 | 拆分为 `routes/briefing.py`、`routes/portfolio.py`、`routes/config.py`、`routes/push.py`、`scheduler.py` |
| T-015 | `market_tools.py` 单文件 796 行，集成 10+ 功能 | 函数过多，耦合严重 | 拆分为 `fund_name_resolver.py`、`estimation.py`、`nav.py`、`fund_profile.py` |
| T-016 | `data_provider.py` 与 `market_tools.py` 功能重叠：`get_fund_nav_multi_source` 未被主流程调用 | 死代码或未完成的重构 | 合并或明确调用关系；移除未使用的代码 |
| T-017 | 持仓合并逻辑重复（`server.py:246-252` vs `303-309`） | 相同逻辑两份，修一处漏另一处 | 提取为 `_merge_holdings()` 公共函数 |
| T-018 | GET/POST estimation 端点循环体完全重复（`server.py:462-471` vs `485-494`） | 重复代码 | 提取为 `_build_estimation_result()` |

#### T2.2 规则引擎可维护性

| 编号 | 问题 | 影响 | 方案 |
|------|------|------|------|
| T-019 | `_rule_engine()` 100+ 行嵌套 if-elif-else（`briefing_agent.py:64-171`） | 新增规则需理解整个函数 | 重构为规则列表 + 优先级的声明式配置模式 |
| T-020 | `_rate_fund()` 阈值全部硬编码（`analysis_agent.py:100-187`） | 无法通过配置调整 | 提取为配置文件或常量类 |
| T-021 | `fund_diagnosis_node` 和 `fall_reason_node` 结构高度重复（`analysis_agent.py`） | 相同模板代码两份 | 提取为模板方法基类 |

#### T2.3 错误处理统一

| 编号 | 问题 | 影响 | 方案 |
|------|------|------|------|
| T-022 | `server.py` 多处手动 `from fastapi.responses import JSONResponse` 返回错误 | 错误响应格式不一致 | 使用 FastAPI `HTTPException` + 统一 `@app.exception_handler` |
| T-023 | `graph.py` 无错误恢复：任何节点异常导致整个工作流失败 | Market Agent 失败时应仍可用 Portfolio 数据生成简报 | 每个节点包裹 try-except，失败时写 `state["error"]` 并跳过 |
| T-024 | 前端 `api.ts` 错误处理逻辑重复（`parseText` 和 `parseScreenshot`） | 重复代码 | 提取为 `handleApiError()` |

#### T2.4 依赖管理

| 编号 | 问题 | 影响 | 方案 |
|------|------|------|------|
| T-025 | `requirements.txt` 依赖版本无上限（`langchain>=0.3.0`） | 可能安装到破坏性更新版本 | 改为 `langchain>=0.3.0,<1.0` 或使用 `pip-compile` 生成锁文件 |
| T-026 | 缺少 `requirements-dev.txt`：pytest、pytest-cov 等未列出 | 开发环境不一致 | 添加开发依赖文件 |

#### T2.5 Docker & 部署

| 编号 | 问题 | 影响 | 方案 |
|------|------|------|------|
| T-027 | 无 Docker HEALTHCHECK（Dockerfile & docker-compose.yml） | Docker 不知道容器是否健康 | 添加 `HEALTHCHECK CMD curl -f http://localhost:8000/api/health \|\| exit 1` |
| T-028 | `docker-compose.yml` 使用废弃的 `version: "3.8"` | 警告信息 | 移除 version 字段（Compose V2 不需要） |
| T-029 | PyPI 镜像源硬编码为清华源（`Dockerfile:19`） | 海外 CI/CD 可能更慢 | 通过 `ARG PIP_INDEX_URL` 配置化 |
| T-030 | certbot 容器无自动续期机制 | 证书过期需手动处理 | 添加 cron 定时 `certbot renew` |

#### T2.6 前端优化

| 编号 | 问题 | 影响 | 方案 |
|------|------|------|------|
| T-031 | `api.ts` 无请求超时机制 | 浏览器默认超时很长，用户等待体验差 | 使用 `AbortController` + `setTimeout` |
| T-032 | `api.ts` 无请求重试 | 网络波动时直接失败 | 添加 1 次自动重试（非幂等接口除外） |
| T-033 | `localStorage` 无容量保护 | 超过 5MB 限制写入失败但不通知用户 | 写入前检查大小，超限时提示用户清理 |
| T-034 | `recalcHolding` 副作用过重：函数名暗示纯计算但实际修改 localStorage | 违反最小意外原则 | 拆分为 `calcHolding()`（纯计算）和 `updateHolding()`（副作用） |

---

### Tech Phase 3 — 🟢 低优先级（锦上添花）

#### T3.1 性能优化

| 编号 | 问题 | 影响 | 方案 |
|------|------|------|------|
| T-035 | `_fetch_fund_estimation` 每次拉取全量估值表再过滤一条（`market_tools.py:316`） | 极度浪费带宽 | 交易时段批量拉取一次全量表缓存到内存，单个查询直接查内存 |
| T-036 | `get_fund_perf_analysis` 重复调用 `get_sector_performance()`（`market_tools.py:671,675`） | 两次相同外部请求 | 复用第一次的结果 |
| T-037 | `ChatOpenAI` 每次调用都实例化 | 不利于连接池复用 | 模块级缓存实例 |
| T-038 | `TavilyClient` 每次实例化（`news_tools.py:190`） | 不利于连接复用 | 缓存客户端实例 |
| T-039 | Portfolio Agent 和 Market Agent 串行执行但无数据依赖（`graph.py:71`） | 耗时叠加 | 升级为 LangGraph fan-out/fan-in 并行执行 |

#### T3.2 代码质量

| 编号 | 问题 | 影响 | 方案 |
|------|------|------|------|
| T-040 | Mock 数据重复定义（`market_tools.py:424-443` vs `534-544`） | 维护两份相同数据 | 提取为单一 `_MOCK_FUNDS` 常量 |
| T-041 | `get_market_news()` 硬编码 Mock 未集成真正搜索（`market_tools.py:519`） | 功能不完整 | 集成 `news_tools.search_market_news()` |
| T-042 | Mock 数据混入生产逻辑：`_get_mock_sectors` 在 `get_fund_profile` 中被调用 | 重仓行业数据始终为 Mock | 从 AKShare 持仓接口获取真实数据 |
| T-043 | `asyncio.get_event_loop()` 已废弃（`server.py:267`） | 某些环境可能报警告 | 改为 `asyncio.get_running_loop()` |
| T-044 | 裸 `except:` 无异常类型（`market_tools.py:608`） | 吞掉所有异常，难以调试 | 改为 `except (ValueError, TypeError):` |
| T-045 | `.env` 手工解析器不支持引号/多行值（`server.py:589-636`） | 特殊值解析错误 | 使用 `python-dotenv` 的 `dotenv_values()` / `set_key()` |

#### T3.3 测试覆盖率提升

| 编号 | 问题 | 影响 | 方案 |
|------|------|------|------|
| T-046 | 核心模块零测试：`server.py`（路由）、`graph.py`（工作流）、`briefing_agent._rule_engine`（规则引擎）、`analysis_agent._rate_fund`（评分）、`news_tools`、`data_provider`（熔断器）、`push_tools`、`formatter`、`config` | 无法保证回归质量 | 分批补充单元测试，优先覆盖规则引擎和熔断器 |
| T-047 | 无集成测试：无 `graph.invoke()` 端到端测试，无 API 路由集成测试 | 模块间集成问题无法发现 | 添加 pytest + httpx 的 API 集成测试 |
| T-048 | `test_p4_confirm_flow.py` 测试旧版 HTML 前端，与 React 版本脱节 | 测试已过时，100% 会失败 | 删除或重写为 React 组件测试 |
| T-049 | `test_trading_logic.py` 测试 Python 重实现而非实际前端代码 | 实现不一致风险 | 补充 Playwright/Vitest 前端测试 |

---

## 五、未来 Roadmap（产品功能）

### Phase 4 — Chat & 智能化

| 功能 | 描述 |
|------|------|
| Chat 对话入口 | Supervisor 意图识别 → 路由到对应 Agent |
| 对话上下文 | 支持多轮对话，记住上下文 |
| 智能定投 | 估值低→加倍投，估值高→减少投 |
| 个性化建议 | 根据用户风险偏好调整建议力度 |

### Phase 5 — 数据 & 多端

| 功能 | 描述 |
|------|------|
| 数据存储升级 | JSON → SQLite → PostgreSQL |
| 多用户支持 | 用户认证、数据隔离 |
| 历史建议回溯 | 记录建议执行效果，改进算法 |
| 交易统计 | 月度/年度交易汇总、收益曲线图 |
| 导出功能 | 交易记录导出为 CSV |

### Phase 6 — 接入 & 扩展

| 功能 | 描述 |
|------|------|
| 微信/企微对话入口 | 直接在微信内对话 |
| 本地 LLM | 离线模型替代 API 调用 |
| 券商 API 接入 | 自动同步持仓（需合规评估） |
| 组合分析 | 持仓整体的行业分布、风险暴露分析 |

---

## 六、需求管理规范

### 需求分类

| 类型 | 标签 | 说明 |
|------|------|------|
| 新功能 | `feature` | 新增的产品能力 |
| 优化 | `enhancement` | 对现有功能的改进 |
| 修复 | `bugfix` | Bug 修复 |
| 重构 | `refactor` | 技术重构，不影响用户可见行为 |
| 技术债务 | `tech-debt` | 技术优化，提升稳定性/性能/可维护性 |
| 文档 | `docs` | 文档更新 |

### 优先级定义

| 等级 | 说明 |
|------|------|
| P0 | 必须做，阻塞版本发布 |
| P1 | 应该做，重要但不阻塞 |
| P2 | 可以做，锦上添花 |
| P3 | 以后做，记录备忘 |

### 版本号规范

遵循 [语义化版本](https://semver.org/lang/zh-CN/)：`v{主版本}.{次版本}.{修订号}`

| 变更类型 | 版本号变化 | 举例 |
|---------|-----------|------|
| 不兼容的 API 修改 | 主版本号 +1 | v1.x.x → v2.0.0 |
| 新增功能（向下兼容） | 次版本号 +1 | v1.1.x → v1.2.0 |
| Bug 修复 | 修订号 +1 | v1.2.0 → v1.2.1 |
