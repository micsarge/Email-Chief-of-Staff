# Email Chief of Staff

Email Chief of Staff is a personal AI assistant concept for managing an inbox with a human-in-the-loop workflow. The goal is to connect to a Proton Mail account through Proton Bridge, summarize new messages, apply rules, and suggest actions such as move, archive, delete, or follow up.

## Vision

The assistant should behave less like a fully autonomous agent and more like a trusted chief of staff:

- monitor incoming mail
- summarize important updates
- recommend actions based on user-defined rules
- keep the user in control of sensitive decisions

## Current Scope

This repository now contains a working prototype for a human-in-the-loop inbox triage workflow. The MVP focuses on mailbox connectivity, rules-based recommendations, and a review dashboard that remembers approval or rejection decisions between requests.

## Proposed Architecture

- Mail integration layer for Proton Bridge via IMAP
- Rule engine for inbox triage and automation suggestions
- AI summarization layer for email understanding
- UI for reviewing recommended actions and approving them
- Local configuration and logging for privacy-conscious operation

## Getting Started

1. Review the roadmap and architecture notes.
2. Copy .env.example to .env and fill in your Proton Bridge values.
3. Install dependencies with pip install -r requirements.txt.
4. Run the review UI with python app/main.py.
5. Open http://127.0.0.1:5000/ to review recommendations and trigger the full-inbox cleanup action.
6. Use Clean Up Sunday from the dashboard on Sundays to permanently empty Trash.
7. Review the in-app audit log panel to confirm exactly what actions ran.
8. Run mailbox reconciliation with python scripts/reconcile_mailbox.py to compare live folder counts with recent audit events.

## Notes

Security and privacy are first-class design concerns. The current prototype requires explicit action for cleanup operations, moves deleted items to Trash first, and only permanently empties Trash through the Sunday-only cleanup flow. Review decisions are persisted locally so the dashboard can reflect prior choices during subsequent runs.

## Weekly Scheduler (Windows)

Use the script below to run automatic Trash purge every Sunday:

- Script: scripts/cleanup_sunday.py
- Reconciliation script: scripts/reconcile_mailbox.py
- Audit trail: app/audit_log.jsonl and the dashboard Audit Log panel

## Reconciliation API

- Endpoint: GET /api/reconcile
- Purpose: return live folder counts, recent audit events, and aggregated cleanup totals in one snapshot.

Example task registration command:

```powershell
schtasks /Create /TN "EmailChiefOfStaff-CleanUpSunday" /SC WEEKLY /D SUN /ST 09:00 /TR "\"C:\\Users\\micsa\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe\" \"C:\\Users\\micsa\\OneDrive\\Documents\\GitHub\\Email-Chief-of-Staff\\scripts\\cleanup_sunday.py\"" /F
```
