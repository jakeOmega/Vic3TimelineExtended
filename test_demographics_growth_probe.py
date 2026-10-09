"""The growth probe's analysis recovers a known model from synthetic TE_PG lines, and its schedule is the script's."""
import random
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
import demographics_growth_probe as G  # noqa: E402

EFFECTS = ROOT / "common" / "scripted_effects" / "te_debug_growth_effects.txt"
MODIFIERS = ROOT / "common" / "static_modifiers" / "te_debug_growth_modifiers.txt"


def _steps(phase):
    """(births step, deaths step) of a phase id; -5 is off."""
    if phase in G.BIRTH_STEP:
        return G.BIRTH_STEP[phase], -5.0
    if phase in G.DEATH_STEP:
        return -5.0, G.DEATH_STEP[phase]
    return {0: (0.0, 0.0), 8: (0.0, 0.0), 3: (-5.0, -5.0), 11: (-5.0, -5.0)}[phase]


def _synthetic_log(path, countries=48, seed=7):
    """TE_PG lines from births = eb (1 + mb - 0.1 lit - 0.5 mild + X)+ and deaths = ed (1 + md + 0.3 lab + Y)+."""
    rnd = random.Random(seed)
    lines = []
    for i in range(countries):
        tag = f"T{i:02d}"
        g = i % 8
        pop = rnd.uniform(1e6, 5e7)
        eb, ed = pop * 0.0045, pop * 0.0040
        lit, mild, lab = rnd.uniform(0, 0.6), rnd.uniform(0, 0.1), rnd.uniform(0, 0.2)
        mb, md = rnd.uniform(0, 0.1), rnd.uniform(-0.05, 0.05)
        prev_steps = (0.0, 0.0)
        for t in range(G.TICKS + 1):
            ph = -1 if t == 0 else G.expected_phase(t, g)
            if t:
                x, y = _steps(ph)
                if not G.measured(t):   # the transition window: half the old phase, half the new
                    x, y = (x + prev_steps[0]) / 2, (y + prev_steps[1]) / 2
                births = eb * max(0.0, 1 + mb - 0.1 * lit - 0.5 * mild + x)
                deaths = ed * max(0.0, 1 + md + 0.3 * lab + y)
                pop += births - deaths
                prev_steps = _steps(ph)
            lines.append(
                f"[00:00:00][jomini_effect_impl.cpp:454]: common/scripted_effects/te_debug_growth_effects.txt:1: "
                f"TE_PG t={t} tag={tag} g={g} ph={ph} st=3 war=0 pop={pop:.0f} n={pop:.0f} eb={eb:.2f} "
                f"ebl={eb * lit:.2f} ebs={eb * 8:.2f} ebm=0.00 ebst={eb * mild:.2f} ebsv=0.00 mb={mb:.5f} "
                f"ed={ed:.2f} edst={ed * mild:.2f} edsv=0.00 edlab={ed * lab:.2f} edmach=0.00 edeng=0.00 "
                f"edslv=0.00 edtu=0.00 md={md:.5f}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestAnalysis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile("w", suffix=".log", delete=False)
        self.tmp.close()
        _synthetic_log(self.tmp.name)
        rows, _, _, bad = G.parse([self.tmp.name, self.tmp.name])   # a second copy is read once
        self.assertEqual(bad, [])
        self.pm = G.phase_means(G.windows(rows), 500000)
        self.fits = {tag: G.fit_country(ph) for tag, ph in self.pm.items()}

    def test_every_country_gets_every_phase(self):
        for tag, ph in self.pm.items():
            self.assertEqual(sorted(ph), list(range(16)), tag)

    def test_slopes_are_the_curves(self):
        for tag, f in self.fits.items():
            self.assertAlmostEqual(f["b"]["ratio"], 1.0, places=3, msg=tag)
            self.assertAlmostEqual(f["d"]["ratio"], 1.0, places=3, msg=tag)

    def test_the_missing_terms_are_recovered(self):
        data, w = [], []
        for tag, f in self.fits.items():
            p = self.pm[tag][2]
            data.append(dict(y=f["b"]["total"] - f["b"]["read"], lit=p["ebl"] / p["eb"], mild=p["ebst"] / p["eb"]))
            w.append(p["eb"])
        coef = G.regress(data, ["lit", "mild"], w)
        self.assertAlmostEqual(coef["lit"], -0.1, places=3)
        self.assertAlmostEqual(coef["mild"], -0.5, places=3)
        self.assertAlmostEqual(coef["const"], 0.0, places=3)

    def test_the_floor_steps_are_linear_above_the_floor(self):
        for tag, f in self.fits.items():
            for x, (got, lin) in f["b"]["floor"].items():
                self.assertAlmostEqual((got - lin) / f["b"]["slope"], 0.0, places=3, msg=(tag, x))

    def test_check_and_report_run(self):
        self.assertEqual(G.main(["check", self.tmp.name]), 0)
        self.assertEqual(G.main(["report", self.tmp.name]), 0)


class TestScheduleMatchesScript(unittest.TestCase):
    def test_phase_table(self):
        """te_pg_apply_phase adds, for each phase and cycle, the steps the analysis assumes."""
        body = re.sub(r"#[^\n]*", "", EFFECTS.read_text(encoding="utf-8-sig"))
        values = {}
        for m in re.finditer(r"^(te_pg_[bd]_\w+) = \{(.*?)^\}", re.sub(r"#[^\n]*", "", MODIFIERS.read_text(
                encoding="utf-8-sig")), re.M | re.S):
            v = float(re.search(r"_mult = (-?[\d.]+)", m.group(2)).group(1))
            values[m.group(1)] = v
        apply = body[body.index("te_pg_apply_phase = {"):body.index("te_pg_clear_steps = {")]
        chunks = re.split(r"local_var:te_pg_p = (\d)", apply)[1:]
        for p, chunk in zip(chunks[::2], chunks[1::2]):
            p = int(p)
            for cycle in (0, 1):
                if "local_var:te_pg_cycle = 0" in chunk:
                    common, c0, c1 = re.match(r"(.*?)if = \{\s*limit = \{ local_var:te_pg_cycle = 0 \}(.*?)else = \{(.*)",
                                              chunk, re.S).groups()
                    names = re.findall(r"name = (te_pg_\w+)", common + (c0 if cycle == 0 else c1))
                else:
                    names = re.findall(r"name = (te_pg_\w+)", chunk)
                x = sum(values[n] for n in names if n.startswith("te_pg_b_"))
                y = sum(values[n] for n in names if n.startswith("te_pg_d_"))
                self.assertEqual((x, y), _steps(cycle * 8 + p), (p, cycle, names))

    def test_switch_cadence(self):
        """The script switches when tick mod 3 is 0 and stops at 48; the analysis assumes both."""
        body = EFFECTS.read_text(encoding="utf-8-sig")
        self.assertIn("value = { value = global_var:te_pg_tick modulo = 3 }", body)
        self.assertIn("global_var:te_pg_tick >= 48", body)
        self.assertEqual(G.TICKS, 48)
        self.assertIn("value = { value = local_var:te_pg_within add = var:te_pg_group modulo = 8 }", body)


if __name__ == "__main__":
    unittest.main()
