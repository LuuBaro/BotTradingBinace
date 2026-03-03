# 🚀 Binance AI Trading Bot - Production Ready

Hệ thống giao dịch tự động tích hợp Trí tuệ nhân tạo (AI) cho thị trường Binance USDⓈ-M Futures. Hệ thống được thiết kế với kiến trúc chịu tải cao (Crash-safe), bảo mật đa lớp và khả năng tự học từ dữ liệu thị trường.

---

## 📊 Trạng Thái Dự Án (Latest Status)
Hiện tại dự án đã hoàn tất toàn bộ **Phase 1 đến Phase 7** và đang trong giai đoạn tối ưu hóa chiến lược AI.

*   **Phase 1-3 ✅ ĐÃ XONG**: Xây dựng nền tảng, tích hợp Binance, Bot Telegram & phân quyền RBAC.
*   **Phase 4 ✅ ĐÃ XONG**: Web Dashboard (React + Tailwind) chuyên nghiệp, theo dõi thời gian thực.
*   **Phase 5 ✅ ĐÃ XONG**: AI Orchestrator - Tự động hiểu yêu cầu của Trader qua ngôn ngữ tự nhiên (Prompt).
*   **Phase 6 ✅ ĐÃ XONG**: Learning Agent - Phân tích lịch sử lệnh để tự điều chỉnh chiến lược.
*   **Phase 7 ✅ ĐÃ XONG**: Production Hardening - Docker, PostgreSQL, Redis, Nginx, Backup tự động.

---

## 🛠️ Tính Năng Chính (Core Features)

### 1. ⚡ AI Decision Engine (LLM Power)
*   **Prompt-to-Strategy**: Chuyển đổi yêu cầu của bạn (ví dụ: "Lấy lời 2$/lệnh, vốn 200$, thắng trên 80%") thành các thông số kỹ thuật thực thi.
*   **Market Regime Detection**: Tự động nhận diện xu hướng thị trường (Trending Up, Range, Trending Down).
*   **Rationale Analysis**: Giải thích lý do tại sao AI vào lệnh hoặc chốt lệnh trong từng tình huống cụ thể.

### 2. 🛡️ Quản Trị Rủi Ro (Risk Management)
*   **3 Lớp Bảo Vệ**: Kiểm tra rủi ro tại AI -> Kiểm tra tại Risk Engine -> Kiểm tra cuối cùng tại Engine thực thi.
*   **Dynamic Stop-Loss**: Tế bào an toàn tự động đóng lệnh nếu trader không chỉ định SL cụ thể.
*   **Leverage & Size Control**: Giới hạn đòn bẩy và quy mô vị thế dựa trên số dư tài khoản thực tế.

### 3. 📱 Đa Nền Tảng Điều Khiển
*   **Web Dashboard**: Theo dõi PNL, vị thế, lệnh chờ và biểu đồ tăng trưởng trực quan.
*   **Telegram Bot**: Thông báo biến động, cho phép đóng lệnh khẩn cấp, tra cứu lịch sử qua `/positions`, `/status`.
*   **Decision Tracing**: Mỗi lệnh đều có `trace_id` để bạn xem lại toàn bộ tư duy của AI khi đó.

---

## 📂 Kiến Trúc Hệ Thống (Structure)

```text
BotTradingBinace/
├── apps/
│   ├── api/          # Backend FastAPI (REST & WebSocket)
│   ├── dashboard/    # Frontend React (Vite, Tailwind, Zustand)
│   ├── telegram/     # Bot Telegram điều khiển từ xa
│   └── worker/       # Core Engine (Logic giao dịch & Phân tích AI)
├── packages/
│   └── shared/       # Thư viện dùng chung (Database, Models, AI Orchestrator)
├── docker/           # Cấu hình Production (Postgres, Redis, Nginx)
├── scripts/          # Script công cụ (Migration, Backup, Initialization)
└── tests/            # Bộ test suite cho toàn bộ hệ thống
```

---

## 🚀 Hướng Dẫn Cài Đặt (Quick Start)

### 1. Cấu hình Môi trường
Tạo file `.env` từ `.env.example` và điền các thông tin:
- `BINANCE_API_KEY` & `BINANCE_API_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY` (hoặc các LLM provider khác)

### 2. Chạy với Docker (Khuyên dùng cho Production)
```bash
docker-compose up -d
```

### 3. Chạy thủ công cho Developer
```bash
# Cài đặt thư viện
pip install -r requirements.txt

# Khởi tạo Database
python scripts/init_db.py

# Khởi động Backend
python -m apps.api.main

# Khởi động Worker (AI Trading)
python -m apps.worker.main
```

---

## 📈 Lộ Trình Phát Triển (Roadmap)
- [x] Tích hợp PostgreSQL thay cho SQLite để chịu tải tốt hơn.
*   [x] Hệ thống Backup tự động hằng ngày.
*   [x] Tính năng "Fixed Profit USD" (Chốt lời theo số tiền cố định).
*   [ ] Tích hợp Deep Learning để dự báo spread và trượt giá.
*   [ ] Hỗ trợ giao dịch đa tài sản (ETH, SOL, XRP...).

---

## 🛡️ Bảo Mật & An Toàn
- **Idempotency**: Chống việc đặt lệnh lặp lại khi mất kết nối.
- **Circuit Breaker**: Tự động tạm dừng nếu hệ thống phát hiện lỗi API liên tục.
- **Audit Logging**: Ghi lại mọi hành động thay đổi cấu hình hoặc can thiệp thủ công.

---
*Dự án được phát triển bởi đội ngũ trading chuyên nghiệp. Vui lòng kiểm tra kỹ trên Testnet trước khi sử dụng tài khoản thật.*
