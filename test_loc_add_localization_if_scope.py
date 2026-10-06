"""A key named in AddLocalizationIf( cond, 'key' ) renders without SCOPE.

The Subjugate action's tooltip (te_subjugation_strength_sufficient_tt, #710)
picked its power-bloc identity line with AddLocalizationIf, and each line read
SCOPE.ScriptValue(...) and SCOPE.sCountry('target_country'). The parent's own
SCOPE reads worked (it chose the right line), but inside the named key SCOPE
was gone: every render logged "Promote 'SCOPE' returned nullptr" three times
and the line came out blank (2,796 lines of each in four seconds, observer
launch 2026-10-06). SelectLocalization( cond, 'key', 'te_tt_blank' ) passes
SCOPE on; vanilla's Zanzibar notifications use it with SCOPE-reading keys.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

_LOC_LINE = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\d*\s*"(.*)"\s*$')
_CALL = re.compile(r"AddLocalizationIf\(")
_STRING_OR_COMMENT = re.compile(r'("[^"\n]*")|#[^\n]*')


def english_loc():
    values = {}
    for path in sorted((ROOT / "localization" / "english").glob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = _LOC_LINE.match(line)
            if m:
                values[m[1]] = m[2]
    return values


def expanded(key, loc, seen=()):
    text = loc.get(key, "")
    if key in seen:
        return text
    return re.sub(r"\$([A-Za-z0-9_.\-]+)\$",
                  lambda m: expanded(m[1], loc, seen + (key,)) if m[1] in loc else m[0], text)


def named_keys(text, loc):
    """Loc keys named as string literals in each AddLocalizationIf( ... ) call."""
    found = []
    for m in _CALL.finditer(text):
        depth, j = 1, m.end()
        while depth and j < len(text):
            depth += {"(": 1, ")": -1}.get(text[j], 0)
            j += 1
        found.extend(k for k in re.findall(r"'([A-Za-z_][A-Za-z0-9_.]*)'", text[m.end():j - 1]) if k in loc)
    return found


class TestAddLocalizationIfScope(unittest.TestCase):
    def test_no_key_named_in_add_localization_if_reads_scope(self):
        loc = english_loc()
        sources = [(f"loc {k}", v) for k, v in loc.items()]
        for path in sorted((ROOT / "gui").rglob("*.gui")):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            text = "\n".join(_STRING_OR_COMMENT.sub(lambda m: m[1] or "", line) for line in text.splitlines())
            sources.append((path.relative_to(ROOT).as_posix(), text))
        bad = [f"{where}: '{key}'"
               for where, text in sources
               for key in named_keys(text, loc)
               if "[SCOPE." in expanded(key, loc)]
        self.assertEqual(bad, [], "use SelectLocalization( cond, 'key', 'te_tt_blank' ), which passes SCOPE on")

    def test_the_check_sees_what_it_rejects(self):
        loc = {"a": "x [SCOPE.sCountry('t').GetName]", "b": "$a$!", "c": "no scope", "d": "",
               "p": "[AddLocalizationIf(EqualTo_CFixedPoint(SCOPE.ScriptValue('i'), '(CFixedPoint)1'), 'b')]"
                    "[AddLocalizationIf(Not(Is('x')), 'c')][SelectLocalization(Is('y'), 'a', 'd')]"}
        self.assertEqual(named_keys(loc["p"], loc), ["b", "c"])
        self.assertEqual([k for k in named_keys(loc["p"], loc) if "[SCOPE." in expanded(k, loc)], ["b"])


if __name__ == "__main__":
    unittest.main()
