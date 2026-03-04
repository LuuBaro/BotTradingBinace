# 2-Tier LLM Cascade Guide

## Overview

The 2-tier cascade architecture reduces token usage and 429 rate-limit errors by using two LLMs:
- **Scout**: Lightweight scanner (cheap model) that quickly scans many symbols
- **Verifier**: Detailed analyzer (expensive model) that only processes high-priority signals

## Token Savings

| Mode | Tokens/Symbol | Example (2 symbols/loop) |
|------|--------------|-------------------------|
| Single-tier | ~1500 tokens | 3000 tokens/loop |
| 2-tier cascade | Scout: ~200, Verifier: ~1500 | ~400-1900 tokens/loop |
| **Savings** | | **~40-60% reduction** |

## How It Works

1. **Scout Phase**: Scan all symbols with minimal context
   - Quick regime detection (Trending/Range/Volatile)
   - Action hint (ENTRY/EXIT/HOLD/OBSERVE)
   - Confidence score (0-1)
   - Priority score (0-10)
   - Risk flags

2. **Filter**: Only proceed to verifier if:
   - Scout confidence >= threshold (default 0.6) OR
   - Priority score >= 7 OR
   - Symbol has open position

3. **Verifier Phase**: Full AI analysis for filtered symbols only
   - Detailed checklist execution
   - Order specification with entry/TP/SL
   - Risk assessment
   - Trade journal

## Configuration

### Enable 2-Tier Mode

Add to `.env` (or create from `.env.example`):

```bash
# Enable 2-tier cascade
WORKER_AI_USE_TWO_TIER=true

# Scout: Lightweight scanner (cheap, fast)
WORKER_AI_SCOUT_PROVIDER=groq
WORKER_AI_SCOUT_MODEL=llama-3.1-8b-instant

# Verifier: Detailed analyzer (expensive, accurate)
WORKER_AI_VERIFIER_PROVIDER=openai
WORKER_AI_VERIFIER_MODEL=gpt-4-turbo

# Confidence threshold (0.5-0.8 recommended)
WORKER_AI_SCOUT_CONFIDENCE_THRESHOLD=0.6
```

### Model Recommendations

| Use Case | Scout | Verifier |
|----------|-------|----------|
| **Budget** | groq/llama-3.1-8b-instant | openai/gpt-3.5-turbo |
| **Balanced** | groq/llama-3.1-8b-instant | openai/gpt-4-turbo |
| **Premium** | openai/gpt-3.5-turbo | anthropic/claude-3-sonnet |

### Tuning Confidence Threshold

The `WORKER_AI_SCOUT_CONFIDENCE_THRESHOLD` setting controls the balance between cost and quality:

| Threshold | Verifier Calls | Token Usage | Signal Quality |
|-----------|----------------|-------------|----------------|
| 0.5 | High (~60-80%) | Higher | Best (fewer missed signals) |
| 0.6 | Medium (~40-60%) | Medium | Good (recommended default) |
| 0.7 | Low (~20-40%) | Lower | Fair (some signals missed) |
| 0.8 | Very Low (~10-20%) | Lowest | Risk (many signals missed) |

**Start with 0.6** and adjust based on:
- If missing important signals → lower to 0.5
- If token costs too high → raise to 0.7

## Anti-429 Protection

The 2-tier mode works alongside anti-429 hardening:

```bash
# AI call budgeting (max symbols analyzed per loop)
WORKER_AI_MAX_SYMBOLS_PER_LOOP=2

# Minimum pacing between AI calls (milliseconds)
WORKER_AI_MIN_INTERVAL_MS=350

# Exponential backoff on 429 errors
WORKER_AI_BACKOFF_BASE_SEC=2.0
WORKER_AI_BACKOFF_MAX_SEC=60.0

# Always prioritize symbols with open positions
WORKER_AI_PRIORITIZE_OPEN_POSITIONS=true
```

## Monitoring

### Log Messages

**Scout scan:**
```
scout_signal_strong symbol=BTCUSDT confidence=0.82 action_hint=ENTRY priority=8.5 has_position=false
```

**Scout filter:**
```
scout_filtered_low_priority symbol=ETHUSDT confidence=0.45 action_hint=HOLD priority=3.2
```

**Scout error (fallback to verifier):**
```
scout_failed_fallback_verifier symbol=BNBUSDT
```

**2-tier mode enabled:**
```
ai_two_tier_linked scout_provider=groq scout_model=llama-3.1-8b-instant verifier_provider=openai verifier_model=gpt-4-turbo
```

### Performance Metrics

Track these in logs to measure effectiveness:
- Scout scan count (should be ~2x loop count)
- Verifier call count (should be lower than scan count)
- Token savings: `(1 - verifier_calls/scout_scans) * 100%`

## Troubleshooting

### Scout filtering too aggressively (missing signals)

**Symptom**: Low verifier calls, no trades happening

**Solution**:
1. Lower confidence threshold: `WORKER_AI_SCOUT_CONFIDENCE_THRESHOLD=0.5`
2. Check scout logs for confidence scores
3. Verify scout model has sufficient API quota

### Still hitting 429 errors

**Symptom**: `ai_rate_limited` in logs even with 2-tier mode

**Solution**:
1. Reduce symbols per loop: `WORKER_AI_MAX_SYMBOLS_PER_LOOP=1`
2. Increase pacing: `WORKER_AI_MIN_INTERVAL_MS=500`
3. Check scout provider also has rate limits (Groq: 6000 TPM)

### Scout errors (fallback too often)

**Symptom**: `scout_failed_fallback_verifier` frequent in logs

**Solution**:
1. Check scout API key is valid
2. Verify scout model name is correct
3. Check scout provider status (Groq uptime)
4. Review `scout_error` logs for details

## Testing

### 1. Verify 2-tier mode enabled

```powershell
# Check worker startup logs
docker-compose logs worker | Select-String "ai_two_tier_linked"
```

Expected output:
```
ai_two_tier_linked scout_provider=groq scout_model=llama-3.1-8b-instant verifier_provider=openai verifier_model=gpt-4-turbo
```

### 2. Monitor scout scans

```powershell
docker-compose logs worker | Select-String "scout_signal"
```

Should see mix of `scout_signal_strong` and `scout_filtered_low_priority`.

### 3. Check token savings

Compare before/after enabling 2-tier mode:
- Count verifier calls in logs (`make_decision` calls)
- Should be ~40-60% fewer than without 2-tier mode

## Rollback to Single-Tier

If issues arise, disable 2-tier mode:

```bash
WORKER_AI_USE_TWO_TIER=false
```

Worker will fallback to single LLM (selected via `SELECTED_LLM` setting).

## FAQ

**Q: Can I use same model for scout and verifier?**
A: Yes, but defeats the purpose. 2-tier is for cost optimization (cheap scout + expensive verifier).

**Q: Does 2-tier affect trade quality?**
A: Minimal impact if threshold tuned correctly. High-confidence signals always reach verifier.

**Q: Can I customize scout prompt?**
A: Yes, edit `packages/shared/ai_scout.py` → `_build_compact_prompt()` method.

**Q: What if scout gives wrong signal?**
A: Verifier still makes final decision. Scout only filters, not decides.

**Q: Can I disable scout for specific symbols?**
A: Not directly, but scout always passes symbols with open positions to verifier (safety).

---

**Deployment**: After configuring `.env`, restart worker:
```powershell
docker-compose restart worker
# OR
.\restart_backend.ps1
```

**Support**: Check logs with `docker-compose logs worker -f --tail=100`
