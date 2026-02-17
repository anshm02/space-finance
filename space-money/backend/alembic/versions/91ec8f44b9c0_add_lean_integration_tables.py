"""add lean integration tables

Revision ID: 91ec8f44b9c0
Revises: ef07c16c97aa
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

# revision identifiers, used by Alembic.
revision = '91ec8f44b9c0'
down_revision = 'ef07c16c97aa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create legacy Lean integration tables in transactions schema
    # These tables support the existing Lean API integration
    
    # users table (for backward compatibility with Lean integration)
    op.create_table(
        'users',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('email', sa.String(), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        schema='transactions'
    )
    
    # lean_customers table
    op.create_table(
        'lean_customers',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('customer_id', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('app_user_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['user_id'], ['transactions.users.id']),
        schema='transactions'
    )
    
    # lean_entities table
    op.create_table(
        'lean_entities',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('customer_id', sa.String(), nullable=False, index=True),
        sa.Column('entity_id', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('bank_identifier', sa.String()),
        sa.Column('status', sa.String(), server_default='PENDING'),
        sa.Column('permissions', JSON),
        sa.Column('last_synced_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['customer_id'], ['transactions.lean_customers.id']),
        schema='transactions'
    )
    
    # lean_accounts table
    op.create_table(
        'lean_accounts',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('entity_id', sa.String(), nullable=False, index=True),
        sa.Column('account_id', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('account_number', sa.String()),
        sa.Column('account_type', sa.String()),
        sa.Column('currency', sa.String()),
        sa.Column('balance', sa.String()),
        sa.Column('available_balance', sa.String()),
        sa.Column('raw_data', JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['entity_id'], ['transactions.lean_entities.id']),
        schema='transactions'
    )
    
    # lean_sync_logs table
    op.create_table(
        'lean_sync_logs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('entity_id', sa.String(), nullable=False, index=True),
        sa.Column('sync_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('file_path', sa.String()),
        sa.Column('error_message', sa.String()),
        sa.Column('records_count', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['entity_id'], ['transactions.lean_entities.id']),
        schema='transactions'
    )
    
    # balance_history table
    op.create_table(
        'balance_history',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('account_id', sa.String(), nullable=False, index=True),
        sa.Column('entity_id', sa.String(), nullable=False, index=True),
        sa.Column('balance', sa.String(), nullable=False),
        sa.Column('available_balance', sa.String()),
        sa.Column('currency_code', sa.String()),
        sa.Column('account_name', sa.String()),
        sa.Column('account_type', sa.String()),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), index=True),
        sa.Column('raw_data', JSON),
        sa.ForeignKeyConstraint(['entity_id'], ['transactions.lean_entities.id']),
        schema='transactions'
    )
    
    # recurring_transactions table
    op.create_table(
        'recurring_transactions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('account_id', sa.String(), nullable=False, index=True),
        sa.Column('entity_id', sa.String(), nullable=False, index=True),
        sa.Column('merchant_name', sa.String(), nullable=False),
        sa.Column('category', sa.String()),
        sa.Column('frequency', sa.String()),
        sa.Column('average_amount', sa.String()),
        sa.Column('currency_code', sa.String()),
        sa.Column('last_transaction_date', sa.DateTime(timezone=True)),
        sa.Column('predicted_next_date', sa.DateTime(timezone=True)),
        sa.Column('transaction_count', sa.Integer(), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('confidence_score', sa.String()),
        sa.Column('transaction_ids', JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['entity_id'], ['transactions.lean_entities.id']),
        schema='transactions'
    )


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('recurring_transactions', schema='transactions')
    op.drop_table('balance_history', schema='transactions')
    op.drop_table('lean_sync_logs', schema='transactions')
    op.drop_table('lean_accounts', schema='transactions')
    op.drop_table('lean_entities', schema='transactions')
    op.drop_table('lean_customers', schema='transactions')
    op.drop_table('users', schema='transactions')
