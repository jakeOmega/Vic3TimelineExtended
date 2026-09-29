"""The UN's section order and collapse defaults (spec 2026-09-28-un-gui-pass-design.md §1)."""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(REPO, "gui", "journal_entry_widgets")
LAYOUT = os.path.join(W, "un_layout_widget.gui")
UN_GUI = [os.path.join(W, f) for f in ("un_chamber_widget.gui", "un_authority_widget.gui",
                                        "un_layout_widget.gui")]
UN_GUI.append(os.path.join(REPO, "gui", "diplomatic_overview.gui"))

STATUS = ["te_un_sec_assembly", "te_un_sec_why", "te_un_sec_missions", "te_un_sec_programmes",
          "te_un_sec_mandates", "te_un_sec_obligations", "te_un_sec_exposure"]
REFERENCE = ["te_un_sec_auth_history", "te_un_sec_archive", "te_un_sec_how"]
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

AUTHORITY = os.path.join(W, "un_authority_widget.gui")
PILLARS = ("participation", "commitment", "credibility", "funding", "order", "delivery")


class PillarBarTest(unittest.TestCase):
    def test_each_pillar_is_a_bar_with_a_trend(self):
        body = _type_body(_read(AUTHORITY), "te_un_sec_why")
        for p in PILLARS:
            for v in ("pos", "neg", "trend"):
                self.assertIn(f"ScriptValue('un_disp_pillar_{p}_{v}')", body, f"{p} {v}")
            self.assertNotRegex(body, rf'blockoverride "pillar_value" \{{ text = "je_un_auth_tbl_{p}_value" \}}',
                                f"{p} still has its old table row")

class TabStatusTest(unittest.TestCase):
    def test_the_tab_keeps_the_entrys_status_text_open(self):
        """Open by default (owner, 2026-09-28): the flag is the CLOSED flag."""
        tab = _read(os.path.join(REPO, "gui", "diplomatic_overview.gui"))
        m = re.search(r"flowcontainer = \{\s*visible = \"\[Not\(GetVariableSystem\.Exists\('te_un_tab_status_closed'\)\)\]\"(.*?)\}", tab, re.S)
        self.assertTrue(m, "no Status section gated on te_un_tab_status_closed")
        self.assertIn("te_je_status_desc", m.group(1))

CHAMBER = os.path.join(W, "un_chamber_widget.gui")
# Explanations that live in "How the UN works", and the live sections they left.
HOW_KEYS = ["je_un_auth_tbl_explain", "je_un_chamber_missions_intro", "je_un_chamber_missions_help",
            "je_un_chamber_deleg_intro", "je_un_chamber_obligations_help", "je_un_chamber_exposure_help"]
LIVE_SECTIONS = [(AUTHORITY, "te_un_sec_why"), (CHAMBER, "te_un_sec_missions"),
                 (CHAMBER, "te_un_sec_delegations"), (CHAMBER, "te_un_sec_obligations"),
                 (CHAMBER, "te_un_sec_exposure")]


class HowItWorksTest(unittest.TestCase):
    def test_explanations_live_in_how_the_un_works(self):
        how = _type_body(_read(LAYOUT), "te_un_sec_how")
        for key in HOW_KEYS:
            self.assertIn(f'"{key}"', how, key)
        for sub in ("te_un_help_authority", "te_un_help_standing"):
            self.assertIn(f"{sub} = {{", how, sub)
        self.assertIn("GetVariableSystem.Toggle('un_how_open')", how)

    def test_live_sections_carry_no_explanations(self):
        for path, sec in LIVE_SECTIONS:
            body = _type_body(_read(path), sec)
            for key in HOW_KEYS:
                self.assertNotIn(f'"{key}"', body, f"{sec} still explains ({key})")

    def test_recent_entries_and_ended_missions_start_collapsed(self):
        why = _type_body(_read(AUTHORITY), "te_un_sec_why")
        self.assertIn("GetVariableSystem.Toggle('un_auth_log_open')", why)
        missions = _type_body(_read(CHAMBER), "te_un_sec_missions")
        self.assertIn("GetVariableSystem.Toggle('un_chamber_missions_ended_open')", missions)

    def test_the_probe_is_gone(self):
        self.assertNotIn("GetGlobalList", _read(os.path.join(REPO, "gui", "diplomatic_overview.gui")))


class PowersTest(unittest.TestCase):
    def test_champions_underminers_outsiders_are_groups(self):
        why = _type_body(_read(AUTHORITY), "te_un_sec_why")
        for group in ("champions", "underminers", "outsiders"):
            self.assertIn(f"GetScriptedGui('un_authority_{group}_sgui').IsShown", why, group)
            self.assertIn(f"GetScriptedGui('un_authority_{group}_sgui').ExecuteTooltip", why, group)


class ProposeRowTest(unittest.TestCase):
    def test_the_propose_button_sits_beside_its_topic(self):
        self.assertRegex(_read(CHAMBER), r"type un_chamber_propose_row = flowcontainer \{\s*direction = horizontal")

PROGRAMME_TALLIES = ("un_peacekeeping_count", "un_development_count", "un_human_rights_champion_count",
                     "un_human_rights_signatories", "un_arms_control_count",
                     "un_nonproliferation_signatories", "un_climate_signatories",
                     "un_heritage_participants", "un_sanctions_target_count")


class ProgrammesTest(unittest.TestCase):
    def test_programmes_are_a_collapsed_table(self):
        body = _type_body(_read(CHAMBER), "te_un_sec_programmes")
        self.assertIn("GetVariableSystem.Toggle('un_chamber_programmes_open')", body)
        for sv in PROGRAMME_TALLIES:
            self.assertIn(f"ScriptValue('{sv}')", body, sv)

if __name__ == "__main__":
    unittest.main()
