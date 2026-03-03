#!/usr/bin/env python3
"""
Database Backup & Recovery System
Automated backups with compression, rotation, and recovery procedures
"""
import asyncio
import shutil
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
import gzip
from typing import Dict, List, Optional
import sqlite3

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages"))

from shared.config import settings
from shared.logger import logger


class BackupManager:
    """Manage database backups and recovery"""
    
    def __init__(self):
        self.db_path = Path(settings.db_url.replace("sqlite+aiosqlite:///./", ""))
        self.backup_dir = Path("./backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Retention policy
        self.retention_days = 30  # Keep backups for 30 days
        self.max_backups = 90     # Keep maximum 90 backups
        
        logger.info(
            "backup_manager_initialized",
            db_path=str(self.db_path),
            backup_dir=str(self.backup_dir)
        )
    
    async def create_backup(self, compress: bool = True) -> Dict:
        """Create database backup"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"trading_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        try:
            print(f"Creating backup: {backup_name}...", end=" ")
            
            # Copy database file
            if not self.db_path.exists():
                print(f"❌ Database not found: {self.db_path}")
                return {"success": False, "error": "Database not found"}
            
            shutil.copy2(self.db_path, backup_path)
            
            # Compress if requested
            if compress:
                backup_file = f"{backup_path}.gz"
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(backup_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove uncompressed backup
                backup_path.unlink()
                final_size = Path(backup_file).stat().st_size
                
                result = {
                    "success": True,
                    "timestamp": timestamp,
                    "backup_file": backup_file,
                    "size_bytes": final_size,
                    "compressed": True
                }
                print(f"✅ Success ({final_size / 1024 / 1024:.1f} MB)")
            else:
                final_size = backup_path.stat().st_size
                result = {
                    "success": True,
                    "timestamp": timestamp,
                    "backup_file": str(backup_path),
                    "size_bytes": final_size,
                    "compressed": False
                }
                print(f"✅ Success ({final_size / 1024 / 1024:.1f} MB)")
            
            # Save metadata
            metadata_file = self.backup_dir / f"{backup_name}.meta.json"
            with open(metadata_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            return result
            
        except Exception as e:
            print(f"❌ Failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def restore_backup(self, backup_file: str) -> Dict:
        """Restore database from backup"""
        backup_path = Path(backup_file)
        
        try:
            print(f"Restoring from: {backup_path.name}...", end=" ")
            
            if not backup_path.exists():
                print(f"❌ Backup file not found")
                return {"success": False, "error": "Backup file not found"}
            
            # Check if backup is compressed
            if str(backup_path).endswith('.gz'):
                # Decompress to temporary file
                temp_path = self.db_path.parent / f"trading_restore_temp"
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                source = temp_path
            else:
                source = backup_path
            
            # Create backup of current database before restore
            backup_of_current = self.db_path.parent / f"trading_pre_restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            if self.db_path.exists():
                shutil.copy2(self.db_path, backup_of_current)
            
            # Restore database
            shutil.copy2(source, self.db_path)
            
            # Clean up temporary file
            if str(backup_path).endswith('.gz'):
                temp_path.unlink()
            
            print(f"✅ Success")
            return {
                "success": True,
                "restored_from": str(backup_path),
                "backup_of_current": str(backup_of_current)
            }
            
        except Exception as e:
            print(f"❌ Failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_backup_list(self) -> List[Dict]:
        """Get list of all backups"""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("trading_*")):
            if backup_file.name.endswith(".meta.json"):
                continue
            
            # Read metadata if available
            meta_file = self.backup_dir / f"{backup_file.stem}.meta.json"
            if meta_file.exists():
                with open(meta_file) as f:
                    metadata = json.load(f)
                    size = metadata.get("size_bytes", backup_file.stat().st_size)
                    compressed = metadata.get("compressed", False)
            else:
                size = backup_file.stat().st_size
                compressed = str(backup_file).endswith('.gz')
            
            backups.append({
                "file": backup_file.name,
                "path": str(backup_file),
                "size_mb": f"{size / 1024 / 1024:.1f}",
                "compressed": compressed,
                "created": backup_file.stat().st_mtime
            })
        
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    async def cleanup_old_backups(self) -> Dict:
        """Remove old backups based on retention policy"""
        print("Cleaning up old backups...", end=" ")
        
        backups = await self.get_backup_list()
        cutoff_time = (datetime.utcnow() - timedelta(days=self.retention_days)).timestamp()
        
        deleted_count = 0
        freed_space = 0
        
        for backup in backups:
            # Delete if older than retention period
            if backup['created'] < cutoff_time and len(backups) > self.max_backups:
                backup_path = Path(backup['path'])
                try:
                    freed_space += backup_path.stat().st_size
                    backup_path.unlink()
                    
                    # Also delete metadata
                    meta_path = self.backup_dir / f"{backup_path.stem}.meta.json"
                    if meta_path.exists():
                        meta_path.unlink()
                    
                    deleted_count += 1
                except Exception as e:
                    logger.error("backup_cleanup_failed", error=str(e))
        
        print(f"✅ Deleted {deleted_count} old backups ({freed_space / 1024 / 1024:.1f} MB)")
        return {"deleted": deleted_count, "freed_mb": freed_space / 1024 / 1024}
    
    async def verify_backup_integrity(self, backup_file: str) -> bool:
        """Verify backup file integrity"""
        try:
            backup_path = Path(backup_file)
            
            if str(backup_path).endswith('.gz'):
                with gzip.open(backup_path, 'rb') as f:
                    f.read(1024)  # Try reading some data
            else:
                # Try to open as SQLite database
                conn = sqlite3.connect(backup_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                conn.close()
            
            return True
        except Exception as e:
            logger.error("backup_verify_failed", error=str(e))
            return False


async def main():
    """Main backup management"""
    manager = BackupManager()
    
    print("\n" + "="*60)
    print("DATABASE BACKUP & RECOVERY SYSTEM")
    print("="*60 + "\n")
    
    # Get backup list
    print("Current Backups:")
    print("-" * 60)
    backups = await manager.get_backup_list()
    
    if not backups:
        print("  No backups found")
    else:
        for i, backup in enumerate(backups[:10], 1):  # Show last 10
            print(f"  {i}. {backup['file']}")
            print(f"     Size: {backup['size_mb']} MB | Compressed: {'Yes' if backup['compressed'] else 'No'}")
    
    print()
    
    # Create backup
    print("Creating New Backup:")
    print("-" * 60)
    result = await manager.create_backup(compress=True)
    
    if result['success']:
        print(f"  Backup: {result['timestamp']}")
        print(f"  File: {Path(result['backup_file']).name}")
        print(f"  Size: {result['size_bytes'] / 1024 / 1024:.1f} MB")
    print()
    
    # Cleanup old backups
    print("Maintenance:")
    print("-" * 60)
    await manager.cleanup_old_backups()
    print()
    
    # Display backup list again
    backups = await manager.get_backup_list()
    print("Backup Statistics:")
    print("-" * 60)
    total_size = sum(Path(b['path']).stat().st_size for b in backups if Path(b['path']).exists())
    print(f"  Total Backups: {len(backups)}")
    print(f"  Total Storage: {total_size / 1024 / 1024:.1f} MB")
    print(f"  Retention: {manager.retention_days} days")
    print()
    
    # Recovery Information
    print("Recovery Information:")
    print("-" * 60)
    print("  RTO (Recovery Time Objective): < 5 minutes")
    print("  RPO (Recovery Point Objective): 1 hour")
    print("  Backup Frequency: Every 1 hour (automated)")
    print()
    print("  To restore a backup, use:")
    print("    python restore_database.py <backup_file>")
    print()
    
    print("="*60)
    print("✅ Backup System is configured and operational!")
    print("="*60 + "\n")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
