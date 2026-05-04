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
import os
import re
from dataclasses import dataclass, field
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
        if not name_m:
            continue
        name = name_m.group("name").rstrip(",")
        modifier_body = lookup(name)
        if not modifier_body:
            continue

        # Find any fast-scaling fields the static modifier carries, with their
        # raw values (so we can report the actual magnitude in the unscaled case).
        fast_fields = [
            (field, value, FAST_SCALING_MODIFIERS[field])
            for field, value in modifier_body.items()
            if field in FAST_SCALING_MODIFIERS
        ]
        if not fast_fields:
            continue

        mult_m = _MULTIPLIER_RE.search(body)
        if mult_m:
            mult_value = mult_m.group("value").rstrip("}").rstrip(",").rstrip()
            if not _is_literal_number(mult_value):
                # multiplier = sv_<...> — already scaled, skip
                continue
            # Anchor # REVIEWED on the multiplier line
            anchor_offset = block_match.start("body") + mult_m.start()
            display_value = mult_value
            kind = "modifier_named"
            extra_hint = ""
        else:
            # No multiplier: defaults to 1, the static modifier's own field
            # value applies absolutely. This is the failure mode where the
            # magnitude lives inside the static modifier definition itself.
            anchor_offset = block_match.start("body") + name_m.start()
            display_value = "(no multiplier; static modifier carries hardcoded value)"
            kind = "modifier_named_no_mult"
            extra_hint = (
                f" — `{name}` carries a hardcoded fast-scaling field; "
                "either replace the reference with a mult-based generic "
                "(prestige_loss_<tier> / bureaucracy_loss_<tier>), or "
                "convert the static modifier itself to use _mult."
            )

        anchor_line = _offset_to_line(line_starts, anchor_offset)
        line_text = lines[anchor_line - 1] if 0 < anchor_line <= len(lines) else ""
        exemption = parse_reviewed_comment(line_text)

        for field, field_value, meta in fast_fields:
            shown = display_value if mult_m else f"{field}={field_value} (in {name})"
            flags.append(AuditFlag(
                file=file_path,
                line=anchor_line,
                event_id=find_event_id_at_line(text, anchor_line),
                kind=kind,
                effect=field,
                value=shown,
                resource=meta.resource,
                fix_hint=meta.fix_hint + extra_hint,
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


# ---------------------------------------------------------------------------
# Top-level audit() entrypoint.
# ---------------------------------------------------------------------------


@dataclass
class AuditResult:
    flags: list[AuditFlag] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)


def _make_static_modifier_lookup(ms) -> Callable[[str], dict | None]:
    """Build a name→{field: value} lookup from ModState's parsed Modifiers.

    The parser stores each modifier as ('=', {field: ('=', value), ...}). We
    unwrap one level for the modifier body and one level for each field value.

    `Modifiers` is ModState's entity-type label for static modifiers (the
    ones in common/static_modifiers/). See /status entity_types.
    """
    raw = ms.get_data("Modifiers") or {}

    def lookup(name: str) -> dict | None:
        entry = raw.get(name)
        if entry is None:
            return None
        body = entry[1] if isinstance(entry, tuple) and len(entry) == 2 else entry
        if not isinstance(body, dict):
            return None
        return {
            k: (v[1] if isinstance(v, tuple) and len(v) == 2 else v)
            for k, v in body.items()
        }

    return lookup


def audit(ms, mod_path: str | None = None) -> AuditResult:
    """Walk every events/*.txt file, return all magnitude flags.

    `mod_path` defaults to whatever `path_constants.mod_path` resolves to so
    tests can pass a tempdir explicitly without touching the global config.
    """
    if mod_path is None:
        # Lazy import so tests that don't need real paths don't import path_constants.
        from path_constants import mod_path as _default
        mod_path = _default
    lookup = _make_static_modifier_lookup(ms)
    events_dir = os.path.join(mod_path, "events")
    if not os.path.isdir(events_dir):
        return AuditResult(flags=[], coverage={"files_audited": 0})

    flags: list[AuditFlag] = []
    files_audited = 0
    for fname in sorted(os.listdir(events_dir)):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(events_dir, fname)
        with open(fpath, encoding="utf-8-sig") as f:
            text = f.read()
        rel = os.path.join("events", fname)
        flags.extend(scan_direct_effects(text, file_path=rel))
        flags.extend(scan_inline_modifier_types(text, file_path=rel))
        flags.extend(scan_named_modifiers(text, file_path=rel, lookup=lookup))
        files_audited += 1

    return AuditResult(flags=flags, coverage={"files_audited": files_audited})


def render_report(result: AuditResult) -> str:
    """Render a markdown report. Top section is the actionable inbox."""
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Event magnitude audit report",
        "",
        "Auto-generated by `event_magnitude_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Suppress a flag by adding a same-line comment in the format:",
        "`# REVIEWED YYYY-MM-DD: rationale`",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out.append("_None._")
        out.append("")
    else:
        by_resource: dict[str, list[AuditFlag]] = {}
        for f in unrev:
            by_resource.setdefault(f.resource, []).append(f)
        for resource in sorted(by_resource):
            out.append(f"### {resource} ({len(by_resource[resource])})")
            out.append("")
            for f in by_resource[resource]:
                # The no-mult case stores `field=value (in name)` in `value` already,
                # so don't repeat the field name in front of it.
                if f.kind == "modifier_named_no_mult":
                    detail = f"`{f.value}`"
                else:
                    detail = f"`{f.effect} = {f.value}`"
                out.append(
                    f"- `{f.file}:{f.line}` — event `{f.event_id or '?'}` — "
                    f"{detail} — fix: {f.fix_hint}"
                )
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        for f in exemp:
            out.append(
                f"- `{f.file}:{f.line}` — `{f.event_id or '?'}` — "
                f"`{f.effect} = {f.value}` — {f.exemption['date']}: "
                f"{f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    for k, v in result.coverage.items():
        out.append(f"- {k}: {v}")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Post-load hook (matches POST_LOAD_GENERATORS protocol in mod_state_server).
# ---------------------------------------------------------------------------


def regenerate(mod_state) -> dict:
    """Run the audit and write docs/event_magnitude_report.md.

    Returns a small summary dict so the caller can log counts.
    Failures should propagate; the server's _run_post_load_generators wraps
    each call in try/except.
    """
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(mod_path, "docs", "event_magnitude_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    unrev = sum(1 for f_ in result.flags if not f_.exemption)
    exemp = sum(1 for f_ in result.flags if f_.exemption)
    return {
        "files_audited": result.coverage.get("files_audited", 0),
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": exemp,
    }
