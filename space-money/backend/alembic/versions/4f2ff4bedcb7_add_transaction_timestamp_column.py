"""add_transaction_timestamp_column

Revision ID: 4f2ff4bedcb7
Revises: 91ec8f44b9c0
Create Date: 2026-02-08 15:10:32.679308

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f2ff4bedcb7'
down_revision = '91ec8f44b9c0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add transaction_timestamp column to transactions.raw_transactions
    op.add_column(
        'raw_transactions',
        sa.Column('transaction_timestamp', sa.DateTime(timezone=True), nullable=True),
        schema='transactions'
    )


def downgrade() -> None:
    # Remove transaction_timestamp column
    op.drop_column('raw_transactions', 'transaction_timestamp', schema='transactions')
