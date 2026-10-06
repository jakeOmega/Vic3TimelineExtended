"""Script forms the game rejects at load that the Python checks would accept.

Each of these logged a load error in a real launch (2026-10-06, #757) and then
misbehaved quietly at run time:

- A numeric literal with more than five decimals. The engine logs "Badly read
  script value 4.333333" (jomini_scriptvalue.h:391), and as a divisor it then
  divides by zero; vanilla never writes more than five. The nuclear incident
  risk read 0 this way, and `banking_external_fx_protection_step` broke before it.
- A named script value as the `add` or `factor` of an event option's
  `ai_chance` modifier. `ai_chance` is MTTH-shaped and takes only numbers; the
  engine logs "Malformed token" at load, and the term can't be relied on.
  Ladder it with literal rungs instead.
- `initiator =` inside `create_diplomatic_play`. effects.log lists the field,
  but the parser rejects it ("Unexpected token: initiator") and the play is
  never created. The current scope is the initiator, as in every vanilla call.

docs/guides/scripting_best_practices.md has the background for each.
"""

import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# common/defines is Lua-like and parsed separately; its floats are not script values.
SCRIPT_GLOBS = ("common/**/*.txt", "events/**/*.txt")
EXCLUDED_DIRS = ("common/defines/",)

_STRING_OR_COMMENT = re.compile(r'("[^"\n]*")|#[^\n]*')
_TOKEN = re.compile(r'"[^"\n]*"|[{}]|>=|<=|\?=|!=|[=<>]|[^\s{}=<>!?"]+')
_LONG_DECIMAL = re.compile(r"-?\d+\.\d{6,}")
_NUMBER = re.compile(r"-?\d+(\.\d+)?")


def script_files():
    seen = set()
    for pattern in SCRIPT_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            rel = path.relative_to(ROOT).as_posix()
            if rel in seen or rel.startswith(EXCLUDED_DIRS):
                continue
            seen.add(rel)
            yield rel, path


def tokens(path):
    """(token, line) pairs with comments removed and quoted strings kept whole."""
    source = path.read_text(encoding="utf-8-sig", errors="replace")
    result = []
    for number, line in enumerate(source.split("\n"), 1):
        line = _STRING_OR_COMMENT.sub(lambda m: m[1] or "", line)
        result.extend((m[0], number) for m in _TOKEN.finditer(line))
    return result


def blocks(toks, key):
    """Yield (start line, body tokens) for every `key = { ... }` block."""
    for i in range(len(toks) - 2):
        if toks[i][0] == key and toks[i + 1][0] == "=" and toks[i + 2][0] == "{":
            depth, j = 1, i + 3
            while j < len(toks) and depth:
                depth += {"{": 1, "}": -1}.get(toks[j][0], 0)
                j += 1
            yield toks[i][1], toks[i + 3:j - 1]


def top_level(body):
    """(key, value token, line) for the clauses directly inside a block body."""
    depth, result = 0, []
    for i, (tok, line) in enumerate(body):
        if tok == "{":
            depth += 1
        elif tok == "}":
            depth -= 1
        elif depth == 0 and i + 2 < len(body) and body[i + 1][0] in ("=", "?=", ">=", "<=", ">", "<"):
            result.append((tok, body[i + 2][0], line))
    return result


class TestEngineLiteralForms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = {rel: tokens(path) for rel, path in script_files()}

    def test_no_numeric_literal_has_more_than_five_decimals(self):
        bad = [f"{rel}:{line} {tok}"
               for rel, toks in self.files.items()
               for tok, line in toks
               if not tok.startswith('"') and _LONG_DECIMAL.fullmatch(tok)]
        self.assertEqual(bad, [], "round to five decimals, or write the ratio as multiply/divide by whole numbers")

    def test_event_ai_chance_modifiers_add_only_numbers(self):
        bad = []
        for rel, toks in self.files.items():
            if not rel.startswith("events/"):
                continue
            for _, body in blocks(toks, "ai_chance"):
                for _, modifier in blocks(body, "modifier"):
                    for key, value, line in top_level(modifier):
                        if key in ("add", "factor") and not _NUMBER.fullmatch(value):
                            bad.append(f"{rel}:{line} {key} = {value}")
        self.assertEqual(bad, [], "ai_chance is MTTH-shaped: ladder a script value with literal rungs")

    def test_create_diplomatic_play_takes_its_initiator_from_scope(self):
        bad = [f"{rel}:{line}"
               for rel, toks in self.files.items()
               for _, body in blocks(toks, "create_diplomatic_play")
               for key, _, line in top_level(body)
               if key == "initiator"]
        self.assertEqual(bad, [], "run create_diplomatic_play in the initiator's scope with target_country")

    def test_the_checks_see_the_forms_they_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "sample.txt"
            sample.write_text(
                'a = { divide = 4.333333 multiply = 0.00001 }  # 1.1234567 in a comment\n'
                'b = { debug_log = "x 1.1234567" }\n'
                'c = { ai_chance = { base = 1 modifier = { trigger = { sv > 0 } add = sv } modifier = { add = 2 factor = 0.5 } } }\n'
                'd = { create_diplomatic_play = { type = dp_x initiator = scope:a add_war_goal = { initiator = x } } }\n'
                'e = { x = -1.1234567 y = { 2.1234567 } z = 0.12345 }\n',
                encoding="utf-8")
            toks = tokens(sample)
        self.assertEqual([t for t, _ in toks if _LONG_DECIMAL.fullmatch(t)], ["4.333333", "-1.1234567", "2.1234567"])
        adds = [(k, v) for _, body in blocks(toks, "ai_chance")
                for _, m in blocks(body, "modifier") for k, v, _ in top_level(m) if k in ("add", "factor")]
        self.assertEqual(adds, [("add", "sv"), ("add", "2"), ("factor", "0.5")])
        keys = [k for _, body in blocks(toks, "create_diplomatic_play") for k, _, _ in top_level(body)]
        self.assertEqual(keys, ["type", "initiator", "add_war_goal"])


if __name__ == "__main__":
    unittest.main()
