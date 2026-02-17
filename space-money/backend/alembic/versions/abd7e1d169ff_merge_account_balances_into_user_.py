"""merge_account_balances_into_user_accounts

Revision ID: abd7e1d169ff
Revises: 02b9ac33af90
Create Date: 2026-02-09 18:53:10.510626

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'abd7e1d169ff'
down_revision = '02b9ac33af90'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add balance columns to accounts.user_accounts
    op.add_column(
        'user_accounts',
        sa.Column('current_balance', sa.DECIMAL(precision=12, scale=2), nullable=True),
        schema='accounts'
    )
    op.add_column(
        'user_accounts',
        sa.Column('balance_updated_at', sa.DateTime(timezone=True), nullable=True),
        schema='accounts'
    )
    
    # Migrate latest balance from account_balances to user_accounts
    # Uses DISTINCT ON to get the most recent balance for each account
    op.execute("""
        UPDATE accounts.user_accounts
        SET current_balance = ab.balance,
            balance_updated_at = ab.snapshot_timestamp
        FROM (
            SELECT DISTINCT ON (account_id)
                account_id, balance, snapshot_timestamp
            FROM accounts.account_balances
            ORDER BY account_id, snapshot_timestamp DESC
        ) ab
        WHERE user_accounts.account_id = ab.account_id
    """)
    
    # Drop the account_balances table
    op.drop_index('idx_account_balances_account_timestamp', table_name='account_balances', schema='accounts', postgresql_ops={'snapshot_timestamp': 'DESC'})
    op.drop_table('account_balances', schema='accounts')


def downgrade() -> None:
    # Recreate account_balances table
    op.create_table('account_balances',
        sa.Column('balance_id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('snapshot_timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('balance', sa.DECIMAL(precision=12, scale=2), nullable=False),
        sa.Column('currency_code', sa.String(length=3), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.user_accounts.account_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('balance_id'),
        schema='accounts'
    )
    op.create_index('idx_account_balances_account_timestamp', 'account_balances', ['account_id', 'snapshot_timestamp'], unique=False, schema='accounts', postgresql_ops={'snapshot_timestamp': 'DESC'})
    
    # Migrate data back from user_accounts to account_balances
    op.execute("""
        INSERT INTO accounts.account_balances (balance_id, account_id, snapshot_timestamp, balance, currency_code)
        SELECT 
            gen_random_uuid(),
            account_id,
            balance_updated_at,
            current_balance,
            currency_code
        FROM accounts.user_accounts
        WHERE current_balance IS NOT NULL AND balance_updated_at IS NOT NULL
    """)
    
    # Drop columns from user_accounts
    op.drop_column('user_accounts', 'balance_updated_at', schema='accounts')
    op.drop_column('user_accounts', 'current_balance', schema='accounts')
