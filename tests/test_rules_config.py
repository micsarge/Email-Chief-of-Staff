import unittest
from pathlib import Path

from src.rules import load_rules_from_yaml


class RulesConfigTests(unittest.TestCase):
    def test_load_rules_from_yaml_reads_rule_file(self):
        rules_path = Path(__file__).resolve().parents[1] / "rules.yaml"
        rules = load_rules_from_yaml(rules_path)

        self.assertGreater(len(rules), 0)
        self.assertEqual(rules[0].name, "delete-old-informed-delivery")


if __name__ == "__main__":
    unittest.main()
