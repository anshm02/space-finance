"""add derived_monthly_summaries table

Revision ID: 3c9e2f7785aa
Revises: abd7e1d169ff
Create Date: 2026-02-09 20:06:12.390317

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3c9e2f7785aa'
down_revision = 'abd7e1d169ff'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'derived_monthly_summaries',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('period_month', sa.Date(), nullable=False),
        sa.Column('total_income', sa.DECIMAL(precision=12, scale=2), server_default='0', nullable=False),
        sa.Column('total_expenses', sa.DECIMAL(precision=12, scale=2), server_default='0', nullable=False),
        sa.Column('net_savings', sa.DECIMAL(precision=12, scale=2), server_default='0', nullable=False),
        sa.Column('savings_rate', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('total_fixed', sa.DECIMAL(precision=12, scale=2), server_default='0', nullable=False),
        sa.Column('total_flexible', sa.DECIMAL(precision=12, scale=2), server_default='0', nullable=False),
        sa.Column('total_savings_allocated', sa.DECIMAL(precision=12, scale=2), server_default='0', nullable=False),
        sa.Column('fixed_pct', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('flexible_pct', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('savings_pct', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('transaction_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('income_transaction_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('expense_transaction_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.user_profiles.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'period_month', name='uq_monthly_summary_user_period'),
        schema='public'
    )


def downgrade() -> None:
    op.drop_table('derived_monthly_summaries', schema='public')
