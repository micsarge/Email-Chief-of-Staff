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

## Notes

Security and privacy are first-class design concerns. The current prototype avoids irreversible actions by default and requires explicit approval for destructive behavior. Review decisions are persisted locally so the dashboard can reflect prior choices during subsequent runs.
