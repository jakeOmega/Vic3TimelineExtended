"""Flag a `custom_tooltip` that hides the modifier lines of an `add_modifier` it wraps (#1213).

`custom_tooltip = { text = X <effects> }` prints X in place of its effects'
own tooltip lines. When an effect inside is an `add_modifier`, the engine's
coloured, bulleted modifier lines are gone, and the player reads only what X
says, which drifts the moment the modifier is tuned: the UN programme
buttons' hand-typed effect lists had already drifted from their modifiers.
The rule (`scripting_best_practices.md`, "Render Static Modifier Effects in
Loc via `[GetStaticModifier('X').GetDesc]`") is to put
`[GetStaticModifier('…').GetDesc]` in X, as the climate policies do, or to
leave the `add_modifier` outside the `custom_tooltip` so the engine prints it
(`civil_rights_buttons.txt`). The GUI and localization audit (#1202, finding
4) counted 22 such blocks by hand, 12 of which rendered no modifier line.

What is checked
---------------
Every `custom_tooltip = { … }` and `custom_description = { … }` block in
`common/**/*.txt` and `events/**/*.txt` (comments aside) that holds an
`add_modifier`, at any depth inside it (an `if`, a scope change). For each
`add_modifier`, the modifier is hidden unless X's loc renders
`GetStaticModifier('<that modifier>')`. X's text is read from the mod's
English loc, then vanilla's (`vanilla_parsed/`), following `$key$` splices
and the keys a `Localize` / `SelectLocalization` inside it names.

Not flagged:

- a modifier with no line to print: a static modifier whose definition holds
  nothing but its `icon` (a cooldown or marker, `un_peacekeeping_cooldown`),
  read from the mod's `common/static_modifiers/` and vanilla's snapshot;
- a block inside a `hidden_effect`, which prints nothing either way;
- a block whose `text` is a `$PARAM$` (counted as `dynamic_skipped`): the
  text depends on the caller. A modifier name from a `$PARAM$` is hidden
  unless X renders some `GetStaticModifier`;
- `te_debug_*` files, the console-only harness.

Blind spot: only an `add_modifier` written in the block counts, not one a
scripted effect called from it adds. Followed through scripted effects, the
scan finds about 65 more blocks, nearly all of them refreshes (`remove` then
re-`add` with a new multiplier), cleanups and cooldown marks, where printing
the lines would mislead more than hiding them.

Suppression is check-tagged, on the block's opening line:

    custom_tooltip = { # REVIEWED 2026-10-27 (hidden_modifier): rationale

A tag on a line that opens no flagged block is stale and fails `--strict`.

Report: docs/engine/hidden_modifier_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from gui_reference_audit import LEX, blocks, masks
from long_tooltip_audit import loc_call_keys
from mod_state import split_loc_line

CHECK = "hidden_modifier"
SCAN_DIRS = ("common", "events")
SKIP_PREFIX = "te_debug_"
LOC_DIR = os.path.join("localization", "english")
STATIC_MODIFIER_DIR = os.path.join("common", "static_modifiers")
VANILLA_LOC = os.path.join("vanilla_parsed", "localization_english.json")
VANILLA_MODIFIERS = os.path.join("vanilla_parsed", "common", "modifiers.json")
REPORT_PATH = os.path.join("docs", "engine", "hidden_modifier_report.md")

_OPEN = re.compile(r"\b(custom_tooltip|custom_description)\s*=\s*\{")
_HIDDEN = re.compile(r"\bhidden_effect\s*=\s*\{")
_ADD = re.compile(r"\badd_modifier\s*=\s*(\{|\"?[\w$.:\-]+\"?)")
_TEXT = re.compile(r"[{}]|\btext\s*=\s*(\"[^\"\n]*\"|[^\s{}]+)")
_GSM = re.compile(r"GetStaticModifier\(\s*(?:'([^']+)')?")
_SPLICE = re.compile(r"\$([\w.\-]+)(?:\|[^$]*)?\$")
_FIELD = re.compile(r"(?<![\w.:@$])([A-Za-z_][\w.:]*)\s*=")
_TAGGED_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$"
)


@dataclass
class Hidden:
    modifier: str
    line: int


@dataclass
class Flag:
    file: str
    line: int
    text_key: str
    hidden: list[Hidden]
    exemption: dict | None = None


@dataclass
class StaleTag:
    file: str
    line: int


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    stale_tags: list[StaleTag] = field(default_factory=list)
    files_scanned: int = 0
    blocks_checked: int = 0
    rendered_ok: int = 0
    dynamic_skipped: int = 0
    lineless_skipped: int = 0

    @property
    def failing(self) -> int:
        return sum(1 for f in self.flags if not f.exemption) + len(self.stale_tags)


def _parse_tag(comment: str) -> dict | None:
    if "REVIEWED" not in comment:
        return None
    m = _TAGGED_REVIEWED_RE.search(comment)
    if not m or CHECK not in re.split(r"[\s,]+", m.group("checks").strip()):
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _match(syntax: str, brace: int) -> int:
    """Index of the `}` closing the `{` at `brace` (syntax mask: no strings
    or comments to fool the count)."""
    depth = 0
    for i in range(brace, len(syntax)):
        c = syntax[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(syntax)


def load_loc(root: Path) -> dict[str, str]:
    """Mod English loc over vanilla's: the text a key renders."""
    path = root / VANILLA_LOC
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} is missing; rebuild it with `python3 vanilla_parsed.py build` "
            "on a machine with the game"
        )
    loc = {k: v for k, v in json.loads(path.read_text(encoding="utf-8")).items() if isinstance(v, str)}
    loc_dir = root / LOC_DIR
    files = sorted(loc_dir.rglob("*.yml"), key=lambda p: (p.parent.name == "replace", p.name))
    if not files:
        raise FileNotFoundError(f"no loc file under {loc_dir}")
    for p in files:
        for raw in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            parsed = split_loc_line(raw)
            if parsed:
                loc[parsed[0]] = parsed[1]
    return loc


def lineless_modifiers(root: Path) -> set[str]:
    """Static modifiers with nothing to print: no field but `icon`, in the mod
    (a name's INJECT/REPLACE copies pooled) and in vanilla's snapshot, where
    the mod doesn't define it."""
    fields: dict[str, set[str]] = {}
    for path in sorted((root / STATIC_MODIFIER_DIR).rglob("*.txt")):
        syntax = masks(path.read_text(encoding="utf-8-sig", errors="replace"))[1]
        for name, _op, start, end in blocks(syntax):
            name = name.split(":")[-1]
            fields.setdefault(name, set()).update(
                k for k in _FIELD.findall(syntax[start:end]) if k != "icon")
    vpath = root / VANILLA_MODIFIERS
    if vpath.is_file():
        for name, entry in json.loads(vpath.read_text(encoding="utf-8")).items():
            if name in fields:
                continue
            body = entry[1] if isinstance(entry, list) and len(entry) == 2 else entry
            keys = set(body) if isinstance(body, dict) else set()
            fields[name] = keys - {"icon"}
    return {name for name, keys in fields.items() if not keys}


def rendered_modifiers(key: str, loc: dict[str, str]) -> tuple[set[str], bool]:
    """(the static modifiers X's text renders by name, whether it renders one
    whose name is built at run time), following splices and Localize keys."""
    names: set[str] = set()
    dynamic = False
    seen: set[str] = set()
    todo = [key]
    while todo:
        k = todo.pop()
        if k in seen or k not in loc:
            continue
        seen.add(k)
        value = loc[k]
        for m in _GSM.finditer(value):
            if m.group(1):
                names.add(m.group(1))
            else:
                dynamic = True
        todo += _SPLICE.findall(value)
        todo += loc_call_keys(value)
    return names, dynamic


def _text_key(body_code: str) -> str | None:
    """The block's own `text = X` (at its top level, not in a nested block)."""
    depth = 0
    for m in _TEXT.finditer(body_code):
        tok = m[0]
        if tok == "{":
            depth += 1
        elif tok == "}":
            depth -= 1
        elif depth == 0:
            return m.group(1).strip('"')
    return None


def _modifier_calls(code: str, syntax: str, start: int, end: int):
    """(name, offset) for each `add_modifier` in the span. Matched in `code`
    (comments gone, strings kept, so a quoted scalar name is readable) and
    skipped where `syntax` shows the match sits inside a string."""
    pos = start
    while m := _ADD.search(code, pos, end):
        if syntax[m.start()] != "a":
            pos = m.end()
            continue
        if m.group(1) == "{":
            close = _match(syntax, m.end() - 1)
            inner, inner_syntax = code[m.end():close], syntax[m.end():close]
            depth, name = 0, None
            for tok in re.finditer(r"[{}]|\bname\s*=\s*\"?([\w$.:\-]+)\"?", inner):
                if inner_syntax[tok.start()] not in "{}n":
                    continue
                if tok[0] == "{":
                    depth += 1
                elif tok[0] == "}":
                    depth -= 1
                elif depth == 0 and name is None:
                    name = tok.group(1)
            if name:
                yield name, m.start()
            pos = close
        else:
            yield m.group(1).strip('"'), m.start()
            pos = m.end()


def _audit_file(root: Path, path: Path, loc, lineless, result: AuditResult) -> None:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    has_tag = CHECK in text
    if "custom_tooltip" not in text and "custom_description" not in text and not has_tag:
        return
    rel = path.relative_to(root).as_posix()
    code, syntax = masks(text)

    def line(offset: int) -> int:
        return text.count("\n", 0, offset) + 1

    tags: dict[int, dict] = {}
    if has_tag:
        for tok in LEX.finditer(text):
            if tok[0].startswith("#"):
                tag = _parse_tag(tok[0])
                if tag:
                    tags[line(tok.start())] = tag
    hidden_spans = [(m.end() - 1, _match(syntax, m.end() - 1)) for m in _HIDDEN.finditer(syntax)]
    flagged_lines: set[int] = set()
    for m in _OPEN.finditer(syntax):
        brace = m.end() - 1
        close = _match(syntax, brace)
        if "add_modifier" not in syntax[brace:close]:
            continue
        if any(a < m.start() < b for a, b in hidden_spans):
            continue
        result.blocks_checked += 1
        key = _text_key(code[brace + 1:close])
        if key is None or "$" in key:
            result.dynamic_skipped += 1
            continue
        names, dynamic = rendered_modifiers(key, loc)
        hidden: list[Hidden] = []
        for name, offset in _modifier_calls(code, syntax, brace + 1, close):
            if "$" in name:
                if names or dynamic:
                    continue
            elif name in names or dynamic:
                continue
            elif name in lineless:
                result.lineless_skipped += 1
                continue
            hidden.append(Hidden(name, line(offset)))
        if not hidden:
            result.rendered_ok += 1
            continue
        opener = line(m.start())
        flagged_lines.add(opener)
        result.flags.append(Flag(rel, opener, key, hidden, exemption=tags.get(opener)))
    for tag_line in sorted(tags):
        if tag_line not in flagged_lines:
            result.stale_tags.append(StaleTag(rel, tag_line))


def audit(mod_path: str | Path | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    root = Path(mod_path)
    loc = load_loc(root)
    lineless = lineless_modifiers(root)
    result = AuditResult()
    for folder in SCAN_DIRS:
        for path in sorted((root / folder).rglob("*.txt")):
            if path.name.startswith(SKIP_PREFIX):
                continue
            result.files_scanned += 1
            _audit_file(root, path, loc, lineless, result)
    if not result.files_scanned:
        raise FileNotFoundError(f"no .txt file to scan under {root / 'common'} or {root / 'events'}")
    return result


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]
    out = [
        "# Hidden modifier audit report",
        "",
        "Auto-generated by `hidden_modifier_audit.py` on every `POST /reload` of the",
        "mod state server. Do not hand-edit.",
        "",
        "Flagged: a `custom_tooltip = { text = X … }` (or `custom_description`)",
        "that wraps an `add_modifier` while X's loc renders no",
        "`GetStaticModifier('<that modifier>')`. The engine prints only X, so the",
        "modifier's own coloured lines never show. Put",
        "`[GetStaticModifier('<name>').GetDesc]` in X, or move the `add_modifier`",
        "out of the `custom_tooltip` (`scripting_best_practices.md`, \"Render Static",
        "Modifier Effects in Loc\").",
        "",
        "Suppress a deliberate case on the block's opening line:",
        "`# REVIEWED YYYY-MM-DD (hidden_modifier): why`",
        "",
        "## Unreviewed flags",
        "",
    ]
    if not unrev:
        out += ["_None._", ""]
    else:
        by_file: dict[str, list[Flag]] = {}
        for f in unrev:
            by_file.setdefault(f.file, []).append(f)
        for fname in sorted(by_file):
            out += [f"### `{fname}` ({len(by_file[fname])})", ""]
            for f in by_file[fname]:
                mods = ", ".join(f"`{h.modifier}` (line {h.line})" for h in f.hidden)
                out.append(f"- line {f.line}: `{f.text_key}` hides {mods}")
            out.append("")
    if result.stale_tags:
        out += ["## Stale tags", "", "Tags that suppress nothing; remove them.", ""]
        out += [f"- `{t.file}:{t.line}` ({CHECK})" for t in result.stale_tags]
        out.append("")
    out += ["## Reviewed exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        for f in exemp:
            mods = ", ".join(f"`{h.modifier}`" for h in f.hidden)
            out.append(f"- `{f.file}` — `{f.text_key}` hides {mods} — "
                       f"**{f.exemption['date']}**: {f.exemption['rationale']}")
        out.append("")
    out += [
        "## Coverage",
        "",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {len(unrev)}",
        f"- exempted: {len(exemp)}",
        f"- stale tags: {len(result.stale_tags)}",
        "",
    ]
    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report. Reads the
    script, static modifier and loc files itself, so `mod_state` is unused."""
    from path_constants import mod_path
    result = audit(mod_path)
    out_path = os.path.join(mod_path, REPORT_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    return {
        "unreviewed": result.failing,
        "total_flags": len(result.flags),
        "exempted": sum(1 for f in result.flags if f.exemption),
        "stale_tags": len(result.stale_tags),
        "files_scanned": result.files_scanned,
        "blocks_checked": result.blocks_checked,
        "rendered_ok": result.rendered_ok,
        "dynamic_skipped": result.dynamic_skipped,
        "lineless_skipped": result.lineless_skipped,
        "path": out_path,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on any untagged flag or stale tag (CI mode)")
    parser.add_argument("--mod-path", type=Path)
    args = parser.parse_args(argv)
    result = audit(args.mod_path)
    print(render_report(result))
    return int(args.strict and result.failing > 0)


if __name__ == "__main__":
    raise SystemExit(main())
