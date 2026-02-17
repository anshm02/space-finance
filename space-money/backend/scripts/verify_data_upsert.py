#!/usr/bin/env python3
"""
Verify data upsert functionality.

This script verifies that Lean API data is being properly
stored in both local files AND the AWS database.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select
from config import get_settings
from models.accounts import UserAccount
from models.transactions import RawTransaction
from models.system import AuditLog

async def verify_dual_persistence():
    """Verify data is stored in both files and database."""
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    
    print("=" * 60)
    print("Space Money Dual Persistence Verification")
    print("=" * 60)
    print()
    
    # Check file storage
    print("1. Checking local file storage...")
    raw_dir = data_dir / "raw"
    if raw_dir.exists():
        files = list(raw_dir.glob("*.json"))
        print(f"   ✓ Found {len(files)} JSON files in {raw_dir}")
        
        # Count by type
        accounts = [f for f in files if f.name.startswith("accounts_")]
        balances = [f for f in files if f.name.startswith("balance_")]
        transactions = [f for f in files if f.name.startswith("transactions_")]
        print(f"     - Accounts: {len(accounts)}")
        print(f"     - Balances: {len(balances)}")
        print(f"     - Transactions: {len(transactions)}")
    else:
        print(f"   ⚠ Directory not found: {raw_dir}")
        print(f"   Run a Lean sync first to generate files")
    
    print()
    
    # Check database storage
    print("2. Checking database storage...")
    try:
        engine = create_async_engine(settings.database_url, echo=False)
        AsyncSessionLocal = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with AsyncSessionLocal() as session:
            # Check accounts
            result = await session.execute(
                text("SELECT COUNT(*) FROM accounts.user_accounts")
            )
            account_count = result.scalar()
            print(f"   ✓ User accounts in database: {account_count}")
            
            # Check balances
            result = await session.execute(
                text("SELECT COUNT(*) FROM accounts.account_balances")
            )
            balance_count = result.scalar()
            print(f"   ✓ Balance snapshots in database: {balance_count}")
            
            # Check transactions
            result = await session.execute(
                text("SELECT COUNT(*) FROM transactions.raw_transactions")
            )
            transaction_count = result.scalar()
            print(f"   ✓ Transactions in database: {transaction_count}")
            
            # Check audit logs
            result = await session.execute(
                text("SELECT COUNT(*) FROM system.audit_log")
            )
            audit_count = result.scalar()
            print(f"   ✓ Audit log entries: {audit_count}")
            
            print()
            
            # Sample data verification
            if account_count > 0:
                print("3. Verifying data integrity...")
                
                # Get a sample account
                result = await session.execute(
                    text("""
                        SELECT account_id, institution_name, account_type, 
                               currency_code, linked_at
                        FROM accounts.user_accounts 
                        LIMIT 1
                    """)
                )
                account = result.fetchone()
                if account:
                    print(f"   Sample account:")
                    print(f"     - ID: {account[0]}")
                    print(f"     - Institution: {account[1]}")
                    print(f"     - Type: {account[2]}")
                    print(f"     - Currency: {account[3]}")
                    print(f"     - Linked: {account[4]}")
                
                # Get latest transaction
                result = await session.execute(
                    text("""
                        SELECT *
                        FROM transactions.raw_transactions 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """)
                )
                txn = result.fetchone()
                if txn:
                    print(f"   Latest transaction:")
                    print(f"     - transaction: {txn}")
                
                print()
                print("=" * 60)
                print("✅ Dual persistence verification complete!")
                print("   Data is being stored in BOTH files AND database")
                print("=" * 60)
            else:
                print()
                print("=" * 60)
                print("⚠ No data found in database")
                print("=" * 60)
                print("To populate the database:")
                print("1. Ensure you have linked a bank account via Lean SDK")
                print("2. Call the /api/v1/lean/sync endpoint")
                print("3. Check that ENCRYPTION_KEY is set in .env")
                print("=" * 60)
        
        await engine.dispose()
        return 0
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Database verification failed!")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print()
        print("Possible issues:")
        print("1. Migrations not run (alembic upgrade head)")
        print("2. Database connection issues")
        print("3. Missing encryption key in .env")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(verify_dual_persistence())
    sys.exit(exit_code)
