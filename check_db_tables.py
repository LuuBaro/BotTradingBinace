"""
List all tables in database
"""
import sqlite3

db_path = 'd:\\BotTradingBinace\\data\\trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
conn.close()

print(f"\n📊 Database tables:\n")
for table in tables:
    print(f"  • {table[0]}")

# Try to query Decision table (guessing different naming)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
try:
    cursor.execute('SELECT COUNT(*) FROM "Decision"')
    count = cursor.fetchone()[0]
    print(f"\n✅ Decision table has {count} records")
    
    # Get last 10
    cursor.execute('SELECT timestamp, symbol, decision_type, confidence FROM "Decision" ORDER BY timestamp DESC LIMIT 10')
    rows = cursor.fetchall()
    print("\nLast 10 decisions:")
    for row in rows:
        print(f"  {row[0][:19]} | {row[1]:8} | {row[2]:8} | {row[3]:.2f}")
except:
   print("\n⚠️  Could not query Decision table")
finally:
    conn.close()
