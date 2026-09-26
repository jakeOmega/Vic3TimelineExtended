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
  vanilla actually uses across the same `SCAN_ROOTS` the audit checks. (b) is
  essential — control-flow and scope keywords like `limit`, `if`,
  `every_scope_country` are NOT in the effect/trigger docs, and neither are the
  entity-schema fields of the `common/` roots. Regenerate on a vanilla bump via
  `bootstrap_catalog()`.
- The audit scans every script-bearing mod dir in `SCAN_ROOTS` — the original
  four plus the `common/` entity dirs that carry effect/trigger blocks
  (`scripted_buttons`, `journal_entries`, `diplomatic_actions`, `decisions`,
  `character_interactions`, `scripted_progress_bars`, `treaty_articles`,
  `political_movements`, `diplomatic_plays`, `power_bloc_principles`, `laws`,
  `script_values`) — and flags any lowercase LHS keyword not in the catalog and
  not a mod-defined callable name. Uppercase tokens (scripted-effect `$PARAM$`
  call args) and `var:`-style refs are never LHS-matched, so they don't
  false-flag. Names at brace depth 0 are entity *definitions*, not calls, so
  they're never checked; each root declares its own entity-schema fields in
  `ScanRoot.extra_valid`.
- An unknown name in *call form* (`x = yes`, `x = { ... }`) is reported as
  `unresolved-helper-call` — a scripted effect/trigger that was renamed or
  deleted with a call site left behind (#288, where a deleted
  `covert_op_refresh_all_targets` survived in `scripted_buttons/`). Everything
  else is `unknown-name` (#295, where 1.14 removed `has_war_exhaustion` but
  `diplomatic_actions/nuke.txt` kept using it).
- Static-modifier block bodies (`modifier = { ... }`, `member_modifier`, …) are
  skipped: those names belong to `modifier_visibility_audit`.
- It also flags `funcname(...)` call-syntax, which Paradox script never uses
  (catches `negate(...)`).

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
    """One directory of the mod (and of vanilla, for the bootstrap) to scan.

    `extra_valid` holds that file format's *entity-schema* fields — LHS keys the
    engine reads off the entity itself rather than as effects/triggers (a journal
    entry's `header`, a diplomatic action's `requires_approval`, …). They are a
    stopgap: `bootstrap_catalog` harvests the same keys from vanilla's matching
    directory, so on the next vanilla bump the catalog subsumes most of this
    list. Keep entries here only when vanilla's corpus doesn't use them.

    `skip_blocks` names blocks whose *body* belongs to another namespace and is
    validated by another audit — in practice the static-modifier containers
    (`modifier`, `member_modifier`, …), whose contents are modifier names owned
    by `modifier_visibility_audit`. `add_modifier`/`ai_enact_weight_modifier` are
    deliberately NOT in it: their bodies are effect args and script-value math.
    """

    rel: str
    extra_valid: frozenset[str] = frozenset()
    skip_blocks: frozenset[str] = frozenset()


# Static-modifier container blocks: `<name> = { <modifier_name> = <number> ... }`.
# Their contents are modifier names, not effects/triggers — `modifier_visibility_audit`
# owns them, so the scan skips the block body wherever it appears.
_STATIC_MODIFIER_BLOCKS: frozenset[str] = frozenset({
    "modifier",
    "modifiers_while_active",
    "acceptance_modifier",
    "institution_modifier",
    "member_modifier",
    "non_member_modifier",
    "leader_modifier",
    "non_leader_modifier",
    "participant_modifier",
    "power_bloc_modifier",
    "source_modifier",
    "target_modifier",
    "mutual_modifier",
    "second_modifier",
    "first_modifier",
})

# Gate / weight blocks nearly every scriptable entity type declares. Grouped so
# each root below doesn't repeat them; scoped to the entity roots only, so they
# stay invalid inside an event or a scripted effect body.
_ENTITY_GATES: frozenset[str] = frozenset({
    "possible", "visible", "is_visible", "is_shown", "potential", "selectable",
    "ai", "ai_weight", "ai_will_do", "evaluation_chance",
})

# Mod dirs scanned (relative to a root); also the vanilla corpus for bootstrap.
# The original four (#146) carry no schema fields of their own — every LHS in an
# event / scripted helper / on-action body is an effect, trigger or control-flow
# keyword. The rest were added for #288 and #295: script blocks live in those
# directories too, and an unknown keyword there (a deleted scripted effect still
# called from a button, a trigger vanilla removed) was previously invisible.
SCAN_ROOTS: tuple[ScanRoot, ...] = (
    ScanRoot("events"),
    ScanRoot(os.path.join("common", "scripted_effects")),
    ScanRoot(os.path.join("common", "scripted_triggers")),
    ScanRoot(os.path.join("common", "on_actions")),
    # --- #288 / #295: the other script-bearing entity directories -----------
    ScanRoot(
        os.path.join("common", "scripted_buttons"),
        extra_valid=_ENTITY_GATES,
    ),
    ScanRoot(
        os.path.join("common", "journal_entries"),
        extra_valid=_ENTITY_GATES | frozenset({
            "group", "header", "progressbar", "widget", "gui", "container",
            "scripted_button", "scripted_progress_bar",
            "can_revolution_inherit", "can_deactivate",
            "should_update_on_player_command",
            "should_be_pinned_by_default_uninvolved_or_context",
            "is_shown_when_inactive", "is_shown_in_lobby",
            "complete", "fail", "invalid",
            "on_complete", "on_fail", "on_invalid", "on_timeout",
            "on_weekly_pulse", "current_value", "goal_add_value",
            "progress_desc", "status_desc",
            "custom_completion_header", "custom_on_completion_header",
            "custom_failure_header", "custom_on_failure_header",
            "event_outcome_activated_effect_desc",
            "event_outcome_completed_effect_desc",
            "event_outcome_failed_effect_desc",
        }),
        skip_blocks=_STATIC_MODIFIER_BLOCKS,
    ),
    ScanRoot(
        os.path.join("common", "diplomatic_actions"),
        extra_valid=_ENTITY_GATES | frozenset({
            "requires_approval", "show_confirmation_box", "is_hostile", "cost",
            "is_two_sided_pact", "show_in_outliner", "should_notify_third_parties",
            "show_effect_in_tooltip", "show_in_lens", "state_selection",
            "second_state_list", "second_state_trigger",
            "will_select_as_second_state", "groups", "pact", "monthly_effect",
            "requirement_to_maintain", "show_about_to_break_warning",
            "will_break", "will_propose", "accept_effect", "accept_score",
            "junior_accept_score", "propose_score",
            "auto_break_effect", "manual_break_effect",
            "max_influence_spending_fraction", "relations_progress_per_day",
            "relations_improvement_max", "relations_improvement_min",
            "income_transfer_to_pops", "second_country_gets_income_transfer",
            "max_paying_country_income_to_transfer", "allow_non_fully_accepted",
            "upper_strata_pops", "middle_strata_pops", "lower_strata_pops",
            "income_transfer_based_on_second_country",
            # The rest of the vanilla pact / AI vocabulary
            # (common/diplomatic_actions/diplomatic_action.md), valid in
            # call form (#456).
            "actor_can_break", "target_can_break", "forced_duration",
            "daily_effect", "weekly_effect", "subject_relation",
            "annex_on_country_formation", "auto_support_type",
            "military_access", "actor_requires_approval_to_break",
            "target_requires_approval_to_break", "is_breaking_hostile",
            "is_target_breaking_hostile", "propose_string", "break_string",
            "ask_to_end_string", "counts_for_tech_spread",
            "max_target_involvement", "target_involvement_applies_to",
            "income_transfer", "exempt_from_service",
            "will_propose_even_if_not_accepted", "accept_break_score",
            "propose_break_score", "use_favor_chance", "owe_favor_chance",
            "evaluation_chance",
        }),
        skip_blocks=_STATIC_MODIFIER_BLOCKS,
    ),
    ScanRoot(
        os.path.join("common", "decisions"),
        extra_valid=_ENTITY_GATES | frozenset({"when_taken"}),
    ),
    ScanRoot(
        os.path.join("common", "character_interactions"),
        extra_valid=_ENTITY_GATES | frozenset({"show_confirmation_box"}),
    ),
    ScanRoot(
        os.path.join("common", "scripted_progress_bars"),
        extra_valid=_ENTITY_GATES | frozenset({
            "start_value", "min_value", "max_value", "monthly_progress",
            "default_green", "default_bad", "double_sided_gold",
        }),
    ),
    ScanRoot(
        os.path.join("common", "treaty_articles"),
        extra_valid=_ENTITY_GATES | frozenset({
            "kind", "cost", "usage_limit", "maintenance_paid_by", "flags",
            "relations_progress_per_day", "relations_improvement_max",
            "relations_improvement_min", "execution_priority", "contestion_type",
            "consequences", "conditions", "article_ai_usage", "can_ratify",
            "inherent_accept_score", "treaty_categories", "mutual_exclusions",
            "unlocked_by_technologies", "required_inputs", "input_company",
            "input_state", "company_valid_trigger", "state_valid_trigger",
            "quantity_input_value", "quantity_min_value", "quantity_max_value",
            "requirement_to_maintain", "non_fulfillment", "infamy", "maneuvers",
            "wargoal", "monthly", "weekly",
            "on_break", "on_entry_into_force", "on_withdrawal",
        }),
        skip_blocks=_STATIC_MODIFIER_BLOCKS,
    ),
    ScanRoot(
        os.path.join("common", "political_movements"),
        extra_valid=_ENTITY_GATES | frozenset({
            "creation_trigger", "creation_weight", "disband_trigger",
            "on_disbanded", "character_ideologies", "character_support_trigger",
            "character_support_weight", "pop_support_factors",
            "pop_support_weight", "additional_radicalism_factors",
            "state_weight", "revolution", "secession",
        }),
        skip_blocks=_STATIC_MODIFIER_BLOCKS,
    ),
    ScanRoot(
        os.path.join("common", "diplomatic_plays"),
        extra_valid=_ENTITY_GATES | frozenset({
            "war_goal", "mirror_war_goal", "requires_interest_marker",
            "blocked_by_diplomatic_status", "selectable_in_lens",
            "add_infamy_for_starting_initiator_wargoals",
            "on_weekly_pulse", "on_war_begins",
        }),
        skip_blocks=_STATIC_MODIFIER_BLOCKS,
    ),
    ScanRoot(
        os.path.join("common", "power_bloc_principles"),
        extra_valid=_ENTITY_GATES | frozenset({
            "background", "allows_foreign_investment_in_lower_rank",
        }),
        skip_blocks=_STATIC_MODIFIER_BLOCKS,
    ),
    ScanRoot(
        os.path.join("common", "laws"),
        extra_valid=_ENTITY_GATES | frozenset({
            "group", "can_enact", "can_impose", "ai_impose_chance",
            "ai_enact_weight_modifier", "unlocking_laws", "disallowing_laws",
            "unlocking_technologies", "on_activate", "on_deactivate", "on_enact",
        }),
        skip_blocks=_STATIC_MODIFIER_BLOCKS,
    ),
    ScanRoot(os.path.join("common", "script_values")),
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
# A call to a scripted effect / trigger takes one of two forms: `name = yes|no`
# or `name = {` (parameterised). An unknown LHS in one of those forms is almost
# always a *dangling helper call* — the helper was renamed or deleted and the
# engine now silently ignores the line (#288). Reported as its own flag kind so
# it reads apart from a misspelled engine effect (`add_authority = -200`).
_CALL_FORM_RE = re.compile(r"^[ \t]*=[ \t]*(?:yes|no)\b|^[ \t]*=[ \t]*\{")
# Valid engine keys the vanilla corpus under SCAN_ROOTS happens not to use as an
# LHS (so they're absent from the bootstrapped catalog), confirmed valid by
# inspection. Unlike ScanRoot.extra_valid these are valid in *every* root.
# Strict-then-permissive: extend deliberately, with a reason per entry.
_CURATED_VALID: frozenset[str] = frozenset({
    "texture",  # event_image = { texture = ... } — vanilla always uses `video`
    "levels",   # add_ownership = { ... levels = N }
    "hue",      # colour field
    "ceiling",  # script-value rounding (ceiling = yes)
    "side",     # join_war = { side = scope:X } (vanilla uses it, just not in scope dirs)
    "parent",   # create_container = { parent = ... } / container iterator filter (1.13.10+; unused by vanilla script)
    "tags",     # create_container = { tags = { ... } } / container iterator filter (1.13.10+; unused by vanilla script)
    "add_ownership",  # building effect: add_ownership = { country = { ... levels = N } }
    "color",    # create_dynamic_country / flag colour block: color = { R G B }
    "law_type", # law-scope trigger: any_active_law = { law_type = law_type:law_x }
    "trade_center",  # market -> trade-center-state scope change
    "modulo",   # script-value math operator (modulo = N)
    "round_to", # script-value math operator (round_to = N)
})
# Mod dirs whose top-level names are *callable* anywhere: scripted effects and
# triggers are invoked as `name = yes` / `name = { ARG = v }`, on-actions are
# referenced by name, and script values are compared by name as triggers. Names
# defined in any other scanned root are valid only as that root's own top-level
# definitions (see `_scan_lines`' depth-0 rule) — that asymmetry is what makes a
# call to a deleted helper from `common/scripted_buttons/` flag (#288).
_HELPER_NAME_DIRS = (
    os.path.join("common", "scripted_effects"),
    os.path.join("common", "scripted_triggers"),
    os.path.join("common", "on_actions"),
    os.path.join("common", "script_values"),
)
_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)
# Top-level entity definition: `name = {` (optionally merge-prefixed).
_TOP_DEF_RE = re.compile(
    r"^[ \t]*(?:REPLACE:|INJECT:|REPLACE_OR_CREATE:)?([a-z_][a-z0-9_]*)[ \t]*=[ \t]*\{"
)


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


# One scanned line: its number, the raw text, the comment-and-quote-stripped
# code, the trailing comment, and the brace depth *before* this line's own
# braces apply (so a top-level entity definition sits at depth 0).
@dataclass
class ScanLine:
    lineno: int
    raw: str
    code: str
    comment: str
    depth: int


def _scan_lines(lines, skip_blocks: frozenset = frozenset()):
    """Yield a `ScanLine` per line, tracking brace depth and omitting the body of
    any block opened by a name in `skip_blocks`.

    Depth matters because an LHS at depth 0 is an *entity definition*, not a
    call: `je_space_race = {` in a journal entry, `te_helper = {` in a scripted
    effect. Callers skip the first key on a depth-0 line for that reason, which
    is what lets a root's own names stay valid without whitelisting them
    globally (and so a call to a deleted helper still flags — #288)."""
    depth = 0
    skip_depth: int | None = None
    for lineno, raw in enumerate(lines, 1):
        code, comment = _strip_comment(raw)
        code = _strip_quotes(code)
        opens = code.count("{")
        closes = code.count("}")

        if skip_depth is not None:
            depth = max(0, depth + opens - closes)
            if depth <= skip_depth:
                skip_depth = None
            continue

        if opens and skip_blocks:
            m = _TOP_DEF_RE.match(code)
            if m and m.group(1) in skip_blocks:
                if opens > closes:      # multi-line block: skip until it closes
                    skip_depth = depth
                depth = max(0, depth + opens - closes)
                continue

        yield ScanLine(lineno, raw, code, comment, depth)
        depth = max(0, depth + opens - closes)


def extract_lhs_keys(text: str, skip_blocks: frozenset = frozenset()) -> set[str]:
    """Every lowercase LHS keyword in `text` (comments stripped), excluding
    depth-0 definition names and the bodies of `skip_blocks`. Used to bootstrap
    the catalog from vanilla, so it must mirror what `audit()` checks."""
    keys: set[str] = set()
    for sl in _scan_lines(text.splitlines(), skip_blocks):
        for i, m in enumerate(_LHS_RE.finditer(sl.code)):
            if sl.depth == 0 and i == 0:
                continue        # the entity being defined, not a keyword
            keys.add(m.group(1))
    return keys


def _top_level_names(root: str) -> set[str]:
    """Names defined at brace depth 0 under `root` — both `name = { ... }`
    entities and bare `name = <value>` script values. Restricted to depth 0 so a
    nested `limit = {` / `possible = {` inside a helper body is not mistaken for
    a definition (which used to make every nested block name globally valid)."""
    names: set[str] = set()
    if not os.path.isdir(root):
        return names
    for path in _iter_txt(root):
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        for sl in _scan_lines(lines):
            if sl.depth != 0:
                continue
            m = _TOP_DEF_RE.match(sl.code)
            if m:
                names.add(m.group(1))
                continue
            m = _LHS_RE.search(sl.code)
            if m:
                names.add(m.group(1))
    return names


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
    # Harvested from the same roots the audit scans, with the same depth-0 and
    # skip_blocks rules — so every entity-schema field vanilla actually uses in
    # e.g. `common/journal_entries/` lands in the catalog (and each root's
    # `extra_valid` shrinks), while modifier names inside `modifier = { ... }`
    # blocks stay out of it.
    for root in SCAN_ROOTS:
        base = os.path.join(game, root.rel)
        if not os.path.isdir(base):
            continue
        for path in _iter_txt(base):
            try:
                with open(path, encoding="utf-8-sig", errors="replace") as fh:
                    keys |= extract_lhs_keys(fh.read(), root.skip_blocks)
            except OSError:
                continue

    out_path = os.path.join(mod_path, _CATALOG_REL)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(
            "# AUTO-GENERATED valid effect/trigger/scope/control-flow keyword "
            "catalog.\n# Union of effects_summary.txt + triggers_summary.txt "
            "names and every LHS keyword\n# vanilla uses in the audit's "
            "SCAN_ROOTS (events/ + the script-bearing common/ dirs),\n"
            "# excluding depth-0 entity names and static-modifier block bodies."
            "\n# Regenerate on a vanilla bump: "
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
    # The mod's own *callable* names — scripted effects/triggers (invoked as
    # `name = yes` / `name = { ARG = v }`), on-actions, and script values (which
    # can be compared by name in a trigger). Valid in every root. Names defined
    # in any other root are handled by the depth-0 rule in `_scan_lines`, so a
    # journal entry id never becomes a globally-valid keyword.
    mod_names: set[str] = set()
    for rel in _HELPER_NAME_DIRS:
        mod_names |= _top_level_names(os.path.join(mod_path, rel))
    base_allowed = valid_keys | mod_names | _CURATED_VALID

    flags: list[Flag] = []
    keys_checked = 0
    files_scanned = 0
    roots_scanned: list[str] = []
    for root in SCAN_ROOTS:
        base = os.path.join(mod_path, root.rel)
        if not os.path.isdir(base):
            continue
        roots_scanned.append(root.rel)
        allowed = base_allowed | root.extra_valid
        for path in _iter_txt(base):
            files_scanned += 1
            try:
                with open(path, encoding="utf-8-sig", errors="replace") as fh:
                    lines = fh.readlines()
            except OSError:
                continue
            for sl in _scan_lines(lines, root.skip_blocks):
                exemption = parse_reviewed_comment(sl.comment)
                for i, m in enumerate(_LHS_RE.finditer(sl.code)):
                    if sl.depth == 0 and i == 0:
                        continue    # the entity being defined
                    kw = m.group(1)
                    keys_checked += 1
                    if kw in allowed:
                        continue
                    kind = (
                        "unresolved-helper-call"
                        if _CALL_FORM_RE.match(sl.code[m.end(1):])
                        else "unknown-name"
                    )
                    flags.append(
                        Flag(path, sl.lineno, kw, kind, sl.raw.strip(), exemption)
                    )
                for m in _CALL_RE.finditer(sl.code):
                    flags.append(
                        Flag(
                            path, sl.lineno, m.group(1) + "(...)", "call-syntax",
                            sl.raw.strip(), exemption,
                        )
                    )

    flags.sort(key=lambda f: (f.kind, f.keyword, f.file, f.line))
    return AuditResult(
        flags=flags,
        coverage={
            "files_scanned": files_scanned,
            "roots_scanned": len(roots_scanned),
            "keys_checked": keys_checked,
            "catalog_size": len(valid_keys),
            "mod_defined_names": len(mod_names),
            "flags": len(flags),
        },
    )


def unresolved_helper_calls(mod_path: str, result: AuditResult | None = None) -> list[dict]:
    """The dangling scripted-helper call sites (#288): every `name = yes` /
    `name = { ... }` whose callee is defined neither by vanilla nor by the mod.
    The inverse of the server's callers index — call sites with a missing
    callee. Returns the shape served by `GET /scripted-helpers/unresolved`."""
    if result is None:
        result = audit(mod_path)
    return [
        {
            "name": f.keyword,
            "file": os.path.relpath(f.file, mod_path) if mod_path else f.file,
            "line": f.line,
            "kind": "effect_call",
            "snippet": f.snippet,
            "reviewed": f.exemption,
        }
        for f in result.flags
        if f.kind == "unresolved-helper-call"
    ]


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
        "Lowercase LHS keywords in every script-bearing mod directory "
        "(`events/` plus the `common/` entity dirs listed in the audit's "
        "`SCAN_ROOTS`) that are neither a known engine "
        "effect/trigger/scope/control-flow keyword (per the frozen vanilla "
        "catalog) nor a mod-defined name — plus `funcname(...)` call-syntax, "
        "which Paradox script never uses. The engine silently ignores these "
        "until a runtime game-load `Unknown effect/trigger` error."
    )
    out.append("")
    out.append(
        "Flag kinds: **unresolved-helper-call** is an unknown name in call form "
        "(`x = yes` / `x = { ... }`) — typically a scripted effect/trigger that "
        "was renamed or deleted while a call site survived (#288). "
        "**unknown-name** is any other unknown LHS keyword (#295). "
        "**call-syntax** is unquoted `f(...)`. Static-modifier block bodies "
        "(`modifier = { ... }`, `member_modifier`, …) are skipped here — their "
        "names are validated by `modifier_visibility_audit`."
    )
    out.append("")
    out.append(
        f"- Roots scanned: **{cov.get('roots_scanned', 0)}**, files scanned: "
        f"**{cov.get('files_scanned', 0)}**, keys checked: "
        f"**{cov.get('keys_checked', 0)}**"
    )
    out.append(
        f"- Catalog size: **{cov.get('catalog_size', 0)}** + mod-defined names: "
        f"**{cov.get('mod_defined_names', 0)}**"
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
        "unresolved_helper_calls": sum(
            1 for f in result.flags
            if f.kind == "unresolved-helper-call" and not f.exemption
        ),
        "roots_scanned": result.coverage.get("roots_scanned", 0),
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
