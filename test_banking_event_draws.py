"""The banking cycle's event pool: what gates each draw (#1612).

`banking_cycle_random_event_effect` draws one event a month from a weighted
list. Every draw's base weight is 0, so the `if` in its `modifier` block that
tests a technology is a hard gate, and the event's text is written to what
that gate guarantees (`docs/guides/event_text_guarantees.md`). A second
top-level `if` beside it adds weight without the gate: under Unregulated
Banking "Predatory Lending Scandal" was drawn in any phase from the first
month of the cycle. The engine has nothing to say about any of this, so these
checks read the script.
"""
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
EFFECTS = "common/scripted_effects/banking_cycle_effects.txt"
TRIGGERS = "common/scripted_triggers/market_triggers.txt"
EVENTS = "events/banking_cycle_events.txt"
MODIFIERS = "common/static_modifiers/extra_modifiers.txt"
LOC = ROOT / "localization/english/te_events_l_english.yml"

# The planned and cooperative variants of two market events share the market
# option's effects under a name of their own: option, its modifier, the market
# modifier it is a twin of.
VARIANT_MODIFIERS = (
    ("banking_cycle_events.104.b", "banking_event_stockpile_release", "banking_event_deposit_guarantee_emergency"),
    ("banking_cycle_events.154.b", "banking_event_federation_relief_fund", "banking_event_deposit_guarantee_emergency"),
    ("banking_cycle_events.116.a", "banking_event_plan_figures_upheld", "banking_event_cb_independence"),
    ("banking_cycle_events.166.a", "banking_event_old_slate_upheld", "banking_event_cb_independence"),
)
# Draws whose subject is a private bank or a trust company.
PRIVATE_BANK_EVENTS = (7, 21, 32, 47, 59)


def parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(str(ROOT / path), False)
    return parser.data


def entries(block):
    for key, items in block.items():
        for op, value in items if isinstance(items, list) else [items]:
            yield key, op, value


def walk(block):
    """Every (key, value) under `block`, at any depth."""
    for key, _, value in entries(block):
        yield key, value
        if isinstance(value, dict):
            yield from walk(value)


def children(block, key):
    return [value for k, _, value in entries(block) if k == key]


def draws():
    """{event number: draw block} for every weighted branch that fires an event.
    A draw with planned and cooperative variants is listed under each id."""
    effect = parse(EFFECTS)["banking_cycle_random_event_effect"][1]
    (random_list,) = [value for key, value in walk(effect) if key == "random_list"]
    found = {}
    for _, _, branch in entries(random_list):
        if not isinstance(branch, dict):
            continue
        for key, value in walk(branch):
            if key == "trigger_event" and isinstance(value, dict):
                event = value["id"][1]
                if event.startswith("banking_cycle_events."):
                    found[int(event.rsplit(".", 1)[1])] = branch
    return found


def asked(block):
    """The (key, value) pairs a trigger block asks, at any depth."""
    return {(key, value) for key, value in walk(block) if not isinstance(value, dict)}


class BankingEventDrawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.draws = draws()

    def test_the_pool_was_found(self):
        self.assertGreater(len(self.draws), 70)
        for event in (16, 20, 44, 116, 120, 166, 170):
            self.assertIn(event, self.draws)

    def test_a_technology_gate_is_the_only_top_level_weight(self):
        """Extra weight for a phase or a law is nested inside the gating `if`."""
        escaped = []
        for event, draw in sorted(self.draws.items()):
            for modifier in children(draw, "modifier"):
                ifs = children(modifier, "if")
                gates = [block for block in ifs
                         if any(key == "has_technology_researched" for key, _ in asked(children(block, "limit")[0]))]
                if gates and len(ifs) > 1:
                    escaped.append(event)
        self.assertEqual(escaped, [], "these draws add weight outside their technology gate")

    def test_the_reported_draws_keep_their_bonus_inside_the_gate(self):
        for event, law in ((16, "law_type:law_central_bank_independence"),
                           (20, "law_type:law_unregulated_banking"),
                           (44, "law_type:law_unregulated_banking")):
            (modifier,) = children(self.draws[event], "modifier")
            (gate,) = children(modifier, "if")
            nested = [asked(block) for block in children(gate, "if")]
            self.assertTrue(any(("has_law", law) in block for block in nested), event)

    def test_the_wealth_fund_is_for_market_economies(self):
        (trigger,) = children(self.draws[19], "trigger")
        self.assertIn(("banking_is_market_economy", "yes"), asked(trigger))

    def test_fintech_needs_networked_computers(self):
        (modifier,) = children(self.draws[36], "modifier")
        (gate,) = children(modifier, "if")
        limit = asked(children(gate, "limit")[0])
        self.assertIn(("has_technology_researched", "computer_networks"), limit)
        self.assertIn(("has_technology_researched", "modern_financial_instruments"), limit)

    def test_private_bank_events_skip_state_owned_banking(self):
        trigger = parse(TRIGGERS)["banking_has_private_banks"][1]
        self.assertEqual(asked(trigger), {("banking_is_market_economy", "yes"), ("te_mon_is_state_banking", "no")})
        for event in PRIVATE_BANK_EVENTS:
            (draw_trigger,) = children(self.draws[event], "trigger")
            self.assertIn(("banking_has_private_banks", "yes"), asked(draw_trigger), event)


class BankingVariantModifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modifiers = parse(MODIFIERS)
        cls.events = parse(EVENTS)
        cls.loc = LOC.read_text(encoding="utf-8-sig")

    def option(self, name):
        event = self.events[name.rsplit(".", 1)[0]][1]
        (found,) = [block for block in children(event, "option") if block["name"][1] == name]
        return found

    def test_variant_options_add_their_own_modifier(self):
        for option, variant, market in VARIANT_MODIFIERS:
            added = {value["name"][1] for key, value in walk(self.option(option))
                     if key == "add_modifier" and isinstance(value, dict)}
            self.assertIn(variant, added, option)
            self.assertNotIn(market, added, option)

    def test_variants_match_the_market_modifier(self):
        for _, variant, market in VARIANT_MODIFIERS:
            self.assertEqual(self.modifiers[variant][1], self.modifiers[market][1], variant)

    def test_variants_are_named(self):
        for _, variant, market in VARIANT_MODIFIERS:
            for key in (variant, variant + "_desc"):
                self.assertIn("\n %s:0 \"" % key, self.loc, key)
            # the new name is not the market one's
            name = self.loc.split("\n %s:0 \"" % variant, 1)[1].split('"', 1)[0]
            market_name = self.loc.split("\n %s:0 \"" % market, 1)[1].split('"', 1)[0]
            self.assertNotEqual(name, market_name)


if __name__ == "__main__":
    unittest.main()
