"""Read the AI telemetry probe's lines out of debug.log and say how the AI countries did.

TEMPORARY (2026-11-15), with scripts/generators/gen_ai_probe.py, which writes the probe and documents its lines.

    ai_probe_report.py check  <log> [<log> ...]              did the probe arm, which canaries printed, what is missing
    ai_probe_report.py parse  <log> [<log> ...] --out DIR    snapshots.jsonl, events.jsonl, ticks.json, canary.json
    ai_probe_report.py report <log or DIR> [...] [--md FILE] the scorecard, by the owner's five priorities

A log is any file holding the game's debug.log lines: the QA harness's `fixture_debug.log` for an unattended run
(`python3 -m game_qa fixture --until ...` copies the whole log as the game writes it), or debug.log and its rotated
generations. Lines are read in file order, so name the files oldest first. A DIR is one `parse` wrote.

Read-only apart from `parse --out`. Needs nothing but the log and `ai_probe_key.json` beside this script.

THE SCORECARD takes each country's yearly snapshots and reports, by decade and for AI countries that are not
decentralized: growth (GDP and GDP per head a year, the countries shrinking), the means of growth (construction
sectors, queue, buildings finished, the investment pool against income, peasants), solvency (in default, declared
bankrupt, debt against the limit, income against expenses), technology (count, a year, innovation, universities,
whether anything is being researched), laws (enacting, starts and outcomes a year, the commonest law per group),
the military (size, share of spending, how modern the army's units are) and expansion (states, colonies, plays).
Figures are medians with the 10th and 90th percentiles unless a line says otherwise.
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEY_PATH = HERE / "ai_probe_key.json"
MARK = "TE_AIP "
_NUMBER = re.compile(r"-?[0-9][0-9,]*(?:\.[0-9]+)?")


def load_key(path: Path = KEY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def number(text: str):
    """A printed figure as int or float; the text itself when it is not one (a name, an unrendered accessor)."""
    text = text.strip()
    if _NUMBER.fullmatch(text):
        plain = text.replace(",", "")
        return float(plain) if "." in plain else int(plain)
    return text


def pairs(body: str) -> dict:
    """`a=1 b=2.5 c=x` as a dict. A value runs to the next ` key=`."""
    out = {}
    parts = re.split(r"(?:^| )([a-z][a-z0-9_]*)=", body)
    for i in range(1, len(parts) - 1, 2):
        out[parts[i]] = number(parts[i + 1])
    return out


class Parsed:
    def __init__(self):
        self.armed: list[str] = []                  # the ARM lines' bodies
        self.disarmed = 0
        self.canary: dict[str, object] = {}
        self.canary_seen = False
        self.ticks: dict[int, dict] = {}            # k -> {y, date}
        self.snapshots: dict[tuple[int, int], dict] = {}   # (id, k) -> record
        self.data_lines: dict[tuple[int, int], dict] = {}  # the X lines, same key
        self.events: list[dict] = []
        self.world: dict[int, dict] = {}            # the W lines (version 2): k -> {y, countries, dn, dn_states}
        self.bad: list[str] = []
        self.line_names: Counter = Counter()
        self.k_restarts = 0                         # a K line whose month is below the last one's: a second run
        self._last_k = 0

    def version(self) -> int:
        """The probe version the log armed with (1 before ARM lines carried it)."""
        versions = [int(m.group(1)) for body in self.armed for m in [re.search(r"v=(\d+)", body)] if m]
        return max(versions, default=1)

    def records(self) -> list[dict]:
        out = []
        for key in sorted(self.snapshots, key=lambda pair: (pair[1], pair[0])):
            record = dict(self.snapshots[key])
            extra = self.data_lines.get(key)
            if extra:
                record["x"] = extra
            out.append(record)
        return out


def parse_lines(lines, key: dict, parsed: Parsed | None = None) -> Parsed:
    parsed = parsed or Parsed()
    positional = set(key.get("positional_groups", []))
    line_fields = key["lines"]
    # Fields a later version took off the end of a positional line: an older log's line still carries them, and
    # they are dropped from its end (version 6's army census, gen_ai_probe.RETIRED_TAIL).
    retired = key.get("retired_tail", {})
    for raw in lines:
        at = raw.find(MARK)
        if at < 0:
            continue
        text = raw[at + len(MARK):].rstrip("\r\n")
        kind, _, rest = text.partition(" ")
        try:
            if kind == "ARM":
                parsed.armed.append(rest)
            elif kind == "DISARM":
                parsed.disarmed += 1
            elif kind == "CANARY":
                parsed.canary_seen = True
                name, _, value = rest.partition(" ")
                parsed.canary[name] = number(value[2:]) if value.startswith("v=") else (value or True)
            elif kind == "K":
                k, _, body = rest.partition(" ")
                if int(k) < parsed._last_k:
                    parsed.k_restarts += 1
                parsed._last_k = int(k)
                parsed.ticks.setdefault(int(k), {}).update(pairs(body))
            elif kind == "W":
                k, _, body = rest.partition(" ")
                parsed.world[int(k)] = {"k": int(k), **pairs(body)}
            elif kind == "KDATE":
                k, _, date = rest.partition(" ")
                parsed.ticks.setdefault(int(k), {})["date"] = date.strip()
            elif kind in ("S", "X", "E"):
                name, tag, ident, k, *tail = rest.split(" ", 4)
                body = tail[0] if tail else ""
                ident, k = int(ident), int(k)
                if kind == "E":
                    parsed.events.append({"event": name, "tag": tag, "id": ident, "k": k, **pairs(body)})
                    continue
                store = parsed.snapshots if kind == "S" else parsed.data_lines
                record = store.setdefault((ident, k), {"tag": tag, "id": ident, "k": k})
                if kind == "S":
                    parsed.line_names[name] += 1
                    if name[0] in positional:
                        values = [number(part) for part in body.split(";")]
                        fields = line_fields.get(name, [])
                        if fields and len(values) == len(fields) + len(retired.get(name, [])):
                            values = values[:len(fields)]
                        if len(values) != len(fields):
                            parsed.bad.append(f"{name}: {len(values)} values for {len(fields)} fields: {text[:120]}")
                            continue
                        record.update(zip(fields, values))
                    else:
                        record.update(pairs(body))
                else:
                    record.update(pairs(body))
            else:
                parsed.bad.append(text[:160])
        except (ValueError, IndexError):
            parsed.bad.append(text[:160])
    return parsed


def read_logs(paths: list[Path], key: dict) -> Parsed:
    parsed = Parsed()
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as handle:
            parse_lines(handle, key, parsed)
    return parsed


def load_dir(folder: Path) -> Parsed:
    parsed = Parsed()
    for line in (folder / "snapshots.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        parsed.snapshots[(record["id"], record["k"])] = record
    events = folder / "events.jsonl"
    if events.exists():
        parsed.events = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]
    ticks = folder / "ticks.json"
    if ticks.exists():
        parsed.ticks = {int(k): v for k, v in json.loads(ticks.read_text(encoding="utf-8")).items()}
    world = folder / "world.json"
    if world.exists():
        parsed.world = {int(k): v for k, v in json.loads(world.read_text(encoding="utf-8")).items()}
    canary = folder / "canary.json"
    if canary.exists():
        parsed.canary = json.loads(canary.read_text(encoding="utf-8"))
    armed = folder / "armed.json"
    if armed.exists():
        parsed.armed = json.loads(armed.read_text(encoding="utf-8"))
    return parsed


def gather(sources: list[str], key: dict) -> Parsed:
    paths = [Path(source) for source in sources]
    if len(paths) == 1 and paths[0].is_dir():
        return load_dir(paths[0])
    return read_logs(paths, key)


# --- check ---------------------------------------------------------------------------------------------------------

def check(parsed: Parsed, key: dict) -> tuple[list[str], bool]:
    """What a first, short run should show. Returns the lines to print and whether the probe is fit for a long run."""
    out, ok = [], True
    if not parsed.armed:
        return ["NOT ARMED: no `TE_AIP ARM` line. In an unattended run this means the game counted a human player "
                "(`any_country = { is_player = yes }`), or the run ended before its first monthly pulse."], False
    out.append(f"armed: {parsed.armed[0]} ({len(parsed.armed)} ARM lines, {parsed.disarmed} DISARM)")
    version = parsed.version()
    wanted = ["start", "date", *data_functions_of(key, version), "end"]
    missing = [name for name in wanted if name not in parsed.canary]
    out.append(f"canaries printed: {len(wanted) - len(missing)} of {len(wanted)}")
    for name in wanted:
        if name in parsed.canary:
            out.append(f"  ok       {name} = {parsed.canary[name]!r}")
        else:
            out.append(f"  MISSING  {name}  (the engine dropped the line: take the accessor out of DATA_FUNCTIONS)")
    if "start" in missing or "end" in missing:
        ok = False
    out.append(f"ticks: {len(parsed.ticks)} months, k {min(parsed.ticks, default=0)} to {max(parsed.ticks, default=0)}; "
               f"with a date: {sum(1 for t in parsed.ticks.values() if 'date' in t)}")
    records = parsed.records()
    out.append(f"snapshots: {len(records)} of {len({r['id'] for r in records})} countries")
    expected = expected_lines(key, version)
    if len(expected) < len(key["lines"]):
        out.append(f"  a version-{version} log: the {len(key['lines']) - len(expected)} lines later versions added "
                   "are not expected of it")
    absent = [name for name in expected if not parsed.line_names.get(name)]
    if records:
        top = max(parsed.line_names.values())
        short = {name: parsed.line_names[name] for name in expected if 0 < parsed.line_names[name] < top}
        if absent:
            ok = False
            out.append(f"  snapshot lines that NEVER printed: {', '.join(absent)}")
        if short:
            out.append(f"  snapshot lines printed fewer times than the commonest ({top}): {short}")
        if not absent and not short:
            out.append(f"  all {len(expected)} snapshot lines printed for every snapshot")
        sample = records[len(records) // 2]
        shown = {k: sample[k] for k in ("tag", "id", "k", "y", "ai", "gdp", "pop", "techs", "levels", "income",
                                        "expenses", "army", "states") if k in sample}
        out.append(f"  a sample: {shown}")
        texts = Counter(k for r in records for k, v in r.items() if isinstance(v, str) and k not in ("tag",))
        if texts:
            out.append(f"  fields that printed text, not a number (an unrendered value): {dict(texts.most_common(12))}")
        zeros = [f for f in ("gdp", "pop", "income", "levels", "techs") if all(not r.get(f) for r in records)]
        if zeros:
            ok = False
            out.append(f"  fields that are 0 or absent in every snapshot (the read is wrong): {zeros}")
        # Not a verdict: early in a game much is rightly 0. A whole group at 0 is a read that does not work
        # (every building-type level was, until the read took a `bt:` link).
        positional = set(key.get("positional_groups", []))
        for name, fields in key["lines"].items():
            if name not in expected:
                continue
            # A field no record carries is not in this log's version (version 2's additions to a version-1 line).
            fields = [f for f in fields if any(f in r for r in records)]
            dead = [f for f in fields if all(not r.get(f) for r in records)]
            if not dead:
                continue
            if name[0] in positional or len(dead) > 8:
                out.append(f"  {name}: {len(dead)} of {len(fields)} fields are 0 in every snapshot"
                           + (" (ALL: check the read)" if len(dead) == len(fields) else ""))
            else:
                out.append(f"  {name}: 0 in every snapshot: {', '.join(dead)}")
            out.extend(f"    {note}" for note in dead_field_notes(parsed, key, dead, version))
    else:
        out.append("  none yet: a country first reports within twelve months of arming")
    data = len(parsed.data_lines)
    out.append(f"data-function (X) records: {data}")
    out.extend(check_x_construction(records))
    out.extend(check_spacing(parsed, key, records, version))
    out.append(f"events: {len(parsed.events)} {dict(Counter(e['event'] for e in parsed.events).most_common())}")
    if version >= 2:
        lines, good = check_version_2(parsed, key, records)
        out.extend(lines)
        ok = ok and good
    if version >= 3:
        out.extend(check_version_3(parsed, key, records))
    if version >= 4:
        out.extend(check_version_4(parsed, key, records))
    if parsed.k_restarts:
        out.append(f"WARNING: the month count went back {parsed.k_restarts} times: these files hold more than one "
                   "run, whose serials and months collide. Read each run alone.")
    if parsed.bad:
        out.append(f"unreadable probe lines: {len(parsed.bad)}; first: {parsed.bad[0]}")
    return out, ok


def expected_lines(key: dict, version: int) -> list[str]:
    """The snapshot lines a log of this probe version prints (every line, for a key without `lines_added`)."""
    added = key.get("lines_added")
    if not added:
        return list(key["lines"])
    wanted = {name for v, names in added.items() if int(v) <= version for name in names}
    return [name for name in key["lines"] if name in wanted]


def data_functions_of(key: dict, version: int) -> list[str]:
    """The data functions (X fields and their canaries) a log of this probe version prints."""
    later = {name for v, names in key.get("data_functions_added", {}).items() if int(v) > version for name in names}
    return [name for name in key["data_functions"] if name not in later]


def rule_settings(parsed: Parsed, key: dict) -> dict[str, list[str]]:
    """Each W-line game rule (version 4) by the settings its lines read, in month order: {field: [setting, ...]},
    a setting given once for each run of months it held."""
    out: dict[str, list[str]] = {}
    for name, rule in key.get("rules", {}).items():
        seen: list[str] = []
        for k in sorted(parsed.world):
            index = parsed.world[k].get(name)
            if not isinstance(index, int):
                continue
            settings = rule["settings"]
            setting = settings[index - 1] if 0 < index <= len(settings) else f"none ({index})"
            if not seen or seen[-1] != setting:
                seen.append(setting)
        if seen:
            out[name] = seen
    return out


# Every run before version 4 was made under the owner's last lobby rules, which on 2026-11-16 held
# free_market_construction_no_retooling (the harness's run4_start.json, `rules`).
RUN_RULE_BEFORE_V4 = "free_market_construction_no_retooling"
# The settings that remove pm_retooling, for a key from before version 4, which does not list them (the generator's
# RETOOLING_WAIVED; test_ai_probe.py holds the two equal).
RETOOLING_WAIVED_BEFORE_V4 = ["free_market_construction_no_ai_retooling", "free_market_construction_no_retooling",
                              "free_market_construction_no_maintenance"]


def retooling_waived(key: dict) -> list[str]:
    return key.get("retooling_waived") or RETOOLING_WAIVED_BEFORE_V4


def dead_field_notes(parsed: Parsed, key: dict, dead: list[str], version: int) -> list[str]:
    """What a field at 0 in every snapshot means where that is known: a rule's doing or a known misread."""
    notes = []
    waived = retooling_waived(key)
    if any(f.startswith("rt_") for f in dead):
        settings = rule_settings(parsed, key).get("r_fmc")
        if settings:
            if all(s in waived for s in settings):
                notes.append(f"rt_*: 0 by the rule: the run's free_market_construction setting ({', '.join(settings)}) "
                             "removes pm_retooling as the engine applies it (te_remove_waived_pm_retooling)")
            else:
                notes.append(f"rt_*: 0 although the setting ({', '.join(settings)}) leaves AI retooling in place: the "
                             "read fails, if production methods changed (n_pm) in these snapshots")
        else:
            notes.append("rt_*: this log names no rule (the W line carries it from version 4). Under "
                         f"{', '.join(waived)} the modifier is removed as the engine applies it, so 0 is the rule's "
                         f"doing; every run before version 4 was under {RUN_RULE_BEFORE_V4}")
    if "bt_company_headquarter" in dead and version < 4:
        notes.append("bt_company_headquarter: versions 1 to 3 read the template building type, which no company's "
                     "headquarters is (each company has a type of its own); read bg_company_headquarter (G2), as "
                     "version 4's bt_company_headquarter does")
    return notes


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def month_of(date) -> int | None:
    """The month (0 = January) of a KDATE line's date, `February 1, 1836`; None when it does not read."""
    name = str(date or "").split(" ", 1)[0]
    return MONTHS.index(name) if name in MONTHS else None


def check_x_construction(records: list[dict]) -> list[str]:
    """The X construction readings that do not stand for the country's construction (x_construction), counted: the
    report leaves them out of its construction figures. Not a verdict: they are the engine's state that week."""
    rows, _ = once_a_year([r for r in records if "y" in r])
    top = largest_by_year(rows)
    kinds, big, named = Counter(), Counter(), []
    for r in rows:
        kind = x_construction(r)
        kinds[kind] += 1
        if kind in ("unpaid", "idle") and r["id"] in top.get(r["y"], ()):
            big[kind] += 1
            named.append(f"{r['tag']} {r['y']} {kind}")
    if not rows:
        return []
    out = [f"X construction readings left out of the report's construction figures: {kinds['unpaid']} unpaid "
           f"(private points used, no private construction goods booked) and {kinds['idle']} idle (no construction "
           f"while building: not paused, private levels queued, a pool of {X_BUILDING_POOL:,} or more), of "
           f"{len(rows) - kinds['none']}; among the 20 largest of their year {big['unpaid']} unpaid, {big['idle']} idle"]
    if named:
        out.append(f"  the 20 largest's: {', '.join(named[:24])}" + (" ..." if len(named) > 24 else ""))
    # `wasted` (has_wasted_construction) is not unused points: in run 2 it held on 11,750 of 16,119 unpaused rows
    # with con_unused above 0 on 108, and never while paused. Unused points are con_unused.
    unpaused = [r for r in rows if num(r, "paused") != 1 and x_construction(r) != "none"]
    if unpaused:
        out.append(f"  unpaused readings: `wasted` yes in {sum(1 for r in unpaused if num(r, 'wasted') == 1)}, unused "
                   f"points (con_unused) above 0 in {sum(1 for r in unpaused if num(r.get('x') or {}, 'con_unused') > 0)}"
                   f" of {len(unpaused)}; paused: `wasted` yes in "
                   f"{sum(1 for r in rows if num(r, 'paused') == 1 and num(r, 'wasted') == 1)} (the flag is not unused "
                   "points: read con_unused)")
    return out


def check_spacing(parsed: Parsed, key: dict, records: list[dict], version: int) -> list[str]:
    """How a log's reports are spaced: the months between a country's reports, the country-years that hold two, and
    for a version-3 log whether each report fell in the country's own month."""
    rows = [r for r in records if "y" in r]
    if not rows:
        return []
    _, folded = once_a_year(rows)
    gaps = Counter(b["k"] - a["k"] for mine in series(rows).values() for a, b in zip(mine, mine[1:]))
    out = [f"spacing: months between a country's reports {dict(sorted(gaps.items()))}; country-years holding two "
           f"reports: {folded}"]
    if version < key.get("calendar_schedule_from", 3):
        if folded:
            out.append("  (versions 1 and 2 count twelve 30-day pulses, so a report drifts and now and then falls twice "
                       "in a year: the report keeps the later and adds the earlier's counters to it)")
        return out
    if folded:
        out.append("  version 3 reports once a calendar year: two in one year means the schedule "
                   "(te_aip_country_tick, te_aip_due) did not work as written")
    # The month a report fell in, from the date the global pulse stamped its month count with, against the
    # country's own (serial modulo 12). A pulse on the 1st may run before the global pulse of that day, so the
    # month before also counts; a February report moves to March when the country's pulse misses February.
    offsets = Counter()
    for r in rows:
        month = month_of(parsed.ticks.get(r["k"], {}).get("date"))
        if month is not None:
            offsets[(month - r["id"] % 12) % 12] += 1
    if offsets:
        near = offsets[0] + offsets[1] + offsets[11]
        out.append(f"  reports in the country's own month: {offsets[0]}, the month after {offsets[1]}, the month before "
                   f"{offsets[11]}, elsewhere {sum(offsets.values()) - near} (version 3's calendar schedule: "
                   "unverified until a game prints it)")
    return out


def check_version_3(parsed: Parsed, key: dict, records: list[dict]) -> list[str]:
    """Version 3's additions, read once each: none of them had printed in a game when written (2026-11-16), so each
    stays flagged here until one does. Not a verdict."""
    out = ["version 3 additions (unverified until a game prints them):"]
    lines = [w for w in parsed.world.values() if "states" in w]
    if lines:
        last = parsed.world[max(k for k, w in parsed.world.items() if "states" in w)]
        agree = sum(1 for w in lines if num(w, "states") - num(w, "c_states") == num(w, "dn_states"))
        out.append(f"  W: the last line {last}; dn_states equals states - c_states in {agree} of {len(lines)} lines")
        if all(not w.get("dn") for w in lines):
            out.append("  W: dn is 0 in every line: every_decentralized_country reaches nothing in a script value; "
                       "read the land left to colonize as states - c_states")
        if all(not w.get("states") for w in lines):
            out.append("  W: states is 0 in every line: every_state in a script value reaches nothing")
    else:
        out.append("  W: no line carries version 3's states and c_states yet")
    rows = [r for r in records if "bank_phase" in r]
    if not rows:
        return out + ["  banking cycle: no snapshot carries bank_phase yet"]
    phases = key.get("bank_phases", [])
    running = [r for r in rows if num(r, "bank_phase") > 0]
    counts = Counter(phases[num(r, "bank_phase") - 1] if 0 < num(r, "bank_phase") <= len(phases)
                     else num(r, "bank_phase") for r in running)
    out.append(f"  banking cycle running in {len(running)} of {len(rows)} snapshots; phases {dict(counts.most_common())}; "
               f"a crash in the year before {sum(1 for r in rows if num(r, 'bank_crashed') == 1)}; pulses in a panic or "
               f"downturn {sum(num(r, 'n_bank_down') for r in rows)}")
    if not running:
        out.append("  no cycle running in any snapshot: right before the first stock exchanges and with the banking "
                   "rule off; past about 1860 with the rule on, te_banking_cycle_running does not read in the probe")
        return out
    # The phase is the band of the cycle value (BANK_PHASES); the value prints with one decimal.
    edges = (10, 25, 40, 60, 75, 88)

    def band(value):
        return 1 + sum(1 for edge in edges if value >= edge)
    agree = sum(1 for r in running if num(r, "bank_phase") in (band(num(r, "bank_cycle") - 0.05),
                                                               band(num(r, "bank_cycle") + 0.05)))
    out.append(f"  bank_phase is the band of bank_cycle in {agree} of {len(running)}"
               + ("" if agree == len(running) else " (the phase or the value does not read as written)"))
    return out


def check_version_4(parsed: Parsed, key: dict, records: list[dict]) -> list[str]:
    """Version 4's additions (#1877), read once each against what the other fields say they must be. None had
    printed in a game when written (2026-11-16), so each stays flagged here until one does. Not a verdict."""
    out = ["version 4 additions (unverified until a game prints them):"]
    rules = rule_settings(parsed, key)
    if rules:
        out.append("  W: game rules " + "; ".join(f"{key['rules'][name]['rule']} {' then '.join(seen)}"
                                                 for name, seen in rules.items()))
        fmc = rules.get("r_fmc", [])
        if fmc and all(s in retooling_waived(key) for s in fmc):
            out.append("  rt_*: this run's setting removes pm_retooling as the engine applies it, so rt_* reads 0 by "
                       "design")
        if any("none" in s for seen in rules.values() for s in seen):
            out.append("  W: a rule read no setting (index 0): has_game_rule does not read the setting as written")
    else:
        out.append("  W: no line carries version 4's game rules yet")
    rows = [r for r in records if "pp_states" in r]
    if not rows:
        return out + ["  no snapshot carries the P lines yet"]
    n = len(rows)

    def count(test):
        return sum(1 for r in rows if test(r))

    # Retooling under a setting that leaves it: 0 everywhere while methods change is a read that fails.
    if rules.get("r_fmc") and not all(s in retooling_waived(key) for s in rules["r_fmc"]):
        changing = [r for r in rows if num(r, "n_pm") > 0]
        if changing and all(not num(r, "rt_all") for r in changing):
            out.append(f"  rt_*: 0 in all {len(changing)} snapshots with production-method changes under a setting "
                       "that keeps retooling: `has_modifier = pm_retooling` does not read in a building walk")
        else:
            out.append(f"  rt_all above 0 in {count(lambda r: num(r, 'rt_all') > 0)} of {n}")
    out.append(f"  bt_company_headquarter equals bg_company_headquarter in "
               f"{count(lambda r: num(r, 'bt_company_headquarter') == num(r, 'bg_company_headquarter'))} of {n}; "
               f"above 0 in {count(lambda r: num(r, 'bt_company_headquarter') > 0)}")
    # Electrification.
    flags = key.get("tech_flags_4", [])
    held = {t: count(lambda r, t=t: num(r, "h_" + t.replace("-", "_")) == 1) for t in flags}
    out.append(f"  H2: technology flags held: {held}")
    gen = "h_electrical_generation"
    out.append(f"  states with a power plant (pp_states) at most the country's states in "
               f"{count(lambda r: num(r, 'pp_states') <= num(r, 'states'))} of {n}; above 0 in "
               f"{count(lambda r: num(r, 'pp_states') > 0)}, of {count(lambda r: num(r, 'bg_power') > 0)} snapshots "
               "with power levels")
    plants = [r for r in rows if num(r, "bg_power") > 0]
    out.append(f"  Electricity made (elec_made) above 0 in {sum(1 for r in plants if num(r, 'elec_made') > 0)} of "
               f"{len(plants)} snapshots with power levels; bought (elec_used) above 0 in "
               f"{count(lambda r: num(r, 'elec_used') > 0)} of {n}")
    priced = [num(r, "elec_price") for r in rows if num(r, "elec_used") > 0]
    if priced:
        out.append(f"  Electricity price over base where bought: median {pct(priced, .5):.2f}, 10th-90th "
                   f"{pct(priced, .1):.2f}-{pct(priced, .9):.2f}"
                   + (" (exactly 1 everywhere: the state price read returns nothing)"
                      if all(abs(p - 1) < 0.0005 for p in priced) else ""))
    out.append(f"  Electricity price 0 where none is bought in {count(lambda r: num(r, 'elec_used') <= 0 and num(r, 'elec_price') == 0)}"
               f" of {count(lambda r: num(r, 'elec_used') <= 0)}")
    centres = [r for r in rows if num(r, "bt_urban_center") > 0]
    summed = sum(1 for r in centres if num(r, "uc_no_light") + num(r, "uc_gas_light") + num(r, "uc_elec_light")
                 == num(r, "bt_urban_center"))
    out.append(f"  street lighting: none + gas + electric = urban centre levels in {summed} of {len(centres)}; electric "
               f"lights without Electrical Generation in {sum(1 for r in centres if num(r, 'uc_elec_light') > 0 and num(r, gen) != 1)}")
    radios = [num(r, "radio_price") for r in rows]
    out.append(f"  radios: price over base median {pct(radios, .5):.2f} (10th-90th {pct(radios, .1):.2f}-"
               f"{pct(radios, .9):.2f}); buy orders above 0 in {count(lambda r: num(r, 'radio_buy') > 0)}, sell orders "
               f"in {count(lambda r: num(r, 'radio_sell') > 0)}, of {n}")
    # The queue by kind.
    gov_kinds = ("q_uni", "q_admin", "q_mil")
    out.append(f"  queue by kind: universities + administrations + military <= queue_gov in "
               f"{count(lambda r: sum(num(r, q) for q in gov_kinds) <= num(r, 'queue_gov'))} of {n}; each kind <= "
               f"queue_levels in {count(lambda r: all(num(r, q) <= num(r, 'queue_levels') for q in (*gov_kinds, 'q_infra', 'q_power')))}"
               f"; above 0: " + ", ".join(f"{q} {count(lambda r, q=q: num(r, q) > 0)}"
                                          for q in (*gov_kinds, "q_infra", "q_power")))
    queued = [r for r in rows if num(r, "queue_levels") > 0]
    if queued and all(not any(num(r, q) for q in (*gov_kinds, "q_infra", "q_power")) for r in queued):
        out.append("  queue by kind: every kind is 0 in every snapshot with a queue (level_after_queued_constructions "
                   "does not read in a building walk)")
    # Construction cost.
    scale = [num(r, "cc_scale") for r in rows]
    total = [num(r, "cc_total") for r in rows]
    out.append(f"  cost scaling (cc_scale) median {pct(scale, .5):.2f} (10th-90th {pct(scale, .1):.2f}-{pct(scale, .9):.2f}); "
               f"all modifiers (cc_total) median {pct(total, .5):.2f} (10th-90th {pct(total, .1):.2f}-{pct(total, .9):.2f})"
               + (" (cc_scale 0 everywhere: te_cc_scaling_factor does not read)" if all(not s for s in scale) else ""))
    # Bureaucracy.
    x_rows = [r for r in rows if isinstance((r.get("x") or {}).get("bur_inst"), (int, float))]
    if x_rows:
        inst = [r for r in x_rows if any(num(r, f) > 0 for f in r if f.startswith("in_"))]
        out.append(f"  bureaucracy: the institutions' cost (X7 bur_inst) at most bureaucracy used in "
                   f"{sum(1 for r in x_rows if r['x']['bur_inst'] <= num(r, 'bur_used') + 1)} of {len(x_rows)}; above 0 "
                   f"in {sum(1 for r in inst if r['x']['bur_inst'] > 0)} of {len(inst)} with an institution")
    else:
        out.append("  bureaucracy: no X7 line (the canary says whether the data function printed)")
    out.append("  bureaucracy modifiers non-zero: " + ", ".join(
        f"{f} {count(lambda r, f=f: num(r, f) != 0)}" for f in ("bur_add", "bur_mult", "bur_cost_add", "bur_inst_mult",
                                                                 "bur_pop_mult")) + f" of {n}")
    # Living standards and slack.
    sol_rows = [r for r in rows if isinstance((r.get("x") or {}).get("sol_lower"), (int, float))]
    if sol_rows:
        ordered = sum(1 for r in sol_rows
                      if r["x"]["sol_lower"] - 0.05 <= num(r, "sol") <= num(r["x"], "sol_upper") + 0.05)
        out.append(f"  strata's standard of living (X8): lower <= average <= upper in {ordered} of {len(sol_rows)}")
    else:
        out.append("  strata's standard of living: no X8 line (the canary says whether GetTrendValue printed)")
    out.append(f"  slack in [0, 1] with peasants <= slack in "
               f"{count(lambda r: 0 <= num(r, 'slack_peasants') <= num(r, 'slack') <= 1)} of {n}; above 0 in "
               f"{count(lambda r: num(r, 'slack') > 0)}")
    # The army census of versions 4 and 5, retired in version 6: a combat unit holds no variables, so it counted
    # nothing, and its fields are dropped from an older log's P2 line as it is read.
    if "unit_vars" in parsed.canary:
        out.append(f"  army census (versions 4 and 5): `CANARY unit_vars v={parsed.canary['unit_vars']}`; retired in "
                   "version 6, since a combat unit holds no variables (#2090): its u_* fields are not read")
    return out


def check_version_2(parsed: Parsed, key: dict, records: list[dict]) -> tuple[list[str], bool]:
    """Version 2's additions, each read here once: none of them had printed when it was written (2026-11-16)."""
    out, ok = ["version 2 additions:"], True
    # The W line.
    if parsed.world:
        first = parsed.world[min(parsed.world)]
        out.append(f"  world (W) lines: {len(parsed.world)}; the first: {first}")
        if all(not w.get("dn") for w in parsed.world.values()) and parsed.version() == 2:
            out.append("  W: dn is 0 in every line, as in every version-2 log: it counted with every_country, which "
                       "does not reach a decentralized nation (version 3 counts with every_decentralized_country)")
    else:
        out.append("  world (W) lines: NONE (the first prints in the month the probe arms)")
        ok = False
    # Law ends.
    ends = [e for e in parsed.events if e["event"] == "law_end"]
    if ends:
        how = Counter(e.get("how") for e in ends)
        names = key.get("law_end_how", [])
        shown = {(names[h - 1] if isinstance(h, int) and 0 < h <= len(names) else h): n for h, n in how.items()}
        out.append(f"  law ends by how they ended: {shown}; maximum setbacks: "
                   f"{dict(Counter(e.get('max') for e in ends))}")
        passes = sum(1 for e in parsed.events if e["event"] == "law_pass")
        if how.get(1, 0) != passes:
            out.append(f"  law_end how=passed {how.get(1, 0)} against {passes} law_pass lines (the pass mark is not "
                       "reaching the end hook)")
        if not any(isinstance(h, int) and h > 0 for h in how):
            ok = False
    else:
        out.append("  law ends: none yet")
    sets = sum(num(r, "n_law_set") for r in records)
    out.append(f"  laws set outside an enactment (n_law_set), all snapshots: {sets}")
    # Plays.
    plays = [e for e in parsed.events if e["event"] == "play"]
    if plays:
        types = key.get("play_types", [])
        named = Counter(types[e["type"] - 1] if isinstance(e.get("type"), int) and 0 < e["type"] <= len(types)
                        else e.get("type") for e in plays)
        out.append(f"  plays by type: {dict(named.most_common(8))}; initiator rank 0 in "
                   f"{sum(1 for e in plays if not e.get('rank'))} of {len(plays)}; serial 0 in "
                   f"{sum(1 for e in plays if not e.get('id'))}")
        if all(not e.get("type") for e in plays):
            out.append("  plays: type is 0 in every play (the type index did not evaluate in the play's scope)")
            ok = False
    else:
        out.append("  plays: none yet")
    zero_ids = sum(1 for e in parsed.events if not e.get("id"))
    out.append(f"  events with serial 0: {zero_ids} of {len(parsed.events)}")
    new = [r for r in records if any(f.startswith("im_") for f in r)]
    if new:
        # Institutions: the level can never be above the maximum the country may invest in.
        over = Counter()
        held = 0
        for r in new:
            for f in r:
                if f.startswith("in_") and num(r, f) > 0:
                    held += 1
                    if num(r, "im_" + f[3:]) < num(r, f):
                        over[f[3:]] += 1
        out.append(f"  institutions: level above investment_max in {sum(over.values())} of {held} held "
                   f"institutions{(': ' + str(dict(over.most_common(5)))) if over else ''}")
        if held and sum(over.values()) == held:
            out.append("  im_*: every maximum reads below its level (investment_max is not read)")
            ok = False
        # Units: the R line's shares add up to the army.
        unit_fields = list(key.get("unit_line", {}))
        armies = [r for r in new if num(r, "army") > 0]
        sums = [sum(num(r, f) for f in unit_fields) for r in armies]
        if sums:
            near = sum(1 for s in sums if abs(s - 1) <= 0.02)
            out.append(f"  units: the R line's shares add to 1 (within 0.02) in {near} of {len(sums)} armies; "
                       f"median sum {pct(sums, .5):.3f}")
        # Technologies.
        flags = [f for f in key.get("tech_flags", {}) if any(f in r for r in new)]
        held_any = Counter(f for r in new for f in flags if num(r, f) == 1)
        out.append(f"  technology flags held at least once: {len(held_any)} of {len(flags)}")
        # The construction purchase, recomputed from the snapshot.
        pairs_ = [(purchase_target(r), num(r, "cm_target")) for r in new if num(r, "cm_price") > 0]
        pairs_ = [(a, b) for a, b in pairs_ if a is not None]
        if pairs_:
            match = sum(1 for a, b in pairs_ if abs(a - b) <= max(0.011, 0.02 * abs(b)))
            out.append(f"  purchase recomputed from the snapshot matches cm_target in {match} of {len(pairs_)}"
                       + ("" if match >= 0.9 * len(pairs_) else " (a term is missing or misread: see purchase_target)"))
        bubbles = sum(1 for r in new if num(r, "bubble") > 0)
        out.append(f"  bubble pressure above 0 in {bubbles} of {len(new)}; cm_level_max above 0 in "
                   f"{sum(1 for r in new if num(r, 'cm_level_max') > 0)}")
    else:
        out.append("  no snapshot with the version-2 fields yet")
    lines, good = check_construction_sector(key, records)
    return out + lines, ok and good


def check_construction_sector(key: dict, records: list[dict]) -> tuple[list[str], bool]:
    """The O2 line's Construction Sector fields: each read against what the others say it must be."""
    out, ok = [], True
    rows = [r for r in records if "cs_low" in r]
    if not rows:
        return ["  Construction Sector fields: no snapshot carries them yet"], True
    sector = [r for r in rows if num(r, "bt_construction_sector") > 0]
    methods = list(key.get("construction_methods", {}))
    out.append(f"  Construction Sector: {len(sector)} of {len(rows)} snapshots hold a sector")
    if sector:
        def levels_of(r):
            return num(r, "bt_construction_sector")
        summed = sum(1 for r in sector if sum(num(r, m) for m in methods) == levels_of(r))
        order = sum(1 for r in sector if num(r, "cs_low") <= num(r, "cs_low80") <= levels_of(r))
        staffing = [num(r, "cs_staffed") / levels_of(r) for r in sector]
        out.append(f"  sector levels on a named method add to its levels in {summed} of {len(sector)}; under half "
                   f"<= under {100 * key.get('ai_expansion_staffing', 0.8):.0f}% <= levels in {order}")
        out.append(f"  sector staffing (cs_staffed over levels): median {pct(staffing, .5):.2f}, 10th-90th "
                   f"{pct(staffing, .1):.2f}-{pct(staffing, .9):.2f}; above 1 in {sum(1 for s in staffing if s > 1.01)}; "
                   f"subsidized in {sum(1 for r in sector if num(r, 'cs_sub') > 0)}")
        if summed == 0:
            out.append("  cs_pm_*: no sector's methods add up to its levels (the method read is wrong)")
        # A sector not all under half staffed has staff, so a 0 there everywhere is a read that returns nothing.
        staffed = [r for r in sector if num(r, "cs_low") < levels_of(r)]
        if staffed and all(not num(r, "cs_staffed") for r in staffed):
            out.append("  cs_staffed is 0 in every sector with staff (occupancy did not read as a value)")
            ok = False
    prices = [num(r, "cs_price") for r in rows]
    out.append(f"  construction good, price over base: median {pct(prices, .5):.3f}, 10th-90th "
               f"{pct(prices, .1):.3f}-{pct(prices, .9):.3f}; below base in {sum(1 for p in prices if p < 0.999)}")
    if all(abs(p - 1) < 0.0005 for p in prices):
        out.append("  cs_price is exactly 1 in every snapshot (the market read returns nothing)")
        ok = False
    for name in ("cs_buy", "cs_sell"):
        positive = sum(1 for r in rows if num(r, name) > 0)
        out.append(f"  {name} above 0 in {positive} of {len(rows)}"
                   + ("" if positive else " (the order read returns nothing; the price is not affected)"))
    sites = [r for r in rows if num(r, "bg_te_construction_market_bg") > 0]
    out.append(f"  Construction Sites: {len(sites)} snapshots hold one; under half staffed in "
               f"{sum(1 for r in sites if num(r, 'site_low') > 0)}")
    return out, ok


# te_construction_market_ai_values.txt's TE_CONSTRUCTION_MARKET_AI_RATE_GAIN (test_ai_probe.py runs both rules).
RATE_GAIN = 2.0


def purchase_target(r: dict):
    """te_construction_market_ai_purchase_target (common/script_values/te_construction_market_ai_values.txt)
    restated over a snapshot's fields, None where the snapshot lacks a term (version 1). Script `min = X` raises
    the value to X, `max = X` lowers it to X. A paused country buys nothing, whatever `cm_admin` reads: the purchase
    through the pause for a queued administration was removed on 2026-11-16, so a log from a build that still had it
    differs on the rows of a paused country with `cm_admin` 1. From version 5 the rate's terms (THE RATE, #1877) read
    the snapshot's `cm_reserve` and `cm_credit`; a log without them is from a build before the rate, whose rule they
    leave unchanged at nothing."""
    if "cm_level_max" not in r or num(r, "cm_price") <= 0:
        return None
    price = num(r, "cm_price")
    fixed, net, gold, debt = num(r, "fixed_income"), num(r, "net_fixed"), num(r, "gold_scaled"), num(r, "debt_scaled")
    queue, level_max = num(r, "queue_gov"), num(r, "cm_level_max")
    required, allowance = num(r, "cm_reserve"), num(r, "cm_credit")
    bureaucracy_buy = fixed * 0.2 / price
    if num(r, "paused") != 1 and queue > 0:
        factor = 1 + gold - debt
        factor += RATE_GAIN * max(0.0, allowance - debt)
        factor -= min(gold, required) + RATE_GAIN * max(0.0, required - gold)
        if num(r, "war") == 1 and gold < 0.5:
            factor -= 0.5 - gold
        if num(r, "bubble") >= 50 and gold < 0.3:
            factor -= 0.3 - gold
        value = max(net, 0) / price * max(factor, 0.1)
        whole = min(fixed * 0.05 / price, 10)
        floor = whole * min(max((gold - required) / 0.1, 0), 1)
        floor = max(floor, min(max(net, 0) / price, whole * 0.1))
        if num(r, "bur") < 0:
            floor += bureaucracy_buy
        return min(max(value, floor), queue * level_max)
    return 0.0


# --- report --------------------------------------------------------------------------------------------------------

def pct(values, q):
    values = sorted(values)
    if not values:
        return None
    pos = (len(values) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def spread(values, digits=1, scale=1.0) -> str:
    values = [v * scale for v in values if isinstance(v, (int, float))]
    if not values:
        return "-"
    return f"{pct(values, .5):.{digits}f} ({pct(values, .1):.{digits}f} to {pct(values, .9):.{digits}f}, n={len(values)})"


def share(records, test) -> str:
    records = list(records)
    if not records:
        return "-"
    hits = sum(1 for r in records if test(r))
    return f"{100 * hits / len(records):.0f}% ({hits}/{len(records)})"


def num(record: dict, field: str, default=0):
    value = record.get(field, default)
    return value if isinstance(value, (int, float)) else default


def series(records: list[dict]) -> dict[int, list[dict]]:
    by_id: dict[int, list[dict]] = defaultdict(list)
    for record in records:
        by_id[record["id"]].append(record)
    for rows in by_id.values():
        rows.sort(key=lambda r: r["k"])
    return by_id


# --- one row a country a year, and the construction readings to trust ---------------------------------------------

def once_a_year(records: list[dict]) -> tuple[list[dict], int]:
    """One record for each country object and calendar year (`y`): its later one, carrying the earlier's counters.

    Versions 1 and 2 reported a country at every twelfth of its monthly pulses, which are 30 days apart, so its
    report drifted five days earlier a year, and every six years or so it reported in January and again in December
    of one year: 3,237 of the 19,798 gaps between a country's reports in the first long run were 11 months, and 2 to
    6 countries a year reported twice (China in 1900 in the first two runs). Kept twice, such a country counts twice
    in that year's sums and cross-sections. The counters (`n_*`) are flows since the country's last report, so the
    earlier row's are added to the later's and no flow is lost. Version 3 reports each country once a calendar year,
    so its logs fold nothing. Returns the rows (in month order) and how many were folded into another."""
    kept: dict[tuple, dict] = {}
    folded = 0
    for r in sorted(records, key=lambda r: r["k"]):
        slot = (r["id"], r.get("y"))
        held = kept.get(slot)
        if held is None:
            kept[slot] = r
            continue
        folded += 1
        merged = dict(r)
        for name, value in held.items():
            if name.startswith("n_") and isinstance(value, (int, float)) and isinstance(merged.get(name), (int, float)):
                merged[name] += value
        kept[slot] = merged
    return sorted(kept.values(), key=lambda r: (r["k"], r["id"])), folded


# An X reading of construction that does not stand for the country's construction, found by the 2026-11-16 analysis
# of the first two long runs. Each is what the engine held at the instant of the snapshot, not a read the probe got
# wrong: every X figure is printed in one effect, with nothing between the reads that changes them, and the S lines
# printed in the same instant agree (in 95-99% of the unpaid readings the S line's income equals its fixed income, so
# the budget held no investment-pool transfer either; in 28 of the 31 idle readings `queue_days` reads the engine's
# "never", 2147483647, so the construction speed was 0 then). A snapshot is one week standing for a year, though,
# and these weeks are not the year: Great Britain's 1893-95 readings (1,464, 1,089 and 455 private points a week,
# no goods booked) came in years its counters show building at the usual rate. So they are left out of the
# construction figures, and `check` counts them.
X_BUILDING_POOL = 1_000_000          # an investment pool this large is spending: an idle reading is not idleness


def x_construction(r: dict) -> str:
    """'none' (no X construction line), 'unpaid' (private points used, no private construction goods booked), 'idle'
    (no construction capacity and none used on a country that is building: not paused, private levels queued, a
    pool of X_BUILDING_POOL or more), or 'ok'."""
    x = r.get("x") or {}
    used_priv = x.get("con_used_priv")
    if not isinstance(used_priv, (int, float)):
        return "none"
    if used_priv > 0 and x.get("con_goods_priv") == 0:
        return "unpaid"
    if (x.get("con_base") == 0 and not x.get("con_used") and num(r, "paused") != 1 and num(r, "queue_priv") > 0
            and num(r, "pool") >= X_BUILDING_POOL):
        return "idle"
    return "ok"


def valid_x(r: dict) -> bool:
    """An X construction reading to use (x_construction)."""
    return x_construction(r) == "ok"


def largest_by_year(records: list[dict], n: int = 20) -> dict[int, set[int]]:
    """The n largest economies (by GDP) of each year, as country serials: a set that moves from year to year."""
    by_year: dict[int, list[dict]] = defaultdict(list)
    for r in records:
        if isinstance(r.get("y"), int):
            by_year[r["y"]].append(r)
    return {year: {r["id"] for r in sorted(rows, key=lambda r: -num(r, "gdp"))[:n]} for year, rows in by_year.items()}


# A default within this many months of the same country's last default ending continues that episode: the engine
# moves a country in and out of default month to month (in the first long run half the gaps were 0 months, 89%
# were within 12, and 1,925 defaults made 317 episodes on this rule).
DEFAULT_EPISODE_GAP = 12
CADENCE_FROM_YEAR = 1890


def k_to_year(ticks: dict[int, dict]):
    """A function from a month count to its year, from the K lines (the nearest earlier month for a gap)."""
    ks = sorted(k for k, t in ticks.items() if isinstance(t.get("y"), int))
    years = [ticks[k]["y"] for k in ks]

    def year(k):
        if not ks:
            return None
        i = bisect.bisect_right(ks, k) - 1
        return years[max(i, 0)]
    return year


def first_k_of_year(ticks: dict[int, dict], year: int):
    ks = [k for k, t in ticks.items() if isinstance(t.get("y"), int) and t["y"] >= year]
    return min(ks) if ks else None


def default_episodes(events: list[dict], gap: int = DEFAULT_EPISODE_GAP) -> list[dict]:
    """The default events that open an episode: a country's first default, or one more than `gap` months after its
    last default ended. Countries are told apart by tag (version 1 logged some events with serial 0)."""
    out, last_end = [], {}
    for event in sorted((e for e in events if e["event"] in ("default", "default_end")), key=lambda e: e["k"]):
        tag = event["tag"]
        if event["event"] == "default_end":
            last_end[tag] = event["k"]
        elif tag not in last_end or event["k"] - last_end[tag] > gap:
            out.append(event)
    return out


def law_cadence(events: list[dict], ai: list[dict], strategies: list[str], from_k=None, include=None) -> list[dict]:
    """Law starts per idle month, by the political agenda held: the reference computation of the 2026-11-16
    baseline analysis (l1_cadence.py), here so a later run reads the same way.

    For each tag that reported: an idle spell runs from an enactment's end (or month 1) to the next start, or to
    the last month the tag reported (censored, no start). Each idle month counts against the agenda the tag held at
    that month (its latest snapshot at or before it; the first one before that); a start counts against the agenda
    held in its month. A start in the month an enactment ended counts with no idle month. `from_k` repeats the count
    for months from that one on. `include(tag, k)`, where given, keeps only the months (and starts) it accepts: the
    largest economies' months, for instance."""
    snaps: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for r in ai:
        snaps[r["tag"]].append((r["k"], num(r, "strat_political")))
    for rows in snaps.values():
        rows.sort(key=lambda pair: pair[0])     # by month only, stably: two objects can share a tag and a month
    keys = {tag: [k for k, _ in rows] for tag, rows in snaps.items()}

    def agenda(tag, k):
        rows = snaps[tag]
        i = bisect.bisect_right(keys[tag], k) - 1
        idx = rows[max(i, 0)][1]
        return strategies[idx - 1] if 0 < idx <= len(strategies) else "none"

    if not events:
        return []
    last_k = max(e["k"] for e in events)
    by_tag: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for e in events:
        if e["event"] == "law_end":
            by_tag[e["tag"]].append((e["k"], 0))
        elif e["event"] == "law_start":
            by_tag[e["tag"]].append((e["k"], 1))
    stats: dict[str, dict] = defaultdict(lambda: {"starts": 0, "months": 0, "starts_late": 0, "months_late": 0,
                                                  "waits": []})
    for tag in snaps:
        seq = sorted(by_tag.get(tag, []))
        enacting, free = bool(seq) and seq[0][1] == 0, 1
        spells = []
        for k, kind in seq:
            if kind == 1:
                if not enacting:
                    spells.append((free, k, True))
                enacting = True
            else:
                enacting, free = False, k
        if not enacting:
            spells.append((free, min(keys[tag][-1], last_k), False))
        for k0, k1, started in spells:
            months = range(k0, k1) if started else range(k0, k1 + 1)
            for m in months:
                if include is not None and not include(tag, m):
                    continue
                row = stats[agenda(tag, m)]
                row["months"] += 1
                if from_k is not None and m >= from_k:
                    row["months_late"] += 1
            if started and (include is None or include(tag, k1)):
                row = stats[agenda(tag, k1)]
                row["starts"] += 1
                row["waits"].append(k1 - k0)
                if from_k is not None and k1 >= from_k:
                    row["starts_late"] += 1
    return [{"agenda": name, **row} for name, row in sorted(stats.items(), key=lambda item: -item[1]["months"])]


def yearly_rate(first: dict, last: dict, field: str):
    a, b, months = num(first, field), num(last, field), last["k"] - first["k"]
    if a <= 0 or b <= 0 or months <= 0:
        return None
    return (b / a) ** (12 / months) - 1


# The scorecard's three lenses, in the order every table gives them. The owner judges a run first by the largest
# economies (2026-11-16): "I am most interested in ensuring the big economies grow - they are typically the
# competitors to the player. A game where only the big economies grow is better than one where only small economies
# grow. But by country count, most economies are small. So just a warning about measuring success by median country
# or anything like that."
TOP_N = 20
LENSES = [
    ("top", f"The {TOP_N} largest AI economies of the decade (by GDP): medians, with the 10th and 90th percentiles"),
    ("world", "All AI countries, weighted by GDP: medians become GDP-weighted means, shares become shares of GDP, "
              "ratios become the ratio of the totals, and counts a year become totals a year"),
    ("all", "The typical country: every AI country, medians (most of them are small)"),
]
RANK_BANDS = [
    ("great", ["great_power"]), ("major", ["major_power"]), ("minor", ["minor_power"]),
    ("insignificant", ["insignificant_power"]),
    ("unrecognized", ["unrecognized_major_power", "unrecognized_regional_power", "unrecognized_power"]),
]


def gdp(record: dict) -> float:
    return max(num(record, "gdp"), 0)


def weighted(pairs_, digits=1, scale=1.0) -> str:
    """The GDP-weighted mean of (value, record) pairs."""
    pairs_ = [(v, r) for v, r in pairs_ if isinstance(v, (int, float))]
    weight = sum(gdp(r) for _, r in pairs_)
    if not pairs_ or weight <= 0:
        return "-"
    return f"{sum(v * gdp(r) for v, r in pairs_) / weight * scale:.{digits}f}"


def gdp_share(records, test) -> str:
    records = list(records)
    total = sum(gdp(r) for r in records)
    if not records or total <= 0:
        return "-"
    return f"{100 * sum(gdp(r) for r in records if test(r)) / total:.0f}% of GDP"


class Col:
    """A scorecard column, read through each lens (LENSES).

    value(r)            a figure per snapshot: its median (or mean, `mean=True`); weighted by GDP, or summed a year
                        (`total=True`) through the world lens. None leaves the snapshot out.
    test(r)             a share of snapshots; of GDP through the world lens.
    ratio=(top, bottom) the median of a ratio per snapshot; the ratio of the totals through the world lens.
    custom(rows)        a string from the rows, "-" through the world lens.
    world(rows)         replaces any of these through the world lens.
    among(r)            keeps only the snapshots it accepts, through every lens.
    """

    def __init__(self, name, value=None, *, test=None, ratio=None, custom=None, world=None, digits=1, scale=1.0,
                 mean=False, total=False, among=None):
        self.name, self.value, self.test, self.ratio, self.custom, self.world = name, value, test, ratio, custom, world
        self.digits, self.scale, self.mean, self.total, self.among = digits, scale, mean, total, among

    def cell(self, rows: list[dict], lens: str) -> str:
        if self.among:
            rows = [r for r in rows if self.among(r)]
        if lens == "world" and self.world is not None:
            return str(self.world(rows))
        if self.custom:
            return "-" if lens == "world" else str(self.custom(rows))
        if self.test:
            return gdp_share(rows, self.test) if lens == "world" else share(rows, self.test)
        if self.ratio:
            top, bottom = self.ratio
            usable = [r for r in rows if isinstance(bottom(r), (int, float)) and bottom(r) > 0
                      and isinstance(top(r), (int, float))]
            if lens == "world":
                below = sum(bottom(r) for r in usable)
                return f"{sum(top(r) for r in usable) / below * self.scale:.{self.digits}f}" if below else "-"
            return spread([top(r) / bottom(r) for r in usable], self.digits, self.scale)
        values = [(self.value(r), r) for r in rows]
        values = [(v, r) for v, r in values if isinstance(v, (int, float))]
        if lens == "world":
            if self.total:
                years = len({r["y"] for _, r in values})
                return f"{sum(v for v, _ in values) / years * self.scale:.{self.digits}f}" if years else "-"
            return weighted(values, self.digits, self.scale)
        if self.mean:
            return f"{statistics.fmean(v for v, _ in values) * self.scale:.{self.digits}f}" if values else "-"
        return spread([v for v, _ in values], self.digits, self.scale)


def field(name: str):
    return lambda r: num(r, name)


def logged(name: str, fn):
    """fn(r) where the snapshot's probe version logged the field, else None (a version-1 log has none of
    version 2's fields, and a 0 there would read as a real figure)."""
    return lambda r: fn(r) if name in r else None


def report(parsed: Parsed, key: dict, bucket_years: int = 10, cadence_from: int = CADENCE_FROM_YEAR) -> str:
    records, folded = once_a_year([r for r in parsed.records() if "y" in r])
    out: list[str] = []
    if not records:
        return "No snapshots with a year yet.\n"
    world = [r for r in records if num(r, "type") != key["country_types"].index("decentralized") + 1]
    ai = [r for r in world if num(r, "ai") == 1]
    run_years = sorted({r["y"] for r in records})
    out.append(f"# AI probe scorecard: {run_years[0]} to {run_years[-1]}")
    out.append("")
    out.append(f"{len(records)} snapshots of {len({r['id'] for r in records})} countries; {len(ai)} are AI countries "
               "that are not decentralized nations, which is what every table below counts. Each country counts once "
               "a calendar year"
               + (f": {folded} reports that fell in a year the country had already reported in (versions 1 and 2 "
                  "drift) were folded into its later one, their counters added to it." if folded else "."))
    out.append("")
    out.append(f"**A run is judged first by the largest economies.** Every table gives the {TOP_N} largest AI "
               "economies of each decade first, then all AI countries weighted by GDP, and only then the typical "
               "country, which is small: most AI countries are tiny unrecognized ones, so a median over countries "
               "says little about the competitors a player meets.")
    if not ai:
        out.append("")
        out.append("No AI country has reported yet.")
        return "\n".join(out) + "\n"
    by_id = series(ai)
    ranks = key["ranks"]
    year_of = k_to_year(parsed.ticks)

    def bucket_of(year):
        return year - year % bucket_years

    def label_of(start):
        return f"{start}s" if bucket_years == 10 else f"{start}-{start + bucket_years - 1}"

    bucket_rows: dict[int, list[dict]] = defaultdict(list)
    for r in ai:
        bucket_rows[bucket_of(r["y"])].append(r)

    def buckets():
        for start in sorted(bucket_rows):
            yield label_of(start), bucket_rows[start]

    # The largest economies of each decade: the ids with the highest median GDP over their snapshots in it.
    top_ids: dict[int, set[int]] = {}
    for start, rows in bucket_rows.items():
        gdps = defaultdict(list)
        for r in rows:
            gdps[r["id"]].append(gdp(r))
        ranked = sorted(gdps, key=lambda ident: -statistics.median(gdps[ident]))
        top_ids[start] = set(ranked[:TOP_N])
    top_tags = {(r["tag"], start) for start, rows in bucket_rows.items() for r in rows if r["id"] in top_ids[start]}

    def top(rows):
        return [r for r in rows if r["id"] in top_ids[bucket_of(r["y"])]]

    def lens_rows(rows, lens):
        return top(rows) if lens == "top" else rows

    def table(title: str, columns: list[Col], note: str = ""):
        out.append("")
        out.append(f"## {title}")
        if note:
            out.append("")
            out.append(note)
        for lens, heading in LENSES:
            out.append("")
            out.append(f"**{heading}**")
            out.append("")
            out.append("| Years | " + " | ".join(col.name for col in columns) + " |")
            out.append("|---|" + "---|" * len(columns))
            for label, rows in buckets():
                chosen = lens_rows(rows, lens)
                out.append(f"| {label} | " + " | ".join(col.cell(chosen, lens) for col in columns) + " |")

    def rates(rows, fn):
        """(yearly growth of fn, the country's first snapshot) for each country with two snapshots in the rows."""
        ids = {r["id"] for r in rows}
        chosen = {id(r) for r in rows}
        out_ = []
        for ident in ids:
            mine = [r for r in by_id[ident] if id(r) in chosen]
            if len(mine) >= 2 and mine[-1]["k"] > mine[0]["k"]:
                a, b = fn(mine[0]), fn(mine[-1])
                if a and b and a > 0 and b > 0:
                    out_.append(((b / a) ** (12 / (mine[-1]["k"] - mine[0]["k"])) - 1, mine[0]))
        return out_

    def per_head(r):
        return num(r, "gdp") / num(r, "pop") if num(r, "pop") > 0 else None

    def growth(fn):
        return Col("", custom=lambda rows: spread([v for v, _ in rates(rows, fn)], 2, 100),
                   world=lambda rows: weighted(rates(rows, fn), 2, 100))

    def named(name, col):
        col.name = name
        return col

    def totals(top_fn, bottom_fn, digits=1, scale=1.0):
        """The ratio of two totals over the rows (the world lens of a per-country ratio)."""
        def run(rows):
            usable = [r for r in rows if isinstance(bottom_fn(r), (int, float)) and isinstance(top_fn(r), (int, float))]
            below = sum(bottom_fn(r) for r in usable)
            return f"{sum(top_fn(r) for r in usable) / below * scale:.{digits}f}" if below else "-"
        return run

    # Event counts a snapshot: the events of the snapshot's tag in its year.
    def event_rate(events, digits=3):
        by = Counter((e["tag"], year_of(e["k"])) for e in events)
        value = (lambda r: by[(r["tag"], r["y"])]) if parsed.ticks else (lambda r: None)
        return dict(value=value, mean=True, total=True, digits=digits)

    # --- the headline ----------------------------------------------------------------------------------------------
    out.append("")
    out.append(f"## The headline: the {TOP_N} largest economies against the rest")
    out.append("")
    out.append(f"| Years | GDP growth, % a year, {TOP_N} largest (median) | GDP growth, GDP-weighted, all | "
               f"GDP per head growth, {TOP_N} largest | GDP growth, the rest (median) | "
               f"{TOP_N} largest, share of AI GDP | Technologies, {TOP_N} largest (median) |")
    out.append("|---|---|---|---|---|---|---|")
    for label, rows in buckets():
        biggest = top(rows)
        chosen = {id(r) for r in biggest}
        rest = [r for r in rows if id(r) not in chosen]
        total = sum(gdp(r) for r in rows)
        big_share = f"{100 * sum(gdp(r) for r in biggest) / total:.0f}%" if total else "-"
        out.append(f"| {label} | {spread([v for v, _ in rates(biggest, field('gdp'))], 2, 100)} | "
                   f"{weighted(rates(rows, field('gdp')), 2, 100)} | "
                   f"{spread([v for v, _ in rates(biggest, per_head)], 2, 100)} | "
                   f"{spread([v for v, _ in rates(rest, field('gdp'))], 2, 100)} | {big_share} | "
                   f"{spread([num(r, 'techs') for r in biggest], 0)} |")
    newest_top = sorted({r["tag"] for r in top(list(buckets())[-1][1])})
    out.append("")
    out.append(f"The {TOP_N} largest in the last decade read: {', '.join(newest_top)}.")

    def band_of(r):
        name = ranks[num(r, "rank") - 1] if 0 < num(r, "rank") <= len(ranks) else "none"
        return next((band for band, members in RANK_BANDS if name in members), "other")

    out.append("")
    out.append("## GDP growth by rank band, % a year (median of countries)")
    out.append("")
    out.append("| Years | " + " | ".join(band for band, _ in RANK_BANDS) + " |")
    out.append("|---|" + "---|" * len(RANK_BANDS))
    for label, rows in buckets():
        cells = [spread([v for v, _ in rates([r for r in rows if band_of(r) == band], field("gdp"))], 2, 100)
                 for band, _ in RANK_BANDS]
        out.append(f"| {label} | " + " | ".join(cells) + " |")

    # --- 1. growth -------------------------------------------------------------------------------------------------
    table("1. Economic growth", [
        named("GDP growth, % a year", growth(field("gdp"))),
        named("GDP per head growth, % a year", growth(per_head)),
        Col("GDP per head", lambda r: per_head(r) or None, digits=2, world=totals(field("gdp"), field("pop"), 2)),
        Col("Standard of living", field("sol")),
        Col("Peasants, % of pops", field("peasants"), digits=0, scale=100),
        Col("Building levels (world: total)", field("levels"), digits=0, total=True),
    ])
    table("1a. The means of growth: construction and investment", [
        Col("Construction sector levels (world: total)", field("bt_construction_sector"), digits=0, total=True),
        Col("No construction sector", test=lambda r: num(r, "bt_construction_sector") == 0),
        Col("Queued levels (world: total)", field("queue_levels"), digits=0, total=True),
        Col("Empty queue", test=lambda r: num(r, "queue_levels") == 0),
        Col("Built + expanded a year", lambda r: num(r, "n_built") + num(r, "n_expanded"), digits=0, total=True),
        Col("Of which government", field("n_built_gov"), digits=0, total=True),
        Col("Investment pool, weeks of income", ratio=(field("pool"), field("income")), digits=1),
        Col("Method changes a year", field("n_pm"), digits=0, total=True),
    ])

    def outside_construction(r):
        return num(r, "bg_manufacturing") - num(r, "bg_construction")

    table("1c. Staffing, retooling and old methods (shares of levels, %)", [
        Col("Manufacturing incl. Construction Sectors, under half staffed",
            ratio=(field("low_mfg"), field("bg_manufacturing")), digits=0, scale=100),
        Col("Manufacturing excl. Construction Sectors, under half staffed",
            ratio=(logged("low_mfg_nc", field("low_mfg_nc")), logged("low_mfg_nc", outside_construction)),
            digits=0, scale=100),
        Col("Construction Sector levels, share of manufacturing", ratio=(field("bg_construction"),
                                                                       field("bg_manufacturing")), digits=0, scale=100),
        Col("Manufacturing retooling", ratio=(field("rt_mfg"), field("bg_manufacturing")), digits=0, scale=100),
        Col("Power under half staffed", ratio=(field("low_power"), field("bg_power")), digits=0, scale=100),
        Col("Infrastructure under half staffed", ratio=(field("low_infra"), field("bg_infrastructure")), digits=0,
            scale=100),
        Col("Mines under half staffed", ratio=(field("low_mine"), field("bg_mining")), digits=0, scale=100),
        Col("All levels retooling", ratio=(field("rt_all"), field("levels")), digits=0, scale=100),
        Col("All levels subsidized", ratio=(field("sub_all"), field("levels")), digits=0, scale=100),
        Col("Urban centers with no street lighting", ratio=(field("uc_no_light"), field("bt_urban_center")),
            digits=0, scale=100),
        Col("Administrations on the first method", ratio=(field("ga_simple"), field("bt_government_administration")),
            digits=0, scale=100),
    ], note="The mod puts the Construction Sector under bg_heavy_industry, so the first column counts idle "
            "sectors as idle manufacturing; the second (version 2) leaves them out.")

    # Version 2: the sector itself (gen_ai_probe.py, CONSTRUCTION_SECTOR).
    methods = list(key.get("construction_methods", {}))
    gate = key.get("ai_expansion_staffing", 0.8)

    def has_sector(r):
        return "cs_low" in r and num(r, "bt_construction_sector") > 0

    def sector_share(name):
        return Col("", ratio=(field(name), field("bt_construction_sector")), digits=0, scale=100, among=has_sector)

    def method_mix(rows):
        totals_ = [sum(num(r, m) for r in rows) for m in methods]
        whole = sum(totals_)
        return "/".join(f"{100 * t / whole:.0f}" for t in totals_) if whole else "-"

    def site_share(name):
        return Col("", ratio=(field(name), field("bg_te_construction_market_bg")), digits=0, scale=100,
                   among=lambda r: "site_low" in r and num(r, "bg_te_construction_market_bg") > 0)

    if methods:
        table("1f. The Construction Sector itself: staffing, subsidies, methods and the good's price", [
            Col("Sector levels (world: total)", field("bt_construction_sector"), digits=0, total=True,
                among=lambda r: "cs_low" in r),
            named("Under half staffed, % of levels", sector_share("cs_low")),
            named(f"Under {100 * gate:.0f}% staffed (the AI's expansion gate), % of levels", sector_share("cs_low80")),
            named("Mean staffing, % (level-weighted)", sector_share("cs_staffed")),
            named("Subsidized, % of levels", sector_share("cs_sub")),
            Col("Levels by method, % (" + "/".join(m[6:] for m in methods) + ")", custom=method_mix,
                world=method_mix, among=has_sector),
            Col("Construction good, price over base", field("cs_price"), digits=2, among=lambda r: "cs_price" in r),
            Col("Sell orders / buy orders", ratio=(field("cs_sell"), field("cs_buy")), digits=2,
                among=lambda r: "cs_buy" in r),
            named("Construction Sites under half staffed, % of site levels", site_share("site_low")),
            named(f"Sites under {100 * gate:.0f}% staffed, %", site_share("site_low80")),
        ], note=f"Vanilla's AI expands no building under {100 * gate:.0f}% staffed unless it hired the week before "
                "(00_ai.txt, PRODUCTION_BUILDING_LOW_EMPLOYMENT_THRESHOLD). The price and the orders are the "
                "country's market's, which a country in another's market shares; the world lens's orders count a "
                "shared market once for each of its countries. The method mix is of all the rows' levels in each "
                "lens. Construction Sites are the market's own building, not the sector.")
    table("1d. The government's purchase of construction (the construction market)", [
        Col("Buying any", test=lambda r: num(r, "cm_public") > 0),
        Col("Points a week, where buying (world: total)", lambda r: num(r, "cm_public") or None, digits=2,
            total=True),
        Col("Construction paused", test=lambda r: num(r, "paused") == 1),
        Col("No government level queued", test=lambda r: num(r, "queue_gov") == 0),
        Col("Debt at 40% of limit or more", test=lambda r: num(r, "debt_scaled") >= 0.4),
        Col("Reserves under 10% of limit", test=lambda r: num(r, "gold_scaled") < 0.1 and num(r, "debt_scaled") == 0),
        Col("Tax, % of GDP", ratio=(field("tax_income"), field("gdp")), digits=1, scale=5200),
        Col("Script expenses, % of GDP", ratio=(field("ux_all"), field("gdp")), digits=1, scale=5200),
        Col("Banking brake on (bubble pressure 50+, reserves under 0.3)", among=lambda r: "bubble" in r,
            test=lambda r: num(r, "bubble") >= 50 and num(r, "gold_scaled") < 0.3),
    ], note="The world lens's points a week are the total the AI governments buy, over the weeks sampled.")

    episodes = default_episodes(parsed.events)
    table("1b. Solvency", [
        Col("In default", test=lambda r: num(r, "default") == 1),
        Col(f"Default episodes started a year (a default {DEFAULT_EPISODE_GAP}+ months after the last ended)",
            **event_rate(episodes)),
        Col("Defaults a year (every default event)", **event_rate([e for e in parsed.events
                                                                     if e["event"] == "default"])),
        Col("Declared bankrupt (10 years)", test=lambda r: num(r, "bankrupt") == 1),
        Col("Taking loans", test=lambda r: num(r, "loans") == 1),
        Col("Debt, share of limit", field("debt_scaled"), digits=2),
        Col("Reserves, share of limit", field("gold_scaled"), digits=2),
        Col("Income / expenses", ratio=(field("income"), field("expenses")), digits=2),
        Col("Military, share of spending", field("mil_share"), digits=0, scale=100,
            world=totals(field("mil_expenses"), field("expenses"), 0, 100)),
        Col("Bureaucracy below 0", test=lambda r: num(r, "bur") < 0),
    ], note="Defaults and episodes are a mean a country-year (the world lens: a total a year). The engine moves a "
            "country in and out of default month to month, so episodes are the figure to read.")

    def xnum(record, name):
        value = (record.get("x") or {}).get(name)
        return value if isinstance(value, (int, float)) else None

    def x_field(name):
        return lambda r: xnum(r, name)

    def of_gdp(name, construction=False):
        """A weekly budget line of the X records against yearly GDP, %; a construction line from the readings
        valid_x keeps."""
        col = Col("", ratio=(x_field(name), lambda r: gdp(r) / 52 if xnum(r, name) is not None else None),
                  digits=1, scale=100)
        col.among = valid_x if construction else None
        return col

    table("1e. Where the government's money goes (share of GDP, %)", [
        named("Government goods", of_gdp("gov_goods")),
        named("Government wages", of_gdp("gov_wages")),
        named("Military goods", of_gdp("mil_goods")),
        named("Military wages", of_gdp("mil_wages")),
        named("Subsidies", of_gdp("subsidies")),
        named("Welfare", of_gdp("welfare")),
        named("Construction goods, government", of_gdp("con_goods_gov", construction=True)),
        Col("All expenses", ratio=(field("expenses"), field("gdp")), digits=1, scale=5200),
        Col("All income", ratio=(field("income"), field("gdp")), digits=1, scale=5200),
    ])

    table("1g. Construction points a week (the interface's figures)", [
        Col("Points used (world: total)", x_field("con_used"), digits=0, total=True, among=valid_x),
        Col("Private points (world: total)", x_field("con_used_priv"), digits=0, total=True, among=valid_x),
        Col("Government points (world: total)", x_field("con_used_gov"), digits=0, total=True, among=valid_x),
        Col("Private points, share of points used, %", ratio=(x_field("con_used_priv"), x_field("con_used")), digits=0,
            scale=100, among=valid_x),
        Col("Unused, share of the base, %", ratio=(x_field("con_unused"), x_field("con_base")), digits=0, scale=100,
            among=valid_x),
        Col("Private construction goods per private point", ratio=(x_field("con_goods_priv"), x_field("con_used_priv")),
            digits=0, among=valid_x),
        Col("Readings left out (unpaid or idle)", test=lambda r: x_construction(r) in ("unpaid", "idle"),
            among=lambda r: x_construction(r) != "none"),
    ], note="A snapshot's construction figures are one week's. Two kinds of week are left out of every column but "
            "the last, which counts them: private points used with no private construction goods booked, and no "
            "construction at all on a country that is building (not paused, private levels queued, a pool of "
            f"{X_BUILDING_POOL:,} or more). Both are what the engine held that week, not a failed read, but they are "
            "not the year (`x_construction`). The world lens's totals are a year's sum over the readings kept.")

    # Version 3: the banking cycle (gen_ai_probe.py, BANK_PHASES). A crash falling in different years in two runs
    # confounds their comparison, so this table says how much of each lens's GDP was in a crisis.
    bank_names = key.get("bank_phases", [])
    if any("bank_phase" in r for r in ai):
        def banked(r):
            return "bank_phase" in r

        def in_crisis(r):
            return num(r, "bank_phase") in (1, 2)

        def gdp_in(test):
            return Col("", custom=lambda rows: gdp_share(rows, test), world=lambda rows: gdp_share(rows, test),
                       among=banked)

        def phase_mix(rows):
            counts = Counter(num(r, "bank_phase") for r in rows if num(r, "bank_phase") > 0)
            whole = sum(counts.values())
            return ", ".join(f"{bank_names[p - 1] if 0 < p <= len(bank_names) else p} {100 * n / whole:.0f}%"
                             for p, n in sorted(counts.items())) if whole else "-"
        table("1h. The banking cycle", [
            named("In a panic or downturn at the snapshot, share of GDP", gdp_in(in_crisis)),
            named("A crash in the year before the snapshot, share of GDP",
                  gdp_in(lambda r: num(r, "bank_crashed") == 1)),
            named("A crash, or a panic or downturn, in the year: share of GDP",
                  gdp_in(lambda r: in_crisis(r) or num(r, "bank_crashed") == 1 or num(r, "n_bank_down") > 0)),
            Col("Months in a panic or downturn a year, mean", field("n_bank_down"), mean=True, digits=2,
                among=banked),
            Col("Cycle running", test=lambda r: num(r, "bank_phase") > 0, among=banked),
            Col("Cycle value, where running", field("bank_cycle"), digits=0,
                among=lambda r: banked(r) and num(r, "bank_phase") > 0),
            Col("Phases, where running", custom=phase_mix, world=phase_mix, among=banked),
        ], note="From version 3. A cycle runs once a country has a stock exchange and an Urban Center of level 5 "
                "(te_banking_cycle_unlocked) and the banking rule is on. Panic is a cycle value under 10, downturn "
                "under 25. A crash marks the country for 365 days (banking_crashed_last_year), and the months count "
                "the country's monthly pulses in a panic or downturn since its last snapshot, so the third column "
                "says whether the year held a crisis at all. Every share is of the lens's GDP, the 20 largest's "
                "first.")

    # Version 4 (gen_ai_probe.py, version_4_fields): the queue by kind, the cost of construction, labour.
    def v4(r):
        return "pp_states" in r

    if any(v4(r) for r in ai):
        def of_gov(name):
            return Col("", ratio=(field(name), field("queue_gov")), digits=0, scale=100, among=v4)

        def gov_rest(r):
            return max(num(r, "queue_gov") - num(r, "q_uni") - num(r, "q_admin") - num(r, "q_mil"), 0)

        table("1i. The construction queue by kind", [
            Col("Government levels queued (world: total)", field("queue_gov"), digits=0, total=True, among=v4),
            Col("No government level queued", test=lambda r: num(r, "queue_gov") == 0, among=v4),
            named("Universities, % of the government queue", of_gov("q_uni")),
            named("Administrations, %", of_gov("q_admin")),
            named("Military buildings, %", of_gov("q_mil")),
            Col("The rest of the government queue, %", ratio=(gov_rest, field("queue_gov")), digits=0, scale=100,
                among=v4),
            Col("Infrastructure, % of all queued levels", ratio=(field("q_infra"), field("queue_levels")), digits=0,
                scale=100, among=v4),
            Col("Power plants, % of all queued levels", ratio=(field("q_power"), field("queue_levels")), digits=0,
                scale=100, among=v4),
        ], note="From version 4. Each kind is the queued levels of its buildings (their levels once the queued "
                "constructions finish, less their levels). Universities, administrations and military buildings are "
                "government buildings, set against the government queue (the rest is what else it queued: "
                "infrastructure, power plants, anything else). Infrastructure and power plants can be in either queue, "
                "so they are set against all queued levels. A share is the median of each country's share (the world "
                "lens: the ratio of the totals), so the columns need not add up.")

        table("1j. The cost of construction", [
            Col("Cost scaling (S x d)", field("cc_scale"), digits=2, among=v4),
            Col("All construction-cost modifiers", field("cc_total"), digits=2, among=v4),
            Col("Construction good, price over base", field("cs_price"), digits=2, among=v4),
            Col("All cost modifiers x price (the power plant's break-even multiple)",
                lambda r: num(r, "cc_total") * num(r, "cs_price") if v4(r) and "cs_price" in r else None, digits=2),
            Col("Above the early plant's break-even (3.4)",
                test=lambda r: num(r, "cc_total") * num(r, "cs_price") > 3.4, among=v4),
            Col("Small-economy factor below 1 (cost scaling under 1)", test=lambda r: num(r, "cc_scale") < 0.999,
                among=v4),
        ], note="From version 4. A construction point's cost over its base: the cost scaling in force (its own "
                "factor times the small-economy factor, te_cc_scaling_factor) and every construction-cost modifier "
                "with it (te_cc_total_factor). docs/systems/mod_systems/construction.md (Maintenance tiers) measures a "
                "power plant's profit against the multiple of base construction cost, cost scaling times the "
                "construction price: the early plant breaks even at about 3.4 and the coal-fired plant at 9.0 since "
                "the graded maintenance tiers. The W line names the small-economy rule's setting.")

        def unemployed(r):
            return max(num(r, "slack") - num(r, "slack_peasants"), 0) if v4(r) else None

        def x_sol(name):
            return lambda r: xnum(r, name)

        table("1k. Labour and living standards", [
            Col("Slack: peasants and unemployed, % of the workforce", field("slack"), digits=1, scale=100, among=v4),
            Col("Unemployed, % of the workforce", unemployed, digits=1, scale=100),
            Col("Peasants, % of the workforce", field("slack_peasants"), digits=1, scale=100, among=v4),
            Col("Standard of living, lower strata", x_sol("sol_lower"), digits=1),
            Col("Middle strata", x_sol("sol_middle"), digits=1),
            Col("Upper strata", x_sol("sol_upper"), digits=1),
            Col("All pops", field("sol"), digits=1, among=v4),
        ], note="From version 4. The slack is the cost scaling's yearly reading of the states' pop walks "
                "(te_cc_slack, te_cc_peasants): the workforce with no market workplace over the workforce walked. "
                "The strata's standard of living is the latest value of the Politics panel's trend lines (X8). No "
                "script read or data function gives an average wage.")

    # --- 2. technology ---------------------------------------------------------------------------------------------
    table("2. Technology", [
        Col("Technologies", field("techs"), digits=0),
        Col("Leader", custom=lambda rows: max((num(r, "techs") for r in rows), default="-"),
            world=lambda rows: max((num(r, "techs") for r in rows), default="-")),
        Col("Acquired a year", field("n_tech"), digits=1),
        Col("Innovation", field("innovation"), digits=0),
        Col("Innovation, share of its cap, %", ratio=(x_field("innovation"), x_field("innovation_max")), digits=0,
            scale=100),
        Col("University levels (world: total)", field("bt_university"), digits=0, total=True),
        Col("No university", test=lambda r: num(r, "bt_university") == 0),
        Col("Researching nothing", test=lambda r: num(r, "researching") == 0),
        Col("Literacy, %", field("lit"), digits=0, scale=100),
        Col("Schools at the maximum it may invest in (those with schools)",
            test=lambda r: num(r, "in_schools") >= num(r, "im_schools"),
            among=lambda r: num(r, "im_schools") > 0),
    ], note="The schools column reads version 2's J line (the institution's maximum investment), so a version-1 "
            "log shows -.")

    # The flags this log's version printed (version 4's H2 is not in an older log).
    flags = {name: tech for name, tech in key.get("tech_flags", {}).items() if any(name in r for r in ai)}
    flagged = [r for r in ai if any(f in r for f in flags)]
    if key.get("tech_flags"):
        out.append("")
        out.append(f"## 2a. Specific technologies: share holding each, %, the {TOP_N} largest / every AI country")
        out.append("")
        if not flagged:
            out.append("Not logged by this log's probe version (version 2 adds the H line).")
        else:
            labels = [label for label, _ in buckets()]
            out.append("| Technology | " + " | ".join(labels) + " |")
            out.append("|---|" + "---|" * len(labels))
            for name, tech in flags.items():
                cells = []
                for _, rows in buckets():
                    rows = [r for r in rows if name in r]
                    biggest = top(rows)
                    if not rows:
                        cells.append("-")
                        continue
                    a = f"{100 * sum(num(r, name) for r in biggest) / len(biggest):.0f}" if biggest else "-"
                    cells.append(f"{a} / {100 * sum(num(r, name) for r in rows) / len(rows):.0f}")
                out.append(f"| {tech} | " + " | ".join(cells) + " |")

    # 2b. Electrification (version 4's P and H2 lines).
    electrified = [r for r in ai if "pp_states" in r]
    if not electrified:
        out.append("")
        out.append("## 2b. Electrification")
        out.append("")
        out.append("Not logged by this log's probe version (version 4 adds the P and H2 lines).")
    else:
        def p4(r):
            return "pp_states" in r

        def has(tech):
            return Col("", test=lambda r: num(r, "h_" + tech) == 1, among=p4)

        def lit(name):
            return Col("", ratio=(field(name), field("bt_urban_center")), digits=0, scale=100, among=p4)

        table("2b. Electrification", [
            Col("Power levels (world: total)", field("bg_power"), digits=0, total=True, among=p4),
            Col("Power levels queued (world: total)", field("q_power"), digits=0, total=True, among=p4),
            Col("States with a power plant, %", ratio=(field("pp_states"), field("states")), digits=0, scale=100,
                among=p4),
            Col("No power plant", test=lambda r: num(r, "pp_states") == 0, among=p4),
            Col("Electricity made a week (world: total)", field("elec_made"), digits=0, total=True, among=p4),
            Col("Electricity price over base, where bought", lambda r: num(r, "elec_price") if p4(r) and
                num(r, "elec_used") > 0 else None, digits=2),
            named("Holding Electrical Generation", has("electrical_generation")),
            named("Holding Steam Turbine", has("steam_turbine")),
            named("Holding Radio", has("radio")),
            named("Urban centres unlit, % of levels", lit("uc_no_light")),
            named("On gas, %", lit("uc_gas_light")),
            named("On electric, %", lit("uc_elec_light")),
            Col("Radios, price over base", field("radio_price"), digits=2, among=p4),
            Col("Radios, sell orders / buy orders", ratio=(field("radio_sell"), field("radio_buy")), digits=2,
                among=p4),
        ], note="From version 4. Power levels are bg_power's (the coal and oil plant, hydro, nuclear, renewable and "
                "fusion plants), queued levels in either queue. A state has a power plant when any building that "
                "makes Electricity stands there or is being built (te_state_has_a_power_plant). Electricity is a "
                "local good, so it is read in each state and summed, its price weighted by what each state buys. "
                "Electric street lights take Electricity (vanilla's required_input_goods) and Electrical Generation; "
                "electric counts the mod's later lights too. The radios market is the country's (a shared market's "
                "for a country in one): the units below take radios as upkeep.")
        blocked = [f for f in ("u_squad_infantry", "u_mechanized_infantry", "u_siege_artillery", "u_light_tanks")
                   if f in key.get("unit_info", {})]
        latest_p = {}
        for r in bucket_rows[max(bucket_rows)]:
            if p4(r) and num(r, "army") > 0 and (r["id"] not in latest_p or r["k"] > latest_p[r["id"]]["k"]):
                latest_p[r["id"]] = r
        if blocked and latest_p:
            def unlocked(r, name):
                techs = ["h_" + t.replace("-", "_") for t in key["unit_info"][name].get("techs", [])]
                return all(num(r, t) == 1 for t in techs)

            for heading, chosen in ((f"the {TOP_N} largest", top(list(latest_p.values()))),
                                    ("every AI country", list(latest_p.values()))):
                cells = [f"{name[2:]} {sum(1 for r in chosen if num(r, name) > 0)}/"
                         f"{sum(1 for r in chosen if unlocked(r, name))}" for name in blocked]
                out.append("")
                out.append(f"The units that take radios, held by / unlocked for, in the last decade read ({heading}, "
                           f"{len(chosen)} armies, each country's last report): " + ", ".join(cells) + ".")

    # --- 3. laws ---------------------------------------------------------------------------------------------------
    table("3. Laws", [
        Col("Enacting a law", test=lambda r: num(r, "enacting") == 1),
        Col("Enactments started a year", field("n_law_start"), digits=1),
        Col("Passed a year, mean", field("n_law_pass"), mean=True, total=True, digits=2),
        Col("Failed a year, mean", field("n_law_fail"), mean=True, total=True, digits=2),
        Col("Ended a year, mean", field("n_law_end"), mean=True, total=True, digits=2),
        Col("Laws set outside an enactment a year, mean (script, revolution, a new country)",
            logged("n_law_set", field("n_law_set")), mean=True, total=True, digits=2),
        Col("Institution levels, all", lambda r: sum(num(r, f) for f in r if f.startswith("in_")), digits=0),
        Col("Government reforms a year, mean", field("n_reform"), mean=True, total=True, digits=2),
    ])

    # 3a. The law cadence: the largest economies' months first, then every AI country's (the reference figures).
    from_k = first_k_of_year(parsed.ticks, cadence_from)

    def top_month(tag, k):
        y = year_of(k)
        return y is not None and (tag, bucket_of(y)) in top_tags

    def cadence_table(rows_):
        def rate(starts, months):
            return f"{starts / months:.4f}" if months else "-"
        out.append("")
        out.append(f"| Agenda | Starts | Idle months | Starts per idle month | Months idle before a start, median | "
                   f"Starts from {cadence_from} | Idle months from {cadence_from} | "
                   f"Starts per idle month from {cadence_from} |")
        out.append("|---|---|---|---|---|---|---|---|")
        total = {"starts": 0, "months": 0, "starts_late": 0, "months_late": 0, "waits": []}
        for row in rows_:
            for name in total:
                total[name] += row[name]
        for row in rows_ + [{"agenda": "all agendas", **total}]:
            wait = f"{statistics.median(row['waits']):.1f}" if row["waits"] else "-"
            late = (f"{row['starts_late']} | {row['months_late']} | {rate(row['starts_late'], row['months_late'])}"
                    if from_k is not None else "- | - | -")
            out.append(f"| {row['agenda']} | {row['starts']} | {row['months']} | {rate(row['starts'], row['months'])} "
                       f"| {wait} | {late} |")

    cadence = law_cadence(parsed.events, ai, key["strategies"]["political"], from_k)
    if cadence:
        out.append("")
        out.append("## 3a. Law starts per idle month, by political agenda")
        out.append("")
        out.append("An idle month is one with no enactment under way, from an enactment's end (or the first month) to "
                   "the next start; it counts against the agenda held that month. The rate is the monthly hazard of "
                   f"a start. The last three columns count months from {cadence_from} only"
                   + ("" if from_k is not None else " (none in this log)") + ".")
        out.append("")
        out.append(f"**The {TOP_N} largest AI economies: their months in the decades they were among them**")
        cadence_table(law_cadence(parsed.events, ai, key["strategies"]["political"], from_k, include=top_month))
        out.append("")
        out.append("**Every AI country** (the baseline analysis's l1_cadence.py, which reads the same way)")
        cadence_table(cadence)

    # 3b. How enactments ended.
    ends = [e for e in parsed.events if e["event"] == "law_end" and e["tag"] in {r["tag"] for r in ai}]
    if ends:
        how_names = key.get("law_end_how", [])
        passed_at = {(e["tag"], e["k"]) for e in parsed.events if e["event"] == "law_pass"}

        def how(e):
            h = e.get("how")
            if isinstance(h, int) and 0 < h <= len(how_names):
                return how_names[h - 1]
            return "passed" if (e["tag"], e["k"]) in passed_at else "unpassed"
        out.append("")
        out.append("## 3b. How enactments ended")
        out.append("")
        out.append("From the law_end events of AI countries. Version 2 logs how each ended (`how`): cancelled means "
                   "stopped with the law still available (by the AI, or by script), replaced means stopped because "
                   "the law was no longer available (a law set by script or a revolution barred it). A version-1 "
                   "log tells only passed (a law_pass the same month) from unpassed.")
        kinds = how_names + ["unpassed"]
        for lens, heading in (("top", f"The {TOP_N} largest AI economies"), ("all", "Every AI country")):
            out.append("")
            out.append(f"**{heading}**")
            out.append("")
            out.append("| Years | Ended | " + " | ".join(k.capitalize() for k in kinds)
                       + " | Chance to pass at a cancellation, median |")
            out.append("|---|---|" + "---|" * len(kinds) + "---|")
            for start in sorted(bucket_rows):
                mine = [e for e in ends if year_of(e["k"]) is not None and bucket_of(year_of(e["k"])) == start
                        and (lens == "all" or (e["tag"], start) in top_tags)]
                if not mine:
                    continue
                counts = Counter(how(e) for e in mine)
                chances = [num(e, "chance") for e in mine if how(e) in ("cancelled", "unpassed")]
                chance = f"{statistics.median(chances):.2f}" if chances else "-"
                out.append(f"| {label_of(start)} | {len(mine)} | " + " | ".join(str(counts.get(k, 0)) for k in kinds)
                           + f" | {chance} |")
        laws = key["all_laws"]
        stopped = Counter(laws[e["law"] - 1] for e in ends
                          if how(e) != "passed" and isinstance(e.get("law"), int) and 0 < e["law"] <= len(laws))
        if stopped:
            out.append("")
            out.append("Laws most often ended without passing, every AI country: " + ", ".join(
                f"{name} {n}" for name, n in stopped.most_common(12)))

    # 3c. The old law kept while the technology for the next one is held (version 2's H line).
    def holding(label, law_group, law, techs):
        name = "lw_" + (law_group[len("lawgroup_"):] if law_group.startswith("lawgroup_") else law_group).lower()
        names = key["laws"].get(law_group, [])
        if law not in names:
            return None
        idx = names.index(law) + 1
        tech_fields = ["h_" + t.replace("-", "_") for t in techs]
        return Col(label, test=lambda r: num(r, name) == idx,
                   among=lambda r: all(f in r for f in tech_fields) and any(num(r, f) == 1 for f in tech_fields))

    gates = [
        ("No Schools, holding Rationalism", "lawgroup_education_system", "law_no_schools", ["rationalism"]),
        ("Land-Based taxation, holding Currency Standards", "lawgroup_taxation", "law_land_based_taxation",
         ["currency_standards"]),
        ("Land-Based taxation, holding an era-3 society technology", "lawgroup_taxation", "law_land_based_taxation",
         ["civilizing_mission", "human_rights", "pan-nationalism"]),
        ("Traditionalism, holding an era-3 society technology", "lawgroup_economic_system", "law_traditionalism",
         ["civilizing_mission", "human_rights", "pan-nationalism"]),
        ("No Colonial Affairs, holding Colonization", "lawgroup_colonization", "law_no_colonial_affairs",
         ["colonization"]),
        ("Peasant Levies, holding Military Drill", "lawgroup_army_model", "law_peasant_levies", ["military_drill"]),
    ]
    columns = [col for col in (holding(*gate) for gate in gates) if col is not None]
    if flagged and columns:
        table("3c. The old law kept while the technology for the next is held (share of those holding it)", columns)

    # 3d. Institutions against their maximum (version 2's J line), in the last decade read.
    last_start = max(bucket_rows)
    newest = {}
    for r in bucket_rows[last_start]:
        if any(f.startswith("im_") for f in r) and (r["id"] not in newest or r["k"] > newest[r["id"]]["k"]):
            newest[r["id"]] = r
    if newest:
        out.append("")
        out.append("## 3d. Institutions against the maximum a country may invest in, in the last decade read")
        out.append("")
        out.append(f"| Institution | Countries with it | Level, median | Maximum, median | At its maximum, the "
                   f"{TOP_N} largest | At its maximum, all |")
        out.append("|---|---|---|---|---|---|")
        for name in key["institutions"]:
            short_name = name[len("institution_"):] if name.startswith("institution_") else name
            have = [r for r in newest.values() if num(r, "im_" + short_name) > 0]
            if not have:
                continue

            def at_max(r, s=short_name):
                return num(r, "in_" + s) >= num(r, "im_" + s)
            out.append(f"| {short_name} | {len(have)} | "
                       f"{statistics.median(num(r, 'in_' + short_name) for r in have):.0f} | "
                       f"{statistics.median(num(r, 'im_' + short_name) for r in have):.0f} | "
                       f"{share(top(have), at_max)} | {share(have, at_max)} |")

    # 3e. Bureaucracy: what makes it and what uses it, as far as script and the interface split it (version 4).
    if any("bur_inst_mult" in r for r in ai):
        def b4(r):
            return "bur_inst_mult" in r

        def inst_cost(r):
            return xnum(r, "bur_inst") if b4(r) else None

        def rest_of_use(r):
            cost = xnum(r, "bur_inst")
            return max(num(r, "bur_used") - cost - max(num(r, "bur_cost_add"), 0), 0) if b4(r) and cost is not None \
                else None

        table("3e. Bureaucracy: production and use", [
            Col("In deficit", test=lambda r: num(r, "bur") < 0, among=b4),
            Col("Used / produced", ratio=(field("bur_used"), field("bur_made")), digits=2, among=b4),
            Col("Institutions, % of use", ratio=(inst_cost, field("bur_used")), digits=0, scale=100, among=b4),
            Col("Flat costs (modifiers), % of use", ratio=(field("bur_cost_add"), field("bur_used")), digits=0,
                scale=100, among=b4),
            Col("The rest: incorporated states and their people, %", ratio=(rest_of_use, field("bur_used")),
                digits=0, scale=100, among=b4),
            Col("Institution cost multiplier, %", field("bur_inst_mult"), digits=0, scale=100, among=b4),
            Col("Cost per head multiplier, %", field("bur_pop_mult"), digits=0, scale=100, among=b4),
            Col("Production multiplier, %", field("bur_mult"), digits=0, scale=100, among=b4),
            Col("Flat production (modifiers), % of produced", ratio=(field("bur_add"), field("bur_made")), digits=0,
                scale=100, among=b4),
            Col("Administration levels per 100 used", ratio=(field("bt_government_administration"), field("bur_used")),
                digits=2, scale=100, among=b4),
        ], note="From version 4. Bureaucracy is made by Government Administrations and flat modifiers, times the "
                "production multiplier; it is used by the institutions (X7: the Politics panel's figure), by flat "
                "costs (country_bureaucracy_cost_add) and by each incorporated state and its people (vanilla's "
                "STATE_BUREAUCRACY_* defines), which no script read or data function gives, so the rest is that and "
                "whatever else the engine counts. The institutions' cost multiplier is "
                "country_bureaucracy_investment_cost_factor_mult (37 of the mod's laws move it), the cost per head's "
                "state_bureaucracy_population_base_cost_factor_mult (14).")

    # --- 4. military -----------------------------------------------------------------------------------------------
    def armed(r):
        return num(r, "army") > 0

    table("4. Military", [
        Col("Army (battalions; world: total)", field("army"), digits=0, total=True),
        Col("Navy (world: total)", field("navy"), digits=0, total=True),
        Col("Army units, mean era of their types", field("army_tier"), digits=2, among=armed),
        Col("Military technologies", lambda r: sum(num(r, f) for f in r if f.startswith("tc_military_")), digits=0),
        Col("Irregular infantry, % of the army", field("irregular"), digits=0, scale=100, among=armed),
        Col("Barracks levels", field("bt_barrack"), digits=0),
    ])

    unit_line = key.get("unit_line", {})
    unit_info = key.get("unit_info", {})
    if any(f in r for r in ai for f in unit_line):
        def with_units(r):
            return num(r, "army") > 0 and "u_irregular_infantry" in r

        era1 = [f for f, info in unit_info.items() if info["tier"] <= 1]

        def group(name):
            members = [f for f, info in unit_info.items() if info["group"] == name]
            return lambda r: sum(num(r, f) for f in members)

        table("4a. The army by unit type (shares of the army, %)", [
            Col("Irregular infantry", field("u_irregular_infantry"), digits=0, scale=100, among=with_units),
            Col("Line infantry", field("u_line_infantry"), digits=0, scale=100, among=with_units),
            Col("Irregulars over half the army", test=lambda r: num(r, "u_irregular_infantry") > 0.5,
                among=with_units),
            Col("Of those, holding Line Infantry", test=lambda r: num(r, "h_line_infantry") == 1,
                among=lambda r: with_units(r) and num(r, "u_irregular_infantry") > 0.5),
            Col("Holding General Staff, nothing past era-1 types",
                test=lambda r: sum(num(r, f) for f in era1) >= 0.995,
                among=lambda r: with_units(r) and num(r, "h_general_staff") == 1),
            Col("Artillery", group("combat_unit_group_artillery"), digits=0, scale=100, among=with_units),
            Col("Cavalry", group("combat_unit_group_cavalry"), digits=0, scale=100, among=with_units),
            Col("Shares add to", lambda r: sum(num(r, f) for f in unit_line), digits=2, among=with_units),
        ])
        held, unlocked = Counter(), Counter()
        latest = {}
        for r in bucket_rows[last_start]:
            if with_units(r) and (r["id"] not in latest or r["k"] > latest[r["id"]]["k"]):
                latest[r["id"]] = r
        for r in latest.values():
            for name, info in unit_info.items():
                if num(r, name) > 0:
                    held[name] += 1
                techs = ["h_" + t.replace("-", "_") for t in info.get("techs", [])]
                if all(num(r, t) == 1 for t in techs):
                    unlocked[name] += 1
        out.append("")
        out.append(f"In the last decade read, of {len(latest)} armies, each type held by / unlocked for: "
                   + ", ".join(f"{name[2:]} {held[name]}/{unlocked[name]}" for name in unit_info
                               if held[name] or unlocked[name]))

    # 4b. Where irregulars come from. Every version: the net change in irregular battalions between a country's
    # reports (army x the irregular share). Versions 4 and 5's census, meant to tell recruits from type changes,
    # counted nothing (#2090).
    previous = {}
    for rows_ in by_id.values():
        for a, b in zip(rows_, rows_[1:]):
            previous[id(b)] = a

    def irregulars(r):
        return num(r, "army") * num(r, "irregular")

    def net_irregular(r):
        a = previous.get(id(r))
        if a is None or num(r, "army") <= 0 or r["k"] <= a["k"]:
            return None
        return (irregulars(r) - irregulars(a)) * 12 / (r["k"] - a["k"])

    columns = [
        Col("Irregular battalions, net change a year (world: total)", net_irregular, digits=1, total=True),
        Col("Irregular battalions, net change a year, % of the army",
            lambda r: (net_irregular(r) / num(r, "army") if net_irregular(r) is not None else None), digits=1,
            scale=100),
    ]
    if any(num(r, "army") > 0 for r in ai):
        table("4b. Where the irregulars come from", columns,
              note="The net change is the irregular battalions (the army times its irregular share) at a report less "
                   "at the country's last, a year's worth: it nets recruits against upgrades and losses. Recruits and "
                   "upgrades can't be told apart from script, since a combat unit holds no variables (#2090): "
                   "compare two saves' battalion records for that.")

    # --- 5. expansion ----------------------------------------------------------------------------------------------
    plays = [e for e in parsed.events if e["event"] == "play"]
    table("5. Expansion", [
        Col("States (world: total)", field("states"), digits=0, total=True),
        Col("Colonies under way", test=lambda r: num(r, "colonies") > 0),
        Col("Plays started a year, mean", field("n_play"), mean=True, total=True, digits=3),
        Col("Play events a year, as initiator", **event_rate(plays)),
        Col("Wars started a year, mean", field("n_war"), mean=True, total=True, digits=3),
        Col("At war", test=lambda r: num(r, "war") == 1),
        Col("Infamy", field("infamy"), digits=0),
        Col("Countries reporting", custom=lambda rows: len({r["id"] for r in rows}),
            world=lambda rows: len({r["id"] for r in rows})),
    ], note="n_play counts plays of snapshotted countries between their snapshots (a country's last months and a "
            "dead country's are lost); play events count every play, so they run higher. n_war counts the plays "
            "that became wars.")

    play_types = key.get("play_types", [])
    typed = [e for e in plays if isinstance(e.get("type"), int) and e["type"] > 0]
    if typed:
        def rank(i):
            return ranks[i - 1] if isinstance(i, int) and 0 < i <= len(ranks) else "none"
        out.append("")
        out.append("## 5a. Diplomatic plays by type, every initiator")
        out.append("")
        out.append("| Type | Plays | Initiators by rank | Targets by rank |")
        out.append("|---|---|---|---|")
        by_type = defaultdict(list)
        for e in typed:
            by_type[play_types[e["type"] - 1] if e["type"] <= len(play_types) else str(e["type"])].append(e)
        for name, mine in sorted(by_type.items(), key=lambda item: -len(item[1])):
            a = Counter(rank(e.get("rank")) for e in mine).most_common(3)
            b = Counter(rank(e.get("target_rank")) for e in mine).most_common(3)
            out.append(f"| {name} | {len(mine)} | {', '.join(f'{n} {c}' for n, c in a)} | "
                       f"{', '.join(f'{n} {c}' for n, c in b)} |")
    if plays:
        tags = {r["tag"] for r in ai}
        out.append("")
        out.append(f"{sum(1 for e in plays if e['tag'] not in tags)} of {len(plays)} plays came from countries the "
                   "probe never snapshotted (decentralized nations' uprisings and the like).")

    if parsed.world:
        out.append("")
        out.append("## 5b. The world outside the AI countries: the last reading of each decade")
        out.append("")
        out.append("Version 2 counted the decentralized nations with `every_country`, which does not reach them, so its "
                   "two columns read 0; version 3 counts them with their own iterator, and reads the same land a "
                   "second way: every state in the world less the states of the other countries.")
        out.append("")
        out.append("| Years | Countries (not decentralized) | Decentralized nations | States they hold | "
                   "States in the world | Held by the other countries | The difference |")
        out.append("|---|---|---|---|---|---|---|")
        by_decade = {}
        for k in sorted(parsed.world):
            w = parsed.world[k]
            if isinstance(w.get("y"), int):
                by_decade[bucket_of(w["y"])] = w
        for start, w in sorted(by_decade.items()):
            difference = num(w, "states") - num(w, "c_states") if "states" in w else "-"
            out.append(f"| {label_of(start)} | {w.get('countries', '-')} | {w.get('dn', '-')} | "
                       f"{w.get('dn_states', '-')} | {w.get('states', '-')} | {w.get('c_states', '-')} | "
                       f"{difference} |")

    # --- the last decade's laws and strategies ---------------------------------------------------------------------
    latest = {}
    for record in bucket_rows[last_start]:
        if record["id"] not in latest or record["k"] > latest[record["id"]]["k"]:
            latest[record["id"]] = record
    biggest = [r for r in latest.values() if r["id"] in top_ids[last_start]]

    def commonest(rows, name, names, n=4):
        counts = Counter(num(r, name) for r in rows)
        return ", ".join(f"{names[idx - 1] if 0 < idx <= len(names) else 'none'} {c}"
                         for idx, c in counts.most_common(n))

    out.append("")
    out.append("## The commonest law in each group, in the last decade read")
    out.append("")
    out.append(f"| Group | The {TOP_N} largest | Every AI country |")
    out.append("|---|---|---|")
    for group_name in key["law_groups"]:
        name = "lw_" + (group_name[len("lawgroup_"):] if group_name.startswith("lawgroup_") else group_name).lower()
        if {num(r, name) for r in latest.values()} - {0}:
            names = key["laws"][group_name]
            out.append(f"| {group_name} | {commonest(biggest, name, names, 3)} | "
                       f"{commonest(latest.values(), name, names)} |")

    out.append("")
    out.append("## Strategies held, in the last decade read")
    out.append("")
    for kind, names in key["strategies"].items():
        out.append(f"- {kind}, the {TOP_N} largest: {commonest(biggest, f'strat_{kind}', names, 20)}")
        out.append(f"- {kind}, every AI country: {commonest(latest.values(), f'strat_{kind}', names, 20)}")

    events = Counter(e["event"] for e in parsed.events)
    if events:
        out.append("")
        out.append("## Events logged")
        out.append("")
        out.append(", ".join(f"{name} {n}" for name, n in events.most_common()))
        starts = [e for e in parsed.events if e["event"] == "law_start"]
        if starts:
            laws = Counter(num(e, "law") for e in starts)
            names = key["all_laws"]
            out.append("")
            out.append("Laws the AI started most: " + ", ".join(
                f"{names[idx - 1] if 0 < idx <= len(names) else 'unknown'} {n}" for idx, n in laws.most_common(15)))
            chances = [num(e, "chance") for e in starts if isinstance(e.get("chance"), (int, float))]
            if chances:
                out.append(f"Chance to pass when started: {spread(chances, 2)}")
    return "\n".join(out) + "\n"


def write_parse(parsed: Parsed, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / "snapshots.jsonl", "w", encoding="utf-8") as handle:
        for record in parsed.records():
            handle.write(json.dumps(record) + "\n")
    with open(folder / "events.jsonl", "w", encoding="utf-8") as handle:
        for event in parsed.events:
            handle.write(json.dumps(event) + "\n")
    (folder / "ticks.json").write_text(json.dumps(parsed.ticks, indent=1), encoding="utf-8")
    (folder / "canary.json").write_text(json.dumps(parsed.canary, indent=1), encoding="utf-8")
    (folder / "world.json").write_text(json.dumps(parsed.world, indent=1), encoding="utf-8")
    (folder / "armed.json").write_text(json.dumps(parsed.armed), encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="verb", required=True)
    for verb in ("check", "parse", "report"):
        p = sub.add_parser(verb)
        p.add_argument("sources", nargs="+", help="log files, oldest first" + (", or a parsed DIR" if verb == "report" else ""))
        p.add_argument("--key", type=Path, default=KEY_PATH, help="ai_probe_key.json of the build that ran")
        if verb == "parse":
            p.add_argument("--out", type=Path, required=True)
        if verb == "report":
            p.add_argument("--md", type=Path, help="write the scorecard here as well")
            p.add_argument("--years", type=int, default=10, help="years per row (default 10)")
            p.add_argument("--cadence-from", type=int, default=CADENCE_FROM_YEAR,
                           help=f"the year table 3a's later columns start (default {CADENCE_FROM_YEAR})")
    args = parser.parse_args(argv)
    key = load_key(args.key)
    parsed = gather(args.sources, key)
    if parsed.k_restarts and args.verb != "check":
        print(f"WARNING: the month count went back {parsed.k_restarts} times: these files hold more than one run, "
              "whose serials and months collide. Parse each run alone.", file=sys.stderr)
    if args.verb == "check":
        lines, ok = check(parsed, key)
        print("\n".join(lines))
        print("VERDICT: " + ("fit for a long run" if ok else "NOT fit for a long run: fix the lines above first"))
        return 0 if ok else 1
    if args.verb == "parse":
        write_parse(parsed, args.out)
        print(f"{len(parsed.snapshots)} snapshots, {len(parsed.events)} events, {len(parsed.ticks)} ticks -> {args.out}")
        return 0
    text = report(parsed, key, args.years, args.cadence_from)
    print(text)
    if args.md:
        args.md.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
