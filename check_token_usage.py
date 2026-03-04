from sqlalchemy import create_engine, text
from datetime import datetime

DB_URL = 'sqlite:///./data/trading.db'
engine = create_engine(DB_URL)

with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT COUNT(*), SUM(tokens_used) FROM decisions 
        WHERE DATE(timestamp) = DATE('now') AND tokens_used IS NOT NULL
    '''))
    count, total = result.fetchone()
    print(f"\n📊 Today's decisions with actual tokens from OpenAI:")
    print(f"   Count: {count or 0}")
    print(f"   Total tokens: {total or 0}\n")
