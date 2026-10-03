# -*- coding: utf-8 -*-
"""The legislated tax code across civil wars, new countries and state transfers.

Spec §10: at a revolution's outbreak both sides receive the operative code and
the approved future changes with their original dates; each side legislates
on its own during the war; at reunification the winner's complete code
applies, never a mixture of both. A civil war's winner inherits every loser
variable it does not hold itself, but no modifier and no list
(docs/guides/scripting_best_practices.md, "What a Civil War's Winner
Inherits"), so the code is plain country variables and these tests pin the
wiring that keeps it coherent:

* the shared civil-war hooks call the tax effects (te_civil_war_on_actions.txt);
* the outbreak copy writes every country token of the schema table
  (docs/systems/tax_code_schema.md, parsed) on the rebels from the original,
  except the four it sets itself (no bill, no draft, never synced, migrated);
* the win repair closes the bill and the draft, hands the month back and
  records history kind 7, and never commences a package, bumps a version or
  grants an approval or a modifier;
* a release copies only the parent's enacted provisions when the parent holds
  the carrier law, otherwise migrates; formations migrate;
* a state that changes owner loses its relief marks unless the code that
  named it travels with it (the Strategic Reserve hub's rule plus a new tag);
* the enacted named states are one country list, te_tax_en_relief_states,
  which a list cannot survive the merge with: the outbreak and a release copy
  it, and the copies and the repair rebuild the marks from the country's own
  list (te_tax_rebuild_relief_marks; Task 11, test_tax_code_goods_relief.py).

Shape of test_decolonization_civil_war.py: source text, brace-matched blocks.

Run: python3 -m unittest test_tax_code_civil_war -v
"""

import re
import unittest
from pathlib import Path

from test_tax_code_rule import load
from test_tax_code_scheduler import closure, effects
from test_tax_code_state import KEYS, block, catalog, gen, read, schema_tokens

ROOT = Path(__file__).resolve().parent

CIVIL_WAR_ON_ACTIONS = "common/on_actions/te_civil_war_on_actions.txt"
TAX_ON_ACTIONS = "common/on_actions/te_tax_on_actions.txt"
CIVIL_WAR_EFFECTS = "common/scripted_effects/te_tax_civil_war_effects.txt"
EVENTS = "events/te_tax_internal_events.txt"
TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_generated_effects.txt"
SCHEMA_DOC = "docs/systems/tax_code_schema.md"
LEDGER = "docs/testing/tax-code-capability-ledger.md"

SLOTS = ("a", "b")
HEADER_SUFFIXES = tuple(suffix for suffix, _ in gen.PACKAGE_HEADER)
STATE_MARKS = ("te_tax_relief_state", "te_tax_pending_relief_a", "te_tax_pending_relief_b")
# What the outbreak copy sets on the rebels instead of copying (spec §10: no
# unfinished bill or draft; the rebels' carrier has never been synced by their
# own writer; the copy is the migration).
REBEL_OVERRIDES = {"te_tax_bl_on": "0", "te_tax_dr_on": "0", "te_tax_sync_version": "-1",
                   "te_tax_migrated": "1"}

COPY = re.compile(r"te_tax_copy_token = \{ NAME = (\w+) \}")
SET = re.compile(r"set_variable = \{ name = (\w+) value = ([^}]+?) \}")


def copied(names, defined):
    """The tokens te_tax_copy_token copies anywhere in the closure of `names`."""
    found = set()
    for name in closure(set(names), defined):
        found |= set(COPY.findall(defined[name]))
    return found


def raisers(event):
    """[(path, event)] for every trigger_event of `event`, in either form."""
    pattern = re.compile(r"trigger_event = (?:\{ id = )?(" + re.escape(event) + r")\b")
    found = []
    for directory in ("common", "events"):
        for path in sorted((ROOT / directory).rglob("*.txt")):
            rel = path.relative_to(ROOT).as_posix()
            found += [(rel, match) for match in pattern.findall(read(rel))]
    return sorted(set(found))


class HookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.civil_war = read(CIVIL_WAR_ON_ACTIONS)
        cls.tax = read(TAX_ON_ACTIONS)

    def test_outbreak_copy_runs_after_the_sides_are_recorded(self):
        start = block(self.civil_war, "te_civil_war_on_start")
        self.assertIn("te_tax_on_uprising = yes", start)
        self.assertLess(start.index("te_civil_war_record_start = yes"), start.index("te_tax_on_uprising = yes"))

    def test_win_repair_runs_between_resolve_and_clear(self):
        won = block(self.civil_war, "te_civil_war_on_won")
        self.assertIn("te_tax_repair_after_civil_war = yes", won)
        self.assertLess(won.index("te_civil_war_resolve_sides = yes"),
                        won.index("te_tax_repair_after_civil_war = yes"))
        self.assertLess(won.index("te_tax_repair_after_civil_war = yes"), won.index("te_civil_war_clear = yes"))

    def test_the_tax_on_actions_no_longer_hook_the_uprising(self):
        # Same-name on_actions union across files in no known order: a second
        # handler would race the copy with a migration of the rebels.
        parsed = load(TAX_ON_ACTIONS)
        for hook in ("on_revolution_start", "on_secession_start", "te_tax_on_uprising_start"):
            with self.subTest(hook=hook):
                self.assertNotIn(hook, parsed)

    def test_releases_copy_or_migrate_in_the_new_country(self):
        body = block(self.tax, "te_tax_on_country_released")
        self.assertIn("te_tax_code_on = yes", body)
        self.assertLess(body.index("save_scope_as = te_tax_source"), body.index("scope:target ?= {"))
        self.assertIn("te_tax_init_released_country = yes", body[body.index("scope:target ?= {"):])
        self.assertNotIn("trigger_event", body)

    def test_formations_still_migrate(self):
        parsed = load(TAX_ON_ACTIONS)
        self.assertEqual(parsed["te_tax_on_country_formed"]["effect"]["if"]["trigger_event"], {"id": "te_tax.3"})

    def test_state_owner_change_is_hooked_and_gated(self):
        parsed = load(TAX_ON_ACTIONS)
        self.assertEqual(parsed["on_state_owner_change"]["on_actions"], ["te_tax_on_state_owner_change"])
        effect = parsed["te_tax_on_state_owner_change"]["effect"]
        self.assertEqual(effect, {"if": {"limit": {"te_tax_code_on": "yes"}, "te_tax_relief_follow_owner": "yes"}})


class OutbreakTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.defined = effects()
        cls.text = read(CIVIL_WAR_EFFECTS)
        cls.uprising = block(cls.text, "te_tax_on_uprising")
        cls.copy = block(cls.text, "te_tax_copy_code")

    def test_gated_on_the_rule_and_an_original_with_a_code(self):
        self.assertRegex(self.uprising, r"^\s*if = \{\s*limit = \{\s*te_tax_code_on = yes\s+exists = scope:target\s*\}")
        self.assertIn("te_tax_code_in_force = yes", self.uprising)

    def test_the_source_is_saved_before_the_copy_on_the_rebels(self):
        self.assertLess(self.uprising.index("save_scope_as = te_tax_source"),
                        self.uprising.index("te_tax_copy_code = yes"))
        target = self.uprising[self.uprising.index("scope:target = {"):]
        self.assertIn("te_tax_copy_code = yes", target)
        self.assertIn("trigger_event = { id = te_tax.6 }", target)
        # te_tax.6 is gated on the code being in force (te_tax_migrated >= 1),
        # which the copy writes last; an event raised without days may run at once.
        self.assertLess(target.index("te_tax_copy_code = yes"), target.index("trigger_event = { id = te_tax.6 }"))

    def test_an_original_without_a_code_lets_the_rebels_migrate(self):
        fallback = self.uprising[self.uprising.index("else = {"):]
        self.assertIn("trigger_event = { id = te_tax.3 }", fallback)
        self.assertNotIn("te_tax_copy_code", fallback)

    def test_every_country_token_of_the_schema_is_copied_or_set(self):
        country, _ = schema_tokens()
        written = copied({"te_tax_copy_code"}, self.defined) - copied({"te_tax_init_country"}, self.defined)
        overrides = dict(SET.findall(self.copy))
        missing = sorted(set(country) - written - set(overrides))
        self.assertEqual(missing, [], "schema tokens the outbreak copy neither copies nor sets")

    def test_the_rebels_set_only_the_four_overrides(self):
        overrides = {name: value for name, value in SET.findall(self.copy) if name.startswith("te_tax_")}
        self.assertEqual(overrides, REBEL_OVERRIDES)
        written = copied({"te_tax_copy_code"}, self.defined)
        self.assertFalse(written & set(REBEL_OVERRIDES), "an override is also copied")

    def test_the_month_guard_is_copied_never_claimed(self):
        self.assertIn("te_tax_last_month", copied({"te_tax_copy_code"}, self.defined))
        self.assertNotRegex(self.text, r"name = te_tax_last_month value = (?!-1 )")

    def test_migrated_is_written_last(self):
        last = self.copy[self.copy.rfind("set_variable"):]
        self.assertTrue(last.startswith("set_variable = { name = te_tax_migrated value = 1 }"))

    def test_init_backfills_after_the_copy(self):
        self.assertLess(self.copy.index("te_tax_gen_copy_code = yes"), self.copy.index("te_tax_init_country = yes"))

    def test_commitments_are_reset_not_copied(self):
        self.assertIn("te_tax_gen_reset_commitments = yes", self.copy)
        written = copied({"te_tax_copy_code"}, self.defined)
        self.assertFalse({name for name in written if name.startswith(("te_tax_com_", "te_tax_bl_", "te_tax_dr_"))})

    def test_package_payload_is_copied_only_for_an_occupied_slot(self):
        for slot in SLOTS:
            with self.subTest(slot=slot):
                self.assertRegex(
                    self.copy,
                    r"if = \{ limit = \{ scope:te_tax_source = \{ var:te_tax_p" + slot
                    + r"_on = 1 \} \} te_tax_gen_copy_slot_" + slot + r" = yes \}")

    def test_slot_copy_is_exactly_the_payload_the_store_writes(self):
        generated = read(GEN_EFFECTS)
        for slot in SLOTS:
            with self.subTest(slot=slot):
                header = {f"te_tax_p{slot}{suffix}" for suffix in HEADER_SUFFIXES}
                store = set(re.findall(r"name = (te_tax_p" + slot + r"_\w+)",
                                       block(generated, f"te_tax_gen_store_{slot}")))
                copy = set(COPY.findall(block(generated, f"te_tax_gen_copy_slot_{slot}")))
                self.assertEqual(copy, store - header)

    def test_the_copy_activates_nothing_and_syncs_nothing_inline(self):
        reach = closure({"te_tax_on_uprising"}, self.defined)
        self.assertNotIn("te_tax_sync_collection", reach)
        self.assertNotIn("te_tax_process_month", reach)
        for name in reach:
            with self.subTest(name=name):
                self.assertNotIn("activate_law", self.defined[name])
                self.assertNotIn("add_modifier", self.defined[name])

    def test_relief_marks_travel_and_are_rebuilt(self):
        # The original's list of named states is copied whole, then the rebels'
        # marks are rebuilt from it (Task 11, test_tax_code_goods_relief.py).
        self.assertIn("te_tax_copy_relief_states = yes", self.copy)
        self.assertIn("te_tax_rebuild_relief_marks = yes", self.copy)
        self.assertNotRegex(self.copy, r"name = te_tax_(relief_state|pending_relief_[ab]) ")


class AdoptTest(unittest.TestCase):
    """te_tax.6: the carrier on a country that received a copied code, then a sync tomorrow."""

    @classmethod
    def setUpClass(cls):
        cls.parsed = load(EVENTS)
        cls.adopt = block(read(CIVIL_WAR_EFFECTS), "te_tax_adopt_copied_code")

    def test_event_is_a_hidden_rule_gated_country_event(self):
        body = self.parsed["te_tax.6"]
        self.assertEqual(body["type"], "country_event")
        self.assertEqual(body["hidden"], "yes")
        self.assertEqual(body["trigger"], {"te_tax_code_on": "yes"})
        self.assertEqual(body["immediate"], {"te_tax_adopt_copied_code": "yes"})

    def test_activates_the_carrier_only_if_absent_and_syncs_tomorrow(self):
        self.assertIn("te_tax_code_in_force = yes", self.adopt)
        self.assertRegex(self.adopt, r"limit = \{ NOT = \{ has_law = law_type:law_te_tax_code \} \}\s*"
                                     r"activate_law = law_type:law_te_tax_code")
        self.assertEqual(self.adopt.count("activate_law"), 1)
        self.assertIn("trigger_event = { id = te_tax.4 days = 1 }", self.adopt)
        self.assertNotIn("te_tax_sync_collection", self.adopt)

    def test_logs_whether_the_carrier_arrived(self):
        lines = re.findall(r'debug_log = "([^"]*)"', self.adopt)
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertTrue(line.startswith("TE_TAX adopted"))
            self.assertNotIn("$", line)
            self.assertNotIn("ROOT", line)

    def test_raised_only_by_the_civil_war_effects(self):
        self.assertEqual(raisers("te_tax.6"), [(CIVIL_WAR_EFFECTS, "te_tax.6")])

    def test_post_migration_sync_logs(self):
        immediate = self.parsed["te_tax.4"]["immediate"]
        self.assertEqual(immediate["te_tax_sync_collection"], "yes")
        self.assertTrue(immediate["debug_log"].strip('"').startswith("TE_TAX post-migration sync"))


class RepairTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.defined = effects()
        cls.repair = block(read(CIVIL_WAR_EFFECTS), "te_tax_repair_after_civil_war")
        cls.reach = closure({"te_tax_repair_after_civil_war"}, cls.defined)

    def test_runs_only_after_a_merge(self):
        # Rebels won a revolution, or the original government won; a seceder
        # that won is a new nation, nothing merged (cr_repair_after_civil_war).
        guard = self.repair[:self.repair.index("te_tax_bill_close")]
        self.assertIn("te_tax_code_in_force = yes", guard)
        self.assertIn("AND = { has_variable = te_cw_rebels_won var:te_cw_rebels_won = 1 }", guard)
        self.assertIn("AND = { has_variable = te_cw_role var:te_cw_role = 1 }", guard)

    def test_closes_the_bill_and_the_draft_and_hands_the_month_back(self):
        for phrase in ("te_tax_bill_close = yes", "te_tax_draft_close = yes", "te_tax_gen_reset_commitments = yes",
                       "set_variable = { name = te_tax_bl_on value = 0 }",
                       "set_variable = { name = te_tax_dr_on value = 0 }",
                       "set_variable = { name = te_tax_last_month value = -1 }",
                       "te_tax_history_push = { KIND = 7 SLOT = none }",
                       "te_tax_rebuild_relief_marks = yes",
                       "trigger_event = { id = te_tax.6 }"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.repair)

    def test_never_commences_bumps_a_version_or_rewards(self):
        for name in ("te_tax_process_month", "te_tax_watchdog_month", "te_tax_sync_collection",
                     "te_tax_gen_bump_pver", "te_tax_gen_oppose_approval", "te_tax_store_package",
                     *(f"te_tax_gen_{part}_{slot}" for part in ("commence", "apply", "store", "supersede")
                       for slot in SLOTS)):
            with self.subTest(name=name):
                self.assertNotIn(name, self.reach)
        for name in self.reach:
            body = self.defined[name]
            with self.subTest(name=name):
                self.assertNotRegex(body, r"name = te_tax_(xver|pver)_\w+ (value|add)")
                self.assertNotRegex(body, r"name = te_tax_code_version (value|add)")
                self.assertNotIn("ig_approval_effect", body)
                self.assertNotIn("add_modifier", body)
                self.assertNotIn("change_variable = { name = te_tax_drift", body)

    def test_obligations_hook_is_marked_for_task_12(self):
        raw = read(CIVIL_WAR_EFFECTS, strip_comments=False)
        self.assertIn("te_tax_repair_obligations_after_civil_war", raw)


class ReleaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.defined = effects()
        cls.release = block(read(CIVIL_WAR_EFFECTS), "te_tax_init_released_country")

    def test_copies_only_from_a_parent_holding_the_carrier(self):
        guard = self.release[:self.release.index("te_tax_gen_copy_enacted = yes")]
        self.assertIn("te_tax_code_on = yes", guard)
        self.assertRegex(guard, r"scope:te_tax_source = \{\s*te_tax_code_in_force = yes\s+"
                                r"has_law = law_type:law_te_tax_code\s*\}")

    def test_otherwise_migrates(self):
        fallback = self.release[self.release.index("else_if = {"):]
        self.assertIn("te_tax_code_on = yes", fallback)
        self.assertIn("trigger_event = { id = te_tax.3 }", fallback)

    def test_copies_exactly_the_enacted_provisions(self):
        expected = {f"te_tax_en_{key}{suffix}" for key in KEYS for suffix, _ in gen.INSTRUMENT_TOKENS}
        expected |= {f"te_tax_en_g_{good}" for good in catalog()} | {"te_tax_en_agrel", "te_tax_en_regrel"}
        self.assertEqual(set(COPY.findall(block(read(GEN_EFFECTS), "te_tax_gen_copy_enacted"))), expected)
        written = copied({"te_tax_init_released_country"}, self.defined) - copied({"te_tax_init_country"},
                                                                                     self.defined)
        self.assertEqual(written, expected)

    def test_starts_with_no_package_bill_or_draft(self):
        for name in ("te_tax_bl_on", "te_tax_dr_on", "te_tax_pa_on", "te_tax_pa_state", "te_tax_pb_on",
                     "te_tax_pb_state"):
            with self.subTest(name=name):
                self.assertIn(f"set_variable = {{ name = {name} value = 0 }}", self.release)

    def test_hands_the_month_to_the_dispatch_and_installs_the_carrier(self):
        for phrase in ("set_variable = { name = te_tax_last_month value = -1 }",
                       "te_tax_recompute_next_month = yes", "te_tax_copy_relief_states = yes",
                       "te_tax_rebuild_relief_marks = yes",
                       "trigger_event = { id = te_tax.6 }"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.release)
        copy_branch = self.release[:self.release.index("else_if = {")]
        last = copy_branch[copy_branch.rfind("set_variable"):]
        self.assertTrue(last.startswith("set_variable = { name = te_tax_migrated value = 1 }"))
        # te_tax.6 is gated on the code being in force; an event raised without
        # days may run at once, so it is raised only once te_tax_migrated is 1.
        self.assertLess(copy_branch.index("set_variable = { name = te_tax_migrated value = 1 }"),
                        copy_branch.index("trigger_event = { id = te_tax.6 }"))

    def test_the_parents_pending_relief_marks_are_dropped(self):
        for slot in SLOTS:
            with self.subTest(slot=slot):
                self.assertIn(f"set_variable = {{ name = te_tax_pending_relief_{slot} value = 0 }}", self.release)

    def test_no_history_and_no_version_change(self):
        self.assertNotIn("te_tax_history_push", self.release)
        self.assertNotIn("te_tax_code_version", self.release)


class ReliefEligibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(CIVIL_WAR_EFFECTS)
        cls.follow = block(cls.text, "te_tax_relief_follow_owner")
        cls.stays = block(read(TRIGGERS), "te_tax_relief_stays_with_code")

    def test_clears_every_mark_by_sentinel(self):
        clear = self.follow[self.follow.index("te_tax_relief_stays_with_code"):]
        for mark in STATE_MARKS:
            with self.subTest(mark=mark):
                self.assertIn(f"set_variable = {{ name = {mark} value = 0 }}", clear)
        self.assertNotIn("remove_variable", self.follow)
        self.assertRegex(self.follow, r"NOT = \{ te_tax_relief_stays_with_code = yes \}")

    def test_modifiers_are_left_to_the_new_owners_sync(self):
        self.assertNotRegex(self.follow, r"(add|remove)_modifier")

    def test_saves_the_new_owner_and_the_stamped_holder(self):
        self.assertIn("owner = { save_scope_as = te_tax_owner_new }", self.follow)
        self.assertIn("var:te_tax_relief_holder ?= { save_scope_as = te_tax_owner_holder }", self.follow)

    def test_the_code_travels_with_a_new_tag_the_holder_or_a_civil_war_side(self):
        for condition in (
                "OR = { NOT = { has_variable = te_tax_migrated } var:te_tax_migrated < 1 }",
                "scope:te_tax_owner_new = { this = scope:te_tax_owner_holder }",
                "country_definition = scope:te_tax_owner_holder.country_definition",
                "scope:te_tax_owner_new = { var:te_cw_origin ?= scope:te_tax_owner_holder }",
                "scope:te_tax_owner_holder = { var:te_cw_origin ?= scope:te_tax_owner_new }"):
            with self.subTest(condition=condition):
                self.assertIn(condition, " ".join(self.stays.split()))

    def test_flags_and_marks_are_stamped_where_they_are_set(self):
        # Commencement replaces the enacted list (Task 11) and sets no flag; the
        # rebuild derives each flag from the list and stamps it in the same block.
        generated = read(GEN_EFFECTS)
        stamp = "set_variable = { name = te_tax_relief_holder value = scope:te_tax_country }"
        rebuild = block(self.text, "te_tax_rebuild_relief_marks")
        flag = rebuild.index("set_variable = { name = te_tax_relief_state value = 1 }")
        self.assertEqual(rebuild[flag:].split("}", 1)[1].strip().split("\n")[0].strip(), stamp)
        self.assertLess(rebuild.index("save_scope_as = te_tax_country"), flag)
        for slot in SLOTS:
            with self.subTest(slot=slot):
                apply = block(generated, f"te_tax_gen_apply_{slot}")
                self.assertNotIn("name = te_tax_relief_state value = 1", apply)
                self.assertIn("te_tax_en_relief_states", apply)
                store = block(generated, f"te_tax_gen_store_{slot}")
                mark = store.index(f"set_variable = {{ name = te_tax_pending_relief_{slot} value = 1 }}")
                self.assertEqual(store[mark:].split("}", 1)[1].strip().split("\n")[0].strip(), stamp)

    def test_the_copies_and_the_repair_rebuild(self):
        restamp = block(self.text, "te_tax_rebuild_relief_marks")
        self.assertIn("save_scope_as = te_tax_country", restamp)
        self.assertIn("set_variable = { name = te_tax_relief_holder value = scope:te_tax_country }", restamp)
        for mark in STATE_MARKS:
            with self.subTest(mark=mark):
                self.assertIn(f"has_variable = {mark} var:{mark} = 1", " ".join(restamp.split()))

    def test_the_stamp_is_a_schema_state_variable(self):
        _, state = schema_tokens()
        self.assertIn("te_tax_relief_holder", state)


class SafetyTest(unittest.TestCase):
    def test_no_token_is_removed_and_root_is_never_read(self):
        text = read(CIVIL_WAR_EFFECTS)
        country, state = schema_tokens()
        for name in re.findall(r"remove_variable\s*=\s*(?:\{[^}]*?name\s*=\s*)?([\w$]+)", text):
            with self.subTest(name=name):
                self.assertNotIn(name, set(country) | set(state))
        self.assertNotRegex(text, r"\bROOT\b|\broot\b")

    def test_every_entry_point_is_gated_positively(self):
        text = read(CIVIL_WAR_EFFECTS)
        self.assertNotRegex(text, r"NOT = \{\s*te_tax_code_on")
        for name in ("te_tax_on_uprising", "te_tax_repair_after_civil_war", "te_tax_init_released_country",
                     "te_tax_adopt_copied_code"):
            with self.subTest(name=name):
                head = block(text, name)[:400]
                self.assertRegex(head, r"te_tax_code_(on|in_force) = yes")

    def test_debug_lines_carry_the_stamp_and_no_parameters(self):
        for line in re.findall(r'debug_log = "([^"]*)"', read(CIVIL_WAR_EFFECTS)):
            with self.subTest(line=line[:50]):
                self.assertTrue(line.startswith("TE_TAX "))
                self.assertNotIn("$", line)
                self.assertIn("date=[TimeKeeper.GetCurrentDate.GetString]", line)

    def test_file_has_bom_lf_tabs_and_formatter_parity(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import format_paradox_tabs
        finally:
            sys.path.pop(0)
        raw = (ROOT / CIVIL_WAR_EFFECTS).read_bytes()
        text = raw.decode("utf-8-sig")
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r", raw)
        self.assertNotRegex(text, r"(?m)^ +\S")
        self.assertEqual(format_paradox_tabs.format_text(text), text)


class DocTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = read(SCHEMA_DOC, strip_comments=False)

    def test_section_describes_the_rules(self):
        section = self.doc.split("\n## Civil wars and new countries\n", 1)[1].split("\n## ", 1)[0]
        for phrase in ("te_tax_on_uprising", "te_tax_repair_after_civil_war", "te_tax_init_released_country",
                       "te_tax.6", "te_tax_relief_holder", "on_state_owner_change", "te_tax_sync_version",
                       "kind 7", "on_law_activated", "country_definition", "Task 11", "Task 12"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)

    def test_balance_decisions_name_the_short_term_tax_cuts(self):
        balance = self.doc.split("\n## Balance decisions\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("amendment_short_term_tax_cuts", balance)

    def test_no_research_citations(self):
        for path in (TAX_ON_ACTIONS, SCHEMA_DOC):
            with self.subTest(path=path):
                self.assertNotRegex(read(path, strip_comments=False), r"\(research [A-F]\b")

    def test_hungarys_button_is_not_called_a_live_path(self):
        # It activates Per-Capita only from Land-Based, which no country holds
        # under the rule; restore_peruvian_constitution is the live one.
        for path in (TAX_ON_ACTIONS, SCHEMA_DOC):
            with self.subTest(path=path):
                text = read(path, strip_comments=False)
                self.assertIn("restore_peruvian_constitution", text)
                self.assertNotRegex(text, r"Hungary's Per-Capita button,")
        ledger = read(LEDGER, strip_comments=False)
        self.assertNotRegex(ledger, r"\| Hungary's Per-Capita button, `restore_peruvian_constitution`")


if __name__ == "__main__":
    unittest.main()
