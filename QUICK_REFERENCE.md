# Production Quick Reference

**Phase 7 Deployment - Quick Start & Common Commands**

---

## 🚀 Quick Deployment (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/yourorg/bottrading.git
cd bottrading

# 2. Create production environment
cat > .env.production << 'EOF'
ENVIRONMENT=production
JWT_SECRET=$(openssl rand -urlsafe 32 | head -c32)
DB_PASSWORD=$(openssl rand -base64 20)
REDIS_PASSWORD=$(openssl rand -base64 20)
DB_USER=bottrading
DB_HOST=db
DB_PORT=5432
DB_NAME=bottrading
REDIS_HOST=redis
REDIS_PORT=6379
EOF

# 3. Start services
docker-compose up -d

# 4. Verify health
curl http://localhost:8000/health | jq .

# Done! ✅
```

---

## 📊 Health Monitoring

### Single Health Check
```bash
curl http://localhost:8000/health | jq .status
```

**Response**: `"healthy"` or `"degraded"` or `"unhealthy"`

### Full System Status
```bash
curl http://localhost:8000/health/detailed | jq '.'
```

**Response**: Detailed metrics including request count, error rate, response times

### Service Status
```bash
docker-compose ps

# 5 services should show "Up":
# - api (with health check status)
# - db (PostgreSQL)
# - redis
# - worker (Celery)
# - nginx
```

### Resource Usage
```bash
docker stats --no-stream

# Check if any service:
# - Using >500MB RAM (except db)
# - CPU >80%
# - Restarting (STATUS column)
```

---

## 🔧 Common Operations

### Start/Stop Services
```bash
# Start all
docker-compose up -d

# Stop all
docker-compose down

# Restart one service
docker-compose restart api
docker-compose restart worker
docker-compose restart db

# Stop specific service
docker-compose stop nginx

# Start specific service
docker-compose start nginx
```

### View Logs
```bash
# All services (follow mode)
docker-compose logs -f

# Last 20 lines
docker-compose logs --tail 20

# Specific service
docker-compose logs -f api
docker-compose logs -f db
docker-compose logs -f worker

# Last 24 hours
docker-compose logs --since 24h

# With timestamps
docker-compose logs -f --timestamps
```

### Database Management
```bash
# Connect to database
docker-compose exec db psql -U bottrading -d bottrading

# Useful queries:
# Count tables
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';

# Database size
SELECT pg_size_pretty(pg_database.datsize) FROM pg_database WHERE datname='bottrading';

# Active connections
SELECT COUNT(*) FROM pg_stat_activity WHERE datname='bottrading';

# List all tables
\dt

# Check audit logs
SELECT * FROM audit.audit_log ORDER BY timestamp DESC LIMIT 10;
```

### Redis Operations
```bash
# Connect to Redis
docker-compose exec redis redis-cli -a $REDIS_PASSWORD

# Useful commands:
PING                    # Check connection
DBSIZE                  # Number of keys
FLUSHDB                 # Clear all data (use carefully!)
KEYS *                  # List all keys
```

---

## 💾 Backup Management

### Create Backup
```bash
# Manual backup
docker-compose exec -T db pg_dump -U bottrading bottrading | \
  gzip > backups/backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Or use backup script
python scripts/backup_restore.py backup
```

### List Backups
```bash
# Show all backups with sizes
ls -lh backups/

# Or use backup script
python scripts/backup_restore.py list
```

### Restore Backup
```bash
# ⚠️ WARNING: This will overwrite current database!

# With confirmation
python scripts/backup_restore.py restore backups/backup_20240115_020000.sql.gz

# Or manually
gunzip -c backups/backup_20240115_020000.sql.gz | \
  docker-compose exec -T db psql -U bottrading -d bottrading
```

### Auto-Cleanup Old Backups
```bash
# Keep 30 days, minimum 5 copies
python scripts/backup_restore.py cleanup 30 5
```

---

## 🔒 Security

### Verify No Exposed Secrets
```bash
# Check code for secrets
grep -r "password\|secret\|token" . --include="*.py" | \
  grep -v ".env\|example\|test\|CHANGEME"

# Check logs for secrets
docker-compose logs | grep -i "password\|secret"

# Check running environment
docker-compose exec api env | grep -i "secret\|password"
```

### Rotate Secrets
```bash
# Generate new secrets
NEW_JWT=$(openssl rand -urlsafe 32 | head -c32)
NEW_DB_PASS=$(openssl rand -base64 20)

# Update .env.production
sed -i "s/JWT_SECRET=.*/JWT_SECRET=$NEW_JWT/" .env.production
sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$NEW_DB_PASS/" .env.production

# Restart services
docker-compose down
docker-compose up -d
```

### Check Security Headers
```bash
curl -I http://localhost:8000/health | grep -i "x-\|strict"

# Should see:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
```

### Test Rate Limiting
```bash
# Send 110 requests in rapid succession
for i in {1..110}; do
  curl -s http://localhost:8000/health | jq '.status'
done | grep -c "null"

# Should see some 429 errors (rate limit exceeded)
```

---

## ⚠️ Troubleshooting

### "API not responding"
```bash
# Check if running
docker-compose ps api

# View errors
docker-compose logs api --tail 50

# Restart
docker-compose restart api

# Verify
curl http://localhost:8000/health -v
```

### "Database connection failed"
```bash
# Check if DB running
docker-compose ps db

# Test connectivity
docker-compose exec db psql -U bottrading -d bottrading -c "SELECT 1;"

# Check logs
docker-compose logs db --tail 50

# Restart (rebuilds if needed)
docker-compose restart db
docker-compose restart api
```

### "Redis connection failed"
```bash
# Check if Redis running
docker-compose ps redis

# Test connectivity
docker-compose exec redis redis-cli ping

# Restart
docker-compose restart redis
docker-compose restart api
```

### "High memory usage"
```bash
# Check which service
docker stats --no-stream

# Restart problematic service
docker-compose restart <service-name>

# If persistent, check logs for memory leaks
docker-compose logs <service-name> | grep -i "memory\|leak"
```

### "Slow responses"
```bash
# Check API metrics
curl http://localhost:8000/health/metrics | jq '.avg_response_time'

# Check database latency
curl http://localhost:8000/health/database | jq '.latency'

# Check slow queries
docker-compose exec db psql -U bottrading -d bottrading << EOF
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC LIMIT 5;
EOF
```

---

## 🎯 Acceptance Criteria Status

Run to verify all 12 criteria met:
```bash
python verify_phase7.py
```

Expected output: All ✅ marks

**AC1**: Docker Compose with all services ✅  
**AC2**: SQLite→PostgreSQL migration ✅  
**AC3**: Backup/restore system ✅  
**AC4**: Health checks (6 endpoints) ✅  
**AC5**: Alert thresholds ✅  
**AC6**: Secrets management ✅  
**AC7**: Production configuration ✅  
**AC8**: Startup automation ✅  
**AC9**: Documentation complete ✅  
**AC10**: SSL/TLS ready ✅  
**AC11**: Rate limiting (100/s API, 1000/s UI) ✅  
**AC12**: Health check logging ✅  

---

## 📚 Documentation

For detailed information, see:

| Document | Purpose |
|----------|---------|
| [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) | Step-by-step verification |
| [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md) | Daily operations & troubleshooting |
| [SECURITY_HARDENING.md](SECURITY_HARDENING.md) | Security implementation |
| [PHASE7_COMPLETE.md](PHASE7_COMPLETE.md) | Architecture & design |
| [DEPLOYMENT_GUIDE.sh](DEPLOYMENT_GUIDE.sh) | Automated deployment script |

---

## 🆘 Support

### Get Help
```bash
# View all service logs
docker-compose logs

# Export diagnostic info
docker-compose logs > diagnostics.log
docker stats > resources.log
df -h > diskspace.log

# Check system status
systemctl status docker
systemctl status bottrading
```

### Emergency Restart
```bash
# Full system restart
docker-compose down && docker-compose up -d

# With log capture
docker-compose down && docker-compose logs > restart_logs.txt && docker-compose up -d
```

### Contact
- **Issues**: File GitHub issue with logs from `docker-compose logs`
- **Security**: Report to [security-team@company.com]
- **Operations**: On-call at [contact]

---

## 📋 Daily Checklist

```bash
# Run every morning:
echo "=== Daily Health Check ==="
echo ""
echo "✓ Services Status:"
docker-compose ps | grep -E "api|db|redis|worker|nginx"
echo ""
echo "✓ API Health:"
curl -s http://localhost:8000/health | jq '.status'
echo ""
echo "✓ Error Rate:"
curl -s http://localhost:8000/health/metrics | jq '.error_rate'
echo ""
echo "✓ Latest Backup:"
ls -lh backups/ | head -2 | tail -1
echo ""
echo "✓ Disk Space:"
df -h | grep -E "^/dev|Filesystem"
```

---

## 🔄 Common Workflows

### Complete Fresh Deployment
```bash
# 1. Stop and remove old containers
docker-compose down -v

# 2. Update code
git pull origin main

# 3. Rebuild images
docker-compose build --no-cache

# 4. Start fresh
docker-compose up -d

# 5. Verify
docker-compose ps
curl http://localhost:8000/health
```

### Zero-Downtime Update
```bash
# 1. Update API (separate container)
docker-compose build api
docker-compose up -d api

# 2. Verify health
curl http://localhost:8000/health

# 3. Update worker (separate container)
docker-compose build worker
docker-compose up -d worker

# 4. Update database (if migrations needed)
docker-compose exec api alembic upgrade head

# No downtime! ✅
```

### Scaling Workers
```bash
# Edit docker-compose.yml for worker service
# Change:   replicas: 1
# To:       replicas: 3

docker-compose up -d worker

# Verify
docker-compose ps | grep worker
```

---

## 📊 Monitoring Dashboard

```bash
#!/bin/bash
# Save as: monitor.sh
# Run: watch -n 5 ./monitor.sh

clear
echo "╔════════════════════════════════════════════════════╗"
echo "║  Bot Trading Platform - Live Monitoring            ║"
echo "║  $(date '+%Y-%m-%d %H:%M:%S')                                       ║"
echo "╚════════════════════════════════════════════════════╝"

echo ""
echo "▸ Services"
docker-compose ps | tail -6

echo ""
echo "▸ API Health"
curl -s http://localhost:8000/health | jq '{status, uptime, request_count}' 2>/dev/null || echo "⚠️ API Unreachable"

echo ""
echo "▸ Database"
curl -s http://localhost:8000/health/database | jq '.latency' 2>/dev/null || echo "⚠️ DB Unreachable"

echo ""
echo "▸ Redis"
curl -s http://localhost:8000/health/redis | jq '.latency' 2>/dev/null || echo "⚠️ Redis Unreachable"

echo ""
echo "▸ Memory Usage"
docker stats --no-stream | tail -6

echo ""
echo "▸ Errors (24h)"
docker-compose logs --since 24h | grep ERROR | wc -l
```

---

**Last Updated**: Phase 7 Production Deployment  
**Version**: 1.0.0  
**Status**: ✅ Production Ready
