"""Every non-constant divisor in the mod's Transfer Money article is floored.

The mod overrides vanilla's common/treaty_articles/05_transfer_money.txt whole,
and its inherent_accept_score divided by `gdp` and by the article's quantity
with no floor. A country that has lost its last state has a GDP of 0, and the
engine logged "Div/0 near ...05_transfer_money.txt:149" (the block's opening
line, not the divide) 6,510 times in the 2026-10-10 observer run, about a sixth
of that run's error.log. The registry had it filed as vanilla.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
ARTICLE = os.path.join(REPO, "common", "treaty_articles", "05_transfer_money.txt")


def _text():
    with open(ARTICLE, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


class DivisorTests(unittest.TestCase):
    def test_no_bare_variable_divisor(self):
        bare = [m.group(1) for m in re.finditer(r"\bdivide\s*=\s*([^\s{][^\s]*)", _text())
                if not re.fullmatch(r"-?\d+(\.\d+)?", m.group(1))]
        self.assertEqual(bare, [])

    def test_block_divisors_have_a_floor(self):
        text = _text()
        for m in re.finditer(r"\bdivide\s*=\s*\{([^{}]*)\}", text):
            with self.subTest(divisor=m.group(1).strip()):
                self.assertRegex(m.group(1), r"\bmin\s*=\s*1\b")

    def test_the_gdp_tiers_are_still_there(self):
        self.assertEqual(len(re.findall(r"divide = \{ value = gdp min = 1 \}", _text())), 10)


if __name__ == "__main__":
    unittest.main()
