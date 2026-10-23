"""The Grand Monument registry: every dedication, skin and IG alignment in one
table, pinned against every site that lists them by hand.

Design: docs/superpowers/archive/specs/2026-09-27-grand-monument-rework-design.md.
Adding a dedication touches its PM and the ratchet, the PM group, its kind and
fit trigger, the IG alignment triggers, its local and national modifiers and
their step mirrors, the ceremony option, the skin rules, its flavour event and
the loc. Nothing in the engine checks that they agree. DEDICATIONS is the
single list; each test checks one site against it, so a half-added dedication
fails here, naming the site.

Run: python3 -m unittest test_grand_monument_registry -v
"""
import re
import subprocess
import unittest
from collections import namedtuple
from pathlib import Path

ROOT = Path(__file__).resolve().parent

RULES = "common/game_rules/extra_game_rules.txt"
HERITAGE = "common/scripted_triggers/te_heritage_triggers.txt"
LAW_EVENTS = "events/extra_law_events.txt"
TRIGGERS = "common/scripted_triggers/monument_triggers.txt"
VALUES = "common/script_values/gm_values.txt"
MODIFIERS = "common/static_modifiers/gm_modifiers.txt"
CONCEPTS = "common/game_concepts/extra_concepts.txt"
PMS = "common/production_methods/grand_monument_pms.txt"
PMG = "common/production_method_groups/grand_monument_pmgs.txt"
BUILDING = "common/buildings/grand_monuments.txt"
EFFECTS = "common/scripted_effects/gm_effects.txt"
ON_ACTIONS = "common/on_actions/monument_events_on_actions.txt"
CIVIL_WAR_ON_ACTIONS = "common/on_actions/te_civil_war_on_actions.txt"
LADDER = "common/scripted_effects/te_construction_market_build_effects.txt"
EVENTS = "events/monument_events.txt"
JE = "common/journal_entries/je_grand_monuments.txt"
CULTURAL = "common/script_values/cultural_hegemony_script_values.txt"
CUSTOM_LOC = "common/customizable_localization/gm_custom_loc.txt"
MESSAGES = "common/messages/extra_messages.txt"
SGUIS = "common/scripted_guis/gm_sguis.txt"
WIDGET = "gui/journal_entry_widgets/grand_monuments_widget.gui"
DEBUG_EVENTS = "events/te_debug_monuments_events.txt"
MISC_LOC = "te_miscellaneous_l_english.yml"
SIG_TRIGGERS = "common/scripted_triggers/gm_signature_triggers.txt"
SIG_EFFECTS = "common/scripted_effects/gm_signature_effects.txt"
SIG_VALUES = "common/script_values/gm_signature_values.txt"
SIG_CUSTOM_LOC = "common/customizable_localization/gm_signature_custom_loc.txt"

Dedication = namedtuple(
    "Dedication",
    "key kind approve oppose local_field local_step national_field national_step event")

# approve / oppose are IG keys (without the ig_ prefix); "dynamic" is the
# Leader's: the ruler's own IG approves, the strongest IG outside the
# government opposes (spec §1).
DEDICATIONS = (
    Dedication("crown", "regime", "landowners", "intelligentsia",
               "state_loyalists_from_political_movements_mult", 0.10, None, None, 12),
    Dedication("republic", "regime", "intelligentsia", "landowners",
               "state_loyalists_from_political_movements_mult", 0.10, None, None, 13),
    Dedication("revolution", "regime", "trade_unions", "industrialists",
               "state_loyalists_from_political_movements_mult", 0.10, None, None, 14),
    Dedication("leader", "ruler", "dynamic", "dynamic",
               "state_loyalists_from_political_movements_mult", 0.10,
               "country_authority_add", 25, 15),
    Dedication("religious", "faith", "devout", None,
               "state_conversion_mult", 0.10,
               "interest_group_ig_devout_pop_attraction_mult", 0.05, 4),
    Dedication("civic", "timeless", "petty_bourgeoisie", None,
               "state_loyalists_from_political_movements_mult", 0.10, None, None, 3),
    Dedication("war_memorial", "timeless", "armed_forces", None,
               "state_conscription_rate_add", 0.01,
               "country_war_support_casualties_mult", -0.03, 5),
    Dedication("artistic", "timeless", "intelligentsia", None,
               "building_art_academy_throughput_add", 0.10,
               "interest_group_ig_intelligentsia_pop_attraction_mult", 0.05, 6),
    Dedication("naturalist", "timeless", "rural_folk", None,
               "state_pollution_generation_add", -5000, None, None, 7),
    Dedication("scientific", "timeless", "intelligentsia", None,
               "state_literacy_growth_add", 0.00025,
               "country_weekly_innovation_max_add", 3, 8),
    Dedication("industrial", "timeless", "industrialists", None,
               "state_migration_pull_mult", 0.10,
               "interest_group_ig_industrialists_pop_attraction_mult", 0.05, 9),
    Dedication("athletic", "timeless", "trade_unions", None,
               "state_turmoil_effects_mult", -0.10, None, None, 10),
)
BY_KEY = {d.key: d for d in DEDICATIONS}
BOUND = tuple(d.key for d in DEDICATIONS if d.kind != "timeless")
TECH_GATES = {"artistic": "romanticism", "naturalist": "romanticism", "scientific": "empiricism",
              "industrial": "marketing_research", "athletic": "television_broadcasting"}
# The gates still on the production method. The other three moved to the
# ceremony and first sight (phase 4 §6): the engine switches a building off a
# method whose technology its owner lacks, which would strip five landmarks of
# their dedications.
PM_TECH_GATES = {k: TECH_GATES[k] for k in ("industrial", "athletic")}
# Dedications that take heritage skins (spec §1.1; the War Memorial takes no
# faith skin, plan decision 4).
HERITAGE_SKINNED = ("crown", "republic", "revolution", "leader", "civic", "war_memorial")

IGS = ("armed_forces", "devout", "industrialists", "intelligentsia", "landowners",
       "petty_bourgeoisie", "rural_folk", "trade_unions")

# The language-reform revival partition (extra_law_events.25), in its order.
HERITAGES = ("latin", "hebrew", "sanskrit", "geez", "slavonic", "pali", "avestan", "arabic",
             "chinese", "greek", "irish", "coptic", "nahuatl", "norse", "gothic", "mayan",
             "prussian", "aramaic")
# Pali and Coptic are keyed on the state religion; their heritage skin is the
# matching faith skin.
HERITAGE_AS_FAITH = {"pali": "theravada", "coptic": "oriental_orthodox"}
HERITAGE_SKINS = tuple(h for h in HERITAGES if h not in HERITAGE_AS_FAITH)
FAITHS = ("catholic", "protestant", "orthodox", "oriental_orthodox", "sunni", "shiite", "ibadi",
          "jewish", "mahayana", "gelugpa", "theravada", "confucian", "hindu", "shinto", "sikh",
          "animist")
SKINS = ("generic",) + tuple(f"faith_{f}" for f in FAITHS) + tuple(f"heritage_{h}" for h in HERITAGE_SKINS)

# extra_law_events.25 option comment ("# Revive <name>") -> heritage.
REVIVAL_OPTION = {
    "Latin": "latin", "Hebrew": "hebrew", "Sanskrit": "sanskrit", "Ge'ez": "geez",
    "Old Church Slavonic": "slavonic", "Pali": "pali", "Avestan": "avestan",
    "Classical Arabic": "arabic", "Literary Chinese": "chinese", "Classical Greek": "greek",
    "Classical Irish (Gaeilge)": "irish", "Coptic": "coptic", "Classical Nahuatl": "nahuatl",
    "Old Norse": "norse", "Gothic": "gothic", "Classic Mayan": "mayan",
    "Old Prussian": "prussian", "Aramaic": "aramaic",
}


# ---- helpers -------------------------------------------------------------------------

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _match_brace(text, open_end):
    depth, i = 1, open_end
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[open_end:i - 1]


def block(text, name):
    """Body of `name = {` in text (comments stripped), or None. A top-level
    definition (at the start of a line) wins over a nested use, so a scripted
    effect's body is found even when a call with parameters
    (`gm_add_local = { KEY = crown }`) comes first in the file."""
    text = strip_comments(text)
    m = (re.search(r"(?m)^" + re.escape(name) + r"\s*=\s*\{", text)
         or re.search(r"(?<![\w.:$])" + re.escape(name) + r"\s*=\s*\{", text))
    return _match_brace(text, m.end()) if m else None


def raw_block_at(text, pattern):
    """Body of the block whose opening line matches `pattern` (a regex ending in
    `\\{`), comments kept, or None."""
    m = re.search(pattern, text)
    return _match_brace(text, m.end()) if m else None


def number(body, key):
    """The first `key = <number>` in body, as a float, or None."""
    m = re.search(r"(?<![\w.:])" + re.escape(key) + r"\s*=\s*(-?\d+(?:\.\d+)?)", body or "")
    return float(m.group(1)) if m else None


def squash(text):
    return " ".join((text or "").split())


def top_level_blocks(text):
    """(name, body) for every top-level `name = {` in text (comments stripped)."""
    text = strip_comments(text)
    for m in re.finditer(r"(?m)^([\w:.]+)\s*=\s*\{", text):
        yield m.group(1), _match_brace(text, m.end())


_LOC = None


def _load_loc():
    global _LOC
    if _LOC is None:
        _LOC = {}
        for path in sorted((ROOT / "localization/english").glob("*.yml")):
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                m = re.match(r'\s*([\w.$\'-]+):\d*\s+"(.*)"\s*$', line)
                if m:
                    _LOC[m.group(1)] = (m.group(2), path.name)
    return _LOC


class _Loc(dict):
    """The loc table; a short repr, so a failed assertIn doesn't print 100k keys."""
    def __repr__(self):
        return f"<{len(self)} loc keys>"


def loc():
    return _Loc({k: v[0] for k, v in _load_loc().items()})


def loc_file_of(key):
    entry = _load_loc().get(key)
    return entry[1] if entry else None


# ---- Task 1: loc routing, shared heritage triggers, the game rule --------------------

class RoutingTests(unittest.TestCase):
    def test_gm_keys_route_to_miscellaneous(self):
        from organize_loc import categorize_key
        for key in ("gm_local_crown", "gm_local_crown_desc", "gm_national_prestige",
                    "gm_skin_faith_jewish", "gm_row_title", "gm_je_line_legitimacy",
                    "gm_step_local_scientific_religion_event_add"):
            self.assertEqual(categorize_key(key, set()), "MISCELLANEOUS", key)

    def test_every_gm_key_lives_in_miscellaneous(self):
        for key in loc():
            if key.startswith("gm_"):
                self.assertEqual(loc_file_of(key), MISC_LOC, key)


class HeritageTests(unittest.TestCase):
    def test_eighteen_triggers_and_any(self):
        text = read(HERITAGE)
        for h in HERITAGES:
            self.assertIsNotNone(block(text, f"te_heritage_{h}"), h)
        any_body = squash(block(text, "te_heritage_any"))
        for h in HERITAGES:
            self.assertIn(f"te_heritage_{h} = yes", any_body)

    def test_heritage_reads_own_identity_only(self):
        body = strip_comments(read(HERITAGE))
        self.assertNotRegex(body, r"\bscope:|\bvar:|\bprev\b", "reads only the country's own identity")
        self.assertNotIn("any_scope_pop", body)

    def test_revival_options_call_the_shared_triggers(self):
        text = read(LAW_EVENTS)
        event = raw_block_at(text, r"(?m)^extra_law_events\.25\s*=\s*\{")
        self.assertIsNotNone(event)
        for name, h in REVIVAL_OPTION.items():
            option = raw_block_at(event, r"option\s*=\s*\{\s*# Revive " + re.escape(name) + r"\s*\n")
            self.assertIsNotNone(option, name)
            trigger = squash(block(option, "trigger"))
            self.assertEqual(trigger, f"te_heritage_{h} = yes", name)
        calc = squash(block(event, "calc_true_if"))
        for h in HERITAGES:
            self.assertIn(f"te_heritage_{h} = yes", calc)
        self.assertNotIn("has_discrimination_trait", calc)
        generic = raw_block_at(event, r"option\s*=\s*\{\s*# Revive a classical or historical language")
        self.assertEqual(squash(block(generic, "trigger")), "te_heritage_any = no")


class RuleTests(unittest.TestCase):
    def test_rule_two_settings_default_enabled(self):
        body = block(read(RULES), "grand_monuments_rule")
        self.assertIsNotNone(body)
        self.assertIn("default = grand_monuments_enabled", squash(body))
        for setting in ("grand_monuments_enabled", "grand_monuments_disabled"):
            self.assertIn(f"flag = {setting}", squash(block(body, setting)))

    def test_rule_trigger_tests_the_disabled_setting(self):
        self.assertEqual(squash(block(read(TRIGGERS), "gm_system_enabled")),
                         "NOT = { has_game_rule = grand_monuments_disabled }")

    def test_rule_is_localized(self):
        L = loc()
        self.assertIn("rule_grand_monuments_rule", L)
        for setting in ("grand_monuments_enabled", "grand_monuments_disabled"):
            self.assertIn(f"setting_{setting}", L)
            self.assertIn(f"setting_{setting}_desc", L)


# ---- Task 2: the curve, the step values, the modifiers -------------------------------

NATIONAL = ("leader", "religious", "war_memorial", "artistic", "scientific", "industrial")


def curve_terms(f):
    """(start, size) of the eight steps of a curve with first step f."""
    return [(f * (2 ** k - 1), f * 2 ** k) for k in range(8)]


def lin_curve_terms(f, n=30):
    """(start, size) of the first n steps of the 1/n curve with first step f:
    step k takes k * f (owner, 2026-10-19)."""
    return [(f * k * (k - 1) // 2, f * k) for k in range(1, n + 1)]


# The local effects that stop short of the 1/n curve's end (owner, 2026-10-19):
# dedication -> (its CAP script value, the steps it stops at).
LOCAL_CAPS = {"war_memorial": ("gm_local_cap_war_memorial", 10),
              "athletic": ("gm_local_cap_athletic", 5)}


class CurveTests(unittest.TestCase):
    def _terms(self, name):
        body = squash(block(read(VALUES), name))
        self.assertIsNotNone(body, name)
        return re.findall(r"add = \{ value = var:gm_curve_in (?:subtract = (\d+) )?divide = (\d+) "
                          r"min = 0 max = 1 \}", body)

    def test_steps_double(self):
        for f in (5, 10):
            terms = [(int(s or 0), int(d)) for s, d in self._terms(f"gm_curve_steps_f{f}")]
            self.assertEqual(terms, curve_terms(f), f)

    def test_lin_steps_grow_by_one_first_step(self):
        """The 1/n curve: thirty steps, step k taking k first steps."""
        terms = [(int(s or 0), int(d)) for s, d in self._terms("gm_curve_steps_lin_f5")]
        self.assertEqual(terms, lin_curve_terms(5))
        self.assertRegex(strip_comments(read(VALUES)), r"(?m)^gm_curve_lin_steps = 30\s*$")
        # Each step is worth 1/k of the first a point of grandeur.
        for k, (_, size) in enumerate(lin_curve_terms(5), start=1):
            self.assertEqual(size, 5 * k)

    def test_local_caps(self):
        values = strip_comments(read(VALUES))
        for key, (name, cap) in LOCAL_CAPS.items():
            self.assertRegex(values, r"(?m)^" + name + r" = " + str(cap) + r"\s*$", key)
            self.assertEqual(squash(block(read(VALUES), f"gm_local_max_{key}")),
                             f"value = {name} multiply = gm_step_local_{key}", key)

    def test_next_thresholds(self):
        for f in (5, 10):
            body = squash(block(read(VALUES), f"gm_curve_next_f{f}"))
            ends = [f * (2 ** n - 1) for n in range(1, 9)]
            self.assertTrue(body.startswith(f"value = {ends[-1]} "), f)
            for end in ends[:-1]:
                self.assertIn(f"if = {{ limit = {{ var:gm_curve_in < {end} }} value = {end} }}", body)
            # Each `if` (not else_if) overwrites the last: the override semantics
            # depend on the thresholds appearing in strictly descending order in
            # the file, so a looser match written later cannot clobber a tighter
            # one written earlier (deferred item, 2026-09-27).
            descending = sorted(ends[:-1], reverse=True)
            positions = [body.find(f"var:gm_curve_in < {end} }} value = {end}") for end in descending]
            self.assertNotIn(-1, positions, f)
            self.assertEqual(positions, sorted(positions),
                              f"f={f}: thresholds must appear in strictly descending order")


class ModifierTests(unittest.TestCase):
    def _mod(self, name):
        body = block(read(MODIFIERS), name)
        self.assertIsNotNone(body, name)
        return body

    def assert_pair(self, modifier, field, step_name, expected):
        self.assertAlmostEqual(number(self._mod(modifier), field), expected, msg=modifier)
        mirror = re.search(r"(?m)^" + step_name + r"\s*=\s*(-?\d+(?:\.\d+)?)\s*$",
                           strip_comments(read(VALUES)))
        self.assertIsNotNone(mirror, step_name)
        self.assertAlmostEqual(float(mirror.group(1)), expected, msg=step_name)

    def test_national_pairs(self):
        self.assert_pair("gm_national_prestige", "country_prestige_add", "gm_step_prestige", 25)
        self.assert_pair("gm_national_legitimacy", "country_legitimacy_base_add", "gm_step_legitimacy", 2)
        self.assert_pair("gm_national_teardown", "country_legitimacy_base_add", "gm_step_teardown", 3)
        self.assert_pair("gm_national_vanity", "country_legitimacy_base_add", "gm_step_vanity", -1)
        for key in NATIONAL:
            d = BY_KEY[key]
            self.assert_pair(f"gm_national_{key}", d.national_field, f"gm_step_national_{key}",
                             d.national_step)
        self.assertEqual({d.key for d in DEDICATIONS if d.national_field}, set(NATIONAL))

    def test_ig_pairs(self):
        for ig in IGS:
            self.assert_pair(f"gm_ig_approval_{ig}", f"interest_group_ig_{ig}_approval_add",
                             "gm_step_ig", 1)

    def test_local_pairs(self):
        self.assert_pair("gm_local_tourism", "goods_output_tourism_mult", "gm_step_tourism", 0.10)
        for d in DEDICATIONS:
            self.assert_pair(f"gm_local_{d.key}", d.local_field, f"gm_step_local_{d.key}", d.local_step)

    def test_pilgrim_hostels_is_output(self):
        # Tourism heritage spec 2026-10-23 § 5.1: monument tourism is output, as base appeal is.
        body = block(read(MODIFIERS), "gm_evt_pilgrim_hostels")
        self.assertAlmostEqual(number(body, "goods_output_tourism_mult"), 0.05)
        self.assertNotIn("throughput", body)

    def test_no_monument_loc_promises_throughput(self):
        L = loc()
        keys = [k for k in L if k.startswith(("gm_state_", "gm_sig_", "gm_policy_")) or k == "monument_events.2.common_tt"]
        for k in keys:
            self.assertNotIn("building_tourism_industry_throughput_add", L[k], k)
            self.assertNotIn("Tourism Industry throughput", L[k], k)

    def test_culture_step(self):
        self.assertRegex(strip_comments(read(VALUES)), r"(?m)^gm_step_culture = 1\s*$")

    def test_each_modifier_has_one_field_and_an_icon(self):
        for name, body in top_level_blocks(read(MODIFIERS)):
            if not name.startswith(("gm_national_", "gm_ig_approval_", "gm_local_")):
                continue
            # a mortality line's Causes of Death tag is a label beside it, not a field of its own (owner, 2026-10-22)
            fields = [k for k in re.findall(r"(?m)^\s*(\w+)\s*=", body)
                      if k != "icon" and not k.startswith("state_death_cause_")]
            self.assertEqual(len(fields), 1, name)
            self.assertIn("modifier_statue_", body, name)

    def test_modifiers_are_localized(self):
        L = loc()
        for name, _ in top_level_blocks(read(MODIFIERS)):
            self.assertIn(name, L, name)
            self.assertIn(f"{name}_desc", L, name)

    def test_concept(self):
        self.assertIsNotNone(block(read(CONCEPTS), "concept_grandeur"))
        L = loc()
        self.assertIn("concept_grandeur", L)
        self.assertIn("concept_grandeur_desc", L)


# ---- Task 3: staff-only dedications, the building ------------------------------------

class PMTests(unittest.TestCase):
    def test_group_lists_every_dedication(self):
        group = squash(block(read(PMG), "pmg_monument_dedication"))
        for d in DEDICATIONS:
            self.assertIn(f"pm_monument_{d.key}", group)
        self.assertIn("pm_monument_undedicated", group)

    def test_ratchet(self):
        text = read(PMS)
        undedicated = squash(block(text, "pm_monument_undedicated"))
        self.assertIn("is_default = yes", undedicated)
        # Locked behind itself again: activate_production_method passes the
        # lock (te_debug_monuments probe, 2026-10-08), so script can still
        # replace the engine's copy of a sibling's dedication (CopiedDedicationTests).
        self.assertIn("unlocking_production_methods = { pm_monument_undedicated }", undedicated)
        for d in DEDICATIONS:
            body = squash(block(text, f"pm_monument_{d.key}"))
            self.assertIn(f"unlocking_production_methods = {{ pm_monument_undedicated pm_monument_{d.key} }}",
                          body, d.key)
            self.assertIn("is_hidden_when_unavailable = yes", body, d.key)
            self.assertNotIn("replacement_if_valid", body, d.key)

    def test_staff_only(self):
        text = read(PMS)
        for name in ["pm_monument_undedicated"] + [f"pm_monument_{d.key}" for d in DEDICATIONS]:
            body = squash(block(text, name))
            for forbidden in ("country_modifiers", "state_modifiers", "goods_output", "goods_input",
                              "level_scaled", "workforce_scaled"):
                self.assertNotIn(forbidden, body, f"{name}: {forbidden}")
            self.assertIn("unscaled = { building_employment_laborers_add = 200 "
                          "building_employment_clerks_add = 50 }", body, name)

    def test_tech_gates(self):
        text = read(PMS)
        for d in DEDICATIONS:
            body = squash(block(text, f"pm_monument_{d.key}"))
            if d.key in PM_TECH_GATES:
                self.assertIn(f"unlocking_technologies = {{ {PM_TECH_GATES[d.key]} }}", body, d.key)
            else:
                self.assertNotIn("unlocking_technologies", body, d.key)

    def test_pms_localized(self):
        L = loc()
        for d in DEDICATIONS:
            self.assertIn(f"pm_monument_{d.key}", L)
            self.assertIn(f"pm_monument_{d.key}_desc", L)
        self.assertEqual(L["pm_monument_civic"], "To the Nation")


class BuildingTests(unittest.TestCase):
    def test_possible_reads_the_rule(self):
        possible = squash(block(read(BUILDING), "possible"))
        self.assertIn("text = gm_possible_rule_tt gm_system_enabled = yes", possible)
        self.assertIn("gm_possible_rule_tt", loc())

    def test_ai_avoids_hard_times_and_war(self):
        ai = squash(block(read(SITE_BUILDING), "ai_value"))
        # owner ?= : the AI can ask while a state's owner is briefly invalid.
        self.assertIn("owner ?= { gm_country_hard_times = yes } } add = -100", ai)
        self.assertIn("owner ?= { is_at_war = yes } } add = -100", ai)
        self.assertIn("owner ?= { government_legitimacy < 40 } } add = 25", ai)

    def test_hard_times(self):
        body = squash(block(read(TRIGGERS), "gm_country_hard_times"))
        self.assertIn("in_default = yes", body)
        self.assertIn("has_famine = yes", body)
        self.assertIn("AND = { has_variable = finance_cycle_value banking_cycle_is_recession = yes }", body)

    def test_regime_gates(self):
        text = read(TRIGGERS)
        revolutionary = squash(block(text, "gm_government_is_revolutionary"))
        self.assertIn("law_type:law_single_party_state", revolutionary)
        self.assertIn("law_type:law_council_republic", revolutionary)
        leader = squash(block(text, "gm_can_raise_leader_monument"))
        self.assertIn("law_type:law_autocracy", leader)
        self.assertIn("law_type:law_single_party_state", leader)
        self.assertIn("monument_government_is_crowned = no", leader)


# ---- Task 4: kinds, fit, status, records, the local pulse ----------------------------

REGIME_GATE = {"crown": "monument_government_is_crowned", "republic": "monument_government_is_republican",
               "revolution": "gm_government_is_revolutionary"}


class FitTests(unittest.TestCase):
    def setUp(self):
        self.t = read(TRIGGERS)

    def test_has_pm_reads_the_building(self):
        self.assertEqual(squash(block(self.t, "gm_state_has_pm")),
                         "b:building_grand_monument ?= { has_active_production_method = $PM$ }")

    def test_kinds_match_the_table(self):
        kind_trigger = {"regime": "gm_state_kind_regime", "ruler": "gm_state_kind_ruler",
                        "faith": "gm_state_kind_faith"}
        for d in DEDICATIONS:
            for kind, trig in kind_trigger.items():
                present = f"PM = pm_monument_{d.key} }}" in squash(block(self.t, trig))
                self.assertEqual(present, d.kind == kind, f"{d.key} in {trig}")
        bound = squash(block(self.t, "gm_state_is_bound"))
        for trig in kind_trigger.values():
            self.assertIn(f"{trig} = yes", bound)

    def test_bound_messages_fit_only_for_the_raiser(self):
        body = squash(block(self.t, "gm_state_message_fits"))
        self.assertTrue(body.startswith("OR = { gm_state_is_bound = no AND = { gm_state_raised_by_owner = yes OR = {"))
        for key, gate in REGIME_GATE.items():
            self.assertIn(f"AND = {{ gm_state_has_pm = {{ PM = pm_monument_{key} }} owner = {{ {gate} = yes }} }}", body)
        self.assertIn("AND = { gm_state_kind_ruler = yes gm_state_leader_fits = yes }", body)
        self.assertIn("AND = { gm_state_kind_faith = yes gm_state_shrine_fits = yes }", body)

    def test_raiser_honoree_faith_are_guarded(self):
        raiser = squash(block(self.t, "gm_state_raised_by_owner"))
        self.assertIn("has_variable = gm_raised_by var:gm_raised_by ?=", raiser)
        leader = squash(block(self.t, "gm_state_leader_fits"))
        self.assertIn("has_variable = gm_honoree var:gm_honoree ?=", leader)
        self.assertIn("ruler ?= { this = scope:gm_tmp_honoree }", leader)
        shrine = squash(block(self.t, "gm_state_shrine_fits"))
        self.assertIn("has_variable = gm_faith", shrine)
        self.assertIn("NOT = { has_law_or_variant = law_type:law_state_atheism }", shrine)
        self.assertIn("religion = scope:gm_tmp_faith", shrine)

    def test_statuses(self):
        fits = squash(block(self.t, "gm_state_status_fits"))
        self.assertEqual(fits, "gm_state_is_dedicated = yes gm_state_is_contested = no "
                               "gm_state_is_heritage = no gm_state_message_fits = yes")
        standing = squash(block(self.t, "gm_state_counts_standing"))
        self.assertEqual(standing, "has_building = building_grand_monument gm_state_is_contested = no")

    def test_heritage_skinned(self):
        body = squash(block(self.t, "gm_state_takes_heritage_skin"))
        for key in HERITAGE_SKINNED:
            d = BY_KEY[key]
            if d.kind == "regime":
                self.assertIn("gm_state_kind_regime = yes", body)
            elif d.kind == "ruler":
                self.assertIn("gm_state_kind_ruler = yes", body)
            else:
                self.assertIn(f"PM = pm_monument_{key} }}", body)
        self.assertNotIn("gm_state_kind_faith", body)


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.e = read(EFFECTS)

    def test_first_sight(self):
        body = squash(block(self.e, "gm_state_first_sight"))
        self.assertIn("gm_state_is_dedicated = yes NOT = { has_variable = gm_seen }", body)
        self.assertIn("set_variable = gm_seen", body)
        self.assertIn("limit = { gm_state_is_bound = yes } set_variable = { name = gm_raised_by value = owner }", body)
        # Recording the honoree is gated on the commission (gm_can_raise_leader_monument),
        # not just on being a ruler monument: a Leader picked in the building panel
        # under a government that cannot commission one must record no honoree, so it
        # reads "does not fit" and is contested (I2). gm_state_leader_fits stays ungated.
        self.assertIn("limit = { gm_state_kind_ruler = yes owner = { gm_can_raise_leader_monument = yes } } "
                      "gm_state_record_honoree = yes", body)
        self.assertNotIn("owner = { gm_can_raise_leader_monument = yes }",
                          squash(block(read(TRIGGERS), "gm_state_leader_fits")))
        self.assertIn("limit = { gm_state_kind_faith = yes } gm_state_record_faith = yes", body)
        self.assertIn("gm_state_set_default_skin = yes", body)
        honoree = squash(block(self.e, "gm_state_record_honoree"))
        self.assertIn("ruler = { save_scope_as = gm_tmp_ruler }", honoree)
        self.assertIn("set_variable = { name = gm_honoree value = scope:gm_tmp_ruler }", honoree)
        self.assertIn("gm_ig_to_flag_on_owner = { VAR = gm_tmp_ig_flag }", honoree)
        self.assertIn("set_variable = { name = gm_honoree_ig value = owner.var:gm_tmp_ig_flag }", honoree)
        # Minor 8: gm_tmp_ig_flag is the only temp variable this file leaves on
        # the owner; every other gm_tmp_* is a saved scope, not a variable.
        self.assertIn("set_variable = { name = gm_honoree_ig value = owner.var:gm_tmp_ig_flag } "
                      "owner = { remove_variable = gm_tmp_ig_flag }", honoree)
        faith = squash(block(self.e, "gm_state_record_faith"))
        self.assertIn("religion = { save_scope_as = gm_tmp_faith_scope }", faith)
        self.assertIn("set_variable = { name = gm_faith value = scope:gm_tmp_faith_scope }", faith)

    def test_ig_flags_cover_every_ig(self):
        body = squash(block(self.e, "gm_ig_to_flag_on_owner"))
        for ig in IGS:
            self.assertIn(f"is_interest_group_type = ig_{ig} }} owner = {{ set_variable = "
                          f"{{ name = $VAR$ value = flag:{ig} }} }}", body)

    def test_default_skin_covers_every_faith_and_heritage(self):
        body = squash(block(self.e, "gm_state_set_default_skin"))
        self.assertTrue(body.startswith("set_variable = { name = gm_skin value = flag:generic }"))
        self.assertIn("gm_state_kind_faith = yes } gm_state_default_faith_skin = yes", body)
        self.assertIn("gm_state_takes_heritage_skin = yes } gm_state_default_heritage_skin = yes", body)
        faith = squash(block(self.e, "gm_state_default_faith_skin"))
        for f in FAITHS:
            self.assertIn(f"gm_state_try_faith_skin = {{ R = {f} }}", faith)
        heritage = squash(block(self.e, "gm_state_default_heritage_skin"))
        order = []
        for m in re.finditer(r"gm_state_try_heritage(?:_as_faith)?_skin = \{ H = (\w+)(?: R = (\w+))? \}", heritage):
            order.append(m.group(1))
            if m.group(1) in HERITAGE_AS_FAITH:
                self.assertEqual(m.group(2), HERITAGE_AS_FAITH[m.group(1)])
        # I3: reverse order (the partition's first wins), EXCEPT Hebrew, which
        # is a group-level (Semitic) match less specific than the single-language
        # Arabic, Ge'ez and Aramaic skins, so it is applied first and everything
        # else overrides it -- then re-applied once more, last, but only for a
        # Jewish state religion.
        rest = [h for h in reversed(HERITAGES) if h != "hebrew"]
        self.assertEqual(order, ["hebrew"] + rest + ["hebrew"],
                          "hebrew first (loses to everything), then re-applied last for a Jewish state religion")
        self.assertLess(order.index("hebrew"), order.index("arabic"))
        self.assertLess(order.index("hebrew"), order.index("geez"))
        self.assertLess(order.index("hebrew"), order.index("aramaic"))
        self.assertIn("owner = { country_has_state_religion = rel:jewish } } "
                      "gm_state_try_heritage_skin = { H = hebrew }", heritage)
        self.assertTrue(heritage.endswith("gm_state_try_heritage_skin = { H = hebrew } }"),
                         "hebrew's Jewish re-apply is the last line")

    def test_skin_helpers(self):
        self.assertIn("owner = { religion = rel:$R$ } } set_variable = { name = gm_skin value = flag:faith_$R$ }",
                      squash(block(self.e, "gm_state_try_faith_skin")))
        self.assertIn("owner = { te_heritage_$H$ = yes } } set_variable = { name = gm_skin value = flag:heritage_$H$ }",
                      squash(block(self.e, "gm_state_try_heritage_skin")))
        self.assertIn("owner = { te_heritage_$H$ = yes } } set_variable = { name = gm_skin value = flag:faith_$R$ }",
                      squash(block(self.e, "gm_state_try_heritage_as_faith_skin")))


class LocalPulseTests(unittest.TestCase):
    def setUp(self):
        self.e = read(EFFECTS)

    def test_removes_every_local_modifier(self):
        body = squash(block(self.e, "gm_remove_local_modifiers"))
        self.assertIn("remove_modifier = gm_local_tourism", body)
        for d in DEDICATIONS:
            self.assertIn(f"remove_modifier = gm_local_{d.key}", body)

    def test_pulse_applies_the_curve(self):
        body = squash(block(self.e, "gm_state_monthly"))
        self.assertTrue(body.startswith("gm_state_count_site_levels = yes gm_remove_local_modifiers = yes"))
        self.assertIn("set_variable = { name = gm_curve_in value = gm_state_grandeur }", body)
        # The monument policy (v2 §5) scales the steps: tourism and the local
        # effect separately (each dedication's, SecondaryFitTests).
        self.assertIn("set_variable = { name = gm_local_tourism_steps value = { value = gm_curve_steps_lin_f5 "
                      "multiply = gm_policy_factor_tourism } }", body)
        self.assertIn("add_modifier = { name = gm_local_tourism multiplier = var:gm_local_tourism_steps }", body)
        # Upkeep by the records (UpkeepTests).
        self.assertIn("add_modifier = { name = gm_upkeep multiplier = root.var:gm_upkeep_mult }", body)
        for d in DEDICATIONS:
            cap = LOCAL_CAPS.get(d.key, ("gm_curve_lin_steps",))[0]
            self.assertIn(f"gm_state_local_steps_one = {{ KEY = {d.key} CAP = {cap} }}", body)

    def test_backing_variable_is_never_removed(self):
        self.assertNotRegex(strip_comments(self.e), r"remove_variable = gm_local_steps")
        self.assertIn("set_variable = { name = gm_local_steps value = 0 }", squash(block(self.e, "gm_clear_state")))

    def test_wired_to_the_state_pulse(self):
        oa = read(ON_ACTIONS)
        self.assertIn("gm_state_on_action", squash(block(oa, "on_monthly_pulse_state")))
        body = squash(block(oa, "gm_state_on_action"))
        self.assertIn("trigger = { gm_system_enabled = yes }", body)
        self.assertIn("gm_state_monthly = yes", body)

    def test_state_values(self):
        v = read(VALUES)
        # The building's level is gm_state_level; grandeur is levels + age
        # (AgeTests pins gm_state_grandeur).
        self.assertIn("value = b:building_grand_monument.level", squash(block(v, "gm_state_level")))
        code = squash(block(v, "gm_status_code"))
        for n in (1, 2, 3, 4):
            self.assertIn(f"value = {n} }}", code)


class StateCardTests(unittest.TestCase):
    """The state view's Grand Monument card (te_state_gm_card) shows each
    dedication's local effect: its value, its name and its format."""

    def test_local_value_takes_each_dedications_step(self):
        body = squash(block(read(VALUES), "gm_state_disp_local"))
        self.assertIn("value = var:gm_local_steps", body)
        for d in DEDICATIONS:
            self.assertIn(f"limit = {{ gm_state_has_pm = {{ PM = pm_monument_{d.key} }} }} "
                          f"multiply = gm_step_local_{d.key} }}", body, d.key)

    def test_label_and_value_for_each_dedication(self):
        """One branch per dedication in each family; dedications with the same
        local modifier share a label and a format, and different modifiers
        never share a label."""
        custom, table = read(CUSTOM_LOC), loc()
        label_of_field = {}
        for family in ("gm_local_effect_label", "gm_local_effect_value"):
            body = squash(block(custom, family))
            self.assertIsNotNone(body, family)
            by_field = {}
            for d in DEDICATIONS:
                m = re.search(rf"trigger = {{ gm_state_has_pm = {{ PM = pm_monument_{d.key} }} }} "
                              rf"localization_key = (\w+)", body)
                self.assertIsNotNone(m, (family, d.key))
                self.assertIn(m.group(1), table, (family, d.key))
                self.assertEqual(by_field.setdefault(d.local_field, m.group(1)), m.group(1), (family, d.key))
            if family == "gm_local_effect_label":
                label_of_field = by_field
        self.assertEqual(len(set(label_of_field.values())), len(label_of_field))

    def test_value_formats_follow_the_sign_and_size(self):
        """A share prints as a percent, the pollution step as a number, and
        a negative step has no "+" in front of it."""
        custom, table = squash(block(read(CUSTOM_LOC), "gm_local_effect_value")), loc()
        for d in DEDICATIONS:
            key = re.search(rf"PM = pm_monument_{d.key} }} }} localization_key = (\w+)", custom).group(1)
            text = table[key]
            self.assertIn("ScriptValue('gm_state_disp_local')", text, d.key)
            self.assertEqual("#G +[" in text, d.local_step > 0, d.key)
            self.assertEqual("|D]" in text, abs(d.local_step) >= 1, d.key)


# ---- Task 5: the national refresh, IG alignment, ledgers, the JE ---------------------

class NationalTests(unittest.TestCase):
    def setUp(self):
        self.t, self.e, self.v = read(TRIGGERS), read(EFFECTS), read(VALUES)

    def test_ig_alignment_matches_the_table(self):
        for ig in IGS:
            approve = squash(block(self.t, f"gm_state_approved_by_{ig}"))
            oppose = squash(block(self.t, f"gm_state_opposed_by_{ig}"))
            for d in DEDICATIONS:
                self.assertEqual(f"PM = pm_monument_{d.key} }}" in approve, d.approve == ig, f"{ig} approves {d.key}")
                self.assertEqual(f"PM = pm_monument_{d.key} }}" in oppose, d.oppose == ig, f"{ig} opposes {d.key}")
            self.assertIn(f"gm_state_leader_ig_is = {{ IG = {ig} }}", approve)
            self.assertIn(f"gm_state_leader_opposed_by = {{ IG = {ig} }}", oppose)

    def test_leader_pair_is_dynamic(self):
        self.assertIn("ruler ?= { interest_group ?= { is_interest_group_type = ig_$IG$ } }",
                      squash(block(self.t, "gm_state_leader_ig_is")))
        self.assertIn("var:gm_opposition_ig = flag:$IG$", squash(block(self.t, "gm_state_leader_opposed_by")))
        opp = squash(block(self.e, "gm_set_opposition_ig"))
        self.assertIn("limit = { is_in_government = no } order_by = ig_clout position = 0", opp)
        self.assertIn("gm_ig_to_flag_on_owner = { VAR = gm_opposition_ig }", opp)

    def test_sums_follow_the_status_table(self):
        self.assertIn("limit = { gm_state_counts_standing = yes } add = gm_state_primary_grandeur",
                      squash(block(self.v, "gm_sum_standing")))
        self.assertIn("gm_state_status_fits = yes OR = { gm_state_kind_regime = yes gm_state_kind_ruler = yes }",
                      squash(block(self.v, "gm_sum_regime")))
        for key in NATIONAL:
            self.assertIn(f"gm_state_status_fits = yes gm_state_has_pm = {{ PM = pm_monument_{key} }} "
                          "} add = gm_state_primary_grandeur", squash(block(self.v, f"gm_sum_{key}")))

    def test_totals_use_the_right_curves(self):
        body = squash(block(self.e, "gm_compute_totals"))
        # Prestige and cultural pull on the 1/n curve with no end (owner,
        # 2026-10-19); every other national total keeps the doubling curve.
        self.assertIn("gm_set_steps_lin_open = { IN = gm_g_standing OUT = gm_s_standing NEXT = gm_n_standing "
                      "WIDTH = gm_w_standing F = 5 }", body)
        self.assertIn("gm_set_steps_lin_open = { IN = gm_g_standing OUT = gm_s_culture NEXT = gm_n_culture "
                      "WIDTH = gm_w_culture F = 10 }", body)
        self.assertEqual(body.count("gm_set_steps_lin_open"), 2)
        self.assertIn("gm_set_steps = { IN = gm_g_regime OUT = gm_s_regime NEXT = gm_n_regime F = 10 }", body)
        self.assertIn("gm_set_steps = { IN = gm_teardown_ledger OUT = gm_s_teardown NEXT = gm_n_teardown F = 5 }", body)
        # The monument policy (v2 §5) scales the steps after the curve, so the
        # effect itself moves by the factor (halving grandeur before the curve
        # would take off about one step, not half).
        for g in ("standing", "regime", "leader"):
            self.assertIn(f"set_variable = {{ name = gm_g_{g} value = gm_sum_{g} }}", body)
        for steps, factor in (("standing", "standing"), ("culture", "standing"), ("regime", "regime"),
                              ("leader", "regime")):
            call = f"gm_policy_scale_steps = {{ S = {steps} FACTOR = gm_policy_factor_{factor} }}"
            self.assertIn(call, body)
            self.assertGreater(body.find(call), body.find(f"OUT = gm_s_{steps} "), "after the curve")
        for key in NATIONAL:
            self.assertIn(f"set_variable = {{ name = gm_g_{key} value = gm_sum_{key} }}", body)
            self.assertIn(f"gm_set_steps = {{ IN = gm_g_{key} OUT = gm_s_{key} NEXT = gm_n_{key} F = 5 }}", body)
        for ig in IGS:
            self.assertIn(f"gm_compute_ig = {{ IG = {ig} }}", body)
        steps = squash(block(self.e, "gm_set_steps"))
        self.assertIn("value = gm_curve_steps_f$F$", steps)
        self.assertIn("value = gm_curve_next_f$F$", steps)

    def test_ig_net(self):
        body = squash(block(self.e, "gm_compute_ig"))
        self.assertTrue(body.startswith("set_variable = { name = gm_ig_net_$IG$ value = var:gm_ig_ledger_$IG$ }"))
        self.assertIn("gm_state_approved_by_$IG$ = yes } owner = { change_variable = { name = gm_ig_net_$IG$ add = prev.var:gm_grandeur } }", body)
        self.assertIn("gm_state_opposed_by_$IG$ = yes } owner = { change_variable = { name = gm_ig_net_$IG$ subtract = prev.var:gm_grandeur } }", body)
        self.assertIn("gm_state_is_contested = yes has_variable = gm_base_ig var:gm_base_ig = flag:$IG$", body)
        self.assertIn("multiply = -1", body)

    def test_national_modifiers_on_the_je_from_root(self):
        body = squash(block(self.e, "gm_apply_national_modifiers"))
        self.assertTrue(body.startswith("je:je_grand_monuments ?= { gm_remove_national_modifiers = yes"))
        pairs = [("gm_national_prestige", "gm_s_standing"), ("gm_national_legitimacy", "gm_s_regime"),
                 ("gm_national_teardown", "gm_s_teardown"), ("gm_national_vanity", "gm_vanity_ledger")]
        pairs += [(f"gm_national_{k}", f"gm_s_{k}") for k in NATIONAL]
        for name, var in pairs:
            self.assertIn(f"gm_add_national = {{ NAME = {name} VAR = {var} }}", body)
        for ig in IGS:
            self.assertIn(f"gm_add_national_signed = {{ NAME = gm_ig_approval_{ig} VAR = gm_s_ig_{ig} }}", body)
        removed = squash(block(self.e, "gm_remove_national_modifiers"))
        for name, _ in top_level_blocks(read(MODIFIERS)):
            if name.startswith(("gm_national_", "gm_ig_approval_")):
                self.assertIn(f"remove_modifier = {name}", removed)
        self.assertIn("multiplier = root.var:$VAR$", squash(block(self.e, "gm_add_national")))
        self.assertIn("multiplier = root.var:$VAR$", squash(block(self.e, "gm_add_national_signed")))

    def test_refresh_order(self):
        body = squash(block(self.e, "gm_country_refresh"))
        order = ["gm_init_ledgers = yes", "add_journal_entry = { type = je_grand_monuments }",
                 "clear_variable_list = gm_states",
                 "set_variable = { name = gm_grandeur value = gm_state_primary_grandeur }",
                 "gm_state_first_sight = yes", "add_to_variable_list = { name = gm_states target = prev }",
                 "gm_set_opposition_ig = yes", "gm_check_contests = yes", "gm_compute_totals = yes",
                 "gm_apply_national_modifiers = yes", "gm_notify_new_contests = yes"]
        positions = [body.find(s) for s in order]
        self.assertNotIn(-1, positions, dict(zip(order, positions)))
        self.assertEqual(positions, sorted(positions))

    def test_ledgers(self):
        init = squash(block(self.e, "gm_init_ledgers"))
        decay = squash(block(self.e, "gm_decay_ledgers"))
        idle = squash(block(self.t, "gm_ledgers_idle"))
        for var in ["gm_teardown_ledger", "gm_vanity_ledger"] + [f"gm_ig_ledger_{ig}" for ig in IGS]:
            self.assertIn(f"gm_init_ledger = {{ VAR = {var} }}", init)
            self.assertIn(f"gm_ledger_idle = {{ VAR = {var} }}", idle)
        self.assertIn("gm_decay = { VAR = gm_teardown_ledger RATE = 0.96 }", decay)
        self.assertIn("gm_decay = { VAR = gm_vanity_ledger RATE = 0.92 }", decay)
        for ig in IGS:
            self.assertIn(f"gm_decay = {{ VAR = gm_ig_ledger_{ig} RATE = 0.97 }}", decay)
        snap = squash(block(self.e, "gm_decay"))
        self.assertIn("var:$VAR$ < 0.05 var:$VAR$ > -0.05 } set_variable = { name = $VAR$ value = 0 }", snap)
        self.assertNotRegex(strip_comments(self.e), r"remove_variable = gm_(teardown|vanity|ig)_ledger")
        monthly = squash(block(self.e, "gm_country_monthly"))
        self.assertLess(monthly.find("gm_decay_ledgers = yes"), monthly.find("gm_country_refresh = yes"))

    def test_je_lifecycle(self):
        je = read(JE)
        self.assertIn("any_scope_state = { has_building = building_grand_monument }", squash(block(je, "possible")))
        shown = squash(block(je, "is_shown_when_inactive"))
        self.assertIn("gm_system_enabled = yes", shown)
        self.assertIn("any_scope_state = { has_building = building_grand_monument }", shown)
        invalid = squash(block(je, "invalid"))
        self.assertIn("gm_system_enabled = no", invalid)
        self.assertIn("gm_ledgers_idle = yes", invalid)
        self.assertIn("NOT = { any_scope_state = { has_variable = gm_seen } }", invalid)
        self.assertIsNone(block(je, "immediate"), "nothing a revolution's winner would lose")
        # Old saves that predate this JE never get it from is_shown_when_inactive
        # alone (scripting_best_practices.md § "JE Auto-Activation Requires
        # BOTH"), so gm_country_refresh must add it explicitly too.
        self.assertIn("add_journal_entry = { type = je_grand_monuments }", squash(read(EFFECTS)))
        # No status_desc since play-test round 2 (2026-09-29): its counts were
        # the overview's (LocFixTests.test_no_status_line_repeats_the_overview).
        for key in ("je_grand_monuments", "je_grand_monuments_reason"):
            self.assertIn(key, loc())

    def test_refresh_event_and_hooks(self):
        ev = squash(raw_block_at(read(EVENTS), r"(?m)^monument_events\.20\s*=\s*\{"))
        self.assertIn("type = country_event hidden = yes", ev)
        self.assertIn("immediate = { gm_country_refresh = yes }", ev)
        oa = read(ON_ACTIONS)
        self.assertIn("gm_country_on_action", squash(block(oa, "on_monthly_pulse_country")))
        self.assertIn("gm_country_monthly = yes", squash(block(oa, "gm_country_on_action")))
        for hook, oa_name in (("on_law_activated", "gm_law_activated_on_action"),
                              ("on_new_ruler", "gm_new_ruler_on_action")):
            self.assertIn(oa_name, squash(block(oa, hook)))
            self.assertIn("trigger_event = { id = monument_events.20 }", squash(block(oa, oa_name)))

    def test_cultural_pull(self):
        text = read(CULTURAL)
        body = squash(block(text, "cultural_pull_from_grand_monuments"))
        self.assertIn("value = var:gm_s_culture", body)
        # No ceiling (owner, 2026-10-16): the curve is the diminishing return.
        self.assertNotIn("max =", body)
        self.assertIsNone(block(text, "grand_monument_levels_in_state"))


class OpenCurveTests(unittest.TestCase):
    """gm_set_steps_lin_open: the 1/n curve with no end, for prestige and
    cultural pull (owner, 2026-10-19). Step k takes k first steps, so each is
    worth 1/k of the first a point of grandeur and the effect never stops
    growing."""

    def test_effect_shape(self):
        body = squash(block(read(EFFECTS), "gm_set_steps_lin_open"))
        self.assertIsNotNone(body)
        self.assertEqual(body,
                         "set_variable = { name = $OUT$ value = 0 } "
                         "set_variable = { name = $WIDTH$ value = $F$ } "
                         "set_variable = { name = $NEXT$ value = $F$ } "
                         "while = { limit = { var:$IN$ >= var:$NEXT$ } "
                         "change_variable = { name = $OUT$ add = 1 } "
                         "change_variable = { name = $WIDTH$ add = $F$ } "
                         "change_variable = { name = $NEXT$ add = var:$WIDTH$ } } "
                         "change_variable = { name = $OUT$ add = { value = var:$IN$ subtract = var:$NEXT$ "
                         "add = var:$WIDTH$ divide = var:$WIDTH$ min = 0 } }")
        # The doubling curve's open form went with cultural pull's move.
        self.assertIsNone(block(read(EFFECTS), "gm_set_steps_open"))

    @staticmethod
    def steps(g, f=10):
        """The effect, transcribed."""
        s, width, nxt = 0, f, f
        while g >= nxt:
            s += 1
            width += f
            nxt += width
        s += max((g - nxt + width) / width, 0)
        return s, nxt, width

    def test_matches_the_fixed_curve(self):
        """Inside the fixed curve's thirty steps the open form agrees with it."""
        for g in range(0, 2326, 7):
            fixed = sum(min(max((g - start) / size, 0), 1) for start, size in lin_curve_terms(5))
            self.assertAlmostEqual(self.steps(g, 5)[0], fixed, msg=g)

    def test_step_k_ends_at_k_triangle(self):
        f = 10
        for k in range(1, 60):
            end = f * k * (k + 1) // 2
            s, nxt, width = self.steps(end)
            self.assertAlmostEqual(s, k, msg=end)
            self.assertEqual((nxt, width), (end + f * (k + 1), f * (k + 1)), end)
            self.assertAlmostEqual(self.steps(end - f * k / 2)[0], k - 0.5, msg=end)

    def test_no_ceiling(self):
        self.assertGreater(self.steps(10 ** 6)[0], 400)
        prev = 0
        for g in range(0, 30000, 37):
            s = self.steps(g)[0]
            self.assertGreaterEqual(s, prev, g)
            prev = s


# ---- Task 6: contested monuments -----------------------------------------------------

class ContestTests(unittest.TestCase):
    def setUp(self):
        self.e = read(EFFECTS)

    def test_contest_records_the_table_igs(self):
        body = squash(block(self.e, "gm_state_record_contest_igs"))
        for d in DEDICATIONS:
            if d.kind == "regime":
                self.assertIn(f"gm_state_has_pm = {{ PM = pm_monument_{d.key} }} }} "
                              f"set_variable = {{ name = gm_base_ig value = flag:{d.oppose} }} "
                              f"set_variable = {{ name = gm_supporter_ig value = flag:{d.approve} }}", body)
        self.assertIn("gm_state_kind_faith = yes } set_variable = { name = gm_supporter_ig value = flag:devout }", body)
        self.assertIn("set_variable = { name = gm_base_ig value = owner.var:gm_opposition_ig }", body)
        self.assertIn("set_variable = { name = gm_supporter_ig value = var:gm_honoree_ig }", body)

    def test_monthly_check(self):
        body = squash(block(self.e, "gm_check_contests"))
        self.assertTrue(body.startswith("if = { limit = { NOT = { has_variable = te_cw_role } }"))
        # Nor a gifted monument whose rebuilt method may still read as another
        # dedication (opportunities spec §3.1).
        # Nor one no record describes: a building a merge brought waits to be
        # adopted (issue #936), and first sight or the ceremony always comes first.
        self.assertIn("limit = { gm_state_is_dedicated = yes gm_state_is_bound = yes "
                      "NOT = { has_variable = gm_ceremony_pending } NOT = { has_variable = gm_restore_pm } "
                      "has_variable = gm_seen }", body)
        self.assertIn("owner = { has_variable = gm_cw_adopting } } gm_state_adopt_for_winner = yes", body)
        # A shrine this country did not raise always becomes heritage, whatever
        # the route it arrived by (conquest, a secession that drops te_cw_role,
        # or a civil war of this country's own), and this branch must run
        # before the lift/contest else_ifs so it wins over "contest".
        heritage = "gm_state_kind_faith = yes gm_state_raised_by_owner = no gm_state_is_heritage = no } gm_state_lift_contest = yes set_variable = gm_heritage"
        self.assertIn(heritage, body)
        self.assertIn("gm_state_is_heritage = yes } gm_state_message_fits = yes } gm_state_lift_contest = yes", body)
        self.assertIn("gm_state_is_heritage = no gm_state_message_fits = no } gm_state_contest = yes", body)
        self.assertLess(body.find(heritage), body.find("gm_state_is_contested = yes gm_state_is_heritage = yes"))
        self.assertEqual(body.count("else_if ="), 2, "the lift and contest branches follow the new heritage if")

    def test_months_count_once_a_month(self):
        self.assertNotIn("add = 1", squash(block(self.e, "gm_check_contests")))
        self.assertIn("limit = { gm_state_is_contested = yes } change_variable = { name = gm_contested add = 1 }",
                      squash(block(self.e, "gm_country_monthly")))

    def test_changed_hands(self):
        body = squash(block(self.e, "gm_state_changed_hands"))
        self.assertIn("owner = { NOT = { has_variable = te_cw_role } is_revolutionary = no }", body)
        self.assertIn("gm_state_raised_by_owner = no", body)
        self.assertIn("limit = { gm_state_kind_faith = yes } gm_state_lift_contest = yes set_variable = gm_heritage", body)
        # Unconditional: a monument already contested under the old owner is
        # re-recorded for the new one too, not left with the old owner's IGs
        # and no fresh gm_new_contest (plan-mandated fix).
        self.assertIn("gm_remove_state_var = { VAR = gm_heritage } gm_state_contest = yes", body)
        self.assertNotIn("limit = { gm_state_is_contested = no } gm_state_contest = yes", body)
        self.assertTrue(body.endswith("owner = { trigger_event = { id = monument_events.20 } }"))
        oa = read(ON_ACTIONS)
        self.assertIn("gm_state_owner_change_on_action", squash(block(oa, "on_state_owner_change")))
        self.assertIn("gm_state_changed_hands = yes", squash(block(oa, "gm_state_owner_change_on_action")))

    def test_civil_war_winner_adopts(self):
        won = squash(block(read(CIVIL_WAR_ON_ACTIONS), "te_civil_war_on_won"))
        self.assertLess(won.find("te_civil_war_resolve_sides = yes"), won.find("gm_repair_after_civil_war = yes"))
        self.assertLess(won.find("gm_repair_after_civil_war = yes"), won.find("te_civil_war_clear = yes"))
        repair = squash(block(self.e, "gm_repair_after_civil_war"))
        self.assertIn("set_variable = { name = gm_cw_loser value = scope:te_cw_loser days = 30 }", repair)
        self.assertIn("set_variable = { name = gm_cw_adopting value = yes days = 30 }", repair)
        adopt = squash(block(self.e, "gm_state_adopt_for_winner"))
        self.assertIn("var:gm_raised_by = scope:gm_tmp_loser", adopt)
        self.assertIn("set_variable = { name = gm_raised_by value = owner }", adopt)

    def test_ledger_helper_covers_every_ig(self):
        body = squash(block(self.e, "gm_state_ledger_ig"))
        for ig in IGS:
            self.assertIn(f"gm_state_ledger_ig_one = {{ WHO = $WHO$ FACTOR = $FACTOR$ IG = {ig} }}", body)
        one = squash(block(self.e, "gm_state_ledger_ig_one"))
        self.assertIn("var:$WHO$ = flag:$IG$", one)
        self.assertIn("value = { value = prev.var:gm_grandeur multiply = $FACTOR$ add = var:gm_ig_ledger_$IG$ }", one)

    def test_the_three_choices(self):
        record = squash(block(self.e, "gm_state_record_teardown"))
        self.assertIn("add = prev.var:gm_grandeur", record)
        # Keeps the pulse running so a teardown recorded from the last
        # monument (panel demolition) still gets decayed (plan-mandated fix).
        self.assertIn("owner = { gm_init_ledgers = yes set_variable = { name = gm_teardown_ledger "
                      "value = { value = var:gm_teardown_ledger add = prev.var:gm_grandeur } } "
                      "set_variable = gm_active }", record)
        self.assertIn("gm_state_ledger_ig = { WHO = gm_base_ig FACTOR = 1 }", record)
        self.assertIn("gm_state_ledger_ig = { WHO = gm_supporter_ig FACTOR = -1 }", record)
        tear = squash(block(self.e, "gm_state_tear_down"))
        for s in ("gm_state_record_teardown = yes", "remove_list_variable = { name = gm_states target = prev }",
                  "remove_building = building_grand_monument", "gm_clear_state = { KEEP_LANDMARK = no }"):
            self.assertIn(s, tear)
        # Rededicate asks first and pays on the answer (sites spec 2026-10-18 §5).
        self.assertIn("gm_state_start_ceremony = yes", squash(block(self.e, "gm_state_rededicate")))
        rededicate = squash(block(self.e, "gm_state_apply_rededicate"))
        for s in ("set_variable = { name = gm_rededicate_cost value = gm_state_rededicate_cost }",
                  "add_treasury = { value = prev.var:gm_rededicate_cost multiply = -1 }",
                  "gm_state_ledger_ig = { WHO = gm_supporter_ig FACTOR = -0.5 }",
                  "gm_clear_state = { KEEP_LANDMARK = yes }"):
            self.assertIn(s, rededicate)
        self.assertIn("multiply = 500", squash(block(read(VALUES), "gm_state_rededicate_cost")))
        self.assertNotIn("multiply = 5000", squash(block(read(VALUES), "gm_state_rededicate_cost")))
        preserve = squash(block(self.e, "gm_state_preserve"))
        self.assertIn("gm_state_ledger_ig = { WHO = gm_base_ig FACTOR = -1 }", preserve)
        self.assertIn("set_variable = gm_heritage", preserve)
        for choice in ("tear_down", "rededicate", "preserve"):
            self.assertEqual(squash(block(self.e, f"gm_state_choose_{choice}")),
                             f"custom_tooltip = {{ text = gm_{choice}_tt gm_state_{choice} = yes }}")
            self.assertIn(f"gm_{choice}_tt", loc())

    def test_ladder_reaches_200(self):
        body = squash(block(read(LADDER), "te_construction_market_build_specified_level"))
        for n in range(1, 201):
            self.assertIn(f"{n} = {{ create_building = {{ building = $SPEC_TYPE$ level = {n} }} }}", body)

    def test_one_ceremony_at_a_time(self):
        body = squash(block(self.e, "gm_state_start_ceremony"))
        self.assertIn("NOT = { has_variable = gm_ceremony_pending }", body)
        self.assertIn("set_variable = { name = gm_ceremony_pending days = 30 }", body)
        self.assertIn("set_variable = { name = gm_ceremony_level value = gm_state_primary_levels }", body)
        self.assertIn("trigger_event = { id = monument_events.2 popup = yes }", body)

    def test_the_refresh_asks_a_ceremony_the_hook_missed(self):
        """Five queued levels finishing on one day fired no on_building_built
        (2026-10-07): the refresh asks once for each grandeur no ceremony has
        asked about, so leaving a monument undedicated waits for its next level."""
        sweep = squash(block(self.e, "gm_state_offer_missed_ceremony"))
        self.assertIn("if = { limit = { gm_system_enabled = yes "
                      "gm_state_ai_dedicates_now = yes NOT = { has_variable = gm_ceremony_pending } } "
                      "gm_state_start_ceremony = yes }", sweep)
        refresh = squash(block(self.e, "gm_country_refresh"))
        self.assertLess(refresh.find("every_scope_state = { limit = { has_building = building_grand_monument }"),
                        refresh.find("gm_state_offer_missed_ceremony = yes"))
        self.assertLess(refresh.find("gm_state_offer_missed_ceremony = yes"),
                        refresh.find("add_to_variable_list = { name = gm_states target = prev }"))
        self.assertIn("gm_remove_state_var = { VAR = gm_ceremony_level }", squash(block(self.e, "gm_clear_state")))
        ev2 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.2\s*=\s*\{")))
        # Not yet ends the pending ceremony (gm_state_ceremony_not_yet).
        self.assertIn("default_option = yes", ev2)
        self.assertIn("hidden_effect = { gm_state_ceremony_not_yet = yes }", ev2)

    def test_demolished_contested_counts_as_torn_down(self):
        body = squash(block(self.e, "gm_state_monthly"))
        # Not one carried off as a trophy (trophies spec §1).
        self.assertIn("limit = { gm_state_is_contested = yes NOT = { has_variable = gm_carried_off } } "
                      "gm_state_record_teardown = yes", body)

    def test_ai_and_notice(self):
        monthly = squash(block(self.e, "gm_country_monthly"))
        self.assertIn("gm_ai_decide_contests = yes", monthly)
        ai = squash(block(self.e, "gm_ai_decide_contests"))
        self.assertTrue(ai.startswith("if = { limit = { is_ai = yes }"))
        for s in ("gm_state_tear_down = yes", "gm_state_preserve = yes", "gm_state_rededicate = yes",
                  "var:gm_contested >= 2"):
            self.assertIn(s, ai)
        notify = squash(block(self.e, "gm_notify_new_contests"))
        self.assertIn("limit = { is_ai = no } trigger_event = { id = monument_events.16 }", notify)

    def test_events(self):
        text = read(EVENTS)
        notice = squash(raw_block_at(text, r"(?m)^monument_events\.16\s*=\s*\{"))
        self.assertIn("type = country_event", notice)
        self.assertIn("remove_variable = gm_new_contest", notice)
        self.assertIn("gm_state_tear_down = yes", notice)
        self.assertIn("gm_state_preserve = yes", notice)
        self.assertIn("trigger_event = { id = monument_events.17 }", notice)
        self.assertIn("hidden_effect = { gm_country_refresh = yes }", notice)
        # Minor 2: a state ceded while the notice is open must not act for a
        # country that no longer owns it. Every every_in_list limit in .16
        # checks owner = root (the notice's country), and every gate appears
        # right beside its own gm_state_is_contested check.
        self.assertEqual(notice.count("gm_state_is_contested = yes owner = root"), 3)
        one = squash(raw_block_at(text, r"(?m)^monument_events\.17\s*=\s*\{"))
        self.assertIn("type = state_event", one)
        self.assertIn("owner = { save_scope_as = monument_owner }", one)
        for choice in ("tear_down", "rededicate", "preserve"):
            self.assertIn(f"limit = {{ owner = scope:monument_owner }} gm_state_choose_{choice} = yes", one)
        L = loc()
        for key in ("t", "d", "f", "a", "b", "c", "a.tt", "b.tt", "c.tt"):
            self.assertIn(f"monument_events.16.{key}", L)
        for key in ("t", "desc", "f", "a", "b", "c", "d"):
            self.assertIn(f"monument_events.17.{key}", L)
        self.assertIn("desc = monument_events.17.desc", one)

    def test_custom_loc(self):
        text = read(CUSTOM_LOC)
        ded = squash(block(text, "gm_dedication_name"))
        for d in DEDICATIONS:
            self.assertIn(f"localization_key = pm_monument_{d.key}", ded)
        for name, var in (("gm_base_ig_name", "gm_base_ig"), ("gm_supporter_ig_name", "gm_supporter_ig")):
            body = squash(block(text, name))
            for ig in IGS:
                self.assertIn(f"var:{var} = flag:{ig} }} localization_key = ig_{ig}", body)
            self.assertIn("localization_key = gm_ig_nobody", body)
        status = squash(block(text, "gm_status_name"))
        for s in ("contested", "heritage", "undedicated", "unsettled", "fits"):
            self.assertIn(f"localization_key = gm_status_{s}", status)
            self.assertIn(f"gm_status_{s}", loc())

    # ---- Controller rulings: ledgers zeroed when the pulse stops; gm_active set on sight ----

    def test_ledgers_zeroed_when_pulse_stops(self):
        zero = squash(block(self.e, "gm_zero_ledgers"))
        for var in ["gm_teardown_ledger", "gm_vanity_ledger"] + [f"gm_ig_ledger_{ig}" for ig in IGS]:
            self.assertIn(f"set_variable = {{ name = {var} value = 0 }}", zero)
        monthly = squash(block(self.e, "gm_country_monthly"))
        # Pin placement, not just order: the call must sit inside the outer
        # if's own body (gm_ledgers_idle branch), not merely somewhere before
        # remove_variable = gm_active -- a call hoisted above the outer if
        # would zero every country's ledgers monthly and still pass a
        # find()-based order check.
        # v2 §2: the pulse also keeps running while a commission is open or on offer.
        self.assertIn("gm_ledgers_idle = yes NOT = { has_variable = gm_com_open } "
                      "NOT = { has_variable = gm_com_offered } NOT = { has_variable = gm_naming_active } } "
                      "gm_zero_ledgers = yes", monthly)
        self.assertLess(monthly.find("gm_zero_ledgers = yes"), monthly.find("remove_variable = gm_active"))

    def test_gm_active_set_on_refresh_when_monument_seen(self):
        body = squash(block(self.e, "gm_country_refresh"))
        # A monument, an open commission (v2 §2.7) or a trophy held or abroad
        # (trophies spec §6) keeps the pulse running.
        self.assertTrue(body.startswith("gm_init_ledgers = yes if = { limit = { OR = { any_scope_state = "
                                        "{ has_building = building_grand_monument } has_variable = gm_com_open "
                                        "gm_tr_country_has_any = yes gm_arch_country_has_any = yes } } set_variable = gm_active }"),
                        body[:240])


# ---- Task 7: the ceremony, skins, the inscription ------------------------------------

CEREMONY_OPTION = {"crown": "l", "republic": "b", "revolution": "n", "leader": "o", "religious": "c",
                   "civic": "m", "war_memorial": "e", "artistic": "g", "naturalist": "h", "scientific": "i",
                   "industrial": "j", "athletic": "k"}
CEREMONY_GATE = {"crown": "monument_government_is_crowned = yes",
                 "republic": "monument_government_is_republican = yes",
                 "revolution": "gm_government_is_revolutionary = yes",
                 "leader": "gm_can_raise_leader_monument = yes",
                 "religious": "NOT = { has_law_or_variant = law_type:law_state_atheism }",
                 "industrial": "NOT = { has_law_or_variant = law_type:law_industry_banned }"}
INSCRIPTION_FAITHS = {"catholic": "latin", "jewish": "hebrew", "hindu": "sanskrit", "theravada": "pali",
                      "oriental_orthodox": "coptic", "sunni": "arabic", "shiite": "arabic", "ibadi": "arabic",
                      "orthodox": "slavonic"}
# The landmarks standing in 1836 (phase 4 spec 2026-10-12 §2), in picture-code
# order: code 1,000,000 + the row number. Each is its own skin
# (`landmark_<key>`) with one form, placed once by gm_seed_landmarks. The owner
# is the country holding the state's part in the 1836 history (game files,
# 2026-10-11: Jaipur is Dhundhar's, JAI). The stand-in is the (skin, form) pair
# whose picture it shows until its own is drawn. Adding a row is the checklist:
# the failures name every site. A row with placed=False is never seeded: it
# names a trophy of 1836 with no standing monument of its own (spec
# 2026-10-12-grand-monument-loot-and-1836-trophies-design.md §2.2), and stands
# as a landmark only once that trophy goes home. Its state and owner are its
# origin's (TROPHIES_1836 in test_grand_monument_trophies.py), and it has no level.
# A row with beside=True is a second placed landmark in a state another stands
# in (spec 2026-10-13-multiple-monuments-per-state-design.md §6): it follows that
# state's first row, and the seeding stands it beside it as a secondary monument
# rather than skipping it. Rome, Beijing and Athens are the next.
# A row with a year is a historical opportunity's landmark (signatures spec
# 2026-10-16 §6): never placed at the start, offered once a game to whoever
# holds its state from that year for forty years (HISTORICAL_OPPORTUNITIES), its
# level the opportunity's target. Its owner is whoever completes it, so no tag.
Landmark = namedtuple("Landmark", "key state tag dedication form standin level placed beside buried year",
                      defaults=(True, False, False, None))
LANDMARKS = (
    Landmark("arc_de_triomphe", "STATE_ILE_DE_FRANCE", "FRA", "war_memorial", "arch", ("generic", "arch"), 15),
    Landmark("alexander_column", "STATE_INGRIA", "RUS", "crown", "column", ("generic", "column"), 10),
    Landmark("brandenburg_gate", "STATE_BRANDENBURG", "PRU", "civic", "gate", ("generic", "gate"), 10),
    Landmark("washington_monument_baltimore", "STATE_MARYLAND", "USA", "republic", "column", ("generic", "column"), 5),
    Landmark("la_scala", "STATE_LOMBARDY", "AUS", "artistic", "opera_house", ("generic", "opera_house"), 10),
    Landmark("teatro_di_san_carlo", "STATE_CAMPANIA", "SIC", "artistic", "opera_house", ("generic", "opera_house"), 5),
    Landmark("jantar_mantar", "STATE_RAJPUTANA", "JAI", "scientific", "observatory",
             ("heritage_sanskrit", "observatory"), 5),
    Landmark("shalimar_gardens", "STATE_PUNJAB", "PAN", "naturalist", "gardens", ("heritage_avestan", "gardens"), 5),
    Landmark("jardim_botanico", "STATE_RIO_DE_JANEIRO", "BRZ", "naturalist", "gardens", ("generic", "gardens"), 5),
    Landmark("stelae_of_aksum", "STATE_GONDER", "TGR", "civic", "stele", ("heritage_geez", "stele"), 5),
    Landmark("liberty_column", "STATE_ZEALAND", "DEN", "civic", "obelisk", ("generic", "obelisk"), 5),
    Landmark("lion_monument", "STATE_EAST_SWITZERLAND", "SWI", "war_memorial", "statue", ("generic", "statue"), 5),
    # Added 2026-10-11 (owner): monuments a political revolution contests, in the
    # countries players most often take through one. All To the Crown but the
    # Lion of Saint Mark; it and Sans-Souci are contested from the first refresh
    # (a republic's monument in a monarchy, a king's in a republic).
    Landmark("temple_of_heaven", "STATE_BEIJING", "CHI", "crown", "hall", ("heritage_chinese", "hall"), 10),
    Landmark("topkapi_palace", "STATE_EASTERN_THRACE", "TUR", "crown", "gate", ("heritage_arabic", "gate"), 10),
    Landmark("golestan_palace", "STATE_IRAKAJEMI", "PER", "crown", "hall", ("heritage_avestan", "hall"), 5),
    Landmark("basilica_of_superga", "STATE_PIEDMONT", "SAR", "crown", "mausoleum", ("generic", "mausoleum"), 5),
    Landmark("tomb_of_william_the_silent", "STATE_HOLLAND", "NET", "crown", "mausoleum", ("generic", "mausoleum"), 5),
    Landmark("cenotaph_of_maximilian", "STATE_TYROL", "AUS", "crown", "mausoleum", ("generic", "mausoleum"), 5),
    Landmark("arco_de_santa_maria", "STATE_OLD_CASTILE", "SPA", "crown", "gate", ("generic", "gate"), 5),
    Landmark("statue_of_louis_xiv", "STATE_RHONE", "FRA", "crown", "statue", ("generic", "statue"), 5),
    Landmark("lion_of_saint_mark", "STATE_VENETIA", "AUS", "republic", "column", ("generic", "column"), 5),
    Landmark("sans_souci_palace", "STATE_HAITI", "HAI", "crown", "hall", ("generic", "hall"), 5),
    Landmark("nikko_toshogu", "STATE_KANTO", "JAP", "crown", "gate", ("heritage_chinese", "gate"), 5),
    # Added 2026-10-12 (owner: "grand monuments for the great powers to loot"):
    # where Europe's looting took place. Owners from the game's 00_states.txt:
    # Kumasi is in Asante's part of the Gold Coast, the Red Fort in the Mughal
    # emperor's one province of Delhi (its city hub).
    Landmark("parthenon", "STATE_ATTICA", "GRE", "civic", "pantheon", ("heritage_greek", "pantheon"), 10),
    # Persepolis, Baalbek and Karnak at 10 (owner, 2026-10-19): the great
    # ancient sites, beside the 10-level digs (the Pergamon Altar, Olympia,
    # Delphi), and Karnak's obelisks above the one Luxor obelisk in Paris (5); a
    # monument a century old in 1836 has finished ageing, so what it starts with
    # is what it keeps.
    Landmark("obelisks_of_karnak", "STATE_UPPER_EGYPT", "EGY", "civic", "obelisk", ("generic", "obelisk"), 10),
    Landmark("royal_palace_of_benin", "STATE_BENIN", "BEN", "crown", "hall", ("generic", "hall"), 5),
    Landmark("royal_palace_of_kumasi", "STATE_GOLD_COAST", "ASH", "crown", "hall", ("generic", "hall"), 5),
    Landmark("bukgwan_victory_stele", "STATE_SARIWON", "KOR", "war_memorial", "stele", ("heritage_geez", "stele"), 5),
    Landmark("imperial_city_of_hue", "STATE_ANNAM", "DAI", "crown", "gate", ("heritage_chinese", "gate"), 10),
    Landmark("persepolis", "STATE_FARS", "PER", "civic", "hall", ("heritage_avestan", "hall"), 10),
    Landmark("red_fort", "STATE_DELHI", "MUG", "crown", "gate", ("heritage_avestan", "gate"), 10),
    # Never placed: the trophies of 1836 with no standing monument of their own.
    Landmark("rosetta_stone", "STATE_LOWER_EGYPT", "EGY", "civic", "stele", ("heritage_geez", "stele"), None, False),
    Landmark("temple_of_dendera", "STATE_UPPER_EGYPT", "EGY", "civic", "colonnade", ("heritage_aramaic", "colonnade"),
             None, False),
    Landmark("luxor_obelisk", "STATE_UPPER_EGYPT", "EGY", "civic", "obelisk", ("generic", "obelisk"), None, False),
    Landmark("venus_de_milo", "STATE_WEST_AEGEAN_ISLANDS", "GRE", "civic", "statue", ("generic", "statue"), None, False),
    Landmark("piraeus_lion", "STATE_ATTICA", "GRE", "civic", "statue", ("generic", "statue"), None, False),
    Landmark("horses_of_saint_mark", "STATE_EASTERN_THRACE", "TUR", "civic", "statue", ("generic", "statue"), None,
             False),
    Landmark("tipus_tiger", "STATE_MYSORE", "MYS", "civic", "statue", ("generic", "statue"), None, False),
    Landmark("baba_merzoug", "STATE_ALGIERS", "MAS", "war_memorial", "column", ("generic", "column"), None, False),
    # Added 2026-10-12 (owner: the Throne of Kandy, and looted places in
    # decentralized territory). Great Zimbabwe is in the Mashona's part of
    # Zambezi (Harare and Bulawayo are its hubs), Klungkung in Bali's part of
    # the Sunda Islands (Denpasar is its port). Abomey is Dahomey's.
    Landmark("great_zimbabwe", "STATE_ZAMBEZI", "MSH", "civic", "round_tower", ("heritage_irish", "round_tower"), 5),
    Landmark("royal_palaces_of_abomey", "STATE_DAHOMEY", "DAH", "crown", "hall", ("generic", "hall"), 5),
    Landmark("klungkung_palace", "STATE_SUNDA_ISLANDS", "BAL", "crown", "gate", ("heritage_sanskrit", "gate"), 5),
    Landmark("royal_palace_of_kandy", "STATE_CEYLON", "BCE", "civic", "hall", ("generic", "hall"), None, False),
    # Added 2026-10-12 (owner: Italy, Turkey and the Levant). Each state has
    # one owner in 1836: Tuscany, the Papal States, the Ottomans (Aydin holds
    # Mugla, so Bodrum) and Egypt (Lebanon's Zahle hub is Baalbek's valley).
    Landmark("uffizi_gallery", "STATE_TUSCANY", "TUS", "civic", "hall", ("generic", "hall"), 10),
    Landmark("capitoline_museums", "STATE_LAZIO", "PAP", "civic", "forum", ("heritage_latin", "forum"), 5),
    Landmark("bodrum_castle", "STATE_AYDIN", "TUR", "war_memorial", "tower", ("heritage_gothic", "tower"), 5),
    Landmark("temples_of_baalbek", "STATE_LEBANON", "EGY", "civic", "colonnade", ("heritage_aramaic", "colonnade"),
             10),
    # Added 2026-10-12: heritage sites with no weight in 1836, which the
    # owner's revised rule admits at lower priority. Single-owner states only
    # (owner): Palmyra in Syria (Homs is its nearest hub), Xanthos in Konya
    # (Antalya), Dhiban's stele in Transjordan (Kerak).
    Landmark("palmyra", "STATE_SYRIA", "EGY", "civic", "colonnade", ("heritage_aramaic", "colonnade"), 5),
    Landmark("xanthos", "STATE_KONYA", "TUR", "civic", "rock_cut", ("heritage_aramaic", "rock_cut"), 5),
    Landmark("mesha_stele", "STATE_TRANSJORDAN", "EGY", "war_memorial", "stele", ("heritage_geez", "stele"), 5),
    # Added 2026-10-12 (owner). Baghdad is the Ottomans' alone; the stand-in is
    # the Persian gate, an iwan like Taq Kasra's.
    Landmark("arch_of_ctesiphon", "STATE_BAGHDAD", "TUR", "civic", "arch", ("heritage_avestan", "gate"), 5),
    # Buried until the game (buried=True, issue #939): placed by an excavation, never at the start. The
    # owner is whoever digs, so there is no tag; the level is the monument's when it is unearthed.
    Landmark("nineveh_library", "STATE_MOSUL", None, "civic", "hall", ("heritage_avestan", "hall"), 10, False, False, True),
    Landmark("winged_victory_of_samothrace", "STATE_WESTERN_THRACE", None, "civic", "statue", ("generic", "statue"), 5, False, False, True),
    Landmark("vindolanda_tablets", "STATE_YORKSHIRE", None, "civic", "hall", ("generic", "hall"), 5, False, False, True),
    Landmark("troy_hisarlik", "STATE_HUDAVENDIGAR", None, "civic", "gate", ("generic", "gate"), 10, False, False, True),
    Landmark("mycenae_grave_circle", "STATE_PELOPONNESE", None, "civic", "mausoleum", ("generic", "mausoleum"), 10, False, False, True),
    Landmark("pergamon_altar", "STATE_AYDIN", None, "civic", "pantheon", ("heritage_greek", "pantheon"), 10, False, False, True),
    Landmark("deir_el_bahari_cache", "STATE_UPPER_EGYPT", None, "civic", "rock_cut", ("heritage_aramaic", "rock_cut"), 5, False, False, True),
    Landmark("ishtar_gate_babylon", "STATE_BAGHDAD", None, "civic", "gate", ("heritage_avestan", "gate"), 10, False, False, True),
    Landmark("palace_of_knossos", "STATE_CRETE", None, "civic", "hall", ("generic", "hall"), 10, False, False, True),
    Landmark("antikythera_mechanism", "STATE_PELOPONNESE", None, "civic", "statue", ("generic", "statue"), 5, False, False, True),
    Landmark("oseberg_ship", "STATE_EASTERN_NORWAY", None, "civic", "statue", ("generic", "statue"), 5, False, False, True),
    Landmark("machu_picchu", "STATE_ICA", None, "civic", "gate", ("generic", "gate"), 15, False, False, True),
    Landmark("bust_of_nefertiti", "STATE_MIDDLE_EGYPT", None, "civic", "statue", ("generic", "statue"), 5, False, False, True),
    Landmark("mohenjo_daro", "STATE_SINDH", None, "civic", "forum", ("heritage_latin", "forum"), 10, False, False, True),
    Landmark("tomb_of_tutankhamun", "STATE_UPPER_EGYPT", None, "civic", "mausoleum", ("generic", "mausoleum"), 15, False, False, True),
    Landmark("royal_cemetery_at_ur", "STATE_BASRA", None, "civic", "mausoleum", ("generic", "mausoleum"), 10, False, False, True),
    Landmark("sanxingdui_pits", "STATE_SICHUAN", None, "civic", "hall", ("heritage_chinese", "hall"), 10, False, False, True),
    Landmark("sutton_hoo", "STATE_EAST_ANGLIA", None, "civic", "mausoleum", ("generic", "mausoleum"), 5, False, False, True),
    Landmark("lascaux_caves", "STATE_AQUITAINE", None, "civic", "rock_cut", ("heritage_aramaic", "rock_cut"), 10, False, False, True),
    Landmark("nag_hammadi_library", "STATE_UPPER_EGYPT", None, "civic", "stele", ("heritage_geez", "stele"), 5, False, False, True),
    Landmark("dead_sea_scrolls", "STATE_PALESTINE", None, "civic", "stele", ("heritage_geez", "stele"), 10, False, False, True),
    Landmark("tomb_of_pakal", "STATE_CHIAPAS", None, "civic", "pyramid", ("heritage_mayan", "pyramid"), 10, False, False, True),
    Landmark("mawangdui_tombs", "STATE_HUNAN", None, "civic", "mausoleum", ("generic", "mausoleum"), 10, False, False, True),
    Landmark("terracotta_army", "STATE_XIAN", None, "civic", "mausoleum", ("generic", "mausoleum"), 15, False, False, True),
    Landmark("tomb_of_philip_ii", "STATE_MACEDONIA", None, "civic", "mausoleum", ("generic", "mausoleum"), 10, False, False, True),
    Landmark("tomb_of_marquis_yi", "STATE_EASTERN_HUBEI", None, "civic", "hall", ("heritage_chinese", "hall"), 10, False, False, True),
    Landmark("royal_tombs_of_sipan", "STATE_CAJAMARCA", None, "civic", "pyramid", ("heritage_nahuatl", "pyramid"), 10, False, False, True),
    Landmark("otzi_the_iceman", "STATE_SOUTH_TYROL", None, "civic", "statue", ("generic", "statue"), 5, False, False, True),
    Landmark("caral_supe", "STATE_LIMA", None, "civic", "pyramid", ("heritage_nahuatl", "pyramid"), 10, False, False, True),
    Landmark("gobekli_tepe", "STATE_DIYARBAKIR", None, "civic", "colonnade", ("heritage_aramaic", "colonnade"), 15, False, False, True),
    Landmark("olympia", "STATE_PELOPONNESE", None, "civic", "pantheon", ("heritage_greek", "pantheon"), 10, False, False, True),
    Landmark("delphi", "STATE_ATTICA", None, "civic", "stoa", ("heritage_greek", "stoa"), 10, False, False, True),
    Landmark("sidon_necropolis", "STATE_LEBANON", None, "civic", "mausoleum", ("generic", "mausoleum"), 5, False, False, True),
    Landmark("villa_of_the_papyri", "STATE_CAMPANIA", None, "civic", "hall", ("generic", "hall"), 10, False, False, True),
    Landmark("tomb_of_alexander", "STATE_LOWER_EGYPT", None, "civic", "mausoleum", ("generic", "mausoleum"), 15, False, False, True),
    # Added 2026-10-16 (owner): being dug in 1836, so seeded as a dig already under way (VECTOR = excavating).
    Landmark("pompeii", "STATE_CAMPANIA", None, "civic", "forum", ("heritage_latin", "forum"), 15, False, False, True),
    # Added 2026-10-16 (signatures spec §6.4): the first historical opportunities, raised by completing one.
    Landmark("walhalla", "STATE_BAVARIA", None, "civic", "hall_of_fame", ("heritage_gothic", "hall_of_fame"), 5, False,
             year=1836),
    Landmark("bunker_hill_monument", "STATE_MASSACHUSETTS", None, "war_memorial", "obelisk", ("generic", "obelisk"), 5,
             False, year=1836),
    Landmark("obelisk_of_the_second_of_may", "STATE_NEW_CASTILE", None, "war_memorial", "obelisk",
             ("generic", "obelisk"), 5, False, year=1836),
    # A Grand Shrine stands in its faith's own building: the form is the skin's (gm_form_name).
    Landmark("muhammad_ali_mosque", "STATE_LOWER_EGYPT", None, "religious", "faith", ("faith_sunni", "faith"), 10,
             False, year=1836),
    Landmark("nelsons_column", "STATE_HOME_COUNTIES", None, "war_memorial", "column", ("generic", "column"), 5, False,
             year=1840),
    Landmark("washington_monument", "STATE_DISTRICT_OF_COLUMBIA", None, "republic", "obelisk", ("generic", "obelisk"),
             10, False, year=1848),
)
PLACED_LANDMARKS = tuple(lm for lm in LANDMARKS if lm.placed)
LANDMARK_CODE_BASE = 1_000_000

# The year each historical monument was finished, negative before Christ
# (owner, 2026-10-19): its grandeur at the 1836 rate is split into starting
# grandeur and the years since, as if it had aged in the game from then
# (gm_set_historical_grandeur). Every row placed at the start, every trophy
# abroad in 1836 and every dig; none for a historical opportunity's, which the
# game builds.
BUILT = {
    # Standing in 1836.
    "arc_de_triomphe": 1836, "alexander_column": 1834, "brandenburg_gate": 1791,
    "washington_monument_baltimore": 1829, "la_scala": 1778, "teatro_di_san_carlo": 1817, "jantar_mantar": 1734,
    "shalimar_gardens": 1642, "jardim_botanico": 1808, "stelae_of_aksum": 330, "liberty_column": 1797,
    "lion_monument": 1821, "temple_of_heaven": 1420, "topkapi_palace": 1478, "golestan_palace": 1779,
    "basilica_of_superga": 1731, "tomb_of_william_the_silent": 1623, "cenotaph_of_maximilian": 1584,
    "arco_de_santa_maria": 1553, "statue_of_louis_xiv": 1825, "lion_of_saint_mark": 1293, "sans_souci_palace": 1813,
    "nikko_toshogu": 1636, "parthenon": -432, "obelisks_of_karnak": -1457, "royal_palace_of_benin": 1440,
    "royal_palace_of_kumasi": 1822, "bukgwan_victory_stele": 1709, "imperial_city_of_hue": 1833, "persepolis": -500,
    "red_fort": 1648, "great_zimbabwe": 1300, "royal_palaces_of_abomey": 1645, "klungkung_palace": 1686,
    "uffizi_gallery": 1581, "capitoline_museums": 1734, "bodrum_castle": 1437, "temples_of_baalbek": 150,
    "palmyra": 32, "xanthos": -390, "mesha_stele": -840, "arch_of_ctesiphon": 540,
    # Trophies abroad in 1836 with no standing monument of their own.
    "rosetta_stone": -196, "temple_of_dendera": -50, "luxor_obelisk": -1250, "venus_de_milo": -130,
    "piraeus_lion": -360, "horses_of_saint_mark": 200, "tipus_tiger": 1795, "baba_merzoug": 1542,
    "royal_palace_of_kandy": 1600,
    # Buried until the game.
    "nineveh_library": -650, "winged_victory_of_samothrace": -190, "vindolanda_tablets": 100,
    "troy_hisarlik": -1250, "mycenae_grave_circle": -1600, "pergamon_altar": -165, "deir_el_bahari_cache": -935,
    "ishtar_gate_babylon": -575, "palace_of_knossos": -1700, "antikythera_mechanism": -100, "oseberg_ship": 834,
    "machu_picchu": 1450, "bust_of_nefertiti": -1345, "mohenjo_daro": -2500, "tomb_of_tutankhamun": -1323,
    "royal_cemetery_at_ur": -2600, "sanxingdui_pits": -1200, "sutton_hoo": 625, "lascaux_caves": -15000,
    "nag_hammadi_library": 350, "dead_sea_scrolls": -100, "tomb_of_pakal": 683, "mawangdui_tombs": -168,
    "terracotta_army": -210, "tomb_of_philip_ii": -336, "tomb_of_marquis_yi": -433, "royal_tombs_of_sipan": 250,
    "otzi_the_iceman": -3300, "caral_supe": -2600, "gobekli_tepe": -9500, "olympia": -456, "delphi": -330,
    "sidon_necropolis": -330, "villa_of_the_papyri": -50, "tomb_of_alexander": -320, "pompeii": 79,
}


def historical_split(levels, built, year=1836):
    """gm_set_historical_grandeur, transcribed: (starting grandeur, age)."""
    total = levels * 5
    start = total / max(min(year - built, 100) * 2 / 100 + 1, 1)
    return start, max(total - start, 0)


def ceremony_options():
    event = raw_block_at(read(EVENTS), r"(?m)^monument_events\.2\s*=\s*\{")
    out = {}
    for m in re.finditer(r"option\s*=\s*\{", event):
        body = _match_brace(event, m.end())
        name = re.search(r"name = monument_events\.2\.(\w+)", body)
        out[name.group(1)] = body
    return out


def wrapper_call(d):
    if d.kind == "regime":
        return f"gm_state_dedicate_regime = {{ KEY = {d.key} }}"
    if d.kind == "ruler":
        return "gm_state_dedicate_leader = yes"
    if d.kind == "faith":
        return "gm_state_dedicate_faith = yes"
    axis = "heritage" if d.key in HERITAGE_SKINNED else f"building_{d.key}"
    return f"gm_state_dedicate_timeless = {{ KEY = {d.key} AXIS = {axis} }}"


class CeremonyTests(unittest.TestCase):
    def test_every_dedication_has_its_option(self):
        options = ceremony_options()
        # "opp": the open opportunity's dedication, first (usability §3).
        # "sig_<special>": a held special (signatures spec §5.3).
        self.assertEqual(set(options), set(CEREMONY_OPTION.values()) | {"a", "opp", "keep"}
                         | {f"sig_{s.key}" for s in SIGNATURES if s.kind == "special"})
        for d in DEDICATIONS:
            body = squash(strip_comments(options[CEREMONY_OPTION[d.key]]))
            self.assertIn(f"text = monument_events.2.{CEREMONY_OPTION[d.key]}.tt {wrapper_call(d)}", body, d.key)
            if d.key in CEREMONY_GATE:
                self.assertIn(CEREMONY_GATE[d.key], body, d.key)
            if d.key in TECH_GATES:
                self.assertIn(f"has_technology_researched = {TECH_GATES[d.key]}", body, d.key)

    def test_unavailable_dedications_show_greyed(self):
        options = ceremony_options()
        gated = 0
        for d in DEDICATIONS:
            body = squash(strip_comments(options[CEREMONY_OPTION[d.key]]))
            if "trigger = {" in body.split("ai_chance")[0]:
                gated += 1
                self.assertIn("show_as_unavailable = { always = yes }", body, d.key)
        self.assertEqual(gated, 10, "the ten gated dedications (spec 2026-10-11 §4.1)")
        self.assertNotIn("show_as_unavailable", squash(options["a"]), "leaving it undedicated is always open")

    def test_leave_undedicated_clears_the_pending_flag(self):
        body = ceremony_options()["a"]
        self.assertNotIn("REVIEWED", body)
        self.assertIn("gm_state_ceremony_not_yet = yes", squash(body))
        self.assertIn("gm_remove_state_var = { VAR = gm_ceremony_pending }",
                      squash(block(read(EFFECTS), "gm_state_ceremony_not_yet")))

    def test_tooltips_hold_no_hand_kept_numbers(self):
        L = loc()
        keys = [f"monument_events.2.{o}.tt" for o in list(CEREMONY_OPTION.values()) + ["a"]]
        keys.append("monument_events.2.common_tt")
        for key in keys:
            self.assertIn(key, L)
            self.assertNotRegex(L[key], r"#G [+-]?\d", f"{key}: numbers come from gm_step_* script values")
        for o in CEREMONY_OPTION.values():
            self.assertIn("$monument_events.2.common_tt$", L[f"monument_events.2.{o}.tt"])

    def test_wrappers(self):
        e = read(EFFECTS)
        base = squash(block(e, "gm_state_dedicate"))
        self.assertIn("production_method = pm_monument_$KEY$", base)
        self.assertIn("set_variable = gm_seen", base)
        self.assertIn("set_variable = { name = gm_raised_by value = owner }", squash(block(e, "gm_state_dedicate_regime")))
        leader = squash(block(e, "gm_state_dedicate_leader"))
        self.assertIn("gm_state_record_honoree = yes", leader)
        self.assertIn("gm_state_offer_skins = { AXIS = heritage }", leader)
        faith = squash(block(e, "gm_state_dedicate_faith"))
        self.assertIn("gm_state_record_faith = yes", faith)
        self.assertIn("gm_state_offer_skins = { AXIS = faith }", faith)
        self.assertNotIn("gm_raised_by", squash(block(e, "gm_state_dedicate_timeless")))
        offer = squash(block(e, "gm_state_offer_skins"))
        self.assertIn("gm_state_offer_skins_$AXIS$ = yes", offer)
        self.assertIn("trigger_event = { id = monument_events.20 }", offer)
        faith_offer = squash(block(e, "gm_state_offer_skins_faith"))
        self.assertIn("gm_state_offer_skins_heritage = yes", faith_offer, "mod religions fall back to heritage")
        # The skin choice is for players only; the AI keeps the most specific
        # skin gm_state_default_faith_skin / gm_state_default_heritage_skin
        # already set, unasked (plan-mandated fix, Task 7 fix round 1).
        self.assertIn("limit = { owner = { is_ai = no } } set_variable = { name = gm_skin_axis value = flag:faith } "
                      "trigger_event = { id = monument_events.11 popup = yes }", faith_offer)
        heritage_offer = squash(block(e, "gm_state_offer_skins_heritage"))
        self.assertIn("owner = { is_ai = no } } set_variable = { name = gm_skin_axis value = flag:heritage } "
                      "trigger_event = { id = monument_events.11 popup = yes }", heritage_offer)


class SkinTests(unittest.TestCase):
    def setUp(self):
        self.event = raw_block_at(read(EVENTS), r"(?m)^monument_events\.11\s*=\s*\{")
        self.assertIsNotNone(self.event)

    def _options(self):
        out = []
        for m in re.finditer(r"option\s*=\s*\{", self.event):
            body = squash(strip_comments(_match_brace(self.event, m.end())))
            name = re.search(r"name = monument_events\.11\.(\w+)", body).group(1)
            out.append((name, body))
        return out

    def test_an_option_per_skin_generic_last(self):
        options = self._options()
        names = [n for n, _ in options]
        # I3: heritage_hebrew comes after heritage_arabic, heritage_geez and
        # heritage_aramaic (the last of the single-language matches), so an
        # expired event (no default_option) takes one of those over the
        # group-level Hebrew match for a Semitic-language country.
        heritages_in_option_order = tuple(h for h in HERITAGES if h != "hebrew") + ("hebrew",)
        building = [f"building_{k}_{h}" for k, hs in BUILDING_SKINS.items() for h in hs]
        expected = ([f"faith_{f}" for f in FAITHS]
                    + [f"heritage_{h}" for h in heritages_in_option_order] + building + ["generic"])
        self.assertEqual(names, expected)
        self.assertLess(names.index("heritage_hebrew"), names.index("generic"))
        for h in ("arabic", "geez", "aramaic"):
            self.assertLess(names.index(f"heritage_{h}"), names.index("heritage_hebrew"))
        bodies = dict(options)
        for f in FAITHS:
            self.assertIn(f"highlighted_option = yes trigger = {{ hidden_trigger = {{ var:gm_skin_axis = flag:faith }} "
                          f"custom_tooltip = {{ text = gm_skin_reason_faith_tt owner = {{ religion = rel:{f} }} }} }}",
                          bodies[f"faith_{f}"])
            self.assertIn(f"gm_state_choose_skin = {{ SKIN = faith_{f} }}", bodies[f"faith_{f}"])
        for h in HERITAGES:
            skin = f"faith_{HERITAGE_AS_FAITH[h]}" if h in HERITAGE_AS_FAITH else f"heritage_{h}"
            self.assertIn(f"highlighted_option = yes trigger = {{ hidden_trigger = {{ var:gm_skin_axis = flag:heritage }} "
                          f"custom_tooltip = {{ text = gm_skin_reason_{h}_tt owner = {{ te_heritage_{h} = yes }} }} }}",
                          bodies[f"heritage_{h}"])
            self.assertIn(f"gm_state_choose_skin = {{ SKIN = {skin} }}", bodies[f"heritage_{h}"])
        self.assertNotIn("default_option", squash(strip_comments(self.event)))
        self.assertNotIn("highlighted_option", bodies["generic"])
        L = loc()
        self.assertEqual(L["monument_events.11.t"], "A Style for the Monument")
        self.assertIn("style", L["gm_skin_choice_tt"])

    def test_building_styles(self):
        e = read(EFFECTS)
        bodies = dict(self._options())
        L = loc()
        for key, heritages in BUILDING_SKINS.items():
            self.assertEqual(list(heritages), [h for h in HERITAGES if h in heritages], key)
            offer = squash(block(e, f"gm_state_offer_skins_building_{key}"))
            if not heritages:
                # The Exhibition Hall offers no style: its axis is none in effect.
                self.assertEqual(offer, "gm_state_offer_skins_none = yes", key)
                continue
            self.assertEqual(offer, f"gm_state_offer_building_skins = {{ KEY = {key} }}")
            default = squash(block(e, f"gm_state_default_building_skin_{key}"))
            # Reverse partition order: a later try wins, so the most specific is last.
            self.assertEqual(default, " ".join(f"gm_state_try_heritage_skin = {{ H = {h} }}"
                                               for h in reversed(heritages)), key)
            for h in heritages:
                body = bodies[f"building_{key}_{h}"]
                self.assertIn("highlighted_option = yes", body)
                # The axis names the building: no production-method read-back
                # (Task 3 review), so the option can't vanish if the engine
                # hasn't applied the dedication's PM yet.
                self.assertIn(f"hidden_trigger = {{ var:gm_skin_axis = flag:building_{key} }} "
                              f"custom_tooltip = {{ text = gm_skin_reason_{h}_tt owner = {{ te_heritage_{h} = yes }} }}", body)
                self.assertNotIn("gm_state_has_pm", body)
                self.assertIn(f"gm_state_choose_building_skin = {{ SKIN = heritage_{h} }}", body)
                self.assertIn(f"monument_events.11.building_{key}_{h}", L)
        shared = squash(block(e, "gm_state_offer_building_skins"))
        self.assertIn("gm_state_default_building_skin_$KEY$ = yes", shared)
        self.assertIn("set_variable = { name = gm_skin_axis value = flag:building_$KEY$ } "
                      "trigger_event = { id = monument_events.11 popup = yes }", shared)
        choose = squash(block(e, "gm_state_choose_building_skin"))
        self.assertIn("text = gm_skin_choice_building_tt", choose)
        self.assertIn("gm_state_unveil = yes", choose)
        self.assertIn("gm_skin_choice_building_tt", L)

    def test_a_building_keeps_its_name_in_any_style(self):
        names = squash(block(read(CUSTOM_LOC), "gm_skin_name"))
        # After the landmarks' branches (phase 4 §4), which come first of all.
        first = names.split("text = {")[1 + len(LANDMARKS):6 + len(LANDMARKS)]
        for (key, form), branch in zip(BUILDING_FORMS.items(), first):
            self.assertIn(f"var:gm_form = flag:{form} }} localization_key = pm_monument_{key}", branch)

    def test_skins_read_only_own_identity(self):
        body = strip_comments(self.event)
        self.assertNotRegex(body, r"\bculture\s*=|\bhas_discrimination_trait|any_scope_pop")

    def test_skin_loc_and_names(self):
        L = loc()
        for name, _ in self._options():
            self.assertIn(f"monument_events.11.{name}", L)
        for key in ("t", "d", "f"):
            self.assertIn(f"monument_events.11.{key}", L)
        names = squash(block(read(CUSTOM_LOC), "gm_skin_name"))
        for skin in SKINS:
            self.assertIn(f"gm_skin_{skin}", L, skin)
            if skin != "generic":
                self.assertIn(f"var:gm_skin = flag:{skin} }} localization_key = gm_skin_{skin}", names)
        self.assertTrue(names.endswith("text = { localization_key = gm_skin_generic }"))

    def test_no_landmark_in_the_style_choice(self):
        # Phase 4 §1: a landmark is placed, never chosen; its skin is locked.
        self.assertFalse([n for n, _ in self._options() if n.startswith("landmark_")])
        self.assertNotIn("landmark_", squash(strip_comments(self.event)))

    def test_inscription(self):
        body = squash(block(read(CUSTOM_LOC), "gm_inscription"))
        L = loc()
        for h in HERITAGE_SKINS:
            self.assertIn(f"var:gm_skin = flag:heritage_{h} owner = {{ gm_country_has_revived = {{ LANG = {h} }} }}", body)
        for f, lang in INSCRIPTION_FAITHS.items():
            self.assertIn(f"var:gm_skin = flag:faith_{f} owner = {{ gm_country_has_revived = {{ LANG = {lang} }} }}", body)
        for h in HERITAGES:
            self.assertIn(f"gm_inscription_{h}", L)
        self.assertIn("gm_inscription_none", L)
        revived = squash(block(read(TRIGGERS), "gm_country_has_revived"))
        self.assertIn("has_amendment = amendment_type:amendment_langreform_revived_$LANG$", revived)


# ---- Task 8: vanity backlash ---------------------------------------------------------

class PriceTests(unittest.TestCase):
    """v2 §1: a level costs a tenth of v1's; the doubling curve, not the price, stops spam."""

    def test_a_level_costs_1000(self):
        values = strip_comments(read("common/script_values/extra_script_values.txt"))
        self.assertRegex(values, r"(?m)^construction_cost_grand_monument = 1000\s*$")
        self.assertIn("required_construction = construction_cost_grand_monument", read(BUILDING))


class VanityTests(unittest.TestCase):
    def test_level_finished_hook(self):
        ev = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.1\s*=\s*\{")))
        self.assertIn("type = building_event hidden = yes", ev)
        # Vanity is the construction site's monthly count's (SiteBuildingTests).
        self.assertNotIn("gm_state_vanity_backlash", ev)
        # A player's site waits for its Dedicate button (owner, 2026-10-18);
        # the AI's ceremony asks once nothing more is queued on its site.
        self.assertIn("gm_state_ai_dedicates_now = yes NOT = { has_variable = gm_ceremony_pending } } "
                      "gm_state_start_ceremony = yes", ev)
        self.assertIn("owner = { trigger_event = { id = monument_events.20 } }", ev)
        self.assertNotIn("add_modifier", ev, "ROOT is the building here: no multiplier modifiers")

    def test_backlash(self):
        body = squash(block(read(EFFECTS), "gm_state_vanity_backlash_for"))
        self.assertIn("add_radicals_in_state = { value = 0.005 }", body)
        self.assertIn("change_variable = { name = gm_vanity_ledger add = $AMOUNT$ }", body)
        self.assertIn("post_notification = gm_vanity_backlash_notice", body)

    def test_notice(self):
        msg = squash(block(read(MESSAGES), "gm_vanity_backlash_notice"))
        self.assertIn("type = country", msg)
        self.assertIn("notification_type = toast", msg)
        L = loc()
        self.assertIn("notification_gm_vanity_backlash_notice_name", L)
        self.assertIn("notification_gm_vanity_backlash_notice_desc", L)


# ---- Task 9: the journal entry's widgets and buttons ---------------------------------

class WidgetTests(unittest.TestCase):
    def setUp(self):
        self.gui = read(WIDGET)

    # The three roots of the style-guide pass (2026-09-29): the overview above
    # the status description, the live sections below it, How Grand Monuments
    # Work at the foot (test_grand_monuments_layout.py checks their contents).
    ROOTS = (("widget_je_gm_overview", "custom_widget_container_1"),
             ("widget_je_gm_status", "custom_widget_container_2"),
             ("widget_je_gm_reference", "custom_widget_container_3"))

    def test_mounted(self):
        je = squash(read(JE))
        for name, container in self.ROOTS:
            self.assertIn(f'gui = "gui/journal_entry_widgets/grand_monuments_widget.gui" name = "{name}" '
                          f'container = "{container}"', je)
            self.assertIn(f'name = "{name}"', self.gui)

    def test_roots_gated_and_rows_from_the_list(self):
        g = squash(strip_comments(self.gui))
        # Every named root carries the gate itself, not only the composer it wraps.
        for name, _ in self.ROOTS:
            self.assertIn(f'name = "{name}" visible = "[JournalEntry.IsActive]"', g, name)
        self.assertIn('datamodel = "[JournalEntry.GetCountry.MakeScope.GetList(\'gm_states\')]"', g)
        self.assertIn('gm_monument_row = { datacontext = "[Scope.GetState]" visible = "[EqualTo_CFixedPoint( '
                      'State.MakeScope.ScriptValue(\'gm_state_disp_listed\'), \'(CFixedPoint)1\' )]" }', g)

    def _shown_text(self):
        """The widget and the loc of every key it renders, followed through
        $splices$ and SelectLocalization: the national values moved from the
        .gui into their rows' value and tooltip keys (style pass 2026-09-29)."""
        L = loc()
        text, todo, seen = self.gui, set(re.findall(r'(?:text|tooltip) = "([a-z][\w.]*)"', self.gui)), set()
        todo |= set(re.findall(r"'(gm_[a-z]\w*)'", self.gui)) & set(L)
        while todo:
            key = todo.pop()
            if key in seen or key not in L:
                continue
            seen.add(key)
            text += "\n" + L[key]
            todo |= set(re.findall(r"\$([a-z]\w*)\$", L[key])) | (set(re.findall(r"'([a-z]\w*)'", L[key])) & set(L))
        return text

    def test_national_lines_read_guarded_displays(self):
        values = read(VALUES) + "\n" + read(SIG_VALUES)
        shown_text = self._shown_text()
        for display in re.findall(r"ScriptValue\('(gm_display_\w+)'\)", shown_text):
            body = squash(block(values, display))
            self.assertIsNotNone(block(values, display), display)
            self.assertIn("if = { limit = { has_variable =", body, display)
        shown = set(re.findall(r"ScriptValue\('(gm_display_\w+)'\)", shown_text))
        for key in ["prestige", "legitimacy", "culture", "teardown", "vanity"] + list(NATIONAL):
            self.assertIn(f"gm_display_{key}", shown)
        for ig in IGS:
            self.assertIn(f"gm_display_ig_{ig}", shown)

    def test_buttons(self):
        g = squash(strip_comments(self.gui))
        self.assertIn("visible = \"[EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_status_code'), '(CFixedPoint)4' )]\"", g)
        for choice in ("tear_down", "rededicate", "preserve"):
            self.assertIn(f"datacontext = \"[GetScriptedGui('gm_{choice}_sgui')]\"", g)
        self.assertIn("AddScope( 'gm_state', State.MakeScope )", g)
        sguis = read(SGUIS)
        for choice in ("tear_down", "rededicate", "preserve"):
            body = squash(block(sguis, f"gm_{choice}_sgui"))
            self.assertIn("saved_scopes = { gm_state }", body)
            self.assertIn("exists = scope:gm_state scope:gm_state = { owner = root", body)
            self.assertIn("gm_state_is_contested = yes", body)
            self.assertIn(f"scope:gm_state = {{ gm_state_choose_{choice} = yes }}", body)
            self.assertIn("hidden_effect = { gm_country_refresh = yes }", body)
            self.assertIn("ai_is_valid = { always = no }", body)
        self.assertIn("is_shown = { gm_country_hard_times = yes }", squash(block(sguis, "gm_hard_times_sgui")))

    def test_every_gui_loc_key_exists(self):
        L = loc()
        for key in set(re.findall(r'(?:text|tooltip) = "([a-z][\w.]*)"', self.gui)):
            self.assertIn(key, L, key)


# ---- The two loc fixes from Task 5's review (controller ruling) ----------------------

class LocFixTests(unittest.TestCase):
    def test_reason_does_not_imply_faith_lends_legitimacy(self):
        L = loc()
        self.assertNotIn("faith still stands", L["je_grand_monuments_reason"])

    def test_no_status_line_repeats_the_overview(self):
        # The status lines ("Grand Monuments: 3, contested: 1") repeated the
        # overview's counts and were removed (owner, play-test round 2,
        # 2026-09-29); their wording fix is moot. The counts they showed are
        # the overview's cells (test_grand_monuments_layout.py).
        self.assertIsNone(block(read(JE), "status_desc"))
        L = loc()
        for key in ("je_grand_monuments_status", "je_grand_monuments_status_contested"):
            self.assertNotIn(key, L)
        self.assertIn("ScriptValue('gm_disp_count_contested')", read(WIDGET))

    def test_culture_line_has_no_cap(self):
        # Cultural pull from monuments had a +5 cap until 2026-10-16, when the
        # owner swapped it for diminishing returns alone (gm_set_steps_open).
        # Nothing on the culture row may still stop at a cap: the value, the
        # next step, the bar and the tooltip.
        values = read(VALUES)
        self.assertNotIn("max =", squash(block(values, "gm_display_culture")))
        self.assertEqual("value = 0 if = { limit = { has_variable = gm_n_culture } value = var:gm_n_culture }",
                         squash(block(values, "gm_display_n_culture")))
        self.assertNotIn("gm_s_culture", squash(block(values, "gm_disp_frac_culture")))
        L = loc()
        self.assertNotIn("gm_je_tt_culture_cap", L)
        self.assertNotIn("gm_je_tt_culture_next", L)
        tt = L["gm_je_tt_culture"]
        self.assertIn("Next step at #v [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_n_culture')|0]#!", tt)
        self.assertNotIn("at most", tt)
        self.assertNotIn("+5", L["gm_je_how_grandeur"])
        self.assertIn('tooltip = "gm_je_tt_culture"', read(WIDGET))


# ---- Task 10: flavour events ---------------------------------------------------------

class FlavourTests(unittest.TestCase):
    def test_dispatch(self):
        body = squash(block(read(ON_ACTIONS), "monument_events_on_action"))
        self.assertIn("trigger = { gm_system_enabled = yes "
                      "NOT = { gm_policy_is = { P = mothballed STANDARD = no } } }", body)
        # Every monument of the dedication, those beside another too (ageing
        # spec 2026-10-16 §5; AnniversaryAgeTests).
        for d in DEDICATIONS:
            self.assertIn(f"gm_country_holds_anniversary = {{ KEY = {d.key} }} }} "
                          f"trigger_event = {{ id = monument_events.{d.event} }}", body)

    def test_only_a_fitting_landmark_holds_anniversaries(self):
        self.assertEqual(squash(block(read(TRIGGERS), "gm_state_holds_anniversary")),
                         "gm_state_status_fits = yes gm_state_has_pm = { PM = $PM$ } "
                         "gm_state_primary_grandeur >= 3")

    def test_events(self):
        text, L = read(EVENTS), loc()
        for d in DEDICATIONS:
            ev = raw_block_at(text, rf"(?m)^monument_events\.{d.event}\s*=\s*\{{")
            self.assertIsNotNone(ev, d.event)
            se = strip_comments(ev)
            s = squash(se)
            self.assertIn(f"gm_country_holds_anniversary = {{ KEY = {d.key} }}", s)
            self.assertIn(f"gm_ann_pick = {{ KEY = {d.key} }}", s)
            self.assertEqual(s.count("default_option = yes"), 1, d.event)
            options = [squash(_match_brace(se, m.end())) for m in re.finditer(r"option\s*=\s*\{", se)]
            self.assertEqual(len(options), 2, d.event)
            for o in options:
                effects = re.sub(r"name = \S+|default_option = yes|ai_chance = \{ base = \d+ \}", "", o).strip()
                self.assertTrue(effects, f"{d.event}: an option with no effect")
                self.assertNotRegex(o, r"add_treasury = (?!gm_event_(cost|income)\b)",
                                    "money moves only through gm_event_cost / gm_event_income")
            for k in ("t", "d", "f", "a", "b"):
                self.assertIn(f"monument_events.{d.event}.{k}", L)
            self.assertNotEqual(L[f"monument_events.{d.event}.a"], "A fine thing to have built")

    def test_event_modifiers_are_all_positive(self):
        good_when_negative = {"state_turmoil_effects_mult", "country_war_support_casualties_mult"}
        seen = 0
        for name, body in top_level_blocks(read(MODIFIERS)):
            if not name.startswith("gm_evt_"):
                continue
            seen += 1
            for field, value in re.findall(r"(?m)^\s*(\w+)\s*=\s*(-?[\d.]+)\s*$", body):
                v = float(value)
                self.assertTrue(v < 0 if field in good_when_negative else v > 0, f"{name}.{field}")
        self.assertEqual(seen, 22)


# ---- Task 11: the debug event ---------------------------------------------------------

class DebugTests(unittest.TestCase):
    def test_debug_event(self):
        text = read(DEBUG_EVENTS)
        self.assertIn("namespace = te_debug_monuments", text)
        self.assertRegex(text, r"(?m)^te_debug_monuments\.1 = \{ # REVIEWED \d{4}-\d{2}-\d{2}: console-only")
        body = squash(strip_comments(raw_block_at(text, r"(?m)^te_debug_monuments\.1\s*=\s*\{")))
        for s in ("create_building = { building = building_grand_monument_site level = 20 }",
                  "gm_country_monthly = yes", "gm_state_contest = yes",
                  "gm_state_vanity_backlash = yes", "gm_debug_log = yes"):
            self.assertIn(s, body)
        # Option c (Minor 1): gm_country_refresh would re-run gm_check_contests
        # and immediately lift the just-forced contest, since the monument
        # still fits. gm_notify_new_contests fires monument_events.16 (or
        # clears gm_new_contest for the AI) without re-deriving contests, so
        # the forced contest sticks.
        self.assertIn("gm_state_contest = yes } gm_notify_new_contests = yes", body)
        self.assertEqual(body.count("gm_country_refresh = yes"), 1,
                          "only option d (vanity backlash) should still refresh")
        L = loc()
        for k in ("t", "desc", "flavor", "a", "b", "c", "d", "e"):
            self.assertIn(f"te_debug_monuments.1.{k}", L)

    def test_picture_sweep(self):
        nxt = squash(block(read(PICTURE_EFFECTS), "gm_debug_next_picture"))
        codes = sorted(PICTURES)
        for a, b in zip(codes, codes[1:] + codes[:1]):
            self.assertIn(f"var:gm_picture_code = {a} }} set_variable = {{ name = gm_picture_code value = {b} }}", nxt)
        text = read(DEBUG_EVENTS)
        self.assertRegex(text, r"(?m)^te_debug_monuments\.4 = \{ # REVIEWED \d{4}-\d{2}-\d{2}: console-only")
        ev = squash(raw_block_at(text, r"(?m)^te_debug_monuments\.4\s*=\s*\{"))
        self.assertIn("gm_debug_next_picture = yes", ev)
        self.assertIn("gm_state_update_picture = yes", ev)
        L = loc()
        for k in ("t", "desc", "flavor", "a", "b", "c"):
            self.assertIn(f"te_debug_monuments.4.{k}", L)

    def test_monthly_log_for_players(self):
        monthly = squash(block(read(EFFECTS), "gm_country_monthly"))
        self.assertIn("limit = { is_ai = no } gm_debug_log = yes", monthly)
        log = block(read(EFFECTS), "gm_debug_log")
        self.assertIn('debug_log = "TE_MONUMENTS:', log)
        self.assertNotIn(".MakeScope", log, "debug_log's working form is [SCOPE.ScriptValue('x')|N]")



# ==== Opportunities (docs/superpowers/archive/specs/2026-10-12-grand-monument-opportunities-design.md; v2 §2's commissions reworked) ====
COM_TRIGGERS = "common/scripted_triggers/gm_commission_triggers.txt"
COM_EFFECTS = "common/scripted_effects/gm_commission_effects.txt"
COM_VALUES = "common/script_values/gm_commission_values.txt"
NAME_TRIGGERS = "common/scripted_triggers/gm_name_triggers.txt"
NAME_EFFECTS = "common/scripted_effects/gm_name_effects.txt"
HISTORY = "common/history/extra_history.txt"

Source = namedtuple("Source", "key begins fixed boon_field boon_value boon_shown special", defaults=(None,))
# One row per moment (docs/superpowers/archive/specs/2026-10-12-grand-monument-
# opportunities-design.md §1): what it asks for, how the monument would be
# named, and its boon. A fixed source names the capital (gm_com_fix_to_capital),
# falling back to anywhere when the capital holds a monument of another
# dedication. A begin is the gm_com_begin call less its SOURCE; "$KEY$" is the
# regime's or the technology's dedication. boon_shown is how the boon's
# effect loc prints the value. special: the unique dedication completing one
# gives the monument that completed it (signatures spec 2026-10-16 §5.4;
# SIGNATURES). A historical opportunity (§6) has no boon and is
# HISTORICAL_OPPORTUNITIES', not a row here.
COMMISSION_SOURCES = (
    Source("reign", ("DEDICATION = crown NAMESAKE = ruler FORM = column",
                     "DEDICATION = leader NAMESAKE = ruler FORM = statue"), False,
           "country_authority_mult", 0.1, "+10%"),
    Source("regime", ("DEDICATION = $KEY$ NAMESAKE = year FORM = column",), False,
           "country_loyalists_from_legitimacy_mult", 0.25, "+25%"),
    Source("great_power", ("DEDICATION = civic NAMESAKE = honours FORM = column",), True,
           "country_influence_mult", 0.1, "+10%", "concert_of_nations"),
    Source("victory", ("DEDICATION = war_memorial NAMESAKE = occasion FORM = arch",), False,
           "country_prestige_mult", 0.1, "+10%", "to_victory"),
    Source("defeat", ("DEDICATION = war_memorial NAMESAKE = occasion FORM = hall",), False,
           "country_radicals_from_legitimacy_mult", -0.25, "−25%", "unknown_soldier"),
    Source("centenary", ("DEDICATION = civic NAMESAKE = occasion FORM = column",), True,
           "state_assimilation_mult", 0.25, "+25%"),
    Source("ruler_death", ("DEDICATION = civic NAMESAKE = ruler FORM = mausoleum",), True,
           "country_legitimacy_base_add", 5, "+5"),
    Source("space", ("DEDICATION = civic NAMESAKE = occasion FORM = obelisk",), True,
           "country_weekly_innovation_mult", 0.1, "+10%", "conquerors_of_space"),
    Source("faith", ("DEDICATION = religious NAMESAKE = honours FORM = default",), False,
           "state_conversion_mult", 0.25, "+25%"),
    Source("tech_artistic", (), False, "building_art_academy_throughput_add", 0.1, "+10%"),
    Source("tech_scientific", (), False, "country_tech_spread_mult", 0.1, "+10%"),
    Source("tech_industrial", (), False, "building_group_bg_manufacturing_throughput_add", 0.05, "+5%"),
    Source("tech_athletic", (), False, "state_mortality_mult", -0.05, "−5%", "olympic"),
    Source("tech_naturalist", (), False, "state_pollution_reduction_health_mult", -0.25, "−25%"),
)
SOURCE_KEYS = tuple(s.key for s in COMMISSION_SOURCES)
# The technology moments (§1): each civic-progress dedication's own gate, but
# the Gardens', which Romanticism already spends on the Opera House.
TECH_MOMENTS = {"artistic": "romanticism", "scientific": "empiricism", "industrial": "marketing_research",
                "athletic": "television_broadcasting", "naturalist": "environmental_movement"}
# The regime source's asking groups: each regime dedication's approving IG.
REGIME_IG = {"crown": "landowners", "republic": "intelligentsia", "revolution": "trade_unions"}
# What completing one gives (§3): the gift in levels, the asking group's
# ledger, the boon's months.
REWARDS = {"gift": 5, "ig": 15, "boon_months": 120}
# The space race's firsts that bring an opportunity (§1): every milestone that
# records a world first (space_race_effects.txt) but the suborbital hop and the
# first probe, which lead up to orbit.
SPACE_FIRSTS = ("orbital", "moon_landing", "moon_base", "mars_landing", "interstellar_probe")
# The world pass's trackers, in priority order (§1).
WORLD_PASS = ("gm_com_first_sight", "gm_com_init_founded", "gm_com_track_regime", "gm_com_track_ruler",
              "gm_com_track_great_power", "gm_com_track_faith", "gm_com_track_space", "gm_com_track_centenary",
              "gm_com_track_tech")
FOUNDING_YEARS = {"USA": 1776, "HAI": 1804, "CLM": 1810, "PRG": 1811, "VNZ": 1811, "ARG": 1816, "CHL": 1818,
                  "MEX": 1821, "GRE": 1821, "BRZ": 1822, "BOL": 1825, "URU": 1825, "BEL": 1830, "ECU": 1830}


def _effect_containing(text, needle):
    """The top-level scripted effect whose body contains needle (squashed)."""
    for name, body in top_level_blocks(text):
        if needle in squash(body):
            return name, squash(body)
    return None, ""


class CommissionSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = read(COM_EFFECTS)
        cls.events = read(EVENTS)

    def test_each_source_asks_for_its_table_row(self):
        for src in COMMISSION_SOURCES:
            for begin in src.begins:
                call = f"gm_com_begin = {{ SOURCE = {src.key} {begin} }}"
                name, body = _effect_containing(self.e, call)
                self.assertIsNotNone(name, call)
                self.assertEqual("gm_com_fix_to_capital = yes" in body, src.fixed, src.key)
                self.assertIn("gm_com_send_offer = yes", body, src.key)

    def test_the_technology_moments(self):
        """Each civic-progress dedication has its technology's moment, asked
        for by its approving group, and first sight sees each."""
        self.assertEqual(set(TECH_MOMENTS), set(TECH_GATES))
        for key, tech in TECH_MOMENTS.items():
            if key != "naturalist":
                self.assertEqual(tech, TECH_GATES[key], key)
        track = squash(block(self.e, "gm_com_track_tech"))
        listed = re.findall(r"gm_com_track_tech_one = \{ KEY = (\w+) TECH = (\w+) IG = (\w+) \}", track)
        self.assertEqual({k: t for k, t, _ in listed}, TECH_MOMENTS)
        for key, _, ig in listed:
            self.assertEqual(ig, BY_KEY[key].approve, key)
            self.assertIn(f"tech_{key}", SOURCE_KEYS)
        one = squash(block(self.e, "gm_com_track_tech_one"))
        self.assertIn("gm_com_can_offer = yes gm_country_can_raise_$KEY$ = yes", one)
        self.assertIn("gm_com_begin = { SOURCE = tech_$KEY$ DEDICATION = $KEY$ NAMESAKE = city FORM = default }", one)
        self.assertIn("set_variable = gm_com_seen_tech_$KEY$", one)
        sight = squash(block(self.e, "gm_com_first_sight"))
        for key, tech in TECH_MOMENTS.items():
            self.assertIn(f"gm_com_see_tech_if_known = {{ KEY = {key} TECH = {tech} }}", sight)

    def test_each_source_has_its_offer_text(self):
        ev = squash(raw_block_at(self.events, r"(?m)^monument_events\.21\s*=\s*\{"))
        L = loc()
        for src in COMMISSION_SOURCES:
            self.assertIn(f"var:gm_com_source = flag:{src.key}", ev, src.key)
            self.assertIn(f"monument_events.21.d_{src.key}", L, src.key)
            if src.fixed:
                self.assertIn(f"monument_events.21.d_{src.key}_anywhere", L, src.key)
        for key in ("t", "f", "a", "b"):
            self.assertIn(f"monument_events.21.{key}", L)
        # The title names the moment: every source has an occasion branch.
        self.assertIn("GetCustom('gm_com_occasion_name')", L["monument_events.21.t"])
        occ = squash(block(read(CUSTOM_LOC), "gm_com_occasion_name"))
        for src in COMMISSION_SOURCES:
            self.assertIn(f"var:gm_com_source = flag:{src.key}", occ, src.key)
        for key, tech in TECH_MOMENTS.items():
            self.assertIn(f"flag:tech_{key} }} localization_key = {tech} }}", occ, key)

    def test_regime_petitioners_are_the_approving_igs(self):
        body = squash(block(self.e, "gm_com_track_regime"))
        for key, ig in REGIME_IG.items():
            self.assertEqual(BY_KEY[key].approve, ig, key)
            self.assertIn(f"gm_com_try_regime = {{ KEY = {key} IG = {ig} }}", body)
        # Revolution first: a Council Republic is also a republic.
        self.assertLess(body.find("flag:revolution"), body.find("flag:crown"))
        self.assertLess(body.find("flag:crown"), body.find("flag:republic"))

    def test_a_new_reign(self):
        """A ruler who is not last month's begins a reign: the Crown when
        crowned, else the Leader; nothing on a game's first pass, and nothing
        for a regent, appointed or replaced (has_gov_regency)."""
        track = squash(block(self.e, "gm_com_track_ruler"))
        self.assertIn("else = { if = { limit = { has_variable = gm_ruler NOT = { AND = { exists = var:gm_ruler "
                      "var:gm_ruler = scope:gm_com_tracked_ruler } } has_gov_regency = no } gm_com_try_reign = yes }",
                      track)
        # The regent is still recorded, so the monarch who takes over when the
        # regency ends is seen as the new ruler.
        self.assertLess(track.find("gm_com_try_reign = yes"),
                        track.find("set_variable = { name = gm_ruler value = scope:gm_com_tracked_ruler }"))
        reign = squash(block(self.e, "gm_com_try_reign"))
        self.assertLess(reign.find("gm_country_can_raise_crown = yes"), reign.find("gm_country_can_raise_leader = yes"))
        self.assertIn("set_variable = { name = gm_com_ig value = flag:landowners }", reign)
        self.assertEqual(reign.count("set_variable = { name = gm_com_name_char value = scope:gm_com_tracked_ruler }"), 2)
        self.assertEqual(BY_KEY["crown"].approve, "landowners")

    def test_no_petition_and_no_cooldown(self):
        """Every opportunity comes from a moment (owner, 2026-10-12): the
        petition roll and its cooldown are gone."""
        for gone in ("gm_com_try_petition", "gm_com_offer_petition", "gm_com_begin_petition", "gm_com_count_fit",
                     "gm_com_forget_fit", "gm_com_extend"):
            self.assertIsNone(block(self.e, gone), gone)
        for gone in ("gm_com_petition_fits", "gm_com_any_petition_fits", "gm_com_ai_wants_more_time"):
            self.assertIsNone(block(read(COM_TRIGGERS), gone), gone)
        self.assertEqual(squash(block(self.e, "gm_com_close")), "gm_com_clear = yes")
        self.assertNotIn("gm_com_cooldown", strip_comments(self.e).replace(
            "gm_remove_state_var = { VAR = gm_com_cooldown }", ""))
        can = squash(block(read(COM_TRIGGERS), "gm_com_can_offer"))
        for s_ in ("NOT = { has_variable = gm_com_offered }", "NOT = { has_variable = gm_com_open }",
                   "NOT = { any_scope_state = { has_variable = gm_restore_pm "
                   "NOT = { var:gm_restore_pm = flag:undedicated } } }"):
            self.assertIn(s_, can)

    def test_every_rank_and_the_ai_gate(self):
        """Any rank may take one (owner, 2026-10-12), with longer below great
        and major power; the AI below major power lets them pass, since five
        levels are 5,000 construction (owner, 2026-10-05)."""
        can = squash(block(read(COM_TRIGGERS), "gm_com_can_offer"))
        self.assertNotIn("country_rank", can)
        self.assertEqual(squash(strip_comments(block(read(COM_VALUES), "gm_com_time_months"))),
                         "value = 180 if = { limit = { country_rank >= rank_value:great_power } value = 60 } "
                         "else_if = { limit = { country_rank >= rank_value:major_power } value = 120 } "
                         "if = { limit = { has_variable = gm_com_target var:gm_com_target > 5 } "
                         "multiply = var:gm_com_target divide = 5 }")
        self.assertIn("set_variable = { name = gm_com_months_left value = gm_com_time_months }",
                      squash(block(read(COM_EFFECTS), "gm_com_accept")))
        self.assertIn("OR = { NOT = { country_rank >= rank_value:major_power }",
                      squash(block(read(COM_TRIGGERS), "gm_com_ai_declines")))
        words = squash(block(read(CUSTOM_LOC), "gm_com_time_words"))
        for rank, key in (("great_power", "gm_com_time_5_years"), ("major_power", "gm_com_time_10_years")):
            self.assertIn(f"country_rank >= rank_value:{rank} }} localization_key = {key}", words)
        # A historical opportunity of ten levels has twice as long (signatures spec §6.1).
        for rank, key in (("great_power", "gm_com_time_10_years"), ("major_power", "gm_com_time_20_years")):
            self.assertIn(f"var:gm_com_target > 5 country_rank >= rank_value:{rank} }} localization_key = {key}", words)
        self.assertIn("var:gm_com_target > 5 } localization_key = gm_com_time_30_years", words)
        self.assertTrue(words.endswith("text = { localization_key = gm_com_time_15_years }"))
        L = loc()
        self.assertIn("ScriptValue('gm_com_time_months')", L["gm_com_accept_head"])
        for key, text in L.items():
            if key.startswith("monument_events.21.d_"):
                self.assertNotIn("five years", text, key)

    def test_the_space_firsts(self):
        track = squash(block(self.e, "gm_com_track_space"))
        self.assertEqual(tuple(re.findall(r"gm_com_track_space_one = \{ M = (\w+) \}", track)), SPACE_FIRSTS)
        sight = squash(block(self.e, "gm_com_first_sight"))
        for m in SPACE_FIRSTS:
            self.assertIn(f"gm_com_see_space_if_won = {{ M = {m} }}", sight, m)
            self.assertIn(f"space_{m}", NAMESAKES["occasion"], m)
            self.assertIn(f"var:gm_com_occasion = flag:space_{m} }} localization_key = gm_com_occasion_space_{m}",
                          squash(block(read(CUSTOM_LOC), "gm_com_occasion_name")), m)
            self.assertIn(f"var:gm_com_occasion = flag:space_{m} }} localization_key = gm_com_named_space_{m}",
                          squash(block(read(CUSTOM_LOC), "gm_com_namesake_phrase")), m)
        self.assertIn("limit = { has_variable = sr_was_first_$M$ } set_variable = gm_com_seen_space_$M$",
                      squash(block(self.e, "gm_com_see_space_if_won")))

    def test_civil_war_guards(self):
        """A side in a civil war gets no offer, and a revolutionary country never
        writes the founding year or the faith its win would put over the nation's."""
        can = squash(block(read(COM_TRIGGERS), "gm_com_can_offer"))
        self.assertIn("NOT = { has_variable = te_cw_role }", can)
        self.assertIn("is_revolutionary = no", can)
        for name in ("gm_com_init_founded", "gm_com_track_faith"):
            body = squash(block(self.e, name))
            for s_ in ("NOT = { has_variable = te_cw_role }", "is_revolutionary = no"):
                self.assertIn(s_, body, name)
        self.assertIn("NOT = { has_variable = gm_com_start_country }", squash(block(self.e, "gm_com_init_founded")))

    def test_world_pass(self):
        oa = read(ON_ACTIONS)
        self.assertIn("gm_com_world_on_action", squash(block(oa, "on_monthly_pulse_country")))
        self.assertIn("gm_com_world_monthly = yes", squash(block(oa, "gm_com_world_on_action")))
        body = squash(block(self.e, "gm_com_world_monthly"))
        found = [body.find(f"{t} = yes") for t in WORLD_PASS]
        self.assertNotIn(-1, found)
        self.assertEqual(found, sorted(found))
        self.assertIn("limit = { NOT = { has_variable = gm_com_opp_tracked } } gm_com_first_sight = yes", body)

    def test_first_sight_offers_nothing(self):
        """What a country already has the first time the pass sees it brings
        no opportunity: great power status, the technologies, the faith (its
        tracker writes the first value without offering)."""
        sight = squash(block(self.e, "gm_com_first_sight"))
        self.assertIn("set_variable = gm_com_opp_tracked", sight)
        self.assertIn("limit = { country_rank >= rank_value:great_power } set_variable = gm_com_seen_great_power", sight)
        self.assertNotIn("gm_com_send_offer", sight)
        gp = squash(block(self.e, "gm_com_track_great_power"))
        self.assertIn("NOT = { has_variable = gm_com_seen_great_power } } set_variable = gm_com_seen_great_power", gp)
        faith = squash(block(self.e, "gm_com_track_faith"))
        self.assertIn("has_variable = gm_com_faith_last NOT = { var:gm_com_faith_last = scope:gm_com_faith_now }", faith)
        self.assertTrue(faith.rstrip(" }").endswith(
            "set_variable = { name = gm_com_faith_last value = scope:gm_com_faith_now"), faith[-200:])

    def test_war_and_death_hooks(self):
        """Victory and Defeat come from on_won_war / on_lost_war (1.14.5), which
        carry the war itself, so a capitulation counts and the year of war is
        that war's, for its leader only."""
        oa = read(ON_ACTIONS)
        for hook, name in (("on_won_war", "gm_won_war_on_action"),
                           ("on_lost_war", "gm_lost_war_on_action"),
                           ("on_character_death", "gm_character_death_on_action"),
                           ("on_country_formed", "gm_formed_on_action")):
            self.assertIn(name, squash(block(oa, hook)), hook)
            self.assertNotRegex(squash(block(oa, hook)), r"\beffect =", "vanilla on-actions take lists only")
        for name, flag, call in (("gm_won_war_on_action", "benefitted_from_wargoal", "gm_com_war_victory"),
                                 ("gm_lost_war_on_action", "victim_of_wargoal", "gm_com_war_defeat")):
            body = squash(block(oa, name))
            self.assertIn(f"exists = scope:{flag} exists = scope:war scope:war = {{ is_warleader = root "
                          f"war_duration_months >= 12 }} }} {call} = yes", body, name)
        self.assertNotIn("monument_events.22", self.events)
        for gone in ("on_wargoal_enforced", "on_peace_agreement_signed_war_leader"):
            self.assertIsNone(block(oa, gone), gone)
        victory = squash(block(self.e, "gm_com_war_victory"))
        self.assertIn("scope:enemy_country ?= { capital ?= { save_scope_as = gm_com_enemy_capital } }", victory)
        death = squash(block(oa, "gm_character_death_on_action"))
        self.assertIn("is_ruler_of_own_country = yes", death)
        self.assertIn("var:gm_ruler_months >= 180", death)

    def test_fixed_state_falls_back_to_anywhere(self):
        fix = squash(block(self.e, "gm_com_fix_to_capital"))
        self.assertIn("capital ?= { gm_state_can_host_commission = yes }", fix)
        host = squash(block(read(COM_TRIGGERS), "gm_state_can_host_commission"))
        for case in ("NOT = { has_building = building_grand_monument }", "gm_state_is_dedicated = no",
                     "gm_state_status_fits = yes gm_state_has_dedication_flag = { VAR = gm_com_dedication }"):
            self.assertIn(case, host)

    def test_founding_years(self):
        body = squash(block(self.e, "gm_seed_founding_years"))
        listed = {t: int(y) for t, y in re.findall(r"gm_seed_founding_year = \{ TAG = (\w+) YEAR = (\d+) \}", body)}
        self.assertEqual(listed, FOUNDING_YEARS)
        self.assertTrue(all(y < 1836 for y in listed.values()))
        self.assertIn("gm_com_seed = yes", squash(read(HISTORY)))
        seed = squash(block(self.e, "gm_com_seed"))
        self.assertIn("set_variable = gm_com_start_country", seed)
        self.assertIn("gm_seed_founding_years = yes", seed)


class CommissionLifeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = read(COM_EFFECTS)
        cls.t = read(COM_TRIGGERS)

    def test_can_raise_matches_the_ceremony(self):
        """An opportunity is offered and stays open only for a dedication the
        ceremony would offer: each gate is the ceremony option's trigger."""
        ev = strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.2\s*=\s*\{"))
        for d in DEDICATIONS:
            gate = squash(block(self.t, f"gm_country_can_raise_{d.key}"))
            self.assertIsNotNone(gate, d.key)
            if d.key in CEREMONY_GATE:
                self.assertIn(CEREMONY_GATE[d.key], gate, d.key)
            if d.key in TECH_GATES:
                self.assertIn(f"has_technology_researched = {TECH_GATES[d.key]}", gate, d.key)
            if d.key not in CEREMONY_GATE and d.key not in TECH_GATES:
                self.assertEqual(gate, "always = yes", d.key)
            self.assertIn(f"var:gm_com_dedication = flag:{d.key} gm_country_can_raise_{d.key} = yes",
                          squash(block(self.t, "gm_country_com_gate_holds")))
            self.assertIn(f"owner = {{ var:$VAR$ = flag:{d.key} }} gm_state_has_pm = {{ PM = pm_monument_{d.key} }}",
                          squash(block(self.t, "gm_state_has_dedication_flag")))
            self.assertIn(f"modifier = {{ trigger = {{ gm_state_ceremony_for_commission = {{ KEY = {d.key} }} }} "
                          f"add = 100 }} modifier = {{ trigger = {{ gm_state_ceremony_not_for_commission = "
                          f"{{ KEY = {d.key} }} }} factor = 0 }}", squash(ev), d.key)
        # The opportunity's option is first and the default while it is
        # offered; "leave it undedicated" is the default otherwise. Two copies
        # with complementary triggers keep exactly one default valid
        # (scripting_best_practices.md: a failed default does not fall back).
        self.assertIn("name = monument_events.2.opp highlighted_option = yes trigger = { custom_tooltip = { "
                      "text = gm_ded_reason_opportunity_tt gm_state_ceremony_offers_opportunity = yes } } "
                      "owner = { custom_tooltip = gm_ded_reason_opportunity_tt } default_option = yes "
                      "ai_chance = { base = 0 } gm_state_dedicate_as_opportunity_asks = yes",
                      squash(ev))
        self.assertIn("name = monument_events.2.a trigger = { hidden_trigger = { NOT = { has_variable = gm_ceremony_mode "
                      "var:gm_ceremony_mode = flag:rededicate } } custom_tooltip = { text = gm_ded_reason_leave_tt "
                      "gm_state_ceremony_offers_opportunity = no } } "
                      "default_option = yes ai_chance = { base = 0 }", squash(ev))
        self.assertIn("name = monument_events.2.a trigger = { hidden_trigger = { NOT = { has_variable = gm_ceremony_mode "
                      "var:gm_ceremony_mode = flag:rededicate } } custom_tooltip = { text = gm_ded_reason_leave_tt "
                      "gm_state_ceremony_offers_opportunity = yes } } "
                      "ai_chance = { base = 0 }", squash(ev), "the AI never leaves its monument undedicated")
        # The opportunity's, Not yet's and Keep it as it is's: exactly one valid at a time.
        self.assertEqual(squash(ev).count("default_option = yes"), 3)
        self.assertLess(squash(ev).find("name = monument_events.2.opp"), squash(ev).find("name = monument_events.2.a"))
        offers = squash(block(self.t, "gm_state_ceremony_offers_opportunity"))
        self.assertEqual(offers, "gm_state_ceremony_answers_commission = yes owner = { gm_country_com_gate_holds = yes }")
        # The option repeats each dedication's own: its tooltip and wrapper.
        asks = squash(block(self.e, "gm_state_dedicate_as_opportunity_asks"))
        for d in DEDICATIONS:
            self.assertIn(f"owner = {{ var:gm_com_dedication = flag:{d.key} }} }} custom_tooltip = {{ text = "
                          f"monument_events.2.{CEREMONY_OPTION[d.key]}.tt {wrapper_call(d)} }}", asks, d.key)
        answers = squash(block(self.t, "gm_state_ceremony_answers_commission"))
        self.assertIn("this = scope:gm_tmp_com_state", answers, "only the opportunity's state, if it names one")

    def test_every_dedication_has_a_moment(self):
        """Each of the twelve dedications can be asked for by some moment."""
        asked = set()
        for src in COMMISSION_SOURCES:
            for begin in src.begins:
                asked.add(re.match(r"DEDICATION = (\S+)", begin).group(1))
        asked.discard("$KEY$")
        asked |= set(REGIME_IG) | set(TECH_MOMENTS)
        self.assertEqual(asked, {d.key for d in DEDICATIONS})

    def test_ledger_dispatch_covers_every_ig(self):
        body = squash(block(self.e, "gm_country_ledger_ig_by_flag"))
        scopes = squash(block(self.e, "gm_com_save_scopes"))
        names = squash(block(read(CUSTOM_LOC), "gm_com_ig_name"))
        for ig in IGS:
            self.assertIn(f"IG = {ig} }}", body, ig)
            self.assertIn(f"gm_com_save_ig_scope = {{ IG = {ig} }}", scopes, ig)
            self.assertIn(f"flag:{ig} }} localization_key = ig_{ig}", names, ig)

    def test_the_promise_ledger_is_retired(self):
        """A Promise Kept gave way to the boons (2026-10-12). Its modifier
        stays defined and removed, so a save that carries it sheds it."""
        e = read(EFFECTS)
        for name in ("gm_init_ledgers", "gm_zero_ledgers", "gm_decay_ledgers", "gm_apply_national_modifiers"):
            self.assertNotIn("gm_promise_ledger", squash(block(e, name)), name)
        self.assertNotIn("gm_promise_ledger", squash(block(read(TRIGGERS), "gm_ledgers_idle")))
        self.assertNotIn("gm_promise_ledger", strip_comments(read(COM_EFFECTS)).replace(
            "gm_remove_state_var = { VAR = gm_promise_ledger }", ""))
        self.assertIn("remove_modifier = gm_national_promise", squash(block(e, "gm_remove_national_modifiers")))
        self.assertIsNotNone(block(read(MODIFIERS), "gm_national_promise"))
        self.assertIn("gm_remove_state_var = { VAR = gm_promise_ledger }", squash(block(self.e, "gm_com_first_sight")))

    def test_rewards_and_no_cost(self):
        """Completing one gives the gift, the approval and the boon; nothing
        else costs anything (owner, 2026-10-12)."""
        fulfil = squash(block(self.e, "gm_com_fulfil"))
        self.assertIn(f"gm_country_ledger_ig_by_flag = {{ VAR = gm_com_ig AMOUNT = {REWARDS['ig']} }} "
                      "gm_com_grant_boon = yes", fulfil)
        self.assertIn("set_variable = gm_gift", fulfil)
        self.assertLess(fulfil.index("set_variable = gm_gift"), fulfil.index("trigger_event = { id = monument_events.26 }"))
        for name in ("gm_com_decline", "gm_com_miss", "gm_com_lapse", "gm_com_close", "gm_com_clear"):
            body = squash(block(self.e, name))
            self.assertNotIn("ledger", body, name)
            self.assertNotIn("AMOUNT", body, name)
        values = read(COM_VALUES)
        self.assertRegex(strip_comments(values), rf"(?m)^gm_com_reward_ig = {REWARDS['ig']}\s*$")
        self.assertRegex(strip_comments(values), rf"(?m)^gm_com_gift = {REWARDS['gift']}\s*$")
        self.assertRegex(strip_comments(values), rf"(?m)^gm_boon_months = {REWARDS['boon_months']}\s*$")
        for gone in ("gm_com_reward_promise", "gm_disp_com_extended"):
            self.assertIsNone(block(values, gone), gone)

    def test_the_offer(self):
        ev = squash(raw_block_at(read(EVENTS), r"(?m)^monument_events\.21\s*=\s*\{"))
        self.assertIn("trigger = { has_variable = gm_com_offered has_variable = gm_com_source }", ev)
        self.assertEqual(ev.count("option = {"), 3)
        self.assertEqual(ev.count("default_option = yes"), 1)
        # Seizing is the default: letting it pass, or running out, costs nothing.
        # A historical opportunity's tooltip is a key of its own, chosen in
        # script: a key named in SelectLocalization loses SCOPE.
        self.assertIn("name = monument_events.21.a default_option = yes "
                      "if = { limit = { var:gm_com_source = flag:historical } "
                      "custom_tooltip = { text = gm_com_accept_hist_tt gm_com_accept = yes } } "
                      "else = { custom_tooltip = { text = gm_com_accept_tt gm_com_accept = yes } }", ev)
        self.assertIn("name = monument_events.21.b custom_tooltip = { text = gm_com_decline_tt gm_com_decline = yes }", ev)
        self.assertIn("modifier = { trigger = { gm_com_ai_declines = yes } factor = 0 }", ev)
        self.assertIn("event_image", ev)
        # Seize it and start building (usability §2): players only, where the
        # immediate's pick puts it.
        self.assertIn("immediate = { gm_com_save_scopes = yes gm_com_pick_build_state = yes }",
                      squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.21\s*=\s*\{"))))
        build = ("gm_com_accept = yes set_variable = { name = gm_com_raise_pending value = yes days = 7 } "
                 "trigger_event = { id = monument_events.27 } }")
        self.assertIn("name = monument_events.21.c trigger = { is_ai = no exists = scope:gm_com_build_state } "
                      "if = { limit = { var:gm_com_source = flag:historical } "
                      f"custom_tooltip = {{ text = gm_com_accept_hist_build_tt {build} }} "
                      f"else = {{ custom_tooltip = {{ text = gm_com_accept_build_tt {build} }} "
                      "ai_chance = { base = 0 }", ev)
        declines = squash(block(self.t, "gm_com_ai_declines"))
        for s_ in ("is_at_war = yes", "gm_country_hard_times = yes",
                   "construction_queue_government_duration >= 52", "scaled_debt > 0"):
            self.assertIn(s_, declines)
        L = loc()
        self.assertIn("gm_com_gift", L["gm_com_accept_head"])
        for key in ("gm_com_accept_tt", "gm_com_accept_hist_tt"):
            self.assertTrue(L[key].startswith("$gm_com_accept_head$"), key)
            self.assertNotIn("SelectLocalization", L[key], key)
        for read_ in ("gm_disp_boon_years", "gm_com_boon_name", "gm_com_boon_effect"):
            self.assertIn(read_, L["gm_com_accept_tt"], read_)
            self.assertNotIn(read_, L["gm_com_accept_hist_tt"], read_)
        for read_ in ("gm_com_occasion_name", "gm_com_hist_sig_line"):
            self.assertIn(read_, L["gm_com_accept_hist_tt"], read_)
        self.assertEqual(L["gm_com_accept_build_tt"], "$gm_com_accept_tt$\\n$gm_com_accept_build_line$")
        self.assertEqual(L["gm_com_accept_hist_build_tt"], "$gm_com_accept_hist_tt$\\n$gm_com_accept_build_line$")

    def test_let_it_pass_from_the_panel(self):
        sgui = squash(block(read(SGUIS), "gm_com_let_pass_sgui"))
        self.assertIn("custom_tooltip = { text = gm_com_let_pass_effect_tt gm_com_decline = yes }", sgui)
        self.assertIn("ai_is_valid = { always = no }", sgui)
        self.assertIsNone(block(read(SGUIS), "gm_com_extend_sgui"))
        gui = read(WIDGET)
        self.assertIn("GetScriptedGui('gm_com_let_pass_sgui')", gui)
        self.assertNotIn("gm_com_extend_sgui", gui)

    def test_accept_and_the_ai_queue(self):
        accept = squash(block(self.e, "gm_com_accept"))
        for s_ in ("set_variable = gm_com_open", "set_variable = { name = gm_com_months_left value = gm_com_time_months }",
                   "set_variable = { name = gm_com_baseline value = gm_com_fit_grandeur }",
                   "if = { limit = { is_ai = yes } gm_com_ai_queue = yes }"):
            self.assertIn(s_, accept)
        queue = squash(block(self.e, "gm_com_queue_levels"))
        self.assertIn("while = { limit = { var:gm_com_queued < var:gm_com_raise_levels } scope:gm_com_build_state = "
                      "{ start_building_construction = building_grand_monument_site }", queue)
        self.assertNotIn("create_building", queue, "the country pays for its levels")
        ai = squash(block(self.e, "gm_com_ai_queue"))
        self.assertIn("gm_com_pick_build_state = yes if = { limit = { exists = scope:gm_com_build_state } "
                      "set_variable = { name = gm_com_raise_levels value = gm_com_levels_to_go } gm_com_queue_levels = yes", ai)

    def test_progress_floors_at_zero(self):
        body = squash(block(read(COM_VALUES), "gm_com_progress"))
        self.assertIn("value = gm_com_fit_grandeur subtract = var:gm_com_baseline min = 0", body)
        counts = squash(block(self.t, "gm_state_com_counts"))
        self.assertIn("gm_state_status_fits = yes", counts, "a contested monument stops counting")

    def test_the_month_and_the_refresh(self):
        monthly = squash(block(self.e, "gm_com_monthly"))
        self.assertLess(monthly.find("gm_com_has_lapsed = yes"), monthly.find("var:gm_com_months_left <= 0"),
                        "a lapse is judged before a run-out")
        self.assertNotIn("extend", monthly)
        e = read(EFFECTS)
        country = squash(block(e, "gm_country_monthly"))
        self.assertLess(country.find("gm_tick_boons = yes"), country.find("gm_country_refresh = yes"))
        self.assertLess(country.find("gm_com_monthly = yes"), country.find("gm_country_refresh = yes"))
        refresh = squash(block(e, "gm_country_refresh"))
        self.assertLess(refresh.find("gm_check_contests = yes"), refresh.find("gm_com_check_progress = yes"))
        self.assertLess(refresh.find("gm_com_check_progress = yes"), refresh.find("gm_compute_totals = yes"))
        self.assertIn("has_variable = gm_com_open", squash(block(read(ON_ACTIONS), "gm_country_on_action")))
        lapsed = squash(block(self.t, "gm_com_has_lapsed"))
        self.assertIn("gm_country_com_gate_holds = no", lapsed)
        self.assertIn("NOT = { owner = scope:gm_tmp_com_holder }", lapsed)

    def test_the_journal_entry_opens_for_a_commission(self):
        je = read(JE)
        clause = "has_variable = gm_com_open has_variable = gm_com_offered"
        for name in ("is_shown_when_inactive", "possible"):
            self.assertIn(clause, squash(block(je, name)), name)
        invalid = squash(block(je, "invalid"))
        self.assertIn("NOT = { has_variable = gm_com_open } NOT = { has_variable = gm_com_offered }", invalid)
        self.assertIn(clause, squash(block(read(TRIGGERS), "gm_entry_unlocked")))
        self.assertIn(clause, squash(block(read(EFFECTS), "gm_country_refresh")))

    def test_the_ceremony_names_the_commission(self):
        ev = squash(raw_block_at(read(EVENTS), r"(?m)^monument_events\.2\s*=\s*\{"))
        self.assertIn("trigger = { owner = { has_variable = gm_com_open } } desc = monument_events.2.d_commission", ev)
        self.assertTrue(loc()["monument_events.2.d_commission"].startswith("$monument_events.2.d$"))

    def test_the_last_monument_touched(self):
        self.assertIn("owner = { set_variable = { name = gm_com_last_state value = prev } }",
                      squash(block(read(EFFECTS), "gm_state_dedicate")))
        ev1 = squash(raw_block_at(read(EVENTS), r"(?m)^monument_events\.1\s*=\s*\{"))
        self.assertIn("owner = { set_variable = { name = gm_com_last_state value = prev } }", ev1)


class BoonTests(unittest.TestCase):
    """One boon per moment (opportunities spec §3.2): a flat modifier on the
    journal entry while gm_boon_<source> counts its months down."""

    @classmethod
    def setUpClass(cls):
        cls.e = read(COM_EFFECTS)

    def test_each_boon_is_one_field_and_its_loc_shows_its_value(self):
        L = loc()
        for src in COMMISSION_SOURCES:
            name = f"gm_boon_{src.key}"
            body = block(read(MODIFIERS), name)
            self.assertIsNotNone(body, name)
            # a mortality line's Causes of Death tag is a label beside it (owner, 2026-10-22)
            fields = [k for k in re.findall(r"(?m)^\s*(\w+)\s*=", body)
                      if k != "icon" and not k.startswith("state_death_cause_")]
            self.assertEqual(fields, [src.boon_field], name)
            self.assertAlmostEqual(number(body, src.boon_field), src.boon_value, msg=name)
            self.assertIn("modifier_statue_positive", body, name)
            for key in (name, f"{name}_desc", f"{name}_effect"):
                self.assertIn(key, L, key)
            self.assertTrue(L[f"{name}_effect"].startswith(f"#G {src.boon_shown}#!"), name)
            self.assertEqual(src.boon_shown.startswith("+"), src.boon_value > 0, name)

    def test_every_dispatcher_lists_every_boon(self):
        for effect, call in (("gm_com_grant_boon", "gm_com_grant_boon_one = {{ SRC = {} }}"),
                             ("gm_tick_boons", "gm_tick_boon = {{ SRC = {} }}"),
                             ("gm_add_boons", "gm_add_boon = {{ SRC = {} }}"),
                             ("gm_remove_boons", "remove_modifier = gm_boon_{}")):
            body = squash(block(self.e, effect))
            for key in SOURCE_KEYS:
                self.assertIn(call.format(key), body, (effect, key))
        idle = squash(block(read(COM_TRIGGERS), "gm_boons_idle"))
        custom = read(CUSTOM_LOC)
        for key in SOURCE_KEYS:
            self.assertIn(f"NOT = {{ has_variable = gm_boon_{key} }}", idle, key)
            self.assertIsNotNone(block(read(COM_VALUES), f"gm_disp_boon_{key}"), key)
            for target, loc_key in (("gm_com_boon_name", f"gm_boon_{key}"), ("gm_com_boon_effect", f"gm_boon_{key}_effect")):
                self.assertIn(f"trigger = {{ gm_com_source_is = {{ SRC = {key} }} }} localization_key = {loc_key} }}",
                              squash(block(custom, target)), key)

    def test_wired_into_the_national_refresh(self):
        e = read(EFFECTS)
        self.assertIn("gm_add_boons = yes", squash(block(e, "gm_apply_national_modifiers")))
        self.assertIn("gm_remove_boons = yes", squash(block(e, "gm_remove_national_modifiers")))
        self.assertIn("gm_boons_idle = yes", squash(block(read(TRIGGERS), "gm_ledgers_idle")),
                      "the entry and the pulse stay while a boon runs")
        grant = squash(block(self.e, "gm_com_grant_boon_one"))
        self.assertIn("set_variable = { name = gm_boon_$SRC$ value = gm_boon_months }", grant)
        tick = squash(block(self.e, "gm_tick_boon"))
        self.assertIn("change_variable = { name = gm_boon_$SRC$ add = -1 } if = { limit = { var:gm_boon_$SRC$ <= 0 } "
                      "remove_variable = gm_boon_$SRC$ }", tick)


class GiftTests(unittest.TestCase):
    """The monument's gift (opportunities spec §3.1): rebuilt taller by a
    hidden state event, keeping its records, its dedication put back."""

    @classmethod
    def setUpClass(cls):
        cls.e = read(COM_EFFECTS)
        cls.events = read(EVENTS)

    def test_the_gift_runs_in_its_own_event(self):
        """Never inside gm_com_fulfil, which the refresh runs and tooltips walk."""
        fulfil = squash(block(self.e, "gm_com_fulfil"))
        for s_ in ("remove_building", "create_building", "te_construction_market_build_specified_level"):
            self.assertNotIn(s_, fulfil)
        ev = squash(raw_block_at(self.events, r"(?m)^monument_events\.26\s*=\s*\{"))
        self.assertIn("type = state_event hidden = yes", ev)
        self.assertIn("trigger = { gm_system_enabled = yes has_variable = gm_gift }", ev)
        self.assertIn("immediate = { gm_state_gift_grandeur = yes gm_state_hist_take = yes gm_state_sig_take_grant = yes }",
                      squash(strip_comments(raw_block_at(self.events, r"(?m)^monument_events\.26\s*=\s*\{"))))

    def test_the_gift_fires_after_the_record_closes(self):
        """A trigger_event with no delay runs the event inside gm_com_fulfil,
        and the gift's refresh (monument_events.20) asks gm_com_check_progress
        again: fired before gm_com_close, it found the opportunity still open
        and seized it again without end (two stack-overflow crashes,
        2026-10-17)."""
        fulfil = squash(strip_comments(block(self.e, "gm_com_fulfil")))
        gift = "scope:gm_com_named_state ?= { trigger_event = { id = monument_events.26 } }"
        self.assertEqual(fulfil.count("monument_events.26"), 1)
        self.assertLess(fulfil.index("gm_com_close = yes"), fulfil.index(gift))

    def test_the_gift_is_age(self):
        # Ageing rework (spec 2026-10-16 §5; owner): +5 grandeur, no rebuild.
        gift = squash(block(self.e, "gm_state_gift_grandeur"))
        self.assertTrue(gift.startswith("gm_remove_state_var = { VAR = gm_gift }"))
        self.assertIn("limit = { has_building = building_grand_monument gm_state_is_dedicated = yes } "
                      "gm_state_add_age = { AGE = gm_com_gift }", gift)
        self.assertNotIn("remove_building", gift)
        self.assertNotIn("gm_clear_state", gift, "the gift keeps the monument's records")
        self.assertNotIn("gm_state_start_ceremony", gift)

    def test_the_dedication_is_put_back(self):
        mark = squash(block(self.e, "gm_state_mark_restore_pm"))
        restore = squash(block(self.e, "gm_state_restore_dedication"))
        for d in DEDICATIONS:
            self.assertIn(f"gm_state_mark_restore_pm_one = {{ KEY = {d.key} }}", mark, d.key)
            self.assertIn(f"gm_state_restore_dedication_one = {{ KEY = {d.key} }}", restore, d.key)
        one = squash(strip_comments(block(self.e, "gm_state_restore_dedication_one")))
        # Read back: the flag goes; else one switch (with the creation
        # self-check around both, CreatedOnDedicationTests).
        self.assertIn("remove_variable = gm_restore_pm } else = {", one)
        self.assertTrue(one.endswith("activate_production_method = { building_type = building_grand_monument "
                                     "production_method = pm_monument_$KEY$ } } }"), one[-200:])
        e = read(EFFECTS)
        refresh = squash(block(e, "gm_country_refresh"))
        # After an older save's migration ask (MigrationTests).
        self.assertIn("every_scope_state = { limit = { has_building = building_grand_monument } "
                      "if = { limit = { gm_state_needs_migration = yes } trigger_event = { id = monument_events.32 } } "
                      "gm_state_restore_dedication = yes", refresh)
        monthly = squash(block(e, "gm_state_monthly"))
        self.assertTrue(monthly.startswith("gm_state_count_site_levels = yes gm_remove_local_modifiers = yes "
                                           "gm_state_restore_dedication = yes"))

    def test_nothing_judges_the_method_meanwhile(self):
        e = read(EFFECTS)
        self.assertIn("NOT = { has_variable = gm_restore_pm }", squash(block(e, "gm_state_start_ceremony")))
        self.assertIn("NOT = { has_variable = gm_restore_pm }", squash(block(e, "gm_check_contests")))
        clear = squash(block(e, "gm_clear_state"))
        for var in ("gm_gift", "gm_restore_pm"):
            self.assertIn(f"gm_remove_state_var = {{ VAR = {var} }}", clear, var)


class UsabilityTests(unittest.TestCase):
    """Opportunities made easy to act on (opportunities spec, usability §1-§5)."""

    @classmethod
    def setUpClass(cls):
        cls.e = read(COM_EFFECTS)
        cls.t = read(COM_TRIGGERS)
        cls.events = read(EVENTS)

    def test_raise_it(self):
        sgui = squash(block(read(SGUIS), "gm_com_raise_sgui"))
        self.assertIn("is_valid = { gm_com_can_raise = yes }", sgui)
        self.assertIn("custom_tooltip = { text = gm_com_raise_effect_tt set_variable = { name = gm_com_raise_pending "
                      "value = yes days = 7 } trigger_event = { id = monument_events.27 } }", sgui)
        self.assertIn("ai_is_valid = { always = no }", sgui)
        can = squash(block(self.t, "gm_com_can_raise"))
        for s_ in ("gm_com_monument_under_construction = no", "NOT = { has_variable = gm_com_raise_pending }",
                   "has_variable = gm_com_build_where"):
            self.assertIn(s_, can)
        self.assertEqual(squash(block(self.t, "gm_com_monument_under_construction")),
                         "any_scope_building = { is_building_type = building_grand_monument_site is_under_construction = yes }")
        ev = squash(raw_block_at(self.events, r"(?m)^monument_events\.27\s*=\s*\{"))
        self.assertIn("type = country_event hidden = yes", ev)
        self.assertIn("immediate = { gm_com_raise = yes }", ev)
        raise_ = squash(block(self.e, "gm_com_raise"))
        self.assertIn("gm_com_levels_to_go > 0", raise_)
        self.assertIn("set_variable = { name = gm_com_raise_levels value = gm_com_levels_to_go } gm_com_queue_levels = yes",
                      raise_)
        # The grandeur missing, in levels at today's rate (OpportunityGrandeurTests).
        self.assertEqual(squash(block(read(COM_VALUES), "gm_com_grandeur_to_go")),
                         "value = 0 if = { limit = { has_variable = gm_com_open has_variable = gm_com_target } "
                         "value = var:gm_com_target subtract = gm_com_progress min = 0 }")
        gui = read(WIDGET)
        self.assertIn("GetScriptedGui('gm_com_raise_sgui')", gui)

    def test_where_it_builds_is_refreshed_not_read_back(self):
        refresh = squash(block(read(EFFECTS), "gm_country_refresh"))
        self.assertLess(refresh.find("gm_com_check_progress = yes"), refresh.find("gm_com_update_build_where = yes"))
        where = squash(block(self.e, "gm_com_update_build_where"))
        self.assertNotIn("var:gm_com_build_where", where, "written, never read back in the refresh")
        clear = squash(block(self.e, "gm_com_clear"))
        for var in ("gm_com_build_where", "gm_com_raise_pending"):
            self.assertIn(f"gm_remove_state_var = {{ VAR = {var} }}", clear, var)

    def test_the_panel_says_where_and_what_counts(self):
        sec = squash(raw_block_at(read(WIDGET), r"type te_gm_sec_commission\s*=\s*flowcontainer\s*\{"))
        self.assertIn('text = "gm_je_com_where_line"', sec)
        self.assertIn("ScriptValue('gm_disp_com_building'), '(CFixedPoint)1' )]\" text = \"gm_je_com_building\"", sec)
        L = loc()
        self.assertIn("'gm_je_com_where_line_fixed', 'gm_je_com_where_line_any'", L["gm_je_com_where_line"])
        for rel in (WIDGET, "gui/te_state_panel_widgets.gui"):
            gui = squash(read(rel))
            self.assertIn("ScriptValue('gm_state_disp_com_counts'), '(CFixedPoint)1' )]", gui, rel)
            self.assertIn('text = "gm_row_com_counts"', gui, rel)
        counts = squash(block(read(COM_VALUES), "gm_state_disp_com_counts"))
        self.assertIn("gm_state_com_counts = yes", counts)
        self.assertNotIn("JournalEntry", L["gm_row_com_counts_tt"], "a row tooltip reads nothing but State")

    def test_a_reminder_and_a_completion_event(self):
        monthly = squash(block(self.e, "gm_com_monthly"))
        self.assertIn("else_if = { limit = { is_ai = no var:gm_com_months_left = 12 } "
                      "post_notification = gm_com_reminder_notice }", monthly)
        self.assertIsNotNone(block(read(MESSAGES), "gm_com_reminder_notice"))
        self.assertIsNone(block(read(MESSAGES), "gm_com_fulfilled_notice"), "completion is an event now")
        fulfil = squash(block(self.e, "gm_com_fulfil"))
        self.assertIn("set_variable = { name = gm_com_seized_state value = scope:gm_com_named_state }", fulfil)
        self.assertIn("set_variable = { name = gm_com_seized_source value = var:gm_com_source }", fulfil)
        self.assertIn("if = { limit = { is_ai = no } trigger_event = { id = monument_events.28 popup = yes } }", fulfil)
        self.assertNotIn("post_notification", fulfil)
        ev = squash(raw_block_at(self.events, r"(?m)^monument_events\.28\s*=\s*\{"))
        self.assertIn("event_image", ev)
        self.assertIn("var:gm_com_seized_state ?= { save_scope_as = monument_state }", ev)
        self.assertEqual(ev.count("default_option = yes"), 1)
        source_is = squash(block(self.t, "gm_com_source_is"))
        self.assertIn("NOT = { has_variable = gm_com_source } has_variable = gm_com_seized_source "
                      "var:gm_com_seized_source = flag:$SRC$", source_is)
        L = loc()
        for key in ("monument_events.28.t", "monument_events.28.d", "monument_events.28.d_unnamed",
                    "monument_events.28.a", "notification_gm_com_reminder_notice_name"):
            self.assertIn(key, L, key)
        self.assertIn("GetCustom('gm_com_boon_name')", L["monument_events.28.d"])


class ReviewFixTests(unittest.TestCase):
    """Fixes from the phase 2 review (2026-10-05)."""

    def test_a_revolution_does_not_record_its_regime(self):
        """A winning revolution keeps its own variables: one written through
        the war would hide the regime change the win brings."""
        body = squash(block(read(COM_EFFECTS), "gm_com_track_regime"))
        self.assertIn("if = { limit = { NOT = { has_variable = te_cw_role } is_revolutionary = no } "
                      "set_variable = { name = gm_regime_last value = var:gm_regime_now } }", body)

    def test_a_lost_monument_lowers_the_baseline(self):
        body = squash(block(read(COM_EFFECTS), "gm_com_check_progress"))
        lower = ("if = { limit = { var:gm_com_baseline > gm_com_fit_grandeur } "
                 "set_variable = { name = gm_com_baseline value = gm_com_fit_grandeur } }")
        met = "if = { limit = { var:gm_com_target <= gm_com_progress } gm_com_fulfil = yes }"
        self.assertIn(lower, body)
        self.assertIn(met, body)
        self.assertLess(body.find(lower), body.find(met))

    def test_progress_writes_no_variable_it_reads(self):
        """The policy buttons' tooltips walk the refresh without writing:
        a variable set and then read in gm_com_check_progress read as unset
        there and logged three errors a frame (gm_com_drop, 2026-10-07)."""
        body = squash(block(read(COM_EFFECTS), "gm_com_check_progress"))
        # Only the baseline, which acceptance already set, so a tooltip pass
        # reads the stored value.
        self.assertEqual(set(re.findall(r"set_variable = \{ name = (\w+)", body)), {"gm_com_baseline"})

    def test_a_vanished_state_lapses(self):
        self.assertIn("has_variable = gm_com_state NOT = { exists = var:gm_com_state }",
                      squash(block(read(COM_TRIGGERS), "gm_com_has_lapsed")))
        self.assertNotRegex(strip_comments(read(COM_EFFECTS)), r"var:gm_com_state = \{")

    def test_the_unveiling_keeps_a_commissions_name(self):
        unveil = squash(block(read(NAME_EFFECTS), "gm_state_unveil"))
        self.assertIn("NOT = { AND = { has_variable = gm_name_from_com gm_state_current_form_fits = yes } } } "
                      "gm_state_set_default_form = yes", unveil)
        self.assertIn("else_if = { limit = { NOT = { has_variable = gm_name_from_com } } "
                      "gm_state_set_namesake = { NAMESAKE = city } }", unveil)
        fits = squash(block(read(NAME_TRIGGERS), "gm_state_current_form_fits"))
        for form in list(FORMS) + list(BUILDING_FORMS.values()) + ["faith"]:
            self.assertIn(f"var:gm_form = flag:{form} gm_state_form_fits_{form} = yes", fits, form)

    def test_a_victory_name_needs_a_foreign_capital(self):
        custom = read(CUSTOM_LOC)
        for ctx in ("row", "evt"):
            family = squash(block(custom, f"gm_monument_name_{ctx}"))
            self.assertIn("var:gm_name_occasion = flag:victory gm_state_enemy_cap_is_foreign = yes } "
                          f"localization_key = gm_name_victory_{ctx}", family)
        foreign = squash(block(read(NAME_TRIGGERS), "gm_state_enemy_cap_is_foreign"))
        self.assertIn("exists = var:gm_name_enemy_cap", foreign)

    def test_name_events_check_the_owner(self):
        ev = squash(raw_block_at(read(EVENTS), r"(?m)^monument_events\.25\s*=\s*\{"))
        self.assertIn("save_scope_as = monument_owner", ev)
        self.assertEqual(ev.count("owner = scope:monument_owner"), 7, "every choice but Keep")

    def test_a_cession_clears_the_commission_mark(self):
        self.assertIn("gm_remove_state_var = { VAR = gm_unveiled_for_com }",
                      squash(block(read(EFFECTS), "gm_state_changed_hands")))

    def test_rename_waits_for_an_open_choice(self):
        self.assertIn("NOT = { has_variable = gm_name_choice_open }", squash(block(read(SGUIS), "gm_rename_sgui")))
        self.assertIn("set_variable = { name = gm_name_choice_open value = yes days = 90 }",
                      squash(block(read(NAME_EFFECTS), "gm_state_offer_name_choice")))
        ev = squash(raw_block_at(read(EVENTS), r"(?m)^monument_events\.25\s*=\s*\{"))
        self.assertIn("gm_remove_state_var = { VAR = gm_name_choice_open }", ev, "Keep clears it too")
        for name in ("gm_state_choose_namesake", "gm_state_choose_commission_name"):
            self.assertIn("gm_remove_state_var = { VAR = gm_name_choice_open }", squash(block(read(NAME_EFFECTS), name)))


# ==== v2 phase 2: names (§3) =========================================================
# form -> the skins that offer it ("generic" includes a monument with no skin
# yet). The five civic-progress forms belong to their dedication; "faith" to
# every faith skin. The plan's Task 7 table, which fixes the spec's §3.2 draft.
FORMS = {
    "column": ("generic", "heritage_latin", "heritage_greek", "heritage_slavonic"),
    "arch": ("generic", "heritage_latin"),
    "obelisk": ("generic",), "statue": ("generic",), "mausoleum": ("generic",),
    "gate": ("generic", "heritage_hebrew", "heritage_sanskrit", "heritage_avestan", "heritage_arabic",
             "heritage_chinese"),
    "hall": ("generic", "heritage_avestan", "heritage_arabic", "heritage_chinese", "heritage_norse"),
    # Generic dropped the tower (spec 2026-10-11 §2.2); the Gothic skin keeps it.
    "tower": ("heritage_gothic",),
    "forum": ("heritage_latin",), "pantheon": ("heritage_greek",), "stoa": ("heritage_greek",),
    "court": ("heritage_hebrew",), "pillar": ("heritage_hebrew", "heritage_sanskrit"),
    "stele": ("heritage_geez",), "memorial_church": ("heritage_slavonic",), "pagoda": ("heritage_chinese",),
    "round_tower": ("heritage_irish",), "high_cross": ("heritage_irish",),
    "pyramid": ("heritage_nahuatl", "heritage_mayan"), "rune_stone": ("heritage_norse",),
    "hall_of_fame": ("heritage_gothic",), "hill_shrine": ("heritage_prussian",), "rock_cut": ("heritage_aramaic",),
    # Added 2026-10-11 (§2.3).
    "menorah": ("heritage_hebrew",), "bell_tower": ("heritage_slavonic",),
    "rock_hewn_church": ("heritage_geez",), "sun_stone": ("heritage_nahuatl",), "stela": ("heritage_mayan",),
    "sacred_oak": ("heritage_prussian",), "colonnade": ("heritage_aramaic",),
}
# Forms no skin offers any more. An old monument keeps one, so its noun and its
# gm_form_name branch stay; its fit trigger and .24 option go.
RETIRED_FORMS = ("memorial",)
# skin -> its default form, the first of its row in the plan's table.
DEFAULT_FORM = {"generic": "column", "heritage_latin": "column", "heritage_greek": "pantheon",
                "heritage_hebrew": "gate", "heritage_sanskrit": "pillar", "heritage_geez": "stele",
                "heritage_slavonic": "memorial_church", "heritage_avestan": "gate", "heritage_arabic": "hall",
                "heritage_chinese": "hall", "heritage_irish": "round_tower", "heritage_nahuatl": "pyramid",
                "heritage_mayan": "pyramid", "heritage_norse": "rune_stone", "heritage_gothic": "hall_of_fame",
                "heritage_prussian": "hill_shrine", "heritage_aramaic": "rock_cut"}
BUILDING_FORMS = {"artistic": "opera_house", "naturalist": "gardens", "scientific": "observatory",
                  "industrial": "exhibition_hall", "athletic": "stadium"}
# The heritage styles each civic-progress building offers beyond generic (spec
# 2026-10-11 §2.4), in the revival partition's order (HERITAGES): the first is
# the most specific, so it is the AI's pick and comes first in .11.
BUILDING_SKINS = {
    "artistic": ("chinese", "greek"),
    "naturalist": ("avestan", "arabic", "chinese"),
    "scientific": ("sanskrit", "avestan", "chinese", "mayan"),
    "industrial": (),
    "athletic": ("latin", "greek", "nahuatl", "mayan"),
}
# namesake -> its pattern keys (gm_name_<pattern>_row / _evt).
NAMESAKES = {"city": ("city",), "state": ("state",), "ruler": ("ruler",), "honours": ("honours",),
             "year": ("year",),
             "occasion": ("victory", "defeat", "centenary", "space_orbital", "space_moon_landing",
                          "space_moon_base", "space_mars_landing", "space_interstellar_probe"),
             # A landmark's historical name (phase 4 §4).
             "landmark": ("landmark",)}
NAME_RECORDS = ("gm_namesake", "gm_name_year", "gm_name_char", "gm_name_occasion", "gm_name_enemy_cap",
                "gm_name_from_com")


class NameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = read(NAME_TRIGGERS)
        cls.e = read(NAME_EFFECTS)
        cls.events = read(EVENTS)
        cls.custom = read(CUSTOM_LOC)

    def test_every_skin_offers_a_form(self):
        offered = {skin for skins in FORMS.values() for skin in skins}
        for skin in SKINS:
            if not skin.startswith("faith_"):
                self.assertIn(skin, offered, skin)

    def test_form_triggers_match_the_table(self):
        for form, skins in FORMS.items():
            body = squash(block(self.t, f"gm_state_form_fits_{form}"))
            self.assertIsNotNone(body, form)
            self.assertIn("gm_state_takes_monument_forms = yes", body, form)
            listed = set(re.findall(r"SKIN = (\w+)", body))
            self.assertEqual(listed, set(skins), form)
        for key, form in BUILDING_FORMS.items():
            self.assertEqual(squash(block(self.t, f"gm_state_form_fits_{form}")),
                             f"gm_state_has_pm = {{ PM = pm_monument_{key} }}")

    def test_form_choice_lists_the_skins_with_two_or_more(self):
        counts = {}
        for skins in FORMS.values():
            for skin in skins:
                counts[skin] = counts.get(skin, 0) + 1
        choice = set(re.findall(r"SKIN = (\w+)", squash(block(self.t, "gm_state_has_form_choice"))))
        self.assertEqual(choice, {s for s, n in counts.items() if n > 1})

    def test_default_form_is_each_skins_first(self):
        body = squash(block(self.e, "gm_state_set_default_form"))
        self.assertEqual(set(DEFAULT_FORM), {s for skins in FORMS.values() for s in skins})
        self.assertTrue(body.startswith("set_variable = { name = gm_form value = flag:column }"))
        for skin, first in DEFAULT_FORM.items():
            self.assertIn(skin, FORMS[first], f"{skin}'s default {first} is not one of its forms")
            if first == "column":
                self.assertNotIn(f"SKIN = {skin} ", body, f"{skin} takes the column default")
            else:
                self.assertIn(f"gm_state_default_form_for_skin = {{ SKIN = {skin} FORM = {first} }}", body, skin)
        for key, form in BUILDING_FORMS.items():
            self.assertIn(f"pm_monument_{key} }} }} set_variable = {{ name = gm_form value = flag:{form} }}", body)

    def test_every_form_has_its_noun_and_option(self):
        L = loc()
        ev = squash(raw_block_at(self.events, r"(?m)^monument_events\.24\s*=\s*\{"))
        names = squash(block(self.custom, "gm_form_name"))
        for form in list(FORMS) + list(BUILDING_FORMS.values()):
            self.assertIn(f"gm_form_{form}", L, form)
            self.assertIn(f"var:gm_form = flag:{form} }} localization_key = gm_form_{form}", names, form)
        for form in FORMS:
            self.assertIn(f"name = monument_events.24.{form} trigger = {{ gm_state_form_fits_{form} = yes "
                          f"has_variable = gm_form NOT = {{ var:gm_form = flag:{form} }} owner = scope:monument_owner }} "
                          f"gm_state_choose_form = {{ FORM = {form} }}", ev)
            self.assertIn(f"monument_events.24.{form}", L, form)
        for faith in FAITHS:
            self.assertIn(f"var:gm_skin = flag:faith_{faith} }} localization_key = gm_skin_faith_{faith}", names)

    def test_retired_forms_keep_their_noun_only(self):
        L = loc()
        names = squash(block(self.custom, "gm_form_name"))
        ev = squash(raw_block_at(self.events, r"(?m)^monument_events\.24\s*=\s*\{"))
        com = squash(block(self.t, "gm_state_com_form_fits"))
        for form in RETIRED_FORMS:
            self.assertIn(f"gm_form_{form}", L, form)
            self.assertIn(f"var:gm_form = flag:{form} }} localization_key = gm_form_{form}", names, form)
            self.assertIsNone(block(self.t, f"gm_state_form_fits_{form}"), form)
            self.assertNotIn(f"monument_events.24.{form} ", ev + " ", form)
            self.assertNotIn(f"flag:{form} ", com, form)

    def test_current_form_check_knows_every_form(self):
        # gm_state_unveil keeps a commission's form only while it fits: a form
        # missing here reads as not fitting, and the unveiling resets it.
        cur = squash(block(self.t, "gm_state_current_form_fits"))
        for form in list(FORMS) + list(BUILDING_FORMS.values()) + ["faith"]:
            self.assertIn(f"var:gm_form = flag:{form} gm_state_form_fits_{form} = yes", cur, form)
        for form in RETIRED_FORMS:
            self.assertNotIn(f"flag:{form} ", cur, form)
        # No call to a fit trigger that no longer exists.
        for rel in (NAME_TRIGGERS, NAME_EFFECTS, EVENTS, EFFECTS):
            for form in RETIRED_FORMS:
                self.assertNotIn(f"gm_state_form_fits_{form} ", strip_comments(read(rel)), (rel, form))

    def test_commission_forms_fit_some_skin(self):
        com = squash(block(self.t, "gm_state_com_form_fits"))
        for s in COMMISSION_SOURCES:
            for begin in s.begins:
                form = re.search(r"FORM = (\w+)", begin).group(1)
                if form != "default":
                    self.assertIn(f"var:gm_com_form = flag:{form} }} gm_state_form_fits_{form} = yes", com, s.key)

    def test_every_namesake_has_both_patterns(self):
        L = loc()
        for ctx in ("row", "evt"):
            family = squash(block(self.custom, f"gm_monument_name_{ctx}"))
            for patterns in NAMESAKES.values():
                for pattern in patterns:
                    key = f"gm_name_{pattern}_{ctx}"
                    self.assertIn(f"localization_key = {key}", family, key)
                    self.assertIn(key, L, key)
            for key in (f"gm_name_custom_{ctx}", f"gm_name_skin_{ctx}"):
                self.assertIn(f"localization_key = {key}", family)
            # A target's ROOT is the state it was called on; a saved scope
            # (SCOPE.sState('monument_state')) comes back empty inside one
            # ("the HUB_NAME__city", monument_events.24, 2026-10-18).
            obj = "State" if ctx == "row" else "ROOT.GetState"
            for patterns in NAMESAKES.values():
                for pattern in patterns:
                    text = L[f"gm_name_{pattern}_{ctx}"]
                    other = r"(?<![\w.])State\.|SCOPE\." if ctx == "evt" else r"SCOPE\."
                    self.assertNotRegex(text.replace(obj, ""), other, f"gm_name_{pattern}_{ctx} reads another context")
        ev = squash(raw_block_at(self.events, r"(?m)^monument_events\.25\s*=\s*\{"))
        for namesake in ("city", "state", "ruler", "honours", "year"):
            self.assertIn(f"gm_state_choose_namesake = {{ NAMESAKE = {namesake} }}", ev, namesake)
        self.assertIn("gm_state_choose_commission_name = yes", ev)

    def test_name_events_have_a_default_and_an_image(self):
        for n in (24, 25):
            ev = squash(raw_block_at(self.events, rf"(?m)^monument_events\.{n}\s*=\s*\{{"))
            self.assertEqual(ev.count("default_option = yes"), 1, n)
            self.assertIn("event_image", ev)
            self.assertIn("save_scope_as = monument_state", ev)
        self.assertIn("name = monument_events.24.keep default_option = yes",
                      squash(raw_block_at(self.events, r"(?m)^monument_events\.24\s*=\s*\{")))
        self.assertIn("text = monument_events.25.keep_skin } default_option = yes",
                      squash(raw_block_at(self.events, r"(?m)^monument_events\.25\s*=\s*\{")))

    def test_keep_the_name_spells_out_each_pattern(self):
        # A customizable-localization target loses the event's saved scopes
        # (`SCOPE.sState(...)` is empty: "the HUB_NAME__city"), so #819 gave .25's
        # keep option one name per branch of gm_monument_name_evt, same triggers
        # in the same order, each splicing that branch's key into the option name
        # itself. The targets now read ROOT.GetState and need no saved scope, but
        # the splices stay: one name per branch also keeps the option's text in
        # step with the family.
        L = loc()
        family = strip_comments(block(self.custom, "gm_monument_name_evt"))
        branches = []
        for m in re.finditer(r"\btext\s*=\s*\{", family):
            body = _match_brace(family, m.end())
            trig = block(body, "trigger")
            key = re.search(r"localization_key\s*=\s*(\w+)", body).group(1)
            branches.append((squash(trig) if trig is not None else "always = yes", key))
        ev = strip_comments(raw_block_at(self.events, r"(?m)^monument_events\.25\s*=\s*\{"))
        keep = next(_match_brace(ev, m.end()) for m in re.finditer(r"\boption\s*=\s*\{", ev)
                    if "monument_events.25.keep_" in _match_brace(ev, m.end()))
        names = []
        for m in re.finditer(r"\bname\s*=\s*\{", keep):
            body = _match_brace(keep, m.end())
            names.append((squash(block(body, "trigger")), re.search(r"text\s*=\s*(\S+)", body).group(1)))
        self.assertEqual(len(names), len(branches))
        for (trig, key), (name_trig, text) in zip(branches, names):
            pattern = key.removeprefix("gm_name_").removesuffix("_evt")
            self.assertEqual(name_trig, trig, key)
            self.assertEqual(text, f"monument_events.25.keep_{pattern}", key)
            self.assertIn(f"${key}$", L[text], text)
        # No option name anywhere in the file reaches the family through GetCustom.
        for m in re.finditer(r"\boption\s*=\s*\{", strip_comments(self.events)):
            opt = _match_brace(strip_comments(self.events), m.end())
            for k in re.findall(r"\b(?:name|text)\s*=\s*([\w.]+)", opt):
                self.assertNotIn("GetCustom('gm_monument_name_evt')", L.get(k, ""), k)

    def test_the_unveiling_chain(self):
        e = read(EFFECTS)
        # Deferred to the refresh: the unveiling reads the production method the
        # dedication has only just activated.
        self.assertIn("NOT = { has_variable = gm_skin_axis } } set_variable = gm_unveil_pending }",
                      squash(block(e, "gm_state_offer_skins")))
        self.assertNotIn("gm_state_unveil = yes", squash(block(e, "gm_state_offer_skins")))
        self.assertIn("if = { limit = { has_variable = gm_unveil_pending } remove_variable = gm_unveil_pending "
                      "gm_state_unveil = yes } gm_state_name_if_unnamed = yes", squash(block(e, "gm_country_refresh")))
        self.assertIn("hidden_effect = { gm_state_unveil = yes }", squash(block(e, "gm_state_choose_skin")))
        unveil = squash(block(self.e, "gm_state_unveil"))
        self.assertIn("gm_state_set_default_form = yes", unveil)
        self.assertIn("owner = { is_ai = no } } gm_state_offer_name_choice = yes", unveil)
        self.assertIn("gm_state_name_if_unnamed = yes", squash(block(e, "gm_country_refresh")))

    def test_clear_state_forgets_the_name(self):
        clear = squash(block(read(EFFECTS), "gm_clear_state"))
        self.assertIn("gm_state_clear_namesake = yes", clear)
        for var in ("gm_form", "gm_name", "gm_unveiled_for_com"):
            self.assertIn(f"gm_remove_state_var = {{ VAR = {var} }}", clear)
        forget = squash(block(self.e, "gm_state_clear_namesake"))
        for var in NAME_RECORDS:
            self.assertIn(f"gm_remove_state_var = {{ VAR = {var} }}", forget, var)

    def test_the_commission_names_its_monument(self):
        take = squash(block(self.e, "gm_state_take_commission_name"))
        for var in ("gm_com_namesake", "gm_com_name_year", "gm_com_occasion", "gm_com_name_char",
                    "gm_com_name_enemy_cap"):
            self.assertIn(f"var:{var}", take, var)
        self.assertIn("gm_state_com_form_fits = yes", take, "the commission's form only when it fits the skin")
        fulfil = squash(block(read(COM_EFFECTS), "gm_com_fulfil"))
        # A petition (the city's name) does not overwrite a name already given (owner call, PR body).
        fulfil = squash(strip_comments(block(read(COM_EFFECTS), "gm_com_fulfil")))
        self.assertIn("NOT = { has_variable = gm_unveiled_for_com } gm_state_has_historical_name = no "
                      "NOT = { owner = { has_variable = gm_com_landmark } } "
                      "OR = { NOT = { has_variable = gm_namesake } "
                      "owner = { NOT = { var:gm_com_namesake = flag:city } } } } gm_state_take_commission_name = yes",
                      fulfil)

    def test_names_print_where_the_skin_did(self):
        L = loc()
        self.assertIn("GetCustom('gm_monument_name_row')", L["gm_row_title"])
        for n in (12, 13, 14, 15):
            self.assertIn("GetCustom('gm_monument_name_evt')", L[f"monument_events.{n}.d"], n)
            self.assertNotIn("gm_skin_name", L[f"monument_events.{n}.d"], n)



# ==== v2 phase 3: the monument policy (§5) ============================================
POLICY_EFFECTS = "common/scripted_effects/gm_policy_effects.txt"
POLICY_TRIGGERS = "common/scripted_triggers/gm_policy_triggers.txt"
MODIFIER_TYPES = "common/modifier_type_definitions/mod_entity_modifier_types.txt"
# policy -> its factor on each per-step value (§5), and gm_policy_upkeep's multiplier.
POLICIES = {
    "standard": {"standing": 1, "regime": 1, "tourism": 1, "local": 1, "upkeep": 0},
    "open": {"standing": 1, "regime": 1, "tourism": 1.5, "local": 1, "upkeep": 1},
    "ceremonial": {"standing": 1, "regime": 1.5, "tourism": 0.5, "local": 1, "upkeep": 0},
    "mothballed": {"standing": 0.5, "regime": 1, "tourism": 0.5, "local": 0.5, "upkeep": -1},
}
FACTOR_VALUES = {"standing": "gm_policy_factor_standing", "regime": "gm_policy_factor_regime",
                 "tourism": "gm_policy_factor_tourism", "local": "gm_policy_factor_local"}


def _policy_value(body, policy):
    """What a factor script value gives under `policy`: its first if/else_if
    whose limit names the policy, else its base value."""
    body = squash(body)
    base = float(re.match(r"value = (-?[\d.]+)", body).group(1))
    for m in re.finditer(r"(?:if|else_if) = \{ limit = \{(.*?)\} value = (-?[\d.]+) \}", body):
        if f"P = {policy} " in m.group(1):
            return float(m.group(2))
    return base


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = read(VALUES)
        cls.e = read(POLICY_EFFECTS)

    def test_factors_match_the_table(self):
        for policy, factors in POLICIES.items():
            for what, value_name in FACTOR_VALUES.items():
                body = block(self.values, value_name)
                self.assertIsNotNone(body, value_name)
                self.assertEqual(_policy_value(body, policy), factors[what], f"{policy} {what}")

    def test_upkeep_is_on_the_building(self):
        """The maintenance input is level_scaled, which throughput does not
        touch, so the policy scales the building's construction input (as the
        engine's pm_retooling does), on the monument only."""
        mods = read(MODIFIERS)
        for policy, factors in POLICIES.items():
            body = block(mods, f"gm_policy_upkeep_{policy}")
            if factors["upkeep"] == 0:
                self.assertIsNone(body, policy)
                continue
            self.assertAlmostEqual(number(body, "goods_input_construction_mult"), factors["upkeep"] * 0.5, msg=policy)
        self.assertNotIn("building_grand_monument_throughput_add", strip_comments(mods))
        local = squash(block(read(EFFECTS), "gm_remove_local_modifiers"))
        self.assertIn("b:building_grand_monument ?= { remove_modifier = gm_upkeep remove_modifier = gm_policy_upkeep_open "
                      "remove_modifier = gm_policy_upkeep_mothballed }", local)
        clear = squash(block(read(EFFECTS), "gm_clear_state"))
        self.assertIn("set_variable = { name = gm_local_tourism_steps value = 0 }", clear)
        self.assertNotRegex(strip_comments(read(EFFECTS)), r"remove_variable = gm_local_tourism_steps\b")

    def test_buttons_and_cooldown(self):
        sguis = read(SGUIS)
        for policy in POLICIES:
            body = squash(block(sguis, f"gm_policy_{policy}_sgui"))
            self.assertIsNotNone(body, policy)
            self.assertIn(f"NOT = {{ gm_policy_is = {{ P = {policy} STANDARD = "
                          f"{'yes' if policy == 'standard' else 'no'} }} }}", body)
            self.assertIn("gm_policy_can_change = yes", body)
            self.assertIn(f"custom_tooltip = {{ text = gm_policy_{policy}_effect_tt gm_policy_set = {{ P = {policy} }} }}",
                          body)
            self.assertIn("ai_is_valid = { always = no }", body)
            for key in (f"gm_policy_{policy}", f"gm_policy_effects_{policy}", f"gm_button_policy_{policy}",
                        f"gm_button_policy_{policy}_tooltip", f"gm_policy_{policy}_effect_tt"):
                self.assertIn(key, loc(), key)
        setter = squash(block(self.e, "gm_policy_set"))
        self.assertIn("has_variable = gm_policy_chosen } set_variable = { name = gm_policy_cooldown value = yes "
                      "months = 60 }", setter)
        self.assertIn("else = { set_variable = gm_policy_chosen }", setter, "the first choice is free")
        self.assertEqual(squash(block(read(POLICY_TRIGGERS), "gm_policy_can_change")),
                         "NOT = { has_variable = gm_policy_cooldown }")

    def test_the_ai(self):
        ai = squash(block(self.e, "gm_policy_ai_choose"))
        for s_ in ("is_ai = yes", "month = 0", "gm_policy_can_change = yes"):
            self.assertIn(s_, ai)
        self.assertLess(ai.find("flag:mothballed"), ai.find("flag:ceremonial"))
        self.assertLess(ai.find("flag:ceremonial"), ai.find("flag:open"))
        for policy in POLICIES:
            self.assertIn(f"gm_policy_ai_apply = {{ P = {policy} ", ai, policy)
        self.assertIn("gm_policy_ai_choose = yes", squash(block(read(EFFECTS), "gm_country_monthly")))

    def test_anniversaries(self):
        body = squash(block(read(ON_ACTIONS), "monument_events_on_action"))
        self.assertIn("800 = { modifier = { if = { limit = { gm_policy_is = { P = open STANDARD = no } } "
                      "multiply = 0.5 } } }", body)



# ==== v2 phase 2: typed names (§3.5) =================================================
CARRIER_COMPANY = "common/company_types/gm_name_carrier_company.txt"
CARRIER_BUILDING = "common/buildings/gm_name_carrier.txt"
NAMING_SGUIS = ("gm_name_start_sgui", "gm_name_mark_old_sgui", "gm_name_use_sgui", "gm_name_cancel_sgui",
                "gm_clear_name_sgui")


class TypedNameTests(unittest.TestCase):
    def test_the_carrier_company(self):
        company = squash(block(read(CARRIER_COMPANY), "company_gm_name_carrier"))
        self.assertIn("potential = { has_variable = gm_naming_active }", company)
        self.assertIn("ai_will_do = { always = no }", company)
        self.assertIn("building_types = { building_gm_name_carrier_anchor }", company)
        building = squash(block(read(CARRIER_BUILDING), "building_gm_name_carrier_anchor"))
        for s_ in ("buildable = no", "expandable = no", "downsizeable = no"):
            self.assertIn(s_, building)
        L = loc()
        for key in ("company_gm_name_carrier", "building_gm_name_carrier_anchor", "pm_gm_name_carrier_anchor",
                    "pmg_gm_name_carrier_anchor"):
            self.assertIn(key, L, key)

    def test_the_start_order(self):
        start = squash(block(read(SGUIS), "gm_name_start_sgui"))
        self.assertLess(start.find("set_variable = gm_naming_active"),
                        start.find("add_company = company_type:company_gm_name_carrier"),
                        "the company type's potential reads gm_naming_active")
        # A year, not a month: game time runs while the box is open.
        self.assertIn("set_variable = { name = gm_naming_open value = yes days = 365 }", start)
        self.assertIn("set_variable = { name = gm_naming_open value = yes days = 365 }",
                      squash(block(read(SGUIS), "gm_name_mark_old_sgui")), "the clock restarts as the line appears")
        self.assertIn("NOT = { has_variable = gm_name_carrier }", start, "one naming at a time")
        self.assertIn("gm_state_status_fits = yes", start, "a contested or heritage monument keeps its name")

    def test_every_naming_sgui_is_for_players(self):
        sguis = read(SGUIS)
        for name in NAMING_SGUIS:
            self.assertIn("ai_is_valid = { always = no }", squash(block(sguis, name)), name)

    def test_use_repeats_its_check(self):
        use = squash(block(read(SGUIS), "gm_name_use_sgui"))
        self.assertIn("if = { limit = { scope:gm_state = { has_variable = gm_being_named } } scope:gm_state = "
                      "{ set_variable = { name = gm_name value = scope:gm_name } } gm_name_carrier_close = yes }", use)

    def test_a_naming_is_never_orphaned(self):
        """The pulse that sweeps keeps running with no monument left, and a
        state that changes hands drops its naming mark, so the next owner's row
        is not stuck on a naming line."""
        self.assertIn("has_variable = gm_naming_active", squash(block(read(ON_ACTIONS), "gm_country_on_action")))
        for name in ("gm_state_changed_hands", "gm_clear_state"):
            self.assertIn("gm_remove_state_var = { VAR = gm_being_named }", squash(block(read(EFFECTS), name)), name)
        self.assertIn("has_variable = gm_being_named owner = { has_variable = gm_name_carrier }",
                      squash(block(read(VALUES), "gm_is_being_named")))

    def test_close_and_the_sweep(self):
        names = read(NAME_EFFECTS)
        close = squash(block(names, "gm_name_carrier_close"))
        for s_ in ("has_company = company_type:company_gm_name_carrier } remove_company",
                   "has_modifier = gm_name_carrier_slot } remove_modifier = gm_name_carrier_slot"):
            self.assertIn(s_, close)
        for var in ("gm_name_carrier", "gm_naming_active", "gm_naming_open", "gm_name_old"):
            self.assertIn(f"gm_remove_state_var = {{ VAR = {var} }}", close, var)
        self.assertIn("every_scope_state = { limit = { has_variable = gm_being_named } remove_variable = gm_being_named }",
                      close)
        sweep = squash(block(names, "gm_name_sweep"))
        self.assertIn("has_variable = gm_naming_active NOT = { has_variable = gm_naming_open } } "
                      "gm_name_carrier_close = yes", sweep)
        self.assertIn("gm_name_sweep = yes", squash(block(read(EFFECTS), "gm_country_monthly")))
        self.assertAlmostEqual(number(block(read(MODIFIERS), "gm_name_carrier_slot"), "country_max_companies_add"), 1)



# ---- A new monument copies its siblings' dedication (owner's France, 2026-10-08) -------

class CopiedDedicationTests(unittest.TestCase):
    """A new building starts on the production methods most of its owner's
    buildings of that type use, not on is_default: France's third monument
    stood at level 0 on To the Revolution, its two siblings' dedication, so no
    ceremony asked and the ratchet locked it. The lock binds the panel only,
    so the ceremony's answer replaces the copy, with one switch: two in one
    tick left a dedication listed twice in the save."""

    def setUp(self):
        self.e = read(EFFECTS)
        self.t = read(TRIGGERS)

    def test_the_answer_is_the_one_switch(self):
        self.assertNotIn("activate_production_method", squash(block(self.e, "gm_state_start_ceremony")))
        ev2 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.2\s*=\s*\{")))
        # An older save's monument, before its migration (SiteDedicationTests has the rest).
        self.assertIn("AND = { NOT = { has_variable = gm_ceremony_mode } has_building = building_grand_monument "
                      "NOT = { has_variable = gm_seen } }", ev2)
        self.assertNotIn("has_active_production_method = pm_monument_undedicated", ev2)
        immediate = ev2[ev2.find("immediate = {"):ev2.find("option = {")]
        self.assertNotIn("gm_state_undedicate", immediate)
        self.assertIn("gm_state_undedicate = yes", squash(block(self.e, "gm_state_ceremony_not_yet")))
        self.assertEqual(squash(block(self.e, "gm_state_undedicate")),
                         "if = { limit = { NOT = { gm_state_has_pm = { PM = pm_monument_undedicated } } } "
                         "activate_production_method = { building_type = building_grand_monument "
                         "production_method = pm_monument_undedicated } } "
                         "gm_remove_state_var = { VAR = gm_restore_pm } "
                         "set_variable = { name = gm_picture_code value = 1 } gm_state_picture_landmarks = yes")
        # One switch, past the lock, after the site's or Rededicate's records
        # (SiteDedicationTests); none on a building just created.
        self.assertIn("if = { limit = { NOT = { has_variable = gm_site_created } "
                      "NOT = { gm_state_has_pm = { PM = pm_monument_$KEY$ } } } "
                      "activate_production_method = { building_type = building_grand_monument "
                      "production_method = pm_monument_$KEY$ } }", squash(block(self.e, "gm_state_dedicate")))
        # Nothing switches a monument from a production-method hook.
        self.assertIsNone(block(read(ON_ACTIONS), "on_production_method_changed"))
        self.assertEqual(len(re.findall(r"activate_production_method\s*=", strip_comments(self.e))), 2,
                         "gm_state_undedicate and gm_state_dedicate are the only switches")

    def test_nothing_records_a_copy_the_ceremony_is_replacing(self):
        pending = "NOT = { has_variable = gm_ceremony_pending }"
        self.assertIn(pending, squash(block(self.e, "gm_state_first_sight")))
        self.assertIn(pending, squash(block(read(NAME_EFFECTS), "gm_state_name_if_unnamed")))
        self.assertIn("gm_state_is_bound = yes " + pending, squash(block(self.e, "gm_check_contests")))

    def test_reopen(self):
        text = read(DEBUG_EVENTS)
        self.assertRegex(text, r"(?m)^te_debug_monuments\.3 = \{ # REVIEWED \d{4}-\d{2}-\d{2}: console-only")
        ev3 = squash(strip_comments(raw_block_at(text, r"(?m)^te_debug_monuments\.3\s*=\s*\{")))
        for n, o in ((1, "a"), (2, "b"), (3, "c")):
            self.assertIn(f"name = te_debug_monuments.3.{o} ", ev3)
            self.assertIn(f"trigger = {{ exists = scope:gm_dbg_m{n} }} scope:gm_dbg_m{n} = {{ "
                          f"gm_state_rededicate = yes }}", ev3)
        # The re-open options are .3's alone (#817); .4 is the picture sweep (2026-10-11).
        ev4 = raw_block_at(text, r"(?m)^te_debug_monuments\.4\s*=\s*\{")
        self.assertNotIn("gm_clear_state", squash(strip_comments(ev4 or "")))
        L = loc()
        for k in ("t", "desc", "flavor", "a", "b", "c"):
            self.assertIn(f"te_debug_monuments.3.{k}", L)
        self.assertNotIn("te_debug_monuments.3.d", L)


# ==== Pictures (spec 2026-10-11 §3) =====================================================
PICTURE_EFFECTS = "common/scripted_effects/gm_picture_effects.txt"


def _reachable_pictures():
    """Every (skin, form, civic-progress dedication or None) a monument can
    reach, from the form and style tables: PICTURES must hold exactly these."""
    out = {("undedicated", None, None)}
    for form, skins in FORMS.items():
        for skin in skins:
            out.add((skin, form, None))
    for f in FAITHS:
        out.add((f"faith_{f}", "faith", None))
    for key, form in BUILDING_FORMS.items():
        out.add(("generic", form, key))
        for h in BUILDING_SKINS[key]:
            out.add((f"heritage_{h}", form, key))
    return out


# code -> (skin, form, civic-progress dedication or None). Written out and
# append-only (spec §3.2): a code never moves or is reused, so a new form or
# style takes the code after the highest in its block (generic 10-99; heritage
# 100 + 10 x its HERITAGE_SKINS index; faith 300-399; buildings 400 + 10 x its
# BUILDING_FORMS index). A retired pair keeps its entry, widget and helper
# line, and its code goes in RETIRED_PICTURES.
PICTURES = {
    1: ("undedicated", None, None),
    10: ("generic", "column", None),
    11: ("generic", "arch", None),
    12: ("generic", "obelisk", None),
    13: ("generic", "statue", None),
    14: ("generic", "gate", None),
    15: ("generic", "hall", None),
    16: ("generic", "mausoleum", None),
    100: ("heritage_latin", "column", None),
    101: ("heritage_latin", "arch", None),
    102: ("heritage_latin", "forum", None),
    110: ("heritage_hebrew", "gate", None),
    111: ("heritage_hebrew", "court", None),
    112: ("heritage_hebrew", "pillar", None),
    113: ("heritage_hebrew", "menorah", None),
    120: ("heritage_sanskrit", "pillar", None),
    121: ("heritage_sanskrit", "gate", None),
    130: ("heritage_geez", "stele", None),
    131: ("heritage_geez", "rock_hewn_church", None),
    140: ("heritage_slavonic", "memorial_church", None),
    141: ("heritage_slavonic", "column", None),
    142: ("heritage_slavonic", "bell_tower", None),
    150: ("heritage_avestan", "gate", None),
    151: ("heritage_avestan", "hall", None),
    160: ("heritage_arabic", "hall", None),
    161: ("heritage_arabic", "gate", None),
    170: ("heritage_chinese", "hall", None),
    171: ("heritage_chinese", "gate", None),
    172: ("heritage_chinese", "pagoda", None),
    180: ("heritage_greek", "pantheon", None),
    181: ("heritage_greek", "column", None),
    182: ("heritage_greek", "stoa", None),
    190: ("heritage_irish", "round_tower", None),
    191: ("heritage_irish", "high_cross", None),
    200: ("heritage_nahuatl", "pyramid", None),
    201: ("heritage_nahuatl", "sun_stone", None),
    210: ("heritage_norse", "rune_stone", None),
    211: ("heritage_norse", "hall", None),
    220: ("heritage_gothic", "hall_of_fame", None),
    221: ("heritage_gothic", "tower", None),
    230: ("heritage_mayan", "pyramid", None),
    231: ("heritage_mayan", "stela", None),
    240: ("heritage_prussian", "hill_shrine", None),
    241: ("heritage_prussian", "sacred_oak", None),
    250: ("heritage_aramaic", "rock_cut", None),
    251: ("heritage_aramaic", "colonnade", None),
    300: ("faith_catholic", "faith", None),
    301: ("faith_protestant", "faith", None),
    302: ("faith_orthodox", "faith", None),
    303: ("faith_oriental_orthodox", "faith", None),
    304: ("faith_sunni", "faith", None),
    305: ("faith_shiite", "faith", None),
    306: ("faith_ibadi", "faith", None),
    307: ("faith_jewish", "faith", None),
    308: ("faith_mahayana", "faith", None),
    309: ("faith_gelugpa", "faith", None),
    310: ("faith_theravada", "faith", None),
    311: ("faith_confucian", "faith", None),
    312: ("faith_hindu", "faith", None),
    313: ("faith_shinto", "faith", None),
    314: ("faith_sikh", "faith", None),
    315: ("faith_animist", "faith", None),
    400: ("generic", "opera_house", "artistic"),
    401: ("heritage_chinese", "opera_house", "artistic"),
    402: ("heritage_greek", "opera_house", "artistic"),
    410: ("generic", "gardens", "naturalist"),
    411: ("heritage_avestan", "gardens", "naturalist"),
    412: ("heritage_arabic", "gardens", "naturalist"),
    413: ("heritage_chinese", "gardens", "naturalist"),
    420: ("generic", "observatory", "scientific"),
    421: ("heritage_sanskrit", "observatory", "scientific"),
    422: ("heritage_avestan", "observatory", "scientific"),
    423: ("heritage_chinese", "observatory", "scientific"),
    424: ("heritage_mayan", "observatory", "scientific"),
    430: ("generic", "exhibition_hall", "industrial"),
    440: ("generic", "stadium", "athletic"),
    441: ("heritage_latin", "stadium", "athletic"),
    442: ("heritage_greek", "stadium", "athletic"),
    443: ("heritage_nahuatl", "stadium", "athletic"),
    444: ("heritage_mayan", "stadium", "athletic"),
    # The landmarks (phase 4 §5.1): LANDMARK_CODE_BASE + the LANDMARKS row number,
    # listed once its picture is drawn.
    1000001: ("landmark_arc_de_triomphe", "arch", None),
    1000002: ("landmark_alexander_column", "column", None),
    1000003: ("landmark_brandenburg_gate", "gate", None),
    1000004: ("landmark_washington_monument_baltimore", "column", None),
    1000005: ("landmark_la_scala", "opera_house", None),
    1000006: ("landmark_teatro_di_san_carlo", "opera_house", None),
    1000007: ("landmark_jantar_mantar", "observatory", None),
    1000008: ("landmark_shalimar_gardens", "gardens", None),
    1000009: ("landmark_jardim_botanico", "gardens", None),
    1000010: ("landmark_stelae_of_aksum", "stele", None),
    1000011: ("landmark_liberty_column", "obelisk", None),
    1000012: ("landmark_lion_monument", "statue", None),
    1000013: ("landmark_temple_of_heaven", "hall", None),
    1000014: ("landmark_topkapi_palace", "gate", None),
    1000015: ("landmark_golestan_palace", "hall", None),
    1000016: ("landmark_basilica_of_superga", "mausoleum", None),
    1000017: ("landmark_tomb_of_william_the_silent", "mausoleum", None),
    1000018: ("landmark_cenotaph_of_maximilian", "mausoleum", None),
    1000019: ("landmark_arco_de_santa_maria", "gate", None),
    1000020: ("landmark_statue_of_louis_xiv", "statue", None),
    1000021: ("landmark_lion_of_saint_mark", "column", None),
    1000022: ("landmark_sans_souci_palace", "hall", None),
    1000023: ("landmark_nikko_toshogu", "gate", None),
    1000024: ("landmark_parthenon", "pantheon", None),
    1000025: ("landmark_obelisks_of_karnak", "obelisk", None),
    1000026: ("landmark_royal_palace_of_benin", "hall", None),
    1000027: ("landmark_royal_palace_of_kumasi", "hall", None),
    1000028: ("landmark_bukgwan_victory_stele", "stele", None),
    1000029: ("landmark_imperial_city_of_hue", "gate", None),
    1000030: ("landmark_persepolis", "hall", None),
    1000031: ("landmark_red_fort", "gate", None),
    1000032: ("landmark_rosetta_stone", "stele", None),
    1000033: ("landmark_temple_of_dendera", "colonnade", None),
    1000034: ("landmark_luxor_obelisk", "obelisk", None),
    1000035: ("landmark_venus_de_milo", "statue", None),
    1000036: ("landmark_piraeus_lion", "statue", None),
    1000037: ("landmark_horses_of_saint_mark", "statue", None),
    1000038: ("landmark_tipus_tiger", "statue", None),
    1000039: ("landmark_baba_merzoug", "column", None),
    1000040: ("landmark_great_zimbabwe", "round_tower", None),
    1000041: ("landmark_royal_palaces_of_abomey", "hall", None),
    1000042: ("landmark_klungkung_palace", "gate", None),
    1000043: ("landmark_royal_palace_of_kandy", "hall", None),
    1000044: ("landmark_uffizi_gallery", "hall", None),
    1000045: ("landmark_capitoline_museums", "forum", None),
    1000046: ("landmark_bodrum_castle", "tower", None),
    1000047: ("landmark_temples_of_baalbek", "colonnade", None),
    1000048: ("landmark_palmyra", "colonnade", None),
    1000049: ("landmark_xanthos", "rock_cut", None),
    1000050: ("landmark_mesha_stele", "stele", None),
    1000051: ("landmark_arch_of_ctesiphon", "arch", None),
    1000052: ("landmark_nineveh_library", "hall", None),
    1000053: ("landmark_winged_victory_of_samothrace", "statue", None),
    1000054: ("landmark_vindolanda_tablets", "hall", None),
    1000055: ("landmark_troy_hisarlik", "gate", None),
    1000056: ("landmark_mycenae_grave_circle", "mausoleum", None),
    1000057: ("landmark_pergamon_altar", "pantheon", None),
    1000058: ("landmark_deir_el_bahari_cache", "rock_cut", None),
    1000059: ("landmark_ishtar_gate_babylon", "gate", None),
    1000060: ("landmark_palace_of_knossos", "hall", None),
    1000061: ("landmark_antikythera_mechanism", "statue", None),
    1000062: ("landmark_oseberg_ship", "statue", None),
    1000063: ("landmark_machu_picchu", "gate", None),
    1000064: ("landmark_bust_of_nefertiti", "statue", None),
    1000065: ("landmark_mohenjo_daro", "forum", None),
    1000066: ("landmark_tomb_of_tutankhamun", "mausoleum", None),
    1000067: ("landmark_royal_cemetery_at_ur", "mausoleum", None),
    1000068: ("landmark_sanxingdui_pits", "hall", None),
    1000069: ("landmark_sutton_hoo", "mausoleum", None),
    1000070: ("landmark_lascaux_caves", "rock_cut", None),
    1000071: ("landmark_nag_hammadi_library", "stele", None),
    1000072: ("landmark_dead_sea_scrolls", "stele", None),
    1000073: ("landmark_tomb_of_pakal", "pyramid", None),
    1000074: ("landmark_mawangdui_tombs", "mausoleum", None),
    1000075: ("landmark_terracotta_army", "mausoleum", None),
    1000076: ("landmark_tomb_of_philip_ii", "mausoleum", None),
    1000077: ("landmark_tomb_of_marquis_yi", "hall", None),
    1000078: ("landmark_royal_tombs_of_sipan", "pyramid", None),
    1000079: ("landmark_otzi_the_iceman", "statue", None),
    1000080: ("landmark_caral_supe", "pyramid", None),
    1000081: ("landmark_gobekli_tepe", "colonnade", None),
    1000082: ("landmark_olympia", "pantheon", None),
    1000083: ("landmark_delphi", "stoa", None),
    1000084: ("landmark_sidon_necropolis", "mausoleum", None),
    1000085: ("landmark_villa_of_the_papyri", "hall", None),
    1000086: ("landmark_tomb_of_alexander", "mausoleum", None),
    1000087: ("landmark_pompeii", "forum", None),
}
# Codes of pairs no monument can reach any more (a retired form or style).
RETIRED_PICTURES = set()
# The trophies' own pictures (2026-10-16): what a looter carried off, on display
# in a museum room, which a trophy's rows show over its monument's picture
# (gm_tr_trophy_picture, test_grand_monument_trophies.py). Code TROPHY_CODE_BASE
# + the landmark's LANDMARKS row, key trophy_<landmark key>; a landmark with
# none shows its monument's picture alone.
TROPHY_CODE_BASE = 2_000_000
TROPHY_PICTURES = {
    2000001: "trophy_arc_de_triomphe",
    2000002: "trophy_alexander_column",
    2000003: "trophy_brandenburg_gate",
    2000004: "trophy_washington_monument_baltimore",
    2000005: "trophy_la_scala",
    2000006: "trophy_teatro_di_san_carlo",
    2000007: "trophy_jantar_mantar",
    2000008: "trophy_shalimar_gardens",
    2000009: "trophy_jardim_botanico",
    2000010: "trophy_stelae_of_aksum",
    2000011: "trophy_liberty_column",
    2000012: "trophy_lion_monument",
    2000013: "trophy_temple_of_heaven",
    2000014: "trophy_topkapi_palace",
    2000015: "trophy_golestan_palace",
    2000016: "trophy_basilica_of_superga",
    2000017: "trophy_tomb_of_william_the_silent",
    2000018: "trophy_cenotaph_of_maximilian",
    2000019: "trophy_arco_de_santa_maria",
    2000020: "trophy_statue_of_louis_xiv",
    2000021: "trophy_lion_of_saint_mark",
    2000022: "trophy_sans_souci_palace",
    2000023: "trophy_nikko_toshogu",
    2000024: "trophy_parthenon",
    2000025: "trophy_obelisks_of_karnak",
    2000026: "trophy_royal_palace_of_benin",
    2000027: "trophy_royal_palace_of_kumasi",
    2000028: "trophy_bukgwan_victory_stele",
    2000029: "trophy_imperial_city_of_hue",
    2000030: "trophy_persepolis",
    2000031: "trophy_red_fort",
    2000032: "trophy_rosetta_stone",
    2000033: "trophy_temple_of_dendera",
    2000034: "trophy_luxor_obelisk",
    2000035: "trophy_venus_de_milo",
    2000036: "trophy_piraeus_lion",
    2000037: "trophy_horses_of_saint_mark",
    2000038: "trophy_tipus_tiger",
    2000039: "trophy_baba_merzoug",
    2000040: "trophy_great_zimbabwe",
    2000041: "trophy_royal_palaces_of_abomey",
    2000042: "trophy_klungkung_palace",
    2000043: "trophy_royal_palace_of_kandy",
    2000044: "trophy_uffizi_gallery",
    2000045: "trophy_capitoline_museums",
    2000046: "trophy_bodrum_castle",
    2000047: "trophy_temples_of_baalbek",
    2000048: "trophy_palmyra",
    2000049: "trophy_xanthos",
    2000050: "trophy_mesha_stele",
    2000051: "trophy_arch_of_ctesiphon",
    2000052: "trophy_nineveh_library",
    2000053: "trophy_winged_victory_of_samothrace",
    2000054: "trophy_vindolanda_tablets",
    2000055: "trophy_troy_hisarlik",
    2000056: "trophy_mycenae_grave_circle",
    2000057: "trophy_pergamon_altar",
    2000058: "trophy_deir_el_bahari_cache",
    2000059: "trophy_ishtar_gate_babylon",
    2000060: "trophy_palace_of_knossos",
    2000061: "trophy_antikythera_mechanism",
    2000062: "trophy_oseberg_ship",
    2000063: "trophy_machu_picchu",
    2000064: "trophy_bust_of_nefertiti",
    2000065: "trophy_mohenjo_daro",
    2000066: "trophy_tomb_of_tutankhamun",
    2000067: "trophy_royal_cemetery_at_ur",
    2000068: "trophy_sanxingdui_pits",
    2000069: "trophy_sutton_hoo",
    2000070: "trophy_lascaux_caves",
    2000071: "trophy_nag_hammadi_library",
    2000072: "trophy_dead_sea_scrolls",
    2000073: "trophy_tomb_of_pakal",
    2000074: "trophy_mawangdui_tombs",
    2000075: "trophy_terracotta_army",
    2000076: "trophy_tomb_of_philip_ii",
    2000077: "trophy_tomb_of_marquis_yi",
    2000078: "trophy_royal_tombs_of_sipan",
    2000079: "trophy_otzi_the_iceman",
    2000080: "trophy_caral_supe",
    2000081: "trophy_gobekli_tepe",
    2000082: "trophy_olympia",
    2000083: "trophy_delphi",
    2000084: "trophy_sidon_necropolis",
    2000085: "trophy_villa_of_the_papyri",
    2000086: "trophy_tomb_of_alexander",
    2000087: "trophy_pompeii",
}


def _frozen_problems(pictures, retired, reachable):
    """What breaks append-only: a retired code that isn't in the table, a live
    pair missing or extra, or a pair under two codes."""
    problems = [f"retired code {c} is not in PICTURES" for c in sorted(retired - set(pictures))]
    # A landmark's code follows its LANDMARKS row (LandmarkPictureTests).
    live = {c: v for c, v in pictures.items() if c not in retired and c < LANDMARK_CODE_BASE}
    if set(live.values()) != reachable:
        problems.append(f"live pictures differ from the reachable pairs: missing "
                        f"{sorted(map(str, reachable - set(live.values())))}, extra "
                        f"{sorted(map(str, set(live.values()) - reachable))}")
    if len(set(pictures.values())) != len(pictures):
        problems.append("a pair has two codes")
    return problems


def picture_key(code):
    skin, form, _ = PICTURES[code]
    return "undedicated" if skin == "undedicated" else f"{skin}__{form}"


def committed(rel):
    """Whether a texture is on disk or tracked by git. CI checks out without
    gfx/ (sparse), so a committed texture can be absent from the working tree
    (test_nuclear_deterrence.py's tracked())."""
    if (ROOT / rel).exists():
        return True
    return subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=ROOT, capture_output=True).returncode == 0


class PictureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = read(PICTURE_EFFECTS)
        # The table itself is gm_picture_from_look, which a trophy runs too
        # (gm_tr_update_picture, test_grand_monument_trophies.PictureTests).
        cls.body = squash(block(cls.e, "gm_picture_from_look"))

    def test_the_table(self):
        self.assertEqual(len(PICTURES), 167)
        # Every reachable pair has a picture.
        pairs = {(s, f) for code, (s, f, _) in PICTURES.items() if code != 1}
        for form, skins in FORMS.items():
            for skin in skins:
                self.assertIn((skin, form), pairs, (skin, form))
        # Fixed codes that must never move (append-only).
        self.assertEqual(picture_key(10), "generic__column")
        self.assertEqual(picture_key(102), "heritage_latin__forum")
        self.assertEqual(picture_key(300), "faith_catholic__faith")
        self.assertEqual(picture_key(444), "heritage_mayan__stadium")

    def test_a_retired_pair_keeps_its_code(self):
        # Spec §3.2: retiring a pair (Obelisk may merge into Column) keeps its
        # code, listed in RETIRED_PICTURES, so a save that stored it never
        # shows a blank (final review).
        reachable = _reachable_pictures() - {("generic", "obelisk", None)}
        self.assertEqual(_frozen_problems(PICTURES, {12}, reachable), [])
        self.assertTrue(_frozen_problems(PICTURES, set(), reachable), "an unlisted extra code is a problem")
        self.assertTrue(_frozen_problems(PICTURES, {999}, _reachable_pictures()), "a retired code must exist")

    def test_codes_are_frozen(self):
        # Append-only (spec §3.2): the table is written out, not computed from
        # the forms and styles, so inserting a style mid-list can't renumber
        # pictures a save has stored (Task 6 review).
        self.assertRegex(read("test_grand_monument_registry.py"), r"(?m)^PICTURES = \{\n    1: ")
        self.assertEqual(_frozen_problems(PICTURES, RETIRED_PICTURES, _reachable_pictures()), [])
        heritage_block = {f"heritage_{h}": b for b, h in enumerate(HERITAGE_SKINS)}
        building_block = {k: b for b, k in enumerate(BUILDING_FORMS)}
        for code, (skin, form, key) in PICTURES.items():
            if skin.startswith("landmark_"):
                self.assertEqual(LANDMARKS[code - LANDMARK_CODE_BASE - 1].key, skin.removeprefix("landmark_"), code)
            elif key is not None:
                self.assertEqual((code - 400) // 10, building_block[key], code)
            elif form == "faith":
                self.assertTrue(300 <= code < 400, code)
            elif skin == "generic":
                self.assertTrue(10 <= code < 100, code)
            elif skin != "undedicated":
                self.assertEqual((code - 100) // 10, heritage_block[skin], code)

    def test_helper_sets_every_code_in_order(self):
        self.assertEqual(squash(block(self.e, "gm_state_update_picture")),
                         "set_variable = { name = gm_picture_code value = 1 } if = { limit = { "
                         "gm_state_is_dedicated = yes has_variable = gm_form } gm_picture_from_look = yes } "
                         "gm_state_picture_landmarks = yes")
        b = self.body
        skins_start = b.index("gm_state_picture_skin =")
        pairs_start = b.index("gm_state_picture_pair =")
        buildings_start = b.index("gm_state_picture_building =")
        self.assertLess(skins_start, pairs_start, "skin defaults first: an unknown pair falls back to them")
        self.assertLess(pairs_start, buildings_start, "a building's lines last: its form outranks its skin")
        # The whole call list, in order: a duplicate with a wrong code, or a
        # building's generic line after its styles, would win in game.
        expected = []
        for skin, default in DEFAULT_FORM.items():
            code = next(c for c, (s, f, k) in PICTURES.items() if s == skin and f == default and k is None)
            expected.append(f"gm_state_picture_skin = {{ SKIN = {skin} GENERIC = "
                            f"{'yes' if skin == 'generic' else 'no'} CODE = {code} }}")
        codes = sorted(PICTURES)
        expected += [f"gm_state_picture_skin = {{ SKIN = {PICTURES[c][0]} GENERIC = no CODE = {c} }}"
                     for c in codes if PICTURES[c][1] == "faith"]
        expected += [f"gm_state_picture_pair = {{ SKIN = {PICTURES[c][0]} GENERIC = "
                     f"{'yes' if PICTURES[c][0] == 'generic' else 'no'} FORM = {PICTURES[c][1]} CODE = {c} }}"
                     for c in codes if c != 1 and PICTURES[c][2] is None and PICTURES[c][1] != "faith"
                     and c < LANDMARK_CODE_BASE]
        for c in codes:
            skin, form, key = PICTURES[c]
            if key is not None and skin == "generic":
                expected.append(f"gm_state_picture_building = {{ FORM = {form} CODE = {c} }}")
            elif key is not None:
                expected.append(f"gm_state_picture_building_skin = {{ FORM = {form} SKIN = {skin} CODE = {c} }}")
        self.assertEqual(re.findall(r"gm_state_picture_\w+ = \{[^{}]*\}", b), expected)

    def test_called_wherever_skin_or_form_changes(self):
        names = read(NAME_EFFECTS)
        for effect in ("gm_state_set_default_form", "gm_state_take_commission_name", "gm_state_unveil"):
            self.assertTrue(squash(block(names, effect)).endswith("gm_state_update_picture = yes"), effect)
        self.assertIn("set_variable = { name = gm_form value = flag:$FORM$ } gm_state_update_picture = yes",
                      squash(block(names, "gm_state_choose_form")))
        e = read(EFFECTS)
        self.assertIn("gm_state_name_if_unnamed = yes if = { limit = { NOT = { has_variable = gm_restore_pm } } "
                      "gm_state_update_picture = yes }",
                      squash(block(e, "gm_country_refresh")))
        self.assertIn("gm_remove_state_var = { VAR = gm_picture_code }", squash(block(e, "gm_clear_state")))

    def test_widget_has_every_picture(self):
        gui = read(WIDGET)
        # A GUI type header has no `=` before its brace: `type gm_picture = widget {`.
        raw = raw_block_at(gui, r"(?m)^\ttype gm_picture = widget \{")
        self.assertIsNotNone(raw)
        body = squash(strip_comments(raw))
        for code in PICTURES:
            self.assertIn(f"visible = \"[EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_disp_picture_code'), "
                          f"'(CFixedPoint){code}' )]\" size = {{ 100% 100% }} "
                          f"texture = \"gfx/interface/icons/gm_pictures/{picture_key(code)}.dds\"", body, code)
        self.assertEqual(body.count("ScriptValue('gm_disp_picture_code')"), len(PICTURES))

    def test_every_picture_has_its_art(self):
        import importlib
        import sys
        sys.path.insert(0, str(ROOT / "scripts" / "image_pipeline"))
        ip = importlib.import_module("icon_prompts")
        entries = ip.ICONS["gm_picture"]
        self.assertEqual(set(entries), {picture_key(c) for c in PICTURES} | set(TROPHY_PICTURES.values()))
        for key, entry in entries.items():
            self.assertEqual(entry["now"], "gfx/interface/icons/building_icons/building_grand_monument.dds", key)
            if isinstance(entry.get("seed"), int):
                self.assertTrue(committed(f"gfx/interface/icons/gm_pictures/{key}.dds"), key)

    def test_undedicating_drapes_it_at_once(self):
        # Not gm_state_update_picture: it would read back the PM this effect
        # has just activated (Task 6 review). Without this, a monument that
        # had a form keeps its old picture until the refresh.
        body = squash(block(read(EFFECTS), "gm_state_undedicate"))
        # A landmark keeps its own picture (phase 4 §5.1).
        self.assertTrue(body.endswith("set_variable = { name = gm_picture_code value = 1 } "
                                      "gm_state_picture_landmarks = yes"), body)

    def test_frame_tier_follows_the_grandeur_steps(self):
        # Spec §3.5: the frame shows the step the monument's effects have
        # reached, on the state card's own step list.
        # The local effects' 1/n curve (owner, 2026-10-19): its first five ends.
        values = read(VALUES)
        steps = [start + size for start, size in lin_curve_terms(5, 5)]
        self.assertEqual(steps, [5, 15, 30, 50, 75])
        expected = "value = 0 " + " ".join(f"if = {{ limit = {{ gm_state_grandeur >= {g} }} value = {i + 1} }}"
                                          for i, g in enumerate(steps))
        self.assertEqual(squash(block(values, "gm_disp_frame_tier")), expected)

    def test_frames_draw_over_the_pictures(self):
        raw = raw_block_at(read(WIDGET), r"(?m)^\ttype gm_picture = widget \{")
        body = squash(strip_comments(raw))
        last_picture = body.rindex("ScriptValue('gm_disp_picture_code')")
        for tier in range(1, 6):
            frame = (f"visible = \"[EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_disp_frame_tier'), "
                     f"'(CFixedPoint){tier}' )]\" size = {{ 100% 100% }} "
                     f"texture = \"gfx/interface/icons/gm_pictures/frames/frame_tier_{tier}.dds\"")
            self.assertIn(frame, body, tier)
            self.assertGreater(body.index(frame), last_picture, "a frame draws over every picture")
            self.assertTrue(committed(f"gfx/interface/icons/gm_pictures/frames/frame_tier_{tier}.dds"), tier)
        self.assertEqual(body.count("icon = {"), len(PICTURES) + 5)

    def test_display_value_defaults_to_the_draped_picture(self):
        v = squash(block(read(VALUES), "gm_disp_picture_code"))
        self.assertEqual(v, "value = 1 if = { limit = { has_variable = gm_picture_code } value = var:gm_picture_code }")


# ==== Phase 4: the landmarks standing in 1836 (spec 2026-10-12) ==========================
LANDMARK_EFFECTS = "common/scripted_effects/gm_landmark_effects.txt"


def landmark_seed_call(lm):
    return (f"gm_seed_landmark = {{ KEY = {lm.key} STATE = {lm.state} TAG = {lm.tag} "
            f"DEDICATION = {lm.dedication} FORM = {lm.form} LEVEL = {lm.level} BUILT = {BUILT[lm.key]} }}")


def vanilla_monuments():
    import json
    data = json.loads((ROOT / "vanilla_parsed/common/buildings.json").read_text(encoding="utf-8"))
    return {name for name, (_op, body) in data.items() if body.get("building_group") == ["=", "bg_monuments"]}


class LandmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = read(LANDMARK_EFFECTS)

    def test_the_table(self):
        keys = [lm.key for lm in LANDMARKS]
        self.assertEqual(len(keys), len(set(keys)))
        # One standing monument per state; an unplaced row shares its origin
        # state with whatever stands there (loot spec §2.2).
        states = [lm.state for lm in PLACED_LANDMARKS if not lm.beside]
        self.assertEqual(len(states), len(set(states)),
                         "one landmark per state (§2); a second is beside=True, after the first")
        for i, lm in enumerate(PLACED_LANDMARKS):
            if lm.beside:
                self.assertTrue(any(o.state == lm.state and not o.beside for o in PLACED_LANDMARKS[:i]),
                                f"{lm.key}: seeded beside a landmark that is seeded first")
        for lm in LANDMARKS:
            self.assertIn(lm.dedication, BY_KEY, lm.key)
            # A shrine's form is its faith's own building.
            self.assertTrue(lm.form in FORMS or lm.form in BUILDING_FORMS.values()
                            or (lm.form == "faith" and lm.dedication == "religious"), lm.key)
            if lm.form in BUILDING_FORMS.values():
                self.assertEqual(BUILDING_FORMS[lm.dedication], lm.form, f"{lm.key}: a building's own form")
            if lm.placed:
                self.assertGreaterEqual(lm.level, 5, lm.key)
            elif lm.year:
                # A historical opportunity's landmark: its level is the opportunity's target.
                self.assertIn(lm.level, (5, 10), lm.key)
                self.assertIsNone(lm.tag, f"{lm.key}: whoever completes it owns it")
            elif lm.buried:
                # A buried site (issue #939) is placed by an excavation, whoever owns the ground then:
                # a level of its own, no owner of its own.
                self.assertGreaterEqual(lm.level, 5, lm.key)
                self.assertIsNone(lm.tag, f"{lm.key}: a buried site has the owner who digs it")
            else:
                self.assertIsNone(lm.level, f"{lm.key}: an unplaced landmark's levels are its trophy's")

    def test_no_duplicate_of_a_base_game_monument_or_a_wonder(self):
        taken = vanilla_monuments()
        self.assertGreater(len(taken), 20, "the snapshot's bg_monuments")
        wonders = set(re.findall(r"(?m)^(building_wonder_\w+)\s*=", "\n".join(
            p.read_text(encoding="utf-8-sig") for p in (ROOT / "common/buildings").glob("*.txt"))))
        self.assertGreater(len(wonders), 20)
        for lm in LANDMARKS:
            self.assertNotIn(f"building_{lm.key}", taken, lm.key)
            self.assertNotIn(f"building_wonder_{lm.key}", wonders, lm.key)

    def test_seeded_once_after_the_lobby(self):
        on = read(ON_ACTIONS)
        self.assertIn("on_game_started_after_lobby = { on_actions = { gm_landmarks_on_game_started_after_lobby } }",
                      squash(strip_comments(on)))
        body = squash(block(on, "gm_landmarks_on_game_started_after_lobby"))
        self.assertEqual(body, "effect = { if = { limit = { gm_system_enabled = yes NOT = { has_global_variable = "
                               "gm_landmarks_seeded } } set_global_variable = gm_landmarks_seeded "
                               "gm_seed_landmarks = yes gm_seed_trophies = yes gm_monument_self_check = yes } }")

    def test_a_call_per_row(self):
        raw = (ROOT / LANDMARK_EFFECTS).read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "one BOM")
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf" * 2), "one BOM, not two")
        body = squash(block(self.e, "gm_seed_landmarks"))
        self.assertEqual(re.findall(r"gm_seed_landmark = \{[^{}]*\}", body),
                         [landmark_seed_call(lm) for lm in PLACED_LANDMARKS])

    def test_the_seed_writes_the_five_records(self):
        body = squash(block(self.e, "gm_seed_landmark"))
        self.assertIn("limit = { s:$STATE$.region_state:$TAG$ ?= { NOT = { has_building = building_grand_monument } } }",
                      body, "an owner that proves wrong, or a monument already there, places nothing")
        # At level 1, its size in its records (sites spec 2026-10-18 §3.5).
        self.assertIn("create_building = { building = building_grand_monument level = 1 "
                      "activate_production_methods = { pm_monument_$DEDICATION$ } }", body)
        for record in ("name = gm_landmark value = flag:$KEY$", "name = gm_skin value = flag:landmark_$KEY$",
                       "name = gm_form value = flag:$FORM$", "name = gm_namesake value = flag:landmark",
                       "name = gm_ceremony_level value = $LEVEL$"):
            self.assertIn(f"set_variable = {{ {record} }}", body, record)
        self.assertIn("set_variable = { name = gm_rebuilding days = 1 }", body, "no vanity for its own level")
        self.assertIn("owner = { trigger_event = { id = monument_events.20 } }", body)
        self.assertIn('else = { debug_log = "TE_MONUMENTS: landmark $KEY$ not placed', body)

    def test_the_lock_triggers(self):
        t = read(TRIGGERS)
        self.assertEqual(squash(block(t, "gm_state_is_landmark")), "has_variable = gm_landmark")
        self.assertEqual(squash(block(t, "gm_state_has_historical_name")),
                         "gm_state_is_landmark = yes gm_state_namesake_is = { NAMESAKE = landmark } "
                         "NOT = { has_variable = gm_name }")

    def test_its_name_and_history(self):
        L = loc()
        custom = read(CUSTOM_LOC)
        names = squash(block(custom, "gm_skin_name")).split("text = {")[1:]
        desc = squash(block(custom, "gm_landmark_desc"))
        evt = squash(block(custom, "gm_landmark_name_evt"))
        for i, lm in enumerate(LANDMARKS):
            self.assertIn(f"has_variable = gm_skin var:gm_skin = flag:landmark_{lm.key} }} "
                          f"localization_key = gm_skin_landmark_{lm.key}", names[i], lm.key)
            self.assertIn(f"gm_skin_landmark_{lm.key}", L)
            self.assertIn(f"has_variable = gm_landmark var:gm_landmark = flag:{lm.key} }} "
                          f"localization_key = gm_landmark_{lm.key}_desc", desc, lm.key)
            self.assertTrue(L[f"gm_landmark_{lm.key}_desc"].endswith("."), lm.key)
            self.assertIn(f"var:gm_skin = flag:landmark_{lm.key} }} localization_key = gm_landmark_{lm.key}_evt", evt)
            self.assertIn(f"$gm_skin_landmark_{lm.key}$", L[f"gm_landmark_{lm.key}_evt"], "spliced, never spelt")
        self.assertEqual(L["gm_skin_landmark_la_scala"], "La Scala")
        self.assertEqual(L["gm_landmark_la_scala_evt"], "$gm_skin_landmark_la_scala$")
        self.assertEqual(L["gm_landmark_arc_de_triomphe_evt"], "the $gm_skin_landmark_arc_de_triomphe$")
        # Not "the Washington Monument", which players read as the D.C. obelisk (owner, 2026-10-11).
        self.assertEqual(L["gm_skin_landmark_washington_monument_baltimore"], "Baltimore's Washington Monument")
        self.assertEqual(L["gm_landmark_washington_monument_baltimore_evt"],
                         "$gm_skin_landmark_washington_monument_baltimore$")


class LandmarkLockTests(unittest.TestCase):
    """Phase 4 §3.2: one test per writer the lock gates."""

    @classmethod
    def setUpClass(cls):
        cls.e = read(EFFECTS)
        cls.names = read(NAME_EFFECTS)

    def test_the_style_offer_leaves_a_landmark_alone(self):
        body = squash(block(self.e, "gm_state_offer_skins"))
        self.assertTrue(body.startswith("if = { limit = { gm_state_is_landmark = yes } set_variable = gm_unveil_pending } "
                                        "else = { set_variable = { name = gm_skin value = flag:generic } "
                                        "gm_state_offer_skins_$AXIS$ = yes"), body)
        self.assertTrue(body.endswith("owner = { trigger_event = { id = monument_events.20 } }"), body)

    def test_the_unveiling_keeps_its_form(self):
        unveil = squash(block(self.names, "gm_state_unveil"))
        self.assertTrue(unveil.startswith("if = { limit = { gm_state_is_landmark = no NOT = { AND = { has_variable = "
                                          "gm_name_from_com gm_state_current_form_fits = yes } } } "
                                          "gm_state_set_default_form = yes }"), unveil)
        offer = squash(block(self.names, "gm_state_offer_name_choice"))
        self.assertIn("limit = { gm_state_has_form_choice = yes gm_state_is_landmark = no } "
                      "trigger_event = { id = monument_events.24 popup = yes }", offer)
        unnamed = squash(block(self.names, "gm_state_name_if_unnamed"))
        self.assertIn("limit = { NOT = { has_variable = gm_form } gm_state_is_landmark = no } "
                      "gm_state_set_default_form = yes", unnamed)
        # A landmark skin offers no roster form, so no .24 and no commission form.
        for skins in FORMS.values():
            self.assertFalse([s for s in skins if s.startswith("landmark_")])

    def test_clear_state_keeps_the_look_only_for_rededicate(self):
        clear = squash(block(self.e, "gm_clear_state"))
        look = ("if = { limit = { NOT = { AND = { always = $KEEP_LANDMARK$ gm_state_is_landmark = yes } } } "
                "gm_remove_state_var = { VAR = gm_landmark } gm_remove_state_var = { VAR = gm_skin } "
                "gm_remove_state_var = { VAR = gm_form } gm_remove_state_var = { VAR = gm_picture_code } "
                "gm_remove_state_var = { VAR = gm_signature } gm_remove_state_var = { VAR = gm_sig_parent } }")
        self.assertIn(look, clear)
        for var in ("gm_landmark", "gm_skin", "gm_form", "gm_picture_code", "gm_signature", "gm_sig_parent"):
            self.assertEqual(clear.count(f"gm_remove_state_var = {{ VAR = {var} }}"), 1, var)
        calls = []
        for rel in [p.relative_to(ROOT).as_posix() for d in ("common", "events")
                    for p in (ROOT / d).rglob("*.txt")]:
            text = strip_comments(read(rel))
            for m in re.finditer(r"(?<![\w$])gm_clear_state\s*=\s*(\{[^{}]*\}|\w+)", text):
                calls.append((rel, squash(m.group(1))))
        self.assertGreaterEqual(len(calls), 6)
        for rel, arg in calls:
            self.assertIn(arg, ("{ KEEP_LANDMARK = yes }", "{ KEEP_LANDMARK = no }"), rel)
        self.assertEqual([a for _, a in calls].count("{ KEEP_LANDMARK = yes }"), 1)
        self.assertIn("gm_clear_state = { KEEP_LANDMARK = yes }", squash(block(self.e, "gm_state_apply_rededicate")))

    def test_renaming_waits_while_the_historical_name_stands(self):
        sguis = read(SGUIS)
        for name in ("gm_rename_sgui", "gm_name_start_sgui"):
            valid = squash(block(block(sguis, name), "is_valid"))
            self.assertIn("scope:gm_state = { owner = root custom_tooltip = { text = gm_sgui_rename_upheld_tt "
                          "gm_state_status_fits = yes } custom_tooltip = { text = gm_sgui_landmark_name_tt "
                          "gm_state_has_historical_name = no }", valid, name)
        self.assertIn("gm_sgui_landmark_name_tt", loc())

    def test_a_met_commission_keeps_a_historical_name(self):
        fulfil = squash(block(read(COM_EFFECTS), "gm_com_fulfil"))
        self.assertIn("NOT = { has_variable = gm_unveiled_for_com } gm_state_has_historical_name = no", fulfil)

    def test_the_ai_preserves_a_landmark_more_readily(self):
        ai = squash(block(self.e, "gm_ai_decide_contests"))
        self.assertIn("10 = { modifier = { if = { limit = { var:gm_grandeur >= 10 } add = 10 } "
                      "if = { limit = { gm_state_is_landmark = yes } multiply = 3 } } gm_state_preserve = yes }", ai)


class LandmarkNameTests(unittest.TestCase):
    """Phase 4 §3.3 and §4: its historical name, and a rededication's new one."""

    def test_the_historical_name_comes_before_the_year(self):
        L = loc()
        custom = read(CUSTOM_LOC)
        for ctx in ("row", "evt"):
            family = squash(block(custom, f"gm_monument_name_{ctx}"))
            branch = (f"text = {{ trigger = {{ gm_state_namesake_is = {{ NAMESAKE = landmark }} }} "
                      f"localization_key = gm_name_landmark_{ctx} }}")
            self.assertIn(branch, family, ctx)
            self.assertLess(family.index(branch), family.index(f"gm_name_year_{ctx}"), "never a year")
        self.assertEqual(L["gm_name_landmark_row"], "[State.GetCustom('gm_skin_name')]")
        self.assertEqual(L["gm_name_landmark_evt"], "[ROOT.GetState.GetCustom('gm_landmark_name_evt')]")

    def test_the_namesake_choice_offers_it_back(self):
        L = loc()
        ev = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.25\s*=\s*\{")))
        self.assertIn("name = monument_events.25.landmark trigger = { owner = scope:monument_owner "
                      "gm_state_is_landmark = yes NOT = { gm_state_namesake_is = { NAMESAKE = landmark } } } "
                      "gm_state_choose_namesake = { NAMESAKE = landmark }", ev)
        self.assertLess(ev.index("monument_events.25.landmark "), ev.index("monument_events.25.city "))
        self.assertIn("$gm_name_landmark_evt$", L["monument_events.25.landmark"])
        self.assertEqual(L["monument_events.25.keep_landmark"], "Keep the name: $gm_name_landmark_evt$")


def landmark_picture_code(lm):
    """Its own code once PICTURES lists its picture, else its stand-in pair's (§5.1)."""
    i = LANDMARKS.index(lm) + 1
    if PICTURES.get(LANDMARK_CODE_BASE + i) == (f"landmark_{lm.key}", lm.form, None):
        return LANDMARK_CODE_BASE + i
    skin, form = lm.standin
    return next(c for c, (s, f, _) in PICTURES.items() if (s, f) == (skin, form))


class LandmarkPictureTests(unittest.TestCase):
    def test_codes_follow_the_rows(self):
        for code, (skin, form, key) in PICTURES.items():
            if code >= LANDMARK_CODE_BASE:
                lm = LANDMARKS[code - LANDMARK_CODE_BASE - 1]
                self.assertEqual((skin, form, key), (f"landmark_{lm.key}", lm.form, None), code)

    def test_every_stand_in_has_a_picture(self):
        pairs = {(s, f) for s, f, _ in PICTURES.values()}
        for lm in LANDMARKS:
            self.assertIn(lm.standin, pairs, lm.key)

    def test_a_landmark_shows_its_picture_after_everything_else(self):
        e = read(PICTURE_EFFECTS)
        self.assertTrue(squash(block(e, "gm_state_update_picture")).endswith("gm_state_picture_landmarks = yes"),
                        "last: the building lines match on the form alone, and would overwrite it")
        body = squash(block(e, "gm_state_picture_landmarks"))
        self.assertEqual(re.findall(r"gm_state_picture_landmark = \{[^{}]*\}", body),
                         [f"gm_state_picture_landmark = {{ KEY = {lm.key} CODE = {landmark_picture_code(lm)} }}"
                          for lm in LANDMARKS])
        self.assertEqual(squash(block(e, "gm_state_picture_landmark")),
                         "if = { limit = { has_variable = gm_landmark var:gm_landmark = flag:$KEY$ } "
                         "set_variable = { name = gm_picture_code value = $CODE$ } }")


class LandmarkTechTests(unittest.TestCase):
    """Phase 4 §6: three dedications' technologies leave the production method."""



class LandmarkLineTests(unittest.TestCase):
    """Phase 4 §4: a landmark's line of history, on hover in its row and on its card."""

    VISIBLE = "[EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_disp_is_landmark'), '(CFixedPoint)1' )]"

    def test_the_toggle(self):
        self.assertEqual(squash(block(read(VALUES), "gm_disp_is_landmark")),
                         "value = 0 if = { limit = { gm_state_is_landmark = yes } value = 1 }")

    def test_row_and_card(self):
        row = squash(read(WIDGET))  # raw: strip_comments would eat "#tooltippable"
        self.assertIn(f'gm_row_line = {{ visible = "{self.VISIBLE}" default_format = "#tooltippable" '
                      f'tooltip = "gm_row_landmark_tt" text = "gm_row_landmark" }}', row)
        card = squash(read("gui/te_state_panel_widgets.gui"))
        self.assertIn(f'visible = "{self.VISIBLE}" autoresize = yes multiline = yes minimumsize = {{ 350 -1 }} '
                      f'maximumsize = {{ 350 -1 }} align = left|nobaseline using = fontsize_medium '
                      f'default_format = "#tooltippable" tooltip = "gm_row_landmark_tt" text = "gm_row_landmark"', card)
        L = loc()
        self.assertEqual(L["gm_row_landmark"], "Historical monument")
        self.assertIn("[State.GetCustom('gm_landmark_desc')]", L["gm_row_landmark_tt"])


class LandmarkDebugTests(unittest.TestCase):
    """Phase 4 §7: place the landmarks on an older save, and log them."""

    def test_the_debug_event(self):
        text = read(DEBUG_EVENTS)
        self.assertRegex(text, r"(?m)^te_debug_monuments\.5 = \{ # REVIEWED \d{4}-\d{2}-\d{2}: console-only")
        ev = squash(strip_comments(raw_block_at(text, r"(?m)^te_debug_monuments\.5\s*=\s*\{")))
        self.assertIn("name = te_debug_monuments.5.a gm_seed_landmarks = yes", ev,
                      "the seeding's own checks: the owner matches and no monument stands there")
        self.assertIn("name = te_debug_monuments.5.b default_option = yes gm_debug_log_landmarks = yes", ev)
        L = loc()
        for k in ("t", "desc", "flavor", "a", "b"):
            self.assertIn(f"te_debug_monuments.5.{k}", L)

    def test_a_log_line_per_landmark(self):
        e = read(LANDMARK_EFFECTS)
        body = squash(block(e, "gm_debug_log_landmarks"))
        self.assertEqual(re.findall(r"gm_debug_log_landmark = \{[^{}]*\}", body),
                         [f"gm_debug_log_landmark = {{ KEY = {lm.key} }}" for lm in LANDMARKS])
        one = squash(block(e, "gm_debug_log_landmark"))
        for v in ("gm_state_grandeur", "gm_status_code", "gm_disp_picture_code"):
            self.assertIn(f"[SCOPE.ScriptValue('{v}')|0]", one, v)
        for d in DEDICATIONS:
            self.assertIn(f"gm_debug_log_landmark_pm = {{ KEY = $KEY$ PM = {d.key} }}", one, d.key)
        self.assertIn("gm_debug_log_landmark_pm = { KEY = $KEY$ PM = undedicated }", one)
        self.assertNotIn(".MakeScope", one, "debug_log's working form only")


class LandmarkReviewFixTests(unittest.TestCase):
    """The final review's findings (phase 4)."""

    def test_demolition_ends_a_landmark_without_records(self):
        # I2: a rededicated landmark left undedicated has no gm_seen; demolished
        # from the panel it must still lose its lock, or the next monument in
        # the state reads as the landmark (§8.6).
        monthly = squash(block(read(EFFECTS), "gm_state_monthly"))
        # (A building lost with its records standing is put back, LostBuildingTests.)
        self.assertIn("else = { if = { limit = { OR = { has_variable = gm_seen gm_state_is_landmark = yes } } "
                      "if = { limit = { gm_state_lost_building = yes } trigger_event = { id = monument_events.29 } } "
                      "else = { if = { limit = { gm_state_is_contested = yes NOT = { has_variable = gm_carried_off } } "
                      "gm_state_record_teardown = yes } gm_clear_state = { KEEP_LANDMARK = no } } }", monthly)

    def test_the_seed_writes_its_records_before_the_building(self):
        # I3: if create_building fires on_building_built at once, monument_events.1
        # must already see gm_rebuilding and gm_ceremony_level (no vanity, no copy).
        body = squash(block(read(LANDMARK_EFFECTS), "gm_seed_landmark"))
        build = body.index("create_building")
        for record in ("name = gm_rebuilding days = 1", "name = gm_landmark value", "name = gm_skin value",
                       "name = gm_form value", "name = gm_namesake value", "name = gm_ceremony_level value"):
            self.assertLess(body.index(record), build, record)


# ---- Several monuments in one state (spec 2026-10-13-multiple-monuments-per-state) ----

MON_EFFECTS = "common/scripted_effects/gm_monument_effects.txt"
MON_TRIGGERS = "common/scripted_triggers/gm_monument_triggers.txt"
MON_VALUES = "common/script_values/gm_monument_values.txt"
MON_ON_ACTIONS = "common/on_actions/gm_monument_on_actions.txt"


class MultiMonumentDataTests(unittest.TestCase):
    """Task 1: the primary monument stays on the state's variables; every other
    monument standing in the state is a gm_monument container (a returned
    trophy keeps its gm_tr_* records), listed in the global gm_monuments and,
    by the monthly pass, in its state's gm_monuments_here."""

    def test_a_secondarys_grandeur_is_its_levels_and_age(self):
        body = squash(block(read(MON_VALUES), "gm_mon_grandeur"))
        self.assertEqual(body, "value = gm_mon_start add = gm_mon_age")

    def test_the_state_sums_its_secondaries_from_the_list(self):
        body = squash(block(read(MON_VALUES), "gm_state_secondary_grandeur"))
        self.assertEqual(body, "value = 0 if = { limit = { has_variable_list = gm_monuments_here } "
                               "every_in_list = { variable = gm_monuments_here add = gm_mon_grandeur } }")

    def test_the_primary_is_what_the_building_holds_beyond_them(self):
        body = squash(block(read(MON_VALUES), "gm_state_built_levels"))
        self.assertIn("value = gm_state_level subtract = gm_state_secondary_levels min = 1", body)
        # No building, no monument: the floor of 1 must not invent one.
        self.assertIn("if = { limit = { NOT = { has_building = building_grand_monument } } value = 0 }", body)

    def test_the_count_is_the_primary_and_the_list(self):
        body = squash(block(read(MON_VALUES), "gm_state_monument_count"))
        self.assertIn("if = { limit = { has_building = building_grand_monument } add = 1 }", body)
        self.assertIn("every_in_list = { variable = gm_monuments_here add = 1 }", body)
        self.assertIn("has_variable_list = gm_monuments_here", body)

    def test_a_state_with_a_secondary(self):
        body = squash(block(read(MON_TRIGGERS), "gm_state_has_secondary"))
        self.assertIn("has_variable_list = gm_monuments_here", body)
        # Not variable_list_size: its documented `target` key fails to load in 1.14
        # (un_lobby_list_has_entries), and a list outlives its last entry.
        self.assertIn("any_in_list = { variable = gm_monuments_here exists = this }", body)
        self.assertNotIn("variable_list_size", body)

    def test_the_pass_clears_before_it_lists(self):
        pass_ = squash(block(read(MON_EFFECTS), "gm_monument_pass"))
        self.assertLess(pass_.find("clear_variable_list = gm_monuments_here"), pass_.find("gm_mon_list_one = yes"))
        self.assertIn("remove_variable = gm_mon_here_count", pass_)
        one = squash(block(read(MON_EFFECTS), "gm_mon_list_one"))
        self.assertIn("add_to_variable_list = { name = gm_monuments_here target = scope:gm_mon_listing }", one)
        self.assertIn("var:gm_tr_origin", one)

    def test_the_pass_repairs_a_vanished_state_from_its_region(self):
        monthly = squash(block(read(MON_EFFECTS), "gm_monument_monthly"))
        self.assertIn("gm_system_enabled = yes", monthly)
        self.assertIn("every_in_global_list = { variable = gm_monuments gm_tr_repair_places = yes "
                      "gm_tr_update_picture = yes ", monthly)
        self.assertLess(monthly.find("gm_tr_repair_places = yes"), monthly.find("gm_monument_pass = yes"))

    def test_the_pass_has_nothing_to_do_in_a_game_with_no_secondary(self):
        monthly = squash(block(read(MON_EFFECTS), "gm_monument_monthly"))
        self.assertIn("has_global_variable_list = gm_monuments", monthly)
        self.assertIn("has_global_variable = gm_mon_lists_written", monthly)

    def test_wired_to_the_global_pulse(self):
        oa = squash(strip_comments(read(MON_ON_ACTIONS)))
        self.assertIn("on_monthly_pulse = { on_actions = { gm_monument_monthly_on_action } }", oa)
        self.assertIn("effect = { gm_monument_monthly = yes }", oa)

    def test_new_files_carry_one_bom(self):
        for rel in (MON_EFFECTS, MON_TRIGGERS, MON_VALUES, MON_ON_ACTIONS):
            raw = (ROOT / rel).read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), rel)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"), rel)


class MultiMonumentLevelTests(unittest.TestCase):
    """Task 2: the building's level is what everything standing there adds up
    to, its dedication the primary's. Every reader that means "this monument's
    own" reads gm_state_primary_grandeur; every rebuild keeps the secondaries'
    levels; a primary that goes hands the building to the largest secondary."""

    def setUp(self):
        self.e = read(EFFECTS)
        self.v = read(VALUES)
        self.tr = read("common/scripted_effects/gm_trophy_effects.txt")

    def test_the_dedications_sums_read_the_primarys_own_grandeur(self):
        for name in ("gm_sum_regime", "gm_sum_leader", "gm_sum_religious", "gm_sum_war_memorial",
                     "gm_sum_artistic", "gm_sum_scientific", "gm_sum_industrial"):
            body = squash(block(self.v, name))
            self.assertIn("add = gm_state_primary_grandeur", body, name)
            self.assertNotIn("add = gm_state_grandeur", body, name)

    def test_standing_counts_every_secondary_even_under_a_contested_primary(self):
        # A secondary's own contest takes it out (spec 2026-10-16 §4.2); its
        # primary's does not.
        body = squash(block(self.v, "gm_sum_standing"))
        self.assertIn("limit = { gm_state_counts_standing = yes } add = gm_state_primary_grandeur", body)
        self.assertIn("variable = gm_monuments_held limit = { gm_mon_counts_standing = yes } add = gm_mon_grandeur", body)
        self.assertNotIn("gm_state_is_contested", squash(block(read(MON_TRIGGERS), "gm_mon_counts_standing")))
        self.assertTrue(body.endswith("add = gm_tr_disp_held_grandeur"))

    def test_rededicate_costs_the_primarys_levels(self):
        body = squash(block(self.v, "gm_state_rededicate_cost"))
        self.assertEqual(body, "value = gm_state_primary_levels multiply = 500")

    def test_the_opportunity_counts_the_primarys_levels(self):
        body = squash(block(read("common/script_values/gm_commission_values.txt"), "gm_com_fit_grandeur"))
        # Its starting grandeur (Plan B), which reads its records.
        self.assertIn("add = gm_state_primary_start", body)

    def test_no_record_of_a_level_reads_the_whole_building(self):
        for rel in (EFFECTS, "common/scripted_effects/gm_trophy_effects.txt",
                    "common/scripted_effects/gm_commission_effects.txt", EVENTS):
            text = squash(strip_comments(read(rel)))
            self.assertNotIn("name = gm_grandeur value = gm_state_grandeur", text, rel)
            self.assertNotIn("name = gm_ceremony_level value = gm_state_grandeur", text, rel)

    def test_the_gift_lands_on_the_primarys_age(self):
        gift = squash(block(read("common/scripted_effects/gm_commission_effects.txt"), "gm_state_gift_grandeur"))
        self.assertIn("gm_state_add_age = { AGE = gm_com_gift }", gift)

    def test_a_primary_that_goes_hands_the_building_on(self):
        for name, body in (("gm_state_tear_down", block(self.e, "gm_state_tear_down")),
                           ("gm_state_tr_remove_whole", block(self.tr, "gm_state_tr_remove_whole"))):
            body = squash(body)
            # The building stays for the monument that rises (NoRebuildTests).
            self.assertIn("if = { limit = { gm_state_has_secondary = yes } gm_state_promote_secondary = yes } "
                          "else = {", body, name)
            self.assertLess(body.find("gm_state_promote_secondary = yes"),
                            body.find("remove_building = building_grand_monument"), name)

    def test_promotion_builds_the_largest_at_all_that_remains(self):
        body = squash(block(read(MON_EFFECTS), "gm_state_promote_secondary"))
        # Under a marker, as Rededicate is: a tooltip walks the effect without writing.
        self.assertTrue(body.startswith("set_variable = gm_promote_click if = { limit = { has_variable = gm_promote_click } "
                                        "remove_variable = gm_promote_click"))
        self.assertIn("ordered_in_list = { variable = gm_monuments_here order_by = gm_mon_grandeur position = 0 "
                      "check_range_bounds = no save_scope_as = gm_mon_promoted }", body)
        self.assertNotIn("gm_rebuild_level", body)
        self.assertIn("remove_list_global_variable = { name = gm_monuments target = scope:gm_mon_promoted }", body)
        self.assertLess(body.find("remove_list_global_variable"), body.find("destroy_container = yes"))
        # It is rebuilt as a return with no building is: its records onto the state.
        self.assertIn("scope:gm_mon_promoted = { save_scope_as = gm_tr_moving }", body)
        self.assertLess(body.find("remove_list_global_variable"), body.find("gm_state_tr_rebuild_from_moving = yes"))

    def test_the_pass_promotes_a_state_left_with_no_building(self):
        body = squash(block(read(MON_EFFECTS), "gm_monument_pass"))
        self.assertIn("every_state = { limit = { gm_state_has_secondary = yes "
                      "NOT = { has_building = building_grand_monument } } gm_state_promote_secondary = yes }", body)
        self.assertLess(body.find("gm_mon_list_one = yes"), body.find("gm_state_promote_secondary = yes"))

    def test_a_return_adds_levels_where_a_building_stands_and_rebuilds_where_none(self):
        body = squash(block(self.tr, "gm_state_tr_receive"))
        self.assertIn("if = { limit = { has_building = building_grand_monument } ", body)
        self.assertNotIn("gm_state_tr_add_levels", body)
        self.assertIn("else = { gm_state_tr_rebuild_from_moving = yes }", body)
        self.assertTrue(body.endswith("owner = { trigger_event = { id = monument_events.20 } }"))



class ColocatedLandmarkTests(unittest.TestCase):
    """Task 7: a second landmark in a state another stands in is stood beside
    it as a secondary monument (the Obelisks of Karnak and, home again, the
    Luxor Obelisk), not skipped, and never a second building."""

    def setUp(self):
        self.e = read(LANDMARK_EFFECTS)

    def test_a_held_state_with_a_building_stands_it_beside(self):
        body = squash(block(self.e, "gm_seed_landmark"))
        self.assertIn("else_if = { limit = { s:$STATE$.region_state:$TAG$ ?= { has_building = building_grand_monument "
                      "NOT = { gm_state_has_landmark = { KEY = $KEY$ } } } } "
                      "s:$STATE$.region_state:$TAG$ = { gm_seed_landmark_beside = { KEY = $KEY$ FORM = $FORM$ "
                      "DEDICATION = $DEDICATION$ LEVEL = $LEVEL$ BUILT = $BUILT$ } } }", body)
        # The old else is still the one that says nothing was placed.
        self.assertIn('else = { debug_log = "TE_MONUMENTS: landmark $KEY$ not placed', body)

    def test_the_beside_seed_is_a_monument_container_with_the_landmarks_records(self):
        body = squash(block(read(MON_EFFECTS), "gm_seed_landmark_beside"))
        self.assertIn("create_container = { tags = { gm_monument } save_scope_as = gm_tr_moving", body)
        for record in ("name = gm_tr_levels value = $LEVEL$", "name = gm_tr_dedication value = flag:$DEDICATION$",
                       "name = gm_tr_skin value = flag:landmark_$KEY$", "name = gm_tr_form value = flag:$FORM$",
                       "name = gm_tr_landmark value = flag:$KEY$", "name = gm_tr_namesake value = flag:landmark",
                       # A whole landmark: its row's title is its name, not "<name> - <part>".
                       "name = gm_tr_share value = flag:whole"):
            self.assertIn(f"set_variable = {{ {record} }}", body, record)
        # Its levels go on the building before it is listed, as a return's do.
        self.assertLess(body.find("gm_state_tr_add_levels = yes"),
                        body.find("add_to_variable_list = { name = gm_monuments_here"))
        for line in ("add_to_global_variable_list = { name = gm_monuments target = scope:gm_tr_moving }",
                     "set_variable = { name = gm_tr_origin value = scope:gm_mon_seed_state }",
                     "set_variable = { name = gm_tr_origin_region value = scope:gm_mon_seed_state.state_region }",
                     "set_variable = { name = gm_tr_site value = scope:gm_mon_seed_state }",
                     "gm_tr_update_picture = yes"):
            self.assertIn(line, body)
        self.assertIn("if = { limit = { exists = scope:gm_tr_moving }", body)
        self.assertNotIn("create_building", body, "the state's one building takes the levels")

    def test_a_landmark_stands_in_a_state_as_the_primary_or_a_secondary(self):
        body = squash(block(read(MON_TRIGGERS), "gm_state_has_landmark"))
        self.assertIn("AND = { has_variable = gm_landmark var:gm_landmark = flag:$KEY$ }", body)
        self.assertIn("any_in_list = { variable = gm_monuments_here has_variable = gm_tr_landmark "
                      "var:gm_tr_landmark = flag:$KEY$ }", body)

    def test_upper_egypt_starts_with_karnak_alone(self):
        rows = [lm for lm in PLACED_LANDMARKS if lm.state == "STATE_UPPER_EGYPT"]
        self.assertEqual([lm.key for lm in rows], ["obelisks_of_karnak"])
        self.assertFalse(rows[0].beside)


class MultiMonumentSelfCheckTests(unittest.TestCase):
    """The build rests on an engine fact nobody has verified: that
    `var:gm_landmark = scope:gm_tr_moving.var:gm_tr_landmark` compares two
    flags across scopes. A game logs once, after the seeding, what the 1836
    data says it should (docs/testing/grand-monuments-multiple-playtest.md,
    Self-checks); the fallback is named there."""

    def setUp(self):
        self.body = squash(block(read(MON_EFFECTS), "gm_monument_self_check"))

    def test_both_verdicts_for_both_cases(self):
        for name in ("monument_piece_rejoins", "monument_artifact_stands_apart"):
            self.assertIn(f"TE_SELF_CHECK OK {name}", self.body)
            self.assertIn(f"TE_SELF_CHECK BROKEN {name}", self.body)

    def test_a_degenerate_premise_logs_nothing(self):
        # The marbles read against Attica's Parthenon, the Luxor Obelisk against
        # Upper Egypt's Obelisks of Karnak; with either absent, no verdict.
        self.assertIn("var:gm_tr_landmark = flag:parthenon", self.body)
        self.assertIn("var:gm_landmark = flag:parthenon", self.body)
        self.assertIn("var:gm_tr_landmark = flag:luxor_obelisk", self.body)
        self.assertIn("var:gm_landmark = flag:obelisks_of_karnak", self.body)
        self.assertEqual(self.body.count("has_building = building_grand_monument"), 2)

    def test_the_rule_is_read_through_the_triggers_the_return_uses(self):
        self.assertIn("gm_tr_rejoins_primary = yes", self.body)
        self.assertIn("gm_tr_stands_apart = yes", self.body)
        self.assertIn("save_scope_as = gm_tr_moving", self.body)

    def test_the_broken_line_names_its_fallback(self):
        self.assertIn("docs/testing/grand-monuments-multiple-playtest.md", self.body)
        self.assertTrue((ROOT / "docs/testing/grand-monuments-multiple-playtest.md").exists())


class ReviewFixes20261016Tests(unittest.TestCase):
    """The review of several monuments in one state (2026-10-16; spec
    docs/superpowers/archive/specs/2026-10-16-grand-monument-ageing-design.md §0.5)."""

    TR = "common/scripted_effects/gm_trophy_effects.txt"
    ARCH = "common/scripted_effects/gm_archaeology_effects.txt"
    COM = "common/scripted_effects/gm_commission_effects.txt"

    def test_a_dig_in_a_state_rebuilt_today_waits_a_month(self):
        finish = squash(strip_comments(block(read(self.ARCH), "gm_arch_finish")))
        # The terms (#965's partage) wait with it, so a piece is shipped once.
        self.assertIn("scope:gm_arch_dig_state = { NOT = { has_variable = gm_rebuilding } } } "
                      "gm_arch_settle_levels = yes gm_arch_settle_terms = yes gm_arch_place = yes", finish)

    def test_the_occupiers_roll_sees_a_secondary_beside_an_untakeable_primary(self):
        # Finding 2.
        gate = squash(block(read(MON_TRIGGERS), "gm_state_tr_any_takeable"))
        self.assertEqual(gate, "OR = { gm_state_tr_takeable = yes AND = { gm_state_has_secondary = yes "
                               "gm_state_tr_takeable_secondary = yes } }")
        monthly = squash(strip_comments(block(read(self.TR), "gm_state_tr_monthly")))
        self.assertIn("if = { limit = { gm_state_tr_any_takeable = yes } clear_saved_scope = gm_tr_occupier", monthly)
        # The player's offer names the primary: only while it can go.
        self.assertIn("else_if = { limit = { gm_state_tr_takeable = yes NOT = { has_variable = gm_tr_offered_to", monthly)

    def test_the_ceremonys_answer_clears_a_restore(self):
        # Finding 4.
        for name in ("gm_state_dedicate", "gm_state_undedicate"):
            self.assertIn("gm_remove_state_var = { VAR = gm_restore_pm }", squash(block(read(EFFECTS), name)), name)

    def test_the_primary_row_shows_its_own_grandeur(self):
        # Finding 5.
        self.assertIn("ScriptValue('gm_state_primary_grandeur')", loc()["gm_row_detail"])

    def test_a_change_of_owner_lists_the_secondaries_again(self):
        # Finding 7.
        body = squash(strip_comments(block(read(EFFECTS), "gm_state_changed_hands")))
        self.assertIn("if = { limit = { gm_state_has_secondary = yes } every_in_list = { variable = gm_monuments_here "
                      "gm_mon_changed_hands = yes } gm_monument_pass = yes }", body)


class LevelsApartTests(unittest.TestCase):
    """Ageing rework (spec 2026-10-16 §1): a monument's levels are what was
    built and stand in the building; its grandeur is levels + age. Every
    rebuild height, trophy share, Rededicate's cost and the ceremony's level
    read levels, never grandeur, or a return would rebuild at the wrong
    height once age exists."""

    TR = "common/scripted_effects/gm_trophy_effects.txt"
    TR_VALUES = "common/script_values/gm_trophy_values.txt"
    COM = "common/scripted_effects/gm_commission_effects.txt"

    def test_the_level_values(self):
        values = read(VALUES)
        self.assertEqual(squash(block(values, "gm_state_level")),
                         "value = 0 if = { limit = { has_building = building_grand_monument } "
                         "value = b:building_grand_monument.level }")
        mon = read(MON_VALUES)
        self.assertEqual(squash(block(mon, "gm_mon_levels")),
                         "value = 0 if = { limit = { has_variable = gm_tr_levels } value = var:gm_tr_levels }")
        self.assertEqual(squash(block(mon, "gm_state_secondary_levels")),
                         "value = 0 if = { limit = { has_variable_list = gm_monuments_here } "
                         "every_in_list = { variable = gm_monuments_here add = gm_mon_levels } }")
        # What the building holds for the primary (sites spec 2026-10-18 §3.3):
        # read only where the building itself is the question.
        self.assertEqual(squash(block(mon, "gm_state_built_levels")),
                         "value = gm_state_level subtract = gm_state_secondary_levels min = 1 "
                         "if = { limit = { NOT = { has_building = building_grand_monument } } value = 0 }")
        # The size is the record once there is one.
        self.assertEqual(squash(block(mon, "gm_state_primary_levels")),
                         "value = gm_state_built_levels "
                         "if = { limit = { has_variable = gm_levels } value = var:gm_levels } "
                         "if = { limit = { NOT = { has_building = building_grand_monument } } value = 0 }")

    def test_starting_grandeur(self):
        """Sites spec 2026-10-18 §3.2: grandeur is starting grandeur + age; a
        missing record reads as the levels (old saves, trophies, digs)."""
        mon = read(MON_VALUES)
        self.assertEqual(squash(block(mon, "gm_state_primary_start")),
                         "value = gm_state_primary_levels "
                         "if = { limit = { has_variable = gm_start_grandeur } value = var:gm_start_grandeur } "
                         "if = { limit = { NOT = { has_building = building_grand_monument } } value = 0 }")
        self.assertEqual(squash(block(mon, "gm_mon_start")),
                         "value = gm_mon_levels "
                         "if = { limit = { has_variable = gm_tr_start_grandeur } value = var:gm_tr_start_grandeur }")
        self.assertEqual(squash(block(mon, "gm_state_primary_grandeur")),
                         "value = gm_state_primary_start add = gm_state_primary_age")
        self.assertEqual(squash(block(mon, "gm_mon_grandeur")), "value = gm_mon_start add = gm_mon_age")
        self.assertIn(("gm_start_grandeur", "gm_tr_start_grandeur"), CONTAINER_RECORDS)
        self.assertIn("gm_remove_state_var = { VAR = gm_start_grandeur }",
                      squash(block(read(EFFECTS), "gm_clear_state")))

    def test_only_named_readers_read_the_building(self):
        """The building's level is read only where the building is the
        question: what it holds for an undedicated primary, the merge and
        split arithmetic and the rebuilds (until the sites plan's Task 5 and 7
        retire them), the Dedicate button's first level, and the debug event."""
        allowed = {
            (VALUES, "gm_state_level"), (MON_VALUES, "gm_state_built_levels"),
            (MON_EFFECTS, "gm_sh_settle_region"), (MON_TRIGGERS, "gm_state_merge_pending"),
            (EFFECTS, "gm_state_migrate"),
            # The merge's reset and its self-check (sites final review, I6).
            (MON_EFFECTS, "gm_state_reset_building_level"),
            (MON_EFFECTS, "gm_monument_merge_level_self_check"),
        }
        found = set()
        for path in sorted(ROOT.glob("common/**/*.txt")) + sorted(ROOT.glob("events/*.txt")):
            rel = path.relative_to(ROOT).as_posix()
            if rel == DEBUG_EVENTS:
                continue
            for name, body in top_level_blocks(read(rel)):
                if re.search(r"(?<![\w:.])gm_state_level\b|building_grand_monument\.level", body) \
                        or (name == "gm_state_level" and rel == VALUES):
                    found.add((rel, name))
        self.assertEqual(found - allowed, set())

    def test_shares_cost_and_ceremony_read_levels(self):
        trv = read(self.TR_VALUES)
        for name in ("gm_state_tr_levels", "gm_state_tr_whole", "gm_state_tr_levels_left"):
            body = squash(block(trv, name))
            self.assertIn("gm_state_primary_levels", body, name)
            self.assertNotIn("gm_state_primary_grandeur", body, name)
        mon = read(MON_VALUES)
        for name in ("gm_mon_tr_levels", "gm_mon_tr_whole"):
            body = squash(block(mon, name))
            self.assertIn("gm_mon_levels", body, name)
            self.assertNotIn("gm_mon_grandeur", body, name)
        self.assertEqual(squash(block(read(VALUES), "gm_state_rededicate_cost")),
                         "value = gm_state_primary_levels multiply = 500")
        body = squash(block(read(EFFECTS), "gm_state_start_ceremony"))
        self.assertIn("gm_state_primary_levels", body)
        self.assertIn("gm_state_site_level", body)
        self.assertNotIn("gm_state_primary_grandeur", body)
        for key in ("gm_tr_take_occupation_tt", "gm_tr_take_own_tt"):
            self.assertIn("ScriptValue('gm_state_primary_levels')", loc()[key], key)


class StartGrandeurShareTests(unittest.TestCase):
    """Sites spec 2026-10-18 §5: a taking carries its share of the levels, of
    the starting grandeur and of the age; what it counts for abroad is half
    the starting grandeur and age it carries."""

    TR_VALUES = "common/script_values/gm_trophy_values.txt"

    def test_the_shares(self):
        self.assertEqual(squash(block(read(self.TR_VALUES), "gm_state_tr_start")),
                         "value = gm_state_primary_start if = { limit = { gm_state_tr_whole = 0 } "
                         "multiply = gm_state_tr_levels divide = gm_state_primary_levels }")
        self.assertEqual(squash(block(read(MON_VALUES), "gm_mon_tr_start")),
                         "value = gm_mon_start if = { limit = { gm_mon_tr_whole = 0 } "
                         "multiply = gm_mon_tr_levels divide = gm_mon_levels }")
        self.assertEqual(squash(block(read(self.TR_VALUES), "gm_state_tr_value")),
                         "value = gm_state_tr_start add = gm_state_tr_age divide = 2 ceiling = yes")

    def test_ageing_reads_starting_grandeur(self):
        self.assertTrue(squash(block(read(VALUES), "gm_state_age_step")).startswith(
            "value = gm_state_primary_start multiply = 2 divide = 1200"))
        self.assertTrue(squash(block(read(MON_VALUES), "gm_mon_age_step")).startswith(
            "value = gm_mon_start multiply = 2 divide = 1200"))


class AgeTests(unittest.TestCase):
    """Ageing rework (spec 2026-10-16 §1, §5): grandeur = levels + age. Age
    goes where the levels go: a taking carries its share, a return brings it
    back, a promotion and a rebuild keep it."""

    TR = "common/scripted_effects/gm_trophy_effects.txt"
    TR_VALUES = "common/script_values/gm_trophy_values.txt"

    def test_the_grandeur_values(self):
        mon = read(MON_VALUES)
        self.assertEqual(squash(block(mon, "gm_mon_age")),
                         "value = 0 if = { limit = { has_variable = gm_tr_age } value = var:gm_tr_age }")
        self.assertEqual(squash(block(mon, "gm_mon_grandeur")), "value = gm_mon_start add = gm_mon_age")
        self.assertEqual(squash(block(mon, "gm_state_primary_age")),
                         "value = 0 if = { limit = { has_building = building_grand_monument has_variable = gm_age } "
                         "value = var:gm_age }")
        self.assertEqual(squash(block(mon, "gm_state_primary_grandeur")),
                         "value = gm_state_primary_start add = gm_state_primary_age")
        self.assertEqual(squash(block(mon, "gm_state_secondary_grandeur")),
                         "value = 0 if = { limit = { has_variable_list = gm_monuments_here } "
                         "every_in_list = { variable = gm_monuments_here add = gm_mon_grandeur } }")
        self.assertEqual(squash(block(read(VALUES), "gm_state_grandeur")),
                         "value = 0 if = { limit = { has_building = building_grand_monument } "
                         "value = gm_state_primary_grandeur add = gm_state_secondary_grandeur }")
        self.assertIn("gm_remove_state_var = { VAR = gm_age }", squash(block(read(EFFECTS), "gm_clear_state")))

    def test_a_taking_carries_its_share_of_the_age(self):
        trv = read(self.TR_VALUES)
        self.assertEqual(squash(block(trv, "gm_state_tr_age")),
                         "value = gm_state_primary_age if = { limit = { gm_state_tr_whole = 0 } "
                         "multiply = gm_state_tr_levels divide = gm_state_primary_levels }")
        self.assertEqual(squash(block(trv, "gm_state_tr_value")),
                         "value = gm_state_tr_start add = gm_state_tr_age divide = 2 ceiling = yes")
        take = squash(strip_comments(block(read(self.TR), "gm_state_tr_take")))
        self.assertIn("set_variable = { name = gm_tr_take_age value = gm_state_tr_age }", take)
        self.assertLess(take.find("gm_tr_take_age value"), take.find("gm_state_tr_make_trophy = yes"))
        self.assertIn("gm_remove_state_var = { VAR = gm_tr_take_age }", take)
        make = squash(block(read(self.TR), "gm_state_tr_make_trophy"))
        self.assertIn("set_variable = { name = gm_tr_age value = scope:gm_tr_state.var:gm_tr_take_age }", make)
        piece = squash(strip_comments(block(read(self.TR), "gm_state_tr_remove_piece")))
        self.assertIn("change_variable = { name = gm_age subtract = var:gm_tr_take_age }", piece)

    def test_a_secondarys_piece_carries_its_share(self):
        mon = read(MON_VALUES)
        self.assertEqual(squash(block(mon, "gm_mon_tr_age")),
                         "value = gm_mon_age if = { limit = { gm_mon_tr_whole = 0 } "
                         "multiply = gm_mon_tr_levels divide = gm_mon_levels }")
        take = squash(strip_comments(block(read(MON_EFFECTS), "gm_mon_tr_take")))
        self.assertIn("set_variable = { name = gm_tr_take_age value = gm_mon_tr_age }", take)
        piece = squash(strip_comments(block(read(MON_EFFECTS), "gm_mon_tr_take_piece")))
        self.assertIn("set_variable = { name = gm_tr_age value = scope:gm_tr_state.var:gm_tr_take_age }", piece)
        self.assertIn("change_variable = { name = gm_tr_age subtract = scope:gm_tr_state.var:gm_tr_take_age }", piece)
        self.assertIn("value = { value = scope:gm_tr_state.var:gm_tr_take_start "
                      "add = scope:gm_tr_state.var:gm_tr_take_age divide = 2 ceiling = yes }", piece)
        whole = squash(strip_comments(block(read(MON_EFFECTS), "gm_mon_tr_take_whole")))
        self.assertIn("name = gm_tr_grandeur value = { value = gm_mon_grandeur divide = 2 ceiling = yes }", whole)

    def test_a_return_brings_its_age(self):
        receive = squash(strip_comments(block(read(self.TR), "gm_state_tr_receive")))
        self.assertIn("if = { limit = { scope:gm_tr_moving = { has_variable = gm_tr_age } } "
                      "gm_state_add_age = { AGE = scope:gm_tr_moving.var:gm_tr_age } }", receive)
        self.assertLess(receive.find("gm_state_tr_add_levels = yes"), receive.find("gm_state_add_age"))
        rejoin = squash(strip_comments(block(read(MON_EFFECTS), "gm_tr_rejoin_secondary")))
        self.assertIn("change_variable = { name = gm_tr_age add = scope:gm_tr_moving.var:gm_tr_age }", rejoin)
        rebuild = squash(block(read(self.TR), "gm_state_tr_take_records_from_moving"))
        self.assertIn("gm_tr_copy_to_state = { FROM = gm_tr_age TO = gm_age }", rebuild)
        add = squash(strip_comments(block(read(EFFECTS), "gm_state_add_age")))
        self.assertEqual(add, "if = { limit = { has_variable = gm_age } change_variable = { name = gm_age add = $AGE$ } } "
                              "else = { set_variable = { name = gm_age value = $AGE$ } }")


class AgeingTests(unittest.TestCase):
    """Ageing rework (spec 2026-10-16 §2): a dedicated monument that is not
    contested adds 2% of its levels a year to its age grandeur, half that
    under Mothballed; undedicated monuments and trophies abroad never age."""

    def test_the_monthly_step(self):
        values = read(VALUES)
        self.assertEqual(squash(block(values, "gm_policy_factor_age")),
                         "value = 1 if = { limit = { owner = { gm_policy_is = { P = mothballed STANDARD = no } } } "
                         "value = 0.5 }")
        self.assertEqual(squash(block(values, "gm_state_age_step")),
                         "value = gm_state_primary_start multiply = 2 divide = 1200 multiply = gm_policy_factor_age "
                         "max = gm_state_age_room")
        self.assertEqual(squash(block(read(MON_VALUES), "gm_mon_age_step")),
                         "value = gm_mon_start multiply = 2 divide = 1200 if = { limit = { var:gm_tr_origin ?= { "
                         "owner = { gm_policy_is = { P = mothballed STANDARD = no } } } } multiply = 0.5 } "
                         "max = gm_mon_age_room")

    def test_a_century_then_it_stands(self):
        """Owner, 2026-10-19: ageing stops at a century's worth, twice the
        starting grandeur, so a monument grows to three times what it was
        dedicated with. Gifts are not capped (they go through gm_*_add_age)."""
        values = read(VALUES)
        self.assertRegex(strip_comments(values), r"(?m)^gm_age_cap_years = 100\s*$")
        self.assertEqual(squash(block(values, "gm_state_age_room")),
                         "value = gm_state_primary_start multiply = gm_age_cap_years multiply = 2 divide = 100 "
                         "subtract = gm_state_primary_age min = 0")
        self.assertEqual(squash(block(read(MON_VALUES), "gm_mon_age_room")),
                         "value = gm_mon_start multiply = gm_age_cap_years multiply = 2 divide = 100 "
                         "subtract = gm_mon_age min = 0")
        # Transcribed: a month at a time, the step clamped to the room left.
        start, age = 75.0, 0.0
        for month in range(12 * 150):
            age += min(start * 2 / 1200, max(start * 100 * 2 / 100 - age, 0))
            if month == 12 * 50 - 1:
                self.assertAlmostEqual(start + age, 150)
        self.assertAlmostEqual(start + age, 225)

    def test_what_ages(self):
        ages = squash(block(read(TRIGGERS), "gm_state_ages"))
        for s in ("gm_state_is_dedicated = yes", "has_variable = gm_seen", "gm_state_is_contested = no",
                  "NOT = { has_variable = gm_restore_pm }", "NOT = { has_variable = gm_ceremony_pending }",
                  "NOT = { has_variable = gm_rebuilding }"):
            self.assertIn(s, ages)
        mon = squash(block(read(MON_TRIGGERS), "gm_mon_ages"))
        for s in ("has_tag = gm_monument", "has_variable = gm_tr_dedication", "exists = var:gm_tr_origin",
                  "NOT = { has_variable = gm_tr_contested }"):
            self.assertIn(s, mon)

    def test_the_primary_ages_before_its_steps_are_read(self):
        monthly = squash(strip_comments(block(read(EFFECTS), "gm_state_monthly")))
        step = "if = { limit = { gm_state_ages = yes } gm_state_add_age = { AGE = gm_state_age_step } }"
        self.assertIn(step, monthly)
        self.assertLess(monthly.find(step), monthly.find("name = gm_curve_in"))

    def test_secondaries_age_in_the_pass_and_trophies_never(self):
        monthly = squash(strip_comments(block(read(MON_EFFECTS), "gm_monument_monthly")))
        self.assertIn("if = { limit = { gm_mon_ages = yes } gm_mon_add_age = { AGE = gm_mon_age_step } }", monthly)
        tr = squash(strip_comments(read("common/scripted_effects/gm_trophy_effects.txt")))
        self.assertNotIn("gm_mon_add_age", tr)
        self.assertNotIn("age_step", tr)
        add = squash(block(read(MON_EFFECTS), "gm_mon_add_age"))
        self.assertEqual(add, "if = { limit = { has_variable = gm_tr_age } change_variable = { name = gm_tr_age add = $AGE$ } } "
                              "else = { set_variable = { name = gm_tr_age value = $AGE$ } }")


# Every state record a demoted primary keeps on its container (spec
# 2026-10-16 §4.4): state variable -> container variable.
CONTAINER_RECORDS = (
    ("gm_skin", "gm_tr_skin"), ("gm_form", "gm_tr_form"), ("gm_landmark", "gm_tr_landmark"),
    ("gm_namesake", "gm_tr_namesake"), ("gm_name_year", "gm_tr_name_year"), ("gm_name_char", "gm_tr_name_char"),
    ("gm_name_occasion", "gm_tr_name_occasion"), ("gm_name_enemy_cap", "gm_tr_name_enemy_cap"),
    ("gm_name", "gm_tr_name"), ("gm_honoree", "gm_tr_honoree"), ("gm_honoree_ig", "gm_tr_honoree_ig"),
    ("gm_age", "gm_tr_age"), ("gm_start_grandeur", "gm_tr_start_grandeur"), ("gm_raised_by", "gm_tr_raised_by"), ("gm_faith", "gm_tr_faith"),
    ("gm_built_by", "gm_tr_built_by"), ("gm_contested", "gm_tr_contested"), ("gm_heritage", "gm_tr_heritage"),
    ("gm_base_ig", "gm_tr_base_ig"), ("gm_supporter_ig", "gm_tr_supporter_ig"),
    ("gm_ceremony_level", "gm_tr_ceremony_level"),
    # A unique dedication (signatures spec 2026-10-16 §1, §7).
    ("gm_signature", "gm_tr_signature"), ("gm_sig_parent", "gm_tr_sig_parent"),
)


class FreezeTests(unittest.TestCase):
    """Ageing rework (spec 2026-10-16 §3): a dedicated monument's levels are
    recorded once its construction stops (gm_levels); levels built after
    that found a new monument beside it."""

    TR = "common/scripted_effects/gm_trophy_effects.txt"

    def test_demotion_keeps_every_record(self):
        body = squash(strip_comments(block(read(MON_EFFECTS), "gm_state_demote_primary")))
        self.assertIn("create_container = { tags = { gm_monument }", body)
        self.assertIn("set_variable = { name = gm_tr_levels value = scope:gm_tr_state.var:gm_demote_levels }", body)
        self.assertIn("gm_tr_record_dedication = yes", body)
        for frm, to in CONTAINER_RECORDS:
            self.assertIn(f"gm_tr_copy_from_state = {{ FROM = {frm} TO = {to} }}", body, frm)
        for s in ("add_to_global_variable_list = { name = gm_monuments target = scope:gm_mon_new }",
                  "add_to_variable_list = { name = gm_monuments_here target = scope:gm_mon_new }",
                  "add_to_variable_list = { name = gm_monuments_held target = scope:gm_mon_new }",
                  "set_variable = gm_tr_seen", "gm_tr_update_picture = yes"):
            self.assertIn(s, body)
        # The records are copied before the state forgets them.
        self.assertLess(body.find("gm_tr_copy_from_state"), body.find("gm_clear_state = { KEEP_LANDMARK = no }"))

    def test_the_refresh_only_asks_the_hidden_event(self):
        refresh = squash(strip_comments(block(read(EFFECTS), "gm_country_refresh")))
        for s in ("create_container", "destroy_container", "remove_building", "create_building"):
            self.assertNotIn(s, refresh)
        self.assertIn("if = { limit = { gm_state_newcomer_settled = yes } trigger_event = { id = monument_events.29 } }",
                      refresh)
        ev29 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.29\s*=\s*\{")))
        self.assertIn("type = state_event hidden = yes", ev29)
        self.assertIn("limit = { gm_state_newcomer_settled = yes } gm_state_settle_newcomer = yes", ev29)

    def test_script_keeps_the_frozen_levels(self):
        receive = squash(strip_comments(block(read(self.TR), "gm_state_tr_receive")))
        self.assertIn("change_variable = { name = gm_levels add = scope:gm_tr_moving.var:gm_tr_levels }", receive)
        piece = squash(strip_comments(block(read(self.TR), "gm_state_tr_remove_piece")))
        self.assertIn("set_variable = { name = gm_levels value = var:gm_tr_take_left }", piece)
        rebuild = squash(block(read(self.TR), "gm_state_tr_take_records_from_moving"))
        self.assertIn("set_variable = { name = gm_levels value = scope:gm_tr_moving.var:gm_tr_levels }", rebuild)



class SecondaryFitTests(unittest.TestCase):
    """Ageing rework (spec 2026-10-16 §4.1, §4.2): a monument standing beside
    another carries its own dedication's fit, approvals and effects, read from
    its container (gm_tr_dedication) and its state's owner."""

    def setUp(self):
        self.t = read(MON_TRIGGERS)
        self.v = read(VALUES)

    def test_kinds_match_the_table(self):
        kind_trigger = {"regime": "gm_mon_kind_regime", "ruler": "gm_mon_kind_ruler", "faith": "gm_mon_kind_faith"}
        for d in DEDICATIONS:
            for kind, trig in kind_trigger.items():
                present = f"gm_mon_is = {{ KEY = {d.key} }}" in squash(block(self.t, trig))
                self.assertEqual(present, d.kind == kind, f"{d.key} in {trig}")
        self.assertEqual(squash(block(self.t, "gm_mon_is")),
                         "has_variable = gm_tr_dedication var:gm_tr_dedication = flag:$KEY$")

    def test_bound_messages_fit_only_for_the_raiser(self):
        body = squash(block(self.t, "gm_mon_message_fits"))
        self.assertTrue(body.startswith("OR = { gm_mon_is_bound = no AND = { gm_mon_raised_by_owner = yes OR = {"))
        for key, gate in REGIME_GATE.items():
            self.assertIn(f"AND = {{ gm_mon_is = {{ KEY = {key} }} var:gm_tr_origin ?= {{ owner = {{ {gate} = yes }} }} }}",
                          body)
        self.assertIn("AND = { gm_mon_kind_ruler = yes gm_mon_leader_fits = yes }", body)
        self.assertIn("AND = { gm_mon_kind_faith = yes gm_mon_shrine_fits = yes }", body)
        self.assertIn("ruler ?= { this = scope:gm_tmp_mon_honoree }", squash(block(self.t, "gm_mon_leader_fits")))
        self.assertIn("religion = scope:gm_tmp_mon_faith", squash(block(self.t, "gm_mon_shrine_fits")))
        self.assertIn("owner = scope:gm_tmp_mon_raiser", squash(block(self.t, "gm_mon_raised_by_owner")))

    def test_statuses(self):
        self.assertEqual(squash(block(self.t, "gm_mon_status_fits")),
                         "has_tag = gm_monument has_variable = gm_tr_dedication has_variable = gm_tr_seen "
                         "gm_mon_is_contested = no gm_mon_is_heritage = no gm_mon_message_fits = yes")
        self.assertEqual(squash(block(self.t, "gm_mon_counts_standing")),
                         "has_tag = gm_monument gm_mon_is_contested = no")

    def test_ig_alignment_matches_the_table(self):
        for ig in IGS:
            approve = squash(block(self.t, f"gm_mon_approved_by_{ig}"))
            oppose = squash(block(self.t, f"gm_mon_opposed_by_{ig}"))
            for d in DEDICATIONS:
                self.assertEqual(f"gm_mon_is = {{ KEY = {d.key} }}" in approve, d.approve == ig, f"{ig} approves {d.key}")
                self.assertEqual(f"gm_mon_is = {{ KEY = {d.key} }}" in oppose, d.oppose == ig, f"{ig} opposes {d.key}")
            self.assertIn(f"gm_mon_leader_ig_is = {{ IG = {ig} }}", approve)
            self.assertIn(f"gm_mon_leader_opposed_by = {{ IG = {ig} }}", oppose)

    def test_first_sight(self):
        body = squash(strip_comments(block(read(MON_EFFECTS), "gm_mon_first_sight")))
        for s in ("NOT = { has_variable = gm_tr_seen }", "set_variable = gm_tr_seen",
                  "set_variable = { name = gm_tr_raised_by value = scope:gm_tmp_mon_owner }",
                  "set_variable = { name = gm_tr_built_by value = scope:gm_tmp_mon_owner }"):
            self.assertIn(s, body)
        self.assertIn("gm_mon_first_sight = yes", squash(block(read(MON_EFFECTS), "gm_monument_monthly")))

    def test_national_sums_walk_the_held_secondaries(self):
        standing = squash(block(self.v, "gm_sum_standing"))
        self.assertIn("every_in_list = { variable = gm_monuments_held limit = { gm_mon_counts_standing = yes } "
                      "add = gm_mon_grandeur }", standing)
        self.assertNotIn("gm_state_secondary_grandeur", standing)
        self.assertIn("every_in_list = { variable = gm_monuments_held limit = { gm_mon_status_fits = yes "
                      "OR = { gm_mon_kind_regime = yes gm_mon_kind_ruler = yes } } add = gm_mon_grandeur }",
                      squash(block(self.v, "gm_sum_regime")))
        for key in NATIONAL:
            self.assertIn(f"every_in_list = {{ variable = gm_monuments_held limit = {{ gm_mon_status_fits = yes "
                          f"gm_mon_is = {{ KEY = {key} }} }} add = gm_mon_grandeur }}",
                          squash(block(self.v, f"gm_sum_{key}")), key)

    def test_ig_nets_walk_the_held_secondaries(self):
        body = squash(strip_comments(block(read(EFFECTS), "gm_compute_ig")))
        for s in ("variable = gm_monuments_held",
                  "gm_mon_status_fits = yes gm_mon_approved_by_$IG$ = yes",
                  "gm_mon_status_fits = yes gm_mon_opposed_by_$IG$ = yes",
                  "gm_mon_is_contested = yes has_variable = gm_tr_base_ig var:gm_tr_base_ig = flag:$IG$"):
            self.assertIn(s, body)
        self.assertLess(body.find("variable = gm_monuments_held"), body.find("var:gm_ig_net_$IG$ >= 0"))

    def test_local_effects_by_dedication(self):
        monthly = squash(strip_comments(block(read(EFFECTS), "gm_state_monthly")))
        for d in DEDICATIONS:
            cap = LOCAL_CAPS.get(d.key, ("gm_curve_lin_steps",))[0]
            self.assertIn(f"gm_state_local_steps_one = {{ KEY = {d.key} CAP = {cap} }}", monthly, d.key)
        one = squash(strip_comments(block(read(EFFECTS), "gm_state_local_steps_one")))
        # The 1/n curve, the policy, then the dedication's ceiling (owner,
        # 2026-10-19): a cap on the effect, so it holds under every policy.
        for s in ("gm_state_has_pm = { PM = pm_monument_$KEY$ } } add = gm_state_primary_grandeur",
                  "every_in_list = { variable = gm_monuments_here limit = { gm_mon_is = { KEY = $KEY$ } } "
                  "add = gm_mon_grandeur }",
                  "name = gm_local_steps_$KEY$ value = { value = gm_curve_steps_lin_f5 multiply = gm_policy_factor_local "
                  "max = $CAP$ }",
                  "add_modifier = { name = gm_local_$KEY$ multiplier = var:gm_local_steps_$KEY$ }"):
            self.assertIn(s, one)

    def test_the_overview_counts_secondaries(self):
        for name in ("gm_disp_count_upheld", "gm_disp_count_heritage", "gm_disp_count_contested"):
            self.assertIn("variable = gm_monuments_held", squash(block(self.v, name)), name)
        self.assertIn("variable = gm_monuments_held", squash(block(self.v, "gm_sum_monuments")))


MON_SGUIS = "common/scripted_guis/gm_monument_sguis.txt"


class SecondaryContestTests(unittest.TestCase):
    """Ageing rework (spec 2026-10-16 §4.3): a monument beside another is
    contested, kept as heritage or pulled down on its own."""

    def setUp(self):
        self.e = read(EFFECTS)
        self.m = read(MON_EFFECTS)

    def test_the_contest_records_from_its_dedication(self):
        igs = squash(block(self.m, "gm_mon_record_contest_igs"))
        for key, base, sup in (("crown", "intelligentsia", "landowners"), ("republic", "landowners", "intelligentsia"),
                               ("revolution", "industrialists", "trade_unions")):
            self.assertIn(f"limit = {{ gm_mon_is = {{ KEY = {key} }} }} set_variable = {{ name = gm_tr_base_ig "
                          f"value = flag:{base} }} set_variable = {{ name = gm_tr_supporter_ig value = flag:{sup} }}", igs)
        self.assertIn("set_variable = { name = gm_tr_supporter_ig value = flag:devout }", igs)
        self.assertIn("set_variable = { name = gm_tr_supporter_ig value = var:gm_tr_honoree_ig }", igs)
        contest = squash(block(self.m, "gm_mon_contest"))
        self.assertEqual(contest, "set_variable = { name = gm_tr_contested value = 0 } set_variable = gm_tr_new_contest "
                                  "gm_mon_record_contest_igs = yes")
        lift = squash(block(self.m, "gm_mon_lift_contest"))
        for v in ("gm_tr_contested", "gm_tr_heritage", "gm_tr_new_contest", "gm_tr_base_ig", "gm_tr_supporter_ig"):
            self.assertIn(f"gm_remove_state_var = {{ VAR = {v} }}", lift)

    def test_the_monthly_check_covers_secondaries(self):
        check = squash(strip_comments(block(self.e, "gm_check_contests")))
        self.assertIn("variable = gm_monuments_held", check)
        self.assertIn("gm_mon_check_contest = yes", check)
        one = squash(strip_comments(block(self.m, "gm_mon_check_contest")))
        for s in ("gm_mon_first_sight = yes", "gm_mon_kind_faith = yes gm_mon_raised_by_owner = no",
                  "gm_mon_message_fits = yes } gm_mon_lift_contest = yes",
                  "gm_mon_is_contested = no gm_mon_is_heritage = no gm_mon_message_fits = no } gm_mon_contest = yes"):
            self.assertIn(s, one)
        monthly = squash(strip_comments(block(self.e, "gm_country_monthly")))
        self.assertIn("change_variable = { name = gm_tr_contested add = 1 }", monthly)

    def test_a_change_of_owner_contests_secondaries(self):
        body = squash(strip_comments(block(self.e, "gm_state_changed_hands")))
        self.assertIn("gm_mon_changed_hands = yes", body)
        one = squash(strip_comments(block(self.m, "gm_mon_changed_hands")))
        self.assertIn("gm_mon_raised_by_owner = no", one)
        self.assertIn("gm_mon_contest = yes", one)
        self.assertIn("set_variable = gm_tr_heritage", one)

    def test_a_civil_wars_winner_adopts_secondaries(self):
        body = squash(strip_comments(block(self.e, "gm_repair_after_civil_war")))
        self.assertIn("every_in_global_list = { variable = gm_monuments", body)
        self.assertIn("gm_mon_adopt_for_winner = yes", body)
        self.assertIn("gm_monument_pass = yes", body)

    def test_the_choices_go_through_one_hidden_event(self):
        order = squash(block(self.m, "gm_mon_order_choice"))
        self.assertIn("set_variable = { name = gm_mon_order value = flag:$CHOICE$ }", order)
        self.assertIn("trigger_event = { id = monument_events.30 }", order)
        ev30 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.30\s*=\s*\{")))
        self.assertIn("type = state_event hidden = yes", ev30)
        self.assertIn("gm_state_run_mon_orders = yes", ev30)
        run = squash(strip_comments(block(self.m, "gm_state_run_mon_orders")))
        # No rebuild, no wait (sites spec 2026-10-18 §3.3): every tear-down at once.
        self.assertNotIn("gm_rebuilding", run)
        self.assertNotIn("shrink", run)
        self.assertIn("add_to_temporary_list = gm_mon_tearing", run)
        self.assertIn("gm_state_swap_primary = yes gm_state_rededicate = yes", run)

    def test_the_sguis(self):
        sg = read(MON_SGUIS)
        for name, call in (("gm_mon_tear_down_sgui", "gm_mon_order_choice = { CHOICE = tear_down }"),
                           ("gm_mon_rededicate_sgui", "gm_mon_order_choice = { CHOICE = rededicate }"),
                           ("gm_mon_preserve_sgui", "gm_mon_preserve = yes")):
            body = squash(block(sg, name))
            self.assertIn("saved_scopes = { gm_mon }", body, name)
            self.assertIn(call, body, name)
            self.assertIn("ai_is_valid = { always = no }", body, name)

    def test_the_ai_decides_secondaries_without_rededicating(self):
        ai = squash(strip_comments(block(self.e, "gm_ai_decide_contests")))
        self.assertIn("variable = gm_monuments_held", ai)
        self.assertIn("gm_mon_order_choice = { CHOICE = tear_down }", ai)
        self.assertIn("gm_mon_preserve = yes", ai)
        self.assertNotIn("CHOICE = rededicate", ai)

    def test_the_notice_covers_secondaries(self):
        ev16 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.16\s*=\s*\{")))
        self.assertIn("gm_notice_mons", ev16)
        self.assertIn("gm_mon_order_choice = { CHOICE = tear_down }", ev16)
        self.assertIn("gm_mon_preserve = yes", ev16)
        notify = squash(strip_comments(block(self.e, "gm_notify_new_contests")))
        self.assertIn("has_variable = gm_tr_new_contest", notify)

    def test_a_secondary_leaving_home_forgets_it(self):
        whole = squash(strip_comments(block(self.m, "gm_mon_tr_take_whole")))
        self.assertIn("gm_mon_forget_home = yes", whole)
        forget = squash(block(self.m, "gm_mon_forget_home"))
        for v in ("gm_tr_seen", "gm_tr_raised_by", "gm_tr_contested", "gm_tr_heritage", "gm_tr_base_ig",
                  "gm_tr_supporter_ig", "gm_tr_new_contest", "gm_mon_order"):
            self.assertIn(f"gm_remove_state_var = {{ VAR = {v} }}", forget)


class SwapTests(unittest.TestCase):
    """Ageing rework (spec 2026-10-16 §3.3): a secondary raised onto the
    state's variables and the primary demoted, with no rebuild."""

    TR = "common/scripted_effects/gm_trophy_effects.txt"

    def test_the_swap(self):
        swap = squash(strip_comments(block(read(MON_EFFECTS), "gm_state_swap_primary")))
        self.assertEqual(swap, "set_variable = { name = gm_demote_levels value = gm_state_primary_levels } "
                               "gm_state_demote_primary = yes gm_state_raise_secondary = yes")
        self.assertNotIn("remove_building", swap)
        raise_ = squash(strip_comments(block(read(MON_EFFECTS), "gm_state_raise_secondary")))
        self.assertIn("scope:gm_mon_raise = { save_scope_as = gm_tr_moving }", raise_)
        self.assertIn("gm_state_tr_take_records_from_moving = yes", raise_)
        self.assertIn("destroy_container = yes", raise_)
        self.assertNotIn("te_construction_market_build_specified_level", raise_)

    def test_records_come_back_both_ways(self):
        take = squash(block(read(self.TR), "gm_state_tr_take_records_from_moving"))
        for frm, to in CONTAINER_RECORDS:
            if frm in ("gm_raised_by", "gm_built_by", "gm_ceremony_level"):
                continue
            self.assertIn(f"gm_tr_copy_to_state = {{ FROM = {to} TO = {frm} }}", take, frm)
        self.assertIn("gm_tr_copy_to_state = { FROM = gm_tr_dedication TO = gm_restore_pm }", take)
        # The picture, outside CONTAINER_RECORDS (gm_tr_update_picture writes the
        # container's): the refresh redraws the state's only once gm_restore_pm
        # is gone, so without this a swapped-back monument showed the drape.
        self.assertIn("gm_tr_copy_to_state = { FROM = gm_tr_picture_code TO = gm_picture_code }", take)
        rebuild = squash(block(read(self.TR), "gm_state_tr_rebuild_from_moving"))
        self.assertIn("gm_state_tr_take_records_from_moving = yes", rebuild)
        self.assertLess(rebuild.find("te_construction_market_build_specified_level"),
                        rebuild.find("gm_state_tr_take_records_from_moving = yes"))

    def test_the_grandest_stands_first_once(self):
        settled = squash(block(read(TRIGGERS), "gm_state_newcomer_settled"))
        for s in ("has_variable = gm_newcomer", "has_variable = gm_levels", "NOT = { has_variable = gm_unveil_pending }",
                  "NOT = { has_variable = gm_name_choice_open }", "NOT = { has_variable = gm_skin_axis }",
                  "NOT = { has_variable = gm_restore_pm }"):
            self.assertIn(s, settled)
        settle = squash(strip_comments(block(read(MON_EFFECTS), "gm_state_settle_newcomer")))
        self.assertTrue(settle.startswith("remove_variable = gm_newcomer"))
        self.assertIn("order_by = gm_mon_grandeur", settle)
        self.assertIn("gm_state_swap_primary = yes", settle)
        ev29 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.29\s*=\s*\{")))
        self.assertIn("if = { limit = { gm_state_newcomer_settled = yes } gm_state_settle_newcomer = yes }", ev29)
        refresh = squash(strip_comments(block(read(EFFECTS), "gm_country_refresh")))
        self.assertIn("gm_state_newcomer_settled = yes", refresh)
        self.assertNotIn("gm_state_swap_primary", refresh)


ANNIVERSARIES = (3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15)


class OpportunityLevelTests(unittest.TestCase):
    """Ageing rework (spec 2026-10-16 §5; owner): an opportunity counts new
    levels of fitting monuments of its dedication, ageing never; the gift is
    +5 grandeur with no rebuild."""

    COM_V = "common/script_values/gm_commission_values.txt"
    COM_E = "common/scripted_effects/gm_commission_effects.txt"
    COM_T = "common/scripted_triggers/gm_commission_triggers.txt"

    def test_progress_counts_levels(self):
        body = squash(block(read(self.COM_V), "gm_com_fit_grandeur"))
        # Starting grandeur, never age (Plan B).
        self.assertIn("limit = { gm_state_com_counts = yes } add = gm_state_primary_start", body)
        self.assertIn("every_in_list = { variable = gm_monuments_held limit = { gm_mon_com_counts = yes } "
                      "add = gm_mon_start }", body)
        self.assertNotIn("age", body)
        counts = squash(block(read(MON_TRIGGERS), "gm_mon_com_counts"))
        self.assertIn("gm_mon_status_fits = yes", counts)
        self.assertIn("gm_mon_has_dedication_flag = { VAR = gm_com_dedication }", counts)

    def test_raise_it_builds_only_where_it_may(self):
        pick = squash(strip_comments(block(read(self.COM_E), "gm_com_pick_build_state")))
        self.assertGreaterEqual(pick.count("gm_state_can_build_site = yes"), 4)

    def test_the_gift_is_age(self):
        gift = squash(strip_comments(block(read(self.COM_E), "gm_state_gift_grandeur")))
        self.assertIn("gm_state_add_age = { AGE = gm_com_gift }", gift)
        for s in ("remove_building", "te_construction_market_build_specified_level", "gm_state_mark_restore_pm"):
            self.assertNotIn(s, gift)
        fulfil = squash(strip_comments(block(read(self.COM_E), "gm_com_fulfil")))
        self.assertIn("limit = { gm_mon_com_counts = yes }", fulfil)
        self.assertIn("scope:gm_com_gift_mon = { gm_mon_add_age = { AGE = gm_com_gift } }", fulfil)


class RededicateAgeTests(unittest.TestCase):
    def test_rededicate_halves_the_age(self):
        body = squash(strip_comments(block(read(EFFECTS), "gm_state_apply_rededicate")))
        self.assertIn("set_variable = { name = gm_rededicate_age value = { value = gm_state_primary_age divide = 2 } }",
                      body)
        self.assertLess(body.find("gm_rededicate_age value"), body.find("gm_clear_state = { KEEP_LANDMARK = yes }"))
        self.assertIn("set_variable = { name = gm_age value = var:gm_rededicate_age }", body)
        self.assertLess(body.find("gm_clear_state = { KEEP_LANDMARK = yes }"),
                        body.find("name = gm_age value = var:gm_rededicate_age"))
        self.assertIn("remove_variable = gm_rededicate_age", body)


class AnniversaryAgeTests(unittest.TestCase):
    def test_a_monument_holds_anniversaries_by_its_grandeur(self):
        body = squash(block(read(TRIGGERS), "gm_state_holds_anniversary"))
        self.assertIn("gm_state_primary_grandeur >= 3", body)
        self.assertNotIn("level", body)

    def test_the_public_option_adds_age(self):
        self.assertEqual(squash(block(read(VALUES), "gm_evt_grandeur")),
                         "value = gm_state_primary_start multiply = 0.1 min = 1")
        events = read(EVENTS)
        for n in ANNIVERSARIES:
            ev = squash(strip_comments(raw_block_at(events, r"(?m)^monument_events\.%d\s*=\s*\{" % n)))
            a = ev[ev.find("name = monument_events.%d.a" % n):ev.find("name = monument_events.%d.b" % n)]
            self.assertIn("custom_tooltip = { text = gm_evt_grandeur_tt gm_ann_add_age = yes }", a, n)
        self.assertIn("Var('gm_ann_gain')", loc()["gm_evt_grandeur_tt"])
        add = squash(strip_comments(block(read(MON_EFFECTS), "gm_ann_add_age")))
        self.assertIn("scope:monument_mon = { gm_mon_add_age = { AGE = gm_mon_evt_grandeur } }", add)
        self.assertIn("scope:monument_state = { gm_state_add_age = { AGE = gm_evt_grandeur } }", add)

    def test_every_monument_holds_anniversaries(self):
        # Owner, 2026-10-16: ideally every monument, those beside another too.
        events = read(EVENTS)
        oa = squash(strip_comments(read(ON_ACTIONS)))
        keys = {3: "civic", 4: "religious", 5: "war_memorial", 6: "artistic", 7: "naturalist", 8: "scientific",
                9: "industrial", 10: "athletic", 12: "crown", 13: "republic", 14: "revolution", 15: "leader"}
        for n, key in keys.items():
            ev = squash(strip_comments(raw_block_at(events, r"(?m)^monument_events\.%d\s*=\s*\{" % n)))
            self.assertIn(f"trigger = {{ gm_country_holds_anniversary = {{ KEY = {key} }} }}", ev, n)
            self.assertIn(f"immediate = {{ gm_ann_pick = {{ KEY = {key} }} }}", ev, n)
            self.assertIn(f"trigger = {{ gm_country_holds_anniversary = {{ KEY = {key} }} }} "
                          f"trigger_event = {{ id = monument_events.{n} }}", oa, n)
        country = squash(block(read(MON_TRIGGERS), "gm_country_holds_anniversary"))
        self.assertIn("gm_state_holds_anniversary = { PM = pm_monument_$KEY$ }", country)
        self.assertIn("gm_mon_holds_anniversary = { KEY = $KEY$ }", country)
        mon = squash(block(read(MON_TRIGGERS), "gm_mon_holds_anniversary"))
        self.assertEqual(mon, "gm_mon_status_fits = yes gm_mon_is = { KEY = $KEY$ } gm_mon_grandeur >= 3")
        pick = squash(strip_comments(block(read(MON_EFFECTS), "gm_ann_pick")))
        self.assertIn("order_by = gm_state_primary_grandeur", pick)
        self.assertIn("order_by = gm_mon_grandeur", pick)
        self.assertIn("scope:gm_ann_mon.var:gm_tr_g > var:gm_ann_g", pick)
        self.assertIn("save_scope_as = monument_mon", pick)

    def test_a_named_anniversary_beside_another_names_the_first(self):
        # Event loc cannot reach a container (scripting_best_practices.md), so
        # the four that name their monument have a text for one beside another.
        L = loc()
        events = read(EVENTS)
        for n in (12, 13, 14, 15):
            ev = squash(strip_comments(raw_block_at(events, r"(?m)^monument_events\.%d\s*=\s*\{" % n)))
            self.assertIn(f"triggered_desc = {{ trigger = {{ exists = scope:monument_mon }} "
                          f"desc = monument_events.{n}.d_beside }}", ev, n)
            self.assertIn("the monument standing beside", L[f"monument_events.{n}.d_beside"], n)


class FinalReviewFixTests(unittest.TestCase):
    """The whole-branch review of the ageing rework (2026-10-16)."""

    def test_the_notice_counts_monuments_beside_another(self):
        # Important 2.
        body = squash(block(read(VALUES), "gm_notice_count"))
        self.assertIn("variable = gm_notice_states", body)
        self.assertIn("every_in_list = { variable = gm_notice_mons add = 1 }", body)

    def test_no_loc_reads_grandeur_as_levels(self):
        L = loc()
        self.assertNotIn("ScriptValue('gm_state_grandeur')|0]#! levels", L["monument_trophy_events.1.d"])
        self.assertIn("ScriptValue('gm_state_primary_levels')", L["monument_trophy_events.1.d"])
        for key in ("gm_tr_row_site_value_tt", "gm_tr_row_value_tt", "gm_mon_take_tt"):
            self.assertNotIn("half the levels", L[key], key)
            self.assertNotIn("half its levels", L[key], key)

    def test_a_stale_order_is_run_again(self):
        monthly = squash(strip_comments(block(read(MON_EFFECTS), "gm_monument_monthly")))
        self.assertIn("if = { limit = { has_variable = gm_mon_order } var:gm_tr_origin ?= { "
                      "trigger_event = { id = monument_events.30 } } }", monthly)

    def test_records_taken_on_cache_their_grandeur(self):
        take = squash(block(read("common/scripted_effects/gm_trophy_effects.txt"),
                            "gm_state_tr_take_records_from_moving"))
        self.assertIn("change_variable = { name = gm_g_cache add = scope:gm_tr_moving.var:gm_tr_age }", take)
        self.assertIn("set_variable = { name = gm_grandeur value = var:gm_g_cache }", take)
        self.assertNotIn("set_variable = { name = gm_grandeur value = scope:gm_tr_moving.var:gm_tr_levels }", take)

    def test_the_contested_count_and_the_notice_guard(self):
        self.assertIn("variable = gm_monuments_held", squash(block(read(VALUES), "gm_sum_contested")))
        ev16 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.16\s*=\s*\{")))
        self.assertNotIn("any_in_list = { variable = gm_notice_mons }", ev16)

    def test_a_promotion_never_raises_a_monument_ordered_down(self):
        # Deferred minor, fixed: pulling down a primary handed the building to
        # the grandest secondary even when its Pull Down was ordered and not yet
        # run (.30), so Tear Them All Down left it standing first, contested,
        # with no new notice. The building is already down: the ordered ones go
        # first, and their levels drop out of the one rebuild.
        promote = squash(strip_comments(block(read(MON_EFFECTS), "gm_state_promote_secondary")))
        self.assertIn("gm_state_pull_down_ordered = yes", promote)
        self.assertLess(promote.index("gm_state_pull_down_ordered = yes"), promote.index("ordered_in_list"))
        pull = squash(strip_comments(block(read(MON_EFFECTS), "gm_state_pull_down_ordered")))
        # The filter gm_state_run_mon_orders keeps an order by.
        for cond in ("var:gm_mon_order = flag:tear_down", "gm_mon_is_contested = yes",
                     "var:gm_mon_order_by ?= { this = scope:gm_mon_run_owner }"):
            self.assertIn(cond, pull)
        self.assertIn("gm_mon_tear_down_one = yes", pull)
        self.assertIn("save_scope_as = gm_mon_run_state", pull)
        self.assertNotIn("gm_state_tr_shrink_by", pull)
        # One at a time, not a temporary list: option a pulls down several
        # states in one effect, and a temporary list lasts until it ends.
        self.assertNotIn("add_to_temporary_list", pull)
        self.assertIn("var:gm_pull_n < 16", pull)
        self.assertIn("change_variable = { name = gm_pull_n add = 1 }", pull)

    def test_tear_them_all_down_orders_the_secondaries_first(self):
        ev16 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.16\s*=\s*\{")))
        opt_a = ev16[ev16.index("name = monument_events.16.a"):ev16.index("name = monument_events.16.b")]
        self.assertLess(opt_a.index("gm_mon_order_choice = { CHOICE = tear_down }"),
                        opt_a.index("gm_state_tear_down = yes"))

def _mod_txt_files():
    for sub in ("common", "events"):
        yield from sorted((ROOT / sub).rglob("*.txt"))


# ---- Unique dedications (signatures spec 2026-10-16) ----------------------------------

Signature = namedtuple("Signature", "key kind family name national local ig parent source members")
# The checklist for adding a signature (docs/superpowers/archive/specs/2026-10-16-grand-
# monument-signatures-design.md §10). kind: a family (§4.1), a one-off (§4.2: a
# family of one with a flourish, counted in its family's sums too) or a special
# (§5: given by completing its opportunity). national: (modifier suffix, field,
# step) per field, each its own one-field modifier gm_national_sig_<key><suffix>
# (Ancestral Antiquity's is cultural pull, a script value); local: (field, step)
# of gm_local_sig_<key>; ig: the one group of its own (§2.3); parent: a
# special's dedication; source: a special's moment (COMMISSION_SOURCES);
# members: the landmarks that carry it (a one-off's is its one landmark). The
# row order is the debug codes' (gm_disp_sig_code).
SIGNATURES = (
    Signature("antiquity", "family", None, "Ancestral Antiquity", (("", "cultural_pull", 1),),
              ("goods_output_tourism_mult", 0.05), "intelligentsia", None, None,
              ("stelae_of_aksum", "obelisks_of_karnak", "persepolis", "luxor_obelisk", "venus_de_milo",
               "piraeus_lion", "horses_of_saint_mark", "great_zimbabwe", "uffizi_gallery", "capitoline_museums",
               "temples_of_baalbek", "palmyra", "xanthos", "arch_of_ctesiphon", "winged_victory_of_samothrace",
               "troy_hisarlik", "mycenae_grave_circle", "pergamon_altar", "deir_el_bahari_cache",
               "ishtar_gate_babylon", "palace_of_knossos", "oseberg_ship", "machu_picchu", "bust_of_nefertiti",
               "tomb_of_tutankhamun", "royal_cemetery_at_ur", "sanxingdui_pits", "sutton_hoo", "tomb_of_pakal",
               "tomb_of_philip_ii", "tomb_of_marquis_yi", "royal_tombs_of_sipan", "olympia", "delphi",
               "sidon_necropolis", "tomb_of_alexander", "pompeii")),
    Signature("archive", "family", None, "Epigraphic Archive",
              (("", "country_weekly_innovation_max_add", 2), ("_spread", "country_tech_spread_mult", 0.02)),
              ("building_university_throughput_add", 0.10), "intelligentsia", None, None,
              ("rosetta_stone", "temple_of_dendera", "mesha_stele", "nineveh_library", "vindolanda_tablets",
               "antikythera_mechanism", "mohenjo_daro", "lascaux_caves", "nag_hammadi_library", "dead_sea_scrolls",
               "mawangdui_tombs", "otzi_the_iceman", "caral_supe", "gobekli_tepe", "villa_of_the_papyri")),
    Signature("throne", "family", None, "Seat of the Throne", (("", "country_authority_mult", 0.03),), None, None,
              None, None,
              ("topkapi_palace", "golestan_palace", "sans_souci_palace", "royal_palace_of_benin",
               "royal_palace_of_kumasi", "imperial_city_of_hue", "red_fort", "royal_palaces_of_abomey",
               "klungkung_palace", "royal_palace_of_kandy")),
    Signature("royal_pantheon", "family", None, "Royal Pantheon",
              (("", "country_loyalists_from_legitimacy_mult", 0.05),), None, None, None, None,
              ("alexander_column", "basilica_of_superga", "tomb_of_william_the_silent", "cenotaph_of_maximilian",
               "arco_de_santa_maria", "statue_of_louis_xiv", "nikko_toshogu")),
    Signature("martial_glory", "family", None, "Martial Glory", (("", "unit_morale_recovery_mult", 0.05),), None,
              None, None, None,
              ("brandenburg_gate", "lion_monument", "bukgwan_victory_stele", "tipus_tiger", "baba_merzoug",
               "bodrum_castle", "bunker_hill_monument", "obelisk_of_the_second_of_may", "nelsons_column")),
    Signature("liberty", "family", None, "Liberty", (("", "state_migration_pull_mult", 0.03),), None, None, None,
              None, ("washington_monument_baltimore", "liberty_column", "lion_of_saint_mark", "washington_monument")),
    Signature("grande_armee", "one_off", "martial_glory", "To the Grande Armée",
              (("", "country_prestige_mult", 0.03),), None, None, None, None, ("arc_de_triomphe",)),
    Signature("mandate_of_heaven", "one_off", "throne", "The Mandate of Heaven",
              (("", "country_legitimacy_base_add", 1),), None, None, None, None, ("temple_of_heaven",)),
    Signature("glory_of_athens", "one_off", "antiquity", "The Glory of Athens", (("", "country_influence_mult", 0.02),),
              None, None, None, None, ("parthenon",)),
    Signature("first_emperor", "one_off", "antiquity", "The First Emperor’s Army", (),
              ("goods_output_tourism_mult", 0.10), None, None, None, ("terracotta_army",)),
    Signature("to_victory", "special", None, "To Victory", (("", "country_prestige_mult", 0.02),), None, None,
              "war_memorial", "victory", ()),
    Signature("unknown_soldier", "special", None, "To the Unknown Soldier",
              (("", "country_radicals_from_legitimacy_mult", -0.05),), None, None, "war_memorial", "defeat", ()),
    Signature("concert_of_nations", "special", None, "To the Concert of Nations",
              (("", "country_influence_mult", 0.02),), None, None, "civic", "great_power", ()),
    Signature("conquerors_of_space", "special", None, "To the Conquerors of Space",
              (("", "country_weekly_innovation_mult", 0.02),), None, "intelligentsia", "civic", "space", ()),
    Signature("olympic", "special", None, "Olympic", (("", "state_mortality_mult", -0.01),), None, None, "athletic",
              "tech_athletic", ()),
    # Phase C (§6.3): the national pantheons.
    Signature("heroes", "family", None, "Heroes of the Nation", (("", "state_assimilation_mult", 0.05),), None,
              None, None, None, ("walhalla",)),
)
SIG_BY_KEY = {s.key: s for s in SIGNATURES}
SIG_NATIONAL = tuple(s.key for s in SIGNATURES if s.national)
SIG_LOCAL = tuple(s.key for s in SIGNATURES if s.local)
SPECIAL_SIGS = tuple(s for s in SIGNATURES if s.kind == "special")
# A special is its opportunity's boon made permanent, a fifth a step (§5.4).
SPECIAL_BOON_SHARE = 0.2
# The civic-progress five carry no family (§4.1), and the shrine of §6.4 none.
NO_SIGNATURE = ("la_scala", "teatro_di_san_carlo", "jantar_mantar", "shalimar_gardens", "jardim_botanico",
                "muhammad_ali_mosque")


def counts_as(key):
    """The signatures that count toward key's sums: itself and its one-offs."""
    return (key,) + tuple(s.key for s in SIGNATURES if s.family == key)


def landmark_signature(lm):
    return next((s.key for s in SIGNATURES if lm.key in s.members), None)


# Historical opportunities (§6): one per row, in gm_com_track_historical's
# order. condition: the holder's (gm_com_hist_cond_<condition>); ig: the
# parent's approving group (DEDICATIONS.approve).
HistoricalOpportunity = namedtuple("HistoricalOpportunity", "key condition ig")
HISTORICAL_OPPORTUNITIES = (
    HistoricalOpportunity("walhalla", "german", "petty_bourgeoisie"),
    HistoricalOpportunity("bunker_hill_monument", "none", "armed_forces"),
    HistoricalOpportunity("obelisk_of_the_second_of_may", "none", "armed_forces"),
    HistoricalOpportunity("muhammad_ali_mosque", "sunni", "devout"),
    HistoricalOpportunity("nelsons_column", "none", "armed_forces"),
    HistoricalOpportunity("washington_monument", "republic", "intelligentsia"),
)
HIST_CONDITIONS = {"none": "always = yes",
                   "german": "any_primary_culture = { has_discrimination_trait = language_germanophone }",
                   "sunni": "country_has_state_religion = rel:sunni",
                   "republic": "monument_government_is_republican = yes"}


class SignatureTableTests(unittest.TestCase):
    def test_the_table(self):
        keys = [s.key for s in SIGNATURES]
        self.assertEqual(len(keys), len(set(keys)))
        members = [m for s in SIGNATURES for m in s.members]
        self.assertEqual(len(members), len(set(members)), "one signature a landmark")
        landmark_keys = {lm.key for lm in LANDMARKS}
        self.assertEqual(set(members) | set(NO_SIGNATURE), landmark_keys, "every landmark has one, or is listed without")
        for s in SIGNATURES:
            self.assertIn(s.kind, ("family", "one_off", "special"), s.key)
            if s.kind == "one_off":
                self.assertEqual(SIG_BY_KEY[s.family].kind, "family", s.key)
                self.assertEqual(len(s.members), 1, s.key)
            if s.kind == "special":
                self.assertIn(s.source, SOURCE_KEYS, s.key)
                self.assertIn(s.parent, BY_KEY, s.key)
                self.assertFalse(s.members, s.key)
            self.assertTrue(s.national or s.local, f"{s.key}: does something")

    def test_a_special_is_its_boon_at_a_fifth(self):
        sources = {src.key: src for src in COMMISSION_SOURCES}
        for s in SPECIAL_SIGS:
            ((_, field, step),) = s.national
            src = sources[s.source]
            self.assertEqual(field, src.boon_field, s.key)
            self.assertAlmostEqual(step, src.boon_value * SPECIAL_BOON_SHARE, msg=s.key)
            self.assertEqual(src.special, s.key, s.key)
            # Its parent is its opportunity's only dedication (§5.4).
            begins = src.begins or ("DEDICATION = $KEY$",)
            self.assertEqual(len(begins), 1, s.key)

    def test_the_modifiers_and_their_step_mirrors(self):
        mods = read(MODIFIERS)
        values = read(SIG_VALUES)
        for s in SIGNATURES:
            for suffix, field, step in s.national:
                if field == "cultural_pull":
                    continue
                body = block(mods, f"gm_national_sig_{s.key}{suffix}")
                self.assertIsNotNone(body, s.key)
                self.assertAlmostEqual(number(body, field), step, msg=s.key)
                self.assertIn("modifier_statue_positive.dds", body)
                mirror = re.search(rf"(?m)^gm_step_sig_{s.key}{suffix} = (-?[\d.]+)\s*$", strip_comments(values))
                self.assertIsNotNone(mirror, s.key)
                self.assertAlmostEqual(float(mirror.group(1)), step, msg=s.key)
            if s.local:
                field, step = s.local
                body = block(mods, f"gm_local_sig_{s.key}")
                self.assertIsNotNone(body, s.key)
                self.assertAlmostEqual(number(body, field), step, msg=s.key)
                mirror = re.search(rf"(?m)^gm_step_sig_local_{s.key} = (-?[\d.]+)\s*$", strip_comments(values))
                self.assertAlmostEqual(float(mirror.group(1)), step, msg=s.key)
        # No other signature modifier.
        named = {n for n, _ in top_level_blocks(mods) if n.startswith(("gm_national_sig_", "gm_local_sig_"))}
        expected = {f"gm_national_sig_{s.key}{suf}" for s in SIGNATURES for suf, f, _ in s.national if f != "cultural_pull"}
        expected |= {f"gm_local_sig_{k}" for k in SIG_LOCAL}
        self.assertEqual(named, expected)

    def test_antiquitys_cultural_pull(self):
        body = squash(block(read(CULTURAL), "cultural_pull_from_antiquity"))
        self.assertIn("value = var:gm_s_sig_antiquity multiply = gm_step_sig_antiquity", body)
        # No ceiling (owner, 2026-10-19): its monuments are a fixed list.
        self.assertNotIn("max =", body)
        self.assertNotIn("gm_sig_antiquity_cap", strip_comments(read(SIG_VALUES)))
        self.assertIn("add = cultural_pull_from_antiquity", squash(block(read(CULTURAL), "cultural_pull_from_monuments")))
        self.assertNotIn("max =", squash(block(read(SIG_VALUES), "gm_display_sig_antiquity")))

    def test_loc(self):
        L = loc()
        for s in SIGNATURES:
            self.assertIn(f"gm_sig_{s.key}", L, s.key)
            self.assertIn(f"gm_sig_{s.key}_effect", L, s.key)
            if s.kind == "one_off":
                lm = s.members[0]
                self.assertEqual(L[f"gm_sig_name_{lm}"], s.name, s.key)
                self.assertEqual(L[f"gm_sig_{s.key}"], f"$gm_sig_name_{lm}$", s.key)
            else:
                self.assertEqual(L[f"gm_sig_{s.key}"], s.name, s.key)
            for suffix, field, _ in s.national:
                if field != "cultural_pull":
                    self.assertIn(f"gm_national_sig_{s.key}{suffix}", L)
                    self.assertIn(f"gm_national_sig_{s.key}{suffix}_desc", L)
            if s.local:
                self.assertIn(f"gm_local_sig_{s.key}", L)
                self.assertIn(f"gm_local_sig_{s.key}_desc", L)


class SignatureRecordTests(unittest.TestCase):
    """§1, §4.4, §7: the records, the landmark's signature, every copy point."""

    def test_on_its_parent(self):
        t = read(SIG_TRIGGERS)
        state = squash(block(t, "gm_state_sig_on_parent"))
        mon = squash(block(t, "gm_mon_sig_on_parent"))
        self.assertTrue(state.startswith("has_variable = gm_signature has_variable = gm_sig_parent "
                                         "gm_state_is_dedicated = yes OR = {"))
        self.assertTrue(mon.startswith("has_variable = gm_tr_signature has_variable = gm_tr_sig_parent OR = {"))
        for d in DEDICATIONS:
            self.assertIn(f"AND = {{ var:gm_sig_parent = flag:{d.key} gm_state_has_pm = {{ PM = pm_monument_{d.key} }} }}",
                          state, d.key)
            self.assertIn(f"AND = {{ var:gm_tr_sig_parent = flag:{d.key} gm_mon_is = {{ KEY = {d.key} }} }}", mon, d.key)
        self.assertEqual(squash(block(t, "gm_state_sig_counts")),
                         "gm_state_status_fits = yes gm_state_sig_on_parent = yes")
        self.assertEqual(squash(block(t, "gm_mon_sig_counts")), "gm_mon_status_fits = yes gm_mon_sig_on_parent = yes")

    def test_counts_as_its_family(self):
        t = read(SIG_TRIGGERS)
        for s in SIGNATURES:
            body = squash(block(t, f"gm_sig_counts_as_{s.key}"))
            self.assertIsNotNone(body, s.key)
            found = set(re.findall(r"flag:(\w+)", body)) | set(re.findall(r"SIG = (\w+)", body))
            self.assertEqual(found, set(counts_as(s.key)), s.key)

    def test_each_landmark_member_has_its_branch(self):
        body = squash(block(read(SIG_EFFECTS), "gm_sig_from_landmark"))
        branches = re.findall(r"limit = \{ has_variable = \$LM\$ (.*?) \} set_variable = \{ name = \$SIG\$ value = "
                              r"flag:(\w+) \} set_variable = \{ name = \$PARENT\$ value = flag:(\w+) \}", body)
        found = {}
        for keys, sig, parent in branches:
            for k in re.findall(r"var:\$LM\$ = flag:(\w+)", keys):
                self.assertNotIn(k, found, k)
                found[k] = (sig, parent)
        by_key = {lm.key: lm for lm in LANDMARKS}
        expected = {lm.key: (landmark_signature(lm), lm.dedication) for lm in LANDMARKS if landmark_signature(lm)}
        self.assertEqual(found, expected)
        for k in NO_SIGNATURE:
            self.assertNotIn(k, found)
            self.assertIn(k, by_key)

    def test_the_backfill_and_its_callers(self):
        e = read(SIG_EFFECTS)
        self.assertEqual(squash(block(e, "gm_state_sig_backfill")),
                         "if = { limit = { has_variable = gm_landmark NOT = { has_variable = gm_signature } } "
                         "gm_sig_from_landmark = { LM = gm_landmark SIG = gm_signature PARENT = gm_sig_parent } }")
        self.assertEqual(squash(block(e, "gm_tr_sig_backfill")),
                         "if = { limit = { has_variable = gm_tr_landmark NOT = { has_variable = gm_tr_signature } } "
                         "gm_sig_from_landmark = { LM = gm_tr_landmark SIG = gm_tr_signature PARENT = gm_tr_sig_parent } }")
        self.assertIn("gm_state_sig_backfill = yes", squash(block(read(EFFECTS), "gm_country_refresh")))
        self.assertIn("gm_tr_sig_backfill = yes", squash(block(read(MON_EFFECTS), "gm_monument_monthly")))
        tr = read("common/scripted_effects/gm_trophy_effects.txt")
        self.assertIn("gm_tr_sig_backfill = yes", squash(block(tr, "gm_trophy_monthly")))
        self.assertIn("gm_tr_sig_backfill = yes", squash(block(tr, "gm_seed_trophy")))
        self.assertIn("gm_state_sig_backfill = yes", squash(block(read(LANDMARK_EFFECTS), "gm_seed_landmark")))
        self.assertIn("gm_tr_sig_backfill = yes", squash(block(read(MON_EFFECTS), "gm_seed_landmark_beside")))
        arch = read("common/scripted_effects/gm_archaeology_effects.txt")
        self.assertIn("gm_tr_sig_backfill = yes", squash(block(arch, "gm_arch_place")))
        partage = squash(block(arch, "gm_arch_partage"))
        self.assertIn("gm_tr_sig_backfill = yes", partage)
        for var in ("gm_tr_signature", "gm_tr_sig_parent"):
            self.assertIn(f"set_variable = {{ name = {var} value = scope:gm_arch_partage_site.var:{var} }}", partage)

    def test_the_trophy_copies(self):
        """TROPHY_RECORDS: a piece too (§7); a demotion, shadow and raise are
        CONTAINER_RECORDS' (FreezeTests, MergeShadowTests, SwapTests)."""
        tr = read("common/scripted_effects/gm_trophy_effects.txt")
        make = squash(block(tr, "gm_state_tr_make_trophy"))
        piece = squash(block(read(MON_EFFECTS), "gm_mon_tr_take_piece"))
        for frm, to in (("gm_signature", "gm_tr_signature"), ("gm_sig_parent", "gm_tr_sig_parent")):
            self.assertIn((frm, to), CONTAINER_RECORDS)
            self.assertIn(f"gm_tr_copy_from_state = {{ FROM = {frm} TO = {to} }}", make)
            self.assertIn(f"gm_mon_copy_record = {{ KEY = {to} }}", piece)
        # Carried off whole, the container keeps its records: nothing forgets them.
        self.assertNotIn("signature", squash(block(read(MON_EFFECTS), "gm_mon_forget_home")))


class SignatureEffectTests(unittest.TestCase):
    """§2: national sums, local effects, the interest group."""

    def test_the_sums_walk_once(self):
        sums = squash(strip_comments(block(read(SIG_EFFECTS), "gm_sig_compute_sums")))
        self.assertEqual(sums.count("every_scope_state"), 1)
        self.assertEqual(sums.count("every_in_list"), 2)
        self.assertIn("limit = { has_building = building_grand_monument has_variable = gm_signature "
                      "gm_state_sig_counts = yes }", sums)
        self.assertIn("variable = gm_monuments_held limit = { has_variable = gm_tr_signature gm_mon_sig_counts = yes } "
                      "set_variable = { name = gm_tr_g value = gm_mon_grandeur }", sums)
        for k in SIG_NATIONAL:
            self.assertIn(f"gm_sig_zero_sum = {{ SIG = {k} }}", sums, k)
            self.assertIn(f"gm_state_sig_add_to_sum = {{ SIG = {k} }}", sums, k)
            self.assertIn(f"gm_mon_sig_add_to_sum = {{ SIG = {k} G = gm_tr_g }}", sums, k)
            self.assertIn(f"gm_mon_sig_add_to_sum = {{ SIG = {k} G = gm_tr_grandeur }}", sums, k)
            # Antiquity's cultural pull on the 1/n curve with no end, as the
            # monuments' own pull; the rest on the doubling curve (owner,
            # 2026-10-19).
            call = "gm_sig_set_steps_lin_open" if k == "antiquity" else "gm_sig_set_steps"
            self.assertIn(f"{call} = {{ SIG = {k} }}", sums, k)
        steps = squash(block(read(SIG_EFFECTS), "gm_sig_set_steps"))
        self.assertIn("gm_policy_scale_steps = { S = sig_$SIG$ FACTOR = gm_policy_factor_standing }", steps)
        lin = squash(block(read(SIG_EFFECTS), "gm_sig_set_steps_lin_open"))
        self.assertEqual(lin, "gm_set_steps_lin_open = { IN = gm_g_sig_$SIG$ OUT = gm_s_sig_$SIG$ "
                              "NEXT = gm_n_sig_$SIG$ WIDTH = gm_w_sig_$SIG$ F = 5 } "
                              "gm_policy_scale_steps = { S = sig_$SIG$ FACTOR = gm_policy_factor_standing }")
        self.assertIn("gm_sig_compute_sums = yes", squash(block(read(EFFECTS), "gm_compute_totals")))

    def test_national_hooks_from_root(self):
        apply = squash(block(read(EFFECTS), "gm_apply_national_modifiers"))
        removed = squash(block(read(EFFECTS), "gm_remove_national_modifiers"))
        for s in SIGNATURES:
            for suffix, field, _ in s.national:
                if field == "cultural_pull":
                    continue
                self.assertIn(f"gm_add_national = {{ NAME = gm_national_sig_{s.key}{suffix} VAR = gm_s_sig_{s.key} }}",
                              apply, s.key)
                self.assertIn(f"remove_modifier = gm_national_sig_{s.key}{suffix}", removed, s.key)

    def test_local_effects_on_the_state_pulse(self):
        monthly = squash(block(read(EFFECTS), "gm_state_monthly"))
        remove = squash(block(read(EFFECTS), "gm_remove_local_modifiers"))
        zero = squash(block(read(SIG_EFFECTS), "gm_state_sig_zero_local_steps"))
        for k in SIG_LOCAL:
            self.assertIn(f"gm_state_sig_local_steps_one = {{ SIG = {k} }}", monthly, k)
            self.assertIn(f"remove_modifier = gm_local_sig_{k}", remove, k)
            self.assertIn(f"gm_state_sig_zero_local_steps_one = {{ SIG = {k} }}", zero, k)
        self.assertEqual(monthly.count("gm_state_sig_zero_local_steps = yes"), 1, "in the pulse's else")
        self.assertIn("gm_state_sig_zero_local_steps = yes", squash(block(read(EFFECTS), "gm_clear_state")))
        one = squash(block(read(SIG_EFFECTS), "gm_state_sig_local_steps_one"))
        for s_ in ("gm_state_sig_on_parent = yes gm_sig_counts_as_$SIG$ = { VAR = gm_signature }",
                   "add = gm_state_primary_grandeur", "variable = gm_monuments_here",
                   "gm_mon_sig_on_parent = yes gm_sig_counts_as_$SIG$ = { VAR = gm_tr_signature }",
                   "value = gm_curve_steps_lin_f5 multiply = gm_policy_factor_local",
                   "add_modifier = { name = gm_local_sig_$SIG$ multiplier = var:gm_sig_local_steps_$SIG$ }"):
            self.assertIn(s_, one)
        self.assertNotIn("remove_variable", one, "zeroed, never removed")

    def test_its_interest_group(self):
        t = read(SIG_TRIGGERS)
        asks = {s.key for s in SIGNATURES if s.ig}
        body = squash(block(t, "gm_sig_asks_intelligentsia"))
        self.assertEqual(set(re.findall(r"gm_sig_counts_as_(\w+) = \{ VAR = \$VAR\$ \}", body)), asks)
        self.assertEqual({s.ig for s in SIGNATURES if s.ig}, {"intelligentsia"})
        for ig in IGS:
            for scope, var in (("state", "gm_signature"), ("mon", "gm_tr_signature")):
                trig = squash(block(t, f"gm_{scope}_sig_approved_by_{ig}"))
                if ig == "intelligentsia":
                    self.assertEqual(trig, f"gm_{scope}_sig_on_parent = yes gm_sig_asks_intelligentsia = {{ VAR = {var} }}")
                else:
                    self.assertEqual(trig, "always = no")
        ig = squash(block(read(EFFECTS), "gm_compute_ig"))
        self.assertIn("limit = { gm_state_status_fits = yes gm_state_sig_approved_by_$IG$ = yes } "
                      "owner = { change_variable = { name = gm_ig_net_$IG$ add = prev.var:gm_grandeur } }", ig)
        self.assertIn("limit = { gm_mon_status_fits = yes gm_mon_sig_approved_by_$IG$ = yes } "
                      "scope:gm_ig_country = { change_variable = { name = gm_ig_net_$IG$ add = prev.var:gm_tr_g } }", ig)


class SignatureNameTests(unittest.TestCase):
    """§3: the name in place of the dedication's, the parent on hover (the
    state's label) or on its own line (a container's, §3's fallback)."""

    def _branches(self, text, name):
        return re.findall(r"text = \{ trigger = \{ (.*?) \} localization_key = (\w+) \}", squash(block(text, name)))

    def test_names_come_before_the_twelve(self):
        for text, name, on, sigvar, lmvar in ((read(CUSTOM_LOC), "gm_dedication_name", "gm_state_sig_on_parent",
                                               "gm_signature", "gm_landmark"),
                                              (read("common/customizable_localization/gm_trophy_custom_loc.txt"),
                                               "gm_tr_dedication_name", "gm_mon_sig_on_parent", "gm_tr_signature",
                                               "gm_tr_landmark")):
            branches = self._branches(text, name)
            keys = [k for _, k in branches]
            first_plain = keys.index("pm_monument_crown")
            for s in SIGNATURES:
                i = keys.index(f"gm_sig_{s.key}")
                self.assertLess(i, first_plain, s.key)
                self.assertEqual(branches[i][0], f"{on} = yes gm_sig_var_is = {{ VAR = {sigvar} SIG = {s.key} }}")
                if s.kind == "one_off":
                    lm = s.members[0]
                    j = keys.index(f"gm_sig_name_{lm}")
                    self.assertLess(j, i, f"{s.key}: the landmark's own name first")
                    self.assertEqual(branches[j][0], f"{on} = yes gm_sig_var_is = {{ VAR = {sigvar} SIG = {s.key} }} "
                                                     f"has_variable = {lmvar} var:{lmvar} = flag:{lm}")

    def test_the_label_and_its_hover(self):
        L = loc()
        label = squash(block(read(SIG_CUSTOM_LOC), "gm_dedication_label"))
        self.assertEqual(label, "type = state random_valid = no text = { trigger = { has_variable = gm_signature } "
                                "localization_key = gm_sig_label } text = { localization_key = gm_sig_label_plain }")
        self.assertEqual(L["gm_sig_label"],
                         "#tooltippable;tooltip:[State.GetTooltipTag],gm_sig_parent_tt [State.GetCustom('gm_dedication_name')]#!")
        self.assertEqual(L["gm_sig_label_plain"], "[State.GetCustom('gm_dedication_name')]")
        for key in ("gm_row_title", "gm_row_title_named"):
            self.assertIn("[State.GetCustom('gm_dedication_label')]", L[key])
        for part in ("gm_sig_name", "gm_sig_parent_name", "gm_sig_effect", "gm_sig_status"):
            self.assertIn(f"[State.GetCustom('{part}')]", L["gm_sig_parent_tt"], part)

    def test_a_containers_line(self):
        L = loc()
        gui = read("gui/gm_trophy_widgets.gui")
        line = ('gm_tr_line = { visible = "[EqualTo_CFixedPoint( ScriptContainer.MakeScope.ScriptValue('
                "'gm_tr_disp_has_sig'), '(CFixedPoint)1' )]\" default_format = \"#tooltippable\" "
                'tooltip = "gm_tr_sig_tt" text = "gm_tr_row_sig" }')
        self.assertEqual(squash(gui).count(line), 4, "the three trophy rows and a monument beside another")
        self.assertEqual(L["gm_tr_row_sig"], "[ScriptContainer.GetCustom('gm_tr_sig_line')]")
        for key in ("gm_tr_sig_line_on", "gm_tr_sig_line_dormant", "gm_tr_sig_tt"):
            self.assertNotIn("State.", L[key].replace("GetState.", ""), key)

    def test_effect_names_shown(self):
        L = loc()
        for s in SIGNATURES:
            if s.kind == "one_off":
                self.assertIn(f"$gm_sig_{s.family}$", L[f"gm_sig_{s.key}_effect"], "names its family's effect")
            if s.ig:
                self.assertIn(f"$ig_{s.ig}$", L[f"gm_sig_{s.key}_effect"], s.key)


class SignatureSpecialTests(unittest.TestCase):
    """§5: one monument a completion, held when it can't, the ceremony's option."""

    def test_the_source_mapping(self):
        body = squash(block(read(SIG_EFFECTS), "gm_sig_special_for_source"))
        self.assertTrue(body.startswith("gm_remove_state_var = { VAR = gm_sig_special }"))
        for s in SPECIAL_SIGS:
            self.assertIn(f"limit = {{ has_variable = gm_com_source var:gm_com_source = flag:{s.source} }} "
                          f"set_variable = {{ name = gm_sig_special value = flag:{s.key} }}", body, s.key)
        parent = squash(block(read(SIG_EFFECTS), "gm_sig_set_special_parent"))
        for s in SPECIAL_SIGS:
            self.assertIn(f"limit = {{ var:$SIGVAR$ = flag:{s.key} }} set_variable = {{ name = $VAR$ value = flag:{s.parent} }}",
                          parent, s.key)
        self.assertEqual({src.special for src in COMMISSION_SOURCES if src.special},
                         {s.key for s in SPECIAL_SIGS})

    def test_granted_on_both_paths(self):
        fulfil = squash(strip_comments(block(read(COM_EFFECTS), "gm_com_fulfil")))
        self.assertIn("save_scope_as = gm_sig_granter gm_sig_special_for_source = yes", fulfil)
        self.assertIn("set_variable = { name = gm_sig_grant value = scope:gm_sig_granter.var:gm_sig_special }", fulfil)
        self.assertLess(fulfil.index("set_variable = gm_gift"), fulfil.index("name = gm_sig_grant"))
        self.assertLess(fulfil.index("name = gm_sig_grant"), fulfil.index("trigger_event = { id = monument_events.26 }"))
        beside = fulfil[fulfil.index("scope:gm_com_gift_mon = { gm_mon_add_age = { AGE = gm_com_gift } }"):]
        self.assertIn("scope:gm_com_gift_mon = { gm_mon_takes_special = yes } } scope:gm_com_gift_mon = "
                      "{ gm_mon_sig_take_special = yes }", beside)
        self.assertIn("else = { gm_sig_hold_special = yes }", beside)
        ev = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.26\s*=\s*\{")))
        self.assertIn("gm_state_sig_take_grant = yes", ev)
        take = squash(block(read(SIG_EFFECTS), "gm_state_sig_take_grant"))
        self.assertIn("limit = { gm_state_takes_grant = yes } set_variable = { name = gm_signature value = var:gm_sig_grant }",
                      take)
        for s in SPECIAL_SIGS:
            self.assertIn(f"limit = {{ var:gm_sig_grant = flag:{s.key} }} owner = {{ gm_sig_hold = {{ SIG = {s.key} }} }}",
                          take, s.key)
        takes = squash(block(read(SIG_TRIGGERS), "gm_state_takes_grant"))
        for s in SPECIAL_SIGS:
            self.assertIn(f"AND = {{ var:gm_sig_grant = flag:{s.key} gm_state_has_pm = {{ PM = pm_monument_{s.parent} }} }}",
                          takes, s.key)

    def test_held_in_a_country_variable(self):
        hold = squash(block(read(SIG_EFFECTS), "gm_sig_hold"))
        self.assertIn("change_variable = { name = gm_sig_held_$SIG$ add = 1 }", hold)
        self.assertIn("set_variable = { name = gm_sig_held_$SIG$ value = 1 }", hold)
        idle = squash(block(read(SIG_TRIGGERS), "gm_sig_held_idle"))
        for s in SPECIAL_SIGS:
            self.assertIn(f"NOT = {{ gm_sig_holds = {{ SIG = {s.key} }} }}", idle, s.key)
            self.assertIn(f"gm_disp_sig_held_{s.key}", read(WIDGET), s.key)

    def test_the_ceremony_option(self):
        options = ceremony_options()
        L = loc()
        for s in SPECIAL_SIGS:
            body = squash(strip_comments(options[f"sig_{s.key}"]))
            self.assertIn(f"trigger = {{ custom_tooltip = {{ text = gm_ded_reason_special_tt "
                          f"gm_state_ceremony_offers_special = {{ SIG = {s.key} }} }}", body, s.key)
            self.assertNotIn("show_as_unavailable", body, "hidden, not greyed")
            self.assertIn(f"custom_tooltip = {{ text = monument_events.2.sig_{s.key}.tt "
                          f"gm_state_dedicate_sig_{s.key} = yes }}", body, s.key)
            self.assertIn("base = 1000", body, "the AI takes one whenever offered")
            parent = BY_KEY[s.parent]
            if s.parent in TECH_GATES:
                self.assertIn(f"has_technology_researched = {TECH_GATES[s.parent]}", body, s.key)
            wrapper = squash(block(read(SIG_EFFECTS), f"gm_state_dedicate_sig_{s.key}"))
            self.assertEqual(wrapper, f"{wrapper_call(parent)} gm_state_sig_give = {{ SIG = {s.key} PARENT = {s.parent} }}")
            tt = L[f"monument_events.2.sig_{s.key}.tt"]
            self.assertIn(f"$monument_events.2.{CEREMONY_OPTION[s.parent]}.tt$", tt, "names the parent's effects too")
            self.assertNotRegex(tt.split("$monument_events")[0], r"#G [+\-−]?\d", "numbers from gm_step_sig_*")
        give = squash(block(read(SIG_EFFECTS), "gm_state_sig_give"))
        self.assertEqual(give, "set_variable = { name = gm_signature value = flag:$SIG$ } set_variable = "
                               "{ name = gm_sig_parent value = flag:$PARENT$ } owner = { gm_sig_unhold = { SIG = $SIG$ } }")
        offers = squash(block(read(SIG_TRIGGERS), "gm_state_ceremony_offers_special"))
        self.assertEqual(offers, "NOT = { has_variable = gm_signature } owner = { gm_sig_holds = { SIG = $SIG$ } }")

    def test_the_offer_line(self):
        L = loc()
        line = squash(block(read(SIG_CUSTOM_LOC), "gm_com_special_line"))
        for s in SPECIAL_SIGS:
            self.assertIn(f"gm_com_source_is = {{ SRC = {s.source} }} }} localization_key = gm_com_special_line_{s.key}",
                          line, s.key)
            self.assertIn(f"$gm_sig_{s.key}$", L[f"gm_com_special_line_{s.key}"])
        for key, ctx in (("gm_com_accept_tt", "ROOT.GetCountry"), ("gm_je_com_reward_tt", "JournalEntry.GetCountry")):
            self.assertIn(f"[{ctx}.GetCustom('gm_com_special_line')]", L[key])
        for key, ctx in (("gm_com_decline_tt", "ROOT.GetCountry"),
                         ("gm_button_com_let_pass_tooltip", "JournalEntry.GetCountry")):
            self.assertIn(f"[{ctx}.GetCustom('gm_com_special_pass_line')]", L[key])
        once = squash(block(read(SIG_CUSTOM_LOC), "gm_com_special_pass_line"))
        for s in SPECIAL_SIGS:
            # A moment that comes once a game says that letting it pass loses it.
            self.assertEqual(f"gm_com_special_pass_{s.key}" in once, s.source in ("great_power", "space", "tech_athletic"))

    def test_old_saves(self):
        seed = squash(block(read(SIG_EFFECTS), "gm_sig_seed_monthly"))
        self.assertIn("global_var:gm_sig_seed_round < gm_sig_seed_rounds", seed)
        for s in SPECIAL_SIGS:
            self.assertIn(f"limit = {{ has_variable = gm_boon_{s.source} var:gm_boon_{s.source} > 0 }} "
                          f"gm_sig_hold = {{ SIG = {s.key} }}", seed, s.key)
        self.assertIn("gm_sig_seed_monthly = yes", squash(block(read(MON_EFFECTS), "gm_monument_monthly")))

    def test_the_seized_event_names_it(self):
        ev = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.28\s*=\s*\{")))
        for key in ("d_special", "d_held", "d_unnamed_special", "d_unnamed_held", "d_historical", "d_unnamed_historical"):
            self.assertIn(f"desc = monument_events.28.{key}", ev, key)
            self.assertIn(f"monument_events.28.{key}", loc(), key)


class HistoricalOpportunityTests(unittest.TestCase):
    """§6: offered once a game, to whoever holds its state, for forty years from
    the year its construction began; completing it makes the landmark."""

    def test_a_call_per_row(self):
        by_key = {lm.key: lm for lm in LANDMARKS}
        body = squash(block(read(COM_EFFECTS), "gm_com_track_historical"))
        calls = re.findall(r"gm_com_try_historical = \{[^{}]*\}", body)
        expected = []
        for h in HISTORICAL_OPPORTUNITIES:
            lm = by_key[h.key]
            self.assertEqual(h.ig, BY_KEY[lm.dedication].approve, h.key)
            expected.append(f"gm_com_try_historical = {{ KEY = {h.key} STATE = {lm.state} FROM = {lm.year} "
                            f"UNTIL = {lm.year + 40} DEDICATION = {lm.dedication} LEVEL = {lm.level} IG = {h.ig} "
                            f"COND = {h.condition} }}")
        self.assertEqual(calls, expected)
        self.assertEqual({h.key for h in HISTORICAL_OPPORTUNITIES}, {lm.key for lm in LANDMARKS if lm.year})
        self.assertTrue(squash(block(read(COM_EFFECTS), "gm_com_world_monthly")).endswith(
            "gm_com_track_historical = yes"), "last: a window waits for the moments")

    def test_the_offer(self):
        body = squash(block(read(COM_EFFECTS), "gm_com_try_historical"))
        for s_ in ("NOT = { has_global_variable = gm_hist_offered_$KEY$ }", "game_date >= $FROM$.1.1",
                   "game_date < $UNTIL$.1.1", "gm_com_can_offer = yes", "has_state_in_state_region = $STATE$",
                   "gm_com_hist_cond_$COND$ = yes", "gm_country_can_raise_$DEDICATION$ = yes",
                   "set_global_variable = gm_hist_offered_$KEY$",
                   "gm_com_begin = { SOURCE = historical DEDICATION = $DEDICATION$ NAMESAKE = year FORM = default }",
                   "set_variable = { name = gm_com_landmark value = flag:$KEY$ }",
                   "set_variable = { name = gm_com_target value = $LEVEL$ }",
                   "set_variable = { name = gm_com_ig value = flag:$IG$ }", "gm_com_send_offer = yes"):
            self.assertIn(s_, body)
        self.assertNotIn("country_rank", body, "no rank gate")
        t = read(COM_TRIGGERS)
        for cond, trig in HIST_CONDITIONS.items():
            self.assertEqual(squash(block(t, f"gm_com_hist_cond_{cond}")), trig, cond)
            self.assertIn(f"AND = {{ var:gm_com_hist_cond = flag:{cond} gm_com_hist_cond_{cond} = yes }}",
                          squash(block(t, "gm_com_hist_cond_holds")))
        self.assertIn("gm_com_hist_cond_holds = no", squash(block(t, "gm_com_has_lapsed")))
        clear = squash(block(read(COM_EFFECTS), "gm_com_clear"))
        for var in ("gm_com_landmark", "gm_com_hist_cond"):
            self.assertIn(f"gm_remove_state_var = {{ VAR = {var} }}", clear)
        self.assertNotIn("gm_com_grant_boon_one = { SRC = historical }",
                         squash(block(read(COM_EFFECTS), "gm_com_grant_boon")), "no boon")

    def test_completion_makes_the_landmark(self):
        by_key = {lm.key: lm for lm in LANDMARKS}
        take = squash(block(read(COM_EFFECTS), "gm_state_hist_take"))
        mon = squash(block(read(COM_EFFECTS), "gm_mon_hist_take"))
        for h in HISTORICAL_OPPORTUNITIES:
            lm = by_key[h.key]
            self.assertIn(f"limit = {{ var:gm_hist_become = flag:{h.key} }} gm_state_become_landmark = "
                          f"{{ KEY = {h.key} FORM = {lm.form} }}", take, h.key)
            self.assertIn(f"gm_mon_become_landmark = {{ KEY = {h.key} FORM = {lm.form} }}", mon, h.key)
        become = squash(block(read(COM_EFFECTS), "gm_state_become_landmark"))
        for s_ in ("set_variable = { name = gm_landmark value = flag:$KEY$ }",
                   "set_variable = { name = gm_skin value = flag:landmark_$KEY$ }",
                   "set_variable = { name = gm_form value = flag:$FORM$ }",
                   "set_variable = { name = gm_namesake value = flag:landmark }", "gm_state_sig_backfill = yes",
                   "gm_state_update_picture = yes"):
            self.assertIn(s_, become)
        fulfil = squash(strip_comments(block(read(COM_EFFECTS), "gm_com_fulfil")))
        self.assertIn("set_variable = { name = gm_hist_become value = scope:gm_sig_granter.var:gm_com_landmark }", fulfil)
        self.assertIn("scope:gm_com_gift_mon = { gm_mon_hist_take = yes }", fulfil)

    def test_time_and_text(self):
        L = loc()
        self.assertIn("var:gm_com_target > 5 } multiply = var:gm_com_target divide = 5",
                      squash(strip_comments(block(read(COM_VALUES), "gm_com_time_months"))))
        occasion = squash(block(read(CUSTOM_LOC), "gm_com_occasion_name"))
        for h in HISTORICAL_OPPORTUNITIES:
            self.assertIn(f"var:gm_com_landmark = flag:{h.key} }} localization_key = gm_skin_landmark_{h.key}", occasion)
        self.assertIn("desc = monument_events.21.d_historical",
                      squash(raw_block_at(read(EVENTS), r"(?m)^monument_events\.21\s*=\s*\{")))
        for key in ("monument_events.21.d_historical", "gm_com_accept_hist_tt", "gm_je_com_reward_hist",
                    "gm_je_com_named_hist", "gm_com_boon_historical"):
            self.assertIn(key, L)


class SignatureDebugTests(unittest.TestCase):
    def test_the_debug_event(self):
        text = read(DEBUG_EVENTS)
        self.assertRegex(text, r"(?m)^te_debug_monuments\.8 = \{ # REVIEWED \d{4}-\d{2}-\d{2}: console-only")
        ev = squash(strip_comments(raw_block_at(text, r"(?m)^te_debug_monuments\.8\s*=\s*\{")))
        for s in SPECIAL_SIGS:
            self.assertIn(f"gm_sig_hold = {{ SIG = {s.key} }}", ev)
        self.assertIn("gm_state_sig_backfill = yes", ev)
        self.assertIn("gm_tr_sig_backfill = yes", ev)
        self.assertIn("scope:gm_dbg_m1 = { gm_debug_next_signature = yes }", ev)
        self.assertIn("name = te_debug_monuments.8.d default_option = yes gm_sig_debug_log = yes", ev)
        L = loc()
        for k in ("t", "desc", "flavor", "a", "b", "c", "d"):
            self.assertIn(f"te_debug_monuments.8.{k}", L)
        code = squash(block(read(SIG_VALUES), "gm_disp_sig_code"))
        for i, s in enumerate(SIGNATURES, 1):
            self.assertIn(f"gm_sig_var_is = {{ VAR = gm_signature SIG = {s.key} }} }} value = {i} }}", code, s.key)
        log = squash(block(read(SIG_EFFECTS), "gm_sig_debug_log"))
        self.assertNotIn(".MakeScope", log, "debug_log's working form only")
        for k in SIG_NATIONAL:
            self.assertIn(f"gm_display_g_sig_{k}", log)


class OptionReasonTests(unittest.TestCase):
    """Every gated dedication (monument_events.2) and style (.11) says why it is
    or isn't offered (event_creation_guide.md, greyed options). The engine prints
    an option's conditions only on a highlighted option, and only when it is
    unavailable; an available highlighted option lists its effects under "This
    option is available because:". So each gate sits in a custom_tooltip whose
    text names the reason (shown when greyed), the dedication event's gated
    options are highlighted, and each reason is repeated as the option's first
    effect, in the owner's scope, behind the same gate when the option can be
    greyed (shown when offered)."""

    @staticmethod
    def _own_trigger(body):
        """The option's own `trigger = { }` (depth 0 in the option), or None:
        ai_chance modifiers carry triggers of their own."""
        depth = 0
        for m in re.finditer(r"\{|\}|\btrigger\s*=\s*\{", body):
            if m.group(0) == "{":
                depth += 1
            elif m.group(0) == "}":
                depth -= 1
            elif depth == 0:
                return _match_brace(body, m.end())
            else:
                depth += 1
        return None

    def _options(self, eid):
        ev = strip_comments(raw_block_at(read(EVENTS), rf"(?m)^{re.escape(eid)}\s*=\s*\{{"))
        for m in re.finditer(r"(?m)^\toption\s*=\s*\{", ev):
            body = _match_brace(ev, m.end())
            yield re.search(r"\bname\s*=\s*(\S+)", body).group(1), self._own_trigger(body)

    @staticmethod
    def _reasons(trig):
        """(text key, gate) per custom_tooltip, and what is left outside them and hidden_triggers."""
        out, rest = [], trig
        for opener in ("custom_tooltip", "hidden_trigger"):
            for m in re.finditer(rf"\b{opener}\s*=\s*\{{", trig):
                inner = _match_brace(trig, m.end())
                rest = rest.replace(inner, "", 1)
                if opener == "custom_tooltip":
                    key = re.search(r"\btext\s*=\s*(\w+)", inner).group(1)
                    out.append((key, squash(re.sub(r"\btext\s*=\s*\w+", "", inner))))
        rest = re.sub(r"\b(custom_tooltip|hidden_trigger)\s*=\s*\{\s*\}", "", rest)
        return out, squash(rest)

    def test_every_gate_carries_a_reason(self):
        L = loc()
        gated = 0
        for eid in ("monument_events.2", "monument_events.11"):
            for name, trig in self._options(eid):
                if trig is None:
                    continue
                gated += 1
                with self.subTest(option=name):
                    reasons, rest = self._reasons(trig)
                    self.assertEqual(rest, "", "a gate outside any custom_tooltip draws no reason")
                    self.assertTrue(reasons)
                    for key, _ in reasons:
                        self.assertIn(key, L, key)
        self.assertGreaterEqual(gated, 16 + 2 + 47)

    def test_a_style_names_its_own_heritage(self):
        heritages = re.findall(r"(?m)^te_heritage_(\w+)\s*=\s*\{",
                               read("common/scripted_triggers/te_heritage_triggers.txt"))
        L = loc()
        for h in heritages:
            if h != "any":
                self.assertIn(f"gm_skin_reason_{h}_tt", L, h)
        for name, trig in self._options("monument_events.11"):
            if trig is None:
                continue
            for key, gate in self._reasons(trig)[0]:
                with self.subTest(option=name):
                    h = re.search(r"te_heritage_(\w+) = yes", gate)
                    self.assertEqual(key, f"gm_skin_reason_{h.group(1)}_tt" if h else "gm_skin_reason_faith_tt", gate)

    def test_the_reason_shows_when_offered_too(self):
        for eid in ("monument_events.2", "monument_events.11"):
            ev = strip_comments(raw_block_at(read(EVENTS), rf"(?m)^{re.escape(eid)}\s*=\s*\{{"))
            for m in re.finditer(r"(?m)^\toption\s*=\s*\{", ev):
                body = _match_brace(ev, m.end())
                name = re.search(r"\bname\s*=\s*(\S+)", body).group(1)
                trig = self._own_trigger(body)
                # Not yet and Keep it as it is dedicate nothing (sites spec 2026-10-18).
                if trig is None or name in ("monument_events.2.a", "monument_events.2.keep"):
                    continue
                reasons = self._reasons(trig)[0]
                flat = squash(body)
                with self.subTest(option=name):
                    if eid == "monument_events.2":
                        self.assertIn("highlighted_option = yes", flat)
                    lines = " ".join(f"owner = {{ custom_tooltip = {key} }}" for key, _ in reasons)
                    if "show_as_unavailable" in flat:
                        gates = " ".join(gate for _, gate in reasons)
                        self.assertIn(f"if = {{ limit = {{ {gates} }} {lines} }}", flat,
                                      "a greyed option must not claim a reason it doesn't meet")
                    else:
                        self.assertIn(lines, flat)


# ---- Dedicate (owner, 2026-10-18) -------------------------------------------------------

SITE_BUILDING = "common/buildings/grand_monument_site.txt"


class SiteBuildingTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.1: a player builds and expands a construction
    site; the finished monument is a level-1 building only script makes."""

    def test_the_finished_type(self):
        body = squash(block(read(BUILDING), "building_grand_monument"))
        for s in ("buildable = no", "expandable = no", "downsizeable = no", "building_group = bg_grand_monuments",
                  "pmg_monument_dedication pmg_maintenance", "gm_system_enabled = yes"):
            self.assertIn(s, body)
        for s in ("ai_value", "can_build_government", "can_build_private", "unlocking_technologies"):
            self.assertNotIn(s, body)

    def test_the_site_type(self):
        body = squash(block(read(SITE_BUILDING), "building_grand_monument_site"))
        for s in ("building_group = bg_grand_monuments", "expandable = yes", "downsizeable = yes",
                  "production_method_groups = { pmg_grand_monument_site }",
                  "required_construction = construction_cost_grand_monument",
                  "can_build_government = { gm_state_can_build_site = yes }",
                  "can_build_private = { gm_state_can_build_site = yes }",
                  "gm_system_enabled = yes", "value = gm_state_monument_count multiply = -25",
                  "gm_country_hard_times = yes"):
            self.assertIn(s, body)
        self.assertNotIn("buildable = no", body)

    def test_the_site_method_does_nothing(self):
        self.assertEqual(squash(block(read(PMG), "pmg_grand_monument_site")).split("production_methods = ")[1],
                         "{ pm_grand_monument_site }")
        pm = squash(block(read(PMS), "pm_grand_monument_site"))
        for s in ("building_modifiers", "state_modifiers", "country_modifiers", "goods_"):
            self.assertNotIn(s, pm)
        for key in ("building_grand_monument_site", "building_grand_monument_site_desc",
                    "pmg_grand_monument_site", "pm_grand_monument_site"):
            self.assertIn(key, loc(), key)

    def test_the_gate(self):
        gate = squash(block(read(MON_TRIGGERS), "gm_state_can_build_site"))
        self.assertTrue(gate.startswith("trigger_if = { limit = { NOT = { has_variable = gm_rebuilding } "
                                        "NOT = { b:building_grand_monument_site ?= { is_under_construction = yes } } }"))
        for s in ("NOT = { gm_state_is_contested = yes }", "NOT = { has_variable = gm_ceremony_pending }",
                  "NOT = { has_variable = gm_unveil_pending }", "NOT = { has_variable = gm_name_choice_open }",
                  "NOT = { has_variable = gm_being_named }", "NOT = { has_variable = gm_restore_pm }",
                  "NOT = { has_variable = gm_gift }", "gm_state_monument_count < 6"):
            self.assertIn(s, gate)
        self.assertIsNone(block(read(MON_TRIGGERS), "gm_state_can_expand"))

    def test_presence(self):
        mon = read(MON_VALUES)
        self.assertEqual(squash(block(read(VALUES), "gm_state_site_level")),
                         "value = 0 if = { limit = { has_building = building_grand_monument_site } "
                         "value = b:building_grand_monument_site.level }")
        self.assertEqual(squash(block(read(TRIGGERS), "gm_state_has_site")),
                         "has_building = building_grand_monument_site")
        self.assertIn("if = { limit = { has_building = building_grand_monument_site } add = 1 }",
                      squash(block(mon, "gm_state_monument_count")))

    def test_the_pulse_reaches_a_site(self):
        on_action = squash(block(read(ON_ACTIONS), "gm_state_on_action"))
        self.assertIn("has_building = building_grand_monument_site", on_action)
        monthly = squash(strip_comments(block(read(EFFECTS), "gm_state_monthly")))
        self.assertIn("gm_state_count_site_levels = yes", monthly)
        self.assertLess(monthly.find("gm_state_count_site_levels = yes"),
                        monthly.find("if = { limit = { has_building = building_grand_monument }"))

    def test_the_tracker(self):
        body = squash(strip_comments(block(read(EFFECTS), "gm_state_count_site_levels")))
        for s in ("limit = { gm_state_site_level > var:gm_site_counted }",
                  "change_variable = { name = gm_site_grandeur add = var:gm_site_add }",
                  "gm_state_vanity_backlash_for = { AMOUNT = prev.var:gm_site_add }",
                  "set_variable = { name = gm_site_counted value = gm_state_site_level }",
                  "limit = { gm_state_site_level < var:gm_site_counted }",
                  "remove_variable = gm_site_counted", "remove_variable = gm_site_grandeur"):
            self.assertIn(s, body)
        vanity = squash(block(read(EFFECTS), "gm_state_vanity_backlash_for"))
        self.assertIn("change_variable = { name = gm_vanity_ledger add = $AMOUNT$ }", vanity)
        self.assertIn("add_radicals_in_state = { value = 0.005 }", vanity)

    def test_vanity_left_the_level_hook(self):
        ev1 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.1\s*=\s*\{")))
        self.assertNotIn("gm_state_vanity_backlash", ev1)
        self.assertNotIn("gm_state_count_site_levels", squash(strip_comments(block(read(EFFECTS),
                                                                                  "gm_country_refresh"))))


class SiteConstructionTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.1, §4: the finished type can no longer be
    built, so everything that queues or reads monument construction names
    the site."""

    def test_the_queue_builds_a_site(self):
        com = read(COM_EFFECTS)
        queue = squash(block(com, "gm_com_queue_levels"))
        self.assertIn("start_building_construction = building_grand_monument_site", queue)
        self.assertNotIn("start_building_construction = building_grand_monument ", queue + " ")
        ai = squash(block(com, "gm_com_ai_queue"))
        self.assertIn("set_variable = { name = gm_com_raise_levels value = gm_com_levels_to_go }", ai)

    def test_the_picker(self):
        pick = squash(strip_comments(block(read(COM_EFFECTS), "gm_com_pick_build_state")))
        self.assertNotIn("gm_state_can_expand", pick)
        self.assertIn("gm_state_can_build_site = yes", pick)
        self.assertIn("gm_state_has_site = yes", pick)
        self.assertLess(pick.find("gm_state_has_site = yes"), pick.find("capital"))

    def test_under_construction_is_the_site(self):
        self.assertEqual(squash(block(read(COM_TRIGGERS), "gm_com_monument_under_construction")),
                         "any_scope_building = { is_building_type = building_grand_monument_site "
                         "is_under_construction = yes }")


class SiteDedicationTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.1: Dedicate opens the ceremony on a site; the
    answer removes the site and writes its records onto the state, a
    finished monument standing here moving beside the new one first."""

    def body(self, path, name):
        return squash(strip_comments(block(read(path), name)))

    def ceremony(self):
        return squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.2\s*=\s*\{")))

    def test_the_answer_finishes_the_site(self):
        body = self.body(EFFECTS, "gm_state_finish_site")
        order = ["gm_state_count_site_levels = yes",
                 "limit = { has_building = building_grand_monument has_variable = gm_seen }",
                 "set_variable = { name = gm_demote_levels value = gm_state_primary_levels }",
                 "gm_state_demote_primary = yes", "set_variable = gm_newcomer",
                 "set_variable = { name = gm_levels value = var:gm_site_counted }",
                 "set_variable = { name = gm_start_grandeur value = var:gm_site_grandeur }",
                 "set_variable = { name = gm_rebuilding days = 1 }",
                 "remove_building = building_grand_monument_site",
                 "create_building = { building = building_grand_monument level = 1 "
                 "activate_production_methods = { pm_monument_$KEY$ } }",
                 "set_variable = { name = gm_restore_pm value = flag:$KEY$ }",
                 "set_variable = gm_site_created",
                 "remove_variable = gm_site_counted"]
        positions = [body.find(s) for s in order]
        self.assertNotIn(-1, positions, [s for s, p in zip(order, positions) if p == -1])
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("gm_state_swap_primary", body, "the grander stands first a day later (.29)")

    def test_the_dedication_reads_its_mode(self):
        body = self.body(EFFECTS, "gm_state_dedicate")
        self.assertTrue(body.startswith(
            "if = { limit = { has_variable = gm_ceremony_mode var:gm_ceremony_mode = flag:site } "
            "gm_state_finish_site = { KEY = $KEY$ } } else_if = { limit = { has_variable = gm_ceremony_mode "
            "var:gm_ceremony_mode = flag:rededicate } gm_state_apply_rededicate = yes } "
            "gm_remove_state_var = { VAR = gm_ceremony_mode }"))
        # A building just created is on its method; one standing switches once.
        self.assertIn("NOT = { has_variable = gm_site_created } NOT = { gm_state_has_pm = { PM = pm_monument_$KEY$ } }",
                      body)
        self.assertIn("if = { limit = { NOT = { has_variable = gm_levels } } "
                      "set_variable = { name = gm_levels value = gm_state_primary_levels } }", body)
        self.assertIn("gm_remove_state_var = { VAR = gm_site_created }", body)

    def test_the_ceremony_knows_what_it_asks_about(self):
        start = self.body(EFFECTS, "gm_state_start_ceremony")
        for s in ("limit = { has_variable = gm_rededicate_asking } "
                  "set_variable = { name = gm_ceremony_mode value = flag:rededicate } "
                  "remove_variable = gm_rededicate_asking",
                  "limit = { has_building = building_grand_monument_site } "
                  "set_variable = { name = gm_ceremony_mode value = flag:site }",
                  "set_variable = { name = gm_ceremony_level value = gm_state_site_level }"):
            self.assertIn(s, start)
        ev = self.ceremony()
        for s in ("var:gm_ceremony_mode = flag:site has_building = building_grand_monument_site",
                  "var:gm_ceremony_mode = flag:rededicate has_building = building_grand_monument has_variable = gm_seen"):
            self.assertIn(s, ev)
        self.assertNotIn("trigger = { gm_system_enabled = yes any_scope_building", ev)

    def test_not_yet_is_a_sites_and_keep_is_rededicates(self):
        ev = self.ceremony()
        options = re.findall(r"option = \{ name = (monument_events\.2\.\w+) (.*?) \}(?= option = \{|$)", ev)
        not_rededicate = "hidden_trigger = { NOT = { has_variable = gm_ceremony_mode var:gm_ceremony_mode = flag:rededicate } }"
        a = [b for n, b in options if n == "monument_events.2.a"]
        keep = [b for n, b in options if n == "monument_events.2.keep"]
        self.assertEqual(len(a), 2)
        self.assertEqual(len(keep), 2)
        for b in a:
            self.assertIn(not_rededicate, b)
        for b in keep:
            self.assertIn("var:gm_ceremony_mode = flag:rededicate", b)
            self.assertIn("ai_chance = { base = 0 }", b)
            self.assertIn("gm_remove_state_var = { VAR = gm_ceremony_mode }", b)
        # Exactly one default is valid however the two questions fall.
        self.assertIn("default_option = yes", keep[0])
        self.assertIn("gm_state_ceremony_offers_opportunity = no", keep[0])
        self.assertNotIn("default_option = yes", keep[1])
        for key in ("monument_events.2.keep", "monument_events.2.keep.tt", "monument_events.2.d_rededicate"):
            self.assertIn(key, loc(), key)

    def test_beside_a_grander_one(self):
        """The Arc de Triomphe stays the state's monument: the new one is the
        newcomer, and the grander swaps back in only from .29, a day later,
        once the newcomer is settled (one method switch a tick)."""
        self.assertIn("set_variable = gm_newcomer", self.body(EFFECTS, "gm_state_finish_site"))
        settled = self.body(TRIGGERS, "gm_state_newcomer_settled")
        self.assertIn("has_variable = gm_newcomer", settled)
        ev29 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.29\s*=\s*\{")))
        self.assertIn("gm_state_settle_newcomer = yes", ev29)

    def test_the_ai_dedicates_a_site_once_nothing_is_queued(self):
        self.assertEqual(self.body(TRIGGERS, "gm_state_ai_dedicates_now"),
                         "owner = { is_ai = yes } gm_state_has_site = yes gm_state_site_level >= 1 "
                         "b:building_grand_monument_site ?= { is_under_construction = no }")
        ev1 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.1\s*=\s*\{")))
        self.assertIn("is_building_type = building_grand_monument_site", ev1)
        self.assertIn("gm_state_ai_dedicates_now = yes NOT = { has_variable = gm_ceremony_pending } } "
                      "gm_state_start_ceremony = yes", ev1)
        missed = self.body(EFFECTS, "gm_state_offer_missed_ceremony")
        self.assertIn("gm_state_ai_dedicates_now = yes", missed)
        self.assertIn("gm_state_start_ceremony = yes", missed)


class RededicateTests(unittest.TestCase):
    """Sites spec 2026-10-18 §5, a call for the owner: Rededicate asks first;
    the answer pays and halves; "Keep it as it is" changes nothing."""

    def body(self, path, name):
        return squash(strip_comments(block(read(path), name)))

    def test_the_press_only_asks(self):
        body = self.body(EFFECTS, "gm_state_rededicate")
        self.assertIn("set_variable = gm_rededicate_asking", body)
        self.assertIn("gm_state_start_ceremony = yes", body)
        for s in ("add_treasury", "remove_building", "te_construction_market_build_specified_level",
                  "gm_clear_state"):
            self.assertNotIn(s, body)

    def test_the_answer_pays_and_halves(self):
        body = self.body(EFFECTS, "gm_state_apply_rededicate")
        order = ["set_variable = { name = gm_rededicate_cost value = gm_state_rededicate_cost }",
                 "add_treasury = { value = prev.var:gm_rededicate_cost multiply = -1 }",
                 "gm_state_ledger_ig = { WHO = gm_supporter_ig FACTOR = -0.5 }",
                 "name = gm_rededicate_levels value = { value = gm_state_primary_levels divide = 2 ceiling = yes }",
                 "name = gm_rededicate_start value = { value = gm_state_primary_start divide = 2 }",
                 "name = gm_rededicate_age value = { value = gm_state_primary_age divide = 2 }",
                 "gm_clear_state = { KEEP_LANDMARK = yes }",
                 "set_variable = { name = gm_levels value = var:gm_rededicate_levels }",
                 "set_variable = { name = gm_start_grandeur value = var:gm_rededicate_start }"]
        positions = [body.find(s) for s in order]
        self.assertNotIn(-1, positions, [s for s, p in zip(order, positions) if p == -1])
        self.assertEqual(positions, sorted(positions))
        for s in ("remove_building", "create_building", "te_construction_market_build_specified_level"):
            self.assertNotIn(s, body)


class NoRebuildTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.3: a finished monument's size is its records;
    nothing rebuilds its building. The split pieces and the one-off repair
    (Task 7) are the last to use gm_state_tr_add_levels."""

    GM_FILES = ("common/scripted_effects/gm_*.txt", "common/scripted_triggers/*monument*.txt",
                "common/scripted_triggers/gm_*.txt", "common/script_values/gm_*.txt", "events/monument*.txt")

    # Nothing is excused any more (the split pieces and the repair went with
    # the merge rewrite, sites plan A Task 7).
    UNTIL_TASK_7 = set()

    def texts(self):
        for pattern in self.GM_FILES:
            for path in sorted(ROOT.glob(pattern)):
                yield path.relative_to(ROOT).as_posix(), strip_comments(read(path.relative_to(ROOT).as_posix()))

    def test_no_monument_rebuild(self):
        gone = ("gm_state_tr_shrink_by", "gm_rebuild_level", "gm_rebuild_asked", "gm_monument_rebuild_self_check",
                "gm_disp_rebuild_asked", "gm_state_record_frozen_levels", "gm_state_has_new_levels",
                "gm_state_found_beside", "gm_state_has_copied_dedication", "gm_state_reset_copied_dedication",
                "gm_state_return_to_undedicated", "gm_state_lacks_dedication_tech")
        for rel, text in self.texts():
            for block_name, body in top_level_blocks(text):
                if block_name in self.UNTIL_TASK_7:
                    continue
                for name in gone:
                    self.assertNotRegex(body, rf"\b{name}\b", f"{name} in {rel} {block_name}")
                self.assertNotRegex(body, r"SPEC_TYPE = building_grand_monument\b(?!_)", f"{rel} {block_name}")
                self.assertNotIn("max = 200", body, f"{rel} {block_name}")
        self.assertNotIn("set_variable = gm_tr_return_queued",
                         squash(block(read("common/scripted_effects/gm_trophy_effects.txt"), "gm_tr_return_home")))

    def test_nothing_adds_levels_to_a_building(self):
        for rel, text in self.texts():
            self.assertNotRegex(text, r"\bgm_state_tr_add_levels\b", rel)

    def test_the_finished_building_is_made_and_unmade_in_few_places(self):
        made, unmade = set(), set()
        for rel, text in self.texts():
            for name, body in top_level_blocks(text):
                if re.search(r"create_building = \{\s*building = building_grand_monument\s", body):
                    made.add(name)
                if re.search(r"remove_building = building_grand_monument\s", body):
                    unmade.add(name)
        landmark = squash(block(read(LANDMARK_EFFECTS), "gm_seed_landmark"))
        self.assertIn("create_building = { building = building_grand_monument level = 1 ", landmark)
        self.assertLessEqual(made, {"gm_state_finish_site", "gm_state_put_back_building",
                                    "gm_state_tr_rebuild_from_moving", "gm_seed_landmark", "gm_state_migrate",
                                    "gm_state_raise_orphan", "gm_state_reset_building_level"})
        self.assertLessEqual(unmade, {"gm_state_tear_down", "gm_state_tr_remove_whole", "gm_state_migrate",
                                      "gm_state_reset_building_level", "monument_events.29"})

    def test_a_monument_beside_rises_into_the_standing_building(self):
        for path, name in ((EFFECTS, "gm_state_tear_down"),
                           ("common/scripted_effects/gm_trophy_effects.txt", "gm_state_tr_remove_whole")):
            body = squash(strip_comments(block(read(path), name)))
            self.assertIn("if = { limit = { gm_state_has_secondary = yes } gm_state_promote_secondary = yes } "
                          "else = { set_variable = { name = gm_rebuilding days = 1 } "
                          "remove_building = building_grand_monument }", body, name)
        rise = squash(strip_comments(block(read("common/scripted_effects/gm_trophy_effects.txt"),
                                           "gm_state_tr_rebuild_from_moving")))
        self.assertIn("if = { limit = { NOT = { has_building = building_grand_monument } } "
                      "set_variable = { name = gm_rebuilding days = 1 } "
                      "create_building = { building = building_grand_monument level = 1 } }", rise)
        self.assertLess(rise.find("gm_clear_state = { KEEP_LANDMARK = no }"),
                        rise.find("gm_state_tr_take_records_from_moving = yes"))

    def test_a_piece_carried_off_or_home_changes_the_records(self):
        tr = read("common/scripted_effects/gm_trophy_effects.txt")
        piece = squash(strip_comments(block(tr, "gm_state_tr_remove_piece")))
        self.assertIn("set_variable = { name = gm_levels value = var:gm_tr_take_left }", piece)
        for s in ("remove_building", "gm_rebuilding", "gm_state_mark_restore_pm"):
            self.assertNotIn(s, piece)
        receive = squash(strip_comments(block(tr, "gm_state_tr_receive")))
        self.assertIn("change_variable = { name = gm_levels add = scope:gm_tr_moving.var:gm_tr_levels }", receive)
        self.assertNotIn("gm_state_tr_add_levels", receive)
        # A monument just raised here today (gm_rebuilding) stands: a second
        # trophy home the same day stands beside it.
        self.assertIn("var:gm_tr_origin ?= { OR = { has_building = building_grand_monument "
                      "has_variable = gm_rebuilding } }",
                      squash(block(read(MON_TRIGGERS), "gm_tr_stands_apart")))


class LostBuildingTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.7: a finished monument's building that goes
    while its records stand is put back at level 1 on its dedication; Pull
    Down and a taking clear the records or raise another first."""

    def test_the_dedication_is_recorded(self):
        monthly = squash(strip_comments(block(read(EFFECTS), "gm_state_monthly")))
        self.assertIn("gm_state_record_dedication = yes", monthly)
        rec = squash(block(read(EFFECTS), "gm_state_record_dedication_one"))
        self.assertIn("limit = { gm_state_has_pm = { PM = pm_monument_$KEY$ } NOT = { has_variable = gm_restore_pm } }",
                      rec)
        self.assertIn("set_variable = { name = gm_dedication value = flag:$KEY$ }", rec)
        self.assertIn("gm_remove_state_var = { VAR = gm_dedication }", squash(block(read(EFFECTS), "gm_clear_state")))

    def test_lost_is_put_back(self):
        lost = squash(block(read(TRIGGERS), "gm_state_lost_building"))
        self.assertEqual(lost, "NOT = { has_building = building_grand_monument } has_variable = gm_migrated "
                               "has_variable = gm_seen "
                               "has_variable = gm_levels has_variable = gm_dedication "
                               "NOT = { has_variable = gm_carried_off } NOT = { has_variable = gm_rebuilding }")
        monthly = squash(strip_comments(block(read(EFFECTS), "gm_state_monthly")))
        branch = monthly[monthly.find("else = {"):]
        # Exclusive: its records must stand for the hidden event.
        self.assertIn("if = { limit = { gm_state_lost_building = yes } trigger_event = { id = monument_events.29 } } "
                      "else = {", branch)
        ev29 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.29\s*=\s*\{")))
        self.assertIn("limit = { gm_state_lost_building = yes } gm_state_put_back_building = yes", ev29)
        put = squash(block(read(EFFECTS), "gm_state_put_back_building"))
        self.assertEqual(put, "set_variable = gm_migrated set_variable = { name = gm_rebuilding days = 1 } "
                              "create_building = { building = building_grand_monument level = 1 } "
                              "set_variable = { name = gm_restore_pm value = var:gm_dedication }")


class MigrationTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.5: an older save's monument is recorded and
    its building reset once (a dedicated one), or becomes a construction site
    at its level (an undedicated one, a ceremony open), from the hidden
    monument_events.32; never inside the walked refresh."""

    def body(self, path, name):
        return squash(strip_comments(block(read(path), name)))

    def ev32(self):
        return squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.32\s*=\s*\{")))

    def test_the_refresh_only_asks(self):
        self.assertEqual(self.body(TRIGGERS, "gm_state_needs_migration"),
                         "has_building = building_grand_monument has_variable = gm_premigration "
                         "NOT = { has_variable = gm_migrated } "
                         "NOT = { has_variable = gm_rebuilding } NOT = { has_variable = gm_restore_pm } "
                         "NOT = { has_variable = gm_ceremony_pending }")
        refresh = self.body(EFFECTS, "gm_country_refresh")
        self.assertIn("if = { limit = { gm_state_needs_migration = yes } trigger_event = { id = monument_events.32 } }",
                      refresh)
        self.assertNotIn("gm_state_migrate = yes", refresh)

    def test_waits_for_construction(self):
        ev = self.ev32()
        self.assertIn("type = state_event hidden = yes", ev)
        self.assertIn("trigger = { gm_system_enabled = yes gm_state_needs_migration = yes }", ev)
        self.assertIn("if = { limit = { b:building_grand_monument ?= { is_under_construction = no } } "
                      "gm_state_migrate = yes }", ev)

    def test_a_dedicated_monument_is_recorded_then_reset(self):
        body = self.body(EFFECTS, "gm_state_migrate")
        order = ["set_variable = gm_migrated",
                 "limit = { gm_state_is_dedicated = yes has_variable = gm_seen }",
                 "set_variable = { name = gm_mig_before value = gm_state_grandeur }",
                 "if = { limit = { NOT = { has_variable = gm_levels } } "
                 "set_variable = { name = gm_levels value = gm_state_built_levels } }",
                 "gm_state_record_dedication = yes",
                 "limit = { gm_state_level > 1 }", "gm_state_mark_restore_pm = yes",
                 "set_variable = { name = gm_rebuilding days = 1 }",
                 "remove_building = building_grand_monument",
                 "create_building = { building = building_grand_monument level = 1 }"]
        positions = [body.find(s) for s in order]
        self.assertNotIn(-1, positions, [s for s, p in zip(order, positions) if p == -1])
        self.assertEqual(positions, sorted(positions))

    def test_an_undedicated_one_becomes_a_site(self):
        body = self.body(EFFECTS, "gm_state_migrate")
        rest = body[body.find("else = {"):]
        for s in ("set_variable = { name = gm_migrate_levels value = gm_state_built_levels }",
                  "gm_remove_state_var = { VAR = gm_ceremony_level }",
                  "if = { limit = { gm_state_has_secondary = yes } gm_state_promote_secondary = yes }",
                  "SPEC_TYPE = building_grand_monument_site SPEC_LEVEL = var:gm_migrate_levels",
                  "set_variable = { name = gm_site_counted value = var:gm_migrate_levels }",
                  "set_variable = { name = gm_site_grandeur value = var:gm_migrate_levels }"):
            self.assertIn(s, rest)

    def test_new_monuments_are_never_migrated(self):
        for path, name in ((EFFECTS, "gm_state_finish_site"), (EFFECTS, "gm_state_put_back_building"),
                           ("common/scripted_effects/gm_trophy_effects.txt", "gm_state_tr_rebuild_from_moving"),
                           (LANDMARK_EFFECTS, "gm_seed_landmark")):
            self.assertIn("set_variable = gm_migrated", self.body(path, name), name)
        self.assertIn("has_variable = gm_migrated", self.body(TRIGGERS, "gm_state_lost_building"))
        gate = self.body(MON_TRIGGERS, "gm_state_can_build_site")
        self.assertIn("text = gm_expand_migrating_tt OR = { NOT = { has_building = building_grand_monument } "
                      "has_variable = gm_migrated }", gate)
        self.assertIn("gm_expand_migrating_tt", loc())

    def test_totals_survive(self):
        """Review Focus 1: a dedicated monument's grandeur reads the same a
        month after its migration (TE_SELF_CHECK monument_migrated)."""
        check = self.body(EFFECTS, "gm_monument_migration_self_check")
        for s in ("has_variable = gm_mig_before", "TE_SELF_CHECK OK monument_migrated",
                  "TE_SELF_CHECK BROKEN monument_migrated", "remove_variable = gm_mig_before",
                  "has_global_variable = gm_migration_self_checked"):
            self.assertIn(s, check)
        self.assertIn("gm_monument_migration_self_check = yes", self.body(EFFECTS, "gm_state_monthly"))

    def test_the_one_off_repair_goes(self):
        for pattern in ("common/scripted_effects/gm_*.txt", "common/scripted_triggers/*.txt",
                        "common/script_values/gm_*.txt"):
            for path in sorted(ROOT.glob(pattern)):
                text = strip_comments(read(path.relative_to(ROOT).as_posix()))
                self.assertNotRegex(text, r"gm_short_repair|gm_state_short_|gm_short_log_", path.name)


class MergeRecordTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.7: a merge drops the absorbed state's
    variables, where its monument's records live, so a monthly shadow keeps
    them; an orphaned shadow settles into the part of its region its last owner
    holds, from the records alone, and the finished building there is put back
    to level 1. A revolt keeps the monument whole: a finished building nothing
    records, with no orphan in its region, is removed."""

    SHADOW_EFFECTS = ("gm_shadow_monthly", "gm_state_write_shadow", "gm_state_drop_shadow", "gm_sh_drop",
                      "gm_sh_mirror", "gm_state_adopt_orphans", "gm_sh_settle_region", "gm_sh_settle_one",
                      "gm_sh_adopt_beside", "gm_state_raise_orphan", "gm_sh_lost", "gm_monument_merge_self_check")

    def body(self, path, name):
        return squash(strip_comments(block(read(path), name)))

    def test_the_shadow_carries_records_only(self):
        write = self.body(MON_EFFECTS, "gm_state_write_shadow")
        for s in ("set_variable = { name = gm_sh_levels value = gm_state_primary_levels }",
                  "set_variable = { name = gm_tr_levels value = scope:gm_tr_state.var:gm_sh_levels }",
                  "set_variable = { name = gm_sh_owner value = scope:gm_tr_state.owner }"):
            self.assertIn(s, write)
        for frm, to in CONTAINER_RECORDS:
            self.assertIn(f"gm_sh_mirror = {{ FROM = {frm} TO = {to} }}", write, frm)
        for s in ("gm_sh_short", "gm_tr_piece_of", "gm_tr_split_piece", "unexplained", "levels_short"):
            self.assertNotIn(s, write)
        for name in self.SHADOW_EFFECTS:
            self.assertIsNotNone(block(read(MON_EFFECTS), name), name)

    def test_the_shadow_is_written_only_by_the_pass_and_a_raise(self):
        writers = set()
        for path in sorted(ROOT.glob("common/**/*.txt")) + sorted(ROOT.glob("events/*.txt")):
            for name, body in top_level_blocks(read(path.relative_to(ROOT).as_posix())):
                if re.search(r"\bgm_state_write_shadow = yes", body):
                    writers.add(name)
        self.assertEqual(writers, {"gm_shadow_monthly", "gm_state_raise_orphan"})

    def test_a_merge_is_pending_from_the_records(self):
        self.assertEqual(self.body(MON_TRIGGERS, "gm_state_merge_pending"),
                         "has_building = building_grand_monument OR = { gm_state_unrecorded = yes "
                         "AND = { has_variable = gm_migrated gm_state_level > 1 } } gm_state_orphan_in_region = yes")
        orphan = self.body(MON_TRIGGERS, "gm_state_orphan_in_region")
        self.assertIn("gm_sh_orphan_of = { REGION = scope:gm_tmp_sh_region }", orphan)
        self.assertIn("variable = gm_shadows", orphan)
        self.assertIn("variable = gm_monuments", orphan)

    def test_an_orphan_settles_where_its_owner_holds_its_region(self):
        one = self.body(MON_EFFECTS, "gm_sh_settle_one")
        for s in ("var:gm_sh_owner ?= { save_scope_as = gm_sh_was_owner }",
                  "limit = { exists = owner owner = scope:gm_sh_was_owner }",
                  "limit = { scope:gm_sh_target = { gm_state_unrecorded = yes } } "
                  "scope:gm_sh_target = { gm_state_raise_orphan = yes }",
                  "limit = { scope:gm_sh_target = { has_building = building_grand_monument has_variable = gm_seen } } "
                  "gm_sh_adopt_beside = yes",
                  "limit = { scope:gm_sh_target = { NOT = { has_building = building_grand_monument } } } "
                  "scope:gm_sh_target = { gm_state_raise_orphan = yes }",
                  "gm_sh_lost = yes"):
            self.assertIn(s, one)
        raise_ = self.body(MON_EFFECTS, "gm_state_raise_orphan")
        self.assertIn("if = { limit = { NOT = { has_building = building_grand_monument } } "
                      "set_variable = { name = gm_rebuilding days = 1 } "
                      "create_building = { building = building_grand_monument level = 1 } }", raise_)
        beside = self.body(MON_EFFECTS, "gm_sh_adopt_beside")
        self.assertNotIn("gm_sh_room", beside)

    def test_the_survivor_stands_at_level_1(self):
        region = self.body(MON_EFFECTS, "gm_sh_settle_region")
        self.assertIn("every_scope_state = { limit = { has_building = building_grand_monument "
                      "has_variable = gm_migrated gm_state_level > 1 } "
                      "gm_state_reset_building_level = yes }", region)
        reset = self.body(MON_EFFECTS, "gm_state_reset_building_level")
        self.assertEqual(reset, "set_variable = { name = gm_merge_check value = gm_state_level } "
                                "if = { limit = { has_variable = gm_dedication } "
                                "set_variable = { name = gm_restore_pm value = var:gm_dedication } } "
                                "else_if = { limit = { NOT = { has_variable = gm_restore_pm } } gm_state_mark_restore_pm = yes } "
                                "set_variable = { name = gm_rebuilding days = 1 } "
                                "remove_building = building_grand_monument "
                                "create_building = { building = building_grand_monument level = 1 }")

    def test_a_revolt_keeps_the_monument_whole(self):
        """Owner, 2026-10-18: the monument stays with the part that keeps its
        records. Adopt first (an orphan in the region), then remove a stray."""
        stray = self.body(TRIGGERS, "gm_state_stray_building")
        self.assertEqual(stray, "has_global_variable = gm_sites_marked "
                                "has_building = building_grand_monument NOT = { has_variable = gm_migrated } "
                                "NOT = { has_variable = gm_premigration } NOT = { has_variable = gm_rebuilding } "
                                "gm_state_orphan_in_region = no")
        refresh = self.body(EFFECTS, "gm_country_refresh")
        self.assertIn("if = { limit = { gm_state_stray_building = yes } trigger_event = { id = monument_events.29 } }",
                      refresh)
        ev29 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.29\s*=\s*\{")))
        self.assertIn("limit = { gm_state_stray_building = yes } set_variable = { name = gm_rebuilding days = 1 } "
                      "remove_building = building_grand_monument", ev29)
        # The older save's buildings, marked once before any is migrated.
        self.assertIn("has_variable = gm_premigration", self.body(TRIGGERS, "gm_state_needs_migration"))
        mark = self.body(MON_EFFECTS, "gm_monument_monthly")
        self.assertIn("NOT = { has_global_variable = gm_sites_marked }", mark)
        self.assertIn("set_variable = gm_premigration", mark)
        self.assertIn("set_variable = gm_migrated", self.body("common/scripted_effects/gm_trophy_effects.txt",
                                                              "gm_state_tr_take_records_from_moving"))

    def test_the_split_pieces_are_gone(self):
        gone = r"gm_piece_of|gm_split_piece|gm_split_levels|gm_split_age|gm_split_short|gm_state_split_|gm_sh_rejoin|" \
               r"gm_state_piece_|gm_sh_piece_|gm_state_take_split_identity|gm_state_forget_split|gm_split_rejected|" \
               r"gm_state_whole_merged_into_piece|gm_state_unexplained_levels|gm_state_levels_short|" \
               r"gm_state_shadow_levels|gm_state_was_split|gm_state_levels_readable|gm_sh_short|gm_disp_is_piece|" \
               r"gm_disp_has_piece|gm_piece_where|gm_split_where|monument_split_|gm_state_tr_add_levels|" \
               r"gm_state_takes_orphan_beside|gm_sh_try_raise"
        for pattern in ("common/**/*.txt", "events/*.txt", "gui/**/*.gui", "localization/english/*.yml"):
            for path in sorted(ROOT.glob(pattern)):
                text = strip_comments(read(path.relative_to(ROOT).as_posix())) if path.suffix != ".yml" \
                    else read(path.relative_to(ROOT).as_posix())
                self.assertNotRegex(text, gone, path.relative_to(ROOT).as_posix())

    def test_the_self_check(self):
        check = self.body(MON_EFFECTS, "gm_monument_merge_self_check")
        for s in ("TE_SELF_CHECK OK monument_merge_kept", "TE_SELF_CHECK BROKEN monument_merge_kept",
                  "NOT = { has_global_variable = gm_merge_self_checked }"):
            self.assertIn(s, check)
        self.assertNotIn("found", check)


class UpkeepTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.4: a level-1 finished building pays the upkeep
    of the levels its monuments record (0.1 construction a level, as
    pm_maintenance), x1.5 Open, nothing Mothballed (owner, 2026-10-18)."""

    def test_one_modifier_sized_by_the_records(self):
        self.assertEqual(squash(block(read(MODIFIERS), "gm_upkeep")).split("icon = ")[1].split(" ", 1)[1],
                         "goods_input_construction_mult = 1")
        self.assertEqual(squash(block(read(VALUES), "gm_state_upkeep_mult")),
                         "value = gm_state_primary_levels add = gm_state_secondary_levels "
                         "multiply = gm_policy_factor_upkeep subtract = 1 "
                         "if = { limit = { NOT = { has_variable = gm_migrated } } value = 0 }")
        self.assertEqual(squash(block(read(VALUES), "gm_policy_factor_upkeep")),
                         "value = 1 if = { limit = { owner = { gm_policy_is = { P = open STANDARD = no } } } value = 1.5 } "
                         "if = { limit = { owner = { gm_policy_is = { P = mothballed STANDARD = no } } } value = 0 }")
        self.assertIn("gm_upkeep", loc())

    def test_the_state_pulse_is_its_one_refresh(self):
        monthly = squash(strip_comments(block(read(EFFECTS), "gm_state_monthly")))
        self.assertIn("set_variable = { name = gm_upkeep_mult value = gm_state_upkeep_mult } "
                      "b:building_grand_monument ?= { add_modifier = { name = gm_upkeep multiplier = root.var:gm_upkeep_mult } }",
                      monthly)
        for old in ("add_modifier = { name = gm_policy_upkeep_open }", "add_modifier = { name = gm_policy_upkeep_mothballed }"):
            self.assertNotIn(old, monthly)
        callers = [name for path in sorted(ROOT.glob("common/**/*.txt"))
                   for name, body in top_level_blocks(read(path.relative_to(ROOT).as_posix()))
                   if "name = gm_upkeep " in squash(body)]
        self.assertEqual(callers, ["gm_state_monthly"])
        remove = squash(block(read(EFFECTS), "gm_remove_local_modifiers"))
        for name in ("gm_upkeep", "gm_policy_upkeep_open", "gm_policy_upkeep_mothballed"):
            self.assertIn(f"remove_modifier = {name}", remove)


class SitePanelTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.1: a construction site has its own card in the
    state view and its own row under Awaiting Dedication; Our Monuments lists
    the finished ones; the overview's first cell counts sites."""

    STATE_WIDGETS = "gui/te_state_panel_widgets.gui"

    def type_body(self, path, name):
        raw = strip_comments(read(path))
        m = re.search(r"type " + re.escape(name) + r" = \w+ \{", raw)
        self.assertIsNotNone(m, name)
        return squash(_match_brace(raw, m.end()))

    def test_the_values(self):
        values = read(VALUES)
        self.assertEqual(squash(block(values, "gm_state_disp_site")),
                         "value = 0 if = { limit = { gm_state_has_site = yes } value = 1 }")
        self.assertEqual(squash(block(values, "gm_state_disp_site_grandeur")),
                         "value = 0 if = { limit = { has_variable = gm_site_grandeur } value = var:gm_site_grandeur }")
        self.assertEqual(squash(block(values, "gm_state_disp_site_building")),
                         "value = 0 if = { limit = { b:building_grand_monument_site ?= { is_under_construction = yes } } "
                         "value = 1 }")
        self.assertEqual(squash(block(values, "gm_state_disp_listed")),
                         "value = 0 if = { limit = { has_building = building_grand_monument } value = 1 }")
        self.assertEqual(squash(block(values, "gm_disp_count_listed")), "value = gm_sum_monuments")
        self.assertIn("gm_state_has_site = yes", squash(block(values, "gm_disp_count_undedicated")))

    def test_the_site_row(self):
        row = self.type_body(WIDGET, "gm_site_row")
        for key in ("gm_site_row_title", "gm_site_row_detail", "gm_site_row_detail_tt", "gm_site_row_building",
                    "gm_site_row_ready"):
            self.assertIn(f'"{key}"', row)
            self.assertIn(key, loc(), key)
        sec = squash(strip_comments(read(WIDGET).split("type te_gm_sec_awaiting = flowcontainer {", 1)[1]
                                    .split("type te_gm_sec_monuments", 1)[0]))
        self.assertIn("gm_site_row = {} gm_dedicate_button = {}", sec)
        mon = squash(strip_comments(read(WIDGET).split("type te_gm_sec_monuments = flowcontainer {", 1)[1]))
        self.assertIn("visible = \"[EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_state_disp_listed'), "
                      "'(CFixedPoint)1' )]\"", mon)

    def test_the_site_card(self):
        card = self.type_body(self.STATE_WIDGETS, "te_state_gm_site_card")
        self.assertIn("visible = \"[EqualTo_CFixedPoint(State.MakeScope.ScriptValue('gm_state_disp_site'), "
                      "'(CFixedPoint)1')]\"", card)
        self.assertIn("gm_dedicate_button = {}", card)
        for s in ("onclick", "ScriptedGui.Execute", "JournalEntry"):
            self.assertNotIn(s, card)
        for key in ("gm_site_card_title", "gm_site_card_levels", "gm_site_card_grandeur"):
            self.assertIn(key, loc(), key)
        self.assertNotIn("gm_dedicate_button", self.type_body(self.STATE_WIDGETS, "te_state_gm_card"))
        panel = squash(strip_comments(read("gui/states_panel.gui")))
        self.assertIn("te_state_gm_card = {}", panel)
        self.assertLess(panel.find("te_state_gm_card = {}"), panel.find("te_state_gm_site_card = {}"))

    def test_the_overview_counts_sites(self):
        self.assertTrue(loc()["gm_je_ov_undedicated"].startswith("Being Built "))
        self.assertIn("gm_je_ov_building_tt", read(WIDGET))
        self.assertIn("gm_je_ov_building_tt", loc())

    def test_a_site_opens_the_entry(self):
        site = "any_scope_state = { has_building = building_grand_monument_site }"
        self.assertIn(site, squash(block(read(TRIGGERS), "gm_entry_unlocked")))
        self.assertIn(site, squash(block(read(JE), "is_shown_when_inactive")))
        refresh = squash(block(read(EFFECTS), "gm_country_refresh"))
        self.assertIn("NOT = { has_journal_entry = je_grand_monuments } OR = { any_scope_state = { "
                      "has_building = building_grand_monument } " + site, refresh)


class WalkedRefreshTests(unittest.TestCase):
    """Sites plan A, Review Focus 5: gm_country_refresh runs inside tooltips,
    which walk it writing nothing, so nothing it calls makes, removes or
    swaps a building or a container: that work is the hidden events'
    (monument_events.29, .31, .32). The one method switch it reaches is the
    restore of a dedication script recorded (gm_state_restore_dedication),
    which reads back nothing in the same effect."""

    ALLOWED = {"gm_state_restore_dedication_one"}

    def test_refresh_writes_nothing_structural(self):
        effects = {}
        for path in sorted(ROOT.glob("common/scripted_effects/*.txt")):
            for name, body in top_level_blocks(read(path.relative_to(ROOT).as_posix())):
                effects[name] = body
        bad = re.compile(r"\b(create_building|remove_building|create_container|destroy_container|"
                         r"activate_production_method|gm_state_demote_primary)\b")
        seen, stack, hits = set(), ["gm_country_refresh"], {}
        while stack:
            name = stack.pop()
            if name in seen:
                continue
            seen.add(name)
            body = effects[name]
            if name not in self.ALLOWED and bad.search(body):
                hits[name] = sorted(set(bad.findall(body)))
            for call in re.findall(r"\b([a-z_]\w*)\s*=\s*(?:yes|\{)", body):
                if call in effects and call not in seen:
                    stack.append(call)
        self.assertGreater(len(seen), 50)
        self.assertEqual(hits, {})


class CreatedOnDedicationTests(unittest.TestCase):
    """Sites plan A Task 10: whether create_building's activate_production_methods
    puts the dedication on the finished building it makes, or the engine's copy
    wins and gm_restore_pm has to switch it, is unread. Once a game, the first
    restore after a site's dedication says which."""

    def test_the_self_check(self):
        finish = squash(strip_comments(block(read(EFFECTS), "gm_state_finish_site")))
        self.assertIn("set_variable = gm_created_check", finish)
        one = squash(strip_comments(block(read("common/scripted_effects/gm_commission_effects.txt"),
                                          "gm_state_restore_dedication_one")))
        for s in ("TE_SELF_CHECK OK monument_created_on_dedication",
                  "TE_SELF_CHECK BROKEN monument_created_on_dedication",
                  "has_variable = gm_created_check", "remove_variable = gm_created_check",
                  "NOT = { has_global_variable = gm_created_self_checked }"):
            self.assertIn(s, one)


class RateTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.2 (Plan B): a level's starting grandeur is
    world GDP in 1836 over world GDP when it is counted, times the grandeur a
    level adds in 1836 (owner, 2026-10-19: five), to the nearest thousandth and
    at least 0.001. The 1836 figure is a constant (spec §5): 334,465,286 summed
    from a Timeline Extended save of 1836.1.20, every country's latest GDP."""

    def body(self, path, name):
        return squash(strip_comments(block(read(path), name)))

    def test_the_rate(self):
        self.assertEqual(self.body(VALUES, "gm_world_gdp_1836"), "value = 334000000")
        self.assertEqual(self.body(VALUES, "gm_world_rate_now"),
                         "value = 1 if = { limit = { global_gdp_script_value > 0 } value = gm_world_gdp_1836 "
                         "divide = global_gdp_script_value min = 0.00001 }")
        self.assertEqual(self.body(VALUES, "gm_level_grandeur_1836"), "value = 5")
        # Scaled on reading, so a save's stored ratio takes it before January.
        self.assertEqual(self.body(VALUES, "gm_world_rate_value"),
                         "value = 1 if = { limit = { has_global_variable = gm_world_rate } "
                         "value = global_var:gm_world_rate } multiply = gm_level_grandeur_1836 "
                         "multiply = 1000 round = yes divide = 1000 min = 0.001")

    def test_written_before_counting(self):
        ensure = self.body(EFFECTS, "gm_world_rate_ensure")
        self.assertEqual(ensure, "if = { limit = { NOT = { has_global_variable = gm_world_rate } } "
                                 "set_global_variable = { name = gm_world_rate value = gm_world_rate_now } }")
        self.assertTrue(self.body(EFFECTS, "gm_state_count_site_levels").startswith("gm_world_rate_ensure = yes"))
        monthly = self.body(MON_EFFECTS, "gm_monument_monthly")
        self.assertIn("gm_world_rate_ensure = yes if = { limit = { month = 0 } "
                      "set_global_variable = { name = gm_world_rate value = gm_world_rate_now } }", monthly)

    def test_each_level_at_its_month(self):
        """Review Focus 1 (Plan B): each level counts at the rate of the month
        it is counted, not the dedication's."""
        count = self.body(EFFECTS, "gm_state_count_site_levels")
        self.assertIn("set_variable = { name = gm_site_add value = { value = var:gm_site_new "
                      "multiply = gm_world_rate_value } } "
                      "change_variable = { name = gm_site_grandeur add = var:gm_site_add }", count)
        self.assertIn("remove_variable = gm_site_add", count)
        self.assertNotIn("gm_world_rate", self.body(EFFECTS, "gm_state_finish_site").replace(
            "gm_state_count_site_levels", ""))

    def test_the_base_self_check(self):
        check = self.body(MON_EFFECTS, "gm_world_base_self_check")
        for s in ("NOT = { has_global_variable = gm_world_base_checked }", "game_date < 1836.3.1",
                  "TE_SELF_CHECK OK gm_world_base", "TE_SELF_CHECK BROKEN gm_world_base",
                  "global_gdp_script_value >= gm_world_gdp_1836_low",
                  "global_gdp_script_value <= gm_world_gdp_1836_high"):
            self.assertIn(s, check)
        self.assertIn("gm_world_base_self_check = yes", self.body(MON_EFFECTS, "gm_monument_monthly"))


class OpportunityGrandeurTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.2 (Plan B): an opportunity asks for starting
    grandeur, never age; Raise It queues what that takes at today's rate, at
    most 100 levels a press (Review Focus 3)."""

    def body(self, name):
        return squash(strip_comments(block(read(COM_VALUES), name)))

    def test_progress_counts_starting_grandeur(self):
        fit = self.body("gm_com_fit_grandeur")
        self.assertIn("add = gm_state_primary_start", fit)
        self.assertIn("add = gm_mon_start", fit)
        self.assertNotIn("_levels", fit)
        self.assertNotIn("age", fit)

    def test_the_levels_it_takes(self):
        self.assertEqual(self.body("gm_com_grandeur_to_go"),
                         "value = 0 if = { limit = { has_variable = gm_com_open has_variable = gm_com_target } "
                         "value = var:gm_com_target subtract = gm_com_progress min = 0 }")
        self.assertEqual(self.body("gm_com_levels_to_go"),
                         "value = gm_com_grandeur_to_go divide = gm_world_rate_value ceiling = yes max = 100")
        self.assertEqual(self.body("gm_com_target_levels"),
                         "value = 0 if = { limit = { has_variable = gm_com_target } value = var:gm_com_target "
                         "divide = gm_world_rate_value ceiling = yes max = 100 }")
        self.assertEqual(self.body("gm_disp_com_accept_cost"),
                         "value = gm_com_target_levels multiply = construction_cost_grand_monument")


class MeaningCountsGrandeurTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.6 (Plan B): what a monument means counts its
    grandeur: the vanity backlash of levels finished in hard times, the
    infamy of carrying one off, an anniversary's gift."""

    TR_V = "common/script_values/gm_trophy_values.txt"
    TR_E = "common/scripted_effects/gm_trophy_effects.txt"

    def test_vanity_is_the_grandeur_counted(self):
        count = squash(strip_comments(block(read(EFFECTS), "gm_state_count_site_levels")))
        self.assertIn("gm_state_vanity_backlash_for = { AMOUNT = prev.var:gm_site_add }", count)
        self.assertLess(count.find("name = gm_site_add"), count.find("gm_state_vanity_backlash_for"))
        self.assertIn("for each point of grandeur", loc()["gm_je_how_hard_times"])

    def test_infamy_is_the_grandeur_taken(self):
        self.assertEqual(squash(block(read(self.TR_V), "gm_tr_infamy")),
                         "value = var:gm_tr_tmp_grandeur divide = 5 add = 2 max = 8 "
                         "if = { limit = { has_global_variable = un_agency_unesco } multiply = 2 }")
        self.assertEqual(squash(block(read(self.TR_V), "gm_state_tr_infamy")),
                         "value = gm_state_tr_start add = gm_state_tr_age divide = 5 add = 2 max = 8 "
                         "if = { limit = { has_global_variable = un_agency_unesco } multiply = 2 }")
        self.assertIsNone(block(read(self.TR_V), "gm_tr_infamy_of_trophy"))
        effects = squash(strip_comments(read(self.TR_E)))
        self.assertEqual(effects.count("change_infamy = gm_tr_infamy"), 2)
        self.assertEqual(effects.count("set_variable = { name = gm_tr_tmp_g value = gm_mon_grandeur }"), 2)
        self.assertNotIn("gm_tr_tmp_levels", effects)

    def test_an_anniversary_adds_a_tenth_of_the_starting_grandeur(self):
        self.assertEqual(squash(block(read(VALUES), "gm_evt_grandeur")),
                         "value = gm_state_primary_start multiply = 0.1 min = 1")
        self.assertEqual(squash(block(read(MON_VALUES), "gm_mon_evt_grandeur")),
                         "value = gm_mon_start multiply = 0.1 min = 1")


class RateDisplayTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.2 (Plan B): the player sees what a level is
    worth before building: on the site's card and row, in National Effects
    and in the build menu; and grandeur, often fractional now, prints with a
    decimal (Review Focus 5)."""

    RATE = "ScriptValue('gm_world_rate_value')|3"

    def test_the_four_places(self):
        L = loc()
        card = squash(strip_comments(read("gui/te_state_panel_widgets.gui")))
        self.assertIn('text = "gm_site_card_rate_lbl"', card)
        self.assertIn('text = "gm_site_card_rate"', card)
        self.assertIn(self.RATE, L["gm_site_card_rate"])
        widget = squash(strip_comments(read(WIDGET)))
        self.assertIn('text = "gm_site_row_rate"', widget)
        self.assertIn(self.RATE, L["gm_site_row_rate"])
        self.assertIn('tooltip = "gm_je_world_rate_tt" text = "gm_je_world_rate"', widget)
        self.assertIn(self.RATE, L["gm_je_world_rate"])
        self.assertIn("ScriptValue('gm_world_wealth_factor')|1", L["gm_je_world_rate_tt"])
        # How many times richer: the stored ratio, not the scaled rate.
        self.assertEqual(squash(block(read(VALUES), "gm_world_wealth_factor")),
                         "value = 1 if = { limit = { has_global_variable = gm_world_rate } "
                         "divide = global_var:gm_world_rate }")
        possible = squash(block(read(SITE_BUILDING), "possible"))
        self.assertIn("custom_tooltip = { text = gm_site_rate_tt always = yes }", possible)
        self.assertIn("[SCOPE.ScriptValue('gm_world_rate_value')|3]", L["gm_site_rate_tt"])

    def test_grandeur_prints_a_decimal(self):
        L = loc()
        for key, value in (("gm_row_detail", "gm_state_primary_grandeur"), ("gm_state_val_grandeur", "gm_state_grandeur"),
                           ("gm_state_grandeur_tt_one", "gm_state_grandeur"),
                           ("gm_state_grandeur_tt_many", "gm_state_grandeur")):
            self.assertIn(f"ScriptValue('{value}')|1", L[key], key)
        self.assertIn("ScriptValue('gm_state_primary_start')|1", L["gm_state_grandeur_tt_one"])


class RecordWriterTests(unittest.TestCase):
    """Sites spec 2026-10-18 §3.3, §5: every effect that changes a monument's
    size keeps its starting grandeur in step with its levels."""

    TR = "common/scripted_effects/gm_trophy_effects.txt"

    def body(self, path, name):
        return squash(strip_comments(block(read(path), name)))

    def test_dedication_writes_it_once(self):
        body = self.body(EFFECTS, "gm_state_dedicate")
        start = ("if = { limit = { NOT = { has_variable = gm_start_grandeur } } "
                 "set_variable = { name = gm_start_grandeur value = gm_state_primary_levels } }")
        self.assertIn(start, body)
        self.assertLess(body.find("set_variable = { name = gm_levels"), body.find(start))

    def test_a_piece_of_the_primary_carries_its_share(self):
        take = self.body(self.TR, "gm_state_tr_take")
        self.assertIn("set_variable = { name = gm_tr_take_start value = gm_state_tr_start }", take)
        self.assertIn("gm_remove_state_var = { VAR = gm_tr_take_start }", take)
        trophy = self.body(self.TR, "gm_state_tr_make_trophy")
        self.assertIn("set_variable = { name = gm_tr_start_grandeur value = scope:gm_tr_state.var:gm_tr_take_start }",
                      trophy)
        piece = self.body(self.TR, "gm_state_tr_remove_piece")
        self.assertIn("if = { limit = { has_variable = gm_start_grandeur } "
                      "change_variable = { name = gm_start_grandeur subtract = var:gm_tr_take_start } "
                      "clamp_variable = { name = gm_start_grandeur min = 0 } }", piece)

    def test_a_piece_of_a_monument_beside_carries_its_share(self):
        take = self.body(MON_EFFECTS, "gm_mon_tr_take")
        self.assertIn("set_variable = { name = gm_tr_take_start value = gm_mon_tr_start }", take)
        self.assertIn("set_variable = { name = gm_tr_take_start value = scope:gm_mon_target.var:gm_tr_take_start }",
                      take)
        piece = self.body(MON_EFFECTS, "gm_mon_tr_take_piece")
        self.assertIn("set_variable = { name = gm_tr_start_grandeur value = scope:gm_tr_state.var:gm_tr_take_start }",
                      piece)
        self.assertIn("if = { limit = { has_variable = gm_tr_start_grandeur } "
                      "change_variable = { name = gm_tr_start_grandeur subtract = scope:gm_tr_state.var:gm_tr_take_start } "
                      "clamp_variable = { name = gm_tr_start_grandeur min = 0 } }", piece)
        # What it counts for abroad: half its starting grandeur and age.
        self.assertIn("value = scope:gm_tr_state.var:gm_tr_take_start add = scope:gm_tr_state.var:gm_tr_take_age",
                      piece)

    def test_a_return_brings_it_back(self):
        receive = self.body(self.TR, "gm_state_tr_receive")
        self.assertIn("gm_state_add_start_from_moving = yes", receive)
        add = self.body(self.TR, "gm_state_add_start_from_moving")
        self.assertIn("limit = { has_variable = gm_start_grandeur }", add)
        self.assertIn("change_variable = { name = gm_start_grandeur add = scope:gm_tr_moving.var:gm_tr_start_grandeur }",
                      add)
        self.assertIn("change_variable = { name = gm_start_grandeur add = scope:gm_tr_moving.var:gm_tr_levels }", add)

    def test_rededicate_halves_it(self):
        # The answer's (RededicateTests): every record halves, none is lost.
        body = self.body(EFFECTS, "gm_state_apply_rededicate")
        for s in ("remove_variable = gm_rededicate_levels", "remove_variable = gm_rededicate_start",
                  "remove_variable = gm_rededicate_age"):
            self.assertIn(s, body)

    def test_a_landmark_is_recorded_at_its_levels(self):
        body = self.body(LANDMARK_EFFECTS, "gm_seed_landmark")
        self.assertIn("set_variable = { name = gm_levels value = $LEVEL$ }", body)
        # Its grandeur at the 1836 rate (owner, 2026-10-19), alone or beside
        # another, split by the years since it was built (HistoricalGrandeurTests).
        self.assertIn("gm_set_historical_grandeur = { LEVELS = $LEVEL$ BUILT = $BUILT$ START = gm_start_grandeur "
                      "AGE = gm_age }", body)
        beside = self.body("common/scripted_effects/gm_monument_effects.txt", "gm_seed_landmark_beside")
        self.assertIn("gm_set_historical_grandeur = { LEVELS = $LEVEL$ BUILT = $BUILT$ START = gm_tr_start_grandeur "
                      "AGE = gm_tr_age }", beside)
        self.assertNotIn("gm_start_grandeur", beside.replace("gm_tr_start_grandeur", ""))


class HistoricalGrandeurTests(unittest.TestCase):
    """A historical monument's grandeur, split as if it had aged in the game
    since it was built (owner, 2026-10-19): the same grandeur in 1836, but the
    Parthenon is nearly all years and barely ages further."""

    def test_the_helper(self):
        body = squash(block(read(EFFECTS), "gm_set_historical_grandeur"))
        self.assertEqual(body,
                         "set_variable = { name = $START$ value = { value = $LEVELS$ multiply = gm_level_grandeur_1836 "
                         "divide = { value = gm_this_year subtract = $BUILT$ max = gm_age_cap_years multiply = 2 "
                         "divide = 100 add = 1 min = 1 } } } "
                         "set_variable = { name = $AGE$ value = { value = $LEVELS$ multiply = gm_level_grandeur_1836 "
                         "subtract = var:$START$ min = 0 } }")
        # The same 2% of starting grandeur a year, for at most a century, that
        # ageing adds in the game.
        self.assertTrue(squash(block(read(VALUES), "gm_state_age_step")).startswith(
            "value = gm_state_primary_start multiply = 2 divide = 1200"))

    def test_every_historical_row_has_a_year(self):
        historical = {lm.key for lm in LANDMARKS if lm.year is None}
        self.assertEqual(set(BUILT), historical)
        for key, year in BUILT.items():
            self.assertIsInstance(year, int, key)
            self.assertLessEqual(year, 1836, key)

    def test_the_split_keeps_the_grandeur(self):
        for key, built in BUILT.items():
            start, age = historical_split(10, built)
            self.assertAlmostEqual(start + age, 50, msg=key)
            # Aged at 2% of its start a year since, for at most a century, it
            # comes to what it has.
            self.assertAlmostEqual(start * (1 + 0.02 * min(1836 - built, 100)), 50, msg=key)
        self.assertEqual(historical_split(15, BUILT["arc_de_triomphe"]), (75, 0))
        # A century old or more: a third and two thirds, and no further ageing.
        start, age = historical_split(10, BUILT["parthenon"])
        self.assertAlmostEqual(start, 50 / 3)
        self.assertAlmostEqual(age, 2 * start)
        start, age = historical_split(10, BUILT["brandenburg_gate"])
        self.assertAlmostEqual(start, 50 / 1.9)


class DedicateButtonTests(unittest.TestCase):
    """A monument waits undedicated while it is built, as long as its owner
    likes; its Dedicate button opens the ceremony once none of its levels are
    under construction (owner: pausing is fine, building in parallel is not),
    and the answer finishes it at the levels built, so levels built after it
    raise a new monument beside it. The AI has no button: its ceremony asks
    once nothing more is queued."""

    def test_the_ceremony_starts_only_where_it_should(self):
        """A player's ceremony comes from the button or Rededicate; every other
        start is the AI's, once nothing is queued. Every file under common/ and
        events/ is read, so a new start, or a direct trigger of the ceremony
        event, fails here until it gets a row. The debug events are exempt."""
        allowed = {
            ("common/scripted_effects/gm_effects.txt", "gm_state_rededicate"): None,
            ("common/scripted_effects/gm_effects.txt", "gm_state_offer_missed_ceremony"): "gm_state_ai_dedicates_now = yes",
            (SGUIS, "gm_dedicate_sgui"): None,
            (EVENTS, "monument_events.1"): "gm_state_ai_dedicates_now = yes NOT = { has_variable = gm_ceremony_pending } } "
                                           "gm_state_start_ceremony = yes",
        }
        direct = re.compile(r"monument_events\.2(?![\w.])")
        found, triggers = set(), set()
        paths = sorted(ROOT.glob("common/**/*.txt")) + sorted(ROOT.glob("events/*.txt"))
        self.assertGreater(len(paths), 100)
        for path in paths:
            rel = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            if "gm_state_start_ceremony = yes" not in text and not direct.search(text):
                continue
            for name, body in top_level_blocks(text):
                if rel.startswith("events/te_debug_"):
                    continue
                flat = squash(body)
                if re.search(r"trigger_event\s*=\s*\{\s*id\s*=\s*monument_events\.2(?![\w.])", flat):
                    triggers.add((rel, name))
                if "gm_state_start_ceremony = yes" in flat and name != "gm_state_start_ceremony":
                    found.add((rel, name))
                    self.assertIn((rel, name), allowed, f"{name} in {rel} starts a ceremony")
                    if allowed[(rel, name)]:
                        self.assertIn(allowed[(rel, name)], flat, name)
        self.assertEqual(found, set(allowed))
        self.assertEqual(triggers, {("common/scripted_effects/gm_effects.txt", "gm_state_start_ceremony")},
                         "the ceremony event is triggered only by gm_state_start_ceremony")
        ai = squash(block(read(TRIGGERS), "gm_state_ai_dedicates_now"))
        self.assertEqual(ai, "owner = { is_ai = yes } gm_state_has_site = yes gm_state_site_level >= 1 "
                             "b:building_grand_monument_site ?= { is_under_construction = no }")
        # A finished building is created on its dedication and locked to it:
        # first sight only records an older save's monument, and opens nothing.
        first = squash(block(read(EFFECTS), "gm_state_first_sight"))
        self.assertNotIn("gm_state_start_ceremony", first)

    def test_the_ai_never_leaves_its_monument_undedicated(self):
        """Its ceremony asks once, when its construction stops; a monument it
        left would not be asked again until it grew."""
        ev = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.2\s*=\s*\{")))
        leaves = re.findall(r"name = monument_events\.2\.a .*?ai_chance = \{ base = (\d+) \}", ev)
        self.assertEqual(leaves, ["0", "0"])

    def test_the_button(self):
        sgui = squash(block(read(SGUIS), "gm_dedicate_sgui"))
        self.assertIn("scope = country saved_scopes = { gm_state }", sgui)
        # Visibility never rests on the saved scope reaching is_shown (gui
        # gotcha #22): the button reads the state's value and owner, and
        # is_valid fails closed.
        self.assertIn("is_shown = { always = yes }", sgui)
        self.assertIn("is_valid = { exists = scope:gm_state scope:gm_state = { owner = root "
                      "gm_state_awaits_dedication = yes", sgui)
        for gate in ("gm_state_site_level >= 1", "b:building_grand_monument_site ?= { is_under_construction = no }",
                     "NOT = { has_variable = gm_ceremony_pending }",
                     "NOT = { has_variable = gm_restore_pm }", "NOT = { has_variable = gm_rebuilding }"):
            self.assertIn(gate, sgui.split("is_valid", 1)[1].split("effect", 1)[0])
        self.assertIn("effect = { scope:gm_state = { custom_tooltip = { text = gm_dedicate_effect_tt "
                      "gm_state_start_ceremony = yes } } }", sgui)
        self.assertIn("ai_is_valid = { always = no }", sgui)
        for key in re.findall(r"text = (gm_\w+)", sgui):
            self.assertIn(key, loc(), key)
        # A construction site (sites spec 2026-10-18 §3.1).
        awaits = squash(block(read(TRIGGERS), "gm_state_awaits_dedication"))
        self.assertEqual(awaits, "gm_system_enabled = yes gm_state_has_site = yes")
        self.assertIn("NOT = { has_variable = gm_seen }",
                      squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.2\s*=\s*\{"))))

    def test_mounted_on_the_card_and_the_awaiting_rows(self):
        widget = squash(strip_comments(read(WIDGET)))
        self.assertIn("type gm_dedicate_button = button {", widget)
        self.assertIn("datacontext = \"[GetScriptedGui('gm_dedicate_sgui')]\"", widget)
        self.assertIn("visible = \"[And( ObjectsEqual( State.GetOwner, GetPlayer.Self ), EqualTo_CFixedPoint( "
                      "State.MakeScope.ScriptValue('gm_state_disp_awaiting'), '(CFixedPoint)1' ) )]\"", widget)
        raw = strip_comments(read(WIDGET))
        m = re.search(r"type gm_dedicate_button = button \{", raw)
        button = squash(_match_brace(raw, m.end()))
        self.assertNotIn("IsShown", button, "visibility must not rest on is_shown's saved scope")
        self.assertIn("visible = \"[And( ObjectsEqual( State.GetOwner, GetPlayer.Self ), EqualTo_CFixedPoint( "
                      "State.MakeScope.ScriptValue('gm_state_disp_awaiting'), '(CFixedPoint)1' ) )]\"", button)
        for verb in ("IsValid", "Execute"):
            self.assertIn(f"ScriptedGui.{verb}( GuiScope.SetRoot( GetPlayer.MakeScope ).AddScope( 'gm_state', "
                          f"State.MakeScope ).End )", widget)
        self.assertIn("gm_button_dedicate", loc())
        self.assertIn("gm_button_dedicate_tooltip", loc())
        card = squash(strip_comments(read("gui/te_state_panel_widgets.gui")))
        # On the site's card (SitePanelTests).
        self.assertIn("gm_dedicate_button = {}", card)
        sec = squash(strip_comments(read(WIDGET).split("type te_gm_sec_awaiting = flowcontainer {", 1)[1]
                                    .split("type te_gm_sec_monuments", 1)[0]))
        self.assertIn("visible = \"[GreaterThan_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue("
                      "'gm_disp_count_awaiting'), '(CFixedPoint)0' )]\"", sec)
        self.assertIn("datamodel = \"[JournalEntry.GetCountry.MakeScope.GetList('gm_states')]\"", sec)
        self.assertIn("datacontext = \"[Scope.GetState]\" visible = \"[EqualTo_CFixedPoint( State.MakeScope"
                      ".ScriptValue('gm_state_disp_awaiting'), '(CFixedPoint)1' )]\"", sec)
        self.assertIn("gm_site_row = {} gm_dedicate_button = {}", sec)
        # The section's gate and its rows read the same trigger.
        values = read(VALUES)
        self.assertIn("gm_state_awaits_dedication = yes", squash(block(values, "gm_disp_count_awaiting")))
        self.assertIn("gm_state_awaits_dedication = yes", squash(block(values, "gm_state_disp_awaiting")))
        # Sites are not monuments yet: Our Monuments lists every finished one.
        self.assertEqual(squash(block(values, "gm_disp_count_listed")), "value = gm_sum_monuments")

    def test_the_answer_finishes_it_at_the_levels_built(self):
        dedicate = squash(block(read(EFFECTS), "gm_state_dedicate"))
        # The site's levels (gm_state_finish_site), or an older save's.
        self.assertLess(dedicate.find("set_variable = gm_seen"),
                        dedicate.find("set_variable = { name = gm_levels value = gm_state_primary_levels }"))

    def test_words(self):
        L = loc()
        self.assertNotIn("asks again", L["gm_ded_reason_leave_tt"])
        self.assertNotIn("asks again", L["gm_je_status_undedicated_tt"])
        self.assertNotIn("asks again", L["gm_je_how_counts_other"])
        self.assertIn("Dedicate button", L["gm_je_how_grandeur"])
        self.assertIn("Dedicate button", L["monument_events.2.a.tt"])
        self.assertNotIn("once its last stone is laid", L["monument_events.2.d"])
        # The button can't press mid-construction, so no text promises that
        # levels under construction become a monument beside it.
        for key in ("gm_dedicate_effect_tt", "gm_je_how_grandeur", "gm_row_frozen_tt", "monument_events.2.d"):
            self.assertNotIn("still under construction", L[key], key)
            self.assertNotIn("still being built", L[key], key)
        self.assertIn("under construction", L["gm_sgui_dedicate_building_tt"])


# ---- Final review of the sites branch (2026-10-19) ----------------------------------

class SitesFinalReviewTests(unittest.TestCase):
    """The whole-branch review's findings: each pins the behaviour the
    structural pins above let through."""

    def test_vanity_amount_is_read_on_the_state(self):
        # C1: $AMOUNT$ expands inside owner = { }, so var:gm_site_add read
        # there is the country's (none); prev is the state.
        count = squash(block(read(EFFECTS), "gm_state_count_site_levels"))
        self.assertIn("gm_state_vanity_backlash_for = { AMOUNT = prev.var:gm_site_add }", count)
        helper = squash(block(read(EFFECTS), "gm_state_vanity_backlash_for"))
        # prev must be the state when $AMOUNT$ is read: no call between.
        self.assertIn("owner = { change_variable = { name = gm_vanity_ledger add = $AMOUNT$ }", helper)

    def test_rededicate_asks_while_a_restore_stands(self):
        # I1: Rededicate on a monument beside another swaps it in first, which
        # sets gm_restore_pm; the ceremony must still ask.
        body = squash(block(read(EFFECTS), "gm_state_start_ceremony"))
        self.assertIn("OR = { has_variable = gm_rededicate_asking NOT = { has_variable = gm_restore_pm } }", body)

    def test_migration_keeps_levels_above_the_record(self):
        # I2: levels finished on a dedicated monument above its recorded size
        # (queued before the update) become a construction site, not lost.
        body = squash(block(read(EFFECTS), "gm_state_migrate"))
        dedicated = body[:body.index("else = { set_variable = { name = gm_migrate_levels")]
        self.assertIn("set_variable = { name = gm_mig_excess value = gm_state_built_levels }", dedicated)
        self.assertIn("change_variable = { name = gm_mig_excess subtract = var:gm_levels }", dedicated)
        self.assertIn("SPEC_TYPE = building_grand_monument_site SPEC_LEVEL = var:gm_mig_excess", dedicated)
        self.assertIn("set_variable = { name = gm_site_counted value = var:gm_mig_excess }", dedicated)
        self.assertIn("set_variable = { name = gm_site_grandeur value = var:gm_mig_excess }", dedicated)
        # Measured before the building goes back to level 1.
        self.assertLess(dedicated.index("gm_mig_excess value = gm_state_built_levels"),
                        dedicated.index("remove_building = building_grand_monument"))

    def test_merge_reset_waits_for_migration(self):
        # Minor 7, re-graded: an older save's building stands at its full
        # height until .32 records it; a merge must not reset it first.
        pending = squash(block(read(MON_TRIGGERS), "gm_state_merge_pending"))
        self.assertIn("AND = { has_variable = gm_migrated gm_state_level > 1 }", pending)
        settle = squash(block(read(MON_EFFECTS), "gm_sh_settle_region"))
        self.assertIn("has_building = building_grand_monument has_variable = gm_migrated gm_state_level > 1", settle)

    def test_upkeep_waits_for_migration(self):
        # I3: pm_maintenance is level-scaled, so the multiplier on an older
        # save's full-height building would square its upkeep.
        mult = squash(block(read(VALUES), "gm_state_upkeep_mult"))
        self.assertIn("if = { limit = { NOT = { has_variable = gm_migrated } } value = 0 }", mult)
        self.assertGreater(mult.index("NOT = { has_variable = gm_migrated }"), mult.index("subtract = 1"))

    def test_every_finished_building_script_makes_is_migrated(self):
        # The upkeep and merge gates rest on it: every create_building of the
        # finished type sits in a body that sets gm_migrated.
        # Two set it through what they call: a raised orphan takes its records
        # (gm_state_raise_secondary → gm_state_tr_take_records_from_moving),
        # and the merge's reset runs only where the record stands
        # (test_merge_reset_waits_for_migration).
        through = {"gm_state_raise_orphan": "gm_state_raise_secondary = yes",
                   "gm_state_reset_building_level": None}
        take = squash(block(read("common/scripted_effects/gm_trophy_effects.txt"),
                            "gm_state_tr_take_records_from_moving"))
        self.assertIn("set_variable = gm_migrated", take)
        self.assertIn("gm_state_tr_take_records_from_moving = yes",
                      squash(block(read(MON_EFFECTS), "gm_state_raise_secondary")))
        seen = set()
        for rel in (EFFECTS, MON_EFFECTS, "common/scripted_effects/gm_trophy_effects.txt",
                    LANDMARK_EFFECTS, "common/scripted_effects/gm_archaeology_effects.txt", EVENTS,
                    COM_EFFECTS, DEBUG_EVENTS):
            for name, body in top_level_blocks(read(rel)):
                if re.search(r"create_building\s*=\s*\{\s*building\s*=\s*building_grand_monument\s", body):
                    seen.add(name)
                    if name in through:
                        if through[name]:
                            self.assertIn(through[name], squash(body), name)
                    else:
                        self.assertIn("gm_migrated", body, f"{rel}: {name}")
        self.assertGreaterEqual(len(seen), 7, sorted(seen))

    def test_opportunity_text_counts_grandeur(self):
        # I4: the target is grandeur (Plan B); what is queued is levels.
        L = loc()
        head = L["gm_com_accept_head"]
        self.assertIn("ScriptValue('gm_disp_com_target')|1]#! [concept_grandeur]", head)
        self.assertNotIn("levels of monuments", head)
        build = L["gm_com_accept_build_line"]
        self.assertIn("ScriptValue('gm_disp_com_target_levels')|0]#! levels", build)
        progress = L["gm_je_com_progress_tt"]
        self.assertNotIn("Levels raised", progress)
        self.assertIn("ScriptValue('gm_disp_com_progress')|1]", progress)
        self.assertIn("ScriptValue('gm_disp_com_target')|1]", progress)
        val = L["gm_je_com_val_progress"]
        self.assertIn("ScriptValue('gm_disp_com_progress')|1]", val)
        self.assertIn("ScriptValue('gm_disp_com_target')|1]", val)
        self.assertNotIn("raised higher", L["gm_je_com_ask_tt"])
        self.assertIn("gm_disp_com_target_levels = { value = gm_com_target_levels }",
                      squash(strip_comments(read(COM_VALUES))))
        guide = squash((ROOT / "docs/player_guide/02-timeline.md").read_text(encoding="utf-8"))
        self.assertNotIn("queues its five levels", guide)

    def test_rededicate_tooltip_has_no_rebuild(self):
        # Minor 6, re-graded: Rededicate halves the records; nothing is rebuilt.
        tt = loc()["gm_rededicate_tt"]
        self.assertNotIn("Rebuild", tt)
        self.assertNotIn("200 levels", tt)
        self.assertIn("half its levels", tt)

    def test_ai_tops_up_an_opportunity(self):
        # I5: one queue on seizing is capped at 100 levels; past twenty times
        # 1836's wealth the AI queues the rest once its site is dedicated.
        body = squash(block(read(COM_EFFECTS), "gm_com_monthly"))
        self.assertIn("if = { limit = { has_variable = gm_com_open is_ai = yes gm_com_levels_to_go > 0 "
                      "NOT = { any_scope_state = { has_building = building_grand_monument_site } } } "
                      "gm_com_ai_queue = yes }", body)

    def test_merge_level1_self_check(self):
        # I6: plan A Task 7's self-check, and the reset puts the recorded
        # dedication back, not whatever the merged building kept.
        reset = squash(block(read(MON_EFFECTS), "gm_state_reset_building_level"))
        self.assertIn("set_variable = { name = gm_merge_check value = gm_state_level }", reset)
        self.assertIn("if = { limit = { has_variable = gm_dedication } "
                      "set_variable = { name = gm_restore_pm value = var:gm_dedication } }", reset)
        self.assertLess(reset.index("gm_merge_check"), reset.index("remove_building"))
        check = squash(block(read(MON_EFFECTS), "gm_monument_merge_level_self_check"))
        self.assertIn("NOT = { has_variable = gm_rebuilding } NOT = { has_variable = gm_restore_pm }", check)
        self.assertIn("gm_state_level = 1 gm_state_stands_on_dedication = yes", check)
        self.assertIn("TE_SELF_CHECK OK monument_merge_level1", check)
        self.assertIn("TE_SELF_CHECK BROKEN monument_merge_level1", check)
        self.assertIn("gm_monument_merge_level_self_check = yes", squash(block(read(EFFECTS), "gm_state_monthly")))
        stands = squash(block(read(TRIGGERS), "gm_state_stands_on_dedication"))
        for d in DEDICATIONS:
            self.assertIn(f"AND = {{ var:gm_dedication = flag:{d.key} gm_state_has_pm = {{ PM = pm_monument_{d.key} }} }}",
                          stands, d.key)
        playtest = (ROOT / "docs/testing/grand-monuments-ageing-playtest.md").read_text(encoding="utf-8")
        self.assertIn("`TE_SELF_CHECK OK/BROKEN monument_merge_level1`", playtest)

    def test_created_check_waits_a_day(self):
        # I7: on the creation day the restore neither switches nor judges.
        body = squash(block(read(COM_EFFECTS), "gm_state_restore_dedication"))
        self.assertIn("NOT = { AND = { has_variable = gm_created_check has_variable = gm_rebuilding } }", body)

    def test_dedicate_reads_no_walked_variable(self):
        # Minor 4, re-graded: the options' tooltips walk gm_state_dedicate, and
        # gm_levels is written above in the same walk (never, there).
        body = squash(block(read(EFFECTS), "gm_state_dedicate"))
        self.assertIn("if = { limit = { NOT = { has_variable = gm_start_grandeur } } "
                      "set_variable = { name = gm_start_grandeur value = gm_state_primary_levels } }", body)
        self.assertNotIn("value = var:gm_levels", body)

    def test_rate_prints_small(self):
        # Minor 5, re-graded: past 200 times 1836's wealth |2 reads 0.00.
        L = loc()
        for key in ("gm_je_world_rate", "gm_site_card_rate", "gm_site_rate_tt", "gm_site_row_rate"):
            self.assertIn("ScriptValue('gm_world_rate_value')|3]", L[key], key)
            self.assertNotIn("ScriptValue('gm_world_rate_value')|2]", L[key], key)
        # What a level adds in 1836, spliced, not "N levels make one": the rate
        # passes one in 1836 (owner, 2026-10-19).
        for key in ("gm_je_world_rate", "gm_site_rate_tt", "gm_site_row_rate", "gm_je_world_rate_tt"):
            self.assertIn("ScriptValue('gm_level_grandeur_1836')|0]#! in 1836", L[key], key)
            self.assertNotIn("levels make one", L[key], key)
        # How It Works reads nothing (test_grand_monuments_layout), so it states the figure.
        self.assertEqual(squash(strip_comments(block(read(VALUES), "gm_level_grandeur_1836"))), "value = 5")
        self.assertIn("(5 in 1836, and a tenth as much in a world ten times richer)", L["gm_je_how_grandeur"])
        # A floor, so the wealth factor never divides by zero.
        self.assertIn("min = 0.00001", squash(block(read(VALUES), "gm_world_rate_now")))


# ---- The dedication opens at once (owner, 2026-10-19) -------------------------------

class DedicationPopupTests(unittest.TestCase):
    """The dedication's chain opens as windows, not notification cards: the
    ceremony (2), the style (11), the form (24), the namesake (25) and the seized
    opportunity's notice (28). Each event says `is_popup = yes` and every call
    that fires one says `popup = yes` (event_creation_guide.md § "Making an
    Event Open at Once"). Only the game shows the window; this pins the script."""

    CHAIN = ("2", "11", "24", "25", "28")

    def test_each_event_in_the_chain_is_a_popup(self):
        events = read(EVENTS)
        for n in self.CHAIN:
            ev = squash(strip_comments(raw_block_at(events, rf"(?m)^monument_events\.{n}\s*=\s*\{{")))
            head = ev.split(" option = {")[0]
            self.assertIn(" is_popup = yes ", head + " ", f"monument_events.{n} opens as a card")

    def test_every_call_that_fires_one_asks_for_the_popup(self):
        fire = re.compile(r"trigger_event\s*=\s*\{([^{}]*)\}")
        chain = re.compile(r"id\s*=\s*monument_events\.(" + "|".join(self.CHAIN) + r")(?![\w.])")
        paths = sorted(ROOT.glob("common/**/*.txt")) + sorted(ROOT.glob("events/*.txt"))
        self.assertGreater(len(paths), 100)
        seen = {}
        for path in paths:
            rel = path.relative_to(ROOT).as_posix()
            text = strip_comments(path.read_text(encoding="utf-8-sig", errors="replace"))
            for m in fire.finditer(text):
                hit = chain.search(m.group(1))
                if not hit:
                    continue
                seen[hit.group(1)] = seen.get(hit.group(1), 0) + 1
                self.assertRegex(m.group(1), r"\bpopup\s*=\s*yes\b",
                                 f"{rel}: trigger_event {squash(m.group(1))} opens a card")
        self.assertEqual(set(seen), set(self.CHAIN), "a fire site went missing, so the pin read nothing")
        # The form event's thirty-one options each fire the namesake event.
        self.assertGreaterEqual(seen["25"], 32)

    def test_anniversaries_and_offers_stay_cards(self):
        events = read(EVENTS)
        for n in ("3", "4", "5", "6", "7", "8", "9", "10", "12", "13", "14", "15", "21"):
            ev = squash(strip_comments(raw_block_at(events, rf"(?m)^monument_events\.{n}\s*=\s*\{{")))
            self.assertNotIn("is_popup", ev, f"monument_events.{n}")


if __name__ == "__main__":
    unittest.main()
