"""What the offline audits share: the `# REVIEWED` parser, the result shape,
the report frame and the command line (#1536).

An audit is a function that finds flags. Everything around it is here:

* `parse_reviewed(comment, tags=())` reads a suppression comment, in the plain
  form `# REVIEWED YYYY-MM-DD: why` or the tagged form
  `# REVIEWED YYYY-MM-DD (tag): why`, into `{date, tag, rationale}`.
* `Flag` and `AuditResult`: a result knows its `unreviewed` flags, its
  `exemptions` and its `stale` tags, and whether `--strict` fails on it.
* `write_report(result, path, title)` writes the standard report, with the
  suppression text taken from `audit_registry.suppression_hint`.
* `cli_main(audit_fn)` gives every audit the same command line: `--strict`
  exits 1 when the result fails.

`docs/guides/audits.md` § "Adding an audit" says how a new audit uses these.
The older audits are moving onto this module one batch at a time; each keeps
its own report format, so its committed report does not change.

Stdlib only, like `audit_registry`.
"""
from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass, field
from typing import Callable, Sequence

# Both forms in one pattern. `tags` is None for the plain form. The plain form
# reads exactly as the audits' own patterns did. The tag list takes names
# separated by spaces or commas, or one name with any whitespace around it
# (`roster_membership_audit`'s form). The tagged half reads every comment in
# the repository as each tagged audit's own pattern did;
# `test_audit_common.TAGGED_DIVERGENCES` names the shapes outside it where it
# differs from one of them.
REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*"
    r"(?:\((?P<tags>[\w ,]+|\s*\w+\s*)\)\s*)?"
    r":\s*(?P<rationale>.+?)\s*$"
)
_TAG_SPLIT_RE = re.compile(r"[\s,]+")


def comment_tags(listed: str) -> list[str]:
    """The tag names in a tagged comment's parentheses, in order."""
    return [t for t in _TAG_SPLIT_RE.split(listed.strip()) if t]


def parse_reviewed(comment: str | None, tags: Sequence[str] = ()) -> dict | None:
    """The `{date, tag, rationale}` of the suppression comment in `comment`
    that this audit reads, or None.

    `tags` names the forms the audit takes, as `audit_registry.Audit.tags`
    does: empty, or `""`, for the plain `# REVIEWED YYYY-MM-DD: why`; a name
    for `# REVIEWED YYYY-MM-DD (name): why`, whose parentheses may list several
    names. `tag` in the result is `""` for the plain form, else the first
    listed name the audit takes.

    `comment` may be a whole line: the pattern is searched for. The first
    comment of the plain form decides for the plain form, as every plain
    audit's pattern did. For the tagged form, the first comment that names one
    of `tags` decides, as the one-word and fixed forms did: a line can carry
    one tagged comment per audit, and a comment naming only another audit's
    tag does not hide a later one that names this audit's.
    """
    if not comment or "REVIEWED" not in comment:
        return None
    wanted = tuple(tags) or ("",)
    plain_ok = "" in wanted
    named = [t for t in wanted if t]
    plain = tagged = None
    hit = ""
    pos = 0
    while (plain is None and plain_ok) or (tagged is None and named):
        m = REVIEWED_RE.search(comment, pos)
        if m is None:
            break
        if m.group("tags") is None:
            plain = plain or m
        elif tagged is None:
            hit = next((t for t in comment_tags(m.group("tags")) if t in named), "")
            if hit:
                tagged = m
        pos = m.start() + 1
    found = []
    if plain is not None and plain_ok:
        found.append((plain, ""))
    if tagged is not None:
        found.append((tagged, hit))
    if not found:
        return None
    # An audit taking both forms reads whichever comes first.
    m, tag = min(found, key=lambda pair: pair[0].start())
    return {"date": m.group("date"), "tag": tag, "rationale": m.group("rationale").strip()}


@dataclass
class Flag:
    """One finding. An audit with more to say about a flag subclasses this or
    uses its own dataclass: the shared code reads only `exemption`, and the
    standard report `file`, `line` and `message`."""

    file: str
    line: int
    message: str
    exemption: dict | None = None


@dataclass
class StaleTag:
    """A tagged `# REVIEWED` comment that suppresses nothing."""

    file: str
    line: int
    tag: str = ""


@dataclass
class AuditResult:
    """Flags, with what `--strict` reads already worked out.

    An audit's own result class subclasses this and adds its coverage fields;
    `stale` is keyword-only so those fields keep their positions. An audit in
    which only some unreviewed flags fail (`duplicate_key_audit`'s warnings,
    for one) overrides `failing`."""

    flags: list = field(default_factory=list)
    stale: list = field(default_factory=list, kw_only=True)

    @property
    def unreviewed(self) -> list:
        return [f for f in self.flags if not f.exemption]

    @property
    def exemptions(self) -> list:
        return [f for f in self.flags if f.exemption]

    @property
    def failing(self) -> list:
        """What fails `--strict`: every unreviewed flag and stale tag."""
        return self.unreviewed + list(self.stale)

    @property
    def failed(self) -> bool:
        return bool(self.failing)


def write_text(path: str, text: str) -> None:
    """Write a report, creating its directory."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _flag_where(flag) -> str:
    return f"`{flag.file}:{flag.line}`"


def render_report(result: AuditResult, title: str, how_to_suppress: str = "", *,
                  audit: str = "", intro: str = "") -> str:
    """The standard report: what it is, how to suppress a flag, the unreviewed
    flags (with line numbers), the exemptions (without, so an edit above one
    does not churn the report), any stale tags, and the counts."""
    if not how_to_suppress and audit:
        import audit_registry
        how_to_suppress = audit_registry.suppression_hint(audit)
    out = [f"# {title}", ""]
    if audit:
        out += [f"Auto-generated by `{audit}.py`. Do not hand-edit.", ""]
    if intro:
        out += [intro.strip(), ""]
    if how_to_suppress:
        # One line each: a trailing double space is a Markdown line break.
        hint = how_to_suppress.strip().splitlines()
        out += [line + "  " for line in hint[:-1]] + hint[-1:] + [""]
    out += ["## Unreviewed flags", ""]
    unreviewed = result.unreviewed
    if unreviewed:
        out += [f"- {_flag_where(f)}: {f.message}" for f in unreviewed]
    else:
        out.append("_None._")
    out += ["", "## Reviewed exemptions", ""]
    exemptions = result.exemptions
    if exemptions:
        out += [f"- `{f.file}`: {f.message} — **{f.exemption['date']}**: {f.exemption['rationale']}"
                for f in exemptions]
    else:
        out.append("_None._")
    out.append("")
    if result.stale:
        out += ["## Stale tags", "",
                "A tagged `# REVIEWED` comment where nothing is flagged any more. Remove it.", ""]
        out += [f"- `{t.file}:{t.line}`" + (f" ({t.tag})" if t.tag else "") for t in result.stale]
        out.append("")
    out += [
        "## Coverage", "",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {len(unreviewed)}",
        f"- exempted: {len(exemptions)}",
    ]
    if result.stale:
        out.append(f"- stale tags: {len(result.stale)}")
    out.append("")
    return "\n".join(out)


def write_report(result: AuditResult, path: str, title: str, how_to_suppress: str = "", *,
                 audit: str = "", intro: str = "") -> str:
    """Write the standard report to `path` and return its text. With `audit`
    named and no `how_to_suppress`, the suppression text is the registry's
    hint for that audit."""
    text = render_report(result, title, how_to_suppress, audit=audit, intro=intro)
    write_text(path, text)
    return text


def summary(result: AuditResult, **extra) -> dict:
    """The dict a reload audit's `regenerate()` returns: `unreviewed` feeds
    the reload's `warnings` array."""
    out = {
        "total_flags": len(result.flags),
        "unreviewed": len(result.unreviewed),
        "exempted": len(result.exemptions),
    }
    if result.stale:
        out["stale_tags"] = len(result.stale)
    out.update(extra)
    return out


def cli_main(
    audit_fn: Callable[[argparse.Namespace], AuditResult],
    render: Callable[[AuditResult, argparse.Namespace], str | None] | None = None,
    *,
    argv: Sequence[str] | None = None,
    description: str | None = None,
    aliases: Sequence[str] = (),
    always_strict: bool = False,
    add_arguments: Callable[[argparse.ArgumentParser], None] | None = None,
    strict_help: str = "CI mode: exit 1 on an unreviewed flag or a stale tag.",
) -> int:
    """The audits' command line. Returns the exit code.

    `audit_fn(args)` runs the audit; `render(result, args)` returns the text to
    print (None prints nothing). `--strict` exits 1 when `result.failed`,
    otherwise the exit code is 0. `aliases` are other spellings of `--strict`
    an audit took before this module (`kill_character_audit`'s `--check`);
    `always_strict` is for an audit whose bare run already exited 1
    (`attitude_key_audit`). `add_arguments(parser)` adds an audit's own
    options, and `strict_help` says what fails when `failing` is narrower.
    `args.strict` tells `render` which mode it is in.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--strict", *aliases, dest="strict", action="store_true", help=strict_help,
    )
    if add_arguments is not None:
        add_arguments(parser)
    args = parser.parse_args(argv)
    args.strict = args.strict or always_strict
    result = audit_fn(args)
    if render is not None:
        text = render(result, args)
        if text is not None:
            print(text)
    return 1 if args.strict and result.failed else 0
