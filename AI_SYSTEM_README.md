# 📚 Hệ Thống Quản Lý AI - Tài Liệu Tham Khảo

## 📖 Các File Vừa Được Tạo/Cập Nhật

### 1. **`packages/shared/prompt_manager.py`** ⭐ (NEW)
Hệ thống quản lý prompts với 3 mức độ chi tiết
```
- PromptConfig: Cấu hình mode + level
- ScoutPrompts: 3 mức (lightweight, standard, heavyweight)
- VerifierPrompts: 3 mức tương ứng
- Utility functions: get config, describe status
```

**Cách dùng:**
```python
from packages.shared.prompt_manager import PromptConfig, ScoutPrompts

config = PromptConfig(mode="two_tier_same", prompt_level="heavyweight")
scout_prompt = ScoutPrompts.heavyweight_detailed(symbol, snapshot, has_pos, pnl)
```

---

### 2. **`packages/shared/config.py`** (UPDATED)
Thêm 2 settings mới:
```python
worker_ai_mode: str              # two_tier_hybrid, two_tier_same, single_tier
worker_ai_prompt_level: str      # lightweight, standard, heavyweight
```

**Tác dụng:** Cho phép Config linh hoạt giữa các mode

---

### 3. **`.env`** (UPDATED)
Thêm cấu hình mới:
```env
WORKER_AI_MODE=two_tier_hybrid
WORKER_AI_PROMPT_LEVEL=standard
```

**Tác dụng:** Điều khiển mode AI từ .env file

---

### 4. **`MIGRATION_TO_LOCAL_AI.md`** 📖 (NEW)
**Hướng dẫn chi tiết:**
- Giải thích 3 giai đoạn chuyển đổi
- So sánh mode & level
- Lộ trình migration từng bước
- Troubleshooting
- Checklist

**Nên đọc trước khi deploy local AI**

---

### 5. **`AI_MODE_CHEATSHEET.md`** 🔧 (NEW)
**Quick reference card:**
- 3 cấu hình chính (copy-paste ready)
- Lệnh restart nhanh
- Bảng monitoring
- Troubleshooting commands

**Dùng khi cần chuyển nhanh giữa các mode**

---

### 6. **`AI_ARCHITECTURE.md`** 📊 (NEW)
**Visual architecture:**
- Diagram flow của cách mode
- Token cost estimation
- Decision flow diagram
- Migration timeline
- Final architecture

**Dùng để hiểu rõ cách hoạt động**

---

### 7. **`check_ai_config.py`** 🔍 (NEW)
**Script kiểm tra cấu hình:**
```bash
python check_ai_config.py
```

**Output:**
- Current mode & level
- Provider info
- Token cost estimation
-  Next steps gợi ý

---

## 🎯 Quick Start Path

### **Bước 1: Kiểm tra cấu hình hiện tại**
```bash
python check_ai_config.py
```

### **Bước 2: Nếu muốn bảo vệ local AI sau**
Đọc file này theo thứ tự:

1. [AI_MODE_CHEATSHEET.md](./AI_MODE_CHEATSHEET.md) ← Kiến thức cơ bản (5 phút)
2. [AI_ARCHITECTURE.md](./AI_ARCHITECTURE.md) ← Hiểu cách hoạt động (10 phút)
3. [MIGRATION_TO_LOCAL_AI.md](./MIGRATION_TO_LOCAL_AI.md) ← Chi tiết migration (20 phút)

### **Bước 3: Khi sẵn sàng deploy**
Làm theo checklist trong `MIGRATION_TO_LOCAL_AI.md`

---

## 🔄 Tóm Tắt 3 Mode

| Mode | Config | Dùng khi | Chi phí |
|------|--------|----------|---------|
| **Hybrid** | `WORKER_AI_MODE=two_tier_hybrid` | Bây giờ (cloud) | ~$3.65/yr |
| **Local** | `WORKER_AI_MODE=two_tier_same` | Local AI sẵn | $0.00 |
| **Local+HW** | `WORKER_AI_MODE=two_tier_same` + `PROMPT_LEVEL=heavyweight` | Local mạnh | $0.00 |

---

## 💡 Key Concepts

### **WORKER_AI_MODE** (3 options)
```
two_tier_hybrid  →  Scout: gpt-3.5-turbo, Verifier: gpt-4o
two_tier_same    →  Scout: local LLM, Verifier: local LLM
single_tier      →  1 model cho tất cả (đơn giản nhưng không filtering)
```

### **WORKER_AI_PROMPT_LEVEL** (3 options)
```
lightweight      →  ⚡ Tiết kiệm token, scan nhanh
standard         →  📊 Cân bằng (khuyên dùng)
heavyweight      →  🔥 Full analysis, no token limit
```

### **Combination:** Mode + Level = Quá tốt!
```
two_tier_hybrid + standard      ← Hiện tại
two_tier_same + standard        ← Tương lai (safe)
two_tier_same + heavyweight     ← Tương lai (optimal)
```

---

## 🔗 Cách Code Hoạt Động (Internal)

### **1. Worker Load Config**
```python
# apps/worker/main.py
mode = settings.worker_ai_mode           # two_tier_hybrid
level = settings.worker_ai_prompt_level  # standard
```

### **2. Tế Select Prompts**
```python
# Load prompt manager
config = PromptConfig(mode=mode, prompt_level=level)

# Get scout prompt builder
scout_builder = config.get_scout_prompt_builder()
# → Returns: ScoutPrompts.standard()

# Get verifier prompt builder  
verifier_builder = config.get_verifier_prompt_builder()
# → Returns: VerifierPrompts.standard_full()
```

### **3. Call LLM với Correct Prompt**
```python
# Scout call
scout_prompt = scout_builder(symbol, snapshot, has_pos, pnl)
raw_response = await scout.llm.generate(scout_prompt)

# Verifier call
verifier_prompt = verifier_builder(symbol, market, positions, context, rules)
raw_response = await verifier.llm.generate(verifier_prompt)
```

### **4. Save Decision + Tokens**
```python
decision = Decision(
    symbol=symbol,
    intent=intent,
    tokens_used=tokens_from_api,  # Real token count
    ...
)
db.add(decision)
```

---

## 🎓 Học Thêm

### File cần đọc:
1. `packages/shared/prompt_manager.py` - Xem 3 mức prompt cụ thể
2. `packages/shared/config.py` - Thấy cách settings load
3. `apps/worker/main.py` line 150-175 - Thấy worker logic

### Commands để test:
```bash
# Check config
python check_ai_config.py

# See prompts cho mỗi mode
python -c "from packages.shared.prompt_manager import ScoutPrompts; print(ScoutPrompts.standard.__doc__)"

# Test prompt building
python -c "from packages.shared.prompt_manager import get_prompt_config; c=get_prompt_config(); print(f'Mode: {c.mode}')"
```

---

## ✅ Checklist Để Bắt Đầu

- [x] Hiểu 3 mode AI (hybrid, same, single)
- [x] Hiểu 3 prompt level (lightweight, standard, heavyweight)
- [x] Biết cách chuyển đổi mode (cập nhật `.env` + restart worker)
- [x] Biết khi nào dùng cái nào
- [x] Có script để check config (`check_ai_config.py`)
- [ ] Đọc `AI_MODE_CHEATSHEET.md` ← **Start here**
- [ ] Chuẩn bị local AI hardware
- [ ] Test local AI với mode `two_tier_same`
- [ ] Upgrade lên `heavyweight` nếu cần quality

---

## 🚀 Next Steps

1. **Ngay bây giờ:** Chạy `python check_ai_config.py` để thấy status
2. **Tuần sau:** Đọc `MIGRATION_TO_LOCAL_AI.md` để hiểu migration path
3. **Khi local AI sẵn:** Làm theo checklist trong migration guide

---

## 📞 Troubleshooting

**Q: Cách nào nhanh nhất để chuyển sang local?**  
A: Đọc `AI_MODE_CHEATSHEET.md` + copy config + restart worker

**Q: Local AI yếu, dùng lightweight hay standard?**  
A: Lightweight (ít tính toán) → sau đó test standard

**Q: Có thể rollback về cloud không?**  
A: Yes - đổi `WORKER_AI_MODE=two_tier_hybrid` + restart

**Q: Code có support 3+ model không?**  
A: Có thể modify prompts trong `prompt_manager.py`

---

## 🎉 Lợi Ích Hệ Thống Này

✅ **Linh hoạt:** Dễ chuyển giữa cloud ↔ local  
✅ **Tối ưu:** Mỗi mode có prompt tối ưu  
✅ **Không loạn:** Code tự động chọn đúng config  
✅ **Minh bạch:** Thấy rõ đang dùng mode/level nào  
✅ **Dễ monitor:** Check token cost, quality metric  
✅ **Upgrade dễ:** Từ lightweight → heavyweight chỉ đổi 1 config line  

---

**👉 Ready? Chạy `python check_ai_config.py` ngay! 🚀**
