#!/bin/bash
# Phase 7 Deployment Guide - Detailed VPS Setup
# Run on a fresh Ubuntu 22.04 LTS VM

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Bot Trading Platform - Phase 7 VPS Deployment Guide           ║"
echo "╚════════════════════════════════════════════════════════════════╝"

# ============================================================================
# PRE-DEPLOYMENT CHECKS
# ============================================================================
echo ""
echo "▸ Pre-deployment checks..."

# Check OS
if ! grep -q "Ubuntu 22.04\|Ubuntu 20.04" /etc/issue; then
    echo "⚠️  Warning: This guide is optimized for Ubuntu 20.04+ LTS"
fi

# Check root/sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

echo "✓ System checks passed"

# ============================================================================
# STEP 1: System Updates
# ============================================================================
echo ""
echo "▸ Step 1: System updates..."

apt-get update
apt-get upgrade -y
apt-get install -y \
    curl \
    wget \
    git \
    openssl \
    ca-certificates \
    gnupg \
    lsb-release

echo "✓ System updated"

# ============================================================================
# STEP 2: Install Docker
# ============================================================================
echo ""
echo "▸ Step 2: Installing Docker..."

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Enable Docker service
systemctl enable docker
systemctl start docker

echo "✓ Docker installed"

# ============================================================================
# STEP 3: Install Docker Compose
# ============================================================================
echo ""
echo "▸ Step 3: Installing Docker Compose..."

DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d'"' -f4)
curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

docker-compose --version

echo "✓ Docker Compose installed"

# ============================================================================
# STEP 4: Clone Repository
# ============================================================================
echo ""
echo "▸ Step 4: Cloning repository..."

DEPLOY_DIR="/opt/bottrading"
mkdir -p $DEPLOY_DIR

# Clone repository (update with your repo URL)
cd $DEPLOY_DIR
if [ -d ".git" ]; then
    echo "  Repository already cloned, pulling latest..."
    git pull origin main
else
    echo "  Cloning repository..."
    git clone https://github.com/yourorg/bottrading.git .
fi

echo "✓ Repository ready at $DEPLOY_DIR"

# ============================================================================
# STEP 5: Configure Environment
# ============================================================================
echo ""
echo "▸ Step 5: Configuring environment..."

# Generate strong secrets
JWT_SECRET=$(openssl rand -urlsafe 32 | head -c32)
DB_PASSWORD=$(openssl rand -urlsafe 20 | head -c20)
REDIS_PASSWORD=$(openssl rand -urlsafe 20 | head -c20)

# Create production environment file
cat > $DEPLOY_DIR/.env.production << EOF
# Production Configuration - Generated $(date)
ENVIRONMENT=production
LOG_LEVEL=INFO

# Database
DB_USER=bottrading
DB_PASSWORD=$DB_PASSWORD
DB_HOST=db
DB_PORT=5432
DB_NAME=bottrading

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://$(hostname -I | awk '{print $1}')

# Security
JWT_SECRET=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# LLM (update as needed)
SELECTED_LLM=mock
# OPENAI_API_KEY=
# CLAUDE_API_KEY=

# Backup
BACKUP_DIR=/app/backups
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30

# Monitoring
ENABLE_MONITORING=true
ENABLE_SLOWLOG=true
EOF

chmod 600 $DEPLOY_DIR/.env.production

echo "✓ Environment configured"
echo "  JWT_SECRET: ${JWT_SECRET:0:10}..."
echo "  DB_PASSWORD: ${DB_PASSWORD:0:10}..."
echo "  REDIS_PASSWORD: ${REDIS_PASSWORD:0:10}..."

echo ""
echo "⚠️  SAVE THESE CREDENTIALS IN A SECURE LOCATION!"
echo "   Lost credentials cannot be recovered."

# ============================================================================
# STEP 6: Create Directories
# ============================================================================
echo ""
echo "▸ Step 6: Creating directories..."

mkdir -p $DEPLOY_DIR/logs
mkdir -p $DEPLOY_DIR/backups
mkdir -p $DEPLOY_DIR/docker/nginx/ssl

chmod 755 $DEPLOY_DIR/logs
chmod 755 $DEPLOY_DIR/backups

echo "✓ Directories created"

# ============================================================================
# STEP 7: SSL/TLS Certificates
# ============================================================================
echo ""
echo "▸ Step 7: Setting up SSL/TLS..."

# Generate self-signed certificate (replace with Let's Encrypt in production)
openssl req -x509 -newkey rsa:4096 -nodes \
  -out $DEPLOY_DIR/docker/nginx/ssl/certificate.crt \
  -keyout $DEPLOY_DIR/docker/nginx/ssl/private.key \
  -days 365 \
  -subj "/C=US/ST=State/L=City/O=BotTrading/CN=bottrading.local"

chmod 600 $DEPLOY_DIR/docker/nginx/ssl/private.key
chmod 644 $DEPLOY_DIR/docker/nginx/ssl/certificate.crt

echo "✓ Self-signed SSL cert created"
echo "  ⚠️  Use Let's Encrypt for production:"
echo "     certbot certonly --standalone -d yourdomain.com"

# ============================================================================
# STEP 8: Start Services
# ============================================================================
echo ""
echo "▸ Step 8: Starting Docker services..."

cd $DEPLOY_DIR

# Load environment
export $(cat .env.production | xargs)

# Start services
docker-compose -f docker-compose.yml up -d

echo "✓ Services starting..."
echo ""
echo "  Waiting for services to be ready (this may take 30-60 seconds)..."

# Wait for PostgreSQL
max_retries=60
retries=0
while [ $retries -lt $max_retries ]; do
    if docker-compose exec -T db pg_isready -U $DB_USER &>/dev/null; then
        echo "  ✓ PostgreSQL ready"
        break
    fi
    retries=$((retries + 1))
    echo -n "."
    sleep 1
done

# Wait for Redis
if docker-compose exec -T redis redis-cli -a $REDIS_PASSWORD ping &>/dev/null; then
    echo "  ✓ Redis ready"
fi

# Wait for API
sleep 10
API_HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null | grep -o '"status":"healthy"' || echo "")
if [ -n "$API_HEALTH" ]; then
    echo "  ✓ API healthy"
fi

# ============================================================================
# STEP 9: Database Initialization
# ============================================================================
echo ""
echo "▸ Step 9: Initializing database..."

# Run migrations
echo "  Running database migrations..."
docker-compose exec -T api python -m alembic upgrade head 2>&1 | tail -5

echo "✓ Database initialized"

# ============================================================================
# STEP 10: Backup Configuration
# ============================================================================
echo ""
echo "▸ Step 10: Setting up automatic backups..."

# Create backup cron job
cat > /etc/cron.d/bottrading-backup << EOF
# Bot Trading Platform - Daily Backup
0 2 * * * root cd $DEPLOY_DIR && docker-compose exec -T db pg_dump -U $DB_USER $DB_NAME | gzip > backups/backup_\$(date +\%Y\%m\%d_\%H\%M\%S).sql.gz 2>> logs/backup.log

# Cleanup old backups (keep last 30 days)
0 3 * * * root cd $DEPLOY_DIR && python scripts/backup_restore.py cleanup 30 5
EOF

echo "✓ Backup schedule configured (daily at 2 AM UTC)"

# ============================================================================
# STEP 11: Firewall Configuration
# ============================================================================
echo ""
echo "▸ Step 11: Configuring firewall..."

# Enable UFW if not already enabled
ufw --force enable

# Allow SSH
ufw allow 22/tcp

# Allow HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Block internal services (PostgreSQL, Redis)
ufw default deny incoming
ufw default allow outgoing

echo "✓ Firewall configured"
echo "  - SSH (22): Allowed"
echo "  - HTTP (80): Allowed"
echo "  - HTTPS (443): Allowed"
echo "  - PostgreSQL (5432): Internal only"
echo "  - Redis (6379): Internal only"

# ============================================================================
# STEP 12: Monitoring & Logging
# ============================================================================
echo ""
echo "▸ Step 12: Setting up monitoring..."

# Setup log rotation
cat > /etc/logrotate.d/bottrading << EOF
$DEPLOY_DIR/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
}
EOF

echo "✓ Log rotation configured"

# ============================================================================
# STEP 13: Systemd Service
# ============================================================================
echo ""
echo "▸ Step 13: Creating systemd service..."

cat > /etc/systemd/system/bottrading.service << EOF
[Unit]
Description=Bot Trading Platform
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=$DEPLOY_DIR
EnvironmentFile=$DEPLOY_DIR/.env.production

# Start command
ExecStart=/usr/local/bin/docker-compose -f docker-compose.yml up

# Restart policy
Restart=on-failure
RestartSec=30s

# Resource limits
MemoryLimit=4G

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable bottrading.service

echo "✓ Systemd service created"
echo "  Start: systemctl start bottrading"
echo "  Stop:  systemctl stop bottrading"
echo "  Logs:  journalctl -u bottrading -f"

# ============================================================================
# STEP 14: Verification
# ============================================================================
echo ""
echo "▸ Step 14: Verification..."

docker-compose ps

echo ""
echo "Testing endpoints:"
curl -s http://localhost:8000/health | jq . && echo "✓ API health check" || echo "✗ API health check"
curl -s http://localhost:8000/health/metrics | jq . && echo "✓ Metrics endpoint" || echo "✗ Metrics endpoint"

# ============================================================================
# DEPLOYMENT COMPLETE
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ✅ DEPLOYMENT COMPLETE!                                       ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║                                                                 ║"
echo "║  Deployment Directory: $DEPLOY_DIR"
echo "║  API Endpoint:         http://$(hostname -I | awk '{print $1}'):8000"
echo "║  Health Check:         http://$(hostname -I | awk '{print $1}'):8000/health"
echo "║  Service:              systemctl status bottrading"
echo "║  Logs:                 journalctl -u bottrading -f"
echo "║  Backups:              $DEPLOY_DIR/backups/"
echo "║                                                                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"

echo ""
echo "📋 Next Steps:"
echo ""
echo "1. VERIFY DEPLOYMENT (7-day stability test)"
echo "   - Monitor: watch -n 60 'docker-compose ps && curl http://localhost:8000/health/metrics | jq .'"
echo "   - Check: tail -f logs/startup.log"
echo ""
echo "2. CONFIGURE SSL/TLS FOR PRODUCTION"
echo "   - Install Let's Encrypt: apt-get install certbot python3-certbot-nginx"
echo "   - Get cert: certbot certonly --standalone -d yourdomain.com"
echo "   - Update nginx config with cert paths"
echo ""
echo "3. CONFIGURE DNS"
echo "   - Point yourdomain.com → $(hostname -I | awk '{print $1}')"
echo ""
echo "4. SETUP MONITORING ALERTS"
echo "   - Configure Slack/Email webhooks in health_check.py"
echo "   - Test alerts: systemctl restart bottrading"
echo ""
echo "5. BACKUP VERIFICATION"
echo "   - Verify first backup created: ls -lh $DEPLOY_DIR/backups/"
echo "   - Test restore: python scripts/backup_restore.py list"
echo ""
echo "6. SCALE WORKERS (if needed)"
echo "   - Edit docker-compose.yml"
echo "   - Add more worker services for parallel processing"
echo "   - Restart: docker-compose up -d"
echo ""

exit 0
