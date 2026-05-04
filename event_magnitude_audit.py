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
from typing import Callable


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


@dataclass
class AuditFlag:
    file: str
    line: int
    event_id: str | None
    kind: str             # "direct_effect" | "modifier_inline" | "modifier_named"
    effect: str           # the matched key (e.g. "add_treasury")
    value: str            # the literal string matched
    resource: str         # display name from ResourceMeta
    fix_hint: str         # display hint from ResourceMeta
    exemption: dict | None = None  # {date, rationale} when REVIEWED


def _is_literal_number(token: str) -> bool:
    """True for `100`, `-20`, `0.5`, `-3.14` etc.; False for identifiers."""
    try:
        float(token)
        return True
    except ValueError:
        return False


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


_ADD_MODIFIER_BLOCK_RE = re.compile(
    r"add_modifier\s*=\s*\{(?P<body>[^{}]*?)\}",
    re.DOTALL,
)
_NAME_RE = re.compile(r"(?<!\w)name\s*=\s*(?P<name>\S+)")
_MULTIPLIER_RE = re.compile(r"(?<!\w)multiplier\s*=\s*(?P<value>\S+)")


def _build_line_index(text: str) -> list[int]:
    """Return list of byte offsets where each line starts (1-indexed)."""
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _offset_to_line(starts: list[int], offset: int) -> int:
    line = 0
    for i, start in enumerate(starts):
        if start > offset:
            break
        line = i + 1
    return line


def scan_named_modifiers(
    text: str,
    file_path: str,
    lookup: Callable[[str], dict | None],
) -> list[AuditFlag]:
    """Find `add_modifier = { name = X multiplier = N }` blocks where the
    static modifier X carries a fast-scaling field and N is a literal.

    Emits one AuditFlag per fast-scaling field in X (a single static modifier
    can carry multiple fast-scaling fields, all scaled by the same multiplier).
    """
    flags: list[AuditFlag] = []
    lines = text.splitlines()
    line_starts = _build_line_index(text)

    for block_match in _ADD_MODIFIER_BLOCK_RE.finditer(text):
        body = block_match.group("body")
        name_m = _NAME_RE.search(body)
        mult_m = _MULTIPLIER_RE.search(body)
        if not name_m or not mult_m:
            continue
        name = name_m.group("name").rstrip(",")
        value = mult_m.group("value").rstrip("}").rstrip(",").rstrip()
        if not _is_literal_number(value):
            continue
        modifier_body = lookup(name)
        if not modifier_body:
            continue

        # The line of the multiplier (the actionable target for # REVIEWED).
        # mult_m.start() is relative to the body text; convert back to the
        # absolute file offset.
        mult_offset = block_match.start("body") + mult_m.start()
        mult_line = _offset_to_line(line_starts, mult_offset)
        line_text = lines[mult_line - 1] if 0 < mult_line <= len(lines) else ""
        exemption = parse_reviewed_comment(line_text)

        for field in modifier_body.keys():
            meta = FAST_SCALING_MODIFIERS.get(field)
            if not meta:
                continue
            flags.append(AuditFlag(
                file=file_path,
                line=mult_line,
                event_id=find_event_id_at_line(text, mult_line),
                kind="modifier_named",
                effect=field,
                value=value,
                resource=meta.resource,
                fix_hint=meta.fix_hint,
                exemption=exemption,
            ))
    return flags


def scan_inline_modifier_types(text: str, file_path: str) -> list[AuditFlag]:
    """Find `<fast-scaling-modifier-type> = <literal>` in event files.

    Catches the `add_modifier { country_prestige_add = N }` form (inline
    modifier-type fields, no static-modifier name lookup needed). Same
    word-boundary trick as scan_direct_effects so prefix/suffix collisions
    don't false-match.

    Note: this scanner doesn't validate that the match is *inside* an
    `add_modifier { }` block — but in events/*.txt the same modifier-type
    keys don't appear in any other context, so the simpler search is safe.
    """
    lines = text.splitlines()
    flags: list[AuditFlag] = []
    for i, line in enumerate(lines, start=1):
        for key, meta in FAST_SCALING_MODIFIERS.items():
            m = re.search(rf"(?<!\w){re.escape(key)}\s*=\s*(\S+)", line)
            if not m:
                continue
            value = m.group(1).rstrip("}").rstrip(",").rstrip()
            if not _is_literal_number(value):
                continue
            flags.append(AuditFlag(
                file=file_path,
                line=i,
                event_id=find_event_id_at_line(text, i),
                kind="modifier_inline",
                effect=key,
                value=value,
                resource=meta.resource,
                fix_hint=meta.fix_hint,
                exemption=parse_reviewed_comment(line),
            ))
    return flags


def scan_direct_effects(text: str, file_path: str) -> list[AuditFlag]:
    """Find `<direct_effect> = <literal>` lines for effects in DIRECT_EFFECTS."""
    lines = text.splitlines()
    flags: list[AuditFlag] = []
    for i, line in enumerate(lines, start=1):
        for effect, meta in DIRECT_EFFECTS.items():
            # Word-boundary so `add_treasury` doesn't match `something_add_treasury`.
            # Search anywhere on the line so single-line `immediate = { add_treasury = N }` works.
            m = re.search(rf"(?<!\w){re.escape(effect)}\s*=\s*(\S+)", line)
            if not m:
                continue
            value = m.group(1).rstrip("}").rstrip(",").rstrip()
            if not _is_literal_number(value):
                continue
            flags.append(AuditFlag(
                file=file_path,
                line=i,
                event_id=find_event_id_at_line(text, i),
                kind="direct_effect",
                effect=effect,
                value=value,
                resource=meta.resource,
                fix_hint=meta.fix_hint,
                exemption=parse_reviewed_comment(line),
            ))
    return flags
