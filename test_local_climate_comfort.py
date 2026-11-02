"""Local Climate: comfort (docs/superpowers/specs/2026-11-01-local-climate-design.md § 5, § 6, § 11, § 12).

The five relief types and the technologies that carry them, the comfort formula and its
calibration, and the modifier that applies the penalty.

    python3 test_local_climate_comfort.py
"""
import contextlib
import importlib.util
import operator
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

# Spec § 11 (heat v2): the tuning constants at the head of local_climate_values.txt, in percent of migration pull.
CONSTANTS = {
    "te_climate_heat_start": 26, "te_climate_heat_linear": 4.1, "te_climate_heat_quadratic": 0.36,
    "te_climate_index_per_degree": 0.8, "te_climate_cold_start": 0, "te_climate_cold_weight": 0.94,
    "te_climate_winter_neutral": 3, "te_climate_winter_mild": 15, "te_climate_winter_per_degree": 0.6,
    "te_climate_dry_per_class": 16, "te_climate_malaria_per_class": 5, "te_climate_penalty_max": 80,
    "te_climate_amp_low_lat": 30, "te_climate_amp_high_lat": 66.5, "te_climate_amp_max": 2.5,
    "te_climate_normals_warming": 1.1,
}
# Each term's raw value and the relief that eases it (the dry term's is water).
TERMS = {"heat": "heat", "cold": "cold", "winter": "winter", "dry": "water", "disease": "disease"}
# The terms that only cost; the winter term is signed (spec § 12).
COSTS = ("heat", "cold", "dry", "disease")

KINDS = ("heat", "cold", "winter", "water", "disease")
# Spec § 5.2 as the owner left it on 2026-11-01: the historical eras' stage by era 7, the modern by
# era 10, everything by era 13; malaria gone by era 4.
STAGES = {"cold": {7: 0.6, 10: 0.8, 13: 1.0}, "heat": {7: 0.8, 10: 0.9, 13: 1.0},
          "water": {7: 0.7, 10: 0.85, 13: 1.0}, "disease": {4: 1.0, 13: 1.0},
          # Winter's mildness shrinks with heating but lasts into the era 11+ technologies (owner, 2026-11-01).
          "winter": {4: 0.1, 7: 0.2, 10: 0.4, 11: 0.6, 12: 0.8, 13: 1.0}}


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
    return gen.Row(state="STATE_NO_ROW", ref_place="", summer_mean_c=15, heat_source="fit", reason="", **defaults)


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
        # No floor: a mild winter can make the total a bonus (spec § 12).
        self.assertTrue(body.endswith("max = te_climate_penalty_max"), body)
        self.assertNotIn("min = 0", body)
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
        # The record holds today's normals, so a region reads it exactly at the world's anomaly of today
        # (te_climate_normals_warming): 1836, at anomaly 0, is that much colder (owner, 2026-11-01).
        # Arctic amplification is a cold-season effect: winters take the latitude's amplification, the hot
        # days the world's warming as it is (spec § 11.3), or warming would raise Yakutsk's cost.
        self.assertEqual(values_body("te_climate_summer_warming"),
                         "value = temperature_anomaly_display subtract = te_climate_normals_warming")
        self.assertEqual(values_body("te_climate_winter_warming"),
                         "value = temperature_anomaly_display subtract = te_climate_normals_warming "
                         "multiply = te_climate_amplification")
        self.assertEqual(values_body("te_climate_hot_day_eff"),
                         "value = te_climate_hot_day add = te_climate_summer_warming")
        self.assertEqual(values_body("te_climate_winter_eff"),
                         "value = te_climate_winter_mean add = te_climate_winter_warming")
        # Heat stress rises a little slower than air temperature as the world warms (spec § 11.3).
        self.assertEqual(values_body("te_climate_heat_index_eff"),
                         "value = te_climate_heat_index add = { value = te_climate_summer_warming "
                         "multiply = te_climate_index_per_degree }")

    def test_heat_curve(self):
        """Heat costs a x + b x^2 percent, x the heat stress above te_climate_heat_start: the 8th degree costs
        a little over twice the 1st, a moderate curve (owner, 2026-11-01)."""
        self.assertEqual(values_body("te_climate_heat_excess"),
                         "value = te_climate_heat_index_eff subtract = te_climate_heat_start min = 0")
        self.assertEqual(values_body("te_climate_heat_raw"),
                         "value = te_climate_heat_excess multiply = te_climate_heat_quadratic "
                         "add = te_climate_heat_linear multiply = te_climate_heat_excess")
        a, b = CONSTANTS["te_climate_heat_linear"], CONSTANTS["te_climate_heat_quadratic"]
        self.assertAlmostEqual((a + 2 * b * 7.5) / (a + 2 * b * 0.5), 2.2, delta=0.3)

    def test_winter_axis(self):
        """Winters milder than London's in 1836 earn a small bonus and harsher ones cost, both per degree, the
        bonus stopping at te_climate_winter_mild (owner, 2026-11-01; spec § 12). The one signed term."""
        self.assertEqual(values_body("te_climate_winter_raw"),
                         "value = te_climate_winter_eff max = te_climate_winter_mild multiply = -1 "
                         "add = te_climate_winter_neutral multiply = te_climate_winter_per_degree")
        c, s = self.c, self.s
        bonus_max = c["te_climate_winter_per_degree"] * (c["te_climate_winter_mild"] - c["te_climate_winter_neutral"])
        self.assertAlmostEqual(cal.terms(self.rows["STATE_HOME_COUNTIES"], 1, c, s)["winter"], 0, delta=0.3)
        self.assertAlmostEqual(cal.terms(self.rows["STATE_ANTIOQUIA"], 1, c, s)["winter"], -bonus_max, places=9)
        self.assertGreater(cal.terms(self.rows["STATE_MASSACHUSETTS"], 1, c, s)["winter"], 0)
        for r in self.rows.values():
            self.assertGreaterEqual(cal.terms(r, 1, c, s, 4.0)["winter"], -bonus_max - 1e-9, r.state)

    def test_amplification(self):
        c = self.c
        for lat in (0, 15, -30, 30):
            self.assertAlmostEqual(cal.amplification(lat, c), 1.0, places=9, msg=lat)
        for lat in (66.5, -66.5, 80, -90):
            self.assertAlmostEqual(cal.amplification(lat, c), 2.5, places=9, msg=lat)
        self.assertAlmostEqual(cal.amplification(48.25, c), 1.75, places=9)
        self.assertAlmostEqual(cal.amplification(-48.25, c), 1.75, places=9)

    def test_default_record_has_no_penalty(self):
        """The neutral defaults cost nothing. Their mild winter would read a bonus, but the script gates the
        total on te_climate_has_record (test_no_record_costs_nothing_in_script)."""
        got = cal.terms(neutral_row(), 1, self.c, self.s)
        for kind in COSTS:
            self.assertEqual(got[kind], 0, kind)

    def test_anchor_targets(self):
        """Spec § 12.4's targets, in percent of migration pull (negative a bonus), in 1836 unless an era is
        given: the world's anomaly 0, so each region's hot days run te_climate_normals_warming below the
        record's normals and its winters that times its amplification. London is the winter's neutral point
        (owner, 2026-11-01): a milder winter draws a little, a harsher one costs. Bengal stays a little under
        half, so two of its states 10 points apart stay over 5 apart, the gap pops need (owner's 1892
        breakdowns, 2026-11-01)."""
        p = self.penalty
        ranges = (
            ("STATE_GEORGIA", 1, 24, 32), ("STATE_GEORGIA", 7, 0, 6), ("STATE_GEORGIA", 10, -2, 3),
            ("STATE_WEST_BENGAL", 1, 38, 48),
            ("STATE_HOME_COUNTIES", 1, -1, 1), ("STATE_ILE_DE_FRANCE", 1, 0, 6),
            ("STATE_CATALONIA", 1, -3, 3), ("STATE_LAZIO", 1, 10, 20), ("STATE_LAZIO", 4, 0, 8),
            ("STATE_SAHARA", 1, 35, 55), ("STATE_ARIZONA", 1, 35, 55),
            ("STATE_SAHARA", 10, 0, 10), ("STATE_ARIZONA", 10, 0, 10),
            ("STATE_YAKUTSK", 1, 55, 75), ("STATE_YAKUTSK", 7, 28, 42), ("STATE_YAKUTSK", 10, 15, 30),
            ("STATE_MASSACHUSETTS", 1, 8, 18), ("STATE_HAWAIIAN_ISLANDS", 1, -8, -3), ("STATE_VICTORIA", 1, 2, 12),
            ("STATE_MADEIRA", 1, -8, -5),
        )
        for state, era, low, high in ranges:
            with self.subTest(state=state, era=era):
                self.assertTrue(low <= p(state, era) <= high, f"{state} era {era}: {p(state, era):.2f}")
        self.assertGreater(p("STATE_WEST_BENGAL", 1), p("STATE_GEORGIA", 1))
        self.assertLess(p("STATE_MASSACHUSETTS", 1), p("STATE_GEORGIA", 1))
        # The Sun Belt: air conditioning eases the South's heat by era 7 while the North's winters still
        # count, so the order turns.
        self.assertLess(p("STATE_GEORGIA", 7), p("STATE_MASSACHUSETTS", 7))
        # The owner's case: steady Honolulu costs less than northern Sweden before any technology.
        self.assertLess(p("STATE_HAWAIIAN_ISLANDS", 1), p("STATE_NORRLAND", 1))
        # And Paris, whose summers reach 37 °C some years, costs more than steady Honolulu: the hottest
        # days count, not the warm month's mean.
        self.assertLess(p("STATE_HAWAIIAN_ISLANDS", 1), p("STATE_ILE_DE_FRANCE", 1))
        # Madeira's mild winter beats London's, the neutral point (owner, 2026-11-01).
        self.assertLess(p("STATE_MADEIRA", 1), p("STATE_HOME_COUNTIES", 1))
        self.assertEqual(p("STATE_OMAN", 1), CONSTANTS["te_climate_penalty_max"])
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
        c = self.c
        bonus_max = c["te_climate_winter_per_degree"] * (c["te_climate_winter_mild"] - c["te_climate_winter_neutral"])
        for warming in (-1.0, 0.0, 2.0, 4.0):
            for era in (1, 10):
                for r in rows:
                    got = cal.terms(r, era, self.c, self.s, warming)
                    for kind in COSTS:
                        self.assertGreaterEqual(got[kind], 0, (r.state, era, warming, kind))
                    self.assertTrue(-bonus_max <= got["penalty"] <= self.c["te_climate_penalty_max"],
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



class ScriptValues:
    """A small interpreter for local_climate_values.txt, so the tests read the game's arithmetic, not only the
    mirror's. It knows what the file uses: value/add/subtract/multiply/divide, min (a floor) and max (a ceiling)
    at the point they stand, inline { } operands, and if with a limit of comparisons. Anything else raises, so a
    new operation in the file fails the test until the interpreter learns it."""

    OPS = ("value", "add", "subtract", "multiply", "divide", "min", "max", "if")
    TOKEN = re.compile(r"[{}]|[<>]=?|=|[^\s{}=<>]+")

    def __init__(self, path=VALUES):
        tokens = self.TOKEN.findall(re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig")))
        items, _ = self._parse(tokens, 0)
        self.defs = {key: value for key, _, value in items}

    def _parse(self, tokens, i):
        items = []
        while i < len(tokens) and tokens[i] != "}":
            key, op = tokens[i], tokens[i + 1]
            i += 2
            if tokens[i] == "{":
                value, i = self._parse(tokens, i + 1)
                i += 1
            else:
                value, i = tokens[i], i + 1
            items.append((key, op, value))
        return items, i

    def read(self, value, env):
        if isinstance(value, list):
            return self._block(value, env)
        try:
            return float(value)
        except ValueError:
            pass
        if value in env:
            return env[value]
        if value not in self.defs:
            raise KeyError(f"{value}: neither a script value in {VALUES.name} nor stubbed")
        return self.read(self.defs[value], env)

    def _limit(self, items, env):
        compare = {"<": operator.lt, ">": operator.gt, "<=": operator.le, ">=": operator.ge, "=": operator.eq}
        # has_variable = X holds when the env stubs var:X.
        return all(f"var:{value}" in env if key == "has_variable" else
                   compare[op](self.read(key, env), self.read(value, env)) for key, op, value in items)

    def _block(self, items, env, acc=0.0):
        for key, _, value in items:
            if key not in self.OPS:
                raise KeyError(f"the interpreter doesn't know '{key}'")
            if key == "if":
                limit = [v for k, _, v in value if k == "limit"]
                if self._limit(limit[0], env):
                    acc = self._block([x for x in value if x[0] != "limit"], env, acc)
                continue
            operand = self.read(value, env)
            if key == "value":
                acc = operand
            elif key == "add":
                acc += operand
            elif key == "subtract":
                acc -= operand
            elif key == "multiply":
                acc *= operand
            elif key == "divide":
                acc /= operand
            elif key == "min":
                acc = max(acc, operand)
            else:
                acc = min(acc, operand)
        return acc


def carrier_sums(era):
    """modifier:<type> -> what a country holding every carrier up to `era` reads: each relief type, and the
    census's Malaria Control apart from the disease relief, as the script reads them."""
    eras = cal.tech_eras()
    sums = {f"modifier:state_climate_{kind}_relief_add": 0.0 for kind in KINDS}
    sums["modifier:state_malaria_control_add"] = 0.0
    for _, text in cal._tech_texts(cal.REPO):
        for _, key, body in cal._blocks(text):
            if eras.get(key, 99) > era:
                continue
            for kind, amount in cal.RELIEF_RE.findall(body):
                sums[f"modifier:state_climate_{kind}_relief_add"] += float(amount)
            for amount in cal.CONTROL_RE.findall(body):
                sums["modifier:state_malaria_control_add"] += float(amount)
    return sums


def record_env(row, has_record=1):
    return {"te_climate_has_record": has_record, "te_climate_summer_humidity": row.summer_humidity,
            "te_climate_winter_mean": row.winter_mean_c, "te_climate_aridity": row.aridity,
            "te_climate_malaria": row.malaria, "te_climate_latitude": row.latitude,
            "te_climate_hot_day": row.hot_day_c, "te_climate_heat_index": row.heat_index}


class ScriptMatchesMirror(unittest.TestCase):
    """The game's script values compute what the calibration's mirror computes, for every row (Task 5 review I1:
    a script-only slip, such as a raw term losing its floor, once left the suite green)."""

    ERAS = (1, 4, 7, 10, 13)
    WARMING = (-1.0, 0.0, 3.0)

    @classmethod
    def setUpClass(cls):
        cls.sv = ScriptValues()
        cls.c, cls.s = cal.load_constants(), cal.relief_schedule()
        cls.sums = {era: carrier_sums(era) for era in cls.ERAS}

    def test_every_row_matches_the_mirror(self):
        worst = (0.0, None)
        for row in gen.load_rows() + [neutral_row()]:
            for era in self.ERAS:
                for warming in self.WARMING:
                    env = {**record_env(row), **self.sums[era], "temperature_anomaly_display": warming}
                    mirror = cal.terms(row, era, self.c, self.s, warming)
                    for name in ("heat", "cold", "winter", "dry", "disease", "penalty"):
                        sv = f"te_climate_{name}_term" if name != "penalty" else "te_climate_penalty"
                        diff = abs(self.sv.read(sv, env) - mirror[name])
                        if diff > worst[0]:
                            worst = (diff, (row.state, era, warming, name, self.sv.read(sv, env), mirror[name]))
                    # The values the bonus modifier and the hovers read (review of #1313).
                    for sv, want in (("te_climate_bonus", max(0.0, -mirror["penalty"])),
                                     ("te_climate_winter_draw", -mirror["winter"])):
                        diff = abs(self.sv.read(sv, env) - want)
                        if diff > worst[0]:
                            worst = (diff, (row.state, era, warming, sv, self.sv.read(sv, env), want))
        self.assertLess(worst[0], 1e-6, worst[1])

    def test_no_record_costs_nothing_in_script(self):
        row = neutral_row()
        for warming in (-3.0, 0.0, 12.0):
            env = {**record_env(row, has_record=0), **self.sums[1], "temperature_anomaly_display": warming}
            self.assertEqual(self.sv.read("te_climate_penalty", env), 0.0, warming)

    def test_interpreter_reads_every_value(self):
        """Every value in the file evaluates, so none hides an operation the interpreter would skip."""
        row = gen.load_rows()[0]
        env = {**record_env(row), **self.sums[7], "temperature_anomaly_display": 1.0}
        for name, body in self.sv.defs.items():
            if isinstance(body, list):
                self.sv.read(name, env)


MODIFIERS = ROOT / "common" / "static_modifiers" / "local_climate_modifiers.txt"
EFFECTS = ROOT / "common" / "scripted_effects" / "local_climate_effects.txt"
ON_ACTIONS = ROOT / "common" / "on_actions" / "local_climate_on_actions.txt"
DEFINES = ROOT / "common" / "defines" / "extra_defines.txt"
EFFECT = "te_update_local_climate_modifier"
APPLIED = "te_climate_penalty_applied"
BONUS = "te_climate_bonus_applied"
FEW_STATES_DEFINES = ("MASS_MIGRATION_NUM_TARGET_STATES_FOR_NO_PENALTY", "MASS_MIGRATION_FEW_TARGET_STATES_PENALTY")


def top_blocks(text, name):
    """Every top-level `name = { ... }` body in the text, in order (a file may open one more than once)."""
    found, rest = [], text
    while (body := top_block(rest, name)) is not None:
        found.append(body)
        rest = rest[re.search(rf"(?m)^{re.escape(name)} = \{{", rest).end() + len(body) + 1:]
    return found


def script_texts(*dirs):
    """(path, text without comments) for every .txt under the given repo directories."""
    for d in dirs:
        for path in sorted((ROOT / d).rglob("*.txt")):
            yield path, re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))


class Modifier(unittest.TestCase):
    """The penalty applied: one static modifier, refreshed yearly from a state pulse (spec § 5.1, § 5.4)."""

    def test_files_have_one_bom(self):
        for path in (MODIFIERS, EFFECTS, ON_ACTIONS):
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), f"{path.name} needs a UTF-8 BOM")
            self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"), f"{path.name}: doubled BOM")

    def test_static_modifier(self):
        text = MODIFIERS.read_text(encoding="utf-8-sig")
        body = squash(top_block(text, "local_climate_discomfort") or "")
        # A percentage, not points: a cut every state in a market shares can't pin its poorer states at
        # attraction's floor of 0 (spec § 11.1).
        self.assertEqual(body, "icon = gfx/interface/icons/timed_modifier_icons/modifier_system.dds "
                               "state_migration_pull_mult = -0.01")
        # The bonus is a modifier of its own, not a negative multiplier, which no one has seen work (spec § 12).
        self.assertEqual(squash(top_block(text, "local_climate_amenity") or ""),
                         "icon = gfx/interface/icons/timed_modifier_icons/modifier_system.dds "
                         "state_migration_pull_mult = 0.01")

    def test_refresh_shape(self):
        body = squash(top_block(EFFECTS.read_text(encoding="utf-8-sig"), EFFECT) or "")
        self.assertEqual(body, "remove_modifier_if_exists_effect = { MODIFIER = local_climate_discomfort } "
                               "remove_modifier_if_exists_effect = { MODIFIER = local_climate_amenity } "
                               f"set_variable = {{ name = {APPLIED} value = te_climate_penalty }} "
                               f"set_variable = {{ name = {BONUS} value = te_climate_bonus }} "
                               f"if = {{ limit = {{ var:{APPLIED} > 0.5 }} "
                               f"add_modifier = {{ name = local_climate_discomfort multiplier = var:{APPLIED} }} }} "
                               f"else_if = {{ limit = {{ var:{BONUS} > 0.5 }} "
                               f"add_modifier = {{ name = local_climate_amenity multiplier = var:{BONUS} }} }}")

    def test_refresh_never_removes_the_variable(self):
        """The modifier's multiplier reads the variable on later ticks too (modifier_multiplier_var_audit)."""
        for path, text in script_texts("common", "events"):
            for var in (APPLIED, BONUS):
                self.assertNotRegex(text, rf"remove_variable\s*=\s*{var}\b", path.name)
                self.assertNotRegex(text, rf"remove_variable\s*=\s*\{{\s*name\s*=\s*{var}\b", path.name)

    def test_refresh_sites(self):
        text = ON_ACTIONS.read_text(encoding="utf-8-sig")
        yearly = [squash(b) for b in top_blocks(text, "on_yearly_pulse_state")]
        monthly = [squash(b) for b in top_blocks(text, "on_monthly_pulse_state")]
        self.assertEqual(yearly, ["on_actions = { local_climate_yearly_on_action }"])
        self.assertEqual(monthly, ["on_actions = { local_climate_first_on_action }"])
        self.assertEqual(squash(top_block(text, "local_climate_yearly_on_action") or ""),
                         f"effect = {{ {EFFECT} = yes }}")
        self.assertEqual(squash(top_block(text, "local_climate_first_on_action") or ""),
                         f"trigger = {{ NOT = {{ has_variable = {BONUS} }} }} effect = {{ {EFFECT} = yes }}")
        # One refresh site plus the first application, and nothing else calls the effect.
        calls = [(path.name, n) for path, text in script_texts("common", "events")
                 for n in [len(re.findall(rf"\b{EFFECT}\s*=\s*yes\b", text))] if n]
        self.assertEqual(calls, [(ON_ACTIONS.name, 2)])
        # The three on-actions hang off no other hook in another file.
        for path, other in script_texts("common/on_actions"):
            if path != ON_ACTIONS:
                for name in ("local_climate_yearly_on_action", "local_climate_first_on_action", "local_climate_log_on_action"):
                    self.assertNotIn(name, other, path.name)

    def test_decade_log(self):
        """Informational, not a self-check: a mass migration lasts about a year, so the log samples the targets
        once a year (the first country to pulse after a 360-day global gate) and prints each decade's sums:
        how many targets, and how many with under 10 arable land, the floor the define removes (Task 6 review)."""
        text = ON_ACTIONS.read_text(encoding="utf-8-sig")
        country = [squash(b) for b in top_blocks(text, "on_yearly_pulse_country")]
        self.assertEqual(country, ["on_actions = { local_climate_log_on_action }"])
        body = squash(top_block(text, "local_climate_log_on_action") or "")
        self.assertTrue(body.startswith("trigger = { NOT = { has_global_variable = te_climate_log_year } }"), body[:90])
        self.assertIn("set_global_variable = { name = te_climate_log_year value = yes days = 360 }", body)
        self.assertIn("every_state = { limit = { is_mass_migration_target = yes }", body)
        self.assertIn("arable_land < 10", body)
        decade = body[body.index("limit = { NOT = { has_global_variable = te_climate_log_decade } }"):]
        self.assertIn("set_global_variable = { name = te_climate_log_decade value = yes days = 3650 }", decade)
        self.assertIn('debug_log = "TE_LOCAL_CLIMATE yearly_targets_summed=', decade)
        self.assertIn("under_10_arable=", decade)
        for counter in ("te_climate_log_targets", "te_climate_log_small_targets", "te_climate_log_years"):
            self.assertIn(f"remove_global_variable = {counter}", decade, counter)
        self.assertNotIn("$", body, "no $PARAM$ inside a debug_log string")

    def test_defines(self):
        """The arable land floor goes; the few-states penalty stays vanilla's (owner, 2026-11-01).

        The engine rejects 0 at load ("Must be greater than 0", defines.cpp:167, 2026-11-01), so the
        floor is 1: below every state region's arable land (the least is 2).
        """
        text = DEFINES.read_text(encoding="utf-8-sig")
        blocks = [squash(b) for b in top_blocks(text, "NPops")]
        self.assertTrue(blocks)
        self.assertEqual(sum(len(re.findall(r"MASS_MIGRATION_TARGET_MIN_ARABLE_LAND = 1(?![\d.])", b)) for b in blocks),
                         1, blocks)
        arable = [int(n) for f in sorted((ROOT / "map_data/state_regions").glob("*.txt"))
                  for n in re.findall(r"(?m)^\s*arable_land\s*=\s*(\d+)", f.read_text(encoding="utf-8-sig"))]
        self.assertGreater(len(arable), 600)
        self.assertGreater(min(arable), 1, "a region below the floor can't be a mass migration target")
        for path, body in script_texts("common/defines"):
            self.assertEqual(body.count("MASS_MIGRATION_TARGET_MIN_ARABLE_LAND"), int(path == DEFINES), path.name)
            for define in FEW_STATES_DEFINES:
                self.assertNotIn(define, body, path.name)

    def test_migration_target_concept_drops_the_floor(self):
        """Vanilla's concept text prints the arable land define, which would now read "at least 0"."""
        text = (ROOT / "localization" / "english" / "replace" / "timeline_extended_override_l_english.yml").read_text(
            encoding="utf-8-sig")
        m = re.search(r'(?m)^ concept_migration_target_desc:\d* "(.*)"\s*$', text)
        self.assertIsNotNone(m)
        self.assertNotIn("MASS_MIGRATION_TARGET_MIN_ARABLE_LAND", m.group(1))
        self.assertIn("MASS_MIGRATION_STATE_MIN_MARKET_ACCESS", m.group(1))

    def test_modifier_loc(self):
        for key in ("local_climate_discomfort", "local_climate_amenity"):
            # Plain, no markup: the state panel hides it by comparing TimedModifier.GetName with Localize().
            self.assertEqual(loc_value(key), "Local Climate", key)
            self.assertIn("[concept_local_climate]", loc_value(f"{key}_desc") or "", key)


WIDGETS = ROOT / "gui" / "te_state_panel_widgets.gui"
SHOWN = "GreaterThan_CFixedPoint(State.MakeScope.ScriptValue('te_climate_penalty_shown'), '(CFixedPoint)0')"
HAS_RECORD = "GreaterThan_CFixedPoint(State.MakeScope.ScriptValue('te_climate_has_record'), '(CFixedPoint)0')"


def tile_rows():
    """The visible-condition part and the whole text of each te_state_climate_row in the Local Climate tile."""
    text = WIDGETS.read_text(encoding="utf-8-sig")
    m = re.search(r"(?m)^\s*type te_state_climate_tile = flowcontainer \{", text)
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        if c == "#":
            i = text.index("\n", i)
            continue
        depth += {"{": 1, "}": -1}.get(c, 0)
        i += 1
    rows = text[m.end():i - 1].split("te_state_climate_row = {")[1:]
    return [(row.split("row_tooltip")[0], row) for row in rows]


class Tile(unittest.TestCase):
    """Task 7: the tile's Comfort row and the readings' hovers (spec § 7)."""

    def test_comfort_row_reads_applied(self):
        """The row shows what the modifier applies (the yearly variable), red and signed, not the live value."""
        self.assertEqual(values_body("te_climate_penalty_now"),
                         "value = 0 if = { limit = { has_variable = te_climate_penalty_applied } "
                         "value = var:te_climate_penalty_applied }")
        self.assertEqual(loc_value("te_state_climate_comfort_value"),
                         "#R -[State.MakeScope.ScriptValue('te_climate_penalty_now')|0]%#!")
        # A mild winter's bonus, in green (spec § 12).
        self.assertEqual(values_body("te_climate_bonus_now"),
                         f"value = 0 if = {{ limit = {{ has_variable = {BONUS} }} value = var:{BONUS} }}")
        self.assertEqual(loc_value("te_state_climate_comfort_bonus_value"),
                         "#G +[State.MakeScope.ScriptValue('te_climate_bonus_now')|0]%#!")
        self.assertEqual(loc_value("TE_STATE_CLIMATE_ROW_COMFORT"), "Comfort")

    def test_comfort_row_waits_for_first_application(self):
        """Four Comfort rows, one shown at a time: the red cost, the green bonus, None when the climate does
        neither, and Pending until the state's first monthly application."""
        self.assertEqual(values_body("te_climate_penalty_shown"),
                         "value = 0 if = { limit = { has_variable = te_climate_penalty_applied } value = 1 }")
        comfort = [(gate, row) for gate, row in tile_rows() if "TE_STATE_CLIMATE_ROW_COMFORT" in row]
        self.assertEqual(len(comfort), 4)
        # 0.5, the modifiers' own threshold: under it nothing applies, and a whole percent would print -0%.
        cost = "GreaterThan_CFixedPoint(State.MakeScope.ScriptValue('te_climate_penalty_now'), '(CFixedPoint)0.5')"
        bonus = "GreaterThan_CFixedPoint(State.MakeScope.ScriptValue('te_climate_bonus_now'), '(CFixedPoint)0.5')"
        gates = {key: [g for g, r in comfort if f'"{key}"' in r] for key in
                 ("te_state_climate_comfort_value", "te_state_climate_comfort_bonus_value",
                  "te_state_climate_comfort_none", "te_state_climate_pending")}
        self.assertEqual({k: len(v) for k, v in gates.items()}, dict.fromkeys(gates, 1))
        self.assertIn(f"And(And({HAS_RECORD}, {SHOWN}), {cost})", gates["te_state_climate_comfort_value"][0])
        self.assertIn(f"And(And({HAS_RECORD}, {SHOWN}), {bonus})", gates["te_state_climate_comfort_bonus_value"][0])
        self.assertIn(f"And(And({HAS_RECORD}, {SHOWN}), And(Not({cost}), Not({bonus})))",
                      gates["te_state_climate_comfort_none"][0])
        self.assertIn(f"And({HAS_RECORD}, Not({SHOWN}))", gates["te_state_climate_pending"][0])
        for key in ("te_state_climate_comfort_none", "te_state_climate_pending"):
            self.assertIsNotNone(loc_value(key), key)

    def test_term_hovers(self):
        """Each reading's hover gives its cost before relief, the relief the owner's technologies give, and the
        cost left; the seasons' hovers also give today's normal and the warming against it. Winter's mildness
        shows as what it draws (negative a cost), so a bonus reads +7%, not -(-7)% (spec § 12)."""
        hovers = (("te_state_climate_hot_day_tt", "heat_raw", "relief_heat", "heat_term"),
                  ("te_state_climate_winter_tt", "cold_raw", "relief_cold", "cold_term"),
                  ("te_state_climate_winter_tt", "winter_draw_raw", "relief_winter", "winter_draw"),
                  ("te_state_climate_water_tt", "dry_raw", "relief_water", "dry_term"),
                  ("te_state_climate_malaria_tt", "disease_raw", "relief_disease", "disease_term"))
        for key, *values in hovers:
            text = loc_value(key) or ""
            for value in values:
                self.assertIn(f"State.MakeScope.ScriptValue('te_climate_{value}')", text, (key, value))
        self.assertEqual(values_body("te_climate_winter_draw"), "value = te_climate_winter_term multiply = -1")
        self.assertEqual(values_body("te_climate_winter_draw_raw"), "value = te_climate_winter_raw multiply = -1")
        self.assertEqual(values_body("te_climate_effect_now"), "value = te_climate_penalty_now multiply = -1")
        for key, season, warming in (("te_state_climate_hot_day_tt", "hot_day", "summer"),
                                     ("te_state_climate_winter_tt", "winter_mean", "winter")):
            text = loc_value(key)
            self.assertIn(f"State.MakeScope.ScriptValue('te_climate_{warming}_warming')", text, key)
            self.assertIn(f"State.MakeScope.ScriptValue('te_climate_{season}')", text, key)
        self.assertIn("State.MakeScope.ScriptValue('te_climate_heat_index_eff')", loc_value("te_state_climate_hot_day_tt"))
        comfort = loc_value("te_state_climate_comfort_tt") or ""
        for value in ("heat_term", "cold_term", "winter_draw", "dry_term", "disease_term", "effect_now"):
            self.assertIn(f"State.MakeScope.ScriptValue('te_climate_{value}')", comfort, value)
        self.assertIn("[concept_migration_pull]", comfort)
        # The figures the text quotes come from the constants, so a retune can't leave them stale.
        self.assertIn("State.MakeScope.ScriptValue('te_climate_heat_start')", loc_value("te_state_climate_hot_day_tt"))
        self.assertIn("State.MakeScope.ScriptValue('te_climate_penalty_max')", comfort)

    def test_seasons_show_the_climate_now(self):
        """The Hot days and Winter rows show the record with the warming against today's normals, as the formula
        reads them, so the tile moves as the world warms."""
        self.assertIn("ScriptValue('te_climate_hot_day_eff')", loc_value("te_state_climate_hot_day_value"))
        self.assertIn("ScriptValue('te_climate_winter_eff')", loc_value("te_state_climate_winter_value"))

    def test_rows_gate_on_the_record(self):
        rows = tile_rows()
        self.assertEqual(len(rows), 9)
        for gate, _ in rows:
            self.assertIn(HAS_RECORD, gate)


if __name__ == "__main__":
    unittest.main()
