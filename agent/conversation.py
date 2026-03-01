"""Conversation engine using Amazon Nova Lite via Bedrock."""

import json
import logging

import boto3
from botocore.config import Config

from .extractor import extract_intel

logger = logging.getLogger(__name__)

MODEL_ID = "amazon.nova-lite-v1:0"
MAX_TOKENS = 150
TEMPERATURE = 0.8
MAX_TURNS = 20


def _get_bedrock_client():
    """Create a Bedrock Runtime client."""
    config = Config(
        retries={"max_attempts": 3, "mode": "adaptive"},
    )
    return boto3.client("bedrock-runtime", config=config)


def generate_response(
    persona: dict,
    conversation_history: list[dict],
    scammer_message: str,
) -> str:
    """Generate an in-character response to a scammer message.

    Args:
        persona: Persona dict from persona.py.
        conversation_history: List of {"role": "user"|"assistant", "content": str}.
        scammer_message: The latest message from the scammer.

    Returns:
        In-character response string.
    """
    client = _get_bedrock_client()

    messages = list(conversation_history)
    messages.append({"role": "user", "content": [{"text": scammer_message}]})

    system_prompt = (
        f"{persona['system_prompt']}\n\n"
        "IMPORTANT RULES:\n"
        "- Keep responses short (1-3 sentences), like real text messages.\n"
        "- Occasionally use casual language, abbreviations, or minor typos "
        "matching your persona's style.\n"
        "- Ask for specific details: wallet addresses, website links, "
        "platform names, phone numbers.\n"
        "- Show gradual interest but ask questions before agreeing to anything.\n"
        "- Never break character. Never mention AI, bots, or scams."
    )

    body = {
        "schemaVersion": "messages-v1",
        "system": [{"text": system_prompt}],
        "messages": messages,
        "inferenceConfig": {
            "maxTokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
        },
    }

    response = client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )

    result = json.loads(response["body"].read())
    reply = result["output"]["message"]["content"][0]["text"]

    logger.info("Generated reply: %s", reply[:80])
    return reply


def build_message(role: str, text: str) -> dict:
    """Build a message dict for the conversation history."""
    return {"role": role, "content": [{"text": text}]}


def should_continue_session(
    conversation_history: list[dict],
    all_extracted_intel: dict,
) -> tuple[bool, str]:
    """Decide whether to continue engaging the scammer.

    Returns:
        Tuple of (should_continue, reason).
        reason is one of: "max_turns", "wallet_extracted",
        "phishing_extracted", "intel_sufficient", or "" if continuing.
    """
    turn_count = len(conversation_history)

    if turn_count >= MAX_TURNS:
        logger.info("Max turns (%d) reached, ending session.", MAX_TURNS)
        return False, "max_turns"

    wallets = all_extracted_intel.get("wallets", [])
    links = all_extracted_intel.get("phishing_links", [])

    # Wallet extracted → mission accomplished
    if len(wallets) >= 1:
        logger.info(
            "Wallet address extracted at turn %d, ending session.", turn_count
        )
        return False, "wallet_extracted"

    # Phishing link extracted → mission accomplished
    if len(links) >= 1:
        logger.info(
            "Phishing link extracted at turn %d, ending session.", turn_count
        )
        return False, "phishing_extracted"

    return True, ""


def run_conversation_turn(
    persona: dict,
    conversation_history: list[dict],
    scammer_message: str,
) -> tuple[str, list[dict], dict]:
    """Run a single conversation turn.

    Returns:
        Tuple of (reply, updated_history, extracted_intel_from_this_turn).
    """
    intel = extract_intel(scammer_message)

    reply = generate_response(persona, conversation_history, scammer_message)

    updated_history = list(conversation_history)
    updated_history.append(build_message("user", scammer_message))
    updated_history.append(build_message("assistant", reply))

    return reply, updated_history, intel
