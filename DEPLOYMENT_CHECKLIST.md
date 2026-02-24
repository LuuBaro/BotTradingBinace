# Phase 7 Complete Deployment Checklist

**Production Deployment - Step-by-Step Verification**

---

## Pre-Deployment Verification (Local)

### Code Quality & Tests
- [ ] Run verification script: `python verify_phase7.py`
  - Expected output: All 12 acceptance criteria ✅
  
- [ ] Run unit tests: `pytest apps/api/test_phase7.py -v`
  - Expected output: All 70+ tests passing ✅

- [ ] Check for hardcoded secrets:
  ```bash
  grep -r "password\|secret\|token\|key" . --include="*.py" --include="*.json" --include="*.yml" | \
    grep -v ".env\|.gitignore\|test_\|example\|CHANGEME"
  ```
  - Expected output: No results (or only from .env.example)

### Docker Images
- [ ] Build images: `docker-compose build --no-cache`
  - Expected output: All 5 services built successfully

- [ ] Check image sizes:
  ```bash
  docker images | grep -E "api|worker|db|redis|nginx"
  ```
  - Expected output: All images reasonable size (<1.5GB each)

- [ ] Scan for vulnerabilities:
  ```bash
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image api:latest
  ```
  - Expected output: No critical vulnerabilities

### Configuration
- [ ] Verify `.env.example` contains all required variables
- [ ] Check `docker-compose.yml` syntax:
  ```bash
  docker-compose config > /dev/null && echo "✓ Valid YAML"
  ```
  - Expected output: Valid YAML

- [ ] Verify all volume paths:
  ```bash
  grep -E "volumes:|^\s+-" docker-compose.yml | grep -v "^--"
  ```
  - Expected output: All volumes defined (postgres_data, redis_data, logs, backups)

- [ ] Check health check configurations:
  ```bash
  grep -A 3 "healthcheck:" docker-compose.yml
  ```
  - Expected output: Health checks on all critical services

---

## VPS Setup Verification

### Access & Permissions
- [ ] SSH access confirmed: `ssh user@vps.ip -i key.pem`
- [ ] Sudo privileges available: `sudo -l`
- [ ] Disk space adequate: `df -h /` (need >50GB free)
- [ ] System resources: `free -h` (need >4GB RAM), `nproc` (need ≥2 cores)

### Operating System
- [ ] Ubuntu 20.04+ LTS: `lsb_release -a`
- [ ] Kernel updated: `uname -r`
- [ ] Time synchronized: `timedatectl` (should show "System clock synchronized: yes")
- [ ] Firewall available: `ufw status` OR `firewall-cmd --state`

### Network
- [ ] Domain DNS configured: `nslookup yourdomain.com` or `dig yourdomain.com`
- [ ] DNS resolves to server IP: `nslookup yourdomain.com` shows your VPS IP
- [ ] Ports 80/443 accessible: `curl http://checkip.amazonaws.com` returns correct IP
- [ ] No firewall blocking: `sudo ufw status` shows ports 80,443 allowed

---

## Deployment Script Execution

### Run Automated Deployment
```bash
# Download deployment script
scp DEPLOYMENT_GUIDE.sh user@vps.ip:/tmp/

# SSH into VPS
ssh user@vps.ip

# Run deployment script
sudo bash /tmp/DEPLOYMENT_GUIDE.sh

# Expected output:
# ✅ DEPLOYMENT COMPLETE!
# Deployment Directory: /opt/bottrading
# API Endpoint: http://[VPS_IP]:8000
# Service: systemctl status bottrading
```

### Monitor Script Progress
```bash
# In a separate terminal, watch logs
tail -f /opt/bottrading/logs/startup.log

# Expected sequence:
# - System updates
# - Docker installation
# - Docker Compose installation
# - Repository cloned
# - Environment configured
# - SSL certificates created
# - Services starting
# - PostgreSQL ready
# - Redis ready
# - API health check passed
```

---

## Post-Deployment Verification

### Service Status
```bash
# Check all services running
docker-compose ps

# Expected output: All 5 services in "Up" state
# NAME              COMMAND                    STATUS           PORTS
# bottrading-api    "uvicorn apps.api..."     Up (healthy)     8000/tcp
# bottrading-db     "postgres -c..."          Up (healthy)     5432/tcp
# bottrading-redis  "redis-server..."         Up (healthy)     6379/tcp
# bottrading-worker "celery -A..."            Up                
# bottrading-nginx  "nginx -g daemon=off"     Up (healthy)     80/tcp, 443/tcp
```

### Health Checks
- [ ] API responds:
  ```bash
  curl -s http://localhost:8000/health | jq '.status'
  ```
  - Expected output: `"healthy"`

- [ ] Database check:
  ```bash
  curl -s http://localhost:8000/health/database | jq '.latency'
  ```
  - Expected output: Latency in milliseconds, no error

- [ ] Redis check:
  ```bash
  curl -s http://localhost:8000/health/redis | jq '.status'
  ```
  - Expected output: `"healthy"`

- [ ] All dependencies:
  ```bash
  curl -s http://localhost:8000/health/dependencies | jq '.'
  ```
  - Expected output: All services status

- [ ] Metrics endpoint:
  ```bash
  curl -s http://localhost:8000/health/metrics | jq '.request_count'
  ```
  - Expected output: Increasing number on each call

### Database Verification
```bash
# Connect to database
docker-compose exec db psql -U bottrading -d bottrading

# Run these queries:
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';  # Should be >0

SELECT * FROM pg_stat_activity WHERE pid <> pg_backend_pid();  # Check active connections

SELECT pg_database.datname FROM pg_database WHERE datname='bottrading';  # Database exists
```

### Configuration Verification
```bash
# Check environment variables loaded
docker-compose exec api python -c "from apps.api.config import settings; \
  print(f'Environment: {settings.ENVIRONMENT}'); \
  print(f'DB Host: {settings.DB_HOST}'); \
  print(f'Redis Host: {settings.REDIS_HOST}')"

# Expected output:
# Environment: production
# DB Host: db
# Redis Host: redis
```

### File Permissions
```bash
# Verify sensitive files have correct permissions
ls -la .env.production  # Should be -rw------- (600)
ls -la docker/nginx/ssl/  # Should have restricted access

# Verify no world-readable secrets
find . -perm 644 -name "*.key" -o -name "*.secret"  # Should find nothing
```

---

## Security Verification

### SSL/TLS Certificates
```bash
# Verify certificate exists
ls -la docker/nginx/ssl/

# Check certificate validity
openssl x509 -in docker/nginx/ssl/certificate.crt -noout -dates

# Expected output: 
# notBefore=... 
# notAfter=... (within 365 days)
```

### Rate Limiting
```bash
# Test rate limit (should fail after 100 requests)
for i in {1..110}; do curl -s http://localhost:8000/health/metrics | jq '.status'; done | \
  sort | uniq -c

# Expected output: Some 200s, then 429s (Too Many Requests)
```

### Security Headers
```bash
# Check security headers present
curl -I http://localhost/health 2>&1 | grep -i "x-\|strict-transport"

# Expected headers:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
```

### No Exposed Secrets
```bash
# Check no secrets in logs
docker-compose logs | grep -i "password\|secret\|token"  # Should find nothing

# Check no secrets in environment
docker-compose exec api env | grep -i "secret\|password"  # Should find nothing (or *****)
```

---

## Backup System Verification

### Initial Backup
```bash
# Verify backup was created during deployment
ls -lh /opt/bottrading/backups/

# Expected output: At least one backup file
# backup_full_20240115_020000.sql.gz (size in MB/GB)
```

### Backup Retention
```bash
# Test manual backup
cd /opt/bottrading
python scripts/backup_restore.py backup

# Expected output:
# Starting full backup...
# ✓ Backup created: backups/backup_full_YYYYMMDD_HHMMSS.sql.gz
# ✓ Backup metadata recorded

ls -lh backups/ | head -5
```

### Backup List
```bash
# Verify backup listing works
python scripts/backup_restore.py list

# Expected output: List of all backups with sizes and dates
```

### Backup Integrity Test (Non-Destructive)
```bash
# Extract and verify backup file can be read
gunzip -t backups/backup_full_*.sql.gz

# Expected output: No errors
```

---

## Performance Verification

### API Response Time
```bash
# Check API performance
curl -s http://localhost:8000/health/metrics | jq '.avg_response_time'

# Expected output: <1000ms (less than 1 second)
```

### Database Performance
```bash
# Check database query time
curl -s http://localhost:8000/health/database | jq '.latency'

# Expected output: <500ms
```

### Redis Performance
```bash
# Check Redis response time
curl -s http://localhost:8000/health/redis | jq '.latency'

# Expected output: <100ms
```

### Resource Utilization
```bash
# Check Docker container resource usage
docker stats --no-stream

# Expected output: 
# CPU usage <50% per service
# Memory usage <500MB for API, <300MB for worker
# No containers restarting
```

---

## Logging Verification

### Application Logs
```bash
# Check API logs
docker-compose logs api --since 5m | tail -20

# Expected output: No ERROR level messages
```

### Database Logs
```bash
# Check database logs
docker-compose logs db --since 5m | tail -20

# Expected output: No fatal errors
```

### Nginx Logs
```bash
# Check nginx access logs
docker-compose logs nginx --since 5m | grep "200\|301\|404"

# Expected output: Mix of successful requests
```

### Persistent Logging
```bash
# Verify logs are being written to disk
ls -lh /opt/bottrading/logs/

# Expected output: Multiple log files with recent timestamps
```

---

## 7-Day Stability Test

### Daily Checklist (Days 1-7)

**Day 1:**
- [ ] All services running: `docker-compose ps`
- [ ] No restart loops: `docker events --since 24h | grep "restart"`
- [ ] Error rate <1%: `curl http://localhost:8000/health/metrics | jq '.error_rate'`
- [ ] Backup created: `ls -lh backups/ | head -1`

**Day 2-3:**
- [ ] 48+ hours uptime: `docker-compose exec api uptime`
- [ ] No memory leaks: `docker stats --no-stream` (stable memory)
- [ ] Database size stable: `docker-compose exec db psql -U bottrading -d bottrading -c "SELECT pg_size_pretty(pg_database.datsize) FROM pg_database WHERE datname='bottrading';"`
- [ ] Response times stable: `curl http://localhost:8000/health/metrics | jq '.avg_response_time'`

**Day 4-5:**
- [ ] 100+ hours uptime
- [ ] Run load test (optional): 
  ```bash
  # Simple load test
  ab -n 1000 -c 10 http://localhost:8000/health
  ```
- [ ] All health endpoints responding: `curl http://localhost:8000/health/dependencies | jq '.'`

**Day 6:**
- [ ] 144+ hours uptime
- [ ] Test backup restore (on separate instance if possible):
  ```bash
  python scripts/backup_restore.py list
  # Restore to test environment
  ```

**Day 7:**
- [ ] 168 hours (1 week) uptime achieved ✅
- [ ] No incidents recorded
- [ ] All metrics stable
- [ ] Ready for production traffic

### Stability Metrics to Track

```bash
#!/bin/bash
echo "=== Stability Report (Day $(date +%d)) ==="
echo ""
echo "Uptime:"
docker-compose exec api uptime

echo ""
echo "Error Rate:"
curl -s http://localhost:8000/health/metrics | jq '.error_rate'

echo ""
echo "Response Time:"
curl -s http://localhost:8000/health/metrics | jq '.avg_response_time'

echo ""
echo "Container Restarts:"
docker-compose ps | grep -E "api|worker|db" | awk '{print $1, $(NF-1)}'

echo ""
echo "Memory Usage:"
docker stats --no-stream | awk 'NR>1 {print $1, $6}'

echo ""
echo "Latest Backup:"
ls -lh backups/ | head -2 | tail -1

echo ""
echo "Log Errors (24h):"
docker-compose logs --since 24h | grep ERROR | wc -l
```

---

## Acceptance Criteria Verification

### AC1: Docker Compose with All Services
```bash
# ✅ Verify all 5 services defined
docker-compose config | grep "services:" -A 50 | grep -E "api:|db:|redis:|worker:|nginx:" | wc -l

# Expected: 5 services
```

### AC2: SQLite → PostgreSQL Migration
```bash
# ✅ Verify migration completed
docker-compose exec db psql -U bottrading -d bottrading \
  -c "SELECT * FROM migration_history ORDER BY executed_at DESC LIMIT 1;"

# Expected: Entry showing migration executed
```

### AC3: Automated Backup/Restore with Cleanup
```bash
# ✅ Verify backup scripts exist and work
python scripts/backup_restore.py --help

# Expected: Help output showing backup, restore, list, cleanup commands
```

### AC4: Health Checks on API, DB, Redis
```bash
# ✅ Verify 6 endpoints exist and respond
for endpoint in health health/detailed health/database health/redis health/dependencies health/metrics; do
  echo -n "$endpoint: "
  curl -s http://localhost:8000/$endpoint | jq -r '.status // "OK"'
done

# Expected: All return response (healthy or OK)
```

### AC5: Alert Thresholds Configured
```bash
# ✅ Verify AlertManager configured
docker-compose exec api python -c "from apps.api.health_check import AlertManager; \
  am = AlertManager(); print(f'Error threshold: {am.error_rate_threshold}')"

# Expected: Thresholds output
```

### AC6: Secrets Management with Validation
```bash
# ✅ Verify secrets loaded securely
docker-compose exec api python -c "from apps.api.config import settings; \
  print(f'JWT Secret length: {len(settings.JWT_SECRET)}')"

# Expected: Output shows secret is loaded (but don't print actual secret!)
```

### AC7: Production Configuration Templates
```bash
# ✅ Verify .env.example has all variables
grep -E "^[A-Z_]+=" .env.example | wc -l

# Expected: 40+ variables defined
```

### AC8: Startup Automation & Orchestration
```bash
# ✅ Verify startup script exists and is executable
ls -la scripts/startup.sh
file scripts/startup.sh

# Expected: -rwxr-xr-x (executable)
```

### AC9: Comprehensive Documentation
```bash
# ✅ Verify all documentation files
ls -la PHASE7_COMPLETE.md DEPLOYMENT_GUIDE.sh OPERATIONS_RUNBOOK.md SECURITY_HARDENING.md

# Expected: All files exist and are readable
```

### AC10: SSL/TLS Support
```bash
# ✅ Verify SSL certificates configured
openssl x509 -in docker/nginx/ssl/certificate.crt -noout -text | grep "Subject:"

# Expected: Certificate details displayed
```

### AC11: Rate Limiting (100/s API, 1000/s UI)
```bash
# ✅ Verify rate limiting zones defined
grep -A 2 "limit_req_zone" docker/nginx/nginx.conf

# Expected: api_limit and dashboard_limit zones shown
```

### AC12: Health Check Logging & Metrics
```bash
# ✅ Verify metrics tracked
curl -s http://localhost:8000/health/metrics | jq 'keys[]'

# Expected: request_count, error_count, avg_response_time, uptime
```

---

## Production Sign-Off

### Technical Sign-Off
- [ ] All 12 acceptance criteria verified ✅
- [ ] 7-day stability test passed ✅
- [ ] Security hardening checklist completed ✅
- [ ] Backup/restore tested ✅
- [ ] Performance metrics acceptable ✅

### Operations Readiness
- [ ] Team trained on operational procedures ✅
- [ ] Runbook available and reviewed ✅
- [ ] On-call rotation established ✅
- [ ] Escalation procedures documented ✅
- [ ] Incident response plan ready ✅

### Security Approval
- [ ] Security audit completed ✅
- [ ] No hardcoded secrets found ✅
- [ ] SSL/TLS certificates in place ✅
- [ ] Rate limiting active ✅
- [ ] Security headers verified ✅

### Go-Live Approval
- [ ] Product owner sign-off ✅
- [ ] Security team sign-off ✅
- [ ] DevOps team sign-off ✅
- [ ] Scheduled maintenance window[if needed]
- [ ] Rollback procedure documented ✅

---

## Rollback Procedures

### If Critical Issues Detected

1. **Stop New Traffic**
   ```bash
   docker-compose down
   ```

2. **Restore from Pre-Deployment Backup**
   ```bash
   python scripts/backup_restore.py list  # Find backup before deployment
   python scripts/backup_restore.py restore ./backups/backup_before_deployment.sql.gz
   ```

3. **Restart Services**
   ```bash
   docker-compose up -d
   ```

4. **Verify Rollback**
   ```bash
   curl http://localhost:8000/health
   ```

5. **Analyze Issue**
   - Export logs: `docker-compose logs > issue_logs.txt`
   - Review error patterns
   - Document root cause

---

## Post-Production Monitoring

### Daily (Automated)
```bash
# Create cron job for daily health check
0 8 * * * /opt/bottrading/scripts/daily_healthcheck.sh
```

### Weekly (Manual)
- [ ] Review error logs
- [ ] Analyze performance trends
- [ ] Check backup completeness
- [ ] Review security logs

### Monthly (Quarterly Review)
- [ ] Capacity planning
- [ ] Security audit
- [ ] Update runbooks
- [ ] Training refresh

---

**Deployment Status**: ✅ COMPLETE

**Deployed Date**: _____________  
**Verified By**: _____________  
**Approved By**: _____________  
**Notes**: _____________

---

For issues or questions, refer to:
- [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md) - Daily operations
- [SECURITY_HARDENING.md](SECURITY_HARDENING.md) - Security procedures
- [PHASE7_COMPLETE.md](PHASE7_COMPLETE.md) - Architecture & design
