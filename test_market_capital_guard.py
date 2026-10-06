"""A country that has lost every state while its war goes on stays alive with
no market capital, so `market_capital.owner = THIS` must be guarded.

The environmental movement's radicalism value (new_ideological_movements.txt)
compared market_capital.owner three times with no guard. When it was evaluated
for such a country it logged "Event target link 'market_capital' returned an
invalid object" and the same for 'owner' at each site (observer run,
2026-10-06). It now calls gw_is_market_leader, which checks
`exists = market_capital.owner` first. vanilla_known_bugs.md lists the
vanilla sites of this shape; a mod file there is a mod bug.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_READ = re.compile(r"\bmarket_capital\.owner\s*=")


def script_lines():
    for pattern in ("common/**/*.txt", "events/**/*.txt"):
        for path in sorted(ROOT.glob(pattern)):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            lines = [re.sub(r'("[^"\n]*")|#.*', lambda m: m[1] or "", line) for line in text.splitlines()]
            yield path.relative_to(ROOT).as_posix(), lines


def unguarded(lines):
    """Lines comparing market_capital.owner with no `exists = market_capital.owner` just before."""
    bad = []
    for i, line in enumerate(lines):
        if _READ.search(line):
            before = [prev.strip() for prev in lines[:i] if prev.strip()][-1:]
            if before != ["exists = market_capital.owner"]:
                bad.append(i + 1)
    return bad


class TestMarketCapitalGuard(unittest.TestCase):
    def test_every_market_capital_owner_comparison_is_guarded(self):
        bad = [f"{rel}:{n}" for rel, lines in script_lines() for n in unguarded(lines)]
        self.assertEqual(bad, [], "call gw_is_market_leader, or put exists = market_capital.owner on the line before")

    def test_the_check_sees_what_it_rejects(self):
        self.assertEqual(unguarded(["limit = {", "\tmarket_capital.owner = THIS", "}"]), [2])
        self.assertEqual(unguarded(["\texists = market_capital.owner", "", "\tmarket_capital.owner = THIS"]), [])


if __name__ == "__main__":
    unittest.main()
