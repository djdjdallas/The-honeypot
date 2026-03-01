#!/usr/bin/env python3
"""Generate a Telethon session string for HoneyTrap.

WARNING: Run this script ONCE on your LOCAL machine.
         Never run in CI/CD, Lambda, or any headless environment.
         Never commit the output. Never save it to a file.
         The session string grants full access to your Telegram account.

Usage:
    python scripts/generate_session.py

Prerequisites:
    1. Create an application at https://my.telegram.org
    2. Copy your API ID and API Hash
    3. Add them to your .env file:
         TELEGRAM_API_ID=12345678
         TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
    4. Run this script — it will prompt for your phone number and auth code
    5. Copy the session string into your .env as TELEGRAM_SESSION_STRING=...
"""

import os
import sys

from dotenv import load_dotenv


def main():
    load_dotenv()

    api_id_raw = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")

    if not api_id_raw or not api_hash:
        print("ERROR: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env")
        print("Get these from https://my.telegram.org")
        sys.exit(1)

    try:
        api_id = int(api_id_raw)
    except ValueError:
        print(f"ERROR: TELEGRAM_API_ID must be an integer, got: {api_id_raw!r}")
        sys.exit(1)

    # Import here so missing telethon is caught after env check
    from telethon.sessions import StringSession
    from telethon.sync import TelegramClient

    print("=" * 60)
    print("  HoneyTrap — Telegram Session String Generator")
    print("=" * 60)
    print()
    print("This will authenticate your Telegram account and produce")
    print("a session string. You will be prompted for:")
    print("  1. Your phone number (with country code, e.g. +1234567890)")
    print("  2. The login code Telegram sends you")
    print("  3. Your 2FA password (if enabled)")
    print()

    with TelegramClient(StringSession(), api_id, api_hash) as client:
        session_string = client.session.save()

        print()
        print("=" * 60)
        print("  YOUR SESSION STRING (keep this secret!)")
        print("=" * 60)
        print()
        print(session_string)
        print()
        print("=" * 60)
        print()
        print("Add this to your .env file:")
        print(f'TELEGRAM_SESSION_STRING={session_string}')
        print()
        print("SECURITY NOTES:")
        print("  - This string grants FULL ACCESS to your Telegram account.")
        print("  - Never commit it to git. Never share it.")
        print("  - If compromised, revoke all sessions at my.telegram.org.")
        print("  - You only need to run this script once.")
        print()


if __name__ == "__main__":
    main()
