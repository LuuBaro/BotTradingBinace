#!/usr/bin/env python3
"""Clean Groq API key from config_versions database."""

import sqlite3
import json
from pathlib import Path

db_path = Path("./data/trading.db")

def main():
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("="*80)
    print("🔍 Current config_versions entries:")
    print("="*80)
    
    cursor.execute("""
        SELECT id, version_number, created_at, config_json
        FROM config_versions ORDER BY version_number
    """)
    rows = cursor.fetchall()
    
    for row in rows:
        id_val, version, created_at, config_json_str = row
        try:
            config = json.loads(config_json_str)
            api_key_preview = config.get("openai_api_key", "NULL")
        except:
            api_key_preview = "ERROR_PARSING"
        
        if api_key_preview and api_key_preview.startswith("gsk_"):
            status = "⚠️ GROQ KEY - BAD"
        elif api_key_preview.startswith("sk-proj"):
            status = "✅ OPENAI KEY - GOOD"
        else:
            status = "❓ UNKNOWN"
        
        api_key_short = (api_key_preview or "NULL")[:30] + "..."
        print(f"  ID {id_val} | V{version} | {created_at} | {api_key_short} | {status}")
    
    print("\n" + "="*80)
    print("🗑️  Deleting BAD entries with Groq keys...")
    print("="*80)
    
    # Find and delete bad entries
    cursor.execute("""
        SELECT id, version_number, config_json FROM config_versions
    """)
    all_rows = cursor.fetchall()
    
    bad_ids = []
    for row in all_rows:
        id_val, version, config_json_str = row[0], row[1], row[2]
        try:
            config = json.loads(config_json_str)
            api_key = config.get("openai_api_key", "")
            if api_key.startswith("gsk_"):
                bad_ids.append((id_val, version))
        except:
            pass
    
    if not bad_ids:
        print("✅ No entries with Groq keys found to delete!")
    else:
        for bad_id, bad_version in bad_ids:
            cursor.execute("DELETE FROM config_versions WHERE id = ?", (bad_id,))
            print(f"  ✓ Deleted ID {bad_id} (v{bad_version})")
        
        conn.commit()
        print(f"\n✅ Deleted {len(bad_ids)} bad entry/entries from database")
    
    # Show remaining entries
    print("\n" + "="*80)
    print("✅ Remaining config_versions (should all be OpenAI keys):")
    print("="*80)
    
    cursor.execute("""
        SELECT id, version_number, created_at, config_json
        FROM config_versions ORDER BY version_number
    """)
    rows = cursor.fetchall()
    
    for row in rows:
        id_val, version, created_at, config_json_str = row
        try:
            config = json.loads(config_json_str)
            api_key_preview = config.get("openai_api_key", "NULL")
        except:
            api_key_preview = "ERROR_PARSING"
        
        api_key_short = (api_key_preview or "NULL")[:30] + "..."
        print(f"  ID {id_val} | V{version} | {created_at[:19]} | {api_key_short}")

    conn.close()
    print("\n✅ Database cleanup complete!")

if __name__ == "__main__":
    main()
