# Email Chief of Staff

Email Chief of Staff is a personal AI assistant concept for managing an inbox with a human-in-the-loop workflow. The goal is to connect to a Proton Mail account through Proton Bridge, summarize new messages, apply rules, and suggest actions such as move, archive, delete, or follow up.

## Vision

The assistant should behave less like a fully autonomous agent and more like a trusted chief of staff:

- monitor incoming mail
- summarize important updates
- recommend actions based on user-defined rules
- keep the user in control of sensitive decisions

## Current Scope

This repository currently contains project scaffolding and planning documents for the MVP. The first milestones focus on mailbox connectivity, summarization, and safe rule execution rather than fully autonomous deletion or reply behavior.

## Proposed Architecture

- Mail integration layer for Proton Bridge via IMAP
- Rule engine for inbox triage and automation suggestions
- AI summarization layer for email understanding
- UI for reviewing recommended actions and approving them
- Local configuration and logging for privacy-conscious operation

## Getting Started

1. Review the roadmap and architecture notes.
2. Set up Proton Bridge and your mailbox access details.
3. Implement the mail connector and basic rules engine.
4. Add a simple UI for reviewing recommendations.

## Notes

Security and privacy are first-class design concerns. The initial version should avoid irreversible actions by default and require explicit approval for destructive behavior.
