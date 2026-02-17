"""add analytics pipeline tables

Revision ID: a7b8c9d0e1f2
Revises: 3c9e2f7785aa
Create Date: 2026-02-10 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = '3c9e2f7785aa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. derived_category_summaries
    op.create_table(
        'derived_category_summaries',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('period_month', sa.Date(), nullable=False),
        sa.Column('lean_category', sa.String(50), nullable=False),
        sa.Column('display_category', sa.String(50), nullable=True),
        sa.Column('bucket', sa.String(20), nullable=True),
        sa.Column('total_amount', sa.DECIMAL(12, 2), server_default='0', nullable=True),
        sa.Column('transaction_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('avg_transaction', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('max_transaction', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('min_transaction', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('prev_month_amount', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('pct_change_mom', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('rolling_3m_avg', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('rolling_6m_avg', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.user_profiles.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'period_month', 'lean_category', name='uq_category_summary_user_period_cat'),
        schema='public'
    )

    # 2. app_budgets
    op.create_table(
        'app_budgets',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('budget_amount', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('is_auto_generated', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint('budget_amount > 0', name='ck_budget_amount_positive'),
        sa.ForeignKeyConstraint(['user_id'], ['user.user_profiles.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    # Partial unique index: only one active budget per user/category
    op.create_index(
        'uq_active_user_category',
        'app_budgets',
        ['user_id', 'category'],
        unique=True,
        schema='public',
        postgresql_where=sa.text('is_active = true')
    )

    # 3. app_budget_periods
    op.create_table(
        'app_budget_periods',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('budget_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('period_month', sa.Date(), nullable=False),
        sa.Column('budget_amount', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('actual_amount', sa.DECIMAL(10, 2), server_default='0', nullable=True),
        sa.Column('remaining', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('utilization_pct', sa.DECIMAL(5, 2), server_default='0', nullable=True),
        sa.Column('daily_pace_remaining', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('days_remaining', sa.SmallInteger(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['budget_id'], ['public.app_budgets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.user_profiles.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('budget_id', 'period_month', name='uq_budget_period'),
        schema='public'
    )

    # 4. derived_recurring_transactions
    op.create_table(
        'derived_recurring_transactions',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('merchant_name', sa.String(255), nullable=False),
        sa.Column('lean_category', sa.String(50), nullable=True),
        sa.Column('recurrence_type', sa.String(20), nullable=True),
        sa.Column('typical_amount', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('amount_variance', sa.DECIMAL(10, 2), server_default='0', nullable=True),
        sa.Column('typical_day_of_month', sa.SmallInteger(), nullable=True),
        sa.Column('status', sa.String(20), server_default='active', nullable=True),
        sa.Column('classification', sa.String(20), server_default='unclassified', nullable=True),
        sa.Column('last_charge_date', sa.Date(), nullable=True),
        sa.Column('next_expected_date', sa.Date(), nullable=True),
        sa.Column('times_detected', sa.Integer(), server_default='1', nullable=True),
        sa.Column('times_paid_on_time', sa.Integer(), server_default='0', nullable=True),
        sa.Column('times_paid_late', sa.Integer(), server_default='0', nullable=True),
        sa.Column('times_missed', sa.Integer(), server_default='0', nullable=True),
        sa.Column('user_marked_keep', sa.Boolean(), nullable=True),
        sa.Column('first_detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('confidence', sa.DECIMAL(3, 2), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.user_profiles.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'merchant_name', 'recurrence_type', name='uq_recurring_user_merchant_type'),
        schema='public'
    )

    # 5. derived_health_scores
    op.create_table(
        'derived_health_scores',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('scored_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('period_month', sa.Date(), nullable=False),
        sa.Column('composite_score', sa.SmallInteger(), nullable=True),
        sa.Column('composite_label', sa.String(20), nullable=True),
        sa.Column('credit_utilization_score', sa.SmallInteger(), nullable=True),
        sa.Column('savings_rate_score', sa.SmallInteger(), nullable=True),
        sa.Column('budget_adherence_score', sa.SmallInteger(), nullable=True),
        sa.Column('bill_payment_score', sa.SmallInteger(), nullable=True),
        sa.Column('credit_utilization_pct', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('savings_rate_pct', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('budget_adherence_pct', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('bills_on_time_pct', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('prev_composite_score', sa.SmallInteger(), nullable=True),
        sa.Column('score_delta', sa.SmallInteger(), nullable=True),
        sa.Column('primary_change_driver', sa.String(50), nullable=True),
        sa.Column('risk_high_credit_utilization', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('risk_negative_cash_flow', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('risk_bill_delinquency', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('risk_lifestyle_creep', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.user_profiles.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'period_month', name='uq_health_score_user_period'),
        schema='public'
    )

    # 6. derived_health_score_drivers
    op.create_table(
        'derived_health_score_drivers',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('health_score_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('component_name', sa.String(50), nullable=False),
        sa.Column('current_sub_score', sa.SmallInteger(), nullable=True),
        sa.Column('previous_sub_score', sa.SmallInteger(), nullable=True),
        sa.Column('score_delta', sa.SmallInteger(), nullable=True),
        sa.Column('weighted_impact', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('explanation_text', sa.Text(), nullable=True),
        sa.Column('explanation_context', postgresql.JSONB(), nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['health_score_id'], ['public.derived_health_scores.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.user_profiles.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_index(
        'idx_drivers_health_score_id',
        'derived_health_score_drivers',
        ['health_score_id'],
        schema='public'
    )


def downgrade() -> None:
    op.drop_table('derived_health_score_drivers', schema='public')
    op.drop_table('derived_health_scores', schema='public')
    op.drop_table('derived_recurring_transactions', schema='public')
    op.drop_table('app_budget_periods', schema='public')
    op.drop_index('uq_active_user_category', table_name='app_budgets', schema='public')
    op.drop_table('app_budgets', schema='public')
    op.drop_table('derived_category_summaries', schema='public')
