FROM python:3.11-slim

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码
COPY . .

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

# 创建数据目录
RUN mkdir -p data

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
