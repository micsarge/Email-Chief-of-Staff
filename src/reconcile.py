from pathlib import Path

from src.audit_log import append_audit_event, read_recent_audit_events
from src.config import load_proton_bridge_config
from src.proton_bridge import ProtonBridgeClient


def _mailbox_names(imap_connection) -> list[str]:
    status, mailbox_lines = imap_connection.list()
    if status != "OK":
        return []

    names: list[str] = []
    for raw in mailbox_lines or []:
        line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        if '" "/" "' in line:
            name = line.split('" "/" "')[-1].rstrip('"')
        else:
            name = line.rsplit(" ", 1)[-1].strip('"')
        if name:
            names.append(name)
    return names


def _count_folder(client: ProtonBridgeClient, folder_name: str) -> dict:
    selected = client._select_mailbox(folder_name)
    if selected[0] != "OK":
        return {"folder": folder_name, "available": False, "messageCount": 0}

    imap_connection = client._ensure_imap()
    status, ids = imap_connection.search(None, "UNDELETED")
    if status != "OK":
        return {"folder": folder_name, "available": True, "messageCount": 0}

    count = len(ids[0].split()) if ids and ids[0] else 0
    return {"folder": folder_name, "available": True, "messageCount": count}


def _summarize_audit(events: list[dict]) -> dict:
    summary = {
        "cleanupRuns": 0,
        "cleanupApplied": 0,
        "cleanupDelete": 0,
        "cleanupArchive": 0,
        "cleanupRespond": 0,
        "sundayPurges": 0,
        "sundayPurgedMessages": 0,
        "latestEvent": events[0]["timestamp"] if events else None,
    }

    for event in events:
        event_type = event.get("event")
        details = event.get("details") or {}
        if event_type == "cleanup_inbox":
            summary["cleanupRuns"] += 1
            summary["cleanupApplied"] += int(details.get("applied", 0) or 0)
            counts = details.get("counts") or {}
            summary["cleanupDelete"] += int(counts.get("delete", 0) or 0)
            summary["cleanupArchive"] += int(counts.get("archive", 0) or 0)
            summary["cleanupRespond"] += int(counts.get("respond", 0) or 0)
        if event_type in {"cleanup_sunday", "scheduled_cleanup_sunday"}:
            summary["sundayPurges"] += 1
            summary["sundayPurgedMessages"] += int(details.get("purged", 0) or 0)

    return summary


def generate_reconciliation_report(audit_log_path: Path) -> dict:
    cfg = load_proton_bridge_config()
    client = ProtonBridgeClient(cfg)
    imap = client.connect_imap()

    folder_counts = []
    mailbox_names = _mailbox_names(imap)
    targets = [cfg.mailbox, cfg.trash_mailbox, "Archive", "Spam", "Sent"]
    for mailbox in mailbox_names:
        lower_name = mailbox.lower()
        if "all mail" in lower_name and mailbox not in targets:
            targets.append(mailbox)

    seen = set()
    deduped_targets = []
    for target in targets:
        if target not in seen:
            seen.add(target)
            deduped_targets.append(target)

    for target in deduped_targets:
        folder_counts.append(_count_folder(client, target))

    recent_events = read_recent_audit_events(audit_log_path, limit=100)
    audit_summary = _summarize_audit(recent_events)

    report = {
        "folderCounts": folder_counts,
        "auditSummary": audit_summary,
        "recentAuditEvents": recent_events[:20],
        "mailboxesSeen": mailbox_names,
    }

    append_audit_event(
        audit_log_path,
        "reconciliation_snapshot",
        {
            "summary": "Generated mailbox reconciliation snapshot.",
            "folder_counts": folder_counts,
            "audit_summary": audit_summary,
        },
    )

    return report