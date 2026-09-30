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
HOW_KEYS = ["je_un_chamber_missions_intro", "je_un_chamber_missions_help",
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

CONCEPTS = os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")
DISPLAY_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_authority_display_effects.txt")


def _loc(key):
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        m = re.search(rf'^ {key}:\d* "(.*)"\s*$', _read(path), re.M)
        if m:
            return m.group(1)
    raise AssertionError(f"no loc {key}")


class AuthorityTextTest(unittest.TestCase):
    """Why authority is moving, shortened (owner, 2026-09-28)."""

    def test_commitment_is_one_word(self):
        self.assertEqual(_loc("je_un_auth_tbl_commitment_label"), "Commitment")

    def test_weight_is_a_concept_with_a_breakdown(self):
        why = _type_body(_read(AUTHORITY), "te_un_sec_why")
        self.assertNotIn('"je_un_auth_tbl_weight"', why)
        self.assertIn('"je_un_auth_weight_label"', why)
        self.assertIn('tooltip = "je_un_auth_weight_tt"', why)
        self.assertIn("concept_un_weight", _loc("je_un_auth_weight_label"))

    def test_power_headings_are_centred(self):
        why = _type_body(_read(AUTHORITY), "te_un_sec_why")
        for head in ("je_un_auth_powers_champions", "je_un_auth_powers_underminers",
                     "je_un_auth_powers_outsiders"):
            m = re.search(rf'align = hcenter\|nobaseline\s*text = "{head}"', why)
            self.assertTrue(m, head)

    def test_tier_and_cap_are_concepts(self):
        concepts = _read(CONCEPTS)
        for c in ("concept_un_tier_moribund", "concept_un_tier_contested", "concept_un_tier_established",
                  "concept_un_tier_strong", "concept_un_tier_supranational", "concept_un_authority_cap",
                  "concept_un_weight"):
            self.assertRegex(concepts, rf"(?m)^{c} = \{{\}}", c)
        for tier in ("moribund", "contested", "established", "strong", "supranational"):
            self.assertIn(f"concept_un_tier_{tier}", _loc(f"je_un_auth_tier_{tier}"))
        for level in ("0", "1"):
            self.assertIn("concept_un_authority_cap", _loc(f"je_un_auth_charter_{level}"))

    def test_no_cap_line_once_both_reforms_pass(self):
        effects = _read(DISPLAY_EFFECTS)
        start = effects.index("un_authority_ladder_block = {")
        self.assertNotIn("je_un_auth_charter_2", effects[start:effects.index("\n}\n", start)])


CHAMBER_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_chamber_display_effects.txt")
CHAMBER_SGUIS = os.path.join(REPO, "common", "scripted_guis", "un_chamber_sguis.txt")
NAMED_TARGETS = ("condemn", "sanctions", "expulsion", "mandate", "refugee")
UNNAMED_CASES = ("peacekeepers", "aid", "decolonization")
CONVENTIONS = ("human_rights", "icc", "npt", "climate", "pandemic", "refugee", "heritage",
               "decolonization", "space", "law_of_sea", "physical_protection")


def _block(text, name):
    start = text.index(f"\n{name} = {{") + 1
    return text[start:text.index("\n}\n", start) + 2]


def _loc_or_none(key):
    try:
        return _loc(key)
    except AssertionError:
        return None


def _tooltip_key(value):
    m = re.search(r"#tooltippable;tooltip:(\w+) ", value)
    return m and m.group(1)


class ProposeTextTest(unittest.TestCase):
    """Table a Resolution, shortened (owner, 2026-09-28): the type, the passage
    rule and the target on a line each; the explanations on hover."""

    @classmethod
    def setUpClass(cls):
        cls.effects = _read(CHAMBER_EFFECTS)
        cls.rows = "\n".join(_block(cls.effects, n) for n in
                               re.findall(r"(?m)^(un_chamber_propose_\w+) = \{", cls.effects))

    def assertScopeFreeTooltip(self, value, where):
        key = _tooltip_key(value)
        self.assertTrue(key, f"{where} is not hoverable: {value}")
        body = _loc(key)
        for token in ("THIS.", "SCOPE.", "ROOT", "#Y"):
            self.assertNotIn(token, body, f"{key}: a static tooltip has no scope")
        return body

    def test_passage_rules_are_concepts(self):
        concepts = _read(CONCEPTS)
        for c in ("concept_un_passage_majority", "concept_un_passage_two_thirds"):
            self.assertRegex(concepts, rf"(?m)^{c} = \{{\}}", c)
            self.assertTrue(_loc(c) and _loc(f"{c}_desc"), c)
        self.assertEqual(_loc("je_un_chamber_rule_majority"),
                         "#bold Passage Rule:#! [concept_un_passage_majority]")
        two_thirds = _loc("je_un_chamber_rule_supermajority")
        self.assertTrue(two_thirds.startswith("#bold Passage Rule:#! [concept_un_passage_two_thirds]"))
        self.assertIn("ScriptValue('un_vote_eligible_member_count')", two_thirds)

    def test_type_lines_are_brief(self):
        self.assertEqual(_loc("je_un_chamber_binding_not_vetoed"),
                         "[concept_un_resolution_binding] — [Concept('concept_un_veto','Vetoable')]")
        self.assertEqual(_loc("je_un_chamber_recommendatory"), "[concept_un_resolution_recommendatory]")
        self.assertNotIn("je_un_chamber_binding_flat_block", self.effects)
        self.assertIsNone(_loc_or_none("je_un_chamber_binding_flat_block"))

    def test_a_named_target_reads_target_x_or_none(self):
        for t in NAMED_TARGETS:
            with self.subTest(topic=t):
                self.assertTrue(_loc(f"je_un_chamber_propose_target_{t}").startswith("#bold Target:#! "))
                none = _loc(f"je_un_chamber_propose_no_case_{t}")
                self.assertTrue(none.startswith("#bold Target:#! #tooltippable;tooltip:"), none)
                self.assertTrue(none.endswith(" None#!"), none)
                self.assertScopeFreeTooltip(none, t)

    def test_a_topic_without_a_target_says_no_case(self):
        for t in UNNAMED_CASES:
            with self.subTest(topic=t):
                line = _loc(f"je_un_chamber_propose_no_case_{t}")
                self.assertIn("No Case", line)
                self.assertScopeFreeTooltip(line, t)
        self.assertIn("Both reforms", _loc("je_un_chamber_propose_no_case_reform"))

    def test_the_button_carries_the_gate_the_row_does_not(self):
        for key in ("je_un_chamber_propose_ready", "je_un_chamber_propose_blocked_gates",
                    "je_un_chamber_propose_reform_clock"):
            self.assertNotIn(key, self.effects, key)
            self.assertIsNone(_loc_or_none(key), key)
        self.assertNotIn("POSSIBLE", self.rows)
        self.assertIn("je_un_auth_reform_clock", _block(self.effects, "un_chamber_propose_reform_row"))

    def test_a_held_floor_is_said_once_above_the_rows(self):
        self.assertNotIn("je_un_chamber_propose_blocked_", self.rows)
        intro = _block(_read(CHAMBER_SGUIS), "un_chamber_propose_intro_sgui")
        for key in ("je_un_chamber_propose_blocked_reserved", "je_un_chamber_propose_blocked_in_session"):
            self.assertIn(key, intro)

    def test_in_force_and_cooldown_are_one_hoverable_word(self):
        for key, word in (("je_un_chamber_topic_in_force", "In Force"),
                          ("je_un_chamber_propose_topic_cooldown", "On Cooldown")):
            with self.subTest(key=key):
                line = _loc(key)
                self.assertIn(word, line)
                self.assertScopeFreeTooltip(line, key)

    def test_conventions_and_reforms_explain_on_hover(self):
        self.assertNotIn("je_un_chamber_raised_", self.rows)
        for t in CONVENTIONS:
            with self.subTest(topic=t):
                body = self.assertScopeFreeTooltip(_loc(f"je_un_chamber_propose_topic_{t}"), t)
                raised = re.findall(r"\$(je_un_chamber_raised_\w+)\$", body)
                self.assertEqual(len(raised), 1, body)
                self.assertFalse(_loc(raised[0]).startswith(" "), raised[0])
        for stage in ("1", "2"):
            self.assertScopeFreeTooltip(_loc(f"je_un_chamber_propose_topic_reform_{stage}"), stage)

    def test_no_row_line_is_indented(self):
        keys = set(re.findall(r"custom_tooltip_no_bullet = (je_\w+)", self.rows))
        keys |= set(re.findall(r"= (je_un_chamber_\w+)", self.rows))
        self.assertTrue(keys)
        for key in sorted(keys):
            with self.subTest(key=key):
                self.assertFalse(_loc(key).startswith(" "), key)


MEMBER_MODIFIERS = {   # convention -> (member modifier, where it sits); test_un_convention_registry's table
    "human_rights": ("un_human_rights_declaration_modifier", "je"),
    "icc": ("un_icc_member_modifier", "country"),
    "npt": ("un_nonproliferation_modifier", "je"),
    "climate": ("un_climate_binding_modifier", "je"),
    "pandemic": ("un_pandemic_cooperation_modifier", "je"),
    "refugee": ("un_refugee_program_modifier", "je"),
    "heritage": ("un_heritage_program_modifier", "je"),
    "space": ("un_space_partnership_modifier", "je"),
    "law_of_sea": ("un_law_of_sea_modifier", "country"),
    "physical_protection": ("un_physical_protection_modifier", "country"),
}
TERMS = {   # convention -> its regime terms, in display order
    "human_rights": ("un_regime_rights_violator_modifier",),
    "npt": ("un_regime_npt_inspection_modifier", "un_regime_npt_guarantee_modifier"),
    "climate": ("un_regime_climate_emitter_modifier", "un_regime_climate_adaptation_modifier"),
    "refugee": ("un_regime_refugee_host_modifier", "un_regime_refugee_source_modifier"),
    "heritage": ("un_regime_heritage_site_modifier",),
    "space": ("un_regime_space_leader_modifier", "un_regime_space_laggard_modifier",
              "un_regime_space_weapon_modifier"),
    "law_of_sea": ("un_regime_naval_curb_modifier",),
}
OTHER_TERMS = ("un_regime_colonial_pressure_modifier", "un_regime_shared_intelligence_modifier")


def _modifier_name(mod):
    return _loc_or_none(mod)


class MissionButtonsTest(unittest.TestCase):
    def test_send_and_bring_home_are_centred(self):
        row = _type_body(_read(CHAMBER), "un_chamber_mission_row")
        buttons = re.findall(r"button = \{\s*using = default_button_action\s*size = \{ 200 28 \}\s*(parentanchor = \w+)?", row)
        self.assertEqual(buttons, ["parentanchor = hcenter"] * 2)


class ObligationsTest(unittest.TestCase):
    """Our Obligations, shortened (owner, 2026-09-28): our dues beside the whole
    budget, then one line per convention with its modifiers on hover."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _type_body(_read(CHAMBER), "te_un_sec_obligations")
        cls.regimes = _block(_read(CHAMBER_EFFECTS), "un_chamber_regime_lines")

    def assertModifierHover(self, line_key, modifier):
        line = _loc(line_key)
        m = re.search(r"#tooltippable;tooltip:\[GetPlayer\.GetTooltipTag\],(\w+) ", line)
        self.assertTrue(m, f"{line_key} does not hover its modifier: {line}")
        self.assertIn(f"GetStaticModifier('{modifier}').GetDesc", _loc(m.group(1)))
        self.assertTrue(_modifier_name(modifier), f"{modifier} has no name")

    def test_our_dues_sit_beside_the_budget(self):
        dues = self.gui.index("un_chamber_dues_sgui")
        budget = self.gui.index("un_chamber_budget_sgui")
        conventions = self.gui.index("je_un_chamber_sub_regimes")
        self.assertLess(dues, budget)
        self.assertLess(budget, conventions)
        self.assertNotIn("je_un_chamber_sub_budget", self.gui)
        self.assertIsNone(_loc_or_none("je_un_chamber_sub_budget"))

    def test_every_convention_we_carry_has_a_line_with_its_modifier(self):
        for key, (mod, scope) in MEMBER_MODIFIERS.items():
            with self.subTest(convention=key):
                m = re.search(rf"un_chamber_convention_line_{scope} = \{{ MODIFIER = {mod} LINE = (\w+) \}}",
                              self.regimes)
                self.assertTrue(m, key)
                self.assertModifierHover(m.group(1), mod)

    def test_every_term_sits_under_its_convention_with_its_modifier(self):
        for key, terms in TERMS.items():
            head = self.regimes.index(f"MODIFIER = {MEMBER_MODIFIERS[key][0]} ")
            later = [self.regimes.index(f"MODIFIER = {m[0]} ") for k, m in MEMBER_MODIFIERS.items()]
            nxt = min([i for i in later if i > head] + [len(self.regimes)])
            for mod in terms:
                with self.subTest(term=mod):
                    m = re.search(rf"un_chamber_regime_line = \{{ MODIFIER = {mod} LINE = (\w+) \}}", self.regimes)
                    self.assertTrue(m, mod)
                    self.assertTrue(head < m.start() < nxt, f"{mod} is not under {key}")
                    self.assertModifierHover(m.group(1), mod)
        # Decolonization's term stands alone among the conventions; intelligence
        # sharing is the reach group's (un_chamber_reach_lines).
        reach = _block(_read(CHAMBER_EFFECTS), "un_chamber_reach_lines")
        for mod, block in zip(OTHER_TERMS, (self.regimes, reach)):
            with self.subTest(term=mod):
                m = re.search(rf"un_chamber_regime_line = \{{ MODIFIER = {mod} LINE = (\w+) \}}", block)
                self.assertTrue(m, mod)
                self.assertModifierHover(m.group(1), mod)
        self.assertModifierHover("je_un_chamber_regime_colony", "un_regime_colony_liberty_modifier")

    def test_less_explaining(self):
        for key in ("je_un_chamber_regimes_header", "je_un_chamber_regimes_none"):
            self.assertNotIn(key, self.regimes)
            self.assertIsNone(_loc_or_none(key), key)
        scale = _loc("je_un_chamber_regimes_scale")
        self.assertIn("un_enforcement_now", scale)
        self.assertNotIn("re-assessed", scale)
        self.assertIn("re-assessed", _loc("je_un_chamber_obligations_help"))
        self.assertNotIn("Until we pay", _loc("je_un_chamber_dues_article_19"))


RECORD_TERMS = ("un_case_infamy_term", "un_disp_dos_aggression", "un_disp_dos_defiance",
                "un_disp_dos_violation", "un_disp_dos_covert", "un_disp_dos_nuclear")


class RecordTest(unittest.TestCase):
    """Our Record: one name, and its terms a table (owner, 2026-09-28)."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _type_body(_read(CHAMBER), "te_un_sec_exposure")

    def test_one_name(self):
        self.assertEqual(_loc("je_un_chamber_exposure_header"), "Our Record")
        self.assertNotIn("je_un_chamber_sub_record", self.gui)
        self.assertIsNone(_loc_or_none("je_un_chamber_sub_record"))

    def test_the_terms_are_a_table(self):
        rows = self.gui.count("un_chamber_value_row = {")
        self.assertGreaterEqual(rows, 1 + len(RECORD_TERMS) + 1 + 3)
        for sv in ("un_case_strength",) + RECORD_TERMS:
            self.assertIn(f"ScriptValue('{sv}')", self.gui, sv)
        self.assertRegex(self.gui, r"visible = \"\[GreaterThan_CFixedPoint\( JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('un_case_standing_term'\)")
        for topic in ("condemn", "sanctions", "mandate"):
            self.assertIn(f"GreaterThanOrEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_case_strength'), "
                          f"JournalEntry.GetCountry.MakeScope.ScriptValue('un_case_threshold_{topic}') )", self.gui, topic)

    def test_no_text_builder_left(self):
        self.assertNotIn("un_chamber_exposure_sgui", self.gui)
        self.assertNotIn("un_chamber_exposure_sgui", _read(CHAMBER_SGUIS))
        self.assertNotIn("un_chamber_exposure_block", _read(CHAMBER_EFFECTS))


class HowStyleTest(unittest.TestCase):
    """How the UN Works in one style: the smaller #lore notes under ruled
    subheadings (owner, 2026-09-28)."""

    def test_every_text_is_a_note(self):
        how = _type_body(_read(LAYOUT), "te_un_sec_how")
        helps = _type_body(_read(AUTHORITY), "te_un_help_authority") + _type_body(_read(CHAMBER), "te_un_help_standing")
        for body in (how, helps):
            self.assertNotIn("ExecuteTooltip", body)
            self.assertNotRegex(body, r"\b(un_chamber_text|un_auth_text) = \{")
        for n in range(1, 9):
            self.assertIn(f'"je_un_auth_help_{n}"', helps)
        for part in ("intro", "sources", "losses", "limits"):
            self.assertIn(f'"je_un_standing_help_{part}"', helps)

    def test_the_text_builders_are_gone(self):
        for path, name in ((os.path.join(REPO, "common", "scripted_guis", "un_authority_sguis.txt"), "un_authority_help_sgui"),
                           (CHAMBER_SGUIS, "un_chamber_standing_help_sgui"),
                           (DISPLAY_EFFECTS, "un_authority_help_block"),
                           (CHAMBER_EFFECTS, "un_standing_help_block")):
            self.assertNotIn(f"\n{name} = {{", _read(path), name)

    def test_one_authority_explanation(self):
        self.assertIsNone(_loc_or_none("je_un_auth_tbl_explain"))
        self.assertIn("48th", _loc("je_un_auth_help_1"))
        self.assertIn("Hover a pillar", _loc("je_un_auth_help_3"))


TAB_WIDGETS = os.path.join(REPO, "gui", "te_system_tab_widgets.gui")


def _outside_brackets(value):
    out, depth = [], 0
    for ch in value:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out).strip()


class DebugLogHygieneTest(unittest.TestCase):
    """What the owner's debug.log flagged from these panels (2026-09-29)."""

    def test_no_text_mixes_words_and_data(self):
        # `text = "[X] / 100"` logs "Unlocalized text ... use the raw_text
        # property instead": a text is either a loc key or one data binding.
        files = UN_GUI + [os.path.join(W, "un_overview_widget.gui"), TAB_WIDGETS]
        for path in files:
            for n, line in enumerate(_read(path).splitlines(), 1):
                for m in re.finditer(r'(?<![\w])text\s*=\s*"([^"]*)"', line):
                    if "[" in m.group(1):
                        with self.subTest(file=os.path.basename(path), line=n):
                            self.assertEqual(_outside_brackets(m.group(1)), "", m.group(1))

    def test_the_sixth_tab_has_vanillas_placeholder_key(self):
        # Vanilla's tab_buttons defaults each slot's tooltip to TAB_1..TAB_5,
        # which its loc defines; the sixth slot's default needs its own.
        self.assertIn('tooltip = "TAB_6"', _read(TAB_WIDGETS))
        self.assertEqual(_loc("TAB_6"), "#header Tab 6#!")


UNLOCK_TRIGGERS = {   # the tab gates' is_valid (te_system_tab_sguis.txt), and the file each lives in
    "te_banking_entry_unlocked": "banking_policy_triggers.txt",
    "ch_entry_unlocked": "cultural_hegemony_triggers.txt",
    "un_entry_unlocked": "un_membership_triggers.txt",
    "nuclear_program_entry_unlocked": "nuke_triggers.txt",
    "gw_entry_unlocked": "global_warming_triggers.txt",
    "st_res_entry_unlocked": "st_res_triggers.txt",
}


class TabUnlockTooltipTest(unittest.TestCase):
    """A greyed tab's tooltip lists its unlock conditions. An OR printed
    bare there shows as an empty "All of these:" (owner, 2026-09-29, the UN
    tab), so any OR sits inside a custom_tooltip that says it in one line."""

    def _body(self, name):
        text = _read(os.path.join(REPO, "common", "scripted_triggers", UNLOCK_TRIGGERS[name]))
        return _block(text, name)

    def test_no_bare_or(self):
        for name in UNLOCK_TRIGGERS:
            with self.subTest(trigger=name):
                body = self._body(name)
                stack = []   # the kind of each open block
                for m in re.finditer(r"custom_tooltip = \{|\bOR = \{|\{|\}", body):
                    tok = m.group(0)
                    if tok == "}":
                        stack.pop()
                        continue
                    kind = "tooltip" if tok.startswith("custom_tooltip") else "or" if tok.startswith("OR") else "block"
                    if kind == "or":
                        self.assertIn("tooltip", stack, f"{name}: an OR outside a custom_tooltip")
                    stack.append(kind)

    def test_the_un_line_names_both_ways_in(self):
        body = self._body("un_entry_unlocked")
        m = re.search(r"custom_tooltip = \{\s*text = (\w+)", body)
        self.assertTrue(m, body)
        line = _loc(m.group(1))
        self.assertIn("$intergovernmental_organizations$", line)
        self.assertIn("$je_united_nations$", line)


CONV_KEYS = ("human_rights", "icc", "npt", "climate", "pandemic", "refugee", "heritage", "decolonization",
             "space", "law_of_sea", "physical_protection")
REGIME_TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "un_regime_triggers.txt")


class ReviewRound2Test(unittest.TestCase):
    """The fresh review of the owner's second round (2026-09-29)."""

    @classmethod
    def setUpClass(cls):
        cls.effects = _read(CHAMBER_EFFECTS)
        cls.regimes = _block(cls.effects, "un_chamber_regime_lines")

    def test_a_hover_says_the_multiplier_its_modifier_is_applied_with(self):
        intel = _loc("je_un_chamber_regime_shared_intelligence_tt")
        self.assertNotIn("concept_un_enforcement", intel)          # applied with un_regime_strong_steps
        self.assertIn("concept_un_tier_supranational", intel)
        self.assertIn("warming", _loc("je_un_chamber_regime_climate_adaptation_tt"))

    def test_the_reach_of_a_strong_un_is_its_own_group(self):
        reach = _block(self.effects, "un_chamber_reach_lines")
        for key in ("je_un_chamber_regime_shared_intelligence", "je_un_chamber_sovereignty_resent",
                    "je_un_chamber_sovereignty_welcome"):
            self.assertIn(key, reach, key)
            self.assertNotIn(key, self.regimes, key)
        gui = _type_body(_read(CHAMBER), "te_un_sec_obligations")
        self.assertIn("je_un_chamber_sub_reach", gui)
        self.assertIn("GetScriptedGui('un_chamber_reach_sgui').IsShown", gui)

    def test_the_footnote_needs_a_convention_above_it(self):
        m = re.search(r"if = \{\s*limit = \{ un_chamber_party_to_a_convention = yes \}\s*"
                      r"custom_tooltip_no_bullet = je_un_chamber_regimes_scale", self.regimes)
        self.assertTrue(m, "the footnote is not gated on being party to a convention")
        self.assertIn("je_un_chamber_regimes_not_party", self.regimes)
        party = _block(_read(REGIME_TRIGGERS), "un_chamber_party_to_a_convention")
        for key, (mod, scope) in MEMBER_MODIFIERS.items():
            with self.subTest(convention=key):
                if scope == "je":
                    self.assertRegex(party, rf"je:je_united_nations \?= \{{[^}}]*has_modifier = {mod}\b")
                else:
                    self.assertRegex(party, rf"(?m)^\t+has_modifier = {mod}$")

    def test_icc_jurisdiction_over_a_non_party_is_its_own_line(self):
        self.assertIn("je_un_chamber_regime_icc_outside", self.regimes)
        outside = _loc("je_un_chamber_regime_icc_outside")
        self.assertFalse(outside.startswith(" "))
        self.assertIn("$je_un_conv_name_icc$", outside)

    def test_a_member_colony_sees_its_decolonization_term(self):
        self.assertIn("MODIFIER = un_regime_colony_liberty_modifier LINE = je_un_chamber_regime_colony", self.regimes)

    def test_one_name_per_convention(self):
        for k in CONV_KEYS:
            with self.subTest(convention=k):
                name = _loc(f"je_un_conv_name_{k}")
                self.assertNotIn("$", name)
                self.assertIn(f"$je_un_conv_name_{k}$", _loc(f"je_un_chamber_propose_topic_{k}"))
                if k in MEMBER_MODIFIERS:
                    self.assertIn(f"$je_un_conv_name_{k}$", _loc(f"je_un_chamber_conv_{k}"))
        self.assertIn("$je_un_conv_name_decolonization$", _loc("je_un_chamber_regime_colonial_pressure"))

    def test_the_tab_status_hides_with_nothing_to_say(self):
        tab = _read(os.path.join(REPO, "gui", "diplomatic_overview.gui"))
        self.assertIn("GetScriptedGui('un_status_text_sgui').IsShown", tab)
        for key in ("je_un_status_conference", "je_un_status_dissolved"):
            self.assertFalse(_loc(key).endswith("\\n"), key)

    def test_the_record_rounds_like_the_verdict_reads(self):
        record = _type_body(_read(CHAMBER), "te_un_sec_exposure")
        values = re.findall(r"ScriptValue\('(un_case_[a-z_]+|un_disp_dos_[a-z]+)'\)\|(\d)\]", record)
        self.assertTrue(values)
        for sv, digits in values:
            with self.subTest(value=sv):
                self.assertEqual(digits, "1", sv)

    def test_the_refugee_target_line_ends_its_sentence(self):
        self.assertTrue(_loc("je_un_chamber_propose_target_refugee").endswith("nobody."))

if __name__ == "__main__":
    unittest.main()
