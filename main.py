"""HoneyTrap — Autonomous Crypto Scam Intelligence Honeypot.

Entry point for the Telegram monitor agent.
"""

import argparse
import logging
import sys


def main():
    parser = argparse.ArgumentParser(
        description="HoneyTrap: Autonomous crypto scam intelligence honeypot"
    )
    parser.add_argument(
        "--mode",
        choices=["monitor", "test-persona", "test-classify"],
        default="monitor",
        help="Run mode (default: monitor)",
    )
    parser.add_argument(
        "--persona",
        choices=["mike", "sandra", "james"],
        default=None,
        help="Persona to use (random if not specified)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.mode == "monitor":
        from agent.monitor import run_monitor
        run_monitor()

    elif args.mode == "test-persona":
        from agent.persona import get_persona
        persona = get_persona(args.persona)
        print(f"\nPersona: {persona['name']}")
        print(f"Age: {persona['age']}")
        print(f"Knowledge: {persona['knowledge_level']}")
        print(f"Backstory: {persona['backstory']}")
        print(f"\nSample phrases:")
        for phrase in persona["phrases"]:
            print(f"  - {phrase}")

    elif args.mode == "test-classify":
        from agent.classifier import keyword_prefilter
        print("Enter a message to test scam keyword detection (Ctrl+C to exit):")
        try:
            while True:
                msg = input("> ")
                is_suspicious = keyword_prefilter(msg)
                print(f"  Suspicious: {is_suspicious}")
        except (KeyboardInterrupt, EOFError):
            print("\nDone.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
