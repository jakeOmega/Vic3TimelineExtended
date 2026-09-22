"""Monte-Carlo simulation of the banking cycle + monetary policy loop.

WHY THIS EXISTS
---------------
`je_banking_cycle`'s monthly pulse and `te_monetary_monthly_update` are a coupled
feedback loop: the policy rate sets a stance gap, the stance gap pushes momentum
and bubble pressure, the cycle phase leans the mandate's rate target back. Nothing
in the repo tells you what that loop *does* over a century — how often it crashes,
how long downturns last, how much the currency law or the delegation mandate
matters. This runs the loop a few thousand times and reports the distribution.

WHAT IS PORTED, AND FROM WHERE
------------------------------
Control flow is hand-ported from script; every *number* is read out of the mod
files at import time by `ModConstants` (below), so retuning a script value or a
static modifier changes this simulation without editing it. A renamed or deleted
constant raises at startup rather than silently falling back to a literal.

Sources:
  common/journal_entries/je_banking.txt            monthly pulse order, seeds
  common/scripted_effects/banking_cycle_effects.txt  advance / crash / phase steps
  common/scripted_effects/te_monetary_effects.txt    target / drift / stance / gold
  common/script_values/te_monetary_script_values.txt the monetary constants
  common/script_values/extra_script_values.txt       nudge, crash mult, inertia
  common/static_modifiers/extra_modifiers.txt        phase, inertia, tool modifiers
  common/scripted_buttons/timeline_extended_scripted_buttons.txt  cb_* ai_chance
  common/laws/extra_laws.txt                         the four regime-rule grants
  events/minor_events.txt                            the crash event's options

TWO ENGINE SEMANTICS THAT CHANGE THE ANSWER
-------------------------------------------
1. `random_list` probability is w / (w + other weights), NOT w / 100. The crash
   check is `0 = { modifier = {...} }` against `100 = {}`, so p = w / (w + 100).
2. Inside a `random_list` entry's `modifier` block, `value =` REPLACES the entry's
   literal weight; only `add =` accumulates onto it. Vanilla does the same
   (`game/common/scripted_effects/04_neg_event_options_scripted_effects.txt`,
   `5 = { modifier = { value = neg_option_7_modifier } }`). So the mean-reversion
   nudge's `25 = { modifier = { value = var:finance_cycle_value subtract = 50
   divide = 5 } }` has weight (v-50)/5, not 25 + (v-50)/5.

THE ONE-MONTH LAGS, WHICH ARE LOAD-BEARING
------------------------------------------
`add_modifier`/`remove_modifier` are not visible inside the effect block that
issues them, so within one pulse:
  * `banking_cycle_advance_variables` reads the phase / inertia / fiscal modifiers
    that `banking_cycle_apply_phase_modifiers` put on at the END of LAST month;
  * the stance gap it reads is up to a month old by design (§16.3), because the
    order of `on_monthly_pulse_country` and the JE pulse is not guaranteed.
The simulation reproduces both. `--pulse-order` flips the second for sensitivity.

EXOGENOUS GAME STATE — THE FIDELITY RISK
----------------------------------------
Everything the script reads from the *engine* rather than from its own variables
has to be stubbed. These are the assumptions; they are the first thing to argue
with if a number here looks wrong.

  gdp                      1e7 at start, compounds at the sampled growth rate
  yearly GDP growth        AR(1), mean 2.0%, sd 1.2%  (feeds te_mon_growth_term)
  deficit as % of GDP      AR(1), mean 1.5%, sd 1.0%, x3 while at war
  scaled_debt              integrates the deficit, clamped 0..1.5
  is_at_war                2-state Markov, ~8% of months, mean run 24 months
  basket index (prices)    AR(1) log walk, sd 1.2%/yr  (feeds cost-push)
  scaled_gold_reserves     0.6 flat (only seeds the bank's vault)
  world inflation          1.5% flat (commodity money's specie term)
  world reference rate     te_mon_era_base by tech era: 3.0 / 2.5 / 2.0
  has_healthy_economy      false once scaled_debt > 0.6
  tech unlocks             by year, for the crash event's option list

DELIBERATELY OUT OF SCOPE (pass 1)
----------------------------------
  * the 77 `banking_cycle_events.txt` random events. They are the bulk of the
    system's content and most of them move bubble/momentum, but every one is a
    player CHOICE. Excluding them makes this a study of the *mechanical* loop.
    `--event-channel` adds a crude aggregate stand-in for a sensitivity read.
  * contagion, crisis waves and the Great Depression chain: single-country sim.
  * the FX index, monetisation, and phase-5 arrangements: held at par / zero.
  * `ce_*` / `cw_*` tools: command economy and cooperative ownership are a
    different economic law, and the question posed was about currency laws.

USAGE
-----
    .venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 400
    .venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 400 --json out.json
    .venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --only fiat
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import statistics
import zlib
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

SCRIPT_VALUE_FILES = [
    REPO / "common/script_values/te_monetary_script_values.txt",
    REPO / "common/script_values/extra_script_values.txt",
    REPO / "common/script_values/te_monetary_fx_script_values.txt",
]
STATIC_MODIFIER_FILE = REPO / "common/static_modifiers/extra_modifiers.txt"
LAW_FILE = REPO / "common/laws/extra_laws.txt"


# ─────────────────────────────────────────────────────────────────────────────
# Reading the numbers out of the mod
# ─────────────────────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _block(src: str, name: str) -> str | None:
    """Return the brace-balanced body of `name = { ... }`, or None."""
    m = re.search(r"^%s\s*=\s*\{" % re.escape(name), src, re.M)
    if not m:
        return None
    depth = 0
    i = m.end() - 1
    j = i
    while j < len(src):
        c = src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[i + 1 : j]
        j += 1
    return None


def _strip_comments(body: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in body.splitlines())


class ModConstants:
    """Flat constants and static-modifier fields, read from the mod files.

    Only `name = { value = <number> }` script values are read here. Anything with
    branches is ported as control flow in the simulation instead, because a
    branch's *shape* is the thing being modelled — `te_mon_target_max` differs by
    regime, so it is a function below, not a constant.
    """

    def __init__(self) -> None:
        self._sv_src = "\n".join(_read(p) for p in SCRIPT_VALUE_FILES)
        self._mod_src = _read(STATIC_MODIFIER_FILE)
        self._law_src = _read(LAW_FILE)
        self._cache: dict[str, float] = {}

    def sv(self, name: str) -> float:
        """A script value whose whole body is a single numeric `value =`."""
        if name in self._cache:
            return self._cache[name]
        body = _block(self._sv_src, name)
        if body is None:
            raise KeyError(f"script value {name!r} not found in {SCRIPT_VALUE_FILES}")
        stripped = _strip_comments(body).strip()
        m = re.fullmatch(r"value\s*=\s*(-?[\d.]+)", stripped)
        if not m:
            raise ValueError(
                f"script value {name!r} is not a flat constant; port it as control "
                f"flow instead. Body was:\n{stripped}"
            )
        self._cache[name] = float(m.group(1))
        return self._cache[name]

    def modifier(self, name: str) -> dict[str, float]:
        """Every numeric field of a static modifier, as {key: value}."""
        body = _block(self._mod_src, name)
        if body is None:
            raise KeyError(f"static modifier {name!r} not found in {STATIC_MODIFIER_FILE}")
        out: dict[str, float] = {}
        for line in _strip_comments(body).splitlines():
            m = re.fullmatch(r"\s*(\w+)\s*=\s*(-?[\d.]+)\s*", line)
            if m:
                out[m.group(1)] = float(m.group(2))
        return out

    def law_modifier(self, law: str) -> dict[str, float]:
        """The numeric fields of a law's `modifier = { }` block."""
        body = _block(self._law_src, law)
        if body is None:
            raise KeyError(f"law {law!r} not found in {LAW_FILE}")
        inner = _block(body + "\n", "\tmodifier") or _block(body, "modifier")
        if inner is None:
            # `modifier = {` is indented inside the law body; find it directly.
            m = re.search(r"\n\s*modifier\s*=\s*\{", body)
            if not m:
                return {}
            depth = 0
            i = m.end() - 1
            j = i
            while j < len(body):
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                    if depth == 0:
                        inner = body[i + 1 : j]
                        break
                j += 1
        out: dict[str, float] = {}
        for line in _strip_comments(inner or "").splitlines():
            m = re.fullmatch(r"\s*(\w+)\s*=\s*(-?[\d.]+)\s*", line)
            if m:
                out[m.group(1)] = float(m.group(2))
        return out


K = ModConstants()


# ── phase bands (banking_cycle_is_* in market_triggers.txt) ──────────────────
PANIC, DOWNTURN, STAGNATION, STABLE, EXPANSION, BOOM, FRENZY = (
    "panic",
    "downturn",
    "stagnation",
    "stable",
    "expansion",
    "boom",
    "frenzy",
)
PHASES = [PANIC, DOWNTURN, STAGNATION, STABLE, EXPANSION, BOOM, FRENZY]
PHASE_EDGES = [10, 25, 40, 60, 75, 88]


def phase_of(value: float) -> str:
    for edge, name in zip(PHASE_EDGES, PHASES):
        if value < edge:
            return name
    return FRENZY


# ── the modifiers the cycle reads, pulled from the mod ────────────────────────
PHASE_MODIFIERS = {p: K.modifier(f"financial_cycle_phase_{p}") for p in PHASES if p != STABLE}

# The economic side effects summed for the payoff index (State.payoff). All are
# read from the same modifier blocks the cycle logic reads, so a retune of a
# phase modifier's throughput line changes the payoff without editing this.
PAYOFF_KEYS = (
    "building_group_bg_manufacturing_throughput_add",
    "goods_output_services_mult",
    "state_capitalists_investment_pool_contribution_add",
    "country_risk_premium_add",
    "state_capitalists_investment_pool_efficiency_mult",
    "country_sol_expectations_lower_offset_add",
    "state_tax_waste_add",
    "state_tax_collection_mult",
)
PHASE_MODIFIERS[STABLE] = {}  # stable applies nothing, by design
INERTIA_MODIFIERS = {
    "moderate": K.modifier("bubble_inertia_moderate"),
    "high": K.modifier("bubble_inertia_high"),
    "extreme": K.modifier("bubble_inertia_extreme"),
}
FISCAL_MODIFIER = K.modifier("financial_cycle_government_fiscal_policy_effect")

# The inflation-band family feeds the cycle too: deflation costs momentum, and
# the top two bands add bubble pressure.  te_monetary_apply_inflation_band.
INFLATION_BAND_MODIFIERS = {
    1: K.modifier("te_inflation_band_deflation"),
    2: K.modifier("te_inflation_band_comfort"),
    3: K.modifier("te_inflation_band_elevated"),
    4: K.modifier("te_inflation_band_high"),
    5: K.modifier("te_inflation_band_very_high"),
    6: K.modifier("te_inflation_band_hyper"),
    7: K.modifier("te_mon_dollarised_modifier"),
}

# ── the ten market-economy dashboard tools ────────────────────────────────────
TOOL_MODIFIER_NAMES = {
    "omo": "banking_open_market_ops",
    "moral_suasion": "banking_moral_suasion",
    "buffer": "banking_countercyclical_capital_buffer",
    "margin": "banking_raise_margin_requirements",
    "deposit": "banking_expand_deposit_guarantee",
    "directed": "banking_directed_credit_infrastructure",
    "export_credit": "banking_export_credit_facility",
    "capital_controls": "banking_capital_controls_out",
    "eliq": "banking_emergency_liquidity_program",
    "asset_relief": "banking_asset_relief_program",
}
TOOL_MODIFIERS = {k: K.modifier(v) for k, v in TOOL_MODIFIER_NAMES.items()}
# Point cost is the modifier's own negative country_banking_intervention_max_add.
TOOL_COST = {
    k: -v.get("country_banking_intervention_max_add", 0.0) for k, v in TOOL_MODIFIERS.items()
}

# ── banking_law_base_points_value, restated as a table (it is an if-chain) ────
FIN_LAW_POINTS = {
    "law_unregulated_banking": 1,
    "law_free_mutual_banking": 3,
    "law_universal_banking_light_prudence": 4,
    "law_prudential_narrow_banking": 7,
    "law_directed_credit_development_banks": 5,
    "law_state_owned_banking": 7,
    "law_central_bank_independence": 7,
}
NATIONAL_BANK_POINTS = 1  # law_national_bank adds 1 on top

# te_mon_gold_hot_exit_speed is 2, or 1 for a swap-line recipient in a panic.
# Phase-5 arrangements are out of scope, so the fast branch is the only one.
GOLD_HOT_EXIT_SPEED = 2.0

# ── currency laws, and the modifiers they grant ───────────────────────────────
CURRENCY_LAWS = {
    "commodity": "law_commodity_money",
    "gold": "law_gold_standard",
    "fiat": "law_fiat_currency",
    "digital": "law_digital_currency",
}
CURRENCY_LAW_MODIFIERS = {k: K.law_modifier(v) for k, v in CURRENCY_LAWS.items()}

# The crash event's softening options — events/minor_events.txt,
# minor_events_timelineextended.6. Each is (cycle_add, momentum_add, modifier),
# and the modifier carries the option's real intervention-point cost for a year.
CRASH_SOFTENING_BY_LAW = {
    "law_unregulated_banking": (3, 1, "banking_crash_intervention_suspend_convertibility"),
    "law_free_mutual_banking": (4, 1, "banking_crash_intervention_mutual_clearing"),
    "law_universal_banking_light_prudence": (
        6, 1, "banking_crash_intervention_correspondent_liquidity"),
    "law_prudential_narrow_banking": (10, 2, "banking_crash_intervention_deposit_guarantee"),
    "law_directed_credit_development_banks": (6, 1, "banking_crash_intervention_dev_bank_lending"),
    "law_state_owned_banking": (12, 3, "banking_crash_intervention_nationalize"),
    "law_central_bank_independence": (10, 2, "banking_crash_intervention_open_market"),
}
# Tech-gated options: (year unlocked, cycle_add, momentum_add, modifier, law gate).
CRASH_SOFTENING_TECH = [
    (10, 5, 1, "banking_crash_intervention_discount_window",
     lambda law: law != "law_unregulated_banking"),
    (25, 4, 1, "banking_crash_intervention_swap_lines",
     lambda law: law in ("law_prudential_narrow_banking", "law_state_owned_banking",
                         "law_central_bank_independence")),
    (35, 5, 0, "banking_crash_intervention_capital_controls",
     lambda law: law not in ("law_unregulated_banking", "law_free_mutual_banking")),
    (55, 10, 2, "banking_crash_intervention_keynesian_stimulus",
     lambda law: law in ("law_directed_credit_development_banks", "law_state_owned_banking",
                         "law_central_bank_independence")),
]
CRASH_INTERVENTION_MODIFIERS = {
    name: K.modifier(name)
    for name in (
        [v[2] for v in CRASH_SOFTENING_BY_LAW.values()]
        + [t[3] for t in CRASH_SOFTENING_TECH]
    )
}
CRASH_INTERVENTION_COST = {
    n: -m.get("country_banking_intervention_max_add", 0.0)
    for n, m in CRASH_INTERVENTION_MODIFIERS.items()
}


# ─────────────────────────────────────────────────────────────────────────────
# Proposed retunings, so a recommendation can be measured rather than asserted
# ─────────────────────────────────────────────────────────────────────────────
#
# Each key names one change to the shipped script. `--tune k=v,...` applies them
# on top of the values read from the mod, so the same harness produces the
# before and the after. Nothing here is written back to the mod.

TUNE: dict[str, float | str] = {}

# The retune this study arrived at was WRITTEN INTO THE MOD on 2026-09-22
# (docs/audits/banking_cycle_simulation.md §3, §7), so a plain run now measures
# it. `--tune pre_retune` approximately restores the pre-retune script for an
# A/B: the multiplicative keys undo rounded file values, so it is close rather
# than exact (e.g. the frenzy bubble add reads 20 and x0.35 gives 7.0, but the
# expansion add reads 3 and gives 1.05 against the old 1).
PRE_RETUNE = {
    "below40": "off",       # the crash branch under cycle 40 was missing
    "sev_scale": 1.0,       # crash severity was seeded from 1.0 x bubble
    "phase_bubble": 0.35,   # expansion / boom / frenzy bubble adds were ~1/2.9 of today's
    "tool_bubble": 5.0,     # the cb_* tools' NEGATIVE bubble adds were x5
    "tool_momentum": 3.3,   # the cb_* tools' momentum adds were ~x3.3
    "gap_clamp_loose": 4.0, # the stance gap's LOOSE clamp was -4
    "recovery": 1 / 3,      # downturn / stagnation momentum adds were 1/3
    "climb": -0.5,          # no finance_value_monthly_add in downturn/stagnation
    "growth_bias": -1.0,    # te_mon_mandate_growth_bias was -1.0
    "fiscal_scale": 1 / 13, # the fiscal channel was not annualised (and unclamped)
    "fiscal_clamp": 0,
    "ai_gate": "off",       # flavour / resource AI terms were unconditional
    "ai_directed_off": "off",  # directed credit was held through stable / expansion
}
# Measured but NOT shipped (§3): `crash_mult`, `stance_bubble`, `hyper_edge`,
# `fiat_pull` (the last two contradict the documented fiat design), and
# `ai_eliq_first` (no measurable effect — the lender of last resort is priced
# out by the crash event's own option, §8).


def tuned(key: str, default: float) -> float:
    v = TUNE.get(key)
    return default if v is None else float(v)


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

MODE_NOTHING = "nothing"
MODE_PRICE = "price"
MODE_GROWTH = "growth"
MODE_PEG = "peg"
MODES = [MODE_NOTHING, MODE_PRICE, MODE_GROWTH, MODE_PEG]

MANDATE_PRICE, MANDATE_GROWTH, MANDATE_PEG = 1, 2, 3


@dataclass
class Config:
    currency: str = "fiat"
    mode: str = MODE_NOTHING
    points: int = 0            # the intervention-point budget; 0 means no tools
    fin_law: str = "law_universal_banking_light_prudence"
    national_bank: bool = True
    years: int = 100
    start_year: int = 1836
    pulse_order: str = "cycle_first"  # or "monetary_first"
    growth_feedback: bool = False
    event_channel: bool = False
    no_click_weight: float = 100.0
    excluded_tools: tuple[str, ...] = ()  # dashboard tools the AI never clicks
    simplified: bool = False   # banking_system_simplified: the capital-controls fallback branch

    # exogenous stubs
    gdp0: float = 1.0e7
    growth_mean: float = 2.0
    growth_sd: float = 1.2
    deficit_mean: float = 1.5
    deficit_sd: float = 1.0
    war_start_p: float = 0.0035
    war_end_p: float = 1.0 / 24.0
    world_inflation: float = 1.5
    gold_reserves: float = 0.6

    @property
    def interventions(self) -> bool:
        return self.points > 0

    def label(self) -> str:
        return f"{self.currency}/{self.mode}/{self.points}pt"


# ─────────────────────────────────────────────────────────────────────────────
# Simulation state
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class State:
    # cycle (je_banking.txt immediate)
    finance_cycle_value: float = 50.0
    finance_cycle_momentum: float = 0.0
    bubble_pressure: float = 0.0

    # monetary (te_monetary_init_variables)
    policy_rate: float = 3.0
    policy_rate_target: float = 3.0
    neutral_rate: float = 3.0
    neutral_walk: float = 0.0
    neutral_error: float = 0.0
    stance_gap: float = 0.0
    stance_band: int = 3
    inflation: float = 0.0
    inflation_core: float = 0.0
    inflation_expected: float = 2.0
    inflation_noise: float = 0.0
    inflation_band: int = 2
    inflation_band_applied: int = 0
    hyper_cooldown: int = 0
    dollarised: bool = False
    growth_term: float = 0.0
    commodity_centre: float = 3.0
    world_rate: float = 3.0
    pending_recovery: int | None = None

    # gold (te_monetary_update_gold)
    bank_gold: float = 0.0
    bank_gold_seeded: bool = False
    gold_hot_money: float = 0.0
    gold_flow: float = 0.0
    gold_flow_pct: float = 0.0
    peg_confidence: float = 100.0
    peg_defend_months: int = 0

    # modifiers currently ON the journal entry (applied at the END of last month)
    active_phase: str | None = None
    active_inertia_mult: float = 0.0
    active_inertia_key: str | None = None
    active_fiscal_size: float = 0.0
    tools: set[str] = field(default_factory=set)
    timed: dict[str, int] = field(default_factory=dict)  # name -> months remaining

    # exogenous
    gdp: float = 1.0e7
    growth: float = 2.0
    deficit_pct: float = 1.5
    scaled_debt: float = 0.2
    at_war: bool = False
    basket_index: float = 1.0
    basket_avg: float = 1.0
    basket_seeded: bool = False

    # bookkeeping
    crashes: list[tuple[int, float, float]] = field(default_factory=list)  # month, severity, reset
    phase_months: dict[str, int] = field(default_factory=lambda: {p: 0 for p in PHASES})
    value_series: list[float] = field(default_factory=list)
    bubble_series: list[float] = field(default_factory=list)
    inflation_series: list[float] = field(default_factory=list)
    rate_series: list[float] = field(default_factory=list)
    currency_reforms: int = 0
    months_dollarised: int = 0
    recovery_months: list[int] = field(default_factory=list)
    months_at_floor: int = 0
    months_at_ceiling: int = 0
    tool_months: int = 0
    tool_slot_months: float = 0.0
    tool_usage: dict[str, int] = field(default_factory=lambda: {k: 0 for k in TOOL_MODIFIERS})
    # What the cycle DOES to the economy: month-by-month sums of the modifier
    # fields the phase / tool / band / intervention modifiers carry, so a cell's
    # crash count can be weighed against what it paid for.
    payoff: dict[str, float] = field(default_factory=lambda: {k: 0.0 for k in PAYOFF_KEYS})
    band_months: dict[int, int] = field(default_factory=lambda: {b: 0 for b in range(0, 8)})
    capctl_peace_months: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# Helpers that mirror named script values with branches
# ─────────────────────────────────────────────────────────────────────────────


def era_base(year_index: int) -> float:
    """te_mon_era_base — 3.0, then -0.5 at macroeconomics, -0.5 at globalization.

    Proxied by calendar year: those are late-game techs someone in the world has.
    """
    v = 3.0
    if year_index >= 40:
        v -= 0.5
    if year_index >= 80:
        v -= 0.5
    return v


def bubble_inertia_multiplier(bubble: float) -> float:
    """bubble_inertia_multiplier_script_value (extra_script_values.txt)."""
    if bubble <= 15:
        return 0.0
    if bubble < 50:
        return (bubble - 15) * 0.25 / 35
    return 0.75 + bubble * -0.025 + bubble * bubble * 0.0003


def modifier_sum(state: State, key: str) -> float:
    """`modifier:<key>` as the cycle reads it — every modifier ON the JE now.

    These were all applied at the end of LAST month's pulse, which is the lag
    `banking_cycle_advance_variables` is written against.
    """
    total = 0.0
    if state.active_phase is not None:
        val = PHASE_MODIFIERS[state.active_phase].get(key, 0.0)
        if key == "country_bubble_pressure_monthly_add" and val > 0:
            val *= tuned("phase_bubble", 1.0)
        if (
            key == "country_finance_momentum_monthly_add"
            and state.active_phase in (DOWNTURN, STAGNATION)
        ):
            val *= tuned("recovery", 1.0)
        if (
            key == "country_finance_value_monthly_add"
            and state.active_phase in (DOWNTURN, STAGNATION)
        ):
            val += tuned("climb", 0.0)
        total += val
    if state.active_inertia_key is not None:
        total += INERTIA_MODIFIERS[state.active_inertia_key].get(key, 0.0) * state.active_inertia_mult
    total += FISCAL_MODIFIER.get(key, 0.0) * state.active_fiscal_size
    if state.inflation_band_applied:
        total += INFLATION_BAND_MODIFIERS[state.inflation_band_applied].get(key, 0.0)
    for tool in state.tools:
        val = TOOL_MODIFIERS[tool].get(key, 0.0)
        if key == "country_bubble_pressure_monthly_add" and val < 0:
            val *= tuned("tool_bubble", 1.0)
        # A STANDING momentum add is worth 10x its face value in cycle points:
        # momentum decays x0.9 a month, so a permanent +x converges on x/0.1.
        # The dashboard tools carry +-0.15 to +-0.35 here, i.e. +-1.5 to +-3.5
        # cycle points a month, against the phase modifiers' own +-0.5 to +-2.
        if key == "country_finance_momentum_monthly_add":
            val *= tuned("tool_momentum", 1.0)
        total += val
    for name in state.timed:
        total += CRASH_INTERVENTION_MODIFIERS[name].get(key, 0.0)
    return total


def law_modifier_sum(cfg: Config, key: str) -> float:
    return CURRENCY_LAW_MODIFIERS[cfg.currency].get(key, 0.0)


def intervention_points(cfg: Config, state: State) -> float:
    """`modifier:country_banking_intervention_max_add` — the budget minus tools.

    In game the budget is `banking_law_base_points_value`: 1 / 3 / 4 / 5 / 7 by
    financial-regulation law, plus 1 for a national bank, so a real country holds
    2, 4, 5, 6 or 8. `cfg.points` overrides it so the budget can be swept
    independently of which law happens to grant it.
    """
    spent = sum(TOOL_COST[t] for t in state.tools)
    spent += sum(CRASH_INTERVENTION_COST[n] for n in state.timed)
    return cfg.points - spent


# ── regime predicates (te_monetary_triggers.txt) ──────────────────────────────


def has_dial(cfg: Config, state: State | None = None) -> bool:
    if state is not None and state.dollarised:
        return False
    return cfg.national_bank  # currency law is always one of the four dial regimes


def has_narrow_dial(cfg: Config, state: State | None = None) -> bool:
    return has_dial(cfg, state) and cfg.currency == "commodity"


def is_on_gold(cfg: Config) -> bool:
    return cfg.currency == "gold"  # suspension is an event outcome, out of scope


def is_metallic(cfg: Config) -> bool:
    return cfg.currency in ("gold", "commodity")


def is_cbi(cfg: Config) -> bool:
    return cfg.fin_law == "law_central_bank_independence"


def has_gold_flows(cfg: Config, state: State | None = None) -> bool:
    return is_on_gold(cfg) and has_dial(cfg, state)


# ── the regime rate band (te_mon_target_min / te_mon_target_max) ──────────────


def target_bounds(cfg: Config, state: State, world_rate: float) -> tuple[float, float]:
    # te_mon_target_max
    if is_on_gold(cfg):
        hi = 15.0
    elif has_narrow_dial(cfg, state):
        hi = max(0.0, state.commodity_centre + K.sv("te_mon_commodity_band_margin_up"))
    else:
        hi = 25.0

    # te_mon_target_min
    if state.peg_defend_months > 0 and is_on_gold(cfg):
        lo = min(hi, math.ceil(world_rate + K.sv("te_mon_peg_defend_margin") - 0.05))
    elif has_narrow_dial(cfg, state):
        lo = max(0.0, state.commodity_centre - K.sv("te_mon_commodity_band_margin_down"))
    else:
        lo = law_modifier_sum(cfg, "country_policy_rate_floor_add") * 100
    return lo, hi


# ─────────────────────────────────────────────────────────────────────────────
# The monetary monthly update (te_monetary_effects.txt)
# ─────────────────────────────────────────────────────────────────────────────


def monetary_update(cfg: Config, state: State, rng: random.Random, year_index: int) -> None:
    world_rate = era_base(year_index)
    state.world_rate = world_rate

    # step 0 — the commodity band's whole-point centre, re-rounded when stale
    if abs(state.commodity_centre - world_rate) >= 0.75:
        state.commodity_centre = round(world_rate)

    # steps 2/3 — the dial
    if has_dial(cfg, state):
        monetary_update_target(cfg, state, world_rate)
        monetary_drift_rate(cfg, state)
    else:
        state.policy_rate = world_rate + 1.0

    # step 6 — inflation, then 6c the band and the hyperinflation crisis
    monetary_update_inflation(cfg, state, rng, world_rate)
    update_inflation_band(cfg, state, rng)

    # step 8 — hidden neutral rate, stance gap, band
    monetary_update_stance(cfg, state, rng, world_rate)

    # step 10 — gold flows, for a gold-standard country with a dial
    if has_gold_flows(cfg, state):
        monetary_update_gold(cfg, state, world_rate)


def mandate_for(cfg: Config, state: State) -> int | None:
    if state.dollarised:
        return None
    """Which mandate runs, or None when nobody is steering the dial.

    `te_monetary_update_target`'s formula branch requires the country to be
    delegated, AI, under central bank independence, or without the journal entry.
    A player who never delegates and is not under CBI leaves the target frozen —
    that is what MODE_NOTHING models.
    """
    if cfg.mode == MODE_NOTHING and not is_cbi(cfg):
        return None
    if cfg.mode == MODE_NOTHING:
        # CBI runs the formula anyway, on the default mandate the init seeds.
        mandate = MANDATE_PRICE
    elif cfg.mode == MODE_PRICE:
        mandate = MANDATE_PRICE
    elif cfg.mode == MODE_GROWTH:
        mandate = MANDATE_GROWTH
    else:
        mandate = MANDATE_PEG
    # Peg defence is a gold mandate only; otherwise it falls back to price.
    if mandate == MANDATE_PEG and not is_on_gold(cfg):
        mandate = MANDATE_PRICE
    return mandate


def monetary_update_target(cfg: Config, state: State, world_rate: float) -> None:
    mandate = mandate_for(cfg, state)
    if mandate is None:
        clamp_target(cfg, state, world_rate)
        return

    if mandate == MANDATE_PEG:
        # te_mon_peg_defence_target = world rate + 0.5 x reserve shortfall,
        # with its own tenth-of-a-point hysteresis (ruling Q5).
        limit = bank_gold_limit(cfg, state)
        scaled = min(1.0, max(0.0, state.bank_gold / limit)) if limit > 0 else 0.0
        shortfall = min(2.0, max(0.0, (0.5 - scaled) * 4))
        want = world_rate + 0.5 * shortfall
        diff = state.policy_rate_target - want
        if diff < -0.005 or diff > 0.35:
            state.policy_rate_target = math.ceil((want - 0.005) * 10) / 10
    else:
        # 1 price stability: r* + error + pi_core + 1.0 x (pi_core - anchor) + lean
        anchor = 0.0 if is_metallic(cfg) else 2.0
        work = state.neutral_rate + state.neutral_error + state.inflation_core
        work += (state.inflation_core - anchor) * K.sv("te_mon_mandate_inflation_weight")
        lean = cycle_lean(state)
        work += lean

        if mandate == MANDATE_GROWTH:
            # 2 growth: lean/2 + r* + error + pi_core - 1.0 + 0.5 x max(0, pi-4)
            work2 = lean / 2
            work2 += state.neutral_rate + state.neutral_error + state.inflation_core
            work2 += tuned("growth_bias", K.sv("te_mon_mandate_growth_bias"))
            work2 += (
                max(0.0, state.inflation_core - K.sv("te_mon_mandate_growth_threshold"))
                * K.sv("te_mon_mandate_growth_reaction")
            )
            work = min(work, work2)  # never more hawkish than price stability

        # Hysteresis (§4): move only on a 0.75pp miss, then take a whole point.
        if abs(work - state.policy_rate_target) >= 0.75:
            state.policy_rate_target = round(work)

    clamp_target(cfg, state, world_rate)


def cycle_lean(state: State) -> float:
    """te_mon_cycle_lean."""
    p = phase_of(state.finance_cycle_value)
    lean = {FRENZY: 2.0, BOOM: 1.0, PANIC: -3.0, DOWNTURN: -2.0}.get(p, 0.0)
    if state.bubble_pressure >= K.sv("te_mon_bubble_threshold"):
        lean += 1.0
    return lean


def clamp_target(cfg: Config, state: State, world_rate: float) -> None:
    lo, hi = target_bounds(cfg, state, world_rate)
    state.policy_rate_target = min(hi, max(lo, state.policy_rate_target))


def monetary_drift_rate(cfg: Config, state: State) -> None:
    speed = max(0.1, 1.0 + law_modifier_sum(cfg, "country_policy_rate_drift_speed_mult"))
    step = 0.3333 * speed
    gap = state.policy_rate_target - state.policy_rate
    if gap > step:
        state.policy_rate += step
    elif gap < -step:
        state.policy_rate -= step
    else:
        state.policy_rate = state.policy_rate_target


def monetary_update_inflation(
    cfg: Config, state: State, rng: random.Random, world_rate: float
) -> None:
    # cost-push from the goods basket
    if not state.basket_seeded:
        state.basket_avg = state.basket_index
        state.basket_seeded = True
        cost_push = 0.0
    else:
        cost_push = max(
            -K.sv("te_mon_cost_push_clamp"),
            min(
                K.sv("te_mon_cost_push_clamp"),
                (state.basket_index - state.basket_avg) * K.sv("te_mon_basket_k") * 100,
            ),
        )
        state.basket_avg += (state.basket_index - state.basket_avg) * (1 / 36)

    # the noise walk
    state.inflation_noise *= 0.95
    if has_dial(cfg, state):
        state.inflation_noise += rng.choice([0.1, 0.0, -0.1])
    state.inflation_noise = max(-0.75, min(0.75, state.inflation_noise))

    pressure = pressure_total(cfg, state, world_rate)
    work = (pressure + state.inflation_expected - state.inflation_core) * K.sv("te_mon_core_speed")
    state.inflation_core = max(-10.0, min(100.0, state.inflation_core + work))
    state.inflation = max(-10.0, min(100.0, state.inflation_core + cost_push))

    anchor = 0.0 if is_metallic(cfg) else 2.0
    if is_metallic(cfg):
        state.inflation_expected = 0.0
    else:
        # te_mon_expectation_target: credibility-weighted blend of realised and anchor
        gap_abs = abs(state.inflation - anchor)
        c_own = 0.7 if is_cbi(cfg) else (0.4 if cfg.mode != MODE_NOTHING else 0.25)
        if cfg.fin_law == "law_state_owned_banking":
            c_own = 0.15
        cred = max(0.0, 1 - gap_abs / K.sv("te_mon_deanchor_span")) * c_own
        target = state.inflation * (1 - cred) + anchor * cred
        alpha = 1 / 12 if is_cbi(cfg) else 1 / 24
        state.inflation_expected += (target - state.inflation_expected) * alpha
        state.inflation_expected = max(-10.0, min(100.0, state.inflation_expected))


BAND_EDGE_NAMES = {
    1: "te_mon_band_edge_deflation",
    2: "te_mon_band_edge_elevated",
    3: "te_mon_band_edge_high",
    4: "te_mon_band_edge_very_high",
    5: "te_mon_band_edge_hyper",
}


def update_inflation_band(cfg: Config, state: State, rng: random.Random) -> None:
    """te_monetary_apply_inflation_band (step 6c), with its 0.25pp hysteresis.

    The band is not cosmetic: deflation costs momentum and the top two bands add
    bubble pressure, so it closes a loop from prices back into the cycle. Band 6
    also fires `te_inflation.1`, the currency-reform crisis, on a 24-month
    cooldown — the only scripted exit from a runaway.
    """
    hyst = K.sv("te_mon_band_hysteresis")
    pi = state.inflation
    band = 6
    for b in range(1, 6):
        edge = K.sv(BAND_EDGE_NAMES[b])
        if b == 5:
            edge = tuned("hyper_edge", edge)
        if state.inflation_band_applied != 0:
            edge += -hyst if state.inflation_band >= b + 1 else hyst
        if b == 5 and state.inflation_band >= 6:
            edge = tuned("hyper_edge", K.sv(BAND_EDGE_NAMES[5])) - hyst
        if pi < edge:
            band = b
            break
    state.inflation_band = band
    state.inflation_band_applied = 7 if state.dollarised else band

    if state.hyper_cooldown > 0:
        state.hyper_cooldown -= 1
    if band == 6 and not state.dollarised and state.hyper_cooldown == 0:
        state.hyper_cooldown = int(K.sv("te_mon_hyper_cooldown_months"))
        hyperinflation_crisis(cfg, state, rng)


def hyperinflation_crisis(cfg: Config, state: State, rng: random.Random) -> None:
    """`te_inflation.1`, resolved on its own `ai_chance` weights.

    Not folded into either axis the study varies: currency reform is neither a
    delegation mandate nor a dashboard tool, so every arm resolves it the same
    way — the way the mod's own AI would. Weights with monetisation at zero and
    no war: new currency 8, dollarise 2, ride it out 3.
    """
    reform = 4 + 4  # base 4, +4 because te_monetisation_level is 0 here
    dollarise = 2
    ride = 3
    if state.at_war:
        reform -= 3
        dollarise -= 1
        ride += 4
    roll = rng.random() * (reform + dollarise + ride)
    if roll < reform:
        reset = K.sv("te_mon_currency_reform_reset")
        state.inflation = reset
        state.inflation_core = reset
        state.inflation_expected = reset
        state.currency_reforms += 1
    elif roll < reform + dollarise:
        anchor = 0.0 if is_metallic(cfg) else 2.0
        state.dollarised = True
        state.inflation = anchor
        state.inflation_core = anchor
        state.inflation_expected = anchor


def pressure_total(cfg: Config, state: State, world_rate: float) -> float:
    """te_mon_pressure_total — the standing inflation pressure sum (§9.1)."""
    total = 0.0

    # stance: a tight rate is disinflationary
    total += -K.sv("te_mon_stance_pressure_coeff") * clamped_gap(state)

    # phase
    total += {FRENZY: 1.5, BOOM: 0.8, EXPANSION: 0.3, STAGNATION: -0.3, DOWNTURN: -0.8, PANIC: -1.5}.get(
        phase_of(state.finance_cycle_value), 0.0
    )

    # bubble
    if state.bubble_pressure >= K.sv("te_mon_bubble_threshold"):
        total += K.sv("te_mon_bubble_pressure_term")

    # deficit
    deficit = max(0.0, state.deficit_pct - K.sv("te_mon_deficit_tolerance"))
    deficit *= K.sv("te_mon_deficit_coeff")
    if state.at_war:
        deficit *= 2
    total += deficit

    # QE, while open market operations are running
    if "omo" in state.tools:
        total += K.sv("te_mon_qe_pressure")

    # wage spiral above the high band edge
    if state.inflation >= K.sv("te_mon_band_edge_high"):
        total += 0.0  # country_wage_pressure_add is granted by events; none here

    total += state.inflation_noise

    # regime pull: metal drags core back toward zero. Fiat and digital have no
    # such term in the shipped script, which is why an unsteered fiat dial has no
    # fixed point (finding F4). `--tune fiat_pull=X` adds a proportional one, to
    # measure what a "real balance" pull would be worth.
    if is_metallic(cfg):
        total -= state.inflation_core
    else:
        pull = tuned("fiat_pull", 0.0)
        if pull:
            anchor = 2.0
            total -= pull * max(0.0, state.inflation_core - anchor)

    # gold flow
    total += max(-6.0, min(6.0, state.gold_flow_pct * K.sv("te_mon_gold_flow_pressure_per_pct")))

    # commodity money's specie discipline (§0.6 R7)
    if cfg.currency == "commodity":
        gap = max(-5.0, min(5.0, state.inflation_core - cfg.world_inflation))
        specie = -K.sv("te_mon_commodity_specie_per_pp") * max(
            0.0, gap - K.sv("te_mon_commodity_specie_tolerance")
        )
        total += max(K.sv("te_mon_commodity_specie_clamp"), specie)

    return total


def clamped_gap(state: State) -> float:
    """te_mon_stance_gap_clamped — the bounds the cycle channel reads.

    The bound SATURATES: a country that leaves its dial alone while inflation
    runs sits at the loose bound for ever and takes the maximum loose-money push
    every month (finding F5), which is why the loose side is -2 and the tight
    side 4 (te_mon_stance_gap_clamp_loose / _tight). `--tune gap_clamp_loose=X`
    overrides the loose side's magnitude.
    """
    lo = -tuned("gap_clamp_loose", -K.sv("te_mon_stance_gap_clamp_loose"))
    return max(lo, min(K.sv("te_mon_stance_gap_clamp_tight"), state.stance_gap))


def monetary_update_stance(
    cfg: Config, state: State, rng: random.Random, world_rate: float
) -> None:
    if has_dial(cfg, state):
        state.neutral_walk = state.neutral_walk * 0.95 + rng.choice([0.1, 0.0, -0.1])
        # the bank's estimation error: 1/6 up, 4/6 nothing, 1/6 down
        roll = rng.randrange(6)
        if roll == 0:
            state.neutral_error += 0.1
        elif roll == 5:
            state.neutral_error -= 0.1
    state.neutral_walk = max(-1.0, min(1.0, state.neutral_walk))

    state.neutral_rate = world_rate + state.growth_term + state.neutral_walk
    state.neutral_rate = max(1.0, min(6.0, state.neutral_rate))

    bound = max(0.1, 1.5 + law_grant(cfg, "country_bank_forecast_error_add") * 100)
    state.neutral_error = max(-bound, min(bound, state.neutral_error))

    if has_dial(cfg, state):
        gap = state.policy_rate - state.inflation - state.neutral_rate
        state.stance_gap = max(-10.0, min(10.0, gap))
        read = state.stance_gap - state.neutral_error
        if read <= -2:
            state.stance_band = 1
        elif read <= -0.75:
            state.stance_band = 2
        elif read < 0.75:
            state.stance_band = 3
        elif read < 2:
            state.stance_band = 4
        else:
            state.stance_band = 5
    else:
        state.stance_gap = 0.0
        state.stance_band = 3


def law_grant(cfg: Config, key: str) -> float:
    """A regime-rule modifier granted by the currency law or the financial law."""
    total = CURRENCY_LAW_MODIFIERS[cfg.currency].get(key, 0.0)
    if is_cbi(cfg):
        total += K.law_modifier("law_central_bank_independence").get(key, 0.0)
    return total


def bank_gold_limit(cfg: Config, state: State) -> float:
    return max(1.0, state.gdp * K.sv("te_mon_bank_gold_limit_share"))


def monetary_update_gold(cfg: Config, state: State, world_rate: float) -> None:
    limit = bank_gold_limit(cfg, state)
    if not state.bank_gold_seeded:
        state.bank_gold = min(1.0, max(0.5, cfg.gold_reserves)) * limit
        state.bank_gold_seeded = True

    damp = K.sv("te_mon_controls_damp_value") if "capital_controls" in state.tools else 1.0
    clamp = K.sv("te_mon_gold_gap_clamp")
    gap = max(-clamp, min(clamp, state.policy_rate - world_rate)) * damp
    flow_unit = state.gdp * K.sv("te_mon_gold_flow_per_pp")

    scaled = min(1.0, max(0.0, state.bank_gold / limit)) if limit > 0 else 0.0
    under_pressure = scaled < K.sv("te_mon_peg_reserve_floor")

    flow = 0.0
    if gap > 0:
        flow = min(flow_unit * gap, max(0.0, limit - state.bank_gold))
        state.gold_hot_money += flow
    elif gap <= 0 and not under_pressure:
        work = -gap
        if state.gold_hot_money > 0:
            work = max(work, K.sv("te_mon_gold_hot_exit_gap_floor"))
            work *= GOLD_HOT_EXIT_SPEED
        work *= flow_unit
        if state.gold_hot_money > 0:
            work = min(work, state.gold_hot_money)
        work = min(work, state.bank_gold)
        if state.gold_hot_money > 0:
            state.gold_hot_money = max(0.0, state.gold_hot_money - work)
        flow = -work

    state.bank_gold = max(0.0, state.bank_gold + flow)
    state.gold_flow = flow
    state.gold_flow_pct = flow / max(1.0, state.gdp) * 1200

    # peg confidence
    per_pp = K.sv("te_mon_peg_confidence_per_pp")
    if under_pressure:
        if state.gold_hot_money > 0 and gap <= 0:
            move = (
                -max(-gap, K.sv("te_mon_gold_hot_exit_gap_floor"))
                * GOLD_HOT_EXIT_SPEED
                * per_pp
            )
        elif gap < 0:
            move = gap * per_pp
        else:
            move = 2.0
        if phase_of(state.finance_cycle_value) in (PANIC, DOWNTURN):
            move -= 2
        if state.scaled_debt >= 0.5:
            move -= 2
        state.peg_confidence += move
    elif gap >= 0 and state.gold_hot_money <= 0:
        state.peg_confidence += 1
    state.peg_confidence = max(0.0, min(100.0, state.peg_confidence))

    if state.peg_defend_months > 0:
        state.peg_defend_months -= 1


# ─────────────────────────────────────────────────────────────────────────────
# The banking cycle monthly pulse (banking_cycle_effects.txt)
# ─────────────────────────────────────────────────────────────────────────────


def cycle_pulse(cfg: Config, state: State, rng: random.Random, month: int) -> None:
    # 1. fiscal policy modifier — remove + re-add. Its NEW size is not visible
    #    to step 2 in the same block, so step 2 reads last month's. We therefore
    #    advance first and stage the new size for next month.
    next_fiscal = fiscal_effect_size(cfg, state)

    # 2. advance the variables
    advance_variables(cfg, state, rng)

    # 3. crash check
    crashed = check_and_execute_crash(cfg, state, rng, month)

    # (3b history sampling — not modelled)

    # 4. phase + bubble-inertia modifiers, applied for NEXT month
    apply_phase_modifiers(cfg, state)
    state.active_fiscal_size = next_fiscal

    for name in list(state.timed):
        state.timed[name] -= 1
        if state.timed[name] <= 0:
            del state.timed[name]

    # the dashboard tools: the AI's ai_chance blocks, once a month
    if cfg.points > 0:
        consider_tools(cfg, state, rng)
    prune_overdrawn_tools(cfg, state)

    return crashed


def fiscal_effect_size(cfg: Config, state: State) -> float:
    """financial_cycle_government_fiscal_policy_effect_size.

    Since 2026-09-22 the script annualises the WEEKLY (total_expenses - income)
    by te_mon_deficit_annualise_factor before dividing by the annual `gdp`, then
    multiplies by 25 and clamps to +-1: 0.25 cycle points a month per 1% of GDP
    of deficit. Before that it skipped the annualisation, i.e. was 1/52 of its
    own comment's claim (F8); `--tune fiscal_scale=X` multiplies the size and
    `fiscal_clamp=X` overrides the bound (0 = none).
    """
    annual_deficit_share = state.deficit_pct / 100.0
    size = annual_deficit_share * 25.0 * tuned("fiscal_scale", 1.0)
    clamp = tuned("fiscal_clamp", 1.0)
    if clamp:
        size = max(-clamp, min(clamp, size))
    return size


def advance_variables(cfg: Config, state: State, rng: random.Random) -> None:
    state.finance_cycle_momentum *= 0.9
    state.finance_cycle_momentum += modifier_sum(state, "country_finance_momentum_monthly_add")
    state.bubble_pressure += modifier_sum(state, "country_bubble_pressure_monthly_add")
    state.finance_cycle_value += modifier_sum(state, "country_finance_value_monthly_add")

    # the monetary stance channel (§16.3)
    gap = clamped_gap(state)
    state.finance_cycle_momentum += gap * -tuned("stance_momentum", 0.125)
    state.bubble_pressure += gap * -tuned("stance_bubble", 0.75)

    # the random mean-reversion nudge.  `value =` in the modifier block REPLACES
    # the literal 25, so the weights are (v-50)/5 and (50-v)/5 against a 50.
    v = state.finance_cycle_value
    w_down = max(0.0, (v - 50) / 5)
    w_up = max(0.0, (50 - v) / 5)
    total = w_down + 50.0 + w_up
    roll = rng.random() * total
    nudge_mult = 1.0 + law_modifier_sum(cfg, "country_banking_random_momentum_mult")
    if roll < w_down:
        state.finance_cycle_momentum += -1.0 * nudge_mult
    elif roll < w_down + 50.0:
        pass
    else:
        state.finance_cycle_momentum += 1.0 * nudge_mult

    state.finance_cycle_value += state.finance_cycle_momentum
    state.finance_cycle_value = max(0.0, min(100.0, state.finance_cycle_value))
    state.bubble_pressure = max(0.0, min(100.0, state.bubble_pressure))


def crash_weight(cfg: Config, state: State) -> float:
    """The `0 = { modifier = {...} }` entry's weight in the crash random_list."""
    cm = tuned("crash_mult", 1.0)
    w = state.bubble_pressure
    v = state.finance_cycle_value
    if v >= 88:
        w = (w - 15) * 0.35 * cm
    elif v >= 75:
        w = (w - 25) * 0.15 * cm
    elif v >= 60:
        w = (w - 50) * 0.05 * cm
    elif v >= 40:
        w = (w - 75) * 0.02 * cm
    elif TUNE.get("below40") != "off":
        # Added 2026-09-22 (F4). Before it the weight fell through as raw
        # bubble pressure below cycle 40; `--tune below40=off` restores that.
        w = (w - 90) * 0.01 * cm
    w = max(0.0, w)
    mult = max(0.0, 1.0 + modifier_sum(state, "country_banking_crash_chance_mult"))
    return w * mult


def check_and_execute_crash(cfg: Config, state: State, rng: random.Random, month: int) -> bool:
    w = crash_weight(cfg, state)
    p = w / (w + 100.0)
    if rng.random() >= p:
        return False

    severity = state.bubble_pressure * tuned("sev_scale", K.sv("banking_crash_severity_scale_value"))
    r = rng.random()
    if r < 0.10:
        severity *= 0.5
    elif r < 0.30:
        severity *= 0.75
    elif r < 0.70:
        pass
    elif r < 0.90:
        severity *= 1.5
    else:
        severity *= 2.0
    severity = min(100.0, severity)

    apply_crash(cfg, state, severity, month)
    return True


def apply_crash(cfg: Config, state: State, severity: float, month: int) -> None:
    """apply_banking_crash_origin_effects, plus the chosen crash-event option."""
    e1 = tuned("tier1", 80)
    e2 = tuned("tier2", 60)
    e3 = tuned("tier3", 40)
    e4 = tuned("tier4", 20)
    if severity >= e1:
        value, momentum = 5.0, -5.0
    elif severity >= e2:
        value, momentum = 10.0, -4.0
    elif severity >= e3:
        value, momentum = 20.0, -3.0
    elif severity >= e4:
        value, momentum = 30.0, -2.0
    else:
        value, momentum = 40.0, -1.0
    state.finance_cycle_value = value
    state.finance_cycle_momentum = momentum
    state.bubble_pressure = 0.0

    state.crashes.append((month, severity, value))
    state.pending_recovery = month

    choice = best_softening(cfg, state, month)
    if choice is not None:
        add_v, add_m, name = choice
        state.finance_cycle_value += add_v
        state.finance_cycle_momentum += add_m
        state.timed[name] = 12  # `days = 365` on the option


def best_softening(cfg: Config, state: State, month: int) -> tuple[float, float, str] | None:
    """The strongest crash-event softening option the point budget affords.

    Every softening option leaves a `banking_crash_intervention_*` modifier on the
    country for a year, and every one of those costs intervention points — so a
    country with no points left takes the bare option, which is what a 0-point
    budget models throughout.
    """
    year = month // 12
    options = []
    law_opt = CRASH_SOFTENING_BY_LAW.get(cfg.fin_law)
    if law_opt:
        options.append(law_opt)
    for unlock_year, cyc, mom, name, gate in CRASH_SOFTENING_TECH:
        if year >= unlock_year and gate(cfg.fin_law):
            options.append((cyc, mom, name))
    budget = intervention_points(cfg, state)
    affordable = [o for o in options if CRASH_INTERVENTION_COST[o[2]] <= budget]
    if not affordable:
        return None
    return max(affordable, key=lambda o: o[0])


def apply_phase_modifiers(cfg: Config, state: State) -> None:
    state.active_phase = phase_of(state.finance_cycle_value)
    b = state.bubble_pressure
    if b >= 65:
        state.active_inertia_key = "extreme"
    elif b >= 35:
        state.active_inertia_key = "high"
    elif b > 0.5:
        state.active_inertia_key = "moderate"
    else:
        state.active_inertia_key = None
    state.active_inertia_mult = bubble_inertia_multiplier(b) if state.active_inertia_key else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# The dashboard tools, driven by the buttons' own ai_chance blocks
# ─────────────────────────────────────────────────────────────────────────────


def tool_scores(cfg: Config, state: State) -> dict[str, float]:
    """The `ai_chance` blocks from timeline_extended_scripted_buttons.txt."""
    p = phase_of(state.finance_cycle_value)
    m = state.finance_cycle_momentum
    pts = intervention_points(cfg, state)
    low, med, high = pts <= 2, 3 <= pts <= 5, pts >= 6
    risk_falling = m <= -3
    risk_rising = m >= 3
    bubble_high = state.finance_cycle_value >= 90 or (
        state.finance_cycle_value >= 75 and m >= 3
    )
    recession = p in (PANIC, DOWNTURN)
    fiscal_high = state.scaled_debt > 0.6
    fiscal_low = cfg.gold_reserves < 0.01
    s: dict[str, float] = {}

    # The law-flavour and points-budget terms only count once a core
    # (cycle-state) term is positive — the banking_ai_core_cb_* gates in
    # banking_policy_triggers.txt (2026-09-22, finding F10). Before that they
    # were unconditional adds on a base of 0, so a tool with no cycle reason at
    # all still scored 5-25 in the stable phase and got clicked; `--tune
    # ai_gate=off` restores that. `flavour()` is every gated term; `core` is
    # what precedes it.
    gate = TUNE.get("ai_gate") != "off"

    def flavour(core: float, extra: float) -> float:
        return extra if (core > 0 or not gate) else 0.0

    # cb_open_market_ops
    v = 0.0
    v += 70 if p == PANIC else 0
    v += 45 if p == DOWNTURN else 0
    v += 25 if p == STAGNATION else 0
    v += 15 if risk_falling else 0
    v += 40 if state.inflation < K.sv("te_mon_band_edge_deflation") else 0
    v += flavour(v, (15 if is_cbi(cfg) else 0) + (10 if med else 0) + (5 if low else 0))
    v -= 40 if p == FRENZY else 0
    v -= 30 if bubble_high else 0
    v -= 35 if state.inflation >= K.sv("te_mon_band_edge_elevated") else 0
    v -= 15 if fiscal_high else 0
    s["omo"] = v

    # cb_countercyclical_buffer
    v = 0.0
    v += 10 if p == EXPANSION else 0
    v += 30 if p == BOOM else 0
    v += 35 if p == FRENZY else 0
    v += 15 if risk_rising else 0
    v += flavour(v, (15 if cfg.fin_law == "law_prudential_narrow_banking" else 0)
                 + (10 if cfg.fin_law == "law_universal_banking_light_prudence" else 0)
                 + (5 if cfg.fin_law == "law_free_mutual_banking" else 0)
                 + (10 if low else 0))
    v -= 60 if recession else 0
    s["buffer"] = v

    # `ai_eliq_first=on`: in a panic, while the lender of last resort is
    # affordable and not yet running, the cheaper panic tools stand aside so the
    # budget is not spent before the strongest tool can be bought (F12).
    eliq_room = (
        TUNE.get("ai_eliq_first") == "on" and p == PANIC and "eliq" not in state.tools
        and pts >= TOOL_COST["eliq"]
    )

    # cb_expand_deposit_guarantee
    v = 0.0
    v += 70 if p == PANIC else 0
    v += 25 if p == DOWNTURN else 0
    v -= 50 if eliq_room else 0
    v += flavour(v, (10 if "eliq" not in state.tools else 0)
                 + (15 if cfg.fin_law == "law_prudential_narrow_banking" else 0)
                 + (10 if is_cbi(cfg) else 0))
    v -= 30 if p == FRENZY else 0
    v -= 10 if low else 0
    s["deposit"] = v

    # cb_directed_credit_infrastructure
    v = 0.0
    v += 40 if p == DOWNTURN else 0
    v += 30 if p == STAGNATION else 0
    v += 15 if (p == STABLE and risk_falling) else 0
    v += flavour(v, (25 if cfg.fin_law == "law_directed_credit_development_banks" else 0)
                 + (10 if "eliq" in state.tools else 0) + (10 if med else 0))
    v -= 35 if p == FRENZY else 0
    v -= 30 if p == PANIC else 0
    s["directed"] = v

    # cb_emergency_liquidity_program
    v = 0.0
    v += 85 if p == PANIC else 0
    v += 35 if (p == DOWNTURN and m <= -4) else 0
    v += flavour(v, (10 if is_cbi(cfg) else 0)
                 + (10 if cfg.fin_law == "law_directed_credit_development_banks" else 0)
                 + (10 if low else 0))
    v -= 60 if p == EXPANSION else 0
    v -= 65 if p == BOOM else 0
    v -= 70 if p == FRENZY else 0
    s["eliq"] = v

    # cb_moral_suasion
    v = 0.0
    v += 5 if p == EXPANSION else 0
    v += 30 if risk_rising else 0
    v += flavour(v, 20 if low else 0)
    v -= 30 if p == PANIC else 0
    v -= 25 if p == FRENZY else 0
    v -= 20 if p == DOWNTURN else 0
    s["moral_suasion"] = v

    # cb_raise_margin_requirements
    v = 0.0
    v += 10 if p == BOOM else 0
    v += 15 if p == FRENZY else 0
    v += 35 if risk_rising else 0
    v += flavour(v, (15 if cfg.fin_law == "law_prudential_narrow_banking" else 0)
                 + (10 if cfg.fin_law == "law_universal_banking_light_prudence" else 0)
                 + (5 if cfg.fin_law == "law_free_mutual_banking" else 0)
                 + (10 if low else 0))
    v -= 60 if recession else 0
    s["margin"] = v

    # cb_capital_controls_outflow. Under the full system (the default game rule)
    # the core term is the external-crisis rule, which needs a currency in
    # flight, a draining vault or a peg losing confidence — with FX at par and no
    # peg crisis modelled that is never true, so the core is 0 and only the
    # flavour / resource terms are left. `--simplified` runs the game rule's
    # fallback branch, the pre-phase-1 cycle rule (panic 60 / downturn 35).
    v = 0.0
    if cfg.simplified:
        v += 60 if p == PANIC else 0
        v += 35 if p == DOWNTURN else 0
        v += 15 if risk_falling else 0
    v += flavour(v, (15 if cfg.fin_law == "law_prudential_narrow_banking" else 0)
                 + (10 if cfg.fin_law == "law_directed_credit_development_banks" else 0)
                 + (10 if med else 0) + (5 if low else 0))
    v -= 40 if p == FRENZY else 0
    v -= 20 if bubble_high else 0
    s["capital_controls"] = v

    # cb_export_credit_facility
    v = 0.0
    v += 60 if p == PANIC else 0
    v += 35 if p == DOWNTURN else 0
    v += 25 if p == STAGNATION else 0
    v += 15 if risk_falling else 0
    v -= 50 if eliq_room else 0
    v += flavour(v, (15 if cfg.fin_law == "law_directed_credit_development_banks" else 0)
                 + (10 if med else 0) + (5 if low else 0))
    v -= 40 if p == FRENZY else 0
    v -= 20 if bubble_high else 0
    v -= 30 if state.stance_band >= 4 else 0
    v -= 15 if fiscal_high else 0
    s["export_credit"] = v

    # cb_asset_relief_program
    v = 0.0
    v += 70 if p == PANIC else 0
    v += 40 if p == DOWNTURN else 0
    v += 25 if p == STAGNATION else 0
    v -= 50 if eliq_room else 0
    v += flavour(v, (10 if fiscal_low else 0) + (10 if fiscal_high else 0)
                 + (10 if high else 0))
    v -= 30 if p == BOOM else 0
    v -= 50 if p == FRENZY else 0
    s["asset_relief"] = v

    return s


def tool_possible(cfg: Config, state: State, tool: str) -> bool:
    """`banking_possible_cb_*` — point cost plus the regime / law gates."""
    if tool in state.tools:
        return False
    if intervention_points(cfg, state) < TOOL_COST[tool]:
        return False
    if tool == "omo":
        # needs unbacked money (fiat / digital) AND the rate at its floor
        if not CURRENCY_LAW_MODIFIERS[cfg.currency].get("country_can_create_unbacked_money_bool"):
            return False
        lo, _ = target_bounds(cfg, state, state.world_rate)
        if state.policy_rate > lo + 0.01:
            return False
    return True


def disable_scores(cfg: Config, state: State) -> dict[str, float]:
    """The `cb_disable_*` ai_chance blocks — the AI's path back off a tool.

    These compete in the same pool as the enable buttons, which is what keeps the
    AI from parking a permanent prudential stack on the journal entry.
    """
    p = phase_of(state.finance_cycle_value)
    m = state.finance_cycle_momentum
    risk_rising = m >= 3
    risk_falling = m <= -3
    bubble_high = state.finance_cycle_value >= 90 or (
        state.finance_cycle_value >= 75 and m >= 3
    )
    recession = p in (PANIC, DOWNTURN)
    s: dict[str, float] = {}

    v = 0.0
    v += 10 if p == EXPANSION else 0
    v += 25 if p == BOOM else 0
    v += 55 if p == FRENZY else 0
    v += 30 if bubble_high else 0
    v += 35 if state.stance_band >= 4 else 0
    v += 40 if state.inflation >= K.sv("te_mon_band_edge_elevated") else 0
    s["omo"] = v

    v = 0.0
    v += 75 if recession else 0
    v += 55 if p == DOWNTURN else 0
    v += 45 if p == PANIC else 0
    v += 35 if p == STAGNATION else 0
    v += 15 if (p == STABLE and not risk_rising) else 0
    s["buffer"] = v

    v = 0.0
    v += 15 if p == STABLE else 0
    v += 30 if p == EXPANSION else 0
    v += 45 if p == BOOM else 0
    v += 55 if p == FRENZY else 0
    v += 20 if ("eliq" in state.tools and p != PANIC) else 0
    s["deposit"] = v

    v = 0.0
    v += 35 if p == PANIC else 0
    v += 25 if p == DOWNTURN else 0
    v += 30 if p == FRENZY else 0
    v += 20 if (p == STABLE and not risk_rising) else 0
    v += 15 if p == BOOM else 0
    s["moral_suasion"] = v

    v = 0.0
    v += 75 if recession else 0
    v += 55 if p == DOWNTURN else 0
    v += 40 if p == PANIC else 0
    v += 30 if p == STAGNATION else 0
    v += 20 if (p == STABLE and not risk_rising) else 0
    s["margin"] = v

    v = 0.0
    v += 45 if p == PANIC else 0
    if TUNE.get("ai_directed_off") != "off":
        # lift it once the recovery it was bought for has arrived (F11,
        # 2026-09-22); `--tune ai_directed_off=off` restores the old weights
        v += 20 if (p == STABLE and not risk_falling) else 0
        v += 30 if p == EXPANSION else 0
    else:
        v += 10 if p == EXPANSION else 0
    v += 35 if p == BOOM else 0
    v += 55 if p == FRENZY else 0
    v += 20 if "eliq" in state.tools else 0
    s["directed"] = v

    v = 0.0
    v += 15 if p == STABLE else 0
    v += 15 if p == EXPANSION else 0
    v += 35 if p == BOOM else 0
    v += 55 if p == FRENZY else 0
    v += 20 if bubble_high else 0
    s["export_credit"] = v

    if cfg.simplified:
        v = 0.0
        v += 20 if p == STABLE else 0
        v += 35 if p == EXPANSION else 0
        v += 45 if p == BOOM else 0
        v += 55 if p == FRENZY else 0
        v += 15 if (state.scaled_debt <= 0.6 and p != PANIC) else 0
    else:
        # With FX at par nothing is ever in external crisis, so the +40 "no
        # crisis, take them off" term always fires, plus +10 per peacetime year
        # held (te_mon_controls_fatigue_steps, capped at 5).
        v = 40.0 + 10 * min(5, state.capctl_peace_months // 12)
        v += 10 if p == BOOM else 0
        v += 20 if p == FRENZY else 0
    s["capital_controls"] = v

    v = 0.0
    v += 25 if p == STABLE else 0
    v += 45 if p == EXPANSION else 0
    v += 60 if p == BOOM else 0
    v += 70 if p == FRENZY else 0
    v += 20 if (m > -4 and p != PANIC) else 0
    s["eliq"] = v

    v = 0.0
    v += 20 if p == STABLE else 0
    v += 30 if p == EXPANSION else 0
    v += 45 if p == BOOM else 0
    v += 60 if p == FRENZY else 0
    v += 15 if cfg.gold_reserves < 0.01 else 0
    s["asset_relief"] = v

    return s


def consider_tools(cfg: Config, state: State, rng: random.Random) -> None:
    """One button click a month at most, weighted by `ai_chance`.

    The engine offers every `visible` + `possible` scripted button on the entry
    and weights them by `ai_chance`; enable and disable buttons for the same tool
    are separate buttons in the same pool. `cfg.no_click_weight` stands in for the
    engine's own click cadence, which script does not state — it is the largest
    single assumption on the intervention arms. `--no-click-weight` varies it.
    """
    pool: list[tuple[str, str, float]] = []
    for tool, v in tool_scores(cfg, state).items():
        if tool in cfg.excluded_tools:
            continue
        if v > 0 and tool_possible(cfg, state, tool):
            pool.append(("on", tool, v))
    for tool, v in disable_scores(cfg, state).items():
        if v > 0 and tool in state.tools:
            pool.append(("off", tool, v))
    if not pool:
        return
    total = sum(v for _, _, v in pool) + cfg.no_click_weight
    roll = rng.random() * total
    acc = 0.0
    for action, tool, v in pool:
        acc += v
        if roll < acc:
            if action == "on":
                state.tools.add(tool)
                state.tool_usage[tool] += 1
            else:
                state.tools.discard(tool)
            return


def prune_overdrawn_tools(cfg: Config, state: State) -> None:
    """banking_crash_check_overdrawn_interventions, for the dashboard tools."""
    order = [
        "capital_controls",
        "eliq",
        "asset_relief",
        "deposit",
        "omo",
        "directed",
        "export_credit",
        "buffer",
        "margin",
        "moral_suasion",
    ]
    if intervention_points(cfg, state) < 0:
        # Family interventions are shed first (the timed crash modifiers), then
        # the per-law base options — banking_crash_check_overdrawn_interventions.
        for name in ("banking_crash_intervention_capital_controls",
                     "banking_crash_intervention_swap_lines",
                     "banking_crash_intervention_discount_window",
                     "banking_crash_intervention_keynesian_stimulus"):
            if name in state.timed:
                del state.timed[name]
                return
        for name in list(state.timed):
            del state.timed[name]
            return
        for tool in order:
            if tool in state.tools:
                state.tools.discard(tool)
                break


# ─────────────────────────────────────────────────────────────────────────────
# Exogenous game state
# ─────────────────────────────────────────────────────────────────────────────


def advance_exogenous(cfg: Config, state: State, rng: random.Random, month: int) -> None:
    # war, as a two-state Markov chain
    if state.at_war:
        if rng.random() < cfg.war_end_p:
            state.at_war = False
    elif rng.random() < cfg.war_start_p:
        state.at_war = True

    # deficit as % of GDP, AR(1)
    target = cfg.deficit_mean * (3.0 if state.at_war else 1.0)
    state.deficit_pct += (target - state.deficit_pct) * 0.08
    state.deficit_pct += rng.gauss(0, cfg.deficit_sd * 0.25)
    state.deficit_pct = max(-4.0, min(20.0, state.deficit_pct))

    # debt integrates the deficit
    state.scaled_debt += state.deficit_pct / 100.0 / 12.0 * 2.0
    state.scaled_debt = max(0.0, min(1.5, state.scaled_debt))

    # the yearly GDP-growth snapshot -> te_mon_growth_term
    if month % 12 == 0:
        drift = 0.0
        if cfg.growth_feedback:
            drift = (state.finance_cycle_value - 50) / 50.0 * 1.5
        state.growth += (cfg.growth_mean + drift - state.growth) * 0.4
        state.growth += rng.gauss(0, cfg.growth_sd)
        state.growth_term = max(-1.5, min(1.5, 0.25 * (state.growth - 2.0)))
    state.gdp *= (1 + state.growth / 100.0) ** (1 / 12)

    # goods prices, an AR(1) log walk feeding cost-push
    state.basket_index *= math.exp(rng.gauss(0, 0.012 / math.sqrt(12)))

    # the optional aggregate stand-in for banking_cycle_events.txt
    if cfg.event_channel and rng.random() < 1 / 18.0:
        state.bubble_pressure = max(0.0, min(100.0, state.bubble_pressure + rng.gauss(2, 6)))
        state.finance_cycle_momentum += rng.gauss(0, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# A run
# ─────────────────────────────────────────────────────────────────────────────


def run_once(cfg: Config, seed: int) -> State:
    rng = random.Random(seed)
    state = State(gdp=cfg.gdp0, growth=cfg.growth_mean, deficit_pct=cfg.deficit_mean)
    state.policy_rate = era_base(0)
    state.policy_rate_target = round(era_base(0))
    state.commodity_centre = round(era_base(0))
    state.inflation_expected = 0.0 if is_metallic(cfg) else 2.0

    months = cfg.years * 12
    for month in range(months):
        year_index = month // 12
        advance_exogenous(cfg, state, rng, month)

        if cfg.pulse_order == "monetary_first":
            monetary_update(cfg, state, rng, year_index)
            cycle_pulse(cfg, state, rng, month)
        else:
            cycle_pulse(cfg, state, rng, month)
            monetary_update(cfg, state, rng, year_index)

        if state.pending_recovery is not None and state.finance_cycle_value >= 40:
            state.recovery_months.append(month - state.pending_recovery)
            state.pending_recovery = None
        state.phase_months[phase_of(state.finance_cycle_value)] += 1
        state.value_series.append(state.finance_cycle_value)
        state.bubble_series.append(state.bubble_pressure)
        state.inflation_series.append(state.inflation)
        state.rate_series.append(state.policy_rate)
        if state.tools:
            state.tool_months += 1
        state.tool_slot_months += len(state.tools)
        for key in PAYOFF_KEYS:
            state.payoff[key] += modifier_sum(state, key)
        state.band_months[state.inflation_band_applied] += 1
        if "capital_controls" in state.tools and not state.at_war:
            state.capctl_peace_months += 1
        elif "capital_controls" not in state.tools:
            state.capctl_peace_months = max(0, state.capctl_peace_months - 3)
        if state.dollarised:
            state.months_dollarised += 1
        lo, hi = target_bounds(cfg, state, state.world_rate)
        if has_dial(cfg, state):
            if state.policy_rate <= lo + 0.01:
                state.months_at_floor += 1
            if state.policy_rate >= hi - 0.01:
                state.months_at_ceiling += 1

    return state


def summarise(cfg: Config, states: list[State]) -> dict:
    months = cfg.years * 12
    per_century = [len(s.crashes) / cfg.years * 100 for s in states]
    severities = [sev for s in states for _, sev, _ in s.crashes]
    resets = [r for s in states for _, _, r in s.crashes]
    gaps: list[float] = []
    for s in states:
        ms = [m for m, _, _ in s.crashes]
        gaps += [(b - a) / 12.0 for a, b in zip(ms, ms[1:])]
    occupancy = {
        p: statistics.mean(s.phase_months[p] / months * 100 for s in states) for p in PHASES
    }
    recession_share = occupancy[PANIC] + occupancy[DOWNTURN]

    def flat(attr: str) -> list[float]:
        return [x for s in states for x in getattr(s, attr)]

    infl = flat("inflation_series")
    bubble = flat("bubble_series")
    rate = flat("rate_series")

    # longest run below the stable band, a proxy for depression length
    worst = []
    for s in states:
        run = best = 0
        for v in s.value_series:
            run = run + 1 if v < 40 else 0
            best = max(best, run)
        worst.append(best)

    return {
        "label": cfg.label(),
        "currency": cfg.currency,
        "mode": cfg.mode,
        "points": cfg.points,
        "crashes_per_century_mean": statistics.mean(per_century),
        "crashes_per_century_p10": percentile(per_century, 10),
        "crashes_per_century_p90": percentile(per_century, 90),
        "years_between_crashes_median": statistics.median(gaps) if gaps else float("nan"),
        "crash_severity_mean": statistics.mean(severities) if severities else 0.0,
        "crash_severity_p90": percentile(severities, 90) if severities else 0.0,
        # What the crash actually DID: the cycle value it reset to. 5 and 10 are
        # the panic band, 20 is downturn, 30 stagnation, 40 the bottom of stable.
        "depression_share": (
            sum(1 for r in resets if r <= 10) / len(resets) if resets else 0.0
        ),
        "mild_crash_share": (
            sum(1 for r in resets if r >= 30) / len(resets) if resets else 0.0
        ),
        "reset_mean": statistics.mean(resets) if resets else float("nan"),
        "phase_occupancy": occupancy,
        "recession_share": recession_share,
        "frenzy_share": occupancy[FRENZY],
        "recovery_months_median": (
            statistics.median([m for s in states for m in s.recovery_months])
            if any(s.recovery_months for s in states)
            else float("nan")
        ),
        "longest_slump_months_median": statistics.median(worst),
        "longest_slump_months_p90": percentile(worst, 90),
        "cycle_value_mean": statistics.mean(flat("value_series")),
        "cycle_value_sd": statistics.pstdev(flat("value_series")),
        "bubble_mean": statistics.mean(bubble),
        "bubble_p90": percentile(bubble, 90),
        "inflation_mean": statistics.mean(infl),
        "inflation_sd": statistics.pstdev(infl),
        "inflation_outside_band": sum(1 for x in infl if x < -1 or x > 3) / len(infl) * 100,
        "policy_rate_mean": statistics.mean(rate),
        "months_at_floor_pct": statistics.mean(s.months_at_floor / months * 100 for s in states),
        "months_at_ceiling_pct": statistics.mean(
            s.months_at_ceiling / months * 100 for s in states
        ),
        "tool_months_pct": statistics.mean(s.tool_months / months * 100 for s in states),
        "tool_slots_mean": statistics.mean(s.tool_slot_months / months for s in states),
        "currency_reforms_per_century": statistics.mean(
            s.currency_reforms / cfg.years * 100 for s in states
        ),
        "dollarised_pct": statistics.mean(s.months_dollarised / months * 100 for s in states),
        "tool_usage": {
            t: statistics.mean(s.tool_usage[t] for s in states) for t in TOOL_MODIFIERS
        },
        # Time-weighted means of the economic modifier fields, i.e. what the
        # cycle did to the economy on average over the century.
        "payoff": {
            k: statistics.mean(s.payoff[k] / months for s in states) for k in PAYOFF_KEYS
        },
        "band_occupancy": {
            b: statistics.mean(s.band_months[b] / months * 100 for s in states)
            for b in range(0, 8)
        },
    }


def percentile(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    ys = sorted(xs)
    k = (len(ys) - 1) * q / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return ys[int(k)]
    return ys[lo] * (hi - k) + ys[hi] * (k - lo)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def valid_cells(only: str | None) -> list[tuple[str, str]]:
    """(currency, mode) pairs that are not duplicates of another cell.

    Peg defence is a gold-standard mandate only — `te_monetary_update_target`
    rewrites mandate 3 to price stability off gold, so those three cells would be
    byte-identical to the price-stability ones and are dropped.
    """
    cells = []
    for currency in CURRENCY_LAWS:
        if only and currency != only:
            continue
        for mode in MODES:
            if mode == MODE_PEG and currency != "gold":
                continue
            cells.append((currency, mode))
    return cells


def self_test() -> int:
    """Check the monetary port against `events/te_debug_monetary_events.txt`.

    That file's .5-.7 header carries the numbers a live game should show, which
    is the only oracle in the repo for the monetary half of this simulation.
    Sequence 1 is the fixed point; sequence 3 states the instability threshold.
    """
    failures = 0

    def check(name: str, got: float, want: float, tol: float) -> None:
        nonlocal failures
        ok = abs(got - want) <= tol
        failures += 0 if ok else 1
        print(f"  [{'ok ' if ok else 'FAIL'}] {name}: {got:.3f} (want {want:.3f} +-{tol})")

    # --- SEQUENCE 1: fiat + national bank, not independent, delegation off,
    # target 5, pi = core = expected = 2, r* = 3. The header says the tuple
    # (policy, pi, expected, gap) = (5, 2.00, 2.00, 0.00) reproduces for ever.
    print("sequence 1 - the fixed point (te_debug_monetary .5a/.7a/.6a)")
    cfg = Config(currency="fiat", mode=MODE_NOTHING, points=0,
                 fin_law="law_universal_banking_light_prudence")
    st = State(policy_rate=5.0, policy_rate_target=5.0, inflation=2.0,
               inflation_core=2.0, inflation_expected=2.0, neutral_rate=3.0)
    st.basket_seeded = True
    st.deficit_pct = 0.0
    rng = random.Random(0)
    for _ in range(12):  # twelve more months, as the header's .6 option a does
        # zero the walks each month: the header says "within a tenth or two"
        # precisely because they are redrawn, and the fixed point is the
        # no-noise case.
        st.neutral_walk = 0.0
        st.neutral_error = 0.0
        st.inflation_noise = 0.0
        st.growth_term = 0.0
        monetary_update(cfg, st, rng, 0)
    check("policy rate", st.policy_rate, 5.0, 0.01)
    check("headline inflation", st.inflation, 2.0, 0.05)
    check("expected inflation", st.inflation_expected, 2.0, 0.05)
    check("stance gap", st.stance_gap, 0.0, 0.05)

    # --- SEQUENCE 3: "no fixed point under a held real stance once P > 2.5 x c,
    # which on a manual target (c = 0.25) is P > 0.625 - a boom phase alone
    # (+0.8) clears it ... twenty years should be a slow climb, not a runaway."
    print("\nsequence 3 - a pinned manual target under boom pressure is unstable BY DESIGN")
    st = State(policy_rate=5.0, policy_rate_target=5.0, inflation=2.0,
               inflation_core=2.0, inflation_expected=2.0, neutral_rate=3.0,
               finance_cycle_value=80.0)  # boom: te_mon_phase_pressure = +0.8
    st.basket_seeded = True
    st.deficit_pct = 0.0
    for _ in range(240):  # twenty years
        st.neutral_walk = 0.0
        st.neutral_error = 0.0
        st.inflation_noise = 0.0
        st.growth_term = 0.0
        st.finance_cycle_value = 80.0
        monetary_update(cfg, st, rng, 0)
    print(f"  after 20 years of a held 5% target in a boom: headline {st.inflation:.1f}%")
    ok = 4.0 < st.inflation < 30.0
    failures += 0 if ok else 1
    print(f"  [{'ok ' if ok else 'FAIL'}] climbs, but is a slow climb rather than a "
          f"runaway inside 60 months (want 4 < pi < 30)")
    print("  [info] the header calls this EXPECTED: 'a pinned manual target under "
          "standing pressure is therefore EXPECTED to drift away'")

    print(f"\n{'all checks passed' if failures == 0 else str(failures) + ' CHECK(S) FAILED'}")
    return 1 if failures else 0


def _run_cell(job: tuple[Config, int, int, dict]) -> dict:
    cfg, seed, runs, tune = job
    TUNE.clear()
    TUNE.update(tune)
    # crc32, not hash(): Python salts hash(str) per interpreter, so --seed would
    # not actually reproduce a run.
    base = seed + zlib.crc32(f"{cfg.currency}/{cfg.mode}/{cfg.points}".encode()) % 10_000
    return summarise(cfg, [run_once(cfg, base + i) for i in range(runs)])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=200, help="runs per cell (default 200)")
    ap.add_argument("--years", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20260922)
    ap.add_argument("--only", help="restrict to one currency law")
    ap.add_argument("--points", default="0,2,5,8",
                    help="comma-separated intervention-point budgets to sweep "
                         "(default 0,2,5,8). 0 means the dashboard tools are never "
                         "used. In game the budget is 1/3/4/5/7 by financial-"
                         "regulation law plus 1 for a national bank, so a real "
                         "country holds 2, 4, 5, 6 or 8.")
    ap.add_argument("--fin-law", default="law_universal_banking_light_prudence",
                    choices=sorted(FIN_LAW_POINTS))
    ap.add_argument("--no-national-bank", action="store_true")
    ap.add_argument("--pulse-order", default="cycle_first",
                    choices=["cycle_first", "monetary_first"])
    ap.add_argument("--growth-feedback", action="store_true",
                    help="let the cycle phase move GDP growth (off by default: the "
                         "coefficient is invented, not read from script)")
    ap.add_argument("--event-channel", action="store_true",
                    help="add a crude aggregate stand-in for banking_cycle_events.txt")
    ap.add_argument("--no-click-weight", type=float, default=100.0,
                    help="weight of 'the AI clicks nothing this month' against the "
                         "buttons' ai_chance (default 100; the engine's own cadence "
                         "is not stated in script)")
    ap.add_argument("--exclude-tool", default="",
                    help="comma-separated dashboard tools the AI never clicks "
                         "(keys: " + ",".join(TOOL_MODIFIERS) + "; 'all' for none "
                         "at all while keeping the crash-event options)")
    ap.add_argument("--simplified", action="store_true",
                    help="the banking_system_simplified game rule: capital controls "
                         "score on the cycle fallback branch instead of the "
                         "external-crisis rule")
    ap.add_argument("--tune", default="",
                    help="comma-separated overrides to measure a proposed retune, "
                         "e.g. --tune sev_scale=0.4,phase_bubble=1.5. Pass "
                         "--tune pre_retune for (approximately) the script as it "
                         "stood before the 2026-09-22 retune.")
    ap.add_argument("--self-test", action="store_true",
                    help="check the monetary port against the expected numbers in "
                         "events/te_debug_monetary_events.txt")
    ap.add_argument("--jobs", type=int, default=0, help="worker processes (0 = all cores)")
    ap.add_argument("--json", help="write the full result table here")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.tune.strip() == "pre_retune":
        TUNE.update(PRE_RETUNE)
        args.tune = ",".join(f"{k}={v}" for k, v in PRE_RETUNE.items())
    for part in args.tune.split(","):
        if part.strip():
            k, _, v = part.partition("=")
            TUNE[k.strip()] = v.strip()
    budgets = [int(x) for x in args.points.split(",") if x.strip() != ""]
    excluded = tuple(t.strip() for t in args.exclude_tool.split(",") if t.strip())
    if "all" in excluded:
        excluded = tuple(TOOL_MODIFIERS)
    for t in excluded:
        if t not in TOOL_MODIFIERS:
            ap.error(f"unknown tool {t!r}; keys are {', '.join(TOOL_MODIFIERS)}")
    cfgs = []
    for currency, mode in valid_cells(args.only):
        for points in budgets:
            cfgs.append(
                Config(
                    currency=currency,
                    mode=mode,
                    points=points,
                    fin_law=args.fin_law,
                    national_bank=not args.no_national_bank,
                    years=args.years,
                    pulse_order=args.pulse_order,
                    growth_feedback=args.growth_feedback,
                    event_channel=args.event_channel,
                    no_click_weight=args.no_click_weight,
                    excluded_tools=excluded,
                    simplified=args.simplified,
                )
            )
    jobs = [(cfg, args.seed, args.runs, dict(TUNE)) for cfg in cfgs]
    workers = args.jobs or min(len(jobs), os.cpu_count() or 1)
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(_run_cell, jobs))
    else:
        rows = [_run_cell(j) for j in jobs]

    print_table(rows, args)
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


def print_table(rows: list[dict], args) -> None:
    print(
        f"Banking cycle simulation — {args.runs} runs x {args.years} years per cell, "
        f"pulse order {args.pulse_order}, no-click weight {args.no_click_weight:g}"
        + (f", TUNE {args.tune}" if args.tune else "")
    )
    print()
    head = (
        f"{'cell':<26}{'crash/100y':>11}{'yrs btwn':>9}{'sev':>6}{'depr%':>7}"
        f"{'recess%':>9}{'frenzy%':>8}{'slump':>7}{'bubble':>8}{'infl':>7}"
        f"{'rate':>6}{'floor%':>8}{'slots':>7}{'cyc':>6}{'reform':>7}{'$ised%':>8}"
        f"{'thru':>7}{'serv':>7}{'pool':>7}{'prem':>6}"
    )
    print(head)
    print("-" * len(head))
    for r in rows:
        print(
            f"{r['label']:<26}"
            f"{r['crashes_per_century_mean']:>11.1f}"
            f"{r['years_between_crashes_median']:>9.1f}"
            f"{r['crash_severity_mean']:>6.0f}"
            f"{r['depression_share'] * 100:>7.0f}"
            f"{r['recession_share']:>9.1f}"
            f"{r['frenzy_share']:>8.1f}"
            f"{r['longest_slump_months_median']:>7.0f}"
            f"{r['bubble_mean']:>8.1f}"
            f"{r['inflation_mean']:>7.2f}"
            f"{r['policy_rate_mean']:>6.2f}"
            f"{r['months_at_floor_pct']:>8.1f}"
            f"{r['tool_slots_mean']:>7.2f}"
            f"{r['cycle_value_mean']:>6.1f}"
            f"{r['currency_reforms_per_century']:>7.1f}"
            f"{r['dollarised_pct']:>8.1f}"
            f"{r['payoff']['building_group_bg_manufacturing_throughput_add'] * 100:>7.2f}"
            f"{r['payoff']['goods_output_services_mult'] * 100:>7.1f}"
            f"{r['payoff']['state_capitalists_investment_pool_contribution_add'] * 100:>7.2f}"
            f"{r['payoff']['country_risk_premium_add'] * 100:>6.2f}"
        )
    print()
    print("crash/100y = mean crashes per century   yrs btwn = median gap between crashes")
    print("sev = mean crash severity roll   depr% = share of crashes that reset the")
    print("      cycle into the panic band (value 5 or 10) — a multi-year depression")
    print("recess% = months in panic+downturn   frenzy% = months at cycle >= 88")
    print("slump = median longest unbroken run of months below cycle 40")
    print("bubble = mean bubble pressure   infl = mean headline inflation (%)")
    print("floor% = months with the policy rate pinned at the regime floor")
    print("slots = mean number of dashboard tools active   cyc = mean cycle value (50 = neutral)")
    print("reform = currency reforms per century   $ised% = months dollarised after a hyperinflation")
    print("thru / serv / pool / prem = time-weighted mean of the manufacturing throughput (pp),")
    print("      services output (%), capitalists' pool contribution (pp) and risk premium (pp)")
    print("      the cycle's phase, tool, band and intervention modifiers carried")


if __name__ == "__main__":
    raise SystemExit(main())
