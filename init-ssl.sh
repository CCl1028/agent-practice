#!/bin/bash
# SSL 证书初始化脚本
# 用法: ssh root@106.52.248.165 "cd ~/agent-practice && bash init-ssl.sh your-domain.com"

set -e

DOMAIN=$1

if [ -z "$DOMAIN" ]; then
    echo "❌ 请提供域名参数"
    echo "用法: bash init-ssl.sh your-domain.com"
    exit 1
fi

echo "🔧 域名: ${DOMAIN}"

# 1. 替换 nginx.conf 中的占位域名
sed -i "s/YOUR_DOMAIN/${DOMAIN}/g" nginx/nginx.conf
sed -i "s/server_name _;/server_name ${DOMAIN};/g" nginx/nginx.conf

# 2. 创建目录
mkdir -p certbot/conf certbot/www

# 3. 先用 HTTP 模式启动 Nginx（注释掉 443 块）
echo "📦 先以 HTTP 模式启动 Nginx..."
cat > nginx/nginx-init.conf << 'EOF'
server {
    listen 80;
    server_name _;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://fund-assistant:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 临时用初始化配置启动
docker compose down || true
cp nginx/nginx.conf nginx/nginx.conf.bak
cp nginx/nginx-init.conf nginx/nginx.conf

docker compose up -d fund-assistant nginx
sleep 3

# 4. 申请证书
echo "🔐 申请 Let's Encrypt 证书..."
docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email admin@${DOMAIN} \
    --agree-tos \
    --no-eff-email \
    -d ${DOMAIN}

# 5. 恢复完整 Nginx 配置（含 HTTPS）
echo "🔄 切换到 HTTPS 配置..."
cp nginx/nginx.conf.bak nginx/nginx.conf

# 6. 重启 Nginx 加载证书
docker compose restart nginx

echo ""
echo "✅ HTTPS 配置完成！"
echo "   访问: https://${DOMAIN}"
echo ""
echo "💡 证书自动续期：添加 crontab："
echo "   0 3 * * * cd $(pwd) && docker compose run --rm certbot renew && docker compose restart nginx"
