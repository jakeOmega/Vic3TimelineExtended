"""Audit for ideology law-group blocks that leave laws out.

An ideology states its stance on laws group by group:

    lawgroup_army_model = {
        law_professional_army = approve
        law_private_military_contractors = disapprove
    }

A law the block doesn't name is implicitly `neutral`, unless it is a variant
(a law with `parent = law_x`, such as Warrior Caste under Peasant Levies),
which takes its parent's stance. Neutral is not harmless: a group whose current law it disapproves of will back enacting any
neutral law in the group. Writing every stance out makes the choice visible
and a slip easy to spot, so the mod's rule is that a block names every law in
its group.

Checks
------
Per lawgroup block of every ideology, on merged vanilla + mod data:

- `missing_law`: the block leaves out a law of its group. Variants don't
  count: they follow their parent. Which laws a block must name depends on
  who wrote it:
  - an ideology the mod defines, or a block the mod adds to a vanilla
    ideology: every law in the group;
  - a block vanilla's ideology already had: only the laws the mod adds to the
    group. Vanilla's own omissions are vanilla's design, so injecting just the
    new laws is enough.
- `unknown_lawgroup`: the block's key names no law group.
- `unknown_law`: a stance names no law.
- `wrong_group`: a stance names a law of another group, which the engine
  ignores there.
- `bad_stance`: a value other than `strongly_approve`, `approve`, `neutral`,
  `disapprove` or `strongly_disapprove`.
- `variant_stance`: a stance on a variant law. Vanilla never writes one, and
  whether it overrides the inherited stance or is ignored is unread in game.

The last five are judged only on ideologies the mod defines or touches;
untouched vanilla ideologies are judged for `missing_law` alone. Carrier laws
(`gen_law_consistency.CARRIER_LAW_DENYLIST`: script attaches them, nothing
enacts them) never count as missing.

Suppression
-----------
A check-tagged comment ("explicitly noted"),
`# REVIEWED YYYY-MM-DD (ideology_lawgroup): rationale`, so it blinds no other
audit reading the same line (`loc_coverage_audit` reads an ideology's opening
line):

- in a hand-written `common/ideologies/*.txt` file, on the block's opening
  `lawgroup_x = {` line, or on the ideology's opening `<name> = {` line
  (covers every block);
- for `common/ideologies/modified.txt`, which `apply_ideologies.py`
  generates, on the group's `"lawgroup_x": ...` line in that ideology's
  entry of `ideology_modifications.py`, or on the ideology's
  `"ideology_x": {` line.

A tag that suppresses nothing is reported as `stale_review` and fails
`--strict`.

Data source
-----------
Ideologies and laws are merged vanilla + mod: on a post-load run the server's
ModState, from the command line a small ModState built on the committed
`vanilla_parsed/` snapshot, so the audit needs no game install and runs in
CI. Which blocks vanilla had comes from the snapshot. Line numbers and
comments come from a raw-text scan, because the parser drops both.
"""
import os
import re
from dataclasses import dataclass, field

from iterator_limit_audit import blank_comments_and_strings

ENTITY_TYPES = {
    "Ideologies": "ideologies",
    "Laws": "laws",
}

IDEOLOGIES_DIR = os.path.join("common", "ideologies")
GENERATED_FILE = "common/ideologies/modified.txt"
MODIFICATIONS_FILE = "ideology_modifications.py"
REPORT_PATH = os.path.join("docs", "engine", "ideology_lawgroup_report.md")

CHECK = "ideology_lawgroup"
KIND_ORDER = (
    "missing_law", "unknown_lawgroup", "unknown_law", "wrong_group", "bad_stance", "variant_stance", "stale_review",
)
STANCES = ("strongly_approve", "approve", "neutral", "disapprove", "strongly_disapprove")

_OPERATORS = ("=", "?=", "<", ">", "<=", ">=", "!=", "==")
_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<check>\w+)\)\s*:\s*(?P<rationale>.+)$"
)
_OPEN_RE = re.compile(r"^[ \t]*([A-Za-z0-9_.:\-]+)\s*=\s*\{")


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m or m.group("check") != CHECK:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _entity_name(key: str) -> str:
    return key.rsplit(":", 1)[-1]


def _unwrap(v):
    while isinstance(v, tuple) and len(v) == 2 and v[0] in _OPERATORS:
        v = v[1]
    return v


# ---------------------------------------------------------------------------
# Source scan: where the mod writes each ideology and lawgroup block
# ---------------------------------------------------------------------------


@dataclass
class Source:
    """Where the mod writes one ideology. Sites are (file, line, comment)."""

    openers: list = field(default_factory=list)
    # lawgroup -> [site]
    blocks: dict = field(default_factory=dict)
    generated: bool = False


def scan_text(text: str, rel_path: str, sources: dict | None = None) -> dict:
    """Record every ideology opener and depth-1 block opener in one
    `common/ideologies/` file into `sources` ({name: Source})."""
    if sources is None:
        sources = {}
    clean, comments = blank_comments_and_strings(text)
    depth = 0
    current: Source | None = None
    for lineno, line in enumerate(clean.split("\n"), start=1):
        m = _OPEN_RE.match(line)
        if m and depth == 0:
            current = sources.setdefault(_entity_name(m.group(1)), Source())
            current.openers.append((rel_path, lineno, comments.get(lineno)))
            current.generated = current.generated or rel_path == GENERATED_FILE
        elif m and depth == 1 and current is not None:
            current.blocks.setdefault(m.group(1), []).append(
                (rel_path, lineno, comments.get(lineno))
            )
        depth += line.count("{") - line.count("}")
        depth = max(depth, 0)
    return sources


def scan_modifications(text: str) -> dict:
    """{ideology: Source} for the `modifications` dict of
    ideology_modifications.py: the ideology's `"ideology_x": {` line and each
    `"lawgroup_x": ...` line inside it, with trailing comments."""
    out: dict = {}
    lines = text.split("\n")
    start = next((i for i, ln in enumerate(lines) if re.match(r"^modifications\s*=\s*\{", ln)), None)
    if start is None:
        return out
    current: Source | None = None
    for i in range(start + 1, len(lines)):
        ln = lines[i]
        if ln.startswith("}"):
            break
        m = re.match(r'^    "(\w+)"\s*:\s*\{', ln)
        if m:
            current = out.setdefault(m.group(1), Source())
            current.openers.append((MODIFICATIONS_FILE, i + 1, _py_comment(ln)))
            continue
        m = re.match(r'^        "(\w+)"\s*:', ln)
        if m and current is not None:
            current.blocks.setdefault(m.group(1), []).append(
                (MODIFICATIONS_FILE, i + 1, _py_comment(ln))
            )
    return out


def _py_comment(line: str) -> str | None:
    # Good enough for the dict's lines: no `#` inside their strings.
    pos = line.find("#")
    return line[pos:] if pos >= 0 else None


def scan_sources(mod_path: str) -> tuple[dict, dict, set]:
    """(sources from common/ideologies/*.txt, sources from
    ideology_modifications.py, (file, line) of every comment in either that
    carries this audit's REVIEWED tag)."""
    sources: dict = {}
    tags: set = set()
    root_dir = os.path.join(mod_path, IDEOLOGIES_DIR)
    if os.path.isdir(root_dir):
        for fname in sorted(os.listdir(root_dir)):
            if not fname.endswith(".txt"):
                continue
            rel = f"{IDEOLOGIES_DIR.replace(os.sep, '/')}/{fname}"
            with open(os.path.join(root_dir, fname), "r", encoding="utf-8-sig", errors="replace") as fh:
                text = fh.read()
            scan_text(text, rel, sources)
            if f"({CHECK})" in text:
                _clean, comments = blank_comments_and_strings(text)
                tags |= {(rel, line) for line, c in comments.items() if _parse_reviewed(c)}
    mods: dict = {}
    mod_file = os.path.join(mod_path, MODIFICATIONS_FILE)
    if os.path.isfile(mod_file):
        with open(mod_file, "r", encoding="utf-8-sig") as fh:
            text = fh.read()
        mods = scan_modifications(text)
        for i, line in enumerate(text.split("\n"), start=1):
            if _parse_reviewed(_py_comment(line)):
                tags.add((MODIFICATIONS_FILE, i))
    return sources, mods, tags


# ---------------------------------------------------------------------------
# The audit
# ---------------------------------------------------------------------------


@dataclass
class Flag:
    kind: str
    ideology: str
    lawgroup: str
    laws: list
    detail: str
    file: str | None = None
    line: int | None = None
    exemption: dict | None = None
    # Where the suppressing comment sits, for the stale-tag check.
    exemption_at: tuple | None = None


@dataclass
class AuditResult:
    flags: list = field(default_factory=list)
    ideologies_checked: int = 0
    blocks_checked: int = 0
    # Vanilla blocks leaving out vanilla laws: vanilla's design, counted only.
    vanilla_gaps: int = 0


def law_groups(laws: dict) -> dict:
    """{law: group}."""
    out: dict = {}
    for name, raw in laws.items():
        body = _unwrap(raw)
        if isinstance(body, dict):
            g = _unwrap(body.get("group"))
            if isinstance(g, str):
                out[name] = g
    return out


def law_parents(laws: dict) -> dict:
    """{variant law: parent law} for every law with `parent = law_x`."""
    out: dict = {}
    for name, raw in laws.items():
        body = _unwrap(raw)
        if isinstance(body, dict):
            p = _unwrap(body.get("parent"))
            if isinstance(p, str) and p.startswith("law_"):
                out[name] = p
    return out


def _sites(src_txt: Source | None, src_py: Source | None, lawgroup: str) -> list:
    """Candidate (file, line, comment) sites for a block, most specific
    first: the block line in a hand-written file or the modifications dict,
    then the ideology opener."""
    out: list = []
    if src_txt is not None:
        out += [s for s in src_txt.blocks.get(lawgroup, []) if s[0] != GENERATED_FILE]
    if src_py is not None:
        out += src_py.blocks.get(lawgroup, [])
    if src_txt is not None:
        out += [s for s in src_txt.openers if s[0] != GENERATED_FILE]
    if src_py is not None:
        out += src_py.openers
    return out


def check(ideologies: dict, laws: dict, vanilla_ideologies: dict, vanilla_laws: set,
          sources: dict, mods: dict, carriers: set = frozenset(), tags: set = frozenset()) -> AuditResult:
    """`tags` holds every (file, line) carrying this audit's REVIEWED tag;
    those that suppress nothing come back as `stale_review` flags."""
    result = AuditResult()
    group_of = law_groups(laws)
    parent_of = law_parents(laws)
    members: dict = {}
    groups: set = set(group_of.values())
    for law, g in group_of.items():
        if law not in carriers and law not in parent_of:
            members.setdefault(g, set()).add(law)

    for name in sorted(ideologies):
        body = _unwrap(ideologies[name])
        if not isinstance(body, dict):
            continue
        vbody = _unwrap(vanilla_ideologies.get(name)) if name in vanilla_ideologies else None
        vbody = vbody if isinstance(vbody, dict) else None
        src_txt = sources.get(name)
        src_py = mods.get(name)
        touched = vbody is None or src_txt is not None or src_py is not None
        if touched:
            result.ideologies_checked += 1

        for key, raw in body.items():
            if not key.startswith("lawgroup_"):
                continue
            block = _unwrap(raw)
            stances = block if isinstance(block, dict) else {}
            in_vanilla = vbody is not None and key in vbody
            result.blocks_checked += 1
            sites = _sites(src_txt, src_py, key)

            def flag(kind, laws_, detail):
                f = Flag(kind, name, key, laws_, detail)
                for s in sites:
                    f.file, f.line = s[0], s[1]
                    break
                for s in sites:
                    rev = _parse_reviewed(s[2])
                    if rev:
                        f.exemption, f.exemption_at = rev, (s[0], s[1])
                        break
                result.flags.append(f)

            if key not in groups and touched:
                flag("unknown_lawgroup", [], f"`{key}` names no law group")
                continue

            if touched:
                for law, v in stances.items():
                    g = group_of.get(law)
                    if g is None:
                        flag("unknown_law", [law], f"`{law}` names no law")
                    elif g != key:
                        flag("wrong_group", [law], f"`{law}` belongs to `{g}`")
                    stance = _unwrap(v)
                    if isinstance(stance, list):
                        stance = stance[-1] if stance else None
                        stance = _unwrap(stance)
                    if stance not in STANCES:
                        flag("bad_stance", [law], f"`{law} = {stance}` is not a stance")
                    if law in parent_of:
                        flag("variant_stance", [law],
                             f"`{law}` is a variant of `{parent_of[law]}` and takes its stance")

            required = set(members.get(key, ()))
            if in_vanilla:
                gaps = {law for law in required if law in vanilla_laws and law not in stances}
                result.vanilla_gaps += len(gaps)
                required = {law for law in required if law not in vanilla_laws}
                why = "laws the mod adds to this vanilla block's group"
            elif vbody is None:
                why = "the mod's ideology must name every law in the group"
            else:
                why = "the mod added this block to a vanilla ideology, so it must name every law in the group"
            missing = sorted(required - set(stances))
            if missing:
                flag("missing_law", missing,
                     f"leaves out {', '.join(f'`{law}`' for law in missing)} ({why})")

    used = {f.exemption_at for f in result.flags if f.exemption_at}
    for file, line in sorted(set(tags) - used):
        result.flags.append(Flag(
            "stale_review", "", "", [],
            f"`({CHECK})` REVIEWED tag that suppresses nothing; remove it", file, line,
        ))
    return result


def load_state(mod_path: str, vanilla_data: dict | None = None):
    from mod_state import ModState

    if vanilla_data is None:
        vanilla_data = load_vanilla(mod_path)
    base = {et: "" for et in ENTITY_TYPES}
    mod = {et: os.path.join(mod_path, "common", d) for et, d in ENTITY_TYPES.items()}
    return ModState(base, mod, vanilla_data=vanilla_data)


def load_vanilla(mod_path: str) -> dict:
    import json

    import vanilla_parsed

    snap_dir = os.path.join(mod_path, "vanilla_parsed")
    manifest = vanilla_parsed.read_manifest(snap_dir) or {}
    out: dict = {}
    for et in ENTITY_TYPES:
        info = manifest.get("entity_types", {}).get(et)
        if not info:
            continue
        with open(os.path.join(snap_dir, info["file"]), "r", encoding="utf-8") as fh:
            out[et] = vanilla_parsed.decode(json.load(fh))
    return out


def carrier_laws(mod_path: str) -> set:
    """gen_law_consistency.CARRIER_LAW_DENYLIST, read with `ast`: importing
    the generator resolves the game install path, which this audit doesn't
    need."""
    import ast

    path = os.path.join(mod_path, "gen_law_consistency.py")
    if not os.path.isfile(path):
        return set()
    with open(path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "CARRIER_LAW_DENYLIST" for t in node.targets
        ):
            return set(ast.literal_eval(node.value))
    return set()


def audit(mod_state=None, mod_path: str | None = None, vanilla_data: dict | None = None) -> AuditResult:
    """`vanilla_data` ({"Ideologies": ..., "Laws": ...}) replaces the
    committed snapshot, for tests."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    vanilla = vanilla_data if vanilla_data is not None else load_vanilla(mod_path)
    if mod_state is None:
        mod_state = load_state(mod_path, vanilla)
    sources, mods, tags = scan_sources(mod_path)
    return check(
        mod_state.get_data("Ideologies") or {},
        mod_state.get_data("Laws") or {},
        vanilla.get("Ideologies") or {},
        set(vanilla.get("Laws") or {}),
        sources,
        mods,
        carrier_laws(mod_path),
        tags,
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]
    out = [
        "# Ideology law-group audit report",
        "",
        "Auto-generated by `ideology_lawgroup_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "A law an ideology's lawgroup block leaves out is implicitly `neutral`,",
        "so a group that disapproves of the current law backs enacting it. The",
        "mod's rule is that a block names every law in its group. An ideology",
        "the mod defines, and a block the mod adds to a vanilla ideology, must",
        "name every law; a block vanilla already had must name the laws the mod",
        "adds to the group.",
        "",
        "Variant laws (`parent = law_x`) take their parent's stance and are",
        "never required.",
        "",
        "Flagged: `missing_law`, `unknown_lawgroup` (the key names no law",
        "group), `unknown_law`, `wrong_group` (the law belongs to another",
        "group), `bad_stance` and `variant_stance` (a stance on a variant law,",
        "whose effect is unread in game).",
        "",
        "Suppress a deliberate omission with a check-tagged comment,",
        "`# REVIEWED YYYY-MM-DD (ideology_lawgroup): rationale`, on the block's",
        "opening line in a hand-written `common/ideologies/` file, or for the",
        "generated `modified.txt` on the group's line in",
        "`ideology_modifications.py`; on the ideology's opening line it covers",
        "every block. A tag that suppresses nothing is flagged `stale_review`.",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out += ["_None._", ""]
    else:
        for kind in KIND_ORDER:
            rows = [f for f in unrev if f.kind == kind]
            if not rows:
                continue
            out += [f"### {kind} ({len(rows)})", ""]
            for f in rows:
                where = f" ({f.file}:{f.line})" if f.file else " (vanilla ideology the mod doesn't touch)"
                if f.kind == "stale_review":
                    out.append(f"- {f.file}:{f.line}: {f.detail}")
                    continue
                out.append(f"- `{f.ideology}` `{f.lawgroup}`: {f.detail}{where}")
            out.append("")

    out += ["## Reviewed Exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        for f in exemp:
            out.append(
                f"- {f.kind}: `{f.ideology}` `{f.lawgroup}`: {f.detail} — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    out += [
        "## Coverage",
        "",
        f"- mod-defined or mod-touched ideologies checked: {result.ideologies_checked}",
        f"- lawgroup blocks checked (all ideologies): {result.blocks_checked}",
        f"- vanilla laws vanilla blocks leave out, not judged: {result.vanilla_gaps}",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {len(unrev)}",
        f"- exempted: {len(exemp)}",
        "",
    ]
    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    out_path = os.path.join(mod_path, REPORT_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    unrev = sum(1 for f in result.flags if not f.exemption)
    return {
        "ideologies_checked": result.ideologies_checked,
        "blocks_checked": result.blocks_checked,
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": len(result.flags) - unrev,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    result = audit(mod_path=mod_path)
    print(render_report(result))
    # --strict: CI mode. Exit 1 if any flag lacks a `# REVIEWED ... (ideology_lawgroup)`
    # exemption, including a stale tag.
    if "--strict" in sys.argv:
        raise SystemExit(1 if any(not f.exemption for f in result.flags) else 0)
