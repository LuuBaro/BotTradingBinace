# 📊 AI Architecture Visualization

## 🌐 Mode 1: Two-Tier Hybrid (Cloud) - HIỆN TẠI

```
┌──────────────────────────────────────────────────────────────────┐
│                        MARKET DATA (10 symbols)                   │
└────────────────────────┬─────────────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │  Worker Loop (10s)  │
              └──────────┬──────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    BTCUSDT        ETHUSDT         SOLUSDT
         │               │               │
         │               │               │
    ┌────▼────────────────┴────────────────┴─────────────────────┐
    │                    SCOUT STAGE (All Symbols)               │
    │  Model: gpt-3.5-turbo                                      │
    │  Tokens: ~200 per symbol                                   │
    │  Task: Quick scan, confidence scoring                      │
    │                                                             │
    │  BTC: confidence=0.2 → SKIP                                │
    │  ETH: confidence=0.7 → PASS ✅                            │
    │  SOL: confidence=0.3 → SKIP                                │
    └────────────────┬──────────────────────────────────────────┘
                     │
                     │ Only high-confidence signals proceed
                     │
                ┌────▼──────────────────────────────────────────┐
                │      VERIFIER STAGE (Filtered Symbols)        │
                │  Model: gpt-4o-mini                           │
                │  Tokens: ~800 per symbol                      │
                │  Task: Detailed analysis + decision           │
                │                                                │
                │  ETH: Full analysis → ENTRY/EXIT decision ✅  │
                └────────────────┬───────────────────────────────┘
                                 │
                    ┌────────────▼──────────────────┐
                    │   Database + Dashboard       │
                    │   - Decision saved            │
                    │   - Tokens logged: 1000       │
                    │   - Cost: $0.001              │
                    └───────────────────────────────┘

TOKEN COST PER RUN:
┌─────────────────────────┬──────┬────────────────────────┐
│ Phase                   │ Qty  │ Tokens                 │
├─────────────────────────┼──────┼────────────────────────┤
│ Scout (All 10 symbols)  │ 10   │ 200 × 10 = 2,000      │
│ Verifier (Filtered: 2)  │ 2    │ 800 × 2 = 1,600       │
│ TOTAL                   │ 12   │ 3,600 ❌ TOO MUCH     │
└─────────────────────────┴──────┴────────────────────────┘
```

---

## 🖥️ Mode 2: Two-Tier Same (Local AI) - TƯƠNG LAI

```
┌──────────────────────────────────────────────────────────────────┐
│                        MARKET DATA (15 symbols)                   │
│                    (Can use more - no token cost!)                │
└────────────────────────┬─────────────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │  Worker Loop (10s)  │
              └──────────┬──────────┘
                         │
         ┌───────────────┼──────────────────────────────┐
         │               │                              │
         ▼               ▼                              ▼
    BTCUSDT        ETHUSDT              Others...
         │               │                              │
         │               │                              │
    ┌────▼────────────────┴──────────────────────────────┴─────────┐
    │                  SCOUT STAGE (All 15 Symbols)                │
    │  Model: Local LLM (Llama/Mistral/Deepseek)                  │
    │  Tokens: ~150 per symbol (estimated)                         │
    │  Cost: $0 ✅                                                │
    │  Task: Quick scan, confidence scoring                        │
    │                                                              │
    │  BTC: confidence=0.2 → SKIP                                 │
    │  ETH: confidence=0.7 → PASS ✅                             │
    │  SOL: confidence=0.5 → PASS (has position)  ✅             │
    │  Others: Low confidence → SKIP                               │
    └────────────────┬───────────────────────────────────────────┘
                     │
                     │ Only high-confidence OR has position
                     │
                ┌────▼──────────────────────────────────────────┐
                │     VERIFIER STAGE (Filtered: 2-3 Symbols)    │
                │  Model: Same Local LLM                        │
                │  Tokens: ~300 per symbol (estimated)          │
                │  Cost: $0 ✅                                 │
                │  Task: Detailed analysis + decision           │
                │                                               │
                │  ETH: Full analysis → ENTRY/EXIT decision ✅ │
                │  SOL: Risk check → HOLD/EXIT ✅              │
                └────────────────┬───────────────────────────────┘
                                 │
                    ┌────────────▼──────────────────┐
                    │   Database + Dashboard       │
                    │   - Decision saved            │
                    │   - Tokens logged: 0          │
                    │   - Cost: $0.00 ✅            │
                    └───────────────────────────────┘

TOKEN COST PER RUN:
┌─────────────────────────┬──────┬────────────────────────┐
│ Phase                   │ Qty  │ Tokens (estimated)     │
├─────────────────────────┼──────┼────────────────────────┤
│ Scout (All 15 symbols)  │ 15   │ 150 × 15 = 2,250      │
│ Verifier (Filtered: 2)  │ 2    │ 300 × 2 = 600         │
│ TOTAL                   │ 17   │ 2,850... but COST: $0 │
│                         │      │ (all local) ✅         │
└─────────────────────────┴──────┴────────────────────────┘

BENEFITS:
✅ Zero cost (no API calls)
✅ Can scan MORE symbols (15 vs 10) without hitting costs
✅ Privacy (all local)
✅ Lower latency if local hardware good
```

---

## 🔥 Mode 3: Two-Tier Same + Heavyweight (Max Quality)

```
                    SAME AS MODE 2, BUT:
                    
   Prompts are DOUBLED in complexity:
   - Scout: 200 → 400 tokens/symbol
   - Verifier: 300 → 600 tokens/symbol
   
   RESULT:
   ✅ Same $0 cost (still all local)
   ✅ Better decision quality
   ✅ More detailed analysis
   ⚠️ Longer processing time (3-5s vs 1-2s)
   ⚠️ More GPU usage (requires >6GB VRAM)
```

---

## 📈 Comparison Matrix

```
┌─────────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ Aspect              │ 2-Tier Hybrid    │ 2-Tier Local     │ 2-Tier + HW      │
├─────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Scout Model         │ gpt-3.5          │ Local LLM        │ Local LLM        │
│ Verifier Model      │ gpt-4o           │ Local LLM        │ Local LLM        │
│ Token Cost          │ ~$0.001/decision │ $0.00            │ $0.00            │
│ Tokens/Run          │ 1000-1500        │ ~900 (est)       │ ~1800 (est)      │
│ Prompt Complexity   │ Standard         │ Standard         │ Heavyweight      │
│ Decision Quality    │ 8/10             │ 7.5/10*          │ 9/10*            │
│ Response Time       │ 1-2s             │ 2-3s             │ 3-5s             │
│ Hardware Needed     │ None (cloud)     │ Local GPU 4GB+   │ Local GPU 8GB+   │
│ Best For            │ Now (cloud-based)│ Local deployment │ Max quality      │
│ Risk               │ API rate limits  │ Model quality    │ GPU overload     │
└─────────────────────┴──────────────────┴──────────────────┴──────────────────┘

* Depends on local model quality
```

---

## 🎯 Decision Flow Diagram

```
MARKET DATA INPUT
       │
       ▼
    SCOUT?
    │   │
    │   └─ Low confidence (< 0.6) + No position
    │      │
    │      ▼
    │    SKIP ⏭️  (saves tokens!)
    │
    └─ High confidence (>= 0.6) OR Has position
       │
       ▼
    VERIFIER?
    │   │
    │   ├─ Check risk flags
    │   │  (liquidation danger, extreme volatility, etc)
    │   │
    │   ├─ Analyze trading rules
    │   │  (entry conditions, exit conditions)
    │   │
    │   ├─ Calculate position size
    │   │  (based on risk params)
    │   │
    │   └─ Generate decision
    │      (ENTRY, EXIT, HOLD, OBSERVE)
    │
    ▼
SAVE DECISION
   ├─ Symbol
   ├─ Intent
   ├─ Confidence
   ├─ Tokens used
   ├─ Timestamp
   └─ Trader context

    ▼
MONITOR & EXECUTE
   ├─ Track if order filled
   ├─ Monitor PnL
   ├─ Calculate accuracy
   └─ Update metrics
```

---

## 💰 Cost Analysis Over Time

```
SCENARIO: 10 trading decisions per day

┌──────┬──────────────────┬──────────────────┬──────────────────┐
│ Time │ 2-Tier Hybrid    │ 2-Tier Local     │ Savings          │
├──────┼──────────────────┼──────────────────┼──────────────────┤
│ 1 hr │ $0.01            │ $0.00            │ $0.01 saved      │
│ 1 day│ $0.01            │ $0.00            │ $0.01 saved      │
│ 1 wk │ $0.07            │ $0.00            │ $0.07 saved      │
│ 1 mo │ $0.30            │ $0.00            │ $0.30 saved      │
│ 1 yr │ $3.65            │ $0.00            │ $3.65 saved ✅   │
└──────┴──────────────────┴──────────────────┴──────────────────┘

PLUS: Unlimited heavyweight prompts = better decisions!
```

---

## 🔄 Migration Timeline

```
TODAY (Giai đoạn 1)
└─ 2-Tier Hybrid (Cloud)
   Status: ✅ Working
   Token tracking: ✅ Live
   Cost: ~$3.65/year

WEEK 2 (Giai đoạn 2)
└─ Build Local AI
   └─ Test alongside cloud
   └─ Compare decisions

WEEK 3 (Giai đoạn 3)
└─ Switch to 2-Tier Same
   └─ WORKER_AI_MODE=two_tier_same
   └─ WORKER_AI_PROMPT_LEVEL=standard
   └─ Monitor 24 hours

WEEK 4 (Giai đoạn 3+)
└─ Optimize to Heavyweight
   └─ WORKER_AI_PROMPT_LEVEL=heavyweight
   └─ Best quality + zero cost ✅

RESULT: Same quality + $0 cost!
```

---

## 🎨 Architecture After Migration

```
┌─────────────────────────────────────────────────────────────┐
│                    🖥️ MINI PC (Local)                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Local LLM Server (Llama 2, Mistral, Deepseek)      │  │
│  │  ├─ GPU: 8GB VRAM                                   │  │
│  │  ├─ RAM: 16GB                                       │  │
│  │  ├─ Port: 8000                                      │  │
│  │  └─ Latency: < 5s per decision                      │  │
│  └────────┬─────────────────────────────────────────────┘  │
│           │                                                │
│  ┌────────▼─────────────────────────────────────────────┐  │
│  │  Worker Service                                      │  │
│  │  ├─ Load Mode: two_tier_same                        │  │
│  │  ├─ Load Level: heavyweight                         │  │
│  │  ├─ Use Prompt Manager                              │  │
│  │  └─ Call Local LLM via API                          │  │
│  └────────┬─────────────────────────────────────────────┘  │
│           │                                                │
│  ┌────────▼─────────────────────────────────────────────┐  │
│  │  SQLite Database                                     │  │
│  │  ├─ Store decisions                                 │  │
│  │  ├─ Log tokens (estimated)                          │  │
│  │  └─ Trader journal                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                     │                                      │
└─────────────────────┼──────────────────────────────────────┘
                      │
        ┌─────────────▼──────────────┐
        │  📱 Dashboard (Cloud)      │
        │  ├─ View decisions         │
        │  ├─ Monitor performance    │
        │  └─ $0 cost metrics        │
        └────────────────────────────┘

BENEFITS:
✅ All processing local (no cloud API calls)
✅ Zero token cost (local LLM runs free)
✅ Privacy (data stays on-premises)
✅ Scalable (upgrade GPU if need more power)
✅ Ultimate control (modify prompts anytime)
```

---

**👉 Ready to migrate? Check [MIGRATION_TO_LOCAL_AI.md](./MIGRATION_TO_LOCAL_AI.md)**
