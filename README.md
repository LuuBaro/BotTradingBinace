# AI Trading Bot - Binance USDⓈ-M Futures

Production-grade AI Trading Agent for Binance USDⓈ-M Futures with crash-safe architecture, risk management, and learning capabilities.

## 🚀 Current Status: Phase 3 - Telegram Remote Operations

**Phase 1 ✅ COMPLETE**: Production skeleton with MockExchange  
**Phase 2 ✅ COMPLETE**: Binance Futures integration + reconciliation  
**Phase 3 ✅ COMPLETE**: Telegram bot with RBAC + 2-step confirmation

### Phase 3 Complete Features
- ✅ Telegram bot with 18 commands (5 categories)
- ✅ Role-based access control (3 roles, 13 permissions)
- ✅ 2-step confirmation for risky operations
- ✅ Automatic audit logging
- ✅ Market data monitoring (/price, /spread, /kline)
- ✅ System health monitoring (/health, /latency, /time)
- ✅ Trading state visibility (/positions, /orders, /recon)
- ✅ Remote control operations (/pause, /resume)
- ✅ Position management (/close_position, /close_all)
- ✅ Decision tracing (/decision, /trace)
- ✅ Comprehensive test suite (27 tests)
- ✅ Verification script
- ✅ Complete documentation

## Architecture (Phase 1-3)

```
apps/
├── worker/
│   ├── main.py              # Phase 1 worker (MockExchange)
│   ├── main_phase2.py       # Phase 2 worker (Binance + Recon)
│   ├── engine/
│   │   ├── execution.py     # Unified: Binance + Mock
│   │   ├── reconciler.py    # DB ↔ Exchange sync
│   │   └── circuit_breaker.py  # Safe mode monitoring
│   └── agents/
│       └── trader_stub.py   # Mock AI
├── api/
│   └── main.py              # FastAPI + Phase 2 endpoints
├── telegram/                # Phase 3 Telegram Bot
│   ├── __init__.py
│   ├── bot.py              # 18 commands, RBAC checks, 2FA
│   ├── rbac.py             # 3 roles, 13 permissions
│   └── main.py             # Worker entry point
└── web/
    └── dashboard.html       # Monitoring

packages/
├── shared/
│   ├── exchange/
│   │   ├── mock.py          # Phase 1 exchange
│   │   ├── binance_futures.py   # Phase 2 REST client
│   │   └── binance_ws.py    # Phase 2 WebSocket
│   ├── models.py            # With AuditLog table
│   ├── schemas.py
│   ├── enums.py
│   ├── database.py          # AsyncSessionFactory
│   ├── risk_engine.py
│   ├── config.py            # With Telegram config
│   └── logger.py
```

## Quick Start - Phase 3 (Full Stack with Telegram)

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Everything

```bash
# Get Telegram bot token from @BotFather
# Get Binance testnet credentials from https://testnet.binancefuture.com/
# Create .env file
cp .env.example .env

# Edit .env with:
# - Binance testnet API key/secret
# - Telegram bot token
# - Telegram admin/trader chat IDs
```

### 3. Initialize Database

```bash
# Run migrations
python -m alembic upgrade head

# Seed default config
python scripts/init_db.py
```

### 4. Start Phase 2 Worker (Terminal 1)

```bash
# Run Phase 2 worker with Binance integration
python -m apps.worker.main_phase2
```

### 5. Start Phase 3 Telegram Bot (Terminal 2)

```bash
# Run Telegram bot for remote operations
python -m apps.telegram.main
# Opens polling, ready for Telegram messages
```

### 6. Start API Server (Terminal 3)

```bash
# Run FastAPI for monitoring/control
python -m apps.api.main
# Open http://localhost:8000/docs
```

### 7. Monitor via Telegram

Send `/help` to your Telegram bot to see all available commands!

```
/health           → Check system health
/positions        → View open trades
/pause            → Stop trading
/close_position   → Close specific position (2-step confirm)
/close_all        → Emergency close all (2-step confirm)
... and 13 more commands
```

## Phase 3 - Telegram Bot Commands

### Categories

**🔍 Health & Time** (all roles)
- `/time` - System time, uptime, last tick
- `/latency` - WS/REST latency, clock skew
- `/health` - Component status

**📊 Market** (all roles)
- `/price BTCUSDT` - Current price
- `/spread BTCUSDT` - Bid-ask spread  
- `/kline BTCUSDT 1m 60` - Candlesticks

**📈 State** (all roles)
- `/status` - Bot status
- `/positions` - Open positions
- `/orders` - Open orders
- `/recon` - Reconciliation status
- `/decision` - Latest AI decision
- `/trace <id>` - Decision trace

**⚙️ Control** (traders+admins)
- `/pause` - Stop trading
- `/resume` - Resume trading
- `/close_position BTCUSDT` - Close position (2-step ✓)
- `/close_all` - Close all (2-step ✓)

**🔐 Admin**
- `/sync_now` - Force reconciliation

### RBAC Roles

| Feature | Admin | Trader | Viewer |
|---------|-------|--------|--------|
| View commands | ✅ | ✅ | ✅ |
| Control (pause/resume) | ✅ | ✅ | ❌ |
| Close positions | ✅ | ✅ | ❌ |
| Force sync | ✅ | ❌ | ❌ |

Full details: [PHASE3_COMPLETE.md](PHASE3_COMPLETE.md)

## Documentation

- **Phase 1**: [PHASE1_COMPLETE.md](PHASE1_COMPLETE.md) - Production skeleton
- **Phase 2**: [PHASE2_COMPLETE.md](PHASE2_COMPLETE.md) - Binance integration
- **Phase 3**: [PHASE3_COMPLETE.md](PHASE3_COMPLETE.md) - Telegram remote ops
- **Quick Setup**: [QUICKSTART.md](QUICKSTART.md) - Step-by-step setup

## Architecture Comparison

| Feature | Phase 1 | Phase 2 | Phase 3 |
|---------|---------|---------|---------|
| Exchange | MockExchange | Binance Futures | - |
| Market Data | Generated | Real-time WS | Via API |
| Reconciliation | None | Every 10s ✓ | - |
| Safe Mode | None | Circuit Breaker ✓ | - |
| Crash Safety | Idempotency | + Reconcile ✓ | - |
| SL/TP Orders | Mock market | Real server-side ✓ | - |
| REST API | ✅ | ✅ | ✅ |
| **Remote Ops** | ❌ | ❌ | **Telegram** ✓ |
| **RBAC** | ❌ | ❌ | **3 roles** ✓ |
| **2-Step Confirm** | ❌ | ❌ | **Risky ops** ✓ |
| **Audit Trail** | ✅ | ✅ | **+Telegram** ✓ |

## Testing All Phases

```bash
# Run all tests
pytest -v

# Test specific phases
pytest tests/test_phase1.py -v      # Crash-safe skeleton
pytest tests/test_phase2.py -v      # Binance integration
pytest tests/test_telegram.py -v    # Telegram bot (Phase 3)

# Test specific components
pytest tests/test_idempotency.py -v
pytest tests/test_risk_engine.py -v
pytest tests/test_rbac.py -v        # Phase 3 RBAC
```

## Verification Scripts

```bash
# Verify Phase 1 implementation
python scripts/verify_phase1.py

# Verify Phase 2 implementation
python scripts/verify_phase2.py

# Verify Phase 3 implementation
python scripts/verify_phase3.py
```

## System Requirements

- Python 3.11+
- PostgreSQL (Phase 3+, currently SQLite)

```bash
# Run Alembic migrations
alembic upgrade head

# Seed initial config
python scripts/init_db.py
```

### 4. Run Services

```bash
# Terminal 1: Start Worker
python apps/worker/main.py

# Terminal 2: Start API Server
python apps/api/main.py

# Terminal 3: Start Web (Phase 1 - basic)
cd apps/web
npm install
npm run dev
```

## Testing

```bash
# Run all tests
pytest -v

# Test specific components
pytest tests/test_idempotency.py -v
pytest tests/test_risk_engine.py -v

# Run crash recovery test
bash tests/test_crash_recovery.sh
```

## Project Roadmap

- [x] **Phase 1**: Production skeleton + crash-safe foundation
- [x] **Phase 2**: Binance Futures integration + reconciliation
- [x] **Phase 3**: Telegram bot + RBAC + remote operations
- [ ] **Phase 4**: React dashboard with real-time updates
- [ ] **Phase 5**: AI Trader Agent (LLM-based)
- [ ] **Phase 6**: Learning Agent
- [ ] **Phase 7**: Production deployment

## Key Features

### Risk Management
- Max leverage control
- Position size limits
- Risk per trade limits
- Mandatory stop-loss/take-profit
- Concurrent position limits

### Crash Safety
- Idempotent order execution (client_order_id)
- State reconciliation on restart
- Graceful shutdown handling
- Full audit trail (trace_id)

### AI Integration (Phase 5+)
- Multi-provider LLM support (OpenAI, Anthropic, Local)
- Structured decision output validation
- Market regime detection
- Learning from trade history

## License

Private project - All rights reserved
