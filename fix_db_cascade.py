#!/usr/bin/env python
"""Update news_logs foreign key to use CASCADE delete"""
import sqlite3

try:
    conn = sqlite3.connect('data/trading.db')
    cursor = conn.cursor()
    
    print("🔧 Updating foreign key constraint to use CASCADE...")
    
    # SQLite doesn't support ALTER CONSTRAINT, so we need to recreate the table
    # Step 1: Create new table with CASCADE constraint
    cursor.execute('''
        CREATE TABLE news_logs_new (
            id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            title VARCHAR(255),
            content TEXT NOT NULL,
            url VARCHAR(255),
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            FOREIGN KEY(source_id) REFERENCES news_sources (id) ON DELETE CASCADE
        )
    ''')
    
    # Step 2: Copy data from old table
    cursor.execute('INSERT INTO news_logs_new SELECT * FROM news_logs')
    
    # Step 3: Drop old table
    cursor.execute('DROP TABLE news_logs')
    
    # Step 4: Rename new table
    cursor.execute('ALTER TABLE news_logs_new RENAME TO news_logs')
    
    # Step 5: Recreate index
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_news_logs_timestamp ON news_logs (timestamp)')
    
    conn.commit()
    
    # Verify
    cursor.execute('PRAGMA foreign_key_list(news_logs)')
    fks = cursor.fetchall()
    print("✅ Updated! New foreign key:")
    for fk in fks:
        print(f'  {fk}')
    
    # Check if CASCADE is enabled
    if 'CASCADE' in str(fks):
        print("✅ CASCADE delete is now ENABLED")
    
    conn.close()
    print("✅ Database update successful!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
