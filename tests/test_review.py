import os
import tempfile
import unittest

from src.mailbox import MailMessage
from src.review import ReviewItem, ReviewQueue
from src.rules import RuleAction, RuleResult


class ReviewQueueTests(unittest.TestCase):
    def test_queue_tracks_pending_and_decisions(self):
        message = MailMessage(id="1", subject="Test", sender="sender@example.com", date="", preview="")
        item = ReviewItem(message=message, result=RuleResult(message=message, action=RuleAction(action="archive", reason="Test")))
        queue = ReviewQueue([item])

        self.assertEqual(len(queue.pending()), 1)
        self.assertTrue(queue.approve("1"))
        self.assertEqual(queue.pending(), [])

    def test_queue_summary_reports_status(self):
        message = MailMessage(id="2", subject="Second", sender="sender@example.com", date="", preview="")
        item = ReviewItem(message=message, result=RuleResult(message=message, action=None))
        queue = ReviewQueue([item])

        summary = queue.to_summary()

        self.assertEqual(summary[0]["status"], "pending")

    def test_queue_persists_approval_state(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
            state_path = handle.name

        try:
            message = MailMessage(id="3", subject="Persisted", sender="sender@example.com", date="", preview="")
            item = ReviewItem(message=message, result=RuleResult(message=message, action=RuleAction(action="archive", reason="Test")))
            queue = ReviewQueue([item], state_path=state_path)
            self.assertTrue(queue.approve("3"))
            queue.save_state()

            reloaded = ReviewQueue([], state_path=state_path)
            reloaded.load_state()
            self.assertEqual(reloaded.items[0].approved, True)
        finally:
            if os.path.exists(state_path):
                os.remove(state_path)

    def test_review_queue_persists_target_folder(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
            state_path = handle.name

        try:
            message = MailMessage(
                id="3",
                subject="Proton update",
                sender='"Proton" <news@proton.me>',
                date="",
                preview="",
            )
            item = ReviewItem(
                message=message,
                result=RuleResult(message=message, action=RuleAction(action="move", reason="Test", target_folder="Folders/Proton")),
            )
            queue = ReviewQueue(items=[item], state_path=state_path)
            queue.save_state()

            loaded = ReviewQueue(state_path=state_path)
            loaded.load_state()

            self.assertEqual(loaded.items[0].result.action.action, "move")
            self.assertEqual(loaded.items[0].result.action.target_folder, "Folders/Proton")
        finally:
            if os.path.exists(state_path):
                os.remove(state_path)

    def test_queue_can_load_state_without_rehydrating_items(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
            state_path = handle.name

        try:
            message = MailMessage(id="4", subject="State", sender="sender@example.com", date="", preview="")
            item = ReviewItem(message=message, result=RuleResult(message=message, action=RuleAction(action="delete", reason="Test")))
            queue = ReviewQueue([item], state_path=state_path)
            self.assertTrue(queue.approve("4"))
            queue.save_state()

            reloaded = ReviewQueue([], state_path=state_path)
            state_map = reloaded.load_state(hydrate_items=False)
            self.assertEqual(reloaded.items, [])
            self.assertEqual(state_map["4"], True)
        finally:
            if os.path.exists(state_path):
                os.remove(state_path)


if __name__ == "__main__":
    unittest.main()
