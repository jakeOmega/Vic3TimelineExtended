"""Detects hardcoded delta values in events for fast-scaling resources.

Background: a `multiplier = -20` on a prestige modifier is invisible at
late-game scale (-20 / 163,028 = 0.012%). The audit flags such literals
in events/*.txt and recommends a scaled fix path (mult-based static
modifier, or sv_<resource>_event_<tier> script value).

Adding a new fast-scaling resource: one entry in FAST_SCALING_MODIFIERS
or DIRECT_EFFECTS. Verify the modifier exists via /modifier-search and
that a scaling fix path (`<X>_mult` modifier or a script-value source
like `value = prestige`) is available before adding.

Suppress an intentional hardcoded value with a same-line comment:

    multiplier = 2000  # REVIEWED 2026-05-04: tech-gated; intentionally large
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceMeta:
    resource: str   # display name shown in the report (e.g. "prestige")
    fix_hint: str   # short suggestion for the report's fix column


# Modifier-type keys checked inside static modifiers referenced via
# add_modifier { name = X multiplier = N } (named form), AND inline
# modifier-type keys inside add_modifier { country_prestige_add = N } blocks.
FAST_SCALING_MODIFIERS: dict[str, ResourceMeta] = {
    "country_prestige_add": ResourceMeta(
        resource="prestige",
        fix_hint=(
            "use prestige_loss_<tier> / prestige_gain_<tier> static modifier "
            "(mult-based, no multiplier needed), OR "
            "multiplier = sv_prestige_event_<tier>"
        ),
    ),
    "country_bureaucracy_add": ResourceMeta(
        resource="bureaucracy",
        fix_hint=(
            "use bureaucracy_loss_<tier> / bureaucracy_gain_<tier> static "
            "modifier (mult-based, no multiplier needed)"
        ),
    ),
    # Deferred to v2 (need verified script-value source or mult counterpart):
    #   country_construction_add  — no mult; bare-name `construction` token unverified
    #   country_expenses_add      — no mult; no script-value source verified
    #   country_minting_add       — has mult but conversion ratio is non-trivial
}

# Direct effects (not modifier types). Keys are effect names that take a
# numeric value as their right-hand side.
DIRECT_EFFECTS: dict[str, ResourceMeta] = {
    "add_treasury": ResourceMeta(
        resource="treasury (instant)",
        fix_hint="use add_treasury = sv_treasury_event_<tier>",
    ),
}


# ---------------------------------------------------------------------------
# Source-text helpers (line-based; the AST loses comments + line numbers).
# ---------------------------------------------------------------------------

# Matches event header lines like:
#   foo_events.123 = {
#   REPLACE:foo_events.123 = {
#   INJECT:foo_events.123 = {
#   REPLACE_OR_CREATE:foo_events.123 = {
# Captures the bare event id (without the directive prefix).
_EVENT_HEADER_RE = re.compile(
    r"^(?:REPLACE:|INJECT:|REPLACE_OR_CREATE:)?([A-Za-z_]\w*\.\w+)\s*=\s*\{"
)


_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)


def parse_reviewed_comment(line: str) -> dict | None:
    """Look for `# REVIEWED YYYY-MM-DD: rationale` on the given line.

    Returns {date, rationale} or None. Both date and rationale are required
    so that suppressions stay accountable — drive-by `# REVIEWED` doesn't work.
    """
    m = _REVIEWED_RE.search(line)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def find_event_id_at_line(text: str, line_no: int) -> str | None:
    """Walk upward from `line_no` (1-indexed) to the most recent event header.

    Returns the event id, or None if no header is above the line. Bare-bones
    implementation: doesn't track brace depth, so a value inside a deeply-
    nested `event { }` block in a non-event file would resolve to the most
    recent event-shaped header. For events/*.txt that's correct.
    """
    lines = text.splitlines()
    if not (1 <= line_no <= len(lines)):
        return None
    for i in range(line_no - 1, -1, -1):
        m = _EVENT_HEADER_RE.match(lines[i].lstrip())
        if m:
            return m.group(1)
    return None
