#!/usr/bin/env python3
"""Check signal generation status"""
import sqlite3
from datetime import datetime, timedelta

db_path = './data/trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("📊 Signal Status Check:\n")

# Check decisions table
cursor.execute("""
SELECT COUNT(*) as total_decisions, 
       COUNT(CASE WHEN created_at > datetime('now', '-1 hour') THEN 1 END) as last_hour,
       COUNT(CASE WHEN created_at > datetime('now', '-5 minutes') THEN 1 END) as last_5min,
       MAX(created_at) as latest_decision
FROM decisions
""")

row = cursor.fetchone()
print(f"📈 Decisions in database:")
print(f"  Total: {row[0]}")
print(f"  Last Hour: {row[1]}")
print(f"  Last 5 min: {row[2]}")
print(f"  Latest: {row[3]}\n")

# Check signals table
cursor.execute("""
SELECT COUNT(*) as total_signals,
       COUNT(CASE WHEN created_at > datetime('now', '-1 hour') THEN 1 END) as last_hour,
       MAX(created_at) as latest_signal
FROM signals
""")

row = cursor.fetchone()
print(f"⚡ Signals in database:")
print(f"  Total: {row[0]}")
print(f"  Last Hour: {row[1]}")
print(f"  Latest: {row[2]}\n")

# Check recent errors/events
cursor.execute("""
SELECT COUNT(*) FROM events 
WHERE level='ERROR' AND created_at > datetime('now', '-5 minutes')
""")
error_count = cursor.fetchone()[0]
print(f"❌ Recent errors (last 5 min): {error_count}")

conn.close()
