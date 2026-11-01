"""Local Climate: comfort (docs/superpowers/specs/2026-11-01-local-climate-design.md § 5, § 6).

The four relief types and the technologies that carry them, the comfort formula and its
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

# Spec § 5 and the plan's Task 5: the tuning constants at the head of local_climate_values.txt.
CONSTANTS = {
    "te_climate_heat_start": 22, "te_climate_humidity_factor": 0.33, "te_climate_heat_weight": 1,
    "te_climate_cold_start": 0, "te_climate_cold_weight": 0.8, "te_climate_dry_per_class": 8,
    "te_climate_malaria_per_class": 2.5, "te_climate_penalty_max": 40, "te_climate_amp_low_lat": 30,
    "te_climate_amp_high_lat": 66.5, "te_climate_amp_max": 2.5, "te_climate_normals_warming": 1.1,
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
        # The record holds today's normals, so a region reads it exactly at the world's anomaly of today
        # (te_climate_normals_warming): 1836, at anomaly 0, is that much colder (owner, 2026-11-01).
        self.assertEqual(values_body("te_climate_warming"),
                         "value = temperature_anomaly_display subtract = te_climate_normals_warming "
                         "multiply = te_climate_amplification")
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
        """Spec § 5.3's targets, in attraction points (1 SoL = 2), in 1836: the world's anomaly 0, so each
        region runs te_climate_normals_warming x its amplification below the record's normals."""
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
        return all(compare[op](self.read(key, env), self.read(value, env)) for key, op, value in items)

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
    return {"te_climate_has_record": has_record, "te_climate_summer_mean": row.summer_mean_c,
            "te_climate_summer_humidity": row.summer_humidity, "te_climate_winter_mean": row.winter_mean_c,
            "te_climate_aridity": row.aridity, "te_climate_malaria": row.malaria, "te_climate_latitude": row.latitude}


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
                    for name in ("heat", "cold", "dry", "disease", "penalty"):
                        sv = f"te_climate_{name}_term" if name != "penalty" else "te_climate_penalty"
                        diff = abs(self.sv.read(sv, env) - mirror[name])
                        if diff > worst[0]:
                            worst = (diff, (row.state, era, warming, name, self.sv.read(sv, env), mirror[name]))
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
        body = squash(top_block(MODIFIERS.read_text(encoding="utf-8-sig"), "local_climate_discomfort") or "")
        self.assertEqual(body, "icon = gfx/interface/icons/timed_modifier_icons/modifier_system.dds "
                               "state_migration_pull_add = -1")

    def test_refresh_shape(self):
        body = squash(top_block(EFFECTS.read_text(encoding="utf-8-sig"), EFFECT) or "")
        self.assertEqual(body, "remove_modifier_if_exists_effect = { MODIFIER = local_climate_discomfort } "
                               f"set_variable = {{ name = {APPLIED} value = te_climate_penalty }} "
                               f"if = {{ limit = {{ var:{APPLIED} > 0 }} "
                               f"add_modifier = {{ name = local_climate_discomfort multiplier = var:{APPLIED} }} }}")

    def test_refresh_never_removes_the_variable(self):
        """The modifier's multiplier reads the variable on later ticks too (modifier_multiplier_var_audit)."""
        for path, text in script_texts("common", "events"):
            self.assertNotRegex(text, rf"remove_variable\s*=\s*{APPLIED}\b", path.name)
            self.assertNotRegex(text, rf"remove_variable\s*=\s*\{{\s*name\s*=\s*{APPLIED}\b", path.name)

    def test_refresh_sites(self):
        text = ON_ACTIONS.read_text(encoding="utf-8-sig")
        yearly = [squash(b) for b in top_blocks(text, "on_yearly_pulse_state")]
        monthly = [squash(b) for b in top_blocks(text, "on_monthly_pulse_state")]
        self.assertEqual(yearly, ["on_actions = { local_climate_yearly_on_action }"])
        self.assertEqual(monthly, ["on_actions = { local_climate_first_on_action }"])
        self.assertEqual(squash(top_block(text, "local_climate_yearly_on_action") or ""),
                         f"effect = {{ {EFFECT} = yes }}")
        self.assertEqual(squash(top_block(text, "local_climate_first_on_action") or ""),
                         f"trigger = {{ NOT = {{ has_variable = {APPLIED} }} }} effect = {{ {EFFECT} = yes }}")
        # One refresh site plus the first application, and nothing else calls the effect.
        calls = [(path.name, n) for path, text in script_texts("common", "events")
                 for n in [len(re.findall(rf"\b{EFFECT}\s*=\s*yes\b", text))] if n]
        self.assertEqual(calls, [(ON_ACTIONS.name, 2)])

    def test_decade_log(self):
        """Informational, not a self-check: every ten years, how many mass migration targets there are and how
        many of them have under 10 arable land, the floor the define removes."""
        text = ON_ACTIONS.read_text(encoding="utf-8-sig")
        country = [squash(b) for b in top_blocks(text, "on_yearly_pulse_country")]
        self.assertEqual(country, ["on_actions = { local_climate_log_on_action }"])
        body = squash(top_block(text, "local_climate_log_on_action") or "")
        self.assertIn("days = 3650", body)
        self.assertIn("every_state = { limit = { is_mass_migration_target = yes }", body)
        self.assertIn("arable_land < 10", body)
        self.assertIn('debug_log = "TE_LOCAL_CLIMATE mass_migration_targets=', body)
        self.assertIn("under_10_arable=", body)
        self.assertNotIn("$", body, "no $PARAM$ inside a debug_log string")

    def test_defines(self):
        """The arable land floor goes; the few-states penalty stays vanilla's (owner, 2026-11-01)."""
        text = DEFINES.read_text(encoding="utf-8-sig")
        blocks = [squash(b) for b in top_blocks(text, "NPops")]
        self.assertTrue(blocks)
        self.assertEqual(sum(b.count("MASS_MIGRATION_TARGET_MIN_ARABLE_LAND = 0") for b in blocks), 1, blocks)
        for path, body in script_texts("common/defines"):
            self.assertEqual(body.count("MASS_MIGRATION_TARGET_MIN_ARABLE_LAND"), int(path == DEFINES), path.name)
            for define in FEW_STATES_DEFINES:
                self.assertNotIn(define, body, path.name)

    def test_modifier_loc(self):
        name, desc = loc_value("local_climate_discomfort"), loc_value("local_climate_discomfort_desc")
        self.assertIsNotNone(name)
        self.assertIn("Local Climate", name)
        self.assertIn("[concept_local_climate]", desc or "")


if __name__ == "__main__":
    unittest.main()
