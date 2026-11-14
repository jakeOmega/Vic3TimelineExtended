"""Build only on local claims (te_seabed_local_only; owner, 2026-11-14): the
Seabed tab's checkbox that keeps new Deep-Sea Mine levels to states whose own
basin has a local claim to spare, so none takes another basin's licence and
its Long-Haul penalty.

The model (scripts/analysis/seabed_model.py: local_room, local_gate_open,
can_build) first: the setting is off by default, the basin's room arithmetic,
the gate in both settings, several levels queued in one month, the
under-construction branch letting one level in and shutting, and random worlds
in which a basin's states never hold more than one distant licence. Then the
script against it: the gate reads the setting inside the rule and only for a
country that isn't AI, the five rooms and their state dispatch, the
requirement line naming the basin and the setting, the recording untouched,
and the checkbox: the player's own, bound to its scripted GUI, under the
boxes it governs.
"""
import copy
import os
import random
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "analysis"))

import seabed_model as m  # noqa: E402
from gui_test_helpers import guard_spans, in_spans, mod_types  # noqa: E402
from test_seabed_layout import UNITS  # noqa: E402
from test_banking_layout import MARGIN, _all_loc  # noqa: E402
from test_seabed_script import EFFECTS, TRIGGERS, VALUES, block, read, strip_comments  # noqa: E402

SGUIS = "common/scripted_guis/te_global_commons_seabed_sguis.txt"
GUI = "gui/te_seabed_widgets.gui"
WORLDS = int(os.environ.get("SEABED_MODEL_WORLDS", "30"))
YEARS = int(os.environ.get("SEABED_MODEL_YEARS", "20"))


def one_country(local_only=False, **unbuilt):
    c = m.Country(0, policy=m.SPONSOR, local_only=local_only)
    c.unbuilt.update(unbuilt)
    return c


class LocalOnlyTest(unittest.TestCase):
    """The model."""

    def test_off_by_default(self):
        self.assertFalse(m.Country(0).local_only)
        world = m.random_world(random.Random(1))
        self.assertFalse(any(c.local_only for c in world.countries.values()))

    def test_local_room_counts_the_basins_states_only(self):
        """Unused claims in the basin, less levels there with no licence yet,
        less the distant licences their levels hold; other basins' states
        don't count."""
        c = one_country(pacific=4, atlantic=5)
        waiting = m.State(0, "pacific", 0, levels=2, lic={**dict.fromkeys(m.BASINS, 0), "pacific": 1})
        longhaul = m.State(1, "pacific", 0, levels=2, lic={**dict.fromkeys(m.BASINS, 0), "pacific": 1, "atlantic": 1})
        elsewhere = m.State(2, "atlantic", 0, levels=3)
        world = m.World({0: c}, {0: waiting, 1: longhaul, 2: elsewhere})
        self.assertEqual(m.local_room(world, 0, "pacific"), 4 - 1 - 1)
        self.assertEqual(m.local_room(world, 0, "atlantic"), 5 - 3)
        self.assertEqual(m.room(world, 0), 9 - 1 - 3)      # the national room is as before

    def test_the_gate_in_both_settings(self):
        """No Pacific claim left, Atlantic claims to spare: off, a Pacific
        level is queued and takes an Atlantic licence; on, it can't be queued,
        while an Atlantic state still can."""
        for on in (False, True):
            with self.subTest(local_only=on):
                world = m.World({0: one_country(on, atlantic=5)},
                                {0: m.State(0, "pacific", 0), 1: m.State(1, "atlantic", 0)})
                self.assertEqual(m.can_build(world, 0, world.states[0]), not on)
                self.assertTrue(m.can_build(world, 0, world.states[1]))
        world = m.World({0: one_country(False, atlantic=5)}, {0: m.State(0, "pacific", 0, levels=1, queued=1)})
        m.record_country(world, 0)
        self.assertEqual(world.states[0].lic["atlantic"], 1)

    def test_several_levels_in_one_month_cannot_overshoot(self):
        """Each level queued comes off the basin's room before it is recorded,
        so a month's queue stops at the claims, and every level is local."""
        c = one_country(True, pacific=2, atlantic=10)
        states = {i: m.State(i, "pacific", 0) for i in range(3)}
        world = m.World({0: c}, states)
        queued = 0
        for _ in range(10):
            s = next((s for s in states.values() if m.can_build(world, 0, s) and s.queued == 0), None)
            if s is None:
                break
            s.levels += 1
            s.queued += 1
            queued += 1
        self.assertEqual(queued, 2)
        m.record_country(world, 0)
        self.assertEqual(sum(s.distant() for s in states.values()), 0)
        self.assertEqual(m.local_room(world, 0, "pacific"), 0)

    def _branch(self, plain):
        """One Pacific claim, Atlantic claims to spare, the setting on; a
        builder queues in the Pacific state whenever the gate is open, its
        first level never finishing, for a year."""
        world = m.World({0: one_country(True, pacific=1, atlantic=20)}, {0: m.State(0, "pacific", 0)},
                        local_room_plain=plain)
        s = world.states[0]
        for _ in range(12):
            if m.can_build(world, 0, s):
                s.levels += 1
                s.queued += 1
            m.record_country(world, 0)
        return world

    def test_the_under_construction_branch_lets_one_level_in_and_shuts(self):
        world = self._branch(plain=False)
        s = world.states[0]
        self.assertEqual(s.levels, 2)                       # the local one, and the one the branch let in
        self.assertEqual(s.distant(), 1)
        self.assertEqual(m.local_room(world, 0, "pacific"), -1)
        self.assertFalse(m.can_build(world, 0, s))          # both branches shut
        self.assertGreater(m.room(world, 0), 0)             # though the country has claims elsewhere
        world.countries[0].unbuilt["pacific"] += 1          # a local claim frees up (a sharing)
        m.record_country(world, 0)
        self.assertEqual(s.distant(), 0)                    # the swap takes it
        self.assertEqual(m.local_room(world, 0, "pacific"), 0)

    def test_a_plain_count_lets_one_in_every_month(self):
        """The control: without the distant term the branch reopens each month."""
        world = self._branch(plain=True)
        self.assertEqual(world.states[0].distant(), 11)

    def test_the_recording_is_the_same_in_both_settings(self):
        """The setting stops new levels only: the recording gives the same
        licences with it on or off."""
        rng = random.Random(77)
        world = m.random_world(rng)
        for _ in range(36):
            m.step_month(world, rng, conquest=0, annex=0, split=0)
        for s in world.states.values():               # levels queued since the recording
            if s.coastal and rng.random() < 0.3:
                s.levels += 1
                s.queued += 1
        on = copy.deepcopy(world)
        for c in on.countries.values():
            c.local_only = True
        for w in (world, on):
            for cid in sorted(w.countries):
                if w.alive(cid):
                    m.record_country(w, cid)
        self.assertEqual({k: s.lic for k, s in world.states.items()}, {k: s.lic for k, s in on.states.items()})
        self.assertEqual({k: c.unbuilt for k, c in world.countries.items()},
                         {k: c.unbuilt for k, c in on.countries.items()})

    def _run(self, local_only, seed):
        rng = random.Random(seed)
        world = m.random_world(rng)
        for c in world.countries.values():
            c.overlord = None                     # no pacts: Administer moves claims between recordings
            c.local_only = local_only
        world.administer = set()
        worst = held = 0
        for _ in range(YEARS):
            for _ in range(12):
                m.step_month(world, rng, conquest=0, annex=0, split=0, demolish=0.01, complete=0.15)
                for cid, c in world.countries.items():
                    for b in m.BASINS:
                        d = sum(s.distant() for s in world.owned(cid) if s.basin == b)
                        worst = max(worst, d)
                        held += d
            m.yearly_pass(world)
        return worst, held

    def test_random_worlds_hold_at_most_one_distant_licence_a_basin(self):
        """With the setting on from the start, and the builders using both
        branches as the AI and private investment do, a country's states in a
        basin never hold more than one distant licence: the one the
        under-construction branch let in, which the next freed claim
        replaces. Without the setting they hold many."""
        on = off = 0
        for i in range(WORLDS):
            with self.subTest(world=i):
                worst, held = self._run(True, 8300 + i)
                self.assertLessEqual(worst, 1)
                on += held
                off += self._run(False, 8300 + i)[1]
        self.assertLess(on * 5, off)


class LocalOnlyScriptTest(unittest.TestCase):
    """The script against the model."""

    @classmethod
    def setUpClass(cls):
        cls.triggers = strip_comments(read(TRIGGERS))
        cls.values = strip_comments(read(VALUES))
        cls.sguis = strip_comments(read(SGUIS))
        cls.loc = _all_loc()

    def test_the_gate_reads_the_setting_inside_the_rule_after_the_room(self):
        gate = block(self.triggers, "te_seabed_gate")
        rule = gate.index("limit = { te_global_commons_enabled = yes }")
        room = gate.index("text = te_seabed_gate_room_tt")
        local = gate.index("trigger_if = {\n\t\t\tlimit = { te_seabed_local_only_on = yes }\n\t\t\tte_seabed_gate_local = yes")
        self.assertLess(rule, room)
        self.assertLess(room, local)
        # the information lines wait for the setting's room too
        info = gate[gate.index("te_seabed_gate_next_local_tt") - 600:gate.index("te_seabed_gate_next_local_tt")]
        self.assertIn("NOT = { te_seabed_local_only_on = yes }", info)
        self.assertIn("te_seabed_local_open = yes", info)

    def test_the_setting_is_a_variable_the_ai_never_reads(self):
        on = block(self.triggers, "te_seabed_local_only_on")
        self.assertIn("has_variable = te_seabed_local_only", on)
        self.assertIn("is_ai = no", on)
        sgui = block(self.sguis, "te_seabed_local_only_sgui")
        self.assertIn("ai_is_valid = { always = no }", sgui)
        self.assertIn("is_shown = { te_global_commons_enabled = yes }", sgui)
        self.assertRegex(sgui, r"custom_tooltip = \{\s*text = te_seabed_local_only_off_tt\s*remove_variable = te_seabed_local_only")
        self.assertRegex(sgui, r"custom_tooltip = \{\s*text = te_seabed_local_only_on_tt\s*set_variable = te_seabed_local_only")
        # nothing else writes it, and no list or modifier holds it
        for folder in ("scripted_effects", "on_actions", "history"):
            for root, _, files in os.walk(os.path.join(REPO, "common", folder)):
                for f in files:
                    self.assertNotIn("te_seabed_local_only", read(os.path.relpath(os.path.join(root, f), REPO)), f)

    def test_the_recording_never_reads_the_setting(self):
        self.assertNotIn("te_seabed_local_only", read(EFFECTS))
        self.assertNotIn("te_seabed_local_room", read(EFFECTS))

    def test_each_basins_local_room(self):
        for n, b in enumerate(m.BASINS, 1):
            with self.subTest(basin=b):
                room = block(self.values, f"te_seabed_local_room_{b}")
                self.assertIn(f"value = var:te_seabed_unbuilt_{b}", room)
                self.assertRegex(room, rf"every_scope_state = \{{\s*limit = \{{\s*is_coastal = yes\s*var:te_seabed_basin \?= {n}\s*\}}"
                                       r"\s*subtract = te_seabed_state_unrecorded\s*subtract = te_seabed_state_distant_records")
                state = block(self.values, "te_seabed_state_local_room")
                self.assertRegex(state, rf"var:te_seabed_basin = {n} \}}\s*owner = \{{ add = te_seabed_local_room_{b} \}}")
        self.assertIn("value = te_seabed_state_records\n\tsubtract = te_seabed_state_local_records",
                      block(self.values, "te_seabed_state_distant_records"))

    def test_the_local_gate_has_the_national_branches_behind_cheap_tests(self):
        """Model: local_gate_open. room > 0 behind the owner's local claims,
        room >= 0 behind a mine under construction here (review M1)."""
        gate = block(self.triggers, "te_seabed_local_open")
        self.assertIn("has_variable = te_seabed_basin", gate)
        self.assertRegex(gate, r"te_seabed_state_owner_local_unbuilt > 0\s*te_seabed_state_local_room > 0")
        self.assertRegex(gate, r"is_under_construction = yes\s*\}\s*te_seabed_state_local_room >= 0")
        nxt = block(self.triggers, "te_seabed_state_next_local")
        self.assertRegex(nxt, r"limit = \{ te_seabed_local_only_on = yes \}\s*te_seabed_state_local_room > 0")

    def test_the_line_names_the_basin_and_the_setting(self):
        line = block(self.triggers, "te_seabed_gate_local_line")
        local = block(self.triggers, "te_seabed_gate_local")
        self.assertIn("te_seabed_gate_local_line = { KIND = room OK = yes }", local)
        self.assertIn("te_seabed_gate_local_line = { KIND = none OK = no }", local)
        self.assertIn("text = te_seabed_gate_local_unknown_tt\n\t\t\talways = no", local)
        for n, b in enumerate(m.BASINS, 1):
            with self.subTest(basin=b):
                self.assertIn(f"text = te_seabed_gate_local_$KIND$_{b}_tt", line)
                room = self.loc[f"te_seabed_gate_local_room_{b}_tt"]
                none = self.loc[f"te_seabed_gate_local_none_{b}_tt"]
                self.assertIn(f"$te_seabed_basin_{b}$", room)
                self.assertIn(f"ScriptValue('te_seabed_local_room_{b}')", room)
                self.assertIn(f"$te_seabed_basin_{b}$", none)
                for text in (room, none):
                    self.assertIn("$te_seabed_local_only$", text)
                self.assertIn("Seabed tab", none)
                self.assertIn("Untick", none)
        self.assertIn("var:te_seabed_basin = 4", line)
        self.assertIn("te_seabed_gate_local_$KIND$_southern_tt", line[line.index("trigger_else = {"):])

    def test_the_tooltips_say_what_it_does(self):
        for key in ("te_seabed_local_only_on_tt", "te_seabed_local_only_off_tt"):
            with self.subTest(key=key):
                text = self.loc[key]
                for word in ("$building_ocean_mine$", "own ocean basin", "another basin's license", "$te_seabed_long_haul$",
                             "te_seabed_long_haul_penalty_pct", "private investment"):
                    self.assertIn(word, text)
        self.assertIn("keep their licenses", self.loc["te_seabed_local_only_on_tt"])
        self.assertIn("Untick", self.loc["te_seabed_local_only_off_tt"])


class LocalOnlyCheckboxTest(unittest.TestCase):
    """The checkbox in the Seabed tab's overview."""

    @classmethod
    def setUpClass(cls):
        cls.gui = read(GUI)
        cls.types = mod_types()
        cls.panel = cls.types["te_seabed_overview_panel"].body

    def test_it_sits_under_the_room_and_long_haul_boxes(self):
        at = self.panel.index("te_seabed_local_only_sgui")
        self.assertLess(self.panel.index('"te_seabed_ov_longhaul_tt"'), at)
        self.assertLess(self.panel.index('"te_seabed_ov_room_tt"'), at)
        self.assertLess(at, self.panel.index('"te_seabed_ov_policy_tt"'))

    def test_it_is_the_players_own(self):
        """Another country's National Info leaves it out: Execute there would
        set that country's variable. No visible of its own beside the guard's."""
        at = self.panel.index("te_seabed_local_only_sgui")
        spans = guard_spans(self.panel)
        self.assertTrue(in_spans(at, spans))
        start = self.panel.rindex("using = te_own_country_only", 0, at)
        self.assertNotIn("visible =", self.panel[start:at])

    def test_another_countrys_tab_closes_up_the_slot(self):
        """Hidden there, the fixed 480 x 34 slot would leave a blank row unless
        the overview's vertical flow ignores invisible children."""
        slot = self.panel.rindex("widget = {", 0, self.panel.index("te_seabed_local_only_sgui"))
        flow = self.panel.rindex("direction = vertical", 0, slot)
        self.assertIn("ignoreinvisible = yes", self.panel[flow:self.panel.index("flowcontainer = {", flow)])

    def test_it_is_bound_to_its_scripted_gui(self):
        at = self.panel.index("button_checkbox_label = {")
        box = self.panel[at:self.panel.index("flowcontainer = {", at)]
        self.assertIn("datacontext = \"[GetScriptedGui('te_seabed_local_only_sgui')]\"", box)
        self.assertIn('onclick = "[ScriptedGui.Execute( GuiScope.SetRoot( Country.MakeScope ).End )]"', box)
        self.assertIn('tooltip = "[ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( Country.MakeScope ).End )]"', box)
        self.assertIn("checked = \"[GreaterThan_CFixedPoint( Country.MakeScope.ScriptValue('te_seabed_local_only_disp'), "
                      "'(CFixedPoint)0' )]\"", box)
        self.assertIn('text = "te_seabed_local_only"', box)
        values = strip_comments(read(VALUES))
        self.assertRegex(block(values, "te_seabed_local_only_disp"),
                         r"has_variable = te_seabed_local_only \}\s*value = 1")

    def test_the_label_fits(self):
        at = self.panel.index('text = "te_seabed_local_only"')
        width = int(re.search(r"max_width = (\d+)", self.panel[at:at + 200]).group(1))
        self.assertIn("using = te_seabed_fontsize_row", self.panel[at:at + 200])
        slot = int(re.search(r"size = \{ (\d+) 34 \}", self.panel[self.panel.rindex("widget = {", 0, at):at]).group(1))
        self.assertEqual(slot, 480)
        self.assertLessEqual(30 + 5 + width, slot)          # vanilla's 30-unit checkbox, 5 spacing
        label = _all_loc()["te_seabed_local_only"]
        self.assertLessEqual(len(label) * UNITS["row"] * MARGIN, width)


if __name__ == "__main__":
    unittest.main()
