# -*- coding: utf-8 -*-
"""The legislated tax code's experimental customs schedule (plan Task 15).

Under the rule option ``te_tax_code_enabled_customs`` (``te_tax_customs_on``)
every tradeable good's import and export level, tariffs and subsidies on one
signed scale, is a provision of the market owner's code; under
``te_tax_code_enabled`` tariffs stay native. Structural checks on the committed
script, GUI and loc (no game install needed):

* the catalog is every good that is neither ``local`` nor ``tradeable = no``,
  vanilla and mod, each in one of the four goods categories, and the level
  encoding is the brief's -3 (max subventions) .. 3 (max tariffs);
* authority: only a country that owns its market and is no junior
  customs-union member holds customs records; the records are written by the
  customs migration, which reads every good's native level, one branch per
  level, through the capital's state goods; a country that stops owning its
  market keeps them frozen, one that gains a market migrates afresh, on the
  market and subject hooks and at every month's start;
* the sync writes each level the code holds and the market lacks, only for a
  market owner; a level a re-assert could not restore by the next month (a
  treaty or the tariff cooldown) is adopted into the code, which moves the
  customs external version and marks the good blocked;
* nothing customs-specific is written, read or shown as editable under the
  plain rule option: every write sits behind a customs gate;
* the 14 native tariff and subvention buttons are greyed under the customs
  option only.

Run: python3 -m unittest test_tax_code_customs -v
"""

import re
import unittest
from pathlib import Path

from test_tax_code_bypass import evaluate
from test_tax_code_civil_war import copied
from test_tax_code_rule import load
from test_tax_code_scheduler import effects
from test_tax_code_state import block, close, gen, read, schema_tokens

ROOT = Path(__file__).resolve().parent

STATE = "common/scripted_effects/te_tax_state_effects.txt"
MIGRATION = "common/scripted_effects/te_tax_migration_effects.txt"
COLLECTION = "common/scripted_effects/te_tax_collection_effects.txt"
SCHEDULE = "common/scripted_effects/te_tax_schedule_effects.txt"
CIVIL_WAR = "common/scripted_effects/te_tax_civil_war_effects.txt"
BILL = "common/scripted_effects/te_tax_bill_effects.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_generated_effects.txt"
GEN_BILL = "common/scripted_effects/te_tax_generated_bill_effects.txt"
TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"
GEN_TRIGGERS = "common/scripted_triggers/te_tax_generated_triggers.txt"
GEN_VALUES = "common/script_values/te_tax_generated_values.txt"
GEN_SUPPORT = "common/script_values/te_tax_generated_support_values.txt"
DISPLAY = "common/script_values/te_tax_display_values.txt"
ON_ACTIONS = "common/on_actions/te_tax_on_actions.txt"
EVENTS = "events/te_tax_internal_events.txt"
NATIVE_SGUIS = "common/scripted_guis/te_tax_native_sguis.txt"
GEN_SGUIS = "common/scripted_guis/te_tax_generated_sguis.txt"
WORKBENCH = "gui/journal_entry_widgets/te_tax_workbench_widget.gui"
REVIEW = "gui/journal_entry_widgets/te_tax_review_widget.gui"
GEN_ROWS = "gui/journal_entry_widgets/te_tax_generated_rows.gui"
TAX_LOC = "localization/english/te_tax_l_english.yml"
SCHEMA_DOC = "docs/systems/tax_code_schema.md"

# The brief's encoding, ported by hand: index -> native level key.
LEVELS = {-3: "max_subventions", -2: "high_subventions", -1: "low_subventions", 0: "no_tariffs_or_subventions",
          1: "low_tariffs", 2: "high_tariffs", 3: "max_tariffs"}
DIRS = {"imp": "import", "exp": "export"}
UNTOUCHED = -99
CATEGORIES = ("staple", "industrial", "luxury", "military")
KIND_ADOPTED, KIND_LOST, KIND_GAINED, KIND_DROPPED = 15, 16, 17, 18
# Controller ruling (pre-review): a refused re-assert is retried monthly and the market's level
# adopted only after this many consecutive failed monthly re-asserts (covers the 3-month
# TARIFF_LEVEL_COOLDOWN_MONTHS).
ADOPT_AFTER = 4
LEVEL_KEYS = {-3: "m3", -2: "m2", -1: "m1", 0: "0", 1: "p1", 2: "p2", 3: "p3"}
IGS = ("armed_forces", "devout", "industrialists", "intelligentsia",
       "landowners", "petty_bourgeoisie", "rural_folk", "trade_unions")
# The brief's support points per level step raised, in the material reason
# (subventions mirror the signs: a step down scores the opposite).
POINTS = {
    ("imp", "staple"): {"rural_folk": 4, "landowners": 4, "trade_unions": -4, "petty_bourgeoisie": -2},
    ("imp", "industrial"): {"industrialists": 3, "trade_unions": -1},
    ("imp", "luxury"): {"petty_bourgeoisie": -1, "intelligentsia": -1},
    ("exp", "staple"): {"trade_unions": 2, "landowners": -4},
}
# te_tax_customs_<good>_sgui's ops: op -> (direction, DIR).
OPS = {0: ("imp", 0), 1: ("imp", 1), 2: ("imp", 2), 10: ("exp", 0), 11: ("exp", 1), 12: ("exp", 2)}
# A customs write is reachable only behind one of these: the customs option or
# a trigger that needs it, or a record's customs marker, which only a write
# behind one of them creates (te_tax_<r>_customs_pver, te_tax_p<s>_pver_customs).
CUSTOMS_GATES = ("te_tax_customs_on = yes", "te_tax_customs_eligible = yes", "te_tax_customs_authority = yes",
                 "te_tax_can_draft_customs = {", "has_variable = te_tax_dr_customs_pver",
                 "has_variable = te_tax_bl_customs_pver", "has_variable = te_tax_pa_pver_customs",
                 "has_variable = te_tax_pb_pver_customs")
CUSTOMS_WRITE = re.compile(
    r"\bset_(?:import|export)_tariff_level\b"
    r"|name = te_tax_(?:en_(?:imp|exp)_[\w$]+|customs_held|pver_customs|xver_customs|drift_customs|cretry_[\w$]+|customs_month|dr_customs_dropped"
    r"|cblock_[\w$]+|(?:dr|bl|pa|pb)_(?:imp|exp)_[\w$]+|(?:dr|bl)_customs_pver|bl_xver_customs"
    r"|p[ab]_(?:pver|xver)_customs) (?:value|add)\b")
BRANCH = re.compile(r"\b(if|else_if|else|trigger_if|trigger_else_if) = \{")


def squash(text):
    return " ".join(text.split())


def catalog():
    return gen.customs_catalog()


def tradeable_goods():
    """Every good not `local = yes` and not `tradeable = no`, from the goods files, independently."""
    return sorted(good for good, body in gen.goods_definitions().items()
                  if body.get("local") != "yes" and body.get("tradeable") != "no")


def enclosing_limits(body, at):
    """The limits of every if / else_if block of `body` that encloses offset `at`."""
    limits = []
    for match in BRANCH.finditer(body, 0, at):
        end = close(body, match.end() - 1)
        if end < at:
            continue
        inner = body[match.end():end]
        found = re.match(r"\s*limit = \{", inner)
        if match.group(1) in ("if", "else_if", "trigger_if", "trigger_else_if") and found:
            limits.append(inner[found.end():close(inner, found.end() - 1)])
    return limits


def gated_at(body, at):
    return any(gate in squash(limit) for limit in enclosing_limits(body, at) for gate in CUSTOMS_GATES)


def ungated_paths(name, defined, seen=None):
    """Definitions reaching `name` with no customs gate on the way (empty: every path is gated)."""
    seen = set() if seen is None else seen
    if name in seen:
        return []
    seen.add(name)
    # A call may be parameterised (te_tax_dr_customs_$DIR$ = { ... }): its $P$ stands for any name part.
    callers = [(caller, match.start()) for caller, body in defined.items()
               for match in re.finditer(r"\b(te_tax_[\w$]+) = (?:yes|\{)", body)
               if re.fullmatch(re.sub(r"\\\$\w+\\\$", r"\\w+", re.escape(match.group(1))), name)]
    if not callers:
        return [name]
    missing = []
    for caller, at in callers:
        if not gated_at(defined[caller], at):
            missing += ungated_paths(caller, defined, seen)
    return missing


class CatalogTest(unittest.TestCase):
    def test_the_catalog_is_every_tradeable_good(self):
        self.assertEqual(list(catalog()), tradeable_goods())
        for good in ("services", "electricity", "transportation", "digital_access", "gold"):
            with self.subTest(good=good):
                self.assertNotIn(good, catalog())
        for good in ("grain", "iron", "small_arms", "construction", "launch_capacity"):
            with self.subTest(good=good):
                self.assertIn(good, catalog())

    def test_every_good_is_in_one_category(self):
        by_category = gen.customs_by_category()
        self.assertEqual(tuple(by_category), CATEGORIES)
        listed = [good for goods in by_category.values() for good in goods]
        self.assertEqual(sorted(listed), list(catalog()))
        for category, goods in by_category.items():
            for good in goods:
                with self.subTest(good=good):
                    self.assertEqual(gen.goods_definitions()[good]["category"], category)

    def test_the_level_encoding(self):
        self.assertEqual(dict(gen.CUSTOMS_LEVELS), LEVELS)
        self.assertEqual(dict(gen.CUSTOMS_DIRS), DIRS)
        self.assertEqual(gen.CUSTOMS_UNTOUCHED, UNTOUCHED)


class NativeHelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = read(GEN_EFFECTS)
        cls.triggers = read(GEN_TRIGGERS)

    def test_match_reads_the_capitals_state_goods_one_branch_per_level(self):
        for d, direction in DIRS.items():
            body = squash(block(self.triggers, f"te_tax_gen_customs_matches_{d}"))
            for idx, key in LEVELS.items():
                with self.subTest(d=d, idx=idx):
                    # Null-safe (final review A-I3): the capital may have no state goods for GOOD.
                    self.assertIn(f"AND = {{ var:te_tax_en_{d}_$GOOD$ = {idx} capital ?= {{ sg:$GOOD$ ?= {{ "
                                  f"{direction}_tariff_level = {key} }} }} }}", body)
            self.assertEqual(body.count("AND = {"), len(LEVELS))
            # A level that cannot be read is a match, tested last: no re-assert, no count,
            # no adoption, no drift.
            self.assertTrue(body.endswith("NOT = { capital ?= { sg:$GOOD$ ?= { always = yes } } } }"), body[-120:])
            self.assertNotRegex(body, r"sg:\$GOOD\$ = ")

    def test_setter_writes_the_enacted_level_one_branch_per_level(self):
        for d, direction in DIRS.items():
            body = squash(block(self.effects, f"te_tax_gen_customs_set_native_{d}"))
            for idx, key in LEVELS.items():
                with self.subTest(d=d, idx=idx):
                    self.assertIn(f"limit = {{ var:te_tax_en_{d}_$GOOD$ = {idx} }} set_{direction}_tariff_level = "
                                  f"{{ goods = g:$GOOD$ level = {key} }}", body)
            self.assertEqual(body.count(f"set_{direction}_tariff_level"), len(LEVELS))

    def test_reader_writes_one_index_per_level(self):
        for d, direction in DIRS.items():
            body = squash(block(self.effects, f"te_tax_gen_customs_read_native_{d}"))
            for idx, key in LEVELS.items():
                with self.subTest(d=d, idx=idx):
                    self.assertIn(f"limit = {{ capital ?= {{ sg:$GOOD$ ?= {{ {direction}_tariff_level = {key} }} }} }} "
                                  f"set_variable = {{ name = te_tax_en_{d}_$GOOD$ value = {idx} }}", body)
            # Unreadable (no capital, or no state goods for the good there): vanilla's default
            # level, low tariffs.
            self.assertNotRegex(body, r"sg:\$GOOD\$ = ")
            self.assertIn(f"else = {{ set_variable = {{ name = te_tax_en_{d}_$GOOD$ value = 1 }} }}", body)


class AuthorityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = load(TRIGGERS)

    def test_market_owner_and_no_junior(self):
        owns = self.triggers["te_tax_owns_market"]
        # The whole link, not just the market: a market can exist with an
        # invalid owner (test_market_capital_guard.py).
        self.assertEqual(owns.get("exists"), "market.owner")
        self.assertEqual(owns.get("market.owner"), "this")
        self.assertEqual(owns.get("is_junior_in_customs_union"), "no")

    def test_eligible_needs_the_customs_option(self):
        eligible = self.triggers["te_tax_customs_eligible"]
        self.assertEqual(eligible.get("te_tax_customs_on"), "yes")
        self.assertEqual(eligible.get("te_tax_owns_market"), "yes")

    def test_authority_needs_the_code_eligibility_and_live_records(self):
        body = squash(block(read(TRIGGERS), "te_tax_customs_authority"))
        for condition in ("te_tax_code_in_force = yes", "te_tax_customs_eligible = yes",
                          "has_variable = te_tax_customs_held", "var:te_tax_customs_held = 1"):
            self.assertIn(condition, body)


class MigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(MIGRATION)
        cls.generated = read(GEN_EFFECTS)

    def test_every_good_and_direction_is_read(self):
        body = squash(block(self.generated, "te_tax_gen_migrate_customs"))
        for good in catalog():
            for d in DIRS:
                with self.subTest(good=good, d=d):
                    self.assertIn(f"te_tax_gen_customs_read_native_{d} = {{ GOOD = {good} }}", body)
                    self.assertIn(f"if = {{ limit = {{ has_variable = te_tax_cretry_{d}_{good} }} "
                                  f"remove_variable = te_tax_cretry_{d}_{good} }}", body)
                    self.assertIn(f"if = {{ limit = {{ has_variable = te_tax_cblock_{d}_{good} }} "
                                  f"remove_variable = te_tax_cblock_{d}_{good} }}", body)

    def test_migrate_customs_holds_the_records_and_moves_the_external_version(self):
        body = squash(block(self.text, "te_tax_migrate_customs"))
        self.assertIn("te_tax_gen_migrate_customs = yes", body)
        self.assertIn("set_variable = { name = te_tax_customs_held value = 1 }", body)
        self.assertIn("change_variable = { name = te_tax_xver_customs add = 1 }", body)

    def test_the_migration_takes_customs_only_for_an_eligible_country(self):
        body = squash(block(self.text, "te_tax_migrate_country"))
        self.assertIn("if = { limit = { te_tax_customs_eligible = yes } te_tax_migrate_customs = yes }", body)
        # Before the history entry and the migrated mark.
        self.assertLess(body.find("te_tax_migrate_customs = yes"), body.find("te_tax_history_push"))
        self.assertLess(body.find("te_tax_migrate_customs = yes"),
                        body.find("set_variable = { name = te_tax_migrated value = 1 }"))


class RevalidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = squash(block(read(MIGRATION), "te_tax_customs_revalidate"))

    def test_gated_on_the_customs_option_and_a_code_in_force(self):
        self.assertTrue(self.body.startswith("if = { limit = { te_tax_customs_on = yes te_tax_code_in_force = yes }"))

    def test_a_country_that_gains_its_market_migrates_from_native_levels(self):
        gained = re.search(r"if = \{ limit = \{ te_tax_customs_eligible = yes NOT = \{ var:te_tax_customs_held = 1 \} \}"
                           r"(.*?)\} else_if", self.body)
        self.assertIsNotNone(gained)
        for phrase in ("te_tax_migrate_customs = yes", "change_variable = { name = te_tax_code_version add = 1 }",
                       f"te_tax_history_push = {{ KIND = {KIND_GAINED} SLOT = none }}"):
            self.assertIn(phrase, gained.group(1))

    def test_a_country_that_loses_its_market_keeps_its_records_frozen(self):
        lost = re.search(r"else_if = \{ limit = \{ NOT = \{ te_tax_customs_eligible = yes \} "
                         r"var:te_tax_customs_held = 1 \}(.*)", self.body)
        self.assertIsNotNone(lost)
        for phrase in ("set_variable = { name = te_tax_customs_held value = 0 }",
                       "change_variable = { name = te_tax_xver_customs add = 1 }",
                       "te_tax_gen_customs_clear_retries = yes",
                       f"te_tax_history_push = {{ KIND = {KIND_LOST} SLOT = none }}"):
            self.assertIn(phrase, lost.group(1))
        # Frozen, not removed: no record is written or removed.
        self.assertNotRegex(lost.group(1), r"te_tax_en_(imp|exp)_|te_tax_gen_migrate_customs")

    def test_the_processor_revalidates_after_claiming_the_month_before_any_transition(self):
        body = block(read(SCHEDULE), "te_tax_process_month")
        at = body.find("te_tax_customs_revalidate = yes")
        self.assertGreater(at, body.find("set_variable = { name = te_tax_last_month value = var:te_tax_now }"))
        self.assertLess(at, body.find("te_tax_gen_sunset_wage = yes"))
        self.assertEqual(body.count("te_tax_customs_revalidate = yes"), 1)

    def test_market_and_subject_hooks_dispatch_a_revalidation(self):
        hooks = read(ON_ACTIONS)
        for hook, handler in (("on_merge_markets", "te_tax_on_merge_markets"),
                              ("on_create_market", "te_tax_on_create_market"),
                              ("on_become_subject", "te_tax_on_become_subject"),
                              ("on_become_independent", "te_tax_on_become_independent")):
            with self.subTest(hook=hook):
                self.assertRegex(hooks, rf"(?m)^{hook} = \{{\s*on_actions = \{{\s*{handler}\s*\}}\s*\}}")
                body = squash(block(hooks, handler))
                self.assertTrue(body.startswith("effect = { if = { limit = { te_tax_code_on = yes "
                                                "te_tax_customs_on = yes }"), body)
                self.assertIn("trigger_event = { id = te_tax.7 days = 1 }", body)
        merge = squash(block(hooks, "te_tax_on_merge_markets"))
        self.assertIn("owner = { trigger_event = { id = te_tax.7 days = 1 } }", merge)
        self.assertIn("scope:market.owner = { trigger_event = { id = te_tax.7 days = 1 } }", merge)
        subject = squash(block(hooks, "te_tax_on_become_subject"))
        self.assertIn("overlord = { trigger_event = { id = te_tax.7 days = 1 } }", subject)

    def test_the_revalidation_event(self):
        event = squash(block(read(EVENTS), "te_tax.7"))
        for phrase in ("type = country_event", "hidden = yes", "trigger = { te_tax_code_on = yes }",
                       # The records the loss leaves, right after (final review A-Minor 5).
                       "immediate = { te_tax_customs_revalidate = yes te_tax_customs_drop_records = yes }"):
            self.assertIn(phrase, event)


class SyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.collection = read(COLLECTION)
        cls.writer = block(cls.collection, "te_tax_sync_collection")
        cls.sync = squash(block(cls.collection, "te_tax_sync_customs"))
        cls.generated = squash(block(read(GEN_EFFECTS), "te_tax_gen_sync_customs"))

    def test_only_a_market_owner_holding_the_records_is_synced(self):
        self.assertTrue(self.sync.startswith("if = { limit = { te_tax_customs_authority = yes }"))

    def test_the_writer_syncs_customs_after_the_drift_count_and_before_the_amendments(self):
        at = self.writer.find("te_tax_sync_customs = yes")
        self.assertGreater(at, self.writer.find("te_tax_detect_drift = yes"))
        self.assertLess(at, self.writer.find("te_tax_gen_sync_wage = yes"))
        # Before the mark the drift count compares against, so an adoption's version
        # move is part of the code the next count measures.
        self.assertLess(at, self.writer.find("name = te_tax_sync_version"))

    def test_each_good_and_direction_reasserts_then_adopts(self):
        for good in catalog():
            for d in DIRS:
                with self.subTest(good=good, d=d):
                    differs = (f"if = {{ limit = {{ has_variable = te_tax_en_{d}_{good} NOT = {{ "
                               f"te_tax_gen_customs_matches_{d} = {{ GOOD = {good} }} }} }}")
                    self.assertIn(differs, self.generated)
                    branch = self.generated[self.generated.find(differs):]
                    branch = branch[:close(branch, branch.find("{")) + 1]
                    retry = f"te_tax_cretry_{d}_{good}"
                    # Adopt only on the month's counting sync, after te_tax_customs_adopt_after failed
                    # monthly re-asserts in a row (controller ruling).
                    adopt = (f"if = {{ limit = {{ local_var:te_tax_cu_counts = 1 has_variable = {retry} "
                             f"var:{retry} >= te_tax_customs_adopt_after }} "
                             f"te_tax_gen_customs_read_native_{d} = {{ GOOD = {good} }} "
                             f"remove_variable = {retry} "
                             f"set_variable = {{ name = te_tax_cblock_{d}_{good} value = 1 }} "
                             "change_local_variable = { name = te_tax_cu_adopted add = 1 } }")
                    reassert = (f"else = {{ te_tax_gen_customs_set_native_{d} = {{ GOOD = {good} }} "
                                f"if = {{ limit = {{ local_var:te_tax_cu_counts = 1 }} "
                                f"if = {{ limit = {{ has_variable = {retry} }} change_variable = {{ name = {retry} add = 1 }} }} "
                                f"else = {{ set_variable = {{ name = {retry} value = 1 }} }} }} }}")
                    self.assertIn(adopt, branch)
                    self.assertIn(reassert, branch)
                    # A re-assert that took (the market matches the code again) clears the count and
                    # the direction's blocked mark (fix round 1).
                    self.assertIn(f"else_if = {{ limit = {{ has_variable = {retry} }} remove_variable = {retry} "
                                  f"if = {{ limit = {{ has_variable = te_tax_cblock_{d}_{good} }} "
                                  f"remove_variable = te_tax_cblock_{d}_{good} }} }}", self.generated)
        self.assertNotIn("cpend", self.generated)

    def test_the_adoption_line_is_logged_every_time_for_a_player_and_once_for_the_ai(self):
        self.assertIn("if = { limit = { OR = { is_ai = no NOT = { has_variable = te_tax_customs_logged } } } "
                      "debug_log = \"TE_TAX customs_adopted", self.sync)
        self.assertIn("if = { limit = { is_ai = yes } set_variable = { name = te_tax_customs_logged value = 1 } }",
                      self.sync)
        self.assertEqual(self.sync.count("debug_log"), 1)

    def test_the_threshold_is_spliced_into_the_history_line(self):
        loc = read(TAX_LOC, strip_comments=False)
        for i in range(1, 9):
            text = re.search(rf'(?m)^ te_tax_hist_kind_customs_adopted_{i}:0 "(.*)"$', loc).group(1)
            with self.subTest(position=i):
                self.assertIn("ScriptValue('te_tax_customs_adopt_after')", text)
                self.assertNotIn("four", text)

    def test_the_threshold_and_the_monthly_count(self):
        support = load("common/script_values/te_tax_support_values.txt")
        self.assertEqual(support["te_tax_customs_adopt_after"], str(ADOPT_AFTER))
        # Only the first customs sync of a calendar month counts a failed re-assert or adopts:
        # te_tax.4 and the watchdog may sync again in the month.
        self.assertIn("set_local_variable = { name = te_tax_cu_counts value = 0 } if = { limit = { OR = { NOT = { "
                      "has_variable = te_tax_customs_month } var:te_tax_customs_month < te_history_month_index } } "
                      "set_local_variable = { name = te_tax_cu_counts value = 1 } set_variable = { name = "
                      "te_tax_customs_month value = te_history_month_index } }", self.sync)

    def test_an_adoption_writes_one_entry_a_month_with_the_count(self):
        self.assertIn("set_local_variable = { name = te_tax_cu_adopted value = 0 } te_tax_gen_sync_customs = yes",
                      self.sync)
        adopted = re.search(r"if = \{ limit = \{ local_var:te_tax_cu_adopted > 0 \}(.*)\}", self.sync)
        self.assertIsNotNone(adopted)
        for phrase in ("change_variable = { name = te_tax_xver_customs add = 1 }",
                       "change_variable = { name = te_tax_code_version add = 1 }",
                       f"te_tax_gen_history_write = {{ KIND = {KIND_ADOPTED} SLOT = none INST = local_var:te_tax_cu_adopted }}"):
            self.assertIn(phrase, adopted.group(1))
        self.assertEqual(self.sync.count("te_tax_gen_history_write"), 1)
        self.assertNotIn("te_tax_history_push", self.sync)
        # Each history row prints the count it carries in _inst.
        custom = read("common/customizable_localization/te_tax_generated_custom_loc.txt")
        loc = read(TAX_LOC, strip_comments=False)
        for i in range(1, 9):
            body = squash(block(custom, f"te_tax_hist_event_{i}"))
            with self.subTest(position=i):
                self.assertIn(f"trigger = {{ te_tax_view_hist_{i}_kind = {KIND_ADOPTED} }} "
                              f"localization_key = te_tax_hist_kind_customs_adopted_{i}", body)
                self.assertRegex(loc, rf"(?m)^ te_tax_hist_kind_customs_adopted_{i}:0 \".*"
                                      rf"ScriptValue\('te_tax_view_hist_{i}_inst'\)")

    def test_drift_is_counted_against_the_code_for_a_market_owner_only(self):
        detect = squash(block(self.collection, "te_tax_detect_drift"))
        self.assertIn("AND = { te_tax_customs_authority = yes te_tax_gen_customs_drift = yes }", detect)
        count = squash(block(self.collection, "te_tax_count_drift"))
        self.assertIn("if = { limit = { te_tax_customs_authority = yes } te_tax_gen_count_customs_drift = yes }", count)
        counted = squash(block(read(GEN_EFFECTS), "te_tax_gen_count_customs_drift"))
        any_drift = squash(block(read(GEN_TRIGGERS), "te_tax_gen_customs_drift"))
        for good in catalog():
            for d in DIRS:
                mismatch = (f"has_variable = te_tax_en_{d}_{good} NOT = {{ te_tax_gen_customs_matches_{d} = "
                            f"{{ GOOD = {good} }} }}")
                with self.subTest(good=good, d=d):
                    self.assertIn(f"if = {{ limit = {{ {mismatch} }} change_variable = {{ name = te_tax_drift_customs "
                                  "add = 1 } }", counted)
                    self.assertIn(f"AND = {{ {mismatch} }}", any_drift)

    def test_the_drift_total_is_a_guarded_view(self):
        body = squash(block(read(DISPLAY), "te_tax_view_drift_customs"))
        self.assertEqual(body, "value = 0 if = { limit = { has_variable = te_tax_drift_customs } "
                               "value = var:te_tax_drift_customs }")


class TokenTest(unittest.TestCase):
    def test_customs_tokens_are_initialised_only_under_the_customs_option(self):
        init = squash(block(read(STATE), "te_tax_init_country"))
        gate = re.search(r"if = \{ limit = \{ te_tax_customs_on = yes \}(.*?)\} if = \{ limit = \{ NOT = \{ "
                         r"has_variable = te_tax_schema", init)
        self.assertIsNotNone(gate)
        for token in ("te_tax_customs_held", "te_tax_pver_customs", "te_tax_xver_customs", "te_tax_drift_customs"):
            with self.subTest(token=token):
                self.assertIn(f"if = {{ limit = {{ NOT = {{ has_variable = {token} }} }} "
                              f"set_variable = {{ name = {token} value = 0 }} }}", gate.group(1))
                self.assertEqual(init.count(f"name = {token} "), 1)

    def test_the_schema_lists_the_customs_rows(self):
        country, _ = schema_tokens()
        for token in ("te_tax_customs_held", "te_tax_pver_customs", "te_tax_xver_customs", "te_tax_drift_customs"):
            with self.subTest(token=token):
                self.assertEqual(country.get(token), 0)
        for good in catalog():
            for d in DIRS:
                with self.subTest(good=good, d=d):
                    self.assertIn(f"te_tax_en_{d}_{good}", country)
                    self.assertIsNone(country[f"te_tax_en_{d}_{good}"])

    def test_the_outbreak_copies_the_customs_records(self):
        defined = effects()
        written = copied({"te_tax_copy_code"}, defined)
        for token in ("te_tax_customs_held", "te_tax_pver_customs", "te_tax_xver_customs", "te_tax_drift_customs"):
            self.assertIn(token, written)
        for good in catalog():
            for d in DIRS:
                self.assertIn(f"te_tax_en_{d}_{good}", written)

    def test_a_released_country_takes_up_its_own_market(self):
        release = squash(block(read(CIVIL_WAR), "te_tax_init_released_country"))
        self.assertIn("if = { limit = { te_tax_customs_on = yes } set_variable = { name = te_tax_customs_held value = 0 } "
                      "te_tax_gen_customs_clear_retries = yes }", release)
        enacted = set(re.findall(r"NAME = (\w+)", block(read(GEN_EFFECTS), "te_tax_gen_copy_enacted")))
        self.assertFalse({name for name in enacted if "_imp_" in name or "_exp_" in name or "customs" in name})

    def test_the_win_repair_drops_pending_reasserts_and_blocked_marks(self):
        # Final review A-Minor 7: a winner never inherits a loser's "blocked" mark for a
        # good it never had blocked.
        repair = block(read(CIVIL_WAR), "te_tax_repair_after_civil_war")
        self.assertIn("te_tax_gen_customs_clear_retries = yes", repair)
        clear = squash(block(read(GEN_EFFECTS), "te_tax_gen_customs_clear_retries"))
        for good in catalog():
            for d in DIRS:
                for mark in ("cretry", "cblock"):
                    self.assertIn(f"if = {{ limit = {{ has_variable = te_tax_{mark}_{d}_{good} }} "
                                  f"remove_variable = te_tax_{mark}_{d}_{good} }}", clear)


class BothModesTest(unittest.TestCase):
    """Under te_tax_code_enabled no customs record is written: every customs write
    is reachable only through a customs gate."""

    @classmethod
    def setUpClass(cls):
        cls.defined = effects()

    def test_every_customs_write_is_gated(self):
        writers = {name: body for name, body in self.defined.items() if CUSTOMS_WRITE.search(body)}
        self.assertTrue(writers)
        for name, body in writers.items():
            for match in CUSTOMS_WRITE.finditer(body):
                if gated_at(body, match.start()):
                    continue
                with self.subTest(name=name, write=match.group(0)):
                    self.assertEqual(ungated_paths(name, self.defined), [])

    def test_the_tariff_buttons_are_greyed_under_the_customs_option_only(self):
        valid = load(NATIVE_SGUIS)["te_tax_native_tariff_controls_sgui"]["is_valid"]
        for rule, greyed in (("off", False), ("enabled", False), ("customs", True)):
            with self.subTest(rule=rule):
                self.assertEqual(evaluate(valid, rule, False), not greyed)

    def test_the_customs_gates_need_the_customs_option(self):
        triggers = load(TRIGGERS)
        self.assertEqual(triggers["te_tax_customs_on"], {"has_game_rule": "te_tax_code_enabled_customs"})
        self.assertEqual(triggers["te_tax_customs_eligible"].get("te_tax_customs_on"), "yes")
        self.assertEqual(triggers["te_tax_customs_authority"].get("te_tax_customs_eligible"), "yes")

    def test_only_the_generated_helpers_write_native_tariffs(self):
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                rel = path.relative_to(ROOT).as_posix()
                if rel == GEN_EFFECTS or "te_debug_tax" in rel:
                    continue
                text = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig", errors="replace"))
                with self.subTest(path=rel):
                    self.assertNotRegex(text, r"\bset_(import|export)_tariff_level\b")


class RecordTest(unittest.TestCase):
    """The draft and the bill carry a customs field per good and direction, -99
    when they leave it alone, under the customs option only."""

    @classmethod
    def setUpClass(cls):
        cls.generated = read(GEN_BILL)

    def fields(self, record):
        return [f"te_tax_{record}_{d}_{good}" for good in catalog() for d in DIRS]

    def test_a_new_draft_leaves_every_customs_provision_alone(self):
        init = squash(block(self.generated, "te_tax_gen_draft_init"))
        gate = re.search(r"if = \{ limit = \{ te_tax_customs_on = yes \}(.*?)\}$", init)
        self.assertIsNotNone(gate)
        for name in self.fields("dr"):
            with self.subTest(name=name):
                self.assertIn(f"set_variable = {{ name = {name} value = {UNTOUCHED} }}", gate.group(1))
                self.assertEqual(init.count(f"name = {name} "), 1)
        self.assertIn("set_variable = { name = te_tax_dr_customs_pver value = -1 }", gate.group(1))

    def test_the_bill_copies_the_drafts_customs_with_the_external_version(self):
        copy = squash(block(self.generated, "te_tax_gen_bill_from_draft"))
        gate = "if = { limit = { has_variable = te_tax_dr_customs_pver has_variable = te_tax_xver_customs }"
        self.assertIn(gate, copy)
        body = copy[copy.find(gate):]
        for good in catalog():
            for d in DIRS:
                self.assertIn(f"set_variable = {{ name = te_tax_bl_{d}_{good} value = var:te_tax_dr_{d}_{good} }}", body)
        self.assertIn("set_variable = { name = te_tax_bl_customs_pver value = var:te_tax_dr_customs_pver }", body)
        self.assertIn("set_variable = { name = te_tax_bl_xver_customs value = var:te_tax_xver_customs }", body)

    def test_a_revision_draft_copies_the_bills_customs(self):
        copy = squash(block(self.generated, "te_tax_gen_draft_from_bill"))
        self.assertIn("if = { limit = { has_variable = te_tax_bl_customs_pver }", copy)
        for good in catalog():
            for d in DIRS:
                self.assertIn(f"set_variable = {{ name = te_tax_dr_{d}_{good} value = var:te_tax_bl_{d}_{good} }}", copy)

    def test_closing_removes_the_customs_payload_only_where_it_was_written(self):
        for record, clear, extra in (("dr", "te_tax_gen_draft_clear", ("te_tax_dr_customs_pver",)),
                                     ("bl", "te_tax_gen_bill_clear", ("te_tax_bl_customs_pver",
                                                                      "te_tax_bl_xver_customs"))):
            body = squash(block(self.generated, clear))
            gate = f"if = {{ limit = {{ has_variable = te_tax_{record}_customs_pver }}"
            self.assertIn(gate, body)
            guarded = body[body.find(gate):]
            for name in self.fields(record) + list(extra):
                with self.subTest(name=name):
                    self.assertIn(f"remove_variable = {name}", guarded)

    def test_untouched_is_minus_99_everywhere(self):
        # -1 is a level: a customs field is touched at -3 or more, never ">= 0".
        for path in (GEN_EFFECTS, GEN_BILL, GEN_TRIGGERS, GEN_SUPPORT, GEN_VALUES):
            text = read(path)
            with self.subTest(path=path):
                self.assertNotRegex(text, r"var:te_tax_(?:dr|bl|pa|pb)_(?:imp|exp)_\w+ (?:>= 0|< 0|> -1)\b")
                self.assertNotRegex(text, r"name = te_tax_(?:dr|bl|pa|pb)_(?:imp|exp)_\w+ value = -1 \}")


class PackageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = read(GEN_EFFECTS)
        cls.triggers = read(GEN_TRIGGERS)
        cls.bill = read(GEN_BILL)

    def test_the_store_writes_the_customs_payload_from_the_bill(self):
        for slot in ("a", "b"):
            store = squash(block(self.effects, f"te_tax_gen_store_{slot}"))
            gate = "if = { limit = { has_variable = te_tax_bl_customs_pver }"
            self.assertIn(gate, store)
            body = store[store.find(gate):]
            for good in catalog():
                for d in DIRS:
                    self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_{d}_{good} value = var:te_tax_bl_{d}_{good} }}",
                                  body)
            self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_xver_customs value = var:te_tax_bl_xver_customs }}",
                          body)
            self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_pver_customs value = var:te_tax_pver_customs }}", body)

    def test_commencement_enacts_the_customs_while_the_code_holds_them(self):
        for slot in ("a", "b"):
            apply = squash(block(self.effects, f"te_tax_gen_apply_{slot}"))
            gate = f"if = {{ limit = {{ te_tax_customs_authority = yes has_variable = te_tax_p{slot}_pver_customs }}"
            self.assertIn(gate, apply)
            body = apply[apply.find(gate):]
            for good in catalog():
                for d in DIRS:
                    with self.subTest(slot=slot, good=good, d=d):
                        self.assertIn(f"if = {{ limit = {{ var:te_tax_p{slot}_{d}_{good} >= {gen.CUSTOMS_MIN} }} "
                                      f"set_variable = {{ name = te_tax_en_{d}_{good} value = var:te_tax_p{slot}_{d}_{good} }} "
                                      f"if = {{ limit = {{ has_variable = te_tax_cretry_{d}_{good} }} "
                                      f"remove_variable = te_tax_cretry_{d}_{good} }} "
                                      f"if = {{ limit = {{ has_variable = te_tax_cblock_{d}_{good} }} "
                                      f"remove_variable = te_tax_cblock_{d}_{good} }} }}", body)

    def test_a_package_touching_customs_needs_the_customs_external_version(self):
        for slot in ("a", "b"):
            touches = squash(block(self.triggers, f"te_tax_gen_package_touches_customs_{slot}"))
            self.assertTrue(touches.startswith(f"has_variable = te_tax_p{slot}_pver_customs OR = {{"))
            for good in catalog():
                for d in DIRS:
                    self.assertIn(f"var:te_tax_p{slot}_{d}_{good} >= {gen.CUSTOMS_MIN}", touches)
            current = squash(block(self.triggers, f"te_tax_gen_package_current_{slot}"))
            self.assertIn(f"OR = {{ NOT = {{ te_tax_gen_package_touches_customs_{slot} = yes }} AND = {{ "
                          f"has_variable = te_tax_xver_customs var:te_tax_p{slot}_xver_customs = var:te_tax_xver_customs }} }}",
                          current)
            unsuperseded = squash(block(self.triggers, f"te_tax_gen_package_unsuperseded_{slot}"))
            self.assertIn(f"OR = {{ NOT = {{ te_tax_gen_package_touches_customs_{slot} = yes }} AND = {{ "
                          f"has_variable = te_tax_pver_customs var:te_tax_p{slot}_pver_customs = var:te_tax_pver_customs }} }}",
                          unsuperseded)
            empty = squash(block(self.triggers, f"te_tax_gen_package_empty_{slot}"))
            self.assertIn(f"NOT = {{ te_tax_gen_package_touches_customs_{slot} = yes }}", empty)

    def test_supersession_drops_the_bills_customs_from_a_later_package(self):
        for slot in ("a", "b"):
            supersede = squash(block(self.bill, f"te_tax_gen_supersede_{slot}"))
            gate = f"if = {{ limit = {{ has_variable = te_tax_bl_customs_pver has_variable = te_tax_p{slot}_pver_customs }}"
            self.assertIn(gate, supersede)
            for good in catalog():
                for d in DIRS:
                    self.assertIn(f"if = {{ limit = {{ var:te_tax_bl_{d}_{good} >= {gen.CUSTOMS_MIN} "
                                  f"var:te_tax_p{slot}_{d}_{good} >= {gen.CUSTOMS_MIN} }} set_variable = {{ name = "
                                  f"te_tax_p{slot}_{d}_{good} value = {UNTOUCHED} }} }}", supersede)
            overlaps = squash(block(self.triggers, f"te_tax_gen_bill_overlaps_{slot}"))
            self.assertIn(f"AND = {{ has_variable = te_tax_bl_customs_pver has_variable = te_tax_p{slot}_pver_customs "
                          f"OR = {{ AND = {{ var:te_tax_bl_imp_{catalog()[0]} >= {gen.CUSTOMS_MIN}", overlaps)

    def test_an_approval_moves_the_customs_planned_version(self):
        bump = squash(block(self.bill, "te_tax_gen_bump_pver"))
        self.assertIn("if = { limit = { te_tax_customs_on = yes te_tax_gen_bill_touches_customs = yes } "
                      "change_variable = { name = te_tax_pver_customs add = 1 } }", bump)

    def test_the_outbreak_copies_a_packages_customs(self):
        for slot in ("a", "b"):
            payload = set(gen.slot_payload(slot))
            for good in catalog():
                for d in DIRS:
                    self.assertIn(f"te_tax_p{slot}_{d}_{good}", payload)
            self.assertLessEqual({f"te_tax_p{slot}_xver_customs", f"te_tax_p{slot}_pver_customs"}, payload)


class DraftTriggerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = read(GEN_TRIGGERS)
        cls.triggers = read(TRIGGERS)

    def test_touches_customs_reads_the_fields_behind_the_marker(self):
        for record, label in (("dr", "draft"), ("bl", "bill")):
            body = squash(block(self.generated, f"te_tax_gen_{label}_touches_customs"))
            self.assertTrue(body.startswith(f"has_variable = te_tax_{record}_customs_pver OR = {{"), body[:80])
            for good in catalog():
                for d in DIRS:
                    self.assertIn(f"var:te_tax_{record}_{d}_{good} >= {gen.CUSTOMS_MIN}", body)

    def test_the_draft_and_bill_checks_cover_customs(self):
        self.assertIn("te_tax_gen_draft_touches_customs = yes", block(self.generated, "te_tax_gen_draft_touches_any"))
        baseline = squash(block(self.generated, "te_tax_gen_draft_baseline_current"))
        self.assertIn("OR = { NOT = { te_tax_gen_draft_touches_customs = yes } AND = { has_variable = "
                      "te_tax_pver_customs var:te_tax_dr_customs_pver = var:te_tax_pver_customs } }", baseline)
        current = squash(block(self.generated, "te_tax_gen_bill_current"))
        self.assertIn("OR = { NOT = { te_tax_gen_bill_touches_customs = yes } AND = { has_variable = "
                      "te_tax_xver_customs var:te_tax_bl_xver_customs = var:te_tax_xver_customs } }", current)
        differs = squash(block(self.generated, "te_tax_gen_draft_differs_from_bill"))
        self.assertIn("AND = { has_variable = te_tax_dr_customs_pver has_variable = te_tax_bl_customs_pver OR = {", differs)
        for good in catalog():
            for d in DIRS:
                self.assertIn(f"NOT = {{ var:te_tax_dr_{d}_{good} = var:te_tax_bl_{d}_{good} }}", differs)

    def test_a_customs_bill_is_never_minor(self):
        for name, label in (("te_tax_bill_is_minor", "bill"), ("te_tax_draft_is_minor", "draft")):
            self.assertIn(f"NOT = {{ te_tax_gen_{label}_touches_customs = yes }}", block(self.triggers, name))

    def test_a_draft_touching_customs_needs_the_authority_to_become_a_bill(self):
        ready = squash(block(self.triggers, "te_tax_draft_ready"))
        self.assertIn("trigger_if = { limit = { te_tax_gen_draft_touches_customs = yes } custom_tooltip = { "
                      "text = te_tax_tt_customs_authority te_tax_customs_authority = yes } }", ready)


class CommandTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = read(TRIGGERS)
        cls.bill = read(BILL)
        cls.support = read(GEN_SUPPORT)

    def test_the_step_trigger(self):
        body = squash(block(self.triggers, "te_tax_can_draft_customs"))
        for phrase in ("custom_tooltip = { text = te_tax_tt_code_in_force te_tax_code_in_force = yes }",
                       "custom_tooltip = { text = te_tax_tt_customs_authority te_tax_customs_authority = yes }",
                       "trigger_if = { limit = { te_tax_draft_active = yes has_variable = te_tax_dr_$D$_$GOOD$ } "
                       "te_tax_dr_customs_ok_$DIR$ = { D = $D$ GOOD = $GOOD$ } }",
                       "trigger_else = { custom_tooltip = { text = te_tax_tt_draft_open always = no } }"):
            self.assertIn(phrase, body)
        oks = {"0": f"te_tax_dr_eff_$D$_$GOOD$ > {gen.CUSTOMS_MIN}", "1": f"te_tax_dr_eff_$D$_$GOOD$ < {gen.CUSTOMS_MAX}",
               "2": f"var:te_tax_dr_$D$_$GOOD$ >= {gen.CUSTOMS_MIN}"}
        for direction, condition in oks.items():
            with self.subTest(direction=direction):
                self.assertIn(condition, squash(block(self.triggers, f"te_tax_dr_customs_ok_{direction}")))

    def test_the_step_command(self):
        cmd = squash(block(self.bill, "te_tax_cmd_draft_customs"))
        self.assertEqual(cmd, "if = { limit = { te_tax_can_draft_customs = { GOOD = $GOOD$ D = $D$ DIR = $DIR$ } } "
                              "te_tax_dr_customs_$DIR$ = { GOOD = $GOOD$ D = $D$ } }")
        touch = squash(block(self.bill, "te_tax_customs_dr_touch"))
        self.assertEqual(touch, "if = { limit = { NOT = { te_tax_gen_draft_touches_customs = yes } } set_variable = { "
                                "name = te_tax_dr_customs_pver value = var:te_tax_pver_customs } }")
        for direction, delta in (("0", -1), ("1", 1)):
            body = squash(block(self.bill, f"te_tax_dr_customs_{direction}"))
            with self.subTest(direction=direction):
                self.assertRegex(body, r"^custom_tooltip = te_tax_tt_cmd_draft_customs_\w+ te_tax_customs_dr_touch = yes ")
                self.assertIn("set_variable = { name = te_tax_dr_$D$_$GOOD$ value = te_tax_dr_eff_$D$_$GOOD$ } "
                              f"change_variable = {{ name = te_tax_dr_$D$_$GOOD$ add = {delta} }} clamp_variable = {{ "
                              f"name = te_tax_dr_$D$_$GOOD$ min = {gen.CUSTOMS_MIN} max = {gen.CUSTOMS_MAX} }}", body)
        revert = squash(block(self.bill, "te_tax_dr_customs_2"))
        self.assertIn(f"set_variable = {{ name = te_tax_dr_$D$_$GOOD$ value = {UNTOUCHED} }}", revert)
        self.assertIn("if = { limit = { NOT = { te_tax_gen_draft_touches_customs = yes } } set_variable = { "
                      "name = te_tax_dr_customs_pver value = -1 } }", revert)

    def test_existing_law_in_the_records_month(self):
        for record in ("dr", "bl"):
            for good in catalog()[:3]:
                for d in DIRS:
                    body = squash(block(self.support, f"te_tax_base_{record}_{d}_{good}"))
                    with self.subTest(record=record, good=good, d=d):
                        self.assertTrue(body.startswith(
                            f"value = {gen.CUSTOMS_DEFAULT_LEVEL} if = {{ limit = {{ has_variable = te_tax_customs_held "
                            f"var:te_tax_customs_held = 1 has_variable = te_tax_en_{d}_{good} }} "
                            f"value = var:te_tax_en_{d}_{good} }}"), body[:200])
                        for slot in ("a", "b"):
                            self.assertIn(f"if = {{ limit = {{ te_tax_slot_awaits_before = {{ SLOT = {slot} DUE = "
                                          f"te_tax_{record}_due }} has_variable = te_tax_p{slot}_pver_customs "
                                          f"has_variable = te_tax_p{slot}_{d}_{good} var:te_tax_p{slot}_{d}_{good} >= "
                                          f"{gen.CUSTOMS_MIN} }} value = var:te_tax_p{slot}_{d}_{good} }}", body)
        for good in catalog():
            for d in DIRS:
                eff = squash(block(self.support, f"te_tax_dr_eff_{d}_{good}"))
                self.assertEqual(eff, f"value = te_tax_base_dr_{d}_{good} if = {{ limit = {{ has_variable = "
                                      f"te_tax_dr_{d}_{good} var:te_tax_dr_{d}_{good} >= {gen.CUSTOMS_MIN} }} "
                                      f"value = var:te_tax_dr_{d}_{good} }}")

    def test_the_draft_rebase_accepts_customs(self):
        body = squash(block(self.triggers, "te_tax_can_draft_rebase"))
        self.assertIn("has_variable = te_tax_pver_$KEY$", body)


class SupportTest(unittest.TestCase):
    """Support v1 for customs (the brief's points, ported by hand): reasons in the
    material component, clamped with it; and no affordability bonus for a good
    the bill exempts while raising its import level (spec 6)."""

    @classmethod
    def setUpClass(cls):
        cls.values = read(GEN_SUPPORT)
        cls.triggers = read(TRIGGERS)

    def test_each_good_and_direction_moves_from_existing_law(self):
        for good in catalog():
            for d in DIRS:
                field = f"te_tax_bl_{d}_{good}"
                body = squash(block(self.values, f"te_tax_bl_dstep_{d}_{good}"))
                with self.subTest(good=good, d=d):
                    self.assertEqual(body, f"value = 0 if = {{ limit = {{ has_variable = {field} var:{field} >= "
                                           f"{gen.CUSTOMS_MIN} }} value = var:{field} subtract = te_tax_base_bl_{d}_{good} }}")

    def test_category_sums(self):
        by_category = gen.customs_by_category()
        for (d, category) in POINTS:
            body = block(self.values, f"te_tax_bl_dcu_{d}_{category}")
            with self.subTest(d=d, category=category):
                self.assertEqual(sorted(re.findall(rf"add = te_tax_bl_dstep_{d}_(\w+)", body)),
                                 sorted(by_category[category]))

    def test_the_material_reason_takes_the_brief_points_before_the_clamp(self):
        for ig in IGS:
            body = block(self.values, f"te_tax_mat_{ig}")
            found = {(d, category): int(points) for d, category, points in
                     re.findall(r"add = \{ value = te_tax_bl_dcu_(imp|exp)_(\w+) multiply = (-?\d+) \}", body)}
            expected = {key: table[ig] for key, table in POINTS.items() if ig in table}
            with self.subTest(ig=ig):
                self.assertEqual(found, expected)
                self.assertRegex(body, r"multiply = -10\s*(add = \{ value = te_tax_bl_\w+ multiply = -?\d+ \}\s*)+"
                                       r"min = -40\s*max = 40\s*$")

    def test_no_affordability_bonus_for_a_good_whose_import_level_rises(self):
        both = set(gen.consumption_catalog()) & set(catalog())
        self.assertTrue(both)
        for good in gen.consumption_catalog():
            body = squash(block(self.values, f"te_tax_dl_g_{good}"))
            zero = f"if = {{ limit = {{ te_tax_bl_dstep_imp_{good} > 0 }} min = 0 }}"
            with self.subTest(good=good):
                if good in both:
                    self.assertIn(zero, body)
                    # Inside the bill's branch, after the weight: only a negative term (an exemption) is zeroed.
                    self.assertGreater(body.find(zero), body.find("multiply ="))
                else:
                    self.assertNotIn("te_tax_bl_dstep_imp_", body)

    def test_a_customs_change_keeps_a_bill_for_the_offers(self):
        changed = squash(block(self.values, "te_tax_bl_customs_changed"))
        for good in catalog():
            for d in DIRS:
                self.assertIn(f"if = {{ limit = {{ NOT = {{ te_tax_bl_dstep_{d}_{good} = 0 }} }} add = 1 }}", changed)
        for name in ("te_tax_offer_cut_leaves_a_bill", "te_tax_offer_untax_leaves_a_bill"):
            self.assertIn("te_tax_bl_customs_changed >= 1", block(self.triggers, name))


class SguiTest(unittest.TestCase):
    """One op-coded handler per tradeable good: 0 import down, 1 import up, 2 import
    out of the draft; 10, 11, 12 the same for exports."""

    @classmethod
    def setUpClass(cls):
        cls.text = read(GEN_SGUIS)

    def test_one_handler_per_good_with_the_op_table(self):
        for good in catalog():
            body = squash(block(self.text, f"te_tax_customs_{good}_sgui"))
            with self.subTest(good=good):
                for phrase in ("scope = country", "saved_scopes = { op }", "is_shown = { te_tax_code_in_force = yes }",
                               "ai_is_valid = { always = no }", "trigger_else = { always = no }"):
                    self.assertIn(phrase, body)
                for op, (d, direction) in OPS.items():
                    self.assertIn(f"limit = {{ exists = scope:op scope:op = {op} }} te_tax_can_draft_customs = "
                                  f"{{ GOOD = {good} D = {d} DIR = {direction} }}", body)
                    self.assertIn(f"limit = {{ exists = scope:op scope:op = {op} }} te_tax_cmd_draft_customs = "
                                  f"{{ GOOD = {good} D = {d} DIR = {direction} }}", body)
                self.assertNotRegex(block(self.text, f"te_tax_customs_{good}_sgui").split("effect = {", 1)[1],
                                    r"\belse = \{")


class ViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = read(GEN_VALUES)
        cls.display = read(DISPLAY)

    def test_the_market_level_one_branch_per_level(self):
        for good in catalog():
            for d, direction in DIRS.items():
                body = squash(block(self.values, f"te_tax_cu_native_{d}_{good}"))
                with self.subTest(good=good, d=d):
                    self.assertTrue(body.startswith(f"value = {gen.CUSTOMS_DEFAULT_LEVEL} "))
                    for idx, key in LEVELS.items():
                        self.assertIn(f"if = {{ limit = {{ capital ?= {{ sg:{good} ?= {{ {direction}_tariff_level = "
                                      f"{key} }} }} }} value = {idx} }}", body)
                    self.assertNotIn("var:", body)

    def test_a_row_shows_the_draft_for_the_owner_and_the_market_for_a_member(self):
        for good in catalog():
            for d in DIRS:
                body = squash(block(self.values, f"te_tax_view_cu_{d}_{good}"))
                with self.subTest(good=good, d=d):
                    self.assertIn("if = { limit = { te_tax_customs_authority = yes has_variable = te_tax_dr_on "
                                  f"var:te_tax_dr_on = 1 has_variable = te_tax_dr_due }} value = te_tax_dr_eff_{d}_{good} }}",
                                  body)
                    self.assertIn(f"else_if = {{ limit = {{ te_tax_customs_on = yes }} value = te_tax_cu_native_{d}_{good} }}",
                                  body)

    def test_the_customs_mode(self):
        # 2 only for a country in a market it does not own; an owner whose records are not
        # yet taken up (mode 3) must not read "Set by" its own name (fix round 1).
        body = squash(block(self.display, "te_tax_view_customs_mode"))
        self.assertEqual(body, "value = 0 if = { limit = { te_tax_customs_authority = yes has_variable = "
                               "te_tax_customs_held } value = 1 } else_if = { limit = { te_tax_customs_on = yes "
                               "NOT = { te_tax_owns_market = yes } } value = 2 } else_if = { limit = { "
                               "te_tax_customs_on = yes } value = 3 }")


class GuiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workbench = read(WORKBENCH, strip_comments=False)
        cls.rows = read(GEN_ROWS, strip_comments=False)
        cls.review = read(REVIEW, strip_comments=False)
        cls.loc = read(TAX_LOC, strip_comments=False)

    def loc_value(self, key):
        match = re.search(rf'(?m)^ {key}:0 "(.*)"$', self.loc)
        self.assertIsNotNone(match, key)
        return match.group(1)

    def test_the_workbench_has_a_collapsed_customs_accordion(self):
        self.assertIn("GetVariableSystem.Toggle('te_tax_wb_customs_open')", self.workbench)
        for mode, key in ((0, "te_tax_wb_customs_native"), (2, "te_tax_wb_customs_member"),
                          (1, "te_tax_wb_customs_intro"), (3, "te_tax_wb_customs_pending")):
            with self.subTest(mode=mode):
                self.assertRegex(squash(self.workbench),
                                 r"visible = \"\[And\( GetVariableSystem\.Exists\('te_tax_wb_customs_open'\), "
                                 r"EqualTo_CFixedPoint\( GetPlayer\.MakeScope\.ScriptValue\('te_tax_view_customs_mode'\), "
                                 rf"'\(CFixedPoint\){mode}' \) \)\]\" text = \"{key}\"")
        for category in CATEGORIES:
            with self.subTest(category=category):
                self.assertIn(f"te_tax_wb_customs_rows_{category} = {{", self.workbench)
                self.assertIn(f"text = \"te_tax_wb_cu_cat_{category}\"", self.workbench)

    def test_the_plain_option_and_a_member_say_who_sets_tariffs(self):
        self.assertIn("Market panel", self.loc_value("te_tax_wb_customs_native"))
        self.assertIn("[GetPlayer.GetMarket.GetOwner.GetName]", self.loc_value("te_tax_wb_customs_member"))
        self.assertTrue(self.loc_value("te_tax_wb_customs_member").startswith("Set by "))

    def test_level_names_say_subsidy_below_zero_and_tariff_above(self):
        for idx, suffix in LEVEL_KEYS.items():
            text = self.loc_value(f"te_tax_cu_lv_{suffix}").lower()
            with self.subTest(idx=idx):
                if idx < 0:
                    self.assertIn("subsidy", text)
                elif idx > 0:
                    self.assertIn("tariff", text)

    def test_the_steppers_are_the_editors_only(self):
        row = squash(self.workbench.split("type te_tax_customs_row = flowcontainer {", 1)[1].split("\n\ttype ", 1)[0])
        editor = ("EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_tax_view_customs_mode'), "
                  "'(CFixedPoint)1' )")
        self.assertEqual(row.count("button_icon_minus_action = {"), 2)
        self.assertEqual(row.count("button_icon_plus_action = {"), 2)
        self.assertEqual(row.count(f"visible = \"[{editor}]\""), 4)
        for op in OPS:
            self.assertIn(f"MakeScopeValue( '(CFixedPoint){op}' )", row)

    def test_generated_rows_per_category(self):
        for category, goods in gen.customs_by_category().items():
            body = squash(self.rows.split(f"type te_tax_wb_customs_rows_{category} = flowcontainer {{", 1)[1]
                          .split("\n\ttype ", 1)[0])
            with self.subTest(category=category):
                self.assertEqual(re.findall(r"GetScriptedGui\('te_tax_customs_(\w+)_sgui'\)", body), list(goods))
                for good in goods:
                    for d in DIRS:
                        for idx, suffix in LEVEL_KEYS.items():
                            self.assertIn(f"visible = \"[EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue("
                                          f"'te_tax_view_cu_{d}_{good}'), '(CFixedPoint){idx}' )]\" "
                                          f"text = \"te_tax_cu_lv_{suffix}\"", body)

    def test_the_review_lists_each_changed_level_and_a_blocked_good(self):
        self.assertIn("te_tax_rv_customs_rows = {}", self.review)
        self.assertIn("ScriptValue('te_tax_view_dr_customs_changed')", self.review)
        body = squash(self.rows.split("type te_tax_rv_customs_rows = flowcontainer {", 1)[1].split("\n\ttype ", 1)[0])
        for good in catalog():
            for d in DIRS:
                self.assertIn(f"visible = \"[NotEqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue("
                              f"'te_tax_view_cu_{d}_{good}_on'), '(CFixedPoint)0' )]\"", body)
                self.assertIn(f"ScriptValue('te_tax_view_cu_{d}_{good}_base')", body)
                blocked = (f"visible = \"[And( NotEqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue("
                           f"'te_tax_view_cu_{d}_{good}_blocked'), '(CFixedPoint)0' ), NotEqualTo_CFixedPoint( "
                           f"GetPlayer.MakeScope.ScriptValue('te_tax_view_cu_{d}_{good}_on'), '(CFixedPoint)0' ) )]\"")
                self.assertIn(blocked, body)
        for d in DIRS:
            text = self.loc_value(f"te_tax_rv_cu_blocked_{d}")
            self.assertIn("treaty", text)
            self.assertIn("cooldown", text)
        # One blocked view per direction (fix round 1), not per good.
        values = read(GEN_VALUES)
        self.assertNotIn(f"te_tax_view_cu_{catalog()[0]}_blocked", values)
        self.assertIn(f"has_variable = te_tax_cblock_imp_{catalog()[0]} var:te_tax_cblock_imp_{catalog()[0]} = 1",
                      squash(block(values, f"te_tax_view_cu_imp_{catalog()[0]}_blocked")))

    def test_the_estimate_says_customs_are_not_estimated(self):
        self.assertIn("text = \"te_tax_est_customs\"", self.review)
        self.assertIn("no estimate", self.loc_value("te_tax_est_customs"))
        self.assertIn("trade volumes", self.loc_value("te_tax_est_customs"))


class MarketLostTest(unittest.TestCase):
    """Controller ruling (pre-review): when the market is lost, an open draft's and bill's
    customs levels are dropped (-99), so both stay usable; the bill, whose text changed,
    opens a new revision; one debug line and one history entry (kind 18); the review says why."""

    @classmethod
    def setUpClass(cls):
        cls.lost = squash(block(read(MIGRATION), "te_tax_customs_revalidate")).split("else_if = { limit = { NOT = {", 1)[1]
        cls.drop = squash(block(read(MIGRATION), "te_tax_customs_drop_records"))
        cls.triggers = read(TRIGGERS)
        cls.bill = read(BILL)
        cls.generated = read(GEN_BILL)

    def test_the_records_the_loss_leaves_are_dropped_once(self):
        # Final review A-Minor 5: split from the revalidation, read from the records (the
        # code no longer holds the customs, yet a record changes a level), so it runs once.
        self.assertTrue(self.drop.startswith("if = { limit = { te_tax_customs_on = yes OR = { "
                                             "te_tax_customs_drop_due_draft = yes te_tax_customs_drop_due_bill = yes } }"),
                        self.drop[:200])
        for phrase in ("set_local_variable = { name = te_tax_cu_withdrawn value = 0 }",
                       "if = { limit = { te_tax_customs_drop_due_draft = yes } te_tax_draft_drop_customs = yes }",
                       "if = { limit = { te_tax_customs_drop_due_bill = yes } te_tax_bill_drop_customs = yes }",
                       f"te_tax_gen_history_write = {{ KIND = {KIND_DROPPED} SLOT = none INST = local_var:te_tax_cu_withdrawn }} "
                       "debug_log = \"TE_TAX customs_dropped"):
            self.assertIn(phrase, self.drop)
        for record, active, touches in (("draft", "te_tax_draft_active", "te_tax_gen_draft_touches_customs"),
                                        ("bill", "te_tax_bill_active", "te_tax_gen_bill_touches_customs")):
            with self.subTest(record=record):
                self.assertEqual(squash(block(self.triggers, f"te_tax_customs_drop_due_{record}")),
                                 f"te_tax_customs_on = yes te_tax_code_in_force = yes "
                                 f"NOT = {{ te_tax_customs_authority = yes }} {active} = yes {touches} = yes")
        # The revalidation's lost branch no longer touches the draft or the bill.
        for name in ("te_tax_draft_drop_customs", "te_tax_bill_drop_customs", "te_tax_cu_"):
            self.assertNotIn(name, self.lost)
        # No customs change without the authority, so the condition holds only after a loss.
        self.assertIn("custom_tooltip = { text = te_tax_tt_customs_authority te_tax_customs_authority = yes }",
                      squash(block(self.triggers, "te_tax_can_draft_customs")))

    def test_the_processor_drops_them_after_the_transitions_and_refreshes_once(self):
        body = squash(block(read(SCHEDULE), "te_tax_process_month"))
        self.assertEqual(body.count("te_tax_customs_drop_records = yes"), 2)
        self.assertIn("if = { limit = { te_tax_customs_drop_due_bill = yes } te_tax_customs_drop_records = yes } "
                      "else = { te_tax_customs_drop_records = yes if = { limit = { te_tax_bill_active = yes } "
                      "te_tax_refresh_support = yes } }", body)
        self.assertEqual(body.count("te_tax_refresh_support = yes"), 1)
        self.assertGreater(body.find("te_tax_customs_drop_due_bill"), body.find("te_tax_sync_collection = yes"))
        self.assertGreater(body.find("te_tax_customs_drop_due_bill"), body.find("te_tax_obl_check_month = yes"))
        self.assertLess(body.find("te_tax_customs_revalidate = yes"), body.find("te_tax_gen_sunset_wage = yes"))

    def test_the_draft_keeps_every_other_provision(self):
        body = squash(block(self.bill, "te_tax_draft_drop_customs"))
        self.assertIn("te_tax_gen_customs_drop_draft = yes", body)
        drop = squash(block(self.generated, "te_tax_gen_customs_drop_draft"))
        for good in catalog():
            for d in DIRS:
                self.assertIn(f"set_variable = {{ name = te_tax_dr_{d}_{good} value = {UNTOUCHED} }}", drop)
        self.assertIn("set_variable = { name = te_tax_dr_customs_pver value = -1 }", drop)
        self.assertIn("set_variable = { name = te_tax_dr_customs_dropped value = 1 }", drop)
        self.assertNotRegex(drop, r"name = te_tax_dr_(wage|div|land|head|cons|g_|agrel|regrel|due)")

    def test_a_mixed_bill_opens_a_new_revision_and_a_customs_only_bill_is_withdrawn(self):
        """Fix round 1: a bill that, without its customs, changes nothing from existing law is
        withdrawn as te_tax_cmd_withdraw does (te_tax_bill_close: commitments and pending
        promises released); one that still changes something opens a new revision."""
        body = squash(block(self.bill, "te_tax_bill_drop_customs"))
        self.assertTrue(body.startswith("te_tax_gen_customs_drop_bill = yes if = { limit = { "
                                        "te_tax_bill_changes_something = yes } change_variable = { name = te_tax_bl_rev "
                                        "add = 1 } te_tax_bill_start_debate = yes } else = { te_tax_bill_close = yes "
                                        "set_local_variable = { name = te_tax_cu_withdrawn value = 1 } "
                                        "debug_log = \"TE_TAX customs_bill_withdrawn"), body[:300])
        withdraw = squash(block(self.bill, "te_tax_cmd_withdraw"))
        self.assertIn("te_tax_bill_close = yes", withdraw)
        self.assertIn("te_tax_obl_release_pending = yes", block(self.bill, "te_tax_bill_close"))
        drop = squash(block(self.generated, "te_tax_gen_customs_drop_bill"))
        for good in catalog():
            for d in DIRS:
                self.assertIn(f"set_variable = {{ name = te_tax_bl_{d}_{good} value = {UNTOUCHED} }}", drop)

    def test_changes_something_counts_changes_from_existing_law_not_restatements(self):
        triggers = read(TRIGGERS)
        body = squash(block(triggers, "te_tax_bill_changes_something"))
        self.assertEqual(body, "OR = { te_tax_gen_bill_changes_instruments = yes te_tax_bl_goods_changed >= 1 "
                               "NOT = { te_tax_bl_dstep_agrel = 0 } te_tax_bl_regrel_differs = yes "
                               "te_tax_bl_customs_changed >= 1 }")
        # An instrument counts if the bill moves its rate, sets an expiry or replaces a pending one
        # (a restated rate with an expiry change is an extension, spec 3), never merely if touched.
        instruments = squash(block(read(GEN_TRIGGERS), "te_tax_gen_bill_changes_instruments"))
        for key in ("wage", "div", "land", "head", "cons"):
            self.assertIn(f"AND = {{ var:te_tax_bl_{key} >= 0 OR = {{ NOT = {{ te_tax_bl_dstep_{key} = 0 }} "
                          f"var:te_tax_bl_{key}_sun > 0 AND = {{ has_variable = te_tax_en_{key}_exp "
                          f"var:te_tax_en_{key}_exp >= 0 }} }} }}", instruments)

    def test_passage_and_force_through_refuse_an_empty_bill(self):
        line = "custom_tooltip = { text = te_tax_tt_pass_changes te_tax_bill_changes_something = yes }"
        for name in ("te_tax_can_pass", "te_tax_can_force_through"):
            with self.subTest(name=name):
                self.assertIn(line, squash(block(read(TRIGGERS), name)))

    def test_the_withdrawal_has_its_own_history_line(self):
        custom = read("common/customizable_localization/te_tax_generated_custom_loc.txt")
        for i in range(1, 9):
            body = squash(block(custom, f"te_tax_hist_event_{i}"))
            with self.subTest(position=i):
                self.assertIn(f"trigger = {{ te_tax_view_hist_{i}_kind = {KIND_DROPPED} te_tax_view_hist_{i}_inst = 1 }} "
                              "localization_key = te_tax_hist_kind_customs_dropped_withdrawn", body)
        text = re.search(r'(?m)^ te_tax_hist_kind_customs_dropped_withdrawn:0 "(.*)"$',
                         read(TAX_LOC, strip_comments=False)).group(1)
        self.assertIn("withdrawn", text)
        self.assertIn("no longer owns its market", text)

    def test_the_drafts_dropped_mark_is_payload_and_cleared_on_a_gain(self):
        init = squash(block(self.generated, "te_tax_gen_draft_init"))
        self.assertIn("set_variable = { name = te_tax_dr_customs_dropped value = 0 }", init)
        gained = squash(block(read(MIGRATION), "te_tax_customs_revalidate")).split("else_if", 1)[0]
        self.assertIn("if = { limit = { has_variable = te_tax_dr_customs_dropped } "
                      "set_variable = { name = te_tax_dr_customs_dropped value = 0 } }", gained)

    def test_the_review_says_why(self):
        review = read(REVIEW, strip_comments=False)
        self.assertIn("ScriptValue('te_tax_view_dr_customs_dropped')", review)
        self.assertIn("text = \"te_tax_rv_customs_dropped\"", review)
        text = re.search(r'(?m)^ te_tax_rv_customs_dropped:0 "(.*)"$', read(TAX_LOC, strip_comments=False)).group(1)
        self.assertIn("dropped", text)
        self.assertIn("market", text)
        view = squash(block(read(GEN_VALUES), "te_tax_view_dr_customs_dropped"))
        self.assertIn("has_variable = te_tax_dr_customs_dropped var:te_tax_dr_customs_dropped = 1", view)


class HistoryKindTest(unittest.TestCase):
    def test_kinds_and_their_lines(self):
        loc = read(TAX_LOC, strip_comments=False)
        for kind, key in ((KIND_ADOPTED, "te_tax_hist_kind_customs_adopted"),
                          (KIND_LOST, "te_tax_hist_kind_customs_lost"),
                          (KIND_DROPPED, "te_tax_hist_kind_customs_dropped"),
                          (KIND_GAINED, "te_tax_hist_kind_customs_gained")):
            with self.subTest(kind=kind):
                self.assertEqual(gen.HISTORY_KIND_KEYS[kind], key)
                # An adoption's line prints its count, so each row has its own key (key_<i>).
                for name in ([f"{key}_{i}" for i in range(1, 9)] if kind == KIND_ADOPTED else [key]):
                    self.assertRegex(loc, rf"(?m)^ {name}:0 \"")
        # Adoption and a market gained change the code; losing the market freezes it.
        self.assertIn(KIND_ADOPTED, gen.CODE_CHANGE_KINDS)
        self.assertIn(KIND_GAINED, gen.CODE_CHANGE_KINDS)
        self.assertNotIn(KIND_LOST, gen.CODE_CHANGE_KINDS)
        self.assertNotIn(KIND_DROPPED, gen.CODE_CHANGE_KINDS)


class SchemaDocTest(unittest.TestCase):
    def test_the_doc_lists_the_customs_catalog_and_section(self):
        doc = read(SCHEMA_DOC, strip_comments=False)
        self.assertIn("\n## Customs schedule\n", doc)
        section = doc.split("\n## Customs schedule\n", 1)[1].split("\n## ", 1)[0]
        line = [row for row in section.splitlines() if row.startswith("**Customs catalog")]
        self.assertEqual(len(line), 1)
        self.assertEqual(re.findall(r"`(\w+)`", line[0]), list(catalog()))
        self.assertIn(f"({len(catalog())} goods)", line[0])
        for phrase in ("te_tax_customs_revalidate", "te_tax_sync_customs", "te_tax_cretry_", "te_tax_cblock_",
                       "te_tax_customs_adopt_after", "te_tax_customs_month", "te_tax_dr_customs_dropped",
                       "on_merge_markets", "te_tax.7"):
            self.assertIn(phrase, section)


if __name__ == "__main__":
    unittest.main()
