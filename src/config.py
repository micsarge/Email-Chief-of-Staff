import os
from pathlib import Path

from dotenv import load_dotenv

from src.proton_bridge import ProtonBridgeConfig


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def load_proton_bridge_config() -> ProtonBridgeConfig:
    return ProtonBridgeConfig.from_env()


def load_scan_mailboxes() -> list[str]:
    raw_value = os.getenv("PROTON_BRIDGE_SCAN_MAILBOXES", "INBOX,All Mail")
    mailboxes = [entry.strip() for entry in raw_value.split(",") if entry.strip()]
    return mailboxes or ["INBOX", "All Mail"]
