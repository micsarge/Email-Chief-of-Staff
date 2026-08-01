import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.mailbox import MailMessage
from src.rules import RuleAction, RuleResult


@dataclass
class ReviewItem:
    message: MailMessage
    result: RuleResult
    approved: Optional[bool] = None


class ReviewQueue:
    def __init__(self, items: Optional[List[ReviewItem]] = None, state_path: Optional[str] = None):
        self.items = list(items or [])
        self.state_path = Path(state_path) if state_path else None
        if self.state_path is not None and not self.items:
            self.load_state(hydrate_items=False)

    def add(self, item: ReviewItem) -> None:
        self.items.append(item)

    def save_state(self) -> None:
        if self.state_path is None:
            return

        payload = []
        for item in self.items:
            payload.append(
                {
                    "message_id": item.message.id,
                    "subject": item.message.subject,
                    "sender": item.message.sender,
                    "date": item.message.date,
                    "preview": item.message.preview,
                    "action": item.result.action.action if item.result.action else None,
                    "reason": item.result.action.reason if item.result.action else None,
                    "approved": item.approved,
                }
            )

        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def load_state(self, hydrate_items: bool = True) -> dict:
        if self.state_path is None or not self.state_path.exists():
            return {}

        if self.state_path.stat().st_size == 0:
            return {}

        with self.state_path.open("r", encoding="utf-8") as handle:
            try:
                payload = json.load(handle)
            except json.JSONDecodeError:
                return {}

        if not isinstance(payload, list):
            return {}

        state_by_id = {}
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            message_id = entry.get("message_id")
            if not message_id:
                continue
            state_by_id[message_id] = entry.get("approved")

        if hydrate_items and not self.items:
            for entry in payload:
                if not isinstance(entry, dict):
                    continue
                message = MailMessage(
                    id=entry.get("message_id", ""),
                    subject=entry.get("subject", ""),
                    sender=entry.get("sender", ""),
                    date=entry.get("date", ""),
                    preview=entry.get("preview", ""),
                )
                action = None
                if entry.get("action"):
                    action = RuleAction(action=entry.get("action"), reason=entry.get("reason") or "")
                result = RuleResult(message=message, action=action)
                self.items.append(ReviewItem(message=message, result=result, approved=entry.get("approved")))
            return state_by_id

        for item in self.items:
            if item.message.id in state_by_id:
                item.approved = state_by_id[item.message.id]
        return state_by_id

    def pending(self) -> List[ReviewItem]:
        return [item for item in self.items if item.approved is None]

    def approve(self, message_id: str) -> bool:
        for item in self.items:
            if item.message.id == message_id:
                item.approved = True
                self.save_state()
                return True
        return False

    def reject(self, message_id: str) -> bool:
        for item in self.items:
            if item.message.id == message_id:
                item.approved = False
                self.save_state()
                return True
        return False

    def to_summary(self) -> List[dict]:
        return [
            {
                "id": item.message.id,
                "subject": item.message.subject,
                "sender": item.message.sender,
                "action": item.result.action.action if item.result.action else "none",
                "reason": item.result.action.reason if item.result.action else "",
                "status": "pending" if item.approved is None else ("approved" if item.approved else "rejected"),
            }
            for item in self.items
        ]
