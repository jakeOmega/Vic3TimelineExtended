"""The Grand Monument registry: every dedication, skin and IG alignment in one
table, pinned against every site that lists them by hand.

Design: docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md.
Adding a dedication touches its PM and the ratchet, the PM group, its kind and
fit trigger, the IG alignment triggers, its local and national modifiers and
their step mirrors, the ceremony option, the skin rules, its flavour event and
the loc. Nothing in the engine checks that they agree. DEDICATIONS is the
single list; each test checks one site against it, so a half-added dedication
fails here, naming the site.

Run: python3 -m unittest test_grand_monument_registry -v
"""
import re
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
               "state_conscription_rate_add", 0.05,
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
        self.assert_pair("gm_local_tourism", "building_tourism_industry_throughput_add",
                         "gm_step_tourism", 0.25)
        for d in DEDICATIONS:
            self.assert_pair(f"gm_local_{d.key}", d.local_field, f"gm_step_local_{d.key}", d.local_step)

    def test_culture_step(self):
        self.assertRegex(strip_comments(read(VALUES)), r"(?m)^gm_step_culture = 1\s*$")

    def test_each_modifier_has_one_field_and_an_icon(self):
        for name, body in top_level_blocks(read(MODIFIERS)):
            if not name.startswith(("gm_national_", "gm_ig_approval_", "gm_local_")):
                continue
            fields = [k for k in re.findall(r"(?m)^\s*(\w+)\s*=", body) if k != "icon"]
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
            if d.key in TECH_GATES:
                self.assertIn(f"unlocking_technologies = {{ {TECH_GATES[d.key]} }}", body, d.key)
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
        ai = squash(block(read(BUILDING), "ai_value"))
        self.assertIn("owner = { gm_country_hard_times = yes } } add = -100", ai)
        self.assertIn("owner = { is_at_war = yes } } add = -100", ai)
        self.assertIn("owner = { government_legitimacy < 40 } } add = 25", ai)

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
        self.assertTrue(body.startswith("gm_remove_local_modifiers = yes"))
        self.assertIn("set_variable = { name = gm_curve_in value = gm_state_grandeur }", body)
        # The monument policy (v2 §5) scales the steps: tourism and the local effect separately.
        self.assertIn("set_variable = { name = gm_local_steps value = { value = gm_curve_steps_f5 "
                      "multiply = gm_policy_factor_local } }", body)
        self.assertIn("set_variable = { name = gm_local_tourism_steps value = { value = gm_curve_steps_f5 "
                      "multiply = gm_policy_factor_tourism } }", body)
        self.assertIn("add_modifier = { name = gm_local_tourism multiplier = var:gm_local_tourism_steps }", body)
        for policy in ("open", "mothballed"):
            self.assertIn(f"b:building_grand_monument ?= {{ add_modifier = {{ name = gm_policy_upkeep_{policy} }} }}",
                          body)
        for d in DEDICATIONS:
            self.assertIn(f"gm_add_local = {{ KEY = {d.key} }}", body)
        self.assertIn("add_modifier = { name = gm_local_$KEY$ multiplier = var:gm_local_steps }",
                      squash(block(self.e, "gm_add_local")))

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
        self.assertIn("value = b:building_grand_monument.level", squash(block(v, "gm_state_grandeur")))
        code = squash(block(v, "gm_status_code"))
        for n in (1, 2, 3, 4):
            self.assertIn(f"value = {n} }}", code)


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
        self.assertIn("limit = { gm_state_counts_standing = yes } add = gm_state_grandeur",
                      squash(block(self.v, "gm_sum_standing")))
        self.assertIn("gm_state_status_fits = yes OR = { gm_state_kind_regime = yes gm_state_kind_ruler = yes }",
                      squash(block(self.v, "gm_sum_regime")))
        for key in NATIONAL:
            self.assertIn(f"gm_state_status_fits = yes gm_state_has_pm = {{ PM = pm_monument_{key} }}",
                          squash(block(self.v, f"gm_sum_{key}")))

    def test_totals_use_the_right_curves(self):
        body = squash(block(self.e, "gm_compute_totals"))
        self.assertIn("gm_set_steps = { IN = gm_g_standing OUT = gm_s_standing NEXT = gm_n_standing F = 5 }", body)
        self.assertIn("gm_set_steps = { IN = gm_g_standing OUT = gm_s_culture NEXT = gm_n_culture F = 10 }", body)
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
                 "set_variable = { name = gm_grandeur value = gm_state_grandeur }",
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
        self.assertIn("max = 5", body)
        self.assertIsNone(block(text, "grand_monument_levels_in_state"))


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
        self.assertIn("limit = { gm_state_is_dedicated = yes gm_state_is_bound = yes "
                      "NOT = { has_variable = gm_ceremony_pending } }", body)
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
                  "remove_building = building_grand_monument", "gm_clear_state = yes"):
            self.assertIn(s, tear)
        rededicate = squash(block(self.e, "gm_state_rededicate"))
        for s in ("set_variable = { name = gm_rebuild_cost value = gm_state_rededicate_cost }",
                  "add_treasury = { value = prev.var:gm_rebuild_cost multiply = -1 }",
                  "gm_state_ledger_ig = { WHO = gm_supporter_ig FACTOR = -0.5 }",
                  "divide = 2 ceiling = yes max = 200",
                  "SPEC_TYPE = building_grand_monument SPEC_LEVEL = var:gm_rebuild_level",
                  "gm_state_start_ceremony = yes"):
            self.assertIn(s, rededicate)
        self.assertLess(rededicate.find("gm_clear_state = yes"),
                        rededicate.find("te_construction_market_build_specified_level"))
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
        self.assertIn("set_variable = { name = gm_ceremony_level value = gm_state_grandeur }", body)
        self.assertIn("trigger_event = { id = monument_events.2 }", body)

    def test_the_refresh_asks_a_ceremony_the_hook_missed(self):
        """Five queued levels finishing on one day fired no on_building_built
        (2026-10-07): the refresh asks once for each grandeur no ceremony has
        asked about, so leaving a monument undedicated waits for its next level."""
        sweep = squash(block(self.e, "gm_state_offer_missed_ceremony"))
        self.assertIn("if = { limit = { gm_system_enabled = yes gm_state_is_dedicated = no "
                      "NOT = { has_variable = gm_ceremony_pending } "
                      "OR = { NOT = { has_variable = gm_ceremony_level } "
                      "AND = { has_variable = gm_ceremony_level var:gm_ceremony_level < gm_state_grandeur } } } "
                      "gm_state_start_ceremony = yes }", sweep)
        refresh = squash(block(self.e, "gm_country_refresh"))
        self.assertLess(refresh.find("every_scope_state = { limit = { has_building = building_grand_monument }"),
                        refresh.find("gm_state_offer_missed_ceremony = yes"))
        self.assertLess(refresh.find("gm_state_offer_missed_ceremony = yes"),
                        refresh.find("add_to_variable_list = { name = gm_states target = prev }"))
        self.assertIn("gm_remove_state_var = { VAR = gm_ceremony_level }", squash(block(self.e, "gm_clear_state")))
        # The event records the level again as it opens: a Rededicate rebuild's
        # level may not be readable in the effect that rebuilt it.
        ev2 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.2\s*=\s*\{")))
        self.assertIn("immediate = { set_variable = { name = gm_ceremony_level value = gm_state_grandeur }", ev2)
        # Leaving it undedicated ends the pending ceremony; the recorded level
        # is what holds the next ask back.
        self.assertIn("default_option = yes", ev2)
        self.assertIn("hidden_effect = { gm_remove_state_var = { VAR = gm_ceremony_pending } "
                      "gm_state_undedicate = yes }", ev2)

    def test_demolished_contested_counts_as_torn_down(self):
        body = squash(block(self.e, "gm_state_monthly"))
        self.assertIn("limit = { gm_state_is_contested = yes } gm_state_record_teardown = yes", body)

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
        # A monument, or an open commission (v2 §2.7), keeps the pulse running.
        self.assertTrue(body.startswith("gm_init_ledgers = yes if = { limit = { OR = { any_scope_state = "
                                        "{ has_building = building_grand_monument } has_variable = gm_com_open } } "
                                        "set_variable = gm_active }"), body[:200])


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
# Named landmarks (spec §1.1, phase 2): (key, the dedications it can take). Each
# is a skin flag `landmark_<key>`, an option `monument_events.11.landmark_<key>`
# placed before the faith options (a landmark is the most specific form), whose
# trigger names its state, and the loc `gm_skin_landmark_<key>`. Empty in phase 1.
LANDMARKS = ()


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
    axis = "heritage" if d.key in HERITAGE_SKINNED else "none"
    return f"gm_state_dedicate_timeless = {{ KEY = {d.key} AXIS = {axis} }}"


class CeremonyTests(unittest.TestCase):
    def test_every_dedication_has_its_option(self):
        options = ceremony_options()
        self.assertEqual(set(options), set(CEREMONY_OPTION.values()) | {"a"})
        for d in DEDICATIONS:
            body = squash(strip_comments(options[CEREMONY_OPTION[d.key]]))
            self.assertIn(f"text = monument_events.2.{CEREMONY_OPTION[d.key]}.tt {wrapper_call(d)}", body, d.key)
            if d.key in CEREMONY_GATE:
                self.assertIn(CEREMONY_GATE[d.key], body, d.key)
            if d.key in TECH_GATES:
                self.assertIn(f"has_technology_researched = {TECH_GATES[d.key]}", body, d.key)

    def test_leave_undedicated_clears_the_pending_flag(self):
        body = ceremony_options()["a"]
        self.assertNotIn("REVIEWED", body)
        self.assertIn("gm_remove_state_var = { VAR = gm_ceremony_pending }", squash(body))

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
                      "trigger_event = { id = monument_events.11 }", faith_offer)
        heritage_offer = squash(block(e, "gm_state_offer_skins_heritage"))
        self.assertIn("owner = { is_ai = no } } set_variable = { name = gm_skin_axis value = flag:heritage } "
                      "trigger_event = { id = monument_events.11 }", heritage_offer)


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
        expected = ([f"landmark_{k}" for k, _ in LANDMARKS] + [f"faith_{f}" for f in FAITHS]
                    + [f"heritage_{h}" for h in heritages_in_option_order] + ["generic"])
        self.assertEqual(names, expected)
        self.assertLess(names.index("heritage_hebrew"), names.index("generic"))
        for h in ("arabic", "geez", "aramaic"):
            self.assertLess(names.index(f"heritage_{h}"), names.index("heritage_hebrew"))
        bodies = dict(options)
        for f in FAITHS:
            self.assertIn(f"var:gm_skin_axis = flag:faith owner = {{ religion = rel:{f} }}", bodies[f"faith_{f}"])
            self.assertIn(f"gm_state_choose_skin = {{ SKIN = faith_{f} }}", bodies[f"faith_{f}"])
        for h in HERITAGES:
            skin = f"faith_{HERITAGE_AS_FAITH[h]}" if h in HERITAGE_AS_FAITH else f"heritage_{h}"
            self.assertIn(f"var:gm_skin_axis = flag:heritage owner = {{ te_heritage_{h} = yes }}",
                          bodies[f"heritage_{h}"])
            self.assertIn(f"gm_state_choose_skin = {{ SKIN = {skin} }}", bodies[f"heritage_{h}"])
        self.assertNotIn("default_option", squash(strip_comments(self.event)))

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

    def test_landmarks_phase_2_hook(self):
        L = loc()
        names = [n for n, _ in self._options()]
        names_block = squash(block(read(CUSTOM_LOC), "gm_skin_name"))
        for key, _dedications in LANDMARKS:
            self.assertIn(f"landmark_{key}", names)
            self.assertLess(names.index(f"landmark_{key}"), names.index(f"faith_{FAITHS[0]}"))
            self.assertIn(f"gm_skin_landmark_{key}", L)
            self.assertIn(f"flag:landmark_{key} }} localization_key = gm_skin_landmark_{key}", names_block)

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
        # Minor 3: a Rededicate rebuild's own on_building_built must not
        # backlash on a level it did not earn (gm_state_rededicate sets
        # gm_rebuilding for one day around the rebuild).
        self.assertIn("owner = { gm_country_hard_times = yes } NOT = { has_variable = gm_rebuilding } } "
                      "gm_state_vanity_backlash = yes", ev)
        self.assertIn("gm_state_is_dedicated = no } gm_state_start_ceremony = yes", ev)
        self.assertIn("owner = { trigger_event = { id = monument_events.20 } }", ev)
        self.assertNotIn("add_modifier", ev, "ROOT is the building here: no multiplier modifiers")

    def test_rededicate_guards_against_its_own_backlash(self):
        rededicate = squash(block(read(EFFECTS), "gm_state_rededicate"))
        self.assertIn("set_variable = { name = gm_rebuilding days = 1 }", rededicate)
        self.assertLess(rededicate.find("gm_rebuilding"), rededicate.find("remove_building = building_grand_monument"))

    def test_backlash(self):
        body = squash(block(read(EFFECTS), "gm_state_vanity_backlash"))
        self.assertIn("add_radicals_in_state = { value = 0.005 }", body)
        self.assertIn("change_variable = { name = gm_vanity_ledger add = 1 }", body)
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
        self.assertIn('gm_monument_row = { datacontext = "[Scope.GetState]" }', g)

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
        values = read(VALUES)
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

    def test_culture_line_hides_next_step_at_cap(self):
        # Deferred item (2026-09-27): gm_display_culture caps at +5, but the
        # F=10 curve keeps advancing past it, so "next step at" would keep
        # showing after there is no more benefit to reach. gm_display_n_culture
        # returns 0 at the cap and the loc line drops the clause when it does,
        # the same "hide via SelectLocalization + EqualTo_CFixedPoint" shape
        # TE_HOMELAND_REMOVAL_THRESHOLD_TT uses for its own _ZERO clause.
        v = squash(block(read(VALUES), "gm_display_n_culture"))
        self.assertIn("has_variable = gm_n_culture var:gm_s_culture < 5", v)
        # Since the style pass (2026-09-29) the clause is in the Cultural Pull
        # row's tooltip, and the cap has words of its own instead of ''.
        L = loc()
        self.assertIn("SelectLocalization(EqualTo_CFixedPoint("
                      "JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_n_culture'), "
                      "'(CFixedPoint)0'), 'gm_je_tt_culture_cap', 'gm_je_tt_culture_next')", L["gm_je_tt_culture"])
        self.assertIn("next step at", L["gm_je_tt_culture_next"])
        self.assertNotIn("next step", L["gm_je_tt_culture_cap"])
        self.assertIn('tooltip = "gm_je_tt_culture"', read(WIDGET))


# ---- Task 10: flavour events ---------------------------------------------------------

class FlavourTests(unittest.TestCase):
    def test_dispatch(self):
        body = squash(block(read(ON_ACTIONS), "monument_events_on_action"))
        self.assertIn("trigger = { gm_system_enabled = yes "
                      "NOT = { gm_policy_is = { P = mothballed STANDARD = no } } }", body)
        for d in DEDICATIONS:
            self.assertIn(f"gm_state_holds_anniversary = {{ PM = pm_monument_{d.key} }} }} }} "
                          f"trigger_event = {{ id = monument_events.{d.event} }}", body)

    def test_only_a_fitting_landmark_holds_anniversaries(self):
        self.assertEqual(squash(block(read(TRIGGERS), "gm_state_holds_anniversary")),
                         "gm_state_status_fits = yes gm_state_has_pm = { PM = $PM$ } "
                         "b:building_grand_monument ?= { level >= 3 }")

    def test_events(self):
        text, L = read(EVENTS), loc()
        for d in DEDICATIONS:
            ev = raw_block_at(text, rf"(?m)^monument_events\.{d.event}\s*=\s*\{{")
            self.assertIsNotNone(ev, d.event)
            se = strip_comments(ev)
            s = squash(se)
            self.assertIn(f"gm_state_holds_anniversary = {{ PM = pm_monument_{d.key} }}", s)
            self.assertIn("order_by = gm_state_grandeur position = 0", s)
            self.assertIn("save_scope_as = monument_state", s)
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
        for s in ("gm_state_start_ceremony = yes", "gm_country_monthly = yes", "gm_state_contest = yes",
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

    def test_monthly_log_for_players(self):
        monthly = squash(block(read(EFFECTS), "gm_country_monthly"))
        self.assertIn("limit = { is_ai = no } gm_debug_log = yes", monthly)
        log = block(read(EFFECTS), "gm_debug_log")
        self.assertIn('debug_log = "TE_MONUMENTS:', log)
        self.assertNotIn(".MakeScope", log, "debug_log's working form is [SCOPE.ScriptValue('x')|N]")



# ==== v2 phase 2: commissions (docs/superpowers/specs/2026-10-05-grand-monuments-v2-design.md §2) ====
COM_TRIGGERS = "common/scripted_triggers/gm_commission_triggers.txt"
COM_EFFECTS = "common/scripted_effects/gm_commission_effects.txt"
COM_VALUES = "common/script_values/gm_commission_values.txt"
NAME_TRIGGERS = "common/scripted_triggers/gm_name_triggers.txt"
NAME_EFFECTS = "common/scripted_effects/gm_name_effects.txt"
HISTORY = "common/history/extra_history.txt"

Source = namedtuple("Source", "key dedication namesake form fixed")
# One row per source (§2.2): what it asks for and how the monument would be
# named. A fixed source names the capital (gm_com_fix_to_capital), falling
# back to anywhere when the capital holds a monument of another dedication.
# "$KEY$": the regime's or the petition's dedication.
COMMISSION_SOURCES = (
    Source("victory", "war_memorial", "occasion", "arch", False),
    Source("defeat", "war_memorial", "occasion", "memorial", False),
    Source("centenary", "civic", "occasion", "column", True),
    Source("ruler_death", "civic", "ruler", "mausoleum", True),
    Source("regime", "$KEY$", "year", "column", False),
    Source("space", "civic", "occasion", "obelisk", True),
    Source("petition", "$KEY$", "city", "default", False),
)
# The regime source's petitioners: each regime dedication's approving IG.
REGIME_IG = {"crown": "landowners", "republic": "intelligentsia", "revolution": "trade_unions"}
# Ledger amounts (§2.4): grandeur into the petitioner's IG ledger, legitimacy into the promise ledger.
# A miss costs more than a refusal, so refusing is the way out for a country
# that can't build (owner, 2026-10-05).
REWARDS = {"fulfil": (15, 5), "fulfil_extended": (8, 2.5), "decline": -5, "miss": -15}
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
            call = (f"gm_com_begin = {{ SOURCE = {src.key} DEDICATION = {src.dedication} "
                    f"NAMESAKE = {src.namesake} FORM = {src.form} }}")
            name, body = _effect_containing(self.e, call)
            self.assertIsNotNone(name, call)
            self.assertEqual("gm_com_fix_to_capital = yes" in body, src.fixed, src.key)
            self.assertIn("gm_com_send_offer = yes", body, src.key)

    def test_each_source_has_its_offer_text(self):
        ev = squash(raw_block_at(self.events, r"(?m)^monument_events\.21\s*=\s*\{"))
        L = loc()
        for src in COMMISSION_SOURCES:
            if src.key != "petition":
                self.assertIn(f"var:gm_com_source = flag:{src.key}", ev, src.key)
            self.assertIn(f"monument_events.21.d_{src.key}", L, src.key)
            if src.fixed:
                self.assertIn(f"monument_events.21.d_{src.key}_anywhere", L, src.key)
        for key in ("t", "f", "a", "b"):
            self.assertIn(f"monument_events.21.{key}", L)

    def test_regime_petitioners_are_the_approving_igs(self):
        body = squash(block(self.e, "gm_com_track_regime"))
        for key, ig in REGIME_IG.items():
            self.assertEqual(BY_KEY[key].approve, ig, key)
            self.assertIn(f"gm_com_try_regime = {{ KEY = {key} IG = {ig} }}", body)
        # Revolution first: a Council Republic is also a republic.
        self.assertLess(body.find("flag:revolution"), body.find("flag:crown"))
        self.assertLess(body.find("flag:crown"), body.find("flag:republic"))

    def test_petition_table_is_the_approve_column(self):
        expected = {(d.approve, d.key) for d in DEDICATIONS if d.approve != "dynamic"}
        any_fits = squash(block(read(COM_TRIGGERS), "gm_com_any_petition_fits"))
        listed = set(re.findall(r"gm_com_petition_fits = \{ IG = (\w+) KEY = (\w+) \}", any_fits))
        self.assertEqual(listed, expected)
        offer = squash(block(self.e, "gm_com_offer_petition"))
        picks = set(re.findall(r"trigger = \{ gm_com_petition_fits = \{ IG = (\w+) KEY = (\w+) \} \} "
                               r"gm_com_begin_petition = \{ IG = \1 KEY = \2 \}", offer))
        self.assertEqual(picks, expected)
        counted = set(re.findall(r"gm_com_count_fit = \{ KEY = (\w+) \}", offer))
        forgotten = set(re.findall(r"gm_com_forget_fit = \{ KEY = (\w+) \}", offer))
        self.assertEqual(counted, {k for _, k in expected})
        self.assertEqual(forgotten, counted)

    def test_pacing(self):
        roll = squash(block(self.e, "gm_com_try_petition"))
        self.assertIn("gm_com_can_offer = yes NOT = { has_variable = gm_com_cooldown }", roll)
        self.assertIn("random_list = { 119 = { } 1 = { gm_com_offer_petition = yes } }", roll)
        self.assertIn("set_variable = { name = gm_com_cooldown value = yes months = 60 }",
                      squash(block(self.e, "gm_com_close")))
        can = squash(block(read(COM_TRIGGERS), "gm_com_can_offer"))
        for s_ in ("NOT = { has_variable = gm_com_offered }", "NOT = { has_variable = gm_com_open }"):
            self.assertIn(s_, can)

    def test_only_great_and_major_powers(self):
        """Five levels are 5,000 construction, beyond a minor power (owner, 2026-10-05)."""
        self.assertIn("gm_system_enabled = yes country_rank >= rank_value:major_power",
                      squash(block(read(COM_TRIGGERS), "gm_com_can_offer")))
        # A major power gets ten years, a great power five, fixed on acceptance.
        self.assertEqual(squash(block(read(COM_VALUES), "gm_com_time_months")),
                         "value = 120 if = { limit = { country_rank >= rank_value:great_power } value = 60 }")
        self.assertIn("set_variable = { name = gm_com_months_left value = gm_com_time_months }",
                      squash(block(read(COM_EFFECTS), "gm_com_accept")))
        L = loc()
        self.assertIn("ScriptValue('gm_com_time_months')", L["gm_com_accept_tt"])
        for key, text in L.items():
            if key.startswith("monument_events.21.d_"):
                self.assertNotIn("five years", text, key)

    def test_civil_war_guards(self):
        """A side in a civil war gets no offer, and a revolutionary country never
        writes the founding year its win would put over the nation's."""
        can = squash(block(read(COM_TRIGGERS), "gm_com_can_offer"))
        self.assertIn("NOT = { has_variable = te_cw_role }", can)
        self.assertIn("is_revolutionary = no", can)
        init = squash(block(self.e, "gm_com_init_founded"))
        for s_ in ("NOT = { has_variable = te_cw_role }", "is_revolutionary = no",
                   "NOT = { has_variable = gm_com_start_country }"):
            self.assertIn(s_, init)

    def test_world_pass(self):
        oa = read(ON_ACTIONS)
        self.assertIn("gm_com_world_on_action", squash(block(oa, "on_monthly_pulse_country")))
        self.assertIn("gm_com_world_monthly = yes", squash(block(oa, "gm_com_world_on_action")))
        body = squash(block(self.e, "gm_com_world_monthly"))
        order = ["gm_com_track_ruler", "gm_com_init_founded", "gm_com_track_regime",
                 "gm_com_track_space", "gm_com_track_centenary", "gm_com_try_petition"]
        found = [body.find(f"{t} = yes") for t in order]
        self.assertNotIn(-1, found)
        self.assertEqual(found, sorted(found))

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
        """A commission is offered and stays open only for a dedication the
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
        self.assertIn("name = monument_events.2.a default_option = yes ai_chance = { base = 1 modifier = { trigger = "
                      "{ gm_state_ceremony_answers_commission = yes } factor = 0 } }", squash(ev),
                      "the AI never leaves a commission's monument undedicated")
        answers = squash(block(self.t, "gm_state_ceremony_answers_commission"))
        self.assertIn("this = scope:gm_tmp_com_state", answers, "only the commission's state, if it names one")

    def test_ledger_dispatch_covers_every_ig(self):
        body = squash(block(self.e, "gm_country_ledger_ig_by_flag"))
        scopes = squash(block(self.e, "gm_com_save_scopes"))
        names = squash(block(read(CUSTOM_LOC), "gm_com_ig_name"))
        for ig in IGS:
            self.assertIn(f"IG = {ig} }}", body, ig)
            self.assertIn(f"gm_com_save_ig_scope = {{ IG = {ig} }}", scopes, ig)
            self.assertIn(f"flag:{ig} }} localization_key = ig_{ig}", names, ig)

    def test_the_promise_ledger(self):
        e = read(EFFECTS)
        self.assertIn("gm_init_ledger = { VAR = gm_promise_ledger }", squash(block(e, "gm_init_ledgers")))
        self.assertIn("set_variable = { name = gm_promise_ledger value = 0 }", squash(block(e, "gm_zero_ledgers")))
        self.assertIn("gm_decay = { VAR = gm_promise_ledger RATE = 0.97 }", squash(block(e, "gm_decay_ledgers")))
        self.assertIn("gm_ledger_idle = { VAR = gm_promise_ledger }", squash(block(read(TRIGGERS), "gm_ledgers_idle")))
        self.assertIn("gm_add_national = { NAME = gm_national_promise VAR = gm_promise_ledger }",
                      squash(block(e, "gm_apply_national_modifiers")))
        self.assertIn("remove_modifier = gm_national_promise", squash(block(e, "gm_remove_national_modifiers")))
        ModifierTests().assert_pair("gm_national_promise", "country_legitimacy_base_add", "gm_step_promise", 1)

    def test_rewards_and_costs(self):
        ig, promise = REWARDS["fulfil"]
        ig_x, promise_x = REWARDS["fulfil_extended"]
        fulfil = squash(block(self.e, "gm_com_fulfil"))
        self.assertIn(f"has_variable = gm_com_extended }} gm_country_ledger_ig_by_flag = {{ VAR = gm_com_ig AMOUNT = {ig_x} }} "
                      f"change_variable = {{ name = gm_promise_ledger add = {promise_x} }}", fulfil)
        self.assertIn(f"else = {{ gm_country_ledger_ig_by_flag = {{ VAR = gm_com_ig AMOUNT = {ig} }} "
                      f"change_variable = {{ name = gm_promise_ledger add = {promise} }} }}", fulfil)
        self.assertIn(f"AMOUNT = {REWARDS['decline']} }}", squash(block(self.e, "gm_com_decline")))
        self.assertIn(f"AMOUNT = {REWARDS['miss']} }}", squash(block(self.e, "gm_com_miss")))
        self.assertNotIn("ledger", squash(block(self.e, "gm_com_lapse")), "a lapse costs nothing")
        rewards = read(COM_VALUES)
        self.assertEqual(number(block(rewards, "gm_com_reward_ig"), "value"), ig)
        self.assertEqual(number(block(rewards, "gm_com_reward_promise"), "value"), promise)

    def test_the_offer(self):
        ev = squash(raw_block_at(read(EVENTS), r"(?m)^monument_events\.21\s*=\s*\{"))
        self.assertIn("trigger = { has_variable = gm_com_offered has_variable = gm_com_source }", ev)
        self.assertEqual(ev.count("option = {"), 2)
        self.assertEqual(ev.count("default_option = yes"), 1)
        self.assertIn("name = monument_events.21.a custom_tooltip = { text = gm_com_accept_tt gm_com_accept = yes }", ev)
        # An unanswered offer is declined: the miss would cost more.
        self.assertIn("name = monument_events.21.b default_option = yes custom_tooltip = { text = gm_com_decline_tt "
                      "gm_com_decline = yes }", ev)
        self.assertLess(REWARDS["miss"], REWARDS["decline"], "refusing must be cheaper than missing")
        self.assertIn("modifier = { trigger = { gm_com_ai_declines = yes } factor = 0 }", ev)
        self.assertIn("event_image", ev)
        declines = squash(block(self.t, "gm_com_ai_declines"))
        for s_ in ("is_at_war = yes", "gm_country_hard_times = yes",
                   "construction_queue_government_duration >= 52", "scaled_debt > 0"):
            self.assertIn(s_, declines)

    def test_accept_and_the_ai_queue(self):
        accept = squash(block(self.e, "gm_com_accept"))
        for s_ in ("set_variable = gm_com_open", "set_variable = { name = gm_com_months_left value = gm_com_time_months }",
                   "set_variable = { name = gm_com_baseline value = gm_com_fit_grandeur }",
                   "if = { limit = { is_ai = yes } gm_com_ai_queue = yes }"):
            self.assertIn(s_, accept)
        queue = squash(block(self.e, "gm_com_ai_queue"))
        self.assertIn("while = { limit = { var:gm_com_queued < var:gm_com_target } scope:gm_com_build_state = "
                      "{ start_building_construction = building_grand_monument }", queue)
        self.assertNotIn("create_building", queue, "the AI pays for its levels")

    def test_progress_floors_at_zero(self):
        body = squash(block(read(COM_VALUES), "gm_com_progress"))
        self.assertIn("value = gm_com_fit_grandeur subtract = var:gm_com_baseline min = 0", body)
        counts = squash(block(self.t, "gm_state_com_counts"))
        self.assertIn("gm_state_status_fits = yes", counts, "a contested monument stops counting")

    def test_the_month_and_the_refresh(self):
        monthly = squash(block(self.e, "gm_com_monthly"))
        self.assertLess(monthly.find("gm_com_has_lapsed = yes"), monthly.find("var:gm_com_months_left <= 0"),
                        "a lapse is judged before a miss")
        e = read(EFFECTS)
        country = squash(block(e, "gm_country_monthly"))
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
        self.assertEqual(ev.count("owner = scope:monument_owner"), 6, "every choice but Keep")

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
    "obelisk": ("generic",), "statue": ("generic",), "memorial": ("generic",), "mausoleum": ("generic",),
    "gate": ("generic", "heritage_hebrew", "heritage_sanskrit", "heritage_avestan", "heritage_arabic",
             "heritage_chinese"),
    "hall": ("generic", "heritage_avestan", "heritage_arabic", "heritage_chinese", "heritage_norse"),
    "tower": ("generic", "heritage_gothic"),
    "forum": ("heritage_latin",), "pantheon": ("heritage_greek",), "stoa": ("heritage_greek",),
    "court": ("heritage_hebrew",), "pillar": ("heritage_hebrew", "heritage_sanskrit"),
    "stele": ("heritage_geez",), "memorial_church": ("heritage_slavonic",), "pagoda": ("heritage_chinese",),
    "round_tower": ("heritage_irish",), "high_cross": ("heritage_irish",),
    "pyramid": ("heritage_nahuatl", "heritage_mayan"), "rune_stone": ("heritage_norse",),
    "hall_of_fame": ("heritage_gothic",), "hill_shrine": ("heritage_prussian",), "rock_cut": ("heritage_aramaic",),
}
# skin -> its default form, the first of its row in the plan's table.
DEFAULT_FORM = {"generic": "column", "heritage_latin": "column", "heritage_greek": "pantheon",
                "heritage_hebrew": "gate", "heritage_sanskrit": "pillar", "heritage_geez": "stele",
                "heritage_slavonic": "memorial_church", "heritage_avestan": "gate", "heritage_arabic": "hall",
                "heritage_chinese": "hall", "heritage_irish": "round_tower", "heritage_nahuatl": "pyramid",
                "heritage_mayan": "pyramid", "heritage_norse": "rune_stone", "heritage_gothic": "hall_of_fame",
                "heritage_prussian": "hill_shrine", "heritage_aramaic": "rock_cut"}
BUILDING_FORMS = {"artistic": "opera_house", "naturalist": "gardens", "scientific": "observatory",
                  "industrial": "exhibition_hall", "athletic": "stadium"}
# namesake -> its pattern keys (gm_name_<pattern>_row / _evt).
NAMESAKES = {"city": ("city",), "state": ("state",), "ruler": ("ruler",), "honours": ("honours",),
             "year": ("year",),
             "occasion": ("victory", "defeat", "centenary", "space_orbital", "space_moon_landing")}
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
            obj = "State" if ctx == "row" else "SCOPE.sState('monument_state')"
            for patterns in NAMESAKES.values():
                for pattern in patterns:
                    text = L[f"gm_name_{pattern}_{ctx}"]
                    other = r"(?<![\w.])State\." if ctx == "evt" else r"SCOPE\."
                    self.assertNotRegex(text.replace(obj, ""), other, f"gm_name_{pattern}_{ctx} reads another context")
        ev = squash(raw_block_at(self.events, r"(?m)^monument_events\.25\s*=\s*\{"))
        for namesake in ("city", "state", "ruler", "honours", "year"):
            self.assertIn(f"gm_state_choose_namesake = {{ NAMESAKE = {namesake} }}", ev, namesake)
        self.assertIn("gm_state_choose_commission_name = yes", ev)

    def test_name_events_have_a_default_and_an_image(self):
        for n in (24, 25):
            ev = squash(raw_block_at(self.events, rf"(?m)^monument_events\.{n}\s*=\s*\{{"))
            self.assertEqual(ev.count("default_option = yes"), 1, n)
            self.assertIn(f"name = monument_events.{n}.keep default_option = yes", ev)
            self.assertIn("event_image", ev)
            self.assertIn("save_scope_as = monument_state", ev)

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
        self.assertIn("NOT = { has_variable = gm_unveiled_for_com } OR = { NOT = { has_variable = gm_namesake } "
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
        self.assertIn("b:building_grand_monument ?= { remove_modifier = gm_policy_upkeep_open "
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

    def test_a_copy_is_a_dedication_nothing_recorded(self):
        body = squash(block(self.t, "gm_state_has_copied_dedication"))
        self.assertEqual(body, "gm_state_is_dedicated = yes NOT = { has_variable = gm_seen } "
                               "NOT = { has_variable = gm_ceremony_level } "
                               "NOT = { has_variable = gm_ceremony_pending }")
        reset = squash(block(self.e, "gm_state_reset_copied_dedication"))
        self.assertEqual(reset, "if = { limit = { gm_system_enabled = yes gm_state_has_copied_dedication = yes } "
                                "gm_state_start_ceremony = yes }")

    def test_reset_runs_before_first_sight_and_in_the_level_hook(self):
        refresh = squash(block(self.e, "gm_country_refresh"))
        order = ["set_variable = { name = gm_grandeur value = gm_state_grandeur }",
                 "gm_state_reset_copied_dedication = yes", "gm_state_first_sight = yes",
                 "gm_state_offer_missed_ceremony = yes"]
        positions = [refresh.find(x) for x in order]
        self.assertNotIn(-1, positions, dict(zip(order, positions)))
        self.assertEqual(positions, sorted(positions))
        ev1 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.1\s*=\s*\{")))
        self.assertIn("gm_state_reset_copied_dedication = yes if = { limit = { gm_state_is_dedicated = no } "
                      "gm_state_start_ceremony = yes }", ev1)

    def test_the_answer_is_the_one_switch(self):
        self.assertNotIn("activate_production_method", squash(block(self.e, "gm_state_start_ceremony")))
        ev2 = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.2\s*=\s*\{")))
        self.assertIn("trigger = { gm_system_enabled = yes any_scope_building = { "
                      "is_building_type = building_grand_monument } NOT = { has_variable = gm_seen } }", ev2)
        self.assertNotIn("has_active_production_method = pm_monument_undedicated", ev2)
        immediate = ev2[ev2.find("immediate = {"):ev2.find("option = {")]
        self.assertNotIn("gm_state_undedicate", immediate)
        self.assertIn("hidden_effect = { gm_remove_state_var = { VAR = gm_ceremony_pending } "
                      "gm_state_undedicate = yes }", ev2)
        self.assertEqual(squash(block(self.e, "gm_state_undedicate")),
                         "if = { limit = { NOT = { gm_state_has_pm = { PM = pm_monument_undedicated } } } "
                         "activate_production_method = { building_type = building_grand_monument "
                         "production_method = pm_monument_undedicated } }")
        self.assertTrue(squash(block(self.e, "gm_state_dedicate")).startswith(
            "if = { limit = { NOT = { gm_state_has_pm = { PM = pm_monument_$KEY$ } } } "
            "activate_production_method = { building_type = building_grand_monument "
            "production_method = pm_monument_$KEY$ } }"))
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
                          f"hidden_effect = {{ gm_clear_state = yes }} gm_state_start_ceremony = yes }}", ev3)
        self.assertNotIn("te_debug_monuments.4", text)
        L = loc()
        for k in ("t", "desc", "flavor", "a", "b", "c"):
            self.assertIn(f"te_debug_monuments.3.{k}", L)
        self.assertNotIn("te_debug_monuments.3.d", L)

if __name__ == "__main__":
    unittest.main()
