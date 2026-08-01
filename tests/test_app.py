import unittest
from datetime import date
from unittest.mock import Mock, patch

from app.main import app


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


if __name__ == "__main__":
    unittest.main()
