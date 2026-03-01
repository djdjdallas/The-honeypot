"""Push session results to Supabase."""

import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client

from .classifier import classify_scam

load_dotenv()
logger = logging.getLogger(__name__)


def _get_supabase():
    """Create a Supabase client."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def report_session(
    scammer_id: str,
    persona_name: str,
    transcript: str,
    intel: dict,
    trigger_message: str,
    started_at: str,
    turn_count: int,
) -> dict:
    """Report a completed session to Supabase.

    Creates records in sessions, wallets, and script_patterns tables.
    Returns the created session record.
    """
    supabase = _get_supabase()

    # Classify the scam
    classification = classify_scam(transcript)
    logger.info(
        "Classified as %s (%.0f%% confidence)",
        classification["scam_type"],
        classification["confidence"] * 100,
    )

    # Insert session
    session_data = {
        "scammer_id": scammer_id,
        "persona_used": persona_name,
        "transcript": transcript,
        "trigger_message": trigger_message,
        "scam_type": classification["scam_type"],
        "confidence": classification["confidence"],
        "key_tactics": classification["key_tactics"],
        "turn_count": turn_count,
        "wallets_found": len(intel.get("wallets", [])),
        "phishing_links": intel.get("phishing_links", []),
        "phones_found": intel.get("phones", []),
        "started_at": started_at,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
    }

    result = supabase.table("sessions").insert(session_data).execute()
    session_record = result.data[0] if result.data else {}
    session_id = session_record.get("id")
    logger.info("Session %s stored.", session_id)

    # Insert wallets
    for wallet in intel.get("wallets", []):
        wallet_data = {
            "address": wallet["address"],
            "chain": wallet["chain"],
            "session_id": session_id,
            "scammer_id": scammer_id,
            "first_seen": started_at,
        }
        try:
            supabase.table("wallets").upsert(
                wallet_data, on_conflict="address"
            ).execute()
            logger.info("Wallet stored: %s (%s)", wallet["address"][:12], wallet["chain"])
        except Exception:
            logger.exception("Failed to store wallet %s", wallet["address"][:12])

    # Insert script pattern
    if classification["key_tactics"]:
        pattern_data = {
            "session_id": session_id,
            "scam_type": classification["scam_type"],
            "tactics": classification["key_tactics"],
            "trigger_message": trigger_message,
            "transcript_excerpt": transcript[:2000],
        }
        try:
            supabase.table("script_patterns").insert(pattern_data).execute()
            logger.info("Script pattern stored for session %s", session_id)
        except Exception:
            logger.exception("Failed to store script pattern")

    return session_record
