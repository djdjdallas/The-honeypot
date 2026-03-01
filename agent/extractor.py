"""Extract wallet addresses, phishing links, and phone numbers from text."""

import json
import logging
import re

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

# Wallet address patterns
WALLET_PATTERNS = {
    "ETH": re.compile(r"\b(0x[a-fA-F0-9]{40})\b"),
    "BTC_LEGACY": re.compile(r"\b([13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"),
    "BTC_BECH32": re.compile(r"\b(bc1[a-zA-HJ-NP-Z0-9]{25,62})\b"),
    "SOL": re.compile(r"\b([1-9A-HJ-NP-Za-km-z]{32,44})\b"),
    "TRX": re.compile(r"\b(T[a-zA-HJ-NP-Z1-9]{33})\b"),
}

# URL pattern for phishing link detection
URL_PATTERN = re.compile(
    r"https?://[^\s<>\"']+|"
    r"\b[a-zA-Z0-9][-a-zA-Z0-9]*\."
    r"(?:com|io|net|org|xyz|finance|exchange|trading|app|co|me|pro)"
    r"[^\s<>\"']*",
    re.IGNORECASE,
)

# Phone number patterns (international)
PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?"
    r"(?:\(?\d{2,4}\)?[-.\s]?)?"
    r"\d{3,4}[-.\s]?\d{3,4}"
)


def extract_wallets(text: str) -> list[dict]:
    """Extract cryptocurrency wallet addresses from text.

    Returns list of {"address": str, "chain": str}.
    """
    wallets = []
    seen = set()

    # ETH — must be exactly 42 chars starting with 0x
    for match in WALLET_PATTERNS["ETH"].finditer(text):
        addr = match.group(1)
        if addr not in seen:
            seen.add(addr)
            wallets.append({"address": addr, "chain": "ETH"})

    # BTC legacy — starts with 1 or 3
    for match in WALLET_PATTERNS["BTC_LEGACY"].finditer(text):
        addr = match.group(1)
        if addr not in seen and len(addr) >= 26:
            seen.add(addr)
            wallets.append({"address": addr, "chain": "BTC"})

    # BTC bech32 — starts with bc1
    for match in WALLET_PATTERNS["BTC_BECH32"].finditer(text):
        addr = match.group(1)
        if addr not in seen:
            seen.add(addr)
            wallets.append({"address": addr, "chain": "BTC"})

    # TRX — starts with T, 34 chars total
    for match in WALLET_PATTERNS["TRX"].finditer(text):
        addr = match.group(1)
        if addr not in seen:
            seen.add(addr)
            wallets.append({"address": addr, "chain": "TRX"})

    # SOL — base58, 32-44 chars (check after others to avoid false positives)
    for match in WALLET_PATTERNS["SOL"].finditer(text):
        addr = match.group(1)
        if addr not in seen and len(addr) >= 32 and not _is_common_word(addr):
            # Avoid matching BTC addresses already captured
            if not addr.startswith(("bc1", "0x", "T")):
                seen.add(addr)
                wallets.append({"address": addr, "chain": "SOL"})

    return wallets


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    urls = []
    for match in URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,;:!?)")
        urls.append(url)
    return urls


def extract_phones(text: str) -> list[str]:
    """Extract phone numbers from text."""
    phones = []
    for match in PHONE_PATTERN.finditer(text):
        phone = match.group(0).strip()
        # Filter out numbers that are too short to be phone numbers
        digits = re.sub(r"\D", "", phone)
        if len(digits) >= 10:
            phones.append(phone)
    return phones


def classify_urls_with_nova(urls: list[str]) -> list[str]:
    """Use Nova to classify which URLs are likely phishing links.

    Returns list of URLs classified as suspicious.
    """
    if not urls:
        return []

    client = boto3.client(
        "bedrock-runtime",
        config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
    )

    prompt = (
        "You are a cybersecurity analyst. Given these URLs found in a suspected "
        "crypto scam conversation, classify which are likely phishing or scam links. "
        "Return ONLY a JSON array of the suspicious URLs. If none are suspicious, "
        "return an empty array [].\n\n"
        f"URLs: {json.dumps(urls)}"
    )

    body = {
        "schemaVersion": "messages-v1",
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": 200, "temperature": 0.1},
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

        # Extract JSON array from response
        array_match = re.search(r"\[.*?\]", text, re.DOTALL)
        if array_match:
            return json.loads(array_match.group(0))
    except Exception:
        logger.exception("Failed to classify URLs with Nova")

    # Fallback: treat all URLs as suspicious
    return urls


def extract_intel(text: str) -> dict:
    """Extract all intelligence from a text message.

    Returns dict with keys: wallets, urls, phishing_links, phones.
    """
    wallets = extract_wallets(text)
    urls = extract_urls(text)
    phones = extract_phones(text)

    phishing_links = []
    if urls:
        try:
            phishing_links = classify_urls_with_nova(urls)
        except Exception:
            logger.exception("Phishing classification failed, using raw URLs")
            phishing_links = urls

    return {
        "wallets": wallets,
        "urls": urls,
        "phishing_links": phishing_links,
        "phones": phones,
    }


def merge_intel(existing: dict, new: dict) -> dict:
    """Merge new intel into existing intel dict, deduplicating."""
    merged = {
        "wallets": list(existing.get("wallets", [])),
        "urls": list(existing.get("urls", [])),
        "phishing_links": list(existing.get("phishing_links", [])),
        "phones": list(existing.get("phones", [])),
    }

    existing_addrs = {w["address"] for w in merged["wallets"]}
    for w in new.get("wallets", []):
        if w["address"] not in existing_addrs:
            merged["wallets"].append(w)
            existing_addrs.add(w["address"])

    existing_urls = set(merged["urls"])
    for u in new.get("urls", []):
        if u not in existing_urls:
            merged["urls"].append(u)
            existing_urls.add(u)

    existing_phishing = set(merged["phishing_links"])
    for p in new.get("phishing_links", []):
        if p not in existing_phishing:
            merged["phishing_links"].append(p)
            existing_phishing.add(p)

    existing_phones = set(merged["phones"])
    for p in new.get("phones", []):
        if p not in existing_phones:
            merged["phones"].append(p)
            existing_phones.add(p)

    return merged


def _is_common_word(s: str) -> bool:
    """Check if a string is likely a common word rather than a wallet address."""
    # Very short base58-like strings are probably not SOL addresses
    if len(s) < 32:
        return True
    # If it contains only lowercase or only uppercase, less likely an address
    if s.isalpha():
        return True
    return False
