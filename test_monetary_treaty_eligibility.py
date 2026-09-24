"""Offline scenario tests of the actual treaty triggers, not an engine simulation."""
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
LAWS = ("commodity_money", "gold_standard", "fiat_currency", "digital_currency",
        "decentralized_cryptocurrency")


def country(law, **overrides):
    result = dict(law=law, bank=True, command=False, dollarised=False,
                  board=False, union=False, default=False, suspended=False, dial=True)
    result.update(overrides)
    return result


class TreatyEligibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parser = ParadoxFileParser()
        parser.parse_file(str(ROOT / "common/scripted_triggers/te_monetary_arrangement_triggers.txt"), False)
        cls.triggers = parser.data

    def evaluate(self, name, current, previous=None, params=None):
        # Only the small trigger vocabulary used by these gates is interpreted.
        # Unknown syntax fails rather than silently passing a changed gate.
        return self.block(self.triggers[name][1], current, previous, params or {})

    def block(self, block, current, previous, params, mode="AND"):
        results = []
        for key, entries in block.items():
            for op, value in entries if isinstance(entries, list) else [entries]:
                self.assertEqual(op, "=")
                if key in ("AND", "OR", "NOT"):
                    answer = self.block(value, current, previous, params, key)
                elif key in ("source_country", "target_country", "$OTHER$"):
                    if key == "$OTHER$":
                        ref = params["OTHER"]
                        other = previous if ref == "prev" else previous["target_country"]
                    else:
                        other = current[key]
                    answer = self.block(value, other, current, params)
                elif key == "has_law_or_variant":
                    law = value.removeprefix("law_type:law_")
                    answer = current["bank"] if law == "national_bank" else current["law"] == law
                elif key == "has_type":
                    answer = current["type"] == value
                elif key == "te_mon_is_on_gold":
                    answer = (current["law"] == "gold_standard" and not current["suspended"]) == (value == "yes")
                elif key in {"te_mon_is_command", "te_mon_is_dollarised",
                             "te_mon_is_on_currency_board", "te_mon_is_union_adopter",
                             "in_default", "te_mon_has_dial"}:
                    field = {"te_mon_is_command": "command", "te_mon_is_dollarised": "dollarised",
                             "te_mon_is_on_currency_board": "board", "te_mon_is_union_adopter": "union",
                             "in_default": "default", "te_mon_has_dial": "dial"}[key]
                    answer = current[field] == (value == "yes")
                elif key in self.triggers:
                    answer = self.evaluate(key, current, previous, value if isinstance(value, dict) else params)
                    if value == "no":
                        answer = not answer
                else:
                    self.fail(f"Unsupported test vocabulary: {key}")
                results.append(answer)
        if mode == "OR":
            return any(results)
        if mode == "NOT":
            return not any(results)
        return all(results)

    def peg(self, source, target):
        return self.evaluate("te_mon_peg_article_valid",
                             dict(source_country=source, target_country=target))

    def test_currency_matrix(self):
        for source in LAWS:
            for target in LAWS:
                with self.subTest(source=source, target=target):
                    expected = (target != "decentralized_cryptocurrency" and
                                (source in ("fiat_currency", "digital_currency") or
                                 source in ("commodity_money", "gold_standard") and
                                 target in ("commodity_money", "gold_standard")))
                    self.assertEqual(self.peg(country(source), country(target, dial=target != "decentralized_cryptocurrency")), expected)

    def test_peg_lifecycle(self):
        anchor = country("gold_standard")
        for flag in ("command", "dollarised", "board", "union"):
            with self.subTest(flag=flag):
                self.assertFalse(self.peg(country("fiat_currency", **{flag: True}), anchor))
        # Signing must not require a dial that the peg itself removes.
        self.assertTrue(self.peg(country("fiat_currency", dial=False, bank=False), anchor))
        self.assertFalse(self.peg(country("gold_standard"), country("gold_standard", suspended=True)))
        self.assertFalse(self.peg(country("fiat_currency"), country("fiat_currency", dial=False)))

    def test_support_is_currency_neutral_but_provider_must_remain_capable(self):
        for article in ("swap_line", "lender_of_last_resort", "debt_receivership"):
            for law in LAWS:
                provider, recipient = country(law), country(law)
                source, target = (recipient, provider) if article == "debt_receivership" else (provider, recipient)
                state = dict(type=article, source_country=source, target_country=target)
                with self.subTest(article=article, law=law):
                    self.assertTrue(self.evaluate("te_mon_support_article_valid", state))
                    # Debtor default is an entry pretext, never a maintenance requirement.
                    recipient["default"] = True
                    self.assertTrue(self.evaluate("te_mon_support_article_valid", state))
                    for field, invalid in (("default", True), ("bank", False), ("command", True)):
                        original = provider[field]
                        provider[field] = invalid
                        self.assertFalse(self.evaluate("te_mon_support_article_valid", state))
                        provider[field] = original


if __name__ == "__main__":
    unittest.main()
