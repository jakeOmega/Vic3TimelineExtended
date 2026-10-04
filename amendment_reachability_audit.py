"""Audit for mod amendments no script attaches.

The law panel has no control that adds an amendment. Script attaches one
with `add_amendment = { type = X ... }` on a law scope: an event option, a
journal entry, a scripted effect, the history files. Vanilla's law-enactment
negotiation can also have an interest group sponsor one whose `would_sponsor`
is true for it, but the mod's rule is that every amendment it defines has a
scripted way in, so none depends on that alone. An amendment no script
attaches is dead content or close to it: its modifiers, loc and repeal logic
exist, and few games or none ever see them. The engine logs nothing.

Checks
------
Per amendment the mod defines in `common/amendments/` (a `REPLACE:` or
`INJECT:` of a vanilla amendment is counted, not judged: vanilla's own events
may attach it, and those aren't scanned):

- `unreachable`: no `add_amendment` names it and `would_sponsor` is missing
  or `always = no`, so nothing can attach it.
- `sponsor_only`: no `add_amendment` names it; only an interest group
  sponsoring it in an enactment negotiation can attach it.
- `dead_adds_only`: `add_amendment` sites name it, but every one sits in an
  orphaned event (see `orphaned_event_audit`) or in a scripted effect nothing
  live calls. The detail says whether sponsorship is still possible.
- `unknown_allowed_law`: an `allowed_laws` entry names no law. The amendment
  can't attach to that law; with no valid entry left it can't attach at all.

Per `add_amendment` site anywhere in the mod's `common/` and `events/`:

- `unknown_type`: its `type` names no amendment, mod or vanilla. The effect
  adds nothing and logs nothing.

Add sites inside scripted effects
---------------------------------
A `type = amendment_x_$PARAM$` inside a scripted effect is resolved through
the effect's call sites (`effect = { PARAM = value }`), following a parameter
passed down from another scripted effect up to `_MAX_DEPTH` levels. An add
site in a scripted effect counts only when some call chain reaches it from a
live context: an event that isn't orphaned, or any other file under
`common/` (journal entries, decisions, on-actions, history, buttons, laws).

Suppression
-----------
A check-tagged comment, `# REVIEWED YYYY-MM-DD (amendment_reachability):
rationale`, so it blinds no other audit reading the same line
(`loc_coverage_audit` also reads an amendment's opening line). On the
amendment's opening `<name> = {` line it covers that amendment's
`unreachable`, `sponsor_only`, `dead_adds_only` and `unknown_allowed_law`
flags; on an `allowed_laws` entry's line, that entry's flag. For
`unknown_type`, on the `add_amendment = {` line or its `type =` line. A tag
that suppresses nothing is reported as `stale_review` and fails `--strict`.

Data source
-----------
Mod amendments come from parsing `common/amendments/`. Law and amendment
names are merged vanilla + mod: on a post-load run from the server's
ModState, from the command line from the committed `vanilla_parsed/`
snapshot plus the mod's files, so the audit needs no game install and runs in
CI. Line numbers and comments come from a raw-text scan, because the parser
drops both.
"""
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

from iterator_limit_audit import blank_comments_and_strings

AMENDMENTS_DIR = os.path.join("common", "amendments")
LAWS_DIR = os.path.join("common", "laws")
SCRIPT_ROOTS = ("common", "events")
EFFECTS_PREFIX = "common/scripted_effects/"
REPORT_PATH = os.path.join("docs", "engine", "amendment_reachability_report.md")

CHECK = "amendment_reachability"
KIND_ORDER = (
    "unreachable", "sponsor_only", "dead_adds_only", "unknown_allowed_law", "unknown_type", "stale_review",
)

# How far a `$PARAM$` is followed up a chain of scripted effects.
_MAX_DEPTH = 6

_OPERATORS = ("=", "?=", "<", ">", "<=", ">=", "!=", "==")

_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<check>\w+)\)\s*:\s*(?P<rationale>.+)$"
)
_ADD_RE = re.compile(r"(?<![\w.:$])add_amendment\s*=\s*\{")
_TYPE_RE = re.compile(r"(?<![\w.:$])type\s*=\s*([^\s{}]+)")
_TOP_KEY_RE = re.compile(r"([A-Za-z0-9_.:\-$@]+)\s*=\s*\{")
_PARAM_RE = re.compile(r"\$(\w+)\$")


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m or m.group("check") != CHECK:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _review(sites) -> tuple:
    """(exemption, (file, line)) from the first of `sites` ((file, line,
    comment) triples) carrying this audit's tag, else (None, None)."""
    for file, line, comment in sites:
        rev = _parse_reviewed(comment)
        if rev:
            return rev, (file, line)
    return None, None


def _entity_name(key: str) -> str:
    return key.rsplit(":", 1)[-1]


def _unwrap(v):
    while isinstance(v, tuple) and len(v) == 2 and v[0] in _OPERATORS:
        v = v[1]
    return v


def _names(v) -> list[str]:
    v = _unwrap(v)
    if isinstance(v, str):
        return [v]
    if isinstance(v, dict):
        return list(v)
    if isinstance(v, (list, tuple)):
        out: list[str] = []
        for x in v:
            out += _names(x)
        return out
    return []


def _strip_type(value: str) -> str:
    return value[len("amendment_type:"):] if value.startswith("amendment_type:") else value


# ---------------------------------------------------------------------------
# Script index: every mod script file, its top-level blocks and add sites
# ---------------------------------------------------------------------------


@dataclass
class Block:
    """One top-level `<key> = { ... }` block of a script file."""

    name: str
    start: int
    end: int
    line: int


@dataclass
class ScriptFile:
    rel: str
    raw: str
    _clean: str | None = None
    _comments: dict | None = None
    _starts: list | None = None
    _blocks: list | None = None

    def _prepare(self):
        if self._clean is None:
            self._clean, self._comments = blank_comments_and_strings(self.raw)
            self._starts = [0] + [m.end() for m in re.finditer(r"\n", self._clean)]

    @property
    def clean(self) -> str:
        self._prepare()
        return self._clean

    @property
    def comments(self) -> dict:
        self._prepare()
        return self._comments

    def line_of(self, pos: int) -> int:
        self._prepare()
        return bisect_right(self._starts, pos)

    @property
    def blocks(self) -> list:
        if self._blocks is None:
            self._blocks = _top_blocks(self.clean, self.line_of)
        return self._blocks

    def block_at(self, pos: int) -> Block | None:
        for b in self.blocks:
            if b.start <= pos < b.end:
                return b
        return None

    @property
    def kind(self) -> str:
        if self.rel.startswith("events/"):
            return "event"
        if self.rel.startswith(EFFECTS_PREFIX):
            return "effect"
        return "other"


def _match_brace(text: str, open_pos: int) -> int:
    """Index just past the `}` closing the `{` at `open_pos`."""
    depth = 0
    for i in range(open_pos, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def _top_blocks(clean: str, line_of) -> list:
    blocks: list = []
    depth = 0
    i = 0
    n = len(clean)
    while i < n:
        ch = clean[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        elif depth == 0 and not ch.isspace():
            m = _TOP_KEY_RE.match(clean, i)
            if m:
                open_pos = m.end() - 1
                end = _match_brace(clean, open_pos)
                blocks.append(Block(_entity_name(m.group(1)), m.start(), end, line_of(m.start())))
                i = end
                continue
        i += 1
    return blocks


def load_scripts(mod_path: str) -> list:
    files: list = []
    for root_name in SCRIPT_ROOTS:
        root_dir = os.path.join(mod_path, root_name)
        if not os.path.isdir(root_dir):
            continue
        for root, _dirs, names in os.walk(root_dir):
            for fname in sorted(names):
                if not fname.endswith(".txt"):
                    continue
                abs_p = os.path.join(root, fname)
                rel_p = os.path.relpath(abs_p, mod_path).replace(os.sep, "/")
                try:
                    with open(abs_p, "r", encoding="utf-8-sig", errors="replace") as fh:
                        files.append(ScriptFile(rel_p, fh.read()))
                except OSError:
                    continue
    files.sort(key=lambda f: f.rel)
    return files


@dataclass
class AddSite:
    file: str
    line: int
    raw_type: str
    # Effect the site sits in, when it is inside a scripted effect.
    effect: str | None
    context_kind: str
    context_name: str | None
    # (file, line, comment) for the `add_amendment` line and the `type` line.
    comment_sites: list = field(default_factory=list)


def find_add_sites(files: list) -> list:
    sites: list = []
    for f in files:
        if "add_amendment" not in f.raw:
            continue
        for m in _ADD_RE.finditer(f.clean):
            end = _match_brace(f.clean, m.end() - 1)
            body = f.clean[m.end():end - 1]
            tm = _TYPE_RE.search(body)
            raw_type = tm.group(1) if tm else ""
            line = f.line_of(m.start())
            type_line = f.line_of(m.end() + tm.start()) if tm else line
            block = f.block_at(m.start())
            sites.append(AddSite(
                file=f.rel,
                line=line,
                raw_type=raw_type,
                effect=block.name if (block and f.kind == "effect") else None,
                context_kind=f.kind,
                context_name=block.name if block else None,
                comment_sites=[(f.rel, line, f.comments.get(line)), (f.rel, type_line, f.comments.get(type_line))],
            ))
    return sites


@dataclass
class CallSite:
    file: str
    line: int
    context_kind: str
    context_name: str | None
    args: dict


class CallIndex:
    """Call sites of scripted effects, looked up lazily by name."""

    def __init__(self, files: list):
        self.files = files
        self._cache: dict = {}

    def calls(self, effect: str) -> list:
        if effect in self._cache:
            return self._cache[effect]
        pat = re.compile(r"(?<![\w.:$@])" + re.escape(effect) + r"\s*=\s*")
        out: list = []
        for f in self.files:
            if effect not in f.raw:
                continue
            clean = f.clean
            for m in pat.finditer(clean):
                block = f.block_at(m.start())
                # The effect's own definition, not a call.
                if block is not None and block.start == m.start() and f.kind == "effect":
                    continue
                args: dict = {}
                if m.end() < len(clean) and clean[m.end()] == "{":
                    end = _match_brace(clean, m.end())
                    for am in re.finditer(r"(\w+)\s*=\s*([^\s{}]+)", clean[m.end() + 1:end - 1]):
                        args.setdefault(am.group(1), am.group(2))
                out.append(CallSite(
                    file=f.rel,
                    line=f.line_of(m.start()),
                    context_kind=f.kind,
                    context_name=block.name if block else None,
                    args=args,
                ))
        self._cache[effect] = out
        return out


class Liveness:
    """Whether a context (event, scripted effect, other file) can run."""

    def __init__(self, calls: CallIndex, orphaned_events: set):
        self.calls = calls
        self.orphaned = orphaned_events
        self._effects: dict = {}

    def context(self, kind: str, name: str | None) -> bool:
        if kind == "event":
            return name not in self.orphaned
        if kind == "effect":
            return name is not None and self.effect(name)
        return True

    def effect(self, name: str, _stack: frozenset = frozenset()) -> bool:
        if name in self._effects:
            return self._effects[name]
        if name in _stack:
            return False
        live = False
        for c in self.calls.calls(name):
            if c.context_kind == "effect":
                if c.context_name and self.effect(c.context_name, _stack | {name}):
                    live = True
                    break
            elif self.context(c.context_kind, c.context_name):
                live = True
                break
        if not _stack:
            self._effects[name] = live
        return live


def resolve_site(site: AddSite, calls: CallIndex, live: Liveness) -> list:
    """[(amendment type, live)] an add site can attach."""
    raw = _strip_type(site.raw_type)
    if not raw:
        return []
    if "$" not in raw:
        return [(raw, live.context(site.context_kind, site.context_name))]
    if site.effect is None:
        return []
    return _resolve_param(raw, site.effect, calls, live, 0)


def _resolve_param(value: str, effect: str, calls: CallIndex, live: Liveness, depth: int) -> list:
    if depth > _MAX_DEPTH:
        return []
    out: list = []
    for c in calls.calls(effect):
        resolved = _PARAM_RE.sub(lambda m: c.args.get(m.group(1), m.group(0)), value)
        if "$" not in resolved:
            out.append((_strip_type(resolved), live.context(c.context_kind, c.context_name)))
        elif c.context_kind == "effect" and c.context_name:
            # Still templated: the caller is itself a scripted effect passing
            # one of its own parameters down (`PARAM = $PARAM$`, or none).
            out += _resolve_param(resolved, c.context_name, calls, live, depth + 1)
    return out


# ---------------------------------------------------------------------------
# Amendment definitions in the mod
# ---------------------------------------------------------------------------


@dataclass
class AmendmentSource:
    name: str
    file: str
    line: int
    comment: str | None
    directive: str | None
    body: dict
    # allowed law -> (line, comment)
    allowed_lines: dict = field(default_factory=dict)


def load_mod_amendments(mod_path: str, files: list) -> dict:
    """{name: AmendmentSource} for every amendment block in the mod."""
    from paradox_file_parser import ParadoxFileParser

    by_rel = {f.rel: f for f in files}
    out: dict = {}
    root_dir = os.path.join(mod_path, AMENDMENTS_DIR)
    if not os.path.isdir(root_dir):
        return out
    for fname in sorted(os.listdir(root_dir)):
        if not fname.endswith(".txt"):
            continue
        rel = f"{AMENDMENTS_DIR.replace(os.sep, '/')}/{fname}"
        parser = ParadoxFileParser()
        parser.parse_file(os.path.join(root_dir, fname), apply_directives=False)
        sf = by_rel.get(rel)
        blocks = {b.name: b for b in sf.blocks} if sf else {}
        for key, raw in (parser.data or {}).items():
            name = _entity_name(key)
            body = _unwrap(raw)
            if not isinstance(body, dict):
                continue
            directive = key.split(":", 1)[0] if ":" in key else None
            block = blocks.get(name)
            src = AmendmentSource(
                name=name,
                file=rel,
                line=block.line if block else 0,
                comment=sf.comments.get(block.line) if (sf and block) else None,
                directive=directive,
                body=body,
            )
            if sf and block:
                text = sf.clean[block.start:block.end]
                am = re.search(r"(?<![\w.:])allowed_laws\s*=\s*\{", text)
                if am:
                    end = _match_brace(text, am.end() - 1)
                    for lm in re.finditer(r"[A-Za-z_][\w\-]*", text[am.end():end - 1]):
                        pos = block.start + am.end() + lm.start()
                        ln = sf.line_of(pos)
                        src.allowed_lines.setdefault(lm.group(0), (ln, sf.comments.get(ln)))
            out[name] = src
    return out


def sponsorable(body: dict) -> tuple[bool, str]:
    """(can an interest group ever sponsor it, why not)."""
    if "would_sponsor" not in body:
        return False, "no `would_sponsor`"
    ws = _unwrap(body.get("would_sponsor"))
    if isinstance(ws, dict) and list(ws) == ["always"] and _unwrap(ws["always"]) == "no":
        return False, "`would_sponsor = { always = no }`"
    return True, ""


# ---------------------------------------------------------------------------
# The audit
# ---------------------------------------------------------------------------


@dataclass
class Flag:
    kind: str
    subject: str
    detail: str
    file: str | None = None
    line: int | None = None
    exemption: dict | None = None
    # Where the suppressing comment sits, for the stale-tag check.
    exemption_at: tuple | None = None


@dataclass
class AuditResult:
    flags: list = field(default_factory=list)
    amendments_checked: int = 0
    vanilla_overrides: list = field(default_factory=list)
    add_sites: int = 0
    # Amendments a live `add_amendment` attaches: {name: [file]}.
    by_add: dict = field(default_factory=dict)


def check(mod_amendments: dict, all_amendments: set, all_laws: set,
          sites: list, resolved: list, vanilla_amendments: set, tags: set = frozenset()) -> AuditResult:
    """`tags` holds every (file, line) carrying this audit's REVIEWED tag;
    those that suppress nothing come back as `stale_review` flags."""
    result = AuditResult()
    result.add_sites = len(sites)

    adds: dict = {}
    for site, types in zip(sites, resolved):
        for t, is_live in types:
            adds.setdefault(t, []).append((site, is_live))
        # unknown_type: every type the site resolves to must exist.
        unresolved = not types and site.raw_type
        unknown = [t for t, _ in types if t not in all_amendments]
        if unknown or (unresolved and "$" not in site.raw_type):
            names = unknown or [_strip_type(site.raw_type)]
            flag = Flag(
                "unknown_type",
                f"{site.file}:{site.line}",
                f"`add_amendment` type {', '.join(f'`{n}`' for n in sorted(set(names)))} names no amendment",
                site.file,
                site.line,
            )
            flag.exemption, flag.exemption_at = _review(site.comment_sites)
            result.flags.append(flag)

    for name in sorted(mod_amendments):
        src = mod_amendments[name]
        if name in vanilla_amendments:
            result.vanilla_overrides.append(name)
            continue
        result.amendments_checked += 1
        opener = [(src.file, src.line, src.comment)]

        for law in _names(src.body.get("allowed_laws")):
            if law in all_laws:
                continue
            ln, comment = src.allowed_lines.get(law, (src.line, None))
            flag = Flag("unknown_allowed_law", name, f"`allowed_laws` entry `{law}` names no law", src.file, ln)
            flag.exemption, flag.exemption_at = _review([(src.file, ln, comment)] + opener)
            result.flags.append(flag)

        entries = adds.get(name, [])
        live_entries = [s for s, is_live in entries if is_live]
        if live_entries:
            result.by_add[name] = sorted({s.file for s in live_entries})
            continue
        can_sponsor, why = sponsorable(src.body)
        if entries:
            where = ", ".join(sorted({f"{s.file}:{s.line}" for s, _ in entries}))
            tail = "only sponsorship can attach it" if can_sponsor else f"{why}, so nothing can"
            flag = Flag("dead_adds_only", name,
                        f"every `add_amendment` naming it is unreachable ({where}); {tail}", src.file, src.line)
        elif can_sponsor:
            flag = Flag("sponsor_only", name,
                        "no `add_amendment` names it; only interest-group sponsorship in an"
                        " enactment negotiation attaches it", src.file, src.line)
        else:
            flag = Flag("unreachable", name, f"{why}, and no `add_amendment` names it", src.file, src.line)
        flag.exemption, flag.exemption_at = _review(opener)
        result.flags.append(flag)

    used = {f.exemption_at for f in result.flags if f.exemption_at}
    for file, line in sorted(set(tags) - used):
        result.flags.append(Flag(
            "stale_review", f"{file}:{line}",
            f"`({CHECK})` REVIEWED tag that suppresses nothing; remove it", file, line,
        ))
    return result


def find_tags(files: list) -> set:
    """(file, line) of every comment carrying this audit's REVIEWED tag."""
    out: set = set()
    needle = f"({CHECK})"
    for f in files:
        if needle not in f.raw:
            continue
        for line, comment in f.comments.items():
            if _parse_reviewed(comment):
                out.add((f.rel, line))
    return out


def _orphaned_events(mod_path: str) -> set:
    import orphaned_event_audit

    res = orphaned_event_audit.audit(mod_path)
    # A reviewed orphan was judged dispatched some way the scan can't see.
    return {f.event_id for f in res.flags if not f.exemption}


def _snapshot_names(mod_path: str, entity_type: str) -> set:
    import json

    import vanilla_parsed

    snap_dir = os.path.join(mod_path, "vanilla_parsed")
    manifest = vanilla_parsed.read_manifest(snap_dir) or {}
    info = manifest.get("entity_types", {}).get(entity_type)
    if not info:
        return set()
    with open(os.path.join(snap_dir, info["file"]), "r", encoding="utf-8") as fh:
        return set(vanilla_parsed.decode(json.load(fh)))


def _mod_entity_names(mod_path: str, rel_dir: str) -> set:
    from paradox_file_parser import ParadoxFileParser

    out: set = set()
    root_dir = os.path.join(mod_path, rel_dir)
    if not os.path.isdir(root_dir):
        return out
    for fname in sorted(os.listdir(root_dir)):
        if fname.endswith(".txt"):
            parser = ParadoxFileParser()
            parser.parse_file(os.path.join(root_dir, fname), apply_directives=False)
            out |= {_entity_name(k) for k in (parser.data or {})}
    return out


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    files = load_scripts(mod_path)
    mod_amendments = load_mod_amendments(mod_path, files)
    vanilla_amendments = _snapshot_names(mod_path, "Amendments")
    if mod_state is not None:
        all_amendments = set(mod_state.get_data("Amendments") or {})
        all_laws = set(mod_state.get_data("Laws") or {})
    else:
        all_amendments = vanilla_amendments | set(mod_amendments)
        all_laws = _snapshot_names(mod_path, "Laws") | _mod_entity_names(mod_path, LAWS_DIR)
    all_amendments |= set(mod_amendments)

    sites = find_add_sites(files)
    calls = CallIndex(files)
    live = Liveness(calls, _orphaned_events(mod_path))
    resolved = [resolve_site(s, calls, live) for s in sites]
    return check(mod_amendments, all_amendments, all_laws, sites, resolved, vanilla_amendments, find_tags(files))


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Amendment reachability audit report",
        "",
        "Auto-generated by `amendment_reachability_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "No control in the law panel adds an amendment. Script attaches one with",
        "`add_amendment`; vanilla's enactment negotiation can also have an",
        "interest group sponsor one whose `would_sponsor` is true. The mod's rule",
        "is that every amendment it defines has a scripted way in. The engine",
        "logs nothing for one that has none.",
        "",
        "Flagged: `unreachable` (no `add_amendment` names it and no group can",
        "sponsor it), `sponsor_only` (no `add_amendment` names it; only",
        "sponsorship attaches it), `dead_adds_only` (every `add_amendment` naming",
        "it sits in an orphaned event or an uncalled scripted effect),",
        "`unknown_allowed_law` (an `allowed_laws` entry names no law) and",
        "`unknown_type` (an `add_amendment` whose type names no amendment).",
        "",
        "Suppress a deliberate case with a check-tagged comment,",
        "`# REVIEWED YYYY-MM-DD (amendment_reachability): rationale`, on the",
        "amendment's opening `<name> = {` line (or the `allowed_laws` entry's",
        "line), or for `unknown_type` on the `add_amendment = {` or `type =`",
        "line. A tag that suppresses nothing is flagged `stale_review`.",
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
            out += [f"### {kind}", ""]
            for f in rows:
                where = f" ({f.file}:{f.line})" if f.file and f.kind not in ("unknown_type", "stale_review") else ""
                out.append(f"- `{f.subject}`: {f.detail}{where}")
            out.append("")

    out += ["## Reviewed Exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        for f in exemp:
            out.append(
                f"- {f.kind}: `{f.subject}`: {f.detail} — **{f.exemption['date']}**: "
                f"{f.exemption['rationale']}"
            )
        out.append("")

    out += [
        "## Coverage",
        "",
        f"- mod amendments checked: {result.amendments_checked}",
        f"- attached by a live `add_amendment`: {len(result.by_add)}",
        f"- `REPLACE:`/`INJECT:` of vanilla amendments, not judged: {len(result.vanilla_overrides)}",
        f"- `add_amendment` sites scanned: {result.add_sites}",
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
        "amendments_checked": result.amendments_checked,
        "add_sites": result.add_sites,
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
    # --strict: CI mode. Exit 1 if any flag lacks a `# REVIEWED ... (amendment_reachability)`
    # exemption, including a stale tag.
    if "--strict" in sys.argv:
        raise SystemExit(1 if any(not f.exemption for f in result.flags) else 0)
