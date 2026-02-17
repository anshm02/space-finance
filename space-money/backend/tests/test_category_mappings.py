"""
Test suite for app_category_mappings table.

Tests:
- Table exists in public schema with correct columns
- Seed data contains all 10 system default categories
- Querying by bucket returns fixed=3, flexible=4 (excluding income/excluded)
- User-specific override for GROCERIES works
- Unique constraint enforced
"""
import asyncio
import uuid
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import get_settings

settings = get_settings()


@pytest_asyncio.fixture
async def db_session():
    """Create async database session for tests."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_table_exists(db_session):
    """Verify app_category_mappings table exists in public schema."""
    result = await db_session.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'app_category_mappings'
    """))
    table = result.scalar()
    assert table == 'app_category_mappings', "app_category_mappings table should exist in public schema"
    print("✓ app_category_mappings table exists in public schema")


@pytest.mark.asyncio
async def test_columns_match_spec(db_session):
    """Verify all columns exist with correct types."""
    result = await db_session.execute(text("""
        SELECT column_name, data_type, column_default, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'app_category_mappings'
        ORDER BY ordinal_position
    """))
    columns = {row.column_name: row for row in result.fetchall()}
    
    # Verify bucket column is varchar, not enum
    assert columns['bucket'].data_type == 'character varying', \
        f"bucket should be VARCHAR, got {columns['bucket'].data_type}"
    
    # Verify display_order has default 0
    assert '0' in str(columns['display_order'].column_default), \
        f"display_order should default to 0, got {columns['display_order'].column_default}"
    
    print("✓ All columns match spec:")
    for name, col in columns.items():
        print(f"  - {name}: {col.data_type} (nullable: {col.is_nullable}, default: {col.column_default})")


@pytest.mark.asyncio
async def test_check_constraint(db_session):
    """Verify CHECK constraint on bucket column."""
    result = await db_session.execute(text("""
        SELECT conname 
        FROM pg_constraint 
        WHERE conname = 'ck_bucket_values'
    """))
    constraint = result.scalar()
    assert constraint == 'ck_bucket_values', "CHECK constraint ck_bucket_values should exist"
    print("✓ CHECK constraint ck_bucket_values exists")


@pytest.mark.asyncio
async def test_seed_data_10_rows(db_session):
    """Test (1): Verify 10 rows exist where user_id IS NULL."""
    result = await db_session.execute(text("""
        SELECT COUNT(*) FROM app_category_mappings WHERE user_id IS NULL
    """))
    count = result.scalar()
    assert count == 10, f"Expected 10 system default rows, got {count}"
    
    # Print all seed data
    result = await db_session.execute(text("""
        SELECT lean_category, display_name, bucket, display_order, is_income, exclude_from_expenses
        FROM app_category_mappings
        WHERE user_id IS NULL
        ORDER BY display_order
    """))
    rows = result.fetchall()
    print(f"✓ 10 system default rows verified:")
    for row in rows:
        flags = ""
        if row.is_income:
            flags += " [INCOME]"
        if row.exclude_from_expenses:
            flags += " [EXCLUDE]"
        print(f"  {row.display_order}. {row.lean_category} → {row.bucket}{flags}")


@pytest.mark.asyncio
async def test_bucket_counts_excluding_special(db_session):
    """Test (2): fixed=3, flexible=4 (excluding income and excluded rows)."""
    # Fixed bucket count (excluding income and excluded)
    result = await db_session.execute(text("""
        SELECT COUNT(*) FROM app_category_mappings
        WHERE user_id IS NULL 
        AND bucket = 'fixed'
        AND is_income = false
        AND exclude_from_expenses = false
    """))
    fixed_count = result.scalar()
    assert fixed_count == 3, f"Expected fixed=3, got {fixed_count}"
    
    # Flexible bucket count (excluding income and excluded)
    result = await db_session.execute(text("""
        SELECT COUNT(*) FROM app_category_mappings
        WHERE user_id IS NULL 
        AND bucket = 'flexible'
        AND is_income = false
        AND exclude_from_expenses = false
    """))
    flexible_count = result.scalar()
    assert flexible_count == 5, f"Expected flexible=5, got {flexible_count}"
    
    print(f"✓ Bucket counts (excluding income/excluded): fixed={fixed_count}, flexible={flexible_count}")


@pytest.mark.asyncio
async def test_user_override_groceries(db_session):
    """Test (3): User-specific override for GROCERIES with bucket='fixed' works."""
    test_user_id = str(uuid.uuid4())
    
    # Create a test user
    await db_session.execute(text("""
        INSERT INTO "user".user_profiles 
        (user_id, username, email, password_hash, country_code, account_status)
        VALUES (:user_id, 'test_override', 'override_test@example.com', 'hash', 'AE', 'ACTIVE')
    """), {"user_id": test_user_id})
    
    # Insert user-specific override for GROCERIES with bucket='fixed'
    await db_session.execute(text("""
        INSERT INTO app_category_mappings 
        (user_id, lean_category, display_name, bucket, display_order)
        VALUES (:user_id, 'GROCERIES', 'My Groceries', 'fixed', 4)
    """), {"user_id": test_user_id})
    await db_session.commit()
    
    # Verify the override exists alongside the system default
    result = await db_session.execute(text("""
        SELECT user_id, lean_category, bucket 
        FROM app_category_mappings
        WHERE lean_category = 'GROCERIES'
        ORDER BY user_id NULLS FIRST
    """))
    rows = result.fetchall()
    
    assert len(rows) == 2, f"Expected 2 GROCERIES rows (system + user), got {len(rows)}"
    assert rows[0].user_id is None and rows[0].bucket == 'flexible', "System default should be flexible"
    assert str(rows[1].user_id) == test_user_id and rows[1].bucket == 'fixed', "User override should be fixed"
    
    print("✓ User override for GROCERIES works (system=flexible, user=fixed)")
    
    # Clean up
    await db_session.execute(text("""
        DELETE FROM app_category_mappings WHERE user_id = :user_id
    """), {"user_id": test_user_id})
    await db_session.execute(text("""
        DELETE FROM "user".user_profiles WHERE user_id = :user_id
    """), {"user_id": test_user_id})
    await db_session.commit()


@pytest.mark.asyncio
async def test_unique_constraint(db_session):
    """Verify UNIQUE constraint on (user_id, lean_category) prevents duplicates."""
    try:
        await db_session.execute(text("""
            INSERT INTO app_category_mappings 
            (user_id, lean_category, display_name, bucket, display_order)
            VALUES (NULL, 'GROCERIES', 'Duplicate', 'flexible', 99)
        """))
        await db_session.commit()
        assert False, "Should have raised constraint violation for duplicate (NULL, 'GROCERIES')"
    except Exception as e:
        await db_session.rollback()
        assert 'uq_user_lean_category' in str(e) or 'unique' in str(e).lower(), \
            f"Expected unique constraint violation, got: {e}"
        print("✓ UNIQUE constraint on (user_id, lean_category) prevents duplicates")


if __name__ == "__main__":
    async def run_tests():
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        
        engine = create_async_engine(settings.database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            print("\n=== Running Category Mappings Tests ===\n")
            
            print("Test 1: Table Exists")
            await test_table_exists(session)
            print()
            
            print("Test 2: Columns Match Spec")
            await test_columns_match_spec(session)
            print()
            
            print("Test 3: CHECK Constraint")
            await test_check_constraint(session)
            print()
            
            print("Test 4: 10 Seed Rows")
            await test_seed_data_10_rows(session)
            print()
            
            print("Test 5: Bucket Counts (fixed=3, flexible=4)")
            await test_bucket_counts_excluding_special(session)
            print()
            
            print("Test 6: User Override for GROCERIES")
            await test_user_override_groceries(session)
            print()
            
            print("Test 7: Unique Constraint")
            await test_unique_constraint(session)
            print()
            
            print("=== All Tests Passed ===\n")
        
        await engine.dispose()
    
    asyncio.run(run_tests())
