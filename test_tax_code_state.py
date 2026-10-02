"""The legislated tax code's canonical state, initialisation and collection writer.

Structural checks on the committed script (no game install needed):

* the schema in docs/systems/tax_code_schema.md is what `te_tax_init_country`
  writes, token by token and sentinel by sentinel, every write guarded so an
  existing value is never overwritten;
* no file of this layer removes a schema token (a civil war's winner would
  then inherit the loser's value, CLAUDE.md "Top gotchas");
* `te_tax_sync_collection` is gated on the rule and the carrier law and calls
  every generated per-instrument sync, the goods sync, the relief sync and the
  tax-level pin; nothing else in the mod writes those native settings;
* the generated per-instrument syncs and their amendment-scope triggers name
  exactly the generated amendments, one to one, in the forms the tax probe
  used in game (`type = amendment_type:X`, `has_amendment`, `add_amendment`);
* the consumption-goods catalog, the relief modifiers and the guarded
  display values.

Run: python3 -m unittest test_tax_code_state -v
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from test_tax_code_rule import load, plain

ROOT = Path(__file__).resolve().parent
GENERATOR = ROOT / "scripts" / "generators" / "gen_tax_code.py"

_spec = importlib.util.spec_from_file_location("gen_tax_code", GENERATOR)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

KEYS = ("wage", "div", "land", "head", "cons")
PERCENT_KEYS = ("wage", "div", "cons")

STATE = "common/scripted_effects/te_tax_state_effects.txt"
COLLECTION = "common/scripted_effects/te_tax_collection_effects.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_generated_effects.txt"
GEN_TRIGGERS = "common/scripted_triggers/te_tax_generated_triggers.txt"
GEN_VALUES = "common/script_values/te_tax_generated_values.txt"
DISPLAY = "common/script_values/te_tax_display_values.txt"
MODIFIERS = "common/static_modifiers/te_tax_modifiers.txt"
AMENDMENTS = "common/amendments/te_tax_amendments_generated.txt"
SCHEMA_DOC = "docs/systems/tax_code_schema.md"
TAX_LOC = "localization/english/te_tax_l_english.yml"

# Every script file this layer owns (hand-written and generated).
LAYER_FILES = (STATE, COLLECTION, GEN_EFFECTS, GEN_TRIGGERS, GEN_VALUES, DISPLAY, MODIFIERS)
HAND_WRITTEN = (STATE, COLLECTION, DISPLAY, MODIFIERS)
GENERATED = (GEN_EFFECTS, GEN_TRIGGERS, GEN_VALUES)

RELIEF_MODIFIERS = {
    "te_tax_relief_ag_1": ("building_group_bg_agriculture_tax_mult", Decimal("-0.25")),
    "te_tax_relief_ag_2": ("building_group_bg_agriculture_tax_mult", Decimal("-0.5")),
    "te_tax_relief_region_1": ("state_tax_collection_mult", Decimal("-0.25")),
    "te_tax_relief_region_2": ("state_tax_collection_mult", Decimal("-0.5")),
}

# The single-line guarded write the init effects use for every token.
GUARDED_WRITE = re.compile(
    r"if = \{ limit = \{ NOT = \{ has_variable = (\w+) \} \} "
    r"set_variable = \{ name = (\w+) value = (-?\d+) \} \}"
)


def read(path, strip_comments=True):
    text = (ROOT / path).read_text(encoding="utf-8-sig")
    return re.sub(r"#[^\n]*", "", text) if strip_comments else text


def close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def block(text, name):
    """The body of the top-level `name = { ... }` definition."""
    match = re.search(r"(?m)^" + re.escape(name) + r" = \{", text)
    if match is None:
        raise AssertionError(f"{name} is not defined")
    return text[match.end():close(text, match.end() - 1)]


def top_level_names(text):
    return re.findall(r"(?m)^(\w+) = \{", text)


def amendment_family(key):
    names = re.findall(r"(?m)^(amendment_te_tax_(\w+?)_(\d+)) = \{", read(AMENDMENTS))
    return {name for name, k, _ in names if k == key}


def catalog():
    return gen.consumption_catalog()


def schema_tokens():
    """{token: sentinel} from the schema table, <key> and <good> expanded.

    Sentinel "-" (te_tax_schema, written last with the schema version) is None.
    State-scope rows ("state var") are returned separately.
    """
    country, state = {}, {}
    goods = catalog()
    text = read(SCHEMA_DOC, strip_comments=False)
    table = text.split("\n## Schema\n", 1)[1].split("\n## ", 1)[0]
    for line in table.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or not cells[0] or "`te_tax_" not in cells[0]:
            continue
        names, _, sentinel = cells
        value = None if sentinel in ("—", "-") else int(sentinel)
        target = state if names.startswith("state var") else country
        for name in re.findall(r"`(te_tax_[\w<>]+)`", names):
            if "<key>" in name:
                expanded = [name.replace("<key>", key) for key in KEYS]
            elif "<good>" in name:
                expanded = [name.replace("<good>", good) for good in goods]
            else:
                expanded = [name]
            for token in expanded:
                target[token] = value
    return country, state


class SchemaDocTest(unittest.TestCase):
    def test_schema_table_lists_the_brief_rows(self):
        country, state = schema_tokens()
        for token in ("te_tax_schema", "te_tax_migrated", "te_tax_code_version",
                      "te_tax_last_month", "te_tax_next_month", "te_tax_en_agrel",
                      "te_tax_en_regrel", "te_tax_pver_goods", "te_tax_xver_goods",
                      "te_tax_pver_relief", "te_tax_xver_relief"):
            self.assertIn(token, country)
        for key in KEYS:
            for suffix, sentinel in (("", 0), ("_since", -1), ("_exp", -1), ("_succ", -1)):
                self.assertEqual(country[f"te_tax_en_{key}{suffix}"], sentinel)
            self.assertEqual(country[f"te_tax_pver_{key}"], 0)
            self.assertEqual(country[f"te_tax_xver_{key}"], 0)
        self.assertEqual(country["te_tax_last_month"], -1)
        self.assertEqual(country["te_tax_next_month"], -1)
        self.assertIsNone(country["te_tax_schema"])
        self.assertEqual(state, {"te_tax_relief_state": 0})

    def test_doc_lists_the_consumption_catalog_exactly(self):
        text = read(SCHEMA_DOC, strip_comments=False)
        section = text.split("## Consumption goods catalog", 1)[1].split("\n## ", 1)[0]
        lines = [line for line in section.splitlines() if line.startswith("**Catalog")]
        self.assertEqual(len(lines), 1, "one **Catalog** line in the catalog section")
        listed = re.findall(r"`(\w+)`", lines[0])
        self.assertEqual(listed, list(catalog()))
        self.assertIn(f"({len(catalog())} goods)", lines[0])
        outside = [line for line in section.splitlines() if line.startswith("**Outside the catalog")]
        self.assertEqual(len(outside), 1, "one **Outside the catalog** line")
        self.assertEqual(re.findall(r"`(\w+)`", outside[0]), list(gen.stray_goods()))
        self.assertIn(f"({len(gen.stray_goods())} goods", outside[0])


class InitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = read(STATE)
        cls.generated = read(GEN_EFFECTS)
        cls.init = block(cls.state, "te_tax_init_country")

    def guarded_writes(self, body):
        writes = {}
        for guard, name, value in GUARDED_WRITE.findall(body):
            self.assertEqual(guard, name, f"{name} is guarded by a different variable")
            self.assertNotIn(name, writes, f"{name} written twice")
            writes[name] = int(value)
        return writes

    def test_init_is_gated_on_the_rule(self):
        parsed = load(STATE)["te_tax_init_country"]
        self.assertEqual(set(parsed), {"if"})
        self.assertEqual(parsed["if"]["limit"], {"te_tax_code_on": "yes"})

    def test_init_calls_the_generated_instrument_and_goods_inits(self):
        self.assertIn("te_tax_gen_init_instruments = yes", self.init)
        self.assertIn("te_tax_gen_init_goods = yes", self.init)

    def test_every_country_token_is_written_with_its_sentinel_if_absent(self):
        writes = self.guarded_writes(self.init)
        for name in ("te_tax_gen_init_instruments", "te_tax_gen_init_goods"):
            for token, value in self.guarded_writes(block(self.generated, name)).items():
                self.assertNotIn(token, writes, f"{token} written by two init effects")
                writes[token] = value
        country, _ = schema_tokens()
        expected = {token: value for token, value in country.items() if value is not None}
        expected_schema = writes.pop("te_tax_schema", None)
        self.assertEqual(expected_schema, 1, "te_tax_schema must be set to 1, guarded")
        self.assertEqual(writes, expected)

    def test_every_variable_write_in_the_init_effects_is_guarded(self):
        for body in (self.init, block(self.generated, "te_tax_gen_init_instruments"),
                     block(self.generated, "te_tax_gen_init_goods")):
            self.assertEqual(body.count("set_variable"), len(GUARDED_WRITE.findall(body)))
            self.assertNotIn("change_variable", body)

    def test_schema_version_is_written_last(self):
        last_write = self.init[self.init.rfind("set_variable"):]
        self.assertTrue(last_write.startswith("set_variable = { name = te_tax_schema value = 1 }"))
        self.assertEqual(self.init.count("name = te_tax_schema"), 1)
        self.assertGreater(self.init.find("name = te_tax_schema"),
                           self.init.find("te_tax_gen_init_goods = yes"))


class NoTokenRemovalTest(unittest.TestCase):
    def test_no_layer_file_removes_a_schema_token(self):
        country, state = schema_tokens()
        tokens = set(country) | set(state)
        pattern = re.compile(r"remove_variable\s*=\s*(?:\{[^}]*?name\s*=\s*)?([\w$]+)")
        for path in LAYER_FILES:
            text = read(path)
            for name in pattern.findall(text):
                with self.subTest(path=path, name=name):
                    self.assertNotIn(name, tokens)
                    self.assertNotIn("$", name, "a parameterised remove_variable could hit a token")


class WriterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(COLLECTION)
        cls.writer = block(cls.text, "te_tax_sync_collection")
        cls.parsed = load(COLLECTION)

    def test_writer_is_one_gated_block(self):
        writer = self.parsed["te_tax_sync_collection"]
        self.assertEqual(set(writer), {"if", "else_if"})
        limit = writer["if"]["limit"]
        self.assertEqual(limit.get("te_tax_code_on"), "yes")
        self.assertEqual(limit.get("has_law"), "law_type:law_te_tax_code")
        self.assertEqual(limit.get("has_variable"), "te_tax_schema")

    def test_a_carrier_holder_without_tokens_is_logged_not_synced(self):
        skip = self.parsed["te_tax_sync_collection"]["else_if"]
        self.assertEqual(set(skip), {"limit", "debug_log"})
        self.assertEqual(skip["limit"], {
            "te_tax_code_on": "yes",
            "has_law": "law_type:law_te_tax_code",
            "NOT": {"has_variable": "te_tax_schema"},
        })
        self.assertIn("[THIS.", skip["debug_log"])

    def test_writer_calls_every_part(self):
        for key in KEYS:
            self.assertIn(f"te_tax_gen_sync_{key} = yes", self.writer)
        for call in ("te_tax_gen_sync_goods = yes", "te_tax_sync_relief = yes",
                     "te_tax_pick_sponsor = yes", "save_scope_as = te_tax_country",
                     "te_tax_init_country = yes"):
            self.assertIn(call, self.writer)

    def test_scope_and_sponsor_are_saved_before_any_sync(self):
        first_sync = self.writer.find("te_tax_gen_sync_")
        self.assertLess(self.writer.find("save_scope_as = te_tax_country"), first_sync)
        self.assertLess(self.writer.find("te_tax_pick_sponsor = yes"), first_sync)

    def test_amendment_syncs_run_only_with_a_sponsor(self):
        guarded = re.search(r"if = \{\s*limit = \{ any_interest_group = \{ always = yes \} \}", self.writer)
        self.assertIsNotNone(guarded)
        body = self.writer[guarded.end():close(self.writer, guarded.end() - 1)]
        for key in KEYS:
            self.assertIn(f"te_tax_gen_sync_{key} = yes", body)

    def test_tax_level_is_pinned_to_medium_without_churn(self):
        self.assertRegex(
            self.writer,
            r"if = \{ limit = \{ NOT = \{ tax_level = medium \} \} set_tax_level = medium \}",
        )
        self.assertEqual(self.writer.count("set_tax_level"), 1)

    def test_sponsor_prefers_a_ruling_group_then_the_strongest(self):
        sponsor = self.parsed["te_tax_pick_sponsor"]
        self.assertEqual(set(sponsor), {"if", "else"})
        self.assertEqual(sponsor["if"]["limit"], {"any_interest_group": {"is_in_government": "yes"}})
        ruling = sponsor["if"]["random_interest_group"]
        self.assertEqual(ruling["limit"], {"is_in_government": "yes"})
        self.assertEqual(ruling["save_scope_as"], "te_tax_sponsor")
        strongest = sponsor["else"]["ordered_interest_group"]
        self.assertEqual(strongest["order_by"], "ig_clout")
        self.assertEqual(strongest["save_scope_as"], "te_tax_sponsor")

    def test_no_branch_tests_whether_a_saved_sponsor_exists(self):
        # A sponsor saved for another country earlier in the same execution
        # would pass such a test.
        for path in (COLLECTION, GEN_EFFECTS):
            with self.subTest(path=path):
                self.assertNotIn("exists = scope:te_tax_sponsor", read(path))

    def test_layer_never_reads_root(self):
        for path in (STATE, COLLECTION, GEN_EFFECTS, GEN_TRIGGERS):
            with self.subTest(path=path):
                self.assertNotRegex(read(path), r"\bROOT\b")

    def test_relief_changes_a_modifier_only_when_the_wrong_band_is_present(self):
        relief = block(self.text, "te_tax_sync_relief")
        adds = re.findall(r"add_modifier = \{ name = (\w+) \}", relief)
        guarded_adds = re.findall(
            r"if = \{ limit = \{ NOT = \{ has_modifier = (\w+) \} \} add_modifier = \{ name = (\w+) \} \}",
            relief,
        )
        self.assertEqual(sorted(adds), sorted(name for _, name in guarded_adds))
        self.assertTrue(all(a == b for a, b in guarded_adds))
        removes = re.findall(r"remove_modifier = (\w+)", relief)
        guarded_removes = re.findall(
            r"if = \{ limit = \{ has_modifier = (\w+) \} remove_modifier = (\w+) \}", relief
        )
        self.assertEqual(sorted(removes), sorted(name for _, name in guarded_removes))
        self.assertTrue(all(a == b for a, b in guarded_removes))
        self.assertEqual(set(adds), set(RELIEF_MODIFIERS))
        self.assertEqual(set(removes), set(RELIEF_MODIFIERS))

    def test_relief_reads_the_enacted_depth_and_the_state_flag(self):
        relief = block(self.text, "te_tax_sync_relief")
        self.assertIn("var:te_tax_en_agrel = 1", relief)
        self.assertIn("var:te_tax_en_agrel = 2", relief)
        states = relief[relief.find("every_scope_state"):]
        self.assertIn("has_variable = te_tax_relief_state", states)
        self.assertIn("var:te_tax_relief_state = 1", states)
        self.assertIn("scope:te_tax_country.var:te_tax_en_regrel = 1", states)
        self.assertIn("scope:te_tax_country.var:te_tax_en_regrel = 2", states)


class GeneratedSyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = read(GEN_EFFECTS)
        cls.triggers = read(GEN_TRIGGERS)

    def test_generated_effects_define_every_part(self):
        names = set(top_level_names(self.effects))
        want = {f"te_tax_gen_sync_{key}" for key in KEYS} | {
            "te_tax_gen_sync_goods", "te_tax_gen_init_goods", "te_tax_gen_init_instruments",
        }
        self.assertEqual(names, want)

    def test_each_sync_adds_exactly_its_family_one_to_one(self):
        for key in KEYS:
            body = block(self.effects, f"te_tax_gen_sync_{key}")
            added = re.findall(
                r"add_amendment = \{ type = (\w+) sponsor = scope:te_tax_sponsor cooldown = 0 \}", body
            )
            with self.subTest(key=key):
                self.assertEqual(len(added), len(set(added)))
                self.assertEqual(set(added), amendment_family(key))
                self.assertEqual(body.count("add_amendment"), len(added))

    def test_each_add_matches_its_index_and_is_skipped_when_present(self):
        for key in KEYS:
            body = block(self.effects, f"te_tax_gen_sync_{key}")
            for name in amendment_family(key):
                idx = name.rsplit("_", 1)[1]
                pattern = (
                    r"if = \{\s*limit = \{ var:te_tax_en_" + key + " = " + idx + r" \}\s*"
                    r"active_law:lawgroup_taxation = \{\s*"
                    r"if = \{\s*limit = \{ NOT = \{ has_amendment = amendment_type:" + name + r" \} \}\s*"
                    r"add_amendment = \{ type = " + name + " "
                )
                with self.subTest(name=name):
                    self.assertRegex(body, pattern)

    def test_each_sync_removes_every_family_member_that_does_not_match(self):
        for key in KEYS:
            body = block(self.effects, f"te_tax_gen_sync_{key}")
            pattern = (
                r"active_law:lawgroup_taxation = \{\s*every_scope_amendment = \{\s*limit = \{\s*"
                r"te_tax_amendment_is_" + key + r" = yes\s*"
                r"NOT = \{ te_tax_amendment_matches_" + key + r" = yes \}\s*\}\s*"
                r"remove_amendment = yes\s*\}\s*\}"
            )
            with self.subTest(key=key):
                self.assertRegex(body, pattern)
                self.assertLess(body.find("remove_amendment"), body.find("add_amendment"))

    def test_family_triggers_name_exactly_the_generated_amendments(self):
        self.assertEqual(
            set(top_level_names(self.triggers)),
            {f"te_tax_amendment_{kind}_{key}" for kind in ("is", "matches") for key in KEYS},
        )
        for key in KEYS:
            family = amendment_family(key)
            is_body = block(self.triggers, f"te_tax_amendment_is_{key}")
            members = re.findall(r"type = amendment_type:(\w+)", is_body)
            pairs = re.findall(
                r"AND = \{ type = amendment_type:(amendment_te_tax_(\w+?)_(\d+)) "
                r"scope:te_tax_country\.var:te_tax_en_(\w+) = (\d+) \}",
                block(self.triggers, f"te_tax_amendment_matches_{key}"),
            )
            with self.subTest(key=key):
                self.assertEqual(sorted(members), sorted(family))
                self.assertEqual({p[0] for p in pairs}, family)
                self.assertEqual(len(pairs), len(family))
                for _, k, idx, var_key, value in pairs:
                    self.assertEqual((k, idx), (var_key, value))
                    self.assertEqual(k, key)

    def test_only_probe_proven_amendment_forms(self):
        for path in (COLLECTION, GEN_EFFECTS, GEN_TRIGGERS):
            text = read(path)
            with self.subTest(path=path):
                self.assertNotIn("is_amendment_type", text)
                self.assertNotIn("any_scope_amendment", text)

    def test_goods_sync_has_one_add_and_one_removal_per_catalog_good(self):
        body = block(self.effects, "te_tax_gen_sync_goods")
        goods = catalog()
        adds = re.findall(
            r"if = \{\s*limit = \{ var:te_tax_en_g_(\w+) = 1 NOT = \{ has_consumption_tax = g:(\w+) \} \}\s*"
            r"add_taxed_goods = g:(\w+)\s*\}",
            body,
        )
        removes = re.findall(
            r"else_if = \{\s*limit = \{ NOT = \{ var:te_tax_en_g_(\w+) = 1 \} has_consumption_tax = g:(\w+) \}\s*"
            r"remove_taxed_goods = g:(\w+)\s*\}",
            body,
        )
        self.assertEqual([a[0] for a in adds], list(goods))
        self.assertEqual([r[0] for r in removes], list(goods))
        for triple in adds + removes:
            self.assertEqual(len(set(triple)), 1)
        self.assertEqual(body.count("add_taxed_goods"), len(goods))
        strays = re.findall(
            r"if = \{ limit = \{ has_consumption_tax = g:(\w+) \} remove_taxed_goods = g:(\w+) \}", body
        )
        self.assertEqual([a for a, _ in strays], list(gen.stray_goods()))
        self.assertTrue(all(a == b for a, b in strays))
        self.assertEqual(body.count("remove_taxed_goods"), len(goods) + len(strays))

    def test_native_taxed_set_is_pinned_for_every_good(self):
        # Catalog goods follow their flag; every other good is removed if taxed.
        catalog_goods, strays = set(catalog()), set(gen.stray_goods())
        self.assertFalse(catalog_goods & strays)
        self.assertEqual(catalog_goods | strays, set(gen.all_goods()))
        with open(ROOT / "vanilla_parsed" / "common" / "goods.json", encoding="utf-8") as handle:
            vanilla = set(json.load(handle))
        self.assertTrue(vanilla <= set(gen.all_goods()))
        mod_goods = set()
        for path in sorted((ROOT / "common" / "goods").glob("*.txt")):
            mod_goods |= {name.split(":")[-1] for name in load(path.relative_to(ROOT).as_posix())}
        self.assertTrue(mod_goods <= set(gen.all_goods()))


class ConsumptionCatalogTest(unittest.TestCase):
    def test_catalog_is_sorted_and_unique(self):
        goods = catalog()
        self.assertEqual(list(goods), sorted(set(goods)))

    def test_every_catalog_good_is_a_pop_need_good(self):
        needs = gen.pop_need_goods()
        for good in catalog():
            self.assertIn(good, needs)

    def test_vanilla_goods_with_a_consumption_tax_cost_that_pops_buy_are_kept(self):
        with open(ROOT / "vanilla_parsed" / "common" / "goods.json", encoding="utf-8") as handle:
            goods = plain(json.load(handle))
        needs = gen.pop_need_goods()
        costed = {name for name, body in goods.items()
                  if isinstance(body, dict) and "consumption_tax_cost" in body and name in needs}
        self.assertTrue({"grain", "services", "transportation", "electricity"} <= costed)
        self.assertTrue(costed <= set(catalog()))

    def test_every_good_pops_buy_is_in_and_nothing_else(self):
        goods = set(catalog())
        self.assertEqual(goods, set(gen.pop_need_goods()))
        self.assertEqual(len(goods), 39)
        self.assertIn("digital_access", goods)   # local, no consumption_tax_cost: default cost 100
        for good in ("liquor", "coffee", "tobacco", "opium", "tourism", "telephones"):
            self.assertIn(good, goods)
        self.assertNotIn("construction", goods)  # costed, but no pop need buys it
        self.assertNotIn("ammunition", goods)
        self.assertIn("construction", gen.stray_goods())


class DisplayValueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = {path: read(path) for path in (DISPLAY, GEN_VALUES)}
        cls.views = {}
        cls.parsed = {}
        for path, text in cls.texts.items():
            for name in top_level_names(text):
                if name.startswith("te_tax_view_"):
                    cls.views[name] = block(text, name)
            cls.parsed.update(load(path))

    def test_every_view_has_a_has_variable_guard(self):
        self.assertTrue(self.views)
        for name, body in self.views.items():
            with self.subTest(name=name):
                self.assertIn("has_variable", body)

    def test_views_never_write_or_sweep(self):
        forbidden = re.compile(r"\b(set_variable|change_variable|remove_variable|save_scope_as|"
                               r"every_\w+|any_\w+|random_\w+|ordered_\w+)\b")
        for name, body in self.views.items():
            with self.subTest(name=name):
                self.assertIsNone(forbidden.search(body))

    def test_every_var_read_is_behind_its_own_guard(self):
        for name, body in self.views.items():
            for var in set(re.findall(r"var:(\w+)", body)):
                with self.subTest(name=name, var=var):
                    self.assertIn(f"has_variable = {var}", body)

    def test_required_views_exist(self):
        want = {"te_tax_view_code_version", "te_tax_view_migrated", "te_tax_view_schema",
                "te_tax_view_last_month", "te_tax_view_next_month", "te_tax_view_agrel",
                "te_tax_view_agrel_pct", "te_tax_view_regrel", "te_tax_view_regrel_pct",
                "te_tax_view_relief_state", "te_tax_view_goods_count"}
        for key in KEYS:
            for suffix in ("", "_rate", "_since", "_since_y", "_since_mo", "_exp", "_exp_y",
                           "_exp_mo", "_succ", "_succ_rate"):
                want.add(f"te_tax_view_en_{key}{suffix}")
            if key in PERCENT_KEYS:
                want |= {f"te_tax_view_en_{key}_pct", f"te_tax_view_en_{key}_succ_pct"}
        want |= {f"te_tax_view_en_g_{good}" for good in catalog()}
        self.assertEqual(set(self.views), want)

    def test_defaults_are_the_schema_sentinels(self):
        for name in self.views:
            sentinel_minus_one = re.search(r"_(since|exp|succ|last_month|next_month)(_y|_mo)?$", name) \
                and not name.endswith(("_rate", "_pct"))
            with self.subTest(name=name):
                self.assertEqual(self.parsed[name]["value"], "-1" if sentinel_minus_one else "0")

    def test_rates_are_index_times_step(self):
        for key in KEYS:
            body = self.views[f"te_tax_view_en_{key}_rate"]
            self.assertIn("value = var:te_tax_en_" + key, body)
            self.assertIn(f"multiply = te_tax_step_{key}", body)
            if key in PERCENT_KEYS:
                self.assertIn(f"multiply = te_tax_pct_step_{key}", self.views[f"te_tax_view_en_{key}_pct"])

    def test_relief_percent_step_matches_the_modifiers(self):
        self.assertEqual(Decimal(self.parsed["te_tax_relief_pct_step"]), Decimal(25))
        for name, (_, value) in RELIEF_MODIFIERS.items():
            band = int(name.rsplit("_", 1)[1])
            self.assertEqual(-value * 100, band * Decimal(25))


class ModifierTest(unittest.TestCase):
    def test_four_relief_bands_with_icon_and_value(self):
        modifiers = load(MODIFIERS)
        self.assertEqual(set(modifiers), set(RELIEF_MODIFIERS))
        for name, (field, value) in RELIEF_MODIFIERS.items():
            body = modifiers[name]
            with self.subTest(name=name):
                self.assertEqual(set(body), {"icon", field})
                self.assertEqual(Decimal(body[field]), value)
                self.assertRegex(body["icon"], r"^\"?gfx/interface/icons/.+\.dds\"?$")

    def test_each_band_has_a_name_and_a_desc(self):
        loc = {}
        for line in read(TAX_LOC, strip_comments=False).splitlines():
            match = re.match(r'^ ([\w.\-]+):\d+ "(.*)"$', line)
            if match:
                loc[match.group(1)] = match.group(2)
        for name in RELIEF_MODIFIERS:
            with self.subTest(name=name):
                self.assertTrue(loc.get(name))
                self.assertTrue(loc.get(f"{name}_desc"))
                self.assertNotIn("dividend", loc[f"{name}_desc"].lower())


class SoleWriterTest(unittest.TestCase):
    """Only the collection writer touches a rule-on country's native fiscal state."""

    WRITES = re.compile(
        r"\b(add_taxed_goods|remove_taxed_goods|set_tax_level)\b"
        r"|add_amendment = \{ type = amendment_te_tax_"
        r"|(add|remove)_modifier = (\{ name = )?te_tax_relief_"
    )
    ALLOWED = {COLLECTION, GEN_EFFECTS}

    def test_no_other_file_writes_native_tax_state(self):
        offenders = []
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                rel = path.relative_to(ROOT).as_posix()
                if rel in self.ALLOWED or "te_debug_tax" in rel:
                    continue
                text = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig", errors="replace"))
                if self.WRITES.search(text):
                    offenders.append(rel)
        self.assertEqual(offenders, [])


class GeneratedFilesTest(unittest.TestCase):
    def test_outputs_are_registered(self):
        for path in GENERATED:
            self.assertIn(path, gen.OUTPUTS)

    def test_check_passes_and_an_empty_root_reproduces_every_output(self):
        result = subprocess.run([sys.executable, str(GENERATOR), "--check"], cwd=ROOT,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(GENERATOR), "--root", tmp], cwd=ROOT,
                                    capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for path in gen.OUTPUTS:
                with self.subTest(path=path):
                    self.assertEqual((Path(tmp) / path).read_bytes(), (ROOT / path).read_bytes())

    def test_check_notices_a_hand_edit_of_the_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path in gen.OUTPUTS:
                target = Path(tmp) / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / path, target)
            edited = Path(tmp) / GEN_EFFECTS
            edited.write_bytes(edited.read_bytes().replace(b"cooldown = 0", b"cooldown = 1", 1))
            result = subprocess.run([sys.executable, str(GENERATOR), "--check", "--root", tmp],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 1)
            self.assertIn(GEN_EFFECTS, result.stdout)

    def test_every_layer_file_has_bom_lf_tabs_and_formatter_parity(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import format_paradox_tabs
        finally:
            sys.path.pop(0)
        for path in LAYER_FILES:
            raw = (ROOT / path).read_bytes()
            text = raw.decode("utf-8-sig")
            with self.subTest(path=path):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertNotIn(b"\r", raw)
                self.assertNotRegex(text, r"(?m)^ +\S")
                self.assertEqual(format_paradox_tabs.format_text(text), text)
        for path in GENERATED:
            with self.subTest(path=path):
                self.assertIn(gen.HEADER, read(path, strip_comments=False).splitlines()[:3])


if __name__ == "__main__":
    unittest.main()
