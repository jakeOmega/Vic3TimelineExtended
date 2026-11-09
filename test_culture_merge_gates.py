"""Tests for the culture merges' bespoke gates (owner, 2026-11-09): each merge's own historical precondition.

Files under test:
* scripts/generators/culture_merges_config.py (Gate, the roster's gates, validate)
* common/scripted_triggers/te_culture_merge_gate_triggers.txt (the hand-written te_cm_gate_* triggers)
* the generated triggers, effects, journal entries and loc (scripts/generators/gen_culture_merges.py):
  te_cmg_<m>_gate_ok, the can_start line, the status rows, the latch, the stall of joining and conversion

The gate triggers are run through a small evaluator over a country's laws, entries, variables and tag, and the
generated triggers and effects through test_culture_merge_switch's scenario interpreter.

Run: python3 -m unittest test_culture_merge_gates -v
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import culture_merges_config as cfg  # noqa: E402
import gen_culture_merges as gen  # noqa: E402
from je_multiplier_scope_audit import parse_text  # noqa: E402
from test_culture_merge_census import block, squash, text_of  # noqa: E402
from test_culture_merge_entries import child, definitions  # noqa: E402
from test_culture_merge_switch import Sim, french_world, merge_section_node  # noqa: E402

GATES = ROOT / "common/scripted_triggers/te_culture_merge_gate_triggers.txt"
GEN_TRIGGERS = ROOT / "common/scripted_triggers/te_culture_merges_generated_triggers.txt"
GEN_EFFECTS = ROOT / "common/scripted_effects/te_culture_merges_generated_effects.txt"
JE_FILE = ROOT / "common/journal_entries/te_culture_merges_generated.txt"
GEN_LOC = ROOT / "localization/english/te_culture_merges_generated_l_english.yml"

# The owner's rulings, 2026-11-09: which merge reads which gate, and which optional cultures carry one of their own.
EXPECTED_MERGE_GATES = {
    "german": "te_cm_gate_formed_germany",
    "italian": "te_cm_gate_formed_italy",
    "scandinavian": "te_cm_gate_formed_scandinavia",
    "yugoslav": "te_cm_gate_formed_yugoslavia",
    "czechoslovak": "te_cm_gate_formed_czechoslovakia",
    "platine": "te_cm_gate_formed_la_plata",
    "gran_colombian": "te_cm_gate_formed_gran_colombia",
    "andean": "te_cm_gate_formed_andes",
    "dravidian": "te_cm_gate_formed_dravida_nadu",
    "indonesian": "te_cm_gate_formed_indonesia",
    "japanese": "te_cm_gate_meiji",
    "american": "te_cm_gate_slavery_settled",
    "anglophone": "te_cm_gate_slavery_banned",
    "french": "te_cm_gate_public_schools",
    "chinese": "te_cm_gate_public_schools",
    "filipino": "te_cm_gate_independent",
    "hindustani": "te_cm_gate_independent",
    "arab": "te_cm_gate_independent_schools",
    "east_african": "te_cm_gate_independent_schools",
}
EXPECTED_PART_GATES = {
    ("american", "afro_american"): "te_cm_gate_slavery_banned",
    ("brazilian", "afro_brazilian"): "te_cm_gate_slavery_banned",
}
MILESTONES = {"te_cm_gate_meiji"} | {g for g in EXPECTED_MERGE_GATES.values() if g.startswith("te_cm_gate_formed_")}


def gate_definitions():
    nodes, _ = parse_text(GATES.read_text(encoding="utf-8-sig"), GATES.name)
    return nodes


def loc():
    out = {}
    for line in GEN_LOC.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r'^ (\S+):\d+ "(.*)"$', line)
        if match:
            out[match.group(1)] = match.group(2)
    return out


class Country:
    """What the gate triggers read of one country."""

    def __init__(self, tag="USA", laws=(), entries=(), variables=(), subject=False):
        self.tag, self.laws, self.entries, self.variables, self.subject = tag, set(laws), set(entries), set(variables), subject


def evaluate(nodes, country):
    """The gate triggers' forms: OR/AND/NOT/NOR, has_law(_or_variant), has_journal_entry, has_variable, is_subject and
    c:TAG ?= this (the parser drops the operator). Anything else is a new form this test must learn."""
    return all(_one(n, country) for n in nodes)


def _one(n, country):
    k, v = n.key, n.value
    if k == "OR":
        return any(_one(c, country) for c in n.children)
    if k == "AND":
        return evaluate(n.children, country)
    if k == "NOT":
        return not evaluate(n.children, country)
    if k == "NOR":
        return not any(_one(c, country) for c in n.children)
    if k in ("has_law", "has_law_or_variant"):
        return v.split(":", 1)[1] in country.laws
    if k == "has_journal_entry":
        return v in country.entries
    if k == "has_variable":
        return v in country.variables
    if k == "is_subject":
        return country.subject == (v == "yes")
    if k.startswith("c:") and v == "this":
        return country.tag == k[2:]
    raise KeyError("the gate evaluator does not know %s" % k)


def gate(name, country):
    node = next(n for n in gate_definitions() if n.key == name)
    return evaluate(node.children, country)


class RosterTest(unittest.TestCase):
    def test_each_merge_reads_the_owners_gate(self):
        self.assertEqual({m.key: m.gate.trigger for m in cfg.MERGES if m.gate}, EXPECTED_MERGE_GATES)

    def test_each_optional_culture_with_a_gate_of_its_own(self):
        found = {(m.key, p.cultures[0]): p.gate.trigger for m in cfg.MERGES for p in m.core + m.optional if p.gate}
        self.assertEqual(found, EXPECTED_PART_GATES)

    def test_formations_and_meiji_are_milestones_the_rest_standing(self):
        for merge in cfg.MERGES:
            if merge.gate:
                self.assertEqual(merge.gate.milestone, merge.gate.trigger in MILESTONES, merge.key)

    def test_validate_refuses_a_gate_on_a_core_part_a_milestone_on_a_part_and_a_stray_trigger(self):
        import dataclasses

        cultures = {**json.loads((ROOT / "vanilla_parsed/common/cultures.json").read_text(encoding="utf-8")),
                    cfg.TRAITS_KEY: json.loads((ROOT / "vanilla_parsed/common/discrimination_traits.json").read_text(encoding="utf-8"))}
        self.assertEqual(cfg.validate(cultures), [])
        italian = cfg.merge_by_key("italian")
        others = tuple(m for m in cfg.MERGES if m.key != "italian")
        bad_core = dataclasses.replace(italian, core=(cfg.Part(("north_italian",), gate=cfg.GATE_PUBLIC_SCHOOLS),) + italian.core[1:])
        bad_part = dataclasses.replace(italian, optional=(cfg.Part(("corsican",), gate=cfg.GATE_FORMED_ITALY),))
        bad_name = dataclasses.replace(italian, gate=dataclasses.replace(cfg.GATE_FORMED_ITALY, trigger="formed_italy"))
        for merge, word in ((bad_core, "core part"), (bad_part, "milestone"), (bad_name, "te_cm_gate_")):
            errors = cfg.validate(cultures, others + (merge,))
            self.assertTrue(any(word in e for e in errors), (word, errors))


class TriggerFileTest(unittest.TestCase):
    def test_one_bom_and_every_gate_defined_once_and_used(self):
        raw = GATES.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))
        names = [n.key for n in gate_definitions()]
        self.assertEqual(len(names), len(set(names)))
        used = {m.gate.trigger for m in cfg.MERGES if m.gate} | {p.gate.trigger for m in cfg.MERGES for p in m.optional if p.gate}
        self.assertEqual(set(names), used)

    def test_every_formation_tag_is_a_union_the_game_can_form(self):
        vanilla = json.loads((ROOT / "vanilla_parsed/common/country_formation.json").read_text(encoding="utf-8"))
        mod = set(re.findall(r"^([A-Z0-9]{3}) = \{", (ROOT / "common/country_formation/te_formable_countries.txt").read_text(encoding="utf-8-sig"), re.M))
        # Peru-Bolivia has no formation entry: vanilla's je_peru_bolivia and je_andean_federation name it as a tag.
        entries = (ROOT / "vanilla_parsed/common/journal_entries.json").read_text(encoding="utf-8")
        text = GATES.read_text(encoding="utf-8-sig")
        tags = set(re.findall(r"\bc:([A-Z0-9]{3}) \?= this", text))
        self.assertGreaterEqual(len(tags), 13)
        for tag in tags:
            self.assertTrue(tag in vanilla or tag in mod or '"c:%s"' % tag in entries, tag)

    def test_the_slavery_gate_is_a_settled_position_with_no_civil_war(self):
        cases = [
            ((["law_legacy_slavery"], ["je_acw_countdown"]), False),  # the USA at the start: a house divided
            ((["law_colonial_slavery"], []), False),  # the compromise doesn't count (owner, 2026-11-09)
            ((["law_slavery_banned"], ["je_acw_countdown"]), False),  # banned, but the debate still open
            ((["law_slavery_banned"], []), True),  # banned with the debate over, either way it ended
            ((["law_slavery_banned"], ["je_acw_war"]), False),  # the war is still on
            ((["law_slave_trade"], ["je_acw_countdown"]), True),  # legal in every state
            ((["law_debt_slavery"], []), True),
            ((["law_slave_trade"], ["je_acw_war"]), False),
        ]
        for (laws, entries), expect in cases:
            self.assertEqual(gate("te_cm_gate_slavery_settled", Country(laws=laws, entries=entries)), expect, (laws, entries))
        self.assertTrue(gate("te_cm_gate_slavery_banned", Country(laws=["law_slavery_banned"])))
        for law in ("law_slave_trade", "law_debt_slavery", "law_legacy_slavery", "law_colonial_slavery"):
            self.assertFalse(gate("te_cm_gate_slavery_banned", Country(laws=[law])), law)

    def test_the_meiji_gate_opens_after_the_restoration(self):
        self.assertFalse(gate("te_cm_gate_meiji", Country("JAP", laws=["law_bakufu"])))
        self.assertTrue(gate("te_cm_gate_meiji", Country("JAP", laws=["law_bakufu"], variables=["japan_restoration_complete"])))
        self.assertFalse(gate("te_cm_gate_meiji", Country("JAP", entries=["je_meiji_restoration"])))
        self.assertTrue(gate("te_cm_gate_meiji", Country("JAP")))

    def test_formation_and_independence_gates(self):
        self.assertTrue(gate("te_cm_gate_formed_germany", Country("GER")))
        self.assertTrue(gate("te_cm_gate_formed_germany", Country("HRE")))
        self.assertFalse(gate("te_cm_gate_formed_germany", Country("PRU")))
        self.assertTrue(gate("te_cm_gate_formed_indonesia", Country("NUS")))
        self.assertTrue(gate("te_cm_gate_formed_andes", Country("FND")))
        self.assertFalse(gate("te_cm_gate_independent", Country("PHI", subject=True)))
        self.assertTrue(gate("te_cm_gate_independent", Country("PHI")))
        self.assertFalse(gate("te_cm_gate_independent_schools", Country("EGY")))
        self.assertTrue(gate("te_cm_gate_independent_schools", Country("EGY", laws=["law_public_schools"])))
        self.assertFalse(gate("te_cm_gate_independent_schools", Country("EGY", laws=["law_public_schools"], subject=True)))


class GeneratedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers, cls.effects = text_of(GEN_TRIGGERS), text_of(GEN_EFFECTS)
        cls.loc = loc()

    def test_gate_ok_is_the_trigger_or_for_a_milestone_its_latch(self):
        for merge in cfg.MERGES:
            body = block(self.triggers, "te_cmg_%s_gate_ok" % merge.key)
            if not merge.gate:
                self.assertIsNone(body, merge.key)
                continue
            expect = "%s = yes" % merge.gate.trigger
            if merge.gate.milestone:
                expect = "OR = { has_variable = te_cm_gate_met_%s %s }" % (merge.key, expect)
            self.assertEqual(squash(body), expect, merge.key)

    def test_only_a_milestone_names_a_latch_and_the_census_and_the_start_set_it(self):
        everything = self.triggers + self.effects + JE_FILE.read_text(encoding="utf-8-sig")
        for merge in cfg.MERGES:
            latch = "te_cm_gate_met_%s" % merge.key
            if not gen.milestone_gate(merge):
                self.assertNotIn(latch, everything, merge.key)  # a read of a name nothing sets logs at every load
                continue
            census = squash(block(self.effects, "te_cmg_census_%s_country" % merge.key))
            self.assertTrue(census.startswith(
                "if = { limit = { NOT = { has_variable = %s } %s = yes } set_variable = { name = %s value = 1 } }"
                % (latch, merge.gate.trigger, latch)), merge.key)
            self.assertIn("set_variable = { name = %s value = 1 }" % latch, squash(block(self.effects, "te_cmg_start_%s" % merge.key)))

    def test_a_standing_gate_guards_joining_and_conversion_and_a_milestone_neither(self):
        yearly = definitions(GEN_EFFECTS)["te_cmg_yearly_country"]
        for merge in cfg.MERGES:
            join_ready = squash(block(self.effects, "te_cmg_%s_join_ready" % merge.key))
            limit = squash(" ".join(_lines(child(merge_section_node("te_cmg_yearly_country", merge.key), "if"))))
            reads = "te_cmg_%s_gate_ok = yes" % merge.key
            self.assertEqual(reads in join_ready, gen.standing_gate(merge), merge.key)
            self.assertEqual("scope:te_cm_starter = { %s }" % reads in limit, gen.standing_gate(merge), merge.key)
        self.assertIsNotNone(yearly)

    def test_every_gate_has_its_line_its_row_and_its_reason(self):
        for merge in cfg.MERGES:
            key = merge.key
            if not merge.gate:
                self.assertNotIn("te_cmg_%s_gate_tt" % key, self.loc)
                continue
            self.assertEqual(self.loc["te_cmg_%s_gate_tt" % key], gen._sentence(merge.gate.clause))
            self.assertEqual(self.loc["je_te_cm_%s_status_gate" % key], merge.gate.why)
            self.assertIn("The merge begins only once %s." % merge.gate.clause, self.loc["je_te_cm_%s_reason" % key])
            self.assertEqual("je_te_cm_%s_status_paused" % key in self.loc, gen.standing_gate(merge), key)
        for (key, culture), _ in EXPECTED_PART_GATES.items():
            part = next(p for p in cfg.merge_by_key(key).optional if culture in p.cultures)
            self.assertIn(part.gate.clause, self.loc["je_te_cm_%s_reason" % key])

    def test_the_texts_hold_no_digit_and_no_script(self):
        gates = {m.gate for m in cfg.MERGES if m.gate} | {p.gate for m in cfg.MERGES for p in m.optional if p.gate}
        for g in gates:
            for text in (g.clause, g.why):
                plain = re.sub(r"\$[\w.\-]+\$", "", text)
                self.assertNotRegex(plain, r"\d|_|=|\bte_cm", text)


def _lines(node):
    """The squashed text of a parsed node's limit, for a substring test."""
    out = []

    def walk(n):
        if n.children:
            out.append("%s = {" % n.key)
            for c in n.children:
                walk(c)
            out.append("}")
        else:
            out.append("%s = %s" % (n.key, n.value))

    walk(child(node, "limit"))
    return out


class ScenarioTest(unittest.TestCase):
    """The generated effects run against a small world (test_culture_merge_switch's interpreter)."""

    def converted(self, sim, key):
        sim.run([merge_section_node("te_cmg_yearly_country", key)])
        return {a["CULTURE"] for k, a in sim.calls if k == "te_cm_convert_part"}

    def test_a_complete_merge_converts_no_late_culture_while_its_standing_gate_fails(self):
        for gates, expect in (({}, {"catalan"}), ({"te_cm_gate_public_schools": set()}, set())):
            sim = french_world(gates=gates)
            sim.globals["te_cm_joined_french_catalan"] = 1
            sim.this = "FRA"
            self.assertEqual(self.converted(sim, "french"), expect, gates)

    def test_no_culture_joins_while_a_standing_gate_fails(self):
        for gates, expect in (({}, True), ({"te_cm_gate_public_schools": set()}, False)):
            sim = french_world(gates=gates)
            sim.this = "FRA"
            sim.run(definitions(GEN_EFFECTS)["te_cmg_french_join_ready"].children)
            self.assertEqual("te_cm_joined_french_catalan" in sim.globals, expect, gates)

    def american_world(self, gates):
        g = {"te_cm_state_american": 1, "te_cm_starter_american": "USA"}
        for culture in ("yankee", "dixie", "afro_american"):
            g["te_cm_joined_american_%s" % culture] = 1
        cvars = {"USA": {"te_cm_started_american": 1, "te_cm_sol_ok_american": 1, "te_cm_ok_american_yankee": 1,
                         "te_cm_ok_american_dixie": 1, "te_cm_ok_american_afro_american": 1,
                         "te_cm_sol_ok_american_afro_american": 1}}
        sim = Sim(globals=g, cvars=cvars, alive={"USA": True}, primary={"USA": {"yankee", "cm_american"}},
                  stubs={"te_cm_system_enabled": True, "te_cm_in_sphere": True}, techs={1, 2}, gates=gates)
        sim.this = "USA"
        return sim

    def test_slavery_holds_back_the_whole_american_merge_and_afro_american_pops_alone(self):
        for gates, expect in (
            ({}, {"yankee", "dixie", "afro_american"}),
            ({"te_cm_gate_slavery_settled": set()}, set()),  # back to a house divided: nothing converts
            ({"te_cm_gate_slavery_banned": set()}, {"yankee", "dixie"}),  # settled with slavery legal everywhere
        ):
            self.assertEqual(self.converted(self.american_world(gates), "american"), expect, gates)

    def test_a_milestone_stays_met_once_latched(self):
        trig = definitions(GEN_TRIGGERS)["te_cmg_german_gate_ok"]
        closed = {"te_cm_gate_formed_germany": set()}
        self.assertTrue(Sim().holds(trig.children, this="GER"))
        self.assertFalse(Sim(gates=closed).holds(trig.children, this="EUN"))
        self.assertTrue(Sim(gates=closed, cvars={"EUN": {"te_cm_gate_met_german": 1}}).holds(trig.children, this="EUN"))
        # The census latches it while the formation holds.
        latch = definitions(GEN_EFFECTS)["te_cmg_census_german_country"].children[0]
        for gates, expect in (({}, True), (closed, False)):
            sim = Sim(gates=gates)
            sim.this = "GER"
            sim.run([latch])
            self.assertEqual("te_cm_gate_met_german" in sim.cvars.get("GER", {}), expect)


if __name__ == "__main__":
    unittest.main()
