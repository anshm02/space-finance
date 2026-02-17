"""
Query and filter transactions from Space Money database.

Provides search, filtering, and export capabilities for transaction data.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import argparse
import csv
from sqlalchemy import text
from database import engine
from datetime import datetime, timedelta

async def query_transactions(
    category=None,
    txn_type=None,
    from_date=None,
    to_date=None,
    min_amount=None,
    limit=50
):
    """Query transactions with filters."""
    
    # Build SQL query based on filters
    where_clauses = []
    params = {}
    
    if category:
        where_clauses.append("lean_insights_category = :category")
        params["category"] = category
    
    if txn_type:
        where_clauses.append("transaction_type = :txn_type")
        params["txn_type"] = txn_type
    
    if from_date:
        where_clauses.append("transaction_date >= :from_date")
        params["from_date"] = from_date
    
    if to_date:
        where_clauses.append("transaction_date <= :to_date")
        params["to_date"] = to_date
    
    if min_amount:
        where_clauses.append("amount >= :min_amount")
        params["min_amount"] = min_amount
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    async with engine.begin() as conn:
        # Get total count
        count_sql = f"SELECT COUNT(*) FROM transactions.raw_transactions WHERE {where_sql}"
        result = await conn.execute(text(count_sql), params)
        total = result.scalar()
        
        if total == 0:
            print("No transactions found matching criteria.")
            return []
        
        # Get transactions
        query_sql = f"""
            SELECT transaction_date, amount, currency_code, transaction_type,
                   lean_insights_category, lean_insights_type, lean_category_confidence
            FROM transactions.raw_transactions
            WHERE {where_sql}
            ORDER BY transaction_date DESC
            LIMIT :limit
        """
        params["limit"] = limit
        
        result = await conn.execute(text(query_sql), params)
        rows = result.fetchall()
        
        print(f"\nFound {total} transactions (showing {len(rows)}):")
        print("-" * 100)
        print(f"{'Date':<12} {'Type':<6} {'Amount':<15} {'Category':<25} {'Type':<15} {'Confidence':<10}")
        print("-" * 100)
        
        for row in rows:
            date_str = row[0].strftime('%Y-%m-%d')
            txn_type = "OUT" if row[3] == "debit" else "IN"
            amount_str = f"{row[1]:,.2f} {row[2]}"
            category = (row[4] or "")[:24]
            lean_type = (row[5] or "")[:14]
            confidence = f"{float(row[6] or 0):.2f}" if row[6] else ""
            
            print(f"{date_str:<12} {txn_type:<6} {amount_str:<15} {category:<25} {lean_type:<15} {confidence:<10}")
        
        print("-" * 100)
        print(f"Total: {total} transactions\n")
        
        return rows

async def get_stats():
    """Get transaction statistics."""
    async with engine.begin() as conn:
        # Total count
        result = await conn.execute(text("SELECT COUNT(*) FROM transactions.raw_transactions"))
        total = result.scalar()
        
        # By type
        result = await conn.execute(text("""
            SELECT transaction_type, COUNT(*), SUM(amount)
            FROM transactions.raw_transactions
            GROUP BY transaction_type
        """))
        by_type = result.fetchall()
        
        # By category
        result = await conn.execute(text("""
            SELECT lean_insights_category, COUNT(*), SUM(amount)
            FROM transactions.raw_transactions
            WHERE lean_insights_category IS NOT NULL
            GROUP BY lean_insights_category
            ORDER BY SUM(amount) DESC
            LIMIT 10
        """))
        by_category = result.fetchall()
        
        print("\n📊 TRANSACTION STATISTICS")
        print("=" * 80)
        print(f"\nTotal Transactions: {total}")
        
        print("\nBy Type:")
        for row in by_type:
            print(f"  {row[0]}: {row[1]} txns, {row[2]:,.2f} total")
        
        print("\nTop 10 Categories by Amount:")
        for row in by_category:
            print(f"  {row[0]}: {row[1]} txns, {row[2]:,.2f} total")
        
        print("\n" + "=" * 80)

async def export_to_csv(filename="transactions.csv"):
    """Export all transactions to CSV."""
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT transaction_date, amount, currency_code, transaction_type,
                   lean_insights_category, lean_insights_type, lean_category_confidence
            FROM transactions.raw_transactions
            ORDER BY transaction_date DESC
        """))
        rows = result.fetchall()
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Date', 'Amount', 'Currency', 'Type', 'Category', 'Lean Type', 'Confidence'])
            
            for row in rows:
                writer.writerow([
                    row[0].strftime('%Y-%m-%d'),
                    float(row[1]),
                    row[2],
                    row[3],
                    row[4] or '',
                    row[5] or '',
                    float(row[6]) if row[6] else ''
                ])
        
        print(f"\n✅ Exported {len(rows)} transactions to {filename}")

async def main():
    parser = argparse.ArgumentParser(description='Query Space Money transactions')
    parser.add_argument('--category', help='Filter by category (e.g., RESTAURANTS_DINING)')
    parser.add_argument('--type', choices=['debit', 'credit'], help='Filter by transaction type')
    parser.add_argument('--from-date', help='From date (YYYY-MM-DD)')
    parser.add_argument('--to-date', help='To date (YYYY-MM-DD)')
    parser.add_argument('--min-amount', type=float, help='Minimum amount')
    parser.add_argument('--limit', type=int, default=50, help='Max results (default: 50)')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--export', help='Export to CSV file')
    parser.add_argument('--recent', type=int, help='Show N most recent transactions')
    
    args = parser.parse_args()
    
    if args.stats:
        await get_stats()
    elif args.export:
        await export_to_csv(args.export)
    elif args.recent:
        await query_transactions(limit=args.recent)
    else:
        await query_transactions(
            category=args.category,
            txn_type=args.type,
            from_date=args.from_date,
            to_date=args.to_date,
            min_amount=args.min_amount,
            limit=args.limit
        )

if __name__ == "__main__":
    asyncio.run(main())
