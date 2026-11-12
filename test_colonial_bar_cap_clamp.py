"""The colonial stability bar's monthly cap is a clamp at the end of its monthly_progress, not a 23rd line.

The bar sums its 22 leaves and then clamps the sum to +/- colonial_stability_drift_cap. Until 2026-11-12 the cap was
a last line, colonial_stability_term_cap, the capped total minus the uncapped one, which evaluated every leaf twice
more each month: 641 ms of the bar's 1,035 ms in 30 days of a 1931 game (docs/audits/late_game_performance.md).

The clamp moves the bar by the same amount: clamp(sum of the leaves). colonial_stability_drift_total, which the
snapshot and the history chart read, clamps the same leaves (through the group sums) with the same two values, so
the two stay equal by construction. These tests keep both halves of that.

Run: python3 -m unittest test_colonial_bar_cap_clamp -v
"""
import re
import unittest
from collections import Counter
from pathlib import Path

from je_test_helpers import entry_text, field, strip_comments

ROOT = Path(__file__).resolve().parent
BARS = ROOT / "common/scripted_progress_bars/extra_progress_bars.txt"
VALUES = ROOT / "common/script_values/colonial_empire_values.txt"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _flat(text: str) -> str:
    return " ".join(text.split())


def _top_level_statements(body: str) -> list[str]:
    """The block's own statements, in order: `key = value` or `key = { ... }`, each flattened."""
    out, depth = [], 0
    tokens = re.finditer(r"\{|\}|[^\s{}]+", strip_comments(body))
    current: list[str] = []
    for tok in tokens:
        t = tok.group(0)
        if t == "{":
            depth += 1
        elif t == "}":
            depth -= 1
        current.append(t)
        # A statement ends at depth 0 once it has a key, `=` and a value (a scalar, or a closed block).
        if depth == 0 and len(current) >= 3 and current[1] == "=" and (current[2] != "{" or t == "}"):
            out.append(" ".join(current))
            current = []
    return out


class ColonialBarCapClamp(unittest.TestCase):
    def setUp(self):
        self.progress = field(entry_text(_read(BARS), "colonial_stability_bar"), "monthly_progress")
        self.values = _read(VALUES)

    def test_the_bar_ends_with_the_clamp(self):
        statements = _top_level_statements(self.progress)
        self.assertEqual(set(statements[-2:]),
                         {"max = colonial_stability_drift_cap", "min = colonial_stability_drift_floor"},
                         "the cap's clamp must be the last two lines, after every add, so it clamps the sum")
        self.assertTrue(all(s.startswith("add = {") for s in statements[:-2]),
                        "every line before the clamp is an add of one leaf")

    def test_the_old_cap_leaf_is_gone(self):
        self.assertNotRegex(self.values, r"(?m)^colonial_stability_term_cap\s*=")
        for sub in ("common", "events", "gui"):
            for path in sorted((ROOT / sub).rglob("*")):
                if path.suffix in (".txt", ".gui"):
                    with self.subTest(file=path.relative_to(ROOT).as_posix()):
                        self.assertNotIn("colonial_stability_term_cap", strip_comments(_read(path)))

    def test_the_floor_is_the_cap_negated(self):
        self.assertRegex(self.values, r"(?m)^colonial_stability_drift_cap = [\d.]+$")
        self.assertEqual(_flat(entry_text(self.values, "colonial_stability_drift_floor")),
                         "value = colonial_stability_drift_cap multiply = -1")

    def test_the_total_clamps_with_the_same_two_values(self):
        self.assertEqual(_flat(entry_text(self.values, "colonial_stability_drift_total")),
                         "value = colonial_stability_drift_uncapped max = colonial_stability_drift_cap "
                         "min = colonial_stability_drift_floor")

    def test_the_bar_adds_the_leaves_the_uncapped_total_adds(self):
        """Each leaf once in the bar and once in the uncapped total, through its group sum."""
        bar = Counter(re.findall(r"value = owner\.(colonial_stability_term_\w+)", _flat(self.progress)))
        groups = re.findall(r"(?:value|add) = (colonial_stability_drift_\w+)",
                            _flat(entry_text(self.values, "colonial_stability_drift_uncapped")))
        total: Counter = Counter()
        for group in groups:
            total.update(re.findall(r"(?:value|add) = (colonial_stability_term_\w+)",
                                    _flat(entry_text(self.values, group))))
        self.assertEqual(len(bar), 22)
        self.assertEqual(bar, total)


if __name__ == "__main__":
    unittest.main()
