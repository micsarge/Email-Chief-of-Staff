import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.reconcile import generate_reconciliation_report


def main() -> int:
    audit_log_path = ROOT / "app" / "audit_log.jsonl"
    report = generate_reconciliation_report(audit_log_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
