#!/usr/bin/env python
"""Run Alembic migration for CASCADE delete"""
from alembic.config import Config
from alembic import command
import sys

try:
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    print("✅ Migration successful!")
except Exception as e:
    print(f"❌ Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
