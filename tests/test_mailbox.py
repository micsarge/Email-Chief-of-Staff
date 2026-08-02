import unittest
from unittest.mock import Mock

from src.mailbox import MailboxReader, MailMessage
from src.proton_bridge import ProtonBridgeClient, ProtonBridgeConfig


class MailboxReaderTests(unittest.TestCase):
    def test_fetch_messages_since_parses_the_requested_day(self):
        fake_imap = Mock()
        fake_imap.select.return_value = ("OK", [])
        fake_imap.search.return_value = ("OK", [b"1"])
        fake_imap.fetch.return_value = ("OK", [(b"1", b"Subject: Recent\r\nFrom: tester@example.com\r\nDate: Tue, 1 Jan 2024 12:00:00 +0000\r\n\r\nHello")])

        client = ProtonBridgeClient(ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret"))
        client.imap_connection = fake_imap
        reader = MailboxReader(client)

        messages = reader.fetch_messages_since(limit=1, since_date="2024-01-01")

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].subject, "Recent")
        fake_imap.search.assert_called_once_with(None, "SINCE 01-Jan-2024")

    def test_fetch_recent_messages_parses_headers_and_preview(self):
        fake_imap = Mock()
        fake_imap.select.return_value = ("OK", [])
        fake_imap.search.return_value = ("OK", [b"1 2"])
        fake_imap.fetch.side_effect = [
            ("OK", [(b"1", b"Subject: Test subject\r\nFrom: tester@example.com\r\nDate: Tue, 1 Jan 2024 12:00:00 +0000\r\n\r\n")]),
            ("OK", [(b"1", b"")]),
            ("OK", [(b"2", b"Subject: Another\r\nFrom: sender@example.com\r\nDate: Wed, 2 Jan 2024 13:00:00 +0000\r\n\r\n")]),
            ("OK", [(b"2", b"Hello world")]),
        ]

        client = ProtonBridgeClient(ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret"))
        client.imap_connection = fake_imap
        reader = MailboxReader(client)

        messages = reader.fetch_recent_messages(limit=2)

        self.assertEqual(len(messages), 2)
        self.assertIsInstance(messages[0], MailMessage)
        self.assertEqual(messages[0].subject, "Test subject")
        self.assertEqual(messages[0].sender, "tester@example.com")
        self.assertEqual(messages[1].preview, "Hello world")

    def test_fetch_all_messages_returns_every_matching_message(self):
        fake_imap = Mock()
        fake_imap.select.return_value = ("OK", [])
        fake_imap.search.return_value = ("OK", [b"1 2 3"])
        fake_imap.fetch.side_effect = [
            ("OK", [(b"1", b"Subject: One\r\nFrom: a@example.com\r\nDate: Tue, 1 Jan 2024 12:00:00 +0000\r\n\r\n")]),
            ("OK", [(b"1", b"")]),
            ("OK", [(b"2", b"Subject: Two\r\nFrom: b@example.com\r\nDate: Wed, 2 Jan 2024 13:00:00 +0000\r\n\r\n")]),
            ("OK", [(b"2", b"")]),
            ("OK", [(b"3", b"Subject: Three\r\nFrom: c@example.com\r\nDate: Thu, 3 Jan 2024 14:00:00 +0000\r\n\r\n")]),
            ("OK", [(b"3", b"")]),
        ]

        client = ProtonBridgeClient(ProtonBridgeConfig(host="127.0.0.1", port=1143, username="user@example.com", password="secret"))
        client.imap_connection = fake_imap
        reader = MailboxReader(client)

        messages = reader.fetch_all_messages()

        self.assertEqual(len(messages), 3)
        self.assertEqual([message.subject for message in messages], ["One", "Two", "Three"])


if __name__ == "__main__":
    unittest.main()
