#!/usr/bin/env python3
"""
Database Backup & Restore System
Handles full/incremental backups, restore, and verification
"""
import os
import sys
import gzip
import json
import subprocess
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """Handles database backups"""

    def __init__(self, postgres_url: str, backup_dir: str = "./backups"):
        self.postgres_url = postgres_url
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.engine = None

    async def full_backup(self) -> bool:
        """Execute full database backup"""
        try:
            logger.info("=" * 70)
            logger.info("FULL DATABASE BACKUP")
            logger.info("=" * 70)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"backup_full_{timestamp}.sql.gz"
            metadata_file = self.backup_dir / f"backup_full_{timestamp}.json"

            # Extract connection details from DATABASE_URL
            # postgresql://user:password@host:port/database
            db_url_parts = self.postgres_url.replace('postgresql://', '').split('@')
            user_pass = db_url_parts[0]
            host_port_db = db_url_parts[1]
            user = user_pass.split(':')[0]
            password = user_pass.split(':')[1] if ':' in user_pass else ''
            host = host_port_db.split(':')[0]
            port = host_port_db.split(':')[1].split('/')[0] if ':' in host_port_db else '5432'
            database = host_port_db.split('/')[-1]

            # Create backup using pg_dump
            logger.info(f"Dumping database: {database}...")

            env = os.environ.copy()
            if password:
                env['PGPASSWORD'] = password

            cmd = [
                'pg_dump',
                '-h', host,
                '-p', port,
                '-U', user,
                '-d', database,
                '--verbose',
                '--disable-triggers',
                '--format=plain'
            ]

            with gzip.open(backup_file, 'wb') as gz_file:
                result = subprocess.run(
                    cmd,
                    stdout=gz_file,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True
                )

            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")

            # Record backup metadata
            backup_size = backup_file.stat().st_size
            metadata = {
                'backup_name': backup_file.name,
                'backup_type': 'full',
                'backup_time': datetime.now().isoformat(),
                'backup_size': backup_size,
                'status': 'completed',
                'database': database,
                'compressed': True
            }

            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            # Record in database
            await self._record_backup_metadata(metadata)

            logger.info(f"✅ Backup completed: {backup_file.name}")
            logger.info(f"   Size: {backup_size / (1024*1024):.2f} MB")
            logger.info(f"   Location: {backup_file}")

            return True

        except Exception as e:
            logger.error(f"❌ Backup failed: {str(e)}")
            return False

    async def incremental_backup(self) -> bool:
        """Execute incremental backup (WAL archiving)"""
        try:
            logger.info("Incremental backup not yet implemented")
            return False

        except Exception as e:
            logger.error(f"❌ Incremental backup failed: {str(e)}")
            return False

    async def restore_backup(self, backup_file: str) -> bool:
        """Restore database from backup"""
        try:
            logger.info("=" * 70)
            logger.info("DATABASE RESTORE")
            logger.info("=" * 70)

            backup_path = Path(backup_file)
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_file}")

            # Extract connection details
            db_url_parts = self.postgres_url.replace('postgresql://', '').split('@')
            user_pass = db_url_parts[0]
            host_port_db = db_url_parts[1]
            user = user_pass.split(':')[0]
            password = user_pass.split(':')[1] if ':' in user_pass else ''
            host = host_port_db.split(':')[0]
            port = host_port_db.split(':')[1].split('/')[0] if ':' in host_port_db else '5432'
            database = host_port_db.split('/')[-1]

            logger.info(f"Restoring to database: {database}")
            logger.warning("⚠️  This will overwrite existing data!")

            # Confirmation
            response = input("Type 'CONFIRM' to proceed with restore: ")
            if response != 'CONFIRM':
                logger.info("Restore cancelled")
                return False

            # Drop and recreate database
            logger.info("Dropping existing database...")
            await self._drop_and_recreate_database(host, port, user, password, database)

            # Restore from backup
            logger.info("Restoring from backup...")
            env = os.environ.copy()
            if password:
                env['PGPASSWORD'] = password

            # Detect if file is gzipped
            if backup_path.suffix == '.gz':
                with gzip.open(backup_path, 'rb') as gz_file:
                    cmd = [
                        'psql',
                        '-h', host,
                        '-p', port,
                        '-U', user,
                        '-d', database
                    ]

                    result = subprocess.run(
                        cmd,
                        stdin=gz_file,
                        stderr=subprocess.PIPE,
                        env=env,
                        text=True
                    )
            else:
                cmd = [
                    'psql',
                    '-h', host,
                    '-p', port,
                    '-U', user,
                    '-d', database,
                    '-f', str(backup_path)
                ]

                result = subprocess.run(
                    cmd,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True
                )

            if result.returncode != 0:
                raise Exception(f"Restore failed: {result.stderr}")

            logger.info("✅ Restore completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Restore failed: {str(e)}")
            return False

    async def _drop_and_recreate_database(self, host: str, port: str, user: str, password: str, database: str):
        """Drop and recreate database"""
        env = os.environ.copy()
        if password:
            env['PGPASSWORD'] = password

        # Connect to postgres database
        cmd = [
            'psql',
            '-h', host,
            '-p', port,
            '-U', user,
            '-d', 'postgres',
            '-c', f'DROP DATABASE IF EXISTS {database};'
        ]

        subprocess.run(cmd, env=env, capture_output=True)

        cmd = [
            'psql',
            '-h', host,
            '-p', port,
            '-U', user,
            '-d', 'postgres',
            '-c', f'CREATE DATABASE {database};'
        ]

        result = subprocess.run(cmd, env=env, capture_output=True)
        if result.returncode != 0:
            raise Exception(f"Failed to recreate database: {result.stderr.decode()}")

    async def _record_backup_metadata(self, metadata: dict):
        """Record backup metadata in database"""
        try:
            self.engine = create_async_engine(self.postgres_url)
            async_session = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            async with async_session() as session:
                insert_sql = (
                    "INSERT INTO backup_metadata "
                    "(backup_name, backup_size, backup_type, status, version) "
                    "VALUES (:backup_name, :backup_size, :backup_type, :status, :version)"
                )

                await session.execute(text(insert_sql), {
                    'backup_name': metadata['backup_name'],
                    'backup_size': metadata['backup_size'],
                    'backup_type': metadata['backup_type'],
                    'status': metadata['status'],
                    'version': '1.0'
                })

                await session.commit()

        except Exception as e:
            logger.warning(f"⚠️  Could not record backup metadata: {str(e)}")

    def list_backups(self) -> list:
        """List all available backups"""
        backups = list(self.backup_dir.glob('backup_*.sql.gz'))
        backups.sort(reverse=True)

        logger.info("Available backups:")
        for i, backup in enumerate(backups, 1):
            size_mb = backup.stat().st_size / (1024*1024)
            mod_time = datetime.fromtimestamp(backup.stat().st_mtime)
            logger.info(f"  {i}. {backup.name} ({size_mb:.2f} MB) - {mod_time}")

        return backups

    def cleanup_old_backups(self, keep_days: int = 30, keep_count: int = 5):
        """Clean up old backup files"""
        logger.info(f"Cleaning up backups older than {keep_days} days (keep at least {keep_count})")

        backups = sorted(self.backup_dir.glob('backup_*.sql.gz'), reverse=True)

        cutoff_date = datetime.now() - timedelta(days=keep_days)

        removed = 0
        for backup in backups[keep_count:]:
            mod_time = datetime.fromtimestamp(backup.stat().st_mtime)
            if mod_time < cutoff_date:
                backup.unlink()
                removed += 1
                logger.info(f"  Removed: {backup.name}")

        logger.info(f"✅ Removed {removed} old backups")


async def main():
    """Main backup entry point"""
    postgres_url = os.getenv(
        'DATABASE_URL',
        'postgresql://bottrading:changeme@localhost:5432/bottrading'
    )
    backup_dir = os.getenv('BACKUP_DIR', './backups')

    backup_system = DatabaseBackup(postgres_url, backup_dir)

    if len(sys.argv) < 2:
        print("Usage: python backup_restore.py [backup|restore|list|cleanup]")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'backup':
        success = await backup_system.full_backup()
        sys.exit(0 if success else 1)

    elif command == 'restore':
        if len(sys.argv) < 3:
            print("Usage: python backup_restore.py restore <backup_file>")
            sys.exit(1)
        success = await backup_system.restore_backup(sys.argv[2])
        sys.exit(0 if success else 1)

    elif command == 'list':
        backup_system.list_backups()

    elif command == 'cleanup':
        keep_days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        keep_count = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        backup_system.cleanup_old_backups(keep_days, keep_count)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
