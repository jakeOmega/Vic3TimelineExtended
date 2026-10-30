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
  `script_values`, and since #305 `scripted_guis` and
  `customizable_localization`) — and flags any lowercase LHS keyword not in the catalog and
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
- Context (#1142): a known name can still be in the wrong *kind* of block. The
  engine reads a scripted trigger's body, a `limit`, `trigger`, `potential`,
  `possible`, `is_shown`, `visible`, `can_*`, `*_trigger`, `any_*` … block as
  triggers, and an `immediate`, `option`, `effect`, `after`, `on_*`, `*_effect`
  block or a scripted effect's body as effects; an effect in the first logs
  `Unknown trigger type: <name>` at load and the line is dropped
  (`save_scope_as` opened `decol_fighting_colonial_war`, so every later
  `scope:decol_cw_metropole` read failed — in a trigger the scope is saved
  with `save_temporary_scope_as`). `_scan_lines` keeps a block stack whose
  entries carry that context (`_child_context`; AI weights and script-value
  math are neutral), and a second frozen catalog,
  `docs/engine/effect_trigger_context_keys.txt` (`bootstrap_context_catalog`),
  lists the effect-only and trigger-only names: in `effects.log` and not
  `triggers.log` (or the reverse), never used in the other context anywhere in
  vanilla's `common/` + `events/`. The mod's own scripted effects and triggers
  are added at audit time. An effect-only name in trigger context flags as
  `effect-in-trigger`; a trigger-only name in effect context as
  `trigger-in-effect`.
- A quoted string may run on to the next line (vanilla does it twice), so the
  scanner carries an open string across lines. A stray `"` would then hide the
  rest of its file from every check, so a string the file ends inside, or one
  over `_MAX_STRING_LINES`, flags as `unterminated-string`.

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
    # The context of a top-level entity's body (#1142): a scripted trigger is
    # read as triggers, a scripted effect as effects. Everywhere else the
    # entity body is neutral and a named block (`limit`, `immediate`, …) sets
    # the context; see `_child_context`.
    body_context: str | None = None
    # Schema blocks of this root only that hold triggers (a journal entry's
    # `complete`, a treaty article's `conditions`), on top of the global names
    # and patterns in `_child_context`.
    trigger_blocks: frozenset[str] = frozenset()


# Script contexts (#1142): the engine reads a block's keys either as triggers or
# as effects, and an effect name in trigger context (or the reverse) is logged
# at load (`Unknown trigger type: save_scope_as`) and dropped. `None` is neutral:
# an entity's schema fields, a script value's math, an AI weight.
CTX_TRIGGER = "trigger"
CTX_EFFECT = "effect"

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
    ScanRoot(os.path.join("common", "scripted_effects"), body_context=CTX_EFFECT),
    ScanRoot(os.path.join("common", "scripted_triggers"), body_context=CTX_TRIGGER),
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
        trigger_blocks=frozenset({"complete", "fail", "invalid", "is_progressing"}),
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
            # Vanilla 03_violate_sovereignty.txt / 28_invite_to_power_bloc.txt (#305).
            "can_use_obligations", "decline_effect",
        }),
        skip_blocks=_STATIC_MODIFIER_BLOCKS,
        trigger_blocks=frozenset({
            "will_propose", "will_break", "will_propose_with_states",
            "will_select_as_first_state", "will_select_as_second_state",
            "will_propose_even_if_not_accepted",
        }),
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
            "second_desc",  # vanilla 00_great_game_progress_bars.txt
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
        # non_fulfillment = { conditions = { weekly = { <triggers> } } }
        trigger_blocks=frozenset({"conditions"}),
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
            "ai_acceptance_max",  # vanilla 00_diplomatic_plays.txt (#305)
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
    # --- #305: scripted GUIs and custom loc carry effects and triggers too ---
    # Scripted-GUI schema: vanilla game/common/scripted_guis/scripted_guis.md.
    # No _ENTITY_GATES: an SGUI reads is_shown / is_valid, and a `possible` or
    # `visible` there would be ignored by the engine, so it should flag.
    ScanRoot(
        os.path.join("common", "scripted_guis"),
        extra_valid=frozenset({
            "scope", "saved_scopes", "is_shown", "is_valid", "ai_is_valid",
            "ai_chance", "ai_frequency", "effect", "notification_key",
            "confirm_title", "confirm_text",
        }),
    ),
    # Custom-loc schema, as vanilla game/common/customizable_localization/ uses
    # it (no .md ships for it): `text = { trigger = { … } localization_key = k
    # fallback = yes }` entries, and `parent` + `suffix` for a template child.
    ScanRoot(
        os.path.join("common", "customizable_localization"),
        extra_valid=frozenset({
            "type", "text", "trigger", "localization_key", "random_valid",
            "log_loc_errors", "parent", "suffix", "fallback",
        }),
    ),
)

_ALL_ROOT_TRIGGER_BLOCKS: frozenset[str] = frozenset().union(
    *(root.trigger_blocks for root in SCAN_ROOTS)
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
    "controller",  # province/state -> country scope link (event_targets.log); vanilla script never uses it (trophies' occupation read)
    "member",   # create_power_bloc = { member = scope:x } (effects.log 1.14.5); vanilla passes it only in common/history/, outside SCAN_ROOTS
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
    # "unknown-name" | "unresolved-helper-call" | "call-syntax" |
    # "effect-in-trigger" | "trigger-in-effect" | "unterminated-string"
    kind: str
    snippet: str
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)


def _split_code(line: str, in_quote: bool = False) -> tuple[str, str, bool]:
    """Return (code, comment, in_quote) for one line.

    `code` keeps every offset of the line up to the comment but blanks quoted
    text, quotes included: LHS keys are never quoted, and the legit Vic3
    scripted-value-call form (`"funcname(ARG)" < N`) lives inside quotes. A `#`
    starts the comment only outside a string (`text = "#b Warning#!"` is no
    comment), and a string still open at the end of the line runs on into the
    next, which `in_quote` carries (vanilla's two-line `CRITERIA = "NOT = { … }`
    in neighbor_events.txt)."""
    if not in_quote and '"' not in line:    # the common case
        idx = line.find("#")
        if idx == -1:
            return line, "", False
        return line[:idx], line[idx:], False
    out: list[str] = []
    for i, ch in enumerate(line):
        if ch == '"':
            in_quote = not in_quote
            out.append(" ")
        elif in_quote:
            out.append(" ")
        elif ch == "#":
            return "".join(out), line[i:], False
        else:
            out.append(ch)
    return "".join(out), "", in_quote


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
# braces apply (so a top-level entity definition sits at depth 0). `contexts`
# holds the script context (#1142) as `(offset, context)` pairs: from each
# offset of `code` on, until the next pair, keys are read in that context. It
# changes only at a brace, so `x = { y = 1 }` on one line gets two entries.
@dataclass
class ScanLine:
    lineno: int
    raw: str
    code: str
    comment: str
    depth: int
    contexts: tuple = ((0, None),)

    def context_at(self, pos: int) -> str | None:
        """The context a key starting at `pos` of `code` is read in."""
        ctx = self.contexts[0][1]
        for start, c in self.contexts:
            if start > pos:
                break
            ctx = c
        return ctx


# Blocks whose keys are triggers wherever they appear (#1142). Plus the
# patterns in `_child_context`: `can_*`, `is_shown*`, `should_*`, `*_trigger`,
# and the body of an `any_*` iterator (a misplaced one flags once, not once per
# line of its body).
_TRIGGER_BLOCKS: frozenset[str] = frozenset({
    "limit", "trigger", "potential", "possible", "is_shown", "is_valid",
    "ai_is_valid", "visible", "is_visible", "filter", "selectable",
    "alternative_limit", "show_as_unavailable", "would_sponsor",
    # Bare triggers in vanilla's laws, character interactions, buildings and
    # companies (`ai_will_do = { exists = ruler }`), not a weight.
    "ai_will_do",
})
_TRIGGER_PREFIXES = ("can_", "is_shown", "should_", "any_")
# Blocks whose keys are effects wherever they appear. Plus `on_*` and `*_effect`
# (`on_complete`, `accept_effect`, `hidden_effect`).
_EFFECT_BLOCKS: frozenset[str] = frozenset({
    "immediate", "option", "after", "effect", "when_taken",
})
# Blocks whose keys are neither: AI weights (`ai_chance = { base = 5
# modifier = { trigger = { … } add = 2 } }`) and script-value math
# (`multiplier = { value = x if = { limit = { … } add = 1 } }`). A `limit` or
# `trigger` inside one sets trigger context again. Plus `*_weight`, `*_score`,
# `*_chance`.
_NEUTRAL_BLOCKS: frozenset[str] = frozenset({
    "modifier", "ai", "ai_chance", "weight", "value",
    "multiplier", "add", "subtract", "multiply", "divide", "min", "max",
    "modulo", "round_to", "factor", "base", "days", "weeks", "months", "years",
    "delay", "cooldown", "random_range", "fixed_range", "integer_range",
    "current_value", "goal_add_value", "start_value", "min_value", "max_value",
    "monthly_progress",
})
_NEUTRAL_SUFFIXES = ("_weight", "_score", "_chance")

_BRACE_RE = re.compile(r"[{}]")
_OPERATORS = frozenset({"=", "?=", "==", "!=", "<=", ">=", "<", ">"})
_OP_CHARS = "=<>!?"
_KEY_STOP = " \t\r\n{}" + _OP_CHARS


def _opener_before(code: str, end: int) -> tuple[str, str] | None:
    """The key and operator that end `code[:end]`, or None: the `name = ` of
    `name = {`, `scope:x ?= {`, `gdp > {`. Scans backwards (a `$`-anchored regex
    search retries every start position and tripled the audit's run time)."""
    i = end
    while i > 0 and code[i - 1] in " \t\r\n":
        i -= 1
    j = i
    while j > 0 and code[j - 1] in _OP_CHARS:
        j -= 1
    op = code[j:i]
    if op not in _OPERATORS:
        return None
    k = j
    while k > 0 and code[k - 1] in " \t":
        k -= 1
    m = k
    while m > 0 and code[m - 1] not in _KEY_STOP:
        m -= 1
    if m == k:
        return None
    return code[m:k], op


def _child_context(
    name: str | None, op: str, parent: str | None, depth: int,
    root: ScanRoot | None,
) -> str | None:
    """The context of the block `name <op> {` opened at `depth` inside a block
    of context `parent`. Unnamed blocks, scope changes (`owner`, `scope:x`),
    iterators and `AND`/`OR`/`NOT` inherit their parent's."""
    if depth == 0:
        return root.body_context if root is not None else None
    if op not in ("=", "?="):
        return None     # `x > { … }`: a script value compared, not script
    if name is None:
        return parent
    if name in _NEUTRAL_BLOCKS or name.endswith(_NEUTRAL_SUFFIXES):
        return None
    if (
        name in _TRIGGER_BLOCKS
        or name.startswith(_TRIGGER_PREFIXES)
        or name.endswith("_trigger")
        or (root is not None and name in root.trigger_blocks)
    ):
        return CTX_TRIGGER
    if name in _EFFECT_BLOCKS or name.startswith("on_") or name.endswith("_effect"):
        return CTX_EFFECT
    return parent


def _push_pop_neutral(stack: list, code: str) -> None:
    """Apply a skipped line's braces to the context stack."""
    for bm in _BRACE_RE.finditer(code):
        if bm.group() == "{":
            stack.append(None)
        elif stack:
            stack.pop()


def _scan_lines(
    lines, skip_blocks: frozenset = frozenset(), root: ScanRoot | None = None,
    run_on: list | None = None,
):
    """Yield a `ScanLine` per line, tracking brace depth and script context and
    omitting the body of any block opened by a name in `skip_blocks`.

    Depth matters because an LHS at depth 0 is an *entity definition*, not a
    call: `je_space_race = {` in a journal entry, `te_helper = {` in a scripted
    effect. Callers skip the first key on a depth-0 line for that reason, which
    is what lets a root's own names stay valid without whitelisting them
    globally (and so a call to a deleted helper still flags — #288).

    The context comes from a stack with one entry per open block, set by
    `_child_context` from the block's name; `root` supplies the body context
    of its top-level entities and its own trigger schema blocks.

    If `run_on` is a list, each quoted string that runs past its line is
    appended to it as `(opening line, closing line)`, the closing line None
    when the file ends inside it. Skipped lines count too, which is why the
    generator records them rather than its callers."""
    stack: list[str | None] = []
    skip_depth: int | None = None
    # `name =` ending a line whose `{` opens the next one.
    carry: tuple[str, str] | None = None
    # Inside a quoted string that runs on from an earlier line, and where
    # that string opened.
    in_quote = False
    string_from: int | None = None
    for lineno, raw in enumerate(lines, 1):
        was_in = in_quote
        code, comment, in_quote = _split_code(raw, in_quote)
        if run_on is not None and (was_in or in_quote):
            quotes = raw.count('"', 0, len(code))
            if was_in and quotes:       # the run-on string closes here
                run_on.append((string_from, lineno))
            if in_quote and (quotes > was_in):  # a string opens and runs on
                string_from = lineno
        depth = len(stack)

        if skip_depth is not None:
            _push_pop_neutral(stack, code)
            if len(stack) <= skip_depth:
                skip_depth = None
            carry = None
            continue

        if skip_blocks and "{" in code:
            m = _TOP_DEF_RE.match(code)
            if m and m.group(1) in skip_blocks:
                _push_pop_neutral(stack, code)
                if len(stack) > depth:  # multi-line block: skip until it closes
                    skip_depth = depth
                carry = None
                continue

        contexts = [(0, stack[-1] if stack else None)]
        for bm in _BRACE_RE.finditer(code):
            if bm.group() == "{":
                opener = _opener_before(code, bm.start())
                if opener:
                    name, op = opener
                elif carry and not code[:bm.start()].strip():
                    name, op = carry
                else:
                    name, op = None, "="
                stack.append(_child_context(
                    name, op, stack[-1] if stack else None, len(stack), root,
                ))
            elif stack:
                stack.pop()
            contexts.append((bm.end(), stack[-1] if stack else None))
        carry = _opener_before(code, len(code))

        yield ScanLine(lineno, raw, code, comment, depth, tuple(contexts))

    if run_on is not None and in_quote:
        run_on.append((string_from, None))


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


def _vanilla_install_missing(base_game_path: str) -> str | None:
    """Why the bootstraps can't read vanilla under `base_game_path`, or None.
    Both harvest vanilla's script from game/common and game/events. Without
    it the valid-key catalog shrinks to the engine-doc names, and the context
    catalog loses vanilla's scripted effects and triggers and keeps names
    vanilla uses in both contexts."""
    for rel in ("common", "events"):
        path = os.path.join(base_game_path, "game", rel)
        if not os.path.isdir(path):
            return f"no vanilla {path}"
    return None


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

    # Vanilla's own callable helpers. The depth-0 rule above drops their names,
    # and a mod call to one that vanilla never uses at depth > 0 (1.14.5's
    # `has_treaty_alliance_with`) would flag as an unresolved helper. The audit
    # already allows the mod's own helper names the same way (see `audit`).
    for rel in _HELPER_NAME_DIRS:
        keys |= _top_level_names(os.path.join(game, rel))

    out_path = os.path.join(mod_path, _CATALOG_REL)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(
            "# AUTO-GENERATED valid effect/trigger/scope/control-flow keyword "
            "catalog.\n# Union of effects_summary.txt + triggers_summary.txt "
            "names, every LHS keyword\n# vanilla uses in the audit's "
            "SCAN_ROOTS (events/ + the script-bearing common/ dirs),\n"
            "# excluding depth-0 entity names and static-modifier block "
            "bodies, and the top-level\n# names vanilla defines under "
            "scripted_effects/scripted_triggers/on_actions/script_values."
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
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                keys.add(line)
    return keys


# --- context catalog (#1142) -------------------------------------------------

_CONTEXT_CATALOG_REL = os.path.join(
    "docs", "engine", "effect_trigger_context_keys.txt"
)
_EFFECT_ONLY = "effect_only"
_TRIGGER_ONLY = "trigger_only"
_SECTION_RE = re.compile(r"^\[(\w+)\]$")
_DOC_HEADER_RE = re.compile(r"^## ([A-Za-z_][\w:]*)\s*$")


def _engine_doc_names(path: str) -> set[str]:
    """The `## name` entries of an engine docs dump (`effects.log`,
    `triggers.log`). Same names as `docs/engine/*_summary.txt`, which the
    reload renders from these files."""
    names: set[str] = set()
    if not os.path.isfile(path):
        return names
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = _DOC_HEADER_RE.match(line)
            if m:
                names.add(m.group(1))
    return names


def _root_for(rel_path: str) -> ScanRoot:
    """The `SCAN_ROOTS` entry a file (relative to a mod or `game/` root) falls
    under, or a neutral root for its directory: the bootstrap reads all of
    vanilla's `common/` and `events/`, not only the directories the audit
    checks."""
    rel_path = rel_path.replace("\\", "/")
    for root in SCAN_ROOTS:
        prefix = root.rel.replace("\\", "/") + "/"
        if rel_path.startswith(prefix):
            return root
    # The per-root trigger blocks too, for a directory that shares a schema
    # (an objective's `complete`); on 1.14.5 they add three names to the
    # trigger-context harvest and change neither catalog section.
    return ScanRoot(
        os.path.dirname(rel_path), skip_blocks=_STATIC_MODIFIER_BLOCKS,
        trigger_blocks=_ALL_ROOT_TRIGGER_BLOCKS,
    )


def context_key_uses(lines, root: ScanRoot):
    """Yield `(context, key, lineno, scan_line)` for every LHS keyword read in
    trigger or effect context (neutral keys and depth-0 definitions left out)."""
    for sl in _scan_lines(lines, root.skip_blocks, root):
        for i, m in enumerate(_LHS_RE.finditer(sl.code)):
            if sl.depth == 0 and i == 0:
                continue
            ctx = sl.context_at(m.start())
            if ctx is not None:
                yield ctx, m.group(1), sl.lineno, sl


def harvest_context_keys(game_dir: str) -> dict[str, set[str]]:
    """Every LHS keyword vanilla reads in trigger context and in effect context,
    over all of `game/common/` and `game/events/`."""
    used: dict[str, set[str]] = {CTX_TRIGGER: set(), CTX_EFFECT: set()}
    for top in ("common", "events"):
        base = os.path.join(game_dir, top)
        if not os.path.isdir(base):
            continue
        for path in _iter_txt(base):
            root = _root_for(os.path.relpath(path, game_dir))
            try:
                with open(path, encoding="utf-8-sig", errors="replace") as fh:
                    lines = fh.readlines()
            except OSError:
                continue
            for ctx, key, _lineno, _sl in context_key_uses(lines, root):
                used[ctx].add(key)
    return used


def bootstrap_context_catalog(
    base_game_path: str, mod_path: str, engine_docs_path: str,
) -> dict:
    """Write `docs/engine/effect_trigger_context_keys.txt`: the effect names the
    engine rejects in trigger context and the trigger names it rejects in
    effect context. Re-run on a vanilla bump, like `bootstrap_catalog`.

    effect_only = names in `effects.log`, not in `triggers.log`, and never an
    LHS in trigger context anywhere in vanilla's `common/` or `events/`, plus
    vanilla's scripted effects that are not also scripted triggers, script
    values or engine triggers (on the same terms). trigger_only is the mirror
    image. The vanilla-usage subtraction keeps a name both readers accept
    (vanilla uses it in both) out of the check even where the docs list it on
    one side only."""
    game = os.path.join(base_game_path, "game")
    effects = _engine_doc_names(os.path.join(engine_docs_path, "effects.log"))
    triggers = _engine_doc_names(os.path.join(engine_docs_path, "triggers.log"))
    if not effects or not triggers:
        raise FileNotFoundError(
            f"effects.log / triggers.log not found under {engine_docs_path}"
        )
    used = harvest_context_keys(game)
    sc_effects = _top_level_names(os.path.join(game, "common", "scripted_effects"))
    sc_triggers = _top_level_names(os.path.join(game, "common", "scripted_triggers"))
    svalues = _top_level_names(os.path.join(game, "common", "script_values"))

    effect_side = effects | (sc_effects - sc_triggers - svalues)
    trigger_side = triggers | sc_triggers | svalues
    sections = {
        _EFFECT_ONLY: effect_side - trigger_side - used[CTX_TRIGGER],
        _TRIGGER_ONLY: (triggers | (sc_triggers - sc_effects))
        - effects - sc_effects - used[CTX_EFFECT],
    }
    dropped = {
        _EFFECT_ONLY: sorted((effect_side - trigger_side) & used[CTX_TRIGGER]),
        _TRIGGER_ONLY: sorted(
            ((triggers | sc_triggers) - effects - sc_effects) & used[CTX_EFFECT]
        ),
    }

    out_path = os.path.join(mod_path, _CONTEXT_CATALOG_REL)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(
            "# AUTO-GENERATED effect/trigger context catalog (#1142).\n"
            "# [effect_only]: names the engine reads only as effects, so a "
            "trigger block rejects them\n# (`Unknown trigger type`). Names in "
            "effects.log and not in triggers.log, plus\n# vanilla's scripted "
            "effects that are not also scripted triggers or script values,\n"
            "# less every LHS keyword vanilla's common/ and events/ use in "
            "trigger context.\n# [trigger_only]: the mirror image, for effect "
            "context.\n# Regenerate on a vanilla bump: python3 "
            "effect_trigger_validity_audit.py bootstrap-context\n"
            f"# Sizes: {len(sections[_EFFECT_ONLY])} effect-only, "
            f"{len(sections[_TRIGGER_ONLY])} trigger-only.\n"
        )
        for section in (_EFFECT_ONLY, _TRIGGER_ONLY):
            # Names the docs put on one side that vanilla also writes on the
            # other (effect arguments named like triggers: create_character's
            # `age`, add_loyalists' `strata`), so they are never checked.
            f.write(
                f"# Left out of [{section}], used by vanilla in the other "
                f"context: {', '.join(dropped[section]) or 'none'}\n"
            )
        for section in (_EFFECT_ONLY, _TRIGGER_ONLY):
            f.write(f"[{section}]\n")
            for k in sorted(sections[section]):
                f.write(k + "\n")
    return {
        "effect_only": len(sections[_EFFECT_ONLY]),
        "trigger_only": len(sections[_TRIGGER_ONLY]),
        "dropped_as_used_by_vanilla": dropped,
        "path": out_path,
    }


def load_context_catalog(mod_path: str) -> dict[str, set[str]]:
    """The two sections of the context catalog; empty sets if it is absent."""
    sections: dict[str, set[str]] = {_EFFECT_ONLY: set(), _TRIGGER_ONLY: set()}
    path = os.path.join(mod_path, _CONTEXT_CATALOG_REL)
    if not os.path.isfile(path):
        return sections
    current: set[str] | None = None
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = _SECTION_RE.match(line)
            if m:
                current = sections.setdefault(m.group(1), set())
            elif current is not None:
                current.add(line)
    return sections


# --- audit -----------------------------------------------------------------

# The most lines a quoted string may span before it reads as a stray quote.
# Vanilla's longest are two (the `CRITERIA = "…` strings in
# neighbor_events.txt) and the mod has none. A stray `"` turns the rest of its
# file inside out: every key up to the next quote is read as text, and each
# string after it as script, so the file's checks go blind (one stray quote in
# minor_events.txt took its checked keys from 707 to 22). Each "string" from
# there on runs from one quoted value to the next, mostly over several lines,
# so the first one past this limit sits at or just after the stray quote.
_MAX_STRING_LINES = 2


def _run_on_string_flags(path: str, lines: list[str], run_on: list) -> list[Flag]:
    """`unterminated-string` flags for a file's run-on strings: one that the
    file ends inside, or one longer than `_MAX_STRING_LINES`. Only the first
    unreviewed one is reported, since everything after it is misread. A long
    string that is meant can be reviewed on its closing line (after the
    closing quote); a string to the end of the file never can."""
    out: list[Flag] = []
    for start, end in run_on:
        if end is None:
            what, exemption = "string to end of file", None
        else:
            span = end - start + 1
            if span <= _MAX_STRING_LINES:
                continue
            what = f"string over {span} lines"
            exemption = parse_reviewed_comment(_split_code(lines[end - 1], True)[1])
        out.append(Flag(
            path, start, what, "unterminated-string",
            lines[start - 1].strip(), exemption,
        ))
        if exemption is None:
            break
    return out


def audit(
    mod_path: str,
    valid_keys: set[str] | None = None,
    context_keys: dict[str, set[str]] | None = None,
) -> AuditResult:
    if valid_keys is None:
        valid_keys = load_catalog(mod_path)
    if context_keys is None:
        context_keys = load_context_catalog(mod_path)
    # The mod's own *callable* names — scripted effects/triggers (invoked as
    # `name = yes` / `name = { ARG = v }`), on-actions, and script values (which
    # can be compared by name in a trigger). Valid in every root. Names defined
    # in any other root are handled by the depth-0 rule in `_scan_lines`, so a
    # journal entry id never becomes a globally-valid keyword.
    helper_names = {
        rel: _top_level_names(os.path.join(mod_path, rel))
        for rel in _HELPER_NAME_DIRS
    }
    mod_names: set[str] = set().union(*helper_names.values())
    base_allowed = valid_keys | mod_names | _CURATED_VALID

    # #1142: names one reader rejects. The catalog covers the engine's and
    # vanilla's; the mod's scripted effects are effect-only and its scripted
    # triggers trigger-only unless the other database (or a script value, or a
    # vanilla name the union catalog knows) has the same name.
    m_effects = helper_names[os.path.join("common", "scripted_effects")]
    m_triggers = helper_names[os.path.join("common", "scripted_triggers")]
    m_values = helper_names[os.path.join("common", "script_values")]
    # A catalog name the mod also defines on the other side (a scripted
    # trigger named like a vanilla scripted effect) is valid there too.
    effect_only = (context_keys.get(_EFFECT_ONLY, set()) - m_triggers - m_values) | (
        m_effects - m_triggers - m_values - valid_keys
    )
    trigger_only = (context_keys.get(_TRIGGER_ONLY, set()) - m_effects) | (
        m_triggers - m_effects - valid_keys
    )

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
            run_on: list = []
            for sl in _scan_lines(lines, root.skip_blocks, root, run_on):
                exemption = parse_reviewed_comment(sl.comment)
                for i, m in enumerate(_LHS_RE.finditer(sl.code)):
                    if sl.depth == 0 and i == 0:
                        continue    # the entity being defined
                    kw = m.group(1)
                    keys_checked += 1
                    if kw in allowed:
                        ctx = sl.context_at(m.start())
                        if ctx == CTX_TRIGGER and kw in effect_only:
                            kind = "effect-in-trigger"
                        elif ctx == CTX_EFFECT and kw in trigger_only:
                            kind = "trigger-in-effect"
                        else:
                            continue
                    elif _CALL_FORM_RE.match(sl.code[m.end(1):]):
                        kind = "unresolved-helper-call"
                    else:
                        kind = "unknown-name"
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
            flags.extend(_run_on_string_flags(path, lines, run_on))

    flags.sort(key=lambda f: (f.kind, f.keyword, f.file, f.line))
    return AuditResult(
        flags=flags,
        coverage={
            "files_scanned": files_scanned,
            "roots_scanned": len(roots_scanned),
            "keys_checked": keys_checked,
            "catalog_size": len(valid_keys),
            "effect_only_catalog_size": len(context_keys.get(_EFFECT_ONLY, ())),
            "trigger_only_catalog_size": len(context_keys.get(_TRIGGER_ONLY, ())),
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

    def _rel(f: Flag) -> str:
        return os.path.relpath(f.file, mod_path) if mod_path else f.file

    def _loc(f: Flag) -> str:
        return f"{_rel(f)}:{f.line}"

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
        "**effect-in-trigger** is a known effect where the engine reads "
        "triggers — a scripted trigger's body, a `limit`, `trigger`, "
        "`possible`, `is_shown`, `can_*` or other trigger block (#1142). The "
        "engine logs `Unknown trigger type` at load and drops the line; a scope "
        "saved there takes `save_temporary_scope_as`, not `save_scope_as`. "
        "**trigger-in-effect** is the mirror image: a trigger in an "
        "`immediate`, `option`, `effect`, `on_*` or scripted effect body. "
        "Both read the effect-only and trigger-only names in "
        "`docs/engine/effect_trigger_context_keys.txt` and the mod's own "
        "scripted effects and triggers."
    )
    out.append("")
    out.append(
        "**unterminated-string** is a quoted string the file ends inside, or "
        "one running over more lines than any vanilla string does: almost "
        "always a stray `\"` at or just above the line named, which turns the "
        "rest of the file into text the other checks can't read."
    )
    out.append("")
    # The frozen vanilla catalog changes only on an engine update; the root /
    # file / key / mod-name counts stay in `coverage` but move with unrelated
    # mod content.
    out.append(f"- Catalog size: **{cov.get('catalog_size', 0)}**")
    out.append(
        f"- Context catalog: **{cov.get('effect_only_catalog_size', 0)}** "
        f"effect-only, **{cov.get('trigger_only_catalog_size', 0)}** "
        "trigger-only names"
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
            "Fix the keyword (in trigger context, an effect such as "
            "`save_scope_as` has a trigger counterpart: "
            "`save_temporary_scope_as`), or add an inline "
            "`# REVIEWED YYYY-MM-DD: rationale` on the line if it is a false "
            "positive (e.g. a lowercase scripted-effect parameter)."
        )
        out.append("")
    else:
        out.append("No unreviewed effect/trigger name issues. ✅")
        out.append("")

    if exempted:
        out.append("## REVIEWED-suppressed")
        out.append("")
        # No line number on a reviewed entry: the keyword names it, and an
        # edit above it would otherwise churn the report.
        for f in exempted:
            ex = f.exemption or {}
            out.append(
                f"- `{f.keyword}` ({f.kind}) — {_rel(f)} "
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
        # Coverage, which the committed report no longer prints.
        **result.coverage,
        "path": out_path,
    }


def main(argv: list[str] | None = None, mod_path: str | None = None) -> int:
    """The CLI: `bootstrap`, `bootstrap-context`, or the audit, whose report
    goes to stdout. With `--strict` (CI) it returns 1 if any flag lacks a
    `# REVIEWED ...` exemption."""
    import sys

    argv = sys.argv[1:] if argv is None else argv
    if mod_path is None:
        from path_constants import mod_path
    if argv[:1] in (["bootstrap"], ["bootstrap-context"]):
        # Only the bootstrap subcommands read vanilla; keep the default audit
        # runnable on a machine with no Victoria 3 install.
        from path_constants import base_game_path

        missing = _vanilla_install_missing(base_game_path)
        if missing:
            print(
                f"{argv[0]}: {missing}, so nothing was written. Run it on the "
                "machine with the game (vanilla_patch_runbook.md § 4).",
                file=sys.stderr,
            )
            return 2
    if argv[:1] == ["bootstrap"]:
        print(bootstrap_catalog(base_game_path, mod_path))
        return 0
    if argv[:1] == ["bootstrap-context"]:
        # The effect-only / trigger-only catalog (#1142): engine docs from the
        # pinned snapshot, usage from the live install's game/common + events.
        from path_constants import vanilla_snapshot_docs_path

        print(bootstrap_context_catalog(
            base_game_path, mod_path, vanilla_snapshot_docs_path,
        ))
        return 0
    result = audit(mod_path)
    print(render_report(result, mod_path))
    if "--strict" in argv:
        return 1 if any(not f.exemption for f in result.flags) else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
