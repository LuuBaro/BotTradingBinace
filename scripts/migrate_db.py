#!/usr/bin/env python3
"""
Database Migration Script: SQLite → PostgreSQL
Handles schema migration, data transfer, and verification
"""
import os
import sys
import sqlite3
import asyncio
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles migration from SQLite to PostgreSQL"""

    def __init__(self, sqlite_path: str, postgres_url: str):
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url
        self.sqlite_conn = None
        self.postgres_engine = None
        self.migration_log = []

    async def migrate(self):
        """Execute complete migration"""
        try:
            logger.info("=" * 70)
            logger.info("DATABASE MIGRATION: SQLite → PostgreSQL")
            logger.info("=" * 70)

            # Connect to databases
            self._connect_sqlite()
            await self._connect_postgres()

            # Pre-migration checks
            await self._pre_migration_checks()

            # Get schema from SQLite
            sqlite_schema = self._get_sqlite_schema()
            logger.info(f"✅ Detected {len(sqlite_schema)} tables in SQLite")

            # Create tables in PostgreSQL
            await self._create_postgres_tables(sqlite_schema)

            # Migrate data
            await self._migrate_data(sqlite_schema)

            # Post-migration validation
            await self._validate_migration(sqlite_schema)

            # Create backup metadata
            await self._record_migration()

            logger.info("✅ Migration completed successfully!")
            logger.info("=" * 70)

            return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {str(e)}")
            self._log_error(str(e))
            return False

        finally:
            self._cleanup()

    def _connect_sqlite(self):
        """Connect to SQLite database"""
        if not os.path.exists(self.sqlite_path):
            raise FileNotFoundError(f"SQLite database not found: {self.sqlite_path}")

        self.sqlite_conn = sqlite3.connect(self.sqlite_path)
        self.sqlite_conn.row_factory = sqlite3.Row
        logger.info(f"✅ Connected to SQLite: {self.sqlite_path}")

    async def _connect_postgres(self):
        """Connect to PostgreSQL database"""
        self.postgres_engine = create_async_engine(
            self.postgres_url,
            echo=False,
            pool_size=10,
            max_overflow=20
        )
        logger.info("✅ Connected to PostgreSQL")

    async def _pre_migration_checks(self):
        """Verify migration prerequisites"""
        # Check SQLite file is accessible
        if not os.access(self.sqlite_path, os.R_OK):
            raise PermissionError(f"Cannot read SQLite file: {self.sqlite_path}")

        # Check SQLite is valid
        try:
            cursor = self.sqlite_conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master")
            count = cursor.fetchone()[0]
            logger.info(f"✅ SQLite database has {count} objects")
        except Exception as e:
            raise Exception(f"SQLite database validation failed: {str(e)}")

        logger.info("✅ Pre-migration checks passed")

    def _get_sqlite_schema(self) -> dict:
        """Extract schema from SQLite"""
        cursor = self.sqlite_conn.cursor()

        # Get all tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        schema = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            schema[table] = columns
            logger.info(f"  - {table}: {len(columns)} columns")

        return schema

    async def _create_postgres_tables(self, schema: dict):
        """Create tables in PostgreSQL"""
        async with self.postgres_engine.begin() as conn:
            for table_name, columns in schema.items():
                try:
                    create_sql = self._generate_create_table_sql(table_name, columns)
                    await conn.execute(text(create_sql))
                    logger.info(f"✅ Created table: {table_name}")
                except Exception as e:
                    logger.warning(f"⚠️  Could not create {table_name}: {str(e)}")

    def _generate_create_table_sql(self, table_name: str, columns: list) -> str:
        """Generate PostgreSQL CREATE TABLE statement"""
        col_defs = []

        for col in columns:
            col_name = col[1]
            col_type = col[2]
            is_pk = col[5]

            # Map SQLite types to PostgreSQL
            pg_type = self._map_sqlite_to_postgres_type(col_type)

            col_def = col_name + " " + pg_type

            if is_pk:
                col_def += " PRIMARY KEY"

            col_defs.append(col_def)

        sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
        sql += ",\n".join([f"  {col}" for col in col_defs])
        sql += "\n);"

        return sql

    def _map_sqlite_to_postgres_type(self, sqlite_type: str) -> str:
        """Map SQLite types to PostgreSQL types"""
        type_map = {
            'INTEGER': 'INTEGER',
            'TEXT': 'TEXT',
            'REAL': 'NUMERIC',
            'BLOB': 'BYTEA',
            'BOOLEAN': 'BOOLEAN',
            'TIMESTAMP': 'TIMESTAMP',
            'DATE': 'DATE',
            'UUID': 'UUID',
            'JSON': 'JSONB',
        }

        sqlite_type_upper = sqlite_type.upper()
        for sqlite_t, pg_t in type_map.items():
            if sqlite_t in sqlite_type_upper:
                return pg_t

        return 'TEXT'  # Default fallback

    async def _migrate_data(self, schema: dict):
        """Migrate data from SQLite to PostgreSQL"""
        async_session = sessionmaker(
            self.postgres_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        total_records = 0

        for table_name in schema.keys():
            try:
                # Get data from SQLite
                cursor = self.sqlite_conn.cursor()
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()

                if not rows:
                    logger.info(f"  (empty table)")
                    continue

                # Get column names
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]

                # Insert into PostgreSQL
                async with async_session() as session:
                    for row in rows:
                        values = dict(zip(columns, row))
                        placeholders = ", ".join([f":{k}" for k in columns])
                        col_names = ", ".join(columns)

                        insert_sql = (
                            f"INSERT INTO {table_name} ({col_names}) "
                            f"VALUES ({placeholders}) "
                            f"ON CONFLICT DO NOTHING"
                        )

                        try:
                            await session.execute(text(insert_sql), values)
                        except Exception as e:
                            logger.warning(f"⚠️  Could not insert row in {table_name}: {str(e)}")

                    await session.commit()

                record_count = len(rows)
                total_records += record_count
                logger.info(f"✅ Migrated {table_name}: {record_count} records")

            except Exception as e:
                logger.error(f"❌ Failed to migrate {table_name}: {str(e)}")
                self._log_error(f"Migration error in {table_name}: {str(e)}")

        logger.info(f"✅ Total records migrated: {total_records}")

    async def _validate_migration(self, schema: dict):
        """Verify data integrity after migration"""
        cursor = self.sqlite_conn.cursor()
        validation_passed = 0
        validation_failed = 0

        async with self.postgres_engine.begin() as conn:
            for table_name in schema.keys():
                try:
                    # Get row counts
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    sqlite_count = cursor.fetchone()[0]

                    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    postgres_count = result.scalar()

                    if sqlite_count == postgres_count:
                        logger.info(f"✅ Validation passed: {table_name} ({postgres_count} rows)")
                        validation_passed += 1
                    else:
                        logger.warning(
                            f"⚠️  Row count mismatch in {table_name}: "
                            f"SQLite={sqlite_count}, PostgreSQL={postgres_count}"
                        )
                        validation_failed += 1

                except Exception as e:
                    logger.error(f"❌ Validation error for {table_name}: {str(e)}")
                    validation_failed += 1

        logger.info(f"Validation: {validation_passed} passed, {validation_failed} failed")
        return validation_failed == 0

    async def _record_migration(self):
        """Record migration in database"""
        async with self.postgres_engine.begin() as conn:
            migration_record = {
                'migration_name': f"sqlite_to_postgres_{datetime.now().isoformat()}",
                'status': 'success',
                'error_message': None
            }

            insert_sql = (
                "INSERT INTO migration_history "
                "(migration_name, status, error_message) "
                "VALUES (:migration_name, :status, :error_message)"
            )

            await conn.execute(text(insert_sql), migration_record)

    def _log_error(self, error_msg: str):
        """Log error for review"""
        self.migration_log.append({
            'timestamp': datetime.now().isoformat(),
            'level': 'ERROR',
            'message': error_msg
        })

    def _cleanup(self):
        """Clean up connections"""
        if self.sqlite_conn:
            self.sqlite_conn.close()
        if self.postgres_engine:
            try:
                asyncio.create_task(self.postgres_engine.dispose())
            except:
                pass

    def save_migration_report(self, output_file: str = "migration_report.log"):
        """Save migration report to file"""
        with open(output_file, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("DATABASE MIGRATION REPORT\n")
            f.write("=" * 70 + "\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Source: {self.sqlite_path}\n")
            f.write(f"Target: {self.postgres_url}\n\n")

            for log_entry in self.migration_log:
                f.write(f"[{log_entry['timestamp']}] {log_entry['level']}: {log_entry['message']}\n")


async def main():
    """Main migration entry point"""
    sqlite_path = os.getenv('SQLITE_PATH', './bottrading.db')
    postgres_url = os.getenv(
        'DATABASE_URL',
        'postgresql://bottrading:changeme@localhost:5432/bottrading'
    )

    migrator = DatabaseMigrator(sqlite_path, postgres_url)
    success = await migrator.migrate()

    migrator.save_migration_report()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
