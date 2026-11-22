"""The Grand Tour: the Deep-Space Probe's fourth target (space_race_events.81.e).

A probe that passes Jupiter and the planets beyond it, for a player who will
pay for it. Nothing gates it; its cost is the limit. These tests hold the
shape of that bargain, not its numbers:

- every place that enumerates the probe's targets has the tour too (the
  choice-made trigger, the completion options and their fallback, the
  panel's profile line, the entry's declarations, the loc);
- the tour is the most costly profile: the only one that slows the program
  and the only one billed, through sr_probe_cost, for as long as the
  milestone is, whatever the funding and the approach;
- the tour pays the best total reward: every line a single target pays, none
  above the single target that pays most on that line, for longer;
- the AI never takes it by default and only as a participant with innovation
  to spare.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
EVENTS = os.path.join(REPO, "events", "space_race_events.txt")
MODIFIERS = os.path.join(REPO, "common", "static_modifiers", "space_race_modifiers.txt")
VALUES = os.path.join(REPO, "common", "script_values", "space_race_values.txt")
DISPLAY = os.path.join(REPO, "common", "script_values", "space_race_display_values.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "space_race_triggers.txt")
CUSTOM_LOC = os.path.join(REPO, "common", "customizable_localization", "space_race_custom_loc.txt")
JE = os.path.join(REPO, "common", "journal_entries", "je_space_race.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")

TOUR = "tour"
# What a bare duration name is worth, in days (vanilla's script values).
DAYS = {"long_modifier_time": 3650, "very_long_modifier_time": 7300}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _block(text, name):
    m = re.search(r"^[ \t]*" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    assert m, name
    depth, i = 0, m.end() - 1
    while True:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[m.end():i]
        i += 1


def _options(event_body):
    """The top-level option blocks of an event, in order."""
    out, pos = [], 0
    while True:
        m = re.search(r"^\toption = \{", event_body[pos:], re.M)
        if not m:
            return out
        start = pos + m.end()
        depth, i = 1, start
        while depth:
            depth += {"{": 1, "}": -1}.get(event_body[i], 0)
            i += 1
        out.append(event_body[start:i - 1])
        pos = i


def _lines(body):
    """A flat modifier block as {line: value}, icon aside."""
    return {k: float(v) for k, v in re.findall(r"^\s*(country_\w+)\s*=\s*(-?[\d.]+)\s*$", body, re.M)}


def _loc():
    values = {}
    for name in sorted(os.listdir(LOC_DIR)):
        if not name.endswith(".yml") or name == "te_unused_l_english.yml":
            continue
        with open(os.path.join(LOC_DIR, name), encoding="utf-8-sig") as f:
            for line in f:
                m = re.match(r'\s+([A-Za-z0-9_.\-]+):\d*\s+"(.*)"\s*$', line)
                if m:
                    values[m.group(1)] = m.group(2)
    return values


class GrandTourTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = _read(EVENTS)
        cls.modifiers = _read(MODIFIERS)
        cls.values = _read(VALUES)
        cls.loc = _loc()
        cls.choice = _options(_block(cls.events, "space_race_events.81"))
        cls.targets = [re.search(r"set_variable = \{ name = sr_probe_target_(\w+) value = yes \}", o).group(1)
                       for o in cls.choice]
        cls.singles = [t for t in cls.targets if t != TOUR]
        cls.profile = {t: _lines(_block(cls.modifiers, f"sr_choice_probe_{t}")) for t in cls.targets}
        cls.reward = {t: _lines(_block(cls.modifiers, f"sr_probe_target_{t}")) for t in cls.targets}

    def option(self, target):
        return self.choice[self.targets.index(target)]

    # ---- every enumeration of the targets has all of them -------------------

    def test_the_tour_is_one_of_the_choice_s_targets(self):
        self.assertIn(TOUR, self.targets)
        self.assertEqual(len(self.singles), 3)
        self.assertEqual(len(set(self.targets)), len(self.targets))

    def test_each_option_previews_its_profile_and_explains_itself(self):
        for target in self.targets:
            body = " ".join(self.option(target).split())
            with self.subTest(target=target):
                self.assertIn(f"je:je_space_race_probe ?= {{ add_modifier = sr_choice_probe_{target} }}", body)
                tooltip = re.search(r'custom_tooltip = \{ text = "?(\w+)"? \}', body).group(1)
                self.assertIn(tooltip, self.loc)
                name = re.search(r"name = (space_race_events\.81\.\w+)", body).group(1)
                self.assertIn(name, self.loc)

    def test_the_choice_counts_as_made_for_every_target(self):
        """sr_probe_choice_made keeps .81 from being asked twice."""
        made = set(re.findall(r"has_variable = sr_probe_target_(\w+)",
                              _block(_read(TRIGGERS), "sr_probe_choice_made")))
        self.assertEqual(made, set(self.targets))

    def test_the_completion_pays_every_target_and_the_fallback_excludes_each(self):
        options = _options(_block(self.events, "space_race_events.4"))
        paid = {}
        fallback = None
        for body in options:
            flat = " ".join(body.split())
            m = re.search(r"trigger = \{ has_variable = sr_probe_target_(\w+) \}", flat)
            if m:
                paid[m.group(1)] = flat
            else:
                fallback = flat
        self.assertEqual(set(paid), set(self.targets))
        for target, flat in paid.items():
            with self.subTest(target=target):
                self.assertIn("sr_apply_probe_reward = yes", flat)
                self.assertRegex(flat, rf"add_modifier = \{{ name = sr_probe_target_{target} days = \w+ is_decaying = yes \}}")
                self.assertIn(re.search(r"name = (space_race_events\.4\.\w+)", flat).group(1), self.loc)
        self.assertIsNotNone(fallback)
        self.assertEqual(set(re.findall(r"NOT = \{ has_variable = sr_probe_target_(\w+) \}", fallback)),
                         set(self.targets))

    def test_the_entry_declares_every_profile(self):
        entry = _block(_read(JE), "je_space_race_probe")
        declared = set(re.findall(r"modifier = sr_choice_probe_(\w+)", entry))
        self.assertEqual(declared, set(self.targets))

    def test_the_panel_s_profile_line_has_every_target(self):
        profile = " ".join(_block(_read(CUSTOM_LOC), "sr_probe_profile").split())
        for target in self.targets:
            with self.subTest(target=target):
                key = f"je_space_race_probe_status_{target}"
                self.assertIn(f"text = {{ trigger = {{ has_variable = sr_probe_target_{target} }} "
                              f"localization_key = {key} }}", profile)
                self.assertIn(key, self.loc)

    def test_every_modifier_has_its_name_and_description(self):
        for target in self.targets:
            for key in (f"sr_choice_probe_{target}", f"sr_probe_target_{target}"):
                self.assertIn(key, self.loc)
                self.assertIn(key + "_desc", self.loc)

    # ---- the most costly profile ------------------------------------------------

    def pace(self, target, base=2.5):
        """A month's progress under a profile, at a typical base."""
        lines = self.profile[target]
        return ((base + lines.get("country_space_race_progress_add", 0))
                * (1 + lines.get("country_space_race_progress_mult", 0)))

    def test_the_tour_is_the_slowest_profile(self):
        for base in (1.0, 2.5, 10.0):
            for target in self.singles:
                with self.subTest(base=base, target=target):
                    self.assertLess(self.pace(TOUR, base), self.pace(target, base))
        self.assertLess(self.profile[TOUR]["country_space_race_progress_mult"], 0)
        for target in self.singles:
            self.assertNotIn("country_space_race_progress_mult", self.profile[target])

    def test_only_the_tour_is_billed_and_like_an_approach(self):
        """Its term sits beside the approach overheads in sr_probe_cost, inside
        owner and before the factor, behind the same participation test, and is
        at least the Ambitious approach's two levels."""
        cost = " ".join(_block(self.values, "sr_probe_cost").split())
        billed = set(re.findall(r"has_variable = sr_probe_target_(\w+)", cost))
        self.assertEqual(billed, {TOUR})
        term = ("if = { limit = { has_variable = sr_probe_target_tour sr_ai_should_participate = yes } "
                "add = sr_tour_cost_levels_probe }")
        self.assertIn(term, cost)
        self.assertLess(cost.index(term), cost.index("multiply = sr_cost_factor_probe"))
        levels = float(_block(self.values, "sr_tour_cost_levels_probe").split()[-1])
        ambitious = float(re.search(r"has_variable = sr_ambitious_probe sr_ai_should_participate = yes \} "
                                    r"add = ([\d.]+)", cost).group(1))
        self.assertGreaterEqual(levels, ambitious)

    def test_the_bill_does_not_depend_on_anything_the_player_can_switch(self):
        """No funding level and no approach in the tour's term: nothing turned
        off and on avoids it while the milestone is billed."""
        cost = " ".join(_block(self.values, "sr_probe_cost").split())
        term = re.search(r"if = \{ limit = \{ ([^}]*sr_probe_target_tour[^}]*) \}", cost).group(1)
        self.assertEqual(term.split(), ["has_variable", "=", "sr_probe_target_tour",
                                        "sr_ai_should_participate", "=", "yes"])

    def test_the_option_prints_the_bill(self):
        display = " ".join(_block(_read(DISPLAY), "sr_disp_cost_tour_probe").split())
        self.assertEqual(display, "value = sr_disp_cost_safe_probe multiply = sr_tour_cost_levels_probe")
        self.assertIn("ScriptValue('sr_disp_cost_tour_probe')", self.loc["SR_PROBE_TOUR_CHOSEN_TT"])
        self.assertIn('text = "SR_PROBE_TOUR_CHOSEN_TT"', self.option(TOUR))

    # ---- the best total reward --------------------------------------------------

    def test_the_tour_pays_every_line_a_single_target_pays(self):
        lines = set().union(*(self.reward[t] for t in self.singles))
        self.assertEqual(set(self.reward[TOUR]), lines)

    def test_no_line_beats_the_target_whose_line_it_is(self):
        for line, value in self.reward[TOUR].items():
            best = max(self.reward[t].get(line, 0) for t in self.singles)
            with self.subTest(line=line):
                self.assertGreater(value, 0)
                self.assertLessEqual(value, best)

    def test_the_tour_s_total_is_the_best(self):
        """Each line as a share of the best single target's: the tour's sum
        beats every single target's."""
        best = {line: max(self.reward[t].get(line, 0) for t in self.singles) for line in self.reward[TOUR]}

        def total(target):
            return sum(value / best[line] for line, value in self.reward[target].items())

        for target in self.singles:
            with self.subTest(target=target):
                self.assertGreater(total(TOUR), total(target))

    def test_the_tour_s_data_lasts_longer(self):
        days = {}
        for body in _options(_block(self.events, "space_race_events.4")):
            m = re.search(r"name = sr_probe_target_(\w+)\s+days = (\w+)", body)
            if m:
                days[m.group(1)] = DAYS[m.group(2)]
        for target in self.singles:
            self.assertGreater(days[TOUR], days[target])

    # ---- the AI ---------------------------------------------------------------

    def test_the_ai_takes_the_tour_only_when_it_can_pay(self):
        body = self.option(TOUR)
        self.assertNotIn("default_option", body)
        chance = _block(body, "ai_chance")
        self.assertRegex(chance, r"base = 0\b")
        modifiers = re.findall(r"modifier = \{\s*trigger = \{(.*?)\}\s*add = (\d+)", chance, re.S)
        self.assertTrue(modifiers)
        for trigger, add in modifiers:
            self.assertIn("sr_ai_should_participate = yes", trigger)
            self.assertRegex(trigger, r"country_innovation > \d+")
        # Some other option is the default, and has a weight when the tour has none.
        others = [o for t, o in zip(self.targets, self.choice) if t != TOUR]
        self.assertEqual(sum("default_option = yes" in o for o in others), 1)
        for o in others:
            self.assertRegex(_block(o, "ai_chance"), r"base = [1-9]")


if __name__ == "__main__":
    unittest.main()
