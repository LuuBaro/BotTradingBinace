#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta

db_path = './data/trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("🔍 Signal Freshness Check:\n")

# Get recent signals
cursor.execute("""
SELECT timestamp, symbol, side, probability
FROM signals 
ORDER BY timestamp DESC
LIMIT 10
""")

print("Latest 10 signals:")
for row in cursor.fetchall():
    timestamp = row[0]
    time_diff = datetime.now() - datetime.fromisoformat(timestamp) if timestamp else None
    age = f"{time_diff.total_seconds()/60:.0f} min ago" if time_diff else "N/A"
    print(f"  {timestamp[:19]} | {row[1]} | {row[2]:5} | prob:{row[3]:.2f} | ({age})")

# Check by timestamp range
cursor.execute("""
SELECT 
  COUNT(CASE WHEN timestamp > datetime('now', '-5 minutes') THEN 1 END) as last_5min,
  COUNT(CASE WHEN timestamp > datetime('now', '-1 hour') THEN 1 END) as last_hour,
  COUNT(CASE WHEN timestamp > datetime('now', '-24 hours') THEN 1 END) as last_24h,
  COUNT(*) as total
FROM signals
""")

counts = cursor.fetchone()
print(f"\n📊 Signal distribution:")
print(f"  Last 5 minutes: {counts[0]}")
print(f"  Last 1 hour: {counts[1]}")
print(f"  Last 24 hours: {counts[2]}")  
print(f"  Total: {counts[3]}")

conn.close()
