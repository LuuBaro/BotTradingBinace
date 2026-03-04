# 🛡️ Risk Vault - Cấu Hình An Toàn cho AI Trading

**Phiên bản**: Nâng cấp Phase 7 Pro

---

## 📋 Tổng Quan

**Risk Vault** là hệ thống quản lý rủi ro lõi để bảo vệ tài khoản khi AI trading tự động. Các tham số này hoạt động như "hàng rào" cứng - AI không thể vượt qua được.

---

## 🎯 Các Tham Số Cấu Hình

### **1️⃣ Điều Khiển Trading**

#### `enabled` (Bật/Tắt)
- **Mô tả**: Kích hoạt hoặc vô hiệu hóa toàn bộ hệ thống trading
- **Mặc định**: `true` (Bật)
- **Khi dùng**: Tạm dừng trading trong thời gian bảo trì hoặc khi có vấn đề
- **Gợi ý**: Bật `true` để trading bình thường

#### `min_balance_threshold` (Số Dư Tối Thiểu)
- **Mô tả**: Số USDT tối thiểu để cho phép trading
- **Mặc định**: `100.0` USDT
- **Ý tưởng**: AI sẽ từ chối trade nếu số dư < mức này
- **Gợi ý**: Để tối thiểu 50-100 USDT để tránh lỗi transaction

---

### **2️⃣ Kiểm Soát Kích Thước Vị Thế**

#### `max_position_pct` (% Kích Thước Lệnh Tối Đa)
- **Mô tả**: Kích thước tối đa 1 lệnh so với tổng số dư
- **Mặc định**: `0.15` (15%)
- **Ví dụ**: Với 1000 USDT → tối đa 150 USDT/lệnh
- **An toàn**: Giảm từ 30% xuống 15% để bảo vệ hơn
- **Khi giảm xuống**: 8% hoặc 5% để cực kỳ an toàn

#### `max_position_per_symbol` (% Kích Thước trên 1 Pair)
- **Mô tả**: Giới hạn vị thế trên 1 cặp tiền (VD: ETHUSDT)
- **Mặc định**: `0.08` (8%)
- **Ý tưởng**: Tránh tập trung rủi ro vào 1 pair
- **Gợi ý**: Giữ ở mức 5-10% để đa dạng hóa

#### `max_concurrent_positions` (Số Lệnh Cùng Lúc)
- **Mô tả**: Tối đa bao nhiêu lệnh đang chạy cùng lúc
- **Mặc định**: `3` lệnh
- **Ví dụ**: Tối đa 3 lệnh BUY/SELL mở cùng lúc
- **An toàn**: 2-4 lệnh là hợp lý

---

### **3️⃣ Rủi Ro & Tỉ Lệ Lợi/Lỗ**

#### `max_risk_per_trade_pct` (Rủi Ro % trên 1 Lệnh)
- **Mô tả**: % tài khoản có thể mất trên 1 lệnh
- **Mặc định**: `0.02` (2%)
- **Cách tính**: SL - Entry = Risk, nếu risk > 2% tài khoản → REJECT
- **Ví dụ**: $1000 tài khoản → rủi ro tối đa $20/lệnh
- **An toàn**: Giữ 1-2% là tiêu chuẩn

#### `min_risk_reward_ratio` (Tỉ Lệ R/R Tối Thiểu)
- **Mô tả**: Tỷ lệ tiền kiếm được / tiền có thể mất
- **Mặc định**: `1.5` (kiếm 1.5 phần để rủi ro 1 phần)
- **Ví dụ**: 
  - Entry: 2500 USD
  - SL: 2450 USD (risk = 50)
  - TP: 2575 USD (reward = 75)
  - Tỉ lệ R/R: 75/50 = 1.5 ✅ Chấp nhận
- **Gợi ý**: 1.5-2.0 là tốt, >= 2.0 là xuất sắc

#### `min_confidence_level` (Mức Tin Cậy AI)
- **Mô tả**: AI phải có độ tin cậy >= mức này để trade
- **Mặc định**: `0.7` (70%)
- **Phạm vi**: 0.0 - 1.0
- **Ví dụ**: Nếu AI chỉ 60% chắc chắn → REJECT, cần >= 70%
- **An toàn**: 0.7-0.8 là hợp lý (cân bằng quality & quantity)

---

### **4️⃣ Quản Lý Thua Lỗ & Cooldown**

#### `max_drawdown_day_pct` (Sụt Vốn Tối Đa Ngày)
- **Mô tả**: Mức sụt giảm vốn tối đa trong ngày (% tài khoản)
- **Mặc định**: `0.05` (5%)
- **Ví dụ**: $1000 tài khoản → mất tối đa $50 trong ngày rồi dừng
- **Ý tưởng**: Nếu trong ngày mất hơn 5% → tạm dừng
- **Gợi ý**: 3-5% là hợp lý

#### `max_daily_loss_pct` (Mất Lỗ Tối Đa Ngày)
- **Mô tả**: % mất lỗ tối đa trong 1 ngày
- **Mặc định**: `0.03` (3%)
- **So sánh**: 
  - `max_drawdown_day_pct` = sụt vốn tổng (unrealized loss)
  - `max_daily_loss_pct` = realized loss (cắt lỗ thực tế)
- **Khi trigger**: Dừng all trades cho ngày hôm đó

#### `cooldown_after_loss` (Chờ Sau Lỗ)
- **Mô tả**: Tạm dừng bao nhiêu giây sau khi dính stoploss
- **Mặc định**: `600` giây = **10 phút**
- **Ý tưởng**: Sau khi bị cắt lỗ → chờ 10 phút rồi mới trade tiếp
- **Mục đích**: Tránh vội vàng, đợi tâm lý bình tĩnh
- **An toàn**: 5-15 phút là tốt

#### `max_consecutive_losses` (Losses Liên Tiếp)
- **Mô tả**: Tối đa bao nhiêu losses liên tiếp trước khi tạm dừng
- **Mặc định**: `3` losses
- **Ví dụ**: 3 lệnh liên tiếp bị cắt lỗ → tạm dừng trading
- **Gợi ý**: 2-4 là hợp lý

#### `recovery_days_after_max_loss` (Ngày Hồi Phục)
- **Mô tả**: Tạm dừng bao nhiêu ngày sau khi đạt max drawdown
- **Mặc định**: `1` ngày
- **Ý tưởng**: Sau khi "chạm mức xấu" → nghỉ 1 ngày rồi resume
- **Gợi ý**: 1 ngày là hợp lý

---

### **5️⃣ Kiểm Soát Lệnh**

#### `max_orders_per_hour` (Lệnh/Giờ Tối Đa)
- **Mô tả**: Số lượng lệnh tối đa được vào trong 1 giờ
- **Mặc định**: `10` lệnh
- **Ví dụ**: Trong 1 giờ tối đa 10 lệnh BUY/SELL
- **Mục đích**: Tránh spam orders
- **Gợi ý**: 5-15 là tốt

#### `max_leverage` (Đòn Bẩy Tối Đa)
- **Mô tả**: Hệ số leverage tối đa cho phép
- **Mặc định**: `5x` (5 lần)
- **Ví dụ**: 1000 USDT + 5x leverage = kiểm soát 5000 USDT
- **Cảnh báo**: Leverage cao = rủi ro cao!
- **An toàn**: 1x-5x tốt, > 10x rất nguy hiểm

---

### **6️⃣ Execution Controls (Thực Thi)**

#### `mandatory_sl_tp` (Bắt Buộc SL/TP)
- **Mô tả**: Mọi lệnh PHẢI cài sẵn Stop Loss và Take Profit
- **Mặc định**: `true` (Bật)
- **Ý tưởng**: AI không được phép vào lệnh mà không có kế hoạch thoát
- **Khuyến cáo**: Luôn bật = an toàn tuyệt đối

#### `max_slippage_pct` (Slippage Tối Đa)
- **Mô tả**: Chênh lệch giá chấp nhận được khi thực thi
- **Mặc định**: `0.005` (0.5%)
- **Ví dụ**: Entry @ 2500 → có thể chạy @ 2500-12.5 = 2487.5 (0.5% slippage)
- **An toàn**: 0.3-0.5% là tốt

#### `use_trailing_stop` (Sử Dụng Trailing Stop)
- **Mô tả**: Tự động nâng SL khi lời
- **Mặc định**: `true` (Bật)
- **Ví dụ**: Entry @ 2500, SL @ 2450. Nếu giá lên → SL tự nâng lên theo
- **Lợi ích**: Lock profit, tránh lỗ

---

## 📊 Cấu Hình Mươi Nhanh

### **🟢 An Toàn Nhất (Beginner)**
```
enabled: true
max_position_pct: 0.08 (8%)        ← Rất cẩn thận
max_position_per_symbol: 0.05 (5%)
max_leverage: 3x
max_risk_per_trade_pct: 0.01 (1%)
min_risk_reward_ratio: 2.0
min_confidence_level: 0.8          ← Chỉ trade khi 80% chắc chắn
max_concurrent_positions: 2
max_orders_per_hour: 5
cooldown_after_loss: 900 (15 min)
max_daily_loss_pct: 0.02 (2%)
```

### **🟡 Cân Bằng (Intermediate)**
```
enabled: true
max_position_pct: 0.15 (15%)       ← Mặc định hiện tại
max_position_per_symbol: 0.08 (8%)
max_leverage: 5x
max_risk_per_trade_pct: 0.02 (2%)
min_risk_reward_ratio: 1.5
min_confidence_level: 0.7
max_concurrent_positions: 3
max_orders_per_hour: 10
cooldown_after_loss: 600 (10 min)
max_daily_loss_pct: 0.03 (3%)
```

### **🔴 Tích Cực (Advanced)**
```
enabled: true
max_position_pct: 0.25 (25%)       ← Rủi ro cao
max_position_per_symbol: 0.15 (15%)
max_leverage: 10x
max_risk_per_trade_pct: 0.03 (3%)
min_risk_reward_ratio: 1.2
min_confidence_level: 0.6
max_concurrent_positions: 5
max_orders_per_hour: 20
cooldown_after_loss: 300 (5 min)
max_daily_loss_pct: 0.05 (5%)
```

---

## 🔄 Quy Trình Kiểm Tra Risk Engine

Khi AI muốn vào lệnh, Risk Engine kiểm tra:

```
1. Trading enabled?                ✅ Nếu không → REJECT
2. Min balance threshold?           ✅ Nếu không → REJECT
3. Có SL/TP bắt buộc?             ✅ Nếu không → REJECT
4. Leverage ok?                    ✅ Nếu quá cao → REJECT
5. Position size ok?               ✅ Nếu quá lớn → REJECT
6. Position per symbol ok?         ✅ Nếu quá tập trung → REJECT
7. Risk/reward ratio ok?           ✅ Nếu quá thấp → REJECT
8. Concurrent positions?           ✅ Nếu quá nhiều → REJECT
9. Orders per hour?                ✅ Nếu quá nhiều → REJECT
10. Consecutive losses?            ✅ Nếu quá nhiều → REJECT
11. Cooldown after loss?           ✅ Nếu đang chờ → REJECT
12. ✨ TẤT CẢ PASS → APPROVED ✨
```

---

## 🎓 Ví Dụ Thực Tế

### **Tình Huống 1: Lệnh BUY ETH**

**Thông số:**
- Tài khoản: 1000 USDT
- Giá ETH hiện tại: 2500 USDT
- AI quyết định: BUY 0.4 ETH (1000 USDT)

**Kiểm tra Risk:**
```
1. Trading enabled? ✅ true
2. Min balance (100)? ✅ 1000 > 100
3. Có SL/TP? ✅ SL=2450, TP=2600
4. Leverage 1x? ✅ <= 5x
5. Size 100%? ❌ 100% > 15% → REJECT!
```

**Kết quả**: REJECTED - Position quá lớn

---

### **Tình Huống 2: Lệnh BUY Nhỏ**

**Thông số:**
- Tài khoản: 1000 USDT
- Giá BTC hiện tại: 40000 USDT
- AI quyết định: BUY 0.1 BTC (4000 USDT leverage 2x) = 8% vị thế

**Kiểm tra Risk:**
```
1. Trading enabled? ✅ true
2. Min balance (100)? ✅ 1000 > 100
3. Có SL/TP? ✅ SL=39000, TP=41000
4. Leverage 2x? ✅ <= 5x
5. Size 8%? ✅ <= 15%
6. Size BTC 8%? ✅ <= 8%
7. R/R = 1000/1000 = 1.0? ❌ < 1.5 → REJECT!
```

**Kết quả**: REJECTED - Tỉ lệ R/R quá thấp

---

### **Tình Huống 3: Lệnh Hợp Lệ**

**Thông số:**
- Tài khoản: 1000 USDT
- AI quyết định: BUY 1 BNB @ 500 (1 BNB = 500 USDT) = 50% vị thế, leverage 2x

**Kiểm tra Risk:**
```
1. Trading enabled? ✅ true
2. Min balance (100)? ✅ 1000 > 100
3. Có SL/TP? ✅ SL=475, TP=550
4. Leverage 2x? ✅ <= 5x
5. Size 10%? ✅ <= 15%
6. Size BNB 10%? ✅ <= 8%
7. R/R = 50/25 = 2.0? ✅ >= 1.5
8. Concurrent = 0? ✅ <= 3
9. Orders/hr = 1? ✅ <= 10
10. No cooldown? ✅
✨ ALL PASS → APPROVED! ✨
```

**Kết quả**: APPROVED - Vào lệnh!

---

## ⚙️ Cách Thay Đổi Cấu Hình

### **Cách 1: Dashboard Web**
1. Mở **http://localhost:3000**
2. Đi **Risk Vault** → **Active Parameters**
3. Chỉnh các giá trị
4. Click **APPLY DEPLOYMENT CHANGES**

### **Cách 2: API**
```bash
curl -X POST http://localhost:8000/risk/config \
  -H "Content-Type: application/json" \
  -d '{
    "max_position_pct": 0.15,
    "max_leverage": 5,
    ...
  }'
```

### **Cách 3: Database**
```sql
UPDATE bot_config 
SET risk_json = '{...}' 
WHERE is_active = true;
```

---

## 🚨 Khuyến Cáo An Toàn

1. **Bắt đầu bảo thủ**: Dùng cấu hình "Safe Beginner" trước
2. **Test 1 tuần**: Chạy paper trading trước
3. **Tăng dần**: Chỉ tăng risk khi thắng liên tiếp
4. **Theo dõi logs**: Kiểm tra `/api/events` thường xuyên
5. **Backup config**: Lưu cấu hình trước khi thay đổi
6. **Never all-in**: Không bao giờ betting toàn bộ tài khoản

---

## 📝 Lịch Sử Thay Đổi

| Phiên Bản | Ngày | Thay Đổi |
|-----------|------|---------|
| 1.0 | 03/04/2026 | Thêm 8 trường cấu hình mới, nâng cấp safety |
| 0.1 | Cũ | Cấu hình sơ khai |

---

**Câu hỏi?** Kiểm tra `/api/docs` hoặc xem `PHASE7_PRODUCTION_GUIDE.md`
