"""
Script to clear all data from the database while preserving schema structure.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import logging
from sqlalchemy import text
from database import engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def clear_data():
    print("=" * 80)
    print("🧹 CLEARING DATABASE DATA")
    print("=" * 80)
    
    async with engine.begin() as conn:
        try:
            # Disable triggers to speed up and avoid constraints issues if needed
            # await conn.execute(text("SET session_replication_role = 'replica';"))
            
            # Truncate tables with CASCADE to handle foreign keys
            logger.info("Truncating tables...")
            
            # Order matters less with CASCADE, but good to be explicit
            # System schema
            await conn.execute(text('TRUNCATE TABLE system.audit_log CASCADE;'))
            
            # Transactions schema
            await conn.execute(text('TRUNCATE TABLE transactions.raw_transactions CASCADE;'))
            await conn.execute(text('TRUNCATE TABLE transactions.lean_entities CASCADE;'))
            await conn.execute(text('TRUNCATE TABLE transactions.lean_customers CASCADE;'))
            
            # Accounts schema
            await conn.execute(text('TRUNCATE TABLE accounts.account_balances CASCADE;'))
            await conn.execute(text('TRUNCATE TABLE accounts.user_accounts CASCADE;'))
            
            # User schema
            await conn.execute(text('TRUNCATE TABLE "user".data_ingestion_config CASCADE;'))
            await conn.execute(text('TRUNCATE TABLE "user".consent_records CASCADE;'))
            await conn.execute(text('TRUNCATE TABLE "user".user_demographics CASCADE;'))
            await conn.execute(text('TRUNCATE TABLE "user".user_profiles CASCADE;'))
            
            # Legacy tables if they exist (ignore errors if not)
            try:
                await conn.execute(text('TRUNCATE TABLE transactions.users CASCADE;'))
            except Exception:
                pass

            logger.info("✅ All tables truncated successfully.")
            print("\n✅ Database cleared! It is now neat and empty.")
            
        except Exception as e:
            logger.error(f"❌ Error clearing data: {str(e)}")
            raise

if __name__ == "__main__":
    import asyncio
    
    # Load env vars first
    from dotenv import load_dotenv
    load_dotenv()
    
    # Ensure encryption key exists mostly for imports not to fail
    import os
    if not os.getenv("ENCRYPTION_KEY"):
         # Mock key just to allow app to start/imports to work
        from cryptography.fernet import Fernet
        os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

    asyncio.run(clear_data())
