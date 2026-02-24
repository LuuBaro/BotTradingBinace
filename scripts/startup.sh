#!/bin/bash
# Production Startup Script
# Initializes database, runs migrations, starts services

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Bot Trading Platform - Production Startup                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"

# Configuration
ENVIRONMENT="${ENVIRONMENT:-production}"
LOG_DIR="${LOG_DIR:-./logs}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

# Create directories
mkdir -p $LOG_DIR $BACKUP_DIR

echo "📝 [$(date +'%Y-%m-%d %H:%M:%S')] Starting up..."
echo "Environment: $ENVIRONMENT"

# ============================================================================
# Pre-startup Checks
# ============================================================================
echo ""
echo "✓ Checking environment variables..."
if [ -z "$JWT_SECRET" ]; then
    echo "❌ ERROR: JWT_SECRET not set"
    exit 1
fi

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ ERROR: DB_PASSWORD not set"
    exit 1
fi

if [ -z "$REDIS_PASSWORD" ]; then
    echo "❌ ERROR: REDIS_PASSWORD not set"
    exit 1
fi

echo "✓ All required environment variables set"

# ============================================================================
# Docker Compose Startup
# ============================================================================
echo ""
echo "🐳 Starting Docker services..."

docker-compose -f docker-compose.yml up -d 2>&1 | tee -a $LOG_DIR/startup.log

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
max_retries=30
retries=0

while [ $retries -lt $max_retries ]; do
    if docker-compose exec -T db pg_isready -U $DB_USER >/dev/null 2>&1; then
        echo "✓ PostgreSQL is ready"
        break
    fi
    retries=$((retries + 1))
    echo "  Retry $retries/$max_retries..."
    sleep 2
done

if [ $retries -eq $max_retries ]; then
    echo "❌ PostgreSQL failed to start"
    exit 1
fi

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
sleep 5

if docker-compose exec -T redis redis-cli -a $REDIS_PASSWORD ping >/dev/null 2>&1; then
    echo "✓ Redis is ready"
else
    echo "⚠️  Warning: Redis not yet available, will retry..."
fi

# ============================================================================
# Database Initialization
# ============================================================================
echo ""
echo "💾 Initializing database..."

# Check if migrations table exists
MIGRATION_COUNT=$(docker-compose exec -T db psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM migration_history;" 2>/dev/null || echo "0")

if [ "$MIGRATION_COUNT" -eq "0" ]; then
    echo "  Running initial migrations..."
    docker-compose exec -T api python -m alembic upgrade head 2>&1 | tee -a $LOG_DIR/migrations.log
else
    echo "  Migrations already applied ($MIGRATION_COUNT migrations)"
fi

# ============================================================================
# Health Checks
# ============================================================================
echo ""
echo "🏥 Performing health checks..."

echo "  Checking API..."
sleep 5
API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
if [ "$API_HEALTH" = "200" ]; then
    echo "  ✓ API is healthy"
else
    echo "  ⚠️  API health check returned $API_HEALTH (expected 200)"
fi

echo "  Checking Database..."
if docker-compose exec -T db pg_isready -U $DB_USER >/dev/null 2>&1; then
    echo "  ✓ Database is healthy"
fi

echo "  Checking Redis..."
if docker-compose exec -T redis redis-cli -a $REDIS_PASSWORD ping >/dev/null 2>&1; then
    echo "  ✓ Redis is healthy"
fi

# ============================================================================
# Backup Configuration
# ============================================================================
echo ""
echo "💾 Setting up automatic backups..."

# Schedule backup script (requires cron or equivalent)
echo "  Backup directory: $BACKUP_DIR"
echo "  To enable automatic backups, add to crontab:"
echo "  0 2 * * * cd /path/to/bottrading && python scripts/backup_restore.py backup"

# ============================================================================
# Startup Complete
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ✅ Startup Complete!                                          ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  API:      http://localhost:8000                               ║"
echo "║  Health:   http://localhost:8000/health                        ║"
echo "║  Metrics:  http://localhost:8000/health/metrics                ║"
echo "║  Logs:     $LOG_DIR/                                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"

echo ""
echo "📖 Next steps:"
echo "  1. Configure firewall rules"
echo "  2. Setup SSL/TLS certificates"
echo "  3. Configure monitoring & alerts"
echo "  4. Enable auto-scaling if on Kubernetes"
echo ""

exit 0
