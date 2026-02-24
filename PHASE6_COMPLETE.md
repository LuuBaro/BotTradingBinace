# Phase 6 Complete: Learning Agent & Autonomous Adaptation

## Phase 6 Summary

**Phase 6 implements an AI learning system that analyzes complete trade history, discovers losing patterns, and suggests safe automated configuration changes.**

This phase enables the trading bot to learn from its own performance, adapt to changing market conditions, and continuously improve without human intervention—while maintaining strict safety constraints.

---

## Architecture Overview

```
Trading Execution (Phase 4-5)
    ↓ records trade
    ↓
Trade Journal Entry (recorded after every trade close)
    ↓ accumulates 50 trades OR daily trigger
    ↓
Learning Agent (analyzes patterns)
    ├─ Calculate Win Rate / Profit Factor / Max DD
    ├─ Segment Performance by:
    │  ├─ Market Regime (trending_up, trending_down, choppy)
    │  ├─ Volatility (4 buckets: Very Low, Low, Medium, High)
    │  ├─ Spread (3 categories: Tight, Medium, Wide)
    │  ├─ Leverage (1x, 2x, 3x, 4x)
    │  └─ Time of Day (hour-by-hour UTC analysis)
    ├─ Discover Losing Patterns (5 types)
    └─ Calibrate Confidence (bucket analysis)
    ↓
Learning Report (generated)
    ├─ Statistics (win rate, profit factor, max DD, consecutive wins/losses)
    ├─ Losing Patterns (with occurrence counts & recommendations)
    ├─ Confidence Calibration (actual vs expected win rates)
    └─ Suggested Adaptations (3-variable constraint)
    ↓
Auto-Adapt Decision (human-controlled)
    ├─ Review recommendations
    ├─ Enable/disable adaptations
    └─ Apply changes (with full audit trail)
    ↓
Adapted Configuration
    ├─ size_multiplier (1.0 to 1.2x by default, ±20% constraint)
    ├─ confidence_scaling (0.8 to 1.2x by default, ±20% constraint)
    └─ cooldown_after_loss_minutes (0 to 60 minutes)

Next Trading Cycle (Phase 5)
    ↓ uses adapted config for decisions
```

---

## Core Components

### 1. Trade Journal (packages/shared/trade_journal.py)

**Stores complete trade details with 30+ fields:**

```python
TradeJournalEntry:
  # Trade identification
  - trade_id: str (unique)
  - trace_id: str (links to Phase 5 decision)
  - symbol: str (BTCUSDT, ETHUSDT, etc.)
  - side: str (LONG or SHORT)
  
  # Entry/Exit details
  - entry_time: datetime
  - exit_time: datetime
  - entry_price: float
  - exit_price: float
  - position_size: float
  - entry_reason: str
  - exit_reason: ExitReason (TAKE_PROFIT, STOP_LOSS, MANUAL, TIMEOUT, LIQUIDATION)
  
  # Financial metrics
  - pnl: float (profit/loss in USDT)
  - pnl_pct: float (profit/loss %)
  - max_profit: float (peak unrealized profit)
  - max_loss: float (peak unrealized loss)
  
  # Market conditions at entry
  - market_regime: str (trending_up, trending_down, choppy)
  - volatility_percentile: int (0-100, ATR percentile)
  - spread_avg: float (average bid-ask spread in pips)
  - funding_rate: float (perpetual funding rate)
  - leverage: float (1x to 10x)
  
  # AI decision linkage
  - ai_model: str (claude-3, gpt-4, or mock)
  - confidence: float (0.0 to 1.0)
  - decision_json: dict (complete decision from Phase 5)
  - prompt_pack_version: str (which prompt pack was used)
  
  # Analysis flags
  - is_winner: bool
  - is_breakeven: bool
```

### 2. Learning Agent (packages/shared/learning_agent.py)

**Analyzes trades to discover patterns and suggest improvements:**

```python
LearningAgent:
  
  # Add trades
  def add_trade(entry: TradeJournalEntry) -> None
    "Add a trade to the analysis pool"
  
  # Analysis methods
  def analyze() -> LearningReport
    "Run complete analysis pipeline"
    
  def _calculate_stats() -> TradeJournalStats
    "Compute win rate, profit factor, max DD, consecutive wins/losses"
    
  def _win_rate_by_regime() -> dict
    "Performance in each market regime"
    
  def _performance_by_volatility() -> dict
    "4 buckets: Very Low (0-25%), Low (25-50%), Medium (50-75%), High (75-100%)"
    
  def _performance_by_spread() -> dict
    "3 categories: Tight (<1 pip), Medium (1-5), Wide (≥5)"
    
  def _performance_by_leverage() -> dict
    "Win rate at each leverage level (1x, 2x, 3x, etc.)"
    
  def _performance_by_time_of_day() -> dict
    "Hour-by-hour performance (UTC time)"
    
  def _discover_losing_patterns() -> list[PatternsDiscovered]
    "Detect 5 pattern types:
      1. Low Volatility Losses (loses more in low volatility)
      2. Wide Spread Losses (loses more with wide spreads)
      3. High Leverage Losses (loses more at high leverage)
      4. Regime-Specific Losses (loses in specific regimes)
      5. Time-of-Day Losses (loses at specific hours)
    "
    
  def _analyze_confidence_calibration() -> list[ConfidenceMetrics]
    "Verify AI confidence matches actual results
      Buckets: [0.5-0.6], [0.6-0.7], [0.7-0.8], [0.8-0.9], [0.9+]
      For each: actual_win_rate vs expected_win_rate
    "
    
  def _suggest_adaptations() -> SuggestedAdaptations
    "Generate safe adaptation suggestions (3 variables only)"
```

### 3. Auto-Adapt Engine (SuggestedAdaptations)

**Proposes safe configuration changes with strict constraints:**

```python
SuggestedAdaptations:
  # 3 allowed variables only
  - size_multiplier: float (0.80 to 1.20, ±20% strict)
    Reason: "Increase size for winning patterns / Reduce size for losing patterns"
    
  - confidence_scaling: float (0.80 to 1.20, ±20% strict)
    Reason: "Lower threshold to enter more trades / Raise threshold for quality"
    
  - cooldown_after_loss_minutes: int (0 to 60)
    "Wait X minutes after loss before next trade (prevent revenge trading)"
  
  # NEVER changed
  - max_leverage (remains configurable by user only)
  - stop_loss_logic (remains strict rules)
  - symbols (remains user-selected)
  - entry_conditions (remains LLM-driven)
  
  def apply_to_config(config: dict) -> dict:
    "Apply adaptations to current configuration"
    new_config = {
      "max_position_pct": config["max_position_pct"] * size_multiplier,
      "min_confidence": config["min_confidence"] * confidence_scaling,
      "cooldown_after_loss_minutes": cooldown_after_loss_minutes
    }
    return new_config
  
  def to_dict() -> dict:
    "Export for audit trail / persistence"
```

### 4. Learning Report (LearningReport)

**Complete analysis output:**

```python
LearningReport:
  - analysis_time: datetime
  - trades_analyzed: int (how many trades in this analysis)
  - stats: TradeJournalStats (overall metrics)
  - losing_patterns: list[PatternsDiscovered] (patterns found)
  - confidence_calibration: list[ConfidenceMetrics] (calibration data)
  - suggested_adaptations: SuggestedAdaptations (recommendations)
  - recommendations: list[str] (actionable recommendations)
  
  def to_dict() -> dict:
    "Serialize to dictionary"
  
  def to_json() -> str:
    "Serialize to JSON string"
```

### 5. Database Models (packages/shared/model_phase6.py)

```python
TradeJournal:
  - id: UUID
  - trace_id: str (links to Phase 5 decision trace)
  - trade_id: str
  - symbol: str
  - side: str
  - entry_time, exit_time: datetime
  - entry_price, exit_price, position_size: float
  - pnl, pnl_pct: float
  - market_regime, volatility_percentile: int
  - spread_avg, funding_rate, leverage: float
  - ai_model, confidence: float
  - decision_json: JSON
  - is_winner: bool
  - created_at: datetime

LearningReport:
  - id: UUID
  - analysis_time: datetime
  - trades_analyzed: int
  - stats_json: JSON
  - losing_patterns_json: JSON
  - confidence_calibration_json: JSON
  - recommendations_json: JSON
  - suggested_adaptations_json: JSON
  - adaptations_enabled: bool
  - trigger: str (daily | 50trades | manual)
  - error_message: str (if analysis failed)
  - created_at: datetime

AutoAdaptHistory:
  - id: UUID
  - learning_report_id: UUID
  - size_multiplier_old, size_multiplier_new: float
  - confidence_scaling_old, confidence_scaling_new: float
  - cooldown_old, cooldown_new: int
  - reason: str
  - rolled_back: bool
  - rollback_reason: str
  - applied_at: datetime
  - created_at: datetime

LearningMetrics:
  - id: UUID
  - analysis_date: date
  - total_trades: int
  - win_rate: float
  - profit_factor: float
  - total_pnl: float
  - max_drawdown: float
  - adaptations_applied: int
  - pattern_count: int
  - created_at: datetime
```

---

## API Endpoints

### Trade Journal

```
POST /api/trade-journal
  Record a completed trade
  
  Body:
    TradeJournalEntry (30+ fields)
  
  Response:
    {
      "success": true,
      "trade_id": "trade_001",
      "pnl": 1000.0,
      "pnl_pct": 0.02,
      "total_trades_recorded": 50
    }


GET /api/trade-journal
  List trades with pagination
  
  Query:
    ?limit=50&offset=0&symbol=BTCUSDT&status=winner|loser
  
  Response:
    {
      "trades": [...],
      "total": 500,
      "limit": 50,
      "offset": 0
    }


GET /api/trade-journal/{trade_id}
  Get specific trade details


GET /api/trade-journal/stats/summary
  Quick summary stats
  
  Response:
    {
      "total_trades": 50,
      "winners": 33,
      "losers": 17,
      "win_rate": 0.66,
      "total_pnl": 15000.0,
      "avg_trade": 300.0
    }
```

### Learning Analysis

```
POST /api/learning/analyze
  Trigger manual learning analysis
  
  Response:
    {
      "success": true,
      "report": {
        "analysis_time": "2024-01-15T10:30:00Z",
        "trades_analyzed": 50,
        "stats": {...},
        "losing_patterns": [...],
        "recommendations": [...]
      }
    }


GET /api/learning/reports
  List historical reports
  
  Query:
    ?limit=20&offset=0
  
  Response:
    {
      "reports": [...],
      "total": 15
    }


GET /api/learning/patterns
  Get all discovered losing patterns
  
  Response:
    {
      "patterns": [
        {
          "pattern_name": "low_volatility_losses",
          "description": "Trades lose more often in low volatility markets",
          "occurrences": 5,
          "avg_loss": -250.0,
          "recommendation": "Reduce size or skip trades when volatility < 25th percentile"
        }
      ]
    }


GET /api/learning/confidence-calibration
  AI confidence vs actual performance
  
  Response:
    {
      "calibration": [
        {
          "confidence_range": "0.5-0.6",
          "actual_win_rate": 0.40,
          "trades": 5,
          "expected_win_rate": 0.50
        }
      ]
    }
```

### Auto-Adapt Control

```
POST /api/learning/auto-adapt/apply
  Apply suggested adaptations
  
  Body (optional):
    {
      "learning_report_id": "report_001"
    }
  
  Response:
    {
      "success": true,
      "message": "Adaptations applied",
      "changes": {
        "size_multiplier": 1.1,
        "confidence_scaling": 0.95,
        "cooldown_after_loss_minutes": 5
      },
      "audit_trail": {...}
    }


POST /api/learning/auto-adapt/rollback
  Revert previous adaptation
  
  Body:
    {
      "adapt_history_id": "adapt_001"
    }
  
  Response:
    {
      "success": true,
      "message": "Adaptation rolled back"
    }


GET /api/learning/auto-adapt/history
  Audit trail of all adaptations
  
  Query:
    ?limit=20
  
  Response:
    {
      "history": [
        {
          "id": "adapt_001",
          "size_multiplier_old": 1.0,
          "size_multiplier_new": 1.1,
          "confidence_scaling_old": 0.7,
          "confidence_scaling_new": 0.665,
          "applied_at": "2024-01-15T10:30:00Z",
          "rolled_back": false
        }
      ],
      "total": 8
    }


GET /api/learning/auto-adapt/current
  Current adaptation values
  
  Response:
    {
      "size_multiplier": 1.1,
      "confidence_scaling": 0.95,
      "cooldown_after_loss_minutes": 5,
      "last_updated": "2024-01-15T10:30:00Z"
    }
```

### Dashboard Metrics

```
GET /api/learning/dashboard-metrics
  Complete learning metrics for dashboard
  
  Response:
    {
      "status": "success",
      "trades_analyzed": 50,
      "analysis_time": "2024-01-15T10:30:00Z",
      "stats": {
        "total_trades": 50,
        "win_rate": 0.66,
        "profit_factor": 2.5,
        "max_drawdown": 12.5,
        ...
      },
      "key_metrics": {
        "win_rate": "66.0%",
        "profit_factor": "2.5",
        "max_drawdown": "12.5%"
      },
      "top_patterns": [...],
      "recommendations": [...],
      "suggested_adaptations": {...}
    }
```

---

## Dashboard Integration

### Learning Page (LearningPage.tsx)

**Displays:**
- Key metrics cards (Win Rate, Profit Factor, Max DD, Trades Analyzed)
- Losing patterns with recommendations
- Suggested auto-adapt changes with safety constraints
- Performance segmentation charts:
  - Win rate by market regime
  - Performance by volatility
  - Performance by spread
  - Performance by leverage
  - Performance by time of day
- Auto-adapt history and rollback controls

**Key Features:**
- Real-time metrics update
- Manual analysis trigger
- Safe one-click adaptation application
- Audit trail visibility
- Pattern recommendations

---

## Usage Flow

### 1. Trade Recording (Automatic)

```python
# After every trade closes:
trade = TradeJournalEntry(
    trade_id="trade_001",
    symbol="BTCUSDT",
    side="LONG",
    entry_time=...,
    exit_time=...,
    entry_price=50000.0,
    exit_price=51000.0,
    pnl=1000.0,
    pnl_pct=0.02,
    market_regime="trending_up",
    volatility_percentile=75,
    spread_avg=5.5,
    ai_model="claude-3",
    confidence=0.85,
    decision_json={...},
    is_winner=True,
    # ... other fields
)

# Record via API
response = await apiClient.post('/api/trade-journal', trade.dict())
```

### 2. Learning Analysis (Automatic @ 50 trades or Daily)

```python
# Trigger analysis
response = await apiClient.post('/api/learning/analyze')

# Get report
report = response.data['report']

# Extract key insights
print(f"Win Rate: {report['stats']['win_rate']:.1%}")
print(f"Patterns Found: {len(report['losing_patterns'])}")
print(f"Suggested Adaptations: {report['suggested_adaptations']['enabled']}")
```

### 3. Auto-Adapt Application (Manual, User-Controlled)

```python
# 1. Review recommendations in dashboard
# 2. Decide to apply changes
# 3. Click "Apply Suggestions" button

response = await apiClient.post('/api/learning/auto-adapt/apply')

# New config values applied immediately
# Audit trail recorded for compliance
```

---

## Safety Constraints

### 1. 3-Variable Constraint

Only these can adapt:
- `size_multiplier` (0.80 to 1.20)
- `confidence_scaling` (0.80 to 1.20)
- `cooldown_after_loss_minutes` (0 to 60)

**CANNOT change:**
- ❌ `max_leverage` (user controls only)
- ❌ `stop_loss_logic` (rules-based, strict)
- ❌ `symbols` (user-selected)
- ❌ `entry_conditions` (LLM-driven)

### 2. ±20% Constraint

- Size multiplier: 1.00 ± 0.20 (range: 0.80 to 1.20)
- Confidence scaling: 1.00 ± 0.20 (range: 0.80 to 1.20)

**Rationale:** Prevent extreme swings that could destabilize the system.

### 3. Minimum Trade Threshold

- Requires ≥5 trades before analysis
- Prevents false positives from small sample sizes
- Minimum 3 occurrences for pattern detection

### 4. Audit Trail

- Every adaptation recorded with:
  - Old & new values
  - Reason (from learning report)
  - Timestamp
  - Rollback capability

### 5. User Control

- Adaptations are **suggestions**, not automatic
- User explicitly enables/disables changes
- Rollback available at any time

---

## Pattern Types

### 1. Low Volatility Losses

**Detection:**
- Trades marked as losses
- Volatility percentile < 25 at entry
- Occurrence count ≥ 3

**Recommendation:**
- Skip trading in low volatility
- Or reduce position size

### 2. Wide Spread Losses

**Detection:**
- Trades marked as losses
- Spread > 5 pips at entry
- Occurrence count ≥ 3

**Recommendation:**
- Wait for tighter spreads
- Trade during high liquidity periods

### 3. High Leverage Losses

**Detection:**
- Trades marked as losses
- Leverage > 3x at entry
- Occurrence count ≥ 3

**Recommendation:**
- Reduce leverage
- Use 1x-2x for learning phase

### 4. Regime-Specific Losses

**Detection:**
- Trades marked as losses
- Specific market regime (e.g., choppy)
- Operating win rate significantly lower

**Recommendation:**
- Reduce size or skip trades in this regime
- Wait for regime change

### 5. Time-of-Day Losses

**Detection:**
- Trades marked as losses
- Specific hour (UTC) shows consistent losses
- Occurrence count ≥ 3

**Recommendation:**
- Avoid trading during this hour
- Or apply tighter risk controls

---

## Recommendations Algorithm

Based on analysis, learns agent generates actionable recommendations:

```python
recommendations = [
    "Win rate in choppy markets (17%) is much lower than trending (71%). "
    "Consider reducing size or skipping trades when volatility is below 25th percentile.",
    
    "High leverage (3x+) shows 42% win rate vs 73% at 1x leverage. "
    "Reduce leverage or apply tighter stops.",
    
    "Trades lose more frequently with spreads > 5 pips (58% loss rate). "
    "Wait for tighter spreads or trade during peak liquidity hours.",
    
    "Time-of-day analysis shows losses concentrated in 14:00-16:00 UTC. "
    "Consider skipping trades during this window.",
    
    "AI confidence (0.5-0.6 range) shows 40% actual win rate vs 50% expected. "
    "Either confidence is too low or model needs recalibration."
]
```

---

## Testing

### Run Unit Tests

```bash
# Test trade journal schema
pytest apps/api/test_phase6.py::TestTradeJournalEntry -v

# Test learning agent
pytest apps/api/test_phase6.py::TestLearningAgent -v

# Test pattern discovery
pytest apps/api/test_phase6.py::TestPatternDiscovery -v

# Test auto-adapt constraints
pytest apps/api/test_phase6.py::TestAutoAdaptations -v

# Run all Phase 6 tests
pytest apps/api/test_phase6.py -v
```

### Run Acceptance Tests

```bash
# Run comprehensive verification
python verify_phase6.py

# Output:
# ✅ Trade journal has all 30+ required fields
# ✅ LearningAgent accepts 50+ trades
# ✅ Analysis completes without error
# ✅ Win rate calculated: 62.0%
# ... (12+ acceptance checks)
# 🎉 ALL ACCEPTANCE CRITERIA MET - PHASE 6 COMPLETE
```

---

## Database Schema

### Trade Journal Table

```sql
CREATE TABLE trade_journal (
  id UUID PRIMARY KEY,
  trace_id VARCHAR(255),
  trade_id VARCHAR(255) UNIQUE,
  symbol VARCHAR(20),
  side VARCHAR(10),
  entry_time TIMESTAMP,
  exit_time TIMESTAMP,
  entry_price FLOAT,
  exit_price FLOAT,
  position_size FLOAT,
  entry_reason VARCHAR(100),
  exit_reason VARCHAR(50),
  pnl FLOAT,
  pnl_pct FLOAT,
  max_profit FLOAT,
  max_loss FLOAT,
  market_regime VARCHAR(50),
  volatility_percentile INT,
  spread_avg FLOAT,
  funding_rate FLOAT,
  leverage FLOAT,
  ai_model VARCHAR(50),
  confidence FLOAT,
  decision_json JSONB,
  is_winner BOOLEAN,
  is_breakeven BOOLEAN,
  prompt_pack_version VARCHAR(20),
  created_at TIMESTAMP DEFAULT NOW(),
  INDEX idx_symbol (symbol),
  INDEX idx_is_winner (is_winner),
  INDEX idx_created_at (created_at)
);
```

### Learning Report Table

```sql
CREATE TABLE learning_report (
  id UUID PRIMARY KEY,
  analysis_time TIMESTAMP,
  trades_analyzed INT,
  stats_json JSONB,
  losing_patterns_json JSONB,
  confidence_calibration_json JSONB,
  recommendations_json JSONB,
  suggested_adaptations_json JSONB,
  adaptations_enabled BOOLEAN,
  trigger VARCHAR(20),  -- 'daily' | '50trades' | 'manual'
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  INDEX idx_trigger (trigger),
  INDEX idx_created_at (created_at)
);
```

### AutoAdapt History Table

```sql
CREATE TABLE auto_adapt_history (
  id UUID PRIMARY KEY,
  learning_report_id UUID,
  size_multiplier_old FLOAT,
  size_multiplier_new FLOAT,
  confidence_scaling_old FLOAT,
  confidence_scaling_new FLOAT,
  cooldown_old INT,
  cooldown_new INT,
  reason TEXT,
  rolled_back BOOLEAN DEFAULT FALSE,
  rollback_reason TEXT,
  applied_at TIMESTAMP,
  rolled_back_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (learning_report_id) REFERENCES learning_report(id),
  INDEX idx_rolled_back (rolled_back)
);
```

---

## Integration with Phase 5

When auto-adapt is enabled, Phase 5's AIOrchestrator uses the adapted configuration:

```python
# Phase 5: AIOrchestrator decision flow
async def generate_decision(..., config: dict):
    # Use adapted constraints from Phase 6
    min_confidence = config["min_confidence"]  # Scaled by confidence_scaling
    max_position = config["max_position_pct"]  # Scaled by size_multiplier
    cooldown = config["cooldown_after_loss_minutes"]
    
    # Check if we should skip (cooldown after loss)
    if time_since_last_loss < cooldown:
        return {"status": "skip", "reason": "in_cooldown"}
    
    # LLM generates decision
    decision = await llm_adapter.generate_decision(prompt_pack)
    
    # Validate against adapted confidence threshold
    if decision.confidence < min_confidence:
        return {"status": "skip", "reason": "low_confidence"}
    
    # Validate position size
    decision.position_size *= size_multiplier
    
    # In execution layer (not in Phase 5)
    return decision
```

---

## Troubleshooting

### Analysis Returns "Insufficient Data"

**Problem:** "Insufficient data: 3/5 trades recorded"

**Solution:**
- Wait until 5+ trades have been recorded
- Or trigger manual analysis with `POST /api/learning/analyze`

### No Patterns Discovered

**Possible Causes:**
- Win rate is too high (no clear losing pattern)
- Trades are well-diversified (no concentrated losses)
- Not enough trades (min 50 for reliable patterns)

**Solution:**
- This is actually good! No patterns = no predictable losses

### Confidence Calibration Shows Mismatch

**Example:** "Confidence 0.7-0.8 range shows 45% actual vs 74% expected"

**Interpretation:**
- AI is overconfident in this range
- Either:
  - Model needs recalibration
  - Or threshold should be raised (only enter when confidence > 0.8)

**Solution:**
- Increase `confidence_scaling` to raise minimum threshold
- Or review prompt pack for better quality signals

### Adaptations Won't Apply

**Problem:** "Invalid adaptations - size_multiplier exceeds ±20%"

**Cause:** Learning agent tried to suggest too extreme a change

**Solution:**
- This is the safety mechanism working correctly
- System suggests maximum ±20% to prevent instability
- Consider manual adjustment instead

---

## Quick Start

### 1. Setup Database

```bash
# Ensure models are defined
from packages.shared.model_phase6 import (
    TradeJournal, LearningReport, AutoAdaptHistory, LearningMetrics
)

# Create tables
# db.create_all()
```

### 2. Start Recording Trades

```python
# After each trade closes:
trade = build_trade_entry(...)  # Get all 30+ fields
await apiClient.post('/api/trade-journal', trade.dict())
```

### 3. Monitor Learning Dashboard

```
Open: http://localhost:3000/learning
- View stats as trades accumulate
- See patterns emerge
- Review recommendations
```

### 4. Apply Adaptations

```
When ready:
1. Review suggested changes
2. Click "Apply Suggestions"
3. System logs audit trail
4. Next trades use new config
```

---

## Files Created

| File | Size | Purpose |
|------|------|---------|
| `packages/shared/trade_journal.py` | 400 LOC | Trade recording schema (30+ fields) |
| `packages/shared/learning_agent.py` | 700 LOC | Learning analysis engine (10+ methods) |
| `packages/shared/model_phase6.py` | 200 LOC | Database models (4 tables) |
| `apps/api/phase6_routes.py` | 500 LOC | API endpoints (15+ routes) |
| `apps/dashboard/src/pages/LearningPage.tsx` | 400 LOC | Dashboard visualization |
| `apps/api/test_phase6.py` | 600 LOC | Comprehensive testing (45+ tests) |
| `verify_phase6.py` | 700 LOC | Acceptance verification (12+ checks) |
| `PHASE6_COMPLETE.md` | This doc | Architecture & reference |

**Total Phase 6: 3,500+ lines of production code**

---

## Acceptance Criteria Met

✅ **AC1:** Trade journal captures 30+ fields including entry/exit, PnL, regime, volatility, spread, leverage, AI model, confidence, decision linkage

✅ **AC2:** Learning agent accepts 50+ trades and analyzes them without error

✅ **AC3:** Learning agent discovers losing patterns (5 types: low vol, wide spreads, high leverage, regime-specific, time-of-day)

✅ **AC4:** Auto-adapt strictly respects 3-variable constraint (size, confidence, cooldown) and ±20% limits

✅ **AC5:** Suggested adaptations can be applied to configuration with correct calculations

✅ **AC6:** Every adaptation change is audited with old/new values, timestamp, and reason

✅ **AC7:** API provides 13+ endpoints covering trades, analysis, patterns, and auto-adapt

✅ **AC8:** Performance analysis segments by regime, volatility, spread, leverage, and time-of-day

✅ **AC9:** Database models support trade storage, reports, audit trails, and metrics trending

✅ **AC10:** Confidence calibration verifies AI confidence matches actual win rates in each bracket

✅ **AC11:** Analysis requires minimum 5 trades; pattern detection requires 3+ occurrences

✅ **AC12:** Learning agent generates actionable recommendations based on patterns

---

## Next Steps

Phase 7 (future): **Risk Management & Position Sizing**
- Derivative analysis of optimal position sizing
- Dynamic risk allocation based on market conditions
- Drawdown controls and capital preservation

---

## Questions?

Refer to:
- Architecture: See "Architecture Overview" section
- API Usage: See "API Endpoints" section
- Testing: Run `pytest apps/api/test_phase6.py -v`
- Verification: Run `python verify_phase6.py`
