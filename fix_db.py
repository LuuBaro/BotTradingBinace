import sqlite3
import os
from datetime import datetime

db_path = './data/trading.db'

def fix_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check decisions table
    cursor.execute("PRAGMA table_info(decisions)")
    cols = [row[1] for row in cursor.fetchall()]
    
    needed_cols = [
        ("decision_type", "VARCHAR(20)"),
        ("status", "VARCHAR(20)"),
        ("prompt_pack_id", "VARCHAR(36)"),
        ("rationale", "TEXT"),
        ("timeframe_analysis", "JSON"),
        ("checklist_results", "JSON"),
        ("risk_assessment", "JSON"),
        ("order_spec", "JSON"),
        ("market_snapshot", "JSON"),
        ("current_positions", "JSON"),
        ("risk_passed", "BOOLEAN"),
        ("risk_approval_reason", "TEXT"),
        ("risk_modifications", "JSON"),
        ("order_id", "VARCHAR(100)"),
        ("position_id", "VARCHAR(100)"),
        ("execution_price", "FLOAT"),
        ("execution_status", "VARCHAR(50)"),
        ("execution_error", "TEXT"),
        ("is_valid_json", "BOOLEAN"),
        ("validation_errors", "JSON"),
        ("approved_by", "VARCHAR(50)"),
        ("approved_at", "DATETIME")
    ]
    
    for col_name, col_type in needed_cols:
        if col_name not in cols:
            print(f"Adding column {col_name} to decisions")
            try:
                cursor.execute(f"ALTER TABLE decisions ADD COLUMN {col_name} {col_type}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
                
    # Check signals table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signals'")
    if not cursor.fetchone():
        print("Creating signals table")
        cursor.execute("""
            CREATE TABLE signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                entry_zone VARCHAR(50) NOT NULL,
                probability FLOAT NOT NULL,
                rationale TEXT NOT NULL,
                status VARCHAR(20) DEFAULT 'ACTIVE',
                expires_at DATETIME
            )
        """)
        
    # Check bot_config table for approval_mode
    cursor.execute("PRAGMA table_info(bot_config)")
    cols = [row[1] for row in cursor.fetchall()]
    if "approval_mode" not in cols:
        print("Adding approval_mode to bot_config")
        cursor.execute("ALTER TABLE bot_config ADD COLUMN approval_mode BOOLEAN DEFAULT 0")

    # Ensure at least one active config exists
    cursor.execute("SELECT COUNT(*) FROM bot_config")
    if cursor.fetchone()[0] == 0:
        print("Creating initial bot_config")
        cursor.execute("""
            INSERT INTO bot_config (env, symbols_json, risk_json, version, is_active, created_at, approval_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "demo", 
            '{"symbols": ["BTCUSDT"]}', 
            '{"max_leverage": 5.0, "max_position_size": 0.1, "max_daily_loss": 0.02, "min_win_rate": 0.0}',
            1,
            1,
            datetime.now().isoformat(),
            0
        ))

    conn.commit()
    conn.close()
    print("DB Fix completed")

if __name__ == "__main__":
    fix_db()
