# -*- coding: utf-8 -*-
"""Offers, commitments and political consequences of the legislated tax code
(plan Task 13; spec §7.2-7.4 and §8 steps 1-4).

Structural checks on the committed script (no game install needed):

* offers: one per non-committed, non-marginal interest group per bill
  revision, chosen only at the support refresh (never from a GUI) from the
  group's top negative reason; a group at its red line is offered promises
  only; the catalog is the brief's (schools, health, bureaucracy balance and
  fiscal balance promises; agricultural relief), with clauses that only soften
  what the bill changes (controller ruling): a cut lowers by one step the raise
  that is the group's top grievance, never below existing law; a staple offer
  takes back a staple the bill adds; neither empties the bill;
* anti-farming: an offer is recorded for one revision (te_tax_off_<ig>_rev)
  and reset with the commitments; a clause a group gained in this bill is
  never offered to it again (te_tax_bl_got_<ig>_<c>); a promise is offered
  and accepted only when te_tax_can_obl_propose holds (no identical pending or
  binding obligation), and it adds support only while its pending obligation
  is live;
* accepting any offer is a new revision: the offer is read into locals, the
  bill (and the draft) changes or the promise is recorded on the bill, the
  revision is bumped, commitments and pending promises are released, every
  promise accepted under this bill is proposed again, the accepting group
  commits (unless it was at its red line) and support is refreshed; a
  revision from the draft drops the accepted promises and clause records;
* _prom is recomputed from the bill's promise records at every refresh
  (+20, or +8 for a maintenance-only promise; side effects from the groups'
  stances on the institution's "none" law), never accumulated;
* the fiscal reason sees goods and relief, and the ideology reason counts
  taxing staples as regressive;
* interest-group views of the enacted code (controller ruling): a group's band
  is its own vanilla stance toward the vanilla taxation law the code is
  equivalent to (graduated, proportional, per-capita, land-based,
  consumption-based, through the counts-as triggers); at most one static
  modifier per group (none at band 0) carrying vanilla's approval from a law
  stance, swapped only when the band changes, from one refresh site in the
  monthly processor; every migrated row maps back to its own law, so the
  migration changes no approval;
* force-through reuses the mod's forced-law modifiers and cost script values
  and invents none, and its trigger lists every condition.

Run: python3 -m unittest test_tax_code_offers -v
"""

import re
import unittest
from decimal import Decimal
from pathlib import Path

from test_tax_code_rule import load
from test_tax_code_state import KEYS, block, catalog, close, gen, read, schema_tokens

ROOT = Path(__file__).resolve().parent

OFFERS = "common/scripted_effects/te_tax_offer_effects.txt"
BILL = "common/scripted_effects/te_tax_bill_effects.txt"
SCHEDULE = "common/scripted_effects/te_tax_schedule_effects.txt"
EVENTS = "events/te_tax_internal_events.txt"
MIGRATION = "common/scripted_effects/te_tax_migration_effects.txt"
CIVIL_WAR = "common/scripted_effects/te_tax_civil_war_effects.txt"
STATE = "common/scripted_effects/te_tax_state_effects.txt"
TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"
SUPPORT = "common/script_values/te_tax_support_values.txt"
GEN_BILL = "common/scripted_effects/te_tax_generated_bill_effects.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_generated_effects.txt"
GEN_TRIGGERS = "common/scripted_triggers/te_tax_generated_triggers.txt"
GEN_SUPPORT = "common/script_values/te_tax_generated_support_values.txt"
GEN_VALUES = "common/script_values/te_tax_generated_values.txt"
GEN_CUSTOM_LOC = "common/customizable_localization/te_tax_generated_custom_loc.txt"
GEN_MODIFIERS = "common/static_modifiers/te_tax_generated_modifiers.txt"
SGUIS = "common/scripted_guis/te_tax_sguis.txt"
POLITICS = "gui/journal_entry_widgets/te_tax_politics_widget.gui"
EXTRA_MODIFIERS = "common/static_modifiers/extra_modifiers.txt"
EXTRA_VALUES = "common/script_values/extra_script_values.txt"
SCHEMA_DOC = "docs/systems/tax_code_schema.md"
AUTO_GENERATED_DOC = "docs/auto_generated_files.md"
NIGHTLY_SELECT = "scripts/nightly_audit_select.py"

IGS = ("armed_forces", "devout", "industrialists", "intelligentsia",
       "landowners", "petty_bourgeoisie", "rural_folk", "trade_unions")
# Offer kinds (te_tax_off_<ig>_kind): clauses 1-3; a promise is 10 + its obligation kind.
CUT, AGREL, STAPLE = 1, 2, 3
SCHOOLS, HEALTH, BUREAUCRACY, FISCAL = (1, 1), (1, 2), (2, 0), (4, 0)
# The brief's catalog, ported by hand: who may be offered what.
CLAUSES = {
    "trade_unions": (CUT, STAPLE),
    "rural_folk": (CUT, STAPLE, AGREL),
    "petty_bourgeoisie": (CUT,), "intelligentsia": (CUT,), "devout": (CUT,),
    "armed_forces": (CUT,), "industrialists": (CUT,), "landowners": (CUT,),
}
PROMISES = {
    SCHOOLS: ("devout", "intelligentsia", "rural_folk"),
    HEALTH: ("trade_unions",),
    BUREAUCRACY: ("industrialists", "petty_bourgeoisie"),
    FISCAL: ("industrialists", "landowners"),
}
# The support model's exposure table (test_tax_code_bill.py's port): the channels a
# group pays any of are the ones a cut offer can lower.
PAYS = {"trade_unions": ("wage", "head", "cons"), "rural_folk": KEYS, "petty_bourgeoisie": KEYS,
        "intelligentsia": ("wage", "div", "head", "cons"), "devout": KEYS, "armed_forces": KEYS,
        "industrialists": ("wage", "div", "head", "cons"), "landowners": KEYS}
STAPLES = {"clothes", "electricity", "fabric", "fish", "furniture", "grain", "groceries", "paper",
           "services", "transportation", "wood"}
BANDS = {"m2": -2, "m1": -1, "p1": 1, "p2": 2}
# The vanilla taxation law each equivalence trigger names, in the ruling's order.
EQUIVALENT = (("graduated", "law_graduated_taxation"), ("proportional", "law_proportional_taxation"),
              ("per_capita", "law_per_capita_based_taxation"), ("land_based", "law_land_based_taxation"),
              ("consumption_based", "law_consumption_based_taxation"))
INSTALLED_DEFINES = Path("/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/common/defines/00_defines.txt")


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def sub_block(body, field):
    """The `{ ... }` body of the first `field = {` in `body`."""
    match = re.search(rf"\b{field} = \{{", body)
    assert match, f"no {field}"
    return body[match.end():close(body, match.end() - 1)]


def blocks_of(body, opener):
    """Every `opener = { ... }` body in `body`, at any depth."""
    out = []
    for match in re.finditer(rf"\b{opener} = \{{", body):
        out.append(body[match.end():close(body, match.end() - 1)])
    return out


def gui(path):
    return re.sub(r"(?m)^\s*#.*$", "", (ROOT / path).read_text(encoding="utf-8-sig"))


def loc():
    keys = {}
    for path in sorted((ROOT / "localization/english").glob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            match = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
            if match:
                keys[match.group(1)] = match.group(2)
    return keys


def selection(ig):
    """The generated selection branch for one group (te_tax_gen_offer_select)."""
    body = block(read(GEN_BILL), "te_tax_gen_offer_select")
    marker = f"# {ig}:"
    start = read(GEN_BILL, strip_comments=False)
    whole = block(start, "te_tax_gen_offer_select")
    at = whole.index(marker)
    nxt = [whole.index(f"# {other}:") for other in IGS if other != ig and whole.index(f"# {other}:") > at]
    part = whole[at:min(nxt) if nxt else len(whole)]
    assert body
    return re.sub(r"#[^\n]*", "", part)


class FilesTest(unittest.TestCase):
    def test_new_files_have_bom_lf_tabs_and_formatter_parity(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import format_paradox_tabs
        finally:
            sys.path.pop(0)
        for path in (OFFERS, GEN_MODIFIERS):
            raw = (ROOT / path).read_bytes()
            text = raw.decode("utf-8-sig")
            with self.subTest(path=path):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertNotIn(b"\r", raw)
                self.assertNotRegex(text, r"(?m)^ +\S")
                self.assertEqual(format_paradox_tabs.format_text(text), text)

    def test_generated_modifiers_are_registered(self):
        self.assertIn(GEN_MODIFIERS, gen.OUTPUTS)
        self.assertIn(gen.HEADER, (ROOT / GEN_MODIFIERS).read_text(encoding="utf-8-sig").splitlines()[:2])
        self.assertIn(f"`{GEN_MODIFIERS}`", read(AUTO_GENERATED_DOC, strip_comments=False))
        self.assertIn(f'"{GEN_MODIFIERS}"', read(NIGHTLY_SELECT, strip_comments=False))

    def test_debug_lines_carry_the_stamp_and_no_parameters(self):
        lines = re.findall(r'debug_log = "([^"]*)"', read(OFFERS))
        self.assertTrue(lines)
        for line in lines:
            with self.subTest(line=line[:50]):
                self.assertTrue(line.startswith("TE_TAX "))
                self.assertNotIn("$", line)
                self.assertIn("date=[TimeKeeper.GetCurrentDate.GetString]", line)

    def test_never_reads_root(self):
        self.assertNotRegex(read(OFFERS), r"\bROOT\b|\broot\b")

    def test_every_tooltip_key_is_localised(self):
        table = loc()
        keys = set(re.findall(r"custom_tooltip = (te_tax_tt_[\w$]+)", read(OFFERS)))
        keys |= set(re.findall(r"text = (te_tax_tt_(?:offer|force)\w*)", read(TRIGGERS)))
        self.assertIn("te_tax_tt_cmd_accept_offer", keys)
        self.assertIn("te_tax_tt_cmd_force_through", keys)
        for key in sorted(keys):
            with self.subTest(key=key):
                if "$" in key:
                    continue
                self.assertTrue(table.get(key), key)
        for instrument in KEYS:
            self.assertTrue(table.get(f"te_tax_tt_offer_cut_{instrument}"), instrument)
        for good in STAPLES:
            self.assertTrue(table.get(f"te_tax_tt_offer_untax_{good}"), good)


class CatalogTest(unittest.TestCase):
    def test_staples_and_their_order(self):
        self.assertEqual(set(gen.staple_order()), STAPLES)
        self.assertEqual(gen.staple_order()[0], "grain", "grain carries vanilla's highest tax cost")

    def test_each_group_is_offered_the_brief_catalog(self):
        for ig in IGS:
            part = selection(ig)
            kinds = set(int(k) for k in re.findall(rf"name = te_tax_off_{ig}_kind value = (\d+)", part))
            want = set(CLAUSES[ig]) | {10 + kind for (kind, _), groups in PROMISES.items() if ig in groups}
            with self.subTest(ig=ig):
                self.assertEqual(kinds - {0}, want)
                self.assertEqual(tuple(gen.grievance_keys(ig)), PAYS[ig])


class ClauseRulingTest(unittest.TestCase):
    """Controller ruling 3: a clause only softens what the bill changes, or adds relief."""

    def test_a_grievance_is_only_a_raise_above_existing_law(self):
        values = read(GEN_SUPPORT)
        for ig in IGS:
            for key in PAYS[ig]:
                body = norm(block(values, f"te_tax_bl_grief_{ig}_{key}"))
                with self.subTest(ig=ig, key=key):
                    self.assertRegex(body, rf"^value = 0 if = \{{ limit = \{{ te_tax_bl_dstep_{key} > 0 \}} "
                                           rf"value = te_tax_dl_{key} multiply = [\d.]+ \}}$")
            if "cons" in PAYS[ig]:
                goods = norm(block(values, f"te_tax_bl_grief_{ig}_goods"))
                self.assertRegex(goods, r"^value = 0 if = \{ limit = \{ te_tax_dl_goods > 0 \} "
                                        r"value = te_tax_dl_goods multiply = [\d.]+ \}$")

    def test_a_cut_targets_the_top_grievance_and_never_empties_the_bill(self):
        for ig in IGS:
            part = norm(selection(ig))
            for key in PAYS[ig]:
                grief = f"te_tax_bl_grief_{ig}"
                others = " ".join(f"{grief}_{key} >= {grief}_{other}" for other in PAYS[ig] if other != key)
                goods = f" {grief}_{key} >= {grief}_goods" if "cons" in PAYS[ig] else ""
                with self.subTest(ig=ig, key=key):
                    self.assertIn(f"{grief}_{key} > 0 {others}{goods} te_tax_offer_cut_leaves_a_bill = {{ KEY = {key} }} }} "
                                  f"set_variable = {{ name = te_tax_off_{ig}_kind value = {CUT} }} "
                                  f"set_variable = {{ name = te_tax_off_{ig}_arg value = {KEYS.index(key) + 1} }}", part)
            # No cut of a tax the group pays none of, and no cut from an unchanged rate.
            for key in set(KEYS) - set(PAYS[ig]):
                self.assertNotIn(f"te_tax_bl_grief_{ig}_{key}", part)
            self.assertNotIn("te_tax_bl_eff_", part.replace("te_tax_bl_eff_agrel", "").replace("te_tax_bl_eff_wage", ""))
        leaves = norm(block(read(TRIGGERS), "te_tax_offer_cut_leaves_a_bill"))
        # A customs level the bill changes keeps a bill too (Task 15).
        self.assertEqual(leaves, "OR = { te_tax_bl_dstep_$KEY$ >= 2 te_tax_bl_changed_provisions >= 2 "
                                 "te_tax_bl_goods_changed >= 1 NOT = { te_tax_bl_dstep_agrel = 0 } "
                                 "te_tax_bl_regrel_differs = yes te_tax_bl_customs_changed >= 1 }")

    def test_only_changes_from_existing_law_keep_a_bill(self):
        """Fix round 1: a restatement of existing law is not a change."""
        values = read(GEN_SUPPORT)
        changed = norm(block(values, "te_tax_bl_changed_provisions"))
        for key in KEYS:
            self.assertIn(f"if = {{ limit = {{ NOT = {{ te_tax_bl_dstep_{key} = 0 }} }} add = 1 }}", changed)
        goods = norm(block(values, "te_tax_bl_goods_changed"))
        for good in catalog():
            self.assertIn(f"if = {{ limit = {{ NOT = {{ te_tax_dl_g_{good} = 0 }} }} add = 1 }}", goods)
        self.assertNotIn("te_tax_bl_goods_touched", values)
        triggers = read(TRIGGERS)
        differs = norm(block(triggers, "te_tax_bl_regrel_differs"))
        self.assertEqual(differs, "has_variable = te_tax_bl_regrel var:te_tax_bl_regrel >= 0 OR = { NOT = { "
                                  "var:te_tax_bl_regrel = te_tax_base_bl_regrel } AND = { var:te_tax_bl_regrel >= 1 "
                                  "NOT = { te_tax_bl_relief_states_match = yes } } }")
        match = norm(block(triggers, "te_tax_bl_relief_states_match"))
        for slot in ("a", "b"):
            self.assertIn(f"te_tax_relief_base_from_{slot} = {{ DUE = te_tax_bl_due }} }} "
                          f"te_tax_relief_lists_match = {{ BASE = te_tax_p{slot}_relief_states }}", match)
        self.assertIn("trigger_else = { te_tax_relief_lists_match = { BASE = te_tax_en_relief_states } }", match)
        lists = norm(block(triggers, "te_tax_relief_lists_match"))
        self.assertIn("is_target_in_variable_list = { name = $BASE$ target = PREV }", lists)
        self.assertIn("is_target_in_variable_list = { name = te_tax_bl_relief_states target = PREV }", lists)
        self.assertNotRegex(lists, r"\bROOT\b")
        for name in ("te_tax_offer_cut_leaves_a_bill", "te_tax_offer_untax_leaves_a_bill"):
            body = block(triggers, name)
            self.assertNotIn("te_tax_bl_provisions", body)
            self.assertNotIn("var:te_tax_bl_agrel >= 0", body)
            self.assertNotIn("var:te_tax_bl_regrel >= 0", body)

    def test_a_cut_never_goes_below_existing_law(self):
        cut = norm(block(read(OFFERS), "te_tax_offer_cut"))
        self.assertIn("change_variable = { name = te_tax_bl_$KEY$ add = -1 } "
                      "clamp_variable = { name = te_tax_bl_$KEY$ min = te_tax_base_bl_$KEY$ max = te_tax_max_$KEY$ }", cut)
        self.assertNotIn("te_tax_bl_eff_", cut)
        feasible = norm(block(read(GEN_TRIGGERS), "te_tax_gen_offer_feasible"))
        for idx, key in enumerate(KEYS, start=1):
            self.assertIn(f"var:te_tax_off_$IG$_kind = {CUT} var:te_tax_off_$IG$_arg = {idx} }} "
                          f"te_tax_bl_dstep_{key} > 0 te_tax_offer_cut_leaves_a_bill = {{ KEY = {key} }}", feasible)

    def test_a_staple_offer_takes_back_only_a_staple_the_bill_adds(self):
        for ig in ("trade_unions", "rural_folk"):
            part = norm(selection(ig))
            grief = f"te_tax_bl_grief_{ig}"
            top = " ".join(f"{grief}_goods > {grief}_{key}" for key in PAYS[ig])
            added = " ".join(f"te_tax_dl_g_{good} > 0" for good in gen.staple_order())
            with self.subTest(ig=ig):
                self.assertIn(f"{grief}_goods > 0 {top} OR = {{ {added} }} te_tax_offer_untax_leaves_a_bill = yes }}", part)
                self.assertNotIn("te_tax_bl_eff_g_", part)
        untax = norm(block(read(OFFERS), "te_tax_offer_untax"))
        self.assertTrue(untax.startswith("custom_tooltip = te_tax_tt_offer_untax_$GOOD$ "
                                         "set_variable = { name = te_tax_bl_g_$GOOD$ value = -1 }"))
        feasible = norm(block(read(GEN_TRIGGERS), "te_tax_gen_offer_feasible"))
        for idx, good in enumerate(gen.staple_order(), start=1):
            self.assertIn(f"var:te_tax_off_$IG$_kind = {STAPLE} var:te_tax_off_$IG$_arg = {idx} }} "
                          f"te_tax_dl_g_{good} > 0 te_tax_offer_untax_leaves_a_bill = yes", feasible)
        leaves = norm(block(read(TRIGGERS), "te_tax_offer_untax_leaves_a_bill"))
        self.assertEqual(leaves, "OR = { te_tax_bl_changed_provisions >= 1 te_tax_bl_goods_changed >= 2 "
                                 "NOT = { te_tax_bl_dstep_agrel = 0 } te_tax_bl_regrel_differs = yes "
                                 "te_tax_bl_customs_changed >= 1 }")

    def test_relief_is_added_not_taken(self):
        part = norm(selection("rural_folk"))
        self.assertIn("te_tax_bl_eff_agrel < te_tax_max_agrel te_tax_bl_eff_wage > 0 } "
                      f"set_variable = {{ name = te_tax_off_rural_folk_kind value = {AGREL} }}", part)
        self.assertIn("change_variable = { name = te_tax_bl_agrel add = 1 }", norm(block(read(OFFERS), "te_tax_offer_agrel")))


class SelectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.refresh = block(read(GEN_BILL), "te_tax_gen_refresh_support")
        cls.select = block(read(GEN_BILL), "te_tax_gen_offer_select")

    def test_selection_runs_only_in_the_refresh_after_the_commitments(self):
        self.assertIn("te_tax_gen_offer_select = yes", self.refresh)
        last_commit = max(self.refresh.rfind(f"name = te_tax_com_{ig} value") for ig in IGS)
        self.assertGreater(self.refresh.find("te_tax_gen_offer_select = yes"), last_commit)
        callers = []
        for directory in ("common", "events", "gui"):
            for path in sorted((ROOT / directory).rglob("*.*")):
                if path.suffix not in (".txt", ".gui"):
                    continue
                text = path.read_text(encoding="utf-8-sig", errors="replace")
                if "te_tax_gen_offer_select = yes" in re.sub(r"#[^\n]*", "", text):
                    callers.append(path.name)
        self.assertEqual(callers, ["te_tax_generated_bill_effects.txt"])

    def test_one_offer_per_non_committed_non_marginal_group_per_revision(self):
        for ig in IGS:
            part = norm(selection(ig))
            with self.subTest(ig=ig):
                self.assertIn(f"exists = ig:ig_{ig}", part)
                self.assertIn(f"ig:ig_{ig} = {{ ig_counts_as_marginal = no }}", part)
                self.assertIn(f"NOT = {{ AND = {{ var:te_tax_com_{ig} = 1 var:te_tax_com_{ig}_rev = var:te_tax_bl_rev }} }}",
                              part)
                self.assertIn(f"NOT = {{ var:te_tax_off_{ig}_rev = var:te_tax_bl_rev }}", part)
                self.assertIn(f"set_variable = {{ name = te_tax_off_{ig}_rev value = var:te_tax_bl_rev }}", part)

    def test_a_red_line_group_is_offered_promises_only(self):
        for ig in IGS:
            part = selection(ig)
            red = blocks_of(part, "else")
            promises = {10 + kind for (kind, _), groups in PROMISES.items() if ig in groups}
            with self.subTest(ig=ig):
                if not promises:
                    self.assertEqual(red, [], "an empty red-line branch")
                    continue
                self.assertEqual(len(red), 1)
                kinds = {int(k) for k in re.findall(rf"name = te_tax_off_{ig}_kind value = (\d+)", red[0])}
                self.assertEqual(kinds, promises, "a clause offered at the red line")

    def test_a_clause_gained_in_this_bill_is_not_offered_again(self):
        for ig in IGS:
            part = norm(selection(ig))
            for clause in CLAUSES[ig]:
                with self.subTest(ig=ig, clause=clause):
                    self.assertIn(f"NAND = {{ has_variable = te_tax_bl_got_{ig}_{clause} "
                                  f"var:te_tax_bl_got_{ig}_{clause} = 1 }}", part)

    def test_a_promise_is_offered_only_when_it_can_be_recorded(self):
        for (kind, arg), groups in PROMISES.items():
            for ig in groups:
                part = norm(selection(ig))
                with self.subTest(ig=ig, kind=kind, arg=arg):
                    self.assertIn(f"te_tax_can_obl_propose = {{ KIND = {kind} ARG = {arg} }}", part)
                    self.assertIn(f"te_tax_obl_feasible_{kind}", part)
                    # One accepted promise per group per bill.
                    self.assertIn(f"NAND = {{ has_variable = te_tax_bl_prom_{ig}_kind "
                                  f"var:te_tax_bl_prom_{ig}_kind > 0 }}", part)

    def test_offers_reset_with_the_commitments(self):
        reset = block(read(GEN_BILL), "te_tax_gen_reset_commitments")
        for ig in IGS:
            with self.subTest(ig=ig):
                self.assertIn(f"set_variable = {{ name = te_tax_off_{ig}_kind value = 0 }}", reset)
                self.assertIn(f"set_variable = {{ name = te_tax_off_{ig}_rev value = -1 }}", reset)

    def test_a_committed_groups_offer_is_withdrawn(self):
        for ig in IGS:
            with self.subTest(ig=ig):
                self.assertRegex(norm(selection(ig)),
                                 rf"limit = \{{ var:te_tax_com_{ig} = 1 var:te_tax_com_{ig}_rev = var:te_tax_bl_rev \}} "
                                 rf"set_variable = \{{ name = te_tax_off_{ig}_kind value = 0 \}}")


class AcceptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(OFFERS)
        cls.accept = block(cls.text, "te_tax_cmd_accept_offer")

    def test_accept_runs_behind_its_trigger_and_says_what_it_does(self):
        self.assertRegex(norm(self.accept), r"^if = \{ limit = \{ te_tax_can_accept_offer = \{ IG = \$IG\$ \} \} "
                                            r"custom_tooltip = te_tax_tt_cmd_accept_offer")

    def test_accepting_is_a_new_revision_in_order(self):
        order = [
            "set_local_variable = { name = te_tax_acc_commit value = 0 }",
            "te_tax_gen_offer_apply = { IG = $IG$ }",
            "change_variable = { name = te_tax_bl_rev add = 1 }",
            "te_tax_bill_open_revision = yes",
            "te_tax_gen_offer_repropose = yes",
            "set_variable = { name = te_tax_com_$IG$ value = 1 }",
            "set_variable = { name = te_tax_com_$IG$_rev value = var:te_tax_bl_rev }",
            "te_tax_refresh_support = yes",
        ]
        positions = [self.accept.find(step) for step in order]
        for step, position in zip(order, positions):
            with self.subTest(step=step):
                self.assertGreater(position, 0)
        self.assertEqual(positions, sorted(positions))
        self.assertIn("limit = { local_var:te_tax_acc_commit = 1 }", self.accept)

    def test_only_a_persuadable_acceptor_commits(self):
        """Fix round 1 (spec §7.3): the offer carries a commitment only for a group
        scoring 0 or more when it is accepted, read live; an opposed or red-lined
        acceptor commits only through the refreshed score (the refresh's own rule)."""
        accept = norm(self.accept)
        self.assertIn("set_local_variable = { name = te_tax_acc_commit value = 0 } if = { limit = { "
                      "has_variable = te_tax_sup_$IG$ var:te_tax_sup_$IG$ >= 0 } custom_tooltip = te_tax_tt_offer_commits "
                      "set_local_variable = { name = te_tax_acc_commit value = 1 } } else = { custom_tooltip = "
                      "te_tax_tt_offer_no_commit }", accept)
        self.assertEqual(accept.count("te_tax_acc_commit value = 1"), 1)
        # Nothing stores a commitment flag on the offer.
        for path in (OFFERS, GEN_BILL, GEN_VALUES, TRIGGERS, GEN_CUSTOM_LOC, POLITICS):
            text = (ROOT / path).read_text(encoding="utf-8-sig")
            self.assertNotRegex(text, r"te_tax_off_\w+_commit|te_tax_disp_ig_offer_commit", path)
        # The refresh keeps a committed group and commits any other only at the threshold.
        refresh = norm(block(read(GEN_BILL), "te_tax_gen_refresh_support"))
        for ig in IGS:
            self.assertIn(f"limit = {{ var:te_tax_sup_{ig} >= te_tax_commit_threshold }} "
                          f"set_variable = {{ name = te_tax_com_{ig} value = 1 }}", refresh)

    def test_the_debate_opens_reproposes_then_refreshes(self):
        start = block(read(BILL), "te_tax_bill_start_debate")
        steps = ["te_tax_bill_open_revision = yes", "te_tax_gen_offer_repropose = yes", "te_tax_refresh_support = yes"]
        self.assertEqual([start.find(s) for s in steps], sorted(start.find(s) for s in steps))
        self.assertNotIn(-1, [start.find(s) for s in steps])
        opened = block(read(BILL), "te_tax_bill_open_revision")
        for step in ("set_variable = { name = te_tax_bl_day value = game_date }", "te_tax_bill_set_minor = yes",
                     "te_tax_gen_reset_commitments = yes", "te_tax_obl_release_pending = yes",
                     "set_variable = { name = te_tax_bl_on value = 1 }"):
            with self.subTest(step=step):
                self.assertIn(step, opened)

    def test_the_trigger_reads_the_offer_only_behind_its_guards(self):
        trigger = norm(block(read(TRIGGERS), "te_tax_can_accept_offer"))
        self.assertTrue(trigger.startswith("custom_tooltip = { text = te_tax_tt_code_in_force te_tax_code_in_force = yes }"))
        self.assertIn("var:te_tax_off_$IG$_rev = var:te_tax_bl_rev", trigger)
        self.assertIn("custom_tooltip = { text = te_tax_tt_offer_not_marginal ig:ig_$IG$ ?= { ig_counts_as_marginal = no } }",
                      trigger)
        self.assertIn("NAND = { has_variable = te_tax_com_$IG$ has_variable = te_tax_com_$IG$_rev "
                      "var:te_tax_com_$IG$ = 1 var:te_tax_com_$IG$_rev = var:te_tax_bl_rev }", trigger)
        self.assertIn("custom_tooltip = { text = te_tax_tt_offer_feasible te_tax_gen_offer_feasible = { IG = $IG$ } }",
                      trigger)
        self.assertIn("trigger_else = { custom_tooltip = { text = te_tax_tt_bill_open always = no } }", trigger)
        # One trigger_if (the open bill): no line can pass for want of an offer.
        self.assertEqual(trigger.count("trigger_if"), 1)
        feasible = norm(block(read(GEN_TRIGGERS), "te_tax_gen_offer_feasible"))
        self.assertTrue(feasible.startswith("has_variable = te_tax_off_$IG$_kind has_variable = te_tax_off_$IG$_arg "
                                            "var:te_tax_off_$IG$_kind > 0 trigger_if = {"))
        self.assertTrue(feasible.endswith("trigger_else = { always = no }"))

    def test_clauses_change_the_bill_and_the_draft_and_are_recorded(self):
        cut = block(self.text, "te_tax_offer_cut")
        self.assertIn("change_variable = { name = te_tax_bl_$KEY$ add = -1 }", cut)
        self.assertIn("name = te_tax_dr_$KEY$ value = var:te_tax_bl_$KEY$", cut)
        self.assertIn("set_variable = { name = te_tax_bl_got_$IG$_1 value = 1 }", cut)
        agrel = block(self.text, "te_tax_offer_agrel")
        self.assertIn("change_variable = { name = te_tax_bl_agrel add = 1 }", agrel)
        self.assertIn("name = te_tax_dr_agrel value = var:te_tax_bl_agrel", agrel)
        self.assertIn("set_variable = { name = te_tax_bl_got_$IG$_2 value = 1 }", agrel)
        untax = block(self.text, "te_tax_offer_untax")
        self.assertIn("te_tax_bl_g_$GOOD$", untax)
        self.assertIn("te_tax_dr_g_$GOOD$", untax)
        self.assertIn("set_variable = { name = te_tax_bl_got_$IG$_3 value = 1 }", untax)
        # Fix round 1: the tooltip says a clause replaces the draft's own edit.
        for helper in ("te_tax_offer_cut", "te_tax_offer_agrel", "te_tax_offer_untax"):
            self.assertRegex(norm(block(self.text, helper)),
                             r"if = \{ limit = \{ te_tax_draft_active = yes \} custom_tooltip = te_tax_tt_offer_draft ")
        self.assertIn("draft takes the same value", loc()["te_tax_tt_offer_draft"])
        record = block(self.text, "te_tax_offer_record_promise")
        for field in ("kind", "arg", "target"):
            self.assertIn(f"name = te_tax_bl_prom_$IG$_{field}", record)

    def test_apply_dispatches_every_offer_kind(self):
        apply = norm(block(read(GEN_BILL), "te_tax_gen_offer_apply"))
        for idx, key in enumerate(KEYS, start=1):
            self.assertIn(f"var:te_tax_off_$IG$_kind = {CUT} var:te_tax_off_$IG$_arg = {idx} }} "
                          f"te_tax_offer_cut = {{ IG = $IG$ KEY = {key} }}", apply)
        self.assertIn("te_tax_offer_agrel = { IG = $IG$ }", apply)
        for idx, good in enumerate(gen.staple_order(), start=1):
            self.assertIn(f"var:te_tax_off_$IG$_arg = {idx} }} te_tax_offer_untax = {{ IG = $IG$ GOOD = {good} }}", apply)
        self.assertIn("var:te_tax_off_$IG$_kind > 10 } te_tax_offer_record_promise = { IG = $IG$ }", apply)

    def test_a_revision_from_the_draft_drops_the_records(self):
        copy = block(read(GEN_BILL), "te_tax_gen_bill_from_draft")
        clear = block(read(GEN_BILL), "te_tax_gen_bill_clear")
        for ig in IGS:
            with self.subTest(ig=ig):
                for field in ("kind", "arg", "target"):
                    self.assertIn(f"set_variable = {{ name = te_tax_bl_prom_{ig}_{field} value = -1 }}", copy)
                    self.assertIn(f"remove_variable = te_tax_bl_prom_{ig}_{field}", clear)
                for clause in CLAUSES[ig]:
                    self.assertIn(f"set_variable = {{ name = te_tax_bl_got_{ig}_{clause} value = 0 }}", copy)
                    self.assertIn(f"remove_variable = te_tax_bl_got_{ig}_{clause}", clear)

    def test_every_accepted_promise_is_proposed_again(self):
        repropose = norm(block(read(GEN_BILL), "te_tax_gen_offer_repropose"))
        for (kind, arg), groups in PROMISES.items():
            for ig in groups:
                with self.subTest(ig=ig, kind=kind, arg=arg):
                    self.assertIn(f"var:te_tax_bl_prom_{ig}_kind = {kind} var:te_tax_bl_prom_{ig}_arg = {arg} }} "
                                  f"te_tax_obl_propose = {{ KIND = {kind} ARG = {arg} "
                                  f"TARGET = var:te_tax_bl_prom_{ig}_target IG = te_tax_ig_id_{ig} }}", repropose)
            # A record that could not be proposed again is dropped, so it never counts.
        self.assertIn("NOT = { te_tax_offer_prom_live = { IG = rural_folk } }", repropose)

    def test_the_handler_dispatches_by_group_type_and_fails_closed(self):
        body = block(read(SGUIS), "te_tax_cmd_accept_offer_sgui")
        self.assertRegex(body, r"saved_scopes = \{ te_tax_ig \}")
        valid, effect = norm(sub_block(body, "is_valid")), norm(sub_block(body, "effect"))
        for ig in IGS:
            with self.subTest(ig=ig):
                self.assertIn(f"limit = {{ exists = scope:te_tax_ig scope:te_tax_ig = {{ is_interest_group_type = ig_{ig} }} }} "
                              f"te_tax_can_accept_offer = {{ IG = {ig} }}", valid)
                self.assertIn(f"limit = {{ exists = scope:te_tax_ig scope:te_tax_ig = {{ is_interest_group_type = ig_{ig} }} }} "
                              f"te_tax_cmd_accept_offer = {{ IG = {ig} }}", effect)
        self.assertTrue(valid.endswith("trigger_else = { always = no }"))
        self.assertNotRegex(effect, r"\belse = \{")


class PromiseSupportTest(unittest.TestCase):
    def test_the_refresh_recomputes_prom_from_the_records(self):
        refresh = block(read(GEN_BILL), "te_tax_gen_refresh_support")
        for ig in IGS:
            with self.subTest(ig=ig):
                self.assertIn(f"set_variable = {{ name = te_tax_sr_{ig}_prom value = te_tax_prom_{ig} }}", refresh)
                self.assertNotIn(f"change_variable = {{ name = te_tax_sr_{ig}_prom", refresh)

    def test_own_promise_points_and_clamp(self):
        support = load(SUPPORT)
        self.assertEqual(support["te_tax_offer_points"], "20")
        self.assertEqual(support["te_tax_offer_points_maint"], "8")
        for ig in IGS:
            body = norm(block(read(GEN_SUPPORT), f"te_tax_prom_{ig}"))
            with self.subTest(ig=ig):
                self.assertIn(f"if = {{ limit = {{ te_tax_offer_prom_live_maint = {{ IG = {ig} }} }} "
                              f"add = te_tax_offer_points_maint }}", body)
                self.assertIn(f"else_if = {{ limit = {{ te_tax_offer_prom_live = {{ IG = {ig} }} }} "
                              f"add = te_tax_offer_points }}", body)
                self.assertTrue(body.endswith("min = -40 max = 40"))

    def test_side_effects_follow_the_groups_institution_stances(self):
        laws = {SCHOOLS: "law_no_schools", HEALTH: "law_no_health_system"}
        for ig in IGS:
            body = norm(block(read(GEN_SUPPORT), f"te_tax_prom_{ig}"))
            for promise, law in laws.items():
                others = [other for other in PROMISES[promise] if other != ig]
                with self.subTest(ig=ig, law=law):
                    stance = f"ig:ig_{ig} ?= {{ law_stance = {{ law = law_type:{law} value > approve }} }} }} add = -6"
                    if others:
                        self.assertIn(stance, body)
                        for other in others:
                            self.assertIn(f"var:te_tax_bl_prom_{other}_kind = {promise[0]} "
                                          f"var:te_tax_bl_prom_{other}_arg = {promise[1]}", body)
                    else:
                        self.assertNotIn(f"law_type:{law}", body)
            # No group is its own side effect.
            with self.subTest(ig=ig):
                self.assertNotIn(f"var:te_tax_bl_prom_{ig}_kind", body)

    def test_a_promise_counts_only_while_its_pending_obligation_is_live(self):
        slot = norm(block(read(TRIGGERS), "te_tax_offer_prom_in_slot"))
        for condition in ("var:te_tax_o$N$_on = 1", "var:te_tax_o$N$_state = 1",
                          "var:te_tax_o$N$_kind = var:te_tax_bl_prom_$IG$_kind",
                          "var:te_tax_o$N$_arg = var:te_tax_bl_prom_$IG$_arg",
                          "var:te_tax_o$N$_ig = te_tax_ig_id_$IG$", "var:te_tax_o$N$_rev = var:te_tax_bl_rev"):
            self.assertIn(condition, slot)
        live = norm(block(read(TRIGGERS), "te_tax_offer_prom_live"))
        for n in (1, 2, 3, 4):
            self.assertIn(f"te_tax_offer_prom_in_slot = {{ IG = $IG$ N = {n} }}", live)
        maint = norm(block(read(TRIGGERS), "te_tax_offer_prom_maint_in_slot"))
        self.assertIn("var:te_tax_o$N$_maint_only = 1", maint)


class ReasonsSeeGoodsAndReliefTest(unittest.TestCase):
    def test_taxing_staples_is_regressive(self):
        prog = norm(block(read(GEN_SUPPORT), "te_tax_dl_prog"))
        for good in STAPLES:
            self.assertIn(f"subtract = te_tax_dl_g_{good}", prog)
        for good in set(catalog()) - STAPLES:
            self.assertNotIn(f"te_tax_dl_g_{good}", prog)

    def test_fiscal_direction_sees_goods_and_relief(self):
        revenue = norm(block(read(GEN_SUPPORT), "te_tax_dl_revenue"))
        self.assertEqual(revenue, "value = te_tax_dl_total add = te_tax_dl_goods "
                                  "subtract = { value = te_tax_bl_agrel_scaled multiply = te_tax_agrel_revenue_levels } "
                                  "subtract = { value = te_tax_bl_regrel_coverage multiply = te_tax_regrel_revenue_levels }")
        fiscal = norm(block(read(SUPPORT), "te_tax_fiscal_reason"))
        self.assertIn("te_tax_dl_revenue > 0", fiscal)
        self.assertNotIn("te_tax_dl_total", fiscal)


class IgViewTest(unittest.TestCase):
    """Controller ruling 1 and 2: the band is the group's stance toward the
    code's equivalent vanilla taxation law; band 0 carries no modifier."""

    @classmethod
    def setUpClass(cls):
        cls.modifiers = load(GEN_MODIFIERS)
        cls.views = block(read(GEN_EFFECTS), "te_tax_gen_ig_views")

    def test_four_bands_per_group_carrying_vanillas_approval(self):
        expected = {f"te_tax_ig_view_{ig}_{band}" for ig in IGS for band in BANDS}
        self.assertEqual(set(self.modifiers), expected)
        approval = {-2: -2, -1: -1, 1: 1, 2: 2}
        for ig in IGS:
            for band, value in BANDS.items():
                body = self.modifiers[f"te_tax_ig_view_{ig}_{band}"]
                with self.subTest(ig=ig, band=band):
                    self.assertEqual(set(body), {"icon", f"interest_group_ig_{ig}_approval_add"})
                    self.assertEqual(Decimal(body[f"interest_group_ig_{ig}_approval_add"]), approval[value])
        self.assertEqual((gen.VANILLA_APPROVAL_FROM_LAW, gen.VANILLA_APPROVAL_FROM_LAW_STRONG), (1, 2))

    def test_the_approval_matches_the_installed_defines_when_present(self):
        if not INSTALLED_DEFINES.exists():
            self.skipTest("no installed Victoria 3")
        defines = INSTALLED_DEFINES.read_text(encoding="utf-8-sig", errors="replace")
        self.assertRegex(defines, rf"(?m)^\s*IG_APPROVAL_FROM_LAW = {gen.VANILLA_APPROVAL_FROM_LAW}\b")
        self.assertRegex(defines, rf"(?m)^\s*IG_APPROVAL_FROM_LAW_STRONG_STANCE = {gen.VANILLA_APPROVAL_FROM_LAW_STRONG}\b")

    def test_bands_are_swapped_never_stacked_and_band_0_has_none(self):
        text = norm(self.views)
        for ig in IGS:
            self.assertIn(f"set_local_variable = {{ name = te_tax_band value = te_tax_ig_band_{ig} }}", text)
            for band, value in BANDS.items():
                name = f"te_tax_ig_view_{ig}_{band}"
                with self.subTest(name=name):
                    self.assertEqual(text.count(f"add_modifier = {{ name = {name} }}"), 1)
                    self.assertIn(f"limit = {{ local_var:te_tax_band = {value} NOT = {{ has_modifier = {name} }} }} "
                                  f"add_modifier = {{ name = {name} }}", text)
                    # At any other band, band 0 included, it goes.
                    self.assertIn(f"limit = {{ NOT = {{ local_var:te_tax_band = {value} }} has_modifier = {name} }} "
                                  f"remove_modifier = {name}", text)
            self.assertNotIn(f"te_tax_ig_view_{ig}_0", text)
        self.assertNotIn("multiplier", self.views)

    def test_two_refresh_sites_the_processor_and_the_post_migration_sync(self):
        process = block(read(SCHEDULE), "te_tax_process_month")
        at = process.find("te_tax_refresh_ig_views = yes")
        self.assertGreater(at, process.find("te_tax_obl_check_month = yes"))
        self.assertLess(at, process.find("te_tax_sync_collection = yes"))
        self.assertEqual(process.count("te_tax_refresh_ig_views = yes"), 1)
        # Fix round 1: te_tax.4, after its sync, once.
        immediate = sub_block(block(read(EVENTS), "te_tax.4"), "immediate")
        self.assertEqual(immediate.count("te_tax_refresh_ig_views = yes"), 1)
        self.assertGreater(immediate.find("te_tax_refresh_ig_views = yes"), immediate.find("te_tax_sync_collection = yes"))
        events = re.sub(r"#[^\n]*", "", (ROOT / EVENTS).read_text(encoding="utf-8-sig"))
        self.assertEqual(events.count("te_tax_refresh_ig_views = yes"), 1)
        writers, callers = [], []
        for directory in ("common", "events", "gui"):
            for path in sorted((ROOT / directory).rglob("*.*")):
                if path.suffix not in (".txt", ".gui"):
                    continue
                text = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig", errors="replace"))
                if re.search(r"(add|remove)_modifier = (\{ name = )?te_tax_ig_view_", text):
                    writers.append(path.name)
                if "te_tax_refresh_ig_views = yes" in text or "te_tax_gen_ig_views = yes" in text:
                    callers.append(path.name)
        self.assertEqual(writers, ["te_tax_generated_effects.txt"])
        self.assertEqual(sorted(callers), ["te_tax_internal_events.txt", "te_tax_offer_effects.txt",
                                           "te_tax_schedule_effects.txt"])

    def test_refresh_is_gated(self):
        refresh = norm(block(read(OFFERS), "te_tax_refresh_ig_views"))
        self.assertEqual(refresh, "if = { limit = { te_tax_code_on = yes has_variable = te_tax_schema } "
                                  "te_tax_gen_ig_views = yes }")

    def test_the_band_is_the_stance_toward_the_equivalent_law(self):
        values = read(GEN_SUPPORT)
        branches = [("value > approve", 2), ("value > neutral", 1), ("value < disapprove", -2), ("value < neutral", -1)]
        for ig in IGS:
            body = norm(block(values, f"te_tax_ig_band_{ig}"))
            with self.subTest(ig=ig):
                self.assertTrue(body.startswith("value = 0 if = { limit = { te_tax_code_equivalent_graduated = yes }"))
                positions = [body.find(f"te_tax_code_equivalent_{short} = yes") for short, _ in EQUIVALENT]
                self.assertEqual(positions, sorted(positions))
                self.assertNotIn(-1, positions)
                for _, law in EQUIVALENT:
                    chain = " ".join(f"{'if' if n == 0 else 'else_if'} = {{ limit = {{ ig:ig_{ig} ?= {{ law_stance = "
                                     f"{{ law = law_type:{law} {comparison} }} }} }} value = {stance} }}"
                                     for n, (comparison, stance) in enumerate(branches))
                    self.assertIn(chain, body)
                self.assertNotIn("var:", body)

    def test_the_equivalence_triggers_follow_the_ruling_order(self):
        triggers = read(TRIGGERS)
        neg = ("NOT = { te_tax_code_counts_as_graduated = yes }", "NOT = { te_tax_code_counts_as_proportional = yes }",
               "NOT = { te_tax_code_counts_as_per_capita = yes }")
        self.assertEqual(norm(block(triggers, "te_tax_code_equivalent_graduated")),
                         "te_tax_code_counts_as_graduated = yes")
        self.assertEqual(norm(block(triggers, "te_tax_code_equivalent_proportional")),
                         f"{neg[0]} te_tax_code_counts_as_proportional = yes")
        self.assertEqual(norm(block(triggers, "te_tax_code_equivalent_per_capita")),
                         f"{neg[0]} {neg[1]} te_tax_code_counts_as_per_capita = yes")
        carrier = "te_tax_code_on = yes has_law = law_type:law_te_tax_code"
        self.assertEqual(norm(block(triggers, "te_tax_code_equivalent_land_based")),
                         f"{carrier} {' '.join(neg)} has_variable = te_tax_en_land var:te_tax_en_land >= 1")
        self.assertEqual(norm(block(triggers, "te_tax_code_equivalent_consumption_based")),
                         f"{carrier} {' '.join(neg)} NAND = {{ has_variable = te_tax_en_land var:te_tax_en_land >= 1 }}")
        for kind in ("graduated", "proportional", "per_capita"):
            counts = norm(block(triggers, f"te_tax_code_counts_as_{kind}"))
            self.assertIn(carrier, counts)

    def test_every_migrated_row_maps_back_to_its_own_law(self):
        """The migration changes no group's approval: each vanilla (law, level) row's
        enacted indices are classified, by the counts-as triggers' own comparisons,
        as the law the country had."""
        triggers = read(TRIGGERS)

        def holds(name, indices):
            body = norm(block(triggers, name))
            tests = re.findall(r"var:te_tax_en_(\w+) >= (var:te_tax_en_(\w+)|\d+)", body)
            self.assertTrue(tests, name)
            return all(indices[key] >= (indices[other] if other else int(value)) for key, value, other in tests)

        def equivalent(indices):
            if holds("te_tax_code_counts_as_graduated", indices):
                return "law_graduated_taxation"
            if holds("te_tax_code_counts_as_proportional", indices):
                return "law_proportional_taxation"
            if holds("te_tax_code_counts_as_per_capita", indices):
                return "law_per_capita_based_taxation"
            if indices["land"] >= 1:
                return "law_land_based_taxation"
            return "law_consumption_based_taxation"

        rows = gen.migration_indices()
        self.assertEqual(len(rows), 25)
        for law, level, indices in rows:
            with self.subTest(law=law, level=level):
                self.assertEqual(equivalent(indices), law)

    def test_the_migrated_baseline_is_gone(self):
        """Added and dropped in this task: no token, value or effect of it remains."""
        for directory in ("common", "events", "gui", "localization"):
            for path in sorted((ROOT / directory).rglob("te_tax*")):
                text = path.read_text(encoding="utf-8-sig", errors="replace")
                with self.subTest(path=path.name):
                    self.assertNotIn("te_tax_mig_", text)
                    self.assertNotIn("te_tax_cv_", text)
                    self.assertNotIn("te_tax_gen_record_baseline", text)
                    self.assertNotIn("te_tax_ig_view_threshold", text)
        country, _ = schema_tokens()
        self.assertFalse([token for token in country if token.startswith("te_tax_mig_")])

    def test_no_panel_reads_the_band_values(self):
        surfaces = [path.read_text(encoding="utf-8-sig") for path in (ROOT / "gui").rglob("*.gui")]
        surfaces += [read(GEN_VALUES), read(SGUIS), read(GEN_CUSTOM_LOC)]
        surfaces += [(ROOT / "localization/english/te_tax_l_english.yml").read_text(encoding="utf-8-sig")]
        for text in surfaces:
            self.assertNotIn("te_tax_ig_band_", text)


class ForceThroughTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trigger = norm(block(read(TRIGGERS), "te_tax_can_force_through"))
        cls.command = norm(block(read(OFFERS), "te_tax_cmd_force_through"))
        cls.into = norm(block(read(OFFERS), "te_tax_force_into"))

    def test_every_condition_is_a_tooltip_line(self):
        for condition in ("te_tax_committed_share >= te_tax_force_share",
                          '"modifier:country_legislative_override_capacity_add" >= 2',
                          "produced_authority > forced_law_through_event_authority_cost_medium",
                          "NOT = { te_tax_committed_share > te_tax_passage_share }"):
            with self.subTest(condition=condition):
                self.assertRegex(self.trigger, r"custom_tooltip = \{ text = te_tax_tt_force_\w+ " + re.escape(condition))
        self.assertEqual(load(SUPPORT)["te_tax_force_share"], "0.35")

    def test_every_other_passage_line_is_repeated(self):
        can_pass = norm(block(read(TRIGGERS), "te_tax_can_pass"))
        lines = re.findall(r"custom_tooltip = \{ text = (te_tax_tt_pass_\w+) (.*?) \}(?= custom_tooltip| \} trigger_else)",
                           can_pass)
        self.assertGreaterEqual(len(lines), 7)
        for key, condition in lines:
            if key == "te_tax_tt_pass_support":
                self.assertNotIn(f"text = {key}", self.trigger)
                continue
            with self.subTest(key=key):
                self.assertIn(f"custom_tooltip = {{ text = {key} {condition} }}", self.trigger)

    def test_reuses_the_forced_law_modifiers_and_costs(self):
        self.assertIn("if = { limit = { te_tax_can_force_through = yes } custom_tooltip = te_tax_tt_cmd_force_through",
                      self.command)
        self.assertIn("add_modifier = { name = forced_law_through_event years = 5 "
                      "multiplier = forced_law_through_event_authority_multiplier_medium is_decaying = yes }", self.into)
        self.assertIn("add_modifier = { name = forced_law_through_event_consequences_medium years = 5 "
                      "is_decaying = yes }", self.into)
        self.assertLess(self.into.find("add_modifier"), self.into.find("te_tax_pass_into = { SLOT = $SLOT$ OTHER = $OTHER$ }"))
        self.assertEqual(len(re.findall(r"add_modifier", self.into)), 2)
        self.assertIn("te_tax_can_store_package = { SLOT = $SLOT$ }", self.into)
        modifiers = load(EXTRA_MODIFIERS)
        for name in ("forced_law_through_event", "forced_law_through_event_consequences_medium"):
            self.assertIn(name, modifiers)
        values = read(EXTRA_VALUES)
        for name in ("forced_law_through_event_authority_cost_medium", "forced_law_through_event_authority_multiplier_medium"):
            self.assertRegex(values, rf"(?m)^{name} = \{{")

    def test_invents_no_forced_law_modifier(self):
        for path in sorted((ROOT / "common/static_modifiers").glob("te_tax_*.txt")):
            text = read(path.relative_to(ROOT).as_posix())
            with self.subTest(path=path.name):
                self.assertNotRegex(text, r"(?m)^\w*forced\w* = \{")

    def test_handler_and_button(self):
        body = block(read(SGUIS), "te_tax_cmd_force_through_sgui")
        self.assertEqual(norm(sub_block(body, "is_valid")), "te_tax_can_force_through = yes")
        self.assertEqual(norm(sub_block(body, "effect")), "te_tax_cmd_force_through = yes")
        politics = gui(POLITICS)
        self.assertIn("GetScriptedGui('te_tax_cmd_force_through_sgui').Execute(", politics)


class CardTest(unittest.TestCase):
    def test_the_card_shows_the_offer_and_accept(self):
        politics = gui(POLITICS)
        self.assertIn("InterestGroup.GetCustom('te_tax_ig_offer')", politics + "\n".join(loc().values()))
        self.assertIn("GetScriptedGui('te_tax_cmd_accept_offer_sgui').Execute( GuiScope.SetRoot( GetPlayer.MakeScope )"
                      ".AddScope( 'te_tax_ig', InterestGroup.MakeScope ).End )", politics)
        self.assertIn("InterestGroup.MakeScope.ScriptValue('te_tax_disp_ig_offer')", politics)
        self.assertIn('text = "te_tax_ig_prom"', politics)
        # Fix round 1: what accepting gives follows the group's stance (2 persuadable, 4 red line).
        line = loc()["te_tax_ig_offer_line"]
        self.assertIn("ScriptValue('te_tax_disp_ig_stance'), '(CFixedPoint)2' ), 'te_tax_ig_offer_commits'", line)
        self.assertIn("'te_tax_ig_offer_lifts', 'te_tax_ig_offer_less'", line)
        self.assertIn("oppose the bill less", loc()["te_tax_ig_offer_less"])

    def test_the_offer_text_covers_every_kind(self):
        text = read(GEN_CUSTOM_LOC)
        body = block(text, "te_tax_ig_offer")
        self.assertIn("type = interest_group", body)
        for idx, key in enumerate(KEYS, start=1):
            self.assertIn(f"te_tax_disp_ig_offer = {CUT} te_tax_disp_ig_offer_arg = {idx}", body)
            self.assertIn(f"localization_key = te_tax_offer_cut_{key}", body)
        for idx, good in enumerate(gen.staple_order(), start=1):
            self.assertIn(f"localization_key = te_tax_offer_untax_{good}", body)
        for key in ("te_tax_offer_agrel", "te_tax_offer_prom_schools", "te_tax_offer_prom_health",
                    "te_tax_offer_prom_bureaucracy", "te_tax_offer_prom_fiscal"):
            self.assertIn(f"localization_key = {key}", body)
        table = loc()
        for key in set(re.findall(r"localization_key = (\w+)", body)):
            with self.subTest(key=key):
                self.assertTrue(table.get(key), key)


if __name__ == "__main__":
    unittest.main()
