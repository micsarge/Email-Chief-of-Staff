import unittest
from pathlib import Path
import tempfile

from src.rules import load_rules_from_yaml


class RulesConfigTests(unittest.TestCase):
    def test_load_rules_from_yaml_reads_rule_file(self):
        rules_path = Path(__file__).resolve().parents[1] / "rules.yaml"
        rules = load_rules_from_yaml(rules_path)

        self.assertGreater(len(rules), 0)
        self.assertEqual(rules[0].name, "delete-old-informed-delivery")

        def test_load_rules_from_yaml_skips_disabled_rules(self):
                content = """
rules:
    - name: enabled-rule
        enabled: true
        action: delete
        reason: keep
        match:
            keywords:
                - alpha
    - name: disabled-rule
        enabled: false
        action: delete
        reason: skip
        match:
            keywords:
                - beta
"""

                with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as handle:
                        handle.write(content)
                        temp_path = Path(handle.name)

                try:
                        rules = load_rules_from_yaml(temp_path)
                        rule_names = [rule.name for rule in rules]
                        self.assertIn("enabled-rule", rule_names)
                        self.assertNotIn("disabled-rule", rule_names)
                finally:
                        temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
