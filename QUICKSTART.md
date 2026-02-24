# 🚀 Phase 1 Quick Start Guide

Get the AI Trading Bot up and running in 5 minutes!

## Prerequisites

- Python 3.11+
- pip
- Git

## Step 1: Setup Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment

```powershell
# Copy environment template
copy .env.example .env

# The default settings work for Phase 1 testing
# No need to edit .env yet
```

## Step 3: Initialize Database

```powershell
# Run Alembic migrations to create tables
alembic upgrade head

# Seed initial configuration
python scripts/init_db.py
```

You should see:
```
✅ Database seeded successfully!
   Bot Config Version: 1
   Prompt Pack: default_trader_v1 v1.0.0
```

## Step 4: Start Services

Open **3 separate PowerShell windows**:

### Terminal 1: Worker (Trading Engine)
```powershell
.\venv\Scripts\activate
python apps/worker/main.py
```

You should see logs like:
```
worker_initializing
risk_config_loaded version=1
worker_started loop_interval_sec=10
decision_made action=hold regime=trend
```

### Terminal 2: API Server
```powershell
.\venv\Scripts\activate
python apps/api/main.py
```

You should see:
```
INFO:     Started server process
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 3: Web Dashboard (Optional)
```powershell
cd apps\web
python -m http.server 3000
```

Then open in browser: **http://localhost:3000**

Or just open `apps/web/index.html` directly in your browser.

## Step 5: Verify Everything Works

After running for 5 minutes, verify the system:

```powershell
# In a new terminal
.\venv\Scripts\activate
python scripts/verify_phase1.py
```

You should see:
```
✓ Bot Configs: 1 found
✓ Decisions: 30 logged
✓ Orders: 8 placed
✓ Positions: 2 active
✓ Events: 45 logged
✓ Idempotency: No duplicate orders

✅ Phase 1 Verification PASSED
```

## Quick Commands

### Check API Health
```powershell
curl http://localhost:8000/health
```

### View Recent Events
```powershell
curl http://localhost:8000/events?limit=5
```

### View Positions
```powershell
curl http://localhost:8000/positions
```

### View API Documentation
Open in browser: **http://localhost:8000/docs**

## Running Tests

```powershell
# Activate venv first
.\venv\Scripts\activate

# Test idempotency
pytest tests/test_idempotency.py -v

# Test risk engine
pytest tests/test_risk_engine.py -v

# All tests
pytest -v
```

## Troubleshooting

### Error: "No module named 'packages'"

Make sure you're in the project root directory and virtual environment is activated.

### Error: "sqlalchemy.exc.OperationalError"

Run database migrations:
```powershell
alembic upgrade head
python scripts/init_db.py
```

### Worker not generating decisions

Check that `WORKER_LOOP_INTERVAL_SEC=10` in `.env` (default is 10 seconds between decisions).

### API returns 404 for /events

Make sure worker ran for a few minutes to generate data.

## What's Happening?

1. **Worker** generates mock market snapshots every 10 seconds
2. **TraderStub** makes random AI decisions (60% HOLD, 30% OPEN, 10% CLOSE)
3. **RiskEngine** validates decisions against hard limits
4. **ExecutionEngine** places orders on MockExchange (simulated fills)
5. **Database** logs everything with trace_id for auditability
6. **API** serves data via REST endpoints and WebSocket
7. **Dashboard** shows real-time status

## Next Steps

Once Phase 1 is verified:

- **Phase 2**: Integrate Binance Demo API
- **Phase 3**: Add Telegram bot commands
- **Phase 4**: Build React dashboard with charts
- **Phase 5**: Implement real AI Trader Agent (LLM-based)
- **Phase 6**: Add Learning Agent
- **Phase 7**: Deploy to production

## Stop Services

Press `Ctrl+C` in each terminal window. Worker will gracefully shutdown.

---

**Need help?** Check the main [README.md](README.md) for architecture details.
