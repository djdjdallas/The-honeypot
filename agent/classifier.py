"""Classify scam type from conversation transcripts using Amazon Nova."""

import json
import logging
import re

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

SCAM_TYPES = [
    "pig_butchering",
    "fake_exchange",
    "pump_dump",
    "rug_pull",
    "giveaway_scam",
    "recovery_scam",
    "romance_crypto",
    "other",
]

CLASSIFICATION_PROMPT = """\
You are a cryptocurrency scam classification expert. Analyze the following \
conversation transcript between a scammer and a potential victim.

Classify the scam into exactly ONE of these types:
- pig_butchering: Long-con investment scam building trust over time, often with fake trading platforms
- fake_exchange: Directing victim to a fraudulent exchange or trading platform
- pump_dump: Promoting a token to inflate price before selling
- rug_pull: Promoting a new token/project that will be abandoned after collecting funds
- giveaway_scam: Fake giveaway requiring upfront payment or wallet connection
- recovery_scam: Offering to recover previously lost crypto funds for a fee
- romance_crypto: Romantic manipulation leading to crypto investment requests
- other: Does not fit the above categories

Respond with ONLY valid JSON in this exact format:
{
  "scam_type": "<type>",
  "confidence": <0.0-1.0>,
  "key_tactics": ["tactic1", "tactic2", "tactic3"]
}

TRANSCRIPT:
"""


def classify_scam(transcript: str) -> dict:
    """Classify a conversation transcript into a scam type.

    Args:
        transcript: Full conversation text.

    Returns:
        Dict with scam_type, confidence, and key_tactics.
    """
    client = boto3.client(
        "bedrock-runtime",
        config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
    )

    body = {
        "schemaVersion": "messages-v1",
        "messages": [
            {
                "role": "user",
                "content": [{"text": CLASSIFICATION_PROMPT + transcript}],
            }
        ],
        "inferenceConfig": {"maxTokens": 300, "temperature": 0.1},
    }

    try:
        response = client.invoke_model(
            modelId="amazon.nova-lite-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        result = json.loads(response["body"].read())
        text = result["output"]["message"]["content"][0]["text"]

        # Extract JSON from response
        json_match = re.search(r"\{.*?\}", text, re.DOTALL)
        if json_match:
            classification = json.loads(json_match.group(0))

            # Validate scam_type
            if classification.get("scam_type") not in SCAM_TYPES:
                classification["scam_type"] = "other"

            # Clamp confidence
            confidence = float(classification.get("confidence", 0.5))
            classification["confidence"] = max(0.0, min(1.0, confidence))

            # Ensure key_tactics is a list
            if not isinstance(classification.get("key_tactics"), list):
                classification["key_tactics"] = []

            return classification

    except Exception:
        logger.exception("Scam classification failed")

    return {
        "scam_type": "other",
        "confidence": 0.0,
        "key_tactics": [],
    }


def classify_initial_message(message: str) -> dict:
    """Quick classification of a single message to detect scam solicitation.

    Returns dict with is_scam (bool) and reason (str).
    """
    client = boto3.client(
        "bedrock-runtime",
        config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
    )

    prompt = (
        "You are a crypto scam detection system. Analyze this Telegram message "
        "and determine if it is a scam solicitation (someone trying to lure victims "
        "into a crypto scam). Consider: unsolicited investment offers, guaranteed "
        "returns, urgency tactics, requests to DM, fake giveaways, recovery scam "
        "offers.\n\n"
        "Respond with ONLY valid JSON:\n"
        '{"is_scam": true/false, "reason": "brief explanation"}\n\n'
        f"MESSAGE: {message}"
    )

    body = {
        "schemaVersion": "messages-v1",
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": 100, "temperature": 0.1},
    }

    try:
        response = client.invoke_model(
            modelId="amazon.nova-lite-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        result = json.loads(response["body"].read())
        text = result["output"]["message"]["content"][0]["text"]

        json_match = re.search(r"\{.*?\}", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception:
        logger.exception("Initial message classification failed")

    return {"is_scam": False, "reason": "classification failed"}


# Keyword-based pre-filter (fast, before calling Nova)
SCAM_KEYWORDS = [
    "guaranteed returns",
    "guaranteed profit",
    "100% safe",
    "risk free",
    "double your",
    "send me",
    "minimum investment",
    "dm me",
    "dm for",
    "message me",
    "whatsapp",
    "recover your",
    "lost funds",
    "mining pool",
    "liquidity pool",
    "airdrop",
    "free crypto",
    "free bitcoin",
    "free eth",
    "connect your wallet",
    "validate your wallet",
    "sync your wallet",
    "trading signal",
    "forex crypto",
    "passive income",
    "daily returns",
    "weekly returns",
    "withdrawal fee",
    "tax fee",
    "gas fee to withdraw",
]


def keyword_prefilter(message: str, min_matches: int = 2) -> bool:
    """Quick keyword check before calling Nova.

    Returns True only if at least *min_matches* distinct keywords are found.
    This avoids false-positive engagements from casual messages that happen
    to contain a single common phrase.
    """
    lower = message.lower()
    match_count = sum(1 for kw in SCAM_KEYWORDS if kw in lower)
    return match_count >= min_matches
