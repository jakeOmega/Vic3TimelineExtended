# -*- coding: utf-8 -*-
"""A country's flag is drawn once: a flag widget beside a name prints the name
with GetNameNoFlag.

`Country.GetName` draws a small flag in front of the name. The 2026-10-27 GUI
audit's follow-up put a flag widget beside the country names in the UN's
Delegations, the covert networks, operation cards and known operations, the
Cultural Hegemony leaderboard and the Banking balance sheet, and each of them
showed two flags side by side (play-test, 2026-10-28). `GetNameNoFlag` keeps
the name's link and hover and drops its flag.

This scans every `.gui` file for a flag widget and the texts drawn after it in
the same row (its next 60 lines), resolving loc keys, `$key$` splices and
SelectLocalization choices, and fails on a country's `GetName`. A text built
by a scripted GUI is checked by name below.

Run: python3 -m unittest test_gui_flag_names -v
"""

import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
LOC = os.path.join(REPO, "localization", "english")
FLAG = re.compile(r"^\s*(tiny_flag|small_flag|flag)\s*=\s*\{")
# A country's name with its flag: a name read off a country, not an
# attitude's or a law's.
COUNTRY_NAME = re.compile(r"(Country|GetCountry|GetOwner|GetLeader|GetPlayer|sCountry\('\w+'\))\.GetName\]")
WINDOW = 60
# Rows whose text is a scripted GUI's ExecuteTooltip: the keys it prints.
SCRIPTED_ROWS = {
    "un_chamber_deleg_row_sgui": r"je_un_chamber_deleg_band_\w+",
}


def _loc():
    out = {}
    for path in glob.glob(os.path.join(LOC, "**", "*.yml"), recursive=True):
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                m = re.match(r'^ ([\w.\-]+):\d* "(.*)"\s*$', line)
                if m:
                    out[m.group(1)] = m.group(2)
    return out


class FlagNameTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = _loc()

    def expand(self, text, depth=0):
        if depth > 5:
            return text
        text = re.sub(r"\$(\w+)\$", lambda m: self.expand(self.loc.get(m.group(1), ""), depth + 1), text)
        for key in re.findall(r"'(\w+)'", text):
            if key in self.loc:
                text += " || " + self.expand(self.loc[key], depth + 1)
        return text

    def test_a_flag_widget_is_not_followed_by_a_flagged_name(self):
        seen = 0
        for path in sorted(glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True)):
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                lines = f.read().split("\n")
            for i, line in enumerate(lines):
                if not FLAG.match(line):
                    continue
                seen += 1
                for j in range(i + 1, min(len(lines), i + WINDOW)):
                    m = re.search(r'\btext = "([^"]*)"', lines[j])
                    if not m:
                        continue
                    text = m.group(1)
                    shown = text if text.startswith("[") else self.expand(self.loc.get(text, ""))
                    with self.subTest(file=os.path.relpath(path, REPO), line=j + 1, text=text[:80]):
                        self.assertNotRegex(shown, COUNTRY_NAME)
        self.assertGreater(seen, 40)

    def test_scripted_rows_print_the_name_without_its_flag(self):
        for sgui, keys in SCRIPTED_ROWS.items():
            found = [k for k in self.loc if re.fullmatch(keys, k)]
            self.assertTrue(found, sgui)
            for key in found:
                with self.subTest(key=key):
                    self.assertNotRegex(self.loc[key], COUNTRY_NAME)
                    self.assertIn("GetNameNoFlag]", self.loc[key])


if __name__ == "__main__":
    unittest.main()
