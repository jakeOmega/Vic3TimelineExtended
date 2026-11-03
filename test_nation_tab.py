"""The Nation tab: its registry, the generated filters and counts, its All
Modifiers section, and the country panel's Information tab, whose modifier
list moved there (spec
docs/superpowers/archive/specs/2026-10-17-national-modifiers-tab-design.md §§ 2-4;
the owner, 2026-11-03).

What the engine would never report:

- A permanent modifier the registry doesn't place: the tab doesn't show it,
  and nobody decided that. Every static modifier script adds without a
  duration must match exactly one registry line.
- A generated file older than the registry: a list shows a name the registry
  moved, or misses one it added.
- A listed modifier whose display name another modifier on the country shares:
  the lists match names (gotcha #40), so they would show both.
- A redefined vanilla type that differs from vanilla outside its marked block.
- A modifier type the tab's modifiers carry that no type registry line places
  (#1030): the type's row is missing, and a new field on a listed modifier
  would go unshown.
- A listed name in no group, or a count that reads other flags than its list
  (owner, 2026-11-03): a list compares a row's name only with the groups whose
  monthly flag is on, so an ungrouped name would never show, and a count that
  disagreed would draw an empty section or hide a full one.

No game install needed; the fixture check skips without one.
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gui_test_helpers import _type_body, assert_wide_matches_narrow  # noqa: E402
from scripts.generators import gen_nation_tab as gen  # noqa: E402
from scripts.generators import gen_te_systems_window as window_gen  # noqa: E402

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


def _blocks(values):
    """{script value: its body} from a generated values file."""
    return dict(re.findall(r"^(\w+) = \{\n(.*?)^\}", values, re.S | re.M))


def _counts(values):
    """{script value: [the modifiers it counts]} from a generated values file,
    through the values it adds (`add = te_nation_src_<group>_count`)."""
    blocks = _blocks(values)

    def names(name, seen):
        body = blocks[name]
        found = re.findall(r"has_modifier = (\w+)", body)
        for ref in re.findall(r"\badd = (\w+)", body):
            if ref in blocks and ref not in seen:
                found += names(ref, seen | {ref})
        return found

    return {name: names(name, {name}) for name in blocks}


def _call(expr):
    """(function, [arguments]) for an `F(a, b)` expression, or None for a leaf
    (anything that isn't one Not, And or Or call spanning the whole text)."""
    m = re.match(r"(Not|And|Or)\(", expr)
    if not m:
        return None
    depth, quoted, args, start = 0, False, [], m.end()
    for i in range(m.end() - 1, len(expr)):
        ch = expr[i]
        if ch == "'":
            quoted = not quoted
        elif quoted:
            continue
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                if i != len(expr) - 1:
                    return None
                args.append(expr[start:i].strip())
                return m.group(1), args
        elif ch == "," and depth == 1:
            args.append(expr[start:i].strip())
            start = i + 1
    raise AssertionError(f"unbalanced: {expr[:80]}")


def _or_leaves(expr):
    """The arguments of a tree of Or calls, left to right."""
    call = _call(expr)
    if call and call[0] == "Or":
        return [leaf for arg in call[1] for leaf in _or_leaves(arg)]
    return [expr]


FLAG_LEAF = re.compile(r"GreaterThan_CFixedPoint\(Country\.MakeScope\.Var\('te_nation_src_(\w+)'\)\.GetValue, "
                       r"'\(CFixedPoint\)0'\)")
NAME_LEAF = re.compile(r"EqualTo_string\(TimedModifier\.GetName, Localize\('(\w+)'\)\)")


def _gated_groups(expression):
    """{group: [names]} from a gated filter, an Or tree of And(<the group's
    flag>, an Or tree of its names): each name under the flag it sits behind.
    Raises if the filter has any other shape."""
    groups = {}
    for part in _or_leaves(expression):
        call = _call(part)
        assert call and call[0] == "And" and len(call[1]) == 2, part[:80]
        flag_leaf, names = call[1]
        group = FLAG_LEAF.fullmatch(flag_leaf)
        assert group, flag_leaf
        assert group.group(1) not in groups, f"{group.group(1)} twice"
        leaves = [NAME_LEAF.fullmatch(leaf) for leaf in _or_leaves(names)]
        assert all(leaves), names[:80]
        groups[group.group(1)] = [leaf.group(1) for leaf in leaves]
    return groups


def _count_groups(values, name):
    """(the sentinel its gate asks for, {group: [names]}) for a gated count:
    `if = { limit = { has_variable = <sentinel> } <per group: if = { limit =
    { var:<flag> > 0 } <its names> }> }`."""
    blocks, counts = _blocks(values), _counts(values)
    body = blocks[name]
    gate = re.match(r"\tvalue = 0\n\tif = \{\n\t\tlimit = \{ has_variable = (\w+) \}\n(.*)\t\}\n$", body, re.S)
    assert gate, body[:200]
    flags = gate.group(1)
    groups = {}
    for group, inner in re.findall(r"^\t\tif = \{\n\t\t\tlimit = \{ var:te_nation_src_(\w+) > 0 \}\n(.*?)^\t\t\}\n",
                                   gate.group(2), re.S | re.M):
        names = re.findall(r"has_modifier = (\w+)", inner)
        for ref in re.findall(r"\badd = (\w+)", inner):
            if ref in blocks:
                names += counts[ref]
        groups[group] = names
    return flags, groups


def _twins(names):
    """`names` and the SAME_NAME twins a list showing them shows too."""
    return sorted(set(names) | {twin for twin, of in gen.SAME_NAME.items() if of in names})


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

    def test_every_carrier_is_in_no_list(self):
        # The Budget panel itemizes them, and All Modifiers shows them.
        carriers = gen.budget_carriers() & set(self.candidates)
        self.assertIn("te_demog_pension_bill", carriers)
        lists, rows, budget = gen.resolve(self.candidates)
        self.assertEqual(carriers, set(budget))
        self.assertFalse(carriers & set(gen.listed(lists)))
        self.assertFalse(carriers & {name for names in rows.values() for name in names})

    def test_rows_and_lists_are_in_the_tabs_sections(self):
        self.assertEqual(list(gen.SECTIONS), ["governance", "society", "economy", "science_and_space",
                                              "international"])
        for row, (section, _) in gen.ROWS.items():
            self.assertIn(section, gen.SECTIONS, row)

    def test_no_listed_name_is_shared(self):
        """A modifier the tab's lists don't show must not share a listed one's
        display name: the mod's static modifiers that can sit on the country
        (timed ones, the overrides, the budget carriers) against every name a
        section or a row lists."""
        loc = _loc()
        statics = gen.static_modifiers()
        lists, rows, _ = gen.resolve(self.candidates)
        shown = set(gen.listed(lists)) | {name for names in rows.values() for name in names}
        elsewhere = {name for name, lines in self.placed.items() if lines and lines[0][1] == "elsewhere"}
        others = set(statics) - shown - elsewhere - set(gen.SAME_NAME)
        texts = {}
        for name in others:
            texts.setdefault(loc.get(name, name), set()).add(name)
        clashes = {name: sorted(texts[loc.get(name, name)]) for name in sorted(shown)
                   if loc.get(name, name) in texts}
        self.assertFalse(clashes, f"listed modifiers whose display name an unlisted one shares (a list would show "
                                  f"both: SAME_NAME counts a twin with it): {clashes}")
        # each twin shares its listed twin's name, and no list places it
        for twin, of in gen.SAME_NAME.items():
            with self.subTest(twin=twin):
                self.assertEqual(loc[twin], loc[of])
                self.assertIn(of, set(gen.listed(lists)))
                self.assertNotIn(twin, shown)


class GeneratedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = gen.outputs()

    def test_generated_files_are_current(self):
        files = gen.written()
        self.assertEqual({path for path, _ in files},
                         {gen.GUI_OUT, gen.VALUES_OUT, gen.PANEL_OUT, gen.EFFECTS_OUT, gen.LOC_OUT})
        for path, data in files:
            with self.subTest(path=path.name):
                self.assertEqual(path.read_bytes(), data, "stale: run python3 scripts/generators/gen_nation_tab.py")
        self.assertEqual(gen.main(["--check"]), 0)

    def test_one_bom_each(self):
        for path in (gen.GUI_OUT, gen.VALUES_OUT, gen.PANEL_OUT, gen.EFFECTS_OUT, gen.LOC_OUT):
            raw = path.read_bytes()
            with self.subTest(path=path.name):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))

    def test_the_filters_and_counts_name_the_same_modifiers(self):
        gui, values = self.outputs[:2]
        counts = _counts(values)
        lists, _, _ = gen.resolve(gen.candidates())
        for section in gen.SECTIONS:
            with self.subTest(section=section):
                listed = _names_in(_template(gui, f"te_nation_list_{section}"))
                self.assertEqual(_twins(listed), sorted(counts[f"te_nation_list_{section}_count"]))
                self.assertEqual(sorted(listed), lists[section])

    def test_nothing_filters_the_country_panel_any_more(self):
        """The Information tab's list moved to All Modifiers (owner,
        2026-11-03): its filter, its count and the readiness gate are gone,
        and nothing reads them."""
        gui, values = self.outputs[:2]
        for name in ("te_nation_hidden_filter", "gui_country_hidden_modifier_count", "te_nation_hid_"):
            with self.subTest(name=name):
                self.assertNotIn(name, gui + values + _read(gen.EFFECTS_OUT))
                for sub in ("gui", "common", "localization"):
                    for path in sorted((ROOT / sub).rglob("*.*")):
                        if path.suffix in (".gui", ".txt", ".yml"):
                            self.assertNotIn(name, _read(path), path.relative_to(ROOT).as_posix())

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


class SourceGroupsTest(unittest.TestCase):
    """Where These Come From's lists gated by group (owner, 2026-11-03):
    every listed name in one group of SOURCE_GROUPS, a list comparing a row's
    name only with the groups whose monthly flag is on, and each count reading
    the same flags, so a section and its list agree at every moment."""

    @classmethod
    def setUpClass(cls):
        cls.lists, cls.rows, _ = gen.resolve(gen.candidates())
        cls.listed = gen.listed(cls.lists)
        cls.groups = gen.source_groups(cls.listed)
        cls.gui, cls.values = gen.outputs()[:2]
        cls.effects = _read(gen.EFFECTS_OUT)

    def test_every_listed_name_is_in_one_group(self):
        placed = gen.classify_groups(self.listed)
        wrong = {name: [line[0] for line in lines] for name, lines in placed.items() if len(lines) != 1}
        self.assertFalse(wrong, "listed modifiers with no SOURCE_GROUPS line, or two, in "
                                f"scripts/generators/gen_nation_tab.py: {wrong}")
        self.assertEqual(sorted(n for names in self.groups.values() for n in names), self.listed)

    def test_every_group_line_places_a_name(self):
        used = {line for lines in gen.classify_groups(self.listed).values() for line in lines}
        dead = [line for line in gen.group_lines() if line not in used]
        self.assertFalse(dead, f"SOURCE_GROUPS lines no listed modifier matches: {dead}")
        self.assertEqual(list(self.groups), list(gen.SOURCE_GROUPS))

    def test_groups_are_small(self):
        # At most 32 names keeps each group's Or tree five deep (test_the_filters_stay_shallow).
        for group, names in self.groups.items():
            with self.subTest(group=group):
                self.assertLessEqual(len(names), gen.MAX_GROUP)
        self.assertLessEqual(gen.MAX_GROUP, 32)
        self.assertGreaterEqual(len(self.groups), 10)

    def test_each_groups_names_sit_under_its_flag(self):
        for section, names in self.lists.items():
            with self.subTest(section=section):
                listed = _gated_groups(_template(self.gui, f"te_nation_list_{section}"))
                wanted = {group: [n for n in members if n in names] for group, members in self.groups.items()}
                self.assertEqual(listed, {group: members for group, members in wanted.items() if members})

    def test_the_counts_read_the_same_flags(self):
        """Each section's count: 0 until every flag is set, then a group's
        names counted only while its flag is on, the names the list puts under
        it. The list reads its flags bare: it sits in a container shown only
        while its count is above 0 (TabLayoutTest), so it never reads an unset
        one (an invisible container's children aren't evaluated, gotcha #42)."""
        for section, names in self.lists.items():
            with self.subTest(section=section):
                ready, counted = _count_groups(self.values, f"te_nation_list_{section}_count")
                self.assertEqual(ready, gen.sentinel(list(self.groups)))
                self.assertEqual({group: sorted(members) for group, members in counted.items()},
                                 {group: _twins(members) for group, members
                                  in _gated_groups(_template(self.gui, f"te_nation_list_{section}")).items()})

    def test_the_effect_sets_every_flag(self):
        """Every group's flag, unconditionally (0 included), to the live count
        of exactly the group's names, and then the sentinel the counts' gate
        asks for, its name from the group set (#1372 review: one has_variable,
        and a save from an older group set reads as not set)."""
        body = re.search(rf"^{gen.EFFECT} = \{{\n(.*?)^\}}", self.effects, re.S | re.M).group(1)
        lines = [line for line in body.strip("\n").split("\n") if not line.strip().startswith("#")]
        self.assertEqual(lines, [f"\tset_variable = {{ name = te_nation_src_{g} value = te_nation_src_{g}_count }}"
                                 for g in self.groups] + [f"\tset_variable = {gen.sentinel(list(self.groups))}"])
        self.assertNotEqual(gen.sentinel(list(self.groups)), gen.sentinel(list(self.groups)[:-1]))
        counts = _counts(self.values)
        for group, names in self.groups.items():
            with self.subTest(group=group):
                self.assertEqual(sorted(counts[gen.flag_count(group)]), _twins(names))

    def test_the_monthly_pulse_and_game_start_call_it_for_every_country(self):
        """From extra_on_actions.txt's on_monthly_pulse_country, which has no
        rule gate, through a wrapper with none either, and once for every
        country after the lobby (#1372 review: a new game's lists would wait
        for each country's first 30-day pulse). Nothing else calls it."""
        text = _read(ROOT / "common" / "on_actions" / "extra_on_actions.txt")
        hosts = re.findall(r"^on_monthly_pulse_country = \{\n\ton_actions = \{\n(.*?)\t\}\n\}", text, re.S | re.M)
        self.assertEqual(sum(f"\t\t{gen.PULSE}\n" in host for host in hosts), 1)
        wrapper = re.search(rf"^{gen.PULSE} = \{{\n(.*?)^\}}", text, re.S | re.M).group(1)
        self.assertEqual(wrapper, f"\teffect = {{\n\t\t{gen.EFFECT} = yes\n\t}}\n")
        starts = re.findall(r"^on_game_started_after_lobby = \{\n\ton_actions = \{\n(.*?)\t\}\n\}", text, re.S | re.M)
        self.assertEqual(sum(f"\t\t{gen.SEED}\n" in host for host in starts), 1)
        seed = re.search(rf"^{gen.SEED} = \{{\n(.*?)^\}}", text, re.S | re.M).group(1)
        self.assertEqual(seed, f"\teffect = {{\n\t\tevery_country = {{\n\t\t\t{gen.EFFECT} = yes\n\t\t}}\n\t}}\n")
        self.assertEqual(text.count(f"{gen.EFFECT} = yes"), 2)
        callers = []
        for sub in ("common", "events"):
            for path in sorted((ROOT / sub).rglob("*.txt")):
                body = _read(path)
                if any(f"{name} = yes" in body or f"\t\t{name}\n" in body for name in (gen.EFFECT, gen.PULSE, gen.SEED)):
                    callers.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(callers, ["common/on_actions/extra_on_actions.txt"])

    def test_names_that_read_the_same_share_a_group(self):
        """#1372 review: a list matches a row by its text, a count by its key.
        Two listed names that read the same in different groups would let a
        row show under the other group's flag while neither count has it (the
        Tax Code's views read the same for all eight interest groups). Read in
        English, the mod's loc over vanilla's."""
        loc = _all_loc()
        group_of = {name: group for group, names in self.groups.items() for name in names}
        by_text = {}
        for name in self.listed:
            by_text.setdefault(loc.get(name, name), set()).add(name)
        split = {text: sorted(names) for text, names in by_text.items()
                 if len({group_of[name] for name in names}) > 1}
        self.assertFalse(split, f"listed names that read the same in two SOURCE_GROUPS groups: {split}")
        views = [name for name in self.listed if name.startswith("te_tax_ig_view_")]
        self.assertEqual(len(views), 32)
        self.assertEqual({group_of[name] for name in views}, {"tax_views"})

    def test_the_rows_stay_ungated(self):
        # A score row's list is one to four names, near-universal ones: a flag
        # would cost as much as it saves, so they compare live.
        for row in gen.ROWS:
            with self.subTest(row=row):
                self.assertNotIn("Var(", _template(self.gui, f"te_nation_row_{row}"))


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
        cls.gui, cls.values = gen.outputs()[:2]

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
    its modifier list replaced by a line leading to the Nation tab's All
    Modifiers (owner, 2026-11-03), the change in one `### MOD: Nation tab`
    block that keeps every vanilla line it replaces."""

    @staticmethod
    def _type_lines(text):
        lines = text.splitlines()
        start = next(i for i, line in enumerate(lines) if line.strip().startswith(f"type {gen.PANEL_TYPE} = "))
        depth = 0
        for i in range(start, len(lines)):
            depth += lines[i].count("{") - lines[i].count("}")
            if depth == 0:
                return lines[start:i + 1]
        raise AssertionError("the type never closes")

    def test_only_marked_blocks_differ_from_vanilla(self):
        """Undo each marked block (drop what it adds, put back the vanilla
        lines it records) and the type is vanilla's, line for line."""
        restored, blocks, inside = [], 0, False
        for line in self._type_lines(_read(gen.PANEL_OUT)):
            text = line.strip()
            if text.startswith(gen.MOD_OPEN):
                blocks, inside = blocks + 1, True
            elif text == gen.MOD_CLOSE:
                inside = False
            elif not inside:
                restored.append(text)
            elif text.startswith(gen.VANILLA_LINE):
                restored.append(text[len(gen.VANILLA_LINE):].strip())
        self.assertEqual(blocks, 1)
        self.assertFalse(inside)
        vanilla = [line.strip() for line in self._type_lines(_read(gen.VANILLA_PANEL))]
        self.assertEqual([line for line in restored if line], [line for line in vanilla if line])

    def test_the_list_is_gone(self):
        """No list, so nothing on the tab compares names or reads a script
        value per row. The header keeps vanilla's test, and the line takes the
        same one: both show whenever the country has a modifier."""
        panel = _read(gen.PANEL_OUT)
        live = "\n".join(line for line in panel.splitlines() if "# vanilla:" not in line)
        self.assertNotIn("using = te_nation_", live)
        live = live[live.index("### TIMED MODIFIERS"):]
        for gone in ("datamodel", "EqualTo_string", "TimedModifier.", "ScriptValue"):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, live)
        test = 'visible = "[Not(IsDataModelEmpty(Country.GetTimedModifiers))]"'
        self.assertEqual(live.count(test), 2)
        self.assertLess(live.index('text = "MODIFIERS"'), live.index("### MOD: Nation tab"))

    def test_a_line_says_how_many_and_where_they_are(self):
        """Under MODIFIERS a line counts the country's modifiers, with no
        filter (GetDataModelSize), and says they are on the Nation tab. For the
        player's own country a goto opens the window on the Nation tab (rule 9:
        the tab, then the window). For another country a goto opens National
        Info on its Nation tab (spec 2026-11-02-charts-help-national-info
        § 6.2, way in 3): the window's tab first (te_ni_tab, PR F1's key), then
        vanilla's way into the window, as the country's Politics tab opens it
        (country_panel.gui's POP_BROWSER button)."""
        panel = _read(gen.PANEL_OUT)
        at = panel.index("### MOD: Nation tab: the list moved to the Nation tab's All Modifiers")
        block = panel[at:panel.index(gen.MOD_CLOSE, at)]
        live = "\n".join(line for line in block.splitlines() if "# vanilla:" not in line)
        self.assertIn('visible = "[Not(IsDataModelEmpty(Country.GetTimedModifiers))]"', live)
        gotos = live.split("button_icon_goto = {")[1:]
        self.assertEqual(len(gotos), 2)
        own, other = (goto[:goto.index("\n\t\t\t}")] for goto in gotos)
        self.assertIn('visible = "[Country.IsLocalPlayer]"', own)
        self.assertIn('tooltip = "te_nation_panel_goto_tt"', own)
        self.assertEqual(re.findall(r'onclick = "(.*)"', own),
                         ["[GetVariableSystem.Set('te_systems_window_tab', 'nation')]",
                          "[GetVariableSystem.Set('com_open_window', 'te_systems_window')]"])
        self.assertIn('visible = "[Not( Country.IsLocalPlayer )]"', other)
        self.assertIn('tooltip = "te_nation_panel_goto_other_tt"', other)
        self.assertEqual(re.findall(r'onclick = "(.*)"', other),
                         ["[GetVariableSystem.Set('te_ni_tab', 'nation')]",
                          "[InformationPanelBar.OpenPopBrowserPanel( Country.Self )]"])
        loc = _loc()
        # the window by its own name, the country's adjective in front (POP_BROWSER)
        for key in ("te_nation_panel_goto_other_tt", "te_nation_panel_line_other_tt"):
            with self.subTest(key=key):
                self.assertIn("$POP_BROWSER$", loc[key])
                self.assertIn("$te_window_tab_nation$", loc[key])
        for key in re.findall(r"'?(te_nation_panel_\w+)'?", live):
            with self.subTest(key=key):
                self.assertIn(key, loc)
        self.assertIn("[GetDataModelSize(Country.GetTimedModifiers)]", loc["te_nation_panel_line"])
        # where they went, by the section's own name, and why (the mechanism)
        for key in ("te_nation_panel_line_tt", "te_nation_panel_line_other_tt"):
            with self.subTest(key=key):
                self.assertIn("$te_nation_all_header$", loc[key])
                self.assertIn("every frame", loc[key])

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

    def test_a_list_without_its_datamodel_raises(self):
        # The block replaces the list the second test opens: a vanilla patch
        # that moves the datamodel must stop the generator, not drop a widget.
        text = self._mutated('\t\t\tdatamodel = "[Country.GetTimedModifiers]"\n',
                             '\t\t\tdatamodel = "[Country.GetSomethingElse]"\n')
        with self.assertRaisesRegex(ValueError, "datamodel"):
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
        # the window's tab mounts are generated (scripts/generators/gen_te_systems_window.py)
        window = _read(ROOT / "gui" / "te_systems_window_generated.gui")
        self.assertIn("te_nation_tab_sections = {}", window)
        self.assertTrue(self.TAB.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_sections_in_order(self):
        body = self.gui[self.gui.index("type te_nation_tab_sections"):]
        order = re.findall(r"^\t\t(te_nation_\w+) = \{\}", body, re.M)
        self.assertEqual(order, ["te_nation_overview_panel"]
                         + [f"te_nation_section_{s}" for s in gen.SECTIONS]
                         + ["te_nation_sources_panel", "te_nation_all_panel", "te_nation_how_panel"])

    def test_the_full_screen_layout(self):
        """te_nation_wide_sections, the window's full-screen layout (spec
        2026-11-02-te-window-wide-mode § 7): the tab's sections in three
        columns, read down each and then across. The registry mounts it in
        place of te_nation_tab_sections, which carries no gate or context."""
        columns = assert_wide_matches_narrow(self, "te_nation_wide_sections", ["te_nation_tab_sections"])
        self.assertEqual(columns, [
            ["te_nation_overview_panel", "te_nation_section_governance", "te_nation_section_society"],
            ["te_nation_section_economy", "te_nation_section_science_and_space", "te_nation_section_international"],
            ["te_nation_sources_panel", "te_nation_all_panel", "te_nation_how_panel"]])
        tab = next(t for t in window_gen.TABS if t.key == "nation")
        self.assertEqual((tab.layout, tab.wide), (None, "te_nation_wide_sections"))
        self.assertNotRegex(_type_body(self.gui, "te_nation_tab_sections"), r"(?m)^\s*(visible|datacontext) =")

    def _type(self, name):
        body = self.gui[self.gui.index(f"type {name} = "):]
        return body[:body.index("\n\t}\n")]

    def test_all_modifiers(self):
        """All Modifiers (owner, 2026-11-03): every modifier the country holds
        in vanilla's row (icon, name, time left, its own tooltip), with no
        filter; collapsed by default (te_nation_all_open, set while open), and
        its rows inside the panel that flag shows, so none is evaluated while
        it is collapsed (gotcha #42). It reads the shown Country and is public:
        no te_own_country_only (ForeignViewTest holds the closure)."""
        body = _type_body(self.gui, "te_nation_all_panel")
        self.assertEqual(body.split("\n")[1].strip(),
                         'visible = "[Not(IsDataModelEmpty(Country.GetTimedModifiers))]"')
        self.assertIn("onclick = \"[GetVariableSystem.Toggle('te_nation_all_open')]\"", body)
        self.assertIn('text = "te_nation_all_header_count"', body)
        panel = body[body.index("te_nation_panel = {"):]
        self.assertEqual(panel.split("\n")[1].strip(), "visible = \"[GetVariableSystem.Exists('te_nation_all_open')]\"")
        self.assertEqual(body.count('datamodel = "[Country.GetTimedModifiers]"'), 1)
        self.assertIn('datamodel = "[Country.GetTimedModifiers]"', panel)
        item = panel[panel.index("item = {"):]
        for part in ('tooltip = "[TimedModifier.GetTooltip]"', 'texture = "[TimedModifier.GetIcon]"',
                     'text = "[TimedModifier.GetName]"', 'text = "[TimedModifier.GetRemainingDuration]"'):
            with self.subTest(part=part):
                self.assertIn(part, item)
        for absent in ("visible", "using = te_nation_list_", "using = te_nation_row_", "te_own_country_only",
                       "GetPlayer"):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, item if absent == "visible" else body)
        loc = _loc()
        self.assertIn("[GetDataModelSize(Country.GetTimedModifiers)]", loc["te_nation_all_header_count"])
        self.assertIn("$te_nation_all_header$", loc["te_nation_all_header_count"])
        self.assertIn("te_nation_all_header_tt", body)

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

    # The UN lines' rows, each with the UN display code it reads and the UN
    # overview's words for that code (gui/journal_entry_widgets/un_overview_widget.gui).
    # The UN lines' rows: the UN display code each reads, the UN overview's
    # words for its values in order (gui/journal_entry_widgets/un_overview_widget.gui),
    # and the one other value the row may read, its figure's condition.
    UN_ROWS = (
        ("te_nation_un_member_row", "un_disp_member_code", [f"je_un_ov_member_{i}" for i in range(1, 7)], None),
        ("te_nation_un_standing_row", "un_disp_standing_code", [f"je_un_ov_standing_{i}" for i in range(0, 7)],
         None),
        ("te_nation_un_dues_row", "un_disp_dues_code", [f"je_un_ov_dues_{i}" for i in range(1, 6)],
         "un_disp_arrears_months"),
    )
    # A branch of a code's SelectLocalization chain: the value tested and the
    # key it picks, whose last _N must be that value.
    UN_BRANCH = re.compile(r"EqualTo_CFixedPoint\( Country\.MakeScope\.ScriptValue\('(\w+)'\), "
                           r"'\(CFixedPoint\)(-?\d+)' \), '(\w+?_(-?\d+))'")

    def _assert_chain(self, text, code, keys):
        """text picks keys[i] for each value of code in order, the last one
        the fallback: each branch's value is its key's suffix, and every
        branch tests code."""
        branches = self.UN_BRANCH.findall(text)
        self.assertEqual([key for _, _, key, _ in branches], keys[:-1])
        for tested, value, key, suffix in branches:
            with self.subTest(key=key):
                self.assertEqual(tested, code)
                self.assertEqual(value, suffix)
        self.assertIn(f"'{keys[-2]}', '{keys[-1]}' )", text)

    def test_the_un_lines(self):
        """The United Nations in International (spec
        2026-11-02-charts-help-national-info § 6.4; the owner put Nation with
        the UN lines on the public list, the UN's own tab private): the
        country's seat, its standing and its dues, with any arrears, once a UN
        exists. They read the UN's own display codes, the overview's
        (common/script_values/un_overview_display_values.txt), which ask the
        entry's modifiers through je: in script and so read any country, and
        they say what the overview says. The section shows while they do, or
        while its type rows do."""
        un_on = "GreaterThan_CFixedPoint( Country.MakeScope.ScriptValue('un_disp_member_code'), '(CFixedPoint)0' )"
        types_on = ("GreaterThan_CFixedPoint( Country.MakeScope.ScriptValue('te_nation_types_international_count'), "
                    "'(CFixedPoint)0' )")
        body = self._type("te_nation_section_international")
        self.assertEqual(body.split("\n")[1].strip(), f'visible = "[Or( {un_on}, {types_on} )]"')
        at = body.index('text = "te_nation_un_member_row"')
        block = body[body.rindex("flowcontainer = {", 0, at):body.index("te_nation_types_international = {}")]
        self.assertEqual(block.split("\n")[1].strip(), f'visible = "[{un_on}]"')
        self.assertEqual(re.findall(r'text = "(te_nation_un_\w+)"', block), [row for row, _, _, _ in self.UN_ROWS])
        # standing once the country has a score (a member, or one that left);
        # dues while it is a member
        rows = block.split("te_nation_row = {")[1:]
        self.assertNotIn("visible", rows[0])
        self.assertIn("visible = \"[Not( EqualTo_CFixedPoint( Country.MakeScope.ScriptValue('un_disp_standing_code'), "
                      "'(CFixedPoint)-1' ) )]\"", rows[1])
        self.assertIn("visible = \"[GreaterThan_CFixedPoint( Country.MakeScope.ScriptValue('un_disp_dues_code'), "
                      "'(CFixedPoint)0' )]\"", rows[2])
        loc = _loc()
        for row, code, words, figure in self.UN_ROWS:
            with self.subTest(row=row):
                self.assertIn(f'tooltip = "{row}_tt"', block)
                self.assertIn(f"{row}_tt", loc)
                text = loc[row]
                self.assertEqual(re.findall(r"'(je_un_ov_\w+)'", text), words)
                self._assert_chain(text, code, words)
                for word in words:
                    self.assertIn(word, loc, "the overview's word: without it the row shows a raw key")
                self.assertNotIn("JournalEntry", text)
                self.assertLessEqual(set(re.findall(r"ScriptValue\('(\w+)'\)", text)), {code, figure} - {None})
                self.assertTrue(text.startswith("[concept_"), "Label: value, the label a concept (rule 3)")
        # The figures: the score unless the country is not yet rated (code 1),
        # the months in arrears while any are owed; each reads its own value.
        self.assertIn("[AddLocalizationIf( Not( EqualTo_CFixedPoint( Country.MakeScope.ScriptValue("
                      "'un_disp_standing_code'), '(CFixedPoint)1' ) ), 'te_nation_un_standing_fig' )]",
                      loc["te_nation_un_standing_row"])
        self.assertIn("[AddLocalizationIf( GreaterThan_CFixedPoint( Country.MakeScope.ScriptValue("
                      "'un_disp_arrears_months'), '(CFixedPoint)0' ), 'te_nation_un_arrears' )]",
                      loc["te_nation_un_dues_row"])
        for key, value in (("te_nation_un_standing_fig", "un_disp_standing"),
                           ("te_nation_un_arrears", "un_disp_arrears_months")):
            with self.subTest(key=key):
                self.assertEqual(set(re.findall(r"ScriptValue\('(\w+)'\)", loc[key])), {value})
        # The seat's hover says what each state means, Cannot Join and Not a
        # Member included; the dues' says who pays where the overlord does.
        self._assert_chain(loc["te_nation_un_member_row_tt"], "un_disp_member_code",
                           [f"te_nation_un_member_tt_{i}" for i in range(1, 7)])
        self._assert_chain(loc["te_nation_un_dues_basis_tt"], "un_disp_dues_code",
                           ["te_nation_un_dues_tt_1", "te_nation_un_dues_rate_tt"])
        for key in [f"te_nation_un_member_tt_{i}" for i in range(1, 7)] + ["te_nation_un_dues_tt_1"]:
            with self.subTest(key=key):
                self.assertIn(key, loc)
        self.assertIn("$te_nation_un_dues_basis_tt$", loc["te_nation_un_dues_arrears_tt"])
        self.assertIn("'te_nation_un_dues_arrears_tt', 'te_nation_un_dues_basis_tt' )",
                      loc["te_nation_un_dues_row_tt"])
        values = "".join(_read(ROOT / "common" / "script_values" / name)
                         for name in ("un_overview_display_values.txt", "un_dues_values.txt"))
        defined = set(re.findall(r"^(\w+) = \{", values, re.M))
        text = block + "\n".join(v for k, v in loc.items() if k.startswith("te_nation_un_"))
        used = set(re.findall(r"ScriptValue\('(un_\w+)'\)", text))
        self.assertGreaterEqual(len(used), 6)
        self.assertLessEqual(used, defined)

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
            self.assertIn(f"Country.GetModifier.GetValueWithBreakdownFor('{modifier}')", loc[key])

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
        # Another country's (National Info, spec 2026-11-02-charts-help-national-info
        # § 6.8): its Demographics tab is in the window it is shown in, not the
        # player's Population panel.
        self.assertIn("SelectLocalization( Country.IsLocalPlayer, 'te_nation_wc_row_demog_tt', "
                      "'te_nation_wc_row_demog_other_tt' )", self.gui)
        other = _loc()["te_nation_wc_row_demog_other_tt"]
        self.assertIn("$POP_BROWSER$", other)
        self.assertNotIn("Population", other)

    def test_formatters_are_the_mods_proven_ones(self):
        # D: money, as the UN overview's Dues figure prints what is owed
        # (je_un_ov_dues_fig_4), which the UN lines' arrears hover repeats.
        for key, value in self._nation_loc().items():
            for fmt in re.findall(r"\|([^\]]*)\]", value):
                with self.subTest(key=key, fmt=fmt):
                    self.assertIn(fmt, ("0", "1", "2", "+0", "+1", "+2", "%0", "+%0", "D"))

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


class ForeignViewTest(unittest.TestCase):
    """Another country's Nation tab, in National Info (spec
    2026-11-02-charts-help-national-info § 6.4: Nation shows another country
    everything; its Hidden column is empty). test_te_system_tab_bodies.py's
    BindingTest holds its reads to the shown Country and GuardTest its
    controls to te_own_country_only; this holds the tab to having nothing to
    hide and nothing that acts."""

    def test_nothing_is_hidden_and_nothing_acts(self):
        from gui_test_helpers import CONTROL, GUARD, mod_types, type_closure
        tab = next(t for t in window_gen.TABS if t.key == "nation")
        self.assertTrue(tab.public)
        types = mod_types()
        closure = type_closure({tab.wide}, types)
        self.assertGreater(len(closure), 15)
        for name in sorted(closure):
            body = types[name].body
            with self.subTest(type=name):
                self.assertNotIn(GUARD, body, "nothing on the Nation tab is private (spec § 6.4)")
                self.assertIsNone(CONTROL.search(body), "the Nation tab has no control: one goes under "
                                                        "te_own_country_only (GuardTest), and this test changes")


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
