"""
Test script for Lean Technologies integration.

This script tests the full flow of:
1. Authentication with Lean API
2. Customer creation
3. Entity linking
4. Data extraction to JSON files
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.lean_client import LeanClient, LeanAPIError
from services.data_service import DataService
from config import get_settings

# Configure logging to see debug info
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

settings = get_settings()


async def test_authentication():
    """Test app token with Lean API."""
    print("\n=== Testing Authentication ===")
    async with LeanClient() as client:
        try:
            headers = client._get_headers()
            print(f"✓ App token configured")
            print(f"  Token: {settings.lean_app_token[:20] if settings.lean_app_token else 'NOT SET'}...")
            print(f"  Full token length: {len(settings.lean_app_token) if settings.lean_app_token else 0} characters")
            print(f"  Authorization header: {settings.lean_app_token[:20]}..." if settings.lean_app_token else "NOT SET")
            return bool(settings.lean_app_token)
        except Exception as e:
            print(f"✗ Authentication setup failed: {e}")
            return False


async def test_customer_creation():
    """Test customer creation."""
    print("\n=== Testing Customer Creation ===")
    async with LeanClient() as client:
        try:
            app_user_id = f"test_user_{asyncio.get_event_loop().time()}"
            customer = await client.create_customer(app_user_id)
            print(f"✓ Customer created successfully")
            print(f"  Customer ID: {customer.get('customer_id')}")
            print(f"  App User ID: {app_user_id}")
            return customer.get('customer_id')
        except LeanAPIError as e:
            print(f"✗ Customer creation failed: {e}")
            return None


async def test_data_extraction(entity_id: str = None):
    """
    Test data extraction to JSON files.
    
    Args:
        entity_id: Entity ID to extract data for. If None, uses a test entity ID.
    """
    print("\n=== Testing Data Extraction ===")
    
    # Use provided entity_id or a test one
    if not entity_id:
        entity_id = input("Enter entity_id to test (or press Enter to use sandbox test): ").strip()
        if not entity_id:
            entity_id = "entity_sandbox_test"
    
    async with LeanClient() as client:
        try:
            data_service = DataService(client)
            
            print(f"Using entity_id: {entity_id}")
            print("Syncing all data types...")
            
            # Note: This will fail in sandbox if entity doesn't exist
            # But it demonstrates the flow
            results = await data_service.sync_all_for_entity(entity_id)
            
            print(f"\n✓ Data sync completed")
            print(f"  Files created: {len(results['files_created'])}")
            
            for file_path in results['files_created']:
                print(f"    - {file_path}")
            
            print("\nSync results:")
            for sync_type, result in results['results'].items():
                if isinstance(result, list):
                    for item in result:
                        status = item.get('status', 'unknown')
                        print(f"  {sync_type}: {status}")
                else:
                    status = result.get('status', 'unknown')
                    print(f"  {sync_type}: {status}")
            
            return True
            
        except LeanAPIError as e:
            print(f"✗ Data extraction failed: {e}")
            print(f"  Note: This is expected if the entity doesn't exist in sandbox")
            return False


async def test_individual_endpoints(entity_id: str = None):
    """Test individual API endpoints."""
    print("\n=== Testing Individual Endpoints ===")
    
    if not entity_id:
        entity_id = input("Enter entity_id to test: ").strip()
        if not entity_id:
            print("Skipping individual endpoint tests (no entity_id provided)")
            return
    
    async with LeanClient() as client:
        # Test identity endpoint
        print("\nTesting identity endpoint...")
        try:
            identity = await client.get_identity(entity_id)
            print(f"✓ Identity data retrieved")
        except LeanAPIError as e:
            print(f"✗ Identity fetch failed: {e}")
        
        # Test accounts endpoint
        print("\nTesting accounts endpoint...")
        try:
            accounts_data = await client.get_accounts(entity_id)
            account_ids = [acc.get("account_id") for acc in accounts_data.get("accounts", [])]
            print(f"✓ Accounts data retrieved: {len(account_ids)} accounts")
            
            if account_ids:
                account_id = account_ids[0]
                
                # Test balance endpoint
                print(f"\nTesting balance endpoint for account: {account_id}...")
                try:
                    balance = await client.get_balance(account_id, entity_id)
                    print(f"✓ Balance data retrieved")
                except LeanAPIError as e:
                    print(f"✗ Balance fetch failed: {e}")
                
                # Test transactions endpoint
                print(f"\nTesting transactions endpoint for account: {account_id}...")
                try:
                    transactions = await client.get_transactions(account_id, entity_id)
                    tx_count = len(transactions.get("transactions", []))
                    print(f"✓ Transactions data retrieved: {tx_count} transactions")
                except LeanAPIError as e:
                    print(f"✗ Transactions fetch failed: {e}")
        
        except LeanAPIError as e:
            print(f"✗ Accounts fetch failed: {e}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Lean Technologies Integration Test Suite")
    print("=" * 60)
    
    print(f"\nConfiguration:")
    print(f"  Base URL: {settings.lean_base_url}")
    print(f"  Data Directory: {settings.data_dir}")
    
    # Test authentication
    if not await test_authentication():
        print("\n✗ Authentication failed. Please check your credentials.")
        print("  Required environment variable:")
        print("    - LEAN_APP_TOKEN")
        return
    
    # Test customer creation
    customer_id = await test_customer_creation()
    
    # Test data extraction
    print("\n" + "=" * 60)
    print("Data Extraction Tests")
    print("=" * 60)
    print("\nNote: Data extraction requires a valid entity_id from Lean.")
    print("In sandbox mode, you can use test credentials from Lean documentation.")
    
    entity_id = input("\nDo you want to test data extraction? (y/n): ").strip().lower()
    if entity_id == 'y':
        await test_data_extraction()
    
    # Test individual endpoints
    test_endpoints = input("\nDo you want to test individual endpoints? (y/n): ").strip().lower()
    if test_endpoints == 'y':
        await test_individual_endpoints()
    
    print("\n" + "=" * 60)
    print("Test Suite Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
