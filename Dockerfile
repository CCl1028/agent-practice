FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建数据目录
RUN mkdir -p data

# 配置每日定时任务（每天早上 8:00 运行简报）
RUN echo "0 8 * * * cd /app && python main.py >> /var/log/briefing.log 2>&1" > /etc/cron.d/briefing \
    && chmod 0644 /etc/cron.d/briefing \
    && crontab /etc/cron.d/briefing

EXPOSE 8000

# 启动：同时运行 cron（定时简报）和 API 服务
CMD cron && uvicorn server:app --host 0.0.0.0 --port 8000
