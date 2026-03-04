#!/usr/bin/env python3
"""Inspect SQLite bot_config table to find Groq configuration."""

import sqlite3
from pathlib import Path

db_path = Path("./data/trading.db")

def main():
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("="*80)
    print("🔍 Contents of bot_config table:")
    print("="*80)

    try:
        # Get the structure first
        cursor.execute("PRAGMA table_info(bot_config)")
        columns = cursor.fetchall()
        print("\nColumns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Get all rows
        cursor.execute("SELECT * FROM bot_config")
        rows = cursor.fetchall()
        
        if not rows:
            print("\n❌ bot_config table is EMPTY!")
        else:
            print(f"\n✓ Found {len(rows)} config row(s):")
            for row in rows:
                print(f"\n  Row: {row}")
                # Try to pretty print if it looks like JSON
                for i, col_info in enumerate(columns):
                    col_name = col_info[1]
                    col_value = row[i] if i < len(row) else None
                    
                    highlight = ""
                    if isinstance(col_value, str):
                        if col_value.startswith("gsk_"):
                            highlight = " ⚠️ GROQ KEY!"
                        elif "groq" in col_value.lower():
                            highlight = " ⚠️ GROQ VALUE!"
                    
                    # Truncate long values
                    display_value = str(col_value) if col_value and len(str(col_value)) <= 80 else (str(col_value)[:80] + "..." if col_value else "NULL")
                    print(f"    {col_name}: {display_value}{highlight}")
    except sqlite3.OperationalError as e:
        print(f"❌ Could not query bot_config: {e}")

    # Check other config-related tables
    print("\n" + "="*80)
    print("🔍 Checking config_versions table:")
    print("="*80)
    
    try:
        cursor.execute("PRAGMA table_info(config_versions)")
        columns = cursor.fetchall()
        if columns:
            cursor.execute("SELECT * FROM config_versions LIMIT 3")
            rows = cursor.fetchall()
            for row in rows:
                print(f"  {row}")
    except:
        pass

    # Look for any Groq or gsk references in the entire database
    print("\n" + "="*80)
    print("🔍 Searching entire database for Groq references:")
    print("="*80)

    try:
        # Get all text columns from all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        found_any = False
        for table_tuple in tables:
            table = table_tuple[0]
            try:
                cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                columns = [description[0] for description in cursor.description]
                
                # Search in each text column
                for col in columns:
                    try:
                        cursor.execute(f"SELECT {col} FROM {table} WHERE {col} LIKE '%groq%' OR {col} LIKE '%gsk_%'")
                        results = cursor.fetchall()
                        if results:
                            found_any = True
                            print(f"\n  Found in {table}.{col}:")
                            for result in results:
                                print(f"    - {result[0]}")
                    except:
                        pass
            except:
                pass
        
        if not found_any:
            print("✅ No Groq references found in database!")
    except Exception as e:
        print(f"Error searching database: {e}")

    conn.close()

if __name__ == "__main__":
    main()
