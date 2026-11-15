"""Audit for a comparison that can never pass, or always passes, because its
literal lies outside the range the value it compares can take.

A movement's activism (`political_movement_radicalism`) runs from 0 to 1, and
the engine takes `political_movement_radicalism >= 25` without a word: it is
simply never true. Eight of the mod's comparisons read that way until
2026-11-15 (#1829): five on activism (the terror pool's unrest gate, the loose
warhead plot, Population Transfer's three cultural-unrest tiers) and three on
`turmoil > 25`, copied from vanilla's Doctrine of Lapse. Vanilla has two of its
own (`docs/vanilla/vanilla_known_bugs.md`). The engine's trigger documentation
itself prints `political_movement_radicalism > 50` as its example, which is
likely where the mod's came from, so a doc example is no evidence of scale.
Lesson: `docs/guides/scripting_best_practices.md` § "Activism, Turmoil and
Their Kin Run 0 to 1".

What is flagged
---------------
A comparison of a value in `RANGES` against a number strictly outside that
value's range: above the maximum or below the minimum, where every operator is
constant (`>= 25` on a 0-to-1 value never passes, `< 25` always does, `= 25`
never does). A literal exactly at a bound is left alone: `liberty_desire >= 100`
passes at 100. Read in `common/` and `events/`:

* the inline form, `turmoil > 0.25`, also behind a scope chain
  (`scope:x.capital.turmoil > 25`: the last segment names the value);
* the block form, `radical_fraction = { value >= 0.1 strata = lower }`: the
  block's own `value` child;
* a named script value on the right whose definition is a constant (`name = N`
  or `name = { value = N }` with nothing else): the mod's
  `common/script_values/` first, then vanilla's from `vanilla_parsed/`.

Comparisons inside scripted triggers and effects are read where they are
written, like any other. What is on the right and is not a constant is counted
in the report's coverage and not judged: a `$X$` argument (the mod passes none
to these values today), a `define:` read, a variable or scope, a script value
that computes, a named level (`ig_approval < happy`).

The table
---------
`RANGES` maps each value's name to its range and the evidence for it, row by
row. A bound comes from the engine's description of the value ("the fraction
of Radicals", "(0-1)", "divided by total") or from a define; vanilla's own
literals only confirm the scale, and its largest literal is never taken as a
maximum (`pollution_amount` tops out at 100 in vanilla script; `POLLUTION_MAX`
is 255). A bound a define sets names the define: the mod's `common/defines/`
value replaces vanilla's (`MAX_INSTITUTION_INVESTMENT` is 9 here, 5 in
vanilla). `LEFT_OUT` lists values considered and left out because the
evidence conflicts or no bound is stated, each with its reason.

To add a row: write the value's range and its evidence; check the name is in
`docs/engine/triggers_summary.txt` or `event_targets_summary.txt`
(`test_trigger_range_audit` does); run `python3 trigger_range_audit.py --root
"<game>/game"` over vanilla, where a new flag means a wrong range or a vanilla
bug (the second goes in `vanilla_known_bugs.md` and in the test's expected
set); and update the expected set of `test_vanilla_parsed_inverse` if the
snapshot shows a new one.

Suppress an intended comparison with a trailing
`# REVIEWED YYYY-MM-DD (trigger_range): why` on its line (for the block form,
the `value` line or the block's opening line). A tag that suppresses nothing
is stale and fails `--strict`.

Report: `docs/engine/trigger_range_report.md`. Registered in POST_LOAD_AUDITS.
`--write` writes the report offline; `--root <dir>` audits another tree (the
game's `game/` folder, for the vanilla inverse) and writes nothing.
"""
from __future__ import annotations

import json
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

from audit_common import AuditResult as _AuditResult
from audit_common import StaleTag, cli_main, parse_reviewed, render_report as _standard_report, write_text
from blanked_text import blank_comments_and_strings

CHECK = "trigger_range"
AUDIT_DIRS = ("common", "events")
REPORT_PATH = os.path.join("docs", "engine", "trigger_range_report.md")
VANILLA_VALUES = os.path.join("vanilla_parsed", "common", "script_values.json")


@dataclass(frozen=True)
class Range:
    lo: float
    hi: float
    evidence: str
    lo_define: str | None = None  # a define whose value replaces `lo` when the tree sets it
    hi_define: str | None = None


def _fraction(evidence: str) -> Range:
    return Range(0.0, 1.0, evidence)


_SHARE = "a share of the population; the doc's examples are 0.2 and 0.8"
_LEVELS = "the doc's fraction of a building's levels"
_ACCEPTANCE = Range(0.0, 100.0, "acceptance: `MIN_ACCEPTANCE_VALUE` / `MAX_ACCEPTANCE_VALUE` (0 / 100), "
                    "\"the minimum / maximum acceptance value a pop can have\"",
                    lo_define="MIN_ACCEPTANCE_VALUE", hi_define="MAX_ACCEPTANCE_VALUE")
_FERVOR = Range(0.0, 100.0, "fervor: `CULTURAL_FERVOR_MIN` / `CULTURAL_FERVOR_MAX` (0 / 100); vanilla's 38 "
                "literals run 0-100. The doc's example, `> 0.2`, is on the wrong scale",
                lo_define="CULTURAL_FERVOR_MIN", hi_define="CULTURAL_FERVOR_MAX")
_OUT_OF_100 = "no define states it; the game shows it out of 100"

# Literal counts are vanilla 1.15.1's, common/ and events/ (2026-11-15).
RANGES: dict[str, Range] = {
    # --- political movements --------------------------------------------------
    "political_movement_radicalism": _fraction(
        "a movement's activism. Defines: a civil war starts at `MIN_RADICALISM_FOR_CIVIL_WAR_START` = 1.0 and "
        "organizes from 0.75; the agitating, protesting and militant thresholds are 0.25, 0.5 and 0.75. Vanilla's "
        "law-enactment tooltip prints it with `|0%` and turns it red at 1. 169 of vanilla's 170 literals run 0.1-0.9 (the 170th is a "
        "bug). Saves store 0 to 1. The doc's example, `> 50`, is wrong"),
    "political_movement_support": _fraction(
        "the share of the population behind a movement; the doc's example is `> 0.5`; vanilla's 137 literals run "
        "0.05-0.5"),
    "political_movement_identity_support": _fraction(
        "that share among pops of the movement's culture or religion; the doc's example is 0.5; vanilla's 9 "
        "literals run 0.05-0.15"),
    "political_movement_military_support": _fraction("that share among the military; vanilla's literals are 0.05"),
    "political_movement_popular_support": _fraction("that share among the population at large; vanilla's literal is 0.1"),
    # --- radicals and loyalists ----------------------------------------------
    "radical_fraction": _fraction("the doc's \"radical fraction in pops\"; vanilla's 69 literals run 0.05-0.4"),
    "loyalist_fraction": _fraction("the doc's \"loyalist fraction in pops\"; vanilla's 10 literals run 0.05-0.1"),
    "radical_population_fraction": _fraction("the doc's \"fraction of the population that are radicals\""),
    "pop_radical_fraction": _fraction("the doc's radicals in a pop over its size; vanilla's literal is 0.25"),
    "pop_loyalist_fraction": _fraction("the doc's loyalists in a pop over its size"),
    "pop_neutral_fraction": _fraction("the doc's neutrals in a pop over its size"),
    "turmoil": _fraction(
        "the doc's \"fraction of Radicals\" in a state; defines `TURMOIL_STATE_*_THRESHOLD` are 0.25, 0.5 and "
        "0.75. 112 of vanilla's 113 literals run 0-0.75 (the 113th is a bug)"),
    "country_turmoil": _fraction("the doc's population-weighted turmoil; its example is 0.2"),
    "loyalists": _fraction("the doc's \"fraction of Loyalists\" in a state; vanilla's 14 literals are 0.1"),
    # --- interest groups -------------------------------------------------------
    "ig_clout": _fraction(
        "an interest group's share of clout; defines `POWERFUL_IG_THRESHOLD` 0.20, `MARGINAL_IG_THRESHOLD` 0.05; "
        "vanilla's 12 literals run 0.01-0.25"),
    "ig_government_power_share": _fraction("the doc's political strength divided by the government's total"),
    "ig_state_pol_strength_share": _fraction("a share of a state's political strength; the doc's example is 0.3"),
    "political_strength_share": _fraction("a share of political strength; vanilla's literal is 0.2"),
    "wealth_share": _fraction("a share of wealth political strength"),
    "ig_approval": Range(
        -20.0, 20.0, "`MIN_IG_APPROVAL` / `MAX_IG_APPROVAL` (-20 / 20); vanilla's 199 literals run -10 to 10",
        lo_define="MIN_IG_APPROVAL", hi_define="MAX_IG_APPROVAL"),
    # --- population shares -----------------------------------------------------
    "literacy_rate": _fraction("a rate; vanilla's 55 literals run 0.1-0.95"),
    "culture_percent_country": _fraction(f"{_SHARE}; vanilla's 20 literals run 0-0.1"),
    "culture_percent_state": _fraction(f"{_SHARE}; vanilla's 46 literals run 0-0.6"),
    "religion_percent_country": _fraction(f"{_SHARE}; vanilla's 19 literals run 0-0.5"),
    "religion_percent_state": _fraction(f"{_SHARE}; vanilla's 55 literals run 0.01-0.9"),
    "primary_cultures_percent_country": _fraction(_SHARE),
    "primary_cultures_percent_state": _fraction(f"{_SHARE}; vanilla's 24 literals run 0.05-0.9"),
    "pop_type_percent_country": _fraction(f"{_SHARE}; vanilla's 11 literals run 0-0.6"),
    "pop_type_percent_state": _fraction(f"{_SHARE}; vanilla's 5 literals run 0.01-0.55"),
    "state_unemployment_rate": _fraction("the doc's example is 0.1; vanilla's 8 literals run 0.1-0.2"),
    "total_population_share": _fraction("the doc's share of the global population"),
    "total_population_including_subjects_share": _fraction("the doc's share of the global population"),
    # --- acceptance, fervor ----------------------------------------------------
    "pop_acceptance": _ACCEPTANCE,
    "state_cultural_acceptance": _ACCEPTANCE,
    "country_average_culture_pop_acceptance": _ACCEPTANCE,
    "state_average_culture_pop_acceptance": _ACCEPTANCE,
    "culture_current_fervor": _FERVOR,
    "country_fervor_primary_culture": _FERVOR,
    # --- country standing ------------------------------------------------------
    "government_legitimacy": Range(0.0, 100.0, f"{_OUT_OF_100}; vanilla's 51 literals run 25-95"),
    "legitimacy": Range(0.0, 100.0, f"{_OUT_OF_100}; vanilla's 28 literals run 50-75"),
    "liberty_desire": Range(
        0.0, 100.0, f"{_OUT_OF_100}; the defines read it at 25-90 (`WAR_GOAL_INDEPENDENCE_MIN_LIBERTY_DESIRE` = "
        "90); vanilla's 139 literals run 0-80"),
    "institution_investment_level": Range(
        0.0, 5.0, "levels up to `MAX_INSTITUTION_INVESTMENT` (vanilla 5; the mod sets 9); vanilla's 129 literals "
        "run 0-5", hi_define="MAX_INSTITUTION_INVESTMENT"),
    # --- states, war, blocs ----------------------------------------------------
    "market_access": _fraction("the doc's example is 0.8; vanilla's literals are 0 and 1"),
    "incorporation_progress": _fraction("the doc's example is 0.25; vanilla's literals are 0 and 1"),
    "average_devastation": _fraction("the doc's \"(0-1)\""),
    "devastation": _fraction(
        "a state's devastation as the trigger reads it: vanilla's `TRIGGER_DEVASTATION` prints it with `|%`, and "
        "vanilla's 19 literals run 0-0.5. The doc's example, `> 5`, is wrong; `add_devastation` takes points "
        "(`DEVASTATION_MAX` 100). `scripting_best_practices.md` § \"Devastation\""),
    "pollution_amount": Range(
        0.0, 255.0, "`POLLUTION_MAX` = 255; vanilla's literals run 50-100, and the mod tests up to 200",
        hi_define="POLLUTION_MAX"),
    "civil_war_progress": _fraction("the doc's example is 0.50; vanilla's 65 literals run 0-1"),
    "highest_secession_progress": _fraction("the doc's example is 0.7; vanilla's 7 literals run 0.3-0.5"),
    "culture_secession_progress": _fraction("the doc's \"progress percentage\", example 0.5; vanilla's literals are 0"),
    "enemy_occupation": _fraction(
        "the doc's example is 0.2, and its sibling `enemy_side_occupation` is documented as 0-1; vanilla's "
        "literals run 0-0.4"),
    "size_weighted_won_battles_fraction": _fraction("the doc's fraction of battles"),
    "size_weighted_lost_battles_fraction": _fraction("the doc's fraction of battles"),
    "blockaded_gdp_share": _fraction("the doc's share of GDP in blockaded states"),
    "current_cohesion_percentage": _fraction(
        "the doc's cohesion as a share of the maximum, example 0.5; vanilla's 10 literals run 0.1-0.8"),
    "target_cohesion_percentage": _fraction("the doc's cohesion as a share of the maximum, example 0.5"),
    # --- units -----------------------------------------------------------------
    "army_mobilization_option_fraction": _fraction("the doc's share of units, example 0.2; vanilla's literals run 0.2-0.75"),
    "country_army_unit_type_fraction": _fraction("the doc's share of units, example 0.2; vanilla's literals run 0.2-0.5"),
    "formation_army_unit_type_fraction": _fraction("the doc's share of units, example 0.2; vanilla's literals run 0.2-0.8"),
    "country_ship_type_fraction": _fraction("the doc's fraction of ships, example 0.2; vanilla's literals are 0.1"),
    "formation_ship_type_fraction": _fraction("the doc's fraction of ships, example 0.2; vanilla's literals run 0.1-0.2"),
    "crew_percent": _fraction("the doc's example is 0.1; vanilla's literal is 0.5"),
    "hit_points_percent": _fraction("the doc's example is 0.1"),
    # --- buildings and markets -------------------------------------------------
    "country_ownership_fraction": _fraction(_LEVELS),
    "private_ownership_fraction": _fraction(f"{_LEVELS}; vanilla's literals are 0 and 1"),
    "self_ownership_fraction": _fraction(_LEVELS),
    "fraction_of_levels_owned_by_country": _fraction(_LEVELS),
    "cash_reserves_ratio": _fraction(
        "the doc's reserves over their maximum, 1 with no maximum; vanilla's 43 literals run 0.25-0.95"),
    "gdp_ownership_ratio": _fraction("the doc's ratio of GDP a country owns; vanilla's literals run 0.05-0.2"),
    "market_exports_reliance": _fraction("the doc's fraction of buy orders"),
    "market_imports_reliance": _fraction("the doc's fraction of buy orders"),
    "market_trade_reliance": _fraction("the doc's fraction of buy and sell orders"),
    "market_consumption_share": _fraction("the doc's fraction of consumption"),
    "market_production_share": _fraction("the doc's fraction of production"),
}

# Considered and left out: the evidence conflicts, or nothing states a bound.
LEFT_OUT: dict[str, str] = {
    "occupancy": "the mod tests `occupancy > 1.05` on purpose (a construction site just cut to a smaller crew); "
                 "whether occupancy passes 1 is unread",
    "scaled_debt": "debt over the credit limit, which a country in default can pass",
    "market_goods_pricier": "a price can be more than 100% above base",
    "market_goods_cheaper": "the doc's percentage cheaper than base; no bound is stated",
    "state_goods_pricier": "a price can be more than 100% above base",
    "state_goods_cheaper": "the doc's percentage cheaper than base; no bound is stated",
    "infamy": "no maximum",
    "escalation": "the doc's example is `> -58`; no range is stated",
    "economic_dependence": "a ratio with no stated bound; the mod tests `> 3`",
    "cultural_acceptance_base": "one component of acceptance; its range is not stated",
    "power_bloc_share_gdp": "-1 outside a power bloc, a share inside one",
}

_WORD = r"""[^\s={}<>!?#"]+"""
# A closing brace, `key <op> {`, `key <op> value`, an unattributed `{`, or a
# bare token (a list item).
_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    rf"|(?P<key>{_WORD})\s*(?P<op>\?=|[!<>=]=|[=<>])\s*"
    rf"(?:(?P<open>\{{)|(?P<value>{_WORD}|\"[^\"\n]*\"))"
    r"|(?P<anon>\{)"
    rf"|(?P<bare>{_WORD})"
)
_NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)")
_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_DEFINE_RE = re.compile(r"^[ \t]*(?P<name>[A-Z][A-Z0-9_]*)[ \t]*=[ \t]*(?P<value>[-+]?\d+(?:\.\d+)?)", re.M)
_TOP_VALUE_RE = re.compile(
    r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*"
    r"(?:(?P<bare>[-+]?\d+(?:\.\d+)?)|\{\s*value[ \t]*=[ \t]*(?P<block>[-+]?\d+(?:\.\d+)?)\s*\})[ \t]*$",
    re.M)
_TOP_NAME_RE = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*=", re.M)
_ANY_NAME_RE = re.compile(r"\b(?:" + "|".join(sorted(map(re.escape, RANGES), key=len, reverse=True)) + r")\b")

# op -> outcome above the maximum, below the minimum
_OUTCOMES = {
    ">": ("never", "always"), ">=": ("never", "always"),
    "<": ("always", "never"), "<=": ("always", "never"),
    "=": ("never", "never"), "==": ("never", "never"), "?=": ("never", "never"),
    "!=": ("always", "always"),
}


def outcome(op: str, value: float, lo: float, hi: float) -> str | None:
    """"never" or "always" when `value` lies strictly outside [lo, hi], else
    None. `=` below the minimum is "never" as an equality; read as `>=` it would
    be "always": constant either way."""
    if op not in _OUTCOMES:
        return None
    if value > hi:
        return _OUTCOMES[op][0]
    if value < lo:
        return _OUTCOMES[op][1]
    return None


@dataclass
class Flag:
    file: str
    line: int
    name: str  # the value compared
    op: str
    written: str  # the right-hand side as written
    value: float
    outcome: str  # never / always
    lo: float
    hi: float
    form: str = "inline"  # inline / block
    exemption: dict | None = None

    @property
    def message(self) -> str:
        via = "" if self.written == _fmt(self.value) else f" (`{self.written}` = {_fmt(self.value)})"
        target = f"{self.name} = {{ value {self.op} {self.written} }}" if self.form == "block" \
            else f"{self.name} {self.op} {self.written}"
        return (f"`{target}`{via} {self.outcome} passes: `{self.name}` runs {_fmt(self.lo)} to "
                f"{_fmt(self.hi)}")


@dataclass
class AuditResult(_AuditResult):
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0
    judged: int = 0  # comparisons with a number (or a constant) on the right
    unjudged: dict[str, int] = field(default_factory=dict)  # kind -> count
    ranges: dict[str, Range] = field(default_factory=dict)  # as applied, defines resolved
    root: str = ""


def _fmt(x: float) -> str:
    return f"{x:g}"


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _txt_files(base: str):
    for dirpath, dirs, files in os.walk(base):
        dirs.sort()
        for fname in sorted(files):
            if fname.endswith(".txt"):
                yield os.path.join(dirpath, fname)


def read_defines(root: str) -> dict[str, float]:
    """Every `NAME = <number>` in the tree's `common/defines/`, the last file
    read winning."""
    out: dict[str, float] = {}
    for path in _txt_files(os.path.join(root, "common", "defines")):
        clean, _ = blank_comments_and_strings(_read(path))
        for m in _DEFINE_RE.finditer(clean):
            out[m.group("name")] = float(m.group("value"))
    return out


def applied_ranges(defines: dict[str, float]) -> dict[str, Range]:
    """`RANGES` with each named define's value, where the tree sets it, in
    place of vanilla's."""
    out = {}
    for name, r in RANGES.items():
        lo = defines.get(r.lo_define, r.lo) if r.lo_define else r.lo
        hi = defines.get(r.hi_define, r.hi) if r.hi_define else r.hi
        out[name] = Range(lo, hi, r.evidence, r.lo_define, r.hi_define)
    return out


def read_constants(root: str, snapshot: str | None) -> tuple[dict[str, float], set[str]]:
    """(constant script values, every script value name): the tree's
    `common/script_values/` first (a name's first definition), then the
    snapshot's. A constant is `name = N` or `name = { value = N }` alone."""
    constants: dict[str, float] = {}
    names: set[str] = set()
    for path in _txt_files(os.path.join(root, "common", "script_values")):
        clean, _ = blank_comments_and_strings(_read(path))
        found = {m.group("name") for m in _TOP_NAME_RE.finditer(clean)}
        for m in _TOP_VALUE_RE.finditer(clean):
            n = m.group("name")
            if n not in names:
                constants[n] = float(m.group("bare") or m.group("block"))
        names |= found
    if snapshot and os.path.isfile(snapshot):
        try:
            with open(snapshot, encoding="utf-8") as fh:
                vanilla = json.load(fh)
        except (OSError, ValueError):
            vanilla = {}
        for n, entry in vanilla.items():
            if n in names:
                continue
            names.add(n)
            v = entry[1] if isinstance(entry, list) and len(entry) == 2 else None
            if isinstance(v, dict) and set(v) == {"value"}:
                v = v["value"][1] if isinstance(v["value"], list) and len(v["value"]) == 2 else None
            if isinstance(v, str) and _NUMBER_RE.fullmatch(v):
                constants[n] = float(v)
    return constants, names


def value_name(key: str) -> str | None:
    """The value a comparison's left side names: the last segment of a scope
    chain, or None for a variable, a parameter or a quoted call."""
    name = key.rsplit(".", 1)[-1]
    if not _NAME_RE.fullmatch(name):
        return None
    return name


def _resolve(written: str, constants: dict[str, float], names: set[str]) -> tuple[float | None, str]:
    """(number, "") for a literal or a constant script value, else (None, the
    kind of right-hand side) for the coverage count."""
    if _NUMBER_RE.fullmatch(written):
        return float(written), ""
    if "$" in written:
        return None, "parameter"
    if written.startswith("define:"):
        return None, "define"
    if _NAME_RE.fullmatch(written):
        if written in constants:
            return constants[written], ""
        if written in names:
            return None, "computed script value"
        return None, "named level or other name"
    return None, "variable, scope or other"


def scan_text(text: str, rel: str, ranges: dict[str, Range], constants: dict[str, float],
              names: set[str], result: AuditResult) -> None:
    """Add one file's flags, stale tags and counts to `result`."""
    if not _ANY_NAME_RE.search(text) and CHECK not in text:
        return
    clean, comments = blank_comments_and_strings(text)
    starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]
    # Each open block: (the ranged value it compares, or None; its opening line).
    stack: list[tuple[str | None, int]] = []
    used: set[int] = set()

    def judge(name: str, op: str, written: str, line: int, form: str, opener: int | None) -> None:
        r = ranges[name]
        value, kind = _resolve(written, constants, names)
        if value is None:
            result.unjudged[kind] = result.unjudged.get(kind, 0) + 1
            return
        result.judged += 1
        verdict = outcome(op, value, r.lo, r.hi)
        if verdict is None:
            return
        exemption = parse_reviewed(comments.get(line), (CHECK,))
        tag_line = line
        if exemption is None and opener is not None:
            exemption = parse_reviewed(comments.get(opener), (CHECK,))
            tag_line = opener
        if exemption is not None:
            used.add(tag_line)
        result.flags.append(Flag(rel, line, name, op, written, value, verdict, r.lo, r.hi, form, exemption))

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
            continue
        if m.group("anon"):
            stack.append((None, bisect_right(starts, m.start())))
            continue
        key = m.group("key")
        if key is None:
            continue
        line = bisect_right(starts, m.start())
        name = value_name(key)
        if m.group("open"):
            stack.append((name if name in ranges else None, line))
            continue
        written = m.group("value")
        if written is None or written.startswith('"'):
            continue
        if key == "value":
            if stack and stack[-1][0] is not None:
                judge(stack[-1][0], m.group("op"), written, line, "block", stack[-1][1])
            continue
        if name in ranges:
            judge(name, m.group("op"), written, line, "inline", None)

    for line, comment in comments.items():
        hit = parse_reviewed(comment, (CHECK,))
        if hit is not None and hit["tag"] == CHECK and line not in used:
            result.stale.append(StaleTag(rel, line, CHECK))


def audit(mod_path: str, *, root: str | None = None, snapshot: str | None = "") -> AuditResult:
    """Audit `root` (default `mod_path`). Script values come from the tree
    and, for the mod, from vanilla's snapshot; pass `snapshot=None` for none."""
    tree = root or mod_path
    if snapshot == "":
        snapshot = None if root else os.path.join(mod_path, VANILLA_VALUES)
    ranges = applied_ranges(read_defines(tree))
    constants, names = read_constants(tree, snapshot)
    result = AuditResult(ranges=ranges, root=tree)
    for top in AUDIT_DIRS:
        for path in _txt_files(os.path.join(tree, top)):
            rel = os.path.relpath(path, tree).replace(os.sep, "/")
            result.files_audited += 1
            scan_text(_read(path), rel, ranges, constants, names, result)
    return result


# --- the vanilla snapshot -----------------------------------------------------

_OPS = set(_OUTCOMES)


def _pairs(node):
    """The `[op, value]` pairs a parsed field holds: one, or a list of them for
    a repeated key."""
    if isinstance(node, list) and len(node) == 2 and isinstance(node[0], str) and node[0] in _OPS:
        yield node[0], node[1]
    elif isinstance(node, list):
        for item in node:
            yield from _pairs(item)


def scan_parsed(node, path: tuple = (), ranges: dict[str, Range] | None = None):
    """Yield (path, name, op, literal, outcome) for every out-of-range
    comparison in a `vanilla_parsed/` entity, inline or in a block's `value`.
    Literals only: a script value on the right is not resolved here."""
    ranges = ranges if ranges is not None else RANGES
    if not isinstance(node, dict):
        for _op, value in _pairs(node):
            if isinstance(value, (dict, list)):
                yield from scan_parsed(value, path, ranges)
        return
    for key, field_ in node.items():
        name = value_name(key)
        for op, value in _pairs(field_):
            if name in ranges and isinstance(value, str) and _NUMBER_RE.fullmatch(value):
                r = ranges[name]
                verdict = outcome(op, float(value), r.lo, r.hi)
                if verdict:
                    yield path + (key,), name, op, value, verdict
            elif name in ranges and isinstance(value, dict):
                for vop, vv in _pairs(value.get("value")):
                    if isinstance(vv, str) and _NUMBER_RE.fullmatch(vv):
                        r = ranges[name]
                        verdict = outcome(vop, float(vv), r.lo, r.hi)
                        if verdict:
                            yield path + (key, "value"), name, vop, vv, verdict
            if isinstance(value, (dict, list)):
                yield from scan_parsed(value, path + (key,), ranges)


# --- report -------------------------------------------------------------------

TITLE = "Trigger range audit report"
INTRO = (
    "Flagged: a comparison whose number lies outside the range the value it compares can take, so it never "
    "passes or always passes (`political_movement_radicalism >= 25` on a 0-to-1 value). The engine says nothing. "
    "The ranges and their evidence are below and in `RANGES` in `trigger_range_audit.py`; lesson: "
    "`docs/guides/scripting_best_practices.md` § \"Activism, Turmoil and Their Kin Run 0 to 1\"."
)


def render_report(result: AuditResult) -> str:
    text = _standard_report(result, TITLE, audit="trigger_range_audit", intro=INTRO).rstrip("\n")
    out = [text, f"- comparisons judged: {result.judged}", ""]
    out += ["## Not judged", "",
            "Comparisons of a ranged value with something other than a number or a constant script value on the "
            "right, by kind.", ""]
    if result.unjudged:
        out += [f"- {kind}: {n}" for kind, n in sorted(result.unjudged.items())]
    else:
        out.append("_None._")
    out += ["", "## The ranges", "",
            "| Value | Range | Evidence |", "|---|---|---|"]
    for name in sorted(result.ranges):
        r = result.ranges[name]
        out.append(f"| `{name}` | {_fmt(r.lo)} to {_fmt(r.hi)} | {r.evidence} |")
    out += ["", "## Left out", "", "| Value | Why |", "|---|---|"]
    out += [f"| `{name}` | {why} |" for name, why in sorted(LEFT_OUT.items())]
    out.append("")
    return "\n".join(out)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: a file scan, so `mod_state` is unused."""
    from path_constants import mod_path
    result = audit(mod_path)
    out_path = os.path.join(mod_path, REPORT_PATH)
    write_text(out_path, render_report(result))
    return {
        "unreviewed": len(result.failing),
        "total_flags": len(result.flags),
        "exempted": len(result.exemptions),
        "stale_tags": len(result.stale),
        "judged": result.judged,
        "files_audited": result.files_audited,
        "path": out_path,
    }


def main(argv=None) -> int:
    """Print the report; `--strict` (CI) exits 1 on an unreviewed flag or a
    stale tag."""
    from path_constants import mod_path

    def add_arguments(parser):
        parser.add_argument("--write", action="store_true", help="also write the report (the mod only)")
        parser.add_argument("--root", help="audit this tree instead (vanilla's game/ folder); writes nothing")

    def run(args):
        result = audit(mod_path, root=args.root)
        if args.write and not args.root:
            write_text(os.path.join(mod_path, REPORT_PATH), render_report(result))
        return result

    return cli_main(run, lambda result, args: render_report(result), argv=argv,
                    description=__doc__.splitlines()[0], add_arguments=add_arguments,
                    strict_help="exit 1 on an unreviewed flag or a stale tag (CI mode)")


if __name__ == "__main__":
    raise SystemExit(main())
