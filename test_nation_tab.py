"""The Nation tab: its registry, the generated filters and counts, and the
country panel's filtered modifier list (spec
docs/superpowers/specs/2026-10-17-national-modifiers-tab-design.md §§ 2-4).

What the engine would never report:

- A permanent modifier the registry doesn't place: the country's list keeps it
  and the tab doesn't show it. Every static modifier script adds without a
  duration must match exactly one registry line.
- A generated file older than the registry: the filter hides a name the tab no
  longer shows, or the tab shows one the list still carries.
- A hidden modifier whose display name another modifier on the country shares:
  the filter matches names (gotcha #40), so it would hide both.
- A redefined vanilla type that differs from vanilla outside its marked blocks.

No game install needed; the fixture check skips without one.
"""
import difflib
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scripts.generators import gen_nation_tab as gen  # noqa: E402

LOC_DIR = ROOT / "localization" / "english"


def _read(path):
    return Path(path).read_text(encoding="utf-8-sig")


def _loc():
    keys = {}
    for path in sorted(LOC_DIR.rglob("*.yml")):
        for m in re.finditer(r'^ ([\w.\-]+):\d* "(.*)"\s*$', _read(path), re.M):
            keys[m.group(1)] = m.group(2)
    return keys


def _names_in(expression):
    return re.findall(r"EqualTo_string\(TimedModifier\.GetName, Localize\('(\w+)'\)\)", expression)


def _template(text, name):
    m = re.search(rf'^template {name} \{{\n\tvisible = "\[(.*)\]"\n\}}', text, re.M)
    assert m, f"no template {name}"
    return m.group(1)


class RegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = gen.candidates()
        cls.placed = gen.classify(cls.candidates)

    def test_the_finder_expands_parameters(self):
        # agdiff_$TECH$ from its callers, a two-level demographic line, a milestone's first
        for name in ("agdiff_nitrogen_fixation", "agdiff_green_revolution", "te_demog_line_births_up",
                     "sr_first_moon_landing", "inh_great_fortunes", "un_regime_naval_curb_modifier"):
            self.assertIn(name, self.candidates)
        # timed only: Forceful Legislation's decaying penalty is no candidate
        self.assertNotIn("forced_law_through_event_consequences_small", self.candidates)
        self.assertGreater(len(self.candidates), 600)

    def test_every_candidate_is_placed_once(self):
        unplaced = sorted(name for name, lines in self.placed.items() if not lines)
        self.assertFalse(unplaced, "permanent modifiers with no registry line in "
                                   f"scripts/generators/gen_nation_tab.py: {unplaced}")
        twice = {name: [line[0] for line in lines] for name, lines in self.placed.items() if len(lines) > 1}
        self.assertFalse(twice, f"permanent modifiers two registry lines match (an exact name wins): {twice}")

    def test_every_line_places_a_candidate(self):
        used = {line[:2] for lines in self.placed.values() for line in lines}
        dead = [entry for entry, kind, _ in gen.registry() if (entry, kind) not in used]
        self.assertFalse(dead, f"registry lines that place no permanent modifier (renamed, timed now, "
                               f"or a budget source): {dead}")

    def test_every_carrier_is_hidden(self):
        carriers = gen.budget_carriers() & set(self.candidates)
        self.assertIn("te_demog_pension_bill", carriers)
        _, _, hidden = gen.resolve(self.candidates)
        self.assertLessEqual(carriers, set(hidden))

    def test_rows_and_lists_are_in_the_tabs_sections(self):
        self.assertEqual(list(gen.SECTIONS), ["governance", "society", "economy", "science_and_space",
                                              "international"])
        for row, (section, _) in gen.ROWS.items():
            self.assertIn(section, gen.SECTIONS, row)

    def test_no_hidden_name_is_shared(self):
        """A modifier the list keeps must not share a hidden one's display
        name: the mod's static modifiers that can sit on the country (timed
        ones, the overrides) against every hidden name."""
        loc = _loc()
        statics = gen.static_modifiers()
        _, _, hidden = gen.resolve(self.candidates)
        hidden = set(hidden)
        elsewhere = {name for name, lines in self.placed.items() if lines and lines[0][1] == "elsewhere"}
        kept = set(statics) - hidden - elsewhere
        texts = {}
        for name in kept:
            texts.setdefault(loc.get(name, name), set()).add(name)
        clashes = {name: sorted(texts[loc.get(name, name)]) for name in sorted(hidden)
                   if loc.get(name, name) in texts}
        self.assertFalse(clashes, f"hidden modifiers whose display name a kept one shares: {clashes}")


class GeneratedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = gen.outputs()

    def test_generated_files_are_current(self):
        for path, text in zip((gen.GUI_OUT, gen.VALUES_OUT, gen.PANEL_OUT), self.outputs):
            with self.subTest(path=path.name):
                self.assertEqual(_read(path), text, "stale: run python3 scripts/generators/gen_nation_tab.py")

    def test_one_bom_each(self):
        for path in (gen.GUI_OUT, gen.VALUES_OUT, gen.PANEL_OUT):
            raw = path.read_bytes()
            with self.subTest(path=path.name):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))

    def test_the_filters_and_counts_name_the_same_modifiers(self):
        gui, values, _ = self.outputs
        counts = {}
        for name, body in re.findall(r"^(\w+) = \{\n(.*?)^\}", values, re.S | re.M):
            counts[name] = re.findall(r"has_modifier = (\w+)", body)
        hidden = _names_in(_template(gui, "te_nation_hidden_filter"))
        self.assertEqual(sorted(hidden), sorted(counts["gui_country_hidden_modifier_count"]))
        for section in gen.SECTIONS:
            with self.subTest(section=section):
                listed = _names_in(_template(gui, f"te_nation_list_{section}"))
                self.assertEqual(sorted(listed), sorted(counts[f"te_nation_list_{section}_count"]))
                self.assertLessEqual(set(listed), set(hidden))

    def test_the_filters_stay_shallow(self):
        # A balanced Or tree: depth grows with log2 of the names, not their count.
        gui, _, _ = self.outputs
        for line in gui.splitlines():
            depth = deepest = 0
            for ch in line:
                depth += ch == "("
                depth -= ch == ")"
                deepest = max(deepest, depth)
            self.assertLessEqual(deepest, 16, line[:80])


class CountryPanelTest(unittest.TestCase):
    """gui/00_te_country_panel_information.gui: vanilla's Information tab type,
    its modifier list filtered, every change in a `### MOD: Nation tab` block
    that keeps the vanilla line it replaces."""

    def test_only_marked_blocks_differ_from_vanilla(self):
        vanilla = _read(gen.VANILLA_PANEL).splitlines()
        start = next(i for i, line in enumerate(vanilla) if line.strip().startswith(f"type {gen.PANEL_TYPE} = "))
        mod = _read(gen.PANEL_OUT).splitlines()
        mod_start = next(i for i, line in enumerate(mod) if line.strip().startswith(f"type {gen.PANEL_TYPE} = "))
        mod = mod[mod_start:-1]
        vanilla = vanilla[start:start + len(mod) + 20]
        ops = difflib.SequenceMatcher(None, vanilla, mod, autojunk=False).get_opcodes()
        hunks = [op for op in ops if op[0] != "equal"]
        self.assertEqual(len(hunks), 3 + 1, hunks)    # three blocks, and the tail past the type
        for tag, i1, i2, j1, j2 in hunks[:-1]:
            with self.subTest(line=j1):
                self.assertIn(tag, ("insert", "replace"))
                block = [line.strip() for line in mod[j1:j2]]
                self.assertTrue(block[0].startswith(gen.MOD_OPEN), block)
                self.assertEqual(block[-1], gen.MOD_CLOSE)
                for old in vanilla[i1:i2]:
                    self.assertIn(gen.VANILLA_LINE + old.strip(), block)
        self.assertEqual(hunks[-1][0], "delete")    # vanilla's lines after the type

    def test_the_list_hides_by_name_and_counts_what_is_left(self):
        panel = _read(gen.PANEL_OUT)
        self.assertIn("using = te_nation_hidden_filter", panel)
        self.assertIn("ignoreinvisible = yes", panel)
        self.assertEqual(panel.count("ScriptValue('gui_country_hidden_modifier_count')"), 2)
        self.assertNotIn('visible = "[Not(IsDataModelEmpty(Country.GetTimedModifiers))]"',
                         "\n".join(line for line in panel.splitlines() if "# vanilla:" not in line))

    def test_it_defines_the_constants_it_uses(self):
        panel = _read(gen.PANEL_OUT)
        defined = set(re.findall(r"^(@\w+) = ", panel, re.M))
        used = {m for m in re.findall(r"@panel_width\w*", panel)}
        self.assertLessEqual(used, defined)

    def test_the_file_name_loads_first(self):
        # CMF's naming for type redefinitions (gotcha #30)
        self.assertTrue(gen.PANEL_OUT.name.startswith("00_"))


class FixtureTest(unittest.TestCase):
    def test_the_fixture_is_the_installed_file(self):
        base = os.environ.get("VIC3_BASE_GAME")
        if base is None:
            try:
                import path_constants
                base = path_constants.base_game_path
            except Exception:
                base = None
        game = Path(base) / "game" / "gui" / "country_panel.gui" if base else None
        if game is None or not game.is_file():
            self.skipTest("no Victoria 3 install")
        self.assertEqual(gen.VANILLA_PANEL.read_bytes(), game.read_bytes(),
                         "vanilla changed: replace the fixture and run scripts/generators/gen_nation_tab.py")


if __name__ == "__main__":
    unittest.main()
