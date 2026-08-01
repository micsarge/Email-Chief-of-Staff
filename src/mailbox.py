from dataclasses import dataclass
from datetime import datetime
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


class MailboxReader:
    def __init__(self, client: ProtonBridgeClient):
        self.client = client

    def fetch_recent_messages(self, limit: int = 10) -> List[MailMessage]:
        return self.fetch_all_messages(limit=limit)

    def fetch_all_messages(self, limit: int | None = None) -> List[MailMessage]:
        if self.client.imap_connection is None:
            self.client.connect_imap()

        status, messages = self.client.imap_connection.search(None, "ALL")
        if status != "OK":
            raise ValueError("Unable to search mailbox")

        ids = messages[0].split()
        if limit is not None:
            ids = ids[-limit:] if ids else []
        return self._fetch_messages_for_ids(ids)

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
        return self._fetch_messages_for_ids(recent_ids)

    def _fetch_messages_for_ids(self, recent_ids: List[bytes]) -> List[MailMessage]:
        messages_data: List[MailMessage] = []
        for message_id in recent_ids:
            header_response = self.client.imap_connection.fetch(message_id, "(BODY.PEEK[HEADER])")
            body_response = self.client.imap_connection.fetch(message_id, "(BODY.PEEK[TEXT])")
            header_text = self._extract_payload_text(header_response)
            body_text = self._extract_payload_text(body_response)
            messages_data.append(self._parse_message(message_id.decode(), header_text, body_text))

        return messages_data

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

    def _parse_message(self, message_id: str, header_text: str, body_text: str) -> MailMessage:
        subject = ""
        sender = ""
        date = ""
        for line in header_text.splitlines():
            lower = line.lower()
            if lower.startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
            elif lower.startswith("from:"):
                sender = line.split(":", 1)[1].strip()
            elif lower.startswith("date:"):
                date = line.split(":", 1)[1].strip()

        preview = body_text.strip().splitlines()[0] if body_text.strip() else ""
        return MailMessage(id=message_id, subject=subject, sender=sender, date=date, preview=preview, body=body_text)
