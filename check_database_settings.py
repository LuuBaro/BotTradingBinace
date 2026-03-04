#!/usr/bin/env python3
"""Inspect SQLite database settings to find Groq configuration."""

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

    # First, let's see what tables exist
    print("📋 Tables in database:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  - {table[0]}")

    print("\n" + "="*80)
    print("🔍 Contents of bot_settings table:")
    print("="*80)

    try:
        cursor.execute("SELECT key, value FROM bot_settings ORDER BY key")
        settings = cursor.fetchall()
        
        if not settings:
            print("❌ bot_settings table is EMPTY!")
        else:
            for key, value in settings:
                # Highlight Groq-related settings
                highlight = ""
                if isinstance(value, str):
                    if value.startswith("gsk_"):
                        highlight = " ⚠️ GROQ KEY!"
                    elif "groq" in value.lower():
                        highlight = " ⚠️ GROQ VALUE!"
                    elif key.lower() in ["provider", "llm_provider"]:
                        highlight = " ⚠️ PROVIDER SETTING!"
                
                # Truncate long values for display
                display_value = value if len(str(value)) <= 80 else str(value)[:80] + "..."
                print(f"  {key:40} | {display_value}{highlight}")
    except sqlite3.OperationalError as e:
        print(f"❌ Could not query bot_settings: {e}")

    print("\n" + "="*80)
    print("🔍 Checking for Groq-related entries:")
    print("="*80)

    try:
        cursor.execute("""
            SELECT key, value FROM bot_settings 
            WHERE value LIKE '%groq%' OR value LIKE '%gsk_%' OR key LIKE '%provider%'
        """)
        groq_settings = cursor.fetchall()
        
        if not groq_settings:
            print("✅ No Groq-related settings found in database!")
        else:
            print(f"❌ Found {len(groq_settings)} Groq-related settings:")
            for key, value in groq_settings:
                print(f"  - {key}: {value}")
    except sqlite3.OperationalError as e:
        print(f"❌ Query error: {e}")

    conn.close()

if __name__ == "__main__":
    main()
