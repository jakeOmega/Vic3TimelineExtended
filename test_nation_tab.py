"""The Nation tab: its registry, the generated filters and counts, and the
country panel's filtered modifier list (spec
docs/superpowers/archive/specs/2026-10-17-national-modifiers-tab-design.md §§ 2-4).

What the engine would never report:

- A permanent modifier the registry doesn't place: the country's list keeps it
  and the tab doesn't show it. Every static modifier script adds without a
  duration must match exactly one registry line.
- A generated file older than the registry: the filter hides a name the tab no
  longer shows, or the tab shows one the list still carries.
- A hidden modifier whose display name another modifier on the country shares:
  the filter matches names (gotcha #40), so it would hide both.
- A redefined vanilla type that differs from vanilla outside its marked blocks.
- A modifier type the tab's modifiers carry that no type registry line places
  (#1030): the type's row is missing, and a new field on a listed modifier
  would go unshown.

No game install needed; the fixture check skips without one.
"""
import json
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
VANILLA_LOC = ROOT / "vanilla_parsed" / "localization_english.json"


def _read(path):
    return Path(path).read_text(encoding="utf-8-sig")


def _loc():
    keys = {}
    for path in sorted(LOC_DIR.rglob("*.yml")):
        for m in re.finditer(r'^ ([\w.\-]+):\d* "(.*)"\s*$', _read(path), re.M):
            keys[m.group(1)] = m.group(2)
    return keys


def _all_loc():
    """The mod's loc over vanilla's (the committed snapshot)."""
    keys = json.loads(VANILLA_LOC.read_text(encoding="utf-8"))
    keys.update(_loc())
    return keys


def _counts(values):
    """{script value: [the modifiers it counts]} from a generated values file."""
    return {name: re.findall(r"has_modifier = (\w+)", body)
            for name, body in re.findall(r"^(\w+) = \{\n(.*?)^\}", values, re.S | re.M)}


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

    def test_a_duration_of_minus_one_is_permanent(self):
        # `days = -1` is forever (vanilla's `months = -1 # FOREVER`): the
        # decolonization endings and the Imperial Federation and Mandate
        # System decisions grant their rewards that way.
        for name in ("commonwealth_path_modifier", "iron_fist_path_modifier", "quiet_assimilation_path_modifier",
                     "imperial_federation_modifier", "mandate_system_modifier"):
            self.assertIn(name, self.candidates)

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
        self.assertEqual(gen.LOC_OUT.read_bytes(), self.outputs[3],
                         "stale: run python3 scripts/generators/gen_nation_tab.py")

    def test_one_bom_each(self):
        for path in (gen.GUI_OUT, gen.VALUES_OUT, gen.PANEL_OUT, gen.LOC_OUT):
            raw = path.read_bytes()
            with self.subTest(path=path.name):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))

    def test_the_filters_and_counts_name_the_same_modifiers(self):
        gui, values, _, _ = self.outputs
        counts = _counts(values)
        hidden = _names_in(_template(gui, "te_nation_hidden_filter"))
        self.assertEqual(sorted(hidden), sorted(counts["gui_country_hidden_modifier_count"]))
        for section in gen.SECTIONS:
            with self.subTest(section=section):
                listed = _names_in(_template(gui, f"te_nation_list_{section}"))
                self.assertEqual(sorted(listed), sorted(counts[f"te_nation_list_{section}_count"]))
                self.assertLessEqual(set(listed), set(hidden))

    def test_the_filters_stay_shallow(self):
        # A balanced Or tree: depth grows with log2 of the names, not their count.
        gui = self.outputs[0]
        for line in gui.splitlines():
            depth = deepest = 0
            for ch in line:
                depth += ch == "("
                depth -= ch == ")"
                deepest = max(deepest, depth)
            self.assertLessEqual(deepest, 16, line[:80])


class TypeRowsTest(unittest.TestCase):
    """The type rows (#1030): every modifier type the tab's modifiers carry is
    a row, a status line or a NOT_A_ROW line, and each row's gate counts
    exactly the modifiers that feed it."""

    @classmethod
    def setUpClass(cls):
        lists, rows, _ = gen.resolve(gen.candidates())
        cls.statics = gen.static_modifiers()
        cls.carried = gen.carried_types(lists, rows, cls.statics)
        cls.placed = gen.classify_types(cls.carried)
        cls.types = gen.type_rows(cls.carried)
        cls.tab = {name for names in (*lists.values(), *rows.values()) for name in names}
        cls.gui, cls.values, _, _ = gen.outputs()

    def _rows(self):
        return [(section, group, kind, row, feeders) for section, groups in self.types.items()
                for group, items in groups for kind, row, feeders in items]

    def test_the_inventory(self):
        # The issue's count (2026-10-18): 149 types, 114 rows, 35 not rows; one
        # row fewer since Long-Haul Seabed Operations moved onto the Deep-Sea
        # Mine (2026-10-27), the only modifier that carried its type
        self.assertGreaterEqual(len(self.carried), 148)
        self.assertGreaterEqual(len(self._rows()), 113)
        self.assertIn("state_arable_land_mult", self.carried)
        self.assertTrue({"agdiff_nitrogen_fixation", "agdiff_green_revolution"}
                        <= set(self.carried["state_arable_land_mult"]))

    def test_every_type_is_placed_once(self):
        unplaced = sorted(kind for kind, lines in self.placed.items() if not lines)
        self.assertFalse(unplaced, "modifier types the tab's modifiers carry with no TYPE_ROWS, STATUS_ROWS "
                                   f"or NOT_A_ROW line in scripts/generators/gen_nation_tab.py: {unplaced}")
        twice = {kind: [line[0] for line in lines] for kind, lines in self.placed.items() if len(lines) > 1}
        self.assertFalse(twice, f"types two type registry lines match (an exact name wins): {twice}")

    def test_every_line_places_a_type(self):
        used = {line for lines in self.placed.values() for line in lines}
        dead = [line[0] for line in gen.type_registry() if line not in used]
        self.assertFalse(dead, f"type registry lines no modifier on the tab carries: {dead}")

    def test_each_entry_once(self):
        entries = [line[0] for line in gen.type_registry()]
        self.assertEqual(sorted(set(entries)), sorted(entries))

    def test_sections_and_groups(self):
        for table in (gen.TYPE_ROWS, gen.STATUS_ROWS):
            self.assertLessEqual(set(table), set(gen.SECTIONS))
        self.assertEqual(list(gen.TYPE_ROWS), list(gen.SECTIONS))
        groups = [group for table in (gen.TYPE_ROWS, gen.STATUS_ROWS) for groups in table.values()
                  for group in groups]
        sections_of = {}
        for table in (gen.TYPE_ROWS, gen.STATUS_ROWS):
            for section, groups_ in table.items():
                for group in groups_:
                    sections_of.setdefault(group, set()).add(section)
        self.assertFalse({g: s for g, s in sections_of.items() if len(s) > 1}, "a group name in two sections")
        loc = _loc()
        missing = sorted(f"te_nation_grp_{g}" for g in set(groups) if f"te_nation_grp_{g}" not in loc)
        self.assertFalse(missing, missing)

    def test_bools_are_status_lines(self):
        for section, group, kind, row, _ in self._rows():
            with self.subTest(kind=kind):
                self.assertEqual(row == "status", kind.endswith("_bool"))
        self.assertIn("country_nuclear_program_pause_bool", [r[2] for r in self._rows() if r[3] == "status"])

    def test_every_row_has_a_name_and_a_description(self):
        loc = _all_loc()
        for _, _, kind, _, _ in self._rows():
            with self.subTest(kind=kind):
                self.assertIn(kind, loc)
                self.assertIn(f"{kind}_desc", loc)

    def test_the_generated_loc_splices_what_exists(self):
        loc = _all_loc()
        generated = gen.generated_loc(self.types)
        for key, value in generated.items():
            for ref in re.findall(r"\$(\w+)\$", value):
                with self.subTest(key=key, ref=ref):
                    self.assertIn(ref, loc)
        for _, _, kind, row, _ in self._rows():
            with self.subTest(kind=kind):
                key = gen.row_key(kind, row)
                self.assertTrue(generated[key].startswith(f"${kind}$: "))
                self.assertIn(f"${kind}_desc$", generated[key + "_tt"])
                if row == "row":
                    self.assertIn(f"GetValueWithBreakdownFor('{kind}')", generated[key])
                else:
                    self.assertIn(f"GetFullEntryDescFor('{kind}')", generated[key + "_tt"])
                note = kind.startswith(("state_", "building_", "interest_group_", "character_"))
                self.assertEqual(note, "$te_nation_note_" in generated[key + "_tt"])

    def test_counts_name_each_rows_feeders(self):
        counts = _counts(self.values)
        for section, groups in self.types.items():
            union = set()
            for group, items in groups:
                in_group = set()
                for kind, _, feeders in items:
                    with self.subTest(kind=kind):
                        self.assertEqual(counts[gen.type_count(kind)], feeders)
                        for name in feeders:
                            self.assertIn(name, self.tab)
                            self.assertIn(kind, self.statics[name])
                    in_group |= set(feeders)
                self.assertEqual(sorted(counts[gen.group_count(group)]), sorted(in_group), group)
                union |= in_group
            self.assertEqual(sorted(counts[gen.section_count(section)]), sorted(union), section)

    def test_each_row_is_gated_on_its_own_count(self):
        for section, groups in self.types.items():
            body = self.gui[self.gui.index(f"\ttype te_nation_types_{section} = "):]
            body = body[:body.index("\n\t}\n")]
            self.assertIn(f"ScriptValue('{gen.section_count(section)}')", body.split("\n")[1])
            for group, items in groups:
                self.assertIn(f'text = "te_nation_grp_{group}"', body)
                for kind, row, _ in items:
                    with self.subTest(kind=kind):
                        m = re.search(rf'\tte_nation_row = \{{\n\t+visible = "([^"]*)"\n\t+text = "{gen.row_key(kind, row)}"\n'
                                      rf'\t+tooltip = "{gen.row_key(kind, row)}_tt"\n', body)
                        self.assertTrue(m, kind)
                        self.assertIn(f"ScriptValue('{gen.type_count(kind)}')", m.group(1))


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
        # the list's test and the line under it
        self.assertEqual(panel.count("ScriptValue('gui_country_hidden_modifier_count')"), 2)
        # the header keeps vanilla's: the list or the line shows whenever the country has a modifier
        live = "\n".join(line for line in panel.splitlines() if "# vanilla:" not in line)
        self.assertEqual(live.count('visible = "[Not(IsDataModelEmpty(Country.GetTimedModifiers))]"'), 1)
        self.assertLess(live.index("IsDataModelEmpty"), live.index('datamodel = "[Country.GetTimedModifiers]"'))

    def test_a_line_says_where_the_hidden_ones_went(self):
        """2026-10-27 audit, NAT-1: under the list, while it leaves a modifier out, a line counts them; for the
        player's own country a goto opens the window on the Nation tab (rule 9: the tab, then the window)."""
        panel = _read(gen.PANEL_OUT)
        at = panel.index("### MOD: Nation tab: where the modifiers the list leaves out went")
        block = panel[at:panel.index(gen.MOD_CLOSE, at)]
        self.assertGreater(at, panel.index('datamodel = "[Country.GetTimedModifiers]"'))
        self.assertIn("visible = \"[GreaterThan_CFixedPoint( Country.MakeScope.ScriptValue("
                      "'gui_country_hidden_modifier_count'), '(CFixedPoint)0' )]\"", block)
        goto = block[block.index("button_icon_goto = {"):]
        self.assertIn('visible = "[Country.IsLocalPlayer]"', goto)
        clicks = re.findall(r'onclick = "(.*)"', goto)
        self.assertEqual(clicks, ["[GetVariableSystem.Set('te_systems_window_tab', 'nation')]",
                                  "[GetVariableSystem.Set('com_open_window', 'te_systems_window')]"])
        loc = _loc()
        for key in re.findall(r"'?(te_nation_panel_\w+)'?", block):
            with self.subTest(key=key):
                self.assertIn(key, loc)
        self.assertIn("ScriptValue('gui_country_hidden_modifier_count')", loc["te_nation_panel_line"])

    def test_it_defines_the_constants_it_uses(self):
        panel = _read(gen.PANEL_OUT)
        defined = set(re.findall(r"^(@\w+) = ", panel, re.M))
        used = {m for m in re.findall(r"@panel_width\w*", panel)}
        self.assertLessEqual(used, defined)

    def test_the_file_name_loads_first(self):
        # CMF's naming for type redefinitions (gotcha #30)
        self.assertTrue(gen.PANEL_OUT.name.startswith("00_"))


class PanelDriftTest(unittest.TestCase):
    """generated_panel() raises, naming what moved, when a vanilla patch moves
    a line its blocks hook onto, rather than writing a wrong file."""

    @classmethod
    def setUpClass(cls):
        cls.vanilla = _read(gen.VANILLA_PANEL)

    def _mutated(self, old, new):
        self.assertEqual(self.vanilla.count(old), 1, old)
        return self.vanilla.replace(old, new)

    def test_a_wrapped_list_item_raises(self):
        # The filter must sit on the item's root: on an inner widget a hidden
        # row would leave a blank item behind.
        text = self._mutated("\t\t\titem = {\n\t\t\t\tcontainer = {\n",
                             "\t\t\titem = {\n\t\t\t\twidget = {\n\t\t\t\tcontainer = {\n")
        with self.assertRaisesRegex(ValueError, "item"):
            gen.generated_panel(text)

    def test_a_missing_anchor_raises_value_error(self):
        for old, new, anchor in (("### TIMED MODIFIERS", "### MODIFIERS", "TIMED MODIFIERS"),
                                 (f"type {gen.PANEL_TYPE} = ", "type something_else = ", gen.PANEL_TYPE)):
            with self.subTest(anchor=anchor):
                with self.assertRaisesRegex(ValueError, anchor):
                    gen.generated_panel(self._mutated(old, new))


class TabLayoutTest(unittest.TestCase):
    """gui/te_nation_tab.gui: the sections in the spec's order, each section's
    type rows mounted, each list and row line on its generated filter, each
    list gated on its count, and every key the tab prints defined."""

    TAB = ROOT / "gui" / "te_nation_tab.gui"

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(cls.TAB)
        cls.generated = _read(gen.GUI_OUT)

    def test_the_window_mounts_the_tab(self):
        window = _read(ROOT / "gui" / "te_systems_window.gui")
        self.assertIn("te_nation_tab_sections = {}", window)
        self.assertTrue(self.TAB.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_sections_in_order(self):
        body = self.gui[self.gui.index("type te_nation_tab_sections"):]
        order = re.findall(r"^\t\t(te_nation_\w+) = \{\}", body, re.M)
        self.assertEqual(order, ["te_nation_overview_panel"]
                         + [f"te_nation_section_{s}" for s in gen.SECTIONS]
                         + ["te_nation_sources_panel", "te_nation_how_panel"])

    def _type(self, name):
        body = self.gui[self.gui.index(f"type {name} = "):]
        return body[:body.index("\n\t}\n")]

    def test_each_section_mounts_its_type_rows(self):
        # Score rows first, then the type rows (#1030); a section with no score
        # row shows on its type rows' count (rule 8).
        for section in gen.SECTIONS:
            with self.subTest(section=section):
                self.assertIn(f"\ttype te_nation_types_{section} = ", self.generated)
                self.assertEqual(self.gui.count(f"te_nation_types_{section} = {{}}"), 1)
                body = self._type(f"te_nation_section_{section}")
                self.assertIn(f"te_nation_types_{section} = {{}}", body)
                self.assertNotIn("te_nation_list_", body)
        for section in ("science_and_space", "international"):
            first = self._type(f"te_nation_section_{section}").split("\n")[1]
            self.assertIn(f"ScriptValue('te_nation_types_{section}_count')", first)

    def test_every_filter_is_used_once_and_lists_are_gated(self):
        # The lists live in Where These Come From, collapsed, each under its
        # section's name and shown on its count; the panel on their sum.
        sources = self._type("te_nation_sources_panel")
        self.assertIn("ScriptValue('te_nation_lists_count')", sources.split("\n")[1])
        self.assertIn("GetVariableSystem.Toggle('te_nation_sources_open')", sources)
        for section in gen.SECTIONS:
            with self.subTest(section=section):
                self.assertEqual(self.gui.count(f"using = te_nation_list_{section}\n"), 1)
                at = sources.index(f"using = te_nation_list_{section}\n")
                block = sources[sources.rindex("flowcontainer = {", 0, at):at]
                self.assertIn(f"ScriptValue('te_nation_list_{section}_count'), '(CFixedPoint)0' )", block)
                self.assertIn(f'text = "te_nation_sec_{section}"', block)
        lists = re.search(r"te_nation_lists_count = \{\n(.*?)^\}", _read(gen.VALUES_OUT), re.S | re.M).group(1)
        self.assertEqual(re.findall(r"add = te_nation_list_(\w+)_count", lists), list(gen.SECTIONS))
        for row in gen.ROWS:
            with self.subTest(row=row):
                self.assertEqual(self.gui.count(f"using = te_nation_row_{row}\n"), 1)

    def test_a_list_item_has_one_visible(self):
        # The filter is the item's only `visible` (gotcha #17).
        body = self.gui[self.gui.index("type te_nation_list = "):self.gui.index("type te_nation_target_bar")]
        item = body[body.index("item = {"):]
        self.assertNotIn("visible", item)
        self.assertIn('block "filter" {}', item)
        self.assertIn("ignoreinvisible = yes", body)

    def test_every_key_exists(self):
        loc = _loc()
        keys = set(re.findall(r'\b(?:text|tooltip) = "(te_nation_\w+)"', self.gui + self.generated))
        # SelectLocalization's keys in the loc ("( 'key'" or ", 'key'"; ScriptValue('x') has no space)
        keys |= set(re.findall(r"[(,] '(te_nation_\w+)'", " ".join(loc.values())))
        self.assertGreater(len(keys), 30)
        missing = sorted(k for k in keys if k not in loc)
        self.assertFalse(missing, missing)

    def test_every_script_value_exists(self):
        values = _read(ROOT / "common" / "script_values" / "te_nation_values.txt")
        values += _read(gen.VALUES_OUT)
        defined = set(re.findall(r"^(\w+) = \{", values, re.M))
        text = self.gui + self.generated + "\n".join(_loc().values())
        used = set(re.findall(r"ScriptValue\('(te_nation_\w+)'\)", text))
        self.assertTrue(used)
        self.assertLessEqual(used, defined)

    def test_the_judiciary_row(self):
        """Spec § 2.2 and § 7 phase 3: Judicial Independence in Governance,
        after Legislative Override Capacity and before the Algorithmic
        Mandate, once the score exists; a bar heading for its ceiling, the
        ceiling's sources, and the courts' modifiers under it. A fifth
        overview box."""
        self.assertEqual(gen.ROWS["judicial_independence"][0], "governance")
        self.assertIn("te_judicial_independence", gen.ROWS["judicial_independence"][1])
        gov = self.gui[self.gui.index("type te_nation_section_governance = "):
                       self.gui.index("type te_nation_section_society = ")]
        at = [gov.index(k) for k in ('"te_nation_override_row"', '"te_nation_jud_row"', '"te_nation_mandate_row"')]
        self.assertEqual(at, sorted(at))
        jud = gov[gov.rindex("flowcontainer = {", 0, at[1]):at[2]]
        self.assertIn("ScriptValue('te_nation_judiciary_on')", jud.split("\n")[1])
        for value in ("te_jud_display", "te_jud_ceiling"):
            self.assertIn(f"ScriptValue('{value}')", jud)
        self.assertIn("using = te_nation_row_judicial_independence", jud)
        loc = _loc()
        self.assertIn("country_judicial_independence_ceiling_add", loc["te_nation_jud_ceiling_row"])
        self.assertIn("country_judicial_independence_ceiling_mult", loc["te_nation_jud_ceiling_paper_row"])
        overview = self.gui[self.gui.index("type te_nation_overview_panel = "):
                            self.gui.index("type te_nation_section_governance = ")]
        self.assertEqual(overview.count("te_nation_ov_cell = {"), 5)
        self.assertIn('text = "te_nation_ov_jud_cap"', overview)

    def test_the_construction_hover_gives_the_curve(self):
        # Spec § 2.2: GDP per capita against the curve's floor and ceiling; since #1034's follow-up
        # also the slack part, and the cost as factors (the owner's breakdown, 2026-10-18).
        loc = _loc()
        tt = loc["te_nation_construction_row_tt"]
        for value in ("te_cc_gdppc_now", "construction_cost_gdppc_floor", "construction_cost_gdppc_ceiling",
                      "construction_cost_max_mult", "te_cc_gdp_part_now", "te_cc_slack_factor_now",
                      "construction_cost_slack_full", "construction_cost_slack_none",
                      "te_cc_total_factor", "te_cc_scaling_factor", "te_cc_others_factor", "te_cc_direct_rule",
                      "te_cc_has_reading"):
            self.assertIn(f"ScriptValue('{value}')", tt)
        # the slack, once read; before the first reading, a sentence saying so
        self.assertIn("'te_nation_construction_slack_read', 'te_nation_construction_slack_unread'", tt)
        for value in ("te_cc_slack_now", "te_cc_peasants_now", "te_cc_unemployed_now", "te_cc_slack_target",
                      "construction_cost_slack_ease"):
            self.assertIn(f"ScriptValue('{value}')", loc["te_nation_construction_slack_read"])
        for key, modifier in (("te_nation_construction_breakdown", "goods_input_construction_mult"),
                              ("te_nation_construction_breakdown_direct", "country_construction_goods_cost_mult")):
            self.assertIn(f"'{key}'", tt)
            self.assertIn(f"GetPlayer.GetModifier.GetValueWithBreakdownFor('{modifier}')", loc[key])

    def _nation_loc(self):
        return {k: v for k, v in _loc().items() if k.startswith(("te_nation_", "te_window_tab_nation"))}

    def test_the_overview_fits_its_column(self):
        """Each box's caption, its words and its figure fit the 154 column at
        16 (rule 3; test_banking_layout.py's budget: 8.6 units a character at
        16, plus 10%)."""
        from test_banking_layout import MARGIN
        loc = _loc()

        def shown(key, depth=0):
            v = loc[key]
            self.assertLess(depth, 6, key)
            v = re.sub(r"\$(\w[\w.]*)\$", lambda m: shown(m.group(1), depth + 1), v)
            v = re.sub(r"\[Concept\('\w+',\s*'([^']*)'\)\]", r"\1", v)
            v = re.sub(r"\[(concept_\w+)\]", lambda m: shown(m.group(1), depth + 1), v)
            v = re.sub(r"\[[^\[\]]*\]", "9999", v)
            return re.sub(r"#[A-Za-z_]+(?:;\S*)? ", "", v).replace("#!", "")

        cell = self.gui[self.gui.index("type te_nation_ov_cell = "):self.gui.index("type te_nation_list = ")]
        self.assertEqual(set(re.findall(r"max_width = (\d+)", cell)), {"154"})
        keys = set(re.findall(r'"(te_nation_ov_\w+_(?:cap|fig))"', self.gui))
        # the words are a SelectLocalization of these
        for word in (k for k in loc if k.startswith("te_nation_ov_") and k.endswith("_word")):
            keys |= {k for k in re.findall(r"'(te_nation_\w+)'", loc[word]) if k in loc}   # not ScriptValue('x')
        self.assertGreaterEqual(len(keys), 15)
        for key in sorted(keys):
            with self.subTest(key=key):
                text = shown(key)
                self.assertLessEqual(len(text) * 8.6 * MARGIN, 154, f"{key} shows {text!r}")

    def test_the_tab_reads_the_applied_tech_spread(self):
        # global_tech_spread_script_value sweeps 54 technologies across every
        # country: read the value the yearly pulse applied, never the sweep.
        text = self.gui + "\n".join(self._nation_loc().values())
        self.assertNotIn("global_tech_spread_script_value", text)
        values = _read(ROOT / "common" / "script_values" / "te_nation_values.txt")
        self.assertIn("var:te_global_tech_spread_applied", values)
        pulse = _read(ROOT / "common" / "on_actions" / "extra_on_actions.txt")
        pulse = pulse[pulse.index("tech_spread_on_action = {"):]
        pulse = pulse[:pulse.index("\n}\n")]
        self.assertIn("set_variable = { name = te_global_tech_spread_applied", pulse)
        self.assertIn("multiplier = var:te_global_tech_spread_applied", pulse)

    def test_the_tier_reads_authority_as_the_event_does(self):
        # minor_events_timelineextended.2 offers each option only while the
        # country produces more authority than it costs.
        values = _read(ROOT / "common" / "script_values" / "te_nation_values.txt")
        tier = values[values.index("te_nation_override_tier = {"):]
        tier = tier[:tier.index("\n}\n")]
        for size in ("small", "medium", "large"):
            self.assertIn(f"produced_authority > forced_law_through_event_authority_cost_{size}", tier)

    def test_the_override_bar_starts_where_capacity_first_counts(self):
        """Owner, 2026-10-17: every capacity below 0 plays the same, so the
        bar spends no width on it. It starts at the event's own gate (no
        `add`), and each threshold line stands at t / top of the 480 bar,
        for the thresholds the event's trigger and options read."""
        values = _read(ROOT / "common" / "script_values" / "te_nation_values.txt")
        bar = values[values.index("te_nation_override_bar = {"):]
        bar = bar[:bar.index("\n}\n")]
        self.assertNotRegex(bar, r"\b(add|subtract) =")
        top = float(re.search(r"\bdivide = ([\d.]+)", bar).group(1))
        event = _read(ROOT / "events" / "minor_events.txt")
        event = event[event.index("minor_events_timelineextended.2 = {"):]
        event = event[:event.index("\n}\n")]
        gates = sorted({int(g) for g in re.findall(
            r'"modifier:country_legislative_override_capacity_add" >= (\d+)', event)})
        self.assertEqual(gates, [0, 2, 4])
        self.assertGreater(top, gates[-1])
        gov = self.gui[self.gui.index("type te_nation_section_governance = "):
                       self.gui.index("type te_nation_section_society = ")]
        for t in gates:
            with self.subTest(threshold=t):
                m = re.search(r"position = \{ (\d+) -2 \}\s*texture = \S+\s*color = [^\n]+\s*"
                              rf'tooltip = "te_nation_override_line_{t}_tt"', gov)
                self.assertTrue(m, t)
                self.assertEqual(int(m.group(1)), int(t / top * 480))

    def test_the_demographics_pointer_needs_the_tab(self):
        # The Population panel's Demographics tab is off by default
        # (demographics_rule): point to it only while it is there.
        self.assertNotIn("Demographics tab", _loc()["te_nation_wc_row_tt"])
        self.assertIn("te_pops_demog_tab_sgui", self.gui)

    def test_formatters_are_the_mods_proven_ones(self):
        for key, value in self._nation_loc().items():
            for fmt in re.findall(r"\|([^\]]*)\]", value):
                with self.subTest(key=key, fmt=fmt):
                    self.assertIn(fmt, ("0", "1", "2", "+0", "+1", "+2", "%0", "+%0"))

    def test_names_are_spliced_not_spelled(self):
        # Single-source names: a name another key owns is spliced ($key$).
        loc = _loc()
        names = [loc[k] for k in ("inh_great_fortunes", "inh_dispersed_wealth", "law_algorithmic_governance",
                                  "minor_events_timelineextended.2.t", "algorithmic_mandate", "television",
                                  "concept_legislative_override_capacity", "concept_inheritance_concentration",
                                  "global_technological_development", "nuclear_power")]
        for key, value in self._nation_loc().items():
            for name in names:
                with self.subTest(key=key, name=name):
                    self.assertNotIn(name, value)


class NoUnderlineTest(unittest.TestCase):
    """Style guide rule 3 (owner, 2026-10-30): as in vanilla, a row's hover is
    not underlined, the generated type rows and the country panel's line
    included."""

    def test_no_row_underlines_its_text(self):
        row_type = re.search(r"\ttype te_nation_row = textbox \{\n(.*?)\n\t\}", _read(ROOT / "gui" / "te_nation_tab.gui"),
                             re.S).group(1)
        self.assertNotIn("row_format", row_type)
        for name in ("te_nation_tab.gui", "te_nation_generated.gui", "00_te_country_panel_information.gui"):
            with self.subTest(gui=name):
                gui = _read(ROOT / "gui" / name)
                self.assertNotIn("#tooltippable", gui)
                self.assertNotIn("row_format", gui)


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
