import sqlite3

conn = sqlite3.connect('data/trading.db')
cur = conn.cursor()
rows = cur.execute(
    """
    SELECT timestamp, trace_id, decision_type, status, execution_error, risk_approval_reason
    FROM decisions
    WHERE timestamp >= datetime('now', '-20 minutes')
      AND (status IN ('FAILED', 'REJECTED') OR execution_error IS NOT NULL)
    ORDER BY timestamp DESC
    LIMIT 30
    """
).fetchall()

print(f"rows={len(rows)}")
for r in rows:
    print(r)

conn.close()
