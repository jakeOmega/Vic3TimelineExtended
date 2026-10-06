"""Market links can come back invalid, so a comparison through them is guarded.

A country that has lost every state while its war goes on has no market
capital, and in the 2026-10-06 observer run markets and states also turned up
whose `market.owner` or `owner.market_capital` link returned an invalid object
(vanilla's own route-graphics triggers logged it too). Every unguarded mod
comparison through those links then logged "Event target link ... returned an
invalid object": about 1,300 lines from the environmental movement, the Space
Program and warming pulses, the tax triggers and the currency peg in the first
three minutes after a relaunch.

Each comparison of `market_capital.owner`, `market.owner` or
`owner.market_capital` (with any scope prefix) needs `exists = <the same path>`
on the line before; gw_is_market_leader wraps the commonest one.
vanilla_known_bugs.md lists the vanilla sites of this shape.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_READ = re.compile(r"([\w:]+(?:\.[\w:]+)*\.)?(market_capital\.owner|market\.owner|owner\.market_capital)\s*(!?=)\s*(\S)")


def script_lines():
    for pattern in ("common/**/*.txt", "events/**/*.txt"):
        for path in sorted(ROOT.glob(pattern)):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            lines = [re.sub(r'("[^"\n]*")|#.*', lambda m: m[1] or "", line) for line in text.splitlines()]
            yield path.relative_to(ROOT).as_posix(), lines


def unguarded(lines):
    """Lines comparing through a market link with no `exists = <path>` on the line before."""
    bad = []
    for i, line in enumerate(lines):
        for m in _READ.finditer(line):
            if m[4] == "{":  # a scope switch, not a comparison
                continue
            if line[:m.start()].rstrip().endswith("exists ="):
                continue
            path = (m[1] or "") + m[2]
            before = [prev.strip() for prev in lines[:i] if prev.strip()][-1:]
            if not before or not re.search(r"\bexists\s*=\s*" + re.escape(path) + r"(?![\w.])", before[0]):
                bad.append(i + 1)
    return bad


class TestMarketCapitalGuard(unittest.TestCase):
    def test_every_market_link_comparison_is_guarded(self):
        bad = [f"{rel}:{n}" for rel, lines in script_lines() for n in unguarded(lines)]
        self.assertEqual(bad, [], "put exists = <the same path> on the line before (or call gw_is_market_leader)")

    def test_the_check_sees_what_it_rejects(self):
        self.assertEqual(unguarded(["limit = {", "\tmarket_capital.owner = THIS", "}"]), [2])
        self.assertEqual(unguarded(["\texists = market_capital.owner", "", "\tmarket_capital.owner = THIS"]), [])
        self.assertEqual(unguarded(["\texists = market", "\tmarket.owner = this"]), [2])
        self.assertEqual(unguarded(["\texists = scope:t.market.owner", "\tscope:t.market.owner = this"]), [])
        self.assertEqual(unguarded(["\texists = market.owner", "\tscope:t.market.owner = this"]), [2])
        self.assertEqual(unguarded(["\texists = owner.market_capital", "\tNOT = { owner.market_capital = THIS }"]), [])
        self.assertEqual(unguarded(["\tscope:market.owner = { x = y }"]), [])


if __name__ == "__main__":
    unittest.main()
