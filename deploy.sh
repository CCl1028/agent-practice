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

echo "🚀 部署版本: ${GIT_COMMIT:0:7} | ${BUILD_TIME}"

# 自签名证书：不存在则自动生成
CERT_DIR="./certbot/conf/selfsigned"
if [ ! -f "${CERT_DIR}/fullchain.pem" ]; then
    echo "🔐 生成自签名 SSL 证书..."
    mkdir -p "${CERT_DIR}"
    openssl req -x509 -nodes -days 3650 \
        -newkey rsa:2048 \
        -keyout "${CERT_DIR}/privkey.pem" \
        -out "${CERT_DIR}/fullchain.pem" \
        -subj "/CN=106.52.248.165" \
        -addext "subjectAltName=IP:106.52.248.165"
    echo "✅ 证书已生成"
fi

docker compose down
GIT_COMMIT="${GIT_COMMIT}" BUILD_TIME="${BUILD_TIME}" \
  docker compose up -d --build

echo ""
echo "✅ 部署完成"
echo "   版本: ${GIT_COMMIT:0:7}"
echo "   时间: ${BUILD_TIME}"
echo "   访问: https://106.52.248.165"
echo ""
docker logs fund-assistant --tail 5
