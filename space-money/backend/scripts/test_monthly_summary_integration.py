"""
Script to test the full integration:
1. Create a test user and account
2. Simulate a Lean transaction sync via DataService
3. Verify that DerivedMonthlySummary is automatically updated
"""
import asyncio
import uuid
import os
import sys
from cryptography.fernet import Fernet

# Set encryption key for tests before importing models
if not os.getenv("ENCRYPTION_KEY"):
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_settings
from database import get_db, AsyncSessionLocal
from models.user import UserProfile, AccountStatus
from models.accounts import UserAccount, AccountType
from models.analytics import DerivedMonthlySummary
from services.data_service import DataService
from services.lean_client import LeanClient

# Mock Lean Client to avoid actual API calls
class MockLeanClient(LeanClient):
    def __init__(self):
        pass

async def test_integration():
    settings = get_settings()
    
    # Setup DB
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()
    lean_account_id = uuid.uuid4()
    
    print(f"Testing integration for User {user_id}...")
    
    async with async_session() as session:
        # 1. Create User
        user = UserProfile(
            user_id=user_id,
            username=f"integ_test_{user_id.hex[:8]}",
            email=f"integ_{user_id.hex[:8]}@example.com",
            password_hash="hash",
            country_code="AE",
            account_status=AccountStatus.ACTIVE
        )
        session.add(user)
        await session.flush()
        
        # 2. Create Account
        account = UserAccount(
            account_id=account_id,
            user_id=user_id,
            lean_account_id=lean_account_id,
            institution_name="Test Bank",
            account_name="Integration Test Account",
            account_type=AccountType.CURRENT,
            currency_code="AED",
            account_status="ACTIVE"
        )
        session.add(account)
        await session.commit()
        
        # 3. Simulate Transaction Sync
        # We'll use DataService._upsert_transactions and trigger computation manually if needed,
        # but the goal is to test sync_all_for_entity or just the trigger logic.
        # Since sync_all_for_entity does a lot of API calls, we'll verify the trigger logic 
        # by calling _upsert_transactions then manually calling compute or simulating the flow.
        # Wait, the requirement is to test the TRIGGER. 
        # The trigger is in `sync_all_for_entity`.
        # So we should call `sync_all_for_entity` with a mocked client.
        
        mock_client = MockLeanClient()
        # Monkey patch methods to return dummy data
        async def mock_get_identity(entity_id):
            return {"payload": {}}
        async def mock_get_accounts(entity_id):
            return {"payload": {"accounts": []}} # Skip account upsert, we created it
        async def mock_get_balance(acc_id, ent_id):
            return {"payload": {"balance": 1000.0, "currency_code": "AED"}}
        async def mock_get_transactions(acc_id, ent_id, start, end):
            return {
                "payload": {
                    "transactions": [
                        {
                            "id": str(uuid.uuid4()),
                            "amount": -500.0, # Expense
                            "date": datetime.now().isoformat(),
                            "timestamp": datetime.now().isoformat(),
                            "description": "Integration Test Expense",
                            "currency_code": "AED",
                            "insights": {
                                "category": "RESTAURANTS_DINING" # Matches flexible system default
                            }
                        }
                    ]
                }
            }
            
        mock_client.get_identity = mock_get_identity
        mock_client.get_accounts = mock_get_accounts
        mock_client.get_balance = mock_get_balance
        mock_client.get_transactions = mock_get_transactions
        
        data_service = DataService(lean_client=mock_client, db=session)
        
        # We need to ensure account mapping works. 
        # sync_all_for_entity calls sync_accounts which returns account_ids.
        # We need to mock sync_accounts to return our mock account ID.
        
        async def mock_sync_accounts_override(entity_id, user_id):
             return {
                "status": "success",
                "file_path": "dummy",
                "account_ids": [str(lean_account_id)],
                "db_account_ids": [str(account_id)],
                "count": 1
            }
        data_service.sync_accounts = mock_sync_accounts_override
        
        print("Running full sync (simulated)...")
        # Run the sync which includes the trigger
        await data_service.sync_all_for_entity("dummy_entity", user_id)
        
        # 4. Verify Derived Data matches
        print("Verifying derived summary...")
        stmt = select(DerivedMonthlySummary).where(
            DerivedMonthlySummary.user_id == user_id
        )
        result = await session.execute(stmt)
        summary = result.scalar_one_or_none()
        
        if summary:
            print(f"✓ Summary Found!")
            print(f"  Month: {summary.period_month}")
            print(f"  Expenses: {summary.total_expenses} (Expected 500.00)")
            
            assert summary.total_expenses == Decimal('500.00')
            print("✓ Integration Successful: Data Sync triggered Analytics Computation.")
        else:
            print("❌ Summary NOT found. Trigger failed.")
            
        # Cleanup
        await session.delete(user)
        await session.commit()

if __name__ == "__main__":
    asyncio.run(test_integration())
