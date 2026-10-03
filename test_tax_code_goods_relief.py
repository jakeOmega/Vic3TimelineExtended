# -*- coding: utf-8 -*-
"""The legislated tax code's goods and relief provisions in a bill (plan Task 11).

Structural checks on the committed script, GUI and loc (no game install needed):

* every consumption-catalog good has a support weight from its goods-file
  `category` (staple 1.0, industrial 0.3, luxury 0.2; military goods reach pops
  only through the leisure need and weigh as luxuries), and the material reason
  sees the bill's goods (0.2 level-steps per good x weight on the consumption
  channel) and its relief (agricultural: rural folk +8 and landowners +3 per
  band; regional: every group +4 and industrialists and petty bourgeoisie -2
  per band), clamped to -40..40 with the rest of the material reason;
* a draft changes agricultural and regional relief band by band, records the
  relief group's planned version at its first relief change and can be
  rebased on it; its first regional-relief change copies existing law's named
  states (the enacted list, or an awaiting package's that commences first);
* regional relief names at most three states, chosen from a candidate list of
  the player's incorporated states that only an explicit command builds; a
  relief that relieves names at least one;
* the bill copies the draft's states, the draft copies the bill's, and the
  draft differs from the bill when either names a state the other does not;
* the enacted named states are the country list te_tax_en_relief_states
  (controller ruling, Task 11): commencement replaces it, the writer's relief
  sync derives the state marks from it, prunes it by the same keep rule as
  the state-owner hook, and civil wars and releases copy it and rebuild;
* the counts-as triggers and the Traditionalism condition compare indices,
  with has_variable guards, never a script value on the left;
* relief labels say only what the capability ledger verified: no dividends.

Run: python3 -m unittest test_tax_code_goods_relief -v
"""

import re
import unittest
from decimal import Decimal
from pathlib import Path

from test_tax_code_layout import gui
from test_tax_code_state import block, catalog, gen, read, schema_tokens, top_level_names

ROOT = Path(__file__).resolve().parent

BILL = "common/scripted_effects/te_tax_bill_effects.txt"
GEN_BILL = "common/scripted_effects/te_tax_generated_bill_effects.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_generated_effects.txt"
COLLECTION = "common/scripted_effects/te_tax_collection_effects.txt"
CIVIL_WAR = "common/scripted_effects/te_tax_civil_war_effects.txt"
TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"
GEN_TRIGGERS = "common/scripted_triggers/te_tax_generated_triggers.txt"
GEN_SUPPORT = "common/script_values/te_tax_generated_support_values.txt"
GEN_VALUES = "common/script_values/te_tax_generated_values.txt"
DISPLAY = "common/script_values/te_tax_display_values.txt"
SUPPORT = "common/script_values/te_tax_support_values.txt"
SGUIS = "common/scripted_guis/te_tax_sguis.txt"
GEN_SGUIS = "common/scripted_guis/te_tax_generated_sguis.txt"
WORKBENCH = "gui/journal_entry_widgets/te_tax_workbench_widget.gui"
REVIEW = "gui/journal_entry_widgets/te_tax_review_widget.gui"
TAX_LOC = "localization/english/te_tax_l_english.yml"
SCHEMA_DOC = "docs/systems/tax_code_schema.md"

IGS = ("armed_forces", "devout", "industrialists", "intelligentsia",
       "landowners", "petty_bourgeoisie", "rural_folk", "trade_unions")
# The brief's tables, ported by hand.
CONS_EXPOSURE = {"trade_unions": "0.8", "rural_folk": "0.8", "petty_bourgeoisie": "0.6",
                 "intelligentsia": "0.4", "devout": "0.5", "armed_forces": "0.4",
                 "industrialists": "0.2", "landowners": "0.2"}
CATEGORY_WEIGHT = {"staple": Decimal("1.0"), "industrial": Decimal("0.3"),
                   "luxury": Decimal("0.2"), "military": Decimal("0.2")}
GOODS_LEVEL_STEPS = Decimal("0.2")
AGREL = {"rural_folk": 8, "landowners": 3}
REGREL_ALL, REGREL_CONCERN = 4, {"industrialists": -2, "petty_bourgeoisie": -2}
RELIEF_KEYS = ("agrel", "regrel")
MAX_STATES = 3
SLOTS = ("a", "b")


def squash(text):
    return " ".join(text.split())


def loc_entries():
    entries = {}
    for line in read(TAX_LOC, strip_comments=False).splitlines():
        match = re.match(r'^ ([\w.\-]+):\d+ "(.*)"$', line)
        if match:
            entries[match.group(1)] = match.group(2)
    return entries


class GoodsWeightTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = read(GEN_SUPPORT)
        cls.goods = gen.goods_definitions()

    def test_every_catalog_good_has_a_category_weight(self):
        for good in catalog():
            with self.subTest(good=good):
                self.assertIn(self.goods[good].get("category"), CATEGORY_WEIGHT)

    def test_each_good_moves_the_consumption_channel_by_its_weight(self):
        for good in catalog():
            weight = GOODS_LEVEL_STEPS * CATEGORY_WEIGHT[self.goods[good]["category"]]
            body = block(self.values, f"te_tax_dl_g_{good}")
            with self.subTest(good=good):
                self.assertIn(f"has_variable = te_tax_bl_g_{good}", body)
                self.assertIn(f"var:te_tax_bl_g_{good} >= 0", body)
                self.assertRegex(squash(body), rf"value = var:te_tax_bl_g_{good} subtract = te_tax_base_bl_g_{good} "
                                               rf"multiply = ([\d.]+)")
                found = re.search(r"multiply = ([\d.]+)", body)
                self.assertEqual(Decimal(found.group(1)), weight)
                # Existing law in the bill's month: the enacted flag, then awaiting packages.
                self.assertIn(f"te_tax_base_bl_g_{good}", top_level_names(self.values))
        total = block(self.values, "te_tax_dl_goods")
        self.assertEqual(set(re.findall(r"add = te_tax_dl_g_(\w+)", total)), set(catalog()))

    def test_military_goods_reach_pops_only_through_leisure(self):
        needs = gen.pop_need_goods()
        for good in catalog():
            if self.goods[good]["category"] == "military":
                with self.subTest(good=good):
                    self.assertEqual(needs[good], ("popneed_leisure",))


class MaterialReasonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = read(GEN_SUPPORT)

    def test_goods_join_the_consumption_channel_and_relief_counts_per_band(self):
        for ig in IGS:
            body = block(self.values, f"te_tax_mat_{ig}")
            flat = squash(body)
            with self.subTest(ig=ig):
                goods = re.search(r"add = \{ value = te_tax_dl_goods multiply = ([\d.]+) \}", flat)
                self.assertIsNotNone(goods)
                self.assertEqual(Decimal(goods.group(1)), Decimal(CONS_EXPOSURE[ig]))
                # The tax channels and goods are in tax levels (x -10); relief is in points.
                taxes, points = flat.split("multiply = -10", 1)
                self.assertIn("te_tax_dl_goods", taxes)
                agrel = [int(v) for v in re.findall(
                    r"add = \{ value = te_tax_bl_agrel_scaled multiply = (-?\d+) \}", points)]
                self.assertEqual(sum(agrel), AGREL.get(ig, 0))
                regrel = [int(v) for v in re.findall(
                    r"add = \{ value = te_tax_bl_regrel_coverage multiply = (-?\d+) \}", points)]
                self.assertEqual(sum(regrel), REGREL_ALL + REGREL_CONCERN.get(ig, 0))
                self.assertRegex(flat, r"min = -40 max = 40$")

    def test_relief_changes_are_measured_in_bands_from_existing_law(self):
        body = squash(block(self.values, "te_tax_bl_dstep_agrel"))
        self.assertIn("has_variable = te_tax_bl_agrel var:te_tax_bl_agrel >= 0", body)
        self.assertIn("value = var:te_tax_bl_agrel subtract = te_tax_base_bl_agrel", body)
        self.assertNotIn("te_tax_bl_dstep_regrel", self.values)    # regional relief scores by coverage
        for key in RELIEF_KEYS:
            with self.subTest(key=key):
                for record in ("dr", "bl"):
                    base = squash(block(self.values, f"te_tax_base_{record}_{key}"))
                    self.assertIn(f"value = var:te_tax_en_{key}", base)
                    self.assertIn(f"te_tax_slot_awaits_before = {{ SLOT = a DUE = te_tax_{record}_due }}", base)
                    self.assertIn(f"value = var:te_tax_pb_{key}", base)


class DraftReliefTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bill = read(BILL)
        cls.triggers = read(TRIGGERS)

    def test_relief_steps_band_by_band_behind_its_trigger(self):
        command = squash(block(self.bill, "te_tax_cmd_draft_relief"))
        self.assertTrue(command.startswith("if = { limit = { te_tax_can_draft_relief = { KEY = $KEY$ DIR = $DIR$ } }"))
        self.assertIn("te_tax_dr_relief_$DIR$ = { KEY = $KEY$ }", command)
        for direction in range(5):
            body = squash(block(self.bill, f"te_tax_dr_relief_{direction}"))
            with self.subTest(direction=direction):
                self.assertTrue(body.startswith("custom_tooltip = te_tax_tt_cmd_draft_relief_"))
                self.assertIn("te_tax_dr_relief_settle = yes", body)
                if direction < 4:
                    self.assertIn("te_tax_dr_relief_touch = { KEY = $KEY$ }", body)
        for key in RELIEF_KEYS:
            self.assertRegex(read(GEN_VALUES), rf"(?m)^te_tax_max_{key} = 2$")

    def test_the_first_relief_change_records_the_planned_version(self):
        touch = squash(block(self.bill, "te_tax_dr_relief_touch"))
        self.assertIn("limit = { var:te_tax_dr_agrel < 0 var:te_tax_dr_regrel < 0 } "
                      "set_variable = { name = te_tax_dr_relief_pver value = var:te_tax_pver_relief }", touch)
        self.assertIn("te_tax_dr_$KEY$_touch = yes", touch)
        settle = squash(block(self.bill, "te_tax_dr_relief_settle"))
        self.assertIn("set_variable = { name = te_tax_dr_relief_pver value = -1 }", settle)
        self.assertIn("limit = { var:te_tax_dr_regrel < 1 has_variable_list = te_tax_dr_relief_states } "
                      "clear_variable_list = te_tax_dr_relief_states", settle)

    def test_the_first_regional_change_copies_existing_laws_states(self):
        touch = squash(block(self.bill, "te_tax_dr_regrel_touch"))
        self.assertIn("set_variable = { name = te_tax_dr_regrel value = te_tax_base_dr_regrel }", touch)
        self.assertIn("clear_variable_list = te_tax_dr_relief_states", touch)
        # A package that commences before the draft and restates the states wins,
        # in commencement order (its own slot list); else the enacted list.
        for slot in SLOTS:
            self.assertIn(f"limit = {{ te_tax_relief_base_from_{slot} = {{ DUE = te_tax_dr_due }} }} "
                          f"te_tax_dr_copy_relief_states = {{ LIST = te_tax_p{slot}_relief_states }}", touch)
        self.assertIn("else = { te_tax_dr_copy_relief_states = { LIST = te_tax_en_relief_states } }", touch)
        copy = squash(block(self.bill, "te_tax_dr_copy_relief_states"))
        self.assertIn("limit = { has_variable_list = $LIST$ }", copy)
        self.assertIn("limit = { owner ?= scope:te_tax_country } scope:te_tax_country = { add_to_variable_list = { "
                      "name = te_tax_dr_relief_states target = PREV } }", copy)
        for slot in SLOTS:
            base = squash(block(self.triggers, f"te_tax_relief_base_from_{slot}"))
            with self.subTest(slot=slot):
                self.assertIn(f"te_tax_slot_restates_relief_before = {{ SLOT = {slot} DUE = $DUE$ }}", base)
                self.assertIn("te_tax_slot_b_first = yes", base)
        restates = squash(block(self.triggers, "te_tax_slot_restates_relief_before"))
        self.assertIn("te_tax_slot_awaits_before = { SLOT = $SLOT$ DUE = $DUE$ }", restates)
        self.assertIn("var:te_tax_p$SLOT$_regrel_states_set = 1", restates)

    def test_choosing_states_builds_the_candidates_from_incorporated_states(self):
        choose = squash(block(self.bill, "te_tax_cmd_draft_relief_choose"))
        self.assertTrue(choose.startswith("if = { limit = { te_tax_can_draft_relief_choose = yes }"))
        self.assertIn("te_tax_dr_relief_touch = { KEY = regrel }", choose)
        self.assertIn("clear_variable_list = te_tax_dr_relief_candidates", choose)
        self.assertRegex(choose, r"every_scope_state = \{ limit = \{ is_incorporated = yes \} .*"
                                 r"add_to_variable_list = \{ name = te_tax_dr_relief_candidates target = prev \}")

    def test_candidates_are_built_only_by_the_commands(self):
        writers = []
        for path in sorted((ROOT / "common").rglob("*.txt")) + sorted((ROOT / "events").rglob("*.txt")):
            text = path.read_text(encoding="utf-8-sig")
            if re.search(r"add_to_variable_list = \{ name = te_tax_dr_relief_candidates", text):
                writers.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(writers, [BILL])
        for path in (ROOT / "gui").rglob("*.gui"):
            text = path.read_text(encoding="utf-8-sig")
            for line in text.splitlines():
                if "te_tax_cmd_draft_relief_choose_sgui" in line:
                    with self.subTest(path=path.name, line=line.strip()[:60]):
                        self.assertRegex(line.strip(), r"^(enabled|onclick|tooltip) = ")

    def test_a_state_toggle_names_at_most_three(self):
        trigger = squash(block(self.triggers, "te_tax_can_draft_relief_state"))
        self.assertIn("exists = scope:te_tax_st", trigger)
        self.assertIn("var:te_tax_dr_regrel >= 0", trigger)
        self.assertIn(f"custom_tooltip = {{ text = te_tax_tt_relief_states_max NAND = {{ has_variable_list = "
                      f"te_tax_dr_relief_states any_in_list = {{ variable = te_tax_dr_relief_states count >= {MAX_STATES} "
                      f"exists = this }} }} }}", trigger)
        self.assertIn("scope:te_tax_st = { is_incorporated = yes owner = prev }", trigger)
        self.assertNotIn("variable_list_size", trigger)
        # Dropping a named state is always allowed; naming one is checked.
        self.assertIn("NAND = { has_variable_list = te_tax_dr_relief_states is_target_in_variable_list = { "
                      "name = te_tax_dr_relief_states target = scope:te_tax_st } }", trigger)
        toggle = squash(block(self.bill, "te_tax_cmd_draft_relief_state"))
        self.assertTrue(toggle.startswith("if = { limit = { te_tax_can_draft_relief_state = yes }"))
        self.assertIn("remove_list_variable = { name = te_tax_dr_relief_states target = scope:te_tax_st }", toggle)
        self.assertIn("add_to_variable_list = { name = te_tax_dr_relief_states target = scope:te_tax_st }", toggle)

    def test_a_relief_that_relieves_names_a_state(self):
        ready = squash(block(self.triggers, "te_tax_draft_ready"))
        self.assertIn("trigger_if = { limit = { var:te_tax_dr_regrel >= 1 } custom_tooltip = { "
                      "text = te_tax_tt_relief_states_named has_variable_list = te_tax_dr_relief_states "
                      "any_in_list = { variable = te_tax_dr_relief_states exists = this } } }", ready)

    def test_the_bill_names_at_most_three_states_all_its_own(self):
        """Fix round 1: the readiness guard repeats the toggle's limit, and a named
        state lost since it was named forces a revision (NAND, never a multi-child NOT)."""
        ready = squash(block(self.triggers, "te_tax_draft_ready"))
        self.assertIn("trigger_if = { limit = { has_variable_list = te_tax_dr_relief_states } "
                      "custom_tooltip = { text = te_tax_tt_relief_states_at_most NOT = { any_in_list = { "
                      f"variable = te_tax_dr_relief_states count >= {MAX_STATES + 1} exists = this }} }} }} "
                      "custom_tooltip = { text = te_tax_tt_relief_states_own NOT = { any_in_list = { "
                      "variable = te_tax_dr_relief_states NAND = { is_incorporated = yes owner = PREV } } } } }",
                      ready)

    def test_relief_can_be_rebased(self):
        current = squash(block(read(GEN_TRIGGERS), "te_tax_gen_draft_baseline_current"))
        self.assertIn("OR = { AND = { var:te_tax_dr_agrel < 0 var:te_tax_dr_regrel < 0 } "
                      "var:te_tax_dr_relief_pver = var:te_tax_pver_relief }", current)
        sgui = squash(block(read(SGUIS), "te_tax_cmd_draft_rebase_sgui"))
        self.assertIn("limit = { exists = scope:op scope:op = 7 } te_tax_can_draft_rebase = { KEY = relief }", sgui)
        self.assertIn("limit = { exists = scope:op scope:op = 7 } te_tax_cmd_draft_rebase = { KEY = relief }", sgui)
        self.assertIn("te_tax_view_dr_relief_rebase", gui(REVIEW))


class RecordListTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = read(GEN_BILL)

    def test_the_relief_version_is_part_of_both_records(self):
        for name in ("te_tax_gen_draft_init", "te_tax_gen_draft_clear"):
            self.assertIn("te_tax_dr_relief_pver", block(self.generated, name))
        self.assertIn("set_variable = { name = te_tax_bl_relief_pver value = var:te_tax_dr_relief_pver }",
                      block(self.generated, "te_tax_gen_bill_from_draft"))
        self.assertIn("set_variable = { name = te_tax_dr_relief_pver value = var:te_tax_bl_relief_pver }",
                      block(self.generated, "te_tax_gen_draft_from_bill"))

    def test_the_state_lists_are_copied_both_ways_and_cleared(self):
        for name, source, target in (("te_tax_gen_bill_from_draft", "dr", "bl"),
                                     ("te_tax_gen_draft_from_bill", "bl", "dr")):
            body = squash(block(self.generated, name))
            with self.subTest(name=name):
                clear = body.index(f"clear_variable_list = te_tax_{target}_relief_states")
                copy = body.index(f"variable = te_tax_{source}_relief_states")
                self.assertLess(clear, copy)
                self.assertIn(f"scope:te_tax_country = {{ add_to_variable_list = {{ name = te_tax_{target}_relief_states "
                              "target = PREV } }", body)
        clear = block(self.generated, "te_tax_gen_draft_clear")
        for name in ("te_tax_dr_relief_states", "te_tax_dr_relief_candidates"):
            self.assertIn(f"clear_variable_list = {name}", clear)
        self.assertIn("clear_variable_list = te_tax_dr_relief_states", block(self.generated, "te_tax_gen_draft_init"))

    def test_the_draft_differs_when_either_names_a_state_the_other_does_not(self):
        body = squash(block(read(GEN_TRIGGERS), "te_tax_gen_draft_differs_from_bill"))
        for mine, theirs in (("dr", "bl"), ("bl", "dr")):
            self.assertIn(f"any_in_list = {{ variable = te_tax_{mine}_relief_states PREV = {{ NOT = {{ "
                          f"is_target_in_variable_list = {{ name = te_tax_{theirs}_relief_states target = PREV }} }} }} }}",
                          body)


class CanonicalListTest(unittest.TestCase):
    """Controller ruling (Task 11): the enacted named states are the country list
    te_tax_en_relief_states; the state marks are derived from it."""

    @classmethod
    def setUpClass(cls):
        cls.generated = read(GEN_EFFECTS)
        cls.civil = read(CIVIL_WAR)
        cls.collection = read(COLLECTION)
        cls.triggers = read(TRIGGERS)

    def test_commencement_replaces_the_list_and_leaves_the_marks_to_the_sync(self):
        """Fix round 1: from the slot's own list, kept states only, the list consumed."""
        for slot in SLOTS:
            apply = squash(block(self.generated, f"te_tax_gen_apply_{slot}"))
            plist = f"te_tax_p{slot}_relief_states"
            with self.subTest(slot=slot):
                self.assertIn(f"limit = {{ var:te_tax_p{slot}_regrel_states_set = 1 }} save_scope_as = te_tax_country "
                              "if = { limit = { has_variable_list = te_tax_en_relief_states } "
                              "clear_variable_list = te_tax_en_relief_states }", apply)
                self.assertIn(f"every_in_list = {{ variable = {plist} limit = {{ te_tax_relief_listed_state_kept = yes }} "
                              "scope:te_tax_country = { add_to_variable_list = { name = te_tax_en_relief_states "
                              "target = PREV } } }", apply)
                self.assertTrue(apply.endswith(f"if = {{ limit = {{ has_variable_list = {plist} }} "
                                               f"clear_variable_list = {plist} }}"))
                self.assertNotIn("name = te_tax_relief_state value = 1", apply)

    def test_the_sync_rebuilds_the_marks_before_the_modifiers(self):
        relief = squash(block(self.collection, "te_tax_sync_relief"))
        self.assertLess(relief.index("te_tax_rebuild_relief_marks = yes"), relief.index("every_scope_state"))

    def test_the_rebuild_prunes_then_derives_and_stamps(self):
        rebuild = squash(block(self.civil, "te_tax_rebuild_relief_marks"))
        self.assertTrue(rebuild.startswith("save_scope_as = te_tax_country"))
        # Never remove from the list it iterates: collect, then remove.
        self.assertIn("every_in_list = { variable = te_tax_en_relief_states limit = { NOT = { "
                      "te_tax_relief_listed_state_kept = yes } } add_to_temporary_list = te_tax_relief_dropped }",
                      rebuild)
        # The temporary list lives for the whole top-level effect: test each again.
        self.assertIn("every_in_list = { list = te_tax_relief_dropped limit = { NOT = { "
                      "te_tax_relief_listed_state_kept = yes } } scope:te_tax_country = { "
                      "remove_list_variable = { name = te_tax_en_relief_states target = PREV } } }", rebuild)
        self.assertLess(rebuild.index("te_tax_relief_dropped"), rebuild.index("every_scope_state"))
        self.assertIn("set_variable = { name = te_tax_relief_state value = 0 }", rebuild)
        self.assertIn("set_variable = { name = te_tax_relief_state value = 1 } "
                      "set_variable = { name = te_tax_relief_holder value = scope:te_tax_country }", rebuild)
        self.assertNotIn("pending_relief", rebuild)
        self.assertNotIn("te_tax_restamp_relief", self.civil)

    def test_the_list_keeps_a_state_by_the_hooks_rule(self):
        kept = squash(block(self.triggers, "te_tax_relief_listed_state_kept"))
        for condition in ("owner = scope:te_tax_country",
                          "owner = { country_definition = scope:te_tax_country.country_definition }",
                          "owner = { var:te_cw_origin ?= scope:te_tax_country }",
                          "owner = { scope:te_tax_country = { var:te_cw_origin ?= prev } }"):
            with self.subTest(condition=condition):
                self.assertIn(condition, kept)

    def test_civil_wars_and_releases_copy_the_list_and_rebuild(self):
        copy = squash(block(self.civil, "te_tax_copy_code"))
        self.assertLess(copy.index("te_tax_copy_relief_states = yes"), copy.index("te_tax_rebuild_relief_marks = yes"))
        release = squash(block(self.civil, "te_tax_init_released_country"))
        self.assertLess(release.index("te_tax_copy_relief_states = yes"),
                        release.index("te_tax_rebuild_relief_marks = yes"))
        repair = squash(block(self.civil, "te_tax_repair_after_civil_war"))
        self.assertIn("te_tax_rebuild_relief_marks = yes", repair)
        self.assertNotIn("te_tax_copy_relief_states", repair)       # the winner's own list
        lists = squash(block(self.civil, "te_tax_copy_relief_states"))
        self.assertIn("clear_variable_list = te_tax_en_relief_states", lists)
        self.assertIn("scope:te_tax_source = { every_in_list = { variable = te_tax_en_relief_states", lists)

    def test_a_captured_state_leaves_the_holders_list(self):
        follow = squash(block(self.civil, "te_tax_relief_follow_owner"))
        cleared = follow[follow.index("NOT = { te_tax_relief_stays_with_code = yes }"):]
        self.assertIn("scope:te_tax_owner_holder = { remove_list_variable = { name = te_tax_en_relief_states "
                      "target = scope:te_tax_relief_moved } }", cleared)

    def test_the_schema_doc_lists_the_relief_lists(self):
        doc = read(SCHEMA_DOC, strip_comments=False)
        for name in ("te_tax_en_relief_states", "te_tax_dr_relief_states", "te_tax_dr_relief_candidates",
                     "te_tax_dr_relief_pver", "te_tax_rebuild_relief_marks"):
            with self.subTest(name=name):
                self.assertIn(name, doc)
        self.assertNotIn("Known limit, for Task 11", doc)
        country, _ = schema_tokens()
        self.assertNotIn("te_tax_en_relief_states", country, "a list is not a token")


class SlotListTest(unittest.TestCase):
    """Fix round 1 (controller ruling): a package's regional-relief states are its
    slot's country list te_tax_p<slot>_relief_states, never marks on the states, so a
    civil war's winner (which inherits no list) commences only its own packages'."""

    @classmethod
    def setUpClass(cls):
        cls.generated = read(GEN_EFFECTS)
        cls.bill_generated = read(GEN_BILL)

    def test_no_package_marks_remain(self):
        for path in sorted((ROOT / "common").rglob("*.txt")) + sorted((ROOT / "events").rglob("*.txt")) + \
                sorted((ROOT / "gui").rglob("*.gui")):
            with self.subTest(path=path.name):
                self.assertNotIn("pending_relief", path.read_text(encoding="utf-8-sig"))

    def test_the_store_copies_the_bills_states_into_the_slot_list(self):
        for slot in SLOTS:
            store = squash(block(self.generated, f"te_tax_gen_store_{slot}"))
            plist = f"te_tax_p{slot}_relief_states"
            with self.subTest(slot=slot):
                self.assertLess(store.index(f"clear_variable_list = {plist}"),
                                store.index("variable = te_tax_bl_relief_states"))
                self.assertIn(f"every_in_list = {{ variable = te_tax_bl_relief_states scope:te_tax_country = "
                              f"{{ add_to_variable_list = {{ name = {plist} target = PREV }} }} }}", store)

    def test_every_way_a_slot_frees_empties_its_list(self):
        for slot in SLOTS:
            plist = f"te_tax_p{slot}_relief_states"
            clear = f"if = {{ limit = {{ has_variable_list = {plist} }} clear_variable_list = {plist} }}"
            supersede = squash(block(self.bill_generated, f"te_tax_gen_supersede_{slot}"))
            with self.subTest(slot=slot):
                # Dropping the package's regional relief, and emptying the package.
                self.assertEqual(supersede.count(clear), 2)
                self.assertIn(clear, squash(block(self.generated, f"te_tax_gen_apply_{slot}")))
        release = squash(block(read(BILL), "te_tax_cmd_package_release"))
        self.assertIn("if = { limit = { has_variable_list = te_tax_p$SLOT$_relief_states } "
                      "clear_variable_list = te_tax_p$SLOT$_relief_states }", release)

    def test_existing_laws_states_come_from_the_slot_list(self):
        view = squash(block(read(DISPLAY), "te_tax_view_dr_relief_base_state"))
        for slot in SLOTS:
            self.assertIn(f"owner = {{ te_tax_relief_base_from_{slot} = {{ DUE = te_tax_dr_due }} }}", view)
            self.assertIn(f"is_target_in_variable_list = {{ name = te_tax_p{slot}_relief_states target = PREV }}", view)
        self.assertIn("is_target_in_variable_list = { name = te_tax_en_relief_states target = PREV }", view)

    def test_list_operations_test_the_list_first(self):
        """Fix round 1 minor 6: clear_variable_list and list reads behind has_variable_list."""
        for path in (BILL, CIVIL_WAR, GEN_BILL, GEN_EFFECTS):
            text = squash(read(path))
            for match in re.finditer(r"clear_variable_list = ([\w$]+)", text):
                with self.subTest(path=path, at=match.start()):
                    self.assertTrue(text[:match.start()].endswith(f"has_variable_list = {match.group(1)} }} "),
                                    text[max(0, match.start() - 80):match.end()])


class CoverageTest(unittest.TestCase):
    """Fix round 1 (controller ruling; spec 7.2, coverage matters): regional relief
    scores per band and share of the population named, agricultural relief per band
    and the wage tax it relieves. Read only by the support refresh."""

    @classmethod
    def setUpClass(cls):
        cls.support = read(SUPPORT)

    def test_reference_constants(self):
        self.assertRegex(self.support, r"(?m)^te_tax_regrel_ref_share = 0\.25$")
        self.assertRegex(self.support, r"(?m)^te_tax_agrel_ref_wage_idx = 4$")

    def test_the_bills_population_share(self):
        share = squash(block(self.support, "te_tax_bl_relief_pop_share"))
        self.assertIn("limit = { has_variable_list = te_tax_bl_relief_states total_population > 0 }", share)
        self.assertIn("every_in_list = { variable = te_tax_bl_relief_states limit = { exists = owner owner = prev } "
                      "add = state_population }", share)
        self.assertIn("divide = total_population", share)

    def test_existing_laws_population_share_follows_the_slot_precedence(self):
        base = squash(block(self.support, "te_tax_base_bl_relief_pop_share"))
        self.assertIn("total_population > 0", base)
        order = [base.index(f"te_tax_relief_base_from_{slot} = {{ DUE = te_tax_bl_due }}") for slot in SLOTS]
        order.append(base.index("variable = te_tax_en_relief_states"))
        self.assertEqual(order, sorted(order))
        for slot in SLOTS:
            self.assertIn(f"every_in_list = {{ variable = te_tax_p{slot}_relief_states limit = {{ exists = owner "
                          "owner = prev } add = state_population }", base)

    def test_regional_coverage_formula(self):
        body = squash(block(self.support, "te_tax_bl_regrel_coverage"))
        self.assertEqual(body, "value = 0 if = { limit = { has_variable = te_tax_bl_regrel var:te_tax_bl_regrel >= 0 } "
                               "add = { value = var:te_tax_bl_regrel multiply = te_tax_bl_relief_pop_share } "
                               "subtract = { value = te_tax_base_bl_regrel multiply = te_tax_base_bl_relief_pop_share } "
                               "divide = te_tax_regrel_ref_share }")
        # One band over a quarter of the population, where there was none: the full points.
        self.assertEqual((Decimal(1) * Decimal("0.25") - 0) / Decimal("0.25"), 1)

    def test_agricultural_relief_scales_with_the_wage_tax(self):
        factor = squash(block(self.support, "te_tax_bl_agrel_wage_factor"))
        self.assertEqual(factor, "value = te_tax_base_bl_wage if = { limit = { has_variable = te_tax_bl_wage "
                                 "var:te_tax_bl_wage >= 0 } value = var:te_tax_bl_wage } "
                                 "divide = te_tax_agrel_ref_wage_idx max = 1 min = 0")
        scaled = squash(block(self.support, "te_tax_bl_agrel_scaled"))
        self.assertEqual(scaled, "value = te_tax_bl_dstep_agrel multiply = te_tax_bl_agrel_wage_factor")
        for wage, expected in ((0, 0), (2, Decimal("0.5")), (4, 1), (12, 1)):
            self.assertEqual(max(0, min(1, Decimal(wage) / 4)), expected)

    def test_no_panel_reaches_the_list_iterations(self):
        """The shares iterate a list: only the material reason (the refresh) reads them."""
        hidden = ("te_tax_bl_relief_pop_share", "te_tax_base_bl_relief_pop_share", "te_tax_bl_regrel_coverage",
                  "te_tax_bl_agrel_scaled", "te_tax_mat_")
        surfaces = [path.read_text(encoding="utf-8-sig") for path in (ROOT / "gui").rglob("*.gui")]
        surfaces += [read(TAX_LOC, strip_comments=False), read(DISPLAY), read(GEN_VALUES), read(SGUIS),
                     read(GEN_SGUIS)]
        for name in hidden:
            for text in surfaces:
                with self.subTest(name=name):
                    self.assertNotIn(name, text)
        readers = {name for name in top_level_names(read(GEN_SUPPORT))
                   if "te_tax_bl_regrel_coverage" in block(read(GEN_SUPPORT), name)}
        # Task 13: the fiscal reason's revenue direction subtracts relief granted.
        self.assertEqual(readers, {f"te_tax_mat_{ig}" for ig in IGS} | {"te_tax_dl_revenue"})
        refresh = block(read(GEN_BILL), "te_tax_gen_refresh_support")
        for ig in IGS:
            self.assertIn(f"set_variable = {{ name = te_tax_sr_{ig}_mat value = te_tax_mat_{ig} }}", refresh)


class IndexComparisonTest(unittest.TestCase):
    """Task 9 review, Task 11 ruling: indices with has_variable guards, no script
    value on a trigger's left."""

    @classmethod
    def setUpClass(cls):
        cls.triggers = read(TRIGGERS)

    def test_counts_as_triggers_compare_enacted_indices(self):
        expected = {
            "per_capita": ("var:te_tax_en_head >= 1", "var:te_tax_en_wage >= 1"),
            "proportional": ("var:te_tax_en_wage >= 4", "var:te_tax_en_div >= 1"),
            "graduated": ("var:te_tax_en_wage >= 4", "var:te_tax_en_div >= var:te_tax_en_wage"),
        }
        for kind, conditions in expected.items():
            body = squash(block(self.triggers, f"te_tax_code_counts_as_{kind}"))
            with self.subTest(kind=kind):
                for condition in conditions:
                    self.assertIn(condition, body)
                for var in set(re.findall(r"var:(\w+)", body)):
                    self.assertIn(f"has_variable = {var}", body)
                self.assertNotIn("te_tax_view_", body)

    def test_traditionalism_holds_the_drafts_wage_and_dividend_index_at_zero(self):
        ready = squash(block(self.triggers, "te_tax_draft_ready"))
        tradition = ready[ready.index("has_law = law_type:law_traditionalism"):]
        for key in ("wage", "div"):
            self.assertIn(f"OR = {{ var:te_tax_dr_{key} = 0 var:te_tax_dr_{key} <= te_tax_dr_zero_limit_{key} }}",
                          tradition)
        self.assertNotIn("te_tax_dr_eff_wage <", ready)
        self.assertNotIn("te_tax_dr_eff_div <", ready)

    def test_the_zero_limit_admits_exactly_an_effective_zero(self):
        """value = base, max = 1, multiply = -1, add = -1: -1 when existing law has
        no such tax, -2 when it has. An untouched provision (-1) then passes exactly
        when the baseline is 0; a touched one only at 0."""
        for key in ("wage", "div"):
            body = squash(block(read(GEN_SUPPORT), f"te_tax_dr_zero_limit_{key}"))
            self.assertEqual(body, f"value = te_tax_base_dr_{key} max = 1 multiply = -1 add = -1")
        for base in range(0, 6):
            limit = -min(base, 1) - 1
            for draft in range(-1, 6):
                effective = base if draft < 0 else draft
                with self.subTest(base=base, draft=draft):
                    self.assertEqual(draft == 0 or draft <= limit, effective == 0)


class LabelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = loc_entries()

    def test_relief_rows_say_what_the_ledger_verified(self):
        self.assertIn("Halves (or cuts by a quarter) the wage tax for workers in agricultural buildings",
                      self.loc["te_tax_en_agrel_tt"])
        self.assertIn("Reduces all taxes collected from pops in the named states", self.loc["te_tax_en_regrel_tt"])

    def test_no_relief_text_mentions_dividends(self):
        keys = [key for key in self.loc if re.search(r"agrel|regrel|relief", key)]
        self.assertGreaterEqual(len(keys), 20)
        for key in keys:
            with self.subTest(key=key):
                self.assertNotIn("dividend", self.loc[key].lower())

    def test_the_review_names_beneficiaries_and_foregone_revenue(self):
        review = gui(REVIEW)
        for key in ("te_tax_rv_relief_benefit", "te_tax_rv_relief_forgoes", "te_tax_rv_agrel_benefit",
                    "te_tax_rv_agrel_forgoes", "te_tax_rv_regrel_benefit", "te_tax_rv_regrel_forgoes"):
            with self.subTest(key=key):
                self.assertIn(key, self.loc)
        for key in ("te_tax_rv_agrel_benefit", "te_tax_rv_agrel_forgoes", "te_tax_rv_regrel_benefit",
                    "te_tax_rv_regrel_forgoes"):
            self.assertIn(key, review)
        self.assertIn("GetList('te_tax_dr_relief_states')", review)


class WorkbenchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workbench = gui(WORKBENCH)

    def test_relief_rows_step_through_their_handlers(self):
        for key in RELIEF_KEYS:
            with self.subTest(key=key):
                self.assertIn(f"datacontext = \"[GetScriptedGui('te_tax_relief_{key}_sgui')]\"", self.workbench)
                handler = squash(block(read(GEN_SGUIS), f"te_tax_relief_{key}_sgui"))
                for op in range(5):
                    self.assertIn(f"limit = {{ exists = scope:op scope:op = {op} }} "
                                  f"te_tax_can_draft_relief = {{ KEY = {key} DIR = {op} }}", handler)

    def test_candidates_are_a_datamodel_over_the_built_list(self):
        self.assertIn("datamodel = \"[GetPlayer.MakeScope.GetList('te_tax_dr_relief_candidates')]\"", self.workbench)
        self.assertIn("datacontext = \"[Scope.GetState]\"", self.workbench)
        self.assertIn("AddScope( 'te_tax_st', State.MakeScope )", self.workbench)
        # Fix round 1 minor 3: the draft's own rows are the draft's by construction.
        draft_rows = self.workbench[self.workbench.index("GetList('te_tax_dr_relief_states')"):]
        draft_rows = squash(draft_rows[:draft_rows.index("te_tax_cmd_draft_relief_choose_sgui")])
        self.assertIn("blockoverride \"state_status\" { text = \"te_tax_wb_relief_state_named\" }", draft_rows)
        self.assertIn("blockoverride \"state_button_text\" { text = \"te_tax_wb_relief_state_drop\" }", draft_rows)
        # Fix round 1 minor 7: no standing explanation in the live section.
        self.assertNotIn("te_tax_wb_relief_note", self.workbench)
        handler = squash(block(read(SGUIS), "te_tax_relief_state_sgui"))
        self.assertIn("saved_scopes = { te_tax_st }", handler)
        self.assertIn("is_valid = { te_tax_can_draft_relief_state = yes }", handler)
        self.assertIn("effect = { te_tax_cmd_draft_relief_state = yes }", handler)


if __name__ == "__main__":
    unittest.main()
