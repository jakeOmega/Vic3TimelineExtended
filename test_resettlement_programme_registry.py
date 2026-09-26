"""The internal resettlement registry: every programme in one table, pinned
against every site that lists programmes by hand.

Design: docs/superpowers/specs/2026-09-26-internal-resettlement-design.md.
Adding a programme touches the PM, its loc, the recruitment rule's branch, the
programme-code switch, the transit-mortality table, the volume counter, the
politics modifier, the law gates, the Declaration line and the docs. Nothing in
the engine checks that they agree. PROGRAMMES is the single list; each test
checks one site against it, so a half-added programme fails here, naming the
site. The frontier values and the game rule are pinned here too.

Run: python3 -m unittest test_resettlement_programme_registry -v
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

VALUES = "common/script_values/resettlement_values.txt"
TRIGGERS = "common/scripted_triggers/resettlement_triggers.txt"
RULES = "common/game_rules/extra_game_rules.txt"

RULE_SETTINGS = ("internal_resettlement_enabled", "internal_resettlement_ai_voluntary",
                 "internal_resettlement_disabled")


# ---- helpers -------------------------------------------------------------------------

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def block(text, name):
    """Body of the first `name = {` block in text (comments stripped), or None."""
    text = strip_comments(text)
    m = re.search(r"(?<![\w.:$])" + re.escape(name) + r"\s*=\s*\{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def number(body, key):
    """The first `key = <number>` in body, as a float, or None."""
    m = re.search(r"(?<![\w.:])" + re.escape(key) + r"\s*=\s*(-?\d+(?:\.\d+)?)", body or "")
    return float(m.group(1)) if m else None


def squash(text):
    return " ".join((text or "").split())


def top_level_blocks(text):
    """(name, body) for every top-level `name = {` in text (comments stripped)."""
    text = strip_comments(text)
    for m in re.finditer(r"(?m)^([\w:.]+)\s*=\s*\{", text):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        yield m.group(1), text[m.end():i - 1]


_LOC = None


def loc():
    global _LOC
    if _LOC is None:
        _LOC = {}
        for path in sorted((ROOT / "localization/english").glob("*.yml")):
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                m = re.match(r'\s*([\w.$]+):\d*\s+"(.*)"\s*$', line)
                if m:
                    _LOC[m.group(1)] = m.group(2)
    return _LOC


# ---- the frontier and the game rule (Task 2) -----------------------------------------

class FrontierTests(unittest.TestCase):
    def test_thresholds_are_the_specs(self):
        text = strip_comments(read(VALUES))
        self.assertRegex(text, r"(?m)^resettlement_frontier_open_base = 2\s*$")
        self.assertRegex(text, r"(?m)^resettlement_frontier_close_base = 10\s*$")

    def test_density_is_region_population_over_area(self):
        text = read(VALUES)
        pop = squash(block(text, "te_region_population"))
        self.assertIn("state_region = { every_scope_state = { add = state_population } }", pop)
        area = block(text, "te_region_area_km2")
        self.assertIn("var:te_region_area", area)
        self.assertEqual(number(area, "value"), 1.0, "no table yet must read as 1 km² (never a frontier)")
        density = squash(block(text, "resettlement_frontier_density"))
        self.assertIn("value = te_region_population", density)
        self.assertIn("divide = te_region_area_km2", density)

    def test_both_thresholds_scale_with_the_crowding_modifier(self):
        text = read(VALUES)
        self.assertIn("modifier:state_migration_crowding_density_mult",
                      block(text, "resettlement_crowding_scale"))
        for name, base in (("resettlement_frontier_open_density", "resettlement_frontier_open_base"),
                           ("resettlement_frontier_close_density", "resettlement_frontier_close_base")):
            body = squash(block(text, name))
            self.assertIn(f"value = {base}", body)
            self.assertIn("multiply = resettlement_crowding_scale", body)

    def test_margins_are_threshold_minus_density(self):
        text = read(VALUES)
        for margin, threshold in (("resettlement_frontier_open_margin", "resettlement_frontier_open_density"),
                                  ("resettlement_frontier_close_margin", "resettlement_frontier_close_density")):
            body = squash(block(text, margin))
            self.assertIn(f"value = {threshold}", body)
            self.assertIn("subtract = resettlement_frontier_density", body)

    def test_frontier_triggers_read_the_margins(self):
        text = read(TRIGGERS)
        self.assertIn("resettlement_frontier_open_margin > 0",
                      squash(block(text, "resettlement_state_is_open_frontier")))
        self.assertIn("resettlement_frontier_close_margin > 0",
                      squash(block(text, "resettlement_state_frontier_still_open")))

    def test_rule_triggers(self):
        text = read(TRIGGERS)
        self.assertIn("NOT = { has_game_rule = internal_resettlement_disabled }",
                      squash(block(text, "resettlement_system_enabled")))
        voluntary = squash(block(text, "resettlement_ai_voluntary_only"))
        self.assertIn("is_ai = yes", voluntary)
        self.assertIn("has_game_rule = internal_resettlement_ai_voluntary", voluntary)

    def test_rule_has_three_settings_default_enabled(self):
        body = block(read(RULES), "internal_resettlement_rule")
        self.assertIsNotNone(body)
        self.assertIn("default = internal_resettlement_enabled", squash(body))
        for setting in RULE_SETTINGS:
            self.assertIn(f"flag = {setting}", squash(block(body, setting)))

    def test_rule_is_localized(self):
        L = loc()
        self.assertIn("rule_internal_resettlement_rule", L)
        for setting in RULE_SETTINGS:
            self.assertIn(f"setting_{setting}", L)
            self.assertIn(f"setting_{setting}_desc", L)


if __name__ == "__main__":
    unittest.main()
