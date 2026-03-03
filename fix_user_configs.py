#!/usr/bin/env python3
"""Fix user credentials - set all to Gemini default"""
import sqlite3
import os

db_path = './data/trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("📝 Updating user credentials to Gemini default...\n")

# Update user 1: efefbbcb... từ gemini|mock -> gemini|gemini-2.5-flash
cursor.execute("""
UPDATE user_credentials 
SET ai_model = 'gemini-2.5-flash'
WHERE user_id = 'efefbbcb-9a8a-47ba-b560-13c3643f3f47'
""")
print(f"✓ Updated efefbbcb... → gemini | gemini-2.5-flash")

# Update user 2: bfb06bb5... từ mock|mock -> gemini|gemini-2.5-flash
cursor.execute("""
UPDATE user_credentials 
SET ai_provider = 'gemini', ai_model = 'gemini-2.5-flash'
WHERE user_id = 'bfb06bb5-5695-4eb5-ae13-8975762e4394'
""")
print(f"✓ Updated bfb06bb5... → gemini | gemini-2.5-flash")

conn.commit()

# Verify
print("\n📊 Current configuration:")
cursor.execute('SELECT user_id, ai_provider, ai_model FROM user_credentials ORDER BY user_id')
rows = cursor.fetchall()
for row in rows:
    user_short = row[0][:12] + '...'
    print(f"  {user_short} | {row[1]:<10} | {row[2]}")

conn.close()
print("\n✅ All users configured with Gemini default")
