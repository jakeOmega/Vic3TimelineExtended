"""Demographics phase 3's panel (docs/superpowers/archive/specs/2026-10-11-demographics-late-game-design.md §6): the late rows,
the Longevity sections, the pyramid's Calendar / Biological toggle and their loc, static checks only (the engine draws
them; docs/testing/demographics-playtest.md has the in-game list)."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from test_demographics_registry import _gui_type, _text  # noqa: E402

GUI = ROOT / "gui" / "te_demographics_widgets.gui"
LAYOUT = ROOT / "gui" / "te_demographics_layout.gui"   # the two composers (issue #1029)
LOC = ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml"
SGUIS = ROOT / "common" / "scripted_guis" / "te_demog_lx_sguis.txt"


def _loc():
    return dict(re.findall(r'(?m)^ ([\w.]+):0 "(.*)"$', _text(LOC)))


class TestLatePanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _text(GUI)
        cls.layout = _text(LAYOUT)
        cls.loc = _loc()
        cls.sguis = set(re.findall(r"(?m)^(te_demog_lx_\w+_sgui) = \{", _text(SGUIS)))

    def test_the_sections_sit_after_work_and_retirement(self):
        tab = _gui_type(self.layout, "te_demog_tab_sections")
        self.assertLess(tab.index("te_demog_sec_work = {}"), tab.index("te_demog_sec_longevity = {}"))
        content = _gui_type(self.layout, "te_state_demog_content")
        self.assertLess(content.index("te_state_demog_work = {}"), content.index("te_state_demog_longevity = {}"))

    def test_the_sections_show_only_with_the_late_figures_and_start_open(self):
        for name, gate, flag in (("te_demog_sec_longevity", "te_demog_lx_ready_sgui", "te_demog_lx_closed"),
                                 ("te_state_demog_longevity", "te_demog_lx_state_ready_sgui", "te_demog_st_lx_closed")):
            body = _gui_type(self.gui, name)
            self.assertIn(f"GetScriptedGui('{gate}')", body.split("te_demog_section_header")[0], name)
            self.assertIn(f"GetVariableSystem.Toggle('{flag}')", body, name)
        self.assertNotIn("GetPlayer", _gui_type(self.gui, "te_state_demog_longevity"), "the state's section reads the state")

    def test_the_late_rows_are_gated(self):
        """Living to 100 and Biological Age sit first in the Longevity sections (issue #1029 moved them from the
        overviews), which show only with the late figures; the overviews no longer read them."""
        for name, section, gate in (("te_demog_overview", "te_demog_sec_longevity", "te_demog_lx_ready_sgui"),
                                    ("te_state_demog_overview", "te_state_demog_longevity", "te_demog_lx_state_ready_sgui")):
            body = _gui_type(self.gui, section)
            self.assertIn(f"GetScriptedGui('{gate}')", body.split("te_demog_section_header")[0], section)
            for key in ("_lx_l100_value", "_lx_bio_value"):
                self.assertLess(body.index(key), body.index("_lx_care_value"), (section, key))
                self.assertNotIn(key, _gui_type(self.gui, name), name)

    def test_every_gate_exists_and_every_key_is_localized(self):
        types = ("te_demog_overview", "te_state_demog_overview", "te_demog_sec_longevity", "te_state_demog_longevity",
                 "te_demog_sec_pyramid", "te_state_demog_pyramid")
        for name in types:
            body = _gui_type(self.gui, name)
            for sgui in re.findall(r"GetScriptedGui\('(te_demog_lx_\w+)'\)", body):
                self.assertIn(sgui, self.sguis, (name, sgui))
            for key in re.findall(r"""(?:text|tooltip) = "(te_demog_\w+)\"""", body):
                self.assertIn(key, self.loc, (name, key))
            for key in re.findall(r"'(te_demog_[a-z0-9_]+)'", body):
                if not key.endswith("_sgui") and not key.endswith(("_closed", "_open")) and not key.startswith(
                        ("te_demog_trend_", "te_demog_k_")):
                    self.assertIn(key, self.loc, (name, key))

    def test_the_new_loc_keeps_the_house_style(self):
        new = {k: v for k, v in self.loc.items() if re.match(r"te_demog_(lx_|ov_lx_|st_lx_|pyr_bio|st_pyr_bio|pyr_show|"
                                                              r"pyr_toggle|pyr_legend_bio|ov_tfr_mab|st_tfr_mab|"
                                                              r"ov_tfr_b50|st_tfr_b50|tfr_mab|.*_tt_late|.*_tt_100)", k)}
        self.assertGreater(len(new), 40)
        for key, value in new.items():
            self.assertFalse(value.startswith("\\n"), key)
            self.assertFalse(value.endswith("\\n"), key)
            self.assertNotIn("[b]", value, key)
            self.assertNotIn("…", value, key)
        for key, sguis in (("te_demog_ov_old_age_value", "te_demog_lx_old_none_sgui"),
                           ("te_demog_st_old_age_value", "te_demog_lx_state_old_none_sgui")):
            self.assertIn(sguis, self.loc[key], key)

    def test_the_pyramid_toggle(self):
        """The biological rows read the biological bands, show only where they exist, and carry no outline."""
        for name, flag, gate, prefix in (("te_demog_sec_pyramid", "te_demog_pyr_bio_open", "te_demog_lx_bio_pyr_sgui",
                                          "te_dg_cbb"),
                                         ("te_state_demog_pyramid", "te_demog_st_pyr_bio_open",
                                          "te_demog_lx_state_bio_pyr_sgui", "te_dg_bb")):
            body = _gui_type(self.gui, name)
            self.assertIn(f"GetVariableSystem.Toggle('{flag}')", body)
            bio = body[body.index(f"visible = \"[And( GetVariableSystem.Exists('{flag}'), GetScriptedGui('{gate}')"):]
            for b in range(18):
                for s in "fm":
                    self.assertIn(f"Var('{prefix}{s}{b}')", bio, (name, b, s))
            self.assertNotIn("te_dg_pj", bio.split("te_demog_pyr_legend_bio")[0], "no outline in biological mode")


if __name__ == "__main__":
    unittest.main()
