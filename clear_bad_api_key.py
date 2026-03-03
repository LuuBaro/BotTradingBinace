#!/usr/bin/env python3
"""Remove the bad API key, keep only the validated one"""
import sqlite3

db_path = './data/trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("🔧 Removing quota-exhausted API key...\n")

# Clear ai_api_key for user bfb06bb5 (exhausted quota key)
cursor.execute("""
UPDATE user_credentials
SET ai_api_key = NULL
WHERE user_id = 'bfb06bb5-5695-4eb5-ae13-8975762e4394'
""")
print("✓ Cleared API key for bfb06bb5... (quota exhausted)")
print("  → This user will now fallback to global settings (admin only)")

# Verify
cursor.execute("""
SELECT user_id, 
       CASE WHEN ai_api_key IS NULL OR LENGTH(ai_api_key) = 0 THEN 'NO_KEY' ELSE 'HAS_KEY' END as key_status
FROM user_credentials
ORDER BY user_id
""")

print("\n✅ Current status:")
for row in cursor.fetchall():
    user_short = row[0][:12] + "..."
    print(f"  {user_short} | {row[1]}")

conn.commit()
conn.close()
