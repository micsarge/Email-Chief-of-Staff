from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
import re
from typing import List, Optional

import yaml

from src.mailbox import MailMessage


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

    rules = []
    for entry in payload.get("rules", []):
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
        subject = message.subject.lower()
        token = subject.split("usps tracking")[-1].strip() if "usps tracking" in subject else ""
        if not token:
            return False
        try:
            subject_date = datetime.strptime(token, "%Y-%m-%d")
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
    def is_old_informed_delivery(message: MailMessage) -> bool:
        text = f"{message.subject} {message.sender} {message.preview}".lower()
        if "informed delivery" not in text and "usps" not in text:
            return False
        parsed_date = parse_message_date(message.date)
        if parsed_date is None:
            return False
        return parsed_date <= date.today() - timedelta(days=1)

    def is_old_sender_notification(message: MailMessage) -> bool:
        parsed_date = parse_message_date(message.date)
        if parsed_date is None:
            return False
        sender_text = (message.sender or "").lower()
        if not any(provider in sender_text for provider in ["nextdoor", "homedepot", "indeed", "bose"]):
            return False
        return parsed_date <= date.today() - timedelta(days=1)

    def is_old_usps_tracking(message: MailMessage) -> bool:
        subject = message.subject.lower()
        if "usps tracking" not in subject:
            return False
        token = subject.split("usps tracking")[-1].strip()
        if not token:
            return False
        try:
            subject_date = datetime.strptime(token, "%Y-%m-%d")
        except ValueError:
            return False
        return subject_date.date() < date.today()

    def is_fcc_notice(message: MailMessage) -> bool:
        text = f"{message.subject} {message.sender} {message.preview}".lower()
        return "fcc" in text and "license" in text

    def extract_sender_email(sender: str) -> str:
        sender = (sender or "").strip().lower()
        match = re.search(r"<([^>]+)>", sender)
        if match:
            return match.group(1).strip().lower()
        return sender

    def is_proton_folder_candidate(message: MailMessage) -> bool:
        sender_email = extract_sender_email(message.sender)
        allowed_senders = {
            "no-reply@proton.me",
            "no-reply@mail.proton.me",
            "no-reply@notify.proton.me",
        }
        if sender_email not in allowed_senders:
            return False
        return True

    return [
        Rule(
            name="delete-old-informed-delivery",
            predicate=is_old_informed_delivery,
            action=RuleAction(action="delete", reason="Older informed delivery notifications can be cleaned up."),
        ),
        Rule(
            name="delete-old-sender-notifications",
            predicate=is_old_sender_notification,
            action=RuleAction(action="delete", reason="Older notifications from selected senders can be cleaned up."),
        ),
        Rule(
            name="delete-old-usps-tracking",
            predicate=is_old_usps_tracking,
            action=RuleAction(action="delete", reason="Past USPS tracking notices are no longer useful."),
        ),
        Rule(
            name="archive-fcc-license-notice",
            predicate=is_fcc_notice,
            action=RuleAction(action="archive", reason="Appears to be an official FCC notice that may not need to stay in the inbox."),
        ),
        Rule(
            name="move-non-affiliated-proton-mail",
            predicate=is_proton_folder_candidate,
            action=RuleAction(
                action="move",
                reason="Route Proton-related mail to the Proton folder unless it is from your own accounts.",
                target_folder="Folders/Proton",
            ),
        ),
    ]
