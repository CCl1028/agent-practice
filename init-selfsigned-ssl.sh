#!/bin/bash
# 自签名 SSL 证书初始化脚本（无需域名）
# 用法: ssh root@106.52.248.165 "cd ~/agent-practice && bash init-selfsigned-ssl.sh"

set -e

IP="106.52.248.165"
CERT_DIR="./certbot/conf/selfsigned"

echo "🔐 为 ${IP} 生成自签名 SSL 证书..."

mkdir -p "${CERT_DIR}"

# 生成自签名证书（有效期 10 年）
openssl req -x509 -nodes -days 3650 \
    -newkey rsa:2048 \
    -keyout "${CERT_DIR}/privkey.pem" \
    -out "${CERT_DIR}/fullchain.pem" \
    -subj "/CN=${IP}" \
    -addext "subjectAltName=IP:${IP}"

echo "✅ 证书已生成: ${CERT_DIR}/"

# 启动服务
echo "🚀 启动服务..."
docker compose down || true
docker compose up -d --build

echo ""
echo "✅ HTTPS 配置完成！"
echo "   访问: https://${IP}"
echo "   ⚠️  浏览器会提示「不安全」，点击「高级 → 继续访问」即可"
