#!/usr/bin/env python3
import sqlite3

db_path = './data/trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get schema
cursor.execute("PRAGMA table_info(decisions)")
columns = cursor.fetchall()
print("Decisions table columns:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

print("\nDecision count:")
cursor.execute("SELECT COUNT(*) FROM decisions")
print(f"  Total: {cursor.fetchone()[0]}")

print("\nSignals table columns:")
cursor.execute("PRAGMA table_info(signals)")
columns = cursor.fetchall()
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

print("\nSignal count:")
cursor.execute("SELECT COUNT(*) FROM signals")
print(f"  Total: {cursor.fetchone()[0]}")

conn.close()
