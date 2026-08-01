import os
import unittest
from unittest.mock import Mock, patch

from src.proton_bridge import ProtonBridgeClient, ProtonBridgeConfig, ProtonBridgeConnectionError


class ProtonBridgeConfigTests(unittest.TestCase):
    def test_config_from_env_reads_values(self):
        with patch.dict(
            os.environ,
            {
                "PROTON_BRIDGE_HOST": "localhost",
                "PROTON_BRIDGE_PORT": "1143",
                "PROTON_BRIDGE_USERNAME": "user@example.com",
                "PROTON_BRIDGE_PASSWORD": "secret",
                "PROTON_BRIDGE_MAILBOX": "INBOX",
            },
            clear=True,
        ):
            config = ProtonBridgeConfig.from_env()

        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 1143)
        self.assertEqual(config.username, "user@example.com")
        self.assertEqual(config.password, "secret")
        self.assertEqual(config.mailbox, "INBOX")

    def test_config_requires_username_and_password(self):
        with patch.dict(os.environ, {"PROTON_BRIDGE_HOST": "localhost"}, clear=True):
            with self.assertRaises(ProtonBridgeConnectionError):
                ProtonBridgeConfig.from_env()


class ProtonBridgeClientTests(unittest.TestCase):
    def test_imap_connection_uses_starttls_and_login(self):
        fake_imap = Mock()
        fake_imap.starttls.return_value = ("OK", [])
        fake_imap.login.return_value = ("OK", [])
        fake_imap.select.return_value = ("OK", [])

        with patch("src.proton_bridge.imaplib.IMAP4", return_value=fake_imap) as imap_cls:
            client = ProtonBridgeClient(
                ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret")
            )
            client.connect_imap()

        imap_cls.assert_called_once_with("127.0.0.1", 1143)
        fake_imap.starttls.assert_called_once()
        fake_imap.login.assert_called_once_with("user@example.com", "secret")
        fake_imap.select.assert_called_once_with("INBOX")

    def test_smtp_connection_uses_starttls_and_login(self):
        fake_smtp = Mock()
        fake_smtp.starttls.return_value = None
        fake_smtp.login.return_value = None

        with patch("src.proton_bridge.smtplib.SMTP", return_value=fake_smtp) as smtp_cls:
            client = ProtonBridgeClient(
                ProtonBridgeConfig(host="127.0.0.1", port=1025, username="user@example.com", password="secret")
            )
            client.connect_smtp()

        smtp_cls.assert_called_once_with("127.0.0.1", 1025)
        fake_smtp.starttls.assert_called_once()
        fake_smtp.login.assert_called_once_with("user@example.com", "secret")

    def test_apply_action_moves_message_to_destination_folder(self):
        fake_imap = Mock()
        fake_imap.copy.return_value = ("OK", [])
        fake_imap.store.return_value = ("OK", [])
        fake_imap.expunge.return_value = ("OK", [])

        client = ProtonBridgeClient(
            ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret")
        )
        client.imap_connection = fake_imap

        client.apply_action("42", "archive")

        fake_imap.create.assert_called_once_with("Archive")
        fake_imap.copy.assert_called_once_with("42", "Archive")
        fake_imap.store.assert_called_once_with("42", "+FLAGS.SILENT", "\\Deleted")
        fake_imap.expunge.assert_called_once()


if __name__ == "__main__":
    unittest.main()
