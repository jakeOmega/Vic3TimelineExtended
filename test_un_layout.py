"""The UN's section order and collapse defaults (spec 2026-09-28-un-gui-pass-design.md §1)."""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(REPO, "gui", "journal_entry_widgets")
LAYOUT = os.path.join(W, "un_layout_widget.gui")
UN_GUI = [os.path.join(W, f) for f in ("un_chamber_widget.gui", "un_authority_widget.gui",
                                        "un_layout_widget.gui")]
UN_GUI.append(os.path.join(REPO, "gui", "diplomatic_overview.gui"))

STATUS = ["te_un_sec_assembly", "te_un_sec_why", "te_un_sec_missions", "te_un_sec_mandates",
          "te_un_sec_obligations", "te_un_sec_exposure"]
REFERENCE = ["te_un_sec_auth_history", "te_un_sec_archive", "te_un_sec_standing_help",
             "te_un_sec_auth_help"]
OLD_FLAGS = ["un_chamber_delegations", "un_chamber_standing", "un_chamber_exposure",
             "un_chamber_missions", "un_chamber_obligations", "un_chamber_votes",
             "un_chamber_propose", "un_chamber_mandates", "un_chamber_history", "un_auth_hist_open"]
NOT_SECTIONS = {"un_chamber_veto_armed", "un_chamber_history_details"}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    depth = 0
    for j in range(m.end() - 1, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():j]


class OrderTest(unittest.TestCase):
    def test_status_and_reference_order(self):
        layout = _read(LAYOUT)
        for composer, expected in (("te_un_status_sections", STATUS),
                                   ("te_un_reference_sections", REFERENCE)):
            found = re.findall(r"^\t\t(te_un_sec_\w+) = \{", _type_body(layout, composer), re.M)
            self.assertEqual(found, expected, composer)

    def test_session_subsections_follow_the_session(self):
        body = _type_body(_read(LAYOUT), "te_un_sec_assembly")
        gate = "GetScriptedGui('un_session_open_sgui').IsShown"
        for sec, negated in (("te_un_sec_delegations", False), ("te_un_sec_ballot", False),
                             ("te_un_sec_propose", True)):
            m = re.search(rf"{sec} = \{{\s*visible = \"\[(.*?)\]\"", body, re.S)
            self.assertTrue(m, f"{sec} has no visible gate")
            self.assertIn(gate, m.group(1))
            self.assertEqual(m.group(1).startswith("Not("), negated, sec)


class FlagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = "\n".join(_read(p) for p in UN_GUI)

    def test_section_flags_say_their_default(self):
        flags = {f for f in re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", self.text)
                 if f.startswith(("un_", "te_un_"))} - NOT_SECTIONS
        self.assertTrue(flags)
        for f in flags:
            self.assertRegex(f, r"_(open|closed)$", f"section flag {f} does not say its default")
            negated = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{f}'\)\s*\)", self.text))
            total = len(re.findall(rf"GetVariableSystem\.Exists\('{f}'\)", self.text))
            bare = total - negated
            if f.endswith("_closed"):   # shown unless closed: one bare (show-more), the rest negated
                self.assertEqual(bare, 1, f)
                self.assertGreaterEqual(negated, 2, f)
            else:                        # shown only when opened: one negated (show-more)
                self.assertEqual(negated, 1, f)
                self.assertGreaterEqual(bare, 2, f)

    def test_no_old_flag_survives(self):
        for f in OLD_FLAGS:
            self.assertNotRegex(self.text, rf"'{f}'", f)


class SessionStripTest(unittest.TestCase):
    def test_strip_is_gated_and_the_two_thirds_mark_only_on_supermajority(self):
        body = _type_body(_read(LAYOUT), "te_un_sec_assembly")
        self.assertIn("ScriptValue('un_disp_res_yes_frac')", body)
        self.assertIn("ScriptValue('un_disp_res_not_no_frac')", body)
        self.assertIn("ScriptValue('un_disp_res_months_frac')", body)
        mark = re.search(r"# two-thirds mark.*?visible = \"\[(.*?)\]\"", body, re.S)
        self.assertTrue(mark)
        self.assertIn("un_disp_res_supermajority", mark.group(1))

    def test_every_topic_has_an_icon(self):
        codes = {int(n) for n in re.findall(
            r"ScriptValue\('un_disp_res_topic_code'\), '\(CFixedPoint\)(\d+)'", _read(LAYOUT))}
        self.assertEqual(codes, set(range(18)))

if __name__ == "__main__":
    unittest.main()
