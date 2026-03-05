# Phase 2 Implementation - Binance DEMO Integration

## Overview

Phase 2 adds **real Binance Futures integration** with reconciliation and safe mode. The system now:
- Connects to Binance Futures API (testnet by default)
- Reconciles DB ↔ Exchange state every 10s
- Monitors circuit breaker for safe mode
- Respects pause/resume commands
- Maintains crash safety with idempotent execution

## Architecture Changes

### Exchange Layer (Phase 2+)

#### 1. BinanceFuturesClient (`packages/shared/exchange/binance_futures.py`)
Production-grade REST API client with:
- **Signed requests**: HMAC SHA256 with server time sync
- **Endpoints**: balance, positions, orders, place/cancel, leverage, margin type
- **Error handling**: Retries and logging
- **Type safety**: Full async/await with proper error handling

```python
# Usage
async with BinanceFuturesClient() as client:
    # Get account balance
    balance = await client.get_account_balance()
    
    # Place market order
    order = await client.place_order(
        symbol="BTCUSDT",
        side=Side.LONG,
        order_type=OrderType.MARKET,
        quantity=1.0,
        client_order_id="unique_id",
    )
    
    # Get position risk
    positions = await client.get_position_risk("BTCUSDT")
```

#### 2. BinanceFuturesWebSocket (`packages/shared/exchange/binance_ws.py`)
Real-time market data streams:
- **Streams**: Klines, mark price, ticker
- **Auto-reconnect**: Handles disconnections
- **Callbacks**: Custom event handlers

```python
async def on_kline(msg):
    print(f"Kline: {msg['k']['c']}")

# Subscribe to kline stream
ws = await get_binance_ws()
await subscribe_kline("BTCUSDT", "1m", on_kline)
```

### Execution Engine (Enhanced)

#### ExecutionEngine v2 (`apps/worker/engine/execution.py`)
Now supports both Mock and Binance:

```python
engine = ExecutionEngine(binance_client)  # Or mock_exchange

# Executes with idempotency (same trace_id = same order)
result = await engine.execute_decision(decision, trace_id, session)
```

Key Features:
- ✅ **Idempotent**: trace_id prevents duplicate orders
- ✅ **Server-side SL/TP**: Places STOP_MARKET/TAKE_PROFIT_MARKET orders
- ✅ **Leverage**: Sets leverage before opening position
- ✅ **Reduce-only**: Close with reduce_only=true
- ✅ **Crash Recovery**: Can resume from DB state

### Reconciliation Engine (`apps/worker/engine/reconciler.py`)

Syncs Database ↔ Binance every 10 seconds:

```python
reconciler = ReconcilerEngine(binance_client)

# Full reconciliation
summary = await reconciler.reconcile(session)
# Returns: {
#   "position_mismatches": [...],
#   "order_mismatches": [...],
#   "total_mismatches": 0 (ok) or > 0 (alert)
# }

# Auto-heal mismatches
await reconciler.sync_positions(session)
```

Detects:
- Positions in DB but not on exchange
- Positions on exchange but not in DB
- Quantity mismatches
- Order status mismatches

### Circuit Breaker (`apps/worker/engine/circuit_breaker.py`)

Safe mode when system health degrades:

```python
cb = CircuitBreaker()

# Record WS messages
cb.record_ws_message()

# Record REST API health
cb.record_rest_request(success=True)

# Check if safe for trading
if cb.is_safe_for_trading():
    # Execute new orders
    pass
else:
    # Alert! No new orders
    logger.warning("SAFE MODE: Not starting new trades")

# Get status
status = cb.get_status()
# {
#   "state": "closed|open|half_open",
#   "is_safe_for_trading": true/false,
#   "error_rate": 0.05,
#   ...
# }
```

Triggers OPEN state when:
- **WS down > 10s**: No market data for 10 seconds
- **REST errors > 10%**: More than 10% of requests fail in last 100 requests

Auto-recovers after 60s cooldown.

### Database Updates

#### Position Model
New Binance-specific fields:
```python
position.leverage: int = 1
position.margin_type: str = "CROSSED"  # or "ISOLATED"
position.liquidation_price: float | None
```

Migration: [alembic/versions/002_add_binance_fields.py](alembic/versions/002_add_binance_fields.py)

### API Endpoints (Phase 2+)

#### Worker Control
- `POST /actions/pause` - Pause trading (keep existing positions)
- `POST /actions/resume` - Resume trading
- `GET /actions/status` - Get pause/resume status

#### Reconciliation
- `POST /actions/sync_now` - Trigger reconciliation immediately
- `GET /recon/summary` - Get last reconciliation result (0 mismatches = ok)

#### Circuit Breaker
- `GET /circuit-breaker/status` - Get safe/unsafe status

## Phase 2 Worker (`apps/worker/main_phase2.py`)

Orchestrates all components:

```python
# Automatically:
# 1. Main trading loop (10s interval)
# 2. Reconciliation loop (10s interval, separate task)
# 3. Circuit breaker monitoring
# 4. Pause/resume checks

worker = Phase2TradingWorker()
await worker.initialize()
await worker.run()
```

### Startup

```bash
# Set environment variables
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"
export BINANCE_TESTNET=true

# Run Phase 2 worker
python -m apps.worker.main_phase2
```

### Lifecycle

1. **Initialize**: Load config, connect to Binance
2. **Main loop**: 
   - Generate market snapshot
   - Get AI decision
   - Validate with risk engine
   - Execute if safe (CB closed)
3. **Reconciliation**: Every 10s, sync DB ↔ Binance
4. **Graceful shutdown**: SIGTERM/SIGINT

## Usage Examples

### Start trading with Binance Testnet

```bash
# 1. Update .env
BINANCE_API_KEY=<testnet_key>
BINANCE_API_SECRET=<testnet_secret>
BINANCE_TESTNET=true

# 2. Run worker
python -m apps.worker.main_phase2

# 3. Monitor in another terminal
curl http://localhost:8000/bot/status
curl http://localhost:8000/positions
curl http://localhost:8000/recon/summary
curl http://localhost:8000/circuit-breaker/status
```

### Pause/Resume Trading

```bash
# Pause (stop new orders)
curl -X POST http://localhost:8000/actions/pause \
  -H "Content-Type: application/json" \
  -d '{"reason": "Testing"}'

# Check status
curl http://localhost:8000/actions/status

# Resume
curl -X POST http://localhost:8000/actions/resume
```

### Check Safe Mode

```bash
# If circuit breaker is OPEN, DB still reconciles but no new trades
curl http://localhost:8000/circuit-breaker/status

# Expected when healthy:
# {
#   "state": "closed",
#   "is_safe_for_trading": true,
#   "error_rate": 0.02
# }
```

## Error Handling

### Reconciliation Mismatches

If reconciliation finds mismatches:
1. **Alert**: Event logged with details
2. **Auto-heal**: Position sync fixes most issues
3. **Manual**: API `/actions/sync_now` forces immediate reconciliation

### Circuit Breaker Triggered

If CB goes OPEN (safe mode):
1. **No new orders**: Execution engine skips trades
2. **Existing positions**: Held until health recovers
3. **Recovery**: Auto-heal after 60s cooldown

### Crash During Execution

If bot crashes mid-trade:
1. **Restart**: `python -m apps.worker.main_phase2`
2. **Idempotency**: Same trace_id won't duplicate orders
3. **Reconciliation**: Syncs state with Binance
4. **Continue**: Resumes normal operation

## Testing

### Run tests
```bash
pytest tests/test_phase2.py -v
```

### Run verification
```bash
python scripts/verify_phase2.py
```

## Migration from Phase 1 to Phase 2

1. **Backup database**
   ```bash
   cp data/trading.db data/trading.db.backup
   ```

2. **Update code**
   ```bash
   git pull origin phase2
   ```

3. **Run migration**
   ```bash
   alembic upgrade head
   ```

4. **Configure Binance**
   ```bash
   # .env
   BINANCE_API_KEY=<your_testnet_key>
   BINANCE_API_SECRET=<your_testnet_secret>
   BINANCE_TESTNET=true
   ```

5. **Start Phase 2 worker**
   ```bash
   python -m apps.worker.main_phase2
   ```

## Key Differences from Phase 1

| Feature | Phase 1 | Phase 2 |
|---------|---------|---------|
| Exchange | MockExchange | Binance Futures |
| Market Data | Generated | Real-time WS/REST |
| Reconciliation | None | Every 10s |
| Circuit Breaker | None | Health monitoring |
| Pause/Resume | None | Full API control |
| Safe Mode | None | Auto-trigger |
| Server SL/TP | Mock | Real STOP_MARKET/TP orders |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                  Phase 2 Worker                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐    ┌──────────────────┐         │
│  │  Trading Loop    │    │ Recon Loop (bg)  │         │
│  │  (10s interval)  │    │ (10s interval)   │         │
│  └────────┬─────────┘    └────────┬─────────┘         │
│           │                       │                    │
│  ┌────────▼────────┐    ┌────────▼─────────┐         │
│  │ Decision Making │    │  Reconciliation  │         │
│  │ + Risk Engine   │    │  + DB ↔ Exchange │         │
│  └────────┬────────┘    └────────┬─────────┘         │
│           │                       │                    │
│  ┌────────▼────────┐    ┌────────▼─────────┐         │
│  │ Circuit Breaker │    │   Event Logging  │         │
│  │ (Safe Mode)     │    │                  │         │
│  └────────┬────────┘    └──────────────────┘         │
│           │                                           │
│  ┌────────▼────────┐                                 │
│  │  Execution      │                                 │
│  │  (if safe)      │                                 │
│  └────────┬────────┘                                 │
│           │                                           │
│  ┌────────▼───────────────────────┐                 │
│  │  BinanceFuturesClient (REST)    │                 │
│  │  + BinanceFuturesWebSocket (WS) │                 │
│  └────────┬───────────────────────┘                 │
│           │                                           │
│           ▼                                           │
│    BINANCE FUTURES API (TESTNET)                    │
│                                                     │
└─────────────────────────────────────────────────────────┘
        │                  │                   │
        ▼                  ▼                   ▼
     SQLite           Positions          Orders
     (Local DB)       (Exchange)        (Exchange)
```

## Next Steps (Phase 3+)

- [ ] Live trading mode (production API keys)
- [ ] PostgreSQL migration
- [ ] Multiple symbol trading
- [ ] Portfolio rebalancing
- [ ] Performance metrics tracking
- [ ] Learning system integration
- [ ] Email/Slack alerts
- [ ] Web dashboard UI

## Support

For issues or questions:
1. Check logs: `tail -f logs/bot.log`
2. Run verification: `python scripts/verify_phase2.py`
3. Check circuit breaker: `curl http://localhost:8000/circuit-breaker/status`
4. Review reconciliation: `curl http://localhost:8000/recon/summary`
