# 📊 Overview Page Metrics Explanation

## 🎯 Key Indicators

### 1. **Thời gian hoạt động (Operating Time)** ⏱️
- **Loại dữ liệu**: REAL-TIME từ Backend
- **Nguồn**: `/api/bot/status` - `uptime_seconds`
- **Ý nghĩa**: Tổng thời gian bot đã chạy liên tục
- **Ví dụ**: "18h 18m" = Bot đã chạy 18 giờ 18 phút
- **Cập nhật**: Mỗi 8 giây

---

### 2. **Tổng Alpha (Total PnL)** 💰
- **Công thức**: Realized PnL + Unrealized PnL
- **Loại dữ liệu**: REAL-TIME từ Backend
- **Nguồn**: 
  - Realized: `/api/bot/status` - `realized_pnl_today`
  - Unrealized: `/api/positions/live` hoặc `/api/positions` 
- **Ý nghĩa**: **KHÔNG phải Alpha** - đây là **Total Profit & Loss**
  - Nếu > 0 = lãi (Profit) 🟢
  - Nếu < 0 = lỗ (Loss) 🔴
- **Phân loại**:
  - **Realized**: Lợi nhuận từ các lệnh đã đóng hôm nay
  - **Unrealized**: Lợi nhuận từ các vị thế đang mở
- **Cập nhật**: Mỗi 8 giây

---

### 3. **Sự kiện hệ thống (System Events)** 📡
- **Loại dữ liệu**: REAL-TIME từ Event Store
- **Ý nghĩa**: Số lượng sự kiện được ghi nhận trong phiên hiện tại
- **Ví dụ**: "0" = Chưa có sự kiện nào ghi nhận
- **Nơi xem chi tiết**: "Luồng dữ liệu thời gian thực" section ở dưới
- **Cập nhật**: Real-time khi có event mới

---

### 4. **Live Intent (Dự định)** 🧠 
- **Loại dữ liệu**: REAL-TIME từ Backend
- **Nguồn**: `/api/decisions?limit=10` - Decision mới nhất
- **Bao gồm**:
  - **Rationale**: Giải thích AI đưa ra quyết định
  - **Action/Intent**: OPEN, CLOSE, hoặc HOLD
  - **Confidence**: Mức độ tin cậy (0-100%)
- **Ý nghĩa**: 
  - Quyết định mới nhất của AI dựa trên phân tích thị trường
  - Không phải order thực - chỉ là "intended action"
  - Needs approval nếu chế độ manual approval bật
- **Timestamp**: "about 8 hours ago" = thời gian decision được tạo
- **Cập nhật**: Mỗi khi AI tạo decision mới

---

### 5. **Cơ sở hạ tầng (Infrastructure)** 🏗️
- **Loại dữ liệu**: REAL-TIME kiểm tra thực
- **Nguồn**: `/api/health/status` (mới được cập nhật!)
- **Các dịch vụ kiểm tra**:

| Dịch vụ | Ý nghĩa | Kiểm tra |
|---------|---------|---------|
| **Market Streams** | WebSocket từ Binance | Kiểm tra thời gian update cuối cùng |
| **Risk Validator** | Hệ thống tính toán risk | Kiểm tra nếu đang chạy |
| **Binance API** | API gọi các lệnh | Thử kết nối realtime |
| **Internal DB** | CSDL lưu data | Thử query database |

**Status colors**:
- 🟢 **Optimal/Operational**: Healthy (Healthy: 100% OK, Operational: OK)
- 🟡 **Degraded**: Có vấn đề nhưng vẫn chạy
- 🔴 **Offline**: Không hoạt động

---

### 6. **Luồng dữ liệu thời gian thực (Real-time Telemetry)** 📊
- **Loại dữ liệu**: REAL-TIME Event Stream
- **Ý nghĩa**: Log của tất cả sự kiện hệ thống
- **Bao gồm**:
  - Info (🔵): Thông tin bình thường - "Order opened", "Position closed"
  - Warning (🟡): Cảnh báo - "Risk limit approaching"
  - Error (🔴): Lỗi - "API error", "Connection lost"
- **Timestamp**: Thời gian event xảy ra (HH:mm:ss.SSS)
- **Node ID**: Identifier của event
- **Cập nhật**: Real-time khi có event

---

## 🔄 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    OVERVIEW PAGE (Real-time)                    │
└─────────────────────────────────────────────────────────────────┘
           │
           ├─ Every 8 seconds:
           │  ├─ /api/bot/status  ──────────→ Operating Time, Realized PnL
           │  ├─ /api/positions/live  ──────→ Unrealized PnL
           │  ├─ /api/orders  ──────────────→ Order count
           │  ├─ /api/decisions  ───────────→ Latest AI Decision
           │  ├─ /api/reports/pnl-history  ─→ PnL Chart
           │  └─ /api/health/status  ──────→ Infrastructure Status
           │
           └─ Real-time:
              ├─ Event Stream  ──────────────→ System Events ticker
              └─ WebSocket updates  ────────→ Position updates
```

---

## 📝 Data Sources Summary

| Metric | Real-time? | Source | Update Interval |
|--------|-----------|--------|-----------------|
| Operating Time | ✅ Yes | `/api/bot/status` | 8 seconds |
| Total PnL | ✅ Yes | `/api/bot/status` + `/api/positions/live` | 8 seconds |
| System Events | ✅ Yes | Event Store | Real-time |
| Live Intent | ✅ Yes | `/api/decisions` | 8 seconds |
| Infrastructure | ✅ Yes | `/api/health/status` | 8 seconds |
| Telemetry | ✅ Yes | Event Stream | Real-time |

---

## ⚠️ Important Notes

1. **Live Intent != Order**: 
   - "HOLD" decision = AI says don't trade now, not an actual order
   - Requires approval mode to actually execute actions

2. **Total Alpha != Alpha Strategy**:
   - Alpha = outperformance vs benchmark
   - Total PnL = realized + unrealized P&L
   - These are different metrics

3. **Infrastructure Status**:
   - Now pulls REAL data from actual service checks
   - Each check runs when you load the page
   - This can take 2-3 seconds for all checks to complete

4. **Events/Telemetry**:
   - Events only show during current session
   - Clears on page refresh
   - Not stored in telemetry log (kept in Event Store DB)

---

## 🔧 Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Initializing Neural Core" spinner | Decisions not loaded yet | Wait 8 seconds for API call |
| Infrastructure all showing "Checking..." | Health checks slow | Refresh page |
| PnL doesn't match Binance | Using unrealized only | Check if positions loaded |
| Telemetry empty | No events in current session | Open a position to create events |

---

**Last Updated**: Feb 26, 2026
**Version**: 1.0 (Real-time Infrastructure Checks Added)
