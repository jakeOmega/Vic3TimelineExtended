"""The one table of the mod's offline audits.

Every audit is a module `<name>.py` at the repo root. This registry says, for
each, what it catches, how CI runs it, whether a server reload runs it, and
where its suppression comment goes. Everything that used to restate the roster
by hand reads this table instead:

* `scripts/run_audits.py` runs the CI audits in parallel and, when one fails,
  prints the exact comment that suppresses an intended flag.
* `scripts/preflight.py` and `.github/workflows/ci.yml` call that runner.
* `docs/guides/audits.md` is generated from it (`python3 audit_registry.py
  --write`; `--check` fails when the committed file is stale).
* `docs/guides/python_tools.md` spells out figures taken from it ("the 49
  read-only audits", how many run in CI, how many are pure file scans), names
  the audits outside CI and has a row per CI command. `--check` holds each to
  this table (`PROSE_FIGURES`, `PROSE_NAMES`) and `--write` corrects the
  figures. Two PRs that each add an audit raise a figure to the same value,
  and git merges the identical edits without a conflict, one short (#1695).
* `test_audit_registry.py` holds it to `POST_LOAD_AUDITS` in
  `server/post_load.py` and to the `*_audit.py` files on disk.

Adding an audit: write the module (on `audit_common.py`) and its test, add it
to `POST_LOAD_AUDITS` if a reload should run it, add one `Audit(...)` here, and run
`python3 audit_registry.py --write`. Nothing else restates the roster.

Stdlib only, and it imports no audit: a reader needs neither numpy nor a game
install.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from typing import Callable

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DOC_PATH = os.path.join("docs", "guides", "audits.md")

STRICT = ("--strict",)


@dataclass(frozen=True)
class Audit:
    name: str
    """Module name, `<name>.py` at the repo root."""
    catches: str
    """What a flag means, in one sentence a script author can act on."""
    ci: tuple[str, ...] | None = STRICT
    """Arguments CI passes; `()` for an audit that fails natively; None when
    only a reload runs it."""
    post_load: bool = True
    """In `POST_LOAD_AUDITS`: runs on every `POST /reload`."""
    where: str | None = None
    """Where the `# REVIEWED` comment goes. None: the audit takes none."""
    tags: tuple[str, ...] = ()
    """Check tags. Empty: the plain `# REVIEWED YYYY-MM-DD: why` form."""
    report: str | None = ""
    """Report under docs/engine/. "" means `<stem>_report.md`; None, no report."""
    note: str = ""
    """Anything else a reader running it should know."""
    builds_mod_state: bool = False
    """Builds a `ModState` of its own when run from the command line, small or
    full. False: a pure file scan. `test_audit_registry.py` holds it to the
    module's source; `python_tools.md` counts the pure scans from it."""

    @property
    def report_path(self) -> str | None:
        if self.report is None:
            return None
        stem = self.name[: -len("_audit")] if self.name.endswith("_audit") else self.name
        return "docs/engine/" + (self.report or f"{stem}_report.md")

    @property
    def command(self) -> str | None:
        """The command CI runs, or None for a reload-only audit."""
        if self.ci is None:
            return None
        return " ".join(("python3", f"{self.name}.py") + tuple(self.ci))

    @property
    def comment_forms(self) -> tuple[str, ...]:
        """The suppression comment(s), ready to paste (date and reason to fill in).
        An empty tag is the plain, untagged form."""
        if self.where is None:
            return ()
        return tuple(
            f"# REVIEWED YYYY-MM-DD ({tag}): why" if tag else "# REVIEWED YYYY-MM-DD: why"
            for tag in (self.tags or ("",))
        )


VALUE_LINE = "trailing on the flagged line"

AUDITS: tuple[Audit, ...] = (
    # --- script: syntax the engine reads differently from how it looks -------
    Audit(
        "any_limit_audit",
        "An `any_*` trigger with a `limit = { }` child, an `always = no` child, or a `filter = { }` child "
        "with neither `percent` nor `count = all` beside it. `any_*` takes its conditions directly; the "
        "engine rejects a `limit`, matches nothing against `always = no`, and fails a `filter` with a plain "
        "count at load.",
        where="trailing on the `any_*` opener line, or on the `limit = {`, `always = no` or `filter = {` line",
    ),
    Audit(
        "iterator_limit_audit",
        "An iterator whose `limit = { }` is not its first child. The limit filters the whole iteration "
        "wherever it sits, so the lines written above it are gated by it too.",
        where="trailing on the `limit = {` line or the iterator's opener line",
    ),
    Audit(
        "delayed_event_trigger_audit",
        "An event queued with `days`, `months` or `years` whose top-level `trigger` may be false on the "
        "day it is queued, which seems to drop it for good (#1596). One that waits for something to "
        "become true takes no `trigger` (conditions in `immediate`) or waits in a hidden relay with none; "
        "the comment says why the trigger already holds when queued, starting \"cancels\" when it also "
        "stops an event whose premise went away during the delay.",
        where="trailing on the target event's `trigger = {` line",
        tags=("delayed_trigger",),
        note="Call sites are read through `script_call_graph`, so an id passed as `$EVENT$` counts at its "
             "caller. The self-checks `delayed_trigger_queue_probe` and `delayed_trigger_fire_probe` settle "
             "the engine rule. `--write` writes the report offline.",
    ),
    Audit(
        "random_list_weight_audit",
        "A `trigger = { }` in a `random_list` branch's weight `modifier`: the engine rejects the token "
        "and the tilt is lost. Use `if = { limit = { ... } add = N }`; the `ai_chance` form is valid.",
        post_load=False,
        report=None,
    ),
    Audit(
        "effect_trigger_validity_audit",
        "An effect or trigger name the engine doesn't know, or a known one in the wrong kind of block (an "
        "effect where triggers are read, or the reverse). The engine logs it at load and drops the line.",
        where=VALUE_LINE,
        note="Reads only the committed catalogs under docs/engine/ (#1142).",
    ),
    Audit(
        "script_argument_audit",
        "A scripted effect or trigger call whose arguments are not exactly the `$X$` names its callee's "
        "body uses, or an argument whose value is a `{ }` block.",
        where="on the call's line (its opening line for a multi-line call)",
        tags=("script_argument",),
        note="CI checks mod callees only; a reload on a machine with the game checks calls to vanilla's "
             "too. `GET /script-args/<helper>` lists every caller's arguments.",
    ),
    Audit(
        "duplicate_key_audit",
        "A key repeated inside one modifier-family block. With differing values the last one wins and "
        "the first is lost (error); identical repeats are warnings and don't fail CI (#191).",
        where="trailing on the duplicate's line",
    ),
    Audit(
        "modifier_field_audit",
        "A modifier type name no definition registers: written as a field in a modifier block (the "
        "engine drops the line) or read as `modifier:<name>` (it reads nothing). A name that fits a "
        "dynamic family, or that `modifiers.log` lists, still needs its own definition in "
        "`common/modifier_type_definitions/`. Also a field whose type vanilla registers without a loc "
        "key, so its line shows the raw key.",
        where="for a missing loc key only, trailing on a modifier block's line that writes the field (one "
              "comment covers every use); an unregistered name takes none",
        tags=("modifier_field_loc",),
        note="Builds a small ModState from vanilla_parsed/. A type only the mod registers is "
             "`loc_coverage_audit`'s to name. `/validate/engine-coverage` makes the registration "
             "judgment interactively; this is the copy that fails a reload and CI.",
        builds_mod_state=True,
    ),
    Audit(
        "mod_structure_audit",
        "Unbalanced braces in a `common/` file (the engine drops the rest of the file), an `INJECT:` on "
        "an entity the mod itself defines or REPLACEs (it never applies), and two bare declarations of "
        "one top-level name (only one survives).",
        ci=None,
        where="trailing on the `INJECT:<name>` line (brace and collision flags take none)",
        builds_mod_state=True,
    ),
    Audit(
        "load_order_audit",
        "A key whose value in ModState differs from what the engine loads: a bare copy the engine drops "
        "for an earlier one (the first bare definition wins, and vanilla's and the mod's files sort "
        "together), an `INJECT:` lost to a `REPLACE:` of its key, or a directive on a key nothing "
        "defines. Every tool built on ModState then reads a definition the game doesn't use.",
        note="Replays `external_mod_overlap`'s load-order model against the values ModState holds "
             "(#1191). CI has no game files, so a mod bare copy of a vanilla key is decided only when "
             "its file sorts before or after every vanilla file of the folder; the rest are listed as "
             "undetermined, and a reload on a machine with the game decides them.",
        builds_mod_state=True,
    ),
    Audit(
        "attitude_key_audit",
        "An `attitude = <key>` that is not one of the engine's fifteen attitude keys.",
        where=VALUE_LINE,
        note="The bare run fails on a flag too, as it did before it took `--strict`.",
    ),
    Audit(
        "prev_scope_audit",
        "A `prev` that can only mean a scope the script already names. `prev` is one scope change back, "
        "and re-entering `root` in a loop makes it `root`.",
        where="trailing on the `prev` line or the named scope's opener line",
    ),
    Audit(
        "empty_effect_audit",
        "An empty effect block, or an event option with no effect at all.",
        where="on or inside the empty block (`empty_block`), or anywhere inside the option "
              "(`no_effect_option`)",
        tags=("empty_block", "no_effect_option"),
    ),
    # --- script: variables and modifiers -------------------------------------
    Audit(
        "modifier_multiplier_var_audit",
        "An `add_modifier { multiplier = var:X }` whose variable can read as `none`: the multiplier "
        "resolves against ROOT, not the scope the effect runs in.",
        where="trailing on the `multiplier = ...` line or the `remove_variable` line",
    ),
    Audit(
        "je_multiplier_scope_audit",
        "A country-only read inside a `je:` modifier multiplier, followed through named script values "
        "and scripted triggers. Reads through `owner` or an explicit scope path are safe.",
        where="trailing on the multiplier (or `value`) line",
    ),
    Audit(
        "modifier_duration_audit",
        "An `add_modifier` duration written as `{ value = N }` or computed, which the engine reads as 0 "
        "days. Followed through helpers' `$DAYS$`.",
        where="trailing on the duration's line or the `add_modifier = {` line; for a value passed "
              "through a helper's `$X$`, on the argument's line or the call's opening line",
    ),
    Audit(
        "modifier_visibility_audit",
        "A modifier value too small to show at its type's `decimals = N`, so the tooltip prints 0.",
        ci=None,
        where=VALUE_LINE,
    ),
    Audit(
        "sol_fraction_audit",
        "A `*_standard_of_living_add` that is not a whole number and is not scaled before it applies. "
        "Standard of living is an integer, so the fraction does nothing on its own (#338).",
        where=VALUE_LINE,
    ),
    Audit(
        "change_variable_clamp_audit",
        "A `min =` / `max =` inside `change_variable`, where which way it clamps is a guess.",
        where="trailing on the `min =` / `max =` line or the `change_variable = {` line",
    ),
    Audit(
        "building_scope_variable_audit",
        "A variable set or read in building scope. Buildings hold no variables (#519).",
        where="trailing on the flagged operation or the bare `var:X` line",
    ),
    Audit(
        "variable_guard_audit",
        "A `has_variable = X` guard (or the global or local form) as a direct child of a `NOT`, `NAND` "
        "or `NOR` that also reads `var:X` bare. A multi-child `NOT` reads every child, so the guard "
        "protects nothing and an unset X logs `Failed to fetch variable`; read as NOR the block is "
        "also wrong when X is set. Move the guard into a limit and keep the rest of the block inside "
        "the negation, `trigger_if = { limit = { has_variable = X } NOT = { … } }`; an equality with "
        "a number can instead be read as `var:X ?= N`.",
        where="trailing on the opening line of the `NOT` / `NAND` / `NOR`",
        tags=("variable_guard",),
        note="A guard beside its read in an `AND` or at a trigger's top level is not flagged. Walks "
             "all of `common/` and `events/`, so it takes several seconds.",
    ),
    Audit(
        "container_timed_variable_audit",
        "A timed variable set on a script container, where it never expires.",
        where="trailing on the `set_variable` line or its `days` / `months` line",
    ),
    Audit(
        "je_immediate_reset_audit",
        "An unguarded write in a journal entry's `immediate`. A revolution's winner re-runs `immediate`, "
        "so the write resets state the nation should keep.",
        where="on any line of the flagged write, the innermost `if` / `else_if` / `else` / "
              "`random_list` / `random` opener around it, or a call line leading to it",
    ),
    # --- events --------------------------------------------------------------
    Audit(
        "orphaned_event_audit",
        "An event nothing fires (#147).",
        where="trailing on the event's opening `<id> = {` line",
    ),
    Audit(
        "event_image_audit",
        "A visible event with no `event_image`. It draws a magenta blob and the engine logs nothing "
        "(#353).",
        where="trailing on the event's opening `<id> = {` line",
    ),
    Audit(
        "event_context_audit",
        "An event whose text doesn't fit where it fires: a system's event not gated on its game rule, "
        "text that says the country did something it never chose, or a foreign action imputed to it.",
        where="on a line of its own anywhere inside the event (not the opening line: three other "
              "audits read that one)",
        tags=("system_ungated", "unchosen_self_action", "imputed_foreign_action"),
    ),
    Audit(
        "trigger_event_cycle_audit",
        "A `trigger_event` with no delay on a cycle of scripted effect calls and other undelayed "
        "`trigger_event`s. It runs inside the effect that fires it, so a cycle nothing stops overflows "
        "the stack: a crash with no log line. Write what the cycle re-reads before the `trigger_event`, "
        "or give it `days = 1`; the comment is for a cycle a write already stops, and names that write.",
        where="trailing on the `trigger_event` line; for an id passed as `$EVENT$`, on the opening line "
              "of the call that names it",
        tags=("trigger_event_cycle",),
        note="`--through <event or effect>` lists the flagged cycles a name lies on. The graph is "
             "`script_call_graph.py`.",
    ),
    Audit(
        "tooltip_walk_variable_audit",
        "A variable read after a `set_variable` of it in one body a tooltip walks (a scripted GUI's or a "
        "button's `effect`, an event option, a decision's `when_taken`). The walk writes nothing, so the "
        "read finds it unset and logs every frame the tooltip shows. Compare the values directly, guard the "
        "read with `has_variable`, use `?=`, or put the body behind a click-only marker; names other code "
        "keeps set are left out.",
        where="trailing on the read line; for a read passed as a `$PARAM$` argument, on the line of the "
              "call that passes it",
        tags=("tooltip_walk",),
        post_load=False,
        report=None,
        note="`--root <scripted GUI, event id or decision>` lists one root's flags with their call chains. "
             "It reads `script_call_graph.py` to tell which effects run outside a tooltip. Not on reload: "
             "a run takes about 25 s cold and 13 to 15 s warm.",
    ),
    Audit(
        "faith_scene_audit",
        "An event text with one faith's word in it (a priest, a mosque, a guru, the faith's name) that "
        "a country of another state religion can be shown: its title, description, flavor, option, "
        "tooltip or a modifier it adds. Write the scene without a named faith, or gate that version on "
        "the faith (#1531).",
        where="trailing on the key's loc line",
        tags=("faith_scene",),
        note="`--explain <key>` lists where a key is named and the gate read at each place. It reads "
             "religion gates only: a text gated on culture, a country or a variable is flagged and "
             "takes the comment. The word list is `VOCABULARY` in the audit.",
    ),
    Audit(
        "silent_variable_audit",
        "An event option that moves a number the UI shows with `change_variable` / `set_variable`, "
        "which render nothing in the tooltip. Wrap it in a `custom_tooltip`.",
        where="anywhere inside the option",
        tags=("silent_variable",),
    ),
    Audit(
        "kill_character_audit",
        "A `kill_character` in an event with no guard that the character exists.",
        where="trailing on the `kill_character` line or the line above it",
        report="kill_character_audit.md",
        note="`--strict` (alias `--check`) fails on a kill with neither guard and writes no report; "
             "the bare run writes the report.",
    ),
    Audit(
        "event_magnitude_audit",
        "A hardcoded amount in an event for a resource that grows fast over the game (prestige is the "
        "model case), which is invisible at late-game scale.",
        where=VALUE_LINE,
        note="Reads `events/` only: an amount granted from a scripted effect is flagged only where an "
             "event repeats it, as in a `show_as_tooltip` (#1593).",
        builds_mod_state=True,
    ),
    # --- treaties, blocs, companies, laws ------------------------------------
    Audit(
        "treaty_leverage_side_audit",
        "A treaty article with `country_treaty_leverage_generation_add` on the side that pays, or one "
        "that builds no Involvement because it lacks `max_target_involvement` / "
        "`target_involvement_applies_to` or names the wrong side; and a diplomatic action's pact "
        "that builds none or departs from vanilla's pact convention (`source_country`, or `mutual`).",
        where="trailing on the `country_treaty_leverage_generation_add` line or the article's opening "
              "line; for an Involvement flag, the `(involvement)` form on the article's or action's "
              "opening line, a pact's `pact = {` line, or either field's line",
        tags=("", "involvement"),
    ),
    Audit(
        "treaty_evaluation_scope_audit",
        "A named-scope read in a treaty article's AI `evaluation_chance`, which sees only root; or a "
        "party scope in a block that does not bind it: `scope:source_country` / `scope:target_country` "
        "in `visible` / `possible` (use root and `scope:other_country`), or `scope:other_country` in "
        "`can_ratify` / `requirement_to_maintain` / `can_propose` (use source / target; first / "
        "second on a mutual article).",
        post_load=False,
        where="trailing on the flagged line, for a read in `visible`, `possible`, `can_ratify`, "
              "`requirement_to_maintain` or `can_propose`; a read in `evaluation_chance` takes none",
        tags=("treaty_scope",),
        report=None,
        note="Direct reads only: it does not open a scripted trigger or value the block calls.",
    ),
    Audit(
        "principle_tier_audit",
        "A power bloc principle tier that drops a modifier the tier below carried. Tiers replace each "
        "other, so each restates everything below it.",
        where="trailing on the higher tier's opening line (covers the whole tier) or the modifier's "
              "line in either tier",
        builds_mod_state=True,
    ),
    Audit(
        "prestige_good_roster_audit",
        "A company prestige good no `building_types` building of the company can make, one on a "
        "`local = yes` good, or a fourth prestige good on one base good (the engine keeps three).",
        where="trailing on the prestige good's line in `possible_prestige_goods` or the company's "
              "opening line (covers the whole company); for a `local` or cap flag, the prestige "
              "good's opening line",
        builds_mod_state=True,
    ),
    Audit(
        "amendment_reachability_audit",
        "An amendment no script attaches, or an `add_amendment` whose type names no amendment.",
        where="trailing on the amendment's opening line or its `allowed_laws` entry; for an unknown "
              "type, the `add_amendment = {` or `type =` line",
        tags=("amendment_reachability",),
    ),
    Audit(
        "ideology_lawgroup_audit",
        "An ideology's lawgroup block that leaves out a law of its group, which makes the ideology "
        "neutral on it.",
        where="on the lawgroup block's or the ideology's opening line in a hand-written ideology file; "
              "for the generated `modified.txt`, on the `\"lawgroup_x\":` or `\"ideology_x\": {` line "
              "in `ideology_modifications.py`",
        tags=("ideology_lawgroup",),
        builds_mod_state=True,
    ),
    Audit(
        "roster_membership_audit",
        "A mod ship type with no `ai_ship_category` (required since vanilla 1.14.4), an unknown one, or "
        "no fleet entity row; a ship modification no ship type lists in a slot, so it can never be "
        "fitted; or a production method no production method group lists.",
        where="trailing on the opening line of the unlisted modification or production method; a ship "
              "type flag takes none",
        tags=("roster_membership",),
        note="Builds a small ModState from vanilla_parsed/. The fleet entity check reads the `SHIPS` "
             "table of `scripts/generators/gen_fleet_entities.py`, and the generated blocks too where "
             "gfx/ is on disk.",
        builds_mod_state=True,
    ),
    Audit(
        "pm_employment_audit",
        "A building where some valid production-method combination drives a profession's employment "
        "below zero.",
        where="trailing on the opening line of the building or of the most negative production method "
              "(a method's comment covers every building that uses it)",
        note="Builds a ModState from vanilla_parsed/ (about 7 s). Also fails when a building is "
             "skipped for exceeding the combination cap, since it went unaudited (#681).",
        builds_mod_state=True,
    ),
    # --- localization --------------------------------------------------------
    Audit(
        "loc_coverage_audit",
        "A mod entity (modifier, journal entry, button, building, method...) with no loc key. The game "
        "shows the raw key and logs nothing.",
        where="trailing on the entity's opening `<name> = {` line",
        note="Builds a ModState from vanilla_parsed/ (about 7 s); a stale snapshot can flag or hide a "
             "vanilla key.",
        builds_mod_state=True,
    ),
    Audit(
        "script_loc_reference_audit",
        "A loc key named in script (`desc = \"KEY\"`, `text = KEY`) that no loc file defines.",
        where="trailing on the reference's line",
    ),
    Audit(
        "loc_render_audit",
        "Bracket-style formatting in a loc value (`[b]x[/b]`), which errors on every render: write "
        "`#b x#!`. Also a formatting tag left open at the end of a value (`#bold` with no `#!`), which "
        "runs on into the text after it, a `#` that is no tag (write a literal hash as `##`), and a format "
        "name that no vanilla loc value opens in any case (`#bolt`).",
        where="trailing on the loc line",
        note="Only the mod's own values are judged, and a surplus `#!` is never flagged. An opening "
             "fragment that its caller closes takes the comment, naming the caller.",
    ),
    Audit(
        "loc_script_value_audit",
        "A `ScriptValue('x')` in loc or a script string that names no script value. It renders 0.",
        where="trailing on the loc line, or in script on the line the string closes on",
        tags=("loc_script_value",),
        note="The .gui half is gui_reference_audit's.",
    ),
    Audit(
        "loc_root_context_audit",
        "A loc key on a country root that doesn't fit where it renders, reached there by a `$KEY$` splice, "
        "a named key or a `GetCustom` entry. A `ROOT.`, `SCOPE.` or `THIS.` read in a key a widget renders "
        "comes out blank. A `JournalEntry.` or `Country.` read in a `status_desc` key or a scripted "
        "button's text is the unproven root there (not known to fail): use the proven one, "
        "`ROOT.GetCountry…`. An entry or player read on a public tab shows another country the player's "
        "figure, or nothing.",
        where="trailing on the flagged key's loc line (a public-tab flag takes none: a world read goes "
              "in `WORLD_LOC`)",
        tags=("loc_root_context",),
        note="A reload leaves the public-tab kinds to this command and to `BindingTest` "
             "(`test_te_system_tab_bodies.py`), whose rules they are; it takes about 2.5 s without them, "
             "this command about 5 s. Each flag gives its path from the line that names the first key.",
    ),
    Audit(
        "concept_reference_audit",
        "A loc link to a game concept that doesn't exist. The link breaks and logs three errors a "
        "render (#1257).",
        where="trailing on the loc line",
        note="Builds a ModState from vanilla_parsed/ (about 7 s).",
        builds_mod_state=True,
    ),
    Audit(
        "localization_accessor_audit",
        "A loc accessor chain (`[X.Y.Z]`) the engine's data-type catalog doesn't allow. The engine "
        "renders it as nothing.",
        where="trailing on the loc line",
        note="The catalog knows what vanilla's loc calls. An accessor the engine has and vanilla's "
             "loc never uses flags too: add it to `_BUILTIN_ACCESSORS_BY_TYPE` instead of suppressing "
             "(#348; its row in python_tools.md).",
    ),
    # --- GUI and assets ------------------------------------------------------
    Audit(
        "gui_reference_audit",
        "A mod `.gui` or journal-entry widget mount that names a loc key, scripted GUI, script value, "
        "type or concept that doesn't exist.",
        note="Takes no suppression: fix the reference. Vanilla-unavailable categories and dynamic "
             "saved-scope bindings are warnings.",
    ),
    Audit(
        "texture_reference_audit",
        "An asset path in script that names no file, or an entity that declares no art field its type "
        "needs. The engine logs a missing texture only on first render.",
        where="on the path's line; for an undeclared art field, the entity's opening line",
        tags=("texture_reference",),
        note="Vanilla's files come from docs/engine/vanilla_asset_paths.txt, the mod's from "
             "`git ls-files gfx/`, so it runs in a checkout without gfx/.",
    ),
    Audit(
        "long_tooltip_audit",
        "Live GUI text or a tooltip over 500 rendered characters outside a How section. The rules "
        "belong in How, or in a concept the tooltip links.",
        where="trailing on the key's loc line",
        tags=("long_tooltip",),
    ),
    Audit(
        "hidden_modifier_audit",
        "A `custom_tooltip` around an `add_modifier` whose text renders no `GetStaticModifier` for it: "
        "the player sees the text and none of the modifier's lines.",
        where="on the `custom_tooltip = {` line",
        tags=("hidden_modifier",),
    ),
    Audit(
        "button_reason_audit",
        "A button a scripted GUI greys out whose tooltip doesn't say why, or one whose reason prints "
        "as raw script.",
        where="`missing_reason` on the `enabled =` line; `raw_condition` on the `is_valid = {` / "
              "`possible = {` line",
        tags=("missing_reason", "raw_condition"),
    ),
)

BY_NAME = {a.name: a for a in AUDITS}


def get(name: str) -> Audit:
    return BY_NAME[name]


def ci_audits() -> tuple[Audit, ...]:
    return tuple(a for a in AUDITS if a.ci is not None)


def post_load_audits() -> tuple[Audit, ...]:
    return tuple(a for a in AUDITS if a.post_load)


# --- the figures python_tools.md spells out (#1695) ---------------------------

TOOLS_DOC_PATH = os.path.join("docs", "guides", "python_tools.md")
ROSTER_PATH = os.path.join("server", "post_load.py")  # POST_LOAD_REGENERATORS, POST_LOAD_AUDITS

_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
         "fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()


def spell(n: int) -> str:
    """`n` in words, as the prose writes it ("forty-six"); digits from 100."""
    if n < 20:
        return _ONES[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        return _TENS[tens - 2] + (f"-{_ONES[ones]}" if ones else "")
    return str(n)


_WORDS = {spell(n): n for n in range(100)}
_NUM = r"(\d+|(?i:" + "|".join(sorted(_WORDS, key=len, reverse=True)) + r"))"


def _read_number(text: str) -> int:
    return int(text) if text.isdigit() else _WORDS[text.lower()]


def _write_number(n: int, like: str) -> str:
    """`n` in the form `like` has: digits, or words with its capital."""
    if like.isdigit():
        return str(n)
    word = spell(n)
    return word[:1].upper() + word[1:] if like[:1].isupper() else word


def _named(text: str) -> list[str]:
    return re.findall(r"`([a-z0-9_]+_audit)`", text)


def _rosters() -> dict[str, list[str]]:
    from scripts.analysis.check_post_load_rosters import extract_rosters
    return extract_rosters(os.path.join(REPO_ROOT, ROSTER_PATH))


def _ci_only() -> list[Audit]:
    return [a for a in AUDITS if a.ci is not None and not a.post_load]


def _out_of_ci() -> list[Audit]:
    return [a for a in AUDITS if a.post_load and a.ci is None]


def _ci_builders() -> list[Audit]:
    return [a for a in ci_audits() if a.builds_mod_state]


@dataclass(frozen=True)
class Figure:
    """A sentence of python_tools.md that spells out figures. `{N}` in `template`
    is a figure, digits or words; `{NAMES}` is free text up to a `)`. `expect`
    takes that text (or "") and gives the figures, in order."""
    template: str
    expect: Callable[[str], tuple[int, ...]]
    what: str

    def regex(self) -> re.Pattern:
        parts = re.split(r"(\{N\}|\{NAMES\})", self.template)
        out = []
        for part in parts:
            if part == "{N}":
                out.append(_NUM)
            elif part == "{NAMES}":
                out.append(r"(?P<names>[^)]*)")
            else:
                out.append(re.escape(part))
        return re.compile("".join(out))


PROSE_FIGURES: tuple[Figure, ...] = (
    Figure("`POST_LOAD_REGENERATORS` (the {N} file-rewriting generators)",
           lambda _: (len(_rosters()["POST_LOAD_REGENERATORS"]),),
           "entries in POST_LOAD_REGENERATORS"),
    Figure("`POST_LOAD_AUDITS` (the {N} read-only audits)",
           lambda _: (len(post_load_audits()),),
           "post-load audits"),
    Figure("{N} of these post-load audits, plus {N} CI-only audits",
           lambda _: (sum(1 for a in post_load_audits() if a.ci is not None), len(_ci_only())),
           "post-load audits CI runs, then audits only CI runs"),
    Figure("Of those {N}, {N} are pure file scans that never build a `ModState`",
           lambda _: (len(ci_audits()), len(ci_audits()) - len(_ci_builders())),
           "CI audits, then those whose `builds_mod_state` is False"),
    Figure("The other {N} build one.",
           lambda _: (len(_ci_builders()),),
           "CI audits whose `builds_mod_state` is True"),
    Figure("The other {N} post-load audits stay out of CI.",
           lambda _: (len(_out_of_ci()),),
           "post-load audits with no CI command"),
    Figure("the {N} offline audit CLIs (all in CI)",
           lambda _: (len(ci_audits()),),
           "CI audits"),
)


@dataclass(frozen=True)
class Names:
    """Audits named between `start` and the next `end`: `exact` holds them to
    `expect()`; otherwise every expected audit must be among them."""
    start: str
    end: str
    expect: Callable[[], list[Audit]]
    what: str
    exact: bool = True


PROSE_NAMES: tuple[Names, ...] = (
    Names("CI-only audits (", ")", _ci_only, "the audits only CI runs"),
    Names("build one.", "Each prints its report", _ci_builders,
          "the CI audits whose `builds_mod_state` is True", exact=False),
    Names("post-load audits stay out of CI.", "(vanilla data, loc index)", _out_of_ci,
          "the post-load audits with no CI command"),
)


def _table_rows(text: str, heading: str) -> list[str]:
    """The first column of the table under `heading`, backticks stripped."""
    start = text.find(heading)
    if start < 0:
        return []
    rows, seen_table = [], False
    for line in text[start:].splitlines()[1:]:
        if line.startswith("|"):
            seen_table = True
            m = re.match(r"\| `([^`]+)` \|", line)
            if m:
                rows.append(m.group(1))
        elif seen_table:
            break
    return rows


def check_tools_doc(text: str) -> tuple[str, list[str]]:
    """Hold python_tools.md's audit figures, names and tables to the registry.
    Returns the text with every figure corrected, and what is wrong (figures
    included, so a caller that writes nothing still fails)."""
    problems = []
    for fig in PROSE_FIGURES:
        regex = fig.regex()
        matches = list(regex.finditer(text))
        if len(matches) != 1:
            problems.append(
                f"{TOOLS_DOC_PATH}: found {len(matches)} sentences like `{fig.template}` "
                "where one was expected. If you reworded it, change its `Figure` in "
                "audit_registry.py's PROSE_FIGURES to match.")
            continue
        m = matches[0]
        names = m.groupdict().get("names") or ""
        expected = fig.expect(names)
        groups = [g for g in range(1, len(m.groups()) + 1) if m.re.groupindex.get("names") != g]
        wrong = [(g, want) for g, want in zip(groups, expected) if _read_number(m.group(g)) != want]
        if wrong:
            said = ", ".join(m.group(g) for g in groups)
            right = ", ".join(_write_number(want, m.group(g)) for g, want in zip(groups, expected))
            problems.append(f"{TOOLS_DOC_PATH}: \"{m.group(0)}\" gives {said} ({fig.what}); "
                            f"the registry gives {right}.")
        new = m.group(0)
        for g, want in reversed(wrong):
            lo, hi = m.start(g) - m.start(0), m.end(g) - m.start(0)
            new = new[:lo] + _write_number(want, m.group(g)) + new[hi:]
        if fig.template.endswith("{NAMES})"):
            for name in _named(names):
                audit = BY_NAME.get(name)
                if audit is None or audit.ci is not None:
                    problems.append(
                        f"{TOOLS_DOC_PATH}: \"{m.group(0)}\" counts `{name}` beside the CI "
                        "audits, but it is no audit outside CI.")
        text = text[:m.start(0)] + new + text[m.end(0):]
    for spec in PROSE_NAMES:
        start = text.find(spec.start)
        end = text.find(spec.end, start + len(spec.start)) if start >= 0 else -1
        if start < 0 or end < 0 or text.count(spec.start) > 1:
            problems.append(
                f"{TOOLS_DOC_PATH}: no one text from `{spec.start}` to `{spec.end}`. If you "
                "reworded it, change its `Names` in audit_registry.py's PROSE_NAMES to match.")
            continue
        named = set(_named(text[start + len(spec.start):end]))
        want = {a.name for a in spec.expect()}
        for name in sorted(want - named):
            problems.append(f"{TOOLS_DOC_PATH}: the text after `{spec.start}` names "
                            f"{spec.what} but leaves out `{name}`.")
        if spec.exact:
            for name in sorted(named - want):
                problems.append(f"{TOOLS_DOC_PATH}: the text after `{spec.start}` names "
                                f"`{name}`, which is not one of {spec.what}.")
    heading = "#### `POST_LOAD_AUDITS`"
    rows, roster = _table_rows(text, heading), _rosters()["POST_LOAD_AUDITS"]
    if rows != list(roster):
        first = next((i for i, (a, b) in enumerate(zip(rows, roster)) if a != b),
                     min(len(rows), len(roster)))
        problems.append(
            f"{TOOLS_DOC_PATH}: the table under {heading} is not POST_LOAD_AUDITS in run "
            f"order; row {first + 1} is {rows[first] if first < len(rows) else 'missing'}, "
            f"the roster has {roster[first] if first < len(roster) else 'nothing more'}.")
    rows = [r for r in re.findall(r"^\| `(python3 [^`]+)` \|", text, re.M) if "_audit.py" in r]
    commands = [a.command for a in ci_audits()]
    for command in commands:
        if rows.count(command) != 1:
            problems.append(
                f"{TOOLS_DOC_PATH}: the CI command table has {rows.count(command)} rows for "
                f"`{command}`; it needs one, saying when the command exits 1.")
    for row in sorted(set(rows) - set(commands)):
        problems.append(f"{TOOLS_DOC_PATH}: the CI command table has a row for `{row}`, which is "
                        "not a command CI runs (audit_registry.py gives each audit's).")
    return text, problems


def suppression_hint(name: str) -> str:
    """What to tell someone whose change tripped `name`. Empty for an unknown audit."""
    audit = BY_NAME.get(name)
    if audit is None:
        return ""
    lines = [f"What a flag means: {audit.catches}"]
    if audit.where is None:
        lines.append("This audit takes no suppression comment: fix the flag.")
    else:
        lines.append("Fix it, or if it is intended, add  " + "  or  ".join(audit.comment_forms))
        lines.append(f"Where: {audit.where}.")
    if audit.report_path:
        lines.append(f"Report: {audit.report_path}")
    return "\n".join(lines)


def _forms_cell(audit: Audit) -> str:
    if audit.where is None:
        return "none"
    return "<br>".join(f"`{form}`" for form in audit.comment_forms)


def render_markdown() -> str:
    ci = ci_audits()
    post = post_load_audits()
    out = [
        "# The audits",
        "",
        "<!-- AUTO-GENERATED by `python3 audit_registry.py --write` from `audit_registry.py`. "
        "Do not edit: change the registry and regenerate. -->",
        "",
        f"The mod has {len(AUDITS)} offline audits. Each reads the mod's files and flags something the "
        "engine accepts without a word and then gets wrong in play. "
        f"{len(post)} run on every `POST /reload` and feed its `warnings` array; "
        f"{len(ci)} run in CI and fail the build.",
        "",
        "Run them all, in parallel, the way CI does:",
        "",
        "```sh",
        ".venv/bin/python scripts/run_audits.py            # every CI audit",
        ".venv/bin/python scripts/run_audits.py prev_scope  # one or more, by name",
        "```",
        "",
        "When one fails, the runner prints what the flag means and the comment that suppresses an "
        "intended one. A suppression is a dated, reasoned comment in the mod file; the placement "
        "differs by audit because each reads a different line. For the tagged forms, a tag that no "
        "longer matches a flag fails `--strict`, so a stale comment can't linger.",
        "",
        "One comment on an event's opening line is read by every audit that reads that line. That is "
        "why the event audits added later take a tagged comment inside the event instead.",
        "",
        "## What each audit catches",
        "",
        "| Audit | A flag means | Runs |",
        "|---|---|---|",
    ]
    for a in AUDITS:
        runs = []
        if a.ci is not None:
            runs.append("CI")
        if a.post_load:
            runs.append("reload")
        out.append(f"| `{a.name}` | {a.catches} | {', '.join(runs)} |")
    out += [
        "",
        "## Suppressing an intended flag",
        "",
        "| Audit | Comment | Where it goes |",
        "|---|---|---|",
    ]
    for a in AUDITS:
        out.append(f"| `{a.name}` | {_forms_cell(a)} | {a.where or 'Fix the flag.'} |")
    out += [
        "",
        "## Commands, reports and notes",
        "",
        "| Audit | CI command | Report | Note |",
        "|---|---|---|---|",
    ]
    for a in AUDITS:
        cmd = f"`{a.command}`" if a.command else "reload only"
        report = f"`{a.report_path}`" if a.report_path else "none"
        out.append(f"| `{a.name}` | {cmd} | {report} | {a.note} |")
    out += [
        "",
        "## Adding an audit",
        "",
        "1. Write `<name>_audit.py` at the repo root, and `test_<name>_audit.py` beside it. The audit "
        "is the function that finds flags; `audit_common.py` gives it the rest: "
        "`parse_reviewed(comment, tags)` reads the `# REVIEWED` comment, `Flag` and `AuditResult` "
        "hold the findings (`unreviewed`, `exemptions`, `stale`), `write_report` writes the report "
        "with this page's suppression text, and `cli_main(audit_fn)` gives the `--strict` mode that "
        "exits 1 on an unreviewed flag or a stale tag. A reload audit also needs "
        "`regenerate(mod_state)` returning a dict whose `unreviewed` count feeds the `warnings` array "
        "(`audit_common.summary` builds it).",
        "2. Add it to `POST_LOAD_AUDITS` in `server/post_load.py` if a reload should run it.",
        "3. Add one `Audit(...)` entry to `audit_registry.py`, with `builds_mod_state=True` if its "
        "command line builds a `ModState`.",
        "4. Run `python3 audit_registry.py --write` and commit this file with the rest. It also "
        "corrects the audit counts `docs/guides/python_tools.md` spells out, and prints what is left "
        "there for you to write: a CI audit's row in the command table, its row in the reload table, "
        "its name where a sentence lists audits by where they run.",
        "",
        "CI, `scripts/preflight.py` and this page all read the registry, "
        "`test_audit_registry.py` fails on an audit file the registry leaves out, and "
        "`audit_registry.py --check` fails on a count in `python_tools.md` that disagrees with it.",
        "",
    ]
    return "\n".join(out)


def _read(path: str) -> str:
    try:
        with open(os.path.join(REPO_ROOT, path), encoding="utf-8", newline="") as fh:
            return fh.read()
    except FileNotFoundError:
        return ""


def _write(path: str, text: str) -> None:
    with open(os.path.join(REPO_ROOT, path), "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true",
                       help=f"Regenerate {DOC_PATH} and correct the figures in {TOOLS_DOC_PATH}.")
    group.add_argument("--check", action="store_true",
                       help=f"Exit 1 if {DOC_PATH} is stale or {TOOLS_DOC_PATH} disagrees.")
    group.add_argument("--hint", metavar="AUDIT", help="Print an audit's suppression hint.")
    args = parser.parse_args(argv)

    text = render_markdown()
    if args.hint:
        name = args.hint if args.hint.endswith("_audit") else args.hint + "_audit"
        hint = suppression_hint(name)
        print(hint or f"No audit named {name}.")
        return 0 if hint else 1
    if args.write:
        _write(DOC_PATH, text)
        print(f"Wrote {DOC_PATH} ({len(AUDITS)} audits).")
        tools = _read(TOOLS_DOC_PATH)
        fixed, problems = check_tools_doc(tools)
        if fixed != tools:
            _write(TOOLS_DOC_PATH, fixed)
            print(f"Corrected the figures in {TOOLS_DOC_PATH}.")
        left = check_tools_doc(fixed)[1]
        for problem in left:
            print(problem)
        if left:
            print(f"{len(left)} problem(s) in {TOOLS_DOC_PATH} need a hand edit.")
        return 1 if left else 0
    if args.check:
        failed = False
        if _read(DOC_PATH) != text:
            print(f"{DOC_PATH} is stale: run `python3 audit_registry.py --write` and commit it.")
            failed = True
        problems = check_tools_doc(_read(TOOLS_DOC_PATH))[1]
        for problem in problems:
            print(problem)
        if problems:
            print("Run `python3 audit_registry.py --write` to correct the figures; it prints "
                  "what needs a hand edit.")
            failed = True
        if failed:
            return 1
        print(f"OK: {DOC_PATH} and the figures in {TOOLS_DOC_PATH} match audit_registry.py "
              f"({len(AUDITS)} audits).")
        return 0
    for a in AUDITS:
        print(f"{a.name:34} {'CI ' if a.ci is not None else '   '} {'reload' if a.post_load else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
