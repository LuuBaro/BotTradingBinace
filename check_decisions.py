#!/usr/bin/env python3
import sqlite3

db_path = './data/trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Checking decision generation:\n")

cursor.execute("""
SELECT COUNT(*) as recent_decisions
FROM decisions
WHERE approved_at > datetime('now', '-2 minutes')
""")
count = cursor.fetchone()[0]
print(f"Decisions approved in last 2 minutes: {count}")

cursor.execute("""
SELECT symbol, side, confidence, approved_at
FROM decisions
WHERE approved_at IS NOT NULL
ORDER BY approved_at DESC
LIMIT 5
""")
print("\nLatest 5 approved decisions:")
for row in cursor.fetchall():
    print(f"  {row[0]:<10} | {row[1]:<6} | conf: {row[2]} | {row[3][:19]}")

conn.close()
