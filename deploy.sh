#!/bin/bash
# 部署脚本 — 在服务器上执行
# 用法: ssh root@106.52.248.165 "cd ~/agent-practice && bash deploy.sh"

set -e

BRANCH="main"

echo "📦 拉取最新代码 (${BRANCH})..."
git fetch origin
git checkout ${BRANCH}
git reset --hard origin/${BRANCH}

export GIT_COMMIT=$(git rev-parse HEAD)
export BUILD_TIME=$(date '+%Y-%m-%d %H:%M')
export BUILD_VERSION="1.0.0"

echo "🚀 部署版本: ${GIT_COMMIT:0:7} | ${BUILD_TIME}"

docker compose down
docker compose up -d --build

echo ""
echo "✅ 部署完成"
echo "   版本: ${GIT_COMMIT:0:7}"
echo "   时间: ${BUILD_TIME}"
echo ""
docker logs fund-assistant --tail 5
