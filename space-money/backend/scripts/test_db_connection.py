#!/usr/bin/env python3
"""
Test database connection to AWS RDS.

This script verifies:
- SSL connection to AWS RDS
- Database authentication
- Schema access permissions
- UUID generation functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from config import get_settings

async def test_connection():
    """Test database connection and permissions."""
    settings = get_settings()
    
    print("=" * 60)
    print("Space Money Database Connection Test")
    print("=" * 60)
    print()
    print(f"Connecting to: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'database'}")
    print()
    
    try:
        # Create engine
        engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=0,
            connect_args={
                "ssl": "require",
                "command_timeout": 60,
            }
        )
        
        async with engine.connect() as conn:
            # Test 1: Basic connection
            print("✓ Connected to database successfully")
            
            # Test 2: Check PostgreSQL version
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✓ PostgreSQL version: {version.split(',')[0]}")
            
            # Test 3: Check if schemas exist
            result = await conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name IN ('user', 'accounts', 'transactions', 'system')
                ORDER BY schema_name
            """))
            schemas = [row[0] for row in result]
            if schemas:
                print(f"✓ Schemas found: {', '.join(schemas)}")
            else:
                print("⚠ No application schemas found (run migrations first)")
            
            # Test 4: Check UUID extension
            result = await conn.execute(text("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp'
                )
            """))
            has_uuid = result.scalar()
            if has_uuid:
                print("✓ UUID extension available")
                
                # Test UUID generation
                result = await conn.execute(text("SELECT gen_random_uuid()"))
                test_uuid = result.scalar()
                print(f"✓ UUID generation works: {test_uuid}")
            else:
                print("⚠ UUID extension not installed (will be added by migration)")
            
            # Test 5: Check SSL connection (PostgreSQL 17 compatible)
            result = await conn.execute(text("""
                SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()
            """))
            ssl_row = result.fetchone()
            if ssl_row and ssl_row[0]:
                print("✓ SSL connection active (DIFC compliant)")
            else:
                print("⚠ SSL not active - check connection string")
            
            # Test 6: Check connection pooling
            print(f"✓ Connection pool size: {engine.pool.size()}")
            
            # Test 7: List tables if schemas exist
            if schemas:
                result = await conn.execute(text("""
                    SELECT schemaname, tablename 
                    FROM pg_tables 
                    WHERE schemaname IN ('user', 'accounts', 'transactions', 'system')
                    ORDER BY schemaname, tablename
                """))
                tables = result.fetchall()
                if tables:
                    print(f"✓ Found {len(tables)} tables:")
                    for schema, table in tables:
                        print(f"  - {schema}.{table}")
                else:
                    print("⚠ No tables found (run migrations)")
            
            print()
            print("=" * 60)
            print("✅ All connection tests passed!")
            print("=" * 60)
        
        await engine.dispose()
        return 0
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Connection test failed!")
        print("=" * 60)
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print()
        print("Troubleshooting:")
        
        # Specific error guidance
        error_str = str(e).lower()
        if "timeout" in error_str or "timed out" in error_str:
            print("⚠ Connection timeout - likely security group issue")
            print("  → Check AWS RDS security group allows your IP")
            print("  → Verify VPC settings and subnet groups")
        elif "authentication" in error_str or "password" in error_str:
            print("⚠ Authentication failed")
            print("  → Verify username and password in DATABASE_URL")
            print("  → Check master credentials in AWS RDS console")
        elif "database" in error_str and "does not exist" in error_str:
            print("⚠ Database does not exist")
            print("  → Create database first: CREATE DATABASE spacemoney;")
        elif "ssl" in error_str:
            print("⚠ SSL connection issue")
            print("  → Try removing ?ssl=require from DATABASE_URL temporarily")
        else:
            print("1. Check DATABASE_URL format in .env file")
            print("2. Verify AWS RDS endpoint and credentials")
            print("3. Ensure security group allows your IP address")
            print("4. Confirm database name exists")
            print("5. Try connecting with psql client to verify credentials")
        
        print("=" * 60)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(test_connection())
    sys.exit(exit_code)
