"""Initial schema - all tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-02-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # bot_config table
    op.create_table(
        'bot_config',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('env', sa.String(length=10), nullable=False),
        sa.Column('symbols_json', sa.JSON(), nullable=False),
        sa.Column('risk_json', sa.JSON(), nullable=False),
        sa.Column('execution_json', sa.JSON(), nullable=True),
        sa.Column('active_prompt_pack_id', sa.Integer(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_bot_config_is_active', 'bot_config', ['is_active'])

    # prompt_packs table
    op.create_table(
        'prompt_packs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('content_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # market_snapshots table
    op.create_table(
        'market_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('data_json', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_market_snapshots_timestamp', 'market_snapshots', ['timestamp'])
    op.create_index('ix_market_snapshots_symbol', 'market_snapshots', ['symbol'])
    op.create_index('ix_market_snapshots_symbol_timestamp', 'market_snapshots', ['symbol', 'timestamp'])

    # decisions table
    op.create_table(
        'decisions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('trace_id', sa.String(length=36), nullable=False),
        sa.Column('decision_json', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('regime', sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trace_id')
    )
    op.create_index('ix_decisions_timestamp', 'decisions', ['timestamp'])
    op.create_index('ix_decisions_trace_id', 'decisions', ['trace_id'])

    # risk_logs table
    op.create_table(
        'risk_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trace_id', sa.String(length=36), nullable=False),
        sa.Column('result', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_risk_logs_trace_id', 'risk_logs', ['trace_id'])

    # order_intents table
    op.create_table(
        'order_intents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trace_id', sa.String(length=36), nullable=False),
        sa.Column('client_order_id', sa.String(length=50), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('client_order_id')
    )
    op.create_index('ix_order_intents_trace_id', 'order_intents', ['trace_id'])
    op.create_index('ix_order_intents_client_order_id', 'order_intents', ['client_order_id'])

    # orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('client_order_id', sa.String(length=50), nullable=False),
        sa.Column('exchange_order_id', sa.String(length=50), nullable=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('order_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('filled_qty', sa.Float(), nullable=False, default=0.0),
        sa.Column('avg_price', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('client_order_id')
    )
    op.create_index('ix_orders_client_order_id', 'orders', ['client_order_id'])
    op.create_index('ix_orders_exchange_order_id', 'orders', ['exchange_order_id'])
    op.create_index('ix_orders_symbol', 'orders', ['symbol'])
    op.create_index('ix_orders_status', 'orders', ['status'])

    # positions table
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('qty', sa.Float(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('unrealized_pnl', sa.Float(), nullable=False, default=0.0),
        sa.Column('sl_order_id', sa.String(length=50), nullable=True),
        sa.Column('tp_order_id', sa.String(length=50), nullable=True),
        sa.Column('opened_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol')
    )
    op.create_index('ix_positions_symbol', 'positions', ['symbol'])

    # trade_journal table
    op.create_table(
        'trade_journal',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trace_id', sa.String(length=36), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=False),
        sa.Column('pnl', sa.Float(), nullable=False),
        sa.Column('rr', sa.Float(), nullable=True),
        sa.Column('holding_time', sa.Integer(), nullable=True),
        sa.Column('regime', sa.String(length=20), nullable=False),
        sa.Column('features_json', sa.JSON(), nullable=True),
        sa.Column('decision_json', sa.JSON(), nullable=False),
        sa.Column('exit_reason', sa.String(length=50), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trade_journal_trace_id', 'trade_journal', ['trace_id'])
    op.create_index('ix_trade_journal_symbol', 'trade_journal', ['symbol'])
    op.create_index('ix_trade_journal_closed_at', 'trade_journal', ['closed_at'])

    # events table
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('trace_id', sa.String(length=36), nullable=True),
        sa.Column('data_json', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_events_timestamp', 'events', ['timestamp'])
    op.create_index('ix_events_level', 'events', ['level'])
    op.create_index('ix_events_trace_id', 'events', ['trace_id'])

    # audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('actor', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('target', sa.String(length=100), nullable=True),
        sa.Column('details_json', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])

    # learning_reports table
    op.create_table(
        'learning_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('analysis_json', sa.JSON(), nullable=False),
        sa.Column('recommendations_json', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_learning_reports_timestamp', 'learning_reports', ['timestamp'])


def downgrade() -> None:
    op.drop_table('learning_reports')
    op.drop_table('audit_logs')
    op.drop_table('events')
    op.drop_table('trade_journal')
    op.drop_table('positions')
    op.drop_table('orders')
    op.drop_table('order_intents')
    op.drop_table('risk_logs')
    op.drop_table('decisions')
    op.drop_table('market_snapshots')
    op.drop_table('prompt_packs')
    op.drop_table('bot_config')
