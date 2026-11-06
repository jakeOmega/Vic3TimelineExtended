"""The Space Race milestones' modifiers are scaling modifiers on their own entries (#1404).

Since 1.15 each of the seven billed milestone entries (suborbital through
interstellar probe, and solar colonization) declares, in
`scaling_modifiers_while_active`, its cost (`sr_space_program_cost`), its two
funding modifiers (`sr_funding_progress`, `sr_funding_throughput`), its approach
(`sr_safe_approach`, `sr_ambitious_approach`) and, for the four milestones with a
choice event, the thirteen choice modifiers (`sr_choice_*`). The engine re-reads
each value from the owning country about every four days (design:
docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md § 4.10).

Until then sr_recalculate_cost cleared and re-added the cost and funding on every
entry after each click, completion and `immediate`, and the monthly pulse
recalculated when participation, the solar production method or the funding cap
moved, or an entry lacked one (sr_cost_modifiers_missing). The approach and
choice modifiers were added by the buttons and the choice events and put back by
sr_sync_<m>_entry. These tests pin each declaration, evaluate its value against
the old multipliers and the old gates (billed, participation, the soft cap, the
solar method), and check the machinery is gone. test_journal_entry_shape.py
checks the tree-wide rule that nothing adds, removes or tests a declared key.
"""

import glob
import os
import re
import unittest

from test_space_race_soft_cap import Script, _ctx, _parse

REPO = os.path.dirname(os.path.abspath(__file__))
JE = os.path.join(REPO, "common", "journal_entries", "je_space_race.txt")
EVENTS = os.path.join(REPO, "events", "space_race_events.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "space_race_triggers.txt")

MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "mars_landing",
              "interstellar_probe", "solar_colonization")
# The cost and funding keys and the per-milestone value each declaration adds.
BILLED = {
    "sr_space_program_cost": "sr_{m}_cost",
    "sr_funding_progress": "sr_funding_{m}_effective",
    "sr_funding_throughput": "sr_funding_{m}_level",
}
APPROACHES = {"sr_safe_approach": "sr_safe_{m}", "sr_ambitious_approach": "sr_ambitious_{m}"}
# milestone -> (choice event, {choice modifier: the variable its option sets})
CHOICES = {
    "orbital": ("80", {"sr_choice_orbital_civilian": "sr_orbital_civilian",
                       "sr_choice_orbital_military": "sr_orbital_military",
                       "sr_choice_orbital_scientist": "sr_orbital_scientist"}),
    "moon_landing": ("5", {"sr_choice_site_shackleton": "sr_moon_site_shackleton",
                           "sr_choice_site_equatorial": "sr_moon_site_equatorial",
                           "sr_choice_site_tranquility": "sr_moon_site_tranquility",
                           "sr_choice_site_far_side": "sr_moon_site_far_side"}),
    "probe": ("81", {"sr_choice_probe_venus": "sr_probe_target_venus",
                     "sr_choice_probe_mars": "sr_probe_target_mars",
                     "sr_choice_probe_asteroid": "sr_probe_target_asteroid"}),
    "mars_landing": ("83", {"sr_choice_mars_direct": "sr_mars_direct",
                            "sr_choice_mars_orbital": "sr_mars_orbital_first",
                            "sr_choice_mars_robotic": "sr_mars_robotic"}),
}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def _block(text, name):
    m = re.compile(r"(?<![\w.])" + re.escape(name) + r"\s*=\s*\{").search(text)
    assert m, f"{name} not found"
    return text[m.end():_close(text, m.end() - 1)]


class Country(Script):
    """soft_cap's evaluator, with the two country reads sr_ai_should_participate
    makes: `is_player` (ctx["player"], default a player) and
    `global_country_ranking` (ctx["rank"])."""

    def check(self, body, ctx):
        rest = []
        for key, op, value in body:
            if key == "is_player":
                if ctx.get("player", True) != (value == "yes"):
                    return False
            elif key == "global_country_ranking":
                if not self.COMPARE[op](ctx.get("rank", 1), float(value)):
                    return False
            else:
                rest.append((key, op, value))
        return super().check(rest, ctx)


SCRIPT = Country()
ENTRIES = {key: body for key, _, body in _parse(_read(JE))}


def _declared(entry):
    """modifier -> [value body] for every scaling_modifiers_while_active block on the entry."""
    out = {}
    for key, _, body in ENTRIES[entry]:
        if key == "scaling_modifiers_while_active":
            fields = {k: v for k, _, v in body}
            out.setdefault(fields["modifier"], []).append(fields["value"])
    return out


def _value(milestone, modifier):
    values = _declared(f"je_space_race_{milestone}")[modifier]
    assert len(values) == 1, (milestone, modifier, len(values))
    return values[0]


def _billed_ctx(m, level, cap, approach=None, player=True, rank=1, solar_method=True, billed=True):
    ctx = _ctx(m, level, cap, billed=billed)
    if m == "solar_colonization" and billed:
        ctx["solar_method"] = solar_method
    if approach:
        ctx["vars"][f"sr_{approach}_{m}"] = 1
    ctx["player"] = player
    ctx["rank"] = rank
    return ctx


class DeclarationShapeTest(unittest.TestCase):
    def test_each_billed_entry_declares_its_keys_once(self):
        for m in MILESTONES:
            declared = _declared(f"je_space_race_{m}")
            expected = set(BILLED) | set(APPROACHES) | set(CHOICES.get(m, (None, {}))[1])
            with self.subTest(milestone=m):
                self.assertEqual(set(declared), expected)
                for modifier, values in declared.items():
                    self.assertEqual(len(values), 1, modifier)

    def test_the_awaiting_data_entry_declares_nothing(self):
        """je_space_race_interstellar_results has no funding, approach or choice."""
        self.assertEqual(_declared("je_space_race_interstellar_results"), {})

    def test_every_value_is_a_block_off_by_default(self):
        """Block form (vanilla's), starting at 0 and adding inside one gate, so a
        value outside its gate is 0 and the modifier is off the entry."""
        for m in MILESTONES:
            for modifier, values in _declared(f"je_space_race_{m}").items():
                with self.subTest(milestone=m, modifier=modifier):
                    body = values[0]
                    self.assertIsInstance(body, list)
                    self.assertEqual(body[0], ("value", "=", "0"))
                    self.assertEqual([k for k, _, _ in body], ["value", "if"])

    def test_cost_and_funding_add_the_old_multipliers_while_billed(self):
        for m in MILESTONES:
            for modifier, value in BILLED.items():
                with self.subTest(milestone=m, modifier=modifier):
                    gate = dict((k, v) for k, _, v in _value(m, modifier)[1][2])
                    self.assertEqual(gate["limit"], [(f"sr_milestone_billed_{m}", "=", "yes")])
                    self.assertEqual(gate["add"], value.format(m=m))

    def test_approaches_follow_their_variable(self):
        for m in MILESTONES:
            for modifier, var in APPROACHES.items():
                with self.subTest(milestone=m, modifier=modifier):
                    gate = dict((k, v) for k, _, v in _value(m, modifier)[1][2])
                    self.assertEqual(gate["limit"], [("has_variable", "=", var.format(m=m))])
                    self.assertEqual(gate["add"], "1")

    def test_choices_follow_their_variable_while_the_milestone_runs(self):
        """sr_sync_choice_modifier_base's gate: the milestone running and the
        choice's variable set. Every choice modifier is declared, and only on
        its own milestone's entry."""
        defined = set(re.findall(r"(?m)^(sr_choice_\w+) = \{",
                                 _read(os.path.join(REPO, "common", "static_modifiers", "space_race_modifiers.txt"))))
        named = {mod for _, choices in CHOICES.values() for mod in choices}
        self.assertEqual(named, defined)
        self.assertEqual(len(named), 13)
        for m, (_, choices) in CHOICES.items():
            for modifier, var in choices.items():
                with self.subTest(milestone=m, modifier=modifier):
                    gate = dict((k, v) for k, _, v in _value(m, modifier)[1][2])
                    self.assertEqual(gate["limit"], [("has_variable", "=", f"sr_active_{m}"),
                                                     ("has_variable", "=", var)])
                    self.assertEqual(gate["add"], "1")
                    others = [e for e in MILESTONES if e != m and modifier in _declared(f"je_space_race_{e}")]
                    self.assertEqual(others, [])


class BilledValueTest(unittest.TestCase):
    """The declared values, evaluated: the old multipliers while billed, 0 otherwise."""

    def test_billed_values_equal_the_old_multipliers(self):
        for m in MILESTONES:
            for cap in (3, 10):
                for level in (0, 1, cap, cap + 2, cap + 6):
                    for approach in (None, "safe", "ambitious"):
                        ctx = _billed_ctx(m, level, cap, approach)
                        for modifier, value in BILLED.items():
                            with self.subTest(milestone=m, cap=cap, level=level, approach=approach,
                                              modifier=modifier):
                                self.assertEqual(SCRIPT.evaluate(_value(m, modifier), ctx),
                                                 SCRIPT.value(value.format(m=m), ctx))

    def test_the_cost_counts_funding_and_the_approach(self):
        factors = {"suborbital": 1, "orbital": 1.5, "moon_landing": 2, "probe": 2, "mars_landing": 6,
                   "interstellar_probe": 12, "solar_colonization": 5}
        for m, factor in factors.items():
            for approach, overhead in ((None, 0), ("safe", 1), ("ambitious", 2)):
                with self.subTest(milestone=m, approach=approach):
                    ctx = _billed_ctx(m, 4, 7, approach)
                    self.assertAlmostEqual(SCRIPT.evaluate(_value(m, "sr_space_program_cost"), ctx),
                                           (4 + overhead) * factor, places=4)

    def test_an_unbilled_milestone_declares_zero(self):
        for m in MILESTONES:
            ctx = _billed_ctx(m, 5, 7, "ambitious", billed=False)
            for modifier in BILLED:
                with self.subTest(milestone=m, modifier=modifier):
                    self.assertEqual(SCRIPT.evaluate(_value(m, modifier), ctx), 0)

    def test_solar_colonization_with_its_method_off_is_not_billed(self):
        """Its entry stays open for the colonies (owner, 2026-09-29). Until #1404
        the monthly pulse caught the switch through sr_cost_solar_running."""
        on = _billed_ctx("solar_colonization", 3, 7, "safe")
        off = _billed_ctx("solar_colonization", 3, 7, "safe", solar_method=False)
        for modifier in BILLED:
            with self.subTest(modifier=modifier):
                self.assertGreater(SCRIPT.evaluate(_value("solar_colonization", modifier), on), 0)
                self.assertEqual(SCRIPT.evaluate(_value("solar_colonization", modifier), off), 0)

    def test_solar_colonization_costs_8_a_level_after_the_mars_landing(self):
        ctx = _billed_ctx("solar_colonization", 2, 7)
        self.assertAlmostEqual(SCRIPT.evaluate(_value("solar_colonization", "sr_space_program_cost"), ctx), 10)
        ctx["vars"]["sr_completed_mars_landing"] = 1
        self.assertAlmostEqual(SCRIPT.evaluate(_value("solar_colonization", "sr_space_program_cost"), ctx), 16)

    def test_an_ai_outside_the_top_three_pays_its_funding_not_its_approach(self):
        """sr_<m>_cost gates the approach overhead on sr_ai_should_participate.
        Until #1404 the monthly pulse caught a rank crossing 3 through
        sr_cost_participation; the declaration reads it live."""
        for m in MILESTONES:
            with self.subTest(milestone=m):
                inside = _billed_ctx(m, 3, 7, "ambitious", player=False, rank=2)
                outside = _billed_ctx(m, 3, 7, "ambitious", player=False, rank=4)
                plain = _billed_ctx(m, 3, 7, None, player=False, rank=4)
                cost = _value(m, "sr_space_program_cost")
                self.assertGreater(SCRIPT.evaluate(cost, inside), SCRIPT.evaluate(cost, outside))
                self.assertEqual(SCRIPT.evaluate(cost, outside), SCRIPT.evaluate(cost, plain))
                # a player always participates
                player = _billed_ctx(m, 3, 7, "ambitious", player=True, rank=9)
                self.assertEqual(SCRIPT.evaluate(cost, player), SCRIPT.evaluate(cost, inside))

    def test_the_pace_follows_the_live_cap(self):
        """The soft cap (lunar colonization design § 5.1): a moved cap moves the
        declared pace with no recalculation. Until #1404 sr_cost_funding_cap
        recorded the cap and the monthly pulse compared it."""
        for m in MILESTONES:
            with self.subTest(milestone=m):
                pace = _value(m, "sr_funding_progress")
                throughput = _value(m, "sr_funding_throughput")
                low, high = _billed_ctx(m, 9, 7), _billed_ctx(m, 9, 9)
                self.assertAlmostEqual(SCRIPT.evaluate(pace, low), 7 + 1 / 2 + 1 / 3, places=4)
                self.assertEqual(SCRIPT.evaluate(pace, high), 9)
                self.assertEqual(SCRIPT.evaluate(throughput, low), 9)
                self.assertEqual(SCRIPT.evaluate(throughput, high), 9)


class FlatValueTest(unittest.TestCase):
    def test_an_approach_is_on_exactly_while_its_variable_is_set(self):
        for m in MILESTONES:
            for approach in (None, "safe", "ambitious"):
                ctx = _billed_ctx(m, 1, 3, approach)
                for kind in ("safe", "ambitious"):
                    with self.subTest(milestone=m, approach=approach, modifier=kind):
                        self.assertEqual(SCRIPT.evaluate(_value(m, f"sr_{kind}_approach"), ctx),
                                         1 if approach == kind else 0)

    def test_a_choice_is_on_exactly_while_its_milestone_runs(self):
        for m, (_, choices) in CHOICES.items():
            for modifier, var in choices.items():
                with self.subTest(milestone=m, modifier=modifier):
                    ctx = _billed_ctx(m, 1, 3)
                    self.assertEqual(SCRIPT.evaluate(_value(m, modifier), ctx), 0)
                    ctx["vars"][var] = 1
                    self.assertEqual(SCRIPT.evaluate(_value(m, modifier), ctx), 1)
                    # completed: the variable stays for the rewards, the modifier goes
                    del ctx["vars"][f"sr_active_{m}"]
                    self.assertEqual(SCRIPT.evaluate(_value(m, modifier), ctx), 0)


class ChoiceEventTest(unittest.TestCase):
    def test_each_option_sets_its_variable_and_previews_the_modifier(self):
        """The option that added the modifier on the entry now sets the variable
        the declaration reads and shows the modifier (design § 4.0, rule 8). The
        preview keeps the bare `add_modifier = X` form the option had, which the
        Nation tab's scan of duration-less adds (gen_nation_tab.py, block form
        only) never counted: these sit on an entry, not the country."""
        events = _read(EVENTS)
        for m, (event, choices) in CHOICES.items():
            body = _block(events, f"space_race_events.{event}")
            made = _block(_read(TRIGGERS), f"sr_{m}_choice_made")
            for modifier, var in choices.items():
                with self.subTest(event=event, choice=var):
                    self.assertRegex(
                        body,
                        r"set_variable = \{ name = " + var + r" value = yes \}\s*"
                        r"show_as_tooltip = \{\s*je:je_space_race_" + m + r" \?= \{ add_modifier = "
                        + modifier + r" \}\s*\}")
                    self.assertIn(f"has_variable = {var}", made)
            self.assertNotRegex(body, r"je:je_space_race_\w+ = \{ add_modifier")


class MachineryGoneTest(unittest.TestCase):
    """The refresh, its caches, the repair and the approach/choice re-adds."""

    GONE = ("sr_recalculate_cost", "sr_clear_milestone_cost_modifiers_base",
            "sr_apply_milestone_cost_modifiers_base", "sr_cost_modifiers_missing",
            "sr_cost_participation", "sr_cost_solar_running", "sr_cost_funding_cap",
            "sr_sync_approach_modifier_base", "sr_sync_choice_modifier_base",
            "sr_sync_suborbital_entry", "sr_sync_orbital_entry", "sr_sync_moon_landing_entry",
            "sr_sync_probe_entry", "sr_sync_mars_landing_entry", "sr_sync_interstellar_probe_entry")

    def test_nothing_names_them(self):
        for sub in ("common", "events", "gui"):
            for path in glob.glob(os.path.join(REPO, sub, "**", "*.*"), recursive=True):
                if not path.endswith((".txt", ".gui")):
                    continue
                text = _read(path)
                for name in self.GONE:
                    with self.subTest(path=os.path.relpath(path, REPO), name=name):
                        self.assertNotRegex(text, r"\b" + name + r"\b")

    def test_each_immediate_refreshes_the_statuses(self):
        """sr_recalculate_cost's tail, kept: the panel's status line reads at once."""
        for m in MILESTONES:
            with self.subTest(milestone=m):
                immediate = _block(_block(_read(JE), f"je_space_race_{m}"), "immediate")
                self.assertIn("sr_refresh_milestone_statuses = yes", immediate)


if __name__ == "__main__":
    unittest.main()
