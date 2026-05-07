#!/usr/bin/env python3
"""Vanilla tech-modifier baseline + polarity classification.

Walks vanilla era_1–5 tech files and produces, per modifier name:
- count of vanilla techs that use it
- min / median / max of values used in vanilla
- polarity classification (positive-good / negative-good / unknown) via a
  substring heuristic, overridable via `docs/tech_modifier_polarity.yml`

Used by `scripts/analysis/tech_balance_audit.py` to normalize each modifier
value against vanilla's typical, so that a `+0.10 country_innovation_mult`
and a `+0.10 state_pollution_generation_mult` are weighed by the scale
their respective modifier types actually operate at.

Cache: `docs/tech_modifier_baseline.json`. Refresh after vanilla bumps with
`tech_balance_audit.py --refresh-baseline`.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import tech_unlocks_lib  # noqa: E402
from path_constants import base_game_path  # noqa: E402

VANILLA_COMMON_DIR = Path(base_game_path) / "game" / "common"
VANILLA_TECH_DIR = VANILLA_COMMON_DIR / "technology" / "technologies"
VANILLA_FILES = ["10_production.txt", "20_military.txt", "30_society.txt"]

BASELINE_JSON = REPO / "docs" / "tech_modifier_baseline.json"
PATTERN_BASELINE_JSON = REPO / "docs" / "tech_modifier_pattern_baseline.json"
PATTERN_OVERRIDES_YAML = REPO / "docs" / "tech_modifier_pattern_overrides.yml"
POLARITY_YAML = REPO / "docs" / "tech_modifier_polarity.yml"


# ---------------------------------------------------------------------------
# Parametric modifier patterns
# ---------------------------------------------------------------------------
# Order matters: more specific patterns must come first. classify_pattern()
# returns the first match; collection logic uses the same precedence so
# building_group_* values aren't double-counted under building_*.

_PATTERN_DEFS = [
    ("building_group_<X>_throughput_add", r"building_group_[a-z][a-z0-9_]*?_throughput_add"),
    ("building_group_<X>_throughput_mult", r"building_group_[a-z][a-z0-9_]*?_throughput_mult"),
    ("building_group_<X>_employee_mult", r"building_group_[a-z][a-z0-9_]*?_employee_mult"),
    ("building_group_<X>_tax_mult", r"building_group_[a-z][a-z0-9_]*?_tax_mult"),
    ("building_<X>_throughput_add", r"building_[a-z][a-z0-9_]*?_throughput_add"),
    ("building_<X>_throughput_mult", r"building_[a-z][a-z0-9_]*?_throughput_mult"),
    ("building_<X>_employee_mult", r"building_[a-z][a-z0-9_]*?_employee_mult"),
    # `_add` variants of goods_output/goods_input collide with PM output
    # definitions (`unscaled = { goods_output_clothes_add = 20 }`) which
    # use the same syntax for raw production volumes. Only `_mult` forms
    # are reliably modifier-only.
    ("goods_output_<X>_mult", r"goods_output_[a-z][a-z0-9_]*?_mult"),
    ("goods_input_<X>_mult", r"goods_input_[a-z][a-z0-9_]*?_mult"),
    ("state_building_<X>_max_level_add", r"state_building_[a-z][a-z0-9_]*?_max_level_add"),
    ("state_building_<X>_max_level_mult", r"state_building_[a-z][a-z0-9_]*?_max_level_mult"),
    ("country_institution_<X>_max_investment_add", r"country_institution_[a-z][a-z0-9_]*?_max_investment_add"),
    ("interest_group_<X>_pol_str_factor", r"interest_group_[a-z][a-z0-9_]*?_pol_str_factor"),
    ("interest_group_<X>_pol_str_mult", r"interest_group_[a-z][a-z0-9_]*?_pol_str_mult"),
    ("interest_group_<X>_pop_attraction_mult", r"interest_group_[a-z][a-z0-9_]*?_pop_attraction_mult"),
    ("interest_group_<X>_approval_add", r"interest_group_[a-z][a-z0-9_]*?_approval_add"),
    ("interest_group_<X>_approval_mult", r"interest_group_[a-z][a-z0-9_]*?_approval_mult"),
    ("unit_<X>_offense_add", r"unit_[a-z][a-z0-9_]*?_offense_add"),
    ("unit_<X>_offense_mult", r"unit_[a-z][a-z0-9_]*?_offense_mult"),
    ("unit_<X>_defense_add", r"unit_[a-z][a-z0-9_]*?_defense_add"),
    ("unit_<X>_defense_mult", r"unit_[a-z][a-z0-9_]*?_defense_mult"),
    ("unit_<X>_morale_loss_add", r"unit_[a-z][a-z0-9_]*?_morale_loss_add"),
    ("unit_<X>_morale_loss_mult", r"unit_[a-z][a-z0-9_]*?_morale_loss_mult"),
    # Per-ship-type combat profile modifiers (mostly defined on ship_types
    # in vanilla; medians: accuracy_mult ~0.8, hull_damage_mult ~2.0).
    ("ship_battle_against_<X>_accuracy_add", r"ship_battle_against_[a-z][a-z0-9_]*?_accuracy_add"),
    ("ship_battle_against_<X>_accuracy_mult", r"ship_battle_against_[a-z][a-z0-9_]*?_accuracy_mult"),
    ("ship_battle_against_<X>_hull_damage_add", r"ship_battle_against_[a-z][a-z0-9_]*?_hull_damage_add"),
    ("ship_battle_against_<X>_hull_damage_mult", r"ship_battle_against_[a-z][a-z0-9_]*?_hull_damage_mult"),
    ("ship_battle_against_<X>_crew_damage_add", r"ship_battle_against_[a-z][a-z0-9_]*?_crew_damage_add"),
    ("ship_battle_against_<X>_crew_damage_mult", r"ship_battle_against_[a-z][a-z0-9_]*?_crew_damage_mult"),
    # Per-battle-condition character buffs (in commander_orders + character
    # traits). Polarity is name-dependent (good condition vs bad condition);
    # default polarity is `unknown` and the user tags individual modifiers
    # in tech_modifier_polarity.yml.
    ("character_battle_condition_<X>_add", r"character_battle_condition_[a-z][a-z0-9_]*?_add"),
    ("character_battle_condition_<X>_mult", r"character_battle_condition_[a-z][a-z0-9_]*?_mult"),
]

# Compiled anchored regexes for classification of a single name.
_PATTERN_RE_ANCHORED = [
    (pname, re.compile(rf"^{regex}$")) for pname, regex in _PATTERN_DEFS
]
# Single combined regex for fast extraction during the vanilla walk.
_PATTERN_RE_COMBINED = re.compile(
    r"\b(" + "|".join(regex for _, regex in _PATTERN_DEFS) + r")\b"
    r"\s*=\s*(-?\d+(?:\.\d+)?)"
)


def classify_pattern(name: str) -> str | None:
    """Return the pattern key (e.g. 'building_<X>_throughput_add') for `name`,
    or None if no parametric pattern matches."""
    for pname, regex in _PATTERN_RE_ANCHORED:
        if regex.match(name):
            return pname
    return None


# ---------------------------------------------------------------------------
# Tech body parsers (shared with tech_balance_audit.py)
# ---------------------------------------------------------------------------

def iter_techs(path: Path):
    """Yield (tech_id, body_text) for each top-level tech in a file."""
    text = path.read_text(encoding="utf-8-sig")
    text = re.sub(r"#[^\n]*", "", text)
    yield from tech_unlocks_lib.iter_top_level_blocks(text)


def extract_modifier_block(body: str) -> str:
    """Return the contents of the top-level `modifier = { ... }` block, or ''."""
    m = re.search(r"\bmodifier\s*=\s*\{", body)
    if not m:
        return ""
    start = m.end()
    depth = 1
    i = start
    while i < len(body) and depth > 0:
        c = body[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return body[start:i - 1]


def parse_modifiers(mod_block: str) -> list[tuple[str, float]]:
    """Extract (name, value) pairs from a modifier block.

    Skips `bool`-style `name = yes` lines (the regex requires a numeric value).
    """
    out = []
    for m in re.finditer(
        r"([a-z_][a-z0-9_]*)\s*=\s*(-?[0-9]+(?:\.[0-9]+)?)", mod_block
    ):
        out.append((m.group(1), float(m.group(2))))
    return out


def extract_field(body: str, field: str) -> str | None:
    m = re.search(rf"\b{re.escape(field)}\s*=\s*([A-Za-z_][A-Za-z0-9_]*)", body)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Polarity heuristic
# ---------------------------------------------------------------------------

# Substrings that indicate "positive value of this modifier is bad for the
# player". Verified against vanilla's known-negative cases.
_NEGATIVE_GOOD_SUBSTRINGS = (
    "pollution",
    "radicals",
    "radicalism",
    "_loss_",
    "_loss_mult",
    "_loss_add",
    "cost_factor",
    "_drain",
    "crowding",
    "infamy",
    "turmoil",
    "mortality",
    "disaster",
    "secession",
    "disloyalty",
    "_disease",
    "decay",
    "consumption_per_level",  # arable land consumption etc.
)

# Names whose direction is genuinely ambiguous — surfaced in
# tech_modifier_polarity.yml for user review.
_AMBIGUOUS_SUBSTRINGS = (
    "migration_pull",  # reducing pull may be good or bad depending on system
    "diplomatic_play_escalation",  # context-dependent
    "convoys_consumption",  # vanilla 1.13 lowers this for efficiency
    "support_separatism",  # some mods make it player-good (revolutionaries)
)


def classify_polarity(name: str) -> str:
    """Return 'positive-good' | 'negative-good' | 'unknown'.

    Heuristic only; user overrides in POLARITY_YAML take precedence (caller
    applies them).
    """
    lname = name.lower()
    for sub in _AMBIGUOUS_SUBSTRINGS:
        if sub in lname:
            return "unknown"
    for sub in _NEGATIVE_GOOD_SUBSTRINGS:
        if sub in lname:
            return "negative-good"
    return "positive-good"


def load_polarity_overrides(path: Path = POLARITY_YAML) -> dict[str, str]:
    """Load user polarity overrides from a YAML file.

    Format:
        country_some_mod: positive-good
        state_other_mod: negative-good

    Missing file → no overrides. Unknown values are ignored with a warning.
    """
    if not path.exists():
        return {}
    overrides: dict[str, str] = {}
    valid = {"positive-good", "negative-good", "unknown"}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip()
        if v in valid:
            overrides[k] = v
        else:
            print(
                f"polarity override for {k!r} has unknown value {v!r}; ignoring",
                file=sys.stderr,
            )
    return overrides


# ---------------------------------------------------------------------------
# Vanilla baseline walk
# ---------------------------------------------------------------------------

def walk_vanilla_modifiers() -> dict[str, list[float]]:
    """Return {modifier_name: [list of values used in vanilla techs]}."""
    out: dict[str, list[float]] = {}
    if not VANILLA_TECH_DIR.exists():
        print(
            f"vanilla tech dir not found: {VANILLA_TECH_DIR}", file=sys.stderr
        )
        return out
    for fname in VANILLA_FILES:
        path = VANILLA_TECH_DIR / fname
        if not path.exists():
            continue
        for _tech_id, body in iter_techs(path):
            mod_block = extract_modifier_block(body)
            for name, value in parse_modifiers(mod_block):
                out.setdefault(name, []).append(value)
    return out


def compute_baseline(
    values_by_name: dict[str, list[float]],
    polarity_overrides: dict[str, str] | None = None,
) -> dict[str, dict]:
    """Roll up per-modifier baseline stats and polarity."""
    overrides = polarity_overrides or {}
    out: dict[str, dict] = {}
    for name, values in values_by_name.items():
        if not values:
            continue
        # Use absolute values for the median anchor — sign is captured by
        # polarity, the magnitude is what we care about for normalization.
        abs_vals = [abs(v) for v in values]
        out[name] = {
            "vanilla_count": len(values),
            "vanilla_min": min(values),
            "vanilla_median": statistics.median(abs_vals),
            "vanilla_max": max(values),
            "polarity": overrides.get(name, classify_polarity(name)),
        }
    return out


def save_baseline(baseline: dict[str, dict], path: Path = BASELINE_JSON) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(baseline, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_baseline(path: Path = BASELINE_JSON) -> dict[str, dict]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get_or_build_baseline(refresh: bool = False) -> dict[str, dict]:
    """Cached entry point: load baseline JSON, or rebuild from vanilla.

    The baseline merges:
      - per-modifier-name values from vanilla era_1–5 tech `modifier = { }`
        blocks (the "tech walk", primary)
      - per-modifier-name values from the broad walk over all vanilla
        `common/*.txt` files, scoped to names that match a parametric
        pattern (laws, static_modifiers, character_traits, etc.) — so
        e.g. `state_building_barrack_max_level_add` gets a vanilla
        median even though no vanilla tech uses it.

    Tech-walk values take precedence on overlap.
    """
    if not refresh:
        cached = load_baseline()
        if cached:
            return cached
    overrides = load_polarity_overrides()
    values = walk_vanilla_modifiers()
    baseline = compute_baseline(values, overrides)
    # Enrich with broad-walk per-name medians for parametric pattern names
    _per_pattern, per_name_broad = walk_vanilla_pattern_instances()
    baseline = enrich_baseline_with_broad_walk(
        baseline, per_name_broad, overrides
    )
    save_baseline(baseline)
    return baseline


# ---------------------------------------------------------------------------
# Parametric pattern baseline (across all vanilla common/*.txt)
# ---------------------------------------------------------------------------

def walk_vanilla_pattern_instances() -> tuple[
    dict[str, list[tuple[str, float]]],
    dict[str, list[float]],
]:
    """Walk every vanilla `common/**/*.txt`, find every parametric-modifier
    instance (name = numeric_value) matching one of `_PATTERN_DEFS`, and
    bucket the pairs both:
      - per-pattern (under the most-specific pattern key)
      - per-modifier-name (so e.g. `state_building_barrack_max_level_add`
        gets its own median across vanilla buildings/laws/decrees)

    Returns (per_pattern, per_name).
    """
    per_pattern: dict[str, list[tuple[str, float]]] = {
        p[0]: [] for p in _PATTERN_DEFS
    }
    per_name: dict[str, list[float]] = {}
    if not VANILLA_COMMON_DIR.exists():
        print(
            f"vanilla common dir not found: {VANILLA_COMMON_DIR}",
            file=sys.stderr,
        )
        return per_pattern, per_name
    line_comment = re.compile(r"#[^\n]*")
    for txt in VANILLA_COMMON_DIR.rglob("*.txt"):
        try:
            text = txt.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        text = line_comment.sub("", text)
        for m in _PATTERN_RE_COMBINED.finditer(text):
            name = m.group(1)
            value = float(m.group(2))
            pattern = classify_pattern(name)
            if pattern is None:
                # Combined regex matched but specific anchored regex didn't —
                # shouldn't happen, but skip defensively.
                continue
            per_pattern[pattern].append((name, value))
            per_name.setdefault(name, []).append(value)
    return per_pattern, per_name


def compute_pattern_baseline(
    instances_by_pattern: dict[str, list[tuple[str, float]]],
) -> dict[str, dict]:
    """Roll up median/min/max + distinct-name count per pattern."""
    out: dict[str, dict] = {}
    for pattern, pairs in instances_by_pattern.items():
        if not pairs:
            continue
        vals = [v for _, v in pairs]
        abs_vals = [abs(v) for v in vals]
        names = sorted({n for n, _ in pairs})
        out[pattern] = {
            "vanilla_count": len(pairs),
            "vanilla_distinct_names": len(names),
            "vanilla_min": min(vals),
            "vanilla_median": statistics.median(abs_vals),
            "vanilla_max": max(vals),
        }
    return out


def enrich_baseline_with_broad_walk(
    baseline: dict[str, dict],
    per_name_broad: dict[str, list[float]],
    polarity_overrides: dict[str, str] | None = None,
) -> dict[str, dict]:
    """Add per-name medians for vanilla parametric-modifier names that
    appear outside tech blocks (laws, static_modifiers, character_traits,
    etc.) when they aren't already in the tech-walk baseline.

    Tech-walk values take precedence; broad-walk fills gaps. Marks added
    entries with `source: broad-walk` so downstream output can distinguish.
    """
    overrides = polarity_overrides or {}
    out = dict(baseline)
    for name, values in per_name_broad.items():
        if name in out:
            continue
        if not values:
            continue
        abs_vals = [abs(v) for v in values]
        out[name] = {
            "vanilla_count": len(values),
            "vanilla_min": min(values),
            "vanilla_median": statistics.median(abs_vals),
            "vanilla_max": max(values),
            "polarity": overrides.get(name, classify_polarity(name)),
            "source": "broad-walk",
        }
    return out


def save_pattern_baseline(
    pattern_baseline: dict[str, dict],
    path: Path = PATTERN_BASELINE_JSON,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(pattern_baseline, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_pattern_baseline(path: Path = PATTERN_BASELINE_JSON) -> dict[str, dict]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_pattern_overrides(path: Path = PATTERN_OVERRIDES_YAML) -> dict[str, float]:
    """Load user pattern-anchor overrides from a YAML file.

    Format:
        state_building_<X>_max_level_add: 1.0
        ship_battle_against_<X>_accuracy_add: 0.05

    These replace the computed vanilla median for the pattern (e.g. when
    the vanilla median is dragged up by outliers, or when no vanilla data
    exists for an `_add` variant).
    """
    if not path.exists():
        return {}
    overrides: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip()
        try:
            overrides[k] = float(v)
        except ValueError:
            print(
                f"pattern override for {k!r} has non-numeric value {v!r}; ignoring",
                file=sys.stderr,
            )
    return overrides


def apply_pattern_overrides(
    baseline: dict[str, dict],
    overrides: dict[str, float],
) -> dict[str, dict]:
    """Return a copy of `baseline` with `vanilla_median` replaced by user
    overrides where present. Adds patterns missing from vanilla data with
    only the override value populated. Annotates with `override=True` so
    output can flag user-set anchors."""
    out: dict[str, dict] = {p: dict(info) for p, info in baseline.items()}
    for pattern, value in overrides.items():
        existing = out.get(pattern, {})
        existing["vanilla_median"] = value
        existing["override"] = True
        # Make sure the entry has the basic keys even if pattern had no
        # vanilla data at all.
        existing.setdefault("vanilla_count", 0)
        existing.setdefault("vanilla_distinct_names", 0)
        existing.setdefault("vanilla_min", value)
        existing.setdefault("vanilla_max", value)
        out[pattern] = existing
    return out


def get_or_build_pattern_baseline(refresh: bool = False) -> dict[str, dict]:
    """Cached entry point: load pattern baseline JSON, or rebuild from vanilla
    common/*.txt walk (~17s on a fresh build). Always re-applies user
    overrides from `docs/tech_modifier_pattern_overrides.yml`."""
    if not refresh:
        cached = load_pattern_baseline()
        if cached:
            return apply_pattern_overrides(cached, load_pattern_overrides())
    per_pattern, _per_name = walk_vanilla_pattern_instances()
    baseline = compute_pattern_baseline(per_pattern)
    save_pattern_baseline(baseline)
    return apply_pattern_overrides(baseline, load_pattern_overrides())


def pattern_anchor_for(name: str, pattern_baseline: dict[str, dict]) -> tuple[float, str] | None:
    """Return (vanilla_median, pattern_key) for a name that matches a known
    parametric pattern, or None."""
    pattern = classify_pattern(name)
    if pattern is None:
        return None
    info = pattern_baseline.get(pattern)
    if not info or not info.get("vanilla_median"):
        return None
    return (info["vanilla_median"], pattern)


# ---------------------------------------------------------------------------
# CLI: refresh the cache standalone
# ---------------------------------------------------------------------------

def main() -> int:
    baseline = get_or_build_baseline(refresh=True)
    print(f"Vanilla tech-modifier baseline written to {BASELINE_JSON}")
    print(f"  {len(baseline)} unique modifier names")
    pos = sum(1 for v in baseline.values() if v["polarity"] == "positive-good")
    neg = sum(1 for v in baseline.values() if v["polarity"] == "negative-good")
    unk = sum(1 for v in baseline.values() if v["polarity"] == "unknown")
    print(f"  polarity: {pos} positive-good · {neg} negative-good · {unk} unknown")
    if unk:
        print(
            "  unknown polarities — review and override in "
            f"{POLARITY_YAML.relative_to(REPO)}:"
        )
        for name, info in sorted(baseline.items()):
            if info["polarity"] == "unknown":
                print(f"    - {name}")

    print("\nWalking vanilla common/*.txt for parametric pattern instances...")
    pattern_baseline = get_or_build_pattern_baseline(refresh=True)
    print(
        f"Pattern baseline written to {PATTERN_BASELINE_JSON.relative_to(REPO)}"
    )
    print(f"  {len(pattern_baseline)} parametric patterns matched")
    for pname, info in sorted(pattern_baseline.items()):
        print(
            f"  {pname:50}  n={info['vanilla_count']:4} "
            f"({info['vanilla_distinct_names']:3} distinct names)  "
            f"median={info['vanilla_median']:.4f}  "
            f"range=[{info['vanilla_min']:.3f}, {info['vanilla_max']:.3f}]"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
