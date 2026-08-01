# Roadmap

## Phase 0 — Foundation
- Create the repository structure and core documentation
- Define the product scope and success criteria
- Establish a safe, human-in-the-loop workflow for inbox actions

## Phase 1 — Mail Connectivity
- Connect to a Proton Mail account through Proton Bridge
- Validate IMAP access and basic mailbox reading
- Build configuration for mailbox credentials and folders

## Phase 2 — Inbox Triage
- Summarize new emails and extract action items
- Add a rules engine for simple categorization and recommendations
- Support examples such as deleting older USPS informed delivery notices

## Phase 3 — Review UI
- Build a lightweight UI for showing summaries and suggested actions
- Allow users to approve or reject recommendations
- Track action history for transparency
- Persist review decisions locally so approvals and rejections survive refreshes and restarts
- Support full-inbox scanning and one-click cleanup of matching messages based on rules

## Phase 4 — Reliability and Safety
- Add logging, error handling, retry behavior, and audit trails
- Introduce sandboxing and confirmation rules for destructive actions
- Improve the rule language and user customization options

## Phase 5 — Expansion
- Add richer summarization, follow-up drafting, and workflow automation
- Explore deeper integrations while keeping privacy and user control central
