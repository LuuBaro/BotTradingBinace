# Production Operations Runbook

**Phase 7 Production Deployment - Operations Manual**

## Quick Reference

### Health Check
```bash
# Simple health check
curl http://localhost:8000/health

# Detailed metrics
curl http://localhost:8000/health/detailed | jq .

# Database health
curl http://localhost:8000/health/database | jq .

# Redis health
curl http://localhost:8000/health/redis | jq .

# All dependencies
curl http://localhost:8000/health/dependencies | jq .
```

### Service Management
```bash
# Check status
docker-compose ps

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f api
docker-compose logs -f db
docker-compose logs -f redis
docker-compose logs -f worker

# Restart service
docker-compose restart api
docker-compose restart worker

# Stop all services
docker-compose down

# Start all services
docker-compose up -d

# Full restart
docker-compose restart
```

### Backup & Recovery
```bash
# Create backup
docker-compose exec db pg_dump -U bottrading bottrading | gzip > ./backups/backup_$(date +%Y%m%d_%H%M%S).sql.gz

# List backups
ls -lh ./backups/

# Restore backup (with data loss warning)
echo "⚠️  This will DELETE all current data. Confirm? [y/N]"
# Then:
cat ./backups/backup_20240115_020000.sql.gz | gunzip | docker-compose exec -T db psql -U bottrading bottrading

# Verify restore
curl http://localhost:8000/health
```

---

## Daily Checklist

### Morning (UTC 8:00)
- [ ] Check all services running: `docker-compose ps`
- [ ] Verify API health: `curl http://localhost:8000/health`
- [ ] Check error rates: `curl http://localhost:8000/health/metrics | jq '.error_rate'`
- [ ] Verify last backup: `ls -lt ./backups/ | head -5`
- [ ] Check disk space: `df -h` (ensure >10% free)
- [ ] Check logs for errors: `docker-compose logs --since 24h | grep ERROR`

### Before Trading Hours
- [ ] Verify Redis connectivity: `docker-compose exec redis redis-cli ping`
- [ ] Check database connections: `curl http://localhost:8000/health/database`
- [ ] Verify all workers running: `docker-compose ps | grep worker`
- [ ] Test API endpoints: `curl http://localhost:8000/api/health`

### After Trading Hours
- [ ] Archive logs: `tar -czf logs/$(date +%Y%m%d).tar.gz logs/*.log 2>/dev/null`
- [ ] Verify backup completed: `ls -lh ./backups/ | head -1`
- [ ] Check system resources: `docker stats --no-stream`
- [ ] Review error logs: `docker-compose logs --since 24h | grep -i error`

### Weekly (Sunday)
- [ ] Full system test: Run `python verify_phase7.py`
- [ ] Backup verification: Test restore on dev environment
- [ ] Security check: Verify no secrets in logs
- [ ] Update documentation: Record any incidents

### Monthly (1st)
- [ ] Database optimization: `docker-compose exec db vacuumdb -U bottrading bottrading`
- [ ] Log cleanup: `find ./logs -mtime +90 -delete`
- [ ] Security audit: Check failed login attempts
- [ ] Capacity planning: Analyze growth trends

---

## Troubleshooting Guide

### API is Down

**Symptoms**: Cannot reach http://localhost:8000/health

**Resolution**:
```bash
# 1. Check if API container is running
docker-compose ps api

# 2. View API logs
docker-compose logs api --tail 50

# 3. Check for port conflicts
netstat -tlnp | grep 8000

# 4. Restart API
docker-compose restart api

# 5. If still failing, check dependencies
curl http://localhost:8000/health/dependencies

# 6. Full restart (nuclear option)
docker-compose down
docker-compose up -d

# 7. Verify
curl -v http://localhost:8000/health
```

### Database Connection Errors

**Symptoms**: API logs show "psycopg2.OperationalError" or "cannot connect to server"

**Resolution**:
```bash
# 1. Check if PostgreSQL is running
docker-compose ps db

# 2. Check database logs
docker-compose logs db --tail 50

# 3. Test database connectivity
docker-compose exec db psql -U bottrading -d bottrading -c "SELECT 1;"

# 4. Check if volume is mounted
docker-compose exec db psql -U bottrading -d bottrading -c "SELECT pg_database.datname FROM pg_database;"

# 5. Restart database
docker-compose restart db
docker-compose restart api

# 6. Verify connection
curl http://localhost:8000/health/database
```

**Common Issues**:
- **"FATAL: role 'bottrading' does not exist"**: Database wasn't initialized
  - Solution: `docker-compose down -v && docker-compose up -d`
- **"could not translate host name"**: DNS/networking issue
  - Solution: Check `.env.production` has correct `DB_HOST=db`

### Redis Connection Issues

**Symptoms**: Cache operations fail, Celery tasks not queuing

**Resolution**:
```bash
# 1. Check Redis status
docker-compose ps redis

# 2. Test Redis connection
docker-compose exec redis redis-cli ping

# 3. Check Redis logs
docker-compose logs redis --tail 50

# 4. Authenticate if password protected
docker-compose exec redis redis-cli -a $REDIS_PASSWORD ping

# 5. Clear cache (use carefully!)
docker-compose exec redis redis-cli FLUSHDB

# 6. Restart Redis
docker-compose restart redis
docker-compose restart api

# 7. Verify
curl http://localhost:8000/health/redis
```

### High Memory Usage

**Symptoms**: Docker stats show memory near limit, OOM killer events

**Resolution**:
```bash
# 1. Check memory usage
docker stats --no-stream

# 2. Identify problem service
docker stats --no-stream | sort -k7 -h | tail -3

# 3. Check logs for memory leaks
docker-compose logs <service> | grep -i "memory\|leak"

# 4. Restart problematic service
docker-compose restart <service>

# 5. Check Celery worker task count
docker-compose exec worker celery -A celery_app inspect active | jq '.[] | length'

# 6. Restart worker to clear tasks
docker-compose restart worker

# 7. Monitor memory over time
watch -n 5 'docker stats --no-stream'
```

### High CPU Usage

**Symptoms**: System slow, CPU near 100%, docker stats shows high CPU

**Resolution**:
```bash
# 1. Check CPU usage per service
docker stats --no-stream

# 2. Check if migrations are running
docker-compose logs api | grep -i "migrate\|upgrade"

# 3. Check active database queries
docker-compose exec db psql -U bottrading -d bottrading \
  -c "SELECT pid, state, query FROM pg_stat_activity WHERE state != 'idle';"

# 4. Kill long-running queries (if needed)
docker-compose exec db psql -U bottrading -d bottrading \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE duration > interval '1 hour';"

# 5. Restart affected service
docker-compose restart api

# 6. Monitor
watch -n 5 'docker stats --no-stream'
```

### Slow API Response Times

**Symptoms**: API endpoints take >2000ms, curl shows slow responses

**Resolution**:
```bash
# 1. Check API metrics
curl http://localhost:8000/health/metrics | jq '.response_times'

# 2. Check slow queries in database
docker-compose exec db psql -U bottrading -d bottrading << EOF
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC LIMIT 10;
EOF

# 3. Check network latency to database
docker-compose exec api ping db

# 4. Check connection pool utilization
curl http://localhost:8000/health/database | jq '.latency'

# 5. Increase database connection pool
# Edit .env.production: DB_POOL_SIZE=20
docker-compose restart api

# 6. Check for lock contention
docker-compose exec db psql -U bottrading -d bottrading \
  -c "SELECT * FROM pg_locks WHERE NOT granted;"

# 7. Restart database
docker-compose restart db
docker-compose restart api
```

### Celery Worker Not Processing Tasks

**Symptoms**: Tasks stuck in Redis queue, worker logs show no activity

**Resolution**:
```bash
# 1. Check if worker is running
docker-compose ps worker

# 2. Check worker logs
docker-compose logs worker --tail 100

# 3. Check active tasks
docker-compose exec redis redis-cli -a $REDIS_PASSWORD LLEN celery

# 4. Check queue statistics
docker-compose exec worker celery -A celery_app inspect stats

# 5. Restart worker
docker-compose restart worker

# 6. Monitor worker
docker-compose logs -f worker

# 7. If persistent, reset queue
docker-compose exec redis redis-cli -a $REDIS_PASSWORD FLUSHDB
docker-compose restart worker
```

### SSL/TLS Certificate Errors

**Symptoms**: HTTPS connections fail, certificate expired warnings

**Resolution**:
```bash
# 1. Check certificate validity
openssl x509 -in docker/nginx/ssl/certificate.crt -noout -dates

# 2. Check certificate details
openssl x509 -in docker/nginx/ssl/certificate.crt -noout -text | head -20

# 3. Renew Let's Encrypt certificate (if using)
certbot renew --quiet

# 4. Update nginx configuration with new cert paths

# 5. Reload nginx
docker-compose exec nginx nginx -s reload

# 6. Test HTTPS
curl -k https://localhost/health
```

### Running Out of Disk Space

**Symptoms**: "No space left on device" errors, df -h shows 100% usage

**Resolution**:
```bash
# 1. Check disk usage
df -h

# 2. Find large files
find . -type f -size +100M | sort -k5 -h | tail -20

# 3. Check Docker storage
du -sh /var/lib/docker/

# 4. Clean up old logs
find ./logs -mtime +30 -delete

# 5. Clean up old backups
ls -t ./backups/ | tail -n +6 | xargs rm -f

# 6. Clear Docker unused images and volumes
docker system prune -a --volumes -f

# 7. Check availability
df -h
```

### Backup Failures

**Symptoms**: Backup process fails, backup file not created

**Resolution**:
```bash
# 1. Check if backup directory exists
ls -la ./backups/

# 2. Check disk space
df -h ./backups/

# 3. Manually test backup
docker-compose exec -T db pg_dump -U bottrading bottrading > test.sql

# 4. Check database logs
docker-compose logs db | tail -20

# 5. Verify database integrity
docker-compose exec db psql -U bottrading -d bottrading -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';"

# 6. Try backup to stdout
docker-compose exec -T db pg_dump -U bottrading bottrading | head -20

# 7. Force backup
mkdir -p ./backups
docker-compose exec -T db pg_dump -U bottrading bottrading | gzip > ./backups/manual_backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

---

## Performance Tuning

### Increase API Worker Count
```bash
# Edit docker-compose.yml
# Change: uvicorn apps.api.main:app --workers 4
# To:     uvicorn apps.api.main:app --workers 8

docker-compose up -d api
```

### Increase Database Connection Pool
```bash
# Edit .env.production
# Change: DB_POOL_SIZE=10
# To:     DB_POOL_SIZE=20

docker-compose restart api
```

### Optimize Redis Settings
```bash
# Check current Redis config
docker-compose exec redis redis-cli CONFIG GET maxmemory

# Set memory limit
docker-compose exec redis redis-cli CONFIG SET maxmemory 2gb
docker-compose exec redis redis-cli CONFIG REWRITE
```

### Enable Database Query Logging
```bash
# Check current log_min_duration_statement
docker-compose exec db psql -U bottrading -d bottrading \
  -c "SHOW log_min_duration_statement;"

# Set to log queries > 1000ms
docker-compose exec db psql -U bottrading -d bottrading \
  -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"

docker-compose restart db
```

---

## Monitoring Commands

### System Health Overview
```bash
#!/bin/bash
echo "╔════════════════════════════════════════════════════════╗"
echo "║  Bot Trading Platform - System Health Report            ║"
echo "╚════════════════════════════════════════════════════════╝"

echo ""
echo "▸ Service Status"
docker-compose ps

echo ""
echo "▸ Resource Usage"
docker stats --no-stream | awk 'NR==1 || NR<=6'

echo ""
echo "▸ API Health"
curl -s http://localhost:8000/health | jq '.status'

echo ""
echo "▸ Database Status"
curl -s http://localhost:8000/health/database | jq '.status'

echo ""
echo "▸ Recent Errors (last 24h)"
docker-compose logs --since 24h | grep ERROR | wc -l

echo ""
echo "▸ Disk Usage"
df -h | grep -E "^/dev|^Filesystem"

echo ""
echo "▸ Latest Backup"
ls -lh ./backups/ | head -2 | tail -1
```

### Continuous Monitoring
```bash
# Watch all services every 10 seconds
watch -n 10 'docker-compose ps && echo "---" && docker stats --no-stream'

# Monitor specific service
watch -n 5 'docker-compose logs --since 5s api'

# Monitor API response times
watch -n 5 'curl -s http://localhost:8000/health/metrics | jq ".response_times"'
```

---

## Incident Response

### API Down in Production

1. **Immediate Action (0-5 min)**
   - [ ] Notify team/stakeholders
   - [ ] Check `docker-compose ps` - is API container running?
   - [ ] Check `docker-compose logs api --tail 20` for errors
   - [ ] Try quick restart: `docker-compose restart api`
   - [ ] Verify with: `curl http://localhost:8000/health`

2. **Investigation (5-15 min)**
   - [ ] Check dependencies: `curl http://localhost:8000/health/dependencies`
   - [ ] Check database: `curl http://localhost:8000/health/database`
   - [ ] Check Redis: `curl http://localhost:8000/health/redis`
   - [ ] Review full logs: `docker-compose logs api --tail 100 | less`
   - [ ] Check system resources: `docker stats`

3. **Resolution (15-30 min)**
   - [ ] If database issue: restart database
   - [ ] If Redis issue: restart Redis and API
   - [ ] If resource issue: kill non-critical services
   - [ ] If persistent: full restart `docker-compose down && docker-compose up -d`

4. **Post-incident (30+ min)**
   - [ ] Document root cause
   - [ ] Create backup from before outage
   - [ ] Review logs for patterns
   - [ ] Update runbook if needed
   - [ ] Communicate status to stakeholders

### Data Corruption Detected

1. **Stop the Bleeding**
   - [ ] Stop API to prevent further writes: `docker-compose stop api`
   - [ ] Stop worker: `docker-compose stop worker`
   - [ ] Create backup immediately: `docker-compose exec -T db pg_dump -U bottrading bottrading | gzip > emergency_backup.sql.gz`

2. **Assess Damage**
   - [ ] Connect to database: `docker-compose exec db psql -U bottrading -d bottrading`
   - [ ] Run integrity checks: `PRAGMA integrity_check;` (SQLite) or use pg_filedump
   - [ ] Identify affected records
   - [ ] Check transaction logs

3. **Recover**
   - [ ] Restore from last good backup
   - [ ] Verify data integrity
   - [ ] Restart services
   - [ ] Monitor for re-occurrence

### Security Incident

1. **Immediate Response**
   - [ ] Take affected system offline
   - [ ] Preserve logs: `docker-compose logs > incident_logs_$(date +%Y%m%d_%H%M%S).txt`
   - [ ] Rotate compromised secrets
   - [ ] Review access logs

2. **Investigation**
   - [ ] Identify attack vector
   - [ ] Check for lateral movement
   - [ ] Review network connections

3. **Recovery**
   - [ ] Patch vulnerability
   - [ ] Redeploy from clean backup
   - [ ] Monitor for re-entry

---

## Contact & Escalation

### Support Contacts
- **On-Call Engineer**: [contact on-call person]
- **DevOps Team**: [devops-team@company.com]
- **Security Team**: [security-team@company.com]

### Escalation Procedure
- **Severity 1 (Critical)**: All hands, immediate escalation
  - API completely down
  - Data corruption detected
  - Security breach confirmed
  
- **Severity 2 (High)**: Team notification
  - Degraded performance (>50% response time increase)
  - Memory/CPU critical
  - Database connectivity issues
  
- **Severity 3 (Medium)**: Ticket/logging
  - High error rates (>10%)
  - Slow but functional
  - Non-critical service down

---

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Celery Documentation](https://docs.celeryproject.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

**Last Updated**: Phase 7 Deployment
**Version**: 1.0.0  
**Owner**: DevOps Team
