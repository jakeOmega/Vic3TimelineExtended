"""Lints localization values for markup that breaks or bleeds when rendered.

**Bracket-style formatting tags** — `[b] [/b] [i] [/i] [u] [/u]` and any `[/x]`
closing-tag form (Markdown / BBCode muscle memory). Vic3 has no such tags; the
engine tries to resolve `[b]` as a data-system-function accessor chain, emits a
per-render `data-system-function` error, and the synchronous log spam drives
measurable in-game lag (confirmed in a prior session). The correct form is
`#b …#!`.

**Nested `[...]` inside `[...]`** — a data-function argument written as its own
bracketed expression, e.g.
`[SelectLocalization( [GetScriptedGui('x').IsShown( … )], 'a', 'b' )]`. The
engine's loc parser has no nesting: the inner `[` terminates the outer
expression, the whole value fails to parse, and any widget whose `text =`
points at that key logs `Failed parsing localized text: <key>` plus a
`failed reading property` at the `.gui` line. Arguments to a data function are
bare expressions — drop the inner brackets. Zero occurrences across all 102,168
vanilla loc values, so the rule is absolute. Single-quoted string literals are
skipped, since a quoted argument may legitimately contain `[`.

**Text pasted into a quoted argument** — a single-quoted data-function
argument is a plain string literal and substituted text is not escaped, so a
`[` or `'` arriving by substitution breaks it:

- `quoted_arg_expansion`: a `$key$` inside the quotes whose mod loc value
  contains `[` or `'`. The UN button effects wrapped
  `$un_peacekeeping_contributor_modifier$` ("[concept_un_peacekeeping]
  Contributor") in `Concept('…','…')` and the whole expression failed to parse.
- `quoted_name_apostrophe`: a straight `'` in the rendered name of a mod static
  modifier or modifier type. Vanilla's add/remove-modifier tooltip pastes the
  name into `GetRawTextTooltipTag('#header $MODIFIER_NAME$…')`, so
  "Women's Integration" ended the literal. Write `’` (U+2019), as vanilla does.

Both fixed 2026-09-25 (20 instances); both are mod-clean regression guards.
From 1.15 every `$key$` in a quoted argument must carry the `q` flag
(`$key|q$`, check 9 of `scripts/analysis/check_localization_files.py`), which
presumably escapes what it pastes. Whether that makes a `[` or `'` safe is not
yet seen in game, so both checks stay. Vanilla 1.15's add-modifier tooltip
also moved the name out of the quotes
(`GetRawTextTooltipTag('$ADD_MODIFIER_BREAKDOWN|q$')] $MODIFIER_NAME$`).

**Article-instance scope in a treaty article's type text**
(`article_desc_scope`) — `[SOURCE_COUNTRY…]`, `[TARGET_COUNTRY…]`,
`[FIRST_COUNTRY…]`, `[SECOND_COUNTRY…]`, `[ROOT…]` or `[SCOPE…]` heading a
data chain in `<article>_desc` or `<article>_effects_desc`. Those scopes are
bound only when an article instance exists, which is the case for
`<article>_article_short_desc`, the one place they belong. `_desc` renders
through `ArticleType.GetDesc` and `_effects_desc` in offered-treaty and
designer previews. Neither has an instance behind it, so the promote returns
nullptr: the text shows blank, and debug.log logs
`Promote 'SOURCE_COUNTRY' returned nullptr` with no script path. The
`enforce_emissions_reduction_effects_desc` bullet reading
`[SOURCE_COUNTRY.MakeScope.ScriptValue(…)]` logged 88 such lines in one session
(fixed 2026-09-27). None of vanilla's 68 `_desc` / `_effects_desc` values
contains any data expression other than a concept link, so the rule is
absolute. Articles are the top-level keys of the mod's
`common/treaty_articles/*.txt`, with any `INJECT:` / `REPLACE:` prefix removed.
The committed `vanilla_parsed/` snapshot adds vanilla's article names when it
is present, which covers a mod override of a vanilla article's loc. Known
limit: a `$key$` reference is not expanded, so scoped text that arrives
through one is missed.

`localization_accessor_audit` catches `[Scope.GetX]` accessor chains and
`concept_reference_audit` catches `[concept_x]` hyperlinks — neither flags
bracket formatting tags or nesting. This audit closes that gap. The two bracket
checks are vanilla- and mod-clean today (0 findings); they are regression guards against
re-introducing the known lag bug and the 2026-09-20 cultural-hegemony
widget-status breakage.

**Formatting tags left open** (`unclosed_format`, issue #266) — a `#bold`,
`#v`, `#R` … opened and never closed with `#!` in the same value. The format
runs on to the end of the text the value is part of, through whatever a
`$key$` reference or a concatenation puts after it. The mod's `GDPPERCAPITA`
line shipped that way, `…@money!#bold $GDP_per_capita$/…|2*]` with no `#!`,
until #261.

The grammar, read off the 12,705 of vanilla's 108,112 English values that
hold a `#`:

- `#!` closes one tag, the innermost. Two tags need two (`#r #b …#!#!`), and
  `#tooltippable #tooltip:TAG,key #v x#!#!#!` needs three.
- `##` is a literal `#` (vanilla's `BUILDING_RANK` writes
  `##[Building.GetProfitabilityRankInType]` for "#3"). It opens nothing.
- A `#` before a letter, `_`, `[` or `$` opens a tag. Its header runs to the
  next space, newline escape, `#` or the end of the value, through any
  `[...]` inside it, and is one tag whatever it combines: `#bold;red`,
  `#indent_newline:3`, `#tooltippable;tooltip:[GetPlayer.GetTooltipTag],my_tt`.
  `#[GetX]` and `#$COLOR$` are tags whose name is computed.
- Everything inside a `[...]` data expression is skipped, so a `#v …#!` in a
  quoted argument is the data function's business. Quotes are tracked there,
  so a `]` in a quoted argument does not end the expression.
- A `#!` with nothing open is ignored. Vanilla writes defensive `#!#!`, and a
  closing fragment is the other half of an opening one.

A value is flagged when a tag is still open at its end. That is stricter than
counting openers against resets (`5#! then #b bold` counts as balanced) and
never flags a surplus reset.

Why this ships when #134's balance check did not. That check was measured on
vanilla, counted both directions, and found 2341 "violations" across
vanilla's eleven languages, because vanilla splits a run across keys: an
`#indent_newline:3` left open so the effect lines the engine appends sit
indented under it, a reset with nothing before it to close
(`LAW_CATEGORIES_HEADER:0 "Legal Categories#!"`). Three things differ here.
Vanilla is never judged: `audit()` reads the mod's own `localization/` only.
A surplus `#!` is never flagged. And an opening fragment, the one split left,
is rare enough in the mod to review key by key: seven values, all color
prefixes that customizable localization returns
(`gw_trend_prefix_warming:0 "#R +"`), each with a `# REVIEWED` naming who
closes it.

Vanilla's text is the evidence that the grammar reads tags as the game's
writers do: 98.8% of its values with a `#` end with nothing open (1.15.1
snapshot). Of the 157 that do not, 112 leave an `#indent_newline` open, 14
end on the opener itself (event flavor ending `#italic`: the snapshot's loc
reader stops a value at its first unescaped quote, so quoted flavor after
the tag is cut off), and 31 are slips (`concept_recovery_rate_desc` never
closes its `#b`) or more such cuts.
`VanillaFormatTagCalibrationTests` holds the grammar to the committed
snapshot.

Known limits. A `$key$` or `[X.GetCustom('y')]` that pastes an opening
fragment is not followed, so a caller that forgets the `#!` for a reviewed
fragment is not caught. Tag names are not checked against the formats the
game defines, so `#bolt x#!` passes.

**A `#` that is not a tag** (`bare_hash`, #266) — a `#` before a digit, a
space, punctuation or the end of the value, which is none of the three forms
above. Vanilla writes every literal hash as `##`; its four bare ones are all
slips (two settings tooltips ending `#` for `#!`, `#b not# have`, a stray
`# ` bullet). What the engine draws for one has not been seen in game, so the
fix is the form known to work: `##`. The mod had three (the cultural board's
`#` column head, a debug panel's "Snapshot #", an issue number in a debug
event), fixed with the check.

Suppress an intentional flag with a trailing comment on the loc line — the
engine ignores anything after the closing quote:

    my_loc_key:0 "... [b]bold[/b] ..." # REVIEWED 2026-05-21: rationale
"""
import json
import os
import re
from dataclasses import dataclass, field


@dataclass
class RenderFlag:
    loc_key: str
    # "bracket_tag" | "nested_brackets" | "quoted_arg_expansion" |
    # "quoted_name_apostrophe" | "article_desc_scope" | "unclosed_format" | "bare_hash"
    issue: str
    detail: str
    file: str
    line: int
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[RenderFlag] = field(default_factory=list)
    loc_files_scanned: int = 0
    values_checked: int = 0


_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)
# `[b] [i] [u]` and their closing forms, plus any other `[/x]` closing tag.
# Valid Vic3 loc never opens a bare single-letter bracket nor uses a `[/` slash;
# accessor chains are `[Scope.Method]` and concept links are `[concept_x]`.
_BRACKET_FMT_RE = re.compile(r"\[/?[biu]\]|\[/[A-Za-z]\w*\]?")


def _nested_bracket_offsets(value: str) -> list[int]:
    """Offsets of every `[` opened while another `[` is still unclosed.

    Single-quoted runs are skipped: a quoted data-function argument is opaque to
    the loc parser, so a `[` inside one is not a nesting error.
    """
    offsets: list[int] = []
    depth = 0
    in_quote = False
    for i, ch in enumerate(value):
        if ch == "'":
            in_quote = not in_quote
        elif in_quote:
            continue
        elif ch == "[":
            if depth > 0:
                offsets.append(i)
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
    return offsets


# What may follow the `#` that opens a formatting tag: a format name, or a
# data expression / `$PARAM$` that computes one.
_TAG_START = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_[$")


def _skip_data_expr(value: str, start: int) -> int:
    """`value[start]` is a `[`: return the offset just past the `]` that
    closes it, or `len(value)` if nothing does. Quotes are tracked, so a
    bracket inside a quoted argument is text."""
    depth = 0
    in_quote = False
    for i in range(start, len(value)):
        ch = value[i]
        if ch == "'":
            in_quote = not in_quote
        elif in_quote:
            continue
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(value)


def _tag_header_end(value: str, start: int) -> int:
    """Offset where the tag header that starts at `value[start]` (the
    character after its `#`) ends: the next whitespace, backslash escape
    (`\\n`) or `#`, outside any `[...]`."""
    i = start
    n = len(value)
    while i < n:
        ch = value[i]
        if ch == "[":
            i = _skip_data_expr(value, i)
        elif ch.isspace() or ch in "#\\":
            break
        else:
            i += 1
    return i


def scan_format_tags(value: str) -> tuple[list[str], list[int]]:
    """Walk one loc value's formatting tags. Returns the headers of the tags
    still open at its end, outermost first, and the offset of every bare `#`.
    The grammar is in the module docstring."""
    open_tags: list[str] = []
    bare: list[int] = []
    i = 0
    n = len(value)
    while i < n:
        ch = value[i]
        if ch == "[":
            i = _skip_data_expr(value, i)
            continue
        if ch != "#":
            i += 1
            continue
        nxt = value[i + 1: i + 2]
        if nxt == "#":
            i += 2
        elif nxt == "!":
            if open_tags:
                open_tags.pop()
            i += 2
        elif nxt in _TAG_START:
            end = _tag_header_end(value, i + 1)
            open_tags.append(value[i:end])
            i = end
        else:
            bare.append(i)
            i += 1
    return open_tags, bare


def _short_tag(header: str) -> str:
    return header if len(header) <= 32 else header[:29] + "..."


def check_format_tags(value: str) -> list[tuple[str, str]]:
    """Flag a formatting tag left open at the end of the value, and a `#` that
    is neither a tag, a `#!` nor a `##`. Pure; unit-testable."""
    if "#" not in value:
        return []
    out: list[tuple[str, str]] = []
    open_tags, bare = scan_format_tags(value)
    if open_tags:
        names = ", ".join(f"`{_short_tag(t)}`" for t in open_tags)
        out.append((
            "unclosed_format",
            f"{names} opened and never closed: the format runs on into "
            "whatever follows this value in the same text. Each tag needs its "
            "own `#!`. If this value is an opening fragment that its caller "
            "closes, say who closes it in a `# REVIEWED` comment",
        ))
    if bare:
        at = bare[0]
        snippet = value[max(0, at - 12): at + 12]
        out.append((
            "bare_hash",
            f"a `#` that is not a tag, a `#!` or a `##` at offset {at} "
            f"(`{snippet}`). Write a literal hash as `##`, as vanilla does",
        ))
    return out


# `$key$`, or `$key|flags$` (`$key|q$` in a quoted argument from 1.15).
_LOC_REF_RE = re.compile(r"\$([A-Za-z0-9_.]+)(?:\|[^$]*)?\$")
_CONCEPT_DISPLAY_RE = re.compile(
    r"\[Concept\(\s*'[^']*'\s*,\s*'([^']*)'\s*\)\]"
)
_DATA_EXPR_RE = re.compile(r"\[[^\[\]]*\]")
_TOP_LEVEL_ENTITY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", re.MULTILINE)

# Entity types whose display name the engine pastes, unescaped, into a
# single-quoted data-function argument: vanilla's `ADD_MODIFIER` /
# `REMOVE_MODIFIER` tooltip is `GetRawTextTooltipTag('#header $MODIFIER_NAME$…')`,
# and the breakdown inside it lists each modifier type by display name.
_QUOTED_NAME_DIRS = (
    "common/static_modifiers",
    "common/modifier_type_definitions",
)


def _quoted_args(value: str):
    """Yield (offset, text) for each single-quoted run inside a `[...]`
    data expression. Quotes in prose outside brackets are apostrophes, not
    string delimiters, so they are ignored."""
    depth = 0
    start = -1
    for i, ch in enumerate(value):
        if start >= 0:
            if ch == "'":
                yield start, value[start:i]
                start = -1
        elif depth == 0:
            if ch == "[":
                depth = 1
        elif ch == "'":
            start = i + 1
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1


def check_quoted_expansion(value: str, loc_values: dict[str, str]) -> list[tuple[str, str]]:
    """Flag a `$key$` inside a quoted data-function argument whose loc value
    contains `[` or `'`.

    `$key$` expands before the data function is parsed, so the expansion
    lands inside the string literal: a `[` in it opens an expression the
    literal cannot hold, and a `'` closes the literal early. Either way the
    whole expression fails to parse. The UN button effects hit this:
    `[Concept('…','$un_peacekeeping_contributor_modifier$')]` expanded to
    `'[concept_un_peacekeeping] Contributor'`. Only keys defined in mod loc
    are resolved. Vanilla's `$UPPER_CASE$` runtime parameters (filled with
    already-rendered text) sometimes share a name with a loc key and would
    false-flag.
    """
    out: list[tuple[str, str]] = []
    if "$" not in value or "[" not in value:
        return out
    for _offset, arg in _quoted_args(value):
        for ref in _LOC_REF_RE.findall(arg):
            expansion = loc_values.get(ref)
            if expansion is None:
                continue
            bad = [c for c in ("[", "'") if c in expansion]
            if bad:
                out.append((
                    "quoted_arg_expansion",
                    f"`${ref}$` sits inside a quoted data-function argument and "
                    f"expands to text containing {' and '.join(f'`{c}`' for c in bad)} "
                    f"(`{expansion[:40]}`), which breaks the string literal — "
                    "move the reference out of the argument",
                ))
    return out


def _rendered_text(value: str, loc_values: dict[str, str], depth: int = 0) -> str:
    """Approximate the text a loc value renders to: expand mod `$key$`
    references, keep a `Concept()` link's display argument, drop every other
    data expression (their quotes are resolved before anything is pasted)."""
    if depth < 6:
        value = _LOC_REF_RE.sub(
            lambda m: _rendered_text(loc_values[m.group(1)], loc_values, depth + 1)
            if m.group(1) in loc_values else m.group(0),
            value,
        )
    value = _CONCEPT_DISPLAY_RE.sub(lambda m: m.group(1), value)
    return _DATA_EXPR_RE.sub("", value)


def check_quoted_name(value: str, loc_values: dict[str, str]) -> list[tuple[str, str]]:
    """Flag a straight apostrophe in the rendered display name of a static
    modifier or modifier type. The engine pastes that name into
    `GetRawTextTooltipTag('…')` for the add/remove-modifier tooltip, and the
    apostrophe ends the literal: "Women's Integration" filled debug.log with
    `Expected ','` and the tooltip broke. Vanilla writes `’` (U+2019) in these
    names; 3 of its ~8,500 modifier and modifier-type names use `'`.

    Known limit: data expressions are dropped, not evaluated, so an apostrophe
    that reaches the name through one (`[GetBuildingType('x').GetName]` naming
    "Workers' Cooperative") is missed."""
    if "'" not in _rendered_text(value, loc_values):
        return []
    return [(
        "quoted_name_apostrophe",
        "straight apostrophe in a modifier / modifier-type name, which the "
        "engine pastes into a quoted tooltip argument — write `’` (U+2019)",
    )]


def _quoted_name_keys(mod_path: str) -> set[str]:
    names: set[str] = set()
    for dir_rel in _QUOTED_NAME_DIRS:
        abs_dir = os.path.join(mod_path, dir_rel)
        if not os.path.isdir(abs_dir):
            continue
        for fname in sorted(os.listdir(abs_dir)):
            if not fname.endswith(".txt"):
                continue
            try:
                with open(os.path.join(abs_dir, fname), encoding="utf-8-sig",
                          errors="replace") as fh:
                    names.update(_TOP_LEVEL_ENTITY_RE.findall(fh.read()))
            except OSError:
                pass
    return names


# A treaty article's top-level key, optionally behind a merge directive
# (`INJECT:foo = {` extends vanilla's `foo`).
_ARTICLE_ENTITY_RE = re.compile(
    r"^(?:[A-Z_]+:)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", re.MULTILINE
)
_VANILLA_ARTICLES_JSON = os.path.join("vanilla_parsed", "common", "treaty_articles.json")
# Scopes bound only when an article instance exists. SOURCE/TARGET are a
# directed article's sides, FIRST/SECOND a mutual article's; ROOT and SCOPE
# read the render context, which a type preview may not supply. Vanilla uses
# none of them in type text.
_ARTICLE_SCOPE_RE = re.compile(
    r"(?<![\w.])(SOURCE_COUNTRY|TARGET_COUNTRY|FIRST_COUNTRY|SECOND_COUNTRY|ROOT|SCOPE)\b"
)
_QUOTED_LITERAL_RE = re.compile(r"'[^']*'")
# Longest suffix first: `foo_effects_desc` belongs to article `foo`, and only
# falls back to being `foo_effects`'s `_desc` when `foo` is not an article.
_ARTICLE_TYPE_TEXT_SUFFIXES = ("_effects_desc", "_desc")


def _treaty_article_keys(mod_path: str) -> set[str]:
    """Names of every treaty article the mod defines or extends, plus
    vanilla's from the committed `vanilla_parsed/` snapshot when present
    (CI has it; a temp-dir test tree does not, and needs no game install)."""
    names: set[str] = set()
    abs_dir = os.path.join(mod_path, "common", "treaty_articles")
    if os.path.isdir(abs_dir):
        for fname in sorted(os.listdir(abs_dir)):
            if not fname.endswith(".txt"):
                continue
            try:
                with open(os.path.join(abs_dir, fname), encoding="utf-8-sig",
                          errors="replace") as fh:
                    names.update(_ARTICLE_ENTITY_RE.findall(fh.read()))
            except OSError:
                pass
    try:
        with open(os.path.join(mod_path, _VANILLA_ARTICLES_JSON), encoding="utf-8") as fh:
            names.update(json.load(fh))
    except (OSError, ValueError):
        pass
    return names


def article_type_text_key(loc_key: str, articles: set[str]) -> tuple[str, str] | None:
    """Return (article, suffix) when `loc_key` is `<article>_desc` or
    `<article>_effects_desc` for a known article, else None. The article name
    must match exactly, so `<article>_article_short_desc` and
    `<article>_crisis_desc` are not type text."""
    for suffix in _ARTICLE_TYPE_TEXT_SUFFIXES:
        if loc_key.endswith(suffix):
            article = loc_key[: -len(suffix)]
            if article in articles:
                return article, suffix
    return None


def check_article_scope(value: str, article: str, suffix: str) -> list[tuple[str, str]]:
    """Flag a data chain in a treaty article's `_desc` / `_effects_desc` that
    starts from a scope only an article instance binds. Such text renders
    with no instance behind it, so the scope promotes to nullptr and renders
    blank. The one valid home is `<article>_article_short_desc`.

    Each `[...]` expression is scanned, not just its head, because
    `[SelectLocalization(SOURCE_COUNTRY.IsX, 'a', 'b')]` fails the same way.
    Single-quoted literals are skipped."""
    if "[" not in value:
        return []
    found: list[str] = []
    for expr in _DATA_EXPR_RE.findall(value):
        for scope in _ARTICLE_SCOPE_RE.findall(_QUOTED_LITERAL_RE.sub("''", expr)):
            if scope not in found:
                found.append(scope)
    if not found:
        return []
    return [(
        "article_desc_scope",
        f"{', '.join(f'`[{s}…]`' for s in found)} in `{article}{suffix}`, which "
        "renders with no article instance behind it (article-type tooltip, "
        "offered-treaty and designer previews), so the scope promotes to "
        "nullptr and shows blank. Keep this text scope-free; scoped text "
        f"belongs in `{article}_article_short_desc`",
    )]


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _parse_loc_line(raw: str) -> tuple[str, str, str] | None:
    """Returns (key, value, trailing-after-closing-quote) or None.

    Mirrors `concept_reference_audit._parse_loc_line`. The trailing segment is
    where `# REVIEWED …` suppression comments live.
    """
    line = raw.rstrip("\n")
    stripped = line.lstrip()
    if not stripped or stripped.startswith("#") or ":" not in stripped:
        return None
    key, rest = line.split(":", 1)
    key = key.strip()
    if not key:
        return None
    quote_locations = [i for i, c in enumerate(rest) if c == '"']
    if len(quote_locations) < 2:
        return None
    value = rest[quote_locations[0] + 1: quote_locations[-1]]
    trailing = rest[quote_locations[-1] + 1:]
    return key, value, trailing


def check_value(value: str) -> list[tuple[str, str]]:
    """Return [(issue, detail)] for one loc value. Pure; unit-testable."""
    out: list[tuple[str, str]] = []
    brackets = _BRACKET_FMT_RE.findall(value)
    if brackets:
        uniq = sorted(set(brackets))
        out.append((
            "bracket_tag",
            "invalid bracket formatting tag(s): "
            + ", ".join(f"`{b}`" for b in uniq)
            + " — use `#b …#!` style, not Markdown/BBCode",
        ))
    nested = _nested_bracket_offsets(value)
    if nested:
        snippet = value[nested[0]: nested[0] + 40]
        out.append((
            "nested_brackets",
            f"`[` opened inside an unclosed `[...]` at offset {nested[0]} "
            f"(`{snippet}`) — the loc parser does not nest; pass data-function "
            "arguments as bare expressions",
        ))
    out += check_format_tags(value)
    return out


def audit(ms=None, mod_path: str | None = None) -> AuditResult:
    """Scan every mod loc value. `ms` is unused (loc and entity files are read
    directly, so CI needs no game install) but kept for the
    POST_LOAD_GENERATORS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    loc_root = os.path.join(mod_path, "localization")
    if not os.path.isdir(loc_root):
        return AuditResult(flags=[], loc_files_scanned=0, values_checked=0)

    # Pass 1: every mod loc line. Pass 2 needs the whole table to resolve
    # `$key$` references across files.
    entries: list[tuple[str, str, str, str, int]] = []
    files_scanned = 0
    for root, _dirs, files in os.walk(loc_root):
        for fname in sorted(files):
            if not fname.endswith(".yml"):
                continue
            abs_p = os.path.join(root, fname)
            rel_p = os.path.relpath(abs_p, mod_path)
            files_scanned += 1
            try:
                with open(abs_p, encoding="utf-8-sig", errors="replace") as fh:
                    for i, raw_line in enumerate(fh, start=1):
                        parsed = _parse_loc_line(raw_line)
                        if parsed is None:
                            continue
                        loc_key, value, trailing = parsed
                        entries.append((loc_key, value, trailing, rel_p, i))
            except OSError:
                pass

    loc_values = {key: value for key, value, _t, _f, _l in entries}
    quoted_names = _quoted_name_keys(mod_path)
    articles = _treaty_article_keys(mod_path)

    flags: list[RenderFlag] = []
    for loc_key, value, trailing, rel_p, line in entries:
        issues = check_value(value) + check_quoted_expansion(value, loc_values)
        if loc_key in quoted_names:
            issues += check_quoted_name(value, loc_values)
        article_text = article_type_text_key(loc_key, articles)
        if article_text:
            issues += check_article_scope(value, *article_text)
        if not issues:
            continue
        exemption = _parse_reviewed(trailing)
        for issue, detail in issues:
            flags.append(RenderFlag(
                loc_key=loc_key,
                issue=issue,
                detail=detail,
                file=rel_p,
                line=line,
                exemption=exemption,
            ))

    return AuditResult(
        flags=flags,
        loc_files_scanned=files_scanned,
        values_checked=len(entries),
    )


_ISSUE_LABEL = {
    "bracket_tag": "Bracket formatting tags ([b], [/x], …)",
    "nested_brackets": "Nested [...] inside [...]",
    "quoted_arg_expansion": "`$key$` expanding [ or ' into a quoted argument",
    "quoted_name_apostrophe": "Straight apostrophe in a modifier name",
    "article_desc_scope": "Article-instance scope in a treaty article's `_desc` / `_effects_desc`",
    "unclosed_format": "Formatting tags left open (`#bold` with no `#!`)",
    "bare_hash": "A `#` that is not a tag (write `##`)",
}


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Localization render audit report",
        "",
        "Auto-generated by `loc_render_audit.py` on every full `POST /reload`",
        "of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a localization value contains a bracket-style formatting tag",
        "(`[b]`, `[/i]`, …). Vic3 has no such tags — the engine treats `[b]` as",
        "a failing data-system-function and floods the log, causing in-game lag.",
        "Fix: replace `[b]X[/b]` with `#b X#!`.",
        "",
        "Also flagged: a `[` opened inside an unclosed `[...]`. The loc parser",
        "does not nest, so the whole value fails to parse and any widget whose",
        "`text =` points at the key logs `Failed parsing localized text`.",
        "Fix: pass data-function arguments as bare expressions, not as their own",
        "bracketed expressions.",
        "",
        "Also flagged: a `$key$` inside a quoted data-function argument whose",
        "value contains `[` or `'` (the expansion breaks the string literal),",
        "and a straight apostrophe in a static modifier's or modifier type's",
        "name (the engine pastes it into `GetRawTextTooltipTag('…')` for the",
        "add/remove-modifier tooltip). Fix: move the reference out of the",
        "argument; write `’` (U+2019) in the name.",
        "",
        "Also flagged: `[SOURCE_COUNTRY…]`, `[TARGET_COUNTRY…]`, `[FIRST_COUNTRY…]`,",
        "`[SECOND_COUNTRY…]`, `[ROOT…]` or `[SCOPE…]` in a treaty article's `_desc`",
        "or `_effects_desc`. That text renders with no article instance behind it,",
        "so the scope promotes to nullptr and shows blank. Fix: keep it scope-free",
        "and move scoped text into `<article>_article_short_desc`.",
        "",
        "Also flagged: a formatting tag (`#bold`, `#v`, `#R`, …) still open at",
        "the end of its value, so the format runs on into whatever follows the",
        "value in the same text. Each tag needs its own `#!`; a surplus `#!` is",
        "not flagged. Fix: close it. An opening fragment that its caller closes",
        "(a color prefix from customizable localization) takes a `# REVIEWED`",
        "naming the caller. And a `#` that is neither a tag, a `#!` nor a `##`.",
        "Fix: write a literal hash as `##`.",
        "",
        "Suppress an intentional flag with a trailing comment on the loc line:",
        "`my_loc_key:0 \"…\" # REVIEWED YYYY-MM-DD: rationale`",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out.append("_None._")
        out.append("")
    else:
        by_issue: dict[str, list[RenderFlag]] = {}
        for f in unrev:
            by_issue.setdefault(f.issue, []).append(f)
        for issue in sorted(by_issue):
            entries = by_issue[issue]
            out.append(f"### {_ISSUE_LABEL.get(issue, issue)} ({len(entries)})")
            out.append("")
            for f in entries:
                out.append(f"- `{f.file}:{f.line}` — `{f.loc_key}`: {f.detail}")
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        # No line number on a reviewed entry: the loc key names it, and an
        # edit above it would otherwise churn the report.
        for f in exemp:
            out.append(
                f"- `{f.file}` — `{f.loc_key}` ({f.issue}) — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    # Flag counts only: the file / value counts stay on the result (and in
    # the regenerate() summary) but move with unrelated loc.
    out.append("## Coverage")
    out.append("")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")
    out.append("")

    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_GENERATORS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(mod_path, "docs", "engine", "loc_render_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    unrev = sum(1 for f in result.flags if not f.exemption)
    exemp = sum(1 for f in result.flags if f.exemption)
    return {
        "loc_files_scanned": result.loc_files_scanned,
        "values_checked": result.values_checked,
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": exemp,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    result = audit(mod_path=mod_path)
    print(render_report(result))
    # --strict: CI mode. Exit 1 if any flag lacks a `# REVIEWED ...` exemption.
    if "--strict" in sys.argv:
        raise SystemExit(1 if any(not f.exemption for f in result.flags) else 0)
