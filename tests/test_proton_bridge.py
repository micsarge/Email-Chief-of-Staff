import imaplib
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
                "PROTON_BRIDGE_TRASH_MAILBOX": "Trash",
            },
            clear=True,
        ):
            config = ProtonBridgeConfig.from_env()

        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 1143)
        self.assertEqual(config.username, "user@example.com")
        self.assertEqual(config.password, "secret")
        self.assertEqual(config.mailbox, "INBOX")
        self.assertEqual(config.trash_mailbox, "Trash")

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

    def test_apply_action_returns_false_for_missing_message(self):
        fake_imap = Mock()
        fake_imap.create.return_value = ("OK", [])
        fake_imap.fetch.return_value = ("NO", [])
        fake_imap.uid.return_value = ("NO", [])
        fake_imap.copy.side_effect = imaplib.IMAP4.error("COPY command error: BAD [b'no such message']")

        client = ProtonBridgeClient(
            ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret")
        )
        client.imap_connection = fake_imap

        self.assertFalse(client.apply_action("42", "archive"))

    def test_apply_action_moves_message_to_destination_folder(self):
        fake_imap = Mock()
        fake_imap.create.return_value = ("OK", [])
        fake_imap.fetch.return_value = ("OK", [(b"42 (UID 123)", b"")])
        fake_imap.uid.return_value = ("NO", [])
        fake_imap.copy.return_value = ("OK", [])
        fake_imap.store.return_value = ("OK", [])
        fake_imap.expunge.return_value = ("OK", [])

        client = ProtonBridgeClient(
            ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret")
        )
        client.imap_connection = fake_imap

        self.assertTrue(client.apply_action("42", "archive"))

        fake_imap.create.assert_called_once_with("Archive")
        fake_imap.uid.assert_called_once_with("MOVE", "123", "Archive")
        fake_imap.copy.assert_called_once_with("42", "Archive")
        fake_imap.store.assert_called_once_with("42", "+FLAGS.SILENT", "\\Deleted")
        fake_imap.expunge.assert_called_once()

    def test_apply_action_moves_message_to_custom_folder(self):
        fake_imap = Mock()
        fake_imap.create.return_value = ("OK", [])
        fake_imap.fetch.return_value = ("OK", [(b"42 (UID 321)", b"")])
        fake_imap.uid.return_value = ("OK", [b"moved"])

        client = ProtonBridgeClient(
            ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret")
        )
        client.imap_connection = fake_imap

        self.assertTrue(client.apply_action("42", "move", target_folder="Folders/Proton"))

        fake_imap.create.assert_called_once_with("Folders/Proton")
        fake_imap.uid.assert_called_once_with("MOVE", "321", "Folders/Proton")
        fake_imap.copy.assert_not_called()
        fake_imap.store.assert_not_called()
        fake_imap.expunge.assert_not_called()

    def test_apply_action_delete_moves_message_to_trash_first(self):
        fake_imap = Mock()
        fake_imap.create.return_value = ("OK", [])
        fake_imap.fetch.return_value = ("OK", [(b"42 (UID 456)", b"")])
        fake_imap.uid.return_value = ("NO", [])
        fake_imap.copy.return_value = ("OK", [])
        fake_imap.store.return_value = ("OK", [])
        fake_imap.expunge.return_value = ("OK", [])

        client = ProtonBridgeClient(
            ProtonBridgeConfig(
                host="127.0.0.1",
                port=1143,
                username="user@example.com",
                password="secret",
                trash_mailbox="Trash",
            )
        )
        client.imap_connection = fake_imap

        self.assertTrue(client.apply_action("42", "delete"))

        fake_imap.create.assert_called_once_with("Trash")
        fake_imap.uid.assert_called_once_with("MOVE", "456", "Trash")
        fake_imap.copy.assert_called_once_with("42", "Trash")
        fake_imap.store.assert_called_once_with("42", "+FLAGS.SILENT", "\\Deleted")
        fake_imap.expunge.assert_called_once()

    def test_apply_action_returns_false_when_move_and_copy_fail(self):
        fake_imap = Mock()
        fake_imap.create.return_value = ("OK", [])
        fake_imap.fetch.return_value = ("OK", [(b"42 (UID 789)", b"")])
        fake_imap.uid.return_value = ("NO", [])
        fake_imap.copy.return_value = ("NO", [b"copy failed"])

        client = ProtonBridgeClient(
            ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret")
        )
        client.imap_connection = fake_imap

        self.assertFalse(client.apply_action("42", "delete"))
        fake_imap.expunge.assert_not_called()

    def test_apply_action_returns_false_for_unknown_action(self):
        fake_imap = Mock()

        client = ProtonBridgeClient(
            ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret")
        )
        client.imap_connection = fake_imap

        self.assertFalse(client.apply_action("42", "unknown-action"))
        fake_imap.create.assert_not_called()
        fake_imap.copy.assert_not_called()
        fake_imap.uid.assert_not_called()

    def test_apply_action_returns_false_for_move_without_target_folder(self):
        fake_imap = Mock()

        client = ProtonBridgeClient(
            ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret")
        )
        client.imap_connection = fake_imap

        self.assertFalse(client.apply_action("42", "move", target_folder=None))
        fake_imap.create.assert_not_called()
        fake_imap.copy.assert_not_called()
        fake_imap.uid.assert_not_called()

    def test_apply_action_returns_false_when_source_mailbox_select_fails(self):
        fake_imap = Mock()
        fake_imap.select.return_value = ("NO", [b"no such mailbox"])

        client = ProtonBridgeClient(
            ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret")
        )
        client.imap_connection = fake_imap

        self.assertFalse(client.apply_action("42", "delete", mailbox="MissingMailbox"))
        fake_imap.create.assert_not_called()
        fake_imap.copy.assert_not_called()
        fake_imap.uid.assert_not_called()

    def test_apply_action_uses_uid_move_when_available(self):
        fake_imap = Mock()
        fake_imap.create.return_value = ("OK", [])
        fake_imap.fetch.return_value = ("OK", [(b"42 (UID 999)", b"")])
        fake_imap.uid.return_value = ("OK", [b"moved"])

        client = ProtonBridgeClient(
            ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret")
        )
        client.imap_connection = fake_imap

        self.assertTrue(client.apply_action("42", "delete"))
        fake_imap.uid.assert_called_once_with("MOVE", "999", "Trash")
        fake_imap.copy.assert_not_called()
        fake_imap.store.assert_not_called()
        fake_imap.expunge.assert_not_called()

    def test_apply_action_extracts_sequence_from_scoped_message_id(self):
        fake_imap = Mock()
        fake_imap.create.return_value = ("OK", [])
        fake_imap.fetch.return_value = ("OK", [(b"42 (UID 1234)", b"")])
        fake_imap.uid.return_value = ("NO", [b"move unsupported"])
        fake_imap.copy.return_value = ("OK", [])
        fake_imap.store.return_value = ("OK", [])
        fake_imap.expunge.return_value = ("NO", [b"operation not allowed"])

        client = ProtonBridgeClient(
            ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret")
        )
        client.imap_connection = fake_imap

        self.assertTrue(client.apply_action("All Mail::42", "delete", message_uid=""))
        fake_imap.fetch.assert_called_once_with("42", "(UID)")
        fake_imap.copy.assert_called_once_with("42", "Trash")
        fake_imap.store.assert_called_once_with("42", "+FLAGS.SILENT", "\\Deleted")

    def test_purge_trash_marks_all_messages_deleted_and_expunge(self):
        fake_imap = Mock()
        fake_imap.select.return_value = ("OK", [])
        fake_imap.search.return_value = ("OK", [b"1 2 3"])
        fake_imap.store.return_value = ("OK", [])
        fake_imap.expunge.return_value = ("OK", [])

        client = ProtonBridgeClient(
            ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret")
        )
        client.imap_connection = fake_imap

        purged = client.purge_trash()

        self.assertEqual(purged, 3)
        fake_imap.select.assert_any_call("Trash")
        fake_imap.store.assert_any_call(b"1", "+FLAGS.SILENT", "\\Deleted")
        fake_imap.store.assert_any_call(b"2", "+FLAGS.SILENT", "\\Deleted")
        fake_imap.store.assert_any_call(b"3", "+FLAGS.SILENT", "\\Deleted")
        fake_imap.expunge.assert_called_once()
        fake_imap.select.assert_any_call("INBOX")

    def test_purge_trash_returns_zero_when_trash_unavailable(self):
        fake_imap = Mock()
        fake_imap.select.side_effect = [("NO", [b"no such mailbox"]), ("OK", [])]

        client = ProtonBridgeClient(
            ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret")
        )
        client.imap_connection = fake_imap

        purged = client.purge_trash()

        self.assertEqual(purged, 0)


if __name__ == "__main__":
    unittest.main()
