"""The assimilation cultures' yearly rate: the engine's figures it restates, and the formula.

Design: docs/superpowers/specs/2026-11-25-assimilation-cultures-design.md, § The pass, step 5. The fraction of a taken
pop that converts in a year is

    te_hc_monthly_rate x te_hc_months                      (the engine's ASSIMILATION_RATE, 0.002 a month, x 12)
    x max(0, 1 + the state's state_assimilation_mult)
    x max(0, 1 + the owner's country_assimilation_<status>_mult)
    x (1 - the pop's pop_radical_fraction)
    x max(0, 1 - te_hc_fervor_effect x the culture's culture_current_fervor)   (the mod's define, 0.0075 a point)
    x te_hc_homeland_factor in a homeland of the culture   (the engine's ASSIMILATION_IN_HOMELAND_MULT, 0.75)

held between 0 and te_hc_rate_cap (one half). It reads the engine's own sums, so every law, institution and decree
that speeds assimilation speeds this too. Each factor is held at 0 on its own: two sums below -100% would otherwise
multiply into a positive rate (Review Focus 3, Clade Citizenship's -300%). With no modifiers that is 2.4% a year; at
the +690% of the owner's 2039 New York 19%.

`pop_rate` is a Python twin of the formula built from the figures the values file states, for the spec's rates; the
script value itself is run through the pass test's interpreter (test_assimilation_cultures_pass.py) and held to the
twin. The figures the pass restates are pinned to the define files: the fervor effect to the mod's always, the
monthly rate and the homeland factor to vanilla's where the game is installed.

Run: python3 -m pytest test_assimilation_cultures_values.py
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from test_assimilation_cultures_pass import (  # noqa: E402
    SHARE, STATUSES, VALUES, World, Interp, code, country_modifiers, parse, rate_world, script, value_in,
)

MOD_DEFINES = ROOT / "common/defines"
FIGURES = {
    "te_hc_monthly_rate": 0.002,
    "te_hc_months": 12,
    "te_hc_fervor_effect": 0.0075,
    "te_hc_homeland_factor": 0.75,
    "te_hc_rate_cap": 0.5,
}


def figure(name):
    """A figure the values file states as a bare top-level `name = N` line."""
    m = re.search(rf"(?m)^{name}\s*=\s*(-?[\d.]+)\s*$", code(VALUES))
    if m is None:
        raise AssertionError(f"{name} is not a bare `{name} = N` line in {VALUES.name}")
    return float(m.group(1))


def pop_rate(state_mult, status_mult=0, radicals=0, fervor=0, homeland=False):
    """The twin of te_hc_pop_rate, from the figures the values file states."""
    rate = figure("te_hc_monthly_rate") * figure("te_hc_months")
    rate *= max(0.0, 1 + state_mult)
    rate *= max(0.0, 1 + status_mult)
    rate *= 1 - radicals
    rate *= max(0.0, 1 - figure("te_hc_fervor_effect") * fervor)
    if homeland:
        rate *= figure("te_hc_homeland_factor")
    return min(max(rate, 0.0), figure("te_hc_rate_cap"))


def callees(text):
    """Every te_hc_ script value `text` reads (dotted reads included), transitively."""
    values = script().values
    seen, todo = [], [text]
    while todo:
        for name in re.findall(r"\b(te_hc_\w+)", todo.pop()):
            if name in values and name not in seen:
                seen.append(name)
                todo.append(values[name][1])
    return seen


def script_rate(state_mult, status_mult=0, radicals=0, fervor=0, homeland=False, status="full_acceptance"):
    world = rate_world(state_mult=state_mult, status=status, status_mult=status_mult, radicals=radicals,
                       fervor=fervor, homeland=homeland)
    return value_in(world, "te_hc_pop_rate")


def define(text, name):
    m = re.search(rf"(?m)^\s*{name}\s*=\s*(-?[\d.]+)", re.sub(r"#[^\n]*", "", text))
    return float(m.group(1)) if m else None


def installed_defines():
    """The text of the installed game's defines, or None on a machine without the game (CI)."""
    try:
        import path_constants
        game = Path(path_constants.base_game_path) / "game"
    except Exception:  # noqa: BLE001 - no paths configured at all
        return None
    folder = game / "common" / "defines"
    if not (game / "common" / "country_definitions").is_dir() or not folder.is_dir():
        return None
    return "\n".join(p.read_text(encoding="utf-8-sig", errors="replace") for p in sorted(folder.glob("*.txt")))


class FiguresTest(unittest.TestCase):
    def test_the_engine_figures(self):
        for name, value in FIGURES.items():
            with self.subTest(name=name):
                self.assertAlmostEqual(figure(name), value)

    def test_the_spec_rates(self):
        self.assertAlmostEqual(pop_rate(0), 0.024)
        self.assertAlmostEqual(pop_rate(1.0), 0.048)
        self.assertAlmostEqual(pop_rate(6.9), 0.1896)
        self.assertAlmostEqual(pop_rate(6.9 - 1), 0.1656)      # Morphological Freedom
        self.assertAlmostEqual(pop_rate(6.9 + 2), 0.2376)      # Prescribed Form

    def test_a_sum_below_minus_one_gives_zero(self):
        # Review Focus 3: Clade Citizenship's -300% in a country with +100%.
        self.assertEqual(pop_rate(1.0 - 3), 0)
        self.assertEqual(script_rate(1.0 - 3), 0)
        # Two sums below -100% each: held at 0 one by one, never a positive product.
        self.assertEqual(script_rate(-3.0, status_mult=-3.0), 0)
        self.assertEqual(script_rate(-3.0, fervor=200), 0)
        self.assertEqual(script_rate(0.0, status_mult=-2.0), 0)

    def test_the_cap(self):
        self.assertEqual(pop_rate(40), 0.5)
        self.assertAlmostEqual(script_rate(40), 0.5)

    def test_radicals_fervor_and_homeland(self):
        self.assertAlmostEqual(pop_rate(0, radicals=0.5), 0.012)
        self.assertAlmostEqual(pop_rate(0, fervor=100), 0.006)
        self.assertAlmostEqual(pop_rate(0, homeland=True), 0.018)

    def test_the_script_value_has_each_factor_and_both_clamps(self):
        body = parse(script().values["te_hc_pop_rate"][1])
        top = {(n.key, n.value) for n in body if n.children is None}
        self.assertTrue([v for k, v in top if k == "min" and re.fullmatch(r"0(\.0*)?", v or "")],
                        "te_hc_pop_rate is not held at 0 at the end")
        self.assertIn(("max", "te_hc_rate_cap"), top, "te_hc_pop_rate is not capped at te_hc_rate_cap")
        # The figures by name, in te_hc_pop_rate or a te_hc_ value it reads (te_hc_status_mult, say); none restated.
        values = script().values
        named = [values["te_hc_pop_rate"][1]] + [values[name][1] for name in callees(values["te_hc_pop_rate"][1])
                                                 if values[name][0] == "block" and name != "te_hc_pop_rate"]
        text = " ".join(named)
        for name in ("te_hc_monthly_rate", "te_hc_months", "te_hc_fervor_effect", "te_hc_homeland_factor"):
            self.assertRegex(text, rf"\b{name}\b")
        for number in ("0.002", "12", "0.0075", "0.75", "0.5"):
            self.assertNotRegex(text, rf"(?<![\w.]){re.escape(number)}(?![\w.])", "restated, not named")
        # The script value run against the twin: each factor, for the pop's own status, each held at 0.
        cases = [
            (0, 0, 0, 0, False), (1.0, 0, 0, 0, False), (6.9, 0, 0, 0, False), (5.9, 0, 0, 0, False),
            (8.9, 0, 0, 0, False), (-2.0, 0, 0, 0, False), (40, 0, 0, 0, False), (0, 0, 0.5, 0, False),
            (0, 0, 0, 100, False), (0, 0, 0, 0, True), (1.0, -0.5, 0.25, 40, True), (2.0, 1.0, 0.1, 20, True),
            (0, 1.0, 0, 0, False), (0, -0.5, 0, 0, False), (0, -2.0, 0, 0, False), (-3.0, -3.0, 0, 0, False),
            (-3.0, 0, 0, 200, False), (0, 0, 0, 150, False), (0, 0, 1.0, 0, False), (-1.0, 0, 0, 0, True),
        ]
        for status in STATUSES:
            for state_mult, status_mult, radicals, fervor, homeland in cases:
                with self.subTest(status=status, state=state_mult, mult=status_mult, radicals=radicals,
                                  fervor=fervor, homeland=homeland):
                    self.assertAlmostEqual(
                        script_rate(state_mult, status_mult, radicals, fervor, homeland, status=status),
                        pop_rate(state_mult, status_mult, radicals, fervor, homeland))

    def test_the_crossing_share_is_the_law_line_read_capped_at_one(self):
        # te_hc_cross_share (country): the owner's country_cross_heritage_assimilation_add, read capped at 100%.
        for line, share in ((0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (1.5, 1.0), (3.0, 1.0)):
            with self.subTest(line=line):
                w = World()
                w.culture("C_HOST", "european", "l_host")
                w.country("OWNER", ["C_HOST"], modifiers=country_modifiers(cross=line))
                self.assertEqual(w.ents["OWNER"].modifiers[SHARE], line)
                interp = Interp(script(), w, saved={"te_hc_owner": "OWNER"})
                self.assertAlmostEqual(interp.value("te_hc_cross_share", ["OWNER"]), share)

    def test_the_figures_match_the_defines(self):
        mod = "\n".join(p.read_text(encoding="utf-8-sig") for p in sorted(MOD_DEFINES.glob("*.txt")))
        fervor = define(mod, "CULTURAL_FERVOR_ASSIMILATIOM_EFFECT")
        self.assertIsNotNone(fervor, "the mod no longer sets CULTURAL_FERVOR_ASSIMILATIOM_EFFECT")
        self.assertAlmostEqual(figure("te_hc_fervor_effect"), fervor)
        vanilla = installed_defines()
        if vanilla is None:
            self.skipTest("no installed game: ASSIMILATION_RATE and ASSIMILATION_IN_HOMELAND_MULT not read")
        for name, ours in (("ASSIMILATION_RATE", "te_hc_monthly_rate"),
                           ("ASSIMILATION_IN_HOMELAND_MULT", "te_hc_homeland_factor")):
            with self.subTest(define=name):
                # The mod's own line where it sets one, as the engine reads it; vanilla's otherwise.
                engine = define(mod, name)
                engine = define(vanilla, name) if engine is None else engine
                self.assertIsNotNone(engine, f"{name} is in neither the mod's nor vanilla's defines")
                self.assertAlmostEqual(figure(ours), engine)


if __name__ == "__main__":
    unittest.main()
