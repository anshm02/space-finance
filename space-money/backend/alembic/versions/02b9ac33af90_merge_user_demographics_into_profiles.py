"""merge_user_demographics_into_profiles

Revision ID: 02b9ac33af90
Revises: 19cef1bc12ee
Create Date: 2026-02-09 14:03:52.717395

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '02b9ac33af90'
down_revision = '19cef1bc12ee'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add demographic columns to user.user_profiles
    op.add_column(
        'user_profiles',
        sa.Column('age', sa.Integer(), nullable=True),
        schema='user'
    )
    op.add_column(
        'user_profiles',
        sa.Column('sex', sa.Enum('male', 'female', 'other', 'prefer_not_to_say', name='sex_enum', create_type=False), nullable=True),
        schema='user'
    )
    op.add_column(
        'user_profiles',
        sa.Column('income_estimate', sa.DECIMAL(precision=10, scale=2), nullable=True),
        schema='user'
    )
    op.add_column(
        'user_profiles',
        sa.Column('income_source', sa.Enum('user_provided', 'auto_detected', name='income_source_enum', create_type=False), nullable=True),
        schema='user'
    )
    
    # Add CHECK constraint for age (18-100)
    op.create_check_constraint(
        'age_check',
        'user_profiles',
        'age >= 18 AND age <= 100',
        schema='user'
    )
    
    # Drop user_demographics table
    op.drop_table('user_demographics', schema='user')


def downgrade() -> None:
    # Recreate user_demographics table
    op.create_table(
        'user_demographics',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('sex', sa.Enum('male', 'female', 'other', 'prefer_not_to_say', name='sex_enum', create_type=False), nullable=True),
        sa.Column('income_estimate', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('income_source', sa.Enum('user_provided', 'auto_detected', name='income_source_enum', create_type=False), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint('age >= 18 AND age <= 100', name='age_check'),
        sa.CheckConstraint('income_estimate >= 0', name='income_estimate_check'),
        sa.ForeignKeyConstraint(['user_id'], ['user.user_profiles.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
        schema='user'
    )
    
    # Drop CHECK constraint and columns from user_profiles
    op.drop_constraint('age_check', 'user_profiles', schema='user', type_='check')
    op.drop_column('user_profiles', 'income_source', schema='user')
    op.drop_column('user_profiles', 'income_estimate', schema='user')
    op.drop_column('user_profiles', 'sex', schema='user')
    op.drop_column('user_profiles', 'age', schema='user')

