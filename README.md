# AI Trading Bot - Binance USDⓈ-M Futures

**Production-grade autonomous trading system** | **Fully Operational** | **TypeScript + Python**

---

## Quick Links
- **📘 [Full Technical Architecture](ARCHITECTURE.md)** ← Start here for system design
- **🚀 [Quick Start Guide](QUICKSTART.md)** ← Setup instructions
- **📖 [Operations Runbook](OPERATIONS_RUNBOOK.md)** ← Running the system
- **⚙️ Guides**: [Risk Management](docs/archive/RISK_VAULT_CONFIG_GUIDE.md) | [Telegram Setup](docs/archive/TELEGRAM_SETUP_GUIDE.md)

---

## What This System Does

```
┌──────────────────────┐
│   Market Analysis    │  AIScout scans for opportunities
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  LLM Decision Engine │  Groq/OpenAI/Local LLM decides action
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  Risk Validation     │  Enforces position size + leverage limits
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Order Execution      │  Places orders on Binance (or mock)
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  Reconciliation      │  Keeps DB ↔ Exchange in sync
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  Monitoring          │  Real-time dashboard + Telegram alerts
└──────────────────────┘
```

**Core Features**:
- ✅ **AI-Powered Trading**: LLM-based decision engine with market regime detection
- ✅ **Crash-Safe**: Automatic position recovery on restarts
- ✅ **Risk Management**: 3-tier position sizing, dynamic risk config, circuit breaker
- ✅ **Multi-Mode**: Mock (testing) and Live (Binance) trading
- ✅ **Real-Time Dashboard**: React + WebSocket with mobile responsiveness
- ✅ **Telegram Bot**: 18 commands with 2-step confirmation for risky operations
- ✅ **Complete Audit Trail**: Event logging + access telemetry

---

## System Architecture

### Four Core Services

| Service | Port | Purpose | Language |
|---------|------|---------|----------|
| **FastAPI Server** | 8000 | REST API + WebSocket | Python |
| **Worker** | — | Trading loop + AI decisions | Python |
| **React Dashboard** | 3000 | Real-time monitoring UI | TypeScript |
| **Telegram Bot** | — | Remote control + alerts | Python |

### Tech Stack
- **Backend**: FastAPI, SQLAlchemy (async), PostgreSQL
- **Frontend**: React 18, TypeScript, Tailwind CSS
- **Exchange**: Binance Futures (python-binance)
- **LLM**: Groq/OpenAI/Local adapters
- **Monitoring**: Structured logging, WebSocket live updates
- **Auth**: JWT + HTTPBearer

For complete architecture details, **[see ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## Project Structure

```
BotTradingBinance/
├── apps/
│   ├── api/                    # FastAPI REST API server
│   │   ├── main.py            # Entry point (lifespan, routers)
│   │   ├── phase4_routes.py   # Auth, config, dashboard
│   │   ├── phase6_routes.py   # Trading endpoints
│   │   ├── phase8_routes.py   # AI decisions, messages
│   │   ├── auth.py            # JWT handling
│   │   ├── health_check.py    # System status
│   │   └── websocket.py       # Live updates
│   │
│   ├── worker/                 # Autonomous trading loop
│   │   ├── main.py            # Entry point (trading loop)
│   │   ├── engine/
│   │   │   ├── execution.py   # Order execution
│   │   │   ├── reconciler.py  # DB ↔ Exchange sync
│   │   │   └── circuit_breaker.py  # Safe mode
│   │   └── agents/
│   │       └── trader_stub.py # Mock trading agent
│   │
│   ├── dashboard/              # React frontend
│   │   ├── src/
│   │   │   ├── components/     # React components
│   │   │   ├── pages/          # Page containers
│   │   │   ├── api/
│   │   │   │   └── client.ts   # HTTP client
│   │   │   └── styles/         # Tailwind CSS
│   │   └── package.json        # npm dependencies
│   │
│   └── telegram/               # Telegram bot
│       ├── bot.py             # 18 commands, RBAC
│       ├── rbac.py            # Role-based access control
│       └── main.py            # Entry point
│
├── packages/shared/            # Shared code
│   ├── models.py              # SQLAlchemy ORM models (Event, Position, Order, etc.)
│   ├── schemas.py             # Pydantic request/response schemas
│   ├── enums.py               # ActionType, Side, OrderStatus, etc.
│   ├── config.py              # Settings from .env
│   ├── database.py            # AsyncSessionFactory, migrations
│   ├── logger.py              # Structured logging
│   ├── risk_engine.py         # Position sizing logic
│   ├── ai_orchestrator.py     # LLM routing + decision orchestration
│   ├── ai_scout.py            # Market opportunity scanner
│   ├── llm_adapter.py         # LLM provider adapters
│   ├── prompt_pack.py         # AI instruction templates
│   ├── trade_journal.py       # P&L tracking
│   └── exchange/
│       ├── binance_futures.py # Binance API client (live)
│       └── mock.py            # Mock exchange (testing)
│
├── alembic/                    # Database migrations
├── docker/                     # Docker configuration
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Project metadata
├── ARCHITECTURE.md             # Technical architecture (this file)
├── START_HERE.md               # First-time setup guide
├── QUICKSTART.md               # Quick start steps
├── OPERATIONS_RUNBOOK.md       # Running the system
└── docs/archive/               # Archived phase documentation
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 14+ (or SQLite for dev)
- Node.js 18+ (for dashboard)
- Binance API keys (testnet or live)
- Telegram bot token (from @BotFather)

### Installation (5 minutes)

```bash
# 1. Clone and environment
git clone <repo>
cd BotTradingBinance
python -m venv .venv
.venv\Scripts\activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure .env (copy template, fill in keys)
cp .env.example .env
# Edit .env with your API keys and database URL

# 4. Initialize database
alembic upgrade head

# 5. Install & build dashboard (optional)
cd apps/dashboard
npm install
npm run build  # or 'npm start' for dev
cd ../..
```

See **[QUICKSTART.md](QUICKSTART.md)** for detailed setup.

---

## Running the System

### Development (4 terminals)

**Terminal 1 - Worker** (trading loop)
```bash
python -m apps.worker.main
# Logs: trading decisions, order execution, P&L
```

**Terminal 2 - API Server**
```bash
python -m uvicorn apps.api.main:app --reload --port 8000
# Visit: http://localhost:8000/docs (Swagger UI)
```

**Terminal 3 - Dashboard** (optional, dev mode)
```bash
cd apps/dashboard
npm start
# Opens: http://localhost:3000
```

**Terminal 4 - Telegram Bot** (optional)
```bash
python -m apps.telegram.main
# Polls for messages; no URL needed
```

### Production (Docker)
```bash
docker-compose up -d

# Services auto-start inside container
# Check logs: docker logs bot-api, docker logs bot-worker, etc.
```

See **[OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md)** for detailed operations.

---

## Key Features

### 1. Trading Loop (~1 second cycle)
```
1. Fetch market data (price, positions, orders)
2. Scan for opportunities (AIScout)
3. Make decision (LLM)
4. Validate risk (RiskEngine)
5. Execute order (ExecutionEngine)
6. Sync state (ReconcilerEngine)
7. Log everything (Events table)
```

### 2. Risk Management
- **Max position size**: Configurable per trade
- **Portfolio leverage**: Hard limit (default 5x)
- **Circuit breaker**: Auto-stop at 15% drawdown
- **Dynamic config**: Adjust risk without restart

### 3. Crash-Safe Architecture
- **Position recovery**: Auto-sync DB ↔ Binance on startup
- **Order reconciliation**: Fills tracked, gaps filled
- **Graceful shutdown**: Cleanup on interrupt (SIGTERM)
- **Auto-reconnect**: Network failures handled

### 4. Monitoring
- **Real-time dashboard**: WebSocket updates (<500ms)
- **Event logging**: Every trade, decision, error logged
- **Access telemetry**: Device, network, IP tracking
- **Telegram alerts**: Critical events sent to chat

### 5. Remote Control (Telegram)
```
/health          → System status
/positions       → Open trades
/orders          → Pending orders
/price BTCUSDT   → Current price
/pause           → Stop trading (2FA)
/resume          → Resume trading (2FA)
/close_all       → Emergency close all (2FA)
... 12 more commands
```

---

## Database

### Main Tables
| Table | Purpose |
|-------|---------|
| `bot_config` | Trading mode, AI provider, enabled state |
| `position` | Open/closed trades with P&L |
| `order` | Pending/filled orders |
| `decision` | LLM decisions + confidence |
| `event` | Complete audit trail (trades, errors, access) |
| `risk_log` | Risk metrics per check |
| `audit_log` | User actions (config changes, approvals) |
| `signal` | Market opportunities detected |

**Full schema in [ARCHITECTURE.md](ARCHITECTURE.md#database-schema)**

---

## Configuration

### Environment Variables (.env)
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/botdb

# Binance (Paper Trading - Recommended for testing)
BINANCE_API_KEY=xxx
BINANCE_SECRET_KEY=xxx
BINANCE_TESTNET=true

# Binance (Live Trading - Use vault for security)
RISK_VAULT=true
RISK_VAULT_KEY=xxx

# AI/LLM Provider
AI_PROVIDER=groq                # groq, openai, local
GROQ_API_KEY=xxx
OPENAI_API_KEY=xxx
LOCAL_LLM_URL=http://localhost:1234

# Telegram (optional)
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_OWNER_ID=123456
TELEGRAM_ADMIN_IDS=123,456,789

# System
LOG_LEVEL=INFO
TIMEZONE=UTC
MAX_POSITIONS=5
```

See `.env.example` for all options.

---

## API Endpoints

### Authentication
```
POST   /api/auth/register              # Create user
POST   /api/auth/login                 # Get JWT token
GET    /api/auth/setup-status          # First-time setup?
POST   /api/auth/setup                 # Initialize system
```

### Trading
```
GET    /api/positions                  # All open positions
GET    /api/orders                     # All pending orders
POST   /api/orders                     # Create order
DELETE /api/orders/{id}                # Cancel order
POST   /api/positions/{id}/close       # Close position
```

### Monitoring
```
GET    /api/overview                   # Trading stats, balance, P&L
GET    /api/events                     # Event log
GET    /api/decisions                  # AI decisions
GET    /api/decisions/{id}/trace       # Full decision trace
GET    /api/health                     # System status
```

### WebSocket (Live Updates)
```
WS     /ws/positions                   # Position updates
WS     /ws/prices                      # Price feed
WS     /ws/orders                      # Order fills
WS     /ws/alerts                      # System alerts
```

**Full API docs at**: `http://localhost:8000/docs` (Swagger UI)

---

## Troubleshooting

### Worker crashes on startup
**Check**: Database connection + permissions  
**Fix**: Verify `DATABASE_URL` in .env; run `alembic upgrade head`

### Dashboard won't connect
**Check**: API server running on :8000  
**Fix**: Ensure `python -m uvicorn apps.api.main:app --port 8000` is active

### Orders not executing
**Check**: Risk config + API keys  
**Fix**: Review `events` table for error codes; verify credentials in vault

### High latency (>1s per cycle)
**Check**: Database query performance + network  
**Fix**: Check DB connection pool size; verify Binance API response times

---

## Learning Resources

- **Risk Management**: See `RISK_VAULT_CONFIG_GUIDE.md` in `docs/archive/`
- **Telegram Setup**: See `TELEGRAM_SETUP_GUIDE.md` in `docs/archive/`
- **AI Decision Flow**: See [ARCHITECTURE.md](ARCHITECTURE.md#data-flow)
- **Position Sizing**: See [ARCHITECTURE.md](ARCHITECTURE.md#risk-management)

---

## Security

- ✅ API keys stored in `.env` (never in code)
- ✅ Sensitive keys in vault (encrypted)
- ✅ JWT tokens for API auth
- ✅ Role-based access (Telegram: Admin/Trader/Observer)
- ✅ 2-step confirmation for risky operations
- ✅ Complete audit trail logged
- ✅ No credentials in logs or database

---

## Production Checklist

- [ ] Database: PostgreSQL 15+ with backups
- [ ] API: Reverse proxy (nginx) + SSL/TLS
- [ ] Keys: All secrets in vault, never in .env
- [ ] Monitoring: Prometheus + alerting on errors
- [ ] Logs: Shipped to ELK/CloudWatch
- [ ] Dashboard: Behind authentication
- [ ] Telegram: Only authorized users have access
- [ ] Binance: Testnet first, then live with limits
- [ ] Risk: Max loss per day set + position limits
- [ ] Documentation: Teams know how to troubleshoot

See full checklist in `OPERATIONS_RUNBOOK.md`.

---

## Support & Issues

**Common Errors & Fixes**: See [ARCHITECTURE.md](ARCHITECTURE.md#troubleshooting)  
**All Logs Go To**: `events` table (queryable in dashboard or psql)  
**Check System Health**: `/api/health` endpoint or Telegram `/health`

---

**Last Updated**: March 2026  
**Status**: Production Ready ✅  
**Maintained By**: Trading Bot Team
