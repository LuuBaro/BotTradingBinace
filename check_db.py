#!/usr/bin/env python
"""Check database structure"""
import sqlite3

try:
    conn = sqlite3.connect('data/trading.db')
    cursor = conn.cursor()
    
    # Get alembic version
    cursor.execute('SELECT * FROM alembic_version')
    versions = cursor.fetchall()
    print('Current DB Migrations:', versions)
    
    # Check if news_logs exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news_logs'")
    if cursor.fetchone():
        print('✅ news_logs table EXISTS')
        # Check foreign key info
        cursor.execute('PRAGMA foreign_key_list(news_logs)')
        fks = cursor.fetchall()
        if fks:
            print('Foreign keys:')
            for fk in fks:
                print(f'  - {fk}')
        else:
            print('No foreign keys found (needs update)')
    else:
        print('❌ news_logs table does not exist')
        
    conn.close()
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
