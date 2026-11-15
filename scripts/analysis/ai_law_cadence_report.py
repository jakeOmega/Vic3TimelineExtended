"""How often AI countries change laws, read from saves: the play-test measure for the AI law cadence.

    ai_law_cadence_report.py <save.v3> [<save.v3> ...]            per save: AI countries mid-enactment, by agenda
    ai_law_cadence_report.py --period <save.v3> <save.v3> ...     the law-update period, from saves of ONE game

Read-only; binary (non-ironman) saves only. Run from the repo root with the venv python. Each save takes 20-60 s.

Shares. For each political strategy, the AI countries holding it and how many are enacting a law. "Active" counts only
countries that have changed a law since the game's first month or are enacting one, which leaves out the
decentralized nations: in an 1864 save, 121 of the 123 AI countries that had changed none were decentralized. The
self-check TE_SELF_CHECK ai_law_cadence reads the same share in game over AI countries that are not decentralized.
Baselines and what to expect: docs/testing/ai-economy-playtest.md § AI law cadence.

Period. A country's law-change starts fall on a fixed phase of its law-update period, so across several saves of one
game every pair of one country's starts is a whole number of periods apart. The report prints, for candidate periods,
the share of pairs in the same phase; the period is the longest candidate where that share stays near 1 (measured
2026-11-15: 1200 hours, 50 days; docs/guides/scripting_best_practices.md § The AI Rolls change_law_chance Every 50
Days).

Save layout (worked out 2026-11-15 on 1.15.1 saves; save_country_probe.py's BINARY LAYOUT has the rest):
  AI database   0x2c28 = { 0x05ab = { u32:<record> = { 0x2840 = u32:<country id>  ...
                                        0x3007 = { 0x00e1 = "<strategy>"  0x2a4f = i32 }  (three: one each of
                                        administrative, political, diplomatic)  ... } ... } }
                A dead country's record stays (451 records, 257 countries). Found from the first political strategy
                string: the token stream is aligned on it and the open blocks walked back to the 0x2c28 key.
  Enactments    the law record's 0x56fc, "being enacted since" (save_country_probe.law_records' `enacting`). The
                start hours are multiples of 6: the tick.
"""

import collections
import itertools
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_save_history_order import read_gamestate  # noqa: E402
from save_country_probe import country_headers, fmt_hours, get, law_records, parse_block, tokens  # noqa: E402
from save_world_report import gamestate_hours  # noqa: E402

KEY_AI_DATABASE = 0x2C28
KEY_ENTRIES = 0x05AB
KEY_AI_COUNTRY = 0x2840
KEY_STRATEGY = 0x3007
KEY_STRATEGY_NAME = 0x00E1
POLITICAL = re.compile(r"^ai_strategy_\w*(agenda|reforms|restoration|mandate_of_heaven)$")
FIRST_MONTH_HOURS = 31 * 24
PERIODS = (240, 400, 600, 800, 1200, 1800, 2400, 3600)


def ai_strategies(blob):
    """{country id: [strategy names]} from the AI database."""
    first = re.search(rb"ai_strategy_[a-z_]+_agenda", blob)
    if not first:
        return {}
    name_at = first.start()
    for start in range(max(0, name_at - 400000), max(0, name_at - 400000) + 64):
        stream = list(tokens(blob, start, name_at + 2))
        if any(o == name_at - 4 and kind == "str" for o, kind, _ in stream):
            break
    else:
        raise ValueError("could not align the token stream on the AI database")
    open_blocks, last = [], []
    for o, kind, value in stream:
        if o >= name_at - 4:
            break
        if kind == "{":
            key = last[-2] if len(last) >= 2 and last[-1][1] == "=" else None
            open_blocks.append((o, key))
        elif kind == "}" and open_blocks:
            open_blocks.pop()
        last = (last + [(o, kind, value)])[-3:]
    brace = next((o for o, key in open_blocks if key and key[1:] == ("tok", KEY_AI_DATABASE)), None)
    if brace is None:
        raise ValueError("no 0x2c28 block around the first political strategy")
    items, _ = parse_block(blob, brace - 4)  # the key and '=' sit 4 bytes before the brace
    out = {}
    for _, record in get(items, KEY_ENTRIES) or []:
        if not isinstance(record, list):
            continue
        country = get(record, KEY_AI_COUNTRY)
        if not country or country[0] != "int":
            continue
        names = []
        for key, value in record:
            if key == ("tok", KEY_STRATEGY) and isinstance(value, list):
                name = get(value, KEY_STRATEGY_NAME)
                if name and name[0] == "str":
                    names.append(name[1])
        out[country[1]] = names
    return out


def political(names):
    return next((n for n in names if POLITICAL.match(n)), None)


def shares(path):
    """(date, {agenda: [countries, enacting, active countries, active enacting]}, warning)."""
    blob = read_gamestate(path)
    alive = {cid for _, cid, _, _ in country_headers(blob)}
    records, warning = law_records(blob)
    first = min(r["since"] for r in records if r["since"])
    enacting = {r["country"] for r in records if r["enacting"] is not None}
    active = enacting | {
        r["country"] for r in records if r["replaced"] and r["since"] and r["since"] > first + FIRST_MONTH_HOURS
    }
    table = collections.defaultdict(lambda: [0, 0, 0, 0])
    for cid, names in ai_strategies(blob).items():
        agenda = political(names)
        if cid not in alive or agenda is None:
            continue
        row = table[agenda.removeprefix("ai_strategy_")]
        row[0] += 1
        row[1] += cid in enacting
        if cid in active:
            row[2] += 1
            row[3] += cid in enacting
    return fmt_hours(gamestate_hours(blob)), dict(table), warning


def starts(paths):
    """{country id: sorted distinct enactment start hours} over saves of one game."""
    out = collections.defaultdict(set)
    for path in paths:
        records, _ = law_records(read_gamestate(path))
        for r in records:
            if r["enacting"] is not None:
                out[r["country"]].add(r["enacting"])
    return {cid: sorted(hours) for cid, hours in out.items()}


def same_phase_share(by_country, period):
    """The share of pairs of one country's starts that fall on the same phase of `period` hours (None: no pairs)."""
    same = pairs = 0
    for hours in by_country.values():
        for a, b in itertools.combinations(hours, 2):
            pairs += 1
            same += (b - a) % period == 0
    return same / pairs if pairs else None


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "--period":
        by_country = {c: h for c, h in starts(argv[1:]).items() if len(h) >= 3}
        print(f"countries with 3+ distinct starts: {len(by_country)}, starts: {sum(map(len, by_country.values()))}")
        for period in PERIODS:
            share = same_phase_share(by_country, period)
            print(f"  {period:5} h ({period / 24:5.1f} days)  same phase {share:.3f}  (chance alone {6 / period:.4f})")
        return 0
    pooled = collections.defaultdict(lambda: [0, 0, 0, 0])
    for path in argv:
        date, table, warning = shares(path)
        print(f"== {Path(path).name}  {date}")
        if warning:
            print("  WARNING", warning)
        total = [0, 0, 0, 0]
        for agenda, row in sorted(table.items(), key=lambda kv: -kv[1][0]):
            print(f"  {agenda:28} enacting {row[1]:4}/{row[0]:4}   active {row[3]:4}/{row[2]:4} = "
                  f"{row[3] / max(row[2], 1):4.0%}")
            for i in range(4):
                total[i] += row[i]
                pooled[agenda][i] += row[i]
        print(f"  {'ALL':28} enacting {total[1]:4}/{total[0]:4}   active {total[3]:4}/{total[2]:4} = "
              f"{total[3] / max(total[2], 1):4.0%}")
    if len(argv) > 1:
        print("== pooled")
        for agenda, row in sorted(pooled.items(), key=lambda kv: -kv[1][0]):
            print(f"  {agenda:28} active {row[3]:4}/{row[2]:4} = {row[3] / max(row[2], 1):4.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
