# HƯỚNG DẪN TRIỂN KHAI PRODUCTION (STEP-BY-STEP)

**Ngày Phát Hành**: 5 Tháng 3, 2026  
**Phiên Bản**: 1.0 Production Ready  
**Ước Tính Thời Gian**: 3-5 ngày từ dev → production

---

## PHẦN 1: Chuẩn Bị Bảo Mật (Hôm Nay)

### Bước 1: Thay Đổi TẤT CẢ API Keys & Secrets

#### 1.1 Binance Futures API
```bash
# 1. Đi tới: https://www.binance.com/en/my/settings/api-management
# 2. Xóa API key cũ (có trong .env hiện tại)
# 3. Tạo API key mới:
#    - IP Whitelist: your-server-ip (e.g., 203.0.113.42)
#    - Enable Spot & Margin Trading
#    - Enable Read & Write

# Sao chép API key + secret mới vào:
.env.production:
BINANCE_API_KEY=<NEW_KEY>
BINANCE_API_SECRET=<NEW_SECRET>
```

#### 1.2 Telegram Bot Token
```bash
# 1. DM @BotFather trên Telegram
# 2. Lệnh: /revoke (chọn bot cũ)
# 3. Tạo bot mới: /newbot
# 4. Sao chép token mới vào:
.env.production:
TELEGRAM_BOT_TOKEN=<NEW_TOKEN>
```

#### 1.3 OpenAI, Groq, Anthropic
```bash
# OpenAI (https://platform.openai.com/api-keys)
# 1. Delete old key
# 2. Create new API key
# 3. Set in .env.production:
OPENAI_API_KEY=<NEW_KEY>

# Groq (https://console.groq.com/)
# 1. Delete old key, create new
GROQ_API_KEY=<NEW_KEY>

# Anthropic (https://console.anthropic.com/)
# 1. Delete old key, create new
ANTHROPIC_API_KEY=<NEW_KEY>
```

#### 1.4 Google OAuth Credentials
```bash
# 1. Đi tới: https://console.cloud.google.com/
# 2. Credentials → Create OAuth 2.0 Client ID
# 3. Set Authorized redirect URIs:
#    - https://yourdomain.com/auth/callback
#    - http://localhost:3000/auth/callback (dev)
GOOGLE_CLIENT_ID=<NEW_ID>
```

#### 1.5 Gmail App Password
```bash
# 1. https://myaccount.google.com/apppasswords
# 2. Select app: Mail, device: Windows
# 3. Copy password
# 4. Set in .env.production:
SMTP_USERNAME=youremail@gmail.com
SMTP_PASSWORD=<GENERATED_APP_PASSWORD>
```

---

### Bước 2: Tạo .env.production (Không Public)

```bash
# Tạo tệp mới
cat > .env.production << 'EOF'
# ============================================================================
# ENVIRONMENT
# ============================================================================
ENVIRONMENT=production
LOG_LEVEL=INFO
ENV=live

# ============================================================================
# DATABASE - PostgreSQL (PRODUCTION)
# ============================================================================
# Tạo password mạnh: python -c "import secrets; print(secrets.token_urlsafe(32))"
DB_USER=bottrading_prod
DB_PASSWORD=xY9zaBcD1eF2gH3iJ4kL5mN6oP7qR8sT9uV0wX
DB_HOST=db.example.com          # Thay bằng RDS endpoint hoặc server PostgreSQL
DB_PORT=5432
DB_NAME=bottrading_prod
DB_URL=postgresql://bottrading_prod:xY9zaBcD1eF2gH3iJ4kL5mN6oP7qR8sT9uV0wX@db.example.com:5432/bottrading_prod

# ============================================================================
# REDIS - Cache & Job Queue
# ============================================================================
REDIS_HOST=redis.example.com    # Thay bằng Redis endpoint
REDIS_PORT=6379
REDIS_PASSWORD=aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aB4cD5eF6

# ============================================================================
# API SERVER
# ============================================================================
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# ============================================================================
# SECURITY - JWT & Authentication
# ============================================================================
# Tạo: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET=aBcD1eF2gH3iJ4kL5mN6oP7qR8sT9uV0wX1yZ2aB3cD4eF5gH6
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# ============================================================================
# LLM CONFIGURATION
# ============================================================================
SELECTED_LLM=groq
GROQ_API_KEY=<NEW_KEY_FROM_GROQ_CONSOLE>
GROQ_MODEL=llama-3.3-70b-versatile
OPENAI_API_KEY=<NEW_KEY_FROM_OPENAI>
OPENAI_MODEL=gpt-4o-mini

# ============================================================================
# BINANCE - PHẢI SỬ DỤNG TESTNET TRƯỚC
# ============================================================================
BINANCE_TESTNET=true              # ⚠️ GIỮ true CHO ĐẾN KHI ĐẦY ĐỦ TEST
BINANCE_API_KEY=<NEW_KEY>
BINANCE_API_SECRET=<NEW_SECRET>
BINANCE_TIMESTAMP_OFFSET=0        # Hoặc update nếu cần

# ============================================================================
# TELEGRAM BOT
# ============================================================================
TELEGRAM_BOT_TOKEN=<NEW_TOKEN>
TELEGRAM_ADMIN_IDS=YOUR_CHAT_ID   # E.g., 5858550670
TELEGRAM_OWNER_ID=YOUR_CHAT_ID

# ============================================================================
# SMTP EMAIL (Optional)
# ============================================================================
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<GMAIL>
SMTP_PASSWORD=<APP_PASSWORD>
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_USE_TLS=true

# ============================================================================
# MONITORING & BACKUP
# ============================================================================
BACKUP_DIR=/backups
BACKUP_SCHEDULE=0 2 * * *         # 2:00 AM mỗi ngày
BACKUP_RETENTION_DAYS=30

ENABLE_MONITORING=true
ENABLE_SLOWLOG=true
SLOW_QUERY_THRESHOLD_MS=1000
EOF

# Bảo vệ file
chmod 600 .env.production
```

### Bước 3: Thêm .env.production Vào .gitignore

```bash
# Chỉnh sửa .gitignore
echo ".env.production" >> .gitignore
echo ".env.*.local" >> .gitignore
echo ".env.staging" >> .gitignore

git add .gitignore
git commit -m "chore: protect production env files"
```

---

## PHẦN 2: Kiểm Tra Code (Hoàn Thành)

✅ **Đã Sửa** (4 vấn đề):
- [x] Xóa unused `import sqlite3` (main.py, database.py)
- [x] Sửa CORS: whitelist domains thay vì `["*"]`
- [x] Sửa API port: 8001 → 8000
- [x] Thay exception từ `sqlite3.OperationalError` → `Exception`

**Kiểm Chứng**: ✅ 0 errors, ✅ 0 warnings

---

## PHẦN 3: Chuẩn Bị Cơ Sở Hạ Tầng (Ngày Mai)

### Tùy Chọn A: AWS (Khuyên Dùng)

#### 3.1 Database: AWS RDS PostgreSQL
```bash
# 1. AWS Console → RDS → Databases → Create Database
# 2. Settings:
#    - Engine: PostgreSQL 15
#    - DB Instance Class: db.t4g.small (khởi đầu)
#    - Storage: 100 GB (gp3)
#    - Multi-AZ: Enabled (high availability)

# 3. Security Group: Allow inbound from app server IP
#    - Port: 5432
#    - Source: your-server-ip/32

# 4. Sao chép endpoint: bottrading-db.xxxx.us-east-1.rds.amazonaws.com
#    DB_HOST=bottrading-db.xxxx.us-east-1.rds.amazonaws.com
```

#### 3.2 Cache: AWS ElastiCache Redis
```bash
# 1. AWS Console → ElastiCache → Redis → Create
# 2. Settings:
#    - Node type: cache.t4g.small
#    - Engine: Redis 7.x
#    - Auth token: Enabled (strong password)
#    - Multi-AZ: Enabled

# 3. Sao chép endpoint: bottrading-redis.xxxx.ng.0001.use1.cache.amazonaws.com
#    REDIS_HOST=bottrading-redis.xxxx.ng.0001.use1.cache.amazonaws.com
```

#### 3.3 Secrets: AWS Secrets Manager
```bash
# 1. AWS CLI: 
aws secretsmanager create-secret \
    --name prod/bottrading/binance \
    --secret-string '{
        "api_key": "xxx",
        "api_secret": "xxx"
    }'

# 2. Load trong code:
import boto3
client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='prod/bottrading/binance')
```

#### 3.4 Monitoring: CloudWatch
```bash
# Tự động được bật cho RDS + ElastiCache
# Dashboard: AWS Console → CloudWatch → Dashboards → Create

# Alarms:
# - Database CPU > 80%
# - Database connections > 90
# - Redis evictions > 0
# - API error rate > 1%
```

---

### Tùy Chọn B: Docker Compose Self-Hosted

```bash
# docker-compose.yml có sẵn, chỉ cần cập nhật:

# 1. Tạo volumes trên host
mkdir -p /data/postgres
mkdir -p /data/redis
mkdir -p /backups

# 2. Sửa docker-compose.yml:
services:
  db:
    volumes:
      - /data/postgres:/var/lib/postgresql/data  # Host path
  redis:
    volumes:
      - /data/redis:/data
  
  api:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

# 3. Chạy:
docker-compose -f docker-compose.yml up -d
```

---

### 3.5 SSL/TLS Certificate

```bash
# Sử dụng Let's Encrypt + Certbot
sudo apt-get install certbot python3-certbot-nginx

sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Sao chép cert:
/etc/letsencrypt/live/yourdomain.com/
├── cert.pem        → API_SSL_CERT
├── privkey.pem     → API_SSL_KEY
└── fullchain.pem   → For nginx/reverse proxy

# Update nginx:
server {
    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

---

## PHẦN 4: Database Setup (Ngày Mai)

```bash
# 1. Kết nối tới PostgreSQL
psql -h DB_HOST -U DB_USER -d DB_NAME

# 2. Kiểm tra kết nối
\dp
\dt

# 3. Chạy migrations
alembic upgrade head

# 4. Tạo backup ban đầu
pg_dump -h DB_HOST -U DB_USER -d DB_NAME > /backups/initial.sql

# 5. Kiểm tra tables
\dt

# Bạn sẽ thấy:
#  - bot_config
#  - position
#  - order
#  - decision
#  - event
#  - risk_log
#  - audit_log
#  - signal
#  - ... (tổng 11 bảng)
```

---

## PHẦN 5: Testing Trước Deploy (Nửa Tuần)

### 5.1 Kiểm Tra Database
```bash
# Từ app server:
psql -h DB_HOST -U DB_USER -d DB_NAME -c "SELECT 1"

# Expected: 1 (kết nối thành công)
```

### 5.2 Kiểm Tra API
```bash
# 1. Khởi động server
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

# 2. Test health
curl http://localhost:8000/api/health

# 3. Test auth
curl -X POST http://localhost:8000/api/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"test123"}'

# 4. Test login
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"test123"}' | jq -r .token)

# 5. Test protected endpoint
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/overview
```

### 5.3 Kiểm Tra Telegram Bot
```bash
# 1. Khởi động bot
python -m apps.telegram.main

# 2. DM bot `/health`
# Expected: System status

# 3. Kiểm tra logs
# Bot sẽ log trên stderr
```

### 5.4 Kiểm Tra Worker
```bash
# 1. Khởi động worker
python -m apps.worker.main

# 2. Kiểm tra logs
# Expected: 
#   - Market data fetched
#   - AI decision made
#   - Order execution (mock mode)

# 3. Check database
# SELECT COUNT(*) FROM event;
# Sẽ có events từ trades, decisions, etc.
```

### 5.5 Load Testing
```bash
# Cài đặt Apache JMeter hoặc:
pip install locust

# Tạo locustfile.py
cat > locustfile.py << 'EOF'
from locust import HttpUser, task

class APIUser(HttpUser):
    @task
    def health_check(self):
        self.client.get("/api/health")

EOF

# Chạy test
locust -f locustfile.py -u 100 -r 10 -t 60s

# Expected: <200ms response time
```

---

## PHẦN 6: Deployment Steps (Tuần Này)

### 6.1 Chọn Deployment Platform

**Option 1: AWS EC2 + Docker** (Khuyên dùng)
```bash
# 1. Tạo EC2 instance (t3.medium)
#    - OS: Ubuntu 22.04 LTS
#    - Storage: 50 GB gp3
#    - Security Group: Allow 443 (HTTPS) + 22 (SSH)

# 2. SSH vào instance
ssh -i key.pem ubuntu@your-ec2-ip

# 3. Setup Docker
sudo apt-get update && apt-get install docker.io docker-compose

# 4. Clone repo
git clone https://github.com/yourrepo/BotTradingBinance.git
cd BotTradingBinance

# 5. Setup environment
cp .env.production .env
# (Đã tạo ở bước 2 trên)

# 6. Start services
docker-compose up -d api worker telegram

# 7. Setup nginx reverse proxy
sudo apt-get install nginx
# (Xem reverse proxy config bên dưới)
```

**Option 2: Docker Hub + GitHub Actions**
```yaml
# .github/workflows/deploy.yml
name: Deploy Production

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build and push Docker
        run: |
          docker build -t bottrading:${{ github.ref_name }} .
          docker push yourrepo/bottrading:${{ github.ref_name }}
      
      - name: Deploy to EC2
        run: |
          ssh -i ${{ secrets.EC2_KEY }} ubuntu@${{ secrets.EC2_HOST }} \
            "cd BotTradingBinance && \
            docker pull yourrepo/bottrading && \
            docker-compose up -d"
```

**Option 3: AWS ECS Fargate** (Fully managed)
```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name bottrading

# 2. Build and push image
docker build -t bottrading .
docker tag bottrading:latest <account-id>.dkr.ecr.<region>.amazonaws.com/bottrading:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/bottrading:latest

# 3. Create ECS Cluster + Services (via AWS Console)
# 4. Deploy with rolling updates
```

### 6.2 Nginx Reverse Proxy Config

```bash
# /etc/nginx/sites-available/bottrading
upstream api_backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect HTTP → HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL Certificates (from Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    
    # API Proxy
    location /api {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Dashboard Frontend
    location / {
        root /var/www/bottrading-frontend;
        try_files $uri $uri/ /index.html;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/bottrading /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6.3 Monitoring Setup

```bash
# 1. Cài Prometheus
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v /etc/prometheus:/etc/prometheus \
  prom/prometheus

# 2. Cài Grafana
docker run -d \
  --name grafana \
  -p 3000:3000 \
  grafana/grafana

# 3. Add data sources trong Grafana:
#    - Prometheus: http://localhost:9090
#    - PostgreSQL: DB_HOST:5432
#    - Redis: REDIS_HOST:6379

# 4. Setup dashboards
#    - Database performance
#    - API latency
#    - Worker status
#    - Trading metrics
```

### 6.4 Backup Strategy

```bash
# Cron job - Daily backup at 2 AM
crontab -e

0 2 * * * /scripts/backup.sh

# /scripts/backup.sh
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y-%m-%d_%H%M%S)

# PostgreSQL backup
pg_dump -h $DB_HOST -U $DB_USER $DB_NAME > $BACKUP_DIR/db_$DATE.sql

# Redis backup
redis-cli --rdb $BACKUP_DIR/redis_$DATE.rdb

# Upload to S3
aws s3 cp $BACKUP_DIR s3://my-backups-bucket/ --recursive

# Keep only 30 days
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
```

---

## PHẦN 7: Post-Deployment Verification (Sau Deploy)

```bash
# 1. Kiểm tra health
curl https://yourdomain.com/api/health

# 2. Kiểm tra logs
docker logs api     # Last 100 lines
docker logs worker
docker logs telegram

# 3. Kiểm tra database
psql -h $DB_HOST -U $DB_USER $DB_NAME -c "SELECT COUNT(*) FROM event;"

# 4. Kiểm tra Telegram
# Send /health command → should get response

# 5. Kiểm tra monitoring
# Visit https://yourdomain.com:3000 (Grafana)
# Verify metrics đang thu thập

# 6. Kiểm tra SSL
openssl s_client -connect yourdomain.com:443

# Expected: Successful SSL handshake
```

---

## PHẦN 8: Monitoring & Alerting Setup

### 8.1 Slack Notifications
```python
# packages/shared/alerting.py
import httpx

async def alert_to_slack(message: str, level: str = "info"):
    webhook_url = settings.slack_webhook
    payload = {
        "text": f"[{level.upper()}] {message}",
        "color": {"critical": "danger", "warning": "warning", "info": "good"}[level]
    }
    await httpx.AsyncClient().post(webhook_url, json=payload)

# Usage
await alert_to_slack("Trading halted - circuit breaker triggered", "critical")
```

### 8.2 Email Alerts
```python
# Cài đặt trong .env.production
ALERT_EMAIL=your-email@company.com
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/...
ALERT_PD_KEY=pagerduty-integration-key

# Các trigger:
# - API error rate > 1%
# - Database connection pool exhausted
# - Worker loop lag > 5 seconds
# - Trading loss > daily limit
```

---

## 🎯 PRODUCTION CHECKLIST - FINAL

### Bảo Mật
- [ ] Tất cả API keys từ Vault/Secrets Manager
- [ ] CORS restricted to yourdomain.com
- [ ] SSL/TLS certificate installed
- [ ] Security headers added (HSTS, CSP, X-Frame-Options)
- [ ] Database firewall: only app server can connect
- [ ] Redis: auth token enabled, encrypted transport

### Database & Backup
- [ ] PostgreSQL 15+ configured
- [ ] Daily automated backups → S3/GCS
- [ ] Backup retention: 30+ days
- [ ] Test restore procedure (monthly)
- [ ] Replication enabled (multi-AZ)

### Monitoring
- [ ] Prometheus + Grafana deployed
- [ ] CloudWatch dashboards created
- [ ] Slack/PagerDuty alerts configured
- [ ] Error tracking (Sentry) enabled
- [ ] Asset alarms: CPU, memory, disk, network

### Code
- [ ] All environment variables externalized
- [ ] No secrets in code or logs
- [ ] Error handling comprehensive
- [ ] Logging to stdout (structured JSON)
- [ ] Load testing validation passed

### Operations
- [ ] Team trained on runbooks
- [ ] Incident response plan documented
- [ ] On-call rotation established
- [ ] Change management process defined
- [ ] Regular security audits scheduled

---

## 📞 Hỗ Trợ & Troubleshooting

**API không tả động?**
```bash
curl -v https://yourdomain.com/api/health
# Kiểm tra SSL, CORS, networking
```

**Database kết nối lỗi?**
```bash
psql -h DB_HOST -U DB_USER -d DB_NAME
# Kiểm tra credentials, firewall, host availability
```

**Telegram bot không phản hồi?**
```bash
docker logs telegram
# Kiểm tra bot token, chat ID, network
```

**Performance issue?**
```bash
# Check database
EXPLAIN ANALYZE SELECT * FROM event WHERE created_at > NOW() - INTERVAL '1 day';

# Check Redis
redis-cli INFO stats

# Check API
curl -H "Authorization: Bearer $TOKEN" https://yourdomain.com/api/health
```

---

**Chúc mừng! Hệ thống sẵn sàng cho production.** 🚀

Tiếp theo: Theo dõi logs, set up alerting, và thực hiện war room testing trước khi bật live trading.
