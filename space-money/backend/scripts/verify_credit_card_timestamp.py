#!/usr/bin/env python3
"""
Verify credit card details and transaction timestamp implementation.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from sqlalchemy import text
from database import engine
from datetime import datetime

async def verify_implementation():
    """Verify credit card details and transaction timestamp features."""
    print("=" * 80)
    print("CREDIT CARD DETAILS & TRANSACTION TIMESTAMP VERIFICATION")
    print("=" * 80)
    print()
    
    async with engine.begin() as conn:
        # 1. Check if transaction_timestamp column exists
        print("1. Checking transaction_timestamp column...")
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'transactions' 
            AND table_name = 'raw_transactions' 
            AND column_name = 'transaction_timestamp'
        """))
        col = result.fetchone()
        
        if col:
            print(f"   ✓ Column exists: {col[0]} ({col[1]})")
        else:
            print("   ✗ Column transaction_timestamp NOT FOUND")
            return
        
        print()
        
        # 2. Check transaction_timestamp data
        print("2. Checking transaction timestamp data...")
        result = await conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(transaction_timestamp) as with_timestamp,
                MIN(transaction_timestamp) as earliest,
                MAX(transaction_timestamp) as latest
            FROM transactions.raw_transactions
        """))
        row = result.fetchone()
        
        if row:
            print(f"   Total transactions: {row[0]}")
            print(f"   With timestamp: {row[1]}")
            if row[2]:
                print(f"   Earliest: {row[2]}")
                print(f"   Latest: {row[3]}")
        
        print()
        
        # 3. Check credit card details table
        print("3. Checking credit card details...")
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM accounts.credit_card_details
        """))
        count = result.scalar()
        print(f"   Credit card records: {count}")
        
        if count > 0:
            result = await conn.execute(text("""
                SELECT 
                    ccd.account_id,
                    ua.account_name,
                    ccd.credit_limit,
                    ccd.next_payment_due_date,
                    ccd.next_payment_due_amount
                FROM accounts.credit_card_details ccd
                JOIN accounts.user_accounts ua ON ccd.account_id = ua.account_id
            """))
            cards = result.fetchall()
            
            print()
            print("   Credit Card Details:")
            for card in cards:
                print(f"     • {card[1]}")
                print(f"       - Limit: {card[2]}")
                print(f"       - Due Date: {card[3] or 'N/A'}")
                print(f"       - Due Amount: {card[4] or 'N/A'}")
        else:
            print("   ⚠ No credit card details found")
            print("   Trigger a Lean sync to populate data")
        
        print()
        
        # 4. Sample transaction with timestamp
        print("4. Sample transactions with timestamps...")
        result = await conn.execute(text("""
            SELECT 
                transaction_date,
                transaction_timestamp,
                amount,
                currency_code,
                lean_insights_category
            FROM transactions.raw_transactions
            WHERE transaction_timestamp IS NOT NULL
            ORDER BY transaction_timestamp DESC
            LIMIT 3
        """))
        txns = result.fetchall()
        
        if txns:
            for txn in txns:
                print(f"   • Date: {txn[0]} | Timestamp: {txn[1]}")
                print(f"     Amount: {txn[2]} {txn[3]} | Category: {txn[4]}")
        else:
            print("   ℹ️  No transactions with timestamps yet")
            print("   Run a new Lean sync to populate timestamps")
        
        print()
        print("=" * 80)
        print("✅ Verification complete")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(verify_implementation())
