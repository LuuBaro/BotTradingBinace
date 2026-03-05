# 🔴 PRODUCTION READINESS AUDIT - CHI TIẾT VẤN ĐỀ

**Ngày**: 5 Tháng 3, 2026 | **Trạng Thái**: ⚠️ **CÓ VẤN ĐỀ CẦN SỬA** | **Mức Độ**: CRITICAL + HIGH

---

## ⚠️ CÁC VẤN ĐỀ PHÁT HIỆN

### 🔴 **CRITICAL - Bảo Mật**

#### 1. **API Keys & Secrets Lộ Lõa Trong .env**
**Vị trí**: `.env` (các dòng công khai)

```dotenv
BINANCE_API_KEY='xxx_BINANCE_API_KEY_EXPOSED_xxx'
BINANCE_API_SECRET='xxx_BINANCE_API_SECRET_EXPOSED_xxx'
TELEGRAM_BOT_TOKEN='xxx_TELEGRAM_BOT_TOKEN_EXPOSED_xxx'
OPENAI_API_KEY='xxx_OPENAI_API_KEY_EXPOSED_xxx'
ANTHROPIC_API_KEY='xxx_ANTHROPIC_API_KEY_EXPOSED_xxx'
GROQ_API_KEY='xxx_GROQ_API_KEY_EXPOSED_xxx'
GOOGLE_CLIENT_ID='xxx_GOOGLE_CLIENT_ID_EXPOSED_xxx'
SMTP_USERNAME='xxx_SMTP_USERNAME_EXPOSED_xxx'
SMTP_PASSWORD='xxx_SMTP_PASSWORD_EXPOSED_xxx'
```

**Rủi Ro**: 🔓 Ác ý có thể:
- Sử dụng API keys để trích xuất tiền
- Truy cập tài khoản Binance thực
- Lấy quyền kiểm soát Telegram bot
- Đọc/gửi email từ Gmail
- Chạy các yêu cầu LLM với chi phí cao

**Giải Pháp**:
- [ ] **Ngay lập tức**: Thay đổi TẤT CẢ API keys + passwords
  - Binance: https://www.binance.com/en/my/settings/api-management
  - Telegram: Nhắn `/newbotfather` → `/revoke` bot cũ
  - OpenAI, Groq, Anthropic: Regenerate API keys
  - Google Cloud: Generate new OAuth credentials
  - Gmail: Generate new app password

- [ ] **Cài đặt sản xuất**: Sử dụng **Vault** hoặc **Secret Manager**
  ```bash
  # Option 1: AWS Secrets Manager
  aws secretsmanager get-secret-value --secret-id prod/binance
  
  # Option 2: HashiCorp Vault
  vault kv get secret/binance
  
  # Option 3: Environment Variables (CI/CD)
  # Đặt trong GitHub Secrets hoặc GitLab CI Variables
  ```

- [ ] **Cập nhật code**:
  ```python
  # Trong config.py, load từ vault thay vì .env
  import os
  
  # Không bao giờ có API key trong mã nguồn hoặc .env
  BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")  # Từ CI/CD secrets
  ```

---

#### 2. **CORS Cho Phép Tất Cả Origins**
**Vị trí**: `apps/api/main.py` dòng 119

```python
allow_origins=["*"],  # TODO: Restrict in production  ← ⚠️ NGUY HIỂM
```

**Vấn đề**: Bất kỳ website nào cũng có thể gọi API của bạn

**Giải Pháp**:
```python
# Thay đổi thành:
allow_origins=[
    "https://yourdomain.com",      # Production frontend
    "https://www.yourdomain.com",
    "http://localhost:3000",       # Dev only
],
allow_credentials=True,
allow_methods=["GET", "POST", "PUT", "DELETE"],
allow_headers=["*"],
```

---

#### 3. **Unused sqlite3 Imports (Inconsistent DB)**
**Vị trí**:
- `apps/api/main.py` dòng 5: `import sqlite3`
- `packages/shared/database.py` dòng 6: `import sqlite3`

**Vấn đề**: Code vẫn có xử lý SQLite nhưng production dùng PostgreSQL

```python
# main.py dòng 57
except sqlite3.OperationalError as exc:  # ← Sẽ không bao giờ xảy ra với PostgreSQL
    logger.warning("api_init_db_skipped", error=str(exc))
```

**Giải Pháp**: Xóa código SQLite không dùng

---

### 🟡 **HIGH - Cấu Hình Production**

#### 4. **Default Database URL Vẫn Là SQLite**
**Vị trí**: `packages/shared/config.py`

```python
db_url: str = Field(
    default="sqlite+aiosqlite:///./data/trading.db",  # ← SQLite!
    description="Async database URL",
)
```

**Vấn đề**: Nếu không set `DB_URL` env var, sẽ dùng SQLite

**Giải Pháp**:
```bash
# .env.production (không public)
DB_URL=postgresql://bottrading:STRONG_PASSWORD@db.example.com:5432/bottrading
```

---

#### 5. **API Port Không Nhất Quán**
**Vị trí**: `packages/shared/config.py`

```python
api_port: int = Field(default=8001, description="API server port")  # Default = 8001
```

Nhưng docker-compose.yml sử dụng port 8000

**Giải Pháp**:
```python
api_port: int = Field(default=8000, description="API server port")
```

---

#### 6. **JWT Secret Không Configured (Insecure)**
**Vị trí**: `.env`

```dotenv
JWT_SECRET=changeme_set_long_random_string_here_at_least_32_chars
```

**Vấn đề**: Nếu production dùng giá trị mặc định này, tất cả JWT tokens có thể giả mạo

**Giải Pháp**:
```bash
# Tạo secret mạnh
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Kết quả: "aBcD1eF2gH3iJ4kL5mN6oP7qR8sT9uV0wX"

# Đặt trong .env.production
JWT_SECRET=aBcD1eF2gH3iJ4kL5mN6oP7qR8sT9uV0wX
```

---

#### 7. **DB Passwords Không Mạnh**
**Vị trí**: `.env`

```dotenv
DB_PASSWORD=changeme_set_strong_password_here
REDIS_PASSWORD=changeme_set_strong_password_here
```

**Giải Pháp**:
```bash
# Tạo password mạnh (32 ký tự)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Đặt trong .env.production
DB_PASSWORD=xY9zaBcD1eF2gH3iJ4kL5mN6oP7qR8sT
REDIS_PASSWORD=aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV
```

---

### 🟠 **MEDIUM - Tính Năng Không Hoàn Thành**

#### 8. **Telegram Bot: TODO Comments (Incomplete)**
**Vị trí**: `apps/telegram/bot.py`

```python
# Line 275:  # TODO: Integrate with actual latency metrics from worker
# Line 300:  # TODO: Integration with actual health checks
# Line 332:  # TODO: Integration with real price from Binance/API
# Line 613:  # TODO: Call worker pause API
# Line 630:  # TODO: Call worker resume API
# Line 724:  # TODO: Call worker sync API
# Line 1083: # TODO: Execute close
# Line 1088: # TODO: Execute close all
```

**Tác Động**: Một số lệnh sẽ không hoạt động đầy đủ

**Giải Pháp**: Xem [ARCHITECTURE.md](ARCHITECTURE.md) để cài đặt đầy đủ các endpoint

---

#### 9. **Phase 4 API: Pause/Resume/Sync APIs Không Hoàn Thành**
**Vị trí**: `apps/api/phase4_routes.py` dòng 2435, 2456

```python
# Line 2435: # TODO: Call worker sync endpoint
# Line 2456: "is_paused": False, # TODO: Connect to global state
```

**Tác Động**: Các lệnh điều khiển worker từ UI sẽ không hoạt động

---

#### 10. **Health Check: Missing Alert Integration**
**Vị trí**: `apps/api/health_check.py` dòng 301

```python
# TODO: Send to external alerting system (Slack, PagerDuty, etc.)
```

---

## ✅ CÁC ĐIỂM TỐT

| Điểm | Trạng Thái |
|------|-----------|
| **Biên dịch** | ✅ 0 errors |
| **Code quality** | ✅ No linting issues |
| **Architecture** | ✅ 4 services tích hợp |
| **Database** | ✅ PostgreSQL + Redis |
| **Docker** | ✅ Docker Compose ready |
| **Auth** | ✅ JWT + RBAC implemented |
| **Logging** | ✅ Structured logging |

---

## 🔧 PRODUCTION CHECKLIST

### Giai Đoạn 1: Sửa Bảo Mật (HÔM NAY)

- [ ] **Thay đổi TẤT CẢ API Keys**
  - [ ] Binance API key + secret
  - [ ] Telegram bot token
  - [ ] OpenAI, Groq, Anthropic keys
  - [ ] Google OAuth credentials
  - [ ] Gmail app password

- [ ] **Sửa Code Issues**
  - [ ] Xóa unused `import sqlite3` (main.py, database.py)
  - [ ] Sửa CORS: `allow_origins=["*"]` → whitelist specific domains
  - [ ] Sửa default API port: 8001 → 8000
  - [ ] Sửa default DB URL: SQLite → leave empty (sẽ load từ env)

- [ ] **Tạo .env.production** (gitignored)
  ```bash
  cp .env .env.production
  # Chỉnh sửa với production values:
  # - DB_URL: PostgreSQL connection
  # - All API keys: NEW KEYS (không phải từ .env cũ)
  # - JWT_SECRET: Generated strong key
  # - DB_PASSWORD, REDIS_PASSWORD: Strong passwords
  # - CORS_ORIGINS: Your domain only
  ```

- [ ] **Cập nhật Vault/Secrets Manager**
  - Nếu dùng AWS: Tạo secrets trong Secrets Manager
  - Nếu dùng GitHub: Set GitHub Secrets
  - Nếu dùng Docker: Dùng Docker Secrets

---

### Giai Đoạn 2: Kiểm Tra Cấu Hình (NGÀY MAI)

- [ ] Chạy database migrations: `alembic upgrade head`
- [ ] Test API với JWT: `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/health`
- [ ] Test CORS: Verify chỉ `yourdomain.com` có thể gọi API
- [ ] Test Telegram: `/health` command
- [ ] Test LLM: Kiểm tra AI decision engine hoạt động

---

### Giai Đoạn 3: Hoàn Thành Tính Năng (NỬA TUẦN NÀY)

- [ ] Hoàn thành Telegram bot endpoints:
  - [ ] `/pause` → call worker API
  - [ ] `/resume` → call worker API
  - [ ] `/price` → real price from Binance
  - [ ] `/close` → actual close position

- [ ] Hoàn thành Phase 4 APIs:
  - [ ] Pause/resume worker
  - [ ] Real global state tracking
  - [ ] Worker sync endpoint

- [ ] Thiết lập alerting:
  - [ ] Slack/PagerDuty integration
  - [ ] Email alerts
  - [ ] Telegram alerts

---

### Giai Đoạn 4: Chuẩn Bị Deployment (TUẦN NÀY)

- [ ] Database:
  - [ ] PostgreSQL 15+ instance
  - [ ] Backups tự động hằng ngày
  - [ ] SSL/TLS enabled
  - [ ] Firewall chỉ cho phép từ app server

- [ ] SSL/TLS:
  - [ ] Cert từ Let's Encrypt hoặc provider
  - [ ] HTTPS bắt buộc (redirect HTTP → HTTPS)

- [ ] Monitoring:
  - [ ] Prometheus metrics
  - [ ] Grafana dashboards
  - [ ] Error tracking (Sentry)
  - [ ] Log aggregation (ELK, CloudWatch)

- [ ] Load Testing:
  - [ ] JMeter: 100 concurrent users
  - [ ] Verify response time < 200ms
  - [ ] Check database performance

- [ ] Security Audit:
  - [ ] Penetration testing
  - [ ] OWASP top 10 check
  - [ ] API key rotation policy

---

## 🚨 TÓML TẮT MỨC ĐỘ

```
CRITICAL (Sửa Ngay):
  [🔴] API keys lộ lõa trong .env
  [🔴] CORS allow_origins=["*"]
  [🔴] JWT_SECRET mặc định yếu

HIGH (Sửa Hôm Nay):
  [🟡] Unused sqlite3 imports
  [🟡] Default DB URL = SQLite
  [🟡] Weak database passwords

MEDIUM (Sửa Ngày/Tuần):
  [🟠] Telegram bot TODOs
  [🟠] API pause/resume incomplete
  [🟠] No external monitoring

LOW (Tuần/Tháng):
  [🟢] Add comprehensive logging
  [🟢] Performance optimization
  [🟢] Documentation updates
```

---

## 📋 HÀNH ĐỘNG NGAY LẬP TỨC

### 1. Xóa Unused Imports
```python
# File: apps/api/main.py
# Xóa dòng 5: import sqlite3

# File: packages/shared/database.py
# Xóa dòng 6: import sqlite3
```

### 2. Sửa CORS
```python
# File: apps/api/main.py dòng 119
# Thay đổi từ:
allow_origins=["*"],

# Thành:
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com", 
    "http://localhost:3000",  # Dev only
],
```

### 3. Tạo .env.production
```bash
# Không public lên git - thêm vào .gitignore
.env.production
.env.*.local

# Copy từ .env
cp .env .env.production

# Chỉnh sửa tất cả secrets với production values
# Sử dụng strong passwords và valid API keys từ các provider
```

---

## ✅ Con Đường Tới Production (Timeline)

| Giai Đoạn | Thời Gian | Công Việc |
|-----------|-----------|----------|
| **Sửa Bảo Mật** | Hôm nay | API keys, CORS, secrets |
| **Kiểm Tra Config** | Ngày mai | Database, TLS, deployment |
| **Hoàn Thành Feature** | Nửa tuần | Telegram, APIs, monitoring |
| **Chuẩn Bị Deploy** | Tuần này | Testing, audit, rollout plan |
| **Deployment** | Tuần sau | Production rollout |

---

## 🎯 DẤU HIỆU SẴN SÀNG PRODUCTION

✅ Khi hoàn thành, hệ thống sẽ có:

- [x] 0 compilation errors
- [x] Complete documentation
- [x] Clean codebase
- [ ] All secrets in vault (not .env)
- [ ] CORS restricted to specific domains
- [ ] SSL/TLS enabled
- [ ] Database backups automated
- [ ] Monitoring & alerting
- [ ] Load testing passed
- [ ] Security audit done

---

**Tiếp Theo**: Làm [Production Checklist](PRODUCTION_SETUP.md) theo thứ tự để lên production an toàn!
