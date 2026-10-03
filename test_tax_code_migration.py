"""The legislated tax code's migration from vanilla tax laws, levels and taxed goods.

Structural checks on the committed script (no game install needed):

* the migration table in `scripts/generators/gen_tax_code.py` is what vanilla
  1.14.5's five taxation laws set at each native level, read from
  `vanilla_parsed/common/laws.json`, so a vanilla patch that moves a rate (or
  adds a law to the group) fails here; every value is an exact index on the
  instrument grid;
* the generated `te_tax_gen_migrate_rates` holds one branch per (law, level)
  pair, 25 in all, writing all five indices, then a branch for a country that
  already holds the carrier law and one for any other law (zeros, flagged as a
  discrepancy, logged); the goods and provisions parts cover every catalog
  good and every instrument;
* `te_tax_migrate_country` is rule-gated, runs once (guarded on
  `te_tax_migrated`, which it writes last), installs the carrier with
  `activate_law`, hands the month to the next dispatch (`te_tax_last_month =
  -1`) and leaves collection to a later event: it never calls the writer;
* the hooks: after the lobby (when the rules are final) every country gets
  `te_tax.3`; a formed country gets it directly; released and uprising
  countries get it dispatched to `scope:target`; the monthly dispatch migrates
  any rule-on country still unmigrated.

Run: python3 -m unittest test_tax_code_migration -v
"""

import json
import os
import re
import unittest
from decimal import Decimal
from pathlib import Path

from test_tax_code_rule import VANILLA_TAX_LAWS, load, plain
from test_tax_code_scheduler import DATE, MONTH, branches, direct, limit_of
from test_tax_code_state import KEYS, block, catalog, close, gen, read, schema_tokens

ROOT = Path(__file__).resolve().parent

MIGRATION = "common/scripted_effects/te_tax_migration_effects.txt"
STATE = "common/scripted_effects/te_tax_state_effects.txt"
ON_ACTIONS = "common/on_actions/te_tax_on_actions.txt"
EVENTS = "events/te_tax_internal_events.txt"
CIVIL_WAR = "common/scripted_effects/te_tax_civil_war_effects.txt"
COLLECTION = "common/scripted_effects/te_tax_collection_effects.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_generated_effects.txt"
SCHEMA_DOC = "docs/systems/tax_code_schema.md"
VANILLA_LAWS = "vanilla_parsed/common/laws.json"
CARRIER = "law_te_tax_code"
HAND_WRITTEN = (MIGRATION, ON_ACTIONS, EVENTS, STATE)

NATIVE_LEVELS = ("very_low", "low", "medium", "high", "very_high")
STEPS = {"wage": Decimal("0.025"), "div": Decimal("0.025"), "land": Decimal("0.025"),
         "head": Decimal("0.05"), "cons": Decimal("0.05")}

# The brief's mapping table, kept here independently of the generator's copy:
# law -> {instrument: the five rates, very_low .. very_high}; an instrument a law
# leaves out is 0. Verified against the installed 1.14.5 common/laws/01_taxation.txt.
LADDER = "0.15 0.20 0.25 0.30 0.35"
BRIEF_TABLE = {
    "law_consumption_based_taxation": {"cons": LADDER},
    "law_land_based_taxation": {"land": "0.40 0.55 0.70 0.85 1.00", "cons": LADDER},
    "law_per_capita_based_taxation": {
        "wage": "0.05 0.075 0.10 0.125 0.15", "land": "0.20 0.275 0.35 0.425 0.50",
        "head": "0.40 0.55 0.70 0.85 1.00", "cons": LADDER},
    "law_proportional_taxation": {
        "wage": "0.10 0.15 0.20 0.25 0.30", "div": "0.025 0.05 0.10 0.15 0.20", "cons": LADDER},
    "law_graduated_taxation": {
        "wage": "0.10 0.125 0.15 0.175 0.20", "div": "0.10 0.15 0.20 0.25 0.30", "cons": LADDER},
}

# Goods vanilla 1.14.5 taxes by script (read from the installed game,
# 2026-10-02): common/history/countries (33 files, 52 add_taxed_goods calls) and
# belle_epoque_events.8 (automobiles). Migration carries a natively taxed good
# only if it is in the catalog, so all of these must be.
HISTORY_TAXED_GOODS = ("coffee", "grain", "liquor", "luxury_clothes", "luxury_furniture",
                       "opium", "tea", "tobacco", "wine")
EVENT_TAXED_GOODS = ("automobiles",)

SET = re.compile(r"set_variable = \{ name = (\w+) value = ([^}]+?) \}")


def brief_indices():
    """{(law, level): {key: index}} from BRIEF_TABLE."""
    out = {}
    for law, rates in BRIEF_TABLE.items():
        for n, level in enumerate(NATIVE_LEVELS):
            indices = {key: 0 for key in KEYS}
            for key, values in rates.items():
                index, remainder = divmod(Decimal(values.split()[n]), STEPS[key])
                assert remainder == 0, (law, level, key)
                indices[key] = int(index)
            out[(law, level)] = indices
    return out


def vanilla_indices():
    """{(law, level): {key: index}} from vanilla_parsed: every taxation law, every level."""
    with open(ROOT / VANILLA_LAWS, encoding="utf-8") as handle:
        laws = plain(json.load(handle))
    by_modifier = {instrument.modifier: instrument for instrument in gen.INSTRUMENTS}
    out = {}
    for law, body in laws.items():
        if not isinstance(body, dict) or body.get("group") != "lawgroup_taxation":
            continue
        for level in NATIVE_LEVELS:
            indices = {key: 0 for key in KEYS}
            for modifier, value in body.get(f"tax_modifier_{level}", {}).items():
                if modifier not in by_modifier:
                    raise AssertionError(f"{law} {level}: {modifier} is not a code instrument")
                instrument = by_modifier[modifier]
                index, remainder = divmod(Decimal(value), instrument.step)
                if remainder != 0:
                    raise AssertionError(f"{law} {level}: {modifier} = {value} is off the grid")
                indices[instrument.key] = int(index)
            out[(law, level)] = indices
    return out


def generated_branches(text):
    """[(limit, {variable: value})] for each top-level branch of te_tax_gen_migrate_rates."""
    body = block(text, "te_tax_gen_migrate_rates")
    out = []
    # Only the direct children: the branch bodies hold no nested if.
    for kind, nested in branches(body):
        out.append((kind, " ".join(limit_of(nested).split()), dict(SET.findall(direct(nested)))))
    return out


class MappingTableTest(unittest.TestCase):
    def test_vanilla_taxation_group_is_exactly_the_five_mapped_laws(self):
        laws = {law for law, _ in vanilla_indices()}
        self.assertEqual(laws, set(VANILLA_TAX_LAWS))
        self.assertEqual({law for law, _ in gen.MIGRATION}, set(VANILLA_TAX_LAWS))

    def test_brief_table_is_vanilla_1_14_5(self):
        self.assertEqual(brief_indices(), vanilla_indices())

    def test_generator_table_is_vanilla_and_exact_on_the_grid(self):
        generated = {(law, level): indices for law, level, indices in gen.migration_indices()}
        self.assertEqual(len(generated), 25)
        self.assertEqual(generated, vanilla_indices())
        for (law, level), indices in generated.items():
            for instrument in gen.INSTRUMENTS:
                with self.subTest(law=law, level=level, key=instrument.key):
                    self.assertGreaterEqual(indices[instrument.key], 0)
                    self.assertLessEqual(indices[instrument.key], instrument.max_idx)

    def test_every_migrated_rate_is_a_vanilla_value_of_its_instrument(self):
        for law, level, indices in gen.migration_indices():
            for instrument in gen.INSTRUMENTS:
                if indices[instrument.key]:
                    with self.subTest(law=law, level=level, key=instrument.key):
                        self.assertIn(instrument.step * indices[instrument.key], instrument.vanilla)

    def test_the_mod_does_not_change_the_vanilla_tax_rates(self):
        # So the effective rate a country collects before migration is vanilla's.
        for path in sorted((ROOT / "common/laws").glob("*.txt")):
            for key, body in load(path.relative_to(ROOT).as_posix()).items():
                name = key.rpartition(":")[2]
                if name in VANILLA_TAX_LAWS and isinstance(body, dict):
                    with self.subTest(path=path.name, key=key):
                        self.assertFalse([field for field in body if field.startswith("tax_modifier_")])
                        self.assertNotIn("modifier", body)

    def test_installed_game_matches_the_table_when_present(self):
        base = os.environ.get("VIC3_BASE_GAME", "")
        laws = Path(base) / "game/common/laws/01_taxation.txt"
        if not laws.is_file():
            self.skipTest("no Victoria 3 install (VIC3_BASE_GAME)")
        text = laws.read_text(encoding="utf-8-sig")
        for (law, level), indices in brief_indices().items():
            law_body = block(text, law)
            level_body = block(law_body.replace("\n\t", "\n"), f"tax_modifier_{level}")
            found = {key: 0 for key in KEYS}
            for modifier, value in re.findall(r"(tax_\w+_add) = ([\d.]+)", level_body):
                instrument = next(i for i in gen.INSTRUMENTS if i.modifier == modifier)
                found[instrument.key] = int(Decimal(value) / instrument.step)
            with self.subTest(law=law, level=level):
                self.assertEqual(found, indices)

    def test_vanilla_history_taxes_only_catalog_goods(self):
        for good in HISTORY_TAXED_GOODS + EVENT_TAXED_GOODS:
            with self.subTest(good=good):
                self.assertIn(good, catalog())

    def test_installed_history_taxes_only_the_listed_goods_when_present(self):
        base = os.environ.get("VIC3_BASE_GAME", "")
        history = Path(base) / "game/common/history/countries"
        if not history.is_dir():
            self.skipTest("no Victoria 3 install (VIC3_BASE_GAME)")
        taxed = set()
        for path in history.glob("*.txt"):
            taxed |= set(re.findall(r"add_taxed_goods\s*=\s*g:(\w+)",
                                    path.read_text(encoding="utf-8-sig")))
        self.assertEqual(taxed, set(HISTORY_TAXED_GOODS))


class GeneratedRatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(GEN_EFFECTS)
        cls.branches = generated_branches(cls.text)

    def test_one_branch_per_law_and_level_then_the_carrier_then_any_other_law(self):
        kinds = [kind for kind, _, _ in self.branches]
        self.assertEqual(kinds, ["if"] + ["else_if"] * 25 + ["else"])
        expected = vanilla_indices()
        seen = set()
        for _, limit, writes in self.branches[:25]:
            match = re.fullmatch(r"has_law = law_type:(\w+) tax_level = (\w+)", limit)
            self.assertIsNotNone(match, limit)
            pair = (match.group(1), match.group(2))
            seen.add(pair)
            with self.subTest(pair=pair):
                self.assertEqual({key: writes.get(f"te_tax_en_{key}") for key in KEYS},
                                 {key: str(index) for key, index in expected[pair].items()})
                self.assertNotIn("te_tax_migration_discrepancy", writes)
        self.assertEqual(seen, set(expected))

    def test_a_country_already_on_the_carrier_migrates_as_zeros_and_is_flagged(self):
        kind, limit, writes = self.branches[25]
        self.assertEqual(limit, f"has_law = law_type:{CARRIER}")
        self.assertEqual({key: writes.get(f"te_tax_en_{key}") for key in KEYS}, {key: "0" for key in KEYS})
        self.assertEqual(writes["te_tax_migration_discrepancy"], "1")

    def test_any_other_law_migrates_as_zeros_and_is_flagged(self):
        kind, limit, writes = self.branches[26]
        self.assertEqual(limit, "")
        self.assertEqual({key: writes.get(f"te_tax_en_{key}") for key in KEYS}, {key: "0" for key in KEYS})
        self.assertEqual(writes["te_tax_migration_discrepancy"], "1")

    def test_flagged_branches_log_with_the_stamp_and_no_parameters(self):
        body = block(self.text, "te_tax_gen_migrate_rates")
        flagged = [nested for kind, nested in branches(body)][25:]
        lines = []
        for nested in flagged:
            found = re.findall(r'debug_log = "([^"]*)"', direct(nested))
            self.assertEqual(len(found), 1)
            lines += found
        self.assertEqual(len(set(lines)), 2, "the two cases log different lines")
        for line in lines:
            with self.subTest(line=line[:40]):
                self.assertTrue(line.startswith("TE_TAX migration_discrepancy"))
                self.assertIn(MONTH, line)
                self.assertIn(DATE, line)
                self.assertIn("[THIS.GetCountry.GetNameNoFormatting]", line)
                self.assertNotIn("$", line)
                self.assertNotIn("ROOT", line)

    def test_goods_mirror_the_native_list_for_every_catalog_good(self):
        body = block(self.text, "te_tax_gen_migrate_goods")
        for good in catalog():
            with self.subTest(good=good):
                self.assertRegex(
                    body,
                    r"if = \{ limit = \{ has_consumption_tax = g:" + good + r" \} "
                    r"set_variable = \{ name = te_tax_en_g_" + good + r" value = 1 \} \}\s*"
                    r"else = \{ set_variable = \{ name = te_tax_en_g_" + good + r" value = 0 \} \}")
        self.assertEqual(sorted(re.findall(r"has_consumption_tax = g:(\w+)", body)), sorted(catalog()))
        self.assertIn("change_variable = { name = te_tax_xver_goods add = 1 }", body)
        self.assertNotIn("add_taxed_goods", body)
        self.assertNotIn("remove_taxed_goods", body)

    def test_provisions_start_now_when_collected_and_carry_no_sunset(self):
        body = block(self.text, "te_tax_gen_migrate_provisions")
        for key in KEYS:
            en = f"te_tax_en_{key}"
            with self.subTest(key=key):
                self.assertRegex(
                    body,
                    r"if = \{\s*limit = \{ var:" + en + r" > 0 \}\s*"
                    r"set_variable = \{ name = " + en + r"_since value = te_history_month_index \}\s*\}\s*"
                    r"else = \{\s*set_variable = \{ name = " + en + r"_since value = -1 \}\s*\}")
                self.assertIn(f"set_variable = {{ name = {en}_exp value = -1 }}", body)
                self.assertIn(f"set_variable = {{ name = {en}_succ value = -1 }}", body)
                self.assertIn(f"change_variable = {{ name = te_tax_xver_{key} add = 1 }}", body)

    def test_generated_names_are_registered_with_the_generator(self):
        self.assertIn(GEN_EFFECTS, gen.OUTPUTS)
        names = set(re.findall(r"(?m)^(\w+) = \{", self.text))
        for name in ("te_tax_gen_migrate_rates", "te_tax_gen_migrate_goods", "te_tax_gen_migrate_provisions"):
            with self.subTest(name=name):
                self.assertIn(name, names)


class MigrationEffectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(MIGRATION)
        cls.parsed = load(MIGRATION)["te_tax_migrate_country"]
        cls.body = block(cls.text, "te_tax_migrate_country")
        opener = cls.body.find("if = {") + len("if = {") - 1
        outer = cls.body[opener + 1:close(cls.body, opener)]
        cls.limit = " ".join(limit_of(outer).split())
        limit = re.match(r"\s*limit = \{", outer)
        cls.branch = direct(outer[close(outer, limit.end() - 1) + 1:])

    def test_gated_on_the_rule_and_on_not_yet_migrated(self):
        self.assertEqual(set(self.parsed), {"if"})
        self.assertIn("te_tax_code_on = yes", self.limit)
        # NOT = { var:te_tax_migrated >= 1 }, safe when the variable is absent.
        self.assertIn("OR = { NOT = { has_variable = te_tax_migrated } var:te_tax_migrated < 1 }", self.limit)
        self.assertNotRegex(self.limit, r"NOT = \{ te_tax_code_on")

    def test_steps_run_in_order(self):
        order = [
            "te_tax_init_country = yes",
            "set_variable = { name = te_tax_migration_discrepancy value = 0 }",
            "te_tax_gen_migrate_rates = yes",
            "te_tax_gen_migrate_goods = yes",
            "te_tax_gen_migrate_provisions = yes",
            f"activate_law = law_type:{CARRIER}",
            "set_variable = { name = te_tax_last_month value = -1 }",
            "change_variable = { name = te_tax_code_version add = 1 }",
            "te_tax_history_push = { KIND = 5 SLOT = none }",
            "trigger_event = { id = te_tax.4 days = 1 }",
            "set_variable = { name = te_tax_migrated value = 1 }",
        ]
        positions = [self.body.find(step) for step in order]
        for step, position in zip(order, positions):
            with self.subTest(step=step):
                self.assertGreater(position, 0)
        self.assertEqual(positions, sorted(positions))

    def test_the_carrier_is_activated_only_if_not_already_held(self):
        self.assertRegex(
            self.body,
            r"if = \{\s*limit = \{ NOT = \{ has_law = law_type:" + CARRIER + r" \} \}\s*"
            r"activate_law = law_type:" + CARRIER + r"\s*\}")
        self.assertEqual(self.body.count("activate_law"), 1)

    def test_migrated_is_written_once_and_last(self):
        self.assertEqual(self.body.count("name = te_tax_migrated"), 1)
        last_write = self.body[max(self.body.rfind("set_variable"), self.body.rfind("change_variable")):]
        self.assertTrue(last_write.startswith("set_variable = { name = te_tax_migrated value = 1 }"))

    def test_collection_is_left_to_a_later_event(self):
        # activate_law is not assumed visible in the same execution, where the writer
        # could sync against the old law; te_tax.4 (a day later) and the next dispatch sync.
        for effect in ("te_tax_sync_collection", "te_tax_process_month", "te_tax_watchdog_month",
                       "add_amendment", "add_taxed_goods", "remove_taxed_goods", "set_tax_level"):
            with self.subTest(effect=effect):
                self.assertNotIn(effect, self.text)
        self.assertNotRegex(self.text, r"te_tax\.[12]\b")

    def test_the_month_is_handed_to_the_dispatch_not_claimed(self):
        # te_tax_last_month = -1: the next global dispatch processes this country.
        writes = re.findall(r"name = te_tax_last_month value = (\S+) \}", self.body)
        self.assertEqual(writes, ["-1"])
        # The file's other writer, the re-assert (test_tax_code_bypass.py), hands it back too.
        self.assertEqual(set(re.findall(r"name = te_tax_last_month value = (\S+) \}", self.text)), {"-1"})

    def test_logs_each_migration(self):
        lines = re.findall(r'debug_log = "([^"]*)"', self.branch)
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertTrue(line.startswith("TE_TAX migrated"))
        for key in KEYS:
            self.assertIn(f"{key}=[SCOPE.ScriptValue('te_tax_view_en_{key}')|0]", line)
        self.assertIn(MONTH, line)
        self.assertIn(DATE, line)
        self.assertNotIn("$", line)
        self.assertNotIn("ROOT", line)

    def test_never_reads_root_or_removes_a_variable(self):
        self.assertNotRegex(self.text, r"\bROOT\b|\broot\b")
        self.assertNotIn("remove_variable", self.text)


class SchemaTest(unittest.TestCase):
    def test_discrepancy_is_a_schema_token_initialised_to_zero(self):
        country, _ = schema_tokens()
        self.assertEqual(country.get("te_tax_migration_discrepancy"), 0)
        self.assertIn(
            "if = { limit = { NOT = { has_variable = te_tax_migration_discrepancy } } "
            "set_variable = { name = te_tax_migration_discrepancy value = 0 } }",
            block(read(STATE), "te_tax_init_country"))

    def test_doc_describes_the_migration_and_the_balance_decisions(self):
        doc = read(SCHEMA_DOC, strip_comments=False)
        migration = doc.split("\n## Migration\n", 1)[1].split("\n## ", 1)[0]
        for phrase in ("te_tax_migrate_country", "te_tax.3", "te_tax.4", "on_game_started_after_lobby",
                       "on_country_formed", "scope:target", "te_tax_migration_discrepancy",
                       "te_tax_last_month", "kind 5", CARRIER):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, migration)
        balance = doc.split("\n## Balance decisions\n", 1)[1].split("\n## ", 1)[0]
        for phrase in ("state_bureaucracy_population_base_cost_factor_mult",
                       "country_consumption_tax_cost_mult", "Millet System", "People of the Book",
                       "amendment_redemption_payments", "outside the catalog"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, balance)
        for good in HISTORY_TAXED_GOODS:
            with self.subTest(good=good):
                self.assertIn(f"`{good}`", balance)


class EventTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parsed = load(EVENTS)

    def test_migration_and_post_migration_sync_are_hidden_rule_gated_country_events(self):
        for event, effect in (("te_tax.3", "te_tax_migrate_country"), ("te_tax.4", "te_tax_sync_collection")):
            with self.subTest(event=event):
                body = self.parsed[event]
                self.assertEqual(body["type"], "country_event")
                self.assertEqual(body["hidden"], "yes")
                self.assertEqual(body["trigger"], {"te_tax_code_on": "yes"})
                immediate = dict(body["immediate"])
                # te_tax.4 logs each post-migration sync (Task 10), and then refreshes
                # the interest groups' views of the code (Task 13 fix round 1) and
                # takes the economy snapshot (Task 14 fix round 1).
                log = immediate.pop("debug_log", None)
                if event == "te_tax.4":
                    self.assertEqual(immediate.pop("te_tax_refresh_ig_views", None), "yes")
                    self.assertEqual(immediate.pop("te_tax_take_snapshot", None), "yes")
                self.assertEqual(immediate, {effect: "yes"})
                if event == "te_tax.4":
                    self.assertTrue(log.strip('"').startswith("TE_TAX post-migration sync"))
                else:
                    self.assertIsNone(log)

    def test_raisers(self):
        # Both forms, `trigger_event = { id = X }` and the bare `trigger_event = X`.
        raisers = []
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                text = read(path.relative_to(ROOT).as_posix())
                for event in re.findall(r"trigger_event = (?:\{ id = )?(te_tax\.[34])\b", text):
                    raisers.append((path.relative_to(ROOT).as_posix(), event))
        # The civil-war effects migrate an uprising or a released country whose
        # parent has no code (te_tax.3) and sync a copied code (te_tax.4, Task 10).
        # The collection writer defers a second sync in one day to te_tax.4 the
        # next day (te_tax_defer_sync, final review A-I1).
        self.assertEqual(sorted(set(raisers)), sorted([(CIVIL_WAR, "te_tax.3"), (CIVIL_WAR, "te_tax.4"),
                                                       (ON_ACTIONS, "te_tax.3"), (MIGRATION, "te_tax.4"),
                                                       (COLLECTION, "te_tax.4")]))


class HookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parsed = load(ON_ACTIONS)
        cls.text = read(ON_ACTIONS)

    def gated(self, handler):
        effect = self.parsed[handler]["effect"]
        self.assertEqual(set(effect), {"if"})
        self.assertEqual(effect["if"]["limit"], {"te_tax_code_on": "yes"})
        return effect["if"]

    def gated_with_source(self, handler):
        """A gated handler that saves its scope as scope:te_tax_source first."""
        gate = dict(self.gated(handler))
        self.assertEqual(gate.pop("save_scope_as"), "te_tax_source")
        return gate

    def test_game_start_fans_out_after_the_lobby(self):
        # on_game_started fires while players are still in the lobby, where the
        # rule can still change (scripting_best_practices.md, "Convert what
        # history placed after the lobby").
        self.assertEqual(self.parsed["on_game_started_after_lobby"]["on_actions"], ["te_tax_on_game_started"])
        self.assertNotIn("on_game_started", self.parsed)
        gate = self.gated("te_tax_on_game_started")
        self.assertEqual(gate["every_country"], {"trigger_event": {"id": "te_tax.3"}})

    def test_a_formed_country_migrates_itself(self):
        self.assertEqual(self.parsed["on_country_formed"]["on_actions"], ["te_tax_on_country_formed"])
        gate = self.gated("te_tax_on_country_formed")
        self.assertEqual(gate["trigger_event"], {"id": "te_tax.3"})

    def test_released_countries_are_handled_in_the_new_country(self):
        # Copy or migrate (Task 10): te_tax_init_released_country runs in
        # scope:target with the parent saved, and dispatches its events there.
        for hook in ("on_country_released_as_independent", "on_country_released_as_own_subject",
                     "on_country_released_as_overlord_subject", "on_country_released_as_company_subject"):
            with self.subTest(hook=hook):
                self.assertEqual(self.parsed[hook]["on_actions"], ["te_tax_on_country_released"])
        gate = self.gated_with_source("te_tax_on_country_released")
        self.assertEqual(gate["scope:target"], {"te_tax_init_released_country": "yes"})
        self.assertIn("scope:target ?= {", block(self.text, "te_tax_on_country_released"))

    def test_uprisings_are_left_to_the_shared_civil_war_hook(self):
        # The outbreak copy hangs off te_civil_war_on_start (test_tax_code_civil_war.py).
        for hook in ("on_revolution_start", "on_secession_start", "te_tax_on_uprising_start"):
            with self.subTest(hook=hook):
                self.assertNotIn(hook, self.parsed)

    def test_monthly_dispatch_migrates_unmigrated_countries(self):
        fan_outs = self.parsed["te_tax_monthly_dispatch"]["effect"]["if"]["every_country"]
        self.assertEqual(len(fan_outs), 2)
        self.assertEqual(fan_outs[1]["trigger_event"], {"id": "te_tax.3"})
        body = block(self.text, "te_tax_monthly_dispatch")
        heal = body[body.rfind("every_country"):]
        self.assertIn("OR = { NOT = { has_variable = te_tax_migrated } var:te_tax_migrated < 1 }",
                      " ".join(limit_of(heal[heal.find("{") + 1:]).split()))

    def test_every_gate_is_positive(self):
        self.assertNotRegex(self.text, r"NOT = \{\s*te_tax_code_on")
        self.assertNotRegex(read(MIGRATION), r"NOT = \{\s*te_tax_code_on")


class FormatTest(unittest.TestCase):
    def test_files_have_bom_lf_tabs_and_formatter_parity(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import format_paradox_tabs
        finally:
            sys.path.pop(0)
        for path in HAND_WRITTEN:
            raw = (ROOT / path).read_bytes()
            text = raw.decode("utf-8-sig")
            with self.subTest(path=path):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertNotIn(b"\r", raw)
                self.assertNotRegex(text, r"(?m)^ +\S")
                self.assertEqual(format_paradox_tabs.format_text(text), text)


if __name__ == "__main__":
    unittest.main()
