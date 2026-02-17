"""
Refresh OAuth token and test the complete flow
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import httpx
from config import get_settings

settings = get_settings()

async def get_fresh_token():
    """Get a fresh OAuth token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.lean_auth_url}/oauth2/token",
            data={
                "client_id": settings.lean_client_id,
                "client_secret": settings.lean_client_secret,
                "grant_type": "client_credentials",
                "scope": "api"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        data = response.json()
        return data["access_token"]

async def test_with_fresh_token():
    print("Getting fresh OAuth token...")
    token = await get_fresh_token()
    print(f"✓ Token obtained: {token[:50]}...")
    
    # Update .env file
    env_path = ".env"
    try:
        with open(env_path, "r") as f:
            lines = f.readlines()
        
        with open(env_path, "w") as f:
            token_updated = False
            for line in lines:
                if line.startswith("LEAN_APP_TOKEN="):
                    f.write(f"LEAN_APP_TOKEN={token}\n")
                    token_updated = True
                else:
                    f.write(line)
            
            if not token_updated:
                f.write(f"\nLEAN_APP_TOKEN={token}\n")
        
        print(f"✓ Updated .env file with new token")
        
        # Test customer creation
        print("\nTesting customer creation...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.lean_base_url}/customers/v1",
                json={"app_user_id": "test_refresh_script"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Customer created: {data.get('customer_id')}")
            else:
                print(f"✗ Failed: {response.status_code} - {response.text}")
                
    except Exception as e:
        print(f"✗ Error updating .env: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_with_fresh_token())
