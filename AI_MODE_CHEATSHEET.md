# 🔧 Cheat Sheet - Chuyển Đổi Nhanh Giữa Các Mode AI

## 🎯 3 Tình Huống Chính

### ✅ Hiện Tại: 2-Tier Cloud (OpenAI)
**Khi nào?** Bây giờ, sử dụng cloud LLM  
**File:** `.env`

```env
WORKER_AI_MODE=two_tier_hybrid
WORKER_AI_PROMPT_LEVEL=standard
WORKER_AI_USE_TWO_TIER=true
WORKER_AI_SCOUT_PROVIDER=openai
WORKER_AI_SCOUT_MODEL=gpt-3.5-turbo
WORKER_AI_VERIFIER_PROVIDER=openai
WORKER_AI_VERIFIER_MODEL=gpt-4o-mini
```

**Command restart:**
```bash
# Stop worker
taskkill /F /IM python.exe

# Start worker
.\.venv\Scripts\python.exe -m apps.worker.main
```

**Check status:**
```bash
curl http://localhost:18000/api/llm/token-usage
# Expect: tokens_actual: 1000-1500 per decision
```

---

### 🚀 Tương Lai: 2-Tier Local (Không Tốn Tiền)
**Khi nào?** Khi local AI sẵn sàng  
**File:** `.env`

```env
WORKER_AI_MODE=two_tier_same
WORKER_AI_PROMPT_LEVEL=standard          # ← Start với standard
WORKER_AI_USE_TWO_TIER=true
WORKER_AI_SCOUT_PROVIDER=local
WORKER_AI_SCOUT_MODEL=my-local-model
WORKER_AI_VERIFIER_PROVIDER=local
WORKER_AI_VERIFIER_MODEL=my-local-model
```

**Command restart:**
```bash
# Stop worker
taskkill /F /IM python.exe

# Start worker
.\.venv\Scripts\python.exe -m apps.worker.main
```

**Check status:**
```bash
.\.venv\Scripts\python.exe check_ai_config.py
# Expect: Mode: two_tier_same, Token cost: $0.00
```

---

### 🔥 Ultimate: 2-Tier Local + Heavyweight (Max Quality)
**Khi nào?** Local AI mạnh, không giới hạn token  
**File:** `.env`

```env
WORKER_AI_MODE=two_tier_same
WORKER_AI_PROMPT_LEVEL=heavyweight       # ← Upgrade từ standard
WORKER_AI_USE_TWO_TIER=true
WORKER_AI_SCOUT_PROVIDER=local
WORKER_AI_SCOUT_MODEL=my-local-model
WORKER_AI_VERIFIER_PROVIDER=local
WORKER_AI_VERIFIER_MODEL=my-local-model
```

**Command restart:**
```bash
# Stop worker
taskkill /F /IM python.exe

# Start worker
.\.venv\Scripts\python.exe -m apps.worker.main

# Monitor
tail -f logs/worker.log | grep "scout\|verifier"
```

---

## 📊 Prompt Level Quick Switch

| Từ | Sang | Action |
|-----|------|--------|
| Standard | Lightweight | Giảm response time (nếu local bị chậm) |
| Standard | Heavyweight | Tăng quality (nếu local mạnh) |

**Change:**
```env
# Option 1: Lightweight
WORKER_AI_PROMPT_LEVEL=lightweight

# Option 2: Standard (default)
WORKER_AI_PROMPT_LEVEL=standard

# Option 3: Heavyweight
WORKER_AI_PROMPT_LEVEL=heavyweight
```

**Restart:** `Ctrl+C` worker → `python -m apps.worker.main`

---

## 🔄 Safe Migration Path

### Phase 1: Test Local AI (Side-by-side)
```env
# Keep cloud as reference
WORKER_AI_MODE=two_tier_hybrid
# Terminal 1: Run cloud worker

# Test local separately
WORKER_AI_MODE=two_tier_same
# Terminal 2: Run local worker in test mode
```

Compare decisions for 1-2 hours, then pick winner.

### Phase 2: Switch to Local
```env
WORKER_AI_MODE=two_tier_same
WORKER_AI_PROMPT_LEVEL=standard
# Restart worker
```

Monitor for 24 hours, check:
- ✅ Decision quality same/better
- ✅ Response time < 10 seconds
- ✅ No errors in logs

### Phase 3: Optimize
```env
WORKER_AI_PROMPT_LEVEL=heavyweight
# Restart worker
```

Check:
- ✅ GPU usage < 80%
- ✅ Response time < 15 seconds
- ✅ Decision quality improved

---

## 🆘 Troubleshooting

### Problem: "Connection refused" on local AI
```bash
# Check if local API is running
curl http://localhost:8000/health

# If not, start it:
# python -m local_ai_server
```

### Problem: High response time with Heavyweight
```env
# Fallback to Standard
WORKER_AI_PROMPT_LEVEL=standard

# Or upgrade local hardware
```

### Problem: Rollback to Cloud ASAP
```env
WORKER_AI_MODE=two_tier_hybrid
WORKER_AI_PROMPT_LEVEL=standard
```

Restart worker immediately.

---

## 📋 Monitoring Commands

```bash
# Check current config
python check_ai_config.py

# Watch worker logs
tail -f logs/worker.log | grep -E "scout|verifier|decision"

# Count decisions today
curl http://localhost:18000/api/llm/token-usage

# Check local AI health
curl http://localhost:8000/health

# See active processes
tasklist | findstr python
```

---

## 💾 Backup Before Change

```bash
# Backup current .env
copy .env .env.backup

# If something goes wrong:
copy .env.backup .env
```

---

## ✨ Summary Table

| Need | Config | Time |
|------|--------|------|
| Quick test local | two_tier_same + standard | 5 min |
| Switch to local | two_tier_same + standard | 10 min |
| Max quality + local | two_tier_same + heavyweight | 10 min |
| Urgent rollback | two_tier_hybrid + standard | 2 min |

---

**👉 Next Step:** Run `python check_ai_config.py` to see current status!
