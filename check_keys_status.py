#!/usr/bin/env python3
import sqlite3

db_path = './data/trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Checking API KEY status:\n")
cursor.execute("""
SELECT user_id, ai_provider, ai_model, 
       CASE WHEN ai_api_key IS NOT NULL AND LENGTH(ai_api_key) > 0 THEN 'HAS_KEY' ELSE 'NO_KEY' END
FROM user_credentials
ORDER BY user_id
""")

for row in cursor.fetchall():
    user_id = row[0][:12] + '...'
    print(f"{user_id:<15} | {row[1]:<10} | {row[2]:<18} | {row[3]}")

conn.close()
