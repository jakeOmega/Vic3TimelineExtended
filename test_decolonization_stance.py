# -*- coding: utf-8 -*-
"""A country's stance on colonialism, and the Colonial Empire tab that outlives
the entry (owner, 2026-11-03).

The entry closes when it fails, succeeds or loses its colonies, and the tab
used to close with it, while The Colonial Question (decolonization_events.14)
asked every great power for a stance every three years. Now:

- the stance changes from the tab: three buttons, a cooldown, and influence
  for either side while the stance counts (a great power's);
- a player meets The Colonial Question once; the AI keeps it, with an
  influence start line and a monthly drop below zero;
- the tab opens once the country has researched Decolonization, showing the
  stance and the largest colonial powers without the entry.

These tests hold the pieces to one another: the setters are the only writers
of the stance, every surface calls them, the figures agree, and the sections
the tab shows without the entry never read the entry.

Run: python3 -m unittest test_decolonization_stance -v
"""

import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


EFFECTS = _path("common", "scripted_effects", "decolonization_stance_effects.txt")
TRIGGERS = _path("common", "scripted_triggers", "decolonization_stance_triggers.txt")
VALUES = _path("common", "script_values", "decolonization_stance_values.txt")
MODIFIERS = _path("common", "static_modifiers", "extra_modifiers.txt")
EVENTS = _path("events", "decolonization_events.txt")
ON_ACTIONS = _path("common", "on_actions", "extra_on_actions.txt")
UN_VOTE = _path("common", "scripted_effects", "un_vote_effects.txt")
DECOL = _path("common", "scripted_effects", "decolonization.txt")
CE_SGUIS = _path("common", "scripted_guis", "colonial_empire_sguis.txt")
TAB_SGUIS = _path("common", "scripted_guis", "te_system_tab_sguis.txt")
GUI = _path("gui", "journal_entry_widgets", "colonial_empire_widget.gui")
LOC_DIR = _path("localization", "english")

STANCE_VARS = ("gp_anti_colonial_stance", "gp_pro_colonial_stance")
STANCE_MODIFIERS = ("gp_anti_colonial_policy_modifier", "gp_pro_colonial_policy_modifier")
SIDES = ("anti", "neutral", "pro")


def _raw(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _read(path):
    return re.sub(r"#[^\n]*", "", _raw(path))


def _block(text, name, prefix=r"^\t*"):
    """The body of the first ``name = { ... }`` block."""
    m = re.search(prefix + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


def _gui_type(text, name):
    """The body of ``type <name> = <base> {``, a type in the file's types block."""
    m = re.search(rf"^\ttype {re.escape(name)} = \w+ \{{", text, re.M)
    if m is None:
        raise AssertionError(f"type {name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"type {name} is not closed")


def _value(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*(-?\d+(?:\.\d+)?)\b", text, re.M)
    if m is None:
        raise AssertionError(f"{name} is not a constant")
    return float(m.group(1))


def _loc():
    keys = {}
    for path in glob.glob(os.path.join(LOC_DIR, "*_l_english.yml")):
        for line in _raw(path).splitlines():
            m = re.match(r'^ ([\w.\-]+):\d* "(.*)"\s*$', line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


def _script_files():
    for sub in ("common", "events"):
        yield from glob.glob(os.path.join(REPO, sub, "**", "*.txt"), recursive=True)


class WritersTest(unittest.TestCase):
    """The setters are the only writers of the stance and its modifiers."""

    def test_only_the_setters_write_a_stance(self):
        allowed = {os.path.normpath(EFFECTS), os.path.normpath(_path("events", "te_debug_colonial_empire_events.txt"))}
        for path in _script_files():
            text = _read(path)
            for var in STANCE_VARS:
                with self.subTest(path=os.path.relpath(path, REPO), var=var):
                    writes = re.findall(rf"\bset_variable = (?:\{{ name = )?{var}\b", text)
                    if os.path.normpath(path) not in allowed:
                        self.assertFalse(writes, f"{var} set outside the stance setters")

    def test_only_the_setters_add_the_policy_modifiers(self):
        for path in _script_files():
            text = _read(path)
            for modifier in STANCE_MODIFIERS:
                adds = re.findall(rf"add_modifier = \{{\s*name = {modifier}\b([^}}]*)\}}", text)
                with self.subTest(path=os.path.relpath(path, REPO), modifier=modifier):
                    if os.path.normpath(path) != os.path.normpath(EFFECTS):
                        self.assertFalse(adds, f"{modifier} added outside the stance setters")
                    for rest in adds:
                        # held while the stance counts: never a duration
                        self.assertNotRegex(rest, r"\b(days|months|years)\b")

    def test_each_core_writes_its_modifiers_on_great_power_rank(self):
        effects = _read(EFFECTS)
        for side, mine, other in (("anti", "gp_anti_colonial_policy_modifier", "gp_pro_colonial_policy_modifier"),
                                  ("pro", "gp_pro_colonial_policy_modifier", "gp_anti_colonial_policy_modifier")):
            core = _block(effects, f"decol_stance_core_{side}")
            with self.subTest(side=side):
                self.assertIn("decol_stance_start_cooldown = yes", core)
                self.assertIn(f"remove_modifier = {other}", core)
                self.assertRegex(core, rf"country_rank >= rank_value:great_power\s*NOT = \{{ has_modifier = {mine} \}}"
                                       rf"\s*\}}\s*add_modifier = \{{ name = {mine} \}}")
        neutral = _block(effects, "decol_stance_core_neutral")
        for name in STANCE_MODIFIERS:
            self.assertIn(f"remove_modifier = {name}", neutral)
        self.assertIn("decol_stance_start_cooldown = yes", neutral)

    def test_each_take_is_its_core_with_a_tooltip(self):
        effects = _read(EFFECTS)
        for side in SIDES:
            take = _block(effects, f"decol_stance_take_{side}")
            with self.subTest(side=side):
                self.assertIn(f"custom_tooltip = decol_stance_take_{side}_tt", take)
                self.assertIn(f"decol_stance_core_{side} = yes", take)

    def test_the_refresh_follows_the_variables_and_the_rank(self):
        triggers = _read(TRIGGERS)
        for side, var in (("anti", "gp_anti_colonial_stance"), ("pro", "gp_pro_colonial_stance")):
            counts = _block(triggers, f"decol_stance_{side}_counts")
            self.assertIn(f"has_variable = {var}", counts)
            self.assertIn("country_rank >= rank_value:great_power", counts)
        refresh = _block(_read(EFFECTS), "decol_stance_refresh")
        for side, modifier in (("anti", "gp_anti_colonial_policy_modifier"), ("pro", "gp_pro_colonial_policy_modifier")):
            self.assertIn(f"decol_stance_{side}_counts = yes", refresh)
            self.assertIn(f"add_modifier = {{ name = {modifier} }}", refresh)
            self.assertIn(f"remove_modifier = {modifier}", refresh)


class SurfacesTest(unittest.TestCase):
    """The Colonial Question, the UN vote, the buttons, the monthly pass and a
    revolution's repair all go through the setters."""

    def test_the_colonial_question_calls_the_takes(self):
        event = _block(_read(EVENTS), "decolonization_events.14", prefix=r"^")
        self.assertIn("decol_stance_question_due = yes", _block(event, "trigger"))
        self.assertIn("set_variable = decol_stance_asked", _block(event, "immediate"))
        options = re.findall(r"\boption = \{", event)
        self.assertEqual(len(options), 3)
        for side in SIDES:
            self.assertEqual(event.count(f"decol_stance_take_{side} = yes"), 1, side)
        for var in STANCE_VARS:
            self.assertNotIn(var, event, "the event writes no stance itself")
        # Both sides cost influence: shown greyed without it, the AI held to
        # its start line; neutral is free, so it is the default.
        self.assertEqual(event.count("trigger = { decol_stance_affordable = yes }"), 2)
        self.assertEqual(event.count("show_as_unavailable = { always = yes }"), 2)
        self.assertEqual(event.count("trigger = { NOT = { decol_stance_ai_can_hold = yes } }"), 2)
        neutral = event[event.index("name = decolonization_events.14.b"):]
        self.assertIn("default_option = yes", neutral[:200])
        self.assertEqual(event.count("default_option = yes"), 1)

    def test_a_player_is_asked_once(self):
        due = _block(_read(TRIGGERS), "decol_stance_question_due")
        self.assertIn("is_ai = yes", due)
        self.assertIn("NOT = { has_variable = decol_stance_asked }", due)
        pool = _read(ON_ACTIONS)
        entry = pool[:pool.index("trigger_event = { id = decolonization_events.14 }")]
        self.assertIn("decol_stance_question_due = yes", entry[-600:])

    def test_the_un_vote_takes_the_core(self):
        text = _read(UN_VOTE)
        self.assertRegex(text, r"custom_tooltip = \{\s*text = decol_stance_un_vote_tt\s*decol_stance_core_anti = yes\s*\}")

    def test_the_monthly_pass_and_the_repair(self):
        pulse = _block(_read(ON_ACTIONS), "decolonization_events_on_action", prefix=r"^")
        self.assertIn("decol_stance_monthly = yes", pulse)
        # every player, tab open or not: National Info shows another country's
        # Colonial Powers to a player without Decolonization
        self.assertRegex(pulse, r"is_player = yes\s*has_game_rule = decolonization_enabled"
                                r"\s*\}\s*decol_world_refresh_display = yes")
        monthly = _block(_read(EFFECTS), "decol_stance_monthly")
        self.assertRegex(monthly, r"is_ai = yes\s*decol_stance_paid = yes\s*influence < 0\s*\}\s*decol_stance_core_neutral = yes")
        self.assertIn("decol_stance_refresh = yes", monthly)
        self.assertIn("decol_stance_refresh = yes", _block(_read(DECOL), "decol_repair_after_civil_war"))

    def test_the_buttons_op_table(self):
        sgui = _block(_read(CE_SGUIS), "colonial_empire_stance_sgui")
        self.assertIn("ai_is_valid = { always = no }", sgui)
        self.assertIn("is_shown = { always = yes }", sgui)
        for op, side in enumerate(SIDES):
            with self.subTest(op=op):
                self.assertRegex(sgui, rf"scope:op = {op} \}}\s*decol_stance_possible_{side} = yes")
                self.assertRegex(sgui, rf"scope:op = {op} \}}\s*decol_stance_take_{side} = yes")
        self.assertIn("decol_world_refresh_display = yes", _block(sgui, "effect"))
        gui = _raw(GUI)
        stance = _gui_type(gui, "te_ce_sec_stance")
        for op, side in enumerate(SIDES):
            self.assertEqual(stance.count(f"MakeScopeValue( '(CFixedPoint){op}' )"), 4, side)
            self.assertIn(f'text = "je_colonial_empire_stance_btn_{side}"', stance)

    def test_the_gates(self):
        triggers = _read(TRIGGERS)
        for side in ("anti", "pro"):
            gate = _block(triggers, f"decol_stance_possible_{side}")
            for line in ("decol_stance_current_tt", "decol_stance_not_cooling_down = yes",
                         "decol_stance_great_power_tt", "decol_stance_affordable = yes"):
                self.assertIn(line, gate, side)
        neutral = _block(triggers, "decol_stance_possible_neutral")
        self.assertIn("decol_stance_not_cooling_down = yes", neutral)
        self.assertNotIn("great_power", neutral)
        self.assertNotIn("influence", neutral)
        affordable = _block(triggers, "decol_stance_affordable")
        self.assertIn("decol_stance_paid = yes", affordable)
        self.assertIn("influence >= decol_stance_influence_cost", affordable)


class FiguresTest(unittest.TestCase):
    """Each figure is restated in the modifiers, the values and the tooltips."""

    @classmethod
    def setUpClass(cls):
        cls.values = _read(VALUES)
        cls.loc = _loc()

    def test_the_cost(self):
        cost = _value(self.values, "decol_stance_influence_cost")
        modifiers = _read(MODIFIERS)
        for name in STANCE_MODIFIERS:
            body = _block(modifiers, name, prefix=r"^")
            self.assertIn(f"country_influence_cost_add = {int(cost)}", body, name)
            self.assertNotIn("country_influence_add", body, name)
        for key in ("decol_stance_influence_tt", "decol_stance_un_vote_tt"):
            self.assertIn(f"#bold {int(cost)}#!", self.loc[key], key)

    def test_the_cooldown(self):
        months = int(_value(self.values, "decol_stance_cooldown_months"))
        for key in ("decol_stance_cooldown_tt", "decol_stance_un_vote_tt", "decol_stance_take_anti_tt",
                    "decol_stance_take_pro_tt", "decol_stance_take_neutral_tt"):
            self.assertIn(f"#bold {months}#! months", self.loc[key], key)
        # The Colonial Question's description says "every two years".
        self.assertEqual(months, 24)
        self.assertIn("every two years", self.loc["decolonization_events.14.d"])

    def test_the_status_codes_match_the_rows(self):
        """ce_power_status: 0 not begun, 1-5 the band, 6 secured, 7 collapsed,
        each with its own cell in the row."""
        status = _block(self.values, "ce_power_status")
        self.assertIn("value = colonial_empire_live_tier", status)
        self.assertRegex(status, r"has_variable = colonial_empire_completed \}\s*value = 6")
        self.assertRegex(status, r"has_variable = colonial_empire_collapsed_recently \}\s*value = 7")
        row = _gui_type(_raw(GUI), "te_ce_power_row")
        names = ["not_begun", "collapsing", "crumbling", "strained", "stable", "solidified", "secured", "collapsed"]
        for code, name in enumerate(names):
            with self.subTest(code=code):
                self.assertRegex(row, rf"'\(CFixedPoint\){code}' \)\]\"\s*text = \"je_colonial_empire_power_status_{name}\"")
                self.assertIn(f"je_colonial_empire_power_status_{name}_tt", self.loc)


class TabTest(unittest.TestCase):
    """The tab opens with the research; without the entry it shows the readout,
    whose sections read the player and never the entry."""

    def test_the_readout_gate_excludes_the_entry(self):
        sguis = _read(TAB_SGUIS)
        readout = _block(sguis, "te_window_colonial_empire_readout_sgui")
        self.assertIn("NOT = { has_journal_entry = je_colonial_empire }", readout)
        self.assertIn("ce_tab_unlocked = yes", readout)
        self.assertIn("has_journal_entry = je_colonial_empire", _block(sguis, "te_window_colonial_empire_tab_sgui"))
        self.assertIn("has_technology_researched = decolonization", _block(_read(TRIGGERS), "ce_tab_unlocked"))

    def test_the_body_shows_the_readout_before_the_gate(self):
        gui = _raw(GUI)
        body = _gui_type(gui, "te_ce_tab_body")
        start = body.index('blockoverride "tab_before_gate" {')
        before = body[start:body.index('blockoverride "tab_gate" {')]
        self.assertIn("te_window_colonial_empire_readout_sgui", before)
        self.assertIn("te_ce_readout = {}", before)
        readout = _gui_type(gui, "te_ce_readout")
        self.assertEqual(re.findall(r"^\t\t(te_ce_sec_\w+) = \{\}", readout, re.M), ["te_ce_sec_stance", "te_ce_sec_powers"])
        self.assertIn("te_window_colonial_empire_entry_unlock_sgui", readout)

    def test_the_outliving_sections_read_the_player_only(self):
        gui = _raw(GUI)
        loc = _loc()
        for name in ("te_ce_readout", "te_ce_sec_stance", "te_ce_sec_powers", "te_ce_stance_line",
                     "te_ce_power_head", "te_ce_power_row"):
            body = _gui_type(gui, name)
            with self.subTest(type=name):
                self.assertNotIn("JournalEntry", body)
                for key in re.findall(r'(?:text|tooltip) = "(\w+)"', body):
                    self.assertNotIn("JournalEntry", loc.get(key, ""), key)
                    self.assertIn(key, loc, f"{key} has no loc")


VANILLA_LAWS = _path("vanilla_parsed", "common", "laws.json")
VANILLA_IDEOLOGIES = _path("vanilla_parsed", "common", "ideologies.json")
AI_TRIGGERS = ("decol_holds_colonial_empire", "decol_ai_regressive", "decol_ai_slaveholding",
               "decol_ai_partner_holds_empire", "decol_ai_colonial_laws", "decol_ai_illiberal")


def _option(event, name):
    """The body of the option whose ``name`` is ``name``."""
    start = event.index(f"name = {name}")
    start = event.rindex("option = {", 0, start)
    return _block(event[start:], "option", prefix=r"")


def _weights(option):
    """The option's ai_chance as (trigger body, 'add'|'factor', number), in order."""
    chance = _block(option, "ai_chance", prefix=r"")
    rows = []
    for m in re.finditer(r"\bmodifier = \{", chance):
        body = _block(chance[m.start():], "modifier", prefix=r"")
        trigger = _block(body, "trigger", prefix=r"")
        kind = re.search(r"\b(add|factor) = (-?\d+(?:\.\d+)?)\s*$", body.strip())
        rows.append((trigger.strip(), kind.group(1), float(kind.group(2))))
    return rows


class AiStanceTest(unittest.TestCase):
    """Issue #1370 (owner, 2026-11-03): the AI never condemns colonialism while
    it runs an empire, and condemns it less often when it is regressive or a
    partner of an empire. The Colonial Question's weights and the monthly
    review."""

    @classmethod
    def setUpClass(cls):
        cls.event = _block(_read(EVENTS), "decolonization_events.14", prefix=r"^")
        cls.triggers = _read(TRIGGERS)
        cls.condemn = _weights(_option(cls.event, "decolonization_events.14.a"))
        cls.neutral = _weights(_option(cls.event, "decolonization_events.14.b"))
        cls.support = _weights(_option(cls.event, "decolonization_events.14.c"))

    def _row(self, rows, trigger, kind):
        found = [n for t, k, n in rows if t == trigger and k == kind]
        self.assertEqual(len(found), 1, f"{kind} on {trigger!r}")
        return found[0]

    def test_an_empire_never_condemns(self):
        self.assertEqual(self._row(self.condemn, "decol_holds_colonial_empire = yes", "factor"), 0)
        # The old -10 for colonies is gone: the factor does its work, and the
        # +15 for powers without colonies reads the same test.
        self.assertNotIn(-10, [n for _, k, n in self.condemn if k == "add"])
        self.assertEqual(self._row(self.condemn, "NOT = { decol_holds_colonial_empire = yes }", "add"), 15)
        # An empire backs the colonial powers instead.
        self.assertEqual(self._row(self.support, "decol_holds_colonial_empire = yes", "add"), 10)

    def test_more_likely_to_back_the_colonial_powers(self):
        """Owner, 2026-11-03: the AI backs colonialism more often with a
        colonizing law, an illiberal government, or an empire of its own or
        a partner's. Support's adds; the event comment's table assumes these."""
        for trigger, add in (("decol_ai_partner_holds_empire = yes", 8), ("decol_ai_colonial_laws = yes", 8),
                             ("decol_ai_illiberal = yes", 8)):
            with self.subTest(trigger=trigger):
                self.assertEqual(self._row(self.support, trigger, "add"), add)
        # Only Support reads the two new tests: Condemn and Neutral are as #1370 left them.
        for rows in (self.condemn, self.neutral):
            self.assertEqual([t for t, _, _ in rows if t in ("decol_ai_colonial_laws = yes", "decol_ai_illiberal = yes")], [])

    def test_the_colonizing_laws_and_the_illiberal_ones(self):
        laws = _block(self.triggers, "decol_ai_colonial_laws")
        self.assertEqual(sorted(re.findall(r"has_law_or_variant = law_type:(law_\w+)", laws)),
                         ["law_colonial_exploitation", "law_colonial_resettlement"])
        body = _block(self.triggers, "decol_ai_illiberal")
        # Every unelected Distribution of Power law and Outlawed Dissent, each
        # with its variants (has_law_or_variant); not Censorship, most
        # countries' starting law.
        illiberal = re.findall(r"has_law_or_variant = law_type:(law_\w+)", _block(body, "OR", prefix=r""))
        self.assertEqual(sorted(illiberal), sorted([
            "law_autocracy", "law_oligarchy", "law_elder_council", "law_technocracy", "law_single_party_state",
            "law_algorithmic_governance", "law_outlawed_dissent"]))
        self.assertNotIn("has_law =", body + laws, "a bare has_law would miss a variant")
        # A Council Republic is never illiberal here (owner, 2026-11-03), so a
        # Soviet-style single-party state gains no Support from it.
        self.assertRegex(body.strip(), r"^NOT = \{ has_law_or_variant = law_type:law_council_republic \}\s*OR = \{")
        import json
        with open(VANILLA_LAWS, encoding="utf-8") as f:
            vanilla = json.load(f)
        known = set(vanilla)
        for path in glob.glob(_path("common", "laws", "*.txt")):
            known |= set(re.findall(r"^(law_\w+) = \{", _read(path), re.M))
        for law in illiberal + ["law_colonial_exploitation", "law_colonial_resettlement", "law_council_republic"]:
            self.assertIn(law, known)
            # Each named law is a parent, not itself a variant.
            self.assertNotIn("parent", vanilla.get(law, ["=", {}])[1], law)
        # Vanilla's variants of those laws are covered by their parents.
        variants = sorted(k for k, v in vanilla.items() if v[1].get("parent", ["=", ""])[1] in illiberal)
        self.assertEqual(variants, ["law_bakufu", "law_neo_absolutism", "law_organic_regulation"])

    def test_less_likely_for_a_stake_in_colonialism(self):
        for trigger in ("decol_ai_regressive = yes", "decol_ai_slaveholding = yes",
                        "decol_ai_partner_holds_empire = yes"):
            with self.subTest(trigger=trigger):
                self.assertEqual(self._row(self.condemn, trigger, "factor"), 0.5)
        # Slavery is regressive and halves Condemn again (owner, 2026-11-03):
        # a slaveholding power at a quarter.
        self.assertIn("decol_ai_slaveholding = yes", _block(self.triggers, "decol_ai_regressive"))
        self.assertIn("NOT = { has_law = law_type:law_slavery_banned }", _block(self.triggers, "decol_ai_slaveholding"))
        self.assertGreater(self._row(self.neutral, "decol_ai_regressive = yes", "add"), 0)
        self.assertGreater(self._row(self.support, "decol_ai_partner_holds_empire = yes", "add"), 0)

    def test_no_add_after_a_factor(self):
        """The weights apply in order: an add after factor = 0 would lift it."""
        for name, rows in (("condemn", self.condemn), ("neutral", self.neutral), ("support", self.support)):
            kinds = [k for _, k, _ in rows]
            with self.subTest(option=name):
                if "factor" in kinds:
                    self.assertNotIn("add", kinds[kinds.index("factor"):])

    def test_the_weights_read_no_is_ai(self):
        for side in ("a", "b", "c"):
            chance = _block(_option(self.event, f"decolonization_events.14.{side}"), "ai_chance", prefix=r"")
            self.assertNotIn("is_ai", chance, side)
        for name in AI_TRIGGERS:
            self.assertNotIn("is_ai", _block(self.triggers, name), name)

    def test_the_empire_test_is_the_entrys(self):
        """je_colonial_empire's `possible`: a colony or a colonial subject; or
        the entry itself."""
        empire = _block(self.triggers, "decol_holds_colonial_empire")
        for line in ("has_journal_entry = je_colonial_empire", "country_has_qualifying_colonial_subject = yes",
                     "any_scope_state = { is_overseas_colonial_state = yes }"):
            self.assertIn(line, empire)

    def test_the_partners(self):
        partner = _block(self.triggers, "decol_ai_partner_holds_empire")
        for line in ("has_treaty_alliance_with = { TARGET = scope:decol_ai_self }",
                     "has_treaty_defensive_pact_with = { TARGET = scope:decol_ai_self }",
                     "is_in_same_power_bloc = scope:decol_ai_self",
                     "is_subject_of = scope:decol_ai_self",
                     "overlord ?= { decol_holds_colonial_empire = yes }"):
            self.assertIn(line, partner)
        self.assertIn("NOT = { this = scope:decol_ai_self }", partner)
        self.assertEqual(partner.count("decol_holds_colonial_empire = yes"), 2)

    def test_every_trigger_is_defined(self):
        """Each scripted trigger the weights and the new tests call exists."""
        defined = set()
        for path in glob.glob(_path("common", "scripted_triggers", "*.txt")):
            defined |= set(re.findall(r"^([A-Za-z_]\w*) = \{", _read(path), re.M))
        for name in AI_TRIGGERS:
            self.assertIn(name, defined)
        calls = re.compile(r"\b(decol_\w+|country_has_\w+|is_overseas_\w+) = yes")
        called = set()
        for side in ("a", "b", "c"):
            chance = _block(_option(self.event, f"decolonization_events.14.{side}"), "ai_chance", prefix=r"")
            called |= set(calls.findall(chance))
        for name in AI_TRIGGERS:
            called |= set(calls.findall(_block(self.triggers, name)))
        self.assertLessEqual(set(AI_TRIGGERS), called)
        self.assertLessEqual({"country_has_qualifying_colonial_subject", "is_overseas_colonial_state"}, called)
        for name in sorted(called):
            with self.subTest(trigger=name):
                self.assertIn(name, defined)

    def test_the_regressive_signals_exist(self):
        """Each law and ideology the regressive test names is in the game."""
        import json
        with open(VANILLA_LAWS, encoding="utf-8") as f:
            laws = set(json.load(f))
        for path in glob.glob(_path("common", "laws", "*.txt")):
            laws |= set(re.findall(r"^(law_\w+) = \{", _read(path), re.M))
        with open(VANILLA_IDEOLOGIES, encoding="utf-8") as f:
            ideologies = json.load(f)
        regressive = _block(self.triggers, "decol_ai_regressive") + _block(self.triggers, "decol_ai_slaveholding")
        named_laws = re.findall(r"law_type:(law_\w+)", regressive)
        self.assertGreaterEqual(len(named_laws), 4)
        for law in named_laws:
            self.assertIn(law, laws)
        named = re.findall(r"ideology:(ideology_\w+)", regressive)
        self.assertEqual(sorted(named), ["ideology_colonialist", "ideology_jingoist_leader"])
        for ideology in named:
            self.assertIn(ideology, ideologies)
        # The ruler's is a leader ideology, the government's an interest group's.
        self.assertEqual(ideologies["ideology_jingoist_leader"][1].get("character_ideology", ["=", "no"])[1], "yes")
        self.assertNotIn("character_ideology", ideologies["ideology_colonialist"][1])

    def test_the_monthly_review_drops_an_empires_condemnation(self):
        monthly = _block(_read(EFFECTS), "decol_stance_monthly")
        self.assertRegex(monthly, r"\}\s*else_if = \{\s*limit = \{\s*is_ai = yes\s*has_variable = gp_anti_colonial_stance"
                                  r"\s*NOT = \{ has_variable = decol_stance_months_left \}"
                                  r"\s*decol_holds_colonial_empire = yes\s*\}\s*decol_stance_core_neutral = yes\s*\}"
                                  r"\s*else = \{\s*decol_stance_refresh = yes")
        # After the influence drop, which it must not shadow.
        self.assertLess(monthly.index("influence < 0"), monthly.index("decol_holds_colonial_empire"))

    def test_the_factor_order_self_check(self):
        """TE_SELF_CHECK ai_condemn_factor_order: BROKEN once a game when an AI
        empire takes Condemn, OK once when one takes another side with Condemn
        open to it; hidden, and logged with proven accessors only."""
        raw = _raw(EFFECTS)
        for name, verdict, flag in (("decol_selfcheck_empire_condemned", "BROKEN", "te_decol_cfo_broken_logged"),
                                    ("decol_selfcheck_empire_declined", "OK", "te_decol_cfo_ok_logged")):
            body = _block(raw, name, prefix=r"^")
            with self.subTest(check=name):
                self.assertRegex(body.strip(), r"^hidden_effect = \{")
                limit = _block(body, "limit", prefix=r"")
                for line in ("is_ai = yes", "decol_holds_colonial_empire = yes",
                             f"NOT = {{ has_global_variable = {flag} }}"):
                    self.assertIn(line, limit)
                self.assertIn(f"set_global_variable = {flag}", body)
                logs = re.findall(r'debug_log = "([^"]*)"', body)
                self.assertEqual(len(logs), 1)
                self.assertTrue(logs[0].startswith(f"TE_SELF_CHECK {verdict} ai_condemn_factor_order "), logs[0])
                self.assertIn("country=[THIS.GetCountry.GetTagName]", logs[0])
                self.assertIn("date=[TimeKeeper.GetCurrentDate.GetString]", logs[0])
                self.assertEqual(re.findall(r"\[([^\]]*)\]", logs[0]),
                                 ["THIS.GetCountry.GetTagName", "TimeKeeper.GetCurrentDate.GetString"])
        # An OK needs Condemn to have been open: the influence for it.
        declined = _block(_block(raw, "decol_selfcheck_empire_declined", prefix=r"^"), "limit", prefix=r"")
        self.assertIn("decol_stance_affordable = yes", declined)
        self.assertIn("decol_stance_ai_can_hold = yes", declined)
        # Each option calls its check before its take changes the stance.
        for side, check in (("a", "condemned"), ("b", "declined"), ("c", "declined")):
            option = _option(self.event, f"decolonization_events.14.{side}")
            with self.subTest(option=side):
                self.assertEqual(option.count("decol_selfcheck_empire_"), 1)
                self.assertLess(option.index(f"decol_selfcheck_empire_{check} = yes"),
                                option.index("decol_stance_take_"))
        # The play-test list names it, with a fallback.
        playtest = _raw(_path("docs", "testing", "colonial-holdings-playtest.md"))
        self.assertRegex(playtest, r"\| `ai_condemn_factor_order` \|[^\n]*\| [^\n]*decol_ai_condemn_weight[^\n]*\|\n")



class PrestigeShareTest(unittest.TestCase):
    """Owner, 2026-11-03: each country's Colonial Empire tab says its share of
    great-power prestige. Our Stance on Colonialism shows it for any country,
    with the entry or without it, from a monthly global total, so the panel
    walks no country."""

    def test_the_global_monthly_total(self):
        on_actions = _read(ON_ACTIONS)
        self.assertIn("decol_gp_prestige_on_action", _block(on_actions, "on_monthly_pulse", prefix=r"^"))
        body = _block(on_actions, "decol_gp_prestige_on_action", prefix=r"^")
        self.assertIn("has_game_rule = decolonization_enabled", body)
        self.assertIn("set_global_variable = { name = decol_gp_prestige_total value = decol_gp_prestige_sum }", body)
        total = _block(_read(VALUES), "decol_gp_prestige_sum", prefix=r"^")
        self.assertRegex(total, r"every_country = \{\s*limit = \{ country_rank >= rank_value:great_power \}\s*add = prestige\s*\}")
        self.assertIn("min = 1", total)

    def test_the_lines_figure(self):
        share = _block(_read(VALUES), "decol_stance_disp_gp_share", prefix=r"^")
        self.assertRegex(share.strip(), r"^value = -1\s*if = \{\s*limit = \{ country_rank >= rank_value:great_power \}")
        self.assertRegex(share, r"if = \{\s*limit = \{ has_global_variable = decol_gp_prestige_total \}\s*"
                                r"divide = global_var:decol_gp_prestige_total\s*\}\s*else = \{\s*divide = decol_gp_prestige_sum\s*\}")
        self.assertIn("max = 1", share)

    def test_the_line(self):
        stance = _gui_type(_raw(GUI), "te_ce_sec_stance")
        self.assertIn('text = "je_colonial_empire_stance_share_label"', stance)
        for key, test in (("je_colonial_empire_stance_share", "GreaterThanOrEqualTo_CFixedPoint"),
                          ("je_colonial_empire_stance_share_none", "LessThan_CFixedPoint")):
            with self.subTest(key=key):
                self.assertRegex(stance, rf"visible = \"\[{test}\( Country\.MakeScope\.ScriptValue\('decol_stance_disp_gp_share'\), "
                                         rf"'\(CFixedPoint\)0' \)\]\"\s*text = \"{key}\"")
        loc = _loc()
        self.assertIn("ScriptValue('decol_stance_disp_gp_share')|%0", loc["je_colonial_empire_stance_share"])
        # It reads the shown Country, never the player or the entry.
        for key in ("je_colonial_empire_stance_share", "je_colonial_empire_stance_share_tt_ours",
                    "je_colonial_empire_stance_share_tt_theirs", "je_colonial_empire_stance_share_none_tt"):
            self.assertNotIn("GetPlayer", loc[key])
            self.assertNotIn("JournalEntry", loc[key])


if __name__ == "__main__":
    unittest.main()
