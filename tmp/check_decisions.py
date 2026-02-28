import sqlite3
import json
import shutil
import os

db_path = 'D:/BotTradingBinace/data/trading.db'
temp_db = 'D:/BotTradingBinace/data/trading_temp.db'

try:
    shutil.copy2(db_path, temp_db)
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute('SELECT id, timestamp, confidence, regime, rationale, status FROM decisions ORDER BY timestamp DESC LIMIT 5')
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]}, Time: {row[1]}, Conf: {row[2]}, Regime: {row[3]}, Status: {row[5]}")
        print(f"Rationale: {row[4][:100]}...")
        print("-" * 20)
    conn.close()
    os.remove(temp_db)
except Exception as e:
    print(f"Error: {e}")
