# Production Security Hardening Guide

**Phase 7 Complete - Security Implementation Checklist**

---

## Pre-Deployment Security

### 1. Secrets Management ✅

**Status**: Implemented in `apps/api/config.py`

**What's Done**:
- Environment variables required: JWT_SECRET (32+ chars), DB_PASSWORD (12+ chars), REDIS_PASSWORD (12+ chars)
- SecretsManager class supports Docker secrets from `/run/secrets/`
- Runtime validation checks minimum lengths
- `.env.example` template with no default values

**To Deploy**:
```bash
# Generate strong secrets
JWT_SECRET=$(openssl rand -urlsafe 32 | head -c32)
DB_PASSWORD=$(openssl rand -base64 20)
REDIS_PASSWORD=$(openssl rand -base64 20)

# Create .env.production (NEVER commit this!)
cat > .env.production << EOF
ENVIRONMENT=production
JWT_SECRET=$JWT_SECRET
DB_PASSWORD=$DB_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
EOF

# Ensure permissions
chmod 600 .env.production

# Add to .gitignore
echo ".env.production" >> .gitignore
```

**Verification**:
```bash
# Check secrets loaded correctly
docker-compose exec api python -c "from apps.api.config import settings; print('✓ Config loaded')"

# Verify no secrets in container environment
docker-compose exec api env | grep -i secret    # Should show no values
docker-compose exec api env | grep -i password  # Should show no values
```

### 2. Image Vulnerability Scanning ✅

**Status**: Included in Dockerfiles

**What's Done**:
- Base images: python:3.11-slim (minimal attack surface)
- Alpine variants for Redis, PostgreSQL, Nginx
- Security: No elevated privileges in containers

**To Deploy**:
```bash
# Scan for vulnerabilities
docker-compose build --no-cache

# Use Trivy for deeper scanning (optional)
trivy image api:latest
trivy image db:latest

# Check for outdated dependencies
docker-compose exec api pip-audit
```

**Hardening**:
```dockerfile
# Use minimal base image
FROM python:3.11-slim

# Run as non-root user
RUN useradd -m -u 1000 bottrading
USER bottrading

# No setuid/setgid
RUN chmod -s /bin/su /bin/mount /bin/umount 2>/dev/null || true
```

### 3. Network Segmentation ✅

**Status**: Implemented in docker-compose.yml

**What's Done**:
- Internal Docker network: `bottrading-network`
- Services communicate only within network
- Only nginx exposed to outside
- Health checks on internal endpoints

**What to Do**:
```bash
# Verify network isolation
docker-compose ps

# List only exposed ports
docker ps --format "table {{.Names}}\t{{.Ports}}"
# Only nginx should have port mappings

# Verify inter-service communication
docker-compose exec api curl -s http://db:5432 
# Should fail (good - using PostgreSQL protocol, not HTTP)

docker-compose exec api curl -s http://redis:6379 ping
# Should work (internal communication)
```

### 4. Database Security ✅

**Status**: Implemented in docker-compose.yml and docker/postgres/init.sql

**What's Done**:
- PostgreSQL user (not superuser): `bottrading`
- Database-level encryption ready
- SQL injection protection via SQLAlchemy ORM
- Row-level audit logging setup

**To Deploy**:
```bash
# Verify database user permissions
docker-compose exec db psql -U bottrading -d bottrading \
  -c "SELECT datname FROM pg_database WHERE datname='bottrading';"

# Check user role
docker-compose exec db psql -U postgres -d bottrading \
  -c "SELECT rolname, rolcanlogin, rolsuper FROM pg_roles WHERE rolname='bottrading';"

# Verify audit table exists
docker-compose exec db psql -U bottrading -d bottrading \
  -c "SELECT * FROM audit.audit_log LIMIT 1;"

# Enable SSL connections (optional)
docker-compose exec db psql -U postgres -d bottrading \
  -c "ALTER SYSTEM SET ssl = on;"
```

### 5. API Security Headers ✅

**Status**: Implemented in docker/nginx/conf.d/default.conf

**What's Done**:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Content-Security-Policy headers
- CORS configuration
- HSTS ready for HTTPS

**To Verify**:
```bash
# Check security headers
curl -v http://localhost:8000/health 2>&1 | grep -i "x-\|content-security\|strict"

# Should see:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
```

### 6. JWT Authentication ✅

**Status**: Implemented in apps/api/config.py

**What's Done**:
- HS256 algorithm (configurable)
- 24-hour expiration (configurable)
- SECRET validation (32 char minimum)
- Token encryption at rest

**To Test**:
```bash
# Get bearer token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | jq -r '.access_token')

# Verify token
echo $TOKEN | cut -d. -f1 | base64 -d | jq .  # Header
echo $TOKEN | cut -d. -f2 | base64 -d | jq .  # Payload

# Use token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/health
```

### 7. Rate Limiting ✅

**Status**: Implemented in docker/nginx/conf.d/default.conf

**What's Done**:
- API rate limit: 100 requests/second per IP
- Dashboard limit: 1000 requests/second per IP
- Zone-based limiting
- 429 Too Many Requests response

**To Test**:
```bash
# Test rate limit (will hit limit after 100 requests in quick succession)
for i in {1..150}; do
  curl -s http://localhost:8000/health | grep status
done | sort | uniq -c

# Should see mostly 200s, then 429s
```

### 8. HTTPS/TLS Configuration ✅

**Status**: Self-signed certificates generated, ready for Let's Encrypt

**What's Done**:
- Nginx configured for SSL/TLS
- Certificate paths defined
- HSTS headers ready
- HTTP→HTTPS redirect ready

**To Deploy with Let's Encrypt**:
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate (stop nginx first if using standalone)
docker-compose stop nginx
sudo certbot certonly --standalone -d yourdomain.com
docker-compose start nginx

# Update nginx configuration with cert paths:
# ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
# ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

# Enable auto-renewal
sudo certbot renew --dry-run
sudo systemctl enable certbot.timer
```

---

## Runtime Security

### 1. Container Scanning

```bash
# Check running containers
docker ps

# Verify only necessary services running
docker-compose ps

# Check for unnecessary exposed ports
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

### 2. File Integrity Monitoring

```bash
# Create baseline
find . -type f -name "*.py" -o -name "*.json" -o -name "*.sql" | xargs md5sum > .baseline.md5

# Check integrity
md5sum -c .baseline.md5

# Verify no unauthorized changes
git status
git diff
```

### 3. Access Logging

```bash
# API access logs
docker-compose logs api | grep -E "GET|POST|PUT|DELETE"

# Database access logs
docker-compose exec db tail -f /var/log/postgresql/postgresql.log

# Nginx access logs
docker-compose logs nginx | grep access

# Failed authentication attempts
docker-compose logs api | grep -i "unauthorized\|forbidden"
```

### 4. Secret Rotation

```bash
# Generate new secrets
NEW_JWT_SECRET=$(openssl rand -urlsafe 32 | head -c32)
NEW_DB_PASSWORD=$(openssl rand -base64 20)

# Update .env.production
sed -i "s/JWT_SECRET=.*/JWT_SECRET=$NEW_JWT_SECRET/" .env.production
sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$NEW_DB_PASSWORD/" .env.production

# Restart services
docker-compose down
docker-compose up -d

# Verify connectivity
curl http://localhost:8000/health
```

### 5. Vulnerability Management

```bash
# Check for known vulnerabilities in dependencies
pip-audit

# Update vulnerable packages (carefully!)
pip install --upgrade <package-name>

# Rebuild Docker images to include patches
docker-compose build --no-cache

# Restart services with new images
docker-compose up -d
```

---

## Operational Security

### 1. Backup Security

```bash
# Encrypt backups
gpg --symmetric ./backups/backup_20240115_020000.sql.gz

# Store encrypted backup off-site
aws s3 cp ./backups/backup_*.sql.gz.gpg s3://backup-bucket/ --sse

# Test restore with decryption
gpg --output backup_decrypted.sql.gz --decrypt backup_20240115_020000.sql.gz.gpg
```

### 2. Log Management

```bash
# Centralize logs (example with ELK stack)
docker-compose logs -f | logstash-forwarder

# Retain logs securely
find ./logs -mtime +90 -exec rm {} \;

# Archive historical logs
tar -czf logs/archive_$(date +%Y%m).tar.gz logs/*.log
```

### 3. Audit Trail

```bash
# Database audit trail
docker-compose exec db psql -U bottrading -d bottrading << EOF
SELECT timestamp, user_id, operation, table_name, changes 
FROM audit.audit_log 
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
EOF

# Access logs
docker-compose logs --since 24h | grep -E "auth|login|permission|denied"

# Configuration changes
git log --oneline -20
```

### 4. Incident Response Plan

**If Breach Detected**:
1. Isolate systems (pause containers)
2. Preserve evidence (export logs, backups)
3. Assess damage (what was accessed?)
4. Rotate all credentials
5. Rebuild from clean backup
6. Deploy patches
7. Monitor for re-compromise

```bash
# Incident response commands
docker-compose pause

# Export all logs
docker-compose logs > incident_$(date +%Y%m%d_%H%M%S).log

# Create snapshot of data
docker-compose exec db pg_dump -U bottrading bottrading > incident_backup_$(date +%Y%m%d_%H%M%S).sql

# Stop services
docker-compose down

# Later: restore from known-good backup
```

---

## Compliance Checklist

### Data Protection (GDPR)
- [ ] User data encrypted at rest
- [ ] Audit logs maintained (30+ days retention)
- [ ] Access logs maintained
- [ ] Backup encryption enabled
- [ ] Data retention policy: _____ days
- [ ] User deletion process documented

### Security Standards (ISO 27001)
- [ ] Access control policy defined
- [ ] Incident response plan documented
- [ ] Security awareness training completed
- [ ] Vulnerability management process implemented
- [ ] Patch management process implemented
- [ ] Security testing scheduled (monthly/quarterly)

### Operational Security
- [ ] Secrets rotation schedule: _____
- [ ] Backup testing schedule: _____
- [ ] Security audit schedule: _____
- [ ] Disaster recovery tested: _____
- [ ] RTO (Recovery Time Objective): _____ hours
- [ ] RPO (Recovery Point Objective): _____ hours

---

## Security Monitoring

### Real-time Alerts

```bash
# Monitor for suspicious activities
watch -n 5 'docker-compose logs --since 5s | grep -i "error\|denied\|unauthorized"'

# Alert on high error rates
curl -s http://localhost:8000/health/metrics | jq 'if .error_rate > 0.1 then "⚠️ HIGH ERROR RATE" else "✓ OK" end'

# Alert on slow responses
curl -s http://localhost:8000/health/metrics | jq 'if .avg_response_time > 2000 then "⚠️ SLOW API" else "✓ OK" end'
```

### Weekly Security Report

```bash
#!/bin/bash
echo "=== Security Report ==="
echo ""
echo "Failed login attempts:"
docker-compose logs --since 7d | grep -i "unauthorized\|forbidden" | wc -l

echo ""
echo "Database queries > 1 second:"
docker-compose logs db --since 7d | grep "duration:" | wc -l

echo ""
echo "Error rate:"
curl -s http://localhost:8000/health/metrics | jq '.error_rate'

echo ""
echo "Vulnerabilities found:"
pip-audit | wc -l

echo ""
echo "Audit log entries:"
docker-compose exec db psql -U bottrading -d bottrading \
  -c "SELECT COUNT(*) FROM audit.audit_log WHERE timestamp > NOW() - INTERVAL '7 days';"
```

---

## Production Deployment Checklist

### Pre-Deployment
- [ ] All secrets generated and stored securely
- [ ] SSL/TLS certificates obtained
- [ ] Firewall rules configured
- [ ] Backup system tested
- [ ] Disaster recovery plan reviewed
- [ ] Incident response contacts documented
- [ ] Security audit completed

### Deployment
- [ ] Services started successfully
- [ ] Health checks passing
- [ ] Security headers verified
- [ ] Rate limiting in effect
- [ ] Access logs being generated
- [ ] Audit logging active

### Post-Deployment
- [ ] Security monitoring enabled
- [ ] Alerting configured
- [ ] 24-hour stability verified
- [ ] No security incidents observed
- [ ] Backup schedule running
- [ ] Weekly security reports enabled

---

## Quick Security Commands

```bash
# Verify no secrets in code
grep -r "password\|secret\|token" . --include="*.py" --include="*.json" | grep -v ".env" | grep -v "\.gitignore"

# Check file permissions
find . -perm 777 -o -perm 666 | head -20

# Verify image signatures
docker inspect api | grep Digest
docker inspect db | grep Digest

# List all environment variables
docker-compose exec api env | grep -v "^PATH\|^HOME\|^PWD"

# Check Docker security options
docker inspect api | jq '.HostConfig | {Privileged, SecurityOpt, CapAdd, CapDrop}'

# Audit user access
docker-compose exec db psql -U postgres -d bottrading -c "SELECT * FROM pg_user;"
```

---

**Last Updated**: Phase 7 Production Deployment  
**Version**: 1.0.0  
**Review Date**: Quarterly
