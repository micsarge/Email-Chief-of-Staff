import unittest
from datetime import date
from unittest.mock import Mock, patch

from app.main import _collect_trashed_message_ids, app
from src.mailbox import MailMessage
from src.rules import RuleAction, RuleResult


class SundayCleanupApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @patch("app.main.datetime")
    def test_cleanup_sunday_rejects_non_sunday(self, mock_datetime):
        mock_datetime.now.return_value = Mock(date=Mock(return_value=date(2026, 8, 1)))  # Saturday

        response = self.client.post("/api/review/cleanup-sunday")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["purged"], 0)

    @patch("app.main.datetime")
    @patch("app.main.ProtonBridgeClient")
    @patch("app.main.load_proton_bridge_config")
    def test_cleanup_sunday_purges_trash_on_sunday(self, mock_load_cfg, mock_client_cls, mock_datetime):
        mock_datetime.now.return_value = Mock(date=Mock(return_value=date(2026, 8, 2)))  # Sunday
        mock_load_cfg.return_value = Mock()
        mock_client = Mock()
        mock_client.purge_trash.return_value = 7
        mock_client_cls.return_value = mock_client

        response = self.client.post("/api/review/cleanup-sunday")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["purged"], 7)
        mock_client.purge_trash.assert_called_once()


class ReconcileApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @patch("app.main.generate_reconciliation_report")
    def test_reconcile_endpoint_returns_report(self, mock_report):
        mock_report.return_value = {
            "folderCounts": [{"folder": "INBOX", "available": True, "messageCount": 3}],
            "auditSummary": {"cleanupRuns": 1},
            "recentAuditEvents": [],
            "mailboxesSeen": ["INBOX", "Trash"],
        }

        response = self.client.get("/api/reconcile")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["auditSummary"]["cleanupRuns"], 1)
        self.assertEqual(payload["folderCounts"][0]["folder"], "INBOX")


class TrashDedupingTests(unittest.TestCase):
    def test_collect_trashed_message_ids_normalizes_values(self):
        reader = Mock()
        reader.fetch_messages_for_mailbox.return_value = [
            MailMessage(
                id="1",
                subject="one",
                sender="a@example.com",
                date="",
                preview="",
                internet_message_id="<ABC@x>",
            ),
            MailMessage(
                id="2",
                subject="two",
                sender="b@example.com",
                date="",
                preview="",
                internet_message_id=" <abc@x> ",
            ),
            MailMessage(
                id="3",
                subject="three",
                sender="c@example.com",
                date="",
                preview="",
                internet_message_id="",
            ),
        ]

        result = _collect_trashed_message_ids(reader, "Trash")

        self.assertEqual(result, {"<abc@x>"})
        reader.fetch_messages_for_mailbox.assert_called_once_with(mailbox="Trash")

    @patch("app.main.ReviewQueue")
    @patch("app.main.RuleEngine")
    @patch("app.main.load_rules_from_yaml", return_value=[])
    @patch("app.main.load_scan_mailboxes", return_value=["All Mail"])
    @patch("app.main.load_proton_bridge_config")
    @patch("app.main.MailboxReader")
    @patch("app.main.ProtonBridgeClient")
    def test_build_review_queue_skips_messages_already_in_proton_folder(
        self,
        mock_client_cls,
        mock_reader_cls,
        mock_load_cfg,
        mock_load_scan_mailboxes,
        mock_load_rules,
        mock_rule_engine_cls,
        mock_queue_cls,
    ):
        mock_load_cfg.return_value = Mock(trash_mailbox="Trash")

        all_mail_message = MailMessage(
            id="all-mail-1",
            subject="Proton update",
            sender='"Proton" <news@proton.me>',
            date="",
            preview="",
            mailbox="All Mail",
            internet_message_id="<abc@x>",
        )
        proton_folder_message = MailMessage(
            id="proton-1",
            subject="Proton update",
            sender='"Proton" <news@proton.me>',
            date="",
            preview="",
            mailbox="Folders/Proton",
            internet_message_id="<abc@x>",
        )

        mock_reader = Mock()
        mock_reader.fetch_all_messages.return_value = [all_mail_message]

        def fetch_messages_for_mailbox(mailbox):
            if mailbox == "Trash":
                return []
            if mailbox == "Folders/Proton":
                return [proton_folder_message]
            return []

        mock_reader.fetch_messages_for_mailbox.side_effect = fetch_messages_for_mailbox
        mock_reader_cls.return_value = mock_reader

        mock_rule_engine = Mock()
        mock_rule_engine.evaluate.return_value = RuleResult(
            message=all_mail_message,
            action=RuleAction(action="move", reason="Test", target_folder="Folders/Proton"),
        )
        mock_rule_engine_cls.return_value = mock_rule_engine

        mock_queue = Mock()
        mock_queue.items = []
        mock_queue_cls.return_value = mock_queue

        from app.main import build_review_queue

        queue, messages = build_review_queue()

        self.assertEqual(messages, [all_mail_message])
        mock_queue.add.assert_not_called()
        self.assertIs(queue, mock_queue)

    @patch("app.main.ReviewQueue")
    @patch("app.main.RuleEngine")
    @patch("app.main.load_rules_from_yaml", return_value=[])
    @patch("app.main.load_scan_mailboxes", return_value=["All Mail"])
    @patch("app.main.load_proton_bridge_config")
    @patch("app.main.MailboxReader")
    @patch("app.main.ProtonBridgeClient")
    def test_build_review_queue_readds_messages_that_already_have_saved_state(
        self,
        mock_client_cls,
        mock_reader_cls,
        mock_load_cfg,
        mock_load_scan_mailboxes,
        mock_load_rules,
        mock_rule_engine_cls,
        mock_queue_cls,
    ):
        mock_load_cfg.return_value = Mock(trash_mailbox="Trash")

        all_mail_message = MailMessage(
            id="all-mail-2",
            subject="April Proton mail",
            sender='"Proton" <no-reply@proton.me>',
            date="",
            preview="",
            mailbox="All Mail",
            internet_message_id="<saved-state@x>",
        )

        mock_reader = Mock()
        mock_reader.fetch_all_messages.return_value = [all_mail_message]
        mock_reader.fetch_messages_for_mailbox.return_value = []
        mock_reader_cls.return_value = mock_reader

        mock_rule_engine = Mock()
        mock_rule_engine.evaluate.return_value = RuleResult(
            message=all_mail_message,
            action=RuleAction(action="move", reason="Test", target_folder="Folders/Proton"),
        )
        mock_rule_engine_cls.return_value = mock_rule_engine

        mock_queue = Mock()
        mock_queue.items = []
        mock_queue.load_state.return_value = {"all-mail-2": True}
        mock_queue_cls.return_value = mock_queue

        from app.main import build_review_queue

        queue, messages = build_review_queue()

        self.assertEqual(messages, [all_mail_message])
        mock_queue.add.assert_called_once()
        self.assertIs(queue, mock_queue)


if __name__ == "__main__":
    unittest.main()
