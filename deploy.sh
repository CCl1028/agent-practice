#!/bin/bash
# 部署脚本 — 自动注入版本信息并构建部署

export GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
export BUILD_TIME=$(date '+%Y-%m-%d %H:%M')
export BUILD_VERSION="1.0.0"

echo "🚀 部署版本: ${GIT_COMMIT:0:7} | ${BUILD_TIME}"

docker compose down
docker compose up -d --build

echo "✅ 部署完成"
docker logs fund-assistant --tail 5
