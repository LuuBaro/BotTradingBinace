import sqlite3
import os

db_path = './data/trading.db'

def fix_positions_table():
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check positions table
    cursor.execute("PRAGMA table_info(positions)")
    cols = [row[1] for row in cursor.fetchall()]
    
    needed_cols = [
        ("sl_order_id", "VARCHAR(50)"),
        ("tp_order_id", "VARCHAR(50)"),
        ("stop_loss", "FLOAT"),
        ("take_profit", "FLOAT"),
        ("leverage", "INTEGER DEFAULT 1"),
        ("margin_type", "VARCHAR(10) DEFAULT 'CROSSED'"),
        ("liquidation_price", "FLOAT")
    ]
    
    for col_name, col_type in needed_cols:
        if col_name not in cols:
            print(f"Adding column {col_name} to positions")
            try:
                cursor.execute(f"ALTER TABLE positions ADD COLUMN {col_name} {col_type}")
            except Exception as e:
                print(f"Error adding {col_name} to positions: {e}")
                
    conn.commit()
    conn.close()
    print("Positions table fix completed")

if __name__ == "__main__":
    fix_positions_table()
