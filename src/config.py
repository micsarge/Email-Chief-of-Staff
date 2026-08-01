from pathlib import Path

from dotenv import load_dotenv

from src.proton_bridge import ProtonBridgeConfig


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def load_proton_bridge_config() -> ProtonBridgeConfig:
    return ProtonBridgeConfig.from_env()
