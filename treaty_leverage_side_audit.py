"""Audit for the two "which side" fields of a treaty article: leverage and Involvement.

Leverage: `country_treaty_leverage_generation_add` on the wrong side of a directed
treaty article. Involvement: an article that builds none, or builds it on the
wrong side (see "Involvement" below).

The modifier reads like "leverage this country generates", and the engine's own
tooltip — "Leverage Generation from Treaty" — does nothing to dispel that. It is
the other way round: the leverage is generated **against** the country whose
`source_modifier` / `target_modifier` carries the line, by the dominant
counterparty, and only while that counterparty leads a power bloc.

Getting it backwards is completely engine-silent. No log line, no parse error,
no `script_parse_error`, nothing in `error.log` — the modifier name is valid and
the block it sits in is valid, so the engine simply routes the influence the
other way. It only shows up in the leverage panel mid-campaign. Monetary phase 6
(#365) shipped all five banking articles (`currency_peg`, `swap_line`,
`lender_of_last_resort`, `imposed_currency_peg`, `debt_receivership`) inverted
this way; the owner caught it in game, not in review.

The heuristic
-------------
There is no way to read "which side is dominant" out of the script, but there is
a reliable proxy already written into every article: **`maintenance_paid_by`**.
The beneficiary of a directed article pays its upkeep, and the party being
leaned on is the other one — so the leverage line belongs on the side that does
**not** pay maintenance. That holds for every vanilla article that carries the
modifier:

===========================  ===================  =================
Vanilla article              `maintenance_paid_by`  leverage line
===========================  ===================  =================
`guarantee_independence`     `source_country`     `target_modifier`
`foreign_investment_rights`  `target_country`     `source_modifier`
`trade_privilege`            `target_country`     `source_modifier`
`host_power_bloc_embassy`    `target_country`     `source_modifier`
===========================  ===================  =================

...and for 13 of the mod's 14 directed articles that carry it. The one
deliberate exception is `request_influence`, where a bloc-less petitioner both
pays the upkeep *and* is the party the bloc leader gains leverage over; it
carries a `# REVIEWED` comment.

What is and isn't flagged
-------------------------
Only a `country_treaty_leverage_generation_add` that is inside a
`source_modifier` or `target_modifier` block **directly under a top-level
article**, in an article that also declares `maintenance_paid_by`. Silent on:

- `mutual_modifier` — a symmetric block has no side to be wrong about;
- an article with no `maintenance_paid_by` — nothing to compare against, so the
  heuristic does not apply (counted under "undetermined" in the report);
- the modifier appearing anywhere else in the article (an effect block, an AI
  score), which carries no side.

Suppress a deliberate case with a trailing `# REVIEWED YYYY-MM-DD: rationale`
comment on the `country_treaty_leverage_generation_add` line or on the article's
opening `<name> = {` line.

Involvement (2026-11-03)
------------------------
The same module checks an article's Involvement, the other side question a
treaty article answers:

    max_target_involvement = 1000
    target_involvement_applies_to = target_country

The second field names the **local** side. The *other* party gains up to the
first figure in every strategic region where the named side is local, scaled
by that side's locality (floor 10%, `INTEREST_MIN_INVOLVEMENT_RATIO`), and all
treaties and pacts together are capped at 5,000 a region
(`INTEREST_TREATY_PACT_INVOLVEMENT_CAP`). Vanilla only reads sensibly this
way: investment rights name the host (`source_country`), so the investor
gains; a guarantee names the guaranteed country (`target_country`), so the
guarantor gains. In all six vanilla articles carrying both fields and a
directed leverage line, the named side is the side carrying the leverage. An
article without the fields builds no Involvement at all, and nothing says so:
none of the mod's 49 articles had them before 2026-11-03.

Flags (`InvolvementFlag.kind`):

- `missing_involvement`: no `max_target_involvement`;
- `missing_side`: a maximum but no `target_involvement_applies_to` (the
  engine defaults it to `source_country` without a word);
- `kind_mismatch`: a mutual article not set to `mutual`, or a directed one
  set to it;
- `wrong_side`: a directed article naming a side other than its leverage
  line's. With no leverage line, naming the side that pays
  `maintenance_paid_by`: the payer is the party gaining a presence, so the
  local side is the one that does not pay. Vanilla breaks the maintenance
  proxy four times (`offer_embassy`, where the unrecognized host pays, and
  `toll_exemption`, `no_strait_closure`, `abandon_piracy`), so a deliberate
  case is reviewed;
- `bad_value`: a maximum that isn't a number, is 0 or less, or is above the
  5,000 cap, or a side that is none of the three values;
- `stale_review`: an `(involvement)` tag that suppresses nothing.

`INJECT:` blocks are skipped, since the article they extend keeps its own
fields. These flags take a **check-tagged** comment,
`# REVIEWED YYYY-MM-DD (involvement): rationale`, on the article's opening
`<name> = {` line or on either field's line. The tag stops it from blinding
the leverage check above and `loc_coverage_audit`, whose untagged regexes
want the colon straight after the date. An article that should build no
Involvement (a one-off transfer, an imposed restriction) carries one on its
opening line.

Pact Involvement (2026-11-12, #1380)
------------------------------------
A diplomatic action's `pact = { }` takes the same two fields, inside the pact
block. Vanilla's directed pacts all name `source_country` (`fund_lobbies`,
`orchestrate_coup`, `support_separatism`, `increase_relations`, `rivalry`
1,000; subject pacts 2,500 to 8,000), and `embargo` alone `mutual`. A puppet
pact's 8,000 only makes sense with the overlord gaining, so pacts seem to read
the side the other way round from articles. The article rule above is not
carried over: a mod pact copies its nearest vanilla analogue's pair, and the
pact rule is vanilla's own convention, which reads right whichever side the
engine means. Every action with a `pact = { }` under
`common/diplomatic_actions/` is judged:

- `missing_involvement`: no `max_target_involvement` inside the pact;
- `missing_side`: a maximum but no `target_involvement_applies_to`;
- `wrong_side`: `target_country`, which no vanilla pact names;
- `bad_value`: a maximum that isn't a number, is 0 or less, or is above
  8,000 (vanilla's highest pact, the puppet), or a side that is none of the
  three values;
- `stale_review`: an `(involvement)` tag that suppresses nothing.

The same `# REVIEWED YYYY-MM-DD (involvement): why` tag suppresses one, on the
action's opening line, the `pact = {` line or either field's line. A pact that
should build none (vanilla's `damage_relations`, `raise_payments` and the
other subject-relation actions build none) carries one on its opening line.
`test_treaty_leverage_side_audit.py` checks the convention against
`vanilla_parsed/`, so a vanilla patch that breaks it fails a test.

Why a raw-text scan instead of `paradox_file_parser`
----------------------------------------------------
Same reason as `iterator_limit_audit`: the parser discards line numbers and
comments, so there would be nothing to report a location against and nothing to
hang a `# REVIEWED` suppression on. The comment/string blanking helper is shared
with that module — it preserves offsets, so line numbers stay exact.
"""
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

from audit_common import AuditResult as _AuditResult
from audit_common import cli_main, parse_reviewed, write_text

# Offset-preserving comment/string blanking, shared with the iterator audit so
# the two agree on what "a commented-out line" means.
from iterator_limit_audit import blank_comments_and_strings

LEVERAGE_MODIFIER = "country_treaty_leverage_generation_add"

# The two directed modifier blocks. `mutual_modifier` is deliberately absent.
DIRECTED_SIDES = ("source_modifier", "target_modifier")

# maintenance side -> the side the leverage line must NOT be on.
_PAYING_SIDE_BLOCK = {
    "source_country": "source_modifier",
    "target_country": "target_modifier",
}

AUDIT_DIRS = (os.path.join("common", "treaty_articles"),)
# Diplomatic actions whose `pact = { }` the pact Involvement rule judges.
PACT_DIRS = (os.path.join("common", "diplomatic_actions"),)

INVOLVEMENT_MAX = "max_target_involvement"
INVOLVEMENT_SIDE = "target_involvement_applies_to"
INVOLVEMENT_CHECK = "involvement"
# Vanilla's INTEREST_TREATY_PACT_INVOLVEMENT_CAP: every treaty and pact together.
TREATY_INVOLVEMENT_CAP = 5000
_INVOLVEMENT_SIDES = ("source_country", "target_country", "mutual")
# Vanilla's highest pact maximum (puppet, dominion, colony, crown land). The
# 5,000 cap is on what all treaties and pacts add together in a region, which
# vanilla's subject pacts exceed in their own figure.
PACT_INVOLVEMENT_MAX = 8000
# The sides vanilla's pacts name: every directed one `source_country`,
# `embargo` `mutual`. None names `target_country`.
PACT_SIDES = ("source_country", "mutual")
# leverage block -> the local side it implies (the side leveraged is local).
_BLOCK_SIDE = {"source_modifier": "source_country", "target_modifier": "target_country"}
_OTHER_SIDE = {"source_country": "target_country", "target_country": "source_country"}
# `INJECT:x` extends an article that keeps its own fields.
_INJECT_PREFIXES = ("INJECT:", "TRY_INJECT:", "INJECT_OR_CREATE:")
INVOLVEMENT_KINDS = (
    "missing_involvement", "missing_side", "kind_mismatch", "wrong_side",
    "bad_value", "stale_review",
)

_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    r"|(?P<key>[A-Za-z_][A-Za-z0-9_.:|@$\-]*)\s*(?:\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[^\s{}#]+))?"
    r"|(?P<anon>\{)"
)


@dataclass
class Flag:
    file: str
    line: int  # line of the offending country_treaty_leverage_generation_add
    article: str
    article_line: int
    side: str  # "source_modifier" | "target_modifier"
    maintenance_paid_by: str  # "source_country" | "target_country"
    exemption: dict | None = None


@dataclass
class InvolvementFlag:
    file: str
    line: int
    article: str
    kind: str  # one of INVOLVEMENT_KINDS
    detail: str
    exemption: dict | None = None


@dataclass
class AuditResult(_AuditResult):
    """`flags` holds the leverage check's flags, `involvement_flags` and
    `pact_involvement_flags` the two Involvement checks'; `unreviewed` and
    `exemptions` read all three, so `failing` is what `--strict` fails on. A
    stale `(involvement)` tag is a `stale_review` involvement flag, never
    exempt, so `stale` stays empty."""

    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0
    articles_checked: int = 0  # directed articles the heuristic could judge
    articles_undetermined: int = 0  # leverage line present, no maintenance side
    involvement_flags: list[InvolvementFlag] = field(default_factory=list)
    articles_with_involvement: int = 0
    articles_reviewed_without_involvement: int = 0
    pact_involvement_flags: list[InvolvementFlag] = field(default_factory=list)
    pacts_checked: int = 0
    pacts_with_involvement: int = 0
    pacts_reviewed_without_involvement: int = 0

    def _every_flag(self) -> list:
        return self.flags + self.involvement_flags + self.pact_involvement_flags

    @property
    def unreviewed(self) -> list:
        return [f for f in self._every_flag() if not f.exemption]

    @property
    def exemptions(self) -> list:
        return [f for f in self._every_flag() if f.exemption]


@dataclass
class _Article:
    """One top-level article's involvement-relevant fields, for the judge."""
    name: str
    line: int
    kind: str | None = None
    maintenance: str | None = None
    max_value: str | None = None
    max_line: int = 0
    side: str | None = None
    side_line: int = 0
    leverage_blocks: set = field(default_factory=set)


@dataclass
class _Pact:
    """One diplomatic action's pact block fields, for the pact judge."""
    name: str
    line: int
    pact_line: int = 0
    max_value: str | None = None
    max_line: int = 0
    side: str | None = None
    side_line: int = 0


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for m in re.finditer(r"\n", text):
        starts.append(m.end())
    return starts


def _line_of(pos: int, starts: list[int]) -> int:
    return bisect_right(starts, pos)


def scan_text(text: str, rel_path: str) -> list[Flag]:
    """Scan one file's raw text; return a flag per misplaced leverage line."""
    clean, comments = blank_comments_and_strings(text)
    starts = _line_starts(clean)
    flags: list[Flag] = []

    # Per-article accumulator, reset at every top-level `<name> = {`.
    article: str | None = None
    article_line = 0
    maintenance: str | None = None
    # (side, line) for every leverage line found in a directed modifier block.
    leverage_hits: list[tuple[str, int]] = []
    # Block names from the article inwards; [] means we are at file level.
    stack: list[str | None] = []

    def finish() -> None:
        nonlocal article, maintenance, leverage_hits
        if article and maintenance in _PAYING_SIDE_BLOCK:
            bad_side = _PAYING_SIDE_BLOCK[maintenance]
            for side, line in leverage_hits:
                if side == bad_side:
                    flags.append(
                        Flag(
                            file=rel_path,
                            line=line,
                            article=article,
                            article_line=article_line,
                            side=side,
                            maintenance_paid_by=maintenance,
                            # The plain form only: an `(involvement)` tag never
                            # suppresses a leverage flag.
                            exemption=(
                                parse_reviewed(comments.get(line))
                                or parse_reviewed(comments.get(article_line))
                            ),
                        )
                    )
        article = None
        maintenance = None
        leverage_hits = []

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
                if not stack:
                    finish()
            continue
        if m.group("anon"):
            if stack:
                stack.append(None)
            continue

        key = m.group("key")
        line = _line_of(m.start(), starts)

        if m.group("open"):
            if not stack:  # a top-level entity: this is the article itself
                article = key
                article_line = line
                maintenance = None
                leverage_hits = []
            stack.append(key)
            continue

        # A scalar `key = value` statement.
        value = m.group("value")
        if len(stack) == 1 and key == "maintenance_paid_by":
            maintenance = value
        elif (
            len(stack) == 2
            and stack[1] in DIRECTED_SIDES
            and key == LEVERAGE_MODIFIER
        ):
            leverage_hits.append((stack[1], line))

    if stack:  # unbalanced braces — judge what we have rather than dropping it
        finish()

    return flags


def _judge_involvement(a: _Article) -> list[tuple[str, int, str]]:
    """(kind, line, detail) for each problem with one article's Involvement."""
    if a.max_value is None:
        return [("missing_involvement", a.line,
                 f"declares no `{INVOLVEMENT_MAX}`, so it builds no Involvement")]
    out: list[tuple[str, int, str]] = []
    try:
        amount = float(a.max_value)
    except ValueError:
        amount = None
    if amount is None or amount <= 0 or amount > TREATY_INVOLVEMENT_CAP:
        out.append(("bad_value", a.max_line,
                    f"`{INVOLVEMENT_MAX} = {a.max_value}` is not a figure from 1 "
                    f"to the {TREATY_INVOLVEMENT_CAP:,} treaty cap"))
    if a.side is None:
        out.append(("missing_side", a.max_line,
                    f"no `{INVOLVEMENT_SIDE}`: the engine defaults it to `source_country`"))
        return out
    if a.side not in _INVOLVEMENT_SIDES:
        out.append(("bad_value", a.side_line,
                    f"`{INVOLVEMENT_SIDE} = {a.side}` is not source_country, "
                    "target_country or mutual"))
        return out
    if a.kind == "mutual":
        if a.side != "mutual":
            out.append(("kind_mismatch", a.side_line,
                        f"a mutual article names `{a.side}`, which it doesn't have; use `mutual`"))
        return out
    if a.side == "mutual":
        out.append(("kind_mismatch", a.side_line,
                    "a directed article set to `mutual`; name its local side"))
        return out
    if len(a.leverage_blocks) == 1:
        block = next(iter(a.leverage_blocks))
        expected = _BLOCK_SIDE[block]
        if a.side != expected:
            out.append(("wrong_side", a.side_line,
                        f"names `{a.side}`, but the leverage line sits in `{block}`: "
                        f"the leveraged side is the local one, so name `{expected}`"))
    elif not a.leverage_blocks and a.maintenance in _OTHER_SIDE and a.side == a.maintenance:
        out.append(("wrong_side", a.side_line,
                    f"names `{a.side}`, the side that pays `maintenance_paid_by`: the "
                    "payer is the party gaining a presence, so name "
                    f"`{_OTHER_SIDE[a.side]}`"))
    return out


def _scan_involvement(text: str, rel_path: str) -> tuple[list[InvolvementFlag], int]:
    """(flags, articles declaring Involvement) for one file's raw text."""
    clean, comments = blank_comments_and_strings(text)
    starts = _line_starts(clean)
    articles: list[_Article] = []
    cur: _Article | None = None
    stack: list[str | None] = []

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
                if not stack and cur is not None:
                    articles.append(cur)
                    cur = None
            continue
        if m.group("anon"):
            if stack:
                stack.append(None)
            continue
        key = m.group("key")
        line = _line_of(m.start(), starts)
        if m.group("open"):
            if not stack:
                cur = None if key.startswith(_INJECT_PREFIXES) else _Article(key, line)
            stack.append(key)
            continue
        if cur is None:
            continue
        value = m.group("value")
        if len(stack) == 1:
            if key == "kind":
                cur.kind = value
            elif key == "maintenance_paid_by":
                cur.maintenance = value
            elif key == INVOLVEMENT_MAX:
                cur.max_value, cur.max_line = value, line
            elif key == INVOLVEMENT_SIDE:
                cur.side, cur.side_line = value, line
        elif len(stack) == 2 and stack[1] in DIRECTED_SIDES and key == LEVERAGE_MODIFIER:
            cur.leverage_blocks.add(stack[1])
    if cur is not None:  # unbalanced braces: judge what we have
        articles.append(cur)

    flags = _tagged_flags(
        rel_path, comments,
        [(a.name, a.line, (a.line, a.max_line, a.side_line), _judge_involvement(a))
         for a in articles],
    )
    with_involvement = sum(1 for a in articles if a.max_value is not None)
    return flags, with_involvement


def _tagged_flags(rel_path, comments, judged) -> list[InvolvementFlag]:
    """Attach `(involvement)` exemptions and flag the tags that suppress nothing.
    The tagged form only: a plain comment never suppresses an Involvement flag.

    `judged` is (name, opening line, exemption sites, [(kind, line, detail)])
    per entity, in file order."""
    flags: list[InvolvementFlag] = []
    used: set[int] = set()
    for name, _line, sites, problems in judged:
        sites = [ln for ln in sites if ln]
        for kind, line, detail in problems:
            exemption = None
            for site in sites:
                exemption = parse_reviewed(comments.get(site), (INVOLVEMENT_CHECK,))
                if exemption:
                    used.add(site)
                    break
            flags.append(InvolvementFlag(rel_path, line, name, kind, detail, exemption))
    for line in sorted(comments):
        if line in used or not parse_reviewed(comments[line], (INVOLVEMENT_CHECK,)):
            continue
        owner = next((name for name, start, _s, _p in reversed(judged) if start <= line), "")
        flags.append(InvolvementFlag(
            rel_path, line, owner, "stale_review",
            "an `(involvement)` REVIEWED tag that suppresses nothing; remove it"))
    flags.sort(key=lambda f: f.line)
    return flags


def _judge_pact(p: _Pact) -> list[tuple[str, int, str]]:
    """(kind, line, detail) for each problem with one pact's Involvement."""
    if p.max_value is None:
        return [("missing_involvement", p.line,
                 f"its pact declares no `{INVOLVEMENT_MAX}`, so it builds no Involvement; "
                 "copy the nearest vanilla pact's pair (fund_lobbies, increase_relations: "
                 "1000 source_country)")]
    out: list[tuple[str, int, str]] = []
    try:
        amount = float(p.max_value)
    except ValueError:
        amount = None
    if amount is None or amount <= 0 or amount > PACT_INVOLVEMENT_MAX:
        out.append(("bad_value", p.max_line,
                    f"`{INVOLVEMENT_MAX} = {p.max_value}` is not a figure from 1 to "
                    f"{PACT_INVOLVEMENT_MAX:,}, vanilla's highest pact"))
    if p.side is None:
        out.append(("missing_side", p.max_line,
                    f"no `{INVOLVEMENT_SIDE}`: the engine defaults it to `source_country`; "
                    "say so"))
    elif p.side not in _INVOLVEMENT_SIDES:
        out.append(("bad_value", p.side_line,
                    f"`{INVOLVEMENT_SIDE} = {p.side}` is not source_country, "
                    "target_country or mutual"))
    elif p.side not in PACT_SIDES:
        out.append(("wrong_side", p.side_line,
                    f"names `{p.side}`, which no vanilla pact does: every directed pact "
                    "names `source_country` and `embargo` `mutual`; copy the analogue's"))
    return out


def _scan_pacts(text: str, rel_path: str) -> tuple[list[InvolvementFlag], int, int]:
    """(flags, pacts, pacts declaring Involvement) for one diplomatic-actions file."""
    clean, comments = blank_comments_and_strings(text)
    starts = _line_starts(clean)
    pacts: list[_Pact] = []
    cur: _Pact | None = None
    has_pact = False
    stack: list[str | None] = []

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
                if not stack and cur is not None:
                    if has_pact:
                        pacts.append(cur)
                    cur = None
            continue
        if m.group("anon"):
            if stack:
                stack.append(None)
            continue
        key = m.group("key")
        line = _line_of(m.start(), starts)
        if m.group("open"):
            if not stack:
                cur = None if key.startswith(_INJECT_PREFIXES) else _Pact(key, line)
                has_pact = False
            elif len(stack) == 1 and key == "pact" and cur is not None:
                has_pact = True
                cur.pact_line = line
            stack.append(key)
            continue
        if cur is None or len(stack) != 2 or stack[1] != "pact":
            continue
        value = m.group("value")
        if key == INVOLVEMENT_MAX:
            cur.max_value, cur.max_line = value, line
        elif key == INVOLVEMENT_SIDE:
            cur.side, cur.side_line = value, line
    if cur is not None and has_pact:  # unbalanced braces: judge what we have
        pacts.append(cur)

    flags = _tagged_flags(
        rel_path, comments,
        [(p.name, p.line, (p.line, p.pact_line, p.max_line, p.side_line), _judge_pact(p))
         for p in pacts],
    )
    return flags, len(pacts), sum(1 for p in pacts if p.max_value is not None)


def scan_pact_text(text: str, rel_path: str) -> list[InvolvementFlag]:
    """Scan one diplomatic-actions file's raw text; a flag per pact Involvement problem."""
    return _scan_pacts(text, rel_path)[0]


def scan_involvement_text(text: str, rel_path: str) -> list[InvolvementFlag]:
    """Scan one file's raw text; return a flag per Involvement problem."""
    return _scan_involvement(text, rel_path)[0]


def scan_file(filepath: str, rel_path: str) -> list[Flag]:
    try:
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    return scan_text(text, rel_path)


def _count_articles(text: str) -> tuple[int, int]:
    """Return (judgeable, undetermined) article counts for coverage stats."""
    clean, _ = blank_comments_and_strings(text)
    judgeable = undetermined = 0
    maintenance: str | None = None
    has_directed_leverage = False
    stack: list[str | None] = []

    def finish() -> None:
        nonlocal judgeable, undetermined, maintenance, has_directed_leverage
        if has_directed_leverage:
            if maintenance in _PAYING_SIDE_BLOCK:
                judgeable += 1
            else:
                undetermined += 1
        maintenance = None
        has_directed_leverage = False

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
                if not stack:
                    finish()
            continue
        if m.group("anon"):
            if stack:
                stack.append(None)
            continue
        key = m.group("key")
        if m.group("open"):
            if not stack:
                maintenance = None
                has_directed_leverage = False
            stack.append(key)
            continue
        if len(stack) == 1 and key == "maintenance_paid_by":
            maintenance = m.group("value")
        elif len(stack) == 2 and stack[1] in DIRECTED_SIDES and key == LEVERAGE_MODIFIER:
            has_directed_leverage = True
    if stack:
        finish()
    return judgeable, undetermined


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_GENERATORS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    flags: list[Flag] = []
    inv_flags: list[InvolvementFlag] = []
    with_involvement = 0
    files_audited = 0
    checked = 0
    undetermined = 0
    for sub in AUDIT_DIRS:
        root_dir = os.path.join(mod_path, sub)
        if not os.path.isdir(root_dir):
            continue
        for root, _dirs, files in os.walk(root_dir):
            for fname in sorted(files):
                if not fname.endswith(".txt"):
                    continue
                abs_p = os.path.join(root, fname)
                rel_p = os.path.relpath(abs_p, mod_path).replace(os.sep, "/")
                files_audited += 1
                flags.extend(scan_file(abs_p, rel_p))
                try:
                    with open(abs_p, "r", encoding="utf-8-sig", errors="replace") as fh:
                        text = fh.read()
                except OSError:
                    text = ""
                c, u = _count_articles(text)
                checked += c
                undetermined += u
                f_inv, n_inv = _scan_involvement(text, rel_p)
                inv_flags.extend(f_inv)
                with_involvement += n_inv

    pact_flags: list[InvolvementFlag] = []
    pacts = pacts_with = 0
    for sub in PACT_DIRS:
        root_dir = os.path.join(mod_path, sub)
        if not os.path.isdir(root_dir):
            continue
        for root, _dirs, files in os.walk(root_dir):
            for fname in sorted(files):
                if not fname.endswith(".txt"):
                    continue
                abs_p = os.path.join(root, fname)
                rel_p = os.path.relpath(abs_p, mod_path).replace(os.sep, "/")
                try:
                    with open(abs_p, "r", encoding="utf-8-sig", errors="replace") as fh:
                        text = fh.read()
                except OSError:
                    continue
                f_p, n_p, n_with = _scan_pacts(text, rel_p)
                pact_flags.extend(f_p)
                pacts += n_p
                pacts_with += n_with

    return AuditResult(
        flags=flags,
        files_audited=files_audited,
        articles_checked=checked,
        articles_undetermined=undetermined,
        involvement_flags=inv_flags,
        articles_with_involvement=with_involvement,
        articles_reviewed_without_involvement=sum(
            1 for f in inv_flags if f.kind == "missing_involvement" and f.exemption
        ),
        pact_involvement_flags=pact_flags,
        pacts_checked=pacts,
        pacts_with_involvement=pacts_with,
        pacts_reviewed_without_involvement=sum(
            1 for f in pact_flags if f.kind == "missing_involvement" and f.exemption
        ),
    )


def strict_failures(result: AuditResult) -> int:
    """Flags with no REVIEWED exemption, across every check (`--strict` fails on any)."""
    return len(result.failing)


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Treaty leverage and involvement side audit report",
        "",
        "Auto-generated by `treaty_leverage_side_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a directed treaty article whose",
        "`country_treaty_leverage_generation_add` sits in the same side's",
        "modifier block as the side named by `maintenance_paid_by`.",
        "",
        "The modifier generates leverage **against** the country whose block",
        "carries it, not by it. The beneficiary of a directed article pays its",
        "upkeep, so the leverage belongs on the *other* side. Vanilla is",
        "consistent: `guarantee_independence` pays from the source and puts the",
        "line on `target_modifier`; `foreign_investment_rights`,",
        "`trade_privilege` and `host_power_bloc_embassy` pay from the target and",
        "put it on `source_modifier`.",
        "",
        "Getting this backwards is engine-silent — no log line, no parse error,",
        "just influence flowing the wrong way. Phase 6 of the monetary system",
        "shipped five articles inverted this way (corrected 2026-09-21).",
        "",
        "`mutual_modifier` blocks and articles with no `maintenance_paid_by`",
        "are not judged — see Coverage below.",
        "",
        "Suppress a deliberate case with a trailing comment on the",
        "`country_treaty_leverage_generation_add` line or the article's opening",
        "`<name> = {` line:",
        "`country_treaty_leverage_generation_add = 200  # REVIEWED YYYY-MM-DD: why`",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out.append("_None._")
        out.append("")
    else:
        by_file: dict[str, list[Flag]] = {}
        for f in unrev:
            by_file.setdefault(f.file, []).append(f)
        for fname in sorted(by_file):
            out.append(f"### `{fname}`")
            out.append("")
            for f in by_file[fname]:
                other = (
                    "target_modifier"
                    if f.side == "source_modifier"
                    else "source_modifier"
                )
                out.append(
                    f"- line {f.line}: `{f.article}` (opened at line "
                    f"{f.article_line}) pays maintenance from "
                    f"`{f.maintenance_paid_by}` and carries the leverage line in "
                    f"`{f.side}` — move it to `{other}`, or mark it reviewed"
                )
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        # No line number on a reviewed entry: the article names it, and an
        # edit above it would otherwise churn the report.
        for f in exemp:
            out.append(
                f"- `{f.file}` — `{f.article}`: leverage in `{f.side}` "
                f"with `maintenance_paid_by = {f.maintenance_paid_by}` — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    inv_unrev = [f for f in result.involvement_flags if not f.exemption]
    inv_none = [f for f in result.involvement_flags
                if f.exemption and f.kind == "missing_involvement"]
    inv_other = [f for f in result.involvement_flags
                 if f.exemption and f.kind != "missing_involvement"]
    out += [
        "## Involvement",
        "",
        "Flagged: a treaty article with no `max_target_involvement` (it builds",
        "no Involvement, silently), one with no explicit",
        "`target_involvement_applies_to` (the engine defaults it to",
        "`source_country`), a mutual article not set to `mutual` or a directed",
        "one set to it, a side other than the leverage line's (or, with no",
        "leverage line, the side paying `maintenance_paid_by`), a figure outside",
        "1 to 5,000, and a stale tag.",
        "",
        "`target_involvement_applies_to` names the **local** side: the other",
        "party gains Involvement where it is local. Vanilla's investment rights",
        "name the host (the investor gains), its guarantee the guaranteed (the",
        "guarantor gains).",
        "",
        "Suppress with a check-tagged comment on the article's opening",
        "`<name> = {` line or on either field's line:",
        "`<name> = {  # REVIEWED YYYY-MM-DD (involvement): why`",
        "",
        "### Unreviewed Involvement Flags",
        "",
    ]
    if not inv_unrev:
        out += ["_None._", ""]
    else:
        by_file_inv: dict[str, list[InvolvementFlag]] = {}
        for f in inv_unrev:
            by_file_inv.setdefault(f.file, []).append(f)
        for fname in sorted(by_file_inv):
            out += [f"#### `{fname}`", ""]
            for f in by_file_inv[fname]:
                out.append(f"- line {f.line}: `{f.article}` — {f.kind}: {f.detail}")
            out.append("")
    out += ["### Articles Reviewed As Building No Involvement", ""]
    if not inv_none:
        out += ["_None._", ""]
    else:
        for f in inv_none:
            out.append(f"- `{f.file}` — `{f.article}` — "
                       f"**{f.exemption['date']}**: {f.exemption['rationale']}")
        out.append("")
    out += ["### Other Reviewed Involvement Flags", ""]
    if not inv_other:
        out += ["_None._", ""]
    else:
        for f in inv_other:
            out.append(f"- `{f.file}` — `{f.article}` ({f.kind}) — "
                       f"**{f.exemption['date']}**: {f.exemption['rationale']}")
        out.append("")

    pact_unrev = [f for f in result.pact_involvement_flags if not f.exemption]
    pact_rev = [f for f in result.pact_involvement_flags if f.exemption]
    out += [
        "## Pact Involvement",
        "",
        "Flagged: a diplomatic action whose `pact = { }` has no",
        "`max_target_involvement` (it builds none, silently), no explicit",
        "`target_involvement_applies_to`, the side `target_country` (no vanilla",
        "pact names it), a figure outside 1 to 8,000, and a stale tag.",
        "",
        "Vanilla's directed pacts all name `source_country` and `embargo`",
        "`mutual`. Pacts seem to read the side the other way round from",
        "articles, so a mod pact copies its nearest vanilla analogue's pair",
        "(`fund_lobbies`, `increase_relations`: 1000 `source_country`).",
        "",
        "Suppress with the same `(involvement)` tag on the action's opening line,",
        "the `pact = {` line or either field's line.",
        "",
        "### Unreviewed Pact Flags",
        "",
    ]
    if not pact_unrev:
        out += ["_None._", ""]
    else:
        by_file_p: dict[str, list[InvolvementFlag]] = {}
        for f in pact_unrev:
            by_file_p.setdefault(f.file, []).append(f)
        for fname in sorted(by_file_p):
            out += [f"#### `{fname}`", ""]
            for f in by_file_p[fname]:
                out.append(f"- line {f.line}: `{f.article}` — {f.kind}: {f.detail}")
            out.append("")
    out += ["### Reviewed Pacts", ""]
    if not pact_rev:
        out += ["_None._", ""]
    else:
        for f in pact_rev:
            out.append(f"- `{f.file}` — `{f.article}` ({f.kind}) — "
                       f"**{f.exemption['date']}**: {f.exemption['rationale']}")
        out.append("")

    # Flag counts, plus the articles the audit could not judge. The file /
    # judged-article counts stay on the result (and in the regenerate()
    # summary) but move with every new article.
    out.append("## Coverage")
    out.append("")
    out.append(
        f"- articles with a leverage line but no `maintenance_paid_by`: "
        f"{result.articles_undetermined}"
    )
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")
    out.append(f"- involvement flags: {len(result.involvement_flags)}")
    out.append(f"- involvement unreviewed: {len(inv_unrev)}")
    out.append(f"- involvement exempted: {len(inv_none) + len(inv_other)}")
    out.append(f"- pact involvement flags: {len(result.pact_involvement_flags)}")
    out.append(f"- pact involvement unreviewed: {len(pact_unrev)}")
    out.append(f"- pact involvement exempted: {len(pact_rev)}")
    out.append("")

    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    write_text(os.path.join(mod_path, "docs", "engine", "treaty_leverage_side_report.md"),
               render_report(result))
    exemp = sum(1 for f in result.flags if f.exemption)  # the leverage check's
    inv_unrev = sum(1 for f in result.involvement_flags if not f.exemption)
    return {
        "files_audited": result.files_audited,
        "articles_checked": result.articles_checked,
        "articles_undetermined": result.articles_undetermined,
        "total_flags": (len(result.flags) + len(result.involvement_flags)
                        + len(result.pact_involvement_flags)),
        # Both checks: the reload warning fires on any unreviewed flag.
        "unreviewed": strict_failures(result),
        "exempted": exemp,
        "involvement_flags": len(result.involvement_flags),
        "involvement_unreviewed": inv_unrev,
        "articles_with_involvement": result.articles_with_involvement,
        "articles_reviewed_without_involvement": result.articles_reviewed_without_involvement,
        "pact_involvement_flags": len(result.pact_involvement_flags),
        "pact_involvement_unreviewed": sum(
            1 for f in result.pact_involvement_flags if not f.exemption),
        "pacts_checked": result.pacts_checked,
        "pacts_with_involvement": result.pacts_with_involvement,
        "pacts_reviewed_without_involvement": result.pacts_reviewed_without_involvement,
    }


def main(argv=None) -> int:
    """Print the report; `--strict` (CI) exits 1 if any flag of either check
    lacks its REVIEWED exemption (a stale `(involvement)` tag never has one)."""
    from path_constants import mod_path
    return cli_main(lambda args: audit(mod_path=mod_path), lambda result, args: render_report(result),
                    argv=argv, description=__doc__.splitlines()[0])


if __name__ == "__main__":
    raise SystemExit(main())
