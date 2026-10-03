#!/usr/bin/env python3
"""Generate the legislated tax code's rate amendments, script values and loc.

The tax code (docs/superpowers/specs/2026-09-29-legislated-tax-code-design.md)
holds each tax instrument as an integer index: rate = index x step. The carrier
law `law_te_tax_code` collects nothing; one generated amendment per instrument
and index carries the rate, identical in all five native tax levels so that a
level change moves only the political static modifier. INSTRUMENTS below is the
single source of truth for that table; MIGRATION, for the rates each vanilla
taxation law sets at each native level.

Outputs (each is registered in OUTPUTS and written byte for byte):

  common/amendments/te_tax_amendments_generated.txt
      amendment_te_tax_<key>_<idx> for every instrument and every idx 1..max.
  common/script_values/te_tax_generated_values.txt
      te_tax_step_<key>, te_tax_max_<key> and te_tax_pct_step_<key> constants,
      and te_tax_slot_id_<slot> for the history ring.
  localization/english/te_tax_generated_l_english.yml
      A name and a _desc per amendment. organize_loc.py files these keys here
      (category TAX_GENERATED) and renders the file itself, so this script
      renders through organize_loc and the two always agree.
  common/scripted_effects/te_tax_generated_effects.txt
      The collection writer's per-instrument and per-good parts
      (te_tax_gen_sync_<key>, te_tax_gen_sync_goods), the initialiser's
      (te_tax_gen_init_instruments, te_tax_gen_init_goods,
      te_tax_gen_init_schedule) and the scheduler's (te_tax_gen_sunset_<key>,
      te_tax_gen_commence/hold_missed/apply/store_<slot>, te_tax_gen_next_month,
      te_tax_gen_history_write) and the migration's (te_tax_gen_migrate_rates,
      one branch per vanilla taxation law and native level from MIGRATION;
      te_tax_gen_migrate_goods; te_tax_gen_migrate_provisions), the copies
      for new countries (te_tax_gen_copy_code, te_tax_gen_copy_slot_<slot>,
      te_tax_gen_copy_enacted), and the policy obligations' init, outbreak
      copy and release reset (te_tax_gen_init_obligations,
      te_tax_gen_copy_obligations, te_tax_gen_clear_obligations).
  common/scripted_triggers/te_tax_generated_triggers.txt
      Amendment-scope family and match triggers the syncs filter on, the
      scheduler's package and bill checks (te_tax_gen_package_current_<slot>,
      te_tax_gen_package_touches_goods_<slot>, te_tax_gen_bill_sunsets_valid)
      and the draft and bill checks (te_tax_gen_draft_touches_any/_goods,
      te_tax_gen_bill_touches_goods, te_tax_gen_draft_baseline_current,
      te_tax_gen_draft_differs_from_bill, te_tax_gen_bill_current,
      te_tax_gen_bill_small_steps, te_tax_gen_bill_overlaps_<slot>,
      te_tax_gen_package_empty_<slot>, te_tax_gen_package_unsuperseded_<slot>)
      and the civil-war repair's obligation checks (te_tax_gen_obl_ig_exists,
      te_tax_gen_obl_slot_gone).
  common/scripted_effects/te_tax_generated_bill_effects.txt
      The draft, bill and passage parts (te_tax_gen_draft_init/_from_bill/
      _clear, te_tax_gen_bill_from_draft/_clear, te_tax_gen_supersede_<slot>,
      te_tax_gen_bump_pver, te_tax_gen_reset_commitments,
      te_tax_gen_refresh_support, te_tax_gen_oppose_approval) and the policy
      obligations' per-group consequences (te_tax_gen_obl_approval,
      te_tax_gen_obl_trust). The only generated file that removes variables:
      a closed record's payload.
  common/script_values/te_tax_generated_support_values.txt
      The draft, bill and support-model values: the baselines at the due
      month (instruments, relief bands, goods), delta-levels, the per-good
      goods terms (GOODS_CATEGORY_WEIGHT), the per-group reasons from the
      EXPOSURE, TAX_LAW_PROGRESSIVENESS and relief-points tables, the trust
      reasons (te_tax_trust_reason_<ig>) and the clout sums.
  common/customizable_localization/te_tax_generated_custom_loc.txt
      te_tax_hist_event_<i>: the line each history row prints (newest first),
      chosen by the entry's kind and, for a sunset, its instrument; and the
      promise rows' parts, te_tax_obl_ig_/what_/inst_/state_<n>.

The script-value file also carries the guarded te_tax_view_* display values
for every instrument and every catalog good, and the panels' views: the open
draft and bill, the package slots, the last change and the history ring
newest first (te_tax_view_hist_<i>_*). The consumption-goods catalog is
derived from the pop needs (vanilla_parsed/common/pop_needs.json plus the mod's
common/pop_needs/*.txt) and the goods definitions (vanilla_parsed/common/
goods.json plus common/goods/*.txt), always read from this repo, never --root.
Schema and catalog rule: docs/systems/tax_code_schema.md.

Later tasks register more outputs the same way: write a function returning the
file's bytes and decorate it with @output("<repo-relative path>").

Usage (repo root, system python3; standard library plus the repo's own
organize_loc and paradox_file_parser):

    python3 scripts/generators/gen_tax_code.py            # write the outputs
    python3 scripts/generators/gen_tax_code.py --check    # write nothing; exit 1 on drift
    python3 scripts/generators/gen_tax_code.py --root DIR # another tree (tests)
"""

import argparse
import functools
import glob
import json
import os
import sys
from decimal import Decimal
from typing import NamedTuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from organize_loc import _render_loc_file, section_label  # noqa: E402
from paradox_file_parser import ParadoxFileParser  # noqa: E402

HEADER = "# AUTO-GENERATED by scripts/generators/gen_tax_code.py — do not edit manually"
CARRIER_LAW = "law_te_tax_code"
GATE_TRIGGER = "te_tax_code_on"
LOC_CATEGORY = "TAX_GENERATED"
LEVELS = (
    "tax_modifier_very_low", "tax_modifier_low", "tax_modifier_medium",
    "tax_modifier_high", "tax_modifier_very_high",
)

AMENDMENTS_PATH = "common/amendments/te_tax_amendments_generated.txt"
VALUES_PATH = "common/script_values/te_tax_generated_values.txt"
LOC_PATH = "localization/english/te_tax_generated_l_english.yml"
EFFECTS_PATH = "common/scripted_effects/te_tax_generated_effects.txt"
TRIGGERS_PATH = "common/scripted_triggers/te_tax_generated_triggers.txt"

# Catalog inputs, read from REPO (never --root).
VANILLA_POP_NEEDS = "vanilla_parsed/common/pop_needs.json"
VANILLA_GOODS = "vanilla_parsed/common/goods.json"
MOD_POP_NEEDS_GLOB = "common/pop_needs/*.txt"
MOD_GOODS_GLOB = "common/goods/*.txt"

# Per-instrument schema tokens (docs/systems/tax_code_schema.md) and their
# sentinels: te_tax_en_<key><suffix>, then the two version tokens.
INSTRUMENT_TOKENS = (("", 0), ("_since", -1), ("_exp", -1), ("_succ", -1))
VERSION_TOKENS = (("te_tax_pver_", 0), ("te_tax_xver_", 0))

# Scheduler (docs/systems/tax_code_schema.md, "Scheduler, package slots and
# history"). Two approved-package slots; a history ring of eight entries.
SLOTS = ("a", "b")
SLOT_IDS = (("none", 0), ("a", 1), ("b", 2))    # te_tax_slot_id_<slot>, stored in history
PACKAGE_HEADER = (("_on", 0), ("_due", -1), ("_state", 0), ("_seq", 0))
HISTORY_SIZE = 8
HISTORY_FIELDS = (("month", -1), ("kind", 0), ("slot", 0), ("inst", 0), ("version", -1))
# History kinds the scheduler writes (the schema doc lists all ten).
KIND_COMMENCED, KIND_SUNSET, KIND_HELD_CONFLICT, KIND_HELD_MISSED = 1, 2, 3, 4
# Package state values.
STATE_EMPTY, STATE_AWAITING, STATE_HELD_CONFLICT, STATE_HELD_MISSED = 0, 1, 2, 3
# Relief fields a package carries besides the per-instrument and per-good ones.
PACKAGE_RELIEF_FIELDS = ("agrel", "regrel", "xver_relief")


def slot_relief_list(slot):
    """The country list naming the states slot `slot`'s package restates regional relief
    for (controller ruling, Task 11 fix round 1). A list, not per-state marks: a civil
    war's winner keeps no loser's list, so only its own packages' states can commence."""
    return f"te_tax_p{slot}_relief_states"


def _clear_list(name, indent="\t"):
    """Clears the country list `name` if it exists."""
    return f"{indent}if = {{ limit = {{ has_variable_list = {name} }} clear_variable_list = {name} }}"
# Every scheduler debug line ends with these. In the country events that run the
# scheduler ROOT = THIS = the country: the tax probe printed month=22032 through
# this ScriptValue form from a country event, and vanilla 1.14.5's election
# lines print the date through TimeKeeper. No $PARAM$ may appear in a debug_log.
LOG_STAMP = ("month=[SCOPE.ScriptValue('te_history_month_index')|0] "
             "date=[TimeKeeper.GetCurrentDate.GetString] "
             "country=[THIS.GetCountry.GetNameNoFormatting]")

# Draft, bill and passage (docs/systems/tax_code_schema.md, "Draft, bill and
# passage"). The draft is te_tax_dr_*, the bill under debate te_tax_bl_*; both
# hold, per instrument, the target index (-1 untouched), the sunset offset in
# months and the planned version recorded when the provision was first touched.
BILL_EFFECTS_PATH = "common/scripted_effects/te_tax_generated_bill_effects.txt"
SUPPORT_VALUES_PATH = "common/script_values/te_tax_generated_support_values.txt"
RECORDS = ("dr", "bl")
RECORD_KEY_FIELDS = (("", -1), ("_sun", 0), ("_pver", -1))   # te_tax_<rec>_<key><field>, draft sentinel
# The draft's country lists (plan Task 11): the states its regional relief names, and the
# player's incorporated states to choose them from. The bill's: te_tax_bl_relief_states.
DRAFT_LISTS = ("te_tax_dr_relief_states", "te_tax_dr_relief_candidates")
KIND_APPROVED, KIND_SUPERSEDED, KIND_RESCHEDULED, KIND_RELEASED = 6, 8, 9, 10

# The panels (plan Task 7): the Budget > Tax Code tab and the journal entry.
# The history rows' text is one customizable localization per row.
CUSTOM_LOC_PATH = "common/customizable_localization/te_tax_generated_custom_loc.txt"
KIND_MIGRATED, KIND_REPAIRED = 5, 7
# History kinds the policy obligations write (plan Task 12; te_tax_obligation_effects.txt).
KIND_OBL_FULFILLED, KIND_OBL_BREACHED, KIND_OBL_RENEGOTIATED, KIND_OBL_RELEASED = 11, 12, 13, 14
# Kinds that changed the enacted code (te_tax_code_version moved); the
# overview's last change is the newest of them.
CODE_CHANGE_KINDS = (KIND_COMMENCED, KIND_SUNSET, KIND_MIGRATED, KIND_REPAIRED)
# The line each history kind prints (te_tax_l_english.yml). A sunset prints
# te_tax_hist_kind_sunset_<key> for the instrument in its _inst.
HISTORY_KIND_KEYS = {
    KIND_COMMENCED: "te_tax_hist_kind_commenced",
    KIND_HELD_CONFLICT: "te_tax_hist_kind_held_conflict",
    KIND_HELD_MISSED: "te_tax_hist_kind_held_missed",
    KIND_MIGRATED: "te_tax_hist_kind_migrated",
    KIND_APPROVED: "te_tax_hist_kind_approved",
    KIND_REPAIRED: "te_tax_hist_kind_repaired",
    KIND_SUPERSEDED: "te_tax_hist_kind_superseded",
    KIND_RESCHEDULED: "te_tax_hist_kind_rescheduled",
    KIND_RELEASED: "te_tax_hist_kind_released",
    KIND_OBL_FULFILLED: "te_tax_hist_kind_obl_fulfilled",
    KIND_OBL_BREACHED: "te_tax_hist_kind_obl_breached",
    KIND_OBL_RENEGOTIATED: "te_tax_hist_kind_obl_renegotiated",
    KIND_OBL_RELEASED: "te_tax_hist_kind_obl_released",
}
HISTORY_KIND_FALLBACK = "te_tax_hist_kind_other"
# The workbench (plan Task 8): the per-instrument step handlers and per-good
# toggles, and the per-good rows of the workbench and the review.
SGUIS_PATH = "common/scripted_guis/te_tax_generated_sguis.txt"
ROWS_PATH = "gui/journal_entry_widgets/te_tax_generated_rows.gui"
# te_tax_step_<key>_sgui's op table: op -> (command, DIR). Ops 0-4 move the
# draft's target (te_tax_cmd_draft_step), 10-11 its expiry (te_tax_cmd_draft_sunset).
STEP_OPS = ((0, "draft_step", 0), (1, "draft_step", 1), (2, "draft_step", 2), (3, "draft_step", 3),
            (4, "draft_step", 4), (10, "draft_sunset", 0), (11, "draft_sunset", 1))
# The interest groups the support model scores, by type key (ig_<key>).
IGS = ("armed_forces", "devout", "industrialists", "intelligentsia",
       "landowners", "petty_bourgeoisie", "rural_folk", "trade_unions")
# One vanilla tax level per channel: the material and ideology reasons count a
# change in these units (delta index x step / level step).
LEVEL_STEPS = {"wage": Decimal("0.05"), "div": Decimal("0.05"), "land": Decimal("0.15"),
               "head": Decimal("0.15"), "cons": Decimal("0.05")}
# How exposed each interest group is to each channel (0..1), in INSTRUMENTS order.
EXPOSURE = {
    "trade_unions": "1.0 0.0 0.0 0.8 0.8",
    "rural_folk": "0.4 0.1 1.0 0.3 0.8",
    "petty_bourgeoisie": "0.6 0.4 0.1 0.5 0.6",
    "intelligentsia": "0.6 0.2 0.0 0.3 0.4",
    "devout": "0.4 0.3 0.3 0.4 0.5",
    "armed_forces": "0.3 0.2 0.1 0.3 0.4",
    "industrialists": "0.2 1.0 0.0 0.1 0.2",
    "landowners": "0.1 0.8 0.3 0.1 0.2",
}
# Raising these channels makes the code more progressive; raising the others, less.
PROGRESSIVE_KEYS = ("wage", "div")
# Vanilla 1.14.5 taxation laws and their progressiveness (checked against
# vanilla_parsed/common/laws.json by test_tax_code_bill.py). An interest group's
# fiscal ideology is the sum over these laws of its stance x progressiveness / 100.
TAX_LAW_PROGRESSIVENESS = (
    ("law_consumption_based_taxation", -100),
    ("law_land_based_taxation", -50),
    ("law_per_capita_based_taxation", 0),
    ("law_proportional_taxation", 50),
    ("law_graduated_taxation", 100),
)
# law_stance buckets, strongest first so each stance scores once.
STANCE_BRANCHES = (("value > approve", 2), ("value > neutral", 1),
                   ("value < disapprove", -2), ("value < neutral", -1))
MATERIAL_WEIGHT, IDEOLOGY_WEIGHT, GOVERNMENT_BONUS = -10, 5, 10
REASON_CAP, SCORE_CAP = 40, 100
SUPPORT_REASONS = ("mat", "ideo", "fisc", "gov", "prom", "trust")
# Relief provisions (plan Task 11): agricultural wage relief and regional relief, each a
# band from 0 (none) to RELIEF_MAX (1 = -25%, 2 = -50%; te_tax_relief_* static modifiers).
# A draft steps them like an instrument (te_tax_cmd_draft_relief, te_tax_relief_<key>_sgui).
RELIEF_KEYS = ("agrel", "regrel")
RELIEF_MAX = 2
# te_tax_relief_<key>_sgui's op table: op -> DIR of te_tax_cmd_draft_relief (no sunsets).
RELIEF_OPS = (0, 1, 2, 3, 4)
# The goods and relief parts of the material reason (plan Task 11). A good the bill puts
# on (or takes off) the taxed list moves the consumption channel by GOODS_LEVEL_STEPS tax
# levels times its category weight, from the goods file's `category`: staples weigh
# most, luxuries least; military goods reach pops only through the leisure need
# (aeroplanes, small_arms), so they weigh as luxuries. Every catalog good must have one.
GOODS_LEVEL_STEPS = Decimal("0.2")
GOODS_CATEGORY_WEIGHT = {"staple": Decimal("1.0"), "industrial": Decimal("0.3"),
                         "luxury": Decimal("0.2"), "military": Decimal("0.2")}
# Relief, in support points (after the x MATERIAL_WEIGHT of the tax channels):
# agricultural relief for the workers it relieves and the landowners whose estates
# employ them, per band, scaled by the wage tax it relieves (te_tax_bl_agrel_scaled);
# regional relief diffusely for every group, less for the two whose members worry most
# about the revenue lost, per band and quarter of the population named
# (te_tax_bl_regrel_coverage; spec 7.2: coverage matters, not just nominal rates).
AGREL_POINTS = {"rural_folk": 8, "landowners": 3}
REGREL_POINTS_ALL = 4
REGREL_POINTS_CONCERN = {"industrialists": -2, "petty_bourgeoisie": -2}
# Traditionalism holds a bill to no tax on these (te_tax_draft_ready).
TRADITIONALISM_KEYS = ("wage", "div")
# Policy obligations (plan Task 12; docs/systems/tax_code_schema.md, "Policy obligations"):
# four slots te_tax_o<n>_*. The header tokens are initialised and copied like a package
# slot's; the payload is written whole by te_tax_obl_write (te_tax_obligation_effects.txt)
# and read only while the slot's _on is 1.
OBLIGATION_SLOTS = (1, 2, 3, 4)
OBLIGATION_HEADER = (("_on", 0), ("_state", 0))
OBLIGATION_PAYLOAD = ("kind", "arg", "target", "baseline", "ig", "deadline", "maint_end", "streak", "fails",
                      "maint_only", "slot", "rev")
# Obligation states: 1 pending passage (attached to the bill), 7 bound to a passed bill's
# slot and awaiting its commencement, 2 delivering, 3 maintaining; 4 fulfilled, 5 breached,
# 6 renegotiated are outcomes, recorded when the slot is freed.
OBL_PENDING, OBL_DELIVERING, OBL_MAINTAINING, OBL_BOUND = 1, 2, 3, 7
OBL_BINDING_STATES = (OBL_BOUND, OBL_DELIVERING, OBL_MAINTAINING)
# Kind 1's institutions by _arg, kind 3's military wage levels by _arg.
OBL_INSTITUTIONS = ((1, "institution_schools"), (2, "institution_health_system"), (3, "institution_social_security"))
OBL_WAGE_LEVELS = ((1, "very_low"), (2, "low"), (3, "medium"), (4, "high"), (5, "very_high"))
# Trust (te_tax_trust_<ig>): +1 per kept promise, -1 per broken or renegotiated one, within
# +-TRUST_CAP; te_tax_trust_<ig>_month records the month of its last change, and it moves a step
# back toward 0 after te_tax_obl_trust_recover_months without one. The support model's trust
# reason is TRUST_WEIGHT points per step, so the cap keeps the reason inside +-REASON_CAP.
TRUST_WEIGHT, TRUST_CAP = 10, 4
# Offers (plan Task 13; docs/systems/tax_code_schema.md, "Offers"). At the support refresh
# each interest group that has not committed to the bill's revision and is not marginal may
# make one offer (te_tax_off_<ig>_kind): a clause (OFFER_CUT, OFFER_AGREL, OFFER_STAPLE) that
# changes the bill, or a promise (OFFER_PROMISE + its obligation kind) that records a policy
# obligation (te_tax_obl_propose). The clause codes double as the te_tax_bl_got_<ig>_<code>
# records of what a group already gained in this bill.
OFFER_CUT, OFFER_AGREL, OFFER_STAPLE = 1, 2, 3
OFFER_PROMISE = 10
# Clause offers per group, preferred first. A clause only softens what the bill changes, or
# adds relief (controller ruling, Task 13 pre-review): OFFER_CUT lowers by one step the tax
# the bill raises that weighs most on the group (its top grievance, the largest exposure-
# weighted raise, te_tax_bl_grief_<ig>_<key>), never below existing law; OFFER_STAPLE stops
# taxing a staple the bill adds, when the goods it taxes are the group's top grievance
# (the first in staple_order()); OFFER_AGREL adds a band of agricultural relief. A grievance
# that is not a raised provision or an added good gets a promise instead, or no offer.
CLAUSE_OFFERS = {
    "trade_unions": (OFFER_CUT, OFFER_STAPLE),
    "rural_folk": (OFFER_CUT, OFFER_STAPLE, OFFER_AGREL),
}
# Promise offers (Task 12's obligation adapters): (name, obligation kind, arg, TARGET, groups).
PROMISE_OFFERS = (
    ("schools", 1, 1, "te_tax_obl_inst_next_1", ("rural_folk", "devout", "intelligentsia")),
    ("health", 1, 2, "te_tax_obl_inst_next_2", ("trade_unions",)),
    ("bureaucracy", 2, 0, "0", ("industrialists", "petty_bourgeoisie")),
    ("fiscal", 4, 0, "0", ("industrialists", "landowners")),
)
# A promise's side effect on the other groups (spec 7.3: a concession can alienate other
# actors): an institution promise is welcomed by a group whose ideology disapproves of the
# law that has none of that institution, and resented by one that approves of it, by
# PROMISE_SIDE_POINTS per stance step (strongly x2), read live with law_stance as the
# ideology reason reads the taxation laws. The balance promises (kinds 2 and 4) name an
# outcome no ideology takes a stance on, so they have none.
PROMISE_SIDE_LAWS = {(1, 1): "law_no_schools", (1, 2): "law_no_health_system"}
PROMISE_SIDE_POINTS = -3
# Interest-group views of the enacted code (plan Task 13, controller ruling): a group's band is
# its own vanilla stance (law_stance, STANCE_BRANCHES) toward the vanilla taxation law the
# enacted code is equivalent to (te_tax_code_equivalent_<law>, te_tax_triggers.txt: graduated,
# else proportional, else per-capita, else land-based with a rural assessment, else
# consumption-based), -2 strongly opposes .. +2 strongly endorses. One static modifier per
# group and nonzero band, te_tax_ig_view_<ig>_<band>; band 0 carries none. Each reproduces the
# approval vanilla gives an interest group for an active law it takes that stance on: 1.14.5
# defines IG_APPROVAL_FROM_LAW = 1 (approve, disapprove) and IG_APPROVAL_FROM_LAW_STRONG_STANCE
# = 2 (strongly). lawgroup_taxation's ideological_opinion_impact (0.5) scales the legitimacy
# friction between governing groups that disagree on a law, not this approval
# (docs/vanilla/vanilla_politics_reference.md section 2.4; inferred from the defines, not
# observed in game). At migration the equivalent law is the law the country had, so the
# migration changes no group's approval (test_tax_code_offers.py round-trips every
# MIGRATION row).
EQUIVALENT_LAWS = (("graduated", "law_graduated_taxation"), ("proportional", "law_proportional_taxation"),
                   ("per_capita", "law_per_capita_based_taxation"), ("land_based", "law_land_based_taxation"),
                   ("consumption_based", "law_consumption_based_taxation"))
VANILLA_APPROVAL_FROM_LAW, VANILLA_APPROVAL_FROM_LAW_STRONG = 1, 2
VIEW_BANDS = (("m2", -2), ("m1", -1), ("p1", 1), ("p2", 2))
VIEW_APPROVAL = {-2: -VANILLA_APPROVAL_FROM_LAW_STRONG, -1: -VANILLA_APPROVAL_FROM_LAW,
                 1: VANILLA_APPROVAL_FROM_LAW, 2: VANILLA_APPROVAL_FROM_LAW_STRONG}
VIEW_ICONS = {-2: "modifier_documents_negative", -1: "modifier_documents_negative",
              1: "modifier_documents_positive", 2: "modifier_documents_positive"}
MODIFIERS_PATH = "common/static_modifiers/te_tax_generated_modifiers.txt"


class Instrument(NamedTuple):
    key: str            # short name used in every generated identifier
    modifier: str       # the native tax modifier the amendment carries
    step: Decimal       # rate per index
    max_idx: int        # highest index that gets an amendment
    label: str          # shown to the player (title-cased in loc)
    payer: str          # who pays, as it reads in "Taxes <payer> at <rate>."
    percent: bool       # printed as a percentage (else as a bare amount)
    vanilla: tuple      # every value the five vanilla taxation laws set


def _values(text):
    return tuple(Decimal(value) for value in text.split())


INSTRUMENTS = (
    Instrument("wage", "tax_income_add", Decimal("0.025"), 20, "Wage tax",
               "the wages of employed pops", True,
               _values("0.05 0.075 0.10 0.125 0.15 0.175 0.20 0.25 0.30")),
    Instrument("div", "tax_dividends_add", Decimal("0.025"), 20, "Dividend tax",
               "dividends paid to pops who own private buildings", True,
               _values("0.025 0.05 0.10 0.15 0.20 0.25 0.30")),
    Instrument("land", "tax_land_add", Decimal("0.025"), 48, "Rural assessment",
               "peasants and farmers working agricultural buildings, who then pay no head tax",
               False, _values("0.20 0.275 0.35 0.40 0.425 0.50 0.55 0.70 0.85 1.00")),
    Instrument("head", "tax_per_capita_add", Decimal("0.05"), 30, "Head tax",
               "working adults who pay no rural assessment", False,
               _values("0.40 0.55 0.70 0.85 1.00")),
    Instrument("cons", "tax_consumption_add", Decimal("0.05"), 12, "Consumption tax rate",
               "goods on the taxed-goods list when pops buy them", True,
               _values("0.15 0.20 0.25 0.30 0.35")),
)


# Migration (docs/systems/tax_code_schema.md, "Migration"): the rates each vanilla
# 1.14.5 taxation law sets at each native tax level, in NATIVE_LEVELS order. An
# instrument a law leaves out is 0. test_tax_code_migration.py checks this table
# against vanilla_parsed/common/laws.json, so a vanilla patch that moves a rate or
# adds a law to lawgroup_taxation fails until the table is updated.
NATIVE_LEVELS = ("very_low", "low", "medium", "high", "very_high")
CONSUMPTION_LADDER = "0.15 0.20 0.25 0.30 0.35"
MIGRATION = (
    ("law_consumption_based_taxation", {"cons": CONSUMPTION_LADDER}),
    ("law_land_based_taxation", {"land": "0.40 0.55 0.70 0.85 1.00", "cons": CONSUMPTION_LADDER}),
    ("law_per_capita_based_taxation", {"wage": "0.05 0.075 0.10 0.125 0.15",
                                       "land": "0.20 0.275 0.35 0.425 0.50",
                                       "head": "0.40 0.55 0.70 0.85 1.00",
                                       "cons": CONSUMPTION_LADDER}),
    ("law_proportional_taxation", {"wage": "0.10 0.15 0.20 0.25 0.30",
                                   "div": "0.025 0.05 0.10 0.15 0.20",
                                   "cons": CONSUMPTION_LADDER}),
    ("law_graduated_taxation", {"wage": "0.10 0.125 0.15 0.175 0.20",
                                "div": "0.10 0.15 0.20 0.25 0.30",
                                "cons": CONSUMPTION_LADDER}),
)


def migration_indices(instruments=INSTRUMENTS):
    """[(law, level, {key: index})] for every MIGRATION law and native level, 25 in all.

    Raises ValueError if a rate is not index x step for an index in 0..max or is
    not one of the instrument's vanilla values.
    """
    by_key = {instrument.key: instrument for instrument in instruments}
    rows = []
    for law, rates in MIGRATION:
        unknown = set(rates) - set(by_key)
        if unknown:
            raise ValueError(f"{law}: no instrument {sorted(unknown)}")
        for n, level in enumerate(NATIVE_LEVELS):
            indices = {}
            for key, instrument in by_key.items():
                value = Decimal(rates[key].split()[n]) if key in rates else Decimal(0)
                index, remainder = divmod(value, instrument.step)
                if remainder != 0 or not 0 <= index <= instrument.max_idx:
                    raise ValueError(f"{law} {level}: {key} = {value} is not an index x {instrument.step}")
                if value and value not in instrument.vanilla:
                    raise ValueError(f"{law} {level}: {key} = {value} is not a vanilla value of {key}")
                indices[key] = int(index)
            rows.append((law, level, indices))
    return rows


def validate(instruments=INSTRUMENTS):
    """Raise ValueError unless every vanilla value is index x step for some index 1..max
    and every catalog good has a support weight (goods_weight)."""
    for instrument in instruments:
        for value in instrument.vanilla:
            index, remainder = divmod(value, instrument.step)
            if remainder != 0 or not 1 <= index <= instrument.max_idx:
                raise ValueError(
                    f"{instrument.key}: vanilla value {value} is not index x {instrument.step} "
                    f"for an index in 1..{instrument.max_idx}"
                )
    migration_indices(instruments)
    for good in consumption_catalog():
        goods_weight(good)
    if TRUST_CAP * TRUST_WEIGHT > REASON_CAP:
        raise ValueError(f"trust {TRUST_CAP} x {TRUST_WEIGHT} points would pass the reason cap {REASON_CAP}")


def fmt(value):
    """A Decimal without trailing zeros or an exponent: 0.075, 0.1, 1, 10."""
    return format(value.normalize(), "f")


def rate(instrument, idx):
    return instrument.step * idx


def amendment_key(instrument, idx):
    return f"amendment_te_tax_{instrument.key}_{idx}"


def display(instrument, idx):
    """The rate as the player reads it: 7.5% for a rate, 0.425 for an amount."""
    value = rate(instrument, idx)
    return f"{fmt(value * 100)}%" if instrument.percent else fmt(value)


# ---------------------------------------------------------------------------
# Consumption-goods catalog
# ---------------------------------------------------------------------------

_OPERATORS = {"=", "<", ">", "<=", ">=", "!=", "?=", "=="}


def _plain(node):
    """Drop (operator, value) pairs from parser or vanilla_parsed JSON output."""
    if (isinstance(node, (tuple, list)) and len(node) == 2
            and isinstance(node[0], str) and node[0] in _OPERATORS):
        return _plain(node[1])
    if isinstance(node, dict):
        return {key: _plain(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_plain(item) for item in node]
    return node


def _merged(vanilla_json, mod_glob):
    """Vanilla entries overlaid with the mod's files, as the engine loads them.

    REPLACE:x replaces x; INJECT:x overwrites x's fields and appends its
    `entry` blocks (a pop need's repeated key); a plain key the vanilla
    database already holds is dropped ("Duplicated key").
    """
    with open(os.path.join(REPO, vanilla_json), encoding="utf-8") as handle:
        merged = _plain(json.load(handle))
    for path in sorted(glob.glob(os.path.join(REPO, mod_glob))):
        parser = ParadoxFileParser()
        parser.parse_file(path, apply_directives=False)
        for key, body in _plain(parser.data).items():
            directive, _, name = key.rpartition(":")
            if not isinstance(body, dict):
                continue
            if "REPLACE" in directive or (directive and name not in merged and "OR_CREATE" in directive):
                merged[name] = body
            elif "INJECT" in directive and name in merged:
                injected = {**merged[name], **body}
                if "entry" in merged[name] and "entry" in body:
                    injected["entry"] = _as_list(merged[name]["entry"]) + _as_list(body["entry"])
                merged[name] = injected
            elif not directive and name not in merged:
                merged[name] = body
    return merged


def _as_list(value):
    return value if isinstance(value, list) else [value]


@functools.lru_cache(maxsize=None)
def goods_definitions():
    return {name: body for name, body in _merged(VANILLA_GOODS, MOD_GOODS_GLOB).items()
            if isinstance(body, dict)}


@functools.lru_cache(maxsize=None)
def pop_need_goods():
    """{good: (pop need, ...)} for every good some pop need lists as an entry."""
    used = {}
    for need, body in sorted(_merged(VANILLA_POP_NEEDS, MOD_POP_NEEDS_GLOB).items()):
        entries = body.get("entry", []) if isinstance(body, dict) else []
        for entry in _as_list(entries):
            used.setdefault(entry["goods"], []).append(need)
    return {good: tuple(needs) for good, needs in used.items()}


@functools.lru_cache(maxsize=None)
def consumption_catalog():
    """The goods a code can put on the taxed-goods list: every good a pop need buys, sorted.

    A good with no `consumption_tax_cost` costs the engine default
    (DEFAULT_GOODS_TAX_COST = 100, 1.14.5 00_defines.txt) and is still
    taxable: vanilla history taxes liquor, tobacco, opium and wine, none of
    which sets one, and the local goods services, transportation and
    electricity are taxable too.
    """
    goods = goods_definitions()
    for good in pop_need_goods():
        if good not in goods:
            raise ValueError(f"pop need good {good} has no goods definition")
    return tuple(sorted(pop_need_goods()))


def goods_weight(good):
    """The support model's weight for catalog good `good` (GOODS_CATEGORY_WEIGHT), from its
    goods-file category. Raises ValueError for a category the table lacks."""
    category = goods_definitions()[good].get("category")
    if category not in GOODS_CATEGORY_WEIGHT:
        raise ValueError(f"catalog good {good}: category {category!r} has no GOODS_CATEGORY_WEIGHT")
    return GOODS_CATEGORY_WEIGHT[category]


def all_goods():
    """Every good defined by vanilla or the mod, sorted."""
    return tuple(sorted(goods_definitions()))


def stray_goods():
    """Goods outside the catalog: no pop buys them, so no code taxes them.

    te_tax_gen_sync_goods removes a native consumption tax on any of these,
    so the native taxed set always equals the enacted one.
    """
    catalog = set(consumption_catalog())
    return tuple(good for good in all_goods() if good not in catalog)


# ---------------------------------------------------------------------------
# Output registry
# ---------------------------------------------------------------------------

OUTPUTS = {}


def output(path):
    """Register a function returning one output file's bytes under its repo-relative path."""
    def register(function):
        OUTPUTS[path] = function
        return function
    return register


def _txt(text):
    """A brace .txt file's bytes: UTF-8 BOM, LF endings."""
    return text.encode("utf-8-sig")


@output(AMENDMENTS_PATH)
def amendments():
    lines = [
        HEADER,
        "# One amendment per instrument and index: rate = index x step (INSTRUMENTS in the generator).",
        f"# {CARRIER_LAW} collects nothing; the amendment attached to it carries the rate. All five",
        "# tax_modifier_* blocks are identical, so a native tax-level change moves only the",
        "# political static modifier. Nothing sponsors, revokes or repeals these on its own.",
    ]
    for instrument in INSTRUMENTS:
        lines += ["", f"# {instrument.label}: {instrument.modifier}, step {fmt(instrument.step)}, "
                      f"indexes 1..{instrument.max_idx}"]
        for idx in range(1, instrument.max_idx + 1):
            value = fmt(rate(instrument, idx))
            if idx > 1:
                lines.append("")
            lines += [
                f"{amendment_key(instrument, idx)} = {{",
                f"\tparent = {CARRIER_LAW}",
                f"\tallowed_laws = {{ {CARRIER_LAW} }}",
                f"\tpossible = {{ {GATE_TRIGGER} = yes }}",
                "\tcan_repeal = { always = no }",
                "\twould_sponsor = { always = no }",
                "\tai_will_revoke = { always = no }",
            ]
            lines += [f"\t{level} = {{ {instrument.modifier} = {value} }}" for level in LEVELS]
            lines.append("}")
    return _txt("\n".join(lines) + "\n")


@output(VALUES_PATH)
def script_values():
    lines = [
        HEADER,
        "# Index encoding for the legislated tax code: rate = index x te_tax_step_<key>, with",
        "# the index from 0 (not set) to te_tax_max_<key>. A display value is written as",
        "# `value = var:<index variable>` `multiply = te_tax_step_<key>`; te_tax_pct_step_<key>",
        "# is the step in percentage points, for the instruments printed as a percentage.",
    ]
    for instrument in INSTRUMENTS:
        lines += [
            "",
            f"te_tax_step_{instrument.key} = {fmt(instrument.step)}",
            f"te_tax_max_{instrument.key} = {instrument.max_idx}",
        ]
        if instrument.percent:
            lines.append(f"te_tax_pct_step_{instrument.key} = {fmt(instrument.step * 100)}")
    lines += ["", "# Relief bands: 0 none, 1 = -25%, 2 = -50% (te_tax_relief_* static modifiers)."]
    lines += [f"te_tax_max_{key} = {RELIEF_MAX}" for key in RELIEF_KEYS]
    lines += [
        "",
        "# Package slots as the history ring stores them (te_tax_h<n>_slot): none, a, b.",
        "# te_tax_gen_history_write reads te_tax_slot_id_<SLOT>, so callers pass the letter.",
    ]
    lines += [f"te_tax_slot_id_{name} = {value}" for name, value in SLOT_IDS]
    lines += [
        "",
        "# Interest groups as an obligation stores its beneficiary (te_tax_o<n>_ig): te_tax_obl_propose",
        "# takes IG = te_tax_ig_id_<ig> (plan Task 12; the support model's IGS order).",
    ]
    lines += [f"te_tax_ig_id_{ig} = {idx}" for idx, ig in enumerate(IGS, start=1)]
    lines += [
        "",
        "# Display values (docs/systems/tax_code_schema.md, \"Display values\"): guarded reads of",
        "# the enacted code for the GUI and loc. Each reads only variables it has just tested",
        "# with has_variable and returns the schema sentinel when one is absent: 0 for an index,",
        "# a rate or a flag, -1 for a month or a successor. _y/_mo split a month index into a",
        "# year and a 1-based month, because the GUI cannot divide. They write nothing.",
    ]
    for instrument in INSTRUMENTS:
        lines += [""] + _instrument_views(instrument)
    lines += ["", "# One per catalog good: 1 if the good is on the enacted taxed-goods list."]
    for good in consumption_catalog():
        lines += _guarded_view(f"te_tax_view_en_g_{good}", f"te_tax_en_g_{good}", 0)
    lines += ["", "# How many catalog goods the enacted code taxes.", "te_tax_view_goods_count = {",
              "\tvalue = 0"]
    for good in consumption_catalog():
        variable = f"te_tax_en_g_{good}"
        lines.append(f"\tif = {{ limit = {{ has_variable = {variable} }} add = var:{variable} }}")
    lines.append("}")
    lines += _panel_views()
    return _txt("\n".join(lines) + "\n")


def _panel_views():
    """The views the Budget > Tax Code tab and the journal entry read (plan Task 7)."""
    lines = [
        "",
        "# The panels' views: the open draft and the bill under debate, the two package",
        "# slots, the newest change to the code and the history ring newest first. A record's",
        "# payload is read only while its own token says it is open: a closed record's payload",
        "# is removed, and a civil war's winner may hold a loser's stale copy.",
    ]
    for record in RECORDS:
        token = f"te_tax_{record}_on"
        lines += _guarded_view(f"te_tax_view_{record}_on", token, 0)
        lines += _month_views(f"te_tax_view_{record}_due", f"te_tax_{record}_due", _is_open(token))
    lines += ["", "# Package slots: on, state (1 awaiting, 2 held_conflict, 3 held_missed), due month."]
    for slot in SLOTS:
        token = f"te_tax_p{slot}_on"
        lines += _guarded_view(f"te_tax_view_p{slot}_on", token, 0)
        lines += _guarded_view(f"te_tax_view_p{slot}_state", f"te_tax_p{slot}_state", 0,
                               condition=_is_open(token))
        lines += _month_views(f"te_tax_view_p{slot}_due", f"te_tax_p{slot}_due", _is_open(token))
    return (lines + _last_change_views() + _history_views() + _workbench_views() + _ig_values()
            + _obligation_views())


def _obligation_views():
    """The promise rows' views (plan Task 12): per obligation slot, its token, and its
    payload only while the slot is on (_on = 1); then how many are binding and pending."""
    lines = [
        "",
        "# Policy obligations (plan Task 12): per slot <n>, on; state (1 pending, 7 bound, 2",
        "# delivering, 3 maintaining), kind, arg, target, beneficiary group, baseline, the kind-4",
        "# surplus streak, the failing maintenance checks and their limit (grace), whether it",
        "# maintains existing provision; the deadline and the end of maintenance as months with",
        "# their year and month. A payload view reads only while the slot is on: a freed slot's",
        "# payload stays, and a civil war's winner may hold a loser's.",
    ]
    for n in OBLIGATION_SLOTS:
        token = f"te_tax_o{n}_on"
        lines += _guarded_view(f"te_tax_view_o{n}_on", token, 0)
        for field in ("state", "kind", "arg", "target", "ig", "baseline", "streak", "fails", "maint_only"):
            lines += _guarded_view(f"te_tax_view_o{n}_{field}", f"te_tax_o{n}_{field}", 0, condition=_is_open(token))
        # The failing checks a maintained obligation may reach before it breaches
        # (te_tax_obl_grace_<kind>).
        lines += [f"te_tax_view_o{n}_grace = {{", "\tvalue = 0"]
        lines += [f"\tif = {{ limit = {{ {_is_open(token)} has_variable = te_tax_o{n}_kind var:te_tax_o{n}_kind = {kind} }} "
                  f"value = te_tax_obl_grace_{kind} }}" for kind in (1, 2, 3, 4)]
        lines.append("}")
        for field in ("deadline", "maint_end"):
            lines += _month_views(f"te_tax_view_o{n}_{field}", f"te_tax_o{n}_{field}", _is_open(token))
    for name, states in (("binding", OBL_BINDING_STATES), ("pending", (OBL_PENDING,))):
        lines += [f"te_tax_view_obl_{name} = {{", "\tvalue = 0"]
        for n in OBLIGATION_SLOTS:
            matches = " ".join(f"var:te_tax_o{n}_state = {state}" for state in states)
            lines.append(f"\tif = {{ limit = {{ {_is_open(f'te_tax_o{n}_on')} has_variable = te_tax_o{n}_state "
                         f"OR = {{ {matches} }} }} add = 1 }}")
        lines.append("}")
    return lines


def _view(name, default, limit, body):
    """A te_tax_view_*: `default`, or the `body` lines when `limit` holds."""
    return [f"{name} = {{", f"\tvalue = {default}", "\tif = {", f"\t\tlimit = {{ {limit} }}"] + [
        f"\t\t{line}" for line in body] + ["\t}", "}"]


DRAFT_OPEN = "has_variable = te_tax_dr_on var:te_tax_dr_on = 1 has_variable = te_tax_dr_due"


def _workbench_views():
    """The workbench, review and pending panels' views (plan Task 8). A draft's
    payload is read only while te_tax_dr_on is 1, a package's only while its slot
    is on. The "law" values are the baseline in the draft's due month
    (te_tax_base_dr_*), the value an untouched provision starts from and the one
    the bill's class and support measure change against."""
    lines = [
        "",
        "# The workbench and review (plan Task 8), per instrument: whether the draft changes it,",
        "# the rate in force under existing law in the draft's due month, the draft's rate and the",
        "# change, its expiry offset and month, the rate it would revert to, and whether a passed bill",
        "# or an outside change moved its baseline since the draft changed it (a rebase is needed).",
    ]
    for instrument in INSTRUMENTS:
        key = instrument.key
        dr, step = f"te_tax_dr_{key}", f"multiply = te_tax_step_{key}"
        touched = f"{DRAFT_OPEN} has_variable = {dr} var:{dr} >= 0"
        lines += _view(f"te_tax_view_dr_{key}_on", 0, touched, ["value = 1"])
        lines += _view(f"te_tax_view_dr_{key}_base_rate", 0, DRAFT_OPEN, [f"value = te_tax_base_dr_{key}", step])
        lines += _view(f"te_tax_view_dr_{key}_rate", 0, DRAFT_OPEN, [f"value = te_tax_dr_eff_{key}", step])
        lines += _view(f"te_tax_view_dr_{key}_delta_rate", 0, DRAFT_OPEN,
                       [f"value = te_tax_dr_eff_{key}", f"subtract = te_tax_base_dr_{key}", step])
        lines += _view(f"te_tax_view_dr_{key}_sun", 0, f"{touched} has_variable = {dr}_sun",
                       [f"value = var:{dr}_sun"])
        expiry = f"te_tax_view_dr_{key}_exp"
        lines += _view(expiry, -1, f"{touched} has_variable = {dr}_sun var:{dr}_sun > 0",
                       ["value = var:te_tax_dr_due", f"add = var:{dr}_sun"])
        lines += _split_month(expiry, expiry, "has_variable = te_tax_dr_on var:te_tax_dr_on = 1")
        lines += _view(f"te_tax_view_dr_{key}_succ_rate", 0, DRAFT_OPEN, [f"value = te_tax_succ_dr_{key}", step])
        pver, mark = f"te_tax_pver_{key}", f"{dr}_pver"
        lines += _view(f"te_tax_view_dr_{key}_rebase", 0,
                       f"{DRAFT_OPEN} has_variable = {mark} has_variable = {pver} var:{mark} >= 0 "
                       f"NOT = {{ var:{mark} = var:{pver} }}", ["value = 1"])
    lines += ["", "# Per catalog good: taxed under existing law in the draft's due month, taxed in the draft,",
              "# and whether the draft touches it; then the counts and the goods' rebase flag."]
    goods = consumption_catalog()
    for good in goods:
        flag = f"te_tax_dr_g_{good}"
        lines += _view(f"te_tax_view_dr_g_{good}_base", 0, DRAFT_OPEN, [f"value = te_tax_base_dr_g_{good}"])
        lines += _view(f"te_tax_view_dr_g_{good}", 0, f"{DRAFT_OPEN} has_variable = {flag}",
                       [f"value = te_tax_base_dr_g_{good}", f"if = {{ limit = {{ var:{flag} >= 0 }} value = var:{flag} }}"])
        lines += _view(f"te_tax_view_dr_g_{good}_on", 0, f"{DRAFT_OPEN} has_variable = {flag} var:{flag} >= 0",
                       ["value = 1"])
    for name, suffix in (("te_tax_view_dr_goods_count", ""), ("te_tax_view_dr_goods_base_count", "_base"),
                         ("te_tax_view_dr_goods_changed", "_on")):
        lines += _view(name, 0, DRAFT_OPEN, [f"add = te_tax_view_dr_g_{good}{suffix}" for good in goods])
    lines += _view("te_tax_view_dr_goods_rebase", 0,
                   f"{DRAFT_OPEN} has_variable = te_tax_dr_goods_pver has_variable = te_tax_pver_goods "
                   "var:te_tax_dr_goods_pver >= 0 NOT = { var:te_tax_dr_goods_pver = var:te_tax_pver_goods }",
                   ["value = 1"])
    lines += _view("te_tax_view_dr_provisions", 0, DRAFT_OPEN, ["value = te_tax_dr_provisions"])
    lines += ["", "# Per package slot and instrument: whether the passed bill changes it, its rate, its expiry",
              "# and the stored \"reverts to\" preview; and how many goods it changes."]
    for slot in SLOTS:
        p = f"te_tax_p{slot}"
        on = _is_open(f"{p}_on")
        for instrument in INSTRUMENTS:
            key = instrument.key
            touched = f"{on} has_variable = {p}_{key} var:{p}_{key} >= 0"
            lines += _view(f"te_tax_view_p{slot}_{key}_on", 0, touched, ["value = 1"])
            lines += _view(f"te_tax_view_p{slot}_{key}_rate", 0, touched,
                           [f"value = var:{p}_{key}", f"multiply = te_tax_step_{key}"])
            lines += _month_views(f"te_tax_view_p{slot}_{key}_exp", f"{p}_{key}_exp", on)
            lines += _view(f"te_tax_view_p{slot}_{key}_succ_rate", 0,
                           f"{on} has_variable = {p}_{key}_succ var:{p}_{key}_succ >= 0",
                           [f"value = var:{p}_{key}_succ", f"multiply = te_tax_step_{key}"])
        lines += _view(f"te_tax_view_p{slot}_goods_changed", 0, on,
                       [f"if = {{ limit = {{ has_variable = {p}_g_{good} var:{p}_g_{good} >= 0 }} add = 1 }}"
                        for good in goods])
    return lines


# The interest-group cards' stance codes (te_tax_disp_ig_stance).
STANCE_COMMITTED, STANCE_PERSUADABLE, STANCE_OPPOSED, STANCE_RED_LINE, STANCE_MARGINAL = 1, 2, 3, 4, 5


def _ig_values():
    """Interest-group scope values for the passage panel's actor cards, read as
    InterestGroup.MakeScope.ScriptValue('te_tax_disp_ig_*') under a datamodel over
    the player's groups. Commitments and reasons are country variables per group
    type (te_tax_com_<ig>, te_tax_sup_<ig>, te_tax_sr_<ig>_<reason>), so each value
    finds the group's type through an is_interest_group_type chain and reads its
    owner's snapshot, only while a bill is open: the snapshot outlives the bill."""
    lines = [
        "",
        "# The passage panel's interest-group cards (interest-group scope; plan Task 8): the",
        "# group's stance on the bill under debate (0 none, 1 committed, 2 persuadable, 3 opposed,",
        "# 4 red line, 5 marginal and not counted), its score and five of its reasons (trust, Task 12), from",
        "# its owner's support snapshot through its type. 0 while no bill is open.",
    ]
    lines += ["te_tax_disp_ig_stance = {", "\tvalue = 0"]
    for n, ig in enumerate(IGS):
        com, sup = f"te_tax_com_{ig}", f"te_tax_sup_{ig}"
        guard = (f"has_variable = te_tax_bl_on var:te_tax_bl_on = 1 has_variable = te_tax_bl_rev "
                 f"has_variable = {com} has_variable = {com}_rev has_variable = {sup}")
        lines += [
            f"\t{'if' if n == 0 else 'else_if'} = {{",
            f"\t\tlimit = {{ is_interest_group_type = ig_{ig} owner = {{ {guard} }} }}",
            f"\t\tif = {{ limit = {{ ig_counts_as_marginal = yes }} value = {STANCE_MARGINAL} }}",
            f"\t\telse_if = {{ limit = {{ owner = {{ var:{com} = 1 var:{com}_rev = var:te_tax_bl_rev }} }} "
            f"value = {STANCE_COMMITTED} }}",
            f"\t\telse_if = {{ limit = {{ owner = {{ var:{com} = -1 }} }} value = {STANCE_RED_LINE} }}",
            f"\t\telse_if = {{ limit = {{ owner = {{ var:{sup} < 0 }} }} value = {STANCE_OPPOSED} }}",
            f"\t\telse = {{ value = {STANCE_PERSUADABLE} }}",
            "\t}",
        ]
    lines.append("}")
    for value, variable in (("score", "te_tax_sup_{ig}"), ("mat", "te_tax_sr_{ig}_mat"),
                            ("ideo", "te_tax_sr_{ig}_ideo"), ("fisc", "te_tax_sr_{ig}_fisc"),
                            ("gov", "te_tax_sr_{ig}_gov"), ("trust", "te_tax_sr_{ig}_trust"),
                            ("prom", "te_tax_sr_{ig}_prom")):
        lines += [f"te_tax_disp_ig_{value} = {{", "\tvalue = 0"]
        for n, ig in enumerate(IGS):
            var = variable.format(ig=ig)
            lines += [
                f"\t{'if' if n == 0 else 'else_if'} = {{",
                f"\t\tlimit = {{ is_interest_group_type = ig_{ig} owner = {{ has_variable = te_tax_bl_on "
                f"var:te_tax_bl_on = 1 has_variable = {var} }} }}",
                f"\t\towner = {{ add = var:{var} }}",
                "\t}",
            ]
        lines.append("}")
    lines += [
        "",
        "# The group's offer for the bill's current revision (plan Task 13): its kind (0 none; 1 cut a",
        "# tax, 2 agricultural relief, 3 untax a staple, 10 + an obligation kind for a promise), arg,",
        "# whether accepting commits it, and whether a promise only maintains what holds.",
    ]
    for value in ("", "_arg", "_commit", "_maint"):
        lines += [f"te_tax_disp_ig_offer{value} = {{", "\tvalue = 0"]
        for n, ig in enumerate(IGS):
            off = f"te_tax_off_{ig}"
            guard = (f"has_variable = te_tax_bl_on var:te_tax_bl_on = 1 has_variable = te_tax_bl_rev "
                     f"has_variable = {off}_kind has_variable = {off}_rev has_variable = {off}{value or '_kind'} "
                     f"var:{off}_rev = var:te_tax_bl_rev var:{off}_kind > 0")
            lines += [
                f"\t{'if' if n == 0 else 'else_if'} = {{",
                f"\t\tlimit = {{ is_interest_group_type = ig_{ig} owner = {{ {guard} }} }}",
                f"\t\towner = {{ add = var:{off}{value or '_kind'} }}",
                "\t}",
            ]
        lines.append("}")
    return lines


def _is_open(token):
    return f"has_variable = {token} var:{token} = 1"


def _split_month(name, month, guard):
    """`name`_y and `name`_mo: the year and 1-based month of the script value `month`."""
    limit = f"{guard} {month} >= 0"
    return ([f"{name}_y = {{", "\tvalue = -1", "\tif = {", f"\t\tlimit = {{ {limit} }}",
             f"\t\tvalue = {month}", "\t\tdivide = 12", "\t\tfloor = yes", "\t}", "}"]
            + [f"{name}_mo = {{", "\tvalue = -1", "\tif = {", f"\t\tlimit = {{ {limit} }}",
               f"\t\tvalue = {month}", "\t\tdivide = 12", "\t\tfloor = yes", "\t\tmultiply = -12",
               f"\t\tadd = {month}", "\t\tadd = 1", "\t}", "}"])


def _last_change_views():
    """The month the enacted code last changed: the newest history entry of a kind
    that moves te_tax_code_version, or an instrument's operative-since month if the
    ring has rolled past it (`min =` keeps the larger)."""
    kinds = " ".join(f"var:te_tax_h{{n}}_kind = {kind}" for kind in CODE_CHANGE_KINDS)
    lines = ["", "# The newest change to the enacted code (-1 if none is known), and its year and month.",
             "te_tax_view_last_change = {", "\tvalue = -1"]
    for n in range(1, HISTORY_SIZE + 1):
        lines.append(f"\tif = {{ limit = {{ has_variable = te_tax_h{n}_kind has_variable = te_tax_h{n}_month "
                     f"OR = {{ {kinds.format(n=n)} }} }} min = var:te_tax_h{n}_month }}")
    for instrument in INSTRUMENTS:
        since = f"te_tax_en_{instrument.key}_since"
        lines.append(f"\tif = {{ limit = {{ has_variable = {since} }} min = var:{since} }}")
    lines.append("}")
    return lines + _split_month("te_tax_view_last_change", "te_tax_view_last_change",
                                "has_variable = te_tax_schema")


def _history_views():
    """Position i (1 = newest) of the ring is entry n = te_tax_h_head - i + 1, wrapping
    from 1 back to HISTORY_SIZE."""
    lines = ["", "# The history ring newest first: position <i> reads entry te_tax_h<n>_* with",
             "# n = te_tax_h_head - i + 1, wrapping past 1 to 8. kind 0 and month -1 while the",
             "# position is empty. _inst is the instrument a sunset changed (INSTRUMENTS order)."]
    for i in range(1, HISTORY_SIZE + 1):
        for field, default in (("kind", 0), ("inst", 0), ("month", -1)):
            lines += [f"te_tax_view_hist_{i}_{field} = {{", f"\tvalue = {default}"]
            for head in range(1, HISTORY_SIZE + 1):
                variable = f"te_tax_h{(head - i) % HISTORY_SIZE + 1}_{field}"
                opener = "if" if head == 1 else "else_if"
                lines.append(f"\t{opener} = {{ limit = {{ has_variable = te_tax_h_head var:te_tax_h_head = {head} "
                             f"has_variable = {variable} }} value = var:{variable} }}")
            lines.append("}")
        month = f"te_tax_view_hist_{i}_month"
        lines += _split_month(month, month, "has_variable = te_tax_h_head")
    return lines


@output(CUSTOM_LOC_PATH)
def custom_localization():
    lines = [
        HEADER,
        "# The history rows' text (gui/journal_entry_widgets/te_tax_overview_widget.gui,",
        "# te_tax_history_section): one customizable localization per row, newest first, read as",
        "# GetPlayer.GetCustom('te_tax_hist_event_<i>'). Each picks the line for the entry's kind",
        "# (te_tax_view_hist_<i>_kind) and, for a sunset, its instrument (_inst). The triggers read",
        "# only the guarded views, never a variable.",
    ]
    for i in range(1, HISTORY_SIZE + 1):
        kind, inst = f"te_tax_view_hist_{i}_kind", f"te_tax_view_hist_{i}_inst"
        entries = []
        for value in range(1, max(HISTORY_KIND_KEYS) + 1):
            if value == KIND_SUNSET:
                entries += [(f"{kind} = {KIND_SUNSET} {inst} = {idx}", f"te_tax_hist_kind_sunset_{instrument.key}")
                            for idx, instrument in enumerate(INSTRUMENTS, start=1)]
            else:
                entries.append((f"{kind} = {value}", HISTORY_KIND_KEYS[value]))
        lines += ["", f"te_tax_hist_event_{i} = {{", "\ttype = country", "\trandom_valid = no"]
        for trigger, key in entries:
            lines += ["\ttext = {", f"\t\ttrigger = {{ {trigger} }}", f"\t\tlocalization_key = {key}", "\t}"]
        lines += ["\ttext = {", f"\t\tlocalization_key = {HISTORY_KIND_FALLBACK}", "\t}", "}"]
    return _txt("\n".join(lines + _obligation_custom_loc() + _offer_custom_loc()) + "\n")


def _offer_custom_loc():
    """The interest-group cards' offer line (plan Task 13): what the group asks for, read as
    InterestGroup.GetCustom('te_tax_ig_offer') under the cards' datamodel. Interest-group scope,
    as vanilla's negotiation lines (05_negotiation_custom_loc.txt); the triggers read only the
    group's guarded te_tax_disp_ig_offer* values, 0 without an offer this revision."""
    keys = [instrument.key for instrument in INSTRUMENTS]
    entries = [(f"te_tax_disp_ig_offer = {OFFER_CUT} te_tax_disp_ig_offer_arg = {idx}", f"te_tax_offer_cut_{key}")
               for idx, key in enumerate(keys, start=1)]
    entries.append((f"te_tax_disp_ig_offer = {OFFER_AGREL}", "te_tax_offer_agrel"))
    entries += [(f"te_tax_disp_ig_offer = {OFFER_STAPLE} te_tax_disp_ig_offer_arg = {n}", f"te_tax_offer_untax_{good}")
                for n, good in enumerate(staple_order(), start=1)]
    seen = set()
    for name, kind, arg, _target, _groups in PROMISE_OFFERS:
        if (kind, arg) not in seen:
            seen.add((kind, arg))
            promise = f"te_tax_disp_ig_offer = {OFFER_PROMISE + kind} te_tax_disp_ig_offer_arg = {arg}"
            # A promise that only maintains what holds says so (spec 7.2), first.
            entries.append((f"{promise} te_tax_disp_ig_offer_maint = 1", f"te_tax_offer_prom_{name}_maint"))
            entries.append((promise, f"te_tax_offer_prom_{name}"))
    lines = [
        "",
        "# The interest-group cards' offers (plan Task 13; te_tax_ig_card, te_tax_politics_widget.gui):",
        "# what the group asks for in return for its support, read as",
        "# InterestGroup.GetCustom('te_tax_ig_offer'). Interest-group scope.",
    ]
    return lines + [line.replace("\ttype = country", "\ttype = interest_group")
                    for line in _custom_loc("te_tax_ig_offer", entries, "te_tax_offer_none")]


def _custom_loc(name, entries, fallback):
    """A country-scope customizable localization: the first (trigger, key) that holds, else `fallback`."""
    lines = ["", f"{name} = {{", "\ttype = country", "\trandom_valid = no"]
    for trigger, key in entries:
        lines += ["\ttext = {", f"\t\ttrigger = {{ {trigger} }}", f"\t\tlocalization_key = {key}", "\t}"]
    return lines + ["\ttext = {", f"\t\tlocalization_key = {fallback}", "\t}", "}"]


def _obligation_custom_loc():
    """The promise rows' text (te_tax_obligations_section, te_tax_politics_widget.gui), per
    obligation slot <n>: whose promise it is (te_tax_obl_ig_<n>, the group's own name), whether
    it reaches new provision or maintains existing provision (te_tax_obl_mode_<n>), what it
    promises (te_tax_obl_what_<n>; te_tax_obl_inst_<n>, kind 1's institution) and where it
    stands (te_tax_obl_state_<n>). The keys that print a slot's numbers are per slot
    (te_tax_l_english.yml); the rest are shared. The triggers read only the guarded views."""
    lines = [
        "",
        "# The promise rows (plan Task 12; te_tax_obligations_section): per obligation slot <n>,",
        "# the beneficiary group's name, the promise and its state, read as",
        "# GetPlayer.GetCustom('te_tax_obl_<part>_<n>'). The triggers read only the guarded",
        "# te_tax_view_o<n>_* views, which are 0 while the slot is free.",
    ]
    for n in OBLIGATION_SLOTS:
        view = f"te_tax_view_o{n}"
        lines += _custom_loc(f"te_tax_obl_ig_{n}", [(f"{view}_ig = {idx}", f"ig_{ig}")
                                                    for idx, ig in enumerate(IGS, start=1)], "te_tax_obl_ig_none")
        lines += _custom_loc(f"te_tax_obl_mode_{n}", [(f"{view}_maint_only = 1", "te_tax_obl_mode_maintain")],
                             "te_tax_obl_mode_reach")
        what = [(f"{view}_kind = 1", f"te_tax_obl_what_inst_{n}"), (f"{view}_kind = 2", "te_tax_obl_what_bureaucracy")]
        what += [(f"{view}_kind = 3 {view}_arg = {arg}", f"te_tax_obl_what_wages_{level}")
                 for arg, level in OBL_WAGE_LEVELS]
        what.append((f"{view}_kind = 4", "te_tax_obl_what_fiscal"))
        lines += _custom_loc(f"te_tax_obl_what_{n}", what, "te_tax_obl_what_none")
        lines += _custom_loc(f"te_tax_obl_inst_{n}", [(f"{view}_arg = {arg}", institution)
                                                      for arg, institution in OBL_INSTITUTIONS], "te_tax_obl_what_none")
        states = [(f"{view}_state = {OBL_PENDING}", "te_tax_obl_st_pending"),
                  (f"{view}_state = {OBL_BOUND}", "te_tax_obl_st_bound"),
                  (f"{view}_state = {OBL_DELIVERING} {view}_kind = 4", f"te_tax_obl_st_surplus_{n}"),
                  (f"{view}_state = {OBL_DELIVERING}", f"te_tax_obl_st_due_{n}"),
                  (f"{view}_state = {OBL_MAINTAINING} {view}_fails > 0", f"te_tax_obl_st_failing_{n}"),
                  (f"{view}_state = {OBL_MAINTAINING}", f"te_tax_obl_st_maint_{n}")]
        lines += _custom_loc(f"te_tax_obl_state_{n}", states, "te_tax_obl_st_none")
    return lines


def _guarded_view(name, variable, default, ops=(), condition=""):
    """A te_tax_view_* value: `default`, or var:`variable` (then `ops`) when it exists."""
    limit = f"has_variable = {variable}" + (f" {condition}" if condition else "")
    if not ops:
        return [f"{name} = {{", f"\tvalue = {default}",
                f"\tif = {{ limit = {{ {limit} }} value = var:{variable} }}", "}"]
    return ([f"{name} = {{", f"\tvalue = {default}", "\tif = {", f"\t\tlimit = {{ {limit} }}",
             f"\t\tvalue = var:{variable}"]
            + [f"\t\t{op}" for op in ops] + ["\t}", "}"])


def _month_views(name, variable, condition=""):
    """The month, its year and its 1-based calendar month (all -1 when unset, or
    when `condition`, a further guard, fails)."""
    started = " ".join(part for part in (condition, f"var:{variable} >= 0") if part)
    return (_guarded_view(name, variable, -1, condition=condition)
            + _guarded_view(f"{name}_y", variable, -1, ("divide = 12", "floor = yes"), started)
            + _guarded_view(f"{name}_mo", variable, -1,
                            ("divide = 12", "floor = yes", "multiply = -12",
                             f"add = var:{variable}", "add = 1"), started))


def _instrument_views(instrument):
    key = instrument.key
    index = f"te_tax_en_{key}"
    successor = f"te_tax_en_{key}_succ"
    step = f"multiply = te_tax_step_{key}"
    pct = f"multiply = te_tax_pct_step_{key}"
    lines = [f"# {instrument.label}: enacted index, rate (index x step), operative since, sunset, successor."]
    lines += _guarded_view(f"te_tax_view_en_{key}", index, 0)
    lines += _guarded_view(f"te_tax_view_en_{key}_rate", index, 0, (step,))
    if instrument.percent:
        lines += _guarded_view(f"te_tax_view_en_{key}_pct", index, 0, (pct,))
    lines += _month_views(f"te_tax_view_en_{key}_since", f"te_tax_en_{key}_since")
    lines += _month_views(f"te_tax_view_en_{key}_exp", f"te_tax_en_{key}_exp")
    lines += _guarded_view(f"te_tax_view_en_{key}_succ", successor, -1)
    started = f"var:{successor} >= 0"
    lines += _guarded_view(f"te_tax_view_en_{key}_succ_rate", successor, 0, (step,), started)
    if instrument.percent:
        lines += _guarded_view(f"te_tax_view_en_{key}_succ_pct", successor, 0, (pct,), started)
    return lines


def _guarded_write(variable, value, indent="\t"):
    """The init idiom: write `variable` only if it is absent, so nothing is overwritten."""
    return (f"{indent}if = {{ limit = {{ NOT = {{ has_variable = {variable} }} }} "
            f"set_variable = {{ name = {variable} value = {value} }} }}")


# ---------------------------------------------------------------------------
# Scheduler: package slots, sunsets, history (docs/systems/tax_code_schema.md)
# ---------------------------------------------------------------------------

def schedule_tokens():
    """[(token, sentinel)] the scheduler initialises: clock, slot headers, history ring."""
    tokens = [("te_tax_now", -1)]
    for slot in SLOTS:
        tokens += [(f"te_tax_p{slot}{suffix}", sentinel) for suffix, sentinel in PACKAGE_HEADER]
    tokens.append(("te_tax_h_head", 0))
    for n in range(1, HISTORY_SIZE + 1):
        tokens += [(f"te_tax_h{n}_{field}", sentinel) for field, sentinel in HISTORY_FIELDS]
    return tokens


def obligation_tokens():
    """[(token, sentinel)] of the policy obligations (plan Task 12): each slot's header and each
    interest group's trust. Initialised, copied at an outbreak and never removed."""
    tokens = [(f"te_tax_o{n}{suffix}", sentinel) for n in OBLIGATION_SLOTS for suffix, sentinel in OBLIGATION_HEADER]
    tokens += [(f"te_tax_trust_{ig}", 0) for ig in IGS]
    return tokens + [(f"te_tax_trust_{ig}_month", -1) for ig in IGS]


def _log(event, detail=""):
    """A scheduler debug line: `TE_TAX <event> [detail] month=... date=... country=...`."""
    text = f"TE_TAX {event} {detail}; {LOG_STAMP}" if detail else f"TE_TAX {event} {LOG_STAMP}"
    return f'debug_log = "{text}"'


def _history(kind, slot="none", inst=0):
    return f"te_tax_gen_history_write = {{ KIND = {kind} SLOT = {slot} INST = {inst} }}"


def _other(slot):
    return SLOTS[1 - SLOTS.index(slot)]


def _sunset(instrument, inst):
    key = instrument.key
    en = f"te_tax_en_{key}"
    dropped = _log("sunset_dropped", f"{key}: no successor recorded")
    executed = _log("sunset", key)
    deferred = _log("sunset_deferred", f"{key}: operative only since this month")
    return [
        "",
        f"# {instrument.label}: executes the enacted value's sunset once its month has come",
        "# (rule 2). It runs only when the value has been operative since an earlier month,",
        "# so a package's own sunset can never share its commencement call; otherwise it",
        "# waits for next month. A late sunset catches up. One without a successor is",
        "# dropped, not deferred, so it cannot hold te_tax_next_month in the past.",
        f"te_tax_gen_sunset_{key} = {{",
        "\tif = {",
        "\t\tlimit = {",
        f"\t\t\tvar:{en}_exp >= 0",
        f"\t\t\tvar:{en}_exp <= var:te_tax_now",
        "\t\t}",
        "\t\tif = {",
        f"\t\t\tlimit = {{ var:{en}_succ < 0 }}",
        f"\t\t\tset_variable = {{ name = {en}_exp value = -1 }}",
        f"\t\t\t{dropped}",
        "\t\t}",
        "\t\telse_if = {",
        f"\t\t\tlimit = {{ var:{en}_since < var:te_tax_now }}",
        f"\t\t\tset_variable = {{ name = {en} value = var:{en}_succ }}",
        f"\t\t\tset_variable = {{ name = {en}_since value = var:te_tax_now }}",
        f"\t\t\tset_variable = {{ name = {en}_exp value = -1 }}",
        f"\t\t\tset_variable = {{ name = {en}_succ value = -1 }}",
        "\t\t\tchange_variable = { name = te_tax_code_version add = 1 }",
        f"\t\t\t{_history(KIND_SUNSET, inst=inst)}",
        f"\t\t\t{executed}",
        "\t\t}",
        "\t\telse = {",
        f"\t\t\t{deferred}",
        "\t\t}",
        "\t}",
        "}",
    ]


def _commence(slot):
    p = f"te_tax_p{slot}"
    commenced = _log("commenced", f"slot={slot}")
    conflict = _log("held_conflict", f"slot={slot}: a touched provision changed outside legislation")
    return [
        "",
        f"# Slot {slot}: commences in its due month and in no other (rule 3). The processor runs",
        "# on the 1st, so the package takes effect from the 1st. If a provision it touches was",
        "# changed outside legislation since approval (te_tax_xver_*), the whole package holds",
        "# and collections stay as they are. A due month already past holds it as missed. The",
        "# obligations bound to it start with it (te_tax_obl_start), and wait while it is held.",
        f"te_tax_gen_commence_{slot} = {{",
        "\tif = {",
        "\t\tlimit = {",
        f"\t\t\tvar:{p}_on = 1",
        f"\t\t\tvar:{p}_state = {STATE_AWAITING}",
        f"\t\t\tvar:{p}_due = var:te_tax_now",
        "\t\t}",
        "\t\tif = {",
        f"\t\t\tlimit = {{ te_tax_gen_package_current_{slot} = yes }}",
        f"\t\t\tte_tax_gen_apply_{slot} = yes",
        "\t\t\tchange_variable = { name = te_tax_code_version add = 1 }",
        "\t\t\t# The obligations bound to this package start their clocks this month (plan Task 12).",
        f"\t\t\tte_tax_obl_start = {{ SLOT = {slot} }}",
        f"\t\t\tset_variable = {{ name = {p}_on value = 0 }}",
        f"\t\t\tset_variable = {{ name = {p}_state value = {STATE_EMPTY} }}",
        f"\t\t\t{_history(KIND_COMMENCED, slot)}",
        f"\t\t\t{commenced}",
        "\t\t}",
        "\t\telse = {",
        f"\t\t\tset_variable = {{ name = {p}_state value = {STATE_HELD_CONFLICT} }}",
        f"\t\t\t{_history(KIND_HELD_CONFLICT, slot)}",
        f"\t\t\t{conflict}",
        "\t\t}",
        "\t}",
        "\telse = {",
        f"\t\tte_tax_gen_hold_missed_{slot} = yes",
        "\t}",
        "}",
    ]


def _hold_missed(slot):
    p = f"te_tax_p{slot}"
    missed = _log("held_missed", f"slot={slot}: due month passed without commencement")
    return [
        "",
        f"# Slot {slot}: an awaiting package whose due month has passed holds as missed; it never",
        "# commences late (spec: missed dates need explicit rescheduling). The watchdog calls",
        "# this too, because it fires only once the month has passed.",
        f"te_tax_gen_hold_missed_{slot} = {{",
        "\tif = {",
        "\t\tlimit = {",
        f"\t\t\tvar:{p}_on = 1",
        f"\t\t\tvar:{p}_state = {STATE_AWAITING}",
        f"\t\t\tvar:{p}_due < var:te_tax_now",
        "\t\t}",
        f"\t\tset_variable = {{ name = {p}_state value = {STATE_HELD_MISSED} }}",
        f"\t\t{_history(KIND_HELD_MISSED, slot)}",
        f"\t\t{missed}",
        "\t}",
        "}",
    ]


def _apply(slot):
    p = f"te_tax_p{slot}"
    lines = [
        "",
        f"# Slot {slot}: copies every field the package touches into the enacted code. Only",
        "# te_tax_gen_commence_<slot> calls it, inside the processor, which has set te_tax_now,",
        "# run this month's sunsets first and syncs collection once after every slot.",
        "# Supersession of the enacted provision happens here, at commencement, never at",
        "# approval: the package replaces the value and its sunset. With no sunset of its own",
        "# the change is permanent and clears any pending sunset (_exp and _succ = -1). With",
        "# one, the provision reverts to the underlying permanent rate: a sunset still pending",
        "# now (this month's have run, so it is in the future) keeps its successor; otherwise",
        "# the rate in force is the successor. Both are captured before anything is",
        "# overwritten. The stored te_tax_p<slot>_<key>_succ is only the review's preview and",
        "# is never read here.",
        f"te_tax_gen_apply_{slot} = {{",
    ]
    for instrument in INSTRUMENTS:
        key = instrument.key
        en = f"te_tax_en_{key}"
        lines += [
            "\tif = {",
            f"\t\tlimit = {{ var:{p}_{key} >= 0 }}",
            "\t\tif = {",
            f"\t\t\tlimit = {{ var:{p}_{key}_exp >= 0 }}",
            "\t\t\t# A pending sunset with a successor keeps it; otherwise the rate in force.",
            "\t\t\tif = {",
            "\t\t\t\tlimit = {",
            "\t\t\t\t\tOR = {",
            f"\t\t\t\t\t\tvar:{en}_exp < 0",
            f"\t\t\t\t\t\tvar:{en}_succ < 0",
            "\t\t\t\t\t}",
            "\t\t\t\t}",
            f"\t\t\t\tset_variable = {{ name = {en}_succ value = var:{en} }}",
            "\t\t\t}",
            "\t\t}",
            "\t\telse = {",
            f"\t\t\tset_variable = {{ name = {en}_succ value = -1 }}",
            "\t\t}",
            f"\t\tset_variable = {{ name = {en} value = var:{p}_{key} }}",
            f"\t\tset_variable = {{ name = {en}_since value = var:te_tax_now }}",
            f"\t\tset_variable = {{ name = {en}_exp value = var:{p}_{key}_exp }}",
            "\t}",
        ]
    for good in consumption_catalog():
        lines.append(f"\tif = {{ limit = {{ var:{p}_g_{good} >= 0 }} "
                     f"set_variable = {{ name = te_tax_en_g_{good} value = var:{p}_g_{good} }} }}")
    for field in ("agrel", "regrel"):
        lines.append(f"\tif = {{ limit = {{ var:{p}_{field} >= 0 }} "
                     f"set_variable = {{ name = te_tax_en_{field} value = var:{p}_{field} }} }}")
    plist = slot_relief_list(slot)
    lines += [
        "\t# A package that restates regional relief names its whole state set, its own list",
        f"\t# {plist}: it replaces the enacted list te_tax_en_relief_states (the canonical set,",
        "\t# at most three) with the states in it that this code keeps (te_tax_relief_listed_state_kept:",
        "\t# its own, or its civil-war counterpart's while a war lasts). The state marks",
        "\t# (te_tax_relief_state) follow from the list in the writer's relief sync",
        "\t# (te_tax_rebuild_relief_marks), which the processor runs after this month's",
        "\t# commencements. The slot's list is consumed either way.",
        "\tif = {",
        f"\t\tlimit = {{ var:{p}_regrel_states_set = 1 }}",
        "\t\tsave_scope_as = te_tax_country",
        _clear_list("te_tax_en_relief_states", "\t\t"),
        "\t\tif = {",
        f"\t\t\tlimit = {{ has_variable_list = {plist} }}",
        "\t\t\tevery_in_list = {",
        f"\t\t\t\tvariable = {plist}",
        "\t\t\t\tlimit = { te_tax_relief_listed_state_kept = yes }",
        "\t\t\t\tscope:te_tax_country = { add_to_variable_list = { name = te_tax_en_relief_states target = PREV } }",
        "\t\t\t}",
        "\t\t}",
        "\t}",
        _clear_list(plist),
        "}",
    ]
    return lines


def _store_successor(slot, key):
    """Lines setting te_tax_p<slot>_<key>_succ, the review's preview of what the sunset restores.

    A forecast at store time by te_tax_gen_apply_<slot>'s rule, the underlying
    permanent rate: the enacted provision's pending successor if it has a sunset (one
    falling before the due month will have run; a later one is still pending), else
    its value; overridden the same way by the other slot's package when that awaiting
    package touches the provision earlier and so commences first. Commencement never
    reads it.
    """
    p, o = f"te_tax_p{slot}", f"te_tax_p{_other(slot)}"
    en = f"te_tax_en_{key}"
    return [
        f"\t\tset_variable = {{ name = {p}_{key}_succ value = var:{en} }}",
        "\t\tif = {",
        "\t\t\tlimit = {",
        f"\t\t\t\tvar:{en}_exp >= 0",
        f"\t\t\t\tvar:{en}_succ >= 0",
        "\t\t\t}",
        f"\t\t\tset_variable = {{ name = {p}_{key}_succ value = var:{en}_succ }}",
        "\t\t}",
        "\t\t# The other slot's payload exists only while it is on, so read it nested.",
        "\t\tif = {",
        "\t\t\tlimit = {",
        f"\t\t\t\tvar:{o}_on = 1",
        f"\t\t\t\tvar:{o}_state = {STATE_AWAITING}",
        f"\t\t\t\tvar:{o}_due < var:te_tax_bl_due",
        "\t\t\t}",
        "\t\t\tif = {",
        f"\t\t\t\tlimit = {{ var:{o}_{key} >= 0 }}",
        f"\t\t\t\tset_variable = {{ name = {p}_{key}_succ value = var:{o}_{key} }}",
        "\t\t\t\tif = {",
        "\t\t\t\t\tlimit = {",
        f"\t\t\t\t\t\tvar:{o}_{key}_exp >= 0",
        f"\t\t\t\t\t\tvar:{o}_{key}_succ >= 0",
        "\t\t\t\t\t}",
        f"\t\t\t\t\tset_variable = {{ name = {p}_{key}_succ value = var:{o}_{key}_succ }}",
        "\t\t\t\t}",
        "\t\t\t}",
        "\t\t}",
    ]


def _store(slot):
    p, o = f"te_tax_p{slot}", f"te_tax_p{_other(slot)}"
    stored = _log("stored", f"slot={slot}")
    lines = [
        "",
        f"# Slot {slot}: writes an approved package from the bill record (te_tax_bl_*). Called",
        "# only through te_tax_store_package, after te_tax_can_store_package and with",
        "# scope:te_tax_country saved. Every payload field is written, so nothing stale from an",
        "# earlier package survives. A sunset is due + offset, written only for an offset of at",
        "# least one month. _succ is a preview for the review only (commencement decides the",
        "# successor then, by te_tax_gen_apply_<slot>'s rule): the underlying permanent rate,",
        "# from the other slot's awaiting package if it touches the provision earlier, else",
        "# from the enacted provision. seq = one above both slots. The slot is switched on last.",
        "# _due0 keeps the approved month and _pver_<group> the planned versions after this",
        "# approval, for te_tax_cmd_package_reschedule: a missed package may move only a few",
        "# months, and only while no later approval has touched what it changes.",
        f"te_tax_gen_store_{slot} = {{",
        f"\tset_variable = {{ name = {p}_due value = var:te_tax_bl_due }}",
        f"\tset_variable = {{ name = {p}_due0 value = var:te_tax_bl_due }}",
        "\tif = {",
        f"\t\tlimit = {{ var:{o}_seq > var:{p}_seq }}",
        f"\t\tset_variable = {{ name = {p}_seq value = var:{o}_seq }}",
        "\t}",
        f"\tchange_variable = {{ name = {p}_seq add = 1 }}",
    ]
    for instrument in INSTRUMENTS:
        key = instrument.key
        lines += [
            f"\tset_variable = {{ name = {p}_{key} value = var:te_tax_bl_{key} }}",
            f"\tset_variable = {{ name = {p}_xver_{key} value = var:te_tax_bl_xver_{key} }}",
            "\tif = {",
            "\t\tlimit = {",
            f"\t\t\tvar:te_tax_bl_{key} >= 0",
            f"\t\t\tvar:te_tax_bl_{key}_sun >= 1",
            "\t\t}",
            f"\t\tset_variable = {{ name = {p}_{key}_exp value = var:te_tax_bl_due }}",
            f"\t\tchange_variable = {{ name = {p}_{key}_exp add = var:te_tax_bl_{key}_sun }}",
        ]
        lines += _store_successor(slot, key)
        lines += [
            "\t}",
            "\telse = {",
            f"\t\tset_variable = {{ name = {p}_{key}_exp value = -1 }}",
            f"\t\tset_variable = {{ name = {p}_{key}_succ value = -1 }}",
            "\t}",
        ]
    lines += [f"\tset_variable = {{ name = {p}_g_{good} value = var:te_tax_bl_g_{good} }}"
              for good in consumption_catalog()]
    lines.append(f"\tset_variable = {{ name = {p}_xver_goods value = var:te_tax_bl_xver_goods }}")
    groups = [instrument.key for instrument in INSTRUMENTS] + ["goods", "relief"]
    lines += [f"\tset_variable = {{ name = {p}_pver_{group} value = var:te_tax_pver_{group} }}" for group in groups]
    lines += [f"\tset_variable = {{ name = {p}_{field} value = var:te_tax_bl_{field} }}"
              for field in PACKAGE_RELIEF_FIELDS]
    plist = slot_relief_list(slot)
    lines += [
        "\t# Regional relief: a bill that touches it (te_tax_bl_regrel >= 0) names its whole",
        f"\t# state set in te_tax_bl_relief_states, possibly none, copied into the slot's {plist};",
        "\t# commencement replaces the enacted list with it.",
        _clear_list(plist),
        "\tif = {",
        "\t\tlimit = { var:te_tax_bl_regrel >= 0 }",
        f"\t\tset_variable = {{ name = {p}_regrel_states_set value = 1 }}",
        "\t\tif = {",
        "\t\t\tlimit = { has_variable_list = te_tax_bl_relief_states }",
        "\t\t\tevery_in_list = {",
        "\t\t\t\tvariable = te_tax_bl_relief_states",
        f"\t\t\t\tscope:te_tax_country = {{ add_to_variable_list = {{ name = {plist} target = PREV }} }}",
        "\t\t\t}",
        "\t\t}",
        "\t}",
        "\telse = {",
        f"\t\tset_variable = {{ name = {p}_regrel_states_set value = 0 }}",
        "\t}",
        f"\t{stored}",
        f"\tset_variable = {{ name = {p}_state value = {STATE_AWAITING} }}",
        f"\tset_variable = {{ name = {p}_on value = 1 }}",
        "}",
    ]
    return lines


def _next_month():
    lines = [
        "",
        "# te_tax_next_month: the earliest month with a transition due, -1 if none. Enacted",
        "# sunsets and awaiting packages count; a held package waits for rescheduling and does",
        "# not. A deferred sunset keeps it at the current month until it runs.",
        "te_tax_gen_next_month = {",
        "\tset_variable = { name = te_tax_next_month value = -1 }",
    ]
    candidates = [(f"var:te_tax_en_{instrument.key}_exp >= 0", f"var:te_tax_en_{instrument.key}_exp")
                  for instrument in INSTRUMENTS]
    candidates += [(f"var:te_tax_p{slot}_on = 1\n\t\t\tvar:te_tax_p{slot}_state = {STATE_AWAITING}",
                    f"var:te_tax_p{slot}_due") for slot in SLOTS]
    for condition, month in candidates:
        lines += [
            "\tif = {",
            "\t\tlimit = {",
            f"\t\t\t{condition}",
            "\t\t\tOR = {",
            "\t\t\t\tvar:te_tax_next_month < 0",
            f"\t\t\t\t{month} < var:te_tax_next_month",
            "\t\t\t}",
            "\t\t}",
            f"\t\tset_variable = {{ name = te_tax_next_month value = {month} }}",
            "\t}",
        ]
    lines.append("}")
    return lines


def _history_write():
    lines = [
        "",
        f"# The history ring: {HISTORY_SIZE} entries te_tax_h<n>_*, te_tax_h_head pointing at the newest",
        "# (0 = empty). Advances the head, then overwrites that entry. KIND: the schema doc's",
        "# history kinds; SLOT: none, a or b (stored as te_tax_slot_id_<SLOT>); INST: 1..5 for",
        "# the instrument a sunset executed (INSTRUMENTS order), else 0. Public entry point:",
        "# te_tax_history_push = { KIND SLOT }.",
        "te_tax_gen_history_write = {",
        "\tif = {",
        "\t\tlimit = {",
        "\t\t\tvar:te_tax_h_head >= 1",
        f"\t\t\tvar:te_tax_h_head < {HISTORY_SIZE}",
        "\t\t}",
        "\t\tchange_variable = { name = te_tax_h_head add = 1 }",
        "\t}",
        "\telse = {",
        "\t\tset_variable = { name = te_tax_h_head value = 1 }",
        "\t}",
    ]
    values = (("month", "te_history_month_index"), ("kind", "$KIND$"), ("slot", "te_tax_slot_id_$SLOT$"),
              ("inst", "$INST$"), ("version", "var:te_tax_code_version"))
    for n in range(1, HISTORY_SIZE + 1):
        lines += [f"\t{'if' if n == 1 else 'else_if'} = {{", f"\t\tlimit = {{ var:te_tax_h_head = {n} }}"]
        lines += [f"\t\tset_variable = {{ name = te_tax_h{n}_{field} value = {value} }}" for field, value in values]
        lines.append("\t}")
    lines.append("}")
    return lines


def _scheduler_effects():
    lines = []
    for inst, instrument in enumerate(INSTRUMENTS, start=1):
        lines += _sunset(instrument, inst)
    for slot in SLOTS:
        lines += _commence(slot) + _hold_missed(slot) + _apply(slot) + _store(slot)
    return lines + _next_month() + _history_write()


# ---------------------------------------------------------------------------
# Copies for new countries (docs/systems/tax_code_schema.md, "Civil wars and new
# countries"). te_tax_copy_token (te_tax_state_effects.txt) copies one token from
# scope:te_tax_source onto THIS when the source holds it.
# ---------------------------------------------------------------------------

def slot_payload(slot):
    """Every payload variable te_tax_gen_store_<slot> writes, header (PACKAGE_HEADER) excluded."""
    p = f"te_tax_p{slot}"
    names = [f"{p}_due0"]
    for instrument in INSTRUMENTS:
        key = instrument.key
        names += [f"{p}_{key}", f"{p}_xver_{key}", f"{p}_{key}_exp", f"{p}_{key}_succ"]
    names += [f"{p}_g_{good}" for good in consumption_catalog()]
    names.append(f"{p}_xver_goods")
    names += [f"{p}_pver_{group}" for group in [i.key for i in INSTRUMENTS] + ["goods", "relief"]]
    names += [f"{p}_{field}" for field in PACKAGE_RELIEF_FIELDS]
    names.append(f"{p}_regrel_states_set")
    return names


def enacted_tokens():
    """The enacted provisions a released country takes from its parent: every
    instrument with its operative month, sunset and successor, the taxed goods
    and the two relief depths."""
    names = [f"te_tax_en_{instrument.key}{suffix}" for instrument in INSTRUMENTS
             for suffix, _ in INSTRUMENT_TOKENS]
    names += [f"te_tax_en_g_{good}" for good in consumption_catalog()]
    return names + ["te_tax_en_agrel", "te_tax_en_regrel"]


def _copy(name):
    return f"\tte_tax_copy_token = {{ NAME = {name} }}"


def _copy_effects():
    code = [f"te_tax_en_{instrument.key}{suffix}" for instrument in INSTRUMENTS
            for suffix, _ in INSTRUMENT_TOKENS]
    code += [f"{prefix}{instrument.key}" for instrument in INSTRUMENTS for prefix, _ in VERSION_TOKENS]
    code += [f"te_tax_en_g_{good}" for good in consumption_catalog()]
    code += [name for name, _ in schedule_tokens()]
    code += [name for name, _ in obligation_tokens()]
    lines = [
        "",
        "# Outbreak copy (te_tax_copy_code, te_tax_civil_war_effects.txt): every token the",
        "# generated initialisers write (te_tax_gen_init_instruments, _goods, _schedule,",
        "# _obligations), from scope:te_tax_source onto the uprising: the enacted provisions with",
        "# their months, the version tokens, the taxed goods, the clock, the package-slot headers,",
        "# the history ring, the obligation-slot headers and the groups' trust.",
        "te_tax_gen_copy_code = {",
    ]
    lines += [_copy(name) for name in code]
    lines += [
        "}",
        "",
        "# Outbreak copy of the policy obligations (plan Task 12): the payload of every slot whose",
        "# obligation binds the original (te_tax_obl_binding: bound to a passed bill, delivering or",
        "# maintaining), with its clocks, so it binds the rebels on the same terms (spec 10: binding",
        "# obligations follow the copied code). A pending one belongs to the bill, which stays with",
        "# the government that wrote it: te_tax_copy_code releases it on the rebels afterwards.",
        "te_tax_gen_copy_obligations = {",
    ]
    for n in OBLIGATION_SLOTS:
        lines += ["\tif = {", f"\t\tlimit = {{ scope:te_tax_source = {{ te_tax_obl_binding = {{ N = {n} }} }} }}"]
        lines += [f"\t\tte_tax_copy_token = {{ NAME = te_tax_o{n}_{field} }}" for field in OBLIGATION_PAYLOAD]
        lines.append("\t}")
    lines += [
        "}",
        "",
        "# A released country starts with no obligation and no record of kept or broken promises",
        "# (te_tax_init_released_country; a revived tag may carry them from an earlier life). The",
        "# parent's obligations stay with the parent.",
        "te_tax_gen_clear_obligations = {",
    ]
    lines += [f"\tset_variable = {{ name = {name} value = {sentinel} }}" for name, sentinel in obligation_tokens()]
    lines.append("}")
    for slot in SLOTS:
        lines += [
            "",
            f"# Outbreak copy of slot {slot}'s package: every payload field te_tax_gen_store_{slot}",
            "# writes, with its original dates, so the package commences on the rebels in its own",
            "# month. Called only while the source's slot is occupied (te_tax_p<slot>_on = 1).",
            f"te_tax_gen_copy_slot_{slot} = {{",
        ]
        lines += [_copy(name) for name in slot_payload(slot)]
        plist = slot_relief_list(slot)
        lines += [
            f"\t# The package's regional-relief states ({plist}), whole.",
            "\tsave_scope_as = te_tax_country",
            _clear_list(plist),
            "\tif = {",
            f"\t\tlimit = {{ scope:te_tax_source = {{ has_variable_list = {plist} }} }}",
            "\t\tscope:te_tax_source = {",
            "\t\t\tevery_in_list = {",
            f"\t\t\t\tvariable = {plist}",
            f"\t\t\t\tscope:te_tax_country = {{ add_to_variable_list = {{ name = {plist} target = PREV }} }}",
            "\t\t\t}",
            "\t\t}",
            "\t}",
        ]
        lines.append("}")
    lines += [
        "",
        "# Release copy (te_tax_init_released_country): the parent's enacted provisions only;",
        "# its packages, bill, draft and commitments stay with it.",
        "te_tax_gen_copy_enacted = {",
    ]
    lines += [_copy(name) for name in enacted_tokens()]
    lines.append("}")
    return lines


# ---------------------------------------------------------------------------
# Migration from the vanilla taxation law (docs/systems/tax_code_schema.md, "Migration")
# ---------------------------------------------------------------------------

def _migrate_writes(indices, indent="\t\t"):
    return [f"{indent}set_variable = {{ name = te_tax_en_{instrument.key} value = {indices[instrument.key]} }}"
            for instrument in INSTRUMENTS]


def _migration_effects():
    zeros = {instrument.key: 0 for instrument in INSTRUMENTS}
    carrier = _log("migration_discrepancy",
                   f"holds {CARRIER_LAW} without migration tokens; every rate migrated as 0")
    unknown = _log("migration_discrepancy", "no mapping for the active taxation law; every rate migrated as 0")
    lines = [
        "",
        "# Migration, rates: the enacted indices that reproduce the active vanilla taxation law at",
        "# the country's native tax level, one branch per (law, level) pair (MIGRATION in the",
        "# generator). Every branch writes all five indices. A country already on the carrier",
        "# without tokens (a rebel or a released country that inherited it), or on any other law",
        "# (the probe carrier, another mod's law), migrates as all zeros and is flagged.",
        "# Called only by te_tax_migrate_country.",
        "te_tax_gen_migrate_rates = {",
    ]
    for n, (law, level, indices) in enumerate(migration_indices()):
        lines += [f"\t{'if' if n == 0 else 'else_if'} = {{",
                  f"\t\tlimit = {{ has_law = law_type:{law} tax_level = {level} }}"]
        lines += _migrate_writes(indices)
        lines.append("\t}")
    lines += ["\telse_if = {", f"\t\tlimit = {{ has_law = law_type:{CARRIER_LAW} }}"]
    lines += _migrate_writes(zeros)
    lines += ["\t\tset_variable = { name = te_tax_migration_discrepancy value = 1 }", f"\t\t{carrier}", "\t}"]
    lines.append("\telse = {")
    lines += _migrate_writes(zeros)
    lines += ["\t\tset_variable = { name = te_tax_migration_discrepancy value = 1 }", f"\t\t{unknown}", "\t}"]
    lines += [
        "}",
        "",
        "# Migration, goods: a catalog good is on the enacted list exactly when the country taxes",
        "# it natively. A good outside the catalog is not carried; the first sync removes it.",
        "te_tax_gen_migrate_goods = {",
    ]
    for good in consumption_catalog():
        lines += [
            f"\tif = {{ limit = {{ has_consumption_tax = g:{good} }} "
            f"set_variable = {{ name = te_tax_en_g_{good} value = 1 }} }}",
            f"\telse = {{ set_variable = {{ name = te_tax_en_g_{good} value = 0 }} }}",
        ]
    lines += [
        "\t# A migration is a change made outside legislation.",
        "\tchange_variable = { name = te_tax_xver_goods add = 1 }",
        "}",
        "",
        "# Migration, provisions: a collected instrument is operative from this month; none has",
        "# a sunset or a successor. A migration is a change made outside legislation, so each",
        "# instrument's external-change token moves.",
        "te_tax_gen_migrate_provisions = {",
    ]
    for instrument in INSTRUMENTS:
        en = f"te_tax_en_{instrument.key}"
        lines += [
            "\tif = {",
            f"\t\tlimit = {{ var:{en} > 0 }}",
            f"\t\tset_variable = {{ name = {en}_since value = te_history_month_index }}",
            "\t}",
            "\telse = {",
            f"\t\tset_variable = {{ name = {en}_since value = -1 }}",
            "\t}",
            f"\tset_variable = {{ name = {en}_exp value = -1 }}",
            f"\tset_variable = {{ name = {en}_succ value = -1 }}",
            f"\tchange_variable = {{ name = te_tax_xver_{instrument.key} add = 1 }}",
        ]
    lines.append("}")
    return lines + _baseline_effects()


def _baseline_effects():
    """The interest groups' views of the enacted code (plan Task 13)."""
    lines = [
        "",
        "# Interest-group views of the enacted code (te_tax_refresh_ig_views, from the monthly",
        "# processor only): each group's band (te_tax_ig_band_<ig>: its stance toward the vanilla",
        "# taxation law the code is equivalent to, -2..2) keeps at most one te_tax_ig_view_<ig>_<band>",
        "# on the country, and none at band 0. A band's modifier is added only where it is missing and",
        "# the others are removed only where present, so an unchanged band changes nothing. Modifier",
        "# changes are not visible later in the same effect; nothing here reads one back.",
        "te_tax_gen_ig_views = {",
    ]
    for ig in IGS:
        lines.append(f"\tset_local_variable = {{ name = te_tax_band value = te_tax_ig_band_{ig} }}")
        for band, value in VIEW_BANDS:
            name = f"te_tax_ig_view_{ig}_{band}"
            lines += [
                f"\tif = {{ limit = {{ local_var:te_tax_band = {value} NOT = {{ has_modifier = {name} }} }} "
                f"add_modifier = {{ name = {name} }} }}",
                f"\tif = {{ limit = {{ NOT = {{ local_var:te_tax_band = {value} }} has_modifier = {name} }} "
                f"remove_modifier = {name} }}",
            ]
    lines.append("}")
    return lines

def _scheduler_triggers():
    lines = []
    for slot in SLOTS:
        p = f"te_tax_p{slot}"
        lines += [
            "",
            f"# Slot {slot}, country scope: the package touches at least one catalog good.",
            f"te_tax_gen_package_touches_goods_{slot} = {{",
            "\tOR = {",
        ]
        lines += [f"\t\tvar:{p}_g_{good} >= 0" for good in consumption_catalog()]
        lines += [
            "\t}",
            "}",
            "",
            f"# Slot {slot}, country scope: every provision group the package touches still has the",
            "# external-change token it had at approval. Only a non-legislative change bumps",
            "# te_tax_xver_*, so expected sunsets and other packages never make it stale.",
            f"te_tax_gen_package_current_{slot} = {{",
        ]
        for instrument in INSTRUMENTS:
            key = instrument.key
            lines += [
                "\tOR = {",
                f"\t\tvar:{p}_{key} < 0",
                f"\t\tvar:{p}_xver_{key} = var:te_tax_xver_{key}",
                "\t}",
            ]
        lines += [
            "\tOR = {",
            f"\t\tNOT = {{ te_tax_gen_package_touches_goods_{slot} = yes }}",
            f"\t\tvar:{p}_xver_goods = var:te_tax_xver_goods",
            "\t}",
            "\tOR = {",
            "\t\tAND = {",
            f"\t\t\tvar:{p}_agrel < 0",
            f"\t\t\tvar:{p}_regrel < 0",
            "\t\t}",
            f"\t\tvar:{p}_xver_relief = var:te_tax_xver_relief",
            "\t}",
            "}",
        ]
    lines += [
        "",
        "# Country scope: every sunset in the bill falls at least one month after commencement.",
        "# te_tax_store_package writes _exp = te_tax_bl_due + te_tax_bl_<key>_sun, so _exp >= _due + 1",
        "# exactly when the offset is at least 1; 0 means no sunset; an untouched provision",
        "# (-1) has none.",
        "te_tax_gen_bill_sunsets_valid = {",
    ]
    for instrument in INSTRUMENTS:
        key = instrument.key
        lines += [
            "\tOR = {",
            f"\t\tvar:te_tax_bl_{key} < 0",
            f"\t\tvar:te_tax_bl_{key}_sun = 0",
            f"\t\tvar:te_tax_bl_{key}_sun >= 1",
            "\t}",
        ]
    lines.append("}")
    return lines


# ---------------------------------------------------------------------------
# Draft, bill and passage (docs/systems/tax_code_schema.md, "Draft, bill and passage")
# ---------------------------------------------------------------------------

def exposure(ig):
    """{key: Decimal} exposure of interest group `ig` to each channel."""
    return dict(zip((instrument.key for instrument in INSTRUMENTS), _values(EXPOSURE[ig])))


def staple_order():
    """The catalog's staples (goods category `staple`), most-taxed first: the untax offer
    stops taxing the first one the bill adds. Most-taxed by vanilla's consumption_tax_cost
    (the engine default DEFAULT_GOODS_TAX_COST where a good sets none; vanilla prices the
    Authority a consumption tax costs by the revenue it yields), then by base price, which
    scales the tax per unit, then by name."""
    definitions = goods_definitions()

    def rank(good):
        entry = definitions[good]
        return (-int(entry.get("consumption_tax_cost") or 100), -int(entry.get("cost") or 0), good)
    return sorted((good for good in consumption_catalog() if definitions[good].get("category") == "staple"), key=rank)


def clause_offers(ig):
    """The clause offers interest group `ig` may make, preferred first."""
    return CLAUSE_OFFERS.get(ig, (OFFER_CUT,))


def grievance_keys(ig):
    """The instruments interest group `ig` pays any of (EXPOSURE above 0), INSTRUMENTS order."""
    return [key for key, weight in exposure(ig).items() if weight]


def promise_offers(ig):
    """[(name, kind, arg, target)] the promises interest group `ig` may ask for."""
    return [(name, kind, arg, target) for name, kind, arg, target, groups in PROMISE_OFFERS if ig in groups]


def _record_payload(record):
    """[(variable, draft sentinel)] for every per-instrument, per-good and relief field of a record."""
    fields = []
    for instrument in INSTRUMENTS:
        fields += [(f"te_tax_{record}_{instrument.key}{suffix}", sentinel)
                   for suffix, sentinel in RECORD_KEY_FIELDS]
    fields += [(f"te_tax_{record}_g_{good}", -1) for good in consumption_catalog()]
    fields += [(f"te_tax_{record}_goods_pver", -1), (f"te_tax_{record}_agrel", -1),
               (f"te_tax_{record}_regrel", -1), (f"te_tax_{record}_relief_pver", -1)]
    return fields


def _copy_state_list(source, target, indent="\t"):
    """Lines replacing the country list `target` with the states in `source`, both
    lists of THIS country (scope:te_tax_country is saved first). Inside the list
    iteration PREV is the country, inside `scope:te_tax_country = { }` the state."""
    t = indent
    return [
        _clear_list(target, t),
        f"{t}if = {{",
        f"{t}\tlimit = {{ has_variable_list = {source} }}",
        f"{t}\tsave_scope_as = te_tax_country",
        f"{t}\tevery_in_list = {{",
        f"{t}\t\tvariable = {source}",
        f"{t}\t\tscope:te_tax_country = {{ add_to_variable_list = {{ name = {target} target = PREV }} }}",
        f"{t}\t}}",
        f"{t}}}",
    ]


def _bill_versions():
    """[(bill variable, canonical token)]: the external versions a bill records."""
    pairs = [(f"te_tax_bl_xver_{instrument.key}", f"te_tax_xver_{instrument.key}") for instrument in INSTRUMENTS]
    return pairs + [("te_tax_bl_xver_goods", "te_tax_xver_goods"), ("te_tax_bl_xver_relief", "te_tax_xver_relief")]


def _baseline_slot(record, slot, field, sunsets, indent, by_due=True):
    """Lines overriding the baseline with slot `slot`'s package if it awaits before the record's due month.

    With `sunsets`, a package's own sunset preview replaces its value: only one
    falling by the due month (`by_due`, the baseline), or any (the successor
    preview, te_tax_succ_<record>_<key>)."""
    p, due = f"te_tax_p{slot}_{field}", f"te_tax_{record}_due"
    t = indent
    if not sunsets:
        return [f"{t}if = {{ limit = {{ te_tax_slot_awaits_before = {{ SLOT = {slot} DUE = {due} }} "
                f"has_variable = {p} var:{p} >= 0 }} value = var:{p} }}"]
    lines = [
        f"{t}if = {{",
        f"{t}\tlimit = {{",
        f"{t}\t\tte_tax_slot_awaits_before = {{ SLOT = {slot} DUE = {due} }}",
        f"{t}\t\thas_variable = {p}",
        f"{t}\t\tvar:{p} >= 0",
        f"{t}\t}}",
        f"{t}\tvalue = var:{p}",
    ]
    if sunsets:
        lines += [
            f"{t}\tif = {{",
            f"{t}\t\tlimit = {{",
            f"{t}\t\t\thas_variable = {p}_exp",
            f"{t}\t\t\thas_variable = {p}_succ",
            f"{t}\t\t\tvar:{p}_exp >= 0",
        ] + ([f"{t}\t\t\tvar:{p}_exp <= var:{due}"] if by_due else []) + [
            f"{t}\t\t\tvar:{p}_succ >= 0",
            f"{t}\t\t}}",
            f"{t}\t\tvalue = var:{p}_succ",
            f"{t}\t}}",
        ]
    return lines + [f"{t}}}"]


def _baseline_value(name, record, field, enacted, sunsets):
    """A value: the index (or good flag) in force under existing law in the record's due month."""
    due = f"te_tax_{record}_due"
    lines = [f"{name} = {{", "\tvalue = 0", f"\tif = {{ limit = {{ has_variable = {enacted} }} value = var:{enacted} }}"]
    if sunsets:
        lines += [
            "\t# An enacted sunset falling on or before the due month has run by then.",
            "\tif = {",
            "\t\tlimit = {",
            f"\t\t\thas_variable = {due}",
            f"\t\t\thas_variable = {enacted}_exp",
            f"\t\t\thas_variable = {enacted}_succ",
            f"\t\t\tvar:{enacted}_exp >= 0",
            f"\t\t\tvar:{enacted}_exp <= var:{due}",
            f"\t\t\tvar:{enacted}_succ >= 0",
            "\t\t}",
            f"\t\tvalue = var:{enacted}_succ",
            "\t}",
        ]
    lines += ["\t# Awaiting packages due earlier, in the order they commence.", "\tif = {",
              "\t\tlimit = { te_tax_slot_b_first = yes }"]
    lines += _baseline_slot(record, "b", field, sunsets, "\t\t") + _baseline_slot(record, "a", field, sunsets, "\t\t")
    lines += ["\t}", "\telse = {"]
    lines += _baseline_slot(record, "a", field, sunsets, "\t\t") + _baseline_slot(record, "b", field, sunsets, "\t\t")
    return lines + ["\t}", "}"]


def _successor_value(name, record, key):
    """The index a sunset in the record would revert to: the scheduler's rule 3
    (te_tax_gen_apply_<slot>) applied at the record's due month, as
    te_tax_gen_store_<slot> previews it for a passed bill. The enacted provision's
    pending successor if it has any sunset (one falling before the due month will
    have run, a later one is still pending; either way it names the underlying
    rate), else its value; then each awaiting package due earlier, in commencement
    order, the same way (a package due on or after the record's month is
    superseded at approval). A display preview: commencement decides."""
    enacted = f"te_tax_en_{key}"
    lines = [
        f"{name} = {{", "\tvalue = 0", f"\tif = {{ limit = {{ has_variable = {enacted} }} value = var:{enacted} }}",
        "\t# Any pending enacted sunset: its successor is the underlying rate.",
        "\tif = {",
        "\t\tlimit = {",
        f"\t\t\thas_variable = {enacted}_exp",
        f"\t\t\thas_variable = {enacted}_succ",
        f"\t\t\tvar:{enacted}_exp >= 0",
        f"\t\t\tvar:{enacted}_succ >= 0",
        "\t\t}",
        f"\t\tvalue = var:{enacted}_succ",
        "\t}",
        "\t# Awaiting packages due earlier, in the order they commence.", "\tif = {",
        "\t\tlimit = { te_tax_slot_b_first = yes }",
    ]
    for first, second in (("b", "a"), ("a", "b")):
        lines += _baseline_slot(record, first, key, True, "\t\t", by_due=False)
        lines += _baseline_slot(record, second, key, True, "\t\t", by_due=False)
        lines += ["\t}", "\telse = {"] if first == "b" else []
    return lines + ["\t}", "}"]


def _dstep(record, key):
    """te_tax_<record>_dstep_<key>: the record's change in index steps from the law
    in force in its due month (0 if it leaves the provision alone)."""
    return [f"te_tax_{record}_dstep_{key} = {{", "\tvalue = 0", "\tif = {",
            f"\t\tlimit = {{ has_variable = te_tax_{record}_{key} var:te_tax_{record}_{key} >= 0 }}",
            f"\t\tvalue = var:te_tax_{record}_{key}", f"\t\tsubtract = te_tax_base_{record}_{key}", "\t}", "}"]


def _provisions(record, keys):
    """te_tax_<record>_provisions: how many instruments the record changes."""
    lines = [f"te_tax_{record}_provisions = {{", "\tvalue = 0"]
    lines += [f"\tif = {{ limit = {{ has_variable = te_tax_{record}_{key} var:te_tax_{record}_{key} >= 0 }} add = 1 }}"
              for key in keys]
    return lines + ["}"]


def _clamped(name, terms, weight, points=()):
    """A reason: the `terms` (in tax levels) times `weight`, plus `points` (already in
    support points), clamped to -REASON_CAP..REASON_CAP."""
    return ([f"{name} = {{", "\tvalue = 0"] + terms + [f"\tmultiply = {weight}"] + list(points)
            + [f"\tmin = -{REASON_CAP}", f"\tmax = {REASON_CAP}", "}"])


def _ideology_value(ig):
    lines = [f"te_tax_ideo_p_{ig} = {{", "\tvalue = 0"]
    for law, progressiveness in TAX_LAW_PROGRESSIVENESS:
        if not progressiveness:
            continue
        lines.append(f"\t# {law}, progressiveness {progressiveness}")
        for n, (comparison, stance) in enumerate(STANCE_BRANCHES):
            weight = fmt(Decimal(stance * progressiveness) / 100)
            lines.append(f"\t{'if' if n == 0 else 'else_if'} = {{ limit = {{ ig:ig_{ig} ?= {{ law_stance = "
                         f"{{ law = law_type:{law} {comparison} }} }} }} add = {weight} }}")
    return lines + ["}"]


def _clout_sum(name, committed):
    lines = [f"{name} = {{", "\tvalue = 0"]
    for ig in IGS:
        lines += ["\tif = {", "\t\tlimit = {", f"\t\t\texists = ig:ig_{ig}",
                  f"\t\t\tig:ig_{ig} = {{ ig_counts_as_marginal = no }}"]
        if committed == "open":
            lines += [f"\t\t\thas_variable = te_tax_com_{ig}", f"\t\t\tvar:te_tax_com_{ig} = 0",
                      f"\t\t\thas_variable = te_tax_sup_{ig}", f"\t\t\tvar:te_tax_sup_{ig} >= 0"]
        elif committed:
            lines += [f"\t\t\thas_variable = te_tax_com_{ig}", f"\t\t\tvar:te_tax_com_{ig} = 1",
                      f"\t\t\thas_variable = te_tax_com_{ig}_rev", "\t\t\thas_variable = te_tax_bl_rev",
                      f"\t\t\tvar:te_tax_com_{ig}_rev = var:te_tax_bl_rev"]
        lines += ["\t\t}", f"\t\tadd = ig:ig_{ig}.ig_clout", "\t}"]
    return lines + ["}"]


def _revenue_value(name, total, goods, agrel, regrel):
    """The revenue direction: the rates' change, plus the goods taxed, less the relief granted."""
    return [f"{name} = {{", f"\tvalue = {total}", f"\tadd = {goods}",
            f"\tsubtract = {{ value = {agrel} multiply = te_tax_agrel_revenue_levels }}",
            f"\tsubtract = {{ value = {regrel} multiply = te_tax_regrel_revenue_levels }}", "}"]


def _prog_value(name, prefix):
    """The change in progressivity: income channels minus the rest, every staple taxed regressive."""
    keys = [instrument.key for instrument in INSTRUMENTS]
    lines = [f"{name} = {{", f"\tvalue = {prefix}{keys[0]}"]
    lines += [f"\t{'add' if key in PROGRESSIVE_KEYS else 'subtract'} = {prefix}{key}" for key in keys[1:]]
    lines += [f"\tsubtract = {prefix}g_{good}" for good in staple_order()]
    return lines + ["}"]


def _material_terms(ig, prefix):
    """The material reason's tax terms (in tax levels) for interest group `ig`, from the
    delta-level values named `<prefix><key>` and `<prefix>goods`."""
    terms = [f"\tadd = {{ value = {prefix}{key} multiply = {fmt(weight)} }}"
             for key, weight in exposure(ig).items() if weight]
    cons = exposure(ig)["cons"]
    if cons:
        terms.append(f"\tadd = {{ value = {prefix}goods multiply = {fmt(cons)} }}")
    return terms


def _material_points(ig, agrel, regrel):
    """The material reason's relief points for interest group `ig`."""
    points = [f"\tadd = {{ value = {agrel} multiply = {AGREL_POINTS[ig]} }}"] if ig in AGREL_POINTS else []
    points.append(f"\tadd = {{ value = {regrel} multiply = {REGREL_POINTS_ALL} }}")
    if ig in REGREL_POINTS_CONCERN:
        points.append(f"\tadd = {{ value = {regrel} multiply = {REGREL_POINTS_CONCERN[ig]} }}")
    return points


def _offer_values():
    """The offers' and promises' support values (plan Task 13)."""
    lines = [
        "",
        "# Offers (plan Task 13). te_tax_bl_eff_wage and te_tax_bl_eff_agrel: the bill's wage index",
        "# and agricultural relief band, or existing law's in its month when the bill leaves them",
        "# alone; the relief offer adds a band to the second while the first leaves a tax to relieve.",
    ]
    for key in ("wage", "agrel"):
        lines += [f"te_tax_bl_eff_{key} = {{", f"\tvalue = te_tax_base_bl_{key}",
                  f"\tif = {{ limit = {{ has_variable = te_tax_bl_{key} var:te_tax_bl_{key} >= 0 }} "
                  f"value = var:te_tax_bl_{key} }}", "}"]
    lines += ["", "# How many catalog goods the bill touches (te_tax_offer_untax_leaves_a_bill).",
              "te_tax_bl_goods_touched = {", "\tvalue = 0"]
    lines += [f"\tif = {{ limit = {{ has_variable = te_tax_bl_g_{good} var:te_tax_bl_g_{good} >= 0 }} add = 1 }}"
              for good in consumption_catalog()]
    lines += [
        "}",
        "",
        "# te_tax_bl_grief_<ig>_<key>: what the bill's raise of an instrument costs the group, in tax",
        "# levels weighted by its exposure (te_tax_dl_<key> x EXPOSURE), 0 unless the bill raises it",
        "# above existing law (te_tax_bl_dstep_<key> above 0); te_tax_bl_grief_<ig>_goods the same for",
        "# the goods the bill taxes on the consumption channel, 0 unless they add to the burden. The",
        "# largest is the group's top grievance, the one a clause offer softens (controller ruling:",
        "# a clause only softens what the bill raises).",
    ]
    for ig in IGS:
        weights = exposure(ig)
        for key in grievance_keys(ig):
            lines += [f"te_tax_bl_grief_{ig}_{key} = {{", "\tvalue = 0",
                      f"\tif = {{ limit = {{ te_tax_bl_dstep_{key} > 0 }} value = te_tax_dl_{key} "
                      f"multiply = {fmt(weights[key])} }}", "}"]
        if weights["cons"]:
            lines += [f"te_tax_bl_grief_{ig}_goods = {{", "\tvalue = 0",
                      f"\tif = {{ limit = {{ te_tax_dl_goods > 0 }} value = te_tax_dl_goods multiply = {fmt(weights['cons'])} }}",
                      "}"]
    lines += [
        "",
        "# te_tax_prom_<ig>: the group's promises reason, recomputed at every refresh from the",
        "# promises accepted under this bill (te_tax_bl_prom_<ig>_*), never accumulated. Its own",
        "# accepted promise counts te_tax_offer_points, or te_tax_offer_points_maint if it only",
        "# maintains what already holds, and only while its pending obligation is live",
        "# (te_tax_offer_prom_live: a promise that could not be recorded, because the same one is",
        "# already pending or binding, adds nothing). Another group's institution promise counts",
        f"# {PROMISE_SIDE_POINTS} per step of the group's stance on the law with none of that institution",
        "# (law_no_schools, law_no_health_system): a group that wants the institution welcomes it.",
    ]
    for ig in IGS:
        lines += [f"te_tax_prom_{ig} = {{", "\tvalue = 0",
                  f"\tif = {{ limit = {{ te_tax_offer_prom_live_maint = {{ IG = {ig} }} }} add = te_tax_offer_points_maint }}",
                  f"\telse_if = {{ limit = {{ te_tax_offer_prom_live = {{ IG = {ig} }} }} add = te_tax_offer_points }}"]
        for name, kind, arg, _target, groups in PROMISE_OFFERS:
            law = PROMISE_SIDE_LAWS.get((kind, arg))
            others = [other for other in groups if other != ig]
            if law is None or not others:
                continue
            lines += [f"\t# Another group's {name} promise.", "\tif = {", "\t\tlimit = {", "\t\t\tOR = {"]
            lines += [f"\t\t\t\tAND = {{ has_variable = te_tax_bl_prom_{other}_kind var:te_tax_bl_prom_{other}_kind = {kind} "
                      f"var:te_tax_bl_prom_{other}_arg = {arg} te_tax_offer_prom_live = {{ IG = {other} }} }}"
                      for other in others]
            lines += ["\t\t\t}", "\t\t}"]
            for n, (comparison, stance) in enumerate(STANCE_BRANCHES):
                lines.append(f"\t\t{'if' if n == 0 else 'else_if'} = {{ limit = {{ ig:ig_{ig} ?= {{ law_stance = "
                             f"{{ law = law_type:{law} {comparison} }} }} }} add = {stance * PROMISE_SIDE_POINTS} }}")
            lines.append("\t}")
        lines += [f"\tmin = -{REASON_CAP}", f"\tmax = {REASON_CAP}", "}"]
    return lines


def _view_values():
    """The interest groups' views of the enacted code (plan Task 13, controller ruling)."""
    lines = [
        "",
        "# Interest-group views of the enacted code (plan Task 13; te_tax_gen_ig_views, from the",
        "# monthly processor). te_tax_ig_band_<ig>: the group's own vanilla stance, -2 strongly",
        "# opposes .. 2 strongly endorses (law_stance, strongest bucket first), toward the vanilla",
        "# taxation law the enacted code is equivalent to (te_tax_code_equivalent_<law>,",
        "# te_tax_triggers.txt, which need the rule and the carrier law); 0 without the carrier, or",
        "# for a neutral stance. Reads no variable and iterates nothing.",
    ]
    for ig in IGS:
        lines += [f"te_tax_ig_band_{ig} = {{", "\tvalue = 0"]
        for n, (short, law) in enumerate(EQUIVALENT_LAWS):
            lines += [f"\t{'if' if n == 0 else 'else_if'} = {{",
                      f"\t\tlimit = {{ te_tax_code_equivalent_{short} = yes }}"]
            for m, (comparison, stance) in enumerate(STANCE_BRANCHES):
                lines.append(f"\t\t{'if' if m == 0 else 'else_if'} = {{ limit = {{ ig:ig_{ig} ?= {{ law_stance = "
                             f"{{ law = law_type:{law} {comparison} }} }} }} value = {stance} }}")
            lines.append("\t}")
        lines.append("}")
    return lines

@output(SUPPORT_VALUES_PATH)
def support_values():
    keys = [instrument.key for instrument in INSTRUMENTS]
    lines = [
        HEADER,
        "# The legislated tax code's draft, bill and support-model values. Schema and rules:",
        "# docs/systems/tax_code_schema.md, \"Draft, bill and passage\". Country scope. Read by",
        "# te_tax_bill_effects.txt, te_tax_triggers.txt, te_tax_support_values.txt and the support",
        "# refresh (te_tax_gen_refresh_support); every variable read is guarded with has_variable,",
        "# and none writes or iterates anything, so a GUI may read them too.",
        "",
        "# One vanilla tax level per channel, for the support model's delta-levels.",
    ]
    lines += [f"te_tax_level_step_{key} = {fmt(LEVEL_STEPS[key])}" for key in keys]
    lines += [
        "",
        "# te_tax_base_<record>_<key>: the index in force under existing law in the draft's (dr) or",
        "# the bill's (bl) due month: the enacted value, its successor if its sunset falls by then,",
        "# then each awaiting package due earlier (one due on or after it is superseded at",
        "# approval), with that package's own sunset preview. The draft's untouched provisions",
        "# start from it; the bill's support model measures change against it.",
    ]
    for record in RECORDS:
        for key in keys:
            lines += _baseline_value(f"te_tax_base_{record}_{key}", record, key, f"te_tax_en_{key}", True)
    lines += ["", "# te_tax_base_<record>_<relief>: the relief band in force under existing law in the record's",
              "# due month (relief has no sunset): the enacted band, then each awaiting package due earlier."]
    for record in RECORDS:
        for key in RELIEF_KEYS:
            lines += _baseline_value(f"te_tax_base_{record}_{key}", record, key, f"te_tax_en_{key}", False)
    lines += ["", "# te_tax_dr_eff_<key>: the draft's target, or the baseline when the draft leaves it alone."]
    for key in keys + list(RELIEF_KEYS):
        lines += [f"te_tax_dr_eff_{key} = {{", f"\tvalue = te_tax_base_dr_{key}",
                  f"\tif = {{ limit = {{ has_variable = te_tax_dr_{key} var:te_tax_dr_{key} >= 0 }} "
                  f"value = var:te_tax_dr_{key} }}", "}"]
    lines += [
        "",
        "# te_tax_dr_zero_limit_<key>: Traditionalism's test that the draft levies no such tax,",
        "# written with the draft's index on the left (te_tax_draft_ready):",
        "#   var:te_tax_dr_<key> = 0  OR  var:te_tax_dr_<key> <= te_tax_dr_zero_limit_<key>",
        "# The limit is -1 when existing law in the draft's month has no such tax and -2 when it",
        "# has, so an untouched provision (-1) passes exactly when that law levies none, and a",
        "# touched one only at 0.",
    ]
    for key in TRADITIONALISM_KEYS:
        lines += [f"te_tax_dr_zero_limit_{key} = {{", f"\tvalue = te_tax_base_dr_{key}", "\tmax = 1",
                  "\tmultiply = -1", "\tadd = -1", "}"]
    lines += ["", "# te_tax_base_<record>_g_<good>: 1 if the good is taxed under existing law in the",
              "# draft's (dr) or the bill's (bl) due month."]
    for record in RECORDS:
        for good in consumption_catalog():
            lines += _baseline_value(f"te_tax_base_{record}_g_{good}", record, f"g_{good}",
                                     f"te_tax_en_g_{good}", False)
    lines += ["", "# The bill's change per instrument: in index steps (0 if untouched), then in vanilla tax levels."]
    for key in keys:
        lines += _dstep("bl", key)
        lines += [f"te_tax_dl_{key} = {{", f"\tvalue = te_tax_bl_dstep_{key}", f"\tmultiply = te_tax_step_{key}",
                  f"\tdivide = te_tax_level_step_{key}", "}"]
    lines += ["", "# The bill's change in agricultural relief, in bands from existing law (0 if untouched); the",
              "# support model scales it by the wage tax it relieves (te_tax_bl_agrel_scaled,",
              "# te_tax_support_values.txt). Regional relief is scored by coverage instead",
              "# (te_tax_bl_regrel_coverage)."]
    lines += _dstep("bl", "agrel")
    lines += [
        "",
        f"# The bill's goods, in tax levels on the consumption channel: {fmt(GOODS_LEVEL_STEPS)} per good it puts on",
        "# the taxed list (negative for one it takes off), times the good's category weight",
        "# (GOODS_CATEGORY_WEIGHT in the generator, from the goods file's category). One value per",
        "# good, so a later provision can zero a single good's term; te_tax_dl_goods is their sum.",
    ]
    for good in consumption_catalog():
        flag = f"te_tax_bl_g_{good}"
        lines += [f"te_tax_dl_g_{good} = {{", "\tvalue = 0", "\tif = {",
                  f"\t\tlimit = {{ has_variable = {flag} var:{flag} >= 0 }}",
                  f"\t\tvalue = var:{flag}", f"\t\tsubtract = te_tax_base_bl_g_{good}",
                  f"\t\tmultiply = {fmt(goods_weight(good) * GOODS_LEVEL_STEPS)}", "\t}", "}"]
    lines += ["te_tax_dl_goods = {", "\tvalue = 0"]
    lines += [f"\tadd = te_tax_dl_g_{good}" for good in consumption_catalog()] + ["}"]
    lines += [
        "",
        "# The rates' change in tax levels (te_tax_dl_total). The revenue direction the fiscal reason",
        "# reads (te_tax_dl_revenue, plan Task 13) adds the goods the bill taxes (te_tax_dl_goods) and",
        "# subtracts the relief it grants, in tax levels forgone: te_tax_agrel_revenue_levels per",
        "# scaled band of agricultural relief and te_tax_regrel_revenue_levels per unit of regional",
        "# coverage (te_tax_support_values.txt). Read only by the support refresh: the coverage",
        "# iterates a state list. Progressivity: income channels minus the rest, and every staple",
        "# the bill taxes counts as regressive.",
    ]
    lines += ["te_tax_dl_total = {", f"\tvalue = te_tax_dl_{keys[0]}"]
    lines += [f"\tadd = te_tax_dl_{key}" for key in keys[1:]] + ["}"]
    lines += _revenue_value("te_tax_dl_revenue", "te_tax_dl_total", "te_tax_dl_goods", "te_tax_bl_agrel_scaled",
                            "te_tax_bl_regrel_coverage")
    lines += _prog_value("te_tax_dl_prog", "te_tax_dl_")
    lines += ["", "# How many provisions the bill changes."] + _provisions("bl", keys)
    lines += [
        "",
        f"# Support reasons per interest group, each clamped to -{REASON_CAP}..{REASON_CAP}. Material:",
        f"# {MATERIAL_WEIGHT} x the exposure-weighted change in tax levels, the bill's goods counted on the",
        "# consumption channel (te_tax_dl_goods); then relief in points: agricultural, per band the",
        "# bill moves it scaled by the wage tax relieved (te_tax_bl_agrel_scaled),",
        f"# {', '.join(f'{ig} +{n}' for ig, n in AGREL_POINTS.items())}; regional, per band x share of the population",
        f"# named over te_tax_regrel_ref_share (te_tax_bl_regrel_coverage), +{REGREL_POINTS_ALL} for every group,",
        f"# {', '.join(f'{ig} {n}' for ig, n in REGREL_POINTS_CONCERN.items())} on top. Ideology: {IDEOLOGY_WEIGHT} x the",
        "# group's fiscal ideology (its stances on the vanilla taxation laws x their progressiveness",
        f"# / 100) x the change in progressivity. Government: +{GOVERNMENT_BONUS} in government. Trust",
        f"# (plan Task 12): {TRUST_WEIGHT} x the group's te_tax_trust_<ig>, +1 per promise kept and -1 per",
        "# promise broken.",
    ]
    for ig in IGS:
        lines += _clamped(f"te_tax_mat_{ig}", _material_terms(ig, "te_tax_dl_"), MATERIAL_WEIGHT,
                          _material_points(ig, "te_tax_bl_agrel_scaled", "te_tax_bl_regrel_coverage"))
        lines += _ideology_value(ig)
        lines += [f"te_tax_ideo_{ig} = {{", f"\tvalue = te_tax_ideo_p_{ig}", "\tmultiply = te_tax_dl_prog",
                  f"\tmultiply = {IDEOLOGY_WEIGHT}", f"\tmin = -{REASON_CAP}", f"\tmax = {REASON_CAP}", "}"]
        lines += [f"te_tax_gov_{ig} = {{", "\tvalue = 0",
                  f"\tif = {{ limit = {{ ig:ig_{ig} ?= {{ is_in_government = yes }} }} value = {GOVERNMENT_BONUS} }}",
                  "}"]
        lines += [f"te_tax_trust_reason_{ig} = {{", "\tvalue = 0",
                  f"\tif = {{ limit = {{ has_variable = te_tax_trust_{ig} }} value = var:te_tax_trust_{ig} "
                  f"multiply = {TRUST_WEIGHT} }}",
                  f"\tmin = -{REASON_CAP}", f"\tmax = {REASON_CAP}", "}"]
    lines += [
        "",
        "# Clout of the non-marginal interest groups, and of those among them committed to the",
        "# bill's current revision (te_tax_committed_share, te_tax_support_values.txt). A marginal",
        "# group (vanilla's ig_counts_as_marginal) counts in neither; a group the country lacks",
        "# contributes nothing.",
    ]
    lines += _clout_sum("te_tax_eligible_clout", False) + _clout_sum("te_tax_committed_clout", True)
    lines += ["", "# Clout of the non-marginal groups that are persuadable (not committed, no red line, a",
              "# score of 0 or more): the passage bar's pale segment (te_tax_view_open_share)."]
    lines += _clout_sum("te_tax_open_clout", "open")
    lines += [
        "",
        "# The panels' draft class and \"reverts to\" preview (plan Task 8). te_tax_dr_dstep_<key>",
        "# and te_tax_dr_provisions are the bill's values for the draft, so the workbench can show",
        "# the class the bill would have (te_tax_draft_is_minor, te_tax_triggers.txt).",
    ]
    for key in keys:
        lines += _dstep("dr", key)
    lines += _provisions("dr", keys)
    lines += ["", "# te_tax_succ_dr_<key>: the index a sunset in the draft would revert to (scheduler rule 3",
              "# at the draft's due month; the review's \"then reverts to\")."]
    for key in keys:
        lines += _successor_value(f"te_tax_succ_dr_{key}", "dr", key)
    lines += _offer_values() + _view_values()
    return _txt("\n".join(lines) + "\n")


def _or_block(conditions, indent="\t"):
    return [f"{indent}OR = {{"] + [f"{indent}\t{condition}" for condition in conditions] + [f"{indent}}}"]


def _bill_triggers():
    keys = [instrument.key for instrument in INSTRUMENTS]
    goods = consumption_catalog()
    lines = [
        "",
        "# Draft, bill and passage (docs/systems/tax_code_schema.md, \"Draft, bill and passage\").",
        "# Country scope. Each reads a record's payload, so callers test te_tax_draft_active /",
        "# te_tax_bill_active (te_tax_triggers.txt) first.",
        "",
        "# The draft changes at least one provision.",
        "te_tax_gen_draft_touches_any = {",
    ]
    lines += _or_block([f"var:te_tax_dr_{key} >= 0" for key in keys]
                       + ["te_tax_gen_draft_touches_goods = yes", "var:te_tax_dr_agrel >= 0",
                          "var:te_tax_dr_regrel >= 0"])
    for record, label in (("dr", "draft"), ("bl", "bill")):
        lines += ["}", "", f"# The {label} changes at least one taxed good.",
                  f"te_tax_gen_{label}_touches_goods = {{"]
        lines += _or_block([f"var:te_tax_{record}_g_{good} >= 0" for good in goods])
    lines += [
        "}",
        "",
        "# Every provision the draft changes still has the planned version it had when first",
        "# touched (te_tax_cmd_draft_rebase acknowledges a change).",
        "te_tax_gen_draft_baseline_current = {",
    ]
    for key in keys:
        lines += _or_block([f"var:te_tax_dr_{key} < 0", f"var:te_tax_dr_{key}_pver = var:te_tax_pver_{key}"])
    lines += _or_block(["NOT = { te_tax_gen_draft_touches_goods = yes }",
                        "var:te_tax_dr_goods_pver = var:te_tax_pver_goods"])
    lines += _or_block(["AND = { var:te_tax_dr_agrel < 0 var:te_tax_dr_regrel < 0 }",
                        "var:te_tax_dr_relief_pver = var:te_tax_pver_relief"])
    lines += ["}", "", "# The draft differs from the bill in any field, or one names a state for regional relief",
              "# that the other does not (inside any_in_list PREV is the country, inside PREV = { } the state).",
              "te_tax_gen_draft_differs_from_bill = {"]
    fields = ["due"] + [f"{key}{suffix}" for key in keys for suffix in ("", "_sun")]
    fields += [f"g_{good}" for good in goods] + ["agrel", "regrel"]
    differs = [f"NOT = {{ var:te_tax_dr_{field} = var:te_tax_bl_{field} }}" for field in fields]
    differs += [f"AND = {{ has_variable_list = te_tax_{mine}_relief_states any_in_list = {{ "
                f"variable = te_tax_{mine}_relief_states PREV = {{ NOT = {{ "
                f"is_target_in_variable_list = {{ name = te_tax_{theirs}_relief_states target = PREV }} }} }} }} }}"
                for mine, theirs in (("dr", "bl"), ("bl", "dr"))]
    lines += _or_block(differs)
    lines += [
        "}",
        "",
        "# Every provision group the bill touches still has the external version it had when the",
        "# bill was introduced: nothing outside legislation changed it since.",
        "te_tax_gen_bill_current = {",
    ]
    for key in keys:
        lines += _or_block([f"var:te_tax_bl_{key} < 0", f"var:te_tax_bl_xver_{key} = var:te_tax_xver_{key}"])
    lines += _or_block(["NOT = { te_tax_gen_bill_touches_goods = yes }",
                        "var:te_tax_bl_xver_goods = var:te_tax_xver_goods"])
    lines += _or_block(["AND = { var:te_tax_bl_agrel < 0 var:te_tax_bl_regrel < 0 }",
                        "var:te_tax_bl_xver_relief = var:te_tax_xver_relief"])
    for record, label in (("bl", "bill"), ("dr", "draft")):
        lines += ["}", "", f"# Every provision the {label} changes moves at most two steps from existing law"
                           f" ({'minor bill' if record == 'bl' else 'its class on the panels'}).",
                  f"te_tax_gen_{label}_small_steps = {{"]
        for key in keys:
            lines += _or_block([f"var:te_tax_{record}_{key} < 0",
                                f"AND = {{ te_tax_{record}_dstep_{key} <= 2 te_tax_{record}_dstep_{key} >= -2 }}"])
    lines.append("}")
    for slot in SLOTS:
        p = f"te_tax_p{slot}"
        lines += ["", f"# Slot {slot}'s package touches a provision the bill touches. Read only while it is on.",
                  f"te_tax_gen_bill_overlaps_{slot} = {{"]
        overlaps = [f"AND = {{ var:te_tax_bl_{key} >= 0 var:{p}_{key} >= 0 }}" for key in keys]
        overlaps += [f"AND = {{ var:te_tax_bl_g_{good} >= 0 var:{p}_g_{good} >= 0 }}" for good in goods]
        overlaps += [f"AND = {{ var:te_tax_bl_{field} >= 0 var:{p}_{field} >= 0 }}" for field in ("agrel", "regrel")]
        lines += _or_block(overlaps)
        lines += [
            "}",
            "",
            f"# Slot {slot}'s package: every provision group it changes still has the planned version",
            "# it had after this package's approval, so no later bill has touched it. Fails closed",
            "# for a package stored before the marks existed.",
            f"te_tax_gen_package_unsuperseded_{slot} = {{",
        ]
        for key in keys:
            mark = f"{p}_pver_{key}"
            lines += _or_block([f"var:{p}_{key} < 0",
                                f"AND = {{ has_variable = {mark} var:{mark} = var:te_tax_pver_{key} }}"])
        lines += _or_block([f"NOT = {{ te_tax_gen_package_touches_goods_{slot} = yes }}",
                            f"AND = {{ has_variable = {p}_pver_goods var:{p}_pver_goods = var:te_tax_pver_goods }}"])
        lines += _or_block([f"AND = {{ var:{p}_agrel < 0 var:{p}_regrel < 0 }}",
                            f"AND = {{ has_variable = {p}_pver_relief var:{p}_pver_relief = var:te_tax_pver_relief }}"])
        lines += ["}", "", f"# Slot {slot}'s package touches nothing (every provision superseded).",
                  f"te_tax_gen_package_empty_{slot} = {{"]
        lines += [f"\tvar:{p}_{key} < 0" for key in keys] + [f"\tvar:{p}_g_{good} < 0" for good in goods]
        lines += [f"\tvar:{p}_agrel < 0", f"\tvar:{p}_regrel < 0", "}"]
    return lines


def _supersede(slot):
    p = f"te_tax_p{slot}"
    superseded = _log("superseded", f"slot={slot}: a later approval replaced provisions due on or after its own")
    withdrawn = _log("superseded", f"slot={slot}: every provision replaced; the slot is free")
    lines = [
        "",
        f"# Slot {slot}: supersession at approval. Called by te_tax_cmd_pass only when the new package",
        f"# goes into the other slot. If slot {slot} holds a package (any state) due on or after the",
        "# bill, every provision, good and relief depth the bill touches is dropped from it, so the",
        "# later-approved law wins. The enacted code and its sunsets are never touched here: the",
        "# enacted provision is superseded when the package commences (te_tax_gen_apply_<slot>).",
        "# A package left touching nothing is withdrawn, and the obligations bound to it are",
        f"# released (te_tax_obl_release_slot). History kind {KIND_SUPERSEDED}.",
        f"te_tax_gen_supersede_{slot} = {{",
        "\tif = {",
        "\t\tlimit = {",
        f"\t\t\tvar:{p}_on = 1",
        f"\t\t\tvar:{p}_due >= var:te_tax_bl_due",
        "\t\t}",
        "\t\t# The payload exists only while the slot is on, so read it nested.",
        "\t\tif = {",
        f"\t\t\tlimit = {{ te_tax_gen_bill_overlaps_{slot} = yes }}",
    ]
    for instrument in INSTRUMENTS:
        key = instrument.key
        lines += [
            "\t\t\tif = {",
            "\t\t\t\tlimit = {",
            f"\t\t\t\t\tvar:te_tax_bl_{key} >= 0",
            f"\t\t\t\t\tvar:{p}_{key} >= 0",
            "\t\t\t\t}",
            f"\t\t\t\tset_variable = {{ name = {p}_{key} value = -1 }}",
            f"\t\t\t\tset_variable = {{ name = {p}_{key}_exp value = -1 }}",
            f"\t\t\t\tset_variable = {{ name = {p}_{key}_succ value = -1 }}",
            "\t\t\t}",
        ]
    lines += [f"\t\t\tif = {{ limit = {{ var:te_tax_bl_g_{good} >= 0 var:{p}_g_{good} >= 0 }} "
              f"set_variable = {{ name = {p}_g_{good} value = -1 }} }}" for good in consumption_catalog()]
    lines += [
        f"\t\t\tif = {{ limit = {{ var:te_tax_bl_agrel >= 0 var:{p}_agrel >= 0 }} "
        f"set_variable = {{ name = {p}_agrel value = -1 }} }}",
        "\t\t\tif = {",
        "\t\t\t\tlimit = {",
        "\t\t\t\t\tvar:te_tax_bl_regrel >= 0",
        f"\t\t\t\t\tvar:{p}_regrel >= 0",
        "\t\t\t\t}",
        f"\t\t\t\tset_variable = {{ name = {p}_regrel value = -1 }}",
        f"\t\t\t\tset_variable = {{ name = {p}_regrel_states_set value = 0 }}",
        _clear_list(slot_relief_list(slot), "\t\t\t\t"),
        "\t\t\t}",
        f"\t\t\tte_tax_history_push = {{ KIND = {KIND_SUPERSEDED} SLOT = {slot} }}",
        f"\t\t\t{superseded}",
        "\t\t\tif = {",
        f"\t\t\t\tlimit = {{ te_tax_gen_package_empty_{slot} = yes }}",
        f"\t\t\t\tset_variable = {{ name = {p}_on value = 0 }}",
        f"\t\t\t\tset_variable = {{ name = {p}_state value = {STATE_EMPTY} }}",
        _clear_list(slot_relief_list(slot), "\t\t\t\t"),
        "\t\t\t\t# Its bound obligations lapse with it, unbreached (plan Task 12).",
        f"\t\t\t\tte_tax_obl_release_slot = {{ SLOT = {slot} }}",
        f"\t\t\t\t{withdrawn}",
        "\t\t\t}",
        "\t\t}",
        "\t}",
        "}",
    ]
    return lines


def offer_records():
    """[(bill variable, sentinel)] the bill keeps of its bargains (plan Task 13): per group, the
    promise it accepted under this bill (te_tax_bl_prom_<ig>_kind/_arg/_target, -1 none) and,
    per clause it may be offered, whether it gained that clause (te_tax_bl_got_<ig>_<code>, 0)."""
    records = []
    for ig in IGS:
        records += [(f"te_tax_bl_prom_{ig}_{field}", -1) for field in ("kind", "arg", "target")]
        records += [(f"te_tax_bl_got_{ig}_{code}", 0) for code in clause_offers(ig)]
    return records


def _not_gained(ig, code):
    return f"NAND = {{ has_variable = te_tax_bl_got_{ig}_{code} var:te_tax_bl_got_{ig}_{code} = 1 }}"


def _offer_writes(ig, kind, arg, target="0", indent="\t\t\t"):
    off = f"te_tax_off_{ig}"
    return [f"{indent}set_variable = {{ name = {off}_kind value = {kind} }}",
            f"{indent}set_variable = {{ name = {off}_arg value = {arg} }}",
            f"{indent}set_variable = {{ name = {off}_target value = {target} }}",
            f"{indent}set_variable = {{ name = {off}_maint value = 0 }}"]


def _clause_candidates(ig, indent):
    """The clause offers group `ig` may make, preferred first, each only while no offer is set."""
    off, t = f"te_tax_off_{ig}", indent
    lines = []
    keys = [instrument.key for instrument in INSTRUMENTS]
    grief = f"te_tax_bl_grief_{ig}"
    goods = exposure(ig)["cons"] != 0
    for code in clause_offers(ig):
        if code == OFFER_CUT:
            # One branch per instrument; the conditions make it the group's top grievance (the
            # first in INSTRUMENTS order on a tie), so at most one can hold.
            for key in grievance_keys(ig):
                others = [f"{grief}_{key} >= {grief}_{other}" for other in grievance_keys(ig) if other != key]
                others += [f"{grief}_{key} >= {grief}_goods"] if goods else []
                lines += [f"{t}if = {{", f"{t}\tlimit = {{", f"{t}\t\tvar:{off}_kind = 0",
                          f"{t}\t\t{_not_gained(ig, code)}", f"{t}\t\t{grief}_{key} > 0"]
                lines += [f"{t}\t\t{condition}" for condition in others]
                lines += [f"{t}\t\tte_tax_offer_cut_leaves_a_bill = {{ KEY = {key} }}", f"{t}\t}}"]
                lines += _offer_writes(ig, OFFER_CUT, keys.index(key) + 1, indent=f"{t}\t")
                lines.append(f"{t}}}")
            continue
        lines += [f"{t}if = {{", f"{t}\tlimit = {{", f"{t}\t\tvar:{off}_kind = 0", f"{t}\t\t{_not_gained(ig, code)}"]
        if code == OFFER_AGREL:
            lines += [f"{t}\t\tte_tax_bl_eff_agrel < te_tax_max_agrel", f"{t}\t\tte_tax_bl_eff_wage > 0", f"{t}\t}}"]
            lines += _offer_writes(ig, OFFER_AGREL, 0, indent=f"{t}\t")
        else:
            # The goods the bill taxes are the top grievance, and the bill adds a staple.
            staples = staple_order()
            lines += [f"{t}\t\t{grief}_goods > 0"]
            lines += [f"{t}\t\t{grief}_goods > {grief}_{key}" for key in grievance_keys(ig)]
            lines += [f"{t}\t\tOR = {{"] + [f"{t}\t\t\tte_tax_dl_g_{good} > 0" for good in staples]
            lines += [f"{t}\t\t}}", f"{t}\t\tte_tax_offer_untax_leaves_a_bill = yes", f"{t}\t}}"]
            lines += _offer_writes(ig, OFFER_STAPLE, 0, indent=f"{t}\t")
            for n, good in enumerate(staples, start=1):
                lines.append(f"{t}\t{'if' if n == 1 else 'else_if'} = {{ limit = {{ te_tax_dl_g_{good} > 0 }} "
                             f"set_variable = {{ name = {off}_arg value = {n} }} }}")
        lines.append(f"{t}}}")
    return lines


def _feasible_call(kind, arg, target):
    return (f"te_tax_obl_feasible_{kind} = {{ ARG = {arg} TARGET = {target} }}" if kind == 1
            else f"te_tax_obl_feasible_{kind} = yes")


def _promise_candidates(ig, indent):
    """The promises group `ig` may ask for, each only while no offer is set, the group has
    accepted no promise under this bill, the promise is feasible and could be recorded
    (te_tax_can_obl_propose: no identical pending or binding obligation, a free slot)."""
    off, t = f"te_tax_off_{ig}", indent
    lines = []
    for _name, kind, arg, target in promise_offers(ig):
        lines += [
            f"{t}if = {{",
            f"{t}\tlimit = {{",
            f"{t}\t\tvar:{off}_kind = 0",
            f"{t}\t\tNAND = {{ has_variable = te_tax_bl_prom_{ig}_kind var:te_tax_bl_prom_{ig}_kind > 0 }}",
            f"{t}\t\t{_feasible_call(kind, arg, target)}",
            f"{t}\t\tte_tax_can_obl_propose = {{ KIND = {kind} ARG = {arg} }}",
            f"{t}\t}}",
        ]
        lines += _offer_writes(ig, OFFER_PROMISE + kind, arg, target, indent=f"{t}\t")
        lines += [
            f"{t}\tif = {{",
            f"{t}\t\tlimit = {{ te_tax_obl_is_maintenance = {{ KIND = {kind} ARG = {arg} TARGET = var:{off}_target }} }}",
            f"{t}\t\tset_variable = {{ name = {off}_maint value = 1 }}",
            f"{t}\t}}",
            f"{t}}}",
        ]
    return lines


def _offer_effects():
    """Offer selection, application and the re-proposal of accepted promises (plan Task 13)."""
    reasons = [reason for reason in SUPPORT_REASONS if reason not in ("mat", "gov")]
    lines = [
        "",
        "# Offers (plan Task 13; docs/systems/tax_code_schema.md, \"Offers\"), the last step of the support",
        "# refresh, never a panel. A group committed to this revision withdraws any offer. Any other",
        "# group that is not marginal and has made no offer for this revision makes at most one,",
        "# from its top negative reason: material first means a clause (its catalog order, then a",
        "# promise); any other reason, or none, a promise first. A group at its red line is offered",
        "# promises only, and accepting one commits it only if the promise lifts its score to the",
        "# threshold (te_tax_off_<ig>_commit = 0). An offer is recorded for this revision",
        "# (te_tax_off_<ig>_rev), so a group offers once a revision; a clause it gained in this bill",
        "# (te_tax_bl_got_<ig>_<code>) and a second promise are never offered again; a promise is",
        "# offered only when it could be recorded (te_tax_can_obl_propose: no identical pending or",
        "# binding obligation). te_tax_off_<ig>_maint marks a promise that only maintains what holds.",
        "te_tax_gen_offer_select = {",
    ]
    for ig in IGS:
        off, com = f"te_tax_off_{ig}", f"te_tax_com_{ig}"
        sr = f"te_tax_sr_{ig}"
        lines += [
            f"\t# {ig}: clauses {', '.join(str(code) for code in clause_offers(ig))}; promises "
            f"{', '.join(name for name, *_ in promise_offers(ig)) or 'none'}.",
            f"\tif = {{ limit = {{ NOT = {{ has_variable = {off}_rev }} }} set_variable = {{ name = {off}_kind value = 0 }} "
            f"set_variable = {{ name = {off}_rev value = -1 }} }}",
            "\tif = {",
            f"\t\tlimit = {{ var:{com} = 1 var:{com}_rev = var:te_tax_bl_rev }}",
            f"\t\tset_variable = {{ name = {off}_kind value = 0 }}",
            "\t}",
            "\telse_if = {",
            "\t\tlimit = {",
            f"\t\t\texists = ig:ig_{ig}",
            f"\t\t\tig:ig_{ig} = {{ ig_counts_as_marginal = no }}",
            f"\t\t\tNOT = {{ AND = {{ var:{com} = 1 var:{com}_rev = var:te_tax_bl_rev }} }}",
            f"\t\t\tNOT = {{ var:{off}_rev = var:te_tax_bl_rev }}",
            "\t\t}",
            f"\t\tset_variable = {{ name = {off}_kind value = 0 }}",
            "\t\tif = {",
            "\t\t\tlimit = {",
            f"\t\t\t\tvar:{com} = 0",
            f"\t\t\t\tvar:{sr}_mat < 0",
        ]
        lines += [f"\t\t\t\tvar:{sr}_mat <= var:{sr}_{reason}" for reason in reasons]
        lines += ["\t\t\t}"]
        lines += _clause_candidates(ig, "\t\t\t") + _promise_candidates(ig, "\t\t\t")
        lines += [f"\t\t\tset_variable = {{ name = {off}_commit value = 1 }}", "\t\t}",
                  "\t\telse_if = {", f"\t\t\tlimit = {{ var:{com} = 0 }}"]
        lines += _promise_candidates(ig, "\t\t\t") + _clause_candidates(ig, "\t\t\t")
        lines += [f"\t\t\tset_variable = {{ name = {off}_commit value = 1 }}", "\t\t}", "\t\telse = {"]
        lines += _promise_candidates(ig, "\t\t\t")
        lines += [f"\t\t\tset_variable = {{ name = {off}_commit value = 0 }}", "\t\t}",
                  f"\t\tif = {{ limit = {{ var:{off}_kind > 0 }} set_variable = {{ name = {off}_rev value = var:te_tax_bl_rev }} }}",
                  "\t}"]
    keys = [instrument.key for instrument in INSTRUMENTS]
    lines += [
        "}",
        "",
        "# Applies group IG's offer to the bill (te_tax_cmd_accept_offer, te_tax_offer_effects.txt,",
        "# which has checked it with te_tax_can_accept_offer): a clause through its helper, a promise",
        "# recorded on the bill for te_tax_gen_offer_repropose.",
        "te_tax_gen_offer_apply = {",
    ]
    branches = [(f"var:te_tax_off_$IG$_kind = {OFFER_CUT} var:te_tax_off_$IG$_arg = {idx}",
                 f"te_tax_offer_cut = {{ IG = $IG$ KEY = {key} }}") for idx, key in enumerate(keys, start=1)]
    branches.append((f"var:te_tax_off_$IG$_kind = {OFFER_AGREL}", "te_tax_offer_agrel = { IG = $IG$ }"))
    branches += [(f"var:te_tax_off_$IG$_kind = {OFFER_STAPLE} var:te_tax_off_$IG$_arg = {n}",
                  f"te_tax_offer_untax = {{ IG = $IG$ GOOD = {good} }}") for n, good in enumerate(staple_order(), start=1)]
    branches.append((f"var:te_tax_off_$IG$_kind > {OFFER_PROMISE}", "te_tax_offer_record_promise = { IG = $IG$ }"))
    for n, (limit, effect) in enumerate(branches):
        lines.append(f"\t{'if' if n == 0 else 'else_if'} = {{ limit = {{ {limit} }} {effect} }}")
    lines += [
        "}",
        "",
        "# Proposes again every promise accepted under this bill (te_tax_bl_prom_<ig>_*), after a new",
        "# revision has released the pending ones (te_tax_bill_start_debate, te_tax_cmd_accept_offer):",
        "# a promise belongs to the text, and accepting an offer makes a new text that keeps the",
        "# earlier bargains. KIND and ARG name helper triggers, so each catalog promise has its own",
        "# branch. A record that could not be proposed again (the same promise already binding, or no",
        "# free slot) is dropped, so it never counts.",
        "te_tax_gen_offer_repropose = {",
    ]
    for ig in IGS:
        for _name, kind, arg, _target in promise_offers(ig):
            rec = f"te_tax_bl_prom_{ig}"
            lines += [f"\tif = {{ limit = {{ has_variable = {rec}_kind var:{rec}_kind = {kind} var:{rec}_arg = {arg} }} "
                      f"te_tax_obl_propose = {{ KIND = {kind} ARG = {arg} TARGET = var:{rec}_target "
                      f"IG = te_tax_ig_id_{ig} }} }}"]
    for ig in IGS:
        if not promise_offers(ig):
            continue
        rec = f"te_tax_bl_prom_{ig}"
        lines += [
            "\tif = {",
            f"\t\tlimit = {{ has_variable = {rec}_kind var:{rec}_kind > 0 NOT = {{ te_tax_offer_prom_live = {{ IG = {ig} }} }} }}",
        ]
        lines += [f"\t\tset_variable = {{ name = {rec}_{field} value = -1 }}" for field in ("kind", "arg", "target")]
        lines += [f"\t\t{_log('offer_promise_dropped', 'an accepted promise could not be recorded again on the new revision')}",
                  "\t}"]
    return lines + ["}"]


def _refresh_support():
    lines = [
        "",
        "# The support snapshot (te_tax_refresh_support, while a bill is open): each interest group's",
        "# reasons, its score (their sum, clamped), and its commitment to the bill's current",
        "# revision. A group committed to this revision stays committed; otherwise it commits at",
        "# te_tax_commit_threshold, draws a red line at te_tax_redline_threshold, else is",
        "# persuadable (0). Trust is the group's record of kept and broken promises",
        "# (te_tax_trust_reason_<ig>, plan Task 12); promises are the promises accepted under this",
        "# bill (te_tax_prom_<ig>, plan Task 13), recomputed each time. A group the country lacks is",
        "# zeroed. Last, each group that has not committed may make an offer (te_tax_gen_offer_select).",
        "te_tax_gen_refresh_support = {",
    ]
    for ig in IGS:
        sup, com = f"te_tax_sup_{ig}", f"te_tax_com_{ig}"
        sources = {"mat": f"te_tax_mat_{ig}", "ideo": f"te_tax_ideo_{ig}", "fisc": "te_tax_fiscal_reason",
                   "gov": f"te_tax_gov_{ig}", "prom": f"te_tax_prom_{ig}", "trust": f"te_tax_trust_reason_{ig}"}
        lines += ["\tif = {", f"\t\tlimit = {{ exists = ig:ig_{ig} }}"]
        lines += [f"\t\tset_variable = {{ name = te_tax_sr_{ig}_{reason} value = {sources[reason]} }}"
                  for reason in SUPPORT_REASONS]
        lines.append(f"\t\tset_variable = {{ name = {sup} value = var:te_tax_sr_{ig}_mat }}")
        lines += [f"\t\tchange_variable = {{ name = {sup} add = var:te_tax_sr_{ig}_{reason} }}"
                  for reason in SUPPORT_REASONS[1:]]
        lines += [
            f"\t\tclamp_variable = {{ name = {sup} min = -{SCORE_CAP} max = {SCORE_CAP} }}",
            "\t\tif = {",
            f"\t\t\tlimit = {{ NOT = {{ has_variable = {com} }} }}",
            f"\t\t\tset_variable = {{ name = {com} value = 0 }}",
            f"\t\t\tset_variable = {{ name = {com}_rev value = -1 }}",
            "\t\t}",
            "\t\tif = {",
            "\t\t\tlimit = {",
            "\t\t\t\tNOT = {",
            "\t\t\t\t\tAND = {",
            f"\t\t\t\t\t\tvar:{com} = 1",
            f"\t\t\t\t\t\tvar:{com}_rev = var:te_tax_bl_rev",
            "\t\t\t\t\t}",
            "\t\t\t\t}",
            "\t\t\t}",
            f"\t\t\tset_variable = {{ name = {com}_rev value = var:te_tax_bl_rev }}",
            "\t\t\tif = {",
            f"\t\t\t\tlimit = {{ var:{sup} >= te_tax_commit_threshold }}",
            f"\t\t\t\tset_variable = {{ name = {com} value = 1 }}",
            "\t\t\t}",
            "\t\t\telse_if = {",
            f"\t\t\t\tlimit = {{ var:{sup} <= te_tax_redline_threshold }}",
            f"\t\t\t\tset_variable = {{ name = {com} value = -1 }}",
            "\t\t\t}",
            "\t\t\telse = {",
            f"\t\t\t\tset_variable = {{ name = {com} value = 0 }}",
            "\t\t\t}",
            "\t\t}",
            "\t}",
            "\telse = {",
        ]
        lines += [f"\t\tset_variable = {{ name = te_tax_sr_{ig}_{reason} value = 0 }}" for reason in SUPPORT_REASONS]
        lines += [f"\t\tset_variable = {{ name = {sup} value = 0 }}", f"\t\tset_variable = {{ name = {com} value = 0 }}",
                  f"\t\tset_variable = {{ name = {com}_rev value = -1 }}", "\t}"]
    lines += ["\t# Then the offers of the groups that have not committed (plan Task 13).",
              "\tte_tax_gen_offer_select = yes"]
    return lines + ["}"]


@output(BILL_EFFECTS_PATH)
def bill_effects():
    keys = [instrument.key for instrument in INSTRUMENTS]
    draft, bill = _record_payload("dr"), _record_payload("bl")
    lines = [
        HEADER,
        "# The legislated tax code's draft and bill records and the passage's per-instrument,",
        "# per-good and per-group parts. Schema and rules: docs/systems/tax_code_schema.md, \"Draft,",
        "# bill and passage\". Country scope; called only by te_tax_bill_effects.txt. Payload is",
        "# removed when its record closes (it is read only while te_tax_dr_on / te_tax_bl_on is 1);",
        "# the two tokens themselves are never removed.",
        "",
        "# A new draft with every field untouched (te_tax_cmd_draft_new sets te_tax_dr_due). Its",
        "# regional-relief states and the candidate states to choose them from start empty; the",
        "# candidates are built only by te_tax_cmd_draft_relief_choose.",
        "te_tax_gen_draft_init = {",
    ]
    lines += [f"\tset_variable = {{ name = {name} value = {sentinel} }}" for name, sentinel in draft]
    lines += [_clear_list(name) for name in DRAFT_LISTS]
    lines += ["}", "", "# A new draft copied from the bill under debate, for its revision, with the bill's",
              "# regional-relief states.",
              "te_tax_gen_draft_from_bill = {", "\tset_variable = { name = te_tax_dr_due value = var:te_tax_bl_due }"]
    lines += [f"\tset_variable = {{ name = {name} value = var:te_tax_bl_{name[len('te_tax_dr_'):]} }}"
              for name, _ in draft]
    lines += _copy_state_list("te_tax_bl_relief_states", "te_tax_dr_relief_states")
    lines.append(_clear_list("te_tax_dr_relief_candidates"))
    lines += ["}", "", "# Closes the draft's payload and its lists (te_tax_dr_on is set to 0 by the caller).",
              "te_tax_gen_draft_clear = {", "\tremove_variable = te_tax_dr_due"]
    lines += [f"\tremove_variable = {name}" for name, _ in draft]
    lines += [_clear_list(name) for name in DRAFT_LISTS]
    lines += [
        "}",
        "",
        "# Writes the whole bill record from the draft, every field te_tax_store_package reads, and",
        "# records the external version of each provision group as it stands now. The bill names",
        "# the draft's regional-relief states (te_tax_bl_relief_states).",
        "te_tax_gen_bill_from_draft = {",
        "\tset_variable = { name = te_tax_bl_due value = var:te_tax_dr_due }",
    ]
    lines += [f"\tset_variable = {{ name = te_tax_bl_{name[len('te_tax_dr_'):]} value = var:{name} }}"
              for name, _ in draft]
    lines += [f"\tset_variable = {{ name = {name} value = var:{token} }}" for name, token in _bill_versions()]
    lines += _copy_state_list("te_tax_dr_relief_states", "te_tax_bl_relief_states")
    lines.append("\t# A text from the draft (introduction or a revision) carries no accepted promise and no")
    lines.append("\t# gained clause (plan Task 13): the offers start again.")
    lines += [f"\tset_variable = {{ name = {name} value = {sentinel} }}" for name, sentinel in offer_records()]
    lines += ["}", "",
              "# Closes the bill's payload (te_tax_bl_on is set to 0 by the caller).", "te_tax_gen_bill_clear = {"]
    lines += [f"\tremove_variable = te_tax_bl_{field}" for field in ("due", "rev", "day", "minor")]
    lines += [f"\tremove_variable = {name}" for name, _ in bill]
    lines += [f"\tremove_variable = {name}" for name, _ in _bill_versions()]
    lines += [f"\tremove_variable = {name}" for name, _ in offer_records()]
    lines += [_clear_list("te_tax_bl_relief_states"), "}"]
    for slot in SLOTS:
        lines += _supersede(slot)
    lines += [
        "",
        "# Planned versions: an approval changes the baseline of every provision group it touches,",
        "# so a draft written against the old one must be rebased before it is introduced.",
        "te_tax_gen_bump_pver = {",
    ]
    for key in keys:
        lines += ["\tif = {", f"\t\tlimit = {{ var:te_tax_bl_{key} >= 0 }}",
                  f"\t\tchange_variable = {{ name = te_tax_pver_{key} add = 1 }}", "\t}"]
    lines += [
        "\tif = {",
        "\t\tlimit = { te_tax_gen_bill_touches_goods = yes }",
        "\t\tchange_variable = { name = te_tax_pver_goods add = 1 }",
        "\t}",
        "\tif = {",
        "\t\tlimit = {",
        "\t\t\tOR = {",
        "\t\t\t\tvar:te_tax_bl_agrel >= 0",
        "\t\t\t\tvar:te_tax_bl_regrel >= 0",
        "\t\t\t}",
        "\t\t}",
        "\t\tchange_variable = { name = te_tax_pver_relief add = 1 }",
        "\t}",
        "}",
        "",
        "# Releases every commitment and withdraws every offer (a new bill or revision, an accepted",
        "# offer; the bill closing). An offer's payload is read only while its kind is above 0.",
        "te_tax_gen_reset_commitments = {",
    ]
    for ig in IGS:
        lines += [f"\tset_variable = {{ name = te_tax_com_{ig} value = 0 }}",
                  f"\tset_variable = {{ name = te_tax_com_{ig}_rev value = -1 }}",
                  f"\tset_variable = {{ name = te_tax_off_{ig}_kind value = 0 }}",
                  f"\tset_variable = {{ name = te_tax_off_{ig}_rev value = -1 }}"]
    lines.append("}")
    lines += _refresh_support() + _offer_effects()
    lines += [
        "",
        "# At passage, each group that opposed the bill (score below 0, not committed to this",
        "# revision) disapproves for six months, through the shared ig_approval_effect.",
        "te_tax_gen_oppose_approval = {",
    ]
    for ig in IGS:
        lines += [
            "\tif = {",
            "\t\tlimit = {",
            f"\t\t\thas_variable = te_tax_sup_{ig}",
            f"\t\t\tvar:te_tax_sup_{ig} < 0",
            f"\t\t\thas_variable = te_tax_com_{ig}",
            f"\t\t\tNOT = {{ AND = {{ var:te_tax_com_{ig} = 1 var:te_tax_com_{ig}_rev = var:te_tax_bl_rev }} }}",
            "\t\t}",
            f"\t\tig_approval_effect = {{ IG = ig_{ig} MODIFIER = ig_approval_negative_modifier "
            "DAYS = te_tax_opposed_approval_days }",
            "\t}",
        ]
    lines.append("}")
    lines += _obligation_outcome_effects()
    return _txt("\n".join(lines) + "\n")


def _obligation_outcome_effects():
    """An obligation's consequences for its beneficiary group (te_tax_o<N>_ig, IGS order), per
    group: approval through the shared ig_approval_effect, and trust +-1 within +-TRUST_CAP."""
    lines = [
        "",
        "# Policy obligations (plan Task 12; te_tax_obligation_effects.txt): the beneficiary group of",
        "# obligation slot N (te_tax_o<N>_ig, te_tax_ig_id_<ig>) reacts once per transition. Approval",
        "# goes through the shared ig_approval_effect with MODIFIER (fulfilled te_tax_obl_kept_modifier",
        "# +3, breached te_tax_obl_broken_modifier -5, renegotiated te_tax_obl_renegotiated_modifier",
        "# -2; te_tax_obligation_modifiers.txt), decaying over te_tax_obl_approval_days.",
        "te_tax_gen_obl_approval = {",
    ]
    for idx, ig in enumerate(IGS, start=1):
        lines += [f"\t{'if' if idx == 1 else 'else_if'} = {{",
                  f"\t\tlimit = {{ var:te_tax_o$N$_ig = {idx} }}",
                  f"\t\tig_approval_effect = {{ IG = ig_{ig} MODIFIER = $MODIFIER$ DAYS = te_tax_obl_approval_days }}",
                  "\t}"]
    lines += [
        "}",
        "",
        "# Trust (te_tax_trust_<ig>): DELTA (+1 kept, -1 broken or renegotiated), held within",
        f"# -{TRUST_CAP}..{TRUST_CAP}, and the month of the change (te_tax_trust_<ig>_month); the support model's",
        f"# trust reason is {TRUST_WEIGHT} points a step (te_tax_trust_reason_<ig>).",
        "te_tax_gen_obl_trust = {",
    ]
    for idx, ig in enumerate(IGS, start=1):
        lines += [f"\t{'if' if idx == 1 else 'else_if'} = {{",
                  f"\t\tlimit = {{ var:te_tax_o$N$_ig = {idx} }}",
                  f"\t\tchange_variable = {{ name = te_tax_trust_{ig} add = $DELTA$ }}",
                  f"\t\tclamp_variable = {{ name = te_tax_trust_{ig} min = -{TRUST_CAP} max = {TRUST_CAP} }}",
                  f"\t\tset_variable = {{ name = te_tax_trust_{ig}_month value = te_history_month_index }}",
                  "\t}"]
    lines += [
        "}",
        "",
        "# Trust recovers (te_tax_obl_check_month, monthly): a group's trust that has not changed for",
        "# te_tax_obl_trust_recover_months moves one step toward 0, and the step counts as its change.",
        "te_tax_gen_trust_recover = {",
    ]
    for ig in IGS:
        trust, month = f"te_tax_trust_{ig}", f"te_tax_trust_{ig}_month"
        lines += [
            "\tif = {",
            f"\t\tlimit = {{ has_variable = {trust} has_variable = {month} var:{month} <= te_tax_obl_trust_recover_before }}",
            f"\t\tif = {{ limit = {{ var:{trust} > 0 }} change_variable = {{ name = {trust} add = -1 }} "
            f"set_variable = {{ name = {month} value = te_history_month_index }} }}",
            f"\t\telse_if = {{ limit = {{ var:{trust} < 0 }} change_variable = {{ name = {trust} add = 1 }} "
            f"set_variable = {{ name = {month} value = te_history_month_index }} }}",
            "\t}",
        ]
    lines.append("}")
    return lines


@output(EFFECTS_PATH)
def scripted_effects():
    lines = [
        HEADER,
        "# The legislated tax code's per-instrument and per-good effects. Schema and rules:",
        "# docs/systems/tax_code_schema.md. All country scope.",
        "#",
        "# te_tax_gen_init_*: called by te_tax_init_country (te_tax_state_effects.txt). Each write",
        "# happens only if the variable is absent, so an existing value is never overwritten.",
        "# te_tax_gen_sync_*: called by te_tax_sync_collection (te_tax_collection_effects.txt),",
        "# the only writer of a rule-on country's native tax state, which saves",
        "# scope:te_tax_country and scope:te_tax_sponsor first. Each sync removes what the",
        "# enacted code does not hold and adds what it holds and is missing. Amendment and",
        "# goods changes are not visible later in the same effect, so run each at most once",
        "# per effect execution; a call in a later execution then changes nothing. The",
        "# removal loop never touches the enacted amendment, and the add checks only that one.",
        "# te_tax_gen_count_goods_drift: the writer's drift count of goods (te_tax_detect_drift).",
        "# The scheduler's parts follow the syncs: te_tax_gen_sunset_<key>,",
        "# te_tax_gen_commence_<slot>, te_tax_gen_hold_missed_<slot>, te_tax_gen_apply_<slot>,",
        "# te_tax_gen_store_<slot>, te_tax_gen_next_month and te_tax_gen_history_write, called",
        "# by te_tax_schedule_effects.txt. The migration's parts follow:",
        "# te_tax_gen_migrate_rates, te_tax_gen_migrate_goods and te_tax_gen_migrate_provisions,",
        "# called by te_tax_migrate_country (te_tax_migration_effects.txt). The copies for new",
        "# countries close the file: te_tax_gen_copy_code, te_tax_gen_copy_slot_<slot> and",
        "# te_tax_gen_copy_enacted, called by te_tax_civil_war_effects.txt, with the policy",
        "# obligations' te_tax_gen_copy_obligations and te_tax_gen_clear_obligations (plan Task 12).",
        "",
        "# Each instrument's tokens with their sentinels, if absent.",
        "te_tax_gen_init_instruments = {",
    ]
    for instrument in INSTRUMENTS:
        for suffix, sentinel in INSTRUMENT_TOKENS:
            lines.append(_guarded_write(f"te_tax_en_{instrument.key}{suffix}", sentinel))
        for prefix, sentinel in VERSION_TOKENS:
            lines.append(_guarded_write(f"{prefix}{instrument.key}", sentinel))
    lines += ["}", "", "# te_tax_en_g_<good> = 0 for every catalog good, if absent.",
              "te_tax_gen_init_goods = {"]
    lines += [_guarded_write(f"te_tax_en_g_{good}", 0) for good in consumption_catalog()]
    lines.append("}")
    lines += [
        "",
        "# The scheduler's clock, package-slot headers and history ring, if absent. A package's",
        "# payload is not initialised: te_tax_store_package writes all of it, and nothing reads",
        "# it while the slot's te_tax_p<slot>_on is 0.",
        "te_tax_gen_init_schedule = {",
    ]
    lines += [_guarded_write(name, sentinel) for name, sentinel in schedule_tokens()]
    lines += [
        "}",
        "",
        "# The policy obligations' slot headers and each interest group's trust, if absent (plan",
        "# Task 12). An obligation's payload is not initialised: te_tax_obl_write writes all of it,",
        "# and nothing reads it while the slot's te_tax_o<n>_on is 0.",
        "te_tax_gen_init_obligations = {",
    ]
    lines += [_guarded_write(name, sentinel) for name, sentinel in obligation_tokens()]
    lines.append("}")
    for instrument in INSTRUMENTS:
        key = instrument.key
        lines += [
            "",
            f"# {instrument.label}: leaves exactly amendment_te_tax_{key}_<te_tax_en_{key}> on the",
            "# carrier, and none at index 0.",
            f"te_tax_gen_sync_{key} = {{",
            "\tactive_law:lawgroup_taxation = {",
            "\t\tevery_scope_amendment = {",
            "\t\t\tlimit = {",
            f"\t\t\t\tte_tax_amendment_is_{key} = yes",
            f"\t\t\t\tNOT = {{ te_tax_amendment_matches_{key} = yes }}",
            "\t\t\t}",
            "\t\t\tremove_amendment = yes",
            "\t\t}",
            "\t}",
        ]
        for idx in range(1, instrument.max_idx + 1):
            name = amendment_key(instrument, idx)
            lines += [
                f"\t{'if' if idx == 1 else 'else_if'} = {{",
                f"\t\tlimit = {{ var:te_tax_en_{key} = {idx} }}",
                "\t\tactive_law:lawgroup_taxation = {",
                "\t\t\tif = {",
                f"\t\t\t\tlimit = {{ NOT = {{ has_amendment = amendment_type:{name} }} }}",
                f"\t\t\t\tadd_amendment = {{ type = {name} sponsor = scope:te_tax_sponsor cooldown = 0 }}",
                "\t\t\t}",
                "\t\t}",
                "\t}",
            ]
        lines.append("}")
    lines += [
        "",
        "# Taxed goods: the native consumption-tax list holds a catalog good exactly when",
        "# te_tax_en_g_<good> = 1, and never holds a good outside the catalog, so the native",
        "# taxed set always equals the enacted one.",
        "te_tax_gen_sync_goods = {",
    ]
    for good in consumption_catalog():
        variable = f"var:te_tax_en_g_{good}"
        lines += [
            "\tif = {",
            f"\t\tlimit = {{ {variable} = 1 NOT = {{ has_consumption_tax = g:{good} }} }}",
            f"\t\tadd_taxed_goods = g:{good}",
            "\t}",
            "\telse_if = {",
            f"\t\tlimit = {{ NOT = {{ {variable} = 1 }} has_consumption_tax = g:{good} }}",
            f"\t\tremove_taxed_goods = g:{good}",
            "\t}",
        ]
    lines.append("\t# Goods no pop buys: never on the enacted list, so never natively taxed.")
    lines += [f"\tif = {{ limit = {{ has_consumption_tax = g:{good} }} remove_taxed_goods = g:{good} }}"
              for good in stray_goods()]
    lines.append("}")
    lines += [
        "",
        "# Drift (te_tax_detect_drift, te_tax_collection_effects.txt): +1 to te_tax_drift_goods for",
        "# each good whose native consumption tax differs from the enacted list, counted before",
        "# the sync puts it back. Reads native state; writes only the counter.",
        "te_tax_gen_count_goods_drift = {",
    ]
    lines += [f"\tif = {{ limit = {{ {condition} }} change_variable = {{ name = te_tax_drift_goods add = 1 }} }}"
              for condition in _goods_drift_conditions()]
    lines.append("}")
    lines += _scheduler_effects() + _migration_effects() + _copy_effects()
    return _txt("\n".join(lines) + "\n")


def _goods_drift_conditions():
    """Per good, the condition that its native consumption tax differs from the
    enacted list: a catalog good taxed or untaxed against te_tax_en_g_<good>,
    any other good taxed at all."""
    out = []
    for good in consumption_catalog():
        variable = f"var:te_tax_en_g_{good}"
        out.append(f"OR = {{ AND = {{ {variable} = 1 NOT = {{ has_consumption_tax = g:{good} }} }} "
                   f"AND = {{ NOT = {{ {variable} = 1 }} has_consumption_tax = g:{good} }} }}")
    out += [f"has_consumption_tax = g:{good}" for good in stray_goods()]
    return out


@output(TRIGGERS_PATH)
def scripted_triggers():
    lines = [
        HEADER,
        "# Amendment-scope triggers over the generated rate amendments, in the form the tax",
        "# probe used in game (te_debug_tax_effects.txt: `type = amendment_type:<key>`).",
        "# te_tax_amendment_is_<key>: the amendment is one of that instrument's family.",
        "# te_tax_amendment_matches_<key>: it is the one the country's enacted index names.",
        "# The match reads scope:te_tax_country, which the caller saves first",
        "# (te_tax_sync_collection does).",
    ]
    for instrument in INSTRUMENTS:
        key = instrument.key
        names = [amendment_key(instrument, idx) for idx in range(1, instrument.max_idx + 1)]
        lines += ["", f"te_tax_amendment_is_{key} = {{", "\tOR = {"]
        lines += [f"\t\ttype = amendment_type:{name}" for name in names]
        lines += ["\t}", "}", "", f"te_tax_amendment_matches_{key} = {{", "\tOR = {"]
        lines += [f"\t\tAND = {{ type = amendment_type:{name} scope:te_tax_country.var:te_tax_en_{key} = {idx} }}"
                  for idx, name in enumerate(names, start=1)]
        lines += ["\t}", "}"]
    lines += [
        "",
        "# Drift (te_tax_detect_drift, te_tax_collection_effects.txt). Country scope; read the",
        "# native state against the enacted code before the sync puts it back.",
        "# te_tax_gen_goods_drift: some good's native consumption tax differs from the enacted list.",
        "te_tax_gen_goods_drift = {",
        "\tOR = {",
    ]
    lines += [f"\t\t{condition}" for condition in _goods_drift_conditions()]
    lines += ["\t}", "}"]
    for instrument in INSTRUMENTS:
        key = instrument.key
        lines += [
            "",
            f"# te_tax_gen_amend_drift_{key}: the carrier's {instrument.label.lower()} amendments differ from",
            f"# te_tax_en_{key}: the enacted one is missing, or another of the family is on the law.",
            f"te_tax_gen_amend_drift_{key} = {{",
            "\tOR = {",
        ]
        for idx in range(1, instrument.max_idx + 1):
            law = f"active_law:lawgroup_taxation = {{ has_amendment = amendment_type:{amendment_key(instrument, idx)} }}"
            lines += [f"\t\tAND = {{ var:te_tax_en_{key} = {idx} NOT = {{ {law} }} }}",
                      f"\t\tAND = {{ NOT = {{ var:te_tax_en_{key} = {idx} }} {law} }}"]
        lines += ["\t}", "}"]
    lines += _scheduler_triggers() + _bill_triggers() + _obligation_triggers() + _offer_triggers()
    return _txt("\n".join(lines) + "\n")


def _offer_triggers():
    """Whether group IG's offer can still be accepted (plan Task 13): the bill still raises the
    tax a cut lowers, still adds the staple, relief still has a band to add, or the promise is
    still feasible and could be recorded. te_tax_can_accept_offer
    asks it, so the Accept button and the click agree; an unknown offer fails."""
    keys = [instrument.key for instrument in INSTRUMENTS]
    off = "te_tax_off_$IG$"
    lines = [
        "",
        "# Offers (plan Task 13; te_tax_can_accept_offer, te_tax_triggers.txt). Country scope, while a",
        "# bill is under debate and group IG has an offer (te_tax_off_<ig>_kind above 0).",
        "te_tax_gen_offer_feasible = {",
    ]
    branches = [(f"var:{off}_kind = {OFFER_CUT} var:{off}_arg = {idx}",
                 f"te_tax_bl_dstep_{key} > 0 te_tax_offer_cut_leaves_a_bill = {{ KEY = {key} }}")
                for idx, key in enumerate(keys, start=1)]
    branches.append((f"var:{off}_kind = {OFFER_AGREL}", "te_tax_bl_eff_agrel < te_tax_max_agrel te_tax_bl_eff_wage > 0"))
    branches += [(f"var:{off}_kind = {OFFER_STAPLE} var:{off}_arg = {n}",
                  f"te_tax_dl_g_{good} > 0 te_tax_offer_untax_leaves_a_bill = yes")
                 for n, good in enumerate(staple_order(), start=1)]
    seen = set()
    for _name, kind, arg, _target, _groups in PROMISE_OFFERS:
        if (kind, arg) in seen:
            continue
        seen.add((kind, arg))
        target = f"var:{off}_target"
        branches.append((f"var:{off}_kind = {OFFER_PROMISE + kind} var:{off}_arg = {arg}",
                         f"{_feasible_call(kind, arg, target)} te_tax_can_obl_propose = {{ KIND = {kind} ARG = {arg} }}"))
    for n, (limit, test) in enumerate(branches):
        lines.append(f"\t{'trigger_if' if n == 0 else 'trigger_else_if'} = {{ limit = {{ {limit} }} {test} }}")
    return lines + ["\ttrigger_else = { always = no }", "}"]


def _obligation_triggers():
    """The civil-war repair's reassessment of obligation slot N (plan Task 12)."""
    lines = [
        "",
        "# Policy obligations (plan Task 12; te_tax_repair_obligations_after_civil_war). Country scope.",
        "# te_tax_gen_obl_ig_exists: the country still has obligation slot N's beneficiary group.",
        "te_tax_gen_obl_ig_exists = {",
        "\tOR = {",
    ]
    lines += [f"\t\tAND = {{ var:te_tax_o$N$_ig = {idx} exists = ig:ig_{ig} }}" for idx, ig in enumerate(IGS, start=1)]
    lines += [
        "\t}",
        "}",
        "",
        "# te_tax_gen_obl_slot_gone: the passed bill obligation slot N is bound to no longer waits",
        "# in its package slot (te_tax_o<N>_slot as te_tax_slot_id_<slot> codes it).",
        "te_tax_gen_obl_slot_gone = {",
        "\tNOR = {",
    ]
    lines += [f"\t\tAND = {{ var:te_tax_o$N$_slot = te_tax_slot_id_{slot} var:te_tax_p{slot}_on = 1 }}"
              for slot in SLOTS]
    lines += ["\t}", "}"]
    return lines


@output(SGUIS_PATH)
def generated_sguis():
    lines = [
        HEADER,
        "# The legislated tax code's workbench handlers (plan Task 8; docs/systems/tax_code_schema.md,",
        "# \"Panels\"). Hand-written ones (commands, the commencement stepper, display gates) are in",
        "# te_tax_sguis.txt. Each handler's is_valid is a Task 6 trigger te_tax_can_<command> and its",
        "# effect the matching te_tax_cmd_<command> with the same parameters, so a button's tooltip and",
        "# its click cannot disagree. Country scope, rooted on the player; never the AI's.",
        "#",
        "# te_tax_step_<key>_sgui, one per instrument (INSTRUMENTS), op-coded by one saved scope:",
    ]
    lines += [f"#   {op:>2}  te_tax_cmd_{command} DIR = {direction}" for op, command, direction in STEP_OPS]
    lines += [
        "# Every branch tests `exists = scope:op`; an unknown or missing op fails closed",
        "# (trigger_else = { always = no }) and runs nothing.",
        "# te_tax_good_<good>_sgui, one per catalog good: te_tax_cmd_draft_good.",
        "# te_tax_relief_<key>_sgui, one per relief (agrel, regrel), op-coded like the step handlers:",
        "#   op 0 one band less, 1 one band more, 2 none, 3 the deepest band, 4 out of the draft",
        "#   (te_tax_cmd_draft_relief DIR = op).",
    ]
    for instrument in INSTRUMENTS:
        key = instrument.key
        lines += ["", f"te_tax_step_{key}_sgui = {{", "\tscope = country", "\tsaved_scopes = { op }",
                  "\tis_shown = { te_tax_code_in_force = yes }", "\tai_is_valid = { always = no }", "\tis_valid = {"]
        for n, (op, command, direction) in enumerate(STEP_OPS):
            lines += [f"\t\t{'trigger_if' if n == 0 else 'trigger_else_if'} = {{",
                      f"\t\t\tlimit = {{ exists = scope:op scope:op = {op} }}",
                      f"\t\t\tte_tax_can_{command} = {{ KEY = {key} DIR = {direction} }}", "\t\t}"]
        lines += ["\t\ttrigger_else = { always = no }", "\t}", "\teffect = {"]
        for n, (op, command, direction) in enumerate(STEP_OPS):
            lines += [f"\t\t{'if' if n == 0 else 'else_if'} = {{",
                      f"\t\t\tlimit = {{ exists = scope:op scope:op = {op} }}",
                      f"\t\t\tte_tax_cmd_{command} = {{ KEY = {key} DIR = {direction} }}", "\t\t}"]
        lines += ["\t}", "}"]
    for good in consumption_catalog():
        lines += ["", f"te_tax_good_{good}_sgui = {{", "\tscope = country", "\tis_shown = { te_tax_code_in_force = yes }",
                  "\tai_is_valid = { always = no }", f"\tis_valid = {{ te_tax_can_draft_good = {{ GOOD = {good} }} }}",
                  f"\teffect = {{ te_tax_cmd_draft_good = {{ GOOD = {good} }} }}", "}"]
    for key in RELIEF_KEYS:
        lines += ["", f"te_tax_relief_{key}_sgui = {{", "\tscope = country", "\tsaved_scopes = { op }",
                  "\tis_shown = { te_tax_code_in_force = yes }", "\tai_is_valid = { always = no }", "\tis_valid = {"]
        for n, op in enumerate(RELIEF_OPS):
            lines += [f"\t\t{'trigger_if' if n == 0 else 'trigger_else_if'} = {{",
                      f"\t\t\tlimit = {{ exists = scope:op scope:op = {op} }}",
                      f"\t\t\tte_tax_can_draft_relief = {{ KEY = {key} DIR = {op} }}", "\t\t}"]
        lines += ["\t\ttrigger_else = { always = no }", "\t}", "\teffect = {"]
        for n, op in enumerate(RELIEF_OPS):
            lines += [f"\t\t{'if' if n == 0 else 'else_if'} = {{",
                      f"\t\t\tlimit = {{ exists = scope:op scope:op = {op} }}",
                      f"\t\t\tte_tax_cmd_draft_relief = {{ KEY = {key} DIR = {op} }}", "\t\t}"]
        lines += ["\t}", "}"]
    return _txt("\n".join(lines) + "\n")


def _gui_view(name, op, value):
    return (f"{op}( GetPlayer.MakeScope.ScriptValue('{name}'), '(CFixedPoint){value}' )")


@output(ROWS_PATH)
def generated_rows():
    lines = [
        HEADER,
        "### The legislated tax code's per-good rows (plan Task 8): the workbench's goods catalog and",
        "### the review's goods lines, one per consumption-catalog good, in catalog order. The row",
        "### types, te_tax_good_row and te_tax_review_good_line, are in te_tax_workbench_widget.gui",
        "### and te_tax_review_widget.gui; the goods' names are their own loc keys. Every value is a",
        "### guarded view of the player's draft (te_tax_view_dr_g_<good>*), shown as a 0/1 code.",
        "",
        "types te_tax_generated_rows_types",
        "{",
        "\t### The goods catalog: the good, taxed or not under existing law in the draft's month,",
        "\t### taxed or not in the draft, and its toggle (te_tax_good_<good>_sgui).",
        "\ttype te_tax_wb_goods_rows = flowcontainer {",
        "\t\tdirection = vertical",
        "\t\tignoreinvisible = yes",
        "\t\tspacing = 1",
    ]
    for good in consumption_catalog():
        law = _gui_view(f"te_tax_view_dr_g_{good}_base", "EqualTo_CFixedPoint", 1)
        draft = _gui_view(f"te_tax_view_dr_g_{good}", "EqualTo_CFixedPoint", 1)
        touched = _gui_view(f"te_tax_view_dr_g_{good}_on", "NotEqualTo_CFixedPoint", 0)
        lines += [
            "",
            "\t\tte_tax_good_row = {",
            f"\t\t\tdatacontext = \"[GetScriptedGui('te_tax_good_{good}_sgui')]\"",
            "\t\t\tblockoverride \"good_name\" {",
            f"\t\t\t\ttext = \"{good}\"",
            "\t\t\t}",
            "\t\t\tblockoverride \"good_law\" {",
            f"\t\t\t\ttext = \"[SelectLocalization( {law}, 'te_tax_wb_good_taxed', 'te_tax_wb_good_untaxed' )]\"",
            "\t\t\t}",
            "\t\t\tblockoverride \"good_draft\" {",
            f"\t\t\t\ttext = \"[SelectLocalization( {touched}, SelectLocalization( {draft}, "
            "'te_tax_wb_good_taxed_changed', 'te_tax_wb_good_untaxed_changed' ), "
            f"SelectLocalization( {draft}, 'te_tax_wb_good_taxed', 'te_tax_wb_good_untaxed' ) )]\"",
            "\t\t\t}",
            "\t\t\tblockoverride \"good_button_text\" {",
            f"\t\t\t\ttext = \"[SelectLocalization( {touched}, 'te_tax_wb_good_undo', "
            f"SelectLocalization( {law}, 'te_tax_wb_good_untax', 'te_tax_wb_good_tax' ) )]\"",
            "\t\t\t}",
            "\t\t}",
        ]
    lines += [
        "\t}",
        "",
        "\t### The review's goods lines: each good the draft changes, and whether it is taxed from the",
        "\t### draft's commencement.",
        "\ttype te_tax_rv_goods_rows = flowcontainer {",
        "\t\tdirection = vertical",
        "\t\tignoreinvisible = yes",
    ]
    for good in consumption_catalog():
        draft = _gui_view(f"te_tax_view_dr_g_{good}", "EqualTo_CFixedPoint", 1)
        touched = _gui_view(f"te_tax_view_dr_g_{good}_on", "NotEqualTo_CFixedPoint", 0)
        lines += [
            "",
            "\t\tte_tax_review_good_line = {",
            f"\t\t\tvisible = \"[{touched}]\"",
            "\t\t\tblockoverride \"line_label\" {",
            f"\t\t\t\ttext = \"{good}\"",
            "\t\t\t}",
            "\t\t\tblockoverride \"line_value\" {",
            f"\t\t\t\ttext = \"[SelectLocalization( {draft}, 'te_tax_rv_good_taxed', 'te_tax_rv_good_untaxed' )]\"",
            "\t\t\t}",
            "\t\t}",
        ]
    lines += ["\t}", "}"]
    return _txt("\n".join(lines) + "\n")


@output(MODIFIERS_PATH)
def static_modifiers():
    lines = [
        HEADER,
        "# Interest-group views of the enacted tax code (plan Task 13; docs/systems/tax_code_schema.md,",
        "# \"Interest-group views of the code\"). Per group, one modifier per nonzero stance band toward",
        "# the vanilla taxation law the code is equivalent to (-2 strongly opposes .. +2 strongly",
        "# endorses), carrying the approval vanilla gives for an active law the group takes that",
        f"# stance on (IG_APPROVAL_FROM_LAW = {VANILLA_APPROVAL_FROM_LAW}, IG_APPROVAL_FROM_LAW_STRONG_STANCE = "
        f"{VANILLA_APPROVAL_FROM_LAW_STRONG}); a neutral",
        "# group has none. te_tax_gen_ig_views (te_tax_generated_effects.txt), run by the monthly",
        "# processor, keeps at most one of each group's four on a country under the rule. Static: no",
        "# multiplier.",
    ]
    for ig in IGS:
        for band, value in VIEW_BANDS:
            lines += ["", f"te_tax_ig_view_{ig}_{band} = {{",
                      f"\ticon = \"gfx/interface/icons/timed_modifier_icons/{VIEW_ICONS[value]}.dds\"",
                      f"\tinterest_group_ig_{ig}_approval_add = {VIEW_APPROVAL[value]}", "}"]
    return _txt("\n".join(lines) + "\n")


VIEW_NAMES = {-2: "Strongly Opposes the Tax Code", -1: "Opposes the Tax Code", 1: "Endorses the Tax Code",
              2: "Strongly Endorses the Tax Code"}


@output(LOC_PATH)
def localization():
    entries = {}
    for instrument in INSTRUMENTS:
        for idx in range(1, instrument.max_idx + 1):
            key = amendment_key(instrument, idx)
            shown = display(instrument, idx)
            entries[key] = f'0 "{instrument.label.title()} {shown}"'
            entries[f"{key}_desc"] = f'0 "Taxes {instrument.payer} at {shown}."'
    # Plan Task 13: the view bands' names and descriptions, and the staple offers' lines.
    for ig in IGS:
        for band, value in VIEW_BANDS:
            key = f"te_tax_ig_view_{ig}_{band}"
            entries[key] = f'0 "{VIEW_NAMES[value]}"'
            entries[f"{key}_desc"] = ('0 "This group\'s stance on the taxation law the enacted tax code comes '
                                      'closest to, counted as it would be for that law."')
    for good in staple_order():
        entries[f"te_tax_offer_untax_{good}"] = f'0 "Leave ${good}$ untaxed."'
        entries[f"te_tax_tt_offer_untax_{good}"] = f'0 "The bill and the draft no longer tax ${good}$."'
    return _render_loc_file([(section_label(LOC_CATEGORY), entries)])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def render_all():
    validate()
    return {path: function() for path, function in OUTPUTS.items()}


def drifted(root, rendered):
    """The repo-relative paths whose file under `root` is missing or differs."""
    changed = []
    for path, expected in rendered.items():
        try:
            with open(os.path.join(root, path), "rb") as handle:
                actual = handle.read()
        except FileNotFoundError:
            actual = None
        if actual != expected:
            changed.append(path)
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check", action="store_true",
        help="write nothing; exit 1 and list the files that differ from the generator's output",
    )
    parser.add_argument("--root", default=REPO, help="tree to read or write (default: this repo)")
    args = parser.parse_args(argv)

    rendered = render_all()
    changed = drifted(args.root, rendered)
    if args.check:
        if changed:
            print("gen_tax_code.py: generated files differ from the generator's output:")
            for path in changed:
                print(f"  {path}")
            print("Edit the generator and run `python3 scripts/generators/gen_tax_code.py`; "
                  "never edit a generated file by hand.")
            return 1
        print(f"gen_tax_code.py: {len(rendered)} generated files match.")
        return 0
    for path in changed:
        target = os.path.join(args.root, path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as handle:
            handle.write(rendered[path])
        print(f"wrote {path}")
    if not changed:
        print(f"gen_tax_code.py: {len(rendered)} generated files already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
