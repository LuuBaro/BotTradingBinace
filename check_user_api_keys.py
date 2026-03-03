#!/usr/bin/env python3
"""Check which API key is being used for each user"""
import sqlite3
from packages.shared.encryption import decrypt_key

db_path = './data/trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("📋 User Credentials Detail:\n")
cursor.execute("""
SELECT user_id, ai_provider, ai_model, ai_api_key
FROM user_credentials
ORDER BY user_id
""")

for row in cursor.fetchall():
    user_id = row[0]
    provider = row[1]
    model = row[2]
    encrypted_key = row[3]
    
    try:
        if encrypted_key:
            actual_key = decrypt_key(encrypted_key)
            if actual_key:
                key_display = actual_key[:30] + "..." if len(actual_key) > 30 else actual_key
            else:
                key_display = "DECRYPTION FAILED"
        else:
            key_display = "NO KEY"
    except Exception as e:
        key_display = f"ERROR: {str(e)[:20]}"
    
    user_short = user_id[:12] + "..."
    print(f"User: {user_short}")
    print(f"  Provider: {provider} | Model: {model}")
    print(f"  API Key: {key_display}")
    print()

conn.close()
