# -*- coding: utf-8 -*-
"""Estimates and the economy snapshot of the legislated tax code (plan Task 14;
spec §5 "Separate a current-economy estimate from a medium-term forecast" and
§10 "UI reads cached results").

Structural checks on the committed script (no game install needed):

* te_tax_take_snapshot writes one dated snapshot (the month, the domestic tax
  aggregate, net fixed and net total income, GDP, the code version, the bill
  revision and the enacted index of every instrument), gated on the rule and an
  initialised country; it is called by the monthly processor once, inside the
  claimed month after the collection write, and when a bill revision opens
  (te_tax_bill_open_revision: introduction, revision and an accepted offer),
  after the bill is open; never from a .gui, a scripted GUI, loc or a
  customizable localization, and nothing removes its variables;
* every snapshot and estimate value is guarded, writes nothing, iterates
  nothing, reads a draft only while one is open, and divides by a snapshot
  index only behind a test that the index is above 0;
* each Budget receipt line the draft changes (Income, Dividends, Poll,
  Consumption: the Budget's own getters) is printed as today's receipts scaled
  by the rates against the snapshot's, labelled a static estimate at today's
  economy, with a no-base branch for a tax not collected at the snapshot and an
  out-of-date marker; Poll prints a range when rural assessment and head tax
  both collect, as they share the line;
* goods and agricultural relief carry labels only; regional relief prints each
  named state's change from its own taxation revenue;
* an offer to cut a tax prints its revenue change against the bill;
* the overview shows the snapshot's date, and the domestic tax aggregate only
  under the label "domestic tax aggregate (unclassified)";
* the three generated comments that called the interest-group view refresh
  "monthly processor only" name its second caller, te_tax.4.

Run: python3 -m unittest test_tax_code_estimates -v
"""

import re
import unittest
from pathlib import Path

from test_tax_code_layout import gui, loc, raw, type_body, uncomment, value_bodies
from test_tax_code_state import KEYS, block, close, gen, read

ROOT = Path(__file__).resolve().parent

SNAPSHOT = "common/scripted_effects/te_tax_snapshot_effects.txt"
SCHEDULE = "common/scripted_effects/te_tax_schedule_effects.txt"
BILL = "common/scripted_effects/te_tax_bill_effects.txt"
DISPLAY = "common/script_values/te_tax_display_values.txt"
GEN_VALUES = "common/script_values/te_tax_generated_values.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_generated_effects.txt"
GEN_SUPPORT = "common/script_values/te_tax_generated_support_values.txt"
GEN_MODIFIERS = "common/static_modifiers/te_tax_generated_modifiers.txt"
GENERATOR = "scripts/generators/gen_tax_code.py"
REVIEW = "gui/journal_entry_widgets/te_tax_review_widget.gui"
POLITICS = "gui/journal_entry_widgets/te_tax_politics_widget.gui"
OVERVIEW = "gui/journal_entry_widgets/te_tax_overview_widget.gui"
SCHEMA_DOC = "docs/systems/tax_code_schema.md"

# The snapshot's fields (the brief's list), then one index per instrument.
SNAP_FIELDS = {
    "te_tax_snap_month": "te_history_month_index",
    "te_tax_snap_tax_income": "te_tax_read_tax_income",
    "te_tax_snap_net_fixed": "te_tax_read_net_fixed_income",
    "te_tax_snap_net_total": "te_tax_read_net_total_income",
    "te_tax_snap_gdp": "te_tax_read_gdp",
    "te_tax_snap_code_version": "te_tax_view_code_version",
    "te_tax_snap_bill_rev": "te_tax_view_bl_rev",
}
READERS = {
    "te_tax_read_tax_income": "tax_income",
    "te_tax_read_net_fixed_income": "net_fixed_income",
    "te_tax_read_net_total_income": "net_total_income",
    "te_tax_read_gdp": "gdp",
}

# The Budget's receipt lines (gui/budget_panel.gui, the Taxes column): the getter that
# prints each and the instruments it collects.
CHANNELS = {
    "income": ("GetIncomeTaxIncome", ("wage",)),
    "dividends": ("PredictDividendsTaxes", ("div",)),
    "poll": ("GetPollTaxIncome", ("land", "head")),
    "consumption": ("PredictConsumptionTaxes", ("cons",)),
}
CHANNEL_OF = {key: name for name, (_, keys) in CHANNELS.items() for key in keys}

FORBIDDEN = re.compile(
    r"\b(set_variable|change_variable|remove_variable|save_scope_as|save_temporary_scope_as|"
    r"every_\w+|any_\w+|random_\w+|ordered_\w+|add_modifier|trigger_event)\b")
DRAFT_OPEN = "has_variable = te_tax_dr_on var:te_tax_dr_on = 1"
BILL_OPEN = "has_variable = te_tax_bl_on var:te_tax_bl_on = 1"


def script_text(path):
    return uncomment(raw(path))


def all_effects():
    """{name: body} of every scripted effect in the mod."""
    defined = {}
    for path in sorted((ROOT / "common" / "scripted_effects").glob("*.txt")):
        text = script_text(path.relative_to(ROOT))
        for match in re.finditer(r"(?m)^(\w+) = \{", text):
            defined[match.group(1)] = text[match.end():close(text, match.end() - 1)]
    return defined


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def enclosing_limits(text, pos):
    """The `limit = { ... }` bodies of every `if`/`else_if` block that encloses `pos`."""
    limits, depth = [], 0
    for i in range(pos, -1, -1):
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth:
                depth -= 1
                continue
            opener = re.search(r"(\w+)\s*=\s*$", text[:i])
            if opener and opener.group(1) in ("if", "else_if"):
                body = text[i + 1:close(text, i)]
                match = re.search(r"\blimit = \{", body)
                if match:
                    limits.append(body[match.end():close(body, match.end() - 1)])
    return limits


class SnapshotEffectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(SNAPSHOT)
        cls.body = block(cls.text, "te_tax_take_snapshot")
        cls.flat = norm(cls.body)

    def test_effect_is_gated_on_the_rule_and_an_initialised_country(self):
        self.assertTrue(self.flat.startswith("if = { limit = { te_tax_code_on = yes has_variable = te_tax_schema }"),
                        self.flat[:120])
        self.assertEqual(self.flat.count("if = { limit = { te_tax_code_on = yes"), 1)

    def test_writes_every_field_of_the_brief_and_each_rate_in_force(self):
        for name, source in SNAP_FIELDS.items():
            with self.subTest(name=name):
                self.assertIn(f"set_variable = {{ name = {name} value = {source} }}", self.flat)
        for key in KEYS:
            with self.subTest(key=key):
                self.assertIn(f"set_variable = {{ name = te_tax_snap_{key} value = te_tax_view_en_{key} }}", self.flat)
        written = set(re.findall(r"name = (te_tax_snap_\w+)", self.flat))
        self.assertEqual(written, set(SNAP_FIELDS) | {f"te_tax_snap_{key}" for key in KEYS})

    def test_engine_reads_go_through_plain_wrappers(self):
        # The tax probe's form (te_tp_read_*, read in game in R2a).
        display = read(DISPLAY)
        for name, trigger in READERS.items():
            with self.subTest(name=name):
                self.assertIn(f"{name} = {{ value = {trigger} }}", norm(display))

    def test_logs_for_players_only(self):
        self.assertRegex(self.flat, r"if = \{ limit = \{ is_ai = no \} debug_log = \"TE_TAX snapshot ")

    def test_called_by_the_processor_and_the_opening_of_a_revision_only(self):
        callers = sorted(name for name, body in all_effects().items() if "te_tax_take_snapshot = yes" in body)
        self.assertEqual(callers, ["te_tax_bill_open_revision", "te_tax_process_month"])
        for name, body in all_effects().items():
            with self.subTest(name=name):
                self.assertLessEqual(body.count("te_tax_take_snapshot"), 1)
        for path in sorted((ROOT / "events").glob("*.txt")):
            self.assertNotIn("te_tax_take_snapshot", script_text(path.relative_to(ROOT)), path.name)

    def test_processor_takes_it_once_inside_the_claimed_month_after_the_sync(self):
        body = block(read(SCHEDULE), "te_tax_process_month")
        claimed = body.find("set_variable = { name = te_tax_last_month value = var:te_tax_now }")
        at = body.find("te_tax_take_snapshot = yes")
        self.assertGreater(claimed, 0)
        self.assertGreater(at, body.find("te_tax_sync_collection = yes"))
        self.assertGreater(at, claimed)

    def test_a_revision_takes_it_once_the_bill_is_open(self):
        body = block(read(BILL), "te_tax_bill_open_revision")
        self.assertGreater(body.find("te_tax_take_snapshot = yes"),
                           body.find("set_variable = { name = te_tax_bl_on value = 1 }"))
        # every path that opens a revision bumps the revision first
        for name in ("te_tax_cmd_introduce", "te_tax_cmd_revise"):
            effect = block(read(BILL), name)
            self.assertLess(effect.find("te_tax_bl_rev"), effect.find("te_tax_bill_start_debate = yes"))
        accept = block(read("common/scripted_effects/te_tax_offer_effects.txt"), "te_tax_cmd_accept_offer")
        self.assertLess(accept.find("change_variable = { name = te_tax_bl_rev add = 1 }"),
                        accept.find("te_tax_bill_open_revision = yes"))

    def test_never_from_a_gui_a_scripted_gui_or_loc(self):
        paths = [*(ROOT / "gui").rglob("*.gui"), *(ROOT / "common" / "scripted_guis").glob("*.txt"),
                 *(ROOT / "common" / "customizable_localization").glob("*.txt"),
                 *(ROOT / "localization").rglob("*.yml")]
        for path in paths:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            if path.suffix != ".yml":
                text = uncomment(text)
            with self.subTest(path=path.name):
                self.assertNotIn("te_tax_take_snapshot", text)

    def test_nothing_removes_a_snapshot_variable(self):
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                text = script_text(path.relative_to(ROOT))
                with self.subTest(path=path.name):
                    self.assertNotRegex(text, r"remove_variable\s*=\s*(\{[^}]*name\s*=\s*)?te_tax_snap_")


class EstimateValueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = value_bodies()
        cls.texts = {path: script_text(path) for path in (DISPLAY, GEN_VALUES)}

    def names(self, prefix):
        return {name for name in self.values if name.startswith(prefix)}

    def test_the_views_exist(self):
        want = {"te_tax_view_snap_month", "te_tax_view_snap_month_y", "te_tax_view_snap_month_mo",
                "te_tax_view_snap_tax_income", "te_tax_view_snap_net_fixed", "te_tax_view_snap_net_total",
                "te_tax_view_snap_gdp", "te_tax_view_snap_current", "te_tax_view_est_poll_shared",
                "te_tax_view_est_regrel_state"}
        want |= {f"te_tax_view_snap_{key}" for key in KEYS}
        want |= {f"te_tax_view_est_cut_{key}" for key in KEYS}
        for channel, (_, keys) in CHANNELS.items():
            want |= {f"te_tax_view_est_{channel}_{part}" for part in ("on", "nobase")}
            if len(keys) == 1:
                want |= {f"te_tax_view_est_{channel}_{part}" for part in ("law", "bill", "delta")}
            else:
                want |= {f"te_tax_view_est_{channel}_{part}_{end}" for part in ("law", "bill", "delta")
                         for end in ("lo", "hi")}
        self.assertEqual(self.names("te_tax_view_snap_") | self.names("te_tax_view_est_"), want)

    def test_generator_channels_are_the_budget_lines(self):
        self.assertEqual({name: (getter, tuple(keys)) for name, getter, keys in gen.CHANNELS}, CHANNELS)

    def test_every_value_is_guarded_inert_and_gated(self):
        names = self.names("te_tax_view_snap_") | self.names("te_tax_view_est_") | self.names("te_tax_est_")
        self.assertTrue(names)
        for name in names:
            body = self.values[name]
            with self.subTest(name=name):
                self.assertIsNotNone(body)
                self.assertIsNone(FORBIDDEN.search(body))
                for var in set(re.findall(r"var:(\w+)", body)):
                    self.assertIn(f"has_variable = {var}", body, f"var:{var} unguarded")
                if name.startswith("te_tax_view_est_") and not name.startswith("te_tax_view_est_cut_") and name not in (
                        "te_tax_view_est_poll_shared", "te_tax_view_est_regrel_state"):
                    self.assertIn(DRAFT_OPEN, norm(body), "a draft view reads only while a draft is open")
                if name.startswith("te_tax_view_est_cut_"):
                    self.assertIn(BILL_OPEN, norm(body), "an offer's estimate reads only while a bill is open")

    def test_snapshot_index_divisions_are_behind_a_positive_test(self):
        for path, text in self.texts.items():
            for match in re.finditer(r"divide = var:(te_tax_snap_\w+)", text):
                limits = enclosing_limits(text, match.start())
                with self.subTest(path=path, at=match.start(), var=match.group(1)):
                    self.assertTrue(any(f"var:{match.group(1)} > 0" in limit for limit in limits))
        # and nothing divides by a snapshot index any other way
        for name, body in self.values.items():
            if body:
                self.assertNotRegex(body, r"divide = (?!var:)\S*te_tax_snap_", name)

    def test_each_channel_scales_by_the_draft_against_the_snapshot(self):
        for key in KEYS:
            law, bill = self.values[f"te_tax_est_r_{key}_law"], self.values[f"te_tax_est_r_{key}_bill"]
            with self.subTest(key=key):
                self.assertIn(f"value = te_tax_base_dr_{key}", law)
                self.assertIn(f"value = te_tax_dr_eff_{key}", bill)
                for body in (law, bill):
                    self.assertIn(f"divide = var:te_tax_snap_{key}", body)
        for channel, (_, keys) in CHANNELS.items():
            on = norm(self.values[f"te_tax_view_est_{channel}_on"])
            for key in keys:
                with self.subTest(channel=channel, key=key):
                    self.assertIn(f"var:te_tax_dr_{key} >= 0", on)
            if len(keys) == 1:
                key = keys[0]
                self.assertIn(f"value = te_tax_est_r_{key}_law", self.values[f"te_tax_view_est_{channel}_law"])
                self.assertIn(f"value = te_tax_est_r_{key}_bill", self.values[f"te_tax_view_est_{channel}_bill"])
                delta = norm(self.values[f"te_tax_view_est_{channel}_delta"])
                self.assertIn(f"value = te_tax_est_r_{key}_bill subtract = te_tax_est_r_{key}_law", delta)

    def test_poll_bounds_take_the_lower_and_higher_of_the_two_shares(self):
        # GetPollTaxIncome is rural assessment plus head tax, split unknown: with both
        # collecting, any split gives a value between the two instruments' scalings.
        for part in ("law", "bill", "delta"):
            lo = norm(self.values[f"te_tax_view_est_poll_{part}_lo"])
            hi = norm(self.values[f"te_tax_view_est_poll_{part}_hi"])
            land, head = ((f"te_tax_est_d_{key}" if part == "delta" else f"te_tax_est_r_{key}_{part}")
                          for key in ("land", "head"))
            with self.subTest(part=part):
                self.assertIn(f"value = {land} max = {head}", lo)
                self.assertIn(f"value = {land} min = {head}", hi)
                # at most one collecting: its scaling alone (the other's helper is 0)
                for body in (lo, hi):
                    self.assertIn(f"else = {{ value = {land} add = {head} }}", body)
        shared = norm(self.values["te_tax_view_est_poll_shared"])
        self.assertIn("var:te_tax_snap_land > 0", shared)
        self.assertIn("var:te_tax_snap_head > 0", shared)

    def test_no_base_when_a_tax_the_schedules_collect_was_not_collected_at_the_snapshot(self):
        for channel, (_, keys) in CHANNELS.items():
            body = norm(self.values[f"te_tax_view_est_{channel}_nobase"])
            with self.subTest(channel=channel):
                self.assertIn(DRAFT_OPEN, body)
                for key in keys:
                    self.assertIn(f"NOT = {{ AND = {{ has_variable = te_tax_snap_{key} var:te_tax_snap_{key} > 0 }} }}",
                                  body)
                    self.assertIn(f"add = te_tax_base_dr_{key}", body)
                    self.assertIn(f"add = te_tax_dr_eff_{key}", body)
                self.assertTrue(body.endswith("max = 1"), body[-40:])

    def test_an_offer_cut_is_one_step_against_the_snapshot_index(self):
        for key in KEYS:
            body = norm(self.values[f"te_tax_view_est_cut_{key}"])
            with self.subTest(key=key):
                self.assertIn(f"var:te_tax_snap_{key} > 0", body)
                self.assertIn(f"value = -1 divide = var:te_tax_snap_{key}", body)

    def test_the_snapshot_is_current_only_for_this_month_this_code_and_this_revision(self):
        body = norm(self.values["te_tax_view_snap_current"])
        self.assertTrue(body.startswith("value = 0"))
        for condition in ("var:te_tax_snap_month = te_history_month_index",
                          "var:te_tax_snap_code_version = var:te_tax_code_version",
                          "var:te_tax_snap_bill_rev = var:te_tax_bl_rev"):
            with self.subTest(condition=condition):
                self.assertIn(condition, body)
        # the revision is compared only while a bill is open
        self.assertIn(f"NOT = {{ AND = {{ {BILL_OPEN} }} }}", body)

    def test_regional_relief_state_ratio(self):
        body = norm(self.values["te_tax_view_est_regrel_state"])
        self.assertIn("owner ?= {", body)
        self.assertIn("value = te_tax_est_regrel_keep_bill subtract = te_tax_est_regrel_keep_law "
                      "divide = te_tax_est_regrel_keep_now", body)
        now = norm(self.values["te_tax_est_regrel_keep_now"])
        self.assertIn("value = 4", now)
        self.assertIn("var:te_tax_relief_state = 1", now)
        self.assertIn("subtract = owner.var:te_tax_en_regrel", now)
        self.assertIn("min = 1", now, "never divides by zero")
        self.assertIn("value = te_tax_view_dr_relief_base_state multiply = owner.te_tax_base_dr_regrel",
                      norm(self.values["te_tax_est_regrel_keep_law"]))
        self.assertIn("value = te_tax_view_dr_relief_state multiply = owner.te_tax_dr_eff_regrel",
                      norm(self.values["te_tax_est_regrel_keep_bill"]))


class EstimatePanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = loc()
        cls.review = type_body(gui(REVIEW), "te_tax_review_section")
        cls.politics = gui(POLITICS)
        cls.card = type_body(cls.politics, "te_tax_ig_card")
        cls.overview = type_body(gui(OVERVIEW), "te_tax_overview_panel")

    def test_labels(self):
        self.assertIn("Static estimate at today's economy", self.loc["te_tax_est_static"])
        self.assertIn("Estimate out of date", self.loc["te_tax_est_stale"])
        self.assertIn("No current base — estimate unavailable", self.loc["te_tax_est_nobase"])
        self.assertIn("no current base — estimate unavailable", self.loc["te_tax_ig_offer_est_nobase"].lower())
        self.assertIn("te_tax_view_snap_current", self.review)
        self.assertIn("'te_tax_est_static', 'te_tax_est_stale'", self.review)

    def test_each_channel_row_has_a_no_base_branch_and_the_budget_getter(self):
        for channel, (getter, keys) in CHANNELS.items():
            with self.subTest(channel=channel):
                self.assertIn(f"ScriptValue('te_tax_view_est_{channel}_on')", self.review)
                self.assertRegex(self.review, rf"SelectLocalization\( EqualTo_CFixedPoint\( GetPlayer\.MakeScope\."
                                              rf"ScriptValue\('te_tax_view_est_{channel}_nobase'\), '\(CFixedPoint\)1' \), "
                                              rf"'te_tax_est_nobase'")
                forms = ("", "_range") if len(keys) > 1 else ("",)
                for form in forms:
                    text = self.loc[f"te_tax_est_{channel}{form}"]
                    self.assertIn(f"Multiply_CFixedPoint( GetPlayer.{getter}, GetPlayer.MakeScope.ScriptValue(", text)
                    for other in {g for g, _ in CHANNELS.values()} - {getter}:
                        self.assertNotIn(other, text)
                    # A two-tax line's single form prints the low bound, which equals
                    # the high one while at most one of its taxes collects.
                    if len(keys) == 1:
                        parts = ("law", "bill", "delta")
                    elif not form:
                        parts = ("law_lo", "bill_lo", "delta_lo")
                    else:
                        parts = tuple(f"{p}_{e}" for p in ("law", "bill", "delta") for e in ("lo", "hi"))
                    for part in parts:
                        self.assertIn(f"ScriptValue('te_tax_view_est_{channel}_{part}')", text)
        # Poll prints a range when both of its taxes collect at the snapshot.
        self.assertIn("ScriptValue('te_tax_view_est_poll_shared')", self.review)

    def test_goods_and_agricultural_relief_carry_labels_not_numbers(self):
        self.assertIn("depends on how much pops buy of these goods", self.loc["te_tax_est_goods"])
        self.assertIn("agricultural wages", self.loc["te_tax_est_agrel"])
        self.assertIn("named states", self.loc["te_tax_est_regrel"])
        for key in ("te_tax_est_goods", "te_tax_est_agrel", "te_tax_est_regrel"):
            with self.subTest(key=key):
                self.assertNotIn("_CFixedPoint", self.loc[key])
                self.assertIn(f'"{key}"', self.review)

    def test_regional_relief_prints_each_named_state_change(self):
        text = self.loc["te_tax_rv_regrel_state_est"]
        self.assertIn("Multiply_CFixedPoint( State.GetTaxationRevenue, "
                      "State.MakeScope.ScriptValue('te_tax_view_est_regrel_state') )", text)
        # the bill's states always; existing law's only when the draft drops one
        self.assertIn('text = "te_tax_rv_regrel_state_est"', self.review)
        self.assertIn("ScriptValue('te_tax_view_dr_relief_state'), '(CFixedPoint)0' ), 'te_tax_rv_regrel_state_est', "
                      "'te_tax_rv_regrel_state'", self.review)

    def test_an_offer_shows_its_revenue_change(self):
        self.assertIn("te_tax_disp_ig_offer_arg", self.card)
        for key in KEYS:
            getter = CHANNELS[CHANNEL_OF[key]][0]
            text = self.loc[f"te_tax_ig_offer_est_{key}"]
            with self.subTest(key=key):
                self.assertIn(f"Multiply_CFixedPoint( GetPlayer.{getter}, "
                              f"GetPlayer.MakeScope.ScriptValue('te_tax_view_est_cut_{key}') )", text)
                self.assertRegex(self.card, rf"ScriptValue\('te_tax_view_snap_{key}'\), '\(CFixedPoint\)0' \)( \))?, "
                                            rf"'te_tax_ig_offer_est_nobase'")
        for key in ("land", "head"):
            self.assertIn(f"'te_tax_ig_offer_est_{key}_shared'", self.card)
            self.assertIn("te_tax_view_est_cut_" + key, self.loc[f"te_tax_ig_offer_est_{key}_shared"])
        for key in ("te_tax_ig_offer_est_agrel", "te_tax_ig_offer_est_untax"):
            with self.subTest(key=key):
                self.assertNotIn("_CFixedPoint", self.loc[key])
                self.assertIn(f"'{key}'", self.card)
        self.assertIn("agricultural wages", self.loc["te_tax_ig_offer_est_agrel"])
        self.assertIn("how much pops buy", self.loc["te_tax_ig_offer_est_untax"])

    def test_the_overview_dates_the_snapshot_and_labels_the_aggregate(self):
        self.assertIn("te_tax_view_snap_month", self.overview)
        self.assertIn('"te_tax_ov_snapshot"', self.overview)
        readers = [key for key, text in self.loc.items() if "te_tax_view_snap_tax_income" in text]
        self.assertTrue(readers)
        for key in readers:
            with self.subTest(key=key):
                self.assertIn("domestic tax aggregate (unclassified)", self.loc[key].lower())

    def test_estimates_never_sweep_the_world_in_a_panel(self):
        # The Budget getters are the engine's own cached figures; a datamodel over
        # pops or buildings would be a per-frame sweep.
        for text in (self.review, self.card):
            self.assertNotRegex(text, r"datamodel = \"\[[^\]]*(Pops|Buildings)")


class GeneratedCommentTest(unittest.TestCase):
    def test_the_view_refresh_names_both_callers(self):
        generator = (ROOT / GENERATOR).read_text(encoding="utf-8")
        self.assertNotIn("processor only)", generator)
        for path in (GEN_EFFECTS, GEN_SUPPORT, GEN_MODIFIERS):
            text = raw(path)
            with self.subTest(path=path):
                self.assertIn("te_tax.4", text)

    def test_schema_doc_has_the_section(self):
        doc = raw(SCHEMA_DOC)
        self.assertTrue("\n## Economy snapshot and estimates\n" in doc, "no Economy snapshot section")
        for name in (*SNAP_FIELDS, "te_tax_take_snapshot", SNAPSHOT):
            with self.subTest(name=name):
                self.assertIn(name, doc)


if __name__ == "__main__":
    unittest.main()
