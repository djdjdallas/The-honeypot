"""Telegram group monitor using Telethon user client.

Production-ready monitor that:
  - Loads session from StringSession (no interactive auth at runtime)
  - Integrates anti-detection layer for human-like behavior
  - Uses config system for target group management
  - Rate-limits concurrent sessions and new engagements
  - Ends sessions on silence timeout (10 minutes)
  - Logs every conversation turn to Supabase
"""

import asyncio
import logging
from datetime import datetime, timezone

from telethon import TelegramClient, events
from telethon.sessions import StringSession

from .antidetect import AntiDetect
from .classifier import classify_initial_message, keyword_prefilter
from .config import AgentConfig, load_config
from .conversation import (
    build_message,
    run_conversation_turn,
    should_continue_session,
)
from .extractor import merge_intel
from .persona import get_persona
from .reporter import report_session, log_turn

logger = logging.getLogger(__name__)

# Silence timeout: end session if scammer doesn't reply within this window.
SILENCE_TIMEOUT_SECONDS = 600  # 10 minutes


def _create_client(config: AgentConfig) -> TelegramClient:
    """Create a Telethon client from config.

    Uses StringSession if TELEGRAM_SESSION_STRING is set (production/Lambda).
    Falls back to file-based session with phone auth for local development.
    """
    if config.session_string:
        logger.info("Using StringSession (production mode).")
        session = StringSession(config.session_string)
    else:
        logger.info("No session string found — using file-based session (dev mode).")
        session = "honeytrap_dev"

    return TelegramClient(session, config.api_id, config.api_hash)


class HoneyTrapMonitor:
    """Monitors Telegram groups and engages detected scammers.

    Integrates anti-detection to simulate human-like message timing,
    typing indicators, occasional corrections, and rate limiting.
    """

    def __init__(self, config: AgentConfig | None = None):
        self.config = config or load_config()
        self.client = _create_client(self.config)
        self.antidetect = AntiDetect(client=self.client)

        # Apply rate limit settings from config
        from .antidetect import MAX_CONCURRENT_SESSIONS, NEW_SESSION_COOLDOWN
        self.antidetect._active_session_count = 0  # reset

        # Track active sessions: {scammer_user_id: session_data}
        self.active_sessions: dict[int, dict] = {}

        # Silence timeout tasks: {scammer_user_id: asyncio.Task}
        self._timeout_tasks: dict[int, asyncio.Task] = {}

        # Map of group entity IDs → group config (for source tracking)
        self._group_entity_map: dict[int, dict] = {}

    async def start(self):
        """Start the monitor — connects, resolves groups, registers handlers."""
        if self.config.session_string:
            await self.client.start()
        else:
            if not self.config.phone:
                raise RuntimeError(
                    "No TELEGRAM_SESSION_STRING or TELEGRAM_PHONE set. "
                    "Run: python scripts/generate_session.py"
                )
            await self.client.start(phone=self.config.phone)

        me = await self.client.get_me()
        logger.info("Connected as: %s (ID: %d)", me.first_name, me.id)

        # Resolve group entities from config
        active_groups = self.config.active_groups
        if not active_groups:
            logger.error("No active groups configured. Check groups.yaml or MONITOR_GROUPS.")
            return

        group_entities = []
        group_persona_map = {}  # entity_id -> preferred_persona

        for group_cfg in active_groups:
            try:
                entity = await self.client.get_entity(group_cfg.identifier)
                group_entities.append(entity)
                if group_cfg.preferred_persona:
                    group_persona_map[entity.id] = group_cfg.preferred_persona
                # Store full mapping for source group tracking
                self._group_entity_map[entity.id] = {
                    "identifier": group_cfg.identifier,
                    "name": group_cfg.display_name,
                }
                logger.info(
                    "Monitoring: %s (%s)",
                    group_cfg.display_name,
                    group_cfg.identifier,
                )
            except Exception:
                logger.exception(
                    "Failed to resolve group: %s (%s)",
                    group_cfg.display_name,
                    group_cfg.identifier,
                )

        if not group_entities:
            logger.error("Could not resolve any groups. Exiting.")
            return

        self._group_persona_map = group_persona_map

        # --- Event handlers ---

        @self.client.on(events.NewMessage(chats=group_entities))
        async def on_group_message(event):
            await self._handle_group_message(event)

        @self.client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
        async def on_direct_message(event):
            await self._handle_direct_message(event)

        logger.info(
            "Monitor started. Watching %d group(s). Max %d concurrent sessions.",
            len(group_entities),
            self.config.max_concurrent_sessions,
        )
        await self.client.run_until_disconnected()

    async def _handle_group_message(self, event):
        """Process a message from a monitored group."""
        message_text = event.message.text
        if not message_text:
            return

        sender = await event.get_sender()
        if not sender or sender.bot:
            return

        # Stage 1: Fast keyword pre-filter (≥2 keyword matches required)
        if not keyword_prefilter(message_text):
            return

        logger.info(
            "Keyword hit from user %d in group %s: %.80s",
            sender.id,
            getattr(event.chat, "title", "?"),
            message_text,
        )

        # Stage 2: Nova classification (API call)
        classification = classify_initial_message(message_text)
        if not classification.get("is_scam"):
            logger.debug("Nova says not a scam: %s", classification.get("reason"))
            return

        logger.info(
            "Scam confirmed from user %d: %s",
            sender.id,
            classification.get("reason"),
        )

        # Don't re-engage active targets
        if sender.id in self.active_sessions:
            logger.debug("Already tracking user %d, skipping.", sender.id)
            return

        # Rate limit check
        if not self.antidetect.can_start_new_session():
            logger.info("Rate limited — skipping engagement with user %d.", sender.id)
            return

        # Pick persona (group preference or random)
        group_id = getattr(event.chat, "id", None)
        preferred = self._group_persona_map.get(group_id)
        persona = get_persona(preferred)

        # Track source group
        source_group = self._group_entity_map.get(group_id, {}).get(
            "name", getattr(event.chat, "title", "Unknown")
        )

        await self._initiate_engagement(sender, persona, message_text, source_group)

    async def _initiate_engagement(self, scammer, persona, trigger_message, source_group):
        """Send initial DM to a detected scammer with human-like timing."""
        # Craft a natural opener using the persona's phrases
        opener = (
            f"Hey, I saw your message in the group about crypto. "
            f"I'm interested — {persona['phrases'][0]}. Can you tell me more?"
        )

        try:
            # Set typing speed for this persona
            self.antidetect.set_persona_speed(persona["knowledge_level"])

            # Send with anti-detection (delays, typing simulation)
            await self.antidetect.send_human_message(scammer.id, opener)

            self.antidetect.register_new_session()
            self.active_sessions[scammer.id] = {
                "persona": persona,
                "history": [build_message("assistant", opener)],
                "intel": {"wallets": [], "urls": [], "phishing_links": [], "phones": []},
                "trigger_message": trigger_message,
                "source_group": source_group,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "turn_count": 1,
            }

            # Start silence timeout
            self._reset_silence_timer(scammer.id)

            logger.info(
                "Engaged user %d as %s (from %s). Active sessions: %d",
                scammer.id,
                persona["name"],
                source_group,
                self.antidetect._active_session_count,
            )
        except Exception:
            logger.exception("Failed to DM user %d", scammer.id)

    async def _handle_direct_message(self, event):
        """Process a reply from a scammer in DMs."""
        sender = await event.get_sender()
        if not sender or sender.id not in self.active_sessions:
            return

        message_text = event.message.text
        if not message_text:
            return

        # Reset silence timeout — scammer is still active
        self._reset_silence_timer(sender.id)

        session = self.active_sessions[sender.id]
        logger.info(
            "Scammer %d (turn %d/%d): %.80s",
            sender.id,
            session["turn_count"],
            self.config.max_turns,
            message_text,
        )

        # Check if we should continue
        should_continue, reason = should_continue_session(
            session["history"], session["intel"]
        )
        if not should_continue:
            await self._end_session(sender.id, outcome=reason)
            return

        if session["turn_count"] >= self.config.max_turns:
            await self._end_session(sender.id, outcome="max_turns")
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

            # Log this turn to Supabase
            try:
                log_turn(
                    scammer_id=str(sender.id),
                    persona_name=session["persona"]["name"],
                    turn_number=session["turn_count"],
                    scammer_message=message_text,
                    agent_reply=reply,
                    intel_this_turn=new_intel,
                )
            except Exception:
                logger.exception("Failed to log turn %d for user %d", session["turn_count"], sender.id)

            # Send reply with full anti-detection (typing, delays, possible correction)
            await self.antidetect.send_human_message(sender.id, reply)

            logger.info("Replied to scammer %d: %.80s", sender.id, reply)

        except Exception:
            logger.exception("Error in conversation with user %d", sender.id)
            await self._end_session(sender.id, outcome="error")

    def _reset_silence_timer(self, scammer_id: int):
        """Cancel the existing timeout and start a new 10-minute timer."""
        # Cancel existing timer if any
        existing = self._timeout_tasks.pop(scammer_id, None)
        if existing and not existing.done():
            existing.cancel()

        # Start new timer
        self._timeout_tasks[scammer_id] = asyncio.create_task(
            self._silence_timeout(scammer_id)
        )

    async def _silence_timeout(self, scammer_id: int):
        """End the session if the scammer doesn't reply within the timeout."""
        try:
            await asyncio.sleep(SILENCE_TIMEOUT_SECONDS)
            if scammer_id in self.active_sessions:
                logger.info(
                    "Silence timeout (%ds) for user %d — ending session.",
                    SILENCE_TIMEOUT_SECONDS,
                    scammer_id,
                )
                await self._end_session(scammer_id, outcome="abandoned")
        except asyncio.CancelledError:
            pass  # Timer was reset because scammer replied

    async def _end_session(self, scammer_id: int, outcome: str = "unknown"):
        """End a session, report results, and release rate limit slot."""
        session = self.active_sessions.pop(scammer_id, None)
        if not session:
            return

        # Cancel silence timer
        timeout_task = self._timeout_tasks.pop(scammer_id, None)
        if timeout_task and not timeout_task.done():
            timeout_task.cancel()

        self.antidetect.release_session()

        logger.info(
            "Ending session with user %d after %d turns. Outcome: %s. Active: %d",
            scammer_id,
            session["turn_count"],
            outcome,
            self.antidetect._active_session_count,
        )

        # Build transcript
        transcript_parts = []
        for msg in session["history"]:
            role = msg["role"]
            text = (
                msg["content"][0]["text"]
                if isinstance(msg["content"], list)
                else msg["content"]
            )
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
                outcome=outcome,
                source_group=session.get("source_group", "Unknown"),
            )
        except Exception:
            logger.exception("Failed to report session for user %d", scammer_id)


def run_monitor():
    """Entry point to run the monitor."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config = load_config()

    logger.info("HoneyTrap starting...")
    logger.info("  Groups configured: %d (%d active)", len(config.groups), len(config.active_groups))
    logger.info("  Max turns: %d", config.max_turns)
    logger.info("  Max concurrent sessions: %d", config.max_concurrent_sessions)
    logger.info("  Session mode: %s", "StringSession" if config.session_string else "file-based (dev)")

    monitor = HoneyTrapMonitor(config)
    asyncio.run(monitor.start())


if __name__ == "__main__":
    run_monitor()
