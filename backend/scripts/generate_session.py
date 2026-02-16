import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

async def main():
    print("--- Telegram String Session Generator ---")
    api_id = input("Enter your API ID: ")
    api_hash = input("Enter your API HASH: ")
    
    async with TelegramClient(StringSession(), int(api_id), api_hash) as client:
        session_str = client.session.save()
        print("\nSUCCESS! Your session string is below:\n")
        print(session_str)
        print("\nCopy this string to your .env as TELEGRAM_USER_SESSION")

if __name__ == "__main__":
    asyncio.run(main())
