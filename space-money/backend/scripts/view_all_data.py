"""
Comprehensive database viewer for Space Money.

Displays all data across DIFC-compliant tables with counts and sample records.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from sqlalchemy import text
from database import engine
from datetime import datetime

async def view_all_data():
    """View all data in DIFC-compliant schema."""
    print("=" * 80)
    print("SPACE MONEY - DATABASE VIEWER")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    async with engine.begin() as conn:
        # User schema
        print("👤 USER SCHEMA")
        print("-" * 80)
        
        result = await conn.execute(text('SELECT COUNT(*) FROM "user".user_profiles'))
        count = result.scalar()
        print(f"user_profiles: {count} records")
        
        result = await conn.execute(text('SELECT COUNT(*) FROM "user".user_demographics'))
        count = result.scalar()
        print(f"user_demographics: {count} records")
        
        result = await conn.execute(text('SELECT COUNT(*) FROM "user".consent_records'))
        count = result.scalar()
        print(f"consent_records: {count} records")
        
        print()
        
        # Accounts schema
        print("🏦 ACCOUNTS SCHEMA")
        print("-" * 80)
        
        result = await conn.execute(text("SELECT COUNT(*) FROM accounts.user_accounts"))
        count = result.scalar()
        print(f"user_accounts: {count} records")
        
        if count > 0:
            result = await conn.execute(text("""
                SELECT lean_account_id, account_name, account_type, currency_code, account_status
                FROM accounts.user_accounts
                LIMIT 10
            """))
            rows = result.fetchall()
            print("\nSample Accounts:")
            for row in rows:
                print(f"  • {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}")
        
        result = await conn.execute(text("SELECT COUNT(*) FROM accounts.account_balances"))
        count = result.scalar()
        print(f"\naccount_balances: {count} records")
        
        if count > 0:
            result = await conn.execute(text("""
                SELECT account_id, balance, currency_code, snapshot_timestamp
                FROM accounts.account_balances
                ORDER BY snapshot_timestamp DESC
                LIMIT 5
            """))
            rows = result.fetchall()
            print("\nLatest Balances:")
            for row in rows:
                print(f"  • {row[0]} | {row[1]:,.2f} {row[2]} | {row[3]}")
        
        print()
        
        # Transactions schema  
        print("💸 TRANSACTIONS SCHEMA")
        print("-" * 80)
        
        result = await conn.execute(text("SELECT COUNT(*) FROM transactions.raw_transactions"))
        count = result.scalar()
        print(f"raw_transactions: {count} records")
        
        if count > 0:
            result = await conn.execute(text("""
                SELECT transaction_date, amount, currency_code, transaction_type, 
                       lean_insights_category, lean_insights_type
                FROM transactions.raw_transactions
                ORDER BY transaction_date DESC
                LIMIT 10
            """))
            rows = result.fetchall()
            print("\nRecent Transactions:")
            for row in rows:
                txn_type = "OUT" if row[3] == "debit" else "IN"
                print(f"  • {row[0]} | {txn_type} {row[1]:,.2f} {row[2]} | {row[4]} | {row[5]}")
            
            # Category breakdown
            result = await conn.execute(text("""
                SELECT lean_insights_category, COUNT(*), SUM(amount)
                FROM transactions.raw_transactions
                WHERE lean_insights_category IS NOT NULL
                GROUP BY lean_insights_category
                ORDER BY SUM(amount) DESC
                LIMIT 5
            """))
            rows = result.fetchall()
            if rows:
                print("\nTop Categories by Spend:")
                for row in rows:
                    print(f"  • {row[0]}: {row[1]} txns, {row[2]:,.2f} total")
        
        print()
        
        # System schema
        print("🔧 SYSTEM SCHEMA")
        print("-" * 80)
        
        result = await conn.execute(text("SELECT COUNT(*) FROM system.audit_log"))
        count = result.scalar()
        print(f"audit_log: {count} records")
        
        if count > 0:
            result = await conn.execute(text("""
                SELECT event_type, entity_type, logged_at
                FROM system.audit_log
                ORDER BY logged_at DESC
                LIMIT 5
            """))
            rows = result.fetchall()
            print("\nRecent Audit Logs:")
            for row in rows:
                print(f"  • {row[0]} | {row[1]} | {row[2]}")
        
        print()
        print("=" * 80)
        print("✅ Database view complete")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(view_all_data())
