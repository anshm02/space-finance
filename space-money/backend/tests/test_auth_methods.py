"""Test different authentication methods with Lean API."""
import asyncio
import httpx
from config import get_settings

settings = get_settings()

async def test_bearer_auth():
    """Test with Authorization: Bearer header."""
    print("\n" + "=" * 60)
    print("Testing: Authorization: Bearer {token}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "Authorization": f"Bearer {settings.lean_app_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await client.post(
                f"{settings.lean_base_url}/customers/v1",
                json={"app_user_id": "test_bearer_auth"},
                headers=headers
            )
            print(f"✓ Status Code: {response.status_code}")
            print(f"✓ Response: {response.text[:200]}")
            return True
        except httpx.HTTPStatusError as e:
            print(f"✗ Status Code: {e.response.status_code}")
            print(f"✗ Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return False


async def test_lean_app_token_header():
    """Test with lean-app-token header."""
    print("\n" + "=" * 60)
    print("Testing: lean-app-token: {token}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "lean-app-token": settings.lean_app_token,
            "Content-Type": "application/json"
        }
        
        try:
            response = await client.post(
                f"{settings.lean_base_url}/customers/v1",
                json={"app_user_id": "test_lean_token_header"},
                headers=headers
            )
            print(f"✓ Status Code: {response.status_code}")
            print(f"✓ Response: {response.text[:200]}")
            return True
        except httpx.HTTPStatusError as e:
            print(f"✗ Status Code: {e.response.status_code}")
            print(f"✗ Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return False


async def test_api_key_header():
    """Test with x-api-key header."""
    print("\n" + "=" * 60)
    print("Testing: x-api-key: {token}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "x-api-key": settings.lean_app_token,
            "Content-Type": "application/json"
        }
        
        try:
            response = await client.post(
                f"{settings.lean_base_url}/customers/v1",
                json={"app_user_id": "test_api_key_header"},
                headers=headers
            )
            print(f"✓ Status Code: {response.status_code}")
            print(f"✓ Response: {response.text[:200]}")
            return True
        except httpx.HTTPStatusError as e:
            print(f"✗ Status Code: {e.response.status_code}")
            print(f"✗ Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return False


async def main():
    """Run all authentication tests."""
    print("=" * 60)
    print("Lean API Authentication Method Testing")
    print("=" * 60)
    print(f"\nBase URL: {settings.lean_base_url}")
    print(f"Token (first 30 chars): {settings.lean_app_token[:30]}...")
    print(f"Token length: {len(settings.lean_app_token)} characters")
    
    bearer_works = await test_bearer_auth()
    lean_header_works = await test_lean_app_token_header()
    api_key_works = await test_api_key_header()
    
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)
    print(f"Bearer Token Auth: {'✓ WORKS' if bearer_works else '✗ FAILED'}")
    print(f"lean-app-token Header: {'✓ WORKS' if lean_header_works else '✗ FAILED'}")
    print(f"x-api-key Header: {'✓ WORKS' if api_key_works else '✗ FAILED'}")
    
    if bearer_works:
        print("\n✓ Use: Authorization: Bearer {token}")
    elif lean_header_works:
        print("\n✓ Use: lean-app-token: {token}")
    elif api_key_works:
        print("\n✓ Use: x-api-key: {token}")
    else:
        print("\n✗ None of the authentication methods worked!")
        print("   Please check:")
        print("   1. Your LEAN_APP_TOKEN is correct")
        print("   2. Your token is from the correct environment (sandbox/production)")
        print("   3. Your token has the necessary permissions")


if __name__ == "__main__":
    asyncio.run(main())
