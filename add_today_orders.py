import sqlite3
from datetime import datetime
import uuid

def fix_orders():
    conn = sqlite3.connect('data/trading.db')
    cursor = conn.cursor()
    
    # Get last ID
    cursor.execute("SELECT MAX(id) FROM orders")
    last_id = cursor.fetchone()[0] or 10
    
    # Create 3 today orders
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
    
    orders = [
        ('BTCUSDT', 'BUY', 0.15, 'FILLED', now),
        ('BTCUSDT', 'SELL', 0.05, 'FILLED', now),
        ('ETHUSDT', 'BUY', 1.2, 'NEW', now)
    ]
    
    for i, (symbol, side, qty, status, dt) in enumerate(orders):
        new_id = last_id + i + 1
        client_oid = f"c_{uuid.uuid4().hex[:10]}"
        cursor.execute('''
            INSERT INTO orders (id, client_order_id, symbol, side, order_type, quantity, filled_qty, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (new_id, client_oid, symbol, side, 'MARKET', qty, qty if status == 'FILLED' else 0, status, dt, dt))
        
    conn.commit()
    print(f"Added {len(orders)} orders for today: {now}")
    conn.close()

if __name__ == "__main__":
    fix_orders()
