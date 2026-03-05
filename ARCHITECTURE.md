# AI Trading Bot - Complete Technical Architecture

**Version**: Production v1.0 | **Status**: Fully Operational  
**Last Updated**: March 2026 | **Framework**: FastAPI + React + SQLAlchemy + Telegram

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture Layers](#architecture-layers)
4. [Core Components](#core-components)
5. [Data Flow](#data-flow)
6. [API Endpoints](#api-endpoints)
7. [Database Schema](#database-schema)
8. [Deployment Model](#deployment-model)

---

## System Overview

The AI Trading Bot is a **production-grade autonomous trading system** for **Binance USDⓈ-M Futures** with crash-safe architecture, risk management, and comprehensive monitoring.

### Key Capabilities
- ✅ **AI-Powered Trading**: LLM-based decision engine (Groq, OpenAI, local LLMs)
- ✅ **Crash-Safe**: Automatic reconciliation & position recovery on restart
- ✅ **Risk Management**: 3-tier position sizing, dynamic risk config, circuit breaker
- ✅ **Real-Time Monitoring**: WebSocket dashboard with live price/position tracking
- ✅ **Remote Operations**: Telegram bot with 18 commands + 2-step confirmation
- ✅ **Multi-Mode**: Support for both Mock (testing) and Live (Binance) trading
- ✅ **Audit Trail**: Complete event logging with access telemetry

---

## Technology Stack

### Backend
| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API Server** | FastAPI 0.109+ | REST + WebSocket server |
| **Database** | PostgreSQL 14+ | State persistence with async ORM |
| **ORM** | SQLAlchemy 2.0+ | Async ORM with migrations (Alembic) |
| **Auth** | JWT + HTTPBearer | Token-based API security |
| **Logging** | Structlog 24.1+ | Structured logging to events table |
| **LLM** | Groq/OpenAI/Local | Decision engine adapters |
| **Exchange** | python-binance 1.0+ | Binance Futures integration |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | React 18 | UI library |
| **Language** | TypeScript | Type-safe development |
| **Styling** | Tailwind CSS 3+ | Responsive design |
| **HTTP Client** | Axios | API communication |
| **Icons** | lucide-react | UI icons |

### Telegram Bot
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Library** | python-telegram-bot | Telegram integration |
| **Auth** | JWT (via API) | Secure command execution |
| **RBAC** | Custom roles/permissions | Access control (Admin/Trader/Observer) |

### Infrastructure
| Component | Purpose |
|-----------|---------|
| **Docker** | Containerization |
| **Docker Compose** | Multi-container orchestration |
| **Alembic** | Database schema migrations |

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  React Dashboard        │  Telegram Bot      │ REST API Docs  │
│  (Port 3000)           │ (Telegram Server)   │  (Swagger UI)  │
└────────────────┬────────────────┬────────────────┬───────────┘
                 │                │                │
┌────────────────▼────────────────▼────────────────▼───────────┐
│                   FASTAPI REST/WEBSOCKET LAYER                │
│        (Port 8000 - main.py + routers)                       │
│  ├─ phase4_routes.py  (Auth, config, dashboard)             │
│  ├─ phase6_routes.py  (Position, order, trading)            │
│  ├─ phase8_routes.py  (Messages, AI decisions, analytics)   │
│  ├─ health_check.py   (System status)                       │
│  └─ websocket.py      (Live data streaming)                 │
└────────────────┬─────────────────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────────────────┐
│                  BUSINESS LOGIC LAYER                         │
│  Worker (apps/worker/)                                       │
│  ├─ main.py              ┬─ AI execution loop               │
│  ├─ engine/execution.py  ├─ Order execution + validation    │
│  ├─ engine/reconciler.py ├─ DB ↔ Binance sync              │
│  ├─ engine/circuit_breaker.py ├─ Safe mode monitoring      │
│  ├─ agents/trader_stub.py ├─ Mock trading agent             │
│  └─ ai_orchestrator      └─ LLM decision orchestration      │
│                                                               │
│  Risk Management (packages/shared/)                          │
│  ├─ risk_engine.py       ┬─ Position sizing logic           │
│  ├─ ai_scout.py          ├─ Market opportunity scanner      │
│  └─ ai_orchestrator.py   └─ AI decision routing             │
└────────────────┬─────────────────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────────────────┐
│              EXCHANGE & DATA LAYER                            │
│  ├─ exchange/binance_futures.py ─ Live Binance API         │
│  ├─ exchange/mock.py ──────────── Test/paper trading       │
│  ├─ llm_adapter.py ─────────────── LLM provider adapters   │
│  └─ prompt_pack.py ─────────────── AI instruction templates │
└────────────────┬─────────────────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────────────────┐
│               DATA PERSISTENCE LAYER                          │
│  PostgreSQL Database (via AsyncSessionFactory)              │
│  ├─ BotConfig          ├─ Position        ├─ Event         │
│  ├─ Decision           ├─ Order           ├─ AuditLog      │
│  ├─ RiskLog            ├─ Signal          └─ TraderContext │
│  └─ (See schema below for full list)                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. **FastAPI Server** (`apps/api/main.py`)
**Responsibility**: REST API + WebSocket gateway

```python
# Key Routers (loaded from apps/api/)
- phase4_routes     # Auth, user management, config, dashboard overview
- phase6_routes     # Live trading: positions, orders, execution
- phase8_routes     # AI decisions, messages, analytics
- health_check      # System status, readiness probes

# WebSocket Manager (ws_manager)
- Live price updates
- Position changes
- Order fills
- System alerts
```

**Port**: 8000  
**CORS**: Enabled for dashboard (localhost:3000)  
**Lifespan**: Async init/cleanup with DB pool management

---

### 2. **Worker Process** (`apps/worker/main.py`)
**Responsibility**: Autonomous trading loop + market monitoring

```python
# Core Loop (async, ~1 second cycle)
1. Fetch current market state (price, positions, orders)
2. Scan for opportunities (AIScout)
3. AI decision making (LLM call)
4. Risk validation (RiskEngine)
5. Order execution (ExecutionEngine)
6. Reconciliation (ReconcilerEngine)
7. Logging + state updates (Events table)
```

**Key Features**:
- **Execution Engine**: Unified order handling (Binance or Mock)
- **Reconciler**: Keeps DB ↔ Exchange in sync
- **Circuit Breaker**: Automatic safe mode on errors
- **Trader Stub** (Mock): Simulates market fills

**Failure Recovery**:
- Auto-reconnect on network failure
- Position recovery on startup (reads DB, syncs with exchange)
- Graceful shutdown with cleanup

---

### 3. **React Dashboard** (`apps/dashboard/`)
**Responsibility**: Real-time UI for trading system monitoring

```
src/
├── components/
│   ├── Layout.tsx          # Main shell + sidebar + telemetry
│   ├── OverviewPage.tsx    # Trading stats, balance, P&L
│   ├── PositionsPage.tsx   # Active positions detail
│   ├── MessageCenterPage.tsx # Message inbox
│   ├── SettingsPage.tsx    # Configuration management
│   ├── WalletIndicator.tsx # Balance display with popup
│   └── ...
├── api/
│   └── client.ts           # Axios HTTP client
├── pages/
│   ├── DashboardPage.tsx   # Main layout
│   ├── LoginPage.tsx       # Authentication
│   └── ...
└── styles/
    └── tailwind CSS        # Responsive theming

Key Features:
- ✅ Mobile responsive (sm: 640px, md: 768px, lg: 1024px)
- ✅ WebSocket for live updates
- ✅ JWT authentication (localStorage token)
- ✅ Access telemetry logging (device, network, IP)
```

**Telemetry Collected**:
- Network status (online/offline, effective type, RTT)
- Device spec (screen size, memory, CPU cores)
- User agent, timezone, language
- IP address (server-side extraction with proxy support)

---

### 4. **Telegram Bot** (`apps/telegram/`)
**Responsibility**: Remote control + status monitoring

```python
# Commands (18 total, organized in categories)

Market Data:
├─ /price BTCUSDT       # Current spot price
├─ /spread BTCUSDT      # Bid-ask spread
└─ /kline BTCUSDT       # OHLCV candle stats

Trading State:
├─ /positions           # Active positions
├─ /orders              # Pending orders
└─ /recon               # DB vs Exchange status

Decision Tracing:
├─ /decision            # Latest AI decision
└─ /trace               # Full decision trace

System Control:
├─ /pause               # Halt trading (2FA)
├─ /resume              # Resume trading (2FA)
└─ /close_all           # Close all positions (2FA)

System Health:
├─ /health              # Worker + API status
├─ /latency             # Response time metrics
└─ /time                # Server time offset

3 Roles with 13 Permissions:
├─ Admin        (all commands)
├─ Trader       (trading + read-only)
└─ Observer     (read-only)
```

**Security**: 2-step confirmation for risky operations (pause, resume, close_all)

---

## Data Flow

### Trading Loop (Worker)
```
┌─────────────────────────────────────────────────┐
│ 1. MARKET SCAN (every ~1 second)                │
│    - Fetch KLINE candles (15m, 1h, 4h)          │
│    - Get current positions                       │
│    - Retrieve pending orders                     │
│    - Calculate spreads                           │
├─────────────────────────────────────────────────┤
│ 2. AI SCOUT (opportunity detection)             │
│    - AIScout analyzes market regime (trend/mean) │
│    - Identifies entry/exit candidates            │
│    - Generates signals                           │
├─────────────────────────────────────────────────┤
│ 3. AI DECISION (LLM call)                       │
│    - Groq/OpenAI/Local LLM                      │
│    - Decision schema (buy/sell/hold)             │
│    - Confidence + reasoning                      │
├─────────────────────────────────────────────────┤
│ 4. RISK VALIDATION                              │
│    - Max position size check                     │
│    - Portfolio leverage check                    │
│    - Risk/reward ratio validation                │
├─────────────────────────────────────────────────┤
│ 5. ORDER EXECUTION (Binance or Mock)            │
│    - Place limit/market orders                   │
│    - Update position in DB                       │
│    - Track pending fills                         │
├─────────────────────────────────────────────────┤
│ 6. RECONCILIATION (on any order)                │
│    - Compare DB ↔ Exchange state                 │
│    - Fill missing positions/orders               │
├─────────────────────────────────────────────────┤
│ 7. LOGGING (all decisions)                      │
│    - Insert Decision record                      │
│    - Update Event log                            │
│    - Record risk metrics                         │
└─────────────────────────────────────────────────┘
```

### API Request Flow (Dashboard)
```
Browser (React)
    ↓
[Axios HTTP Client] POST /api/positions
    ↓
[FastAPI] phase6_routes.py:get_positions()
    ├─ Verify JWT token
    ├─ Query DB (SQLAlchemy async)
    ├─ Serialize to JSON
    │
    └─→ Response 200 {positions: [...]}
        ↓
     [React Component] Update state
        ↓
     [UI Render] Display on screen
```

### Telemetry Flow (Access Logging)
```
1. Dashboard/Layout mounts
   └─ logAccessTelemetry('session_start') → API

2. Navigator collects device data:
   ├─ network.effectiveType
   ├─ navigator.deviceMemory
   ├─ screen size
   ├─ user agent
   └─ timezone

3. POST /api/access/telemetry {payload}
        ↓
   [phase4_routes.py]
        ├─ Verify JWT
        ├─ Extract real IP (x-forwarded-for fallback)
        └─ Create Event {code:'ACCESS_TELEMETRY', data_json:{...}}
        ↓
   PostgreSQL events table INSERT
        ↓
   Queryable audit trail
```

---

## API Endpoints

### **Authentication (phase4_routes.py)**
```
POST   /api/auth/register          # Create user
POST   /api/auth/login             # JWT token
GET    /api/auth/setup-status      # First-time setup check
POST   /api/auth/setup             # Initialize system
```

### **Dashboard (phase4_routes.py)**
```
GET    /api/overview               # Trading stats, balance, P&L
GET    /api/events                 # Event log (filtered)
POST   /api/access/telemetry       # Log device/network access
```

### **Trading (phase6_routes.py)**
```
GET    /api/positions              # All open positions
GET    /api/orders                 # All pending orders
POST   /api/orders                 # Create new order
DELETE /api/orders/{order_id}      # Cancel order
POST   /api/positions/{position_id}/close  # Close position
```

### **AI Decisions (phase8_routes.py)**
```
GET    /api/decisions              # Latest N decisions
GET    /api/decisions/{id}/trace   # Full decision trace
POST   /api/messages               # Send AI instruction
GET    /api/messages              # Retrieve AI responses
```

### **Health (health_check.py)**
```
GET    /api/health                 # System status
GET    /api/health/ready           # Readiness probe
GET    /api/health/live            # Liveness probe
```

### **WebSocket (ws_manager)**
```
WS     /ws/positions               # Live position updates
WS     /ws/prices                  # Live price feed
WS     /ws/orders                  # Order fill notifications
WS     /ws/alerts                  # System alerts
```

---

## Database Schema

### Core Tables

**bot_config**
- `id`: Primary key
- `mode`: 'MOCK' | 'LIVE' (trading mode)
- `enabled`: Boolean (trading on/off)
- `trading_pair`: e.g. 'BTCUSDT'
- `timeframe`: '15m' | '1h' | '4h'
- `ai_provider`: 'groq' | 'openai' | 'local'
- Updated by: admin via settings API

**position**
- `id`: UUID
- `symbol`: 'BTCUSDT', etc.
- `side`: 'LONG' | 'SHORT'
- `quantity`: Open amount
- `entry_price`: Average entry
- `current_price`: Latest market price
- `unrealized_pnl`: Calculated P&L
- `status`: 'OPEN' | 'CLOSING' | 'CLOSED'
- `created_at`, `updated_at`: Timestamps

**order**
- `id`: UUID
- `symbol`, `type`, `side`: Order params
- `quantity`, `price`: Order details
- `status`: 'PENDING' | 'FILLED' | 'CANCELLED'
- `fill_price`, `filled_qty`: Execution data
- `created_at`, `filled_at`: Timestamps

**decision**
- `id`: UUID
- `symbol`: Trading pair
- `decision_type`: 'BUY' | 'SELL' | 'HOLD'
- `confidence`: 0-100 score
- `reasoning`: Text explanation from LLM
- `market_context`: JSON (price, trend, regime)
- `executed`: Boolean (did order execute)
- `outcome`: 'WIN' | 'LOSS' | 'PENDING'
- `created_at`: Timestamp

**event**
- `id`: UUID
- `timestamp`: When occurred
- `level`: 'INFO' | 'WARN' | 'ERROR'
- `code`: Event type ('POSITION_OPENED', 'ORDER_FILLED', 'ACCESS_TELEMETRY', etc.)
- `message`: Human-readable summary
- `data_json`: Full context as JSON (position details, error trace, telemetry fields, etc.)
- `created_at`: Insertion timestamp

**risk_log**
- `id`: UUID
- `timestamp`: When checked
- `total_risk`: Percentage of account at risk
- `position_count`: Number of open positions
- `max_position_size`: Largest position %
- `portfolio_leverage`: Current leverage
- `status`: 'GREEN' | 'YELLOW' | 'RED'
- `details`: JSON (per-position breakdown)

**audit_log**
- `id`: UUID
- `timestamp`: Action time
- `user`: Username who performed action
- `action`: 'LOGIN', 'SETTINGS_CHANGE', 'POSITION_CLOSE', etc.
- `target`: What was affected
- `old_value`, `new_value`: Before/after state
- `ip_address`: 2FA verification

**signal**
- `id`: UUID
- `timestamp`: Generated time
- `symbol`: Trading pair
- `type`: 'ENTRY' | 'EXIT' | 'ALERT'
- `confidence`: Score
- `market_regime`: 'TRENDING' | 'MEAN_REVERTING'
- `technical_score`: Combined indicator value
- `activated`: Boolean (if used by trader)

---

## Deployment Model

### Development Setup
```bash
# 1. Clone and set up venv
git clone <repo>
cd BotTradingBinance
python -m venv .venv
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment (.env)
BINANCE_API_KEY=your_key
DATABASE_URL=postgresql://user:pass@localhost/botdb
GROQ_API_KEY=your_groq_key

# 4. Run migrations
alembic upgrade head

# 5. Start services
# Terminal 1: API
python -m uvicorn apps.api.main:app --reload --port 8000

# Terminal 2: Worker
python -m apps.worker.main

# Terminal 3: Dashboard (if npm installed)
cd apps/dashboard && npm start

# Terminal 4: Telegram Bot
python -m apps.telegram.main
```

### Docker Deployment
```bash
# Single container (all services)
docker-compose up -d

# Services started:
# - FastAPI: 0.0.0.0:8000
# - PostgreSQL: 0.0.0.0:5432
# - Worker: runs inside container
# - Telegram: runs inside container
```

### Environment Variables (.env)
```
# Database
DATABASE_URL=postgresql://user:pass@host:5432/botdb

# Binance (Paper trading)
BINANCE_API_KEY=xxx
BINANCE_SECRET_KEY=xxx
BINANCE_TESTNET=true

# Binance (Live - use vault)
RISK_VAULT=true
RISK_VAULT_KEY=xxx

# AI/LLM
AI_PROVIDER=groq              # groq, openai, local
GROQ_API_KEY=xxx
OPENAI_API_KEY=xxx
LOCAL_LLM_URL=http://localhost:1234

# Telegram
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_OWNER_ID=123456
TELEGRAM_ADMIN_IDS=123,456

# Other
LOG_LEVEL=INFO
TIMEZONE=UTC
```

---

## System Requirements

### Minimal
- Python 3.11+
- PostgreSQL 14+ (or SQLite for development)
- 2GB RAM
- 500MB storage

### Recommended (Production)
- Python 3.11
- PostgreSQL 15+ (managed, with backups)
- 4GB+ RAM
- 20GB storage (for historical data)
- Stable internet (1Mbps+ uplink)

---

## Success Metrics

✅ **System Health**:
- Worker uptime: >99.5% (auto-recovery)
- API response: <200ms (p95)
- DB sync: <100ms (reconciliation)
- Order fill: <500ms (Binance latency)

✅ **Trading**:
- Win rate: >55% (target)
- Risk/Reward: >1.5:1 (minimum)
- Max drawdown: <10% (circuit breaker stops at 15%)
- PnL tracking: 100% accuracy

✅ **Monitoring**:
- Event logging: 100% coverage
- Access audit trail: All logins tracked
- Alert latency: <2 seconds
- Dashboard updates: <500ms (WebSocket)

---

## Troubleshooting

### Worker crashes after restart
**Cause**: Position recovery fails  
**Fix**: Check `reconciler.py` logs; manually sync via DB admin panel

### Dashboard WebSocket disconnects
**Cause**: API timeout or network split  
**Fix**: Browser auto-reconnects; check `ws_manager` logs

### Orders not executing
**Cause**: Risk engine rejection or Binance API error  
**Fix**: Check `events` table for error code; verify API keys in vault

### High database latency
**Cause**: Slow queries or connection pool exhaustion  
**Fix**: Check query plans; increase `SQLALCHEMY_POOL_SIZE` in .env

---

**See also**: [START_HERE.md](START_HERE.md) | [QUICKSTART.md](QUICKSTART.md) | [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md)
