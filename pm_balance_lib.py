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


# ---------------------------------------------------------------------------
# Constants — keep the repo-relative directory list authoritative here so
# both the audit script and the server agree on what to walk.
# ---------------------------------------------------------------------------

PM_SUBDIR = Path("common") / "production_methods"
PM_FILES: list[str] = [
    "extra_pms.txt",
    "unique_pms.txt",
    "strategic_reserve_pms.txt",
    "resettlement_pms.txt",
    "te_construction_market_pms.txt",
]

# Flag values returned by classify_pm. Documented for /annotators consumers.
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

def iter_pms(path: Path) -> Iterator[tuple[str, str]]:
    """Yield (pm_id, body_with_comments) for each top-level PM in a file.

    Includes the leading comment block that precedes the PM's `= {` so we
    can parse the auto-generated cost summary.
    """
    text = path.read_text(encoding="utf-8-sig")
    pos = 0
    while pos < len(text):
        m = re.search(r"^pm_[A-Za-z0-9_]+\s*=\s*\{", text[pos:], re.MULTILINE)
        if not m:
            break
        pm_start = pos + m.start()
        pm_id_match = re.match(r"(pm_[A-Za-z0-9_]+)", text[pm_start:])
        pm_id = pm_id_match.group(1) if pm_id_match else "?"
        body_start = pm_start + m.end() - m.start()
        depth = 1
        i = body_start
        while i < len(text) and depth > 0:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            i += 1
        body = text[body_start:i - 1]
        yield pm_id, body
        pos = i


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
    """Walk PM files under `repo_root/common/production_methods/` and return
    `{pm_id: {flag, margin_pct, wage_be, profit, file}}` for every PM that
    has a cost-comment block. PMs without comments are recorded as
    `flag = "NO-COSTS"` with the numeric fields as None.
    """
    out: dict[str, dict] = {}
    pm_dir = repo_root / PM_SUBDIR
    if not pm_dir.exists():
        return out
    for fname in PM_FILES:
        path = pm_dir / fname
        if not path.exists():
            continue
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
