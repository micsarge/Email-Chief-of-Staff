import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def append_audit_event(log_path: Path, event_type: str, details: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "details": details,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def read_recent_audit_events(log_path: Path, limit: int = 25) -> list[dict[str, Any]]:
    if not log_path.exists() or log_path.stat().st_size == 0:
        return []

    events: list[dict[str, Any]] = []
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return list(reversed(events[-limit:]))