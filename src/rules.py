from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
import re
from typing import List, Optional

import yaml

from src.mailbox import MailMessage


DEFAULT_RULES_PAYLOAD = {
    "rules": [
        {
            "name": "delete-old-informed-delivery",
            "action": "delete",
            "reason": "Older informed delivery notifications can be cleaned up.",
            "match": {
                "keywords": ["informed delivery"],
                "date": "older-than-1-day",
            },
        },
        {
            "name": "delete-old-sender-notifications",
            "action": "delete",
            "reason": "Older notifications from selected senders can be cleaned up.",
            "match": {
                "providers": [
                    "nextdoor",
                    "homedepot",
                    "indeed",
                    "bose",
                    "Hulu",
                    "Bindertek",
                    "Olander Earthworks",
                    "Pensachi Company",
                    "Agilite",
                    "namecheap",
                    "Chase",
                ],
                "date": "older-than-1-day",
            },
        },
        {
            "name": "delete-old-usps-tracking",
            "action": "delete",
            "reason": "Past USPS tracking notices are no longer useful.",
            "match": {
                "keywords": ["usps tracking"],
                "date": "before-today",
            },
        },
        {
            "name": "archive-fcc-license-notice",
            "action": "archive",
            "reason": "Appears to be an official FCC notice that may not need to stay in the inbox.",
            "match": {
                "keywords": ["fcc", "license"],
            },
        },
        {
            "name": "move-non-affiliated-proton-mail",
            "action": "move",
            "target_folder": "Folders/Proton",
            "reason": "Route Proton-related mail to the Proton folder unless it is from your own accounts.",
            "match": {
                "providers": [
                    "no-reply@proton.me",
                    "no-reply@mail.proton.me",
                    "no-reply@notify.proton.me",
                ],
            },
        },
    ]
}


@dataclass
class RuleAction:
    action: str
    reason: str
    target_folder: Optional[str] = None


@dataclass
class RuleResult:
    message: MailMessage
    action: Optional[RuleAction]


class Rule:
    def __init__(self, name: str, predicate, action: RuleAction):
        self.name = name
        self.predicate = predicate
        self.action = action

    def applies(self, message: MailMessage) -> bool:
        return self.predicate(message)


class RuleEngine:
    def __init__(self, rules: Optional[List[Rule]] = None):
        self.rules = rules or []

    def evaluate(self, message: MailMessage) -> RuleResult:
        for rule in self.rules:
            if rule.applies(message):
                return RuleResult(message=message, action=rule.action)
        return RuleResult(message=message, action=None)

    def evaluate_many(self, messages: List[MailMessage]) -> List[RuleResult]:
        return [self.evaluate(message) for message in messages]


def load_rules_from_yaml(path: Optional[Path | str] = None) -> List[Rule]:
    if path is None:
        path = Path(__file__).resolve().parents[1] / "rules.yaml"

    path = Path(path)
    if not path.exists():
        return build_default_rules()

    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    if not isinstance(payload, dict):
        return build_default_rules()

    return build_rules_from_entries(payload.get("rules", []))


def build_rules_from_entries(entries: list[dict]) -> List[Rule]:
    rules = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("enabled", True) is False:
            continue
        action = entry.get("action", "none")
        rules.append(
            Rule(
                name=entry.get("name", "unnamed-rule"),
                predicate=lambda message, entry=entry: matches_rule(message, entry),
                action=RuleAction(
                    action=action,
                    reason=entry.get("reason", ""),
                    target_folder=entry.get("target_folder"),
                ),
            )
        )
    return rules


def matches_rule(message: MailMessage, entry: dict) -> bool:
    text = f"{message.subject} {message.sender} {message.preview}".lower()
    sender_text = (message.sender or "").lower()
    keywords = entry.get("match", {}).get("keywords", [])
    providers = entry.get("match", {}).get("providers", [])

    keyword_match = False
    if keywords:
        keyword_match = any(keyword.lower() in text for keyword in keywords)
    else:
        keyword_match = True

    provider_match = False
    if providers:
        provider_match = any(provider.lower() in sender_text for provider in providers)
    else:
        provider_match = True

    if not keyword_match or not provider_match:
        return False

    date_rule = entry.get("match", {}).get("date")
    if date_rule == "older-than-1-day":
        parsed_date = parse_message_date(message.date)
        if parsed_date is None:
            return False
        return parsed_date <= date.today() - timedelta(days=1)

    if date_rule == "before-today":
        subject = (message.subject or "").lower()
        match = re.search(r"(\d{4}-\d{2}-\d{2})", subject)
        if not match:
            return False
        try:
            subject_date = datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            return False
        return subject_date.date() < date.today()

    return True


def parse_message_date(message_date: str) -> Optional[date]:
    if not message_date:
        return None
    for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"]:
        try:
            return datetime.strptime(message_date.strip(), fmt).date()
        except ValueError:
            continue
    return None


def build_default_rules() -> List[Rule]:
    return build_rules_from_entries(DEFAULT_RULES_PAYLOAD.get("rules", []))
