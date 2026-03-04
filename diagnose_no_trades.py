"""
Phân tích tại sao AI chưa vào lệnh trade
"""
import sqlite3
from datetime import datetime, timedelta

db_path = 'd:\\BotTradingBinace\\data\\trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n" + "="*80)
print("🔍 PHÂN TÍCH AI TRADING STATUS")
print("="*80)

# 1. Check recent decisions (last 20)
print("\n📊 20 QUYẾT ĐỊNH GÂN NHẤT:\n")
cursor.execute('''
    SELECT timestamp, decision_type, confidence, rationale, tokens_used
    FROM decisions 
    ORDER BY timestamp DESC 
    LIMIT 20
''')

decisions = cursor.fetchall()
entry_count = sum(1 for d in decisions if d[1] == 'ENTRY')
no_trade_count = sum(1 for d in decisions if d[1] == 'NO_TRADE')

for i, (ts, dtype, conf, rationale, tokens) in enumerate(decisions[:10], 1):
    icon = "🟢" if dtype == "ENTRY" else "⚪"
    print(f"{icon} {i:2}. {ts[:19]} | {dtype:8} | Conf: {conf:.2f}")
    if rationale and len(rationale) > 0:
        print(f"      Lý do: {rationale[:80]}...")

print(f"\n📈 Thống kê 20 quyết định gần nhất:")
print(f"   • ENTRY decisions: {entry_count}")
print(f"   • NO_TRADE decisions: {no_trade_count}")

# 2. Check risk config
print("\n🛡️ RISK CONFIGURATION:\n")
cursor.execute('SELECT risk_json FROM bot_config ORDER BY id DESC LIMIT 1')
risk_row = cursor.fetchone()
if risk_row:
    import json
    risk = json.loads(risk_row[0])
    print(f"   • Enabled: {risk.get('enabled', 'Unknown')}")
    print(f"   • Min Confidence: {risk.get('min_confidence_level', 'N/A')}")
    print(f"   • Min R/R Ratio: {risk.get('min_risk_reward_ratio', 'N/A')}")
    print(f"   • Max Position %: {risk.get('max_position_pct', 'N/A')}")
    print(f"   • Max Consecutive Losses: {risk.get('max_consecutive_losses', 'N/A')}")

# 3. Check if there are any validation failures
print("\n❌ RISK VALIDATION FAILURES (Recent):\n")
cursor.execute('''
    SELECT timestamp, decision_type, risk_approval_reason, validation_errors
    FROM decisions 
    WHERE risk_passed = 0 OR validation_errors IS NOT NULL
    ORDER BY timestamp DESC 
    LIMIT 5
''')

failures = cursor.fetchall()
if failures:
    for ts, dtype, reason, errors in failures:
        print(f"   • {ts[:19]} | {dtype} → Rejected")
        if reason:
            print(f"     Reason: {reason[:80]}")
        if errors:
            print(f"     Errors: {errors[:80]}")
else:
    print("   ✅ Không có validation failures gần đây")

# 4. Check AI activity in last 10 minutes
print("\n⏱️ HOẠT ĐỘNG AI (10 phút gần nhất):\n")
cursor.execute('''
    SELECT COUNT(*) 
    FROM decisions 
    WHERE timestamp > datetime('now', '-10 minutes')
''')
recent = cursor.fetchone()[0]
print(f"   • Decisions trong 10 phút: {recent}")

cursor.execute('''
    SELECT COUNT(*) 
    FROM decisions 
    WHERE timestamp > datetime('now', '-10 minutes')
    AND tokens_used > 0
''')
with_tokens = cursor.fetchone()[0]
print(f"   • Decisions có sử dụng AI (tokens > 0): {with_tokens}")

# 5. Common NO_TRADE reasons
print("\n📋 LÝ DO NO_TRADE PHÖBIẾN:\n")
cursor.execute('''
    SELECT rationale, COUNT(*) as cnt
    FROM decisions 
    WHERE decision_type = 'NO_TRADE'
    AND timestamp > datetime('now', '-1 hour')
    GROUP BY rationale
    ORDER BY cnt DESC
    LIMIT 5
''')

reasons = cursor.fetchall()
for reason, count in reasons:
    if reason:
        print(f"   • [{count}x] {reason[:70]}...")

conn.close()

print("\n" + "="*80)
print("💡 KẾT LUẬN:")
print("="*80)

if entry_count == 0:
    print("""
   ⚠️  AI CHƯA TÌM THẤY CƠ HỘI TRADE PHÙ HỢP
   
   Nguyên nhân có thể:
   1. 📉 Market conditions không match entry rules (RSI, EMA, volume)
   2. 🛡️ Risk parameters quá strict (min confidence, R/R ratio)
   3. 💰 Không đủ balance hoặc vượt max position limits
   4. 🔴 Đã thua liên tục → trong cooldown period
   
   Gợi ý:
   • Giảm min_confidence_level từ 0.7 → 0.55
   • Giảm min_risk_reward_ratio từ 1.5 → 1.2
   • Kiểm tra wallet balance đủ không
   • Xem log worker để thấy chi tiết hơn
""")
else:
    print(f"\n   ✅ AI đã tạo {entry_count} ENTRY decisions!")
    print("   → Kiểm tra xem có bị reject bởi RiskEngine không")

print()
