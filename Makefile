# ============================================
# FundPal — 常用开发命令
# ============================================

.PHONY: help install lint format typecheck test test-cov ci clean

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ---- 安装 ----

install: ## 安装所有依赖（生产 + 开发）
	pip install -r requirements-dev.txt

install-prod: ## 仅安装生产依赖
	pip install -r requirements.txt

# ---- 代码质量 ----

lint: ## 运行 ruff 检查
	ruff check src/ server.py main.py

format: ## 自动格式化代码
	ruff format src/ server.py main.py
	ruff check --fix src/ server.py main.py

typecheck: ## 运行 mypy 类型检查
	mypy src/ server.py --ignore-missing-imports

# ---- 测试 ----

test: ## 运行单元测试
	pytest -x -v

test-cov: ## 运行测试 + 覆盖率报告
	pytest --cov=src --cov=server --cov-report=term-missing --cov-report=html -x

# ---- 复合命令 ----

ci: lint typecheck test ## 本地模拟 CI（lint + typecheck + test）

# ---- 依赖锁定 ----

lock: ## 使用 pip-compile 锁定依赖版本
	pip-compile requirements.in -o requirements.txt --strip-extras --no-header

# ---- 清理 ----

clean: ## 清理缓存文件
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml
