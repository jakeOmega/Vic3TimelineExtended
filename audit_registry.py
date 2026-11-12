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
* `test_audit_registry.py` holds it to `POST_LOAD_AUDITS` in
  `mod_state_server.py` and to the `*_audit.py` files on disk.

Adding an audit: write the module and its test, add it to `POST_LOAD_AUDITS`
if a reload should run it, add one `Audit(...)` here, and run
`python3 audit_registry.py --write`. Nothing else restates the roster.

Stdlib only, and it imports no audit: a reader needs neither numpy nor a game
install.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

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
        "An `any_*` trigger with a `limit = { }` child. `any_*` takes its conditions directly; the engine "
        "rejects the block.",
        where="trailing on the `any_*` opener line or on the `limit = {` line",
    ),
    Audit(
        "iterator_limit_audit",
        "An iterator whose `limit = { }` is not its first child. The limit filters the whole iteration "
        "wherever it sits, so the lines written above it are gated by it too.",
        where="trailing on the `limit = {` line or the iterator's opener line",
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
        "mod_structure_audit",
        "Unbalanced braces in a `common/` file (the engine drops the rest of the file), an `INJECT:` on "
        "an entity the mod itself defines or REPLACEs (it never applies), and two bare declarations of "
        "one top-level name (only one survives).",
        ci=None,
        where="trailing on the `INJECT:<name>` line (brace and collision flags take none)",
    ),
    Audit(
        "attitude_key_audit",
        "An `attitude = <key>` that is not one of the engine's fifteen attitude keys.",
        ci=(),
        where=VALUE_LINE,
        note="Runs bare in CI: it has no flag, and `main()` returns the exit code.",
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
        ci=("--check",),
        where="trailing on the `kill_character` line or the line above it",
        report="kill_character_audit.md",
    ),
    Audit(
        "event_magnitude_audit",
        "A hardcoded amount in an event for a resource that grows fast over the game (prestige is the "
        "model case), which is invisible at late-game scale.",
        where=VALUE_LINE,
        note="Reads `events/` only: an amount granted from a scripted effect is flagged only where an "
             "event repeats it, as in a `show_as_tooltip` (#1593).",
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
        "`can_ratify` / `requirement_to_maintain` (use source / target; first / second on a mutual "
        "article).",
        post_load=False,
        where="trailing on the flagged line, for a read in `visible`, `possible`, `can_ratify` or "
              "`requirement_to_maintain`; a read in `evaluation_chance` takes none",
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
    ),
    Audit(
        "prestige_good_roster_audit",
        "A company prestige good no `building_types` building of the company can make, or one on a "
        "`local = yes` good.",
        where="trailing on the prestige good's line in `possible_prestige_goods` or the company's "
              "opening line (covers the whole company); for a `local` flag, the prestige good's "
              "opening line",
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
    ),
    Audit(
        "pm_employment_audit",
        "A building where some valid production-method combination drives a profession's employment "
        "below zero.",
        where="trailing on the opening line of the building or of the most negative production method "
              "(a method's comment covers every building that uses it)",
        note="Builds a ModState from vanilla_parsed/ (about 7 s). Also fails when a building is "
             "skipped for exceeding the combination cap, since it went unaudited (#681).",
    ),
    # --- localization --------------------------------------------------------
    Audit(
        "loc_coverage_audit",
        "A mod entity (modifier, journal entry, button, building, method...) with no loc key. The game "
        "shows the raw key and logs nothing.",
        where="trailing on the entity's opening `<name> = {` line",
        note="Builds a ModState from vanilla_parsed/ (about 7 s); a stale snapshot can flag or hide a "
             "vanilla key.",
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
        "runs on into the text after it, and a `#` that is no tag: write a literal hash as `##`.",
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
             "(`test_te_system_tab_bodies.py`), whose rules they are; it takes about 1.4 s without them, "
             "this command about 4 s. Each flag gives its path from the line that names the first key.",
    ),
    Audit(
        "concept_reference_audit",
        "A loc link to a game concept that doesn't exist. The link breaks and logs three errors a "
        "render (#1257).",
        where="trailing on the loc line",
        note="Builds a ModState from vanilla_parsed/ (about 7 s).",
    ),
    Audit(
        "localization_accessor_audit",
        "A loc accessor chain (`[X.Y.Z]`) the engine's data-type catalog doesn't allow. The engine "
        "renders it as nothing.",
        ci=(),
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
        "1. Write `<name>_audit.py` at the repo root, with a `--strict` mode that exits 1 on an "
        "unreviewed flag, and `test_<name>_audit.py` beside it. A reload audit also needs "
        "`regenerate(mod_state)` returning a dict whose `unreviewed` count feeds the `warnings` array.",
        "2. Add it to `POST_LOAD_AUDITS` in `mod_state_server.py` if a reload should run it.",
        "3. Add one `Audit(...)` entry to `audit_registry.py`.",
        "4. Run `python3 audit_registry.py --write` and commit this file with the rest.",
        "",
        "CI, `scripts/preflight.py` and this page all read the registry, and "
        "`test_audit_registry.py` fails on an audit file the registry leaves out.",
        "",
    ]
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help=f"Regenerate {DOC_PATH}.")
    group.add_argument("--check", action="store_true", help=f"Exit 1 if {DOC_PATH} is stale.")
    group.add_argument("--hint", metavar="AUDIT", help="Print an audit's suppression hint.")
    args = parser.parse_args(argv)

    path = os.path.join(REPO_ROOT, DOC_PATH)
    text = render_markdown()
    if args.hint:
        name = args.hint if args.hint.endswith("_audit") else args.hint + "_audit"
        hint = suppression_hint(name)
        print(hint or f"No audit named {name}.")
        return 0 if hint else 1
    if args.write:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"Wrote {DOC_PATH} ({len(AUDITS)} audits).")
        return 0
    if args.check:
        try:
            with open(path, encoding="utf-8") as fh:
                current = fh.read()
        except FileNotFoundError:
            current = ""
        if current != text:
            print(f"{DOC_PATH} is stale: run `python3 audit_registry.py --write` and commit it.")
            return 1
        print(f"OK: {DOC_PATH} matches audit_registry.py ({len(AUDITS)} audits).")
        return 0
    for a in AUDITS:
        print(f"{a.name:34} {'CI ' if a.ci is not None else '   '} {'reload' if a.post_load else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
