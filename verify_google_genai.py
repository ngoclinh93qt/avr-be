import asyncio
import os
import sys

# Ensure the current directory is in the path to import 'app'
sys.path.append(os.getcwd())

from app.core.llm_router import llm_router

async def verify_google_genai():
    print("Verifying Google GenAI migration...")
    
    # Check if API key is set
    if not os.getenv("GOOGLE_API_KEY"):
        print("Skipping verification: GOOGLE_API_KEY not set")
        # checking .env file manually if env var is missing
        from dotenv import load_dotenv
        load_dotenv()
        if not os.getenv("GOOGLE_API_KEY"):
             print("Please set GOOGLE_API_KEY in .env")
             return

    try:
        response = await llm_router.call(
            prompt="Hello, are you using the new SDK?",
            provider="google",
            model="gemini-2.0-flash"
        )
        print("\nResponse from Gemini:")
        print(response)
        print("\nVerification SUCCESS")
    except Exception as e:
        print(f"\nVerification FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_google_genai())
