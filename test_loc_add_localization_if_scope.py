"""A key named in AddLocalizationIf( cond, 'key' ) or SelectLocalization( cond,
'key', 'other' ) renders without SCOPE.

The Subjugate action's tooltip (te_subjugation_strength_sufficient_tt, #710)
picked its power-bloc identity line with AddLocalizationIf, and each line read
SCOPE.ScriptValue(...) and SCOPE.sCountry('target_country'). The parent's own
SCOPE reads worked (it chose the right line), but inside the named key SCOPE
was gone: every render logged "Promote 'SCOPE' returned nullptr" three times
and the line came out blank (2,796 lines of each in four seconds, observer
launch 2026-10-06). #767 switched to SelectLocalization on the strength of
vanilla's Zanzibar notifications, and the France game that evening logged the
same three failures 993 times from the SelectLocalization form. So the parent
keeps every SCOPE read; a named key holds fixed text, or reads GetPlayer.

ROOT goes the same way. The Civil Rights entry's status read its months run
through ROOT.GetCountry in the parent, which worked, and again inside
je_civil_rights_months_line, named by AddLocalizationIf, where each of the six
reads logged "Promote 'ROOT' returned nullptr" (about 220 renders in 36
seconds, 2026-10-28).

THIS too. The Map Room's life-expectancy tooltip (a journal entry's
map_tooltip, the state as THIS) named te_jmap_tt_e0_value in a
SelectLocalization, and every hover logged "Promote 'THIS' returned nullptr"
and showed no figure (649 lines, 2026-11-05). Grand Monuments' tear-down and
rededicate hovers name six keys that read THIS (UNVERIFIED_THIS): a scripted
button's tooltip may keep it, and no log has shown them failing, so they wait
on an in-game look rather than a rewrite.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UNVERIFIED_THIS = {
    "gm_mon_prev_rd_sup_line", "gm_mon_prev_td_base_line", "gm_mon_prev_td_sup_line",
    "gm_prev_rd_sup_line", "gm_prev_td_base_line", "gm_prev_td_sup_line",
}
_LOST_SCOPE_BUT_THIS = re.compile(r"\b(?:SCOPE|ROOT)\.")

_LOC_LINE = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\d*\s*"(.*)"\s*$')
_CALL = re.compile(r"(?:AddLocalizationIf|SelectLocalization)\(")
_STRING_OR_COMMENT = re.compile(r'("[^"\n]*")|#[^\n]*')
_LOST_SCOPE = re.compile(r"\b(?:SCOPE|ROOT|THIS)\.")


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
    """Loc keys named as string literals in each AddLocalizationIf( ... ) or SelectLocalization( ... ) call."""
    found = []
    for m in _CALL.finditer(text):
        depth, j = 1, m.end()
        while depth and j < len(text):
            depth += {"(": 1, ")": -1}.get(text[j], 0)
            j += 1
        found.extend(k for k in re.findall(r"'([A-Za-z_][A-Za-z0-9_.]*)'", text[m.end():j - 1]) if k in loc)
    return found


class TestAddLocalizationIfScope(unittest.TestCase):
    def test_no_key_named_in_add_localization_if_or_select_localization_reads_scope_root_or_this(self):
        loc = english_loc()
        sources = [(f"loc {k}", v) for k, v in loc.items()]
        for path in sorted((ROOT / "gui").rglob("*.gui")):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            text = "\n".join(_STRING_OR_COMMENT.sub(lambda m: m[1] or "", line) for line in text.splitlines())
            sources.append((path.relative_to(ROOT).as_posix(), text))
        bad = [f"{where}: '{key}'"
               for where, text in sources
               for key in named_keys(text, loc)
               if (_LOST_SCOPE_BUT_THIS if key in UNVERIFIED_THIS else _LOST_SCOPE).search(expanded(key, loc))]
        self.assertEqual(bad, [], "keep SCOPE, ROOT and THIS reads in the parent string; the named key loses them")

    def test_the_check_sees_what_it_rejects(self):
        loc = {"a": "x [SCOPE.sCountry('t').GetName]", "b": "$a$!", "c": "no scope", "d": "",
               "e": "[AddLocalizationIf(GreaterThan_CFixedPoint(ROOT.GetCountry.MakeScope.ScriptValue('m'), "
                    "'(CFixedPoint)0'), 'c')]", "f": "[GetPlayer.MakeScope.ScriptValue('m')|0]", "g": "[THIS.GetState.GetName]",
               "p": "[AddLocalizationIf(EqualTo_CFixedPoint(SCOPE.ScriptValue('i'), '(CFixedPoint)1'), 'b')]"
                    "[AddLocalizationIf(Not(Is('x')), 'c')][SelectLocalization(Is('y'), 'a', 'd')]"
                    "[AddLocalizationIf(Is('z'), 'e')][AddLocalizationIf(Is('w'), 'f')][SelectLocalization(Is('v'), 'g', 'c')]"}
        self.assertEqual(named_keys(loc["p"], loc), ["b", "c", "a", "d", "e", "f", "g", "c"])
        self.assertEqual([k for k in named_keys(loc["p"], loc) if _LOST_SCOPE.search(expanded(k, loc))],
                         ["b", "a", "e", "g"])


if __name__ == "__main__":
    unittest.main()
