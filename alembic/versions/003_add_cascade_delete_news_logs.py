"""Add CASCADE delete to news_logs.source_id foreign key

Revision ID: 003
Revises: 002
Create Date: 2026-03-04 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_cascade_delete'
down_revision = '002_add_binance_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade: Add CASCADE delete constraint"""
    # For SQLite, we need to recreate the table because SQLite doesn't support modifying foreign keys
    # For other databases (PostgreSQL, MySQL), we would use ALTER TABLE
    
    # Check database type
    dialect = op.get_context().dialect.name
    
    if dialect == 'sqlite':
        # SQLite approach: Create new table with CASCADE, copy data, drop old, rename
        op.execute('''
            CREATE TABLE news_logs_new (
                id INTEGER NOT NULL, 
                source_id INTEGER NOT NULL, 
                title VARCHAR(255), 
                content TEXT NOT NULL, 
                url VARCHAR(255), 
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                PRIMARY KEY (id), 
                FOREIGN KEY(source_id) REFERENCES news_sources (id) ON DELETE CASCADE
            )
        ''')
        
        # Copy data from old table
        op.execute('INSERT INTO news_logs_new SELECT * FROM news_logs')
        
        # Drop old table
        op.execute('DROP TABLE news_logs')
        
        # Rename new table
        op.execute('ALTER TABLE news_logs_new RENAME TO news_logs')
        
        # Recreate index
        op.execute('CREATE INDEX ix_news_logs_timestamp ON news_logs (timestamp)')
        
    elif dialect == 'postgresql':
        # PostgreSQL approach: ALTER TABLE
        op.drop_constraint('news_logs_source_id_fkey', 'news_logs', type_='foreignkey')
        op.create_foreign_key(
            'news_logs_source_id_fkey',
            'news_logs',
            'news_sources',
            ['source_id'],
            ['id'],
            ondelete='CASCADE'
        )
    elif dialect == 'mysql':
        # MySQL approach: ALTER TABLE
        op.drop_constraint('news_logs_ibfk_1', 'news_logs', type_='foreignkey')
        op.create_foreign_key(
            'news_logs_ibfk_1',
            'news_logs',
            'news_sources',
            ['source_id'],
            ['id'],
            ondelete='CASCADE'
        )


def downgrade() -> None:
    """Downgrade: Remove CASCADE delete constraint"""
    dialect = op.get_context().dialect.name
    
    if dialect == 'sqlite':
        # SQLite approach: Recreate table without CASCADE
        op.execute('''
            CREATE TABLE news_logs_new (
                id INTEGER NOT NULL, 
                source_id INTEGER NOT NULL, 
                title VARCHAR(255), 
                content TEXT NOT NULL, 
                url VARCHAR(255), 
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                PRIMARY KEY (id), 
                FOREIGN KEY(source_id) REFERENCES news_sources (id)
            )
        ''')
        
        op.execute('INSERT INTO news_logs_new SELECT * FROM news_logs')
        op.execute('DROP TABLE news_logs')
        op.execute('ALTER TABLE news_logs_new RENAME TO news_logs')
        op.execute('CREATE INDEX ix_news_logs_timestamp ON news_logs (timestamp)')
        
    elif dialect == 'postgresql':
        op.drop_constraint('news_logs_source_id_fkey', 'news_logs', type_='foreignkey')
        op.create_foreign_key(
            'news_logs_source_id_fkey',
            'news_logs',
            'news_sources',
            ['source_id'],
            ['id']
        )
    elif dialect == 'mysql':
        op.drop_constraint('news_logs_ibfk_1', 'news_logs', type_='foreignkey')
        op.create_foreign_key(
            'news_logs_ibfk_1',
            'news_logs',
            'news_sources',
            ['source_id'],
            ['id']
        )
