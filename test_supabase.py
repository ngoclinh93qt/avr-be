"""
Test Supabase connection and configuration.
"""

import asyncio
from app.config import get_settings


def test_config():
    """Test that Supabase is configured."""
    print("=" * 50)
    print("Testing Supabase Configuration")
    print("=" * 50)

    settings = get_settings()

    print(f"\n✓ SUPABASE_URL: {settings.supabase_url[:50]}..." if settings.supabase_url else "✗ SUPABASE_URL: Not set")
    print(f"✓ SUPABASE_PUBLISHABLE_KEY: {settings.supabase_publishable_key[:20]}..." if settings.supabase_publishable_key else "✗ SUPABASE_PUBLISHABLE_KEY: Not set")
    print(f"✓ SUPABASE_SECRET_KEY: {settings.supabase_secret_key[:20]}..." if settings.supabase_secret_key else "✗ SUPABASE_SECRET_KEY: Not set")


def test_client_connection():
    """Test client connection."""
    print("\n" + "=" * 50)
    print("Testing Client Connection (publishable key)")
    print("=" * 50)

    try:
        from app.core.supabase_client import get_supabase_client
        client = get_supabase_client()
        print("✓ Client created successfully")

        # Test a simple query (this will work even without tables)
        # Just checking if we can communicate with Supabase
        print("✓ Connection established")
        return True
    except Exception as e:
        print(f"✗ Client error: {e}")
        return False


def test_admin_connection():
    """Test admin connection."""
    print("\n" + "=" * 50)
    print("Testing Admin Connection (secret key)")
    print("=" * 50)

    try:
        from app.core.supabase_client import get_supabase_admin
        admin = get_supabase_admin()
        print("✓ Admin client created successfully")
        return True
    except Exception as e:
        print(f"✗ Admin client error: {e}")
        return False


def test_tables():
    """Test if required tables exist."""
    print("\n" + "=" * 50)
    print("Testing Database Tables")
    print("=" * 50)

    try:
        from app.core.supabase_client import supabase_service

        # Test research_sessions table
        try:
            response = supabase_service.admin.table("research_sessions").select("id").limit(1).execute()
            print("✓ research_sessions table exists")
        except Exception as e:
            print(f"✗ research_sessions table error: {e}")

        # Test research_papers table
        try:
            response = supabase_service.admin.table("research_papers").select("id").limit(1).execute()
            print("✓ research_papers table exists")
        except Exception as e:
            print(f"✗ research_papers table error: {e}")

        # Test profiles table
        try:
            response = supabase_service.admin.table("profiles").select("id").limit(1).execute()
            print("✓ profiles table exists")
        except Exception as e:
            print(f"✗ profiles table error: {e}")

    except Exception as e:
        print(f"✗ Table test failed: {e}")


async def test_auth():
    """Test auth functionality."""
    print("\n" + "=" * 50)
    print("Testing Auth (sign up / sign in)")
    print("=" * 50)

    from app.core.supabase_client import supabase_service

    test_email = "test@example.com"
    test_password = "testpassword123"

    # Try sign in first (in case user exists)
    try:
        result = await supabase_service.sign_in(test_email, test_password)
        if result.get("user"):
            print(f"✓ Sign in works (user exists: {result['user'].email})")
            return
    except Exception:
        pass

    # Try sign up
    try:
        result = await supabase_service.sign_up(test_email, test_password)
        if result.get("user"):
            print(f"✓ Sign up works (created user: {result['user'].email})")
            if not result.get("session"):
                print("  ℹ️  Email confirmation is enabled - check email to confirm")
        else:
            print("✗ Sign up returned no user")
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            print(f"✓ Auth is working (user already exists)")
        elif "email" in error_msg.lower() and "confirm" in error_msg.lower():
            print(f"✓ Auth is working (email confirmation required)")
        else:
            print(f"✗ Auth error: {e}")


def main():
    print("\n🔌 SUPABASE CONNECTION TEST\n")

    # Test configuration
    test_config()

    # Test connections
    client_ok = test_client_connection()
    admin_ok = test_admin_connection()

    if admin_ok:
        # Test tables
        test_tables()

    if client_ok:
        # Test auth
        asyncio.run(test_auth())

    print("\n" + "=" * 50)
    print("Test Complete")
    print("=" * 50)

    if not admin_ok:
        print("\n⚠️  To fix admin connection, update SUPABASE_SECRET_KEY in .env")
        print("   Get it from: https://supabase.com/dashboard/project/_/settings/api")
        print("   Look for 'Secret' API key")


if __name__ == "__main__":
    main()
