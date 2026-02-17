"""
Check all database tables for synced data (both legacy and new schemas).
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from sqlalchemy import text
from database import engine

async def check_all_tables():
    print("=" * 60)
    print("Database Data Verification - All Tables")
    print("=" * 60)
    print()
    
    async with engine.begin() as conn:
        # Check legacy Lean integration tables
        print("📊 LEGACY LEAN INTEGRATION TABLES (transactions schema)")
        print("-" * 60)
        
        # Users
        result = await conn.execute(text("SELECT COUNT(*) FROM transactions.users"))
        count = result.scalar()
        print(f"✓ transactions.users: {count} records")
        
        # Lean customers
        result = await conn.execute(text("SELECT COUNT(*) FROM transactions.lean_customers"))
        count = result.scalar()
        print(f"✓ transactions.lean_customers: {count} records")
        
        # Lean entities
        result = await conn.execute(text("SELECT COUNT(*) FROM transactions.lean_entities"))
        count = result.scalar()
        print(f"✓ transactions.lean_entities: {count} records")
        
        # Lean accounts
        result = await conn.execute(text("SELECT COUNT(*) FROM transactions.lean_accounts"))
        count = result.scalar()
        print(f"✓ transactions.lean_accounts: {count} records")
        
        # Lean sync logs
        result = await conn.execute(text("SELECT COUNT(*) FROM transactions.lean_sync_logs"))
        count = result.scalar()
        print(f"✓ transactions.lean_sync_logs: {count} records")
        
        # Balance history
        result = await conn.execute(text("SELECT COUNT(*) FROM transactions.balance_history"))
        count = result.scalar()
        print(f"✓ transactions.balance_history: {count} records")
        
        print()
        print("📊 NEW DIFC-COMPLIANT TABLES")
        print("-" * 60)
        
        # User profiles
        result = await conn.execute(text('SELECT COUNT(*) FROM "user".user_profiles'))
        count = result.scalar()
        print(f"✓ user.user_profiles: {count} records")
        
        # User accounts
        result = await conn.execute(text("SELECT COUNT(*) FROM accounts.user_accounts"))
        count = result.scalar()
        print(f"✓ accounts.user_accounts: {count} records")
        
        # Account balances
        result = await conn.execute(text("SELECT COUNT(*) FROM accounts.account_balances"))
        count = result.scalar()
        print(f"✓ accounts.account_balances: {count} records")
        
        # Raw transactions
        result = await conn.execute(text("SELECT COUNT(*) FROM transactions.raw_transactions"))
        count = result.scalar()
        print(f"✓ transactions.raw_transactions: {count} records")
        
        # Audit log
        result = await conn.execute(text("SELECT COUNT(*) FROM system.audit_log"))
        count = result.scalar()
        print(f"✓ system.audit_log: {count} records")
        
        print()
        print("=" * 60)
        print("📋 SAMPLE DATA FROM LEGACY TABLES")
        print("=" * 60)
        print()
        
        # Show sample lean accounts
        result = await conn.execute(text("""
            SELECT account_id, account_type, currency, balance, created_at
            FROM transactions.lean_accounts
            LIMIT 5
        """))
        rows = result.fetchall()
        if rows:
            print("Latest Lean Accounts:")
            for row in rows:
                print(f"  - Account {row[0][:20]}... | Type: {row[1]} | Currency: {row[2]} | Balance: {row[3]}")
        else:
            print("No lean accounts found")
        
        print()
        
        # Show sample sync logs
        result = await conn.execute(text("""
            SELECT sync_type, status, records_count, created_at
            FROM transactions.lean_sync_logs
            ORDER BY created_at DESC
            LIMIT 5
        """))
        rows = result.fetchall()
        if rows:
            print("Latest Sync Operations:")
            for row in rows:
                print(f"  - {row[0]} | Status: {row[1]} | Records: {row[2]} | {row[3]}")
        else:
            print("No sync logs found")
        
        print()
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(check_all_tables())
