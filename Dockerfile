# ---- Stage 1: Build frontend ----
FROM node:20-alpine AS frontend-builder

WORKDIR /web
COPY web/package.json web/package-lock.json* ./
RUN npm install
COPY web/ .
# Rename vite entry html for build
RUN cp index.vite.html index.html
RUN npm run build

# ---- Stage 2: Python app ----
FROM python:3.11-slim

WORKDIR /app

# T-012: 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# 安装 Python 依赖（T-029: PIP 镜像源可配置）
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i ${PIP_INDEX_URL}

# 复制项目代码
COPY . .

# 复制前端构建产物到 web/dist
COPY --from=frontend-builder /web/dist /app/web/dist

# 版本信息（构建时注入，放在 COPY 之后避免被覆盖）
ARG BUILD_TIME=unknown
ARG GIT_COMMIT=unknown
RUN if [ -f /app/version.json ]; then \
      BASE_VERSION=$(python -c "import json; print(json.load(open('/app/version.json')).get('version','dev'))"); \
      CODENAME=$(python -c "import json; print(json.load(open('/app/version.json')).get('codename',''))"); \
    else \
      BASE_VERSION="dev"; \
      CODENAME=""; \
    fi && \
    echo "{\"version\":\"${BASE_VERSION}\",\"codename\":\"${CODENAME}\",\"build_time\":\"${BUILD_TIME}\",\"git_commit\":\"${GIT_COMMIT}\"}" > /app/version.json

# 创建数据目录并设置权限
RUN mkdir -p data && chown -R appuser:appuser /app

# T-012: 切换到非 root 用户
USER appuser

EXPOSE 8000

# T-027: 添加 Docker 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
