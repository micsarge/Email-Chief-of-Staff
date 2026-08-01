# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Initial repository scaffolding for the Email Chief of Staff concept
- Project README, roadmap, and architecture documents
- Basic folder structure for source code, docs, and future UI work
- Local persistence for review approvals and rejections in the dashboard workflow
- Regression tests covering persisted review state behavior
- Full-inbox scanning and one-click cleanup of messages that match the configured rules
- External YAML rules configuration for recommendation and cleanup behavior
- Sunday-only trash purge endpoint and dashboard action ("Clean Up Sunday")
- Weekly Windows scheduled task support using `scripts/cleanup_sunday.py`
- Reconciliation API (`/api/reconcile`) and script (`scripts/reconcile_mailbox.py`) for mailbox-vs-audit snapshots
- In-app audit log panel backed by JSONL audit events

### Changed
- Delete actions now move messages to Trash before expunging from INBOX
- Proton Bridge config now supports `PROTON_BRIDGE_TRASH_MAILBOX`

### Fixed
- Cleanup flows now skip stale IMAP message IDs instead of failing the full request
- Improved status visibility and summary feedback during cleanup operations in the dashboard

## [0.1.0] - 2026-07-31

### Added
- Created the initial project structure
- Documented the product vision and phased roadmap
- Added a starter .gitignore file for Python and editor artifacts
