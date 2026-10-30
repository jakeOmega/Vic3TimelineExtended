# -*- coding: utf-8 -*-
"""Unemployment as a share of the workforce: every mod reader goes through one conversion.

The engine's state_unemployment_rate is the idle workforce over all the state's people, dependents included, not a
share of the workforce: in Mecklenburg-Strelitz in January 1836 it read 0.048 where the pops held 0.195 of their
workforce with no workplace (the Demographics self-check unemployment_rate_read, 2026-10-17). A threshold written as a
share of the workforce (> 0.1) bit at about four times that. te_state_unemployment_share divides the figure by the
workforce's share of the people, which a yearly walk of each state's pops stores (te_unemp_wf_share). The Demographics
census stores it at its walk (te_dg_unemp, owner 2026-10-17), and its youth bulge, event wave, pension AI and panel read
that. These tests keep a new reader from thresholding the engine's figure directly, and the walk, its wiring and its
self-check whole. The engine reports none of it.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

VALUES = os.path.join(REPO, "common", "script_values", "te_unemployment_values.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_unemployment_effects.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "te_unemployment_on_actions.txt")
PLAYTEST = os.path.join(REPO, "docs", "testing", "ai-economy-playtest.md")
DEMOG_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_demog_effects.txt")
DEMOG_VALUES = [os.path.join(REPO, "common", "script_values", name) for name in
                ("te_demog_consequence_values.txt", "te_demog_wave_values.txt", "te_demog_work_values.txt")]

# file -> the script values allowed to read the engine's figure there: the conversion and its effect wrapper, and the
# Demographics self-check's wrapper (the census reads its own count, test_demographics_registry).
ENGINE_READERS = {
    "common/script_values/te_unemployment_values.txt": ["te_state_unemployment_share", "te_unemp_engine_read"],
    "common/script_values/te_debug_demog_values.txt": ["te_debug_demog_unemp_engine_read"],
}

# (file, the block that reads, the comparison it makes): the readers the conversion replaced, thresholds unchanged.
READERS = [
    ("common/buildings/resettlement.txt", "building_resettlement_colony", "te_state_unemployment_share > 0.1"),
    ("common/decrees/extra_decrees.txt", "decree_greenest_grass_campaign", "te_state_unemployment_share >= 0.1"),
    ("common/decrees/extra_decrees.txt", "decree_resettlement_recruitment_drive", "te_state_unemployment_share > 0.1"),
    ("common/script_values/extra_script_values.txt", "migration_attraction_script_value",
     "te_state_unemployment_share > 0.1"),
]


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _body(text, name, start=0):
    """The body of the first ``name = { ... }`` block at or after ``start``."""
    m = re.compile(r"(?<![\w.:])" + re.escape(name) + r"\s*=\s*\{").search(text, start)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


def _top_blocks(text):
    """{name: body} for each top-level ``name = { ... }`` block."""
    out, depth, i = {}, 0, 0
    pattern = re.compile(r"([\w:.]+)\s*=\s*\{")
    while i < len(text):
        if depth == 0:
            m = pattern.match(text, i)
            if m:
                out[m.group(1)] = _body(text, m.group(1), i)
                i = m.start() + len(m.group(0)) + len(out[m.group(1)]) + 1
                continue
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return out


def _squash(text):
    return re.sub(r"\s+", " ", text).strip()


class EveryReaderGoesThroughTheConversion(unittest.TestCase):
    def test_no_reader_thresholds_the_engines_figure(self):
        found = {}
        for folder in ("common", "events", "gui"):
            for root, _dirs, files in os.walk(os.path.join(REPO, folder)):
                for name in files:
                    if not name.endswith((".txt", ".gui")):
                        continue
                    path = os.path.join(root, name)
                    text = _read(path)
                    if "state_unemployment_rate" not in text:
                        continue
                    rel = os.path.relpath(path, REPO).replace(os.sep, "/")
                    found[rel] = sorted(n for n, body in _top_blocks(text).items()
                                        if "state_unemployment_rate" in body)
        self.assertEqual(found, {k: sorted(v) for k, v in ENGINE_READERS.items()})

    def test_each_reader_reads_the_share_at_its_threshold(self):
        for rel, block, comparison in READERS:
            with self.subTest(block=block):
                body = _squash(_body(_read(os.path.join(REPO, rel)), block))
                self.assertIn(comparison, body)

    def test_no_gui_or_loc_reads_the_conversion(self):
        """The conversion reads the trigger, which a scripted GUI reads as none (scripting_best_practices.md, The op
        slots). A GUI or loc line needs a variable stored from an effect instead."""
        hits = []
        for folder in ("gui", os.path.join("common", "scripted_guis"), "localization"):
            for root, _dirs, files in os.walk(os.path.join(REPO, folder)):
                for name in files:
                    path = os.path.join(root, name)
                    with open(path, encoding="utf-8-sig", errors="replace") as f:
                        text = f.read()
                    # a loc line reads it through ScriptValue('...'); a GUI or scripted GUI by name
                    read = ("ScriptValue('te_state_unemployment_share')" in text if folder == "localization"
                            else re.search(r"\bte_state_unemployment_share\b", re.sub(r"#[^\n]*", "", text)))
                    if read:
                        hits.append(os.path.relpath(path, REPO))
        self.assertEqual(hits, [])


class TheCensusStoresTheConversion(unittest.TestCase):
    """One source for every reader (owner, 2026-10-17). A scripted GUI reads the trigger as none, so the census stores
    the conversion from an effect and its effects and panel read the variable."""

    def test_the_census_figure_is_the_conversion(self):
        store = _squash(_body(_read(DEMOG_EFFECTS), "te_demog_work_walk_store"))
        self.assertIn("set_variable = { name = te_dg_unemp value = te_state_unemployment_share }", store)
        # a state the conversion's walk hasn't reached takes the census walk's workforce share, not the fallback
        self.assertLess(store.index("set_variable = { name = te_unemp_wf_share value = var:te_dg_wf_engine }"),
                        store.index("name = te_dg_unemp value"))

    def test_its_readers_read_the_stored_figure(self):
        values = {}
        for path in DEMOG_VALUES:
            values.update(_top_blocks(_read(path)))
        self.assertIn("value = var:te_dg_unemp", _squash(values["te_demog_unemployment"]))
        self.assertEqual(_squash(values["te_demog_unemployment_census"]), "value = te_demog_unemployment")
        for name in ("te_demog_wave_unemployment", "te_demog_country_unemployment"):
            with self.subTest(name=name):
                self.assertIn("value = te_demog_unemployment", _squash(values[name]))
                self.assertNotIn("te_state_unemployment_share", values[name])
        # the youth bulge reads it through its unemployment factor (the 2026-10-22 effects design), the panel's own
        self.assertIn("multiply = te_demog_youth_unemployment_part", _squash(values["te_demog_youth_bulge_now"]))
        self.assertEqual(_squash(values["te_demog_youth_unemployment_reach"]).split(" divide")[0],
                         "value = te_demog_unemployment_census")
        for name in ("te_demog_youth_bulge_now", "te_demog_youth_unemployment_part", "te_demog_youth_unemployment_reach"):
            self.assertNotIn("te_state_unemployment_share", values[name])


class TheConversion(unittest.TestCase):
    def setUp(self):
        self.values = _top_blocks(_read(VALUES))

    def test_it_divides_the_live_figure_by_the_workforce_share(self):
        self.assertEqual(_squash(self.values["te_state_unemployment_share"]),
                         "value = state_unemployment_rate divide = te_state_workforce_share max = 1 min = 0")

    def test_the_share_is_the_walks_with_a_floored_fallback(self):
        body = _squash(self.values["te_state_workforce_share"])
        self.assertTrue(body.startswith("value = te_unemp_k_wf_share_fallback"), body)
        self.assertIn("if = { limit = { has_variable = te_unemp_wf_share } value = var:te_unemp_wf_share }", body)
        self.assertTrue(body.endswith("min = 0.05"), body)
        self.assertEqual(_squash(self.values["te_unemp_k_wf_share_fallback"]), "value = 0.25")

    def test_the_1836_reading_converts_to_the_pops_share(self):
        """Mecklenburg-Strelitz, January 1836: the engine's 0.048 over the workforce's share of the people (about
        0.246 then) is the 0.195 the pops held."""
        self.assertAlmostEqual(0.048 / 0.246, 0.195, places=2)


class TheWalk(unittest.TestCase):
    def setUp(self):
        self.effects = _top_blocks(_read(EFFECTS))

    def test_it_counts_the_workforce_with_no_workplace(self):
        walk = _squash(_body(self.effects["te_unemp_share_refresh"], "every_scope_pop"))
        self.assertEqual(walk, "te_unemp_count_pop = yes")              # one rule, shared with the cost self-check
        count = _squash(self.effects["te_unemp_count_pop"])
        self.assertIn("change_local_variable = { name = te_unemp_w_pop add = total_size }", count)
        self.assertIn("change_local_variable = { name = te_unemp_w_wf add = workforce }", count)
        self.assertIn("if = { limit = { NOT = { exists = workplace } } "
                      "change_local_variable = { name = te_unemp_w_idle add = workforce } }", count)

    def test_it_counts_slack_as_the_dataset_does(self):
        # Construction Cost Scaling's slack: every peasant's workforce, and every other pop's with no workplace
        # (econ_save_series.pops_by_state), so a peasant with no workplace isn't counted twice.
        count = _squash(self.effects["te_unemp_count_pop"])
        self.assertIn("if = { limit = { is_pop_type = peasants } "
                      "change_local_variable = { name = te_unemp_w_slack add = workforce } "
                      "change_local_variable = { name = te_unemp_w_peasant add = workforce } } "
                      "else_if = { limit = { NOT = { exists = workplace } } "
                      "change_local_variable = { name = te_unemp_w_slack add = workforce } }", count)
        body = _squash(self.effects["te_unemp_share_refresh"])
        for name, local in (("te_unemp_wf_count", "te_unemp_w_wf"), ("te_unemp_slack_count", "te_unemp_w_slack"),
                            ("te_unemp_peasant_count", "te_unemp_w_peasant")):
            self.assertIn("set_local_variable = { name = " + local + " value = 0 }", body)
            self.assertIn("set_variable = { name = " + name + " value = local_var:" + local + " }", body)

    def test_it_stores_the_share_and_its_own_count(self):
        body = _squash(self.effects["te_unemp_share_refresh"])
        self.assertIn("limit = { local_var:te_unemp_w_pop > 0 }", body)
        self.assertIn("set_variable = { name = te_unemp_wf_share value = { value = local_var:te_unemp_w_wf "
                      "divide = local_var:te_unemp_w_pop } }", body)
        self.assertIn("set_variable = { name = te_unemp_share_exact value = { value = local_var:te_unemp_w_idle "
                      "divide = { value = local_var:te_unemp_w_wf min = 1 } } }", body)

    def test_the_yearly_pulse_walks_and_checks_and_the_monthly_fills_a_gap(self):
        on_actions = _read(ON_ACTIONS)
        self.assertIn("te_unemp_share_yearly_on_action", _body(on_actions, "on_yearly_pulse_state"))
        self.assertIn("te_unemp_share_monthly_on_action", _body(on_actions, "on_monthly_pulse_state"))
        self.assertIn("te_unemp_share_yearly = yes", _body(on_actions, "te_unemp_share_yearly_on_action"))
        monthly = _squash(_body(on_actions, "te_unemp_share_monthly_on_action"))
        # a state with no walk yet, or none since the walk stored Construction Cost Scaling's counts
        self.assertIn("if = { limit = { OR = { NOT = { has_variable = te_unemp_wf_share } "
                      "NOT = { has_variable = te_unemp_slack_count } } } te_unemp_share_refresh = yes }", monthly)
        self.assertNotIn("selfcheck", monthly)
        yearly = _squash(self.effects["te_unemp_share_yearly"])
        # the share readers held is taken before the walk replaces it, and the check reads the walk's locals after
        self.assertLess(yearly.index("te_unemp_c_prev"), yearly.index("te_unemp_share_refresh = yes"))
        self.assertLess(yearly.index("te_unemp_share_refresh = yes"), yearly.index("te_unemp_share_selfcheck = yes"))


class TheSelfCheck(unittest.TestCase):
    def setUp(self):
        self.check = _read(EFFECTS)
        self.body = _squash(_top_blocks(self.check)["te_unemp_share_selfcheck"])

    def test_once_a_game_and_only_where_it_can_tell(self):
        self.assertIn("NOT = { has_global_variable = te_unemp_share_check_done }", self.body)
        self.assertIn("local_var:te_unemp_w_wf >= 10000", self.body)
        self.assertIn("limit = { local_var:te_unemp_c_exact >= 0.02 }", self.body)
        # the flag is set before the line, and the conversion is the one readers use, read after the walk's store
        self.assertLess(self.body.index("set_global_variable = { name = te_unemp_share_check_done"),
                        self.body.index("debug_log"))
        self.assertIn("set_variable = { name = te_unemp_chk_conv value = te_state_unemployment_share }", self.body)
        self.assertIn("var:te_unemp_chk_ratio >= 0.75 var:te_unemp_chk_ratio <= 1.33", self.body)

    def test_both_lines_and_the_playtest_row(self):
        with open(EFFECTS, encoding="utf-8-sig") as f:
            raw = f.read()
        self.assertIn('debug_log = "TE_SELF_CHECK OK unemployment_share_read ', raw)
        self.assertIn('debug_log = "TE_SELF_CHECK BROKEN unemployment_share_read ', raw)
        with open(PLAYTEST, encoding="utf-8") as f:
            self.assertIn("`TE_SELF_CHECK … unemployment_share_read`", f.read())

    def test_every_check_variable_is_removed(self):
        written = set(re.findall(r"set_variable = \{ name = (te_unemp_chk_\w+)", self.body))
        removed = set(re.findall(r"remove_variable = (te_unemp_chk_\w+)", self.body))
        self.assertTrue(written)
        self.assertEqual(written, removed)


if __name__ == "__main__":
    unittest.main()
