#!/usr/bin/env python3
import sqlite3
import json

db_path = './data/trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Decision generation check:\n")

cursor.execute("""SELECT COUNT(*) FROM decisions""")
total_decisions = cursor.fetchone()[0]
print(f"Total decisions: {total_decisions}")

cursor.execute("""SELECT COUNT(*) FROM decisions WHERE status='APPROVED'""")
approved = cursor.fetchone()[0]
print(f"Approved decisions: {approved}")

cursor.execute("""SELECT id, decision_json FROM decisions ORDER BY id DESC LIMIT 1""")
row = cursor.fetchone()
if row:
    try:
        decision = json.loads(row[1]) if isinstance(row[1], str) else row[1]
        symbol = decision.get('asset', 'unknown')
        side = decision.get('side', 'unknown')
        print(f"\nLatest decision: {symbol} {side}")
    except:
        print(f"\nLatest decision ID: {row[0]}")
else:
    print("\nNo decisions found")

conn.close()
