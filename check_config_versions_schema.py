#!/usr/bin/env python3
"""Check exact schema of config_versions table."""

import sqlite3
from pathlib import Path

db_path = Path("./data/trading.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Columns in config_versions table:")
cursor.execute("PRAGMA table_info(config_versions)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col}")

print("\nActual data:")
cursor.execute("SELECT * FROM config_versions LIMIT 1")
row = cursor.fetchone()
if row:
    print(f"  Columns: {[desc[0] for desc in cursor.description]}")
    print(f"  Values: {row}")

conn.close()
