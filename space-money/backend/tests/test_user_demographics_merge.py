"""
Test suite for user_demographics merge into user_profiles.

Tests:
- user_demographics table no longer exists
- New columns exist on user_profiles (age, sex, income_estimate, income_source)
- Age CHECK constraint enforces 18-100 range
- All new columns are nullable
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
async def test_user_demographics_table_dropped(db_session):
    """Verify user_demographics table no longer exists."""
    result = await db_session.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'user' AND table_name = 'user_demographics'
    """))
    table = result.scalar()
    assert table is None, "user_demographics table should not exist after migration"
    print("✓ user_demographics table successfully dropped")


@pytest.mark.asyncio
async def test_new_columns_exist_on_user_profiles(db_session):
    """Verify the 4 new demographic columns exist on user_profiles."""
    result = await db_session.execute(text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'user' 
        AND table_name = 'user_profiles'
        AND column_name IN ('age', 'sex', 'income_estimate', 'income_source')
        ORDER BY column_name
    """))
    columns = result.fetchall()
    
    # Verify we got exactly 4 columns
    assert len(columns) == 4, f"Expected 4 demographic columns, got {len(columns)}"
    
    # Verify column names
    column_names = {col.column_name for col in columns}
    expected_columns = {'age', 'sex', 'income_estimate', 'income_source'}
    assert column_names == expected_columns, f"Expected columns {expected_columns}, got {column_names}"
    
    print("✓ All 4 demographic columns exist on user_profiles:")
    for col in columns:
        print(f"  - {col.column_name}: {col.data_type} (nullable: {col.is_nullable})")


@pytest.mark.asyncio
async def test_age_check_constraint(db_session):
    """Verify age CHECK constraint allows 18-100 and rejects outside values."""
    # Create a test user first
    test_user_id = str(uuid.uuid4())
    result = await db_session.execute(text("""
        INSERT INTO "user".user_profiles 
        (user_id, username, email, password_hash, country_code, account_status, age)
        VALUES (:user_id, 'test_user_valid', 'test@example.com', 'hash', 'US', 'ACTIVE', 25)
        RETURNING user_id
    """), {"user_id": test_user_id})
    await db_session.commit()
    user_id = result.scalar()
    assert user_id is not None, "Should create user with age=25"
    print("✓ Age constraint allows valid age (25)")
    
    # Clean up
    await db_session.execute(text(f"DELETE FROM \"user\".user_profiles WHERE user_id = '{user_id}'"))
    await db_session.commit()
    
    # Test age below minimum (should fail)
    try:
        young_user_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT INTO "user".user_profiles 
            (user_id, username, email, password_hash, country_code, account_status, age)
            VALUES (:user_id, 'test_user_young', 'young@example.com', 'hash', 'US', 'ACTIVE', 17)
        """), {"user_id": young_user_id})
        await db_session.commit()
        assert False, "Should reject age=17"
    except Exception as e:
        await db_session.rollback()
        assert 'age_check' in str(e) or 'check constraint' in str(e).lower(), \
            f"Expected age_check constraint violation, got: {e}"
        print("✓ Age constraint rejects invalid age (17)")
    
    # Test age above maximum (should fail)
    try:
        old_user_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT INTO "user".user_profiles 
            (user_id, username, email, password_hash, country_code, account_status, age)
            VALUES (:user_id, 'test_user_old', 'old@example.com', 'hash', 'US', 'ACTIVE', 101)
        """), {"user_id": old_user_id})
        await db_session.commit()
        assert False, "Should reject age=101"
    except Exception as e:
        await db_session.rollback()
        assert 'age_check' in str(e) or 'check constraint' in str(e).lower(), \
            f"Expected age_check constraint violation, got: {e}"
        print("✓ Age constraint rejects invalid age (101)")


@pytest.mark.asyncio
async def test_columns_are_nullable(db_session):
    """Verify all 4 new columns accept NULL values."""
    # Insert a user with all demographic columns as NULL
    test_user_id = str(uuid.uuid4())
    result = await db_session.execute(text("""
        INSERT INTO "user".user_profiles 
        (user_id, username, email, password_hash, country_code, account_status, age, sex, income_estimate, income_source)
        VALUES (:user_id, 'test_nullable', 'nullable@example.com', 'hash', 'US', 'ACTIVE', NULL, NULL, NULL, NULL)
        RETURNING user_id
    """), {"user_id": test_user_id})
    await db_session.commit()
    user_id = result.scalar()
    assert user_id is not None, "Should create user with all demographic columns NULL"
    
    # Verify the values are NULL
    result = await db_session.execute(text(f"""
        SELECT age, sex, income_estimate, income_source
        FROM "user".user_profiles
        WHERE user_id = '{user_id}'
    """))
    row = result.fetchone()
    
    assert row.age is None, "age should be NULL"
    assert row.sex is None, "sex should be NULL"
    assert row.income_estimate is None, "income_estimate should be NULL"
    assert row.income_source is None, "income_source should be NULL"
    
    print("✓ All 4 demographic columns accept NULL values")
    
    # Clean up
    await db_session.execute(text(f"DELETE FROM \"user\".user_profiles WHERE user_id = '{user_id}'"))
    await db_session.commit()


if __name__ == "__main__":
    # Run tests directly
    async def run_tests():
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        
        engine = create_async_engine(settings.database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            print("\n=== Running User Demographics Merge Tests ===\n")
            
            print("Test 1: user_demographics Table Dropped")
            await test_user_demographics_table_dropped(session)
            print()
            
            print("Test 2: New Columns Exist on user_profiles")
            await test_new_columns_exist_on_user_profiles(session)
            print()
            
            print("Test 3: Age CHECK Constraint")
            await test_age_check_constraint(session)
            print()
            
            print("Test 4: Columns Are Nullable")
            await test_columns_are_nullable(session)
            print()
            
            print("=== All Tests Passed ===\n")
        
        await engine.dispose()
    
    asyncio.run(run_tests())
