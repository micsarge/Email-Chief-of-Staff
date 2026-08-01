from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audit_log import append_audit_event
from src.config import load_proton_bridge_config
from src.proton_bridge import ProtonBridgeClient


def main() -> int:
    today = datetime.now().date()
    if today.weekday() != 6:
        append_audit_event(
            Path(__file__).resolve().parents[1] / "app" / "audit_log.jsonl",
            "scheduled_cleanup_sunday_skipped",
            {
                "today": today.isoformat(),
                "summary": "Scheduled trash purge skipped because today is not Sunday.",
            },
        )
        print("Skipped: today is not Sunday.")
        return 0

    cfg = load_proton_bridge_config()
    client = ProtonBridgeClient(cfg)
    purged = client.purge_trash()

    append_audit_event(
        Path(__file__).resolve().parents[1] / "app" / "audit_log.jsonl",
        "scheduled_cleanup_sunday",
        {
            "today": today.isoformat(),
            "purged": purged,
            "summary": f"Scheduled Sunday purge removed {purged} message(s) from Trash.",
        },
    )

    print(f"Purged {purged} message(s) from Trash.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
