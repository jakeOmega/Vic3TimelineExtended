"""Tourism heritage (docs/superpowers/specs/2026-10-23-tourism-heritage-design.md).

Monuments give tourism as an output bonus, as base appeal does (§ 5), and the
heritage a monument stands for comes off base appeal through a gated term (§ 6).

    python3 test_tourism_heritage.py
"""
import collections
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOURISM = ROOT / "common" / "script_values" / "tourism.txt"
PANEL_WIDGETS = ROOT / "gui" / "te_state_panel_widgets.gui"
GENERATED = ROOT / "common" / "script_values" / "tourism_heritage_generated.txt"

_spec = importlib.util.spec_from_file_location(
    "gen_tourism_heritage", ROOT / "scripts" / "generators" / "gen_tourism_heritage.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def read(path):
    return Path(path).read_text(encoding="utf-8-sig")


def squash(text):
    """Comments dropped, every whitespace run one space."""
    return re.sub(r"\s+", " ", re.sub(r"#[^\n]*", "", text)).strip()


def block(text, name):
    """The body of the block `name = {` or `name = <type> {` (a .gui `type X = flowcontainer {`), braces
    balanced, or None."""
    m = re.search(rf"(?m)^[ \t]*{re.escape(name)} = (?:\w+ )?\{{", text)
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


def appeal_scores():
    """STATE_X -> its score in base_tourism_appeal_value (the value after its state_region)."""
    body = block(read(TOURISM), "base_tourism_appeal_value")
    return {s: int(v) for s, v in re.findall(r"state_region = s:(STATE_\w+) \}\s*value = (\d+)", body)}


def loc_value(key):
    """The text of an English loc key, or None."""
    for path in (ROOT / "localization" / "english").glob("*.yml"):
        m = re.search(rf'(?m)^ {re.escape(key)}:\d* "(.*)"\s*$', path.read_text(encoding="utf-8-sig"))
        if m:
            return m.group(1)
    return None


# Where vanilla's history creates each wonder standing in 1836 (game/common/history/buildings/*.txt). Its
# `potential` can differ (the Taj Mahal's names Rajputana), and CI has no history files.
WONDERS_1836 = {"building_taj_mahal": "STATE_AGRA", "building_angkor_wat": "STATE_CAMBODIA",
                "building_hagia_sophia": "STATE_EASTERN_THRACE", "building_vatican_city": "STATE_LAZIO",
                "building_forbidden_city": "STATE_BEIJING", "building_saint_basils_cathedral": "STATE_MOSCOW",
                "building_white_house": "STATE_DISTRICT_OF_COLUMBIA"}


# Spec § 5.2: each wonder's output figure is the appeal its state's heritage took.
WONDERS = {"building_taj_mahal": 0.40, "building_angkor_wat": 0.30, "building_hagia_sophia": 0.20,
           "building_vatican_city": 0.20, "building_forbidden_city": 0.20,
           "building_saint_basils_cathedral": 0.20, "building_white_house": 0.20}


class MonumentsAreOutput(unittest.TestCase):
    def test_each_wonder_has_its_figure(self):
        body = squash(block(read(TOURISM), "tourism_bonus_from_monuments"))
        for b, v in WONDERS.items():
            self.assertRegex(body, rf"is_building_type = {b} \}} add = {v:g} \}}", b)

    def test_other_monuments_get_the_default(self):
        body = squash(block(read(TOURISM), "tourism_bonus_from_monuments"))
        self.assertIn("every_scope_building = { limit = { is_building_group = bg_monuments }", body)
        self.assertRegex(body, r"else = \{ add = 0\.1 \}")

    def test_totals(self):
        t = read(TOURISM)
        self.assertIn("add = tourism_bonus_from_monuments", block(t, "total_tourism_output_bonus_percent"))
        thr = block(t, "total_tourism_throughput_bonus_percent")
        self.assertIn("add = tourism_throughput_from_skyscraper", thr)
        self.assertNotIn("monuments", thr)

    def test_wonder_figures_match_their_moves(self):
        # Spec call 7: a wonder's figure is the points its state moves to it, and no other wonder has one.
        body = squash(block(read(TOURISM), "tourism_bonus_from_monuments"))
        named = {b: float(v) for b, v in re.findall(r"is_building_type = (building_\w+) \} add = ([\d.]+)", body)}
        moved = {f"building_{m.monument}": m.points / 100 for m in gen.load_moves() if m.kind == "vanilla_wonder"}
        self.assertEqual(named, moved)

    def test_old_value_is_gone(self):
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "gui").rglob("*.gui")):
            self.assertFalse("tourism_throughput_from_monuments" in path.read_text(encoding="utf-8-sig"), path)

    def test_card_shows_monuments_with_output(self):
        card = block(read(PANEL_WIDGETS), "type te_state_tourism_card")
        out_col, thr_col = card.split("te_state_tourism_throughput_tt", 1)
        self.assertTrue("tourism_bonus_from_monuments" in out_col, "Monuments not in the output column")
        self.assertTrue("tourism_throughput_from_skyscraper" in thr_col, "no Skyscraper row in throughput")


class HeritageMoves(unittest.TestCase):
    def test_generated_file_is_current(self):
        self.assertEqual(read(GENERATED), gen.render(gen.load_moves()))

    def test_gates_follow_the_rule_and_the_seeding(self):
        out = squash(gen.render([gen.Move("STATE_X", 20, "a", "vanilla_wonder", ""),
                                 gen.Move("STATE_X", 30, "b", "existing_landmark", ""),
                                 gen.Move("STATE_X", 10, "c", "existing_site", ""),
                                 gen.Move("STATE_X", 5, "d", "new_site", "")]))
        self.assertIn("limit = { state_region = s:STATE_X } add = 20 if =", out)
        self.assertIn("if = { limit = { gm_system_enabled = yes has_global_variable = gm_landmarks_seeded } "
                      "add = 30 }", out)
        self.assertIn("if = { limit = { gm_system_enabled = yes } add = 15 }", out)
        self.assertTrue(out.rstrip().endswith("divide = 100 }"))

    def test_every_monument_exists(self):
        seeds = read(ROOT / "common/scripted_effects/gm_landmark_effects.txt")
        sites = read(ROOT / "common/scripted_effects/gm_archaeology_effects.txt")
        vanilla = json.loads((ROOT / "vanilla_parsed/common/buildings.json").read_text(encoding="utf-8"))
        for m in gen.load_moves():
            if m.kind in ("existing_landmark", "new_landmark"):
                self.assertIn(f"KEY = {m.monument} ", seeds, m)
            elif m.kind in ("existing_site", "new_site"):
                self.assertIn(f"KEY = {m.monument} ", sites, m)
            else:
                self.assertIn('"bg_monuments"', json.dumps(vanilla[f"building_{m.monument}"]), m)

    def test_monuments_stand_where_they_take_points(self):
        seeds = read(ROOT / "common/scripted_effects/gm_landmark_effects.txt")
        sites = read(ROOT / "common/scripted_effects/gm_archaeology_effects.txt")
        vanilla = json.loads((ROOT / "vanilla_parsed/common/buildings.json").read_text(encoding="utf-8"))
        for m in gen.load_moves():
            if m.kind == "vanilla_wonder":
                b = f"building_{m.monument}"
                where = WONDERS_1836.get(b) or re.findall(r'"state_region": \["=", "s:(STATE_\w+)"\]',
                                                          json.dumps(vanilla[b]))
                self.assertIn(m.state, [where] if isinstance(where, str) else where, m)
            else:
                text = seeds if m.kind.endswith("landmark") else sites
                self.assertIn(f"KEY = {m.monument} STATE = {m.state} ", text, m)

    def test_every_state_is_scored(self):
        scored = appeal_scores()
        for m in gen.load_moves():
            self.assertIn(m.state, scored, m)

    def test_base_appeal_nets_the_moves(self):
        t = read(TOURISM)
        body = squash(block(t, "tourism_bonus_from_base_appeal"))
        self.assertIn("value = base_tourism_appeal_value subtract = tourism_heritage_moved min = 0", body)
        parks = block(t, "tourism_throughput_from_parks")
        self.assertIn("base_tourism_appeal_value", parks)
        self.assertNotIn("tourism_bonus_from_base_appeal", parks)

    def test_scores_left_match_the_spec(self):
        scores = appeal_scores()
        moved = collections.Counter()
        for m in gen.load_moves():
            moved[m.state] += m.points
        for state, left in {"STATE_ATTICA": 60, "STATE_EASTERN_THRACE": 60, "STATE_BEIJING": 55,
                            "STATE_ILE_DE_FRANCE": 70, "STATE_TUSCANY": 90, "STATE_CAMBODIA": 60,
                            "STATE_CRETE": 75, "STATE_UPPER_EGYPT": 50, "STATE_MOSCOW": 65,
                            "STATE_WESTERN_MALI": 60}.items():
            self.assertEqual(scores[state] - moved[state], left, state)


def moved_totals():
    totals = collections.Counter()
    for m in gen.load_moves():
        totals[m.state] += m.points
    return totals


class ScoreNotes(unittest.TestCase):
    def test_annotate_is_idempotent_and_touches_only_comments(self):
        moves = gen.load_moves()
        once = gen.annotate(read(TOURISM), moves)
        self.assertEqual(gen.annotate(once, moves), once)

        def strip(t):
            return re.sub(r"#.*", "", t)
        self.assertEqual(strip(once), strip(read(TOURISM)))

    def test_annotate_drops_a_stale_note(self):
        text = ("\tif = {\n\t\tlimit = { state_region = s:STATE_A }\n\t\tvalue = 50 # Hills."
                " (20 moved to monuments: tourism_heritage_generated.txt)\n\t}\n")
        self.assertNotIn("moved to monuments", gen.annotate(text, []))

    def test_scores_carry_their_note(self):
        t = read(TOURISM)
        for state, n in moved_totals().items():
            self.assertRegex(t, rf"s:{state} \}}\n\t\tvalue = \d+ #[^\n]*\({n} moved to monuments: "
                                rf"tourism_heritage_generated\.txt\)", state)


class TourismTexts(unittest.TestCase):
    """Review Focus 5: no tourism text credits monuments with throughput, and the output texts name them."""

    def test_throughput_texts_dont_credit_monuments(self):
        for key in ("concept_tourism_throughput_desc", "building_tourism_industry_throughput_add_desc",
                    "te_state_tourism_throughput_applied_tt"):
            text = loc_value(key)
            self.assertIsNotNone(text, key)
            self.assertNotIn("monument", text.lower(), key)

    def test_output_texts_credit_monuments(self):
        for key in ("concept_tourism_output_desc", "te_state_tourism_output_applied_tt"):
            self.assertIn("monument", loc_value(key).lower(), key)

    def test_moved_line_points_at_the_row_and_the_digs(self):
        line = loc_value("te_state_tourism_appeal_moved_line")
        self.assertIn("Monuments below", line)
        self.assertIn("dug", line)


if __name__ == "__main__":
    unittest.main()
