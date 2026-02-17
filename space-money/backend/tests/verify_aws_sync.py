"""
Verification script to prove data sync to AWS RDS.

This script:
1. Creates a test user in the new DIFC schema
2. Mocks Lean API data
3. Runs DataService sync
4. Verifies data exists in AWS RDS tables
"""
import asyncio
import uuid
import logging
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from database import engine, AsyncSession
from models.user import UserProfile, AccountStatus
from models.accounts import UserAccount, AccountBalance
from models.transactions import RawTransaction
from services.data_service import DataService
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
import os
load_dotenv()

# Ensure encryption key is set for testing
if not os.getenv("ENCRYPTION_KEY"):
    logger.warning("ENCRYPTION_KEY not found in .env, using mock key for testing")
    # Generate a valid Fernet key for testing if missing
    from cryptography.fernet import Fernet
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

# Init DB after loading env
from database import engine, AsyncSession
class MockLeanClient:
    async def get_identity(self, entity_id):
        return {
            "payload": {
                "customer": {"id": "cust_123"},
                "identity": {"full_name": "Test User"}
            }
        }
    
    async def get_accounts(self, entity_id):
        return {
            "payload": {
                "accounts": [
                    {
                        "account_id": "12345678-1234-5678-1234-567812345678",
                        "name": "Test Account",
                        "currency_code": "AED",
                        "type": "CURRENT",
                        "iban": "AE123456789012345678901",
                        "account_number": "1234567890"
                    }
                ]
            }
        }

    async def get_balance(self, account_id, entity_id):
        return {
            "payload": {
                "balance": 5000.00,
                "currency_code": "AED",
                "account_type": "CURRENT"
            }
        }

    async def get_transactions(self, account_id, entity_id, from_date=None, to_date=None):
        return {
            "payload": {
                "transactions": [
                    {
                        "id": "87654321-4321-4321-4321-876543210987",
                        "amount": -150.00,
                        "currency": "AED",
                        "date": datetime.now().isoformat(),
                        "description": "Test Transaction",
                        "type": "debit",
                        "pending": False,
                        "transaction_reference": "ref-123",
                        "insights": {
                            "category": "RESTAURANTS_DINING",
                            "type": "CARD",
                            "confidence": 0.95,
                            "description_cleansed": "Test Restaurant"
                        }
                    }
                ]
            }
        }

async def verify_sync():
    print("=" * 80)
    print("🚀 VERIFYING AWS RDS SYNC")
    print("=" * 80)
    
    # Generate test IDs
    test_user_id = uuid.uuid4()
    test_username = f"test_user_{test_user_id}"
    entity_id = "entity_test_123"
    
    # 1. Setup DB Session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # 2. Create Test User in AWS RDS
            print(f"\n1️⃣  Creating test user: {test_user_id}")
            user = UserProfile(
                user_id=test_user_id,
                username=test_username,
                email=f"{test_username}@test.com",
                password_hash="test_hash",
                country_code="AE",
                account_status=AccountStatus.ACTIVE
            )
            db.add(user)
            await db.commit()
            print("   ✅ User created in `user.user_profiles`")
            
            # 3. Run Sync with Mock Data
            print("\n2️⃣  Running DataService sync...")
            mock_client = MockLeanClient()
            data_service = DataService(mock_client, db)
            
            # Override _save_json to prevent file writing during test (optional, but cleaner)
            data_service._save_json = AsyncMock(return_value="mock_path.json")
            
            # Sync
            await data_service.sync_all_for_entity(
                entity_id,
                user_id=test_user_id
            )
            print("   ✅ Sync completed")
            
            # 4. Verify Data in AWS RDS
            print("\n3️⃣  Verifying data in Database Tables:")
            
            # Verify Account
            result = await db.execute(
                select(UserAccount).where(UserAccount.user_id == test_user_id)
            )
            account = result.scalar_one_or_none()
            if account:
                print(f"   ✅ Account found: {account.account_name} ({account.currency_code})")
                print(f"      ID: {account.account_id}")
                # Verify encryption (implicitly handled by type, but we check retrieved value)
                print(f"      IBAN: {account.iban} (Decrypted on retrieval)")
            else:
                print("   ❌ Account NOT found!")
                return
            
            # Verify Balance
            result = await db.execute(
                select(AccountBalance).where(AccountBalance.account_id == account.account_id)
            )
            balance = result.scalar_one_or_none()
            if balance:
                print(f"   ✅ Balance found: {balance.balance} {balance.currency_code}")
            else:
                print("   ❌ Balance NOT found!")
            
            # Verify Transaction
            result = await db.execute(
                select(RawTransaction).where(RawTransaction.account_id == account.account_id)
            )
            txn = result.scalar_one_or_none()
            if txn:
                print(f"   ✅ Transaction found: {txn.amount} {txn.currency_code}")
                print(f"      Category: {txn.lean_insights_category}")
                print(f"      Description: {txn.description} (Decrypted)")
            else:
                print("   ❌ Transaction NOT found!")

        except Exception as e:
            print(f"   ❌ Error during verification: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup (Optional - keep for inspection)
            # await db.delete(user)
            # await db.commit()
            pass

if __name__ == "__main__":
    asyncio.run(verify_sync())
