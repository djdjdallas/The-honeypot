"""Anti-detection layer for human-like Telegram behavior.

Telegram monitors account patterns and flags bots. This module makes the
agent behave like a real person by introducing:
  - Variable response delays based on message length
  - Typing action simulation proportional to reply length
  - Occasional self-corrections ("*correction" messages)
  - Rate limiting on concurrent conversations
  - Jitter on all timing to avoid detectable periodicity
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field

from telethon import TelegramClient
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction, SendMessageCancelAction

logger = logging.getLogger(__name__)

# --- Timing constants (seconds) ---

# Base delay before the agent starts "reading" a message
_READ_DELAY_MIN = 1.5
_READ_DELAY_MAX = 4.0

# Typing speed simulation: seconds per character of the reply
_TYPING_SPEED_MIN = 0.03  # ~33 chars/sec (fast texter)
_TYPING_SPEED_MAX = 0.08  # ~12 chars/sec (slow texter)

# Additional random pause after "typing" completes (thumb hesitation)
_POST_TYPING_PAUSE_MIN = 0.5
_POST_TYPING_PAUSE_MAX = 2.0

# Minimum/maximum total delay (floor and ceiling)
_TOTAL_DELAY_FLOOR = 3.0
_TOTAL_DELAY_CEILING = 25.0

# Cooldown between any two outbound messages (regardless of recipient)
_GLOBAL_SEND_COOLDOWN = 2.0

# Self-correction probability (chance of sending a "typo correction")
_CORRECTION_PROBABILITY = 0.08  # ~8% of messages

# Maximum concurrent active conversations
MAX_CONCURRENT_SESSIONS = 3

# Minimum gap before engaging a new scammer (seconds)
NEW_SESSION_COOLDOWN = 30.0


# --- Typo / correction data ---

_TYPO_CORRECTIONS = [
    ("teh", "the"),
    ("adn", "and"),
    ("taht", "that"),
    ("hwo", "how"),
    ("waht", "what"),
    ("yuo", "you"),
    ("woudl", "would"),
    ("jsut", "just"),
    ("dont", "don't"),
    ("cant", "can't"),
    ("im", "I'm"),
    ("thier", "their"),
    ("recieve", "receive"),
    ("definately", "definitely"),
    ("wierd", "weird"),
]


@dataclass
class AntiDetect:
    """Manages human-like timing and behavior for a Telegram client.

    Usage:
        ad = AntiDetect(client)
        await ad.send_human_message(peer, "Hello!")
        if ad.can_start_new_session():
            ...
    """

    client: TelegramClient
    _last_send_time: float = 0.0
    _last_new_session_time: float = 0.0
    _active_session_count: int = 0
    _persona_speed: float = field(default_factory=lambda: random.uniform(0.6, 1.4))

    async def send_human_message(self, peer, text: str) -> str:
        """Send a message with human-like delays and typing simulation.

        May inject a typo correction as a follow-up message (~8% chance).
        Returns the text actually sent (may differ if correction was applied).
        """
        # 1. "Reading" delay — simulate reading the scammer's message
        read_delay = random.uniform(_READ_DELAY_MIN, _READ_DELAY_MAX) * self._persona_speed
        await asyncio.sleep(read_delay)

        # 2. Decide whether to inject a typo + correction
        will_correct = random.random() < _CORRECTION_PROBABILITY
        typo_text = text
        correction_text = None

        if will_correct:
            typo_text, correction_text = self._inject_typo(text)

        # 3. Simulate typing for the message length
        await self._simulate_typing(peer, typo_text)

        # 4. Respect global send cooldown
        await self._enforce_send_cooldown()

        # 5. Send the message
        await self.client.send_message(peer, typo_text)
        self._last_send_time = time.monotonic()
        logger.debug("Sent message to %s (%d chars)", peer, len(typo_text))

        # 6. If correcting, wait briefly then send correction
        if correction_text:
            correction_delay = random.uniform(1.5, 4.0)
            await asyncio.sleep(correction_delay)
            await self._simulate_typing(peer, correction_text)
            await self.client.send_message(peer, correction_text)
            self._last_send_time = time.monotonic()
            logger.debug("Sent correction to %s: %s", peer, correction_text)
            return typo_text  # Return original typo text (correction is separate)

        return typo_text

    async def _simulate_typing(self, peer, text: str):
        """Show 'typing...' indicator for a realistic duration."""
        char_count = len(text)
        speed = random.uniform(_TYPING_SPEED_MIN, _TYPING_SPEED_MAX) * self._persona_speed
        typing_duration = char_count * speed
        post_pause = random.uniform(_POST_TYPING_PAUSE_MIN, _POST_TYPING_PAUSE_MAX)

        total = typing_duration + post_pause
        total = max(_TOTAL_DELAY_FLOOR - 2.0, min(total, _TOTAL_DELAY_CEILING - 2.0))

        try:
            await self.client(SetTypingRequest(
                peer=peer,
                action=SendMessageTypingAction(),
            ))
        except Exception:
            logger.debug("Failed to set typing action (non-critical)")

        # Sleep in chunks, refreshing typing indicator every 5s (Telegram timeout)
        elapsed = 0.0
        while elapsed < total:
            chunk = min(5.0, total - elapsed)
            await asyncio.sleep(chunk)
            elapsed += chunk
            if elapsed < total:
                try:
                    await self.client(SetTypingRequest(
                        peer=peer,
                        action=SendMessageTypingAction(),
                    ))
                except Exception:
                    pass

        # Cancel typing indicator
        try:
            await self.client(SetTypingRequest(
                peer=peer,
                action=SendMessageCancelAction(),
            ))
        except Exception:
            pass

    async def _enforce_send_cooldown(self):
        """Wait if needed to respect the global send cooldown."""
        now = time.monotonic()
        elapsed = now - self._last_send_time
        if elapsed < _GLOBAL_SEND_COOLDOWN:
            wait = _GLOBAL_SEND_COOLDOWN - elapsed + random.uniform(0.1, 0.5)
            await asyncio.sleep(wait)

    def _inject_typo(self, text: str) -> tuple[str, str]:
        """Inject a plausible typo and return (typo_text, correction_message).

        Picks a random word in the text and swaps it for a common typo.
        The correction is a natural follow-up like "*the" or "sorry, *the".
        """
        words = text.split()
        if len(words) < 3:
            # Too short to make a natural typo
            return text, None

        # Try to find a word we have a typo mapping for
        for correct, typo in random.sample(_TYPO_CORRECTIONS, min(5, len(_TYPO_CORRECTIONS))):
            for i, word in enumerate(words):
                stripped = word.strip(".,!?;:'\"")
                if stripped.lower() == correct:
                    typo_word = word.replace(stripped, typo, 1)
                    typo_words = list(words)
                    typo_words[i] = typo_word
                    typo_text = " ".join(typo_words)
                    correction = random.choice([
                        f"*{correct}",
                        f"*{correct} sorry",
                        f"oops *{correct}",
                        f"*{correct} lol",
                    ])
                    return typo_text, correction

        # No applicable typo found — skip correction
        return text, None

    def can_start_new_session(self) -> bool:
        """Check if we can engage a new scammer without triggering rate limits."""
        now = time.monotonic()

        if self._active_session_count >= MAX_CONCURRENT_SESSIONS:
            logger.info(
                "Rate limit: %d/%d concurrent sessions, deferring new engagement.",
                self._active_session_count,
                MAX_CONCURRENT_SESSIONS,
            )
            return False

        if now - self._last_new_session_time < NEW_SESSION_COOLDOWN:
            remaining = NEW_SESSION_COOLDOWN - (now - self._last_new_session_time)
            logger.info(
                "Rate limit: new session cooldown (%.0fs remaining).",
                remaining,
            )
            return False

        return True

    def register_new_session(self):
        """Record that a new session has started."""
        self._active_session_count += 1
        self._last_new_session_time = time.monotonic()
        logger.info("Session started. Active: %d", self._active_session_count)

    def release_session(self):
        """Record that a session has ended."""
        self._active_session_count = max(0, self._active_session_count - 1)
        logger.info("Session ended. Active: %d", self._active_session_count)

    def set_persona_speed(self, knowledge_level: str):
        """Adjust typing speed based on persona's tech literacy.

        Novice personas type slower; intermediate personas type at normal speed.
        """
        if knowledge_level == "novice":
            self._persona_speed = random.uniform(1.1, 1.6)  # slower
        elif knowledge_level == "intermediate":
            self._persona_speed = random.uniform(0.8, 1.1)  # moderate
        else:
            self._persona_speed = random.uniform(0.9, 1.3)  # default range
        logger.debug("Persona speed factor: %.2f", self._persona_speed)
