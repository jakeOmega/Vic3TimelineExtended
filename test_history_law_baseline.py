"""The history law baseline reaches decentralized nations too (common/history/extra_history.txt).

GLOBAL's every_country gives every country a tech-free law in each group the
mod adds, and it never reached decentralized nations: all 158 kept each group's
first law, five of them barred to them, in the first new game after #1408
(2026-11-05). They take no events and no monthly pulse, so nothing mends them
later. The every_decentralized_country block repeats the baseline; these tests
keep the two lists the same and the self-check honest.

No game install needed.
"""

import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.join(REPO, "common", "history", "extra_history.txt")
SELFCHECK = os.path.join(REPO, "common", "on_actions", "te_decentralized_laws_selfcheck_on_actions.txt")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _block(text, opener):
    """The body of the first block opened by a line that is exactly `opener`."""
    m = re.search(r"(?m)^" + re.escape(opener) + r"\s*$", text)
    if not m:
        raise AssertionError(f"no {opener.strip()!r} block")
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return text[m.end():i - 1]


def _top_level_laws(body):
    """activate_law lines that are the block's own children (not inside an if)."""
    return re.findall(r"(?m)^\t\tactivate_law = law_type:(\w+)", body)


def _law_groups():
    groups = {}
    for path in glob.glob(os.path.join(REPO, "common", "laws", "*.txt")):
        law = None
        for line in _read(path).split("\n"):
            m = re.match(r"^(law_\w+) = \{", line)
            if m:
                law = m.group(1)
            m = re.match(r"^\tgroup = (lawgroup_\w+)", line)
            if m and law:
                groups[law] = m.group(1)
    return groups


class HistoryLawBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = _read(HISTORY)
        cls.every = _top_level_laws(_block(text, "\tevery_country = {"))
        cls.decentralized = _top_level_laws(_block(text, "\tevery_decentralized_country = {"))

    def test_the_baseline_is_there(self):
        self.assertIn("law_minority_rights_discrimination", self.every)
        self.assertGreaterEqual(len(self.every), 15)

    def test_decentralized_nations_take_the_same_baseline(self):
        self.assertEqual(self.decentralized, self.every)

    def test_the_self_check_names_laws_the_baseline_replaces(self):
        groups = _law_groups()
        baseline_groups = {groups[law] for law in self.every}
        checked = re.findall(r"has_law = law_type:(\w+)", _read(SELFCHECK))
        self.assertEqual(len(checked), 5)
        for law in checked:
            self.assertIn(groups[law], baseline_groups, law)
            self.assertNotIn(law, self.every, law)


if __name__ == "__main__":
    unittest.main()
