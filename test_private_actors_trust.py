"""Private Actors, the trust and the foundation (docs/systems/mod_systems/private_actors.md § The Trust; plan Task 4).

What is pinned here:

- every firm type with a sector has its three generated modifiers (te_pa_cartel_<type>, te_pa_cartel_secret_<type>,
  te_pa_found_<type>), the two cartel ones carrying exactly the type's building types' throughput, and every
  throughput type they name is registered (vanilla's, the mod's, or the generated definitions);
- the teardown removes the cartel and foundation families (generated remove-all effects it reaches), and every
  generated add_modifier names a modifier those remove;
- te_pa_spend_funds is the only effect that lowers te_pa_funds for a spend (plan Review Focus 4);
- te_pa_act's lists name only verbs that have both a te_pa_can_ trigger and a te_pa_do_ effect;
- each modifier has one refresh site: the cartel's in the quarter, the foundation's in the state pulse;
- a secret holding shows on no row: the sync copies the strength the state knows of;
- the trust's ledger verbs sit in Task 4a's block, 20-29, and the self-check has its play-test row.

Run: .venv/bin/python -m pytest test_private_actors_trust.py -q
"""

import json
import re
import sys
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import gen_private_actors as gen  # noqa: E402

TRUST_EFFECTS = "common/scripted_effects/te_pa_trust_effects.txt"
CORE_EFFECTS = "common/scripted_effects/te_pa_core_effects.txt"
ON_ACTIONS = "common/on_actions/te_pa_on_actions.txt"
GOAL_CODES = {"inputs": 1, "market": 2, "abroad": 3, "law": 4, "dominance": 5, "labor": 6, "tech": 7, "survival": 8}


def parse(rel) -> dict:
    p = ParadoxFileParser()
    text = (ROOT / rel).read_text(encoding="utf-8-sig")
    return p.parse_object(p.tokenize("{" + text + "}"))[0]


def items(node):
    for part in node if isinstance(node, list) else [node]:
        if isinstance(part, dict):
            for key, (_op, value) in part.items():
                yield key, value


def walk(node):
    for key, value in items(node):
        yield key, value
        if isinstance(value, (dict, list)):
            yield from walk(value)


def te_pa(folder: str) -> dict:
    out = {}
    for path in sorted((ROOT / folder).glob("te_pa_*.txt")):
        out.update(parse(path.relative_to(ROOT)))
    return out


_PLAN = None


def plan():
    global _PLAN
    if _PLAN is None:
        _PLAN = gen.build_plan(gen.load_state())
    return _PLAN


def registered() -> set:
    names = set(json.loads((ROOT / gen.VANILLA_MODIFIER_TYPES).read_text(encoding="utf-8")))
    for path in (ROOT / gen.MODIFIER_TYPES_DIR).glob("*.txt"):
        names.update(re.findall(r"^(?:[A-Z_]+:)?(\w+)\s*=\s*\{", path.read_text(encoding="utf-8-sig"), re.M))
    return names


class GeneratedModifiersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modifiers = parse(gen.STATIC_MODIFIERS_OUT)
        cls.sectors = plan().sectors

    def fields(self, name) -> dict:
        return {k: v for k, v in items(self.modifiers[name][1]) if k != "icon"}

    def test_every_type_with_a_sector_has_its_three(self):
        self.assertGreater(len(self.sectors), 300)
        for s in self.sectors:
            for prefix in (gen.CARTEL_PREFIX, gen.CARTEL_SECRET_PREFIX, gen.FOUNDATION_PREFIX):
                with self.subTest(modifier=prefix + s.company):
                    self.assertIn(prefix + s.company, self.modifiers)
        expected = {p + s.company for s in self.sectors
                    for p in (gen.CARTEL_PREFIX, gen.CARTEL_SECRET_PREFIX, gen.FOUNDATION_PREFIX)}
        self.assertEqual(set(self.modifiers), expected, "a generated modifier for no sector")

    def test_cartels_carry_exactly_the_types_building_types(self):
        cut = -gen.cfg.NUMBERS["cartel_cut"]
        for s in self.sectors:
            want = {f"{b}_throughput_add" for b in s.buildings}
            for name in (gen.CARTEL_PREFIX + s.company, gen.CARTEL_SECRET_PREFIX + s.company):
                with self.subTest(modifier=name):
                    fields = self.fields(name)
                    throughput = {k for k in fields if k.endswith("_throughput_add")}
                    self.assertEqual(throughput, want)
                    for k in throughput:
                        self.assertAlmostEqual(float(fields[k]), cut)
                    self.assertEqual(set(fields) - throughput, {"country_wealth_concentration_economy_add"})

    def test_foundations_carry_education_and_mortality(self):
        for s in self.sectors:
            fields = self.fields(gen.FOUNDATION_PREFIX + s.company)
            self.assertEqual(float(fields["state_education_access_add"]), gen.cfg.NUMBERS["found_education"])
            self.assertEqual(float(fields["state_mortality_mult"]), -gen.cfg.NUMBERS["found_mortality"])
            self.assertEqual(set(fields), {"state_education_access_add", "state_mortality_mult"})

    def test_every_type_they_name_is_registered(self):
        names = registered()
        used = {k for name in self.modifiers for k in self.fields(name)}
        self.assertEqual(used - names, set(), "an unregistered type is dropped at load")

    def test_the_generated_definitions_are_only_the_missing_ones(self):
        generated = set(parse(gen.MODIFIER_TYPES_OUT))
        self.assertTrue(generated)
        elsewhere = gen.registered_types(ROOT)
        self.assertEqual(generated & elsewhere, set(), "registered twice")
        for name in generated:
            self.assertRegex(name, r"^building_\w+_throughput_add$")

    def test_names_name_the_firm_and_secret_ones_name_none(self):
        loc = (ROOT / gen.LOC_OUT).read_text(encoding="utf-8-sig")
        for s in self.sectors[:40]:
            with self.subTest(company=s.company):
                self.assertIn(f' {gen.CARTEL_PREFIX}{s.company}:0 "${s.company}$ $te_pa_holding_cartel$"', loc)
                self.assertIn(f' {gen.CARTEL_SECRET_PREFIX}{s.company}:0 "$te_pa_cartel_secret$"', loc)
                self.assertIn(f' {gen.FOUNDATION_PREFIX}{s.company}:0 "${s.company}$ $te_pa_holding_found$"', loc)

    def test_organize_loc_files_them_in_the_generated_file(self):
        import organize_loc
        for key in (gen.CARTEL_PREFIX + "company_basf", gen.CARTEL_SECRET_PREFIX + "company_basf_desc",
                    gen.FOUNDATION_PREFIX + "company_basf"):
            self.assertEqual(organize_loc.categorize_key(key, set()), "PA_GENERATED")
        for name in sorted(parse(gen.MODIFIER_TYPES_OUT))[:5]:
            self.assertEqual(organize_loc.categorize_key(name, set()), "PA_GENERATED")
            self.assertEqual(organize_loc.categorize_key(name + "_desc", set()), "PA_GENERATED")
        self.assertEqual(organize_loc.categorize_key("te_pa_cartel_secret", set()), "MISCELLANEOUS")
        self.assertEqual(organize_loc.categorize_key("building_textile_mills_throughput_add", set()), "BUILDINGS")


class TeardownTest(unittest.TestCase):
    """The rule switched off: the trust's families go (plan § Rules; test_private_actors.TeardownTest holds the
    hand-written add_modifiers, this the generated ones)."""

    @classmethod
    def setUpClass(cls):
        cls.effects = {**te_pa("common/scripted_effects"), **parse(gen.EFFECTS_OUT)}
        cls.modifiers = set(parse(gen.STATIC_MODIFIERS_OUT))

    def reached(self, start: str) -> tuple[set, set]:
        removed, seen = set(), set()

        def visit(name):
            if name in seen or name not in self.effects:
                return
            seen.add(name)
            for key, value in walk(self.effects[name][1]):
                if key == "remove_modifier":
                    removed.add(value)
                elif key in self.effects:
                    visit(key)

        visit(start)
        return removed, seen

    def test_the_teardown_removes_both_families(self):
        removed, seen = self.reached("te_pa_teardown")
        self.assertIn("te_pa_trust_teardown", seen)
        self.assertIn("te_pa_gen_cartel_remove_all", seen)
        self.assertIn("te_pa_gen_found_remove_all", seen)
        self.assertEqual(self.modifiers - removed, set(), "a trust modifier the teardown leaves")

    def test_every_generated_add_is_a_removed_modifier(self):
        added = {dict(items(v))["name"] for k, v in walk(parse(gen.EFFECTS_OUT)) if k == "add_modifier"}
        self.assertTrue(added)
        self.assertLessEqual(added, self.modifiers)

    def test_the_foundations_teardown_walks_the_index_not_every_state(self):
        body = self.effects["te_pa_trust_teardown"][1]
        lists = [dict(items(v)).get("variable") for k, v in walk(body) if k == "every_in_global_list"]
        self.assertEqual(lists, ["te_pa_found_states"])
        self.assertFalse(any(k in ("every_state", "every_scope_state") for k, _ in walk(body)))

    def test_the_clear_takes_the_cartel_off(self):
        _removed, seen = self.reached("te_pa_clear_firm")
        self.assertIn("te_pa_trust_clear", seen)
        self.assertIn("te_pa_gen_cartel_remove", seen)


class SpendTest(unittest.TestCase):
    """Money from nowhere or money twice (plan Review Focus 4): te_pa_funds goes down for a spend in one place."""

    ALLOWED = {
        # (effect, value written): the record's start, the quarter's accrual (adds, or holds the claim to its cap
        # as the pool shrinks; nothing moves), and the spend
        ("te_pa_make_record", "te_pa_funds_starting"),
        ("te_pa_accrue", "te_pa_funds_after_quarter"),
        ("te_pa_spend_funds", "te_pa_funds_after_spend"),
    }

    def test_te_pa_spend_funds_is_the_only_spender(self):
        found = set()
        for path in sorted((ROOT / "common").rglob("*.txt")):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            if "te_pa_funds" not in text:
                continue
            for top, (_op, body) in parse(path.relative_to(ROOT)).items():
                for key, value in walk(body):
                    if key in ("set_variable", "change_variable") and isinstance(value, (dict, list)):
                        fields = dict(items(value))
                        if fields.get("name") == "te_pa_funds":
                            found.add((top, fields.get("value", "change_variable")))
        self.assertEqual(found, self.ALLOWED)

    def test_the_accrual_never_subtracts(self):
        values = parse("common/script_values/te_pa_core_values.txt")
        keys = {k for k, _ in walk(values["te_pa_funds_after_quarter"][1])}
        self.assertNotIn("subtract", keys)

    def test_the_spend_takes_the_pool_capped(self):
        values = parse("common/script_values/te_pa_trust_values.txt")
        hit = dict(items(values["te_pa_spend_pool_hit"][1]))
        self.assertEqual(hit["max"], "0")
        self.assertIn("investment_pool", str(hit["min"]))
        body = te_pa("common/scripted_effects")["te_pa_spend_funds"][1]
        self.assertIn(("add_investment_pool", "te_pa_spend_pool_hit"), list(walk(body)))

    def test_every_spend_passes_a_named_value(self):
        for path in sorted((ROOT / "common").rglob("te_pa_*.txt")):
            for m in re.finditer(r"te_pa_spend_funds = \{ AMOUNT = (\S+) \}", path.read_text(encoding="utf-8-sig")):
                self.assertRegex(m.group(1), r"^te_pa_\w+_value$", path.name)


class DispatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = te_pa("common/scripted_effects")
        cls.triggers = {**te_pa("common/scripted_triggers")}

    def test_te_pa_act_dispatches_on_the_goal(self):
        body = self.effects["te_pa_act"][1]
        calls = [k for k, _ in walk(body) if k.startswith("te_pa_act_")]
        self.assertTrue(calls)
        for call in calls:
            self.assertIn(call, self.effects)
            self.assertIn(call.removeprefix("te_pa_act_"), GOAL_CODES)

    def test_every_listed_verb_has_a_trigger_and_an_effect(self):
        lists = [name for name in self.effects if name.startswith("te_pa_act_")]
        self.assertEqual(set(lists), {"te_pa_act_inputs", "te_pa_act_market", "te_pa_act_dominance"})
        verbs = set()
        for name in lists + ["te_pa_act"]:
            for key, value in walk(self.effects[name][1]):
                if key.startswith("te_pa_can_"):
                    verbs.add(key.removeprefix("te_pa_can_"))
                elif key.startswith("te_pa_do_"):
                    verbs.add(key.removeprefix("te_pa_do_"))
        self.assertGreaterEqual(verbs, {"stall", "form_cartel", "capture_reg", "expand", "press_cartel", "endow"})
        for verb in sorted(verbs):
            with self.subTest(verb=verb):
                self.assertIn(f"te_pa_can_{verb}", self.triggers)
                self.assertIn(f"te_pa_do_{verb}", self.effects)

    def test_each_branch_pairs_its_trigger_with_its_effect(self):
        for name in ("te_pa_act_inputs", "te_pa_act_market", "te_pa_act_dominance"):
            for key, value in items(self.effects[name][1]):
                self.assertIn(key, ("if", "else_if"))
                branch = dict(items(value))
                limit = [k for k, _ in items(branch["limit"])]
                done = [k for k in branch if k != "limit"]
                self.assertEqual(len(limit), 1)
                self.assertEqual(done, [limit[0].replace("te_pa_can_", "te_pa_do_")], name)

    def test_the_turn_acts_after_choosing(self):
        turn = [k for k, _ in items(te_pa("common/scripted_effects")["te_pa_turn"][1])]
        self.assertLess(turn.index("te_pa_choose_goal"), turn.index("te_pa_act"))
        self.assertLess(turn.index("te_pa_act"), turn.index("te_pa_expose_rolls"))


class RefreshSiteTest(unittest.TestCase):
    """One refresh site a modifier (the dynamic-modifier pattern): the cartel's from the quarter, the foundation's
    from the state pulse, where ROOT is the state its multiplier resolves against."""

    def callers(self, callee: str) -> set:
        out = set()
        for folder in ("common/scripted_effects", "common/on_actions", "common/scripted_guis"):
            for path in sorted((ROOT / folder).glob("*.txt")):
                text = path.read_text(encoding="utf-8-sig", errors="replace")
                if callee not in text:
                    continue
                for top, (_op, body) in parse(path.relative_to(ROOT)).items():
                    if any(k == callee for k, _ in walk(body)):
                        out.add(top)
        return out

    def test_the_cartel_is_applied_from_the_quarter(self):
        self.assertEqual(self.callers("te_pa_gen_cartel_apply"), {"te_pa_cartel_quarter"})
        self.assertEqual(self.callers("te_pa_cartel_quarter"), {"te_pa_trust_quarter"})
        self.assertEqual(self.callers("te_pa_trust_quarter"), {"te_pa_quarter"})

    def test_the_foundation_is_applied_from_the_state_pulse(self):
        self.assertEqual(self.callers("te_pa_gen_found_apply"), {"te_pa_state_monthly"})
        self.assertEqual(self.callers("te_pa_state_monthly"), {"te_pa_state_monthly_on_action"})
        text = (ROOT / ON_ACTIONS).read_text(encoding="utf-8-sig")
        hook = text[text.index("on_monthly_pulse_state = {"):]
        self.assertIn("te_pa_state_monthly_on_action", hook[:hook.index("}")])

    def test_the_state_pulse_waits_for_the_rule(self):
        body = te_pa("common/scripted_effects")["te_pa_state_monthly"][1]
        first = dict(items(body))["if"]
        self.assertIn(("te_pa_on", "yes"), list(items(dict(items(first))["limit"])))


class SecrecyTest(unittest.TestCase):
    """§ 4.6: secrecy is against the state, and the player is the state."""

    def test_the_row_copies_what_the_state_knows(self):
        sync = te_pa("common/scripted_effects")["te_pa_row_sync"][1]
        copies = {dict(items(v))["TO"]: dict(items(v))["FROM"] for k, v in walk(sync) if k == "te_pa_copy_from"}
        self.assertEqual(copies["te_pa_r_cartel"], "te_pa_cartel_shown")
        self.assertEqual(copies["te_pa_r_reg"], "te_pa_reg_shown")
        values = parse("common/script_values/te_pa_trust_values.txt")
        for name in ("te_pa_cartel_shown_value", "te_pa_reg_shown_value"):
            self.assertIn("_known ?= 1", (ROOT / "common/script_values/te_pa_trust_values.txt").read_text(
                encoding="utf-8-sig").split(f"{name} = {{")[1].split("\n}")[0])
            self.assertIn(name, values)

    def test_a_secret_cartel_forms_with_an_unknown_author(self):
        text = (ROOT / TRUST_EFFECTS).read_text(encoding="utf-8-sig")
        cartel = text.split("\nte_pa_ledger_cartel = {")[1].split("\n}")[0]
        self.assertIn("var:te_pa_cartel_known ?= 1", cartel)
        self.assertIn("KNOWN = 0", cartel)
        self.assertIn("VERB = 25 KNOWN = 0", text)  # the regulator

    def test_the_ai_restrains_only_a_cartel_it_knows_of(self):
        posture = (ROOT / CORE_EFFECTS).read_text(encoding="utf-8-sig").split("te_pa_ai_posture = {")[1]
        posture = posture.split("\n}")[0]
        self.assertIn("te_pa_holds_known_cartel = yes", posture)
        self.assertNotIn("te_pa_holds_cartel = yes", posture)


class LedgerAndChecksTest(unittest.TestCase):
    def test_the_trust_codes_sit_in_task_4as_block(self):
        text = (ROOT / TRUST_EFFECTS).read_text(encoding="utf-8-sig")
        verbs = {int(v) for v in re.findall(r"\bVERB = (\d+)", text)}
        self.assertEqual(verbs, set(range(20, 30)))

    def test_the_self_check_has_its_row(self):
        playtest = (ROOT / "docs/testing/private-actors-playtest.md").read_text(encoding="utf-8")
        self.assertIn("| `cartel_rents` (probe 2)", playtest)
        debug = (ROOT / "common/scripted_effects/te_pa_debug_effects.txt").read_text(encoding="utf-8-sig")
        self.assertIn("TE_SELF_CHECK OK cartel_rents", debug)
        self.assertIn("TE_SELF_CHECK BROKEN cartel_rents", debug)


if __name__ == "__main__":
    unittest.main()
