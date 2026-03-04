"""
Check decision table schema
"""
import sqlite3

db_path = 'd:\\BotTradingBinace\\data\\trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table schema
cursor.execute("PRAGMA table_info(decisions)")
columns = cursor.fetchall()

print("\n📋 'decisions' table schema:\n")
for col_id, col_name, col_type, notnull, default_val, pk in columns:
    print(f"  {col_id+1}. {col_name:20} {col_type:15} {'PK' if pk else ''}")

# Try to get any data
cursor.execute("SELECT COUNT(*) FROM decisions")
count = cursor.fetchone()[0]
print(f"\n Total decisions: {count}\n")

if count > 0:
    cursor.execute("SELECT * FROM decisions LIMIT 1")
    row = cursor.fetchone()
    print("Sample record:")
    for i, (col_id, col_name, *_) in enumerate(columns):
        print(f"  {col_name}: {row[i]}")

conn.close()
