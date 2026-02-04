"""Quick script to check your Lean app token configuration."""
from config import get_settings

settings = get_settings()

print("=" * 60)
print("Lean App Token Configuration Check")
print("=" * 60)
print(f"\nToken is set: {bool(settings.lean_app_token)}")
print(f"Token length: {len(settings.lean_app_token)} characters")
print(f"Token first 30 chars: {settings.lean_app_token[:30]}...")
print(f"Token last 10 chars: ...{settings.lean_app_token[-10:]}")
print(f"\nFull Authorization header would be:")
print(f"  Authorization: {settings.lean_app_token[:30]}...{settings.lean_app_token[-10:]}")
print("\n" + "=" * 60)
print("\nIf token looks like a UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx),")
print("that's normal for Lean sandbox tokens.")
print("\nMake sure:")
print("  1. Token is from https://dev.leantech.me dashboard")
print("  2. Token has no extra spaces or quotes")
print("  3. Token is the 'App Token' not a different credential")
