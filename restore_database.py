#!/usr/bin/env python3
"""
Database Restore Utility
Restore database from backup with verification
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages"))

from shared.logger import logger


async def restore_database(backup_file: str) -> int:
    """Restore database from backup"""
    # Import after path setup
    from backup_database import BackupManager
    
    print("\n" + "="*60)
    print("DATABASE RESTORE UTILITY")
    print("="*60 + "\n")
    
    manager = BackupManager()
    
    print(f"Backup File: {backup_file}")
    print()
    
    # Check if backup exists
    backup_path = Path(backup_file)
    if not backup_path.exists():
        # Try finding in backups directory
        backup_in_dir = manager.backup_dir / backup_file
        if backup_in_dir.exists():
            backup_path = backup_in_dir
        else:
            print(f"❌ ERROR: Backup file not found: {backup_file}")
            return 1
    
    # Verify backup integrity
    print("Verifying backup integrity...", end=" ")
    is_valid = await manager.verify_backup_integrity(str(backup_path))
    if is_valid:
        print("✅ Valid")
    else:
        print("❌ Invalid or corrupted")
        return 1
    
    print()
    
    # Warn about current database
    print("⚠️  WARNING: This will overwrite the current database!")
    print(f"   Current DB: {manager.db_path}")
    print(f"   Restore from: {backup_path}")
    print()
    
    # Confirm restore
    response = input("Type 'RESTORE' to confirm, or 'CANCEL' to abort: ").strip().upper()
    if response != "RESTORE":
        print("\n❌ Restore cancelled")
        return 1
    
    print()
    
    # Perform restore
    result = await manager.restore_backup(str(backup_path))
    
    if result['success']:
        print(f"\n✅ Database restored successfully!")
        print(f"   Restored from: {result['restored_from']}")
        print(f"   Backup of current: {result['backup_of_current']}")
        print()
        print("Current database has been backed up to:")
        print(f"   {result['backup_of_current']}")
        return 0
    else:
        print(f"\n❌ Restore failed: {result['error']}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python restore_database.py <backup_file>")
        print("Example: python restore_database.py backups/trading_20240101_120000.gz")
        sys.exit(1)
    
    backup_file = sys.argv[1]
    exit_code = asyncio.run(restore_database(backup_file))
    sys.exit(exit_code)
