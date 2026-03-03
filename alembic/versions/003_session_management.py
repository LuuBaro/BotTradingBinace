"""add session management fields for Phase 8"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


def upgrade():
    # Add columns to users table for session management
    op.add_column('users', sa.Column('bot_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('last_session_token', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('last_session_refresh_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('session_expiry_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('auto_close_on_logout', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('grace_period_minutes', sa.Integer(), nullable=False, server_default='15'))
    op.add_column('users', sa.Column('graceful_exit_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_bot_activity_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('bot_paused_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('bot_pause_reason', sa.String(255), nullable=True))
    
    # Create indices for performance
    op.create_index('ix_session_expiry', 'users', ['session_expiry_at'])
    op.create_index('ix_last_activity', 'users', ['last_bot_activity_at'])
    op.create_index('ix_bot_enabled', 'users', ['bot_enabled'])
    
    # Create session_logs table
    op.create_table(
        'session_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('session_token', sa.String(500), nullable=False),
        sa.Column('login_at', sa.DateTime(), nullable=False),
        sa.Column('logout_at', sa.DateTime(), nullable=True),
        sa.Column('expired_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='ACTIVE'),
        sa.Column('positions_at_logout', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('action_taken', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_session_user_id', 'user_id'),
        sa.Index('ix_session_expired_at', 'expired_at'),
        sa.Index('ix_session_status', 'status')
    )
    
    # Create quota_logs table
    op.create_table(
        'quota_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('request_type', sa.String(50), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_quota_user_provider', 'user_id', 'provider'),
        sa.Index('ix_quota_timestamp', 'timestamp'),
        sa.Index('ix_quota_provider', 'provider')
    )
    
    # Create recommendation_approval_logs table
    op.create_table(
        'recommendation_approval_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('recommendation_type', sa.String(100), nullable=False),
        sa.Column('safety_category', sa.String(20), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by', sa.String(50), nullable=True),
        sa.Column('previous_config', sa.JSON(), nullable=True),
        sa.Column('current_config', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.GrammarExceptionColumns('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_recommend_user_id', 'user_id'),
        sa.Index('ix_recommend_status', 'status'),
        sa.Index('ix_recommend_created_at', 'created_at')
    )


def downgrade():
    # Drop tables
    op.drop_table('recommendation_approval_logs')
    op.drop_table('quota_logs')
    op.drop_table('session_logs')
    
    # Drop indices
    op.drop_index('ix_bot_enabled', table_name='users')
    op.drop_index('ix_last_activity', table_name='users')
    op.drop_index('ix_session_expiry', table_name='users')
    
    # Drop columns
    op.drop_column('users', 'bot_pause_reason')
    op.drop_column('users', 'bot_paused_at')
    op.drop_column('users', 'last_bot_activity_at')
    op.drop_column('users', 'graceful_exit_at')
    op.drop_column('users', 'grace_period_minutes')
    op.drop_column('users', 'auto_close_on_logout')
    op.drop_column('users', 'session_expiry_at')
    op.drop_column('users', 'last_session_refresh_at')
    op.drop_column('users', 'last_session_token')
    op.drop_column('users', 'bot_enabled')
