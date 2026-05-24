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
  vanilla actually uses in its `events/` + `scripted_effects` +
  `scripted_triggers` + `on_actions` corpus. (b) is essential — control-flow and
  scope keywords like `limit`, `if`, `every_scope_country` are NOT in the
  effect/trigger docs. Regenerate on a vanilla bump via `bootstrap_catalog()`.
- The audit scans the same four mod dirs and flags any lowercase LHS keyword not
  in the catalog and not a mod-defined name (scripted effect/trigger/on_action).
  Uppercase tokens (scripted-effect `$PARAM$` call args) and `var:`-style refs
  are never LHS-matched, so they don't false-flag.
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

# Mod dirs scanned (relative to a root); also the vanilla corpus for bootstrap.
_SCAN_DIRS = (
    "events",
    os.path.join("common", "scripted_effects"),
    os.path.join("common", "scripted_triggers"),
    os.path.join("common", "on_actions"),
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
})
# Mod dirs whose top-level names are valid call/comparison targets but which we
# don't scan for effects (script values are compared as triggers by name).
_NAME_ONLY_DIRS = (os.path.join("common", "script_values"),)
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
    effect / trigger / on_action names — and their definition LHS — never flag)."""
    names: set[str] = set()
    if not os.path.isdir(root):
        return names
    for path in _iter_txt(root):
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                for line in fh:
                    m = _TOP_DEF_RE.match(line)
                    if m:
                        names.add(m.group(1))
        except OSError:
            continue
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
    # script_values is harvested here (vanilla SV names + their math keywords)
    # but NOT scanned for bugs in the mod.
    for rel in _SCAN_DIRS + _NAME_ONLY_DIRS:
        base = os.path.join(game, rel)
        if not os.path.isdir(base):
            continue
        for path in _iter_txt(base):
            try:
                with open(path, encoding="utf-8-sig", errors="replace") as fh:
                    keys |= extract_lhs_keys(fh.read())
            except OSError:
                continue

    out_path = os.path.join(mod_path, _CATALOG_REL)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(
            "# AUTO-GENERATED valid effect/trigger/scope/control-flow keyword "
            "catalog.\n# Union of effects_summary.txt + triggers_summary.txt "
            "names and every LHS keyword\n# vanilla uses in events/ + "
            "scripted_effects + scripted_triggers + on_actions.\n"
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
    # A mod's own top-level names (scripted effects/triggers/on-actions, plus
    # script values — which can be compared by name in a trigger) are valid call
    # targets and definition LHS.
    mod_names: set[str] = set()
    for rel in _SCAN_DIRS + _NAME_ONLY_DIRS:
        mod_names |= _top_level_names(os.path.join(mod_path, rel))
    allowed = valid_keys | mod_names | _CURATED_VALID

    flags: list[Flag] = []
    keys_checked = 0
    files_scanned = 0
    for rel in _SCAN_DIRS:
        base = os.path.join(mod_path, rel)
        if not os.path.isdir(base):
            continue
        for path in _iter_txt(base):
            files_scanned += 1
            try:
                with open(path, encoding="utf-8-sig", errors="replace") as fh:
                    lines = fh.readlines()
            except OSError:
                continue
            for n, raw in enumerate(lines, 1):
                code, comment = _strip_comment(raw)
                code = _strip_quotes(code)
                exemption = parse_reviewed_comment(comment)
                for m in _LHS_RE.finditer(code):
                    kw = m.group(1)
                    keys_checked += 1
                    if kw in allowed:
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
        "Lowercase LHS keywords in `events/`, `common/scripted_effects`, "
        "`common/scripted_triggers`, `common/on_actions` that are neither a "
        "known engine effect/trigger/scope/control-flow keyword (per the frozen "
        "vanilla catalog) nor a mod-defined name — plus `funcname(...)` "
        "call-syntax, which Paradox script never uses. The engine silently "
        "ignores these until a runtime game-load `Unknown effect/trigger` error."
    )
    out.append("")
    out.append(
        f"- Files scanned: **{cov.get('files_scanned', 0)}**, keys checked: "
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
        "path": out_path,
    }


if __name__ == "__main__":
    import sys
    from path_constants import base_game_path, mod_path as _mp

    if len(sys.argv) > 1 and sys.argv[1] == "bootstrap":
        print(bootstrap_catalog(base_game_path, _mp))
    else:
        print(render_report(audit(_mp), _mp))
