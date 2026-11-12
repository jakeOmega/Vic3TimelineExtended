"""Audit for `trigger = { }` inside a `random_list` branch's weight `modifier`.

A `random_list` branch's `modifier = { }` is a script value: it takes `add`,
`multiply`, `value`, and `if = { limit = { ... } add = N }` for a condition.
The `ai_chance` form, `modifier = { trigger = { ... } add = N }`, is not
accepted there:

    random_list = {
        30 = {
            modifier = {
                trigger = { ... }   # "Unexpected token: trigger"
                add = 15
            }
            ...
        }
    }

The engine writes `Unexpected token: trigger` to `error.log` at load and the
weight tilt is lost; nothing offline caught it before this audit
(`decolonization_events.17`, #1573). The same block under `ai_chance` (an
option's AI weight) and under `random = { chance = ... }` (where `trigger` is
required) is valid and is never flagged: only a `modifier` whose parent is a
branch of a `random_list` is read.

Fix: `modifier = { if = { limit = { <the conditions> } add = N } }`
(`docs/guides/scripting_best_practices.md` § "`random_list` Requires Literal
Integer Weights").

The audit takes no suppression comment: the engine rejects the token in
every case. Token scan of `common/` and `events/`, so a one-line block is
seen too. `--strict` exits 1 on any flag.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field


@dataclass
class Flag:
    file: str
    line: int  # line of the `trigger` token
    branch: str  # the random_list branch's weight key
    branch_line: int


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0


_TOKEN_RE = re.compile(r'"[^"\n]*"|[{}]|\?=|[<>!=]=?|[^\s{}<>!=?"]+')


def _tokens(text: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for line_num, raw in enumerate(text.splitlines(), 1):
        idx = raw.find("#")
        content = raw if idx < 0 else raw[:idx]
        for tok in _TOKEN_RE.findall(content):
            out.append((tok, line_num))
    return out


def scan_text(text: str, rel_path: str) -> list[Flag]:
    """Flag every `trigger = {` whose parent block is `modifier` and whose
    grandparent is a branch of a `random_list`."""
    toks = _tokens(text)
    flags: list[Flag] = []
    stack: list[tuple[str | None, int]] = []  # (block name, line)
    for i, (tok, line_num) in enumerate(toks):
        if tok == "{":
            name = toks[i - 2][0] if i >= 2 and toks[i - 1][0] in ("=", "?=") else None
            line = toks[i - 2][1] if name is not None else line_num
            if (
                name == "trigger"
                and len(stack) >= 3
                and stack[-1][0] == "modifier"
                and stack[-3][0] == "random_list"
            ):
                branch, branch_line = stack[-2]
                flags.append(Flag(rel_path, line, branch or "?", branch_line))
            stack.append((name, line))
        elif tok == "}":
            if stack:
                stack.pop()
    return flags


def scan_file(filepath: str, rel_path: str) -> list[Flag]:
    try:
        with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
            return scan_text(fh.read(), rel_path)
    except OSError:
        return []


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    result = AuditResult()
    for sub in ("common", "events"):
        root_dir = os.path.join(mod_path, sub)
        if not os.path.isdir(root_dir):
            continue
        for root, _dirs, files in os.walk(root_dir):
            for fname in sorted(files):
                if not fname.endswith(".txt"):
                    continue
                abs_p = os.path.join(root, fname)
                result.files_audited += 1
                result.flags.extend(scan_file(abs_p, os.path.relpath(abs_p, mod_path)))
    result.flags.sort(key=lambda f: (f.file, f.line))
    return result


def render(result: AuditResult) -> str:
    if not result.flags:
        return (f"random_list_weight_audit: no `trigger` in a random_list weight modifier "
                f"({result.files_audited} files).")
    lines = [
        f"random_list_weight_audit: {len(result.flags)} `trigger = {{ }}` in a random_list "
        "branch's weight `modifier`. The engine rejects it (\"Unexpected token: trigger\") and the "
        "weight tilt is lost. Write `modifier = { if = { limit = { ... } add = N } }` instead.",
    ]
    for f in result.flags:
        lines.append(f"  {f.file}:{f.line}: in branch `{f.branch}` (line {f.branch_line})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    result = audit(mod_path=mod_path)
    print(render(result))
    if "--strict" in argv:
        return 1 if result.flags else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
