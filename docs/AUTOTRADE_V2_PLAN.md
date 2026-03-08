# Local AI AutoTrade v2 Plan

## Goal
Build a production-ready **AI Agent trading system** (not a static bot), with:
- deterministic execution pipeline
- trader constraints + explainable reasoning
- testnet/live switch by config only
- Telegram operations channel
- robust local-AI runtime support

## Non-goals
- Promise of guaranteed profit
- uncontrolled high-risk leverage profiles

## Phase 1 (Immediate): "Start trading stably on testnet"
1. **Execution-first loop**
   - Universe resolver (ALL USDT supported, bounded by prefilter)
   - Prefilter top-N symbols (volume/volatility/spread)
   - AI decision + deterministic fallback policy
   - Risk validation + order execution
2. **Eliminate NO_TRADE dead loops**
   - Explicit no-trade reasons taxonomy
   - Fallback ENTRY policy when strong technical triggers present
3. **Stability guards**
   - local AI call timeout/retry
   - runner health checks
   - DB lock retries
4. **Observability**
   - decision→risk→execution counters
   - top reject reasons
   - per-symbol conversion metrics

## Phase 2: "Agent brain + trader profile"
1. Trader profile schema:
   - style, allowed symbols, leverage cap, session windows
2. Prompt pack versioning per trader
3. Structured reasoning output:
   - setup, trigger, invalidation, risk-plan
4. Trade memory (outcome-based adaptation without unsafe weight training)

## Phase 3: "Ops + Security + Go-Live"
1. Config profiles
   - testnet, shadow-live, live
2. Telegram bot controls
   - status, pause, resume, kill-switch, summaries
3. News source integration (config-driven, auditable)
4. Secret hygiene, IP allowlist, fail-safe defaults

## Environment switch policy
- `BINANCE_TESTNET=true|false` controls exchange endpoint switching
- Same execution pipeline used in both envs
- Live requires explicit checklist gate

## Immediate acceptance criteria (Phase 1)
- Worker produces stable ENTRY decisions on testnet
- Order conversion > 0 over observation window
- Top reject reasons are actionable and non-generic
- No recurring hard failures in API/worker logs
