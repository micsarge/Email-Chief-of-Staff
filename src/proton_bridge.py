import os
import imaplib
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

    @classmethod
    def from_env(cls) -> "ProtonBridgeConfig":
        host = os.getenv("PROTON_BRIDGE_HOST", "localhost")
        port = int(os.getenv("PROTON_BRIDGE_PORT", "1143"))
        username = os.getenv("PROTON_BRIDGE_USERNAME")
        password = os.getenv("PROTON_BRIDGE_PASSWORD")
        mailbox = os.getenv("PROTON_BRIDGE_MAILBOX", "INBOX")

        if not username or not password:
            raise ProtonBridgeConnectionError("PROTON_BRIDGE_USERNAME and PROTON_BRIDGE_PASSWORD are required")

        return cls(host=host, port=port, username=username, password=password, mailbox=mailbox)


class ProtonBridgeClient:
    def __init__(self, config: ProtonBridgeConfig):
        self.config = config
        self.imap_connection = None
        self.smtp_connection = None

    def _ensure_imap(self):
        if self.imap_connection is None:
            self.connect_imap()
        return self.imap_connection

    def connect_imap(self):
        try:
            connection = imaplib.IMAP4(self.config.host, self.config.port)
            connection.starttls()
            connection.login(self.config.username, self.config.password)
            connection.select(self.config.mailbox)
            self.imap_connection = connection
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

    def apply_action(self, message_id: str, action: str) -> bool:
        imap = self._ensure_imap()
        if action == "archive":
            folder_name = "Archive"
            imap.create(folder_name)
            imap.copy(message_id, folder_name)
            imap.store(message_id, "+FLAGS.SILENT", "\\Deleted")
            imap.expunge()
            return True

        if action == "delete":
            imap.store(message_id, "+FLAGS.SILENT", "\\Deleted")
            imap.expunge()
            return True

        return False
