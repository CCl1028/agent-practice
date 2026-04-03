#!/bin/bash
# Let's Encrypt SSL 证书初始化脚本
# 用法: ssh root@106.52.248.165 "cd ~/agent-practice && bash init-ssl.sh"
#
# 前提：DNS 已将 fundpal.xyz 解析到 106.52.248.165

set -e

DOMAIN="fundpal.xyz"
EMAIL="admin@${DOMAIN}"

echo "🔐 为 ${DOMAIN} 申请 Let's Encrypt 证书..."

# 1. 创建目录
mkdir -p certbot/conf certbot/www

# 2. 先用纯 HTTP 配置启动 Nginx（证书还没有，不能开 443）
cat > nginx/nginx-init.conf << 'EOF'
server {
    listen 80;
    server_name fundpal.xyz www.fundpal.xyz;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://fund-assistant:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

echo "📦 以 HTTP 模式启动 Nginx..."
docker compose down || true

# 临时使用初始化配置
cp nginx/nginx.conf nginx/nginx.conf.bak
cp nginx/nginx-init.conf nginx/nginx.conf

docker compose up -d fund-assistant nginx
sleep 3

# 3. 申请证书
echo "🔐 申请证书..."
docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    -d "${DOMAIN}" \
    -d "www.${DOMAIN}"

# 4. 恢复完整 HTTPS 配置
echo "🔄 切换到 HTTPS 配置..."
cp nginx/nginx.conf.bak nginx/nginx.conf
rm -f nginx/nginx.conf.bak nginx/nginx-init.conf

# 5. 重启 Nginx 加载证书
docker compose restart nginx

echo ""
echo "✅ HTTPS 配置完成！"
echo "   访问: https://${DOMAIN}"
echo ""
echo "💡 设置证书自动续期（3个月续一次），执行："
echo "   crontab -e"
echo "   添加: 0 3 1 * * cd $(pwd) && docker compose run --rm certbot renew && docker compose restart nginx"
