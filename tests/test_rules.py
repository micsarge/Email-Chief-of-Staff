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

    def test_rules_route_proton_mail_to_folder_except_for_own_addresses(self):
        engine = RuleEngine(build_default_rules())
        message = MailMessage(
            id="2a",
            subject="Proton is now SOC 2 Type II audited",
            sender='"Proton for Business" <business-updates@proton.me>',
            date="",
            preview="",
        )

        result = engine.evaluate(message)

        self.assertIsNotNone(result.action)
        self.assertEqual(result.action.action, "move")
        self.assertEqual(result.action.target_folder, "Folders/Proton")

        excluded_senders = [
            '"Michael Sargent" <micsarge@cfl.rr.com>',
            '"Deb Lengyel" <deb.lengyel@example.com>',
        ]
        for index, sender in enumerate(excluded_senders, start=1):
            excluded_message = MailMessage(
                id=f"2a-{index}",
                subject="Proton update",
                sender=sender,
                date="",
                preview="",
            )

            excluded_result = engine.evaluate(excluded_message)
            self.assertTrue(excluded_result.action is None or excluded_result.action.action != "move")

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

    def test_provider_rule_does_not_match_preview_only_provider_term(self):
        engine = RuleEngine(build_default_rules())
        two_days_ago = (date.today() - timedelta(days=2)).strftime("%a, %d %b %Y %H:%M:%S %z")
        message = MailMessage(
            id="6",
            subject="Neighborhood update",
            sender="friend@example.com",
            date=two_days_ago,
            preview="Shared from Nextdoor",
        )

        result = engine.evaluate(message)

        # Provider rules should rely on sender identity, not preview text mentions.
        self.assertTrue(result.action is None or result.action.action != "delete")


if __name__ == "__main__":
    unittest.main()
