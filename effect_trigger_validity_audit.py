"""Parse-time audit: validate effect/trigger names against the engine (issue #146).

`modifier_visibility_audit` validates modifier names, but the engine only reports
invalid *effects/triggers* at runtime game-load (`Unknown effect X`,
`Unknown trigger type X`, `PostValidate ... returned false`) — invisible until a
relaunch + log triage. This session's triage found three such bugs an audit
would have caught at `POST /reload`:
  - `add_authority = -200`        — not a valid effect (no instant-authority effect)
  - `negate(sv_treasury_event_*)` — `negate(...)` call-syntax is not valid script
  - `set_country_flag` / other engine-foreign (CK3/EU4) keywords used in Vic3

Approach (strict-then-permissive, per the catalog-audit playbook):
- A frozen **valid-key catalog** (`docs/engine/effect_trigger_valid_keys.txt`)
  is bootstrapped once from vanilla: the union of (a) every effect/trigger name
  in `effects_summary.txt` / `triggers_summary.txt` and (b) every LHS keyword
  vanilla actually uses in the script regions of `_SCAN_ROOTS` (same entry-key
  scoping the audit applies, so vanilla's entity schema and modifier names stay
  out). (b) is essential — control-flow and scope keywords like `limit`, `if`,
  `every_scope_country` are NOT in the effect/trigger docs. Regenerate on a
  vanilla bump via `bootstrap_catalog()`.
- Event-target scopes (`trade_center`, ...) come from
  `docs/engine/event_targets_summary.txt`, read at audit time rather than
  frozen — the engine regenerates that file on every reload.
- The audit scans the mod's script-bearing dirs (`_SCAN_ROOTS`) and flags any
  lowercase LHS keyword not in the catalog and not a mod-defined name (scripted
  effect/trigger/on_action/script value). Uppercase tokens (scripted-effect
  `$PARAM$` call args) and `var:`-style refs are never LHS-matched, so they
  don't false-flag.
- It also flags `funcname(...)` call-syntax, which Paradox script never uses
  (catches `negate(...)`).

Entry-key scoping (issue #295): dirs like `common/laws` or `common/journal_entries`
mix script with per-entity *schema* (`progressiveness`, `icon`, `unlocking_laws`)
and with *modifier* blocks (`modifier = { country_prestige_mult = 0.1 }`) — two
namespaces this audit has no business validating (`modifier_visibility_audit`
owns the latter). So each such root declares the keys whose block bodies ARE
trigger/effect script (`possible`, `on_enact`, `will_propose`, ...); everything
outside those blocks is skipped, and everything nested inside them is scanned.
A root with `entry_keys=None` (events, scripted effects/triggers, on_actions,
script values) is script top to bottom and is scanned whole, as before.
Conservative by construction: a trigger block under a key nobody listed goes
unscanned rather than emitting schema-keyword noise — so extend the table when a
new entity type lands.

Scope note: this validates effect/trigger *names*. Value-level errors (e.g.
`has_role = general`, where `has_role` is a valid trigger but the value should be
`has_role_of_type = general`) are out of scope.

Suppress an intentional flag with an inline `# REVIEWED YYYY-MM-DD: rationale` on
the offending line. Report: docs/engine/effect_trigger_validity_report.md.
"""

import os
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScanRoot:
    """One directory of script, and how much of each file is script.

    `entry_keys=None` — the whole file is trigger/effect/script-value body.
    `entry_keys={...}` — only the bodies of `<key> = { ... }` blocks are, so
    the surrounding entity schema and its modifier blocks stay unscanned.
    `extra_valid` — keys valid as an LHS *inside* this root's script only (a
    schema keyword of a scanned block, e.g. the `header` of a JE's
    `event_outcome_*_effect_desc`). Root-scoped on purpose: unlike
    `_CURATED_VALID` these must not become globally valid.
    """

    rel: str
    entry_keys: frozenset[str] | None = None
    extra_valid: frozenset[str] = frozenset()


def _r(*parts: str) -> str:
    return os.path.join(*parts)


# Mod dirs scanned (relative to a root); also the vanilla corpus for bootstrap.
_SCAN_ROOTS: tuple[ScanRoot, ...] = (
    # --- script top to bottom ---
    ScanRoot("events"),
    ScanRoot(_r("common", "scripted_effects")),
    ScanRoot(_r("common", "scripted_triggers")),
    ScanRoot(_r("common", "on_actions")),
    # Script-value bodies are math + `if/limit` triggers all the way down.
    ScanRoot(_r("common", "script_values")),
    # --- entity dirs: only the trigger/effect blocks (issue #295) ---
    ScanRoot(
        _r("common", "diplomatic_actions"),
        entry_keys=frozenset({
            "potential", "possible", "selectable", "accept_effect",
            "second_state_trigger", "will_select_as_second_state",
            # `ai = { ... }` children, and the `pact = { ... }` script blocks —
            # matched at any depth, so neither wrapper needs to be an entry key
            # (`pact` also holds schema scalars and `second_modifier`).
            "evaluation_chance", "will_propose", "propose_score", "accept_score",
            "junior_accept_score", "will_break", "requirement_to_maintain",
            "manual_break_effect", "auto_break_effect", "monthly_effect",
            "show_about_to_break_warning",
        }),
        # Trigger block inside `requirement_to_maintain`, so it is itself seen
        # as an LHS from within scanned script.
        extra_valid=frozenset({"show_about_to_break_warning"}),
    ),
    ScanRoot(
        _r("common", "journal_entries"),
        entry_keys=frozenset({
            "possible", "is_shown_when_inactive", "immediate", "complete",
            "fail", "invalid", "on_complete", "on_fail", "on_invalid",
            "on_timeout", "on_monthly_pulse", "on_weekly_pulse",
            "on_yearly_pulse", "can_deactivate", "can_revolution_inherit",
            "should_be_pinned_by_default_uninvolved_or_context",
            # script values
            "current_value", "goal_add_value", "weight",
            # `desc`-style blocks — `first_valid`/`triggered_desc`/`trigger`
            "status_desc", "progress_desc", "custom_completion_header",
            "custom_failure_header", "custom_on_completion_header",
            "custom_on_failure_header", "event_outcome_activated_effect_desc",
            "event_outcome_completed_effect_desc",
            "event_outcome_failed_effect_desc",
        }),
        # `event_outcome_*_effect_desc = { header = X effect = { ... } }`
        extra_valid=frozenset({"header"}),
    ),
    ScanRoot(
        _r("common", "scripted_buttons"),
        entry_keys=frozenset({"visible", "possible", "effect", "ai_chance"}),
    ),
    ScanRoot(
        _r("common", "decisions"),
        entry_keys=frozenset({"is_shown", "possible", "when_taken", "ai_chance"}),
    ),
    ScanRoot(
        _r("common", "laws"),
        entry_keys=frozenset({
            "is_visible", "can_enact", "can_impose", "on_enact", "on_activate",
            "on_deactivate", "ai_will_do", "ai_enact_weight_modifier",
            "ai_impose_chance",
        }),
    ),
    ScanRoot(
        _r("common", "diplomatic_plays"),
        entry_keys=frozenset({
            "possible", "selectable_in_lens", "on_weekly_pulse",
            "on_war_begins", "on_war_end",
        }),
    ),
    ScanRoot(
        _r("common", "treaty_articles"),
        entry_keys=frozenset({
            "visible", "possible", "can_ratify", "state_valid_trigger",
            "company_valid_trigger", "on_entry_into_force", "on_break",
            "on_withdrawal", "requirement_to_maintain",
            "conditions",  # non_fulfillment = { conditions = { weekly = {...} } }
            # `ai = { ... }` script children (`article_ai_usage` /
            # `treaty_categories` next to them are schema, so `ai` itself is not
            # an entry key).
            "evaluation_chance", "inherent_accept_score", "quantity_input_value",
            "quantity_min_value", "quantity_max_value", "cost",
            "infamy", "maneuvers",  # wargoal = { ... } script values
        }),
        extra_valid=frozenset({
            "monthly", "weekly",   # non-fulfillment evaluation cadence wrappers
            "input_state", "input_company",  # treaty-article input scopes
        }),
    ),
    ScanRoot(
        _r("common", "power_bloc_principles"),
        entry_keys=frozenset({"possible", "visible", "ai_weight"}),
    ),
)

_CATALOG_REL = os.path.join("docs", "engine", "effect_trigger_valid_keys.txt")

# A lowercase LHS keyword: `key =` (single `=`, not `>=`/`<=`/`==`). The
# lookbehind keeps us from matching the tail of a dotted / word / `$PARAM$`-
# interpolated token (e.g. `heir_education_$TRAIT$_ig_reaction`).
_LHS_RE = re.compile(r"(?<![\w.:$])([a-z_][a-z0-9_]*)[ \t]*=(?!=)")
# Unquoted `name(` call-syntax — never valid in Paradox script (loc-only, and
# the legit Vic3 scripted-value-call form is quoted: `"funcname(ARG)"`, which we
# strip before matching). Catches `negate(...)`.
_CALL_RE = re.compile(r"(?<![\w.$])([a-z_][a-z0-9_]*)\(")
# Valid engine keys the vanilla events/scripted/on-action corpus happens not to
# use as an LHS (so they're absent from the bootstrapped catalog), confirmed
# valid by inspection. Strict-then-permissive: extend deliberately, with reason.
_CURATED_VALID: frozenset[str] = frozenset({
    "texture",  # event_image = { texture = ... } — vanilla always uses `video`
    "levels",   # add_ownership = { ... levels = N }
    "hue",      # colour field
    "ceiling",  # script-value rounding (ceiling = yes)
    "side",     # join_war = { side = scope:X } (vanilla uses it, just not in scope dirs)
    "parent",   # create_container = { parent = ... } / container iterator filter (1.13.10+; unused by vanilla script)
    "tags",     # create_container = { tags = { ... } } / container iterator filter (1.13.10+; unused by vanilla script)
    # Both were masked until #295 tightened `_top_level_names` to depth 0 — the
    # old any-indentation harvest picked them up out of the mod's own nesting
    # and called them "mod-defined names".
    "add_ownership",  # add_ownership = { country = { country = X levels = N } } (see `levels` above)
    "color",    # create_dynamic_country = { color = { R G B } } — colour literal, same family as `hue`
})
_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)
# Top-level entity definition: `name =` at brace depth 0 (optionally
# merge-prefixed). Deliberately not requiring `{`: a constant script value
# (`covert_ops_detection_base = 10`) defines a name just as much as a block does.
_TOP_DEF_RE = re.compile(
    r"^[ \t]*(?:REPLACE:|INJECT:|REPLACE_OR_CREATE:)?([a-z_][a-z0-9_]*)[ \t]*=(?!=)"
)
# A `<key> = {` block opener, used to spot a root's script entry points.
_BLOCK_OPEN_RE = re.compile(r"(?<![\w.:$])([a-z_][a-z0-9_]*)[ \t]*=[ \t]*\{")


@dataclass
class Flag:
    file: str
    line: int
    keyword: str
    kind: str  # "unknown-name" | "call-syntax"
    snippet: str
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)


_QUOTE_RE = re.compile(r'"[^"]*"')


def _strip_comment(line: str) -> tuple[str, str]:
    """Return (code, comment). Splits on the first `#` (good enough for script —
    `#` inside quoted strings is vanishingly rare in effect files)."""
    idx = line.find("#")
    if idx == -1:
        return line, ""
    return line[:idx], line[idx:]


def _strip_quotes(code: str) -> str:
    """Blank out double-quoted spans. LHS keys are never quoted, and the legit
    Vic3 scripted-value-call form (`"funcname(ARG)" < N`) lives inside quotes —
    removing quoted spans drops those false positives without losing real keys."""
    return _QUOTE_RE.sub(lambda m: " " * len(m.group(0)), code)


def parse_reviewed_comment(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _iter_txt(base: str):
    for dirpath, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".txt"):
                yield os.path.join(dirpath, f)


def extract_lhs_keys(text: str) -> set[str]:
    """Every lowercase LHS keyword in `text` (comments stripped)."""
    keys: set[str] = set()
    for line in text.splitlines():
        code, _ = _strip_comment(line)
        code = _strip_quotes(code)
        for m in _LHS_RE.finditer(code):
            keys.add(m.group(1))
    return keys


def _top_level_names(root: str) -> set[str]:
    """Top-level entity names defined under `root` (so a mod's own scripted
    effect / trigger / on_action / script-value names — and their definition
    LHS — never flag).

    Brace depth is tracked so only genuine depth-0 definitions count: matching
    at any indentation would harvest nested keys as if they were entity names
    and quietly widen `allowed`.
    """
    names: set[str] = set()
    if not os.path.isdir(root):
        return names
    for path in _iter_txt(root):
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                depth = 0
                for line in fh:
                    code, _ = _strip_comment(line)
                    code = _strip_quotes(code)
                    if depth == 0:
                        m = _TOP_DEF_RE.match(code)
                        if m:
                            names.add(m.group(1))
                    depth = max(0, depth + code.count("{") - code.count("}"))
        except OSError:
            continue
    return names


def _iter_script_lines(path: str, entry_keys: frozenset[str] | None):
    """Yield `(lineno, raw, code, comment)` for the parts of `path` that are
    trigger/effect script, per the root's entry-key scoping.

    `code` is comment- and quote-stripped and, on the line where an entry block
    opens, truncated to what follows the opening brace — so `possible = {` never
    offers `possible` itself as a key to validate.
    """
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return
    depth = 0
    entry_depth: int | None = None
    for n, raw in enumerate(lines, 1):
        code, comment = _strip_comment(raw)
        code = _strip_quotes(code)
        start: int | None = None
        if entry_keys is None or entry_depth is not None:
            start = 0
        else:
            for m in _BLOCK_OPEN_RE.finditer(code):
                if m.group(1) in entry_keys:
                    head = code[: m.end()]
                    entry_depth = depth + head.count("{") - head.count("}")
                    start = m.end()
                    break
        if start is not None:
            yield n, raw, code[start:], comment
        depth += code.count("{") - code.count("}")
        if entry_depth is not None and depth < entry_depth:
            entry_depth = None


_EVENT_TARGETS_REL = os.path.join("docs", "engine", "event_targets_summary.txt")


def load_event_targets(mod_path: str) -> set[str]:
    """Event-target names from `docs/engine/event_targets_summary.txt`.

    Scope transitions (`trade_center = { ... }`) and value targets
    (`ai_army_comparison = 1`) are legitimate LHS keys, but only the handful
    vanilla happens to use in the bootstrap corpus reach the frozen catalog.
    This file is regenerated from the engine on every reload, so read it live.
    """
    return _summary_names(os.path.join(mod_path, _EVENT_TARGETS_REL))


# --- catalog bootstrap (run once per vanilla version) ----------------------

def _summary_names(path: str) -> set[str]:
    """Parse `scope|name|desc` summary rows -> set of names."""
    names: set[str] = set()
    if not os.path.isfile(path):
        return names
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("#") or "|" not in line:
                continue
            parts = line.split("|")
            if len(parts) >= 2 and parts[1].strip():
                names.add(parts[1].strip())
    return names


def bootstrap_catalog(base_game_path: str, mod_path: str) -> dict:
    """Extract the frozen valid-key catalog from vanilla and write it to
    `docs/engine/effect_trigger_valid_keys.txt`. Re-run on a vanilla bump."""
    game = os.path.join(base_game_path, "game")
    engine_docs = os.path.join(mod_path, "docs", "engine")

    keys: set[str] = set()
    keys |= _summary_names(os.path.join(engine_docs, "effects_summary.txt"))
    keys |= _summary_names(os.path.join(engine_docs, "triggers_summary.txt"))
    # Harvested through the *same* entry-key scoping the audit uses, so the
    # catalog stays a catalog of script keywords: vanilla's law `modifier = { }`
    # bodies and entity schema must not leak in and silently widen what counts
    # as a valid effect/trigger everywhere else.
    for root in _SCAN_ROOTS:
        base = os.path.join(game, root.rel)
        if not os.path.isdir(base):
            continue
        for path in _iter_txt(base):
            for _n, _raw, code, _comment in _iter_script_lines(path, root.entry_keys):
                for m in _LHS_RE.finditer(code):
                    keys.add(m.group(1))

    out_path = os.path.join(mod_path, _CATALOG_REL)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(
            "# AUTO-GENERATED valid effect/trigger/scope/control-flow keyword "
            "catalog.\n# Union of effects_summary.txt + triggers_summary.txt "
            "names and every LHS keyword\n# vanilla uses in the script "
            "regions of effect_trigger_validity_audit._SCAN_ROOTS.\n"
            "# Regenerate on a vanilla bump: "
            "effect_trigger_validity_audit.bootstrap_catalog(...).\n"
        )
        for k in sorted(keys):
            f.write(k + "\n")
    return {"keys": len(keys), "path": out_path}


def load_catalog(mod_path: str) -> set[str]:
    path = os.path.join(mod_path, _CATALOG_REL)
    keys: set[str] = set()
    if not os.path.isfile(path):
        return keys
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                keys.add(line)
    return keys


# --- audit -----------------------------------------------------------------

def audit(mod_path: str, valid_keys: set[str] | None = None) -> AuditResult:
    if valid_keys is None:
        valid_keys = load_catalog(mod_path)
    # A mod's own top-level names (scripted effects/triggers/on-actions, script
    # values — which can be compared by name in a trigger — and every entity
    # name in the scanned roots) are valid call targets and definition LHS.
    mod_names: set[str] = set()
    for root in _SCAN_ROOTS:
        mod_names |= _top_level_names(os.path.join(mod_path, root.rel))
    event_targets = load_event_targets(mod_path)
    allowed = valid_keys | mod_names | event_targets | _CURATED_VALID

    flags: list[Flag] = []
    keys_checked = 0
    files_scanned = 0
    for root in _SCAN_ROOTS:
        base = os.path.join(mod_path, root.rel)
        if not os.path.isdir(base):
            continue
        root_allowed = allowed | root.extra_valid
        for path in _iter_txt(base):
            files_scanned += 1
            for n, raw, code, comment in _iter_script_lines(path, root.entry_keys):
                exemption = parse_reviewed_comment(comment)
                for m in _LHS_RE.finditer(code):
                    kw = m.group(1)
                    keys_checked += 1
                    if kw in root_allowed:
                        continue
                    flags.append(
                        Flag(path, n, kw, "unknown-name", raw.strip(), exemption)
                    )
                for m in _CALL_RE.finditer(code):
                    flags.append(
                        Flag(
                            path, n, m.group(1) + "(...)", "call-syntax",
                            raw.strip(), exemption,
                        )
                    )

    flags.sort(key=lambda f: (f.kind, f.keyword, f.file, f.line))
    return AuditResult(
        flags=flags,
        coverage={
            "files_scanned": files_scanned,
            "keys_checked": keys_checked,
            "catalog_size": len(valid_keys),
            "mod_defined_names": len(mod_names),
            "event_targets": len(event_targets),
            "roots_scanned": len(_SCAN_ROOTS),
            "flags": len(flags),
        },
    )


def render_report(result: AuditResult, mod_path: str = "") -> str:
    unreviewed = [f for f in result.flags if not f.exemption]
    exempted = [f for f in result.flags if f.exemption]
    cov = result.coverage

    def _loc(f: Flag) -> str:
        rel = os.path.relpath(f.file, mod_path) if mod_path else f.file
        return f"{rel}:{f.line}"

    out: list[str] = []
    out.append("# Effect / Trigger Name Validity Report")
    out.append("")
    out.append(
        "Lowercase LHS keywords in the mod's script that are neither a known "
        "engine effect/trigger/scope/control-flow keyword (per the frozen "
        "vanilla catalog) nor a mod-defined name — plus `funcname(...)` "
        "call-syntax, which Paradox script never uses. The engine silently "
        "ignores these until a runtime game-load `Unknown effect/trigger` error."
    )
    out.append("")
    out.append("Roots scanned:")
    out.append("")
    for root in _SCAN_ROOTS:
        rel = root.rel.replace(os.sep, "/")
        if root.entry_keys is None:
            out.append(f"- `{rel}/` — whole file")
        else:
            keys = ", ".join(f"`{k}`" for k in sorted(root.entry_keys))
            out.append(f"- `{rel}/` — script blocks only: {keys}")
    out.append("")
    out.append(
        f"- Files scanned: **{cov.get('files_scanned', 0)}**, keys checked: "
        f"**{cov.get('keys_checked', 0)}**"
    )
    out.append(
        f"- Catalog size: **{cov.get('catalog_size', 0)}** + mod-defined names: "
        f"**{cov.get('mod_defined_names', 0)}** + event targets: "
        f"**{cov.get('event_targets', 0)}**"
    )
    out.append(f"- Flags (unreviewed): **{len(unreviewed)}**")
    out.append(f"- Flags (REVIEWED-suppressed): **{len(exempted)}**")
    out.append("")

    if unreviewed:
        out.append("## Unreviewed")
        out.append("")
        for f in unreviewed:
            out.append(f"- `{f.keyword}` ({f.kind}) — {_loc(f)} — `{f.snippet}`")
        out.append("")
        out.append(
            "Fix the keyword, or add an inline `# REVIEWED YYYY-MM-DD: rationale` "
            "on the line if it is a false positive (e.g. a lowercase scripted-"
            "effect parameter)."
        )
        out.append("")
    else:
        out.append("No unreviewed effect/trigger name issues. ✅")
        out.append("")

    if exempted:
        out.append("## REVIEWED-suppressed")
        out.append("")
        for f in exempted:
            ex = f.exemption or {}
            out.append(
                f"- `{f.keyword}` ({f.kind}) — {_loc(f)} "
                f"(REVIEWED {ex.get('date', '?')}: {ex.get('rationale', '')})"
            )
        out.append("")

    return "\n".join(out)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_GENERATORS entry point. File-based; mod_state unused."""
    from path_constants import mod_path

    result = audit(mod_path)
    report = render_report(result, mod_path)
    out_path = os.path.join(
        mod_path, "docs", "engine", "effect_trigger_validity_report.md"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    return {
        "unreviewed": sum(1 for f in result.flags if not f.exemption),
        "exempted": sum(1 for f in result.flags if f.exemption),
        "path": out_path,
    }


if __name__ == "__main__":
    import sys
    from path_constants import mod_path as _mp

    if len(sys.argv) > 1 and sys.argv[1] == "bootstrap":
        # Only the bootstrap subcommand reads vanilla; keep the default audit
        # runnable on a machine with no Victoria 3 install.
        from path_constants import base_game_path

        print(bootstrap_catalog(base_game_path, _mp))
    else:
        print(render_report(audit(_mp), _mp))
