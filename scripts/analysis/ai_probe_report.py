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
        self.bad: list[str] = []
        self.line_names: Counter = Counter()

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
                parsed.ticks.setdefault(int(k), {}).update(pairs(body))
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
    wanted = ["start", "date", *key["data_functions"], "end"]
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
    expected = list(key["lines"])
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
    else:
        out.append("  none yet: a country first reports within twelve months of arming")
    data = len(parsed.data_lines)
    out.append(f"data-function (X) records: {data}")
    out.append(f"events: {len(parsed.events)} {dict(Counter(e['event'] for e in parsed.events).most_common())}")
    if parsed.bad:
        out.append(f"unreadable probe lines: {len(parsed.bad)}; first: {parsed.bad[0]}")
    return out, ok


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


def yearly_rate(first: dict, last: dict, field: str):
    a, b, months = num(first, field), num(last, field), last["k"] - first["k"]
    if a <= 0 or b <= 0 or months <= 0:
        return None
    return (b / a) ** (12 / months) - 1


def report(parsed: Parsed, key: dict, bucket_years: int = 10) -> str:
    records = [r for r in parsed.records() if "y" in r]
    out: list[str] = []
    if not records:
        return "No snapshots with a year yet.\n"
    world = [r for r in records if num(r, "type") != key["country_types"].index("decentralized") + 1]
    ai = [r for r in world if num(r, "ai") == 1]
    years = sorted({r["y"] for r in records})
    out.append(f"# AI probe scorecard: {years[0]} to {years[-1]}")
    out.append("")
    out.append(f"{len(records)} snapshots of {len({r['id'] for r in records})} countries; {len(ai)} are AI countries "
               f"that are not decentralized nations, which is what every table below counts. Medians, with the 10th "
               f"and 90th percentiles and the count in brackets.")
    if not ai:
        out.append("")
        out.append("No AI country has reported yet.")
        return "\n".join(out) + "\n"
    by_id = series(ai)

    def buckets():
        start = years[0] - years[0] % bucket_years
        while start <= years[-1]:
            rows = [r for r in ai if start <= r["y"] < start + bucket_years]
            if rows:
                yield f"{start}s" if bucket_years == 10 else f"{start}-{start + bucket_years - 1}", rows
            start += bucket_years

    def table(title: str, columns: list[tuple[str, object]]):
        out.append("")
        out.append(f"## {title}")
        out.append("")
        out.append("| Years | " + " | ".join(name for name, _ in columns) + " |")
        out.append("|---|" + "---|" * len(columns))
        for label, rows in buckets():
            out.append(f"| {label} | " + " | ".join(str(fn(rows)) for _, fn in columns) + " |")

    def growth(field):
        def run(rows):
            ids = {r["id"] for r in rows}
            rates = []
            for ident in ids:
                mine = [r for r in by_id[ident] if r in rows]
                if len(mine) >= 2:
                    rate = yearly_rate(mine[0], mine[-1], field)
                    if rate is not None:
                        rates.append(rate)
            return spread(rates, 2, 100)
        return run

    def per_head(r):
        return num(r, "gdp") / num(r, "pop") if num(r, "pop") > 0 else None

    def head_growth(rows):
        ids = {r["id"] for r in rows}
        rates = []
        for ident in ids:
            mine = [r for r in by_id[ident] if r in rows]
            if len(mine) >= 2 and per_head(mine[0]) and per_head(mine[-1]) and mine[-1]["k"] > mine[0]["k"]:
                rates.append((per_head(mine[-1]) / per_head(mine[0])) ** (12 / (mine[-1]["k"] - mine[0]["k"])) - 1)
        return spread(rates, 2, 100)

    table("1. Economic growth", [
        ("GDP growth, % a year", growth("gdp")),
        ("GDP per head growth, % a year", head_growth),
        ("GDP per head", lambda rows: spread([per_head(r) for r in rows if per_head(r)], 2)),
        ("Standard of living", lambda rows: spread([num(r, "sol") for r in rows], 1)),
        ("Peasants, % of pops", lambda rows: spread([num(r, "peasants") for r in rows], 0, 100)),
        ("Building levels", lambda rows: spread([num(r, "levels") for r in rows], 0)),
    ])
    table("1a. The means of growth: construction and investment", [
        ("Construction sector levels", lambda rows: spread([num(r, "bt_construction_sector") for r in rows], 0)),
        ("No construction sector", lambda rows: share(rows, lambda r: num(r, "bt_construction_sector") == 0)),
        ("Queued levels", lambda rows: spread([num(r, "queue_levels") for r in rows], 0)),
        ("Empty queue", lambda rows: share(rows, lambda r: num(r, "queue_levels") == 0)),
        ("Built + expanded a year", lambda rows: spread([num(r, "n_built") + num(r, "n_expanded") for r in rows], 0)),
        ("Of which government", lambda rows: spread([num(r, "n_built_gov") for r in rows], 0)),
        ("Investment pool, weeks of income", lambda rows: spread(
            [num(r, "pool") / num(r, "income") for r in rows if num(r, "income") > 0], 1)),
        ("Method changes a year", lambda rows: spread([num(r, "n_pm") for r in rows], 0)),
    ])
    table("1b. Solvency", [
        ("In default", lambda rows: share(rows, lambda r: num(r, "default") == 1)),
        ("Declared bankrupt (10 years)", lambda rows: share(rows, lambda r: num(r, "bankrupt") == 1)),
        ("Taking loans", lambda rows: share(rows, lambda r: num(r, "loans") == 1)),
        ("Debt, share of limit", lambda rows: spread([num(r, "debt_scaled") for r in rows], 2)),
        ("Reserves, share of limit", lambda rows: spread([num(r, "gold_scaled") for r in rows], 2)),
        ("Income / expenses", lambda rows: spread(
            [num(r, "income") / num(r, "expenses") for r in rows if num(r, "expenses") > 0], 2)),
        ("Military, share of spending", lambda rows: spread([num(r, "mil_share") for r in rows], 0, 100)),
        ("Bureaucracy below 0", lambda rows: share(rows, lambda r: num(r, "bur") < 0)),
    ])
    table("2. Technology", [
        ("Technologies", lambda rows: spread([num(r, "techs") for r in rows], 0)),
        ("Leader", lambda rows: max((num(r, "techs") for r in rows), default="-")),
        ("Acquired a year", lambda rows: spread([num(r, "n_tech") for r in rows], 1)),
        ("Innovation", lambda rows: spread([num(r, "innovation") for r in rows], 0)),
        ("University levels", lambda rows: spread([num(r, "bt_university") for r in rows], 0)),
        ("No university", lambda rows: share(rows, lambda r: num(r, "bt_university") == 0)),
        ("Researching nothing", lambda rows: share(rows, lambda r: num(r, "researching") == 0)),
        ("Literacy, %", lambda rows: spread([num(r, "lit") for r in rows], 0, 100)),
    ])
    table("3. Laws", [
        ("Enacting a law", lambda rows: share(rows, lambda r: num(r, "enacting") == 1)),
        ("Enactments started a year", lambda rows: spread([num(r, "n_law_start") for r in rows], 1)),
        ("Passed a year, mean", lambda rows: f"{statistics.fmean(num(r, 'n_law_pass') for r in rows):.2f}"),
        ("Failed a year, mean", lambda rows: f"{statistics.fmean(num(r, 'n_law_fail') for r in rows):.2f}"),
        ("Ended a year, mean", lambda rows: f"{statistics.fmean(num(r, 'n_law_end') for r in rows):.2f}"),
        ("Institution levels, all", lambda rows: spread(
            [sum(num(r, f) for f in r if f.startswith("in_")) for r in rows], 0)),
        ("Government reforms a year, mean",
         lambda rows: f"{statistics.fmean(num(r, 'n_reform') for r in rows):.2f}"),
    ])
    table("4. Military", [
        ("Army (battalions)", lambda rows: spread([num(r, "army") for r in rows], 0)),
        ("Navy", lambda rows: spread([num(r, "navy") for r in rows], 0)),
        ("Army unit tier (1 = the oldest types)", lambda rows: spread(
            [num(r, "army_tier") for r in rows if num(r, "army") > 0], 2)),
        ("Military technologies", lambda rows: spread(
            [sum(num(r, f) for f in r if f.startswith("tc_military_")) for r in rows], 0)),
        ("Barracks levels", lambda rows: spread([num(r, "bt_barrack") for r in rows], 0)),
    ])
    table("5. Expansion", [
        ("States", lambda rows: spread([num(r, "states") for r in rows], 0)),
        ("Colonies under way", lambda rows: share(rows, lambda r: num(r, "colonies") > 0)),
        ("Plays started a year, mean", lambda rows: f"{statistics.fmean(num(r, 'n_play') for r in rows):.3f}"),
        ("Wars started a year, mean", lambda rows: f"{statistics.fmean(num(r, 'n_war') for r in rows):.3f}"),
        ("At war", lambda rows: share(rows, lambda r: num(r, "war") == 1)),
        ("Infamy", lambda rows: spread([num(r, "infamy") for r in rows], 0)),
        ("Countries reporting", lambda rows: len({r["id"] for r in rows})),
    ])

    out.append("")
    out.append("## The commonest law in each group, in the last decade read")
    out.append("")
    last = list(buckets())[-1][1]
    newest = {}
    for record in last:
        if record["id"] not in newest or record["k"] > newest[record["id"]]["k"]:
            newest[record["id"]] = record
    out.append("| Group | Laws held (countries) |")
    out.append("|---|---|")
    for group in key["law_groups"]:
        field = "lw_" + (group[len("lawgroup_"):] if group.startswith("lawgroup_") else group).lower()
        counts = Counter(num(r, field) for r in newest.values())
        names = key["laws"][group]
        cells = []
        for idx, n in counts.most_common(4):
            name = names[idx - 1] if 0 < idx <= len(names) else "none"
            cells.append(f"{name} {n}")
        if counts.keys() - {0}:
            out.append(f"| {group} | {', '.join(cells)} |")

    out.append("")
    out.append("## Strategies held, in the last decade read")
    out.append("")
    for kind, names in key["strategies"].items():
        counts = Counter(num(r, f"strat_{kind}") for r in newest.values())
        cells = [f"{names[idx - 1] if 0 < idx <= len(names) else 'none'} {n}" for idx, n in counts.most_common()]
        out.append(f"- {kind}: {', '.join(cells)}")

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
    args = parser.parse_args(argv)
    key = load_key(args.key)
    parsed = gather(args.sources, key)
    if args.verb == "check":
        lines, ok = check(parsed, key)
        print("\n".join(lines))
        print("VERDICT: " + ("fit for a long run" if ok else "NOT fit for a long run: fix the lines above first"))
        return 0 if ok else 1
    if args.verb == "parse":
        write_parse(parsed, args.out)
        print(f"{len(parsed.snapshots)} snapshots, {len(parsed.events)} events, {len(parsed.ticks)} ticks -> {args.out}")
        return 0
    text = report(parsed, key, args.years)
    print(text)
    if args.md:
        args.md.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
