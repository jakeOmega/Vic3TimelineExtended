"""The Extraplanetary Base ground types as the player reads them (ground types
design §§ 9.2, 9.6; plan Task 9).

Each type's description states its seven figures, rounded from
``ebase_ground.mix``, in the goods' order; each site's hover in the Modules view
and in Solar System splices its own type's description; the Help page names
every type. The figures and the site map live in
``scripts/generators/ebase_ground.py``, so a change there fails here until the
loc follows.
"""
import glob
import json
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import ebase_ground as eg  # noqa: E402
import gen_solar_sites as gss  # noqa: E402

LOC_DIR = os.path.join(REPO, "localization", "english")
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "space_race_widget.gui")
ROWS = os.path.join(REPO, "gui", "journal_entry_widgets", "sr_sites_generated_rows.gui")
CONCEPTS = os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt")
VANILLA_LOC = os.path.join(REPO, "vanilla_parsed", "localization_english.json")

MINUS = "−"
# A figure as the descriptions print it: "$iron$: #v +12%#!", a true minus below 0.
FIGURE = re.compile(r"\$(\w+)\$: #v ([+−])(\d+)%#!")

_LOC: dict[str, str] = {}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _loc(key):
    if not _LOC:
        for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
            # A value, then perhaps a trailing comment (a `# REVIEWED` exemption).
            for k, v in re.findall(r'^ ([\w.\-]+):\d* "(.*)"(?:\s+#[^"]*)?\s*$', _read(path), re.M):
                _LOC[k] = v
    assert key in _LOC, f"no loc {key}"
    return _LOC[key]


def _good_name(good):
    """A good's name as the game shows it: the mod's rename, else vanilla's."""
    try:
        return _loc(good)
    except AssertionError:
        with open(VANILLA_LOC, encoding="utf-8") as f:
            return dict(json.load(f))[good]


def _signed(n: int) -> str:
    return f"{n:+d}".replace("-", MINUS)


def _type_keys(text):
    """The ground types a text names, by their sr_ground_<type> keys."""
    return set(re.findall(rf"sr_ground_({'|'.join(eg.TYPES)})\b", text))


class TypeDescriptions(unittest.TestCase):
    def test_every_type_has_a_word_and_a_description(self):
        for t in eg.TYPES:
            with self.subTest(type=t):
                self.assertEqual(_loc(f"sr_ground_{t}"), t.capitalize())
                self.assertTrue(_loc(f"sr_ground_{t}_desc"))

    def test_type_desc_figures_match_the_model(self):
        """All seven figures, each its good's rounded mix in percent, in the goods' order."""
        for t in eg.TYPES:
            with self.subTest(type=t):
                found = FIGURE.findall(_loc(f"sr_ground_{t}_desc"))
                self.assertEqual([g for g, _, _ in found], list(eg.GOODS))
                stated = [int(n) * (-1 if sign == MINUS else 1) for _, sign, n in found]
                self.assertEqual(stated, [round(100 * eg.mix(t)[g]) for g in eg.GOODS])

    def test_goods_are_spliced_not_spelled(self):
        """Single-source names: a good is its own key, never its name typed out."""
        for t in eg.TYPES:
            with self.subTest(type=t):
                text = _loc(f"sr_ground_{t}_desc")
                for g in eg.GOODS:
                    self.assertNotIn(_good_name(g), text.replace(f"${g}$", ""))


class SiteHovers(unittest.TestCase):
    def test_site_hover_splices_its_own_type(self):
        """Each colony's base room hover (the Modules view) names its own type and
        no other, splices that type's description, and states its grade."""
        for site in gss.SITES:
            t = eg.GROUND[site.key]
            with self.subTest(site=site.key):
                text = _loc(f"je_space_race_widget_bases_tt_{site.key}")
                self.assertIn(f"$sr_ground_{t}_desc$", text)
                self.assertEqual(_type_keys(text), {t})
                self.assertIn(f"[concept_sr_base_grade] is #v {_signed(site.ebase_grade)}%#!", text)
                self.assertIn(f"#v {site.ebase_room}#! levels from the world", text)

    def test_site_hover_says_blockaded_levels_come_back(self):
        """Under the new design a blockade moves the levels, it does not idle them
        (spec § 8.2 steps 2 and 3)."""
        for site in gss.SITES:
            with self.subTest(site=site.key):
                text = _loc(f"je_space_race_widget_bases_tt_{site.key}")
                self.assertNotIn("Nothing while it is blockaded", text)
                self.assertIn("work elsewhere until it is freed", text)

    def test_solar_system_hover_is_per_type(self):
        """Solar System's base room hover is its type's key (spec § 9.2): each row
        names its own site's type, and the shared key is gone."""
        rows = _read(ROWS)
        named = re.findall(r'blockoverride "site_name" \{\s*text = "sr_site_name_(\w+)"', rows)
        tips = re.findall(r'blockoverride "site_bases_tooltip" \{\s*tooltip = "je_space_race_widget_ss_bases_tt_(\w+)"', rows)
        words = re.findall(r'blockoverride "site_ground" \{\s*text = "sr_ground_(\w+)"', rows)
        self.assertEqual(len(named), 80)  # Solar System's and the colony target popup's
        self.assertEqual(tips, [eg.GROUND[k] for k in named])
        self.assertEqual(words, [eg.GROUND[k] for k in named])
        self.assertNotIn('"je_space_race_widget_ss_bases_tt"', _read(GUI))
        with self.assertRaises(AssertionError):
            _loc("je_space_race_widget_ss_bases_tt")
        for t in set(tips):
            with self.subTest(type=t):
                text = _loc(f"je_space_race_widget_ss_bases_tt_{t}")
                self.assertIn(f"$sr_ground_{t}_desc$", text)
                self.assertEqual(_type_keys(text), {t})


class ConceptsAndHelp(unittest.TestCase):
    def test_ground_type_concept(self):
        """Ground Type (spec § 9.6): registered, named, and a line for each type."""
        self.assertRegex(_read(CONCEPTS), r"(?m)^concept_sr_ground_type = \{\}")
        self.assertEqual(_loc("concept_sr_ground_type"), "Ground Type")
        text = _loc("concept_sr_ground_type_desc")
        for t in eg.TYPES:
            with self.subTest(type=t):
                self.assertIn(f"\\n#b $sr_ground_{t}$#!:", text)

    def test_base_grade_no_longer_fills_the_best_room_first(self):
        """Under the new design the checkbox or the player decides where levels
        work; only unassigned levels fill by grade (spec § 9.6)."""
        text = _loc("concept_sr_base_grade_desc")
        self.assertNotIn("best room first", text)
        self.assertIn("[concept_sr_ground_type]", text)

    def test_help_lines_cover_every_type(self):
        """How Solar Colonization Works names every type, a line each, and gives
        the checkbox's rule; the topic is on the Help page under Simple and Full
        Colonies."""
        text = _loc("je_space_race_widget_howc_bases")
        for t in eg.TYPES:
            with self.subTest(type=t):
                self.assertIn(f"\\n#b $sr_ground_{t}$#!:", text)
        self.assertIn("a quarter of our levels a year", text)
        self.assertIn("5%", text)
        self.assertIn('text = "je_space_race_widget_howc_bases"', _read(GUI))

    def test_near_earth_has_a_name(self):
        self.assertEqual(_loc(f"sr_site_name_{eg.NEAR_EARTH}"), "Near-Earth Asteroids")


if __name__ == "__main__":
    unittest.main()
