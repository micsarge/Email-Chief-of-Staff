import unittest
from unittest.mock import Mock

from src.reconcile import _count_folder


class ReconcileTests(unittest.TestCase):
    def test_count_folder_reports_unavailable_when_select_fails(self):
        client = Mock()
        client._select_mailbox.return_value = ("NO", [b"missing"])

        result = _count_folder(client, "Missing")

        self.assertEqual(result["folder"], "Missing")
        self.assertFalse(result["available"])
        self.assertEqual(result["messageCount"], 0)

    def test_count_folder_uses_active_imap_connection_for_search(self):
        imap = Mock()
        imap.search.return_value = ("OK", [b"1 2 3 4"])

        client = Mock()
        client._select_mailbox.return_value = ("OK", [b"selected"])
        client._ensure_imap.return_value = imap

        result = _count_folder(client, "INBOX")

        client._ensure_imap.assert_called_once()
        imap.search.assert_called_once_with(None, "UNDELETED")
        self.assertTrue(result["available"])
        self.assertEqual(result["messageCount"], 4)


if __name__ == "__main__":
    unittest.main()
