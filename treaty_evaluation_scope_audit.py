"""Find named-scope reads in a treaty-article block that does not bind them.

Two checks over `common/treaty_articles/`. Both are engine-silent at load: the
read fails only when someone drafts the article, and then the trigger is just
false (`Undefined event target`, `Invalid right side during comparison`).

1. AI `evaluation_chance` is root-only. Vanilla's treaty_articles.md gives this
   field only the evaluating country as root, so every `scope:` read in it is
   flagged. Partner eligibility belongs in `possible`, and partner preferences
   in `inherent_accept_score`. This check takes no suppression.

2. The party scopes (`scope:other_country`, `scope:source_country`,
   `scope:target_country`, `scope:first_country`, `scope:second_country`) in
   the five trigger blocks whose bindings are known (issue #1026; the table is
   `UNBOUND` below, from `docs/guides/scripting_best_practices.md` § "Treaty
   Article Scoping", which quotes vanilla's treaty_articles.md):

   * `visible`, `possible`: root is the prospective source and
     `scope:other_country` the prospective target. The other four do not exist.
   * `can_ratify`, `requirement_to_maintain`, and 1.15's `can_propose` (which
     "sees the same scopes as can_ratify", treaty_articles.md, and where
     vanilla's ship_transfer reads `scope:source_country`): a directed article
     gets `scope:source_country` / `scope:target_country`, a mutual one
     `scope:first_country` / `scope:second_country`. `scope:other_country` does
     not exist in any of them, nor source / target in a mutual article.

   Extensive Modernization Aid read `scope:other_country` in `can_ratify` for
   five months (#1025); the requirement could never be met.

   Vanilla's own articles agree with the table wherever they read a party
   scope, and `test_treaty_evaluation_scope_audit.py` keeps it so. That can
   only disprove an entry (vanilla reads a scope the table calls unbound),
   never prove one, and vanilla has two mutual articles (`alliance`,
   `defensive_pact`): the mutual rows rest on those two and on the guide.

What check 2 leaves alone, on purpose:

* Any scope outside the party family (`scope:treaty`, `scope:article`,
  `scope:input`, `scope:is_renegotiation`, a scope the script saved itself).
  It is a deny-list of reads known to be unbound, not an allow-list.
* `scope:first_country` / `scope:second_country` in a directed article's
  `can_ratify` / `requirement_to_maintain` / `can_propose`. No vanilla
  article reads them there and the docs do not say they are unset.
* Every other block: `can_withdraw`, the input valid triggers,
  the `on_*` hooks, `non_fulfillment`, `wargoal`, and the `ai` fields other
  than `evaluation_chance`. The evidence there is thin or contradicts the
  docs: vanilla reads `scope:target_country` bare in two `on_break` hooks, and
  `scope:other_country` in a mutual `inherent_accept_score`.
* A party scope the block saves itself (`save_scope_as` /
  `save_temporary_scope_as`, as vanilla's `alliance` saves `target_country`
  in `possible`): wherever the save sits in the block, the name counts as
  bound.
* An article with no `kind` of its own (an `INJECT:` into a vanilla article):
  only what both kinds leave unbound is flagged.

Both checks cover direct reads, including quoted script-value expressions.
Neither expands a scripted trigger or value the block calls, so review what
those read too. Suppress an intended read of check 2 with a trailing
`# REVIEWED YYYY-MM-DD (treaty_scope): rationale` on the flagged line.
"""
import re
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path

from audit_common import AuditResult as _AuditResult
from audit_common import cli_main, parse_reviewed
from iterator_limit_audit import blank_comments_and_strings
from paradox_file_parser import ParadoxFileParser

_TOKEN = re.compile(
    r"(?P<close>\})|(?P<key>[A-Za-z_][A-Za-z0-9_.:|@$\-]*)"
    r"\s*(?:\?=|[!<>=]=|[=<>])\s*(?:(?P<open>\{)|(?P<value>[^\s{}]+))?"
    r"|(?P<anon>\{)"
)
_SCOPE = re.compile(r"\bscope:[A-Za-z_][A-Za-z0-9_]*", re.IGNORECASE)
_SAVE = re.compile(r"\bsave_(?:temporary_)?scope_as\s*=\s*([A-Za-z_][A-Za-z0-9_]*)")
_KIND = re.compile(r'"?([^\s{}"]*)')
CHECK = "treaty_scope"

EVALUATION_CHANCE = "ai.evaluation_chance"

_PROSPECT_UNBOUND = frozenset({"source_country", "target_country", "first_country", "second_country"})
_RATIFY_UNBOUND = {
    "directed": frozenset({"other_country"}),
    "mutual": frozenset({"other_country", "source_country", "target_country"}),
}
# Block -> article kind -> the party scopes that block does not bind.
UNBOUND = {
    "visible": {"directed": _PROSPECT_UNBOUND, "mutual": _PROSPECT_UNBOUND},
    "possible": {"directed": _PROSPECT_UNBOUND, "mutual": _PROSPECT_UNBOUND},
    "can_ratify": _RATIFY_UNBOUND,
    "requirement_to_maintain": _RATIFY_UNBOUND,
    "can_propose": _RATIFY_UNBOUND,
}
_RATIFY_BLOCKS = frozenset(b for b, by_kind in UNBOUND.items() if by_kind is _RATIFY_UNBOUND)
_BINDS = {
    "visible": "root (the prospective source) and scope:other_country",
    "possible": "root (the prospective source) and scope:other_country",
    "directed": "scope:source_country and scope:target_country",
    "mutual": "scope:first_country and scope:second_country",
}


@dataclass(frozen=True)
class Flag:
    file: str
    line: int
    article: str
    scope: str
    block: str = EVALUATION_CHANCE
    kind: str | None = None
    # Left out of the hash, so a flag stays hashable.
    exemption: dict | None = field(default=None, hash=False)

    @property
    def reviewed(self) -> bool:
        return bool(self.exemption)

    @property
    def message(self) -> str:
        if self.block == EVALUATION_CHANCE:
            return f"{self.scope} in root-only evaluation_chance"
        if self.block in ("visible", "possible"):
            return f"{self.scope} in {self.block}, which binds only {_BINDS[self.block]}"
        if self.kind in _RATIFY_UNBOUND:
            return (f"{self.scope} in {self.block} of a {self.kind} article, "
                    f"which binds {_BINDS[self.kind]}")
        return f"{self.scope} in {self.block}, which binds it for neither kind of article"


def _unbound(block: str, kind: str | None) -> frozenset:
    by_kind = UNBOUND[block]
    if kind in by_kind:
        return by_kind[kind]
    return frozenset.intersection(*by_kind.values())


def scan_text(text: str, rel_path: str) -> list[Flag]:
    """Ignore comments and unrelated fields, retaining source line numbers.
    Returns every flag, suppressed ones included (`Flag.reviewed`)."""
    clean, comments = blank_comments_and_strings(text)
    starts = [0] + [m.end() for m in re.finditer(r"\n", text)]
    stack = []
    flags = []
    kind = None
    pending = []  # (block, line, scope, names the block saves): one article's reads
    block_start = None

    def reads(end):
        """The block's named-scope reads as (line, scope), and the names it saves."""
        # Keep quoted expressions here: a function argument can read a
        # named scope even though quotes protect its braces/comments.
        found, saved, offset = [], set(), block_start
        for line in text[block_start:end].splitlines(keepends=True):
            code = ParadoxFileParser._strip_comment(line)
            saved.update(_SAVE.findall(code))
            for hit in _SCOPE.finditer(code):
                found.append((bisect_right(starts, offset + hit.start()), hit.group()))
            offset += len(line)
        return found, frozenset(saved)

    def flush():
        """An article is complete, so its kind is known: judge its pending reads."""
        for block, line, scope, saved in pending:
            if block != EVALUATION_CHANCE:
                name = scope.split(":", 1)[1].lower()
                if name in saved or name not in _unbound(block, kind):
                    continue
            exemption = None if block == EVALUATION_CHANCE else parse_reviewed(comments.get(line), (CHECK,))
            flags.append(Flag(rel_path, line, stack[0] if stack else "?", scope, block,
                              kind if block in _RATIFY_BLOCKS else None,
                              exemption))
        pending.clear()

    for token in _TOKEN.finditer(clean):
        if token.group("close"):
            block = None
            if len(stack) == 3 and stack[1:] == ["ai", "evaluation_chance"]:
                block = EVALUATION_CHANCE
            elif len(stack) == 2 and stack[1] in UNBOUND:
                block = stack[1]
            if block:
                found, saved = reads(token.start())
                pending.extend((block, line, scope, saved) for line, scope in found)
                block_start = None
            if len(stack) == 1:
                flush()
                kind = None
            if stack:
                stack.pop()
        elif token.group("open"):
            key = token.group("key")
            if ((len(stack) == 2 and stack[1] == "ai" and key == "evaluation_chance")
                    or (len(stack) == 1 and key in UNBOUND)):
                block_start = token.end()
            stack.append(key)
        elif token.group("anon"):
            stack.append(None)
        elif len(stack) == 1 and token.group("key") == "kind" and token.group("value"):
            # From the raw text: `clean` has blanked the body of a quoted value.
            kind = _KIND.match(text, token.start("value")).group(1)
    stack[1:] = []
    flush()  # an article the file never closes
    return flags


def audit(mod_path: str | Path) -> list[Flag]:
    """Every flag in the mod's treaty articles, suppressed ones included."""
    root = Path(mod_path)
    flags = []
    for path in sorted((root / "common/treaty_articles").rglob("*.txt")):
        flags.extend(scan_text(path.read_text(encoding="utf-8-sig"),
                               path.relative_to(root).as_posix()))
    return flags


def unreviewed(flags: list[Flag]) -> list[Flag]:
    return [flag for flag in flags if not flag.reviewed]


@dataclass
class AuditResult(_AuditResult):
    """`audit()`'s flags, for the command line."""

    flags: list[Flag] = field(default_factory=list)


def render(result: AuditResult) -> str:
    failing = result.unreviewed
    lines = [f"{flag.file}:{flag.line}: {flag.article}: {flag.message}" for flag in failing]
    lines.append(f"Treaty evaluation scope audit: {len(failing)} invalid named-scope reads"
                 f" ({len(result.exemptions)} reviewed)")
    return "\n".join(lines)


def main(argv=None) -> int:
    def add_arguments(parser):
        parser.add_argument("--mod-path", type=Path, default=Path(__file__).resolve().parent)

    return cli_main(lambda args: AuditResult(flags=audit(args.mod_path)),
                    lambda result, args: render(result),
                    argv=argv, description=__doc__.split("\n\n")[0], add_arguments=add_arguments,
                    strict_help="Fail if an unsuppressed named-scope read is found")


if __name__ == "__main__":
    raise SystemExit(main())
