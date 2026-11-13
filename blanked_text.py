"""One blanked copy of a script file's text, shared by the raw-text audits.

About twenty post-load audits (`iterator_limit_audit`, `prev_scope_audit`,
`variable_guard_audit`, `empty_effect_audit`, ...) walk the raw text of
`common/` and `events/` rather than the parse, because the parser drops line
numbers and comments. Each first blanks comments and string bodies with
`blank_comments_and_strings`, so its own token regex can stream the text with
offsets that still map to real lines. They used to do that once per audit per
file, and the blanking was about half of each audit's time (#1698).

Two things make it cheap now:

- The blanking is one regex pass instead of a per-character Python loop
  (about twelve times faster; `test_blanked_text` pins it to the old loop's
  output on every mod file).
- Inside `with shared():` the result is kept per text, so the second audit to
  read a file gets the first one's blanking for the cost of a dict lookup.
  `mod_state_server._run_generator_chain` opens one around each post-load
  chain, so a reload blanks each file once; the cache is dropped when the chain
  ends. Outside `shared()` nothing is kept, which is what a CLI run or a test
  sees.

The cache is keyed by the text itself, not by the path, so a file a generator
rewrote mid-chain is simply a new entry, never a stale one. The tokenizers are
not shared: each audit streams its own token regex over the blanked text.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from types import MappingProxyType
from typing import Iterator, Mapping

# A quoted string up to its closing quote or the end of the line (a string
# never spans lines), or a comment up to the end of the line. Whichever of `"`
# and `#` comes first outside the previous match wins: a `#` inside a string
# is string text, a `"` inside a comment is comment text.
_BLANK_RE = re.compile(r'"[^"\n]*"?|#[^\n]*')

# text -> (clean, comments); None outside `shared()`.
_cache: dict[str, tuple[str, Mapping[int, str]]] | None = None


def _blank(text: str) -> tuple[str, dict[int, str]]:
    comments: dict[int, str] = {}
    pieces: list[str] = []
    last = 0
    line = 1
    counted = 0
    for m in _BLANK_RE.finditer(text):
        start, end = m.span()
        pieces.append(text[last:start])
        if text[start] == '"':
            if end - start >= 2 and text[end - 1] == '"':
                pieces.append('"' + " " * (end - start - 2) + '"')
            else:  # unclosed: the body runs to the end of the line
                pieces.append('"' + " " * (end - start - 1))
        else:
            line += text.count("\n", counted, start)
            counted = start
            comments[line] = m.group()
            pieces.append(" " * (end - start))
        last = end
    pieces.append(text[last:])
    return "".join(pieces), comments


def blank_comments_and_strings(text: str) -> tuple[str, Mapping[int, str]]:
    """Return (clean_text, comments_by_line).

    `clean_text` has the same length as `text` — comment bodies and quoted
    string bodies are replaced by spaces, the quotes kept — so match offsets
    still map to real line numbers. `comments_by_line` keeps each line's raw
    comment text, `#` included, for `# REVIEWED` lookups. It is read-only:
    inside `shared()` every caller gets the same one.
    """
    cache = _cache  # one read: a chain on another thread may end meanwhile
    if cache is not None:
        hit = cache.get(text)
        if hit is not None:
            return hit
    clean, comments = _blank(text)
    result = (clean, MappingProxyType(comments))
    if cache is not None:
        cache[text] = result
    return result


@contextmanager
def shared() -> Iterator[None]:
    """Keep each text's blanking until the outermost `shared()` ends."""
    global _cache
    outermost = _cache is None
    if outermost:
        _cache = {}
    try:
        yield
    finally:
        if outermost:
            _cache = None


def cached_texts() -> int:
    """How many texts the open `shared()` holds (0 outside one); for tests."""
    cache = _cache
    return 0 if cache is None else len(cache)
