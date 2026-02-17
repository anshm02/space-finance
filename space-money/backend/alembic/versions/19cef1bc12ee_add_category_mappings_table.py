"""add_category_mappings_table

Revision ID: 19cef1bc12ee
Revises: 4f2ff4bedcb7
Create Date: 2026-02-08 15:58:45.507138

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '19cef1bc12ee'
down_revision = '4f2ff4bedcb7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create app_category_mappings table in public schema
    op.create_table(
        'app_category_mappings',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('lean_category', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=50), nullable=False),
        sa.Column('bucket', sa.String(length=20), nullable=False),
        sa.Column('display_order', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('is_income', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('exclude_from_expenses', sa.Boolean(), nullable=False, server_default='false'),
        sa.CheckConstraint("bucket IN ('fixed', 'flexible', 'savings')", name='ck_bucket_values'),
        sa.ForeignKeyConstraint(['user_id'], ['user.user_profiles.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'lean_category', name='uq_user_lean_category'),
    )
    
    # Add partial unique index for system defaults (NULL user_id)
    # PostgreSQL treats NULLs as distinct in regular unique constraints
    op.create_index(
        'uq_system_default_lean_category',
        'app_category_mappings',
        ['lean_category'],
        unique=True,
        postgresql_where=sa.text('user_id IS NULL')
    )
    
    # Seed system default categories (user_id = NULL)
    op.execute("""
        INSERT INTO app_category_mappings 
        (user_id, lean_category, display_name, bucket, display_order, is_income, exclude_from_expenses)
        VALUES
        (NULL, 'RENT_AND_SERVICES', 'Rent & Services', 'fixed', 1, false, false),
        (NULL, 'GOVERNMENT', 'Government', 'fixed', 2, false, false),
        (NULL, 'LOANS_AND_INVESTMENTS', 'Loans & Investments', 'fixed', 3, false, false),
        (NULL, 'GROCERIES', 'Groceries', 'flexible', 4, false, false),
        (NULL, 'HEALTH_AND_WELLBEING', 'Health & Wellbeing', 'flexible', 5, false, false),
        (NULL, 'RESTAURANTS_DINING', 'Restaurants & Dining', 'flexible', 6, false, false),
        (NULL, 'ENTERTAINMENT', 'Entertainment', 'flexible', 7, false, false),
        (NULL, 'RETAIL', 'Retail', 'flexible', 8, false, false),
        (NULL, 'SALARY_AND_REVENUE', 'Salary & Revenue', 'savings', 9, true, true),
        (NULL, 'TRANSFER', 'Transfer', 'savings', 10, false, true)
    """)


def downgrade() -> None:
    op.drop_table('app_category_mappings')
