"""
Check recent decisions with correct table name
"""
import sqlite3
from datetime import datetime

db_path = 'd:\\BotTradingBinace\\data\\trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Get last 15 decisions
    cursor.execute('''
        SELECT timestamp, symbol, decision_type, confidence 
        FROM decisions 
        ORDER BY timestamp DESC 
        LIMIT 15
    ''')
    
    rows = cursor.fetchall()
    
    if not rows:
        print("❌ No decisions in database")
    else:
        print(f"\n✅ Last {len(rows)} decisions:\n")
        for i, (ts, sym, dtype, conf) in enumerate(rows, 1):
            print(f"{i:2}. {ts[:19]} | {sym:8} | {dtype:10} | Conf: {conf:.2f}")
    
finally:
    conn.close()
