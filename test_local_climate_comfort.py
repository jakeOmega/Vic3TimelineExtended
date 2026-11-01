"""Local Climate: comfort (docs/superpowers/specs/2026-11-01-local-climate-design.md § 5, § 6).

The four relief types and the technologies that carry them, the comfort formula and its
calibration, and the modifier that applies the penalty.

    python3 test_local_climate_comfort.py
"""
import contextlib
import importlib.util
import io
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TECH = ROOT / "common" / "technology" / "technologies"
TYPES = ROOT / "common" / "modifier_type_definitions" / "local_climate_modifier_types.txt"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cal = load("local_climate_calibration", "scripts/analysis/local_climate_calibration.py")
gen = load("gen_local_climate", "scripts/generators/gen_local_climate.py")
VALUES = ROOT / "common" / "script_values" / "local_climate_values.txt"

# Spec § 5 and the plan's Task 5: the tuning constants at the head of local_climate_values.txt.
CONSTANTS = {
    "te_climate_heat_start": 23, "te_climate_humidity_factor": 0.33, "te_climate_heat_weight": 1,
    "te_climate_cold_start": 0, "te_climate_cold_weight": 0.8, "te_climate_dry_per_class": 8,
    "te_climate_malaria_per_class": 2.5, "te_climate_penalty_max": 40, "te_climate_amp_low_lat": 30,
    "te_climate_amp_high_lat": 66.5, "te_climate_amp_max": 2.5,
}
# Each term's raw value and the relief that eases it (the dry term's is water).
TERMS = {"heat": "heat", "cold": "cold", "dry": "water", "disease": "disease"}

KINDS = ("heat", "cold", "water", "disease")
# Spec § 5.2 as the owner left it on 2026-11-01: the historical eras' stage by era 7, the modern by
# era 10, everything by era 13; malaria gone by era 4.
STAGES = {"cold": {7: 0.6, 10: 0.8, 13: 1.0}, "heat": {7: 0.8, 10: 0.9, 13: 1.0},
          "water": {7: 0.7, 10: 0.85, 13: 1.0}, "disease": {4: 1.0, 13: 1.0}}


def loc_value(key):
    for path in (ROOT / "localization" / "english").glob("*.yml"):
        m = re.search(rf'(?m)^ {re.escape(key)}:\d* "(.*)"\s*$', path.read_text(encoding="utf-8-sig"))
        if m:
            return m.group(1)
    return None


def top_block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        if c == "#":
            i = text.index("\n", i)
            continue
        depth += {"{": 1, "}": -1}.get(c, 0)
        i += 1
    return text[m.end():i - 1]


class Relief(unittest.TestCase):
    def test_relief_types_registered(self):
        text = TYPES.read_text(encoding="utf-8-sig")
        for kind in KINDS:
            name = f"state_climate_{kind}_relief_add"
            body = top_block(text, name)
            self.assertIsNotNone(body, name)
            for field in ("percent = yes", "script_only = yes", "color = good"):
                self.assertIn(field, body, (name, field))
            self.assertIsNotNone(loc_value(name), name)
            self.assertIn("[concept_local_climate]", loc_value(f"{name}_desc") or "", name)

    def test_relief_schedule(self):
        schedule = cal.relief_schedule()
        for kind, stages in STAGES.items():
            for era, target in stages.items():
                got = cal.relief_at(schedule, kind, era)
                if target == 1.0:
                    self.assertAlmostEqual(got, 1.0, places=6, msg=(kind, era))
                else:
                    self.assertAlmostEqual(got, target, delta=0.05, msg=(kind, era))

    def test_relief_at_1836_is_zero(self):
        schedule = cal.relief_schedule()
        for kind in KINDS:
            self.assertEqual(cal.relief_at(schedule, kind, 1), 0.0, kind)

    def test_one_inject_per_carrier(self):
        """A carrier keeps one INJECT: a second INJECT of `modifier` on one technology is unread in game.
        (Some technologies outside Local Climate already carry two; this guards the carriers only.)"""
        carriers = {key for kind in KINDS for _, key, _ in cal.relief_schedule()[kind]}
        seen = {}
        for path in sorted(TECH.glob("*.txt")):
            for key in re.findall(r"(?m)^INJECT:(\w+) = \{", path.read_text(encoding="utf-8-sig")):
                if key in carriers:
                    self.assertNotIn(key, seen, f"{key}: INJECTed in {seen.get(key)} and {path.name}")
                    seen[key] = path.name

    def test_carrier_comments(self):
        """Each carrier line says why the technology eases that discomfort."""
        for path in sorted(TECH.glob("*.txt")):
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                if re.search(r"state_climate_\w+_relief_add\s*=", line):
                    self.assertIn("#", line, f"{path.name}: {line.strip()}")


def squash(body):
    """A script body with comments dropped and whitespace collapsed to single spaces."""
    return " ".join(re.sub(r"#[^\n]*", "", body).split())


def values_body(name):
    body = top_block(VALUES.read_text(encoding="utf-8-sig"), name)
    if body is None:
        raise AssertionError(f"{name} is not defined in {VALUES.name}")
    return squash(body)


def neutral_row():
    """A region with no row: the generator's neutral default for every field."""
    defaults = {field: default for _, field, default, _ in gen.VALUES if field}
    return gen.Row(state="STATE_NO_ROW", ref_place="", reason="", **defaults)


class Formula(unittest.TestCase):
    """The comfort formula's script values and their Python mirror (spec § 5, § 6)."""

    @classmethod
    def setUpClass(cls):
        cls.c = cal.load_constants()
        cls.s = cal.relief_schedule()
        cls.rows = {r.state: r for r in gen.load_rows()}

    def penalty(self, state, era, warming=0.0):
        return cal.terms(self.rows[state], era, self.c, self.s, warming)["penalty"]

    def test_values_file_bom(self):
        raw = VALUES.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "needs a UTF-8 BOM")
        self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"), "doubled BOM")

    def test_constants_match_script(self):
        self.assertEqual(cal.load_constants(VALUES), CONSTANTS)

    def test_penalty_body_names_every_term(self):
        body = values_body("te_climate_penalty")
        for kind in TERMS:
            self.assertIn(f"add = te_climate_{kind}_term", body, kind)
        self.assertIn("limit = { te_climate_has_record > 0 }", body)
        self.assertIn("max = te_climate_penalty_max", body)
        self.assertTrue(body.endswith("min = 0"), body)
        for kind, relief in TERMS.items():
            term = values_body(f"te_climate_{kind}_term")
            self.assertEqual(term, f"value = te_climate_{kind}_raw "
                                   f"multiply = {{ value = 1 subtract = te_climate_relief_{relief} }}", kind)

    def test_relief_values_clamp(self):
        for kind in KINDS:
            body = values_body(f"te_climate_relief_{kind}")
            self.assertTrue(body.startswith(f"value = modifier:state_climate_{kind}_relief_add"), kind)
            self.assertTrue(body.endswith("min = 0 max = 1"), (kind, body))
        # Malaria Prevention's relief is the census's Malaria Control (owner, 2026-11-01).
        self.assertIn("add = modifier:state_malaria_control_add", values_body("te_climate_relief_disease"))

    def test_warming_shifts_both_seasons(self):
        self.assertEqual(values_body("te_climate_warming"),
                         "value = temperature_anomaly_display multiply = te_climate_amplification")
        self.assertEqual(values_body("te_climate_summer_eff"),
                         "value = te_climate_summer_mean add = te_climate_warming")
        self.assertEqual(values_body("te_climate_winter_eff"),
                         "value = te_climate_winter_mean add = te_climate_warming")

    def test_amplification(self):
        c = self.c
        for lat in (0, 15, -30, 30):
            self.assertAlmostEqual(cal.amplification(lat, c), 1.0, places=9, msg=lat)
        for lat in (66.5, -66.5, 80, -90):
            self.assertAlmostEqual(cal.amplification(lat, c), 2.5, places=9, msg=lat)
        self.assertAlmostEqual(cal.amplification(48.25, c), 1.75, places=9)
        self.assertAlmostEqual(cal.amplification(-48.25, c), 1.75, places=9)

    def test_default_record_has_no_penalty(self):
        self.assertEqual(cal.terms(neutral_row(), 1, self.c, self.s)["penalty"], 0)

    def test_anchor_targets(self):
        """Spec § 5.3's targets, in attraction points (1 SoL = 2), with no warming."""
        p = self.penalty
        ranges = (
            ("STATE_GEORGIA", 1, 12, 16), ("STATE_GEORGIA", 7, 1, 4), ("STATE_GEORGIA", 10, 0, 2),
            ("STATE_WEST_BENGAL", 1, 20, 25),
            ("STATE_HOME_COUNTIES", 1, 0, 1), ("STATE_ILE_DE_FRANCE", 1, 0, 1),
            ("STATE_CATALONIA", 1, 1, 5), ("STATE_LAZIO", 1, 7, 11), ("STATE_LAZIO", 4, 0, 4),
            ("STATE_SAHARA", 1, 24, 34), ("STATE_ARIZONA", 1, 24, 34),
            ("STATE_SAHARA", 10, 0, 6), ("STATE_ARIZONA", 10, 0, 6),
            ("STATE_YAKUTSK", 1, 26, 34), ("STATE_YAKUTSK", 7, 10, 16), ("STATE_YAKUTSK", 10, 4, 8),
            ("STATE_MASSACHUSETTS", 1, 0, 3),
        )
        for state, era, low, high in ranges:
            with self.subTest(state=state, era=era):
                self.assertTrue(low <= p(state, era) <= high, f"{state} era {era}: {p(state, era):.2f}")
        self.assertGreater(p("STATE_WEST_BENGAL", 1), p("STATE_GEORGIA", 1))
        self.assertLess(p("STATE_MASSACHUSETTS", 1), p("STATE_GEORGIA", 1))
        self.assertLess(p("STATE_MIDDLE_EGYPT", 1), p("STATE_SAHARA", 1))
        heat = {s: cal.terms(self.rows[s], 1, self.c, self.s)["heat"]
                for s in ("STATE_LOWER_ANDALUSIA", "STATE_GEORGIA")}
        self.assertLess(heat["STATE_LOWER_ANDALUSIA"], heat["STATE_GEORGIA"])

    def test_end_game_is_free(self):
        for r in self.rows.values():
            for warming in (0.0, 4.0):
                self.assertAlmostEqual(cal.terms(r, 13, self.c, self.s, warming)["penalty"], 0, places=9,
                                       msg=(r.state, warming))

    def test_penalty_bounds_under_warming(self):
        rows = list(self.rows.values()) + [neutral_row()]
        for warming in (-1.0, 0.0, 2.0, 4.0):
            for era in (1, 10):
                for r in rows:
                    got = cal.terms(r, era, self.c, self.s, warming)
                    for kind in TERMS:
                        self.assertGreaterEqual(got[kind], 0, (r.state, era, warming, kind))
                    self.assertTrue(0 <= got["penalty"] <= self.c["te_climate_penalty_max"],
                                    (r.state, era, warming, got["penalty"]))
        self.assertLess(self.penalty("STATE_YAKUTSK", 1, 3.0), self.penalty("STATE_YAKUTSK", 1))
        georgia = self.rows["STATE_GEORGIA"]
        self.assertGreater(cal.terms(georgia, 1, self.c, self.s, 3.0)["heat"],
                           cal.terms(georgia, 1, self.c, self.s)["heat"])

    def test_cli_regions_exist(self):
        """A misspelled anchor or heartland region would print as "no row yet" for ever."""
        regions = gen.land_regions()
        listed = set(cal.ANCHORS) | {s for _, states in cal.COUNTRIES for s in states}
        self.assertEqual(sorted(listed - regions), [])

    def test_cli_runs(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cal.main(["--warming", "1.5"]), 0)
        text = out.getvalue()
        self.assertIn("STATE_GEORGIA", text)
        self.assertIn("United States", text)


if __name__ == "__main__":
    unittest.main()
