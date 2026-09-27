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
        self.assert_pair("gm_national_vanity", "country_legitimacy_base_add", "gm_step_vanity", -3)
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


if __name__ == "__main__":
    unittest.main()
