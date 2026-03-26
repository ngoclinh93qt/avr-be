"""Script to clear all test data from Supabase including auth users."""

import asyncio
from supabase import create_async_client
from app.config import get_settings


async def clear_all():
    settings = get_settings()
    admin = await create_async_client(settings.supabase_url, settings.supabase_secret_key)

    print("Deleting conversation_turns...")
    await admin.table("conversation_turns").delete().neq("id", 0).execute()

    print("Deleting violations...")
    await admin.table("violations").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    print("Deleting research_sessions...")
    await admin.table("research_sessions").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    print("Deleting profiles...")
    await admin.table("profiles").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    print("Fetching auth users...")
    response = await admin.auth.admin.list_users()
    users = response if isinstance(response, list) else getattr(response, "users", [])

    print(f"Deleting {len(users)} auth users...")
    for user in users:
        uid = user.id if hasattr(user, "id") else user["id"]
        await admin.auth.admin.delete_user(uid)
        print(f"  Deleted user: {uid}")

    print("Done. All data cleared.")


if __name__ == "__main__":
    asyncio.run(clear_all())
