#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime

db_path = './data/trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("New Signals Check:\n")

# Get signals from last minute
cursor.execute("""
SELECT timestamp, symbol, side, probability
FROM signals 
WHERE timestamp > datetime('now', '-1 minute')
ORDER BY timestamp DESC
LIMIT 20
""")

signals = cursor.fetchall()
print(f"Signals generated in last 60 seconds: {len(signals)}")
if signals:
    print("\nLatest signals:")
    for s in signals[:10]:
        print(f"  {s[0][:19]} | {s[1]:<10} | {s[2]:<5} | prob: {s[3]}")
else:
    print("  (none yet)")

# Check overall stats
cursor.execute("SELECT COUNT(*) FROM signals")
total = cursor.fetchone()[0]
print(f"\nTotal signals in DB: {total}")

conn.close()
