"""Configuration system for HoneyTrap target groups and agent settings.

Loads configuration from:
  1. A YAML config file (groups.yaml) for group definitions
  2. Environment variables for secrets and overrides

Config file is optional — groups can be specified via MONITOR_GROUPS env var
as a comma-separated list for simple deployments (e.g. Lambda).
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent


@dataclass
class GroupConfig:
    """Configuration for a single monitored Telegram group."""

    identifier: str  # Username, invite link, or numeric ID
    name: str = ""  # Human-readable label
    active: bool = True
    preferred_persona: str | None = None  # Force a specific persona, or None for random
    notes: str = ""

    @property
    def display_name(self) -> str:
        return self.name or self.identifier


@dataclass
class AgentConfig:
    """Top-level agent configuration."""

    # Telegram credentials
    api_id: int = 0
    api_hash: str = ""
    session_string: str = ""  # StringSession for production (Lambda)
    phone: str = ""  # Fallback for local dev only

    # Agent behavior
    max_turns: int = 20
    max_concurrent_sessions: int = 3
    new_session_cooldown: float = 30.0

    # Target groups
    groups: list[GroupConfig] = field(default_factory=list)

    @property
    def active_groups(self) -> list[GroupConfig]:
        return [g for g in self.groups if g.active]


def load_config() -> AgentConfig:
    """Load agent configuration from environment variables and config file.

    Priority:
      - Environment variables always win for secrets
      - groups.yaml provides group definitions (if present)
      - MONITOR_GROUPS env var is a fallback for group list
    """
    config = AgentConfig()

    # --- Telegram credentials (always from env) ---
    api_id_raw = os.getenv("TELEGRAM_API_ID", "")
    if api_id_raw:
        try:
            config.api_id = int(api_id_raw)
        except ValueError:
            logger.error("TELEGRAM_API_ID must be an integer, got: %r", api_id_raw)

    config.api_hash = os.getenv("TELEGRAM_API_HASH", "")
    config.session_string = os.getenv("TELEGRAM_SESSION_STRING", "")
    config.phone = os.getenv("TELEGRAM_PHONE", "")

    # --- Agent behavior (env overrides) ---
    config.max_turns = int(os.getenv("MAX_TURNS_PER_SESSION", "20"))
    config.max_concurrent_sessions = int(os.getenv("MAX_CONCURRENT_SESSIONS", "3"))
    config.new_session_cooldown = float(os.getenv("NEW_SESSION_COOLDOWN", "30.0"))

    # --- Groups ---
    config.groups = _load_groups()

    # Validation
    if not config.api_id or not config.api_hash:
        logger.warning("TELEGRAM_API_ID / TELEGRAM_API_HASH not set.")

    if not config.session_string and not config.phone:
        logger.warning(
            "Neither TELEGRAM_SESSION_STRING nor TELEGRAM_PHONE set. "
            "Run scripts/generate_session.py to create a session string."
        )

    if not config.groups:
        logger.warning("No target groups configured.")

    return config


def _load_groups() -> list[GroupConfig]:
    """Load groups from groups.yaml, falling back to MONITOR_GROUPS env var."""
    groups = []

    # Try YAML config file first
    config_path = CONFIG_DIR / "groups.yaml"
    if config_path.exists():
        groups = _load_groups_from_yaml(config_path)
        if groups:
            logger.info("Loaded %d groups from %s", len(groups), config_path)
            return groups

    # Fallback: MONITOR_GROUPS env var (comma-separated identifiers)
    env_groups = os.getenv("MONITOR_GROUPS", "")
    if env_groups:
        for identifier in env_groups.split(","):
            identifier = identifier.strip()
            if identifier:
                groups.append(GroupConfig(identifier=identifier))
        logger.info("Loaded %d groups from MONITOR_GROUPS env var", len(groups))

    return groups


def _load_groups_from_yaml(path: Path) -> list[GroupConfig]:
    """Parse groups.yaml into a list of GroupConfig objects."""
    try:
        import yaml
    except ImportError:
        logger.warning(
            "PyYAML not installed — cannot read groups.yaml. "
            "Install with: pip install pyyaml"
        )
        return []

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except Exception:
        logger.exception("Failed to parse %s", path)
        return []

    if not isinstance(data, dict) or "groups" not in data:
        logger.error("groups.yaml must have a top-level 'groups' key")
        return []

    groups = []
    for entry in data["groups"]:
        if isinstance(entry, str):
            groups.append(GroupConfig(identifier=entry))
        elif isinstance(entry, dict):
            groups.append(GroupConfig(
                identifier=str(entry.get("id", entry.get("identifier", ""))),
                name=str(entry.get("name", "")),
                active=bool(entry.get("active", True)),
                preferred_persona=entry.get("persona"),
                notes=str(entry.get("notes", "")),
            ))
    return groups
