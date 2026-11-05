"""Verify that a save's history stores (`te_hist`, `te_dg_hist`) are in chronological order.

The history charts (gui/journal_entry_widgets/te_history_chart.gui) draw one bar
per stored month in raw `GetList` order, so the store's own order IS the x axis.
`remove_list_variable` does not preserve that order — it fills the removed slot
with the list's last element — which is why eviction is followed by
`te_history_sort_samples` (common/scripted_effects/te_history_effects.txt). This
script is how that claim is checked: it reads the order the engine actually
saved, not the order the script intended.

A healthy store reports `ascending=True` for every country. The bug it was
written for reports one break with the newest months at the front:

    n=240  1845.12..1865.11  ascending=False  break@117: 1865.11 -> 1845.12

DEMOGRAPHICS' STORE TOO. `te_dg_hist` (common/scripted_effects/te_demog_history_effects.txt)
is one sample a census year, at most 100, kept the same way and sorted after
every eviction by `te_demog_history_sort`. Its containers carry the year in the
same `te_hist_i` variable, so it is read by the same patterns, with its own
clock: the newest year in any `te_dg_hist` store.

A STORE OUT OF ORDER FAILS, FROZEN OR NOT. `te_history_sort_samples` only runs
on an eviction, and a country that has stopped recording (dropped below
major-power rank, or lost the journal entry the series belongs to) never evicts
again, so a store already scrambled when it froze stays that way. That used to
be unreachable, since nobody could open another country's journal entry, and
was labelled `frozen` without failing. National Info (spec
docs/superpowers/specs/2026-11-02-charts-help-national-info-design.md § 6.6)
shows another country's charts, so it is reachable now. An old-save repair
(`te_repair_history_order`) sorted every store once until the vanilla 1.15
migration retired it, so a save from before 2026-09-21 (#356) may still show
one. A store whose newest sample is more than one step (a month,
or a year for `te_dg_hist`) behind its kind's newest is still labelled
`frozen`, for the reader, and fails like a live one.

Usage:
    python3 scripts/analysis/check_save_history_order.py             # newest save
    python3 scripts/analysis/check_save_history_order.py <save.v3>
    python3 scripts/analysis/check_save_history_order.py --all       # every save

Exits 1 if any store is out of order, 0 otherwise (including "no stores
found", which just means no tracked country has recorded a sample yet).

SAVE FORMAT. A non-ironman .v3 is a 24-byte ASCII header followed by a zip whose
single `gamestate` entry is Clausewitz *binary*: 2-byte little-endian tokens,
with 0x0003/0x0004 for braces, 0x0001 for '=', 0x000f/0x0017 for length-prefixed
strings, 0x000c for i32, 0x0014 for u32 and 0x029c for i64. Mod variable names
survive as plain strings, so the two structures this needs can be found by
pattern rather than by decoding the whole 180 MB tree:

  * a variable list   `0x001b = "te_hist"` then repeated
                      `0x0352 = { 0x00e1 = 0x0360  0x00db = i64:<container id> }`
  * a container       `u32:<id> = { 0x0555 = { 0x00f0 = { { 0x0384 = "<var>"
                      0x0385 = i32:0  0x00f0 = { ... 0x00db = i64:<value * 1e5> } } ...`

Only `te_hist_i` (the monotonic month index, year * 12 + month - 1) is read out
of each container, which is all the ordering check needs.
"""

import io
import re
import struct
import sys
import zipfile
from pathlib import Path

CONTAINER_HDR = re.escape(b"\x01\x00\x03\x00\x55\x05\x01\x00\x03\x00")
MONTH_VAR = b"\x09\x00te_hist_i"
LIST_ENTRY = b"\x52\x03"
FIXED_POINT = 100000.0
# The variable lists checked, each with how its te_hist_i reads: a month index
# (year * 12 + month - 1) or a year.
STORES = (("te_hist", "month"), ("te_dg_hist", "year"))


def _list_name(name):
    raw = name.encode("ascii")
    return struct.pack("<H", len(raw)) + raw


LIST_NAME = _list_name("te_hist")


def find_saves():
    """Newest-first list of .v3 saves in the configured Victoria 3 save folder."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from path_constants import game_logs_path

    folder = Path(game_logs_path).parent / "save games"
    return sorted(folder.glob("*.v3"), key=lambda p: p.stat().st_mtime, reverse=True)


class PlainTextSave(ValueError):
    """The save is plain text (debug mode writes these), not the zipped binary this tool decodes."""


def read_gamestate(save_path):
    """Return the decompressed `gamestate` blob of a non-ironman .v3 save.

    A plain-text save (`SAV0100...` then `meta_data={`, written when the game runs in debug mode) is not a zip and
    says so, instead of the "ironman or corrupt" of a file that is neither.
    """
    with open(save_path, "rb") as handle:
        head = handle.read(256)
        if b"meta_data={" in head:
            raise PlainTextSave(
                f"{save_path}: a plain-text save (debug mode writes these), not a zipped binary one; this tool "
                "reads only binary saves. The tax code's report, scripts/analysis/tax_code_save_report.py, reads both."
            )
        raw = head + handle.read()
    start = raw.find(b"PK\x03\x04")
    if start == -1:
        raise ValueError(f"{save_path}: no zip payload (ironman or corrupt save?)")
    with zipfile.ZipFile(io.BytesIO(raw[start:])) as archive:
        return archive.read("gamestate")


def month_index_by_container(blob):
    """Map script-container id -> te_hist_i, for every container that has one."""
    starts = []
    for match in re.finditer(CONTAINER_HDR, blob):
        off = match.start()
        if off >= 6 and blob[off - 6 : off - 4] == b"\x14\x00":
            starts.append((struct.unpack_from("<I", blob, off - 4)[0], off - 6))

    months = {}
    for pos, (cid, off) in enumerate(starts):
        end = starts[pos + 1][1] if pos + 1 < len(starts) else len(blob)
        at = blob.find(MONTH_VAR, off, end)
        if at == -1:
            continue
        at += len(MONTH_VAR)
        if blob[at : at + 2] != b"\x85\x03":  # 0x0385, the variable's data-type tag
            continue
        at += 10  # 0x0385 '=' i32-token + 4 payload bytes
        if blob[at : at + 2] != b"\xf0\x00":  # 0x00f0, the value wrapper
            continue
        at += 12  # 0x00f0 '=' '{' 0x00e1 '=' <type token>
        if blob[at : at + 2] != b"\xdb\x00":  # 0x00db, the value itself
            continue
        at += 6  # 0x00db '=' i64-token
        months[cid] = int(round(struct.unpack_from("<q", blob, at)[0] / FIXED_POINT))
    return months


def sample_lists(blob, name="te_hist"):
    """Ordered container ids of every `name` variable list in the save."""
    lists = []
    pattern = _list_name(name)
    step = len(pattern)
    at = blob.find(pattern)
    while at != -1:
        if blob[at - 2 : at] == b"\x0f\x00" and blob[at + step : at + step + 2] == LIST_ENTRY:
            ids, cursor = [], at + step
            while blob[cursor : cursor + 2] == LIST_ENTRY:
                cursor += 18  # 0x0352 '=' '{' 0x00e1 '=' <token> 0x00db '=' i64-token
                ids.append(struct.unpack_from("<q", blob, cursor)[0])
                cursor += 10  # 8 payload bytes + '}'
            lists.append((at, ids))
        at = blob.find(pattern, at + 1)
    return lists


def fmt_month(index):
    return "%d.%02d" % (index // 12, index % 12 + 1)


def fmt_year(index):
    return "%d" % index


FORMATS = {"month": fmt_month, "year": fmt_year}


def check_save(save_path):
    """Print one line per history store. Returns the number out of order."""
    blob = read_gamestate(save_path)
    months = month_index_by_container(blob)
    found = [(name, unit, sample_lists(blob, name)) for name, unit in STORES]
    print(f"{save_path}  ({sum(len(s) for _, _, s in found)} history store(s), {len(months)} sample containers)")

    broken = 0
    for name, unit, stores in found:
        fmt = FORMATS[unit]
        spans = {off: [months[i] for i in ids if i in months] for off, ids in stores}
        # The kind's own clock: no store can hold a month (or year) the game has not reached.
        now = max((max(seq) for seq in spans.values() if seq), default=None)
        frozen = 0
        for off, ids in stores:
            seq = spans[off]
            if not seq:
                print(f"  {name} 0x{off:x}  n={len(ids):3d}  no month indices resolved")
                continue
            breaks = [k for k in range(len(seq) - 1) if seq[k + 1] <= seq[k]]
            ascending = not breaks
            # One step of slack: a store can miss the current month (or year) depending on
            # where its pulse sits relative to the save, and still be live.
            is_frozen = now is not None and now - max(seq) > 1
            if not ascending:
                broken += 1
                frozen += is_frozen
            detail = "".join(f"  break@{k}: {fmt(seq[k])} -> {fmt(seq[k + 1])}" for k in breaks[:3])
            if not ascending and is_frozen:
                detail += f"  [frozen since {fmt(max(seq))}: scrambled before #356, 2026-09-21]"
            print(f"  {name} 0x{off:x}  n={len(ids):3d}  {fmt(min(seq))}..{fmt(max(seq))}"
                  f"  ascending={ascending}{detail}")
        if frozen:
            print(f"  ({frozen} frozen {name} store(s) out of order: National Info shows them, so they fail too; "
                  f"see the module docstring)")
    return broken


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if args:
        saves = [Path(a) for a in args]
    else:
        saves = find_saves()
        if not saves:
            print("no .v3 saves found")
            return 0
        if "--all" not in argv:
            saves = saves[:1]

    broken = 0
    for save in saves:
        try:
            broken += check_save(save)
        except PlainTextSave as exc:    # debug mode writes plain text: say so, not a traceback
            print(exc)
            return 1
        print()
    if broken:
        print(f"{broken} history store(s) out of chronological order")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
