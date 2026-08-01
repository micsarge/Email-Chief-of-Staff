import unittest
from datetime import date, timedelta

from src.mailbox import MailMessage
from src.rules import RuleEngine, build_default_rules


class RuleEngineTests(unittest.TestCase):
    def test_rules_flag_usps_notification(self):
        engine = RuleEngine(build_default_rules())
        two_days_ago = (date.today() - timedelta(days=2)).strftime("%a, %d %b %Y %H:%M:%S")
        message = MailMessage(
            id="1",
            subject="Informed Delivery",
            sender="usps@example.com",
            date=two_days_ago,
            preview="Your daily USPS update is here.",
        )

        result = engine.evaluate(message)

        self.assertIsNotNone(result.action)
        self.assertEqual(result.action.action, "delete")

    def test_rules_flag_fcc_notice(self):
        engine = RuleEngine(build_default_rules())
        message = MailMessage(
            id="2",
            subject="FCC License Notice",
            sender="authorizations@fcc.gov",
            date="",
            preview="Official update about your license.",
        )

        result = engine.evaluate(message)

        self.assertIsNotNone(result.action)
        self.assertEqual(result.action.action, "archive")

    def test_rules_delete_old_informed_delivery_messages(self):
        engine = RuleEngine(build_default_rules())
        yesterday = (date.today() - timedelta(days=1)).strftime("%a, %d %b %Y %H:%M:%S %z")
        message = MailMessage(
            id="3",
            subject="Informed Delivery",
            sender="usps@example.com",
            date=yesterday,
            preview="Your daily USPS update is here.",
        )

        result = engine.evaluate(message)

        self.assertIsNotNone(result.action)
        self.assertEqual(result.action.action, "delete")

    def test_rules_delete_old_sender_notifications(self):
        engine = RuleEngine(build_default_rules())
        two_days_ago = (date.today() - timedelta(days=2)).strftime("%a, %d %b %Y %H:%M:%S %z")
        message = MailMessage(
            id="4",
            subject="New updates",
            sender="marketing@nextdoor.com",
            date=two_days_ago,
            preview="A message from Nextdoor.",
        )

        result = engine.evaluate(message)

        self.assertIsNotNone(result.action)
        self.assertEqual(result.action.action, "delete")

    def test_rules_delete_usps_tracking_subject_dates_before_today(self):
        engine = RuleEngine(build_default_rules())
        message = MailMessage(
            id="5",
            subject="USPS Tracking 2024-07-31",
            sender="tracking@usps.com",
            date="",
            preview="Your package update.",
        )

        result = engine.evaluate(message)

        self.assertIsNotNone(result.action)
        self.assertEqual(result.action.action, "delete")


if __name__ == "__main__":
    unittest.main()
