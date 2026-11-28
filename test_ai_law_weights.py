"""AI law weights (#1877 traps 3 and 4): the laws that raise literacy at the innovation cap, the mod's groups halved.

- Trap 3. common/laws/ai_literacy_law_injections.txt restates vanilla's whole ai_enact_weight_modifier on Public
  Schools, Compulsory Primary School and Restricted Child Labor and adds the mod's weight on one top-level `add`, a
  key vanilla's field lacks there, so the field reads vanilla's terms plus the add whether the engine replaces it,
  merges in new keys or appends steps. The weight is vanilla's own No Schools figure, 500, while research sits at
  the innovation cap (te_ai_research_at_innovation_cap), and for Restricted Child Labor only from Child Labor Allowed.
- Trap 4. Every law in one of the mod's own law groups (derived from common/law_groups, none of them vanilla's) ends
  its ai_enact_weight_modifier with `multiply = te_ai_mod_law_group_factor` and `add = te_ai_mod_law_group_offset`:
  half its own terms and 100 off the engine's base while the country holds No Workers' Rights, Child Labor Allowed
  or No Health System. A law in a vanilla group carries neither.
- TE_SELF_CHECK ai_literacy_laws (common/on_actions/te_ai_literacy_laws_selfcheck_on_actions.txt): its counts,
  thresholds and lines, its gates held to vanilla's, and its play-test row.

The numbers and why: docs/systems/mod_systems/ai.md § AI Law Weights: Literacy and the Mod's Groups.
"""

import json
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
LAW_FILES = sorted((ROOT / "common/laws").glob("*.txt"))
LAW_GROUP_FILES = sorted((ROOT / "common/law_groups").glob("*.txt"))
INJECTIONS = ROOT / "common/laws/ai_literacy_law_injections.txt"
TRIGGERS = ROOT / "common/scripted_triggers/te_ai_law_weight_triggers.txt"
VALUES = ROOT / "common/script_values/te_ai_law_weight_values.txt"
BUILD_PASS_VALUES = ROOT / "common/script_values/te_ai_build_pass_values.txt"
CONSTRUCTION_VALUES = ROOT / "common/script_values/te_construction_market_ai_values.txt"
SELFCHECK = ROOT / "common/on_actions/te_ai_literacy_laws_selfcheck_on_actions.txt"
SELFCHECK_VALUES = ROOT / "common/script_values/te_ai_literacy_laws_selfcheck_values.txt"
SELFCHECK_TRIGGERS = ROOT / "common/scripted_triggers/te_ai_literacy_laws_selfcheck_triggers.txt"
VANILLA_LAWS = ROOT / "vanilla_parsed/common/laws.json"
VANILLA_LAW_GROUPS = ROOT / "vanilla_parsed/common/law_groups.json"
PLAYTEST = ROOT / "docs/testing/ai-economy-playtest.md"
SYSTEM_DOC = ROOT / "docs/systems/mod_systems/ai.md"

HALVING = [("multiply", "te_ai_mod_law_group_factor"), ("add", "te_ai_mod_law_group_offset")]
UNREFORMED = {
    "law_no_workers_rights": "lawgroup_labor_rights",
    "law_child_labor_allowed": "lawgroup_childrens_rights",
    "law_no_health_system": "lawgroup_health_system",
}
# The three laws trap 3 weighs, the mod's add on each, and the self-check's gate for each.
TARGETS = {
    "law_public_schools": ("te_ai_literacy_law_weight", "te_alw_public_schools_open"),
    "law_compulsory_primary_school": ("te_ai_literacy_law_weight", "te_alw_compulsory_primary_open"),
    "law_restricted_child_labor": ("te_ai_end_child_labor_weight", "te_alw_end_child_labor_open"),
}
# Vanilla 1.15.2's add to a schools law while a country has No Schools: the size trap 3 takes.
VANILLA_NO_SCHOOLS_ADD = 500


# ---- parsing --------------------------------------------------------------------------------------------------

def entries(node):
    """(key, op, value) of a parsed block, in source order (a block with a repeated key parses as a list)."""
    for part in node if isinstance(node, list) else [node]:
        if isinstance(part, dict):
            for key, (op, value) in part.items():
                yield key, op, value


def parse_text(text):
    parser = ParadoxFileParser()
    return parser.parse_object(parser.tokenize("{" + text + "}"))[0]


def parse(path):
    return parse_text(path.read_text(encoding="utf-8-sig"))


def field(block, key):
    return next((value for k, _, value in entries(block) if k == key), None)


def plain(node):
    """A parsed block as nested [key, op, value] lists, in source order."""
    if isinstance(node, (dict, list)):
        return [[key, op, plain(value)] for key, op, value in entries(node)]
    return node


def unwrap(node):
    """A vanilla_parsed node without its ["=", value] wrapper."""
    return node[1] if isinstance(node, list) and len(node) == 2 and node[0] in ("=", "?=") else node


def vanilla_decoded():
    """The snapshot's laws in the parser's own form (what ModState starts from)."""
    import vanilla_parsed
    return vanilla_parsed.decode(json.loads(VANILLA_LAWS.read_text()))


def injected():
    """{law: the INJECT's normalized block} of ai_literacy_law_injections.txt."""
    parser = ParadoxFileParser()
    parser.parse_file(str(INJECTIONS), apply_directives=False)
    return {name.split(":", 1)[1]: value[1] for name, value in parser.data.items()}


def mod_law_groups():
    groups = set()
    for path in LAW_GROUP_FILES:
        for name, _, _ in entries(parse(path)):
            groups.add(name.split(":")[-1])
    return groups


def law_entries():
    """(written key, file name, block) of every law entry in the mod's law files."""
    for path in LAW_FILES:
        for name, _, block in entries(parse(path)):
            if isinstance(block, (dict, list)):
                yield name, path.name, block


def vanilla_laws():
    return {name: unwrap(entry) for name, entry in json.loads(VANILLA_LAWS.read_text()).items()}


def strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def block_text(text, name):
    """The body of the first `name = { ... }` in comment-stripped text (a directive prefix allowed)."""
    m = re.search(r"(?:^|\s)(?:[A-Z_]+:)?" + re.escape(name) + r"\s*=\s*\{", text)
    if m is None:
        return None
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def norm(text):
    return " ".join(text.replace("{", " { ").replace("}", " } ").split())


# ---- trap 4: the mod's own law groups ---------------------------------------------------------------------------

class ModLawGroupHalving(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups = mod_law_groups()
        cls.laws = list(law_entries())

    def test_the_groups_are_the_mods_own(self):
        vanilla = set(json.loads(VANILLA_LAW_GROUPS.read_text()))
        self.assertGreaterEqual(len(self.groups), 30)
        self.assertFalse(self.groups & vanilla, "a vanilla group in common/law_groups")
        self.assertTrue(set(UNREFORMED.values()) <= vanilla)

    def test_every_law_in_a_mod_group_ends_its_weight_with_the_halving(self):
        found = 0
        for name, file, block in self.laws:
            group = field(block, "group")
            if group not in self.groups:
                continue
            found += 1
            with self.subTest(law=name, file=file):
                self.assertNotIn(":", name, "a mod group's law is the mod's own definition")
                weight = field(block, "ai_enact_weight_modifier")
                self.assertIsNotNone(weight, "no ai_enact_weight_modifier")
                top = [(k, v) for k, _, v in entries(weight)]
                self.assertEqual(top[-2:], HALVING, "the field's last two lines")
                for key, value in HALVING:
                    self.assertEqual(top.count((key, value)), 1)
        self.assertGreaterEqual(found, 150)

    def test_every_group_has_a_law(self):
        held = {field(block, "group") for _, _, block in self.laws}
        self.assertEqual(self.groups - held, set())

    def test_no_law_outside_a_mod_group_carries_it(self):
        for path in LAW_FILES:
            text = strip_comments(path.read_text(encoding="utf-8-sig"))
            for name, _, block in entries(parse(path)):
                if not isinstance(block, (dict, list)) or field(block, "group") in self.groups:
                    continue
                with self.subTest(law=name):
                    weight = field(block, "ai_enact_weight_modifier")
                    self.assertFalse(weight and any((k, v) in HALVING for k, _, v in entries(weight)))
            for key in ("te_ai_mod_law_group_factor", "te_ai_mod_law_group_offset"):
                self.assertEqual(text.count(key), sum(
                    1 for _, _, block in entries(parse(path))
                    if isinstance(block, (dict, list)) and field(block, "group") in self.groups), (path.name, key))

    def test_the_values(self):
        text = strip_comments(VALUES.read_text(encoding="utf-8-sig"))
        self.assertRegex(text, r"(?m)^TE_AI_MOD_LAW_GROUP_FACTOR = 0\.5$")
        self.assertRegex(text, r"(?m)^TE_AI_MOD_LAW_GROUP_CUT = -100$")
        self.assertEqual(norm(block_text(text, "te_ai_mod_law_group_factor")),
                         "value = 1 if = { limit = { te_ai_social_laws_unreformed = yes } "
                         "value = TE_AI_MOD_LAW_GROUP_FACTOR }")
        self.assertEqual(norm(block_text(text, "te_ai_mod_law_group_offset")),
                         "value = 0 if = { limit = { te_ai_social_laws_unreformed = yes } "
                         "value = TE_AI_MOD_LAW_GROUP_CUT }")

    def test_the_trigger_names_the_three_unreformed_laws(self):
        text = strip_comments(TRIGGERS.read_text(encoding="utf-8-sig"))
        body = norm(block_text(text, "te_ai_social_laws_unreformed"))
        self.assertEqual(body, "OR = { " + " ".join(
            f"has_law_or_variant = law_type:{law}" for law in UNREFORMED) + " }")
        vanilla = vanilla_laws()
        for law, group in UNREFORMED.items():
            with self.subTest(law=law):
                self.assertEqual(unwrap(vanilla[law]["group"]), group)


# ---- trap 3: the laws that raise literacy -----------------------------------------------------------------------

class LiteracyLawWeights(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vanilla = vanilla_laws()
        cls.injects = {name.split(":", 1)[1]: block for name, _, block in entries(parse(INJECTIONS))}
        cls.values = strip_comments(VALUES.read_text(encoding="utf-8-sig"))

    def test_the_file_injects_the_three_laws_and_only_their_weight(self):
        raw = [name for name, _, _ in entries(parse(INJECTIONS))]
        self.assertEqual(raw, [f"INJECT:{law}" for law in TARGETS])
        for law, block in self.injects.items():
            with self.subTest(law=law):
                self.assertEqual([k for k, _, _ in entries(block)], ["ai_enact_weight_modifier"])

    def test_each_restates_vanillas_field_and_adds_one_line(self):
        decoded, normalized = vanilla_decoded(), injected()
        for law, (add, _) in TARGETS.items():
            with self.subTest(law=law):
                written = [(k, v) for k, _, v in entries(field(self.injects[law], "ai_enact_weight_modifier"))]
                self.assertEqual(written[0], ("value", "0"))
                self.assertEqual(written[-1], ("add", add), "the add is the field's last line")
                vanilla = decoded[law][1]["ai_enact_weight_modifier"][1]
                self.assertNotIn("add", vanilla, "vanilla's field has a top-level add: it no longer stays single")
                restated = dict(normalized[law]["ai_enact_weight_modifier"][1])
                self.assertEqual(restated.pop("add"), ("=", add))
                self.assertEqual(restated, vanilla, "the restated lines are vanilla's")

    def test_no_other_file_sets_their_weight(self):
        # A later INJECT or a REPLACE of the field would take this one's place.
        for name, file, block in law_entries():
            law = name.split(":")[-1]
            if law in TARGETS and file != INJECTIONS.name:
                with self.subTest(law=name, file=file):
                    self.assertIsNone(field(block, "ai_enact_weight_modifier"))
                    self.assertFalse(name.startswith("REPLACE"), "a REPLACE would drop the INJECT")

    def test_sorts_before_the_other_ai_mods_file(self):
        # Kuromi's AI (Workshop) INJECTs Public Schools' field from kai_education_system.txt; the later INJECT
        # replaces the field, so its weight stands with both mods loaded (ai.md).
        self.assertLess(INJECTIONS.name, "kai_education_system.txt")

    def test_the_weight_is_vanillas_no_schools_figure(self):
        branches = vanilla_decoded()["law_public_schools"][1]["ai_enact_weight_modifier"][1]["if"]
        no_schools = [b[1] for b in branches if "law_type:law_no_schools" in repr(b[1]["limit"])]
        self.assertEqual(len(no_schools), 1)
        self.assertEqual(no_schools[0]["add"], ("=", str(VANILLA_NO_SCHOOLS_ADD)))
        self.assertRegex(self.values, r"(?m)^TE_AI_LITERACY_LAW_WEIGHT = %d$" % VANILLA_NO_SCHOOLS_ADD)

    def test_schools_at_the_cap_child_labour_only_from_child_labor_allowed(self):
        self.assertEqual(norm(block_text(self.values, "te_ai_literacy_law_weight")),
                         "value = 0 if = { limit = { te_ai_research_at_innovation_cap = yes } "
                         "value = TE_AI_LITERACY_LAW_WEIGHT }")
        self.assertEqual(norm(block_text(self.values, "te_ai_end_child_labor_weight")),
                         "value = 0 if = { limit = { te_ai_research_at_innovation_cap = yes "
                         "has_law_or_variant = law_type:law_child_labor_allowed } value = TE_AI_LITERACY_LAW_WEIGHT }")

    def test_the_cap_is_the_build_passs_share_with_a_cap_read(self):
        triggers = strip_comments(TRIGGERS.read_text(encoding="utf-8-sig"))
        self.assertEqual(norm(block_text(triggers, "te_ai_research_at_innovation_cap")),
                         "te_ai_build_pass_innovation_cap > 0 "
                         "te_ai_build_pass_innovation_share >= TE_AI_BUILD_PASS_INNOVATION_SHARE")
        build = strip_comments(BUILD_PASS_VALUES.read_text(encoding="utf-8-sig"))
        self.assertIn("te_ai_build_pass_innovation_cap = { value = modifier:country_weekly_innovation_max_add }", build)
        self.assertIn("value = country_innovation divide = te_ai_build_pass_innovation_cap",
                      norm(block_text(build, "te_ai_build_pass_innovation_share")))
        self.assertRegex(CONSTRUCTION_VALUES.read_text(encoding="utf-8-sig"),
                         r"(?m)^TE_AI_BUILD_PASS_INNOVATION_SHARE = 0\.9$")

    def test_the_parser_reads_vanillas_terms_plus_the_add(self):
        # paradox_file_parser replaces an INJECTed field that has a `value =` line, as the engine did for an interest
        # group's script-value field and a party's join_weight (scripting_best_practices.md), so the mod-state server
        # shows each law's field as vanilla's lines plus the add, and the rest of the law as vanilla's.
        decoded, normalized = vanilla_decoded(), injected()
        parser = ParadoxFileParser()
        parser.data = vanilla_decoded()
        parser.parse_file(str(INJECTIONS))
        for law in TARGETS:
            with self.subTest(law=law):
                merged = parser.data[law][1]
                self.assertEqual(merged["ai_enact_weight_modifier"], normalized[law]["ai_enact_weight_modifier"])
                rest = {k: v for k, v in merged.items() if k != "ai_enact_weight_modifier"}
                self.assertEqual(rest, {k: v for k, v in decoded[law][1].items() if k != "ai_enact_weight_modifier"})


# ---- the self-check ---------------------------------------------------------------------------------------------

class LiteracyLawSelfCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = SELFCHECK.read_text(encoding="utf-8-sig")
        cls.text = strip_comments(cls.raw)
        cls.action = block_text(cls.text, "te_alw_selfcheck_law_started")
        cls.trigger = block_text(cls.action, "trigger")
        cls.effect = block_text(cls.action, "effect")
        cls.values = strip_comments(SELFCHECK_VALUES.read_text(encoding="utf-8-sig"))
        cls.triggers = strip_comments(SELFCHECK_TRIGGERS.read_text(encoding="utf-8-sig"))
        cls.verdict = cls.effect[cls.effect.index("global_var:te_alw_starts >= te_alw_chk_sample"):]

    def test_counts_ai_law_starts_once_a_game(self):
        self.assertRegex(self.text, r"on_law_enactment_started\s*=\s*\{\s*on_actions\s*=\s*\{\s*"
                                    r"te_alw_selfcheck_law_started\s*\}\s*\}")
        self.assertEqual(norm(self.trigger), "NOT = { has_global_variable = te_alw_checked } is_ai = yes "
                                             "NOT = { is_country_type = decentralized }")
        # the latch: the first thing the verdict sets
        self.assertTrue(norm(self.verdict).startswith(
            "global_var:te_alw_starts >= te_alw_chk_sample } set_global_variable = te_alw_checked"))

    def test_every_counter_starts_at_zero(self):
        counters = set(re.findall(r"change_global_variable = \{ name = (\w+) add = 1 \}", self.effect))
        self.assertGreaterEqual(len(counters), 11)
        for name in counters:
            with self.subTest(counter=name):
                self.assertIn(f"set_global_variable = {{ name = {name} value = 0 }}", self.effect)

    def test_the_cohort_and_the_control(self):
        self.assertEqual(norm(block_text(self.triggers, "te_alw_cohort")),
                         "te_ai_research_at_innovation_cap = yes te_alw_clean = yes te_alw_a_target_open = yes")
        self.assertEqual(norm(block_text(self.triggers, "te_alw_control")),
                         "te_ai_build_pass_innovation_cap > 0 te_ai_research_at_innovation_cap = no "
                         "te_alw_clean = yes te_alw_a_target_open = yes")
        clean = norm(block_text(self.triggers, "te_alw_clean"))
        self.assertIn("NOT = { has_law_or_variant = law_type:law_no_schools }", clean)
        for law in TARGETS:
            self.assertIn(f"NOT = {{ has_law_commitment = law_type:{law} }}", clean)
        # the cohort's starts and the control's are counted apart
        cohort = norm(self.effect[self.effect.index("te_alw_cohort = yes"):self.effect.index("te_alw_control = yes")])
        self.assertIn("name = te_alw_starts add = 1", cohort)
        self.assertNotIn("te_alw_ctrl", cohort)

    def test_the_gates_are_vanillas(self):
        # Each law's gate: its unlocking technology, not held, and each law vanilla's disallowing_laws names not held.
        vanilla = vanilla_laws()
        for law, (_, gate) in TARGETS.items():
            with self.subTest(law=law):
                body = norm(block_text(self.triggers, gate))
                for tech in unwrap(vanilla[law]["unlocking_technologies"]):
                    self.assertIn(f"has_technology_researched = {tech}", body)
                for other in unwrap(vanilla[law].get("disallowing_laws", ["=", []])):
                    self.assertIn(f"NOT = {{ has_law = law_type:{other} }}", body)
                if law == "law_restricted_child_labor":
                    self.assertIn("has_law_or_variant = law_type:law_child_labor_allowed", body)
                else:
                    self.assertIn(f"NOT = {{ has_law_or_variant = law_type:{law} }}", body)
        hit = norm(block_text(self.triggers, "te_alw_started_end_child_labor"))
        self.assertEqual(hit, "is_enacting_law = law_type:law_restricted_child_labor "
                              "has_law_or_variant = law_type:law_child_labor_allowed")

    def test_the_mod_group_trigger_names_one_law_of_each_group(self):
        groups = mod_law_groups()
        group_of = {name: field(block, "group") for name, _, block in law_entries() if ":" not in name}
        named = re.findall(r"is_same_law_group_as = law_type:(\w+)", block_text(self.triggers,
                                                                               "te_alw_started_mod_group_law"))
        self.assertEqual(sorted(group_of[law] for law in named), sorted(groups))

    def test_the_verdicts(self):
        lines = re.findall(r'debug_log = "(TE_SELF_CHECK (\w+) ai_literacy_laws[^"]*)"', self.verdict)
        self.assertEqual([kind for _, kind in lines], ["START", "OK", "BROKEN", "NO_VERDICT"])
        self.assertNotIn("[", lines[0][0], "START is a plain marker")
        ok = norm(block_text(self.verdict, "if"))
        self.assertTrue(ok.startswith("limit = { te_alw_chk_share >= 0.20 OR = { global_var:te_alw_ctrl_starts < "
                                      "te_alw_chk_control_sample te_alw_chk_share >= te_alw_chk_ctrl_share_twice } }"))
        self.assertIn("else_if = { limit = { te_alw_chk_share < 0.10 }", norm(self.verdict))
        self.assertRegex(self.values, r"(?m)^te_alw_chk_sample = 40$")
        self.assertRegex(self.values, r"(?m)^te_alw_chk_control_sample = 20$")
        self.assertIn("TE_INFO ai_mod_law_groups unreformed=", self.verdict)
        for line, kind in lines[1:]:
            with self.subTest(verdict=kind):
                # log_triage.py shows a line's first 400 characters: the figures and the reading fit
                shown = re.sub(r"\[[^\]]*\]", "0000", line)[:400]
                self.assertIn("date=0000 (", shown)
                # the agendas that want Public Schools, apart: BROKEN's two causes read from them
                self.assertIn("pro=[SCOPE.ScriptValue('te_alw_chk_pro_hits_g')|0]/"
                              "[SCOPE.ScriptValue('te_alw_chk_pro_starts_g')|0]", line)
        self.assertIn("not grounds for the REPLACE alone", lines[2][0])
        self.assertEqual(norm(block_text(self.triggers, "te_alw_progressive_agenda")),
                         "OR = { has_strategy = ai_strategy_progressive_agenda "
                         "has_strategy = ai_strategy_egalitarian_agenda }")

    def test_every_value_the_lines_read_is_defined(self):
        used = set(re.findall(r"te_alw_chk_\w+", self.effect))
        self.assertTrue(used)
        for name in sorted(used):
            with self.subTest(value=name):
                self.assertRegex(self.values, r"(?m)^%s\s*=" % name)

    def test_every_trigger_it_uses_is_defined(self):
        used = set(re.findall(r"\b(te_alw_\w+) = (?:yes|no)\b", self.effect + self.triggers))
        defined = set(re.findall(r"(?m)^(te_alw_\w+)\s*=\s*\{", self.triggers))
        self.assertTrue(used)
        self.assertEqual(used - defined, set())

    def test_the_play_test_list_and_the_doc_carry_it(self):
        playtest = PLAYTEST.read_text(encoding="utf-8")
        self.assertIn("TE_SELF_CHECK … ai_literacy_laws", playtest)
        self.assertIn("REPLACE", playtest[playtest.index("TE_SELF_CHECK … ai_literacy_laws"):])
        doc = SYSTEM_DOC.read_text(encoding="utf-8")
        self.assertIn("## AI Law Weights: Literacy and the Mod's Groups", doc)
        self.assertIn("ai_literacy_laws", doc)


if __name__ == "__main__":
    unittest.main()
