from dataclasses import dataclass
from datetime import datetime
import re
from typing import List

from src.proton_bridge import ProtonBridgeClient


@dataclass
class MailMessage:
    id: str
    subject: str
    sender: str
    date: str
    preview: str
    body: str = ""
    mailbox: str = "INBOX"
    uid: str = ""
    internet_message_id: str = ""


class MailboxReader:
    def __init__(self, client: ProtonBridgeClient):
        self.client = client

    def fetch_recent_messages(self, limit: int = 10) -> List[MailMessage]:
        return self.fetch_all_messages(limit=limit)

    def fetch_all_messages(self, limit: int | None = None, mailboxes: List[str] | None = None) -> List[MailMessage]:
        mailboxes_to_scan = mailboxes or [self.client.config.mailbox]
        all_messages: List[MailMessage] = []
        for mailbox in mailboxes_to_scan:
            all_messages.extend(self.fetch_messages_for_mailbox(mailbox=mailbox, limit=limit))
        return all_messages

    def fetch_messages_for_mailbox(self, mailbox: str, limit: int | None = None) -> List[MailMessage]:
        if self.client.imap_connection is None:
            self.client.connect_imap()

        select_status, _ = self.client._select_mailbox(mailbox)
        if select_status != "OK":
            return []

        status, messages = self.client.imap_connection.search(None, "ALL")
        if status != "OK":
            raise ValueError("Unable to search mailbox")

        ids = messages[0].split()
        if limit is not None:
            ids = ids[-limit:] if ids else []
        return self._fetch_messages_for_ids(ids, mailbox)

    def fetch_messages_since(self, limit: int = 10, since_date: str = "") -> List[MailMessage]:
        if self.client.imap_connection is None:
            self.client.connect_imap()

        search_value = "ALL"
        if since_date:
            try:
                parsed_date = datetime.strptime(since_date, "%Y-%m-%d")
                imap_date = parsed_date.strftime("%d-%b-%Y")
            except ValueError:
                imap_date = since_date
            search_value = f"SINCE {imap_date}"

        status, messages = self.client.imap_connection.search(None, search_value)
        if status != "OK":
            raise ValueError("Unable to search mailbox")

        ids = messages[0].split()
        recent_ids = ids[-limit:] if ids else []
        return self._fetch_messages_for_ids(recent_ids, self.client.config.mailbox)

    def _fetch_messages_for_ids(self, recent_ids: List[bytes], mailbox: str) -> List[MailMessage]:
        messages_data: List[MailMessage] = []
        for message_id in recent_ids:
            header_response = self.client.imap_connection.fetch(message_id, "(UID BODY.PEEK[HEADER])")
            body_response = self.client.imap_connection.fetch(message_id, "(BODY.PEEK[TEXT])")
            header_text = self._extract_payload_text(header_response)
            body_text = self._extract_payload_text(body_response)
            uid = self._extract_uid(header_response)
            stable_id = f"{mailbox.replace('/', '_')}::{uid or message_id.decode()}"
            messages_data.append(self._parse_message(stable_id, header_text, body_text, mailbox=mailbox, uid=uid))

        return messages_data

    def _extract_uid(self, response) -> str:
        _, payload = response
        if not payload:
            return ""

        for entry in payload:
            if not isinstance(entry, tuple):
                continue
            marker = entry[0]
            marker_text = marker.decode("utf-8", errors="replace") if isinstance(marker, bytes) else str(marker)
            match = re.search(r"UID\s+(\d+)", marker_text)
            if match:
                return match.group(1)
        return ""

    def _extract_payload_text(self, response) -> str:
        _, payload = response
        if not payload:
            return ""

        if isinstance(payload[0], tuple):
            raw_value = payload[0][1]
            if isinstance(raw_value, bytes):
                return raw_value.decode("utf-8", errors="replace")
            return str(raw_value)

        return str(payload[0])

    def _parse_message(self, message_id: str, header_text: str, body_text: str, mailbox: str, uid: str) -> MailMessage:
        subject = ""
        sender = ""
        date = ""
        internet_message_id = ""
        for line in header_text.splitlines():
            lower = line.lower()
            if lower.startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
            elif lower.startswith("from:"):
                sender = line.split(":", 1)[1].strip()
            elif lower.startswith("date:"):
                date = line.split(":", 1)[1].strip()
            elif lower.startswith("message-id:"):
                internet_message_id = line.split(":", 1)[1].strip()

        preview = body_text.strip().splitlines()[0] if body_text.strip() else ""
        return MailMessage(
            id=message_id,
            subject=subject,
            sender=sender,
            date=date,
            preview=preview,
            body=body_text,
            mailbox=mailbox,
            uid=uid,
            internet_message_id=internet_message_id,
        )
