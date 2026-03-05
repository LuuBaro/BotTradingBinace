# 🚀 Hướng Dẫn Chuyển Đổi từ 2 LLM Cloud sang 1 AI Local

## 📋 Tổng Quan

Hệ thống hỗ trợ **3 chế độ hoạt động**:

### **Giai Đoạn 1: Hiện Tại (2-Tier Hybrid - Cloud)**
```
WORKER_AI_MODE=two_tier_hybrid
Scout: gpt-3.5-turbo (OpenAI)      ← Rẻ
Verifier: gpt-4o-mini (OpenAI)     ← Chính xác
Token cost: ~1,000-1,500/run
```

### **Giai Đoạn 2: Chuyển Tiếp (2-Tier Same - Local)**
```
WORKER_AI_MODE=two_tier_same
Scout: my-local-model              ← Cùng model
Verifier: my-local-model           ← Cùng model
Token cost: 0 (không tốn tiền) ✅
```

### **Giai Đoạn 3: Hiệu Năng Cao (Heavyweight + Local)**
```
WORKER_AI_MODE=two_tier_same
WORKER_AI_PROMPT_LEVEL=heavyweight
Scout: my-local-model (lightweight prompt)
Verifier: my-local-model (full deep analysis)
Token cost: 0 + Chất lượng cao = ✅✅✅
```

---

## 🔧 Chi Tiết Cấu Hình

### **1️⃣ Mode: `two_tier_hybrid` (Cloud - Hiện Tại)**
```env
WORKER_AI_MODE=two_tier_hybrid
WORKER_AI_USE_TWO_TIER=true
WORKER_AI_SCOUT_PROVIDER=openai
WORKER_AI_SCOUT_MODEL=gpt-3.5-turbo
WORKER_AI_VERIFIER_PROVIDER=openai
WORKER_AI_VERIFIER_MODEL=gpt-4o-mini
WORKER_AI_PROMPT_LEVEL=standard
```

**Lợi ích:**
- ✅ Scout rẻ (3.5-turbo) → Verifier chính xác (4o)  
- ✅ Tự động lọc signal yếu (tiết kiệm token)
- ✅ Chất lượng quyết định cao

**Chi phí:**
- 200 tokens/scan (scout, gpt-3.5)
- 800 tokens/decision (verifier, gpt-4o)
- **~$0.001 per decision**

---

### **2️⃣ Mode: `two_tier_same` (1 AI Local - Tương Lai)**
```env
WORKER_AI_MODE=two_tier_same
WORKER_AI_USE_TWO_TIER=true
WORKER_AI_SCOUT_PROVIDER=local
WORKER_AI_SCOUT_MODEL=my-local-model
WORKER_AI_VERIFIER_PROVIDER=local
WORKER_AI_VERIFIER_MODEL=my-local-model
WORKER_AI_PROMPT_LEVEL=standard
```

**Lợi ích:**
- ✅ **Chi phí token = 0** (tất cả local)
- ✅ Vẫn có filtering (Scout → Signal yếu → Skip)
- ✅ Privacy (data ở local, không gửi lên cloud)
- ✅ Latency thấp (nếu local PC mạnh)

**Nhược điểm:**
- ⚠️ Cần local AI mạnh (GPU tốt)
- ⚠️ Chất lượng phụ thuộc model local
- ⚠️ Overhead tính toán ở local

---

### **3️⃣ Level: `lightweight` vs `standard` vs `heavyweight`**

#### **LIGHTWEIGHT** ⚡
```env
WORKER_AI_PROMPT_LEVEL=lightweight
```
- Scout: 4 dòng data, output JSON ngắn
- Verifier: Quick decision, 5 phút xử lý
- **Token/run: ~300-500**
- Dùng cho: Limited resources, scan nhanh

#### **STANDARD** 📊
```env
WORKER_AI_PROMPT_LEVEL=standard
```
- Scout: Standard data + context
- Verifier: Full analysis, risk rating
- **Token/run: ~800-1,200**
- Dùng cho: **Khuyên dùng - cân bằng tốt**

#### **HEAVYWEIGHT** 🔥
```env
WORKER_AI_PROMPT_LEVEL=heavyweight
```
- Scout: Chi tiết cao, đầy đủ context
- Verifier: Deep analysis, technical breakdown
- **Token/run: ~2,000-3,000**
- Dùng cho: Powerful local AI, max quality

---

## 📊 So Sánh Mode & Level

| Mode | Level | Token/run | Chi phí | Chất lượng | Khi dùng |
|------|-------|-----------|---------|-----------|----------|
| **2-tier Hybrid** | lightweight | 400 | 💰 rẻ | 7/10 | Cloud + giới hạn token |
| **2-tier Hybrid** | standard | 1,000 | 💰💰 | 8.5/10 | **Cloud - khuyên dùng** |
| **2-tier Hybrid** | heavyweight | 2,500 | 💰💰💰 | 9/10 | Cloud + budget cao |
| **2-tier Same** | lightweight | 0 | ✅ miễn phí | 7/10 | Local yếu, scan nhanh |
| **2-tier Same** | standard | 0 | ✅ miễn phí | 8/10 | Local trung bình |
| **2-tier Same** | heavyweight | 0 | ✅ miễn phí | 9.5/10 | **Local mạnh - tối ưu** |
| **Single-tier** | standard | 1,500 | 💰💰 | 6/10 | Tối giản, không filtering |

---

## 🔄 Lộ Trình Chuyển Đổi

### **Bước 1: Chuẩn Bị (Local AI chưa sẵn)**

Status: **Hiện tại** - Vẫn dùng Cloud 2-tier

```env
WORKER_AI_MODE=two_tier_hybrid
WORKER_AI_PROMPT_LEVEL=standard
```

✅ Hệ thống hoạt động tốt, tracking token thực

---

### **Bước 2: Xây Dựng & Test Local AI**

Khi local AI đã sẵn sàng, **test trước** với mode mới:

```env
WORKER_AI_MODE=two_tier_same
WORKER_AI_USE_TWO_TIER=true
WORKER_AI_SCOUT_PROVIDER=local
WORKER_AI_SCOUT_MODEL=my-model-v1
WORKER_AI_VERIFIER_PROVIDER=local
WORKER_AI_VERIFIER_MODEL=my-model-v1
WORKER_AI_PROMPT_LEVEL=standard        # Bắt đầu với standard
```

**Test kỹ:**
- ✅ So sánh decision: local vs OpenAI
- ✅ Kiểm tra response time
- ✅ Validate JSON parse
- ✅ Monitor GPU usage

---

### **Bước 3: Tối Ưu Hiệu Năng (Không Giới Hạn Token)**

Sau khi local AI ổn định, **tăng prompt complexity**:

```env
WORKER_AI_PROMPT_LEVEL=heavyweight     # ← Tăng từ standard
```

**Gains:**
- 🔥 Scout prompts chi tiết hơn → Filtering tốt hơn
- 🔥 Verifier prompts sâu hơn → Decision chất lượng cao
- 🔥 Zero token cost → Tối ưu hiệu năng hoàn toàn

---

## 📁 Cấu Trúc Config Sau Chuyển Đổi

### **Hiện Tại (2-tier Hybrid)**
```env
# LLM CONFIGURATION
SELECTED_LLM=openai
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_MODEL=gpt-4o-mini

# WORKER AI MODE & LEVEL
WORKER_AI_MODE=two_tier_hybrid
WORKER_AI_PROMPT_LEVEL=standard

# 2-TIER SETTINGS
WORKER_AI_USE_TWO_TIER=true
WORKER_AI_SCOUT_PROVIDER=openai
WORKER_AI_SCOUT_MODEL=gpt-3.5-turbo
WORKER_AI_VERIFIER_PROVIDER=openai
WORKER_AI_VERIFIER_MODEL=gpt-4o-mini
```

### **Sau Chuyển (2-tier Same Local)**
```env
# LLM CONFIGURATION (Local)
SELECTED_LLM=local
LOCAL_LLM_BASE_URL=http://localhost:8000  # ← Local API
USE_LOCAL_LLM=true

# WORKER AI MODE & LEVEL
WORKER_AI_MODE=two_tier_same
WORKER_AI_PROMPT_LEVEL=heavyweight        # ← No limit

# 2-TIER SETTINGS
WORKER_AI_USE_TWO_TIER=true
WORKER_AI_SCOUT_PROVIDER=local
WORKER_AI_SCOUT_MODEL=my-local-model
WORKER_AI_VERIFIER_PROVIDER=local
WORKER_AI_VERIFIER_MODEL=my-local-model
```

---

## ⚙️ Cách Hoạt Động (Code Level)

### **Prompt Selection (Tự động)**

Code sẽ **tự động chọn prompt** dựa vào mode + level:

```python
# apps/worker/main.py
if settings.worker_ai_mode == "two_tier_same":
    # Dùng prompt manager
    config = PromptConfig(
        mode="two_tier_same",
        prompt_level=settings.worker_ai_prompt_level  # standard hay heavyweight
    )
    
    # Scout dùng lightweight prompt
    scout_prompt = config.get_scout_prompt_builder()(
        symbol, snapshot, has_position, pnl
    )
    
    # Verifier dùng full prompt (phụ thuộc level)
    verifier_prompt = config.get_verifier_prompt_builder()(
        symbol, market_data, positions, trader_context, prompt_pack
    )
```

---

## 🔍 Monitoring & Validation

### **Check Mode Hiện Tại**

```bash
# Terminal
curl http://localhost:18000/api/system/config

# Response:
{
  "worker_ai_mode": "two_tier_hybrid",
  "worker_ai_prompt_level": "standard",
  "scout_provider": "openai",
  "verifier_provider": "openai"
}
```

### **Compare Token Usage**

```bash
# Ghi lại token tổng hôm nay
curl http://localhost:18000/api/llm/token-usage

# Before (2-tier hybrid):
{
  "tokens_actual": 15000,
  "cost": "$0.05",
  "decisions": 15
}

# After (2-tier same):
{
  "tokens_actual": 0,
  "cost": "$0.00",
  "decisions": 15
}
```

---

## 🚨 Troubleshooting

### **Q: Code bị loạn khi chuyển mode?**
✅ **Không** - Code tự động detect mode từ config, dùng prompt manager

### **Q: Decision quality sẽ giảm?**
⚠️ **Có khả năng** - Nếu local model yếu hơn GPT-4. Nên test trước.

### **Q: Có thể rollback về Cloud không?**
✅ **Có** - Chỉ cần thay `WORKER_AI_MODE=two_tier_hybrid` + restart worker

### **Q: Lightw eight vs Standard vs Heavyweight, dùng cái nào?**
- **Lightweight**: Khi token hạn chế (OpenAI + limited budget)
- **Standard**: Khuyên dùng cho cả Cloud lẫn Local  
- **Heavyweight**: Khi có Local AI mạnh + không giới hạn token

---

## 📋 Checklist Chuyển Đổi

### **Step 1: Build Local AI Model**
- [ ] Train / setup local LLM (LLaMA 2, Mistral, Deepseek, etc.)
- [ ] Expose via API (port 8000 hoặc custom)
- [ ] Test response format (phải trả JSON)

### **Step 2: Update Config**
- [ ] Copy current .env → .env.backup
- [ ] Update WORKER_AI_MODE=two_tier_same
- [ ] Update WORKER_AI_SCOUT_PROVIDER=local
- [ ] Update LOCAL_LLM_BASE_URL=http://localhost:8000

### **Step 3: Test (Standard Level)**
- [ ] Restart worker
- [ ] Monitor logs: `ai_two_tier_linked scout_provider=local`
- [ ] Generate 5 test decisions
- [ ] Compare quality vs OpenAI

### **Step 4: Optimize (Heavyweight)**
- [ ] If test OK: Set WORKER_AI_PROMPT_LEVEL=heavyweight
- [ ] Restart worker
- [ ] Monitor: GPU usage, response time
- [ ] Fine-tune prompts nếu cần

### **Step 5: Monitor (Production)**
- [ ] Set alerts for decision latency
- [ ] Track decision quality (PnL per decision)
- [ ] Compare cost: 0 vs $0.001 before
- [ ] Document prompt adjustments

---

## 💡 Tips & Best Practices

### **Tip 1: Gradient Transition**
Không cần chuyển toàn bộ cùng lúc. Có thể dùng **hybrid modes**:

```env
# Hybrid: Scout dùng local (rẻ), Verifier dùng cloud (chính xác)
WORKER_AI_SCOUT_PROVIDER=local
WORKER_AI_VERIFIER_PROVIDER=openai
```

### **Tip 2: A/B Testing**
Chạy 2 worker instances:
- Worker 1: Cloud (baseline)
- Worker 2: Local (test)

So sánh decision quality trước khi cutover.

### **Tip 3: Prompt Templates**
Khi chuyển  sang local, có thể cần **tinh chỉnh prompts** cho model cụ thể:
- LLaMA: Dùng [INST] format
- Mistral: Dùng chat format
- Deepseek: Custom instructions

Hệ thống sẽ maintain **prompt_manager.py** để dễ tùy chỉnh.

### **Tip 4: Token Tracking**
Ngay cả khi dùng local (0 token OpenAI), system vẫn track:
- Input token count (estimated)
- Processing time
- Decision latency

Để monitor performance.

---

## 🎯 Target Architecture (Sau Chuyển Đổi)

```
┌─────────────────────────────────────────┐
│        Trader / Dashboard               │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│  API Server (FastAPI)                   │
│  - Config management                    │
│  - Decision API                         │
│  - Token tracking                       │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│  Worker (Async Trading Engine)          │
│  - Read .env (Mode + Level)             │
│  - Load PromptManager                   │
│  - 2-Tier Cascade OR Single             │
└────┬─────────────────────┬──────────────┘
     │                     │
  ┌──▼─────────────┐   ┌──▼─────────────┐
  │ Local AI API   │   │ Cloud API      │
  │ (Port 8000)    │   │ (OpenAI)       │
  │ - Scout        │   │ - Fallback     │
  │ - Verifier     │   │ - Hybrid mode  │
  └────────────────┘   └────────────────┘
     (Zero cost)          (Optional)
```

---

## 📞 Support & Feedback

Nếu gặp lỗi khi chuyển đổi:
1. Check logs: `tail -f logs/worker.log`
2. Verify config: `curl http://localhost:18000/api/system/config`
3. Test local API: `curl http://localhost:8000/api/generate`
4. Rollback: Đổi WORKER_AI_MODE=two_tier_hybrid → restart

Chúc bạn deployment thành công! 🚀
