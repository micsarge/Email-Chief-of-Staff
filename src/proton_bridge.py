import os
import imaplib
import re
import smtplib
from dataclasses import dataclass


class ProtonBridgeConnectionError(Exception):
    """Raised when Proton Bridge configuration is incomplete or invalid."""


@dataclass(frozen=True)
class ProtonBridgeConfig:
    host: str
    port: int
    username: str
    password: str
    mailbox: str = "INBOX"
    trash_mailbox: str = "Trash"

    @classmethod
    def from_env(cls) -> "ProtonBridgeConfig":
        host = os.getenv("PROTON_BRIDGE_HOST", "localhost")
        port = int(os.getenv("PROTON_BRIDGE_PORT", "1143"))
        username = os.getenv("PROTON_BRIDGE_USERNAME")
        password = os.getenv("PROTON_BRIDGE_PASSWORD")
        mailbox = os.getenv("PROTON_BRIDGE_MAILBOX", "INBOX")
        trash_mailbox = os.getenv("PROTON_BRIDGE_TRASH_MAILBOX", "Trash")

        if not username or not password:
            raise ProtonBridgeConnectionError("PROTON_BRIDGE_USERNAME and PROTON_BRIDGE_PASSWORD are required")

        return cls(
            host=host,
            port=port,
            username=username,
            password=password,
            mailbox=mailbox,
            trash_mailbox=trash_mailbox,
        )


class ProtonBridgeClient:
    def __init__(self, config: ProtonBridgeConfig):
        self.config = config
        self.imap_connection = None
        self.smtp_connection = None

    def _ensure_imap(self):
        if self.imap_connection is None:
            self.connect_imap()
        return self.imap_connection

    def _select_mailbox(self, mailbox: str):
        imap = self._ensure_imap()
        try:
            status, data = imap.select(mailbox)
            if status == "OK":
                return status, data
        except Exception:
            pass
        return imap.select(f'"{mailbox}"')

    def connect_imap(self):
        try:
            connection = imaplib.IMAP4(self.config.host, self.config.port)
            connection.starttls()
            connection.login(self.config.username, self.config.password)
            self.imap_connection = connection
            self._select_mailbox(self.config.mailbox)
            return connection
        except Exception as exc:
            raise ProtonBridgeConnectionError(f"Failed to connect to IMAP service: {exc}") from exc

    def connect_smtp(self):
        try:
            connection = smtplib.SMTP(self.config.host, self.config.port)
            connection.starttls()
            connection.login(self.config.username, self.config.password)
            self.smtp_connection = connection
            return connection
        except Exception as exc:
            raise ProtonBridgeConnectionError(f"Failed to connect to SMTP service: {exc}") from exc

    def connect(self) -> bool:
        self.connect_imap()
        self.connect_smtp()
        return True

    def _sequence_id(self, message_id: str) -> str:
        if "::" in message_id:
            token = message_id.split("::", 1)[1].strip()
            if token.isdigit():
                return token
        return message_id

    def _sequence_to_uid(self, message_id: str) -> str | None:
        imap = self._ensure_imap()
        sequence_id = self._sequence_id(message_id)
        fetch_status, fetch_data = imap.fetch(sequence_id, "(UID)")
        if fetch_status != "OK" or not fetch_data:
            return None

        for entry in fetch_data:
            if not isinstance(entry, tuple) or not entry:
                continue
            marker = entry[0]
            if isinstance(marker, bytes):
                marker_text = marker.decode("utf-8", errors="replace")
            else:
                marker_text = str(marker)
            match = re.search(r"UID\s+(\d+)", marker_text)
            if match:
                return match.group(1)
        return None

    def _move_message(self, message_id: str, folder_name: str, message_uid: str = "") -> bool:
        imap = self._ensure_imap()
        sequence_id = self._sequence_id(message_id)

        create_status, _ = imap.create(folder_name)
        if create_status not in {"OK", "NO"}:
            return False

        uid_value = message_uid or self._sequence_to_uid(message_id)
        if uid_value:
            move_status, _ = imap.uid("MOVE", uid_value, folder_name)
            if move_status == "OK":
                return True

        copy_status, _ = imap.copy(sequence_id, folder_name)
        if copy_status != "OK":
            return False

        store_status, _ = imap.store(sequence_id, "+FLAGS.SILENT", "\\Deleted")
        if store_status != "OK":
            return False

        expunge_status, _ = imap.expunge()
        return expunge_status in {"OK", "NO"}

    def apply_action(self, message_id: str, action: str, mailbox: str | None = None, message_uid: str = "") -> bool:
        try:
            imap = self._ensure_imap()
            if mailbox:
                select_status, _ = self._select_mailbox(mailbox)
                if select_status != "OK":
                    return False

            if action == "archive":
                return self._move_message(message_id, "Archive", message_uid=message_uid)

            if action == "delete":
                return self._move_message(message_id, self.config.trash_mailbox, message_uid=message_uid)
        except Exception:
            return False

        return False

    def purge_trash(self) -> int:
        imap = self._ensure_imap()
        original_mailbox = self.config.mailbox
        trash_mailbox = self.config.trash_mailbox

        try:
            status, _ = self._select_mailbox(trash_mailbox)
            if status != "OK":
                return 0

            status, message_ids_raw = imap.search(None, "ALL")
            if status != "OK":
                return 0

            message_ids = message_ids_raw[0].split() if message_ids_raw and message_ids_raw[0] else []
            for message_id in message_ids:
                imap.store(message_id, "+FLAGS.SILENT", "\\Deleted")

            if message_ids:
                imap.expunge()

            return len(message_ids)
        except Exception:
            return 0
        finally:
            try:
                self._select_mailbox(original_mailbox)
            except Exception:
                pass
