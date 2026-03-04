"""
Check recent decisions from database
"""
import sqlite3
from datetime import datetime, timedelta

db_path = 'd:\\BotTradingBinace\\data\\trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get last 15 decisions
cursor.execute('''
    SELECT timestamp, symbol, decision_type, confidence, ai_notes 
    FROM decision 
    ORDER BY timestamp DESC 
    LIMIT 15
''')

rows = cursor.fetchall()
conn.close()

if not rows:
    print("❌ No decisions found in database")
else:
    print(f"\n✅ Last {len(rows)} decisions:\n")
    for i, row in enumerate(rows, 1):
        ts, sym, dtype, conf, notes = row
        print(f"{i}. {ts[:19]} | {sym:8} | {dtype:8} | Conf: {conf:.2f}")

# Check if any from last 5 minutes
recent = [r for r in rows if datetime.fromisoformat(r[0]) > datetime.utcnow() - timedelta(minutes=5)]
print(f"\n{'='*70}")
if recent:
    print(f"✅ {len(recent)} decisions in last 5 minutes")
    print(f"Pattern: {' → '.join([r[2] for r in recent])}")
else:
    print("⚠️  No recent decisions (worker may be processing)")
