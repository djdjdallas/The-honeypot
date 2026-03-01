"""Telegram group monitor using Telethon user client."""

import asyncio
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from telethon import TelegramClient, events

from .classifier import classify_initial_message, keyword_prefilter
from .conversation import (
    build_message,
    run_conversation_turn,
    should_continue_session,
)
from .extractor import merge_intel
from .persona import get_persona
from .reporter import report_session

load_dotenv()
logger = logging.getLogger(__name__)


def _get_config():
    """Load configuration from environment variables."""
    return {
        "api_id": int(os.environ["TELEGRAM_API_ID"]),
        "api_hash": os.environ["TELEGRAM_API_HASH"],
        "phone": os.environ["TELEGRAM_PHONE"],
        "session_name": os.environ.get("TELEGRAM_SESSION_NAME", "honeytrap"),
        "max_turns": int(os.environ.get("MAX_TURNS_PER_SESSION", "20")),
        "monitor_groups": [
            g.strip()
            for g in os.environ.get("MONITOR_GROUPS", "").split(",")
            if g.strip()
        ],
    }


class HoneyTrapMonitor:
    """Monitors Telegram groups and engages detected scammers."""

    def __init__(self):
        config = _get_config()
        self.client = TelegramClient(
            config["session_name"],
            config["api_id"],
            config["api_hash"],
        )
        self.monitor_groups = config["monitor_groups"]
        self.max_turns = config["max_turns"]
        # Track active sessions: {scammer_user_id: session_data}
        self.active_sessions: dict[int, dict] = {}

    async def start(self):
        """Start the monitor."""
        await self.client.start(phone=os.environ["TELEGRAM_PHONE"])
        logger.info("Telegram client connected.")

        # Resolve group entities
        group_entities = []
        for group in self.monitor_groups:
            try:
                entity = await self.client.get_entity(group)
                group_entities.append(entity)
                logger.info("Monitoring group: %s", group)
            except Exception:
                logger.exception("Failed to resolve group: %s", group)

        if not group_entities:
            logger.warning("No groups to monitor.")
            return

        # Register handler for new messages in monitored groups
        @self.client.on(events.NewMessage(chats=group_entities))
        async def on_group_message(event):
            await self._handle_group_message(event)

        # Register handler for direct messages (scammer replies)
        @self.client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
        async def on_direct_message(event):
            await self._handle_direct_message(event)

        logger.info("Monitor started. Listening for messages...")
        await self.client.run_until_disconnected()

    async def _handle_group_message(self, event):
        """Process a message from a monitored group."""
        message_text = event.message.text
        if not message_text:
            return

        sender = await event.get_sender()
        if not sender or sender.bot:
            return

        # Stage 1: Quick keyword pre-filter
        if not keyword_prefilter(message_text):
            return

        logger.info(
            "Keyword match from user %d in group: %s",
            sender.id,
            message_text[:80],
        )

        # Stage 2: Nova classification
        classification = classify_initial_message(message_text)
        if not classification.get("is_scam"):
            logger.info("Nova classified as non-scam: %s", classification.get("reason"))
            return

        logger.info(
            "Scam detected from user %d: %s", sender.id, classification.get("reason")
        )

        # Don't re-engage if we already have an active session
        if sender.id in self.active_sessions:
            logger.info("Already tracking user %d, skipping.", sender.id)
            return

        # Start engagement: send DM to scammer
        persona = get_persona()
        await self._initiate_engagement(sender, persona, message_text)

    async def _initiate_engagement(self, scammer, persona, trigger_message):
        """Send initial DM to a detected scammer."""
        # Create a natural opener based on the trigger message
        opener = (
            f"Hey, I saw your message in the group about crypto. "
            f"I'm interested — {persona['phrases'][0]}. Can you tell me more?"
        )

        try:
            await self.client.send_message(scammer.id, opener)
            logger.info(
                "Initiated engagement with user %d as %s",
                scammer.id,
                persona["name"],
            )

            self.active_sessions[scammer.id] = {
                "persona": persona,
                "history": [build_message("assistant", opener)],
                "intel": {"wallets": [], "urls": [], "phishing_links": [], "phones": []},
                "trigger_message": trigger_message,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "turn_count": 1,
            }
        except Exception:
            logger.exception("Failed to send DM to user %d", scammer.id)

    async def _handle_direct_message(self, event):
        """Process a reply from a scammer in DMs."""
        sender = await event.get_sender()
        if not sender or sender.id not in self.active_sessions:
            return

        message_text = event.message.text
        if not message_text:
            return

        session = self.active_sessions[sender.id]
        logger.info(
            "Scammer %d (turn %d): %s",
            sender.id,
            session["turn_count"],
            message_text[:80],
        )

        # Check if we should continue
        if not should_continue_session(session["history"], session["intel"]):
            await self._end_session(sender.id)
            return

        try:
            reply, updated_history, new_intel = run_conversation_turn(
                session["persona"],
                session["history"],
                message_text,
            )

            session["history"] = updated_history
            session["intel"] = merge_intel(session["intel"], new_intel)
            session["turn_count"] += 1

            # Small delay to seem human
            await asyncio.sleep(3)

            await self.client.send_message(sender.id, reply)
            logger.info("Replied to scammer %d: %s", sender.id, reply[:80])

        except Exception:
            logger.exception("Error in conversation with user %d", sender.id)
            await self._end_session(sender.id)

    async def _end_session(self, scammer_id: int):
        """End a session and report results."""
        session = self.active_sessions.pop(scammer_id, None)
        if not session:
            return

        logger.info(
            "Ending session with user %d after %d turns.",
            scammer_id,
            session["turn_count"],
        )

        # Build transcript
        transcript_parts = []
        for msg in session["history"]:
            role = msg["role"]
            text = msg["content"][0]["text"] if isinstance(msg["content"], list) else msg["content"]
            label = session["persona"]["name"] if role == "assistant" else "Scammer"
            transcript_parts.append(f"{label}: {text}")
        transcript = "\n".join(transcript_parts)

        try:
            report_session(
                scammer_id=str(scammer_id),
                persona_name=session["persona"]["name"],
                transcript=transcript,
                intel=session["intel"],
                trigger_message=session["trigger_message"],
                started_at=session["started_at"],
                turn_count=session["turn_count"],
            )
        except Exception:
            logger.exception("Failed to report session for user %d", scammer_id)


def run_monitor():
    """Entry point to run the monitor."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    monitor = HoneyTrapMonitor()
    asyncio.run(monitor.start())


if __name__ == "__main__":
    run_monitor()
