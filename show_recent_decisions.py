"""
Check recent decisions by timestamp
"""
import sqlite3
from datetime import datetime

db_path = 'd:\\BotTradingBinace\\data\\trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get last 10 decisions 
cursor.execute('''
    SELECT id, timestamp, decision_type, confidence, rationale, tokens_used
    FROM decisions 
    ORDER BY timestamp DESC 
    LIMIT 10
''')

rows = cursor.fetchall()
conn.close()

print(f"\n✅ Last {len(rows)} decisions:\n")
for id, ts, dtype, conf, rationale, tokens in rows:
    print(f"ID {id:3} | {ts[:19]} | {dtype:8} | Conf: {conf:.2f} | Tokens: {tokens}")
    if rationale:
        print(f"         Rationale: {rationale[:60]}...")

print("\n" + "="*80)
now = datetime.utcnow()
cursor = sqlite3.connect(db_path).cursor()
cursor.execute("SELECT COUNT(*) FROM decisions WHERE timestamp > datetime('now', '-5 minutes')")
recent = cursor.fetchone()[0]
print(f"\nDecisions in last 5 minutes: {recent}")
print(f"Current time: {now}")
print(f"\n💡 Worker Status: {'🟢 ACTIVE' if recent > 0 else '🟡 Processing/Idle'}")
