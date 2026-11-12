"""Shared library for PM economic classification.

Extracts the parsing + flag heuristics out of
`scripts/analysis/pm_balance_audit.py` so the mod state server (and any
other consumer) can reuse them without round-tripping through the audit
script.

Also registers a single annotator at import time:
`Annotator(name="balance", entity_type="ProductionMethods", ...)`.

Cost comments aren't preserved by `paradox_file_parser` — they're stripped
during tokenization. So this module reads PM `.txt` files directly off
disk, mirroring the audit script's approach.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

import annotators
from paradox_file_parser import INJECT_DIRECTIVES


# ---------------------------------------------------------------------------
# Constants — keep the repo-relative directory authoritative here so both
# the audit script and the server agree on what to walk.
# ---------------------------------------------------------------------------

PM_SUBDIR = Path("common") / "production_methods"


def pm_file_names(repo_root: Path) -> list[str]:
    """Every `*.txt` under `repo_root/common/production_methods/`, sorted.

    The directory is the list: a hand-kept list of file names here went
    stale as PM files were added, and a PM in an unlisted file came back
    from `?annotate=balance` with no `flag` at all (#1552).
    """
    pm_dir = repo_root / PM_SUBDIR
    if not pm_dir.is_dir():
        return []
    return sorted(p.name for p in pm_dir.glob("*.txt"))


# Flag values returned by classify_pm. Documented for /annotators consumers.
#
# Interpretation gotchas (read before acting on these flags):
#
# - `wage_breakeven` is £ per worker per week, not a revenue share. It's
#   `profit / employment` (see pm_costs.py) — the pop wage at which the
#   building's profit hits zero. HIGHER = more wage headroom (healthy);
#   LOWER = the PM only pays out when wages stay near zero.
#
# - `HIGH-WAGE` is therefore a wage-headroom flag, not a labor-cost
#   concern. The genuine pop-squeeze signal is `LOW-WAGE` (margin > 0
#   and breakeven < 0.01).
#
# - For substitution PMs (e.g. the `pmg_steam_automation_*_mine` chain,
#   where each tier replaces the previous and trades input cost for
#   reduced employment), `DEEP-LOSS` reports the per-PM-block delta the
#   substitution adds, not the building's net economics. The
#   wage_breakeven captures the actual sign change — the substitution
#   is net good for the building when pop wages exceed it. Don't read a
#   `DEEP-LOSS` flag on a substitution PM as "fix the loss"; read it as
#   "where does this tier sit on the chain's wage_breakeven curve?"
FLAGS = ("OK", "HIGH-PROFIT", "DEEP-LOSS", "HIGH-WAGE", "LOW-WAGE",
         "THROUGHPUT", "NO-COSTS")

# Thresholds — kept here so they're discoverable rather than buried in main().
HIGH_PROFIT_MARGIN_PCT = 100
DEEP_LOSS_MARGIN_PCT = -50
HIGH_WAGE_BREAKEVEN = 0.30
LOW_WAGE_BREAKEVEN = 0.01

# Modifier blocks that indicate a PM produces value through modifiers rather
# than goods. Used by is_throughput_pm to auto-classify.
_MODIFIER_BLOCK_RE = re.compile(
    r"\b(country_modifiers|state_modifiers|building_modifiers|"
    r"unit_modifier|character_modifier|timed_modifier)\s*=\s*\{",
)


# ---------------------------------------------------------------------------
# Parsing primitives
# ---------------------------------------------------------------------------

# A top-level definition: `<id> = {` at the start of a line, with an optional
# merge directive (`REPLACE:pm_x = {`). Not every PM is named `pm_*` (the
# plantation methods are `factory_farm_building_*` and
# `GMO_plantation_building_*`), and an id may hold a hyphen
# (`pm_coal-fired_plant`).
_TOP_LEVEL_RE = re.compile(
    r"^(?:(?P<directive>[A-Z_]+):)?(?P<id>[A-Za-z0-9_.-]+)\s*=\s*\{",
    re.MULTILINE,
)


def iter_pms(path: Path) -> Iterator[tuple[str, str]]:
    """Yield (pm_id, body_with_comments) for each PM a file defines.

    Includes the leading comment block that precedes the PM's `= {` so we
    can parse the auto-generated cost summary.

    A `REPLACE:` block (and its `TRY_` and `_OR_CREATE` forms) is a whole
    definition and is yielded under the bare id, as the engine resolves it.
    An `INJECT:` block is a patch to a PM defined somewhere else, usually in
    vanilla, and carries no economics of its own: it is skipped, so it can
    neither stand in for the PM nor overwrite the row of one the mod defines.
    """
    text = path.read_text(encoding="utf-8-sig")
    pos = 0
    while pos < len(text):
        m = _TOP_LEVEL_RE.search(text, pos)
        if not m:
            break
        body_start = m.end()
        depth = 1
        i = body_start
        while i < len(text) and depth > 0:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            i += 1
        pos = i
        if m.group("directive") in INJECT_DIRECTIVES:
            continue
        yield m.group("id"), text[body_start:i - 1]


def parse_cost_comments(body: str) -> dict | None:
    """Extract auto-generated cost summary from PM body comments.

    Returns dict with keys: total_input, total_output, profit,
    profit_margin_pct, wage_breakeven, has_throughput_tag. None if no
    `Profit margin` line was found (the PM has no cost comment block).
    """
    out: dict = {"has_throughput_tag": False}
    for line in body.split("\n"):
        line = line.strip()
        # Explicit author override: `# AUDIT: throughput-pm` marks a PM as
        # intentionally negative-goods-balance, evaluated via its modifier
        # block. Lets the audit skip false-positive DEEP-LOSS / HIGH-WAGE
        # flags for research/comms/throughput PMs.
        if re.match(r"#\s*AUDIT:\s*throughput-pm\b", line, re.IGNORECASE):
            out["has_throughput_tag"] = True
            continue
        m = re.match(r"#\s*Total input cost:\s*([-\d.]+)", line)
        if m:
            out["total_input"] = float(m.group(1))
            continue
        m = re.match(r"#\s*Total output cost:\s*([-\d.]+)", line)
        if m:
            out["total_output"] = float(m.group(1))
            continue
        m = re.match(r"#\s*Profit:\s*([-\d.]+)", line)
        if m:
            out["profit"] = float(m.group(1))
            continue
        m = re.match(r"#\s*Profit margin:\s*([-\d.]+)%", line)
        if m:
            out["profit_margin_pct"] = float(m.group(1))
            continue
        m = re.match(r"#\s*Wage breakeven:\s*([-\d.]+)", line)
        if m:
            out["wage_breakeven"] = float(m.group(1))
            continue
    return out if "profit_margin_pct" in out else None


def is_throughput_pm(body: str, costs: dict) -> bool:
    """Detect modifier-only PMs whose value is in their modifier blocks.

    A PM qualifies if author-tagged `# AUDIT: throughput-pm`, OR if the
    auto-generated cost block reports zero output AND the PM declares at
    least one modifier block carrying a non-input/output line. The second
    arm covers research / comms / throughput-multiplier PMs that the goods
    balance can't see.
    """
    if costs.get("has_throughput_tag"):
        return True
    if costs.get("total_output", 1) > 0:
        return False
    if costs.get("total_input", 0) <= 0:
        return False
    for m in _MODIFIER_BLOCK_RE.finditer(body):
        depth = 1
        i = m.end()
        while i < len(body) and depth > 0:
            c = body[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            i += 1
        block = body[m.end():i - 1]
        for ln in block.split("\n"):
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            if re.match(r"goods_(input|output)_", ln):
                continue
            if "=" in ln:
                return True
    return False


def classify_pm(body: str, costs: dict | None) -> str:
    """Decide a flag for a PM given its parsed cost-comment dict.

    Mirrors the inline if-chain previously in pm_balance_audit.main().
    Throughput PMs are picked up first to avoid surfacing them as
    DEEP-LOSS / HIGH-WAGE false positives.
    """
    if costs is None:
        return "NO-COSTS"
    if is_throughput_pm(body, costs):
        return "THROUGHPUT"
    margin = costs["profit_margin_pct"]
    wage_be = costs.get("wage_breakeven")
    if margin > HIGH_PROFIT_MARGIN_PCT:
        return "HIGH-PROFIT"
    if margin < DEEP_LOSS_MARGIN_PCT:
        return "DEEP-LOSS"
    if wage_be is not None and wage_be > HIGH_WAGE_BREAKEVEN:
        return "HIGH-WAGE"
    if wage_be is not None and wage_be < LOW_WAGE_BREAKEVEN and margin > 0:
        return "LOW-WAGE"
    return "OK"


# ---------------------------------------------------------------------------
# Bulk index — used by the annotator's compute() and by the audit script.
# ---------------------------------------------------------------------------

def build_pm_balance_map(repo_root: Path) -> dict[str, dict]:
    """Walk every PM file under `repo_root/common/production_methods/` and
    return `{pm_id: {flag, margin_pct, wage_be, profit, file}}` for every PM
    the mod defines. PMs without a cost-comment block are recorded as
    `flag = "NO-COSTS"` with the numeric fields as None.

    `file` and `profit` are for callers of this function. The annotator
    declares `flag`, `margin_pct` and `wage_be`, and only those are merged
    into a server entry.
    """
    out: dict[str, dict] = {}
    pm_dir = repo_root / PM_SUBDIR
    for fname in pm_file_names(repo_root):
        path = pm_dir / fname
        for pm_id, body in iter_pms(path):
            costs = parse_cost_comments(body)
            flag = classify_pm(body, costs)
            row: dict = {
                "flag": flag,
                "file": fname,
                "margin_pct": costs.get("profit_margin_pct") if costs else None,
                "wage_be": costs.get("wage_breakeven") if costs else None,
                "profit": costs.get("profit") if costs else None,
            }
            out[pm_id] = row
    return out


# ---------------------------------------------------------------------------
# Annotator registration — happens at import time.
# ---------------------------------------------------------------------------

# Entity type matches the key used by ModState.mod_parsers (see mod_state_server.py
# `base_game_paths` / `mod_paths`) so the annotator finds entries returned by
# the server's PM-related endpoints.
PM_ENTITY_TYPE = "PMs"


annotators.register(annotators.Annotator(
    name="balance",
    entity_type=PM_ENTITY_TYPE,
    fields=["flag", "margin_pct", "wage_be"],
    description=(
        "Per-PM economic classification (HIGH-PROFIT / DEEP-LOSS / "
        "THROUGHPUT / HIGH-WAGE / LOW-WAGE / OK / NO-COSTS) computed "
        "from auto-generated cost comments."
    ),
    compute=build_pm_balance_map,
))
