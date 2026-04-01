FROM python:3.11-slim

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建数据目录
RUN mkdir -p data

EXPOSE 8000

# 启动 API 服务（定时推送由应用内 APScheduler 管理）
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
