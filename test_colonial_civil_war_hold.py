"""A civil war of its own neither brings a colonial empire back nor makes the AI give one up (#1735).

In a 1931–1939 game, Bornu's uprising cut two of its Sahel states off from its
capital, the colony test read them as overseas colonies, the re-entry pass added
`je_colonial_empire`, and twelve seconds later the AI pressed Planned Full
Decolonization and released both. Egypt released Palestine the same way a year
later, with no civil war: the button gave every minor +30 whatever its state
(whether Egypt was under pressure as well, for another 30, no save shows).
This test pins the four changes:

1. `ce_reentry_due` is false while the country fights a civil war of its own
   (`colonial_in_own_civil_war`, read from a live rebel country, never from
   `any_civil_war`, which iterates the civil wars still brewing).
2. The Planned Decolonization, Release Territory and Round Table buttons weigh 0
   in such a war while the bar is 40 or more
   (`colonial_ai_holds_colonies_in_civil_war`).
3. So does every release option of decolonization_events .1, .3, .9 and .13, and
   each of those events keeps an option the AI can still take.
4. Planned Decolonization's minor term counts only beside a reason to press it.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _read(*parts):
    text = (ROOT.joinpath(*parts)).read_text(encoding="utf-8-sig")
    return re.sub(r"#[^\n]*", "", text)


def _close(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unbalanced braces")


def _block(text, name, start=0):
    m = re.compile(r"(?<![\w.:$])" + re.escape(name) + r"\s*=\s*\{").search(text, start)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _norm(text):
    return " ".join(text.split())


def _options(event_body):
    """(name, body) of each top-level option of an event."""
    for m in re.finditer(r"(?<![\w.:$])option\s*=\s*\{", event_body):
        body = event_body[m.end():_close(event_body, m.end() - 1)]
        name = re.search(r"name\s*=\s*(\S+)", body).group(1)
        yield name, body


TRIGGERS = _read("common", "scripted_triggers", "colonial_empire_triggers.txt")
BUTTONS = _read("common", "scripted_buttons", "colonial_empire_buttons.txt")
EVENTS = _read("events", "decolonization_events.txt")
HOLD = "colonial_ai_holds_colonies_in_civil_war = yes"
RELEASES = ("form_decolonized_country = yes", "make_independent = yes", "decol_record_chosen_release = yes")
# Release options the hold does not read: the buttons' confirmations (the
# button's weight already did), the player's widget, and the declaration of
# independence, which comes only below a bar of 40.
NOT_A_CHOICE = {"decolonization_events.%s" % n for n in
                ("400.a", "400.b", "400.c", "401.a", "402.a", "402.b", "403.a", "403.b", "70.a", "70.b")}


class CivilWarTriggerTests(unittest.TestCase):
    def test_reads_a_live_rebel_not_a_brewing_civil_war(self):
        body = _norm(_block(TRIGGERS, "colonial_in_own_civil_war"))
        self.assertNotIn("any_civil_war", body)
        self.assertIn("civil_war_origin_country ?= scope:ce_cw_self", body)
        self.assertIn("is_revolutionary = yes", body)
        self.assertIn("is_secessionist = yes", body)

    def test_the_hold_is_the_bar_at_40_and_our_civil_war(self):
        body = _norm(_block(TRIGGERS, "colonial_ai_holds_colonies_in_civil_war"))
        self.assertEqual(body, "decol_iw_bar_below_40 = no colonial_in_own_civil_war = yes")


class ReentryTests(unittest.TestCase):
    def test_not_due_in_a_civil_war_of_its_own(self):
        due = _norm(_block(TRIGGERS, "ce_reentry_due"))
        self.assertIn("NOT = { colonial_in_own_civil_war = yes }", due)

    def test_the_country_walk_comes_after_the_state_walk(self):
        due = _norm(_block(TRIGGERS, "ce_reentry_due"))
        self.assertGreater(due.index("colonial_in_own_civil_war"), due.index("any_scope_state"))
        self.assertTrue(due.endswith("NOT = { colonial_in_own_civil_war = yes }"))


class ButtonTests(unittest.TestCase):
    def test_every_release_button_weighs_zero_under_the_hold(self):
        for button in ("ce_release_colonial_territory", "ce_planned_decolonization", "ce_round_table_conference"):
            chance = _block(_block(BUTTONS, button), "ai_chance")
            ifs = list(re.finditer(r"(?<![\w.:$])if\s*=\s*\{", chance))
            last = chance[ifs[-1].end():_close(chance, ifs[-1].end() - 1)]
            # Last, so no term after it can lift the zero.
            self.assertEqual(_norm(last), "limit = { %s } multiply = 0" % HOLD, button)

    def test_the_minor_term_needs_a_reason(self):
        chance = _block(_block(BUTTONS, "ce_planned_decolonization"), "ai_chance")
        for m in re.finditer(r"(?<![\w.:$])if\s*=\s*\{", chance):
            body = chance[m.end():_close(chance, m.end() - 1)]
            limit = _norm(_block(body, "limit"))
            if "NOT = { country_rank >= rank_value:great_power }" in limit:
                self.assertIn("OR = {", limit)
                for reason in ("colonial_gp_condemners_count >= 3", "colonial_low_acceptance_count >= 3",
                               "decol_iw_bar_below_40 = yes"):
                    self.assertIn(reason, limit)
                break
        else:
            self.fail("no minor term in ce_planned_decolonization")


class EventOptionTests(unittest.TestCase):
    def _events(self):
        for m in re.finditer(r"^(decolonization_events\.\d+)\s*=\s*\{", EVENTS, re.M):
            yield m.group(1), EVENTS[m.end():_close(EVENTS, m.end() - 1)]

    def test_every_release_choice_reads_the_hold(self):
        seen = set()
        for event, body in self._events():
            for name, option in _options(body):
                if not any(r in _norm(option) for r in RELEASES) or name in NOT_A_CHOICE:
                    continue
                seen.add(name)
                chance = _norm(_block(option, "ai_chance"))
                self.assertIn("modifier = { trigger = { %s } factor = 0 }" % HOLD, chance, name)
        for name in ("1.c", "1.d_neo", "3.a", "3.c", "9.c", "9.e", "13.a", "13.c"):
            self.assertIn("decolonization_events." + name, seen)

    def test_each_event_keeps_an_option_the_ai_can_take(self):
        events = dict(self._events())
        for event in ("decolonization_events.1", "decolonization_events.3",
                      "decolonization_events.9", "decolonization_events.13"):
            open_options = []
            for name, option in _options(events[event]):
                if HOLD in _norm(option):
                    continue
                trigger = re.search(r"(?<![\w.:$])trigger\s*=\s*\{", option)
                if trigger and trigger.start() < option.index("ai_chance"):
                    gate = _norm(option[trigger.end():_close(option, trigger.end() - 1)])
                    # Under the hold the bar is 40 or more: an option gated
                    # below 40 alone is closed.
                    if gate == "decol_iw_bar_below_40 = yes" or gate.startswith("decol_iw_bar_below_40 = yes "):
                        continue
                base = re.search(r"base\s*=\s*(\d+)", _block(option, "ai_chance"))
                if base and int(base.group(1)) > 0:
                    open_options.append(name)
            self.assertTrue(open_options, event)


if __name__ == "__main__":
    unittest.main()
