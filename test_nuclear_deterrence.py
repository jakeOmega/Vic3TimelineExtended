"""Nuclear deterrence and crisis diplomacy: the hand-kept tables that must agree.

The system (docs/systems/nuclear_crisis_design.md §0) keeps a few lists in
more than one place — the panel's op codes in the .gui, the scripted GUIs and
journal_entry_systems.md; the event ids it fires; the loc keys its script,
events, custom loc and widget name; the managed modifier families. Nothing in
the engine checks any of them: a mistyped op is a dead button, a missing loc
key is a raw key in the player's face, a missing event id is a silent no-op.
Each test pins one of those lists in both directions where both exist.

Run: python3 -m unittest test_nuclear_deterrence -v
"""

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GUI = ROOT / "gui/journal_entry_widgets/nuclear_deterrence_widget.gui"
SGUIS = ROOT / "common/scripted_guis/nuclear_deterrence_sguis.txt"
EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
CRISIS_EFFECTS = ROOT / "common/scripted_effects/nuclear_crisis_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"
VALUES = ROOT / "common/script_values/nuclear_deterrence_values.txt"
MODIFIERS = ROOT / "common/static_modifiers/nuclear_deterrence_modifiers.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/nuclear_deterrence_custom_loc.txt"
ACTIONS = ROOT / "common/diplomatic_actions/nuclear_crisis_actions.txt"
ARTICLE = ROOT / "common/treaty_articles/115_nuclear_guarantee.txt"
JE = ROOT / "common/journal_entries/je_nuclear_program.txt"
CRISIS_EVENTS = ROOT / "events/nuclear_crisis_events.txt"
INCIDENT_EVENTS = ROOT / "events/nuclear_incident_events.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_deterrence_events.txt"
JE_DOC = ROOT / "docs/systems/journal_entry_systems.md"
LOC_DIR = ROOT / "localization/english"
LENS_ICONS = ROOT / "gfx/interface/icons/lens_toolbar_icons"
NUKE = ROOT / "common/diplomatic_actions/nuke.txt"
WEAPON_EVENTS = ROOT / "events/nuclear_weapon_events.txt"


def tracked(path):
    """Whether git tracks path. CI checks out without gfx/ (sparse), so a
    texture can be committed yet absent from the working tree."""
    rel = path.relative_to(ROOT).as_posix()
    result = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                            cwd=ROOT, capture_output=True)
    return result.returncode == 0

# `trigger_event = { id = X }`, or nd_crisis_send_event's EVENT parameter.
FIRED = r"\b(?:id|EVENT) = ([a-z_]+\.\d+)"

SCRIPT_FILES = (EFFECTS, CRISIS_EFFECTS, TRIGGERS, ACTIONS, ARTICLE, JE, SGUIS,
                CRISIS_EVENTS, INCIDENT_EVENTS, DEBUG_EVENTS, NUKE)
EVENT_FILES = (CRISIS_EVENTS, INCIDENT_EVENTS, DEBUG_EVENTS)


def read(path):
    return path.read_text(encoding="utf-8-sig")


def strip_comments(text):
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def loc_keys():
    keys = set()
    for path in LOC_DIR.glob("*.yml"):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"\s+([A-Za-z0-9_.\-]+):\d*\s", line)
            if m:
                keys.add(m.group(1))
    return keys


def block(text, name):
    """The body of the first `name = { ... }` block that opens a line: a
    top-level definition if there is one, else the first indented one (an
    indented `name = { PARAM = … }` call must not shadow the definition)."""
    m = (re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
         or re.search(r"^[ \t]*" + re.escape(name) + r"\s*=\s*\{", text, re.M))
    if not m:
        raise AssertionError(f"{name} not found")
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return text[m.end():i - 1]


def gui_ops(gui_text, sgui):
    """Op codes the .gui passes to `sgui` (rows set the datacontext)."""
    ops = set()
    for m in re.finditer(r"datacontext = \"\[GetScriptedGui\('(\w+)'\)\]\"", gui_text):
        if m.group(1) != sgui:
            continue
        # The row's buttons follow its datacontext, up to the next row.
        nxt = re.search(r"datacontext = ", gui_text[m.end():])
        seg = gui_text[m.end(): m.end() + (nxt.start() if nxt else len(gui_text))]
        ops |= {int(x) for x in re.findall(r"\(CFixedPoint\)(\d+)", seg)}
    return ops


def sgui_ops(sgui_text, name, part):
    body = block(sgui_text, name)
    part_body = block(body, part) if part != "effect" else block(body, "effect")
    return {int(x) for x in re.findall(r"scope:op = (\d+)", part_body)}


class TestPanelOps(unittest.TestCase):
    def setUp(self):
        self.gui = read(GUI)
        self.sguis = strip_comments(read(SGUIS))

    def test_every_gui_op_is_handled_and_every_handled_op_is_drawn(self):
        for sgui in ("nd_posture_sgui", "nd_crisis_action_sgui"):
            drawn = gui_ops(self.gui, sgui)
            valid = sgui_ops(self.sguis, sgui, "is_valid")
            effect = sgui_ops(self.sguis, sgui, "effect")
            self.assertTrue(drawn, f"no buttons found for {sgui}")
            self.assertEqual(drawn, valid, f"{sgui}: .gui ops vs is_valid")
            self.assertEqual(drawn, effect, f"{sgui}: .gui ops vs effect")

    def test_op_table_in_docs_names_every_op(self):
        doc = JE_DOC.read_text(encoding="utf-8")
        section = doc.split("### Nuclear Deterrence Widget", 1)[1].split("\n### ", 1)[0]
        documented = set()
        for lo, hi in re.findall(r"\|\s*(\d+)(?:\s*[–-]\s*(\d+))?\s*\|", section):
            documented |= set(range(int(lo), int(hi or lo) + 1))
        for lo, hi in re.findall(r"\|\s*(\d+) / (\d+)\s*\|", section):
            documented |= {int(lo), int(hi)}
        for sgui in ("nd_posture_sgui", "nd_crisis_action_sgui"):
            missing = gui_ops(self.gui, sgui) - documented
            self.assertFalse(missing, f"{sgui} ops missing from journal_entry_systems.md: {sorted(missing)}")


class TestEventReferences(unittest.TestCase):
    def test_every_fired_event_exists(self):
        defined = set()
        for path in (ROOT / "events").glob("*.txt"):
            defined |= set(re.findall(r"^([a-z_]+\.\d+)\s*=\s*\{", read(path), re.M))
        for path in SCRIPT_FILES:
            text = strip_comments(read(path))
            for ev in re.findall(FIRED, text):
                if ev not in defined:
                    self.fail(f"{path.name} fires {ev}, which no event file defines")

    def test_every_new_event_is_fired_somewhere_or_console_only(self):
        fired = set()
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "events").glob("*.txt")):
            fired |= set(re.findall(FIRED, strip_comments(read(path))))
        for path in (CRISIS_EVENTS, INCIDENT_EVENTS):
            for ev in re.findall(r"^([a-z_]+\.\d+)\s*=\s*\{", read(path), re.M):
                if ev not in fired:
                    self.fail(f"{ev} is never fired")


class TestLocalization(unittest.TestCase):
    def setUp(self):
        self.keys = loc_keys()

    def assert_keys(self, keys, where):
        missing = sorted(k for k in keys if k not in self.keys)
        self.assertFalse(missing, f"{where}: missing loc keys {missing}")

    def test_event_text_keys(self):
        for path in EVENT_FILES:
            text = strip_comments(read(path))
            keys = set(re.findall(r"\b(?:title|desc|flavor|name) = ([a-z_]+\.\d+\.[a-z_.]+)", text))
            self.assertTrue(keys, path.name)
            self.assert_keys(keys, path.name)

    def test_custom_tooltip_keys(self):
        keys = set()
        for path in SCRIPT_FILES:
            text = strip_comments(read(path))
            keys |= set(re.findall(r"custom_tooltip(?:_no_bullet)? = (nd_[\w$]+)", text))
            keys |= set(re.findall(r"text = (nd_[\w$]+)", text))
        expanded = {k for k in keys if "$" not in k}
        # Parameterised families: every value the wrappers pass.
        expanded |= {f"nd_tt_doctrine_adopted_{d}" for d in range(1, 6)}
        expanded |= {f"nd_tt_readiness_target_{r}" for r in range(0, 4)}
        expanded |= {f"nd_tt_authority_adopted_{a}" for a in range(1, 5)}
        expanded |= {f"nd_tt_{v}_{o}" for v in ("nd_safeguards", "nd_hardening") for o in ("add", "subtract")}
        self.assert_keys(expanded, "custom tooltips")

    def test_custom_loc_targets(self):
        keys = set(re.findall(r"localization_key = (\w+)", strip_comments(read(CUSTOM_LOC))))
        self.assert_keys(keys, CUSTOM_LOC.name)

    def test_widget_keys(self):
        text = read(GUI)
        keys = set(re.findall(r'(?:text|tooltip) = "(nd_\w+)"', text))
        self.assertTrue(keys)
        self.assert_keys(keys, GUI.name)

    def test_static_modifiers_named_and_described(self):
        mods = re.findall(r"^(nd_\w+)\s*=\s*\{", read(MODIFIERS), re.M)
        self.assertTrue(mods)
        self.assert_keys(set(mods) | {m + "_desc" for m in mods}, MODIFIERS.name)

    def test_diplomatic_actions_and_article(self):
        acts = re.findall(r"^(nd_\w+_action)\s*=\s*\{", read(ACTIONS), re.M)
        self.assertEqual(len(acts), 3)
        needed = set()
        for a in acts:
            needed |= {a, a + "_desc", a + "_action_notification_name", a + "_action_notification_desc"}
        needed |= {"nuclear_guarantee", "nuclear_guarantee_desc",
                   "nuclear_guarantee_article_short_desc", "nuclear_guarantee_effects_desc"}
        self.assert_keys(needed, "actions and article")

    def test_diplomatic_actions_have_lens_icons(self):
        """The engine loads lens_toolbar_icons/<action>.dds for every action
        without show_in_lens = no; a missing one is a VFSOpen error per session."""
        text = strip_comments(read(ACTIONS))
        for action in re.findall(r"^(nd_\w+_action)\s*=\s*\{", text, re.M):
            if re.search(r"show_in_lens\s*=\s*no", block(text, action)):
                continue
            icon = LENS_ICONS / f"{action}.dds"
            self.assertTrue(icon.exists() or tracked(icon), f"missing {icon.relative_to(ROOT)}")

    def test_journal_entry_keys(self):
        # Posture and crises share je_nuclear_program since 2026-09-25.
        self.assert_keys({"je_nuclear_program", "je_nuclear_program_desc",
                          "je_nuclear_program_reason",
                          "je_nuclear_program_status_line"}, JE.name)


def option_body(text, option_name):
    """The body of the `option = { … }` whose `name` is option_name."""
    m = re.search(r"name = " + re.escape(option_name) + r"\s", text)
    if not m:
        raise AssertionError(f"{option_name} not found")
    start = text.rfind("option = {", 0, m.start())
    return block(text[start:], "option")


class TestWarLawGate(unittest.TestCase):
    def test_gate_triggers_exist(self):
        t = read(TRIGGERS)
        for name in ("nd_war_law_permits_strategic_strike",
                     "nd_war_law_permits_tactical_strike",
                     "nd_war_law_exception"):
            self.assertRegex(t, rf"(?m)^{name} = \{{")

    def test_strike_actions_use_the_shared_gate(self):
        text = strip_comments(read(NUKE))
        self.assertNotIn("has_law = law_type:law_limited_war", text)
        self.assertIn("nd_war_law_permits_strategic_strike = yes", block(text, "nuke_diplo_action"))
        self.assertIn("nd_war_law_permits_tactical_strike = yes", block(text, "tactical_nuke_diplo_action"))

    def test_every_crisis_strike_option_checks_the_law(self):
        text = strip_comments(read(CRISIS_EVENTS))
        for opt in ("nuclear_crisis.4.g", "nuclear_crisis.7.a", "nuclear_crisis.20.b"):
            self.assertIn("nd_war_law_permits_strategic_strike = yes", option_body(text, opt), opt)


class TestFollowThrough(unittest.TestCase):
    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def test_triggers_exist(self):
        for name in ("nd_threat_bluff_nfu", "nd_threat_law_permits", "nd_threat_existential_stake",
                     "nd_threat_backed", "nd_threat_uncertain", "nd_enemy_threatens_existence_in_play"):
            self.assertRegex(self.triggers, rf"(?m)^{name} = \{{")

    def test_classification_writes_every_reason_once(self):
        body = block(self.effects, "nd_crisis_classify_follow_through")
        codes = re.findall(r"name = nd_ft_reason value = (\d)", body)
        self.assertEqual(sorted(codes), [str(c) for c in range(1, 8)])

    def test_ai_never_bluffs_in_public(self):
        self.assertIn("nd_threat_backed = { TARGET = $TARGET$ }",
                      block(self.triggers, "nd_ai_would_issue_ultimatum"))

    def test_ai_bluffs_in_private_only_when_aggressive(self):
        warn = block(self.triggers, "nd_ai_would_warn")
        self.assertRegex(warn, r"OR = \{\s*nd_threat_backed = \{ TARGET = \$TARGET\$ \}\s*ruler_is_aggressive = yes\s*\}")


DANGER_PARTS = ["nd_cd_stage", "nd_cd_issuer_readiness", "nd_cd_target_readiness", "nd_cd_public",
                "nd_cd_counter", "nd_cd_reliability", "nd_cd_weeks", "nd_cd_talks", "nd_cd_backed",
                "nd_cd_exercise"]
PRESSURE_PARTS = ["nd_yp_base", "nd_yp_answer", "nd_yp_protector", "nd_yp_credibility", "nd_yp_alert",
                  "nd_yp_recessed", "nd_yp_danger", "nd_yp_exercise", "nd_yp_temperament", "nd_yp_war",
                  "nd_yp_follow_through"]


class TestCrisisFigures(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(VALUES))
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def summed(self, total):
        body = block(self.values, total)
        return re.findall(r"(?:value|add) = (nd_(?:cd|yp)_\w+)_value\b", body)

    def test_totals_are_exactly_their_parts(self):
        self.assertEqual(self.summed("nd_crisis_danger_value"), DANGER_PARTS)
        self.assertEqual(self.summed("nd_yield_pressure_value"), PRESSURE_PARTS)

    def test_every_part_has_a_value(self):
        for part in DANGER_PARTS + PRESSURE_PARTS:
            self.assertRegex(self.values, rf"(?m)^{part}_value = \{{", part)

    def test_refresh_stores_every_part_under_its_own_value(self):
        body = block(self.effects, "nd_crisis_refresh_figures")
        stored = re.findall(r"nd_crisis_store_(?:cd|yp) = \{ C = (\w+) V = (\w+) \}", body)
        self.assertEqual([c for c, _ in stored], DANGER_PARTS + PRESSURE_PARTS)
        for c, v in stored:
            self.assertEqual(v, c + "_value")

    def test_clear_removes_every_part(self):
        body = block(self.effects, "nd_crisis_clear_figures")
        for var in DANGER_PARTS + PRESSURE_PARTS + ["nd_cd_dampened", "nd_ft_reason"]:
            self.assertIn(f"remove_variable = {var}", body, var)

    def test_losing_war_is_read_from_the_target(self):
        self.assertNotIn("is_losing_war_against", block(self.values, "nd_yp_war_value"))
        self.assertIn("nd_is_losing_war_to = { ENEMY = scope:nd_issuer }", block(self.values, "nd_yp_war_value"))
        self.assertNotIn("ROOT", block(strip_comments(read(TRIGGERS)), "nd_is_losing_war_to"))

    def test_refresh_is_the_only_writer_of_the_totals(self):
        for path in (CRISIS_EFFECTS, EFFECTS, CRISIS_EVENTS, INCIDENT_EVENTS):
            text = strip_comments(read(path))
            if path == CRISIS_EFFECTS:
                text = text.replace(block(text, "nd_crisis_refresh_figures"), "")
            self.assertNotRegex(text, r"name = nd_(?:crisis_danger|yield_pressure) value", path.name)


class TestOutcomeNotice(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.events = strip_comments(read(CRISIS_EVENTS))

    def test_close_no_longer_applies_consequences(self):
        self.assertNotRegex(self.effects, r"(?m)^nd_crisis_apply_outcome = \{")
        self.assertNotIn("nd_crisis_apply_outcome = yes", block(self.effects, "nd_crisis_close"))

    def test_close_flushes_before_recording(self):
        body = block(self.effects, "nd_crisis_close")
        flush = body.index("nd_crisis_flush_pending = yes")
        record = body.index("nd_crisis_record_pending = yes")
        self.assertLess(flush, record)
        self.assertEqual(body.count("nd_crisis_flush_pending = yes"), 2)

    def test_outcome_nine_records_nothing(self):
        body = block(self.effects, "nd_crisis_close")
        self.assertRegex(body, r"NOT = \{ var:nd_crisis_outcome_now = 9 \}(\s*\})+\s*nd_crisis_record_pending = yes")

    def test_outcome_option_guards_pending(self):
        body = option_body(self.events, "nuclear_crisis.6.a")
        self.assertIn("has_variable = nd_crisis_pending_outcome", body)
        self.assertIn("var:nd_crisis_pending_opponent ?= scope:nd_outcome_other", body)
        self.assertIn("nd_crisis_apply_outcome_side = yes", body)
        self.assertIn("custom_tooltip = nd_tt_outcome_already_settled", body)

    def test_every_credibility_change_says_its_number(self):
        body = block(self.effects, "nd_crisis_apply_outcome_side") + block(self.effects, "nd_crisis_bluff_called")
        pairs = re.findall(r"text = nd_tt_credibility_(up|down)_(\d+)(?:_bluff)?\s*nd_change_credibility = \{ AMOUNT = (-?\d+) \}", body)
        self.assertTrue(pairs)
        for direction, n, amount in pairs:
            self.assertEqual(int(amount), int(n) if direction == "up" else -int(n))
        self.assertEqual(body.count("nd_change_credibility"), len(pairs), "a credibility change without its number line")


PREVIEW_PINS = {
    # loc key: (script value holding the constant, operation, number)
    "nd_tt_open_f_unarmed": ("nd_yp_answer_value", "add", 20),
    "nd_tt_open_f_survivable": ("nd_yp_answer_value", "subtract", 25),
    "nd_tt_open_f_armed": ("nd_yp_answer_value", "subtract", 10),
    "nd_tt_open_f_protector": ("nd_yp_protector_value", "subtract", 20),
    "nd_tt_open_f_aggressive": ("nd_yp_temperament_value", "subtract", 15),
    "nd_tt_open_f_cautious": ("nd_yp_temperament_value", "add", 10),
    "nd_tt_open_f_losing": ("nd_yp_war_value", "add", 15),
    "nd_tt_open_f_existence": ("nd_yp_war_value", "subtract", 15),
    "nd_tt_open_f_alert": ("nd_yp_alert_value", "add", 10),
    "nd_tt_open_backed": ("nd_yp_follow_through_value", "add", 10),
    "nd_tt_open_bluff_existential": ("nd_yp_follow_through_value", "subtract", 25),
    "nd_tt_open_bluff_flexible": ("nd_yp_follow_through_value", "subtract", 25),
    "nd_tt_open_bluff_law": ("nd_yp_follow_through_value", "subtract", 25),
    "nd_tt_open_bluff_nfu": ("nd_yp_follow_through_value", "subtract", 35),
}


def loc_value(key):
    for path in LOC_DIR.glob("*.yml"):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"\s+" + re.escape(key) + r":\d*\s+\"(.*)\"\s*$", line)
            if m:
                return m.group(1)
    raise AssertionError(f"loc key {key} not found")


class TestActionPreview(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.values = strip_comments(read(VALUES))

    def test_open_uses_the_preview(self):
        body = block(self.effects, "nd_crisis_open")
        self.assertIn("nd_crisis_preview = { TARGET = $TARGET$ PUBLIC = $PUBLIC$ }", body)
        self.assertNotIn("nd_tt_crisis_opens_", body)
        self.assertNotIn("change_infamy", body)
        self.assertNotIn("change_relations", body)

    def test_preview_reads_no_crisis_scopes(self):
        body = block(self.effects, "nd_crisis_preview")
        self.assertNotRegex(body, r"scope:nd_(?!pv_self\b)")
        self.assertNotRegex(body, r"(?<!temporary_)save_scope_as")
        self.assertNotRegex(body, r"= PREV\b", "PREV passed as a parameter")

    def test_preview_numbers_match_the_formula(self):
        preview = block(self.effects, "nd_crisis_preview")
        for key, (value, op, n) in PREVIEW_PINS.items():
            self.assertIn(key, preview, key)
            self.assertRegex(block(self.values, value), rf"{op} = {n}\b", f"{value} lost {op} {n}")
            self.assertIn(str(n), loc_value(key), key)

    def test_preview_stakes_and_deadlines(self):
        self.assertRegex(self.values, r"nd_crisis_deadline_public_weeks = 8\b")
        self.assertRegex(self.values, r"nd_crisis_deadline_private_weeks = 10\b")
        self.assertRegex(self.values, r"nd_crisis_pressure_interval_weeks = 6\b")
        self.assertIn("8", loc_value("nd_tt_open_next_public"))
        self.assertIn("10", loc_value("nd_tt_open_next_private"))
        for key in ("nd_tt_open_next_public", "nd_tt_open_next_private"):
            self.assertIn("6", loc_value(key))
        for n in ("15", "10"):
            self.assertIn(n, loc_value("nd_tt_open_stakes_public"))
        for n in ("10", "5"):
            self.assertIn(n, loc_value("nd_tt_open_stakes_private"))


ACT_LINES = {
    "nd_crisis_act_yield": ["nd_crisis_yield_lines = yes", "custom_tooltip = nd_tt_then_yield"],
    "nd_crisis_yield_lines": ["nd_tt_yield_war", "nd_tt_yield_play", "nd_tt_yield_guarantee",
                              "nd_tt_yield_freeze", "nd_tt_yield_alert"],
    "nd_crisis_act_reject": ["nd_tt_stage_to_confrontation", "nd_tt_reject_defiance"],
    "nd_crisis_act_counter_threat": ["nd_tt_stage_to_confrontation", "nd_tt_counter_danger"],
    "nd_crisis_act_propose_talks": ["nd_tt_talks_terms", "nd_crisis_talks_credibility_lines = yes",
                                    "nd_tt_talks_meanwhile"],
    "nd_crisis_act_accept_standdown": ["nd_tt_standdown_terms", "nd_crisis_talks_credibility_lines = yes"],
    "nd_crisis_act_hold": ["nd_tt_hold_deadline", "nd_tt_hold_alert_4w", "nd_tt_hold_alert_2w"],
    "nd_crisis_act_extend": ["text = nd_tt_credibility_down_3"],
    "nd_crisis_act_back_down": ["nd_tt_then_back_down_public", "nd_tt_then_back_down_private",
                                "nd_tt_then_bluff_called"],
    "nd_crisis_act_go_public": ["change_infamy = 5", "change_relations", "nd_tt_go_public_terms"],
    "nd_crisis_act_exercise": ["text = nd_tt_strain_up_5", "text = nd_tt_credibility_up_3",
                               "nd_tt_exercise_effect"],
}


class TestActLines(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def test_every_act_names_its_numbers(self):
        for act, needles in ACT_LINES.items():
            body = block(self.effects, act)
            for needle in needles:
                self.assertIn(needle, body, f"{act} lacks {needle}")

    def test_visible_act_lines_read_no_saved_scopes(self):
        """The panel renders these acts with no saved scopes."""
        for act in ACT_LINES:
            body = block(self.effects, act)
            hidden = re.findall(r"hidden_effect = \{", body)
            visible = body
            for _ in hidden:
                visible = visible.replace("hidden_effect = {" + block(visible, "hidden_effect") + "}", "")
            self.assertNotRegex(visible, r"scope:nd_(issuer|target)", act)

    def test_act_numbers_match_their_constants(self):
        values = strip_comments(read(VALUES))
        self.assertRegex(values, r"nd_crisis_deadline_extension_weeks = 6\b")
        self.assertIn("6", loc_value("nd_tt_hold_deadline"))
        self.assertIn("6", loc_value("nd_tt_act_extend"))
        self.assertRegex(block(values, "nd_cd_counter_value"), r"add = 10\b")
        self.assertIn("10", loc_value("nd_tt_counter_danger"))
        self.assertRegex(block(values, "nd_cd_talks_value"), r"subtract = 15\b")
        self.assertIn("15", loc_value("nd_tt_talks_meanwhile"))
        self.assertRegex(block(values, "nd_yp_alert_value"), r"add = 10\b")
        self.assertIn("10", loc_value("nd_tt_hold_alert_2w"))
        self.assertIn("name = nd_crisis_exercise_weeks value = 6", block(self.effects, "nd_crisis_act_exercise"))
        self.assertIn("6", loc_value("nd_tt_exercise_effect"))


BREAKDOWN_KEYS = {p: p + "_line" for p in DANGER_PARTS + PRESSURE_PARTS}


class TestCrisisPanel(unittest.TestCase):
    def setUp(self):
        self.sguis = strip_comments(read(SGUIS))
        self.gui = read(GUI)
        self.custom = strip_comments(read(CUSTOM_LOC))
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def test_display_handlers_exist_and_are_display_only(self):
        for name in ("nd_crisis_we_issued_sgui", "nd_crisis_we_are_target_sgui", "nd_crisis_private_sgui",
                     "nd_crisis_pressure_breakdown_sgui", "nd_crisis_danger_breakdown_sgui",
                     "nd_crisis_next_pressure_sgui"):
            body = block(self.sguis, name)
            self.assertIn("is_valid = { always = no }", body, name)
            self.assertIn("ai_is_valid = { always = no }", body, name)
            self.assertIn(name, self.gui, f"{name} is never drawn")

    def test_breakdowns_print_every_stored_part(self):
        pressure = block(self.sguis, "nd_crisis_pressure_breakdown_sgui")
        danger = block(self.sguis, "nd_crisis_danger_breakdown_sgui")
        for part in PRESSURE_PARTS:
            self.assertIn(f"nd_crisis_breakdown_line = {{ C = {part} KEY = {BREAKDOWN_KEYS[part]} }}", pressure)
        for part in DANGER_PARTS:
            self.assertIn(f"nd_crisis_breakdown_line = {{ C = {part} KEY = {BREAKDOWN_KEYS[part]} }}", danger)

    def test_breakdown_lines_guard_their_variable(self):
        body = block(self.effects, "nd_crisis_breakdown_line")
        self.assertIn("has_variable = $C$", body)
        for part, key in BREAKDOWN_KEYS.items():
            self.assertIn(f"THIS.Var('{part}').GetValue", loc_value(key), key)

    def test_role_rows_are_gated(self):
        for key, sgui in (("nd_w_crisis_act_public", "nd_crisis_private_sgui"),
                          ("nd_w_crisis_act_yield", "nd_crisis_we_are_target_sgui"),
                          ("nd_w_crisis_act_back_down", "nd_crisis_we_issued_sgui"),
                          ("nd_w_crisis_act_exercise", "nd_armed_sgui")):
            i = self.gui.index(f'text = "{key}"')
            row = self.gui.rfind("nd_choice_row = {", 0, i)
            self.assertIn(f"GetScriptedGui('{sgui}')", self.gui[row:i], key)

    def test_new_custom_loc_blocks_have_fallbacks(self):
        for name in ("nd_crisis_pressure_label", "nd_crisis_concede_label", "nd_crisis_concession_short",
                     "nd_crisis_concession_long", "nd_crisis_ft_label", "nd_crisis_ft_word",
                     "nd_crisis_ft_reason", "nd_crisis_stakes_short", "nd_crisis_stakes_long",
                     "nd_crisis_concession_past", "nd_crisis_stage_next"):
            body = block(self.custom, name)
            self.assertRegex(body, r"text = \{\s*trigger = \{ always = yes \}\s*localization_key = \w+\s*\}\s*$", name)

    def test_localize_keys_in_gui_exist(self):
        keys = set(re.findall(r"Localize\( '(\w+)' \)", self.gui))
        self.assertTrue(keys)
        missing = sorted(k for k in keys if k not in loc_keys())
        self.assertFalse(missing, missing)

    def test_pressure_thresholds_match_the_events(self):
        events = strip_comments(read(CRISIS_EVENTS))
        concede = option_body(events, "nuclear_crisis.5.a")
        for n in ("50", "70", "85"):
            self.assertIn(f"var:nd_yield_pressure >= {n}", concede)
            self.assertIn(n, loc_value("nd_w_crisis_pressure_tt"))


class TestInterestGroupClasses(unittest.TestCase):
    OLD = ("nd_ig_leader_is_hawk", "nd_ig_leader_is_dove", "nd_ig_class_warfighting", "nd_ig_class_dove")
    NEW = ("nd_stance_militarist_full", "nd_stance_militarist_mild", "nd_stance_restraint_full",
           "nd_stance_restraint_mild", "nd_stance_militarist", "nd_stance_restraint",
           "nd_stance_full", "nd_ig_is_fixed_class", "nd_ig_class_professional", "nd_ig_class_business",
           "nd_ig_class_militarist", "nd_ig_class_restraint", "nd_ig_lean_militarist", "nd_ig_lean_restraint",
           "nd_ig_is_militarist", "nd_ig_is_restraint", "nd_ig_is_hawk", "nd_ig_view_full")

    def test_new_triggers_exist(self):
        t = read(TRIGGERS)
        for name in self.NEW:
            self.assertRegex(t, rf"(?m)^{name} = \{{", name)

    def test_old_triggers_are_gone_everywhere(self):
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "events").glob("*.txt")):
            text = strip_comments(read(path))
            for name in self.OLD:
                self.assertNotIn(name, text, f"{path.name} still uses {name}")

    def test_stances_read_the_rules_of_war_laws(self):
        t = strip_comments(read(TRIGGERS))
        for name in ("nd_stance_militarist_full", "nd_stance_restraint_full"):
            body = block(t, name)
            self.assertIn("law_type:law_total_war", body)
            self.assertIn("law_type:law_limited_war", body)

    def test_rewards_pay_hawks_and_doves(self):
        effects = strip_comments(read(CRISIS_EFFECTS))
        self.assertIn("nd_ig_is_hawk = yes", block(effects, "nd_reward_hawks"))
        self.assertIn("nd_ig_is_restraint = yes", block(effects, "nd_reward_doves"))


IG_VARS = ["nd_ig_class", "nd_ig_lean", "nd_ig_strength", "nd_ig_term_doctrine", "nd_ig_term_readiness",
           "nd_ig_term_authority", "nd_ig_term_strain", "nd_ig_term_business", "nd_ig_stance"]


class TestInterestGroupOpinion(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(VALUES))
        self.effects = strip_comments(read(EFFECTS))

    def test_country_level_stance_values_are_gone(self):
        for old in ("nd_stance_warfighting_value", "nd_stance_professional_value",
                    "nd_stance_dove_value", "nd_stance_business_value"):
            self.assertNotRegex(self.values, rf"(?m)^{old} = \{{")

    def test_ig_values_exist(self):
        for name in ("nd_ig_doctrine_militarist_value", "nd_ig_doctrine_restraint_value",
                     "nd_ig_doctrine_professional_value", "nd_ig_term_doctrine_value",
                     "nd_ig_term_readiness_value", "nd_ig_term_authority_value", "nd_ig_term_strain_value",
                     "nd_ig_term_business_value", "nd_ig_stance_value", "nd_display_stance_months_left"):
            self.assertRegex(self.values, rf"(?m)^{name} = \{{", name)

    def test_store_writes_and_clear_removes_every_variable(self):
        store = block(self.effects, "nd_ig_store_opinion")
        clear = block(self.effects, "nd_ig_clear_opinion")
        for var in IG_VARS:
            self.assertIn(f"name = {var} value", store, var)
            self.assertIn(f"remove_variable = {var}", clear, var)

    def test_band_reads_the_stored_stance(self):
        band = block(self.effects, "nd_ig_set_band")
        self.assertIn("var:nd_ig_stance >= 2", band)
        self.assertNotIn("owner", band)

    def test_business_terms_do_not_wait_for_tenure(self):
        body = block(self.values, "nd_ig_term_business_value")
        self.assertNotIn("nd_ig_posture_judged", body)
        for name in ("nd_ig_term_doctrine_value", "nd_ig_term_readiness_value",
                     "nd_ig_term_authority_value", "nd_ig_term_strain_value"):
            self.assertIn("nd_ig_posture_judged = yes", block(self.values, name), name)


HOME_LINES = ["nd_home_line_militarist", "nd_home_line_militarist_mild", "nd_home_line_restraint",
              "nd_home_line_restraint_mild", "nd_home_line_officers", "nd_home_line_officers_hawkish",
              "nd_home_line_officers_restrained", "nd_home_line_business", "nd_home_line_business_hawkish",
              "nd_home_line_business_restrained"]
HOME_TERMS = ["nd_home_terms_militarist", "nd_home_terms_restraint", "nd_home_terms_officers",
              "nd_home_terms_business", "nd_home_terms_business_lean"]


class TestAtHome(unittest.TestCase):
    def test_every_class_line_is_printed_and_localised(self):
        body = block(strip_comments(read(EFFECTS)), "nd_home_line")
        for key in HOME_LINES + HOME_TERMS:
            self.assertRegex(body, rf"custom_tooltip_no_bullet = {key}\s", key)
            self.assertIn("THIS.Var('nd_ig_", loc_value(key), key)
        for key in HOME_LINES:
            self.assertIn("[THIS.GetInterestGroup.GetName]", loc_value(key), key)

    def test_list_is_drawn_and_old_rows_are_gone(self):
        gui = read(GUI)
        self.assertIn("nd_home_list_sgui", gui)
        for old in ("nd_w_home_warfighting_value", "nd_w_home_professional_value",
                    "nd_w_home_dove_value", "nd_w_home_business_value"):
            self.assertNotIn(old, gui)
        custom = strip_comments(read(CUSTOM_LOC))
        self.assertNotIn("nd_stance_warfighting_word", custom)

    def test_list_handler_is_display_only(self):
        body = block(strip_comments(read(SGUIS)), "nd_home_list_sgui")
        self.assertIn("is_valid = { always = no }", body)
        self.assertIn("every_interest_group", body)

class TestReviewFixes(unittest.TestCase):
    """Fixes from the PR 1 whole-branch review."""

    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.events = strip_comments(read(CRISIS_EVENTS))
        self.triggers = strip_comments(read(TRIGGERS))
        self.values = strip_comments(read(VALUES))

    def test_outcome_option_applies_when_the_opponent_is_gone(self):
        body = option_body(self.events, "nuclear_crisis.6.a")
        self.assertIn("NOT = { exists = scope:nd_outcome_other }", body)
        self.assertIn("NOT = { exists = var:nd_crisis_pending_opponent }", body)

    def test_opponent_reactions_need_the_live_pending_opponent(self):
        self.assertRegex(self.triggers, r"(?m)^nd_outcome_other_is_live = \{")
        body = block(self.effects, "nd_crisis_apply_outcome_side")
        self.assertNotIn("limit = { exists = scope:nd_outcome_other }", body)
        self.assertIn("nd_outcome_other_is_live = yes", body)

    def test_outcome_notices_pop_up(self):
        body = block(self.effects, "nd_crisis_close")
        self.assertEqual(body.count("trigger_event = { id = nuclear_crisis.6 popup = yes }"), 2)

    def test_every_act_credibility_change_says_its_number(self):
        for m in re.finditer(r"(?m)^((?:nd_crisis_act|nd_guarantee_act)_\w+) = \{", self.effects):
            body = block(self.effects, m.group(1))
            pairs = re.findall(r"text = nd_tt_credibility_(up|down)_(\d+)(?:_bluff)?\s*nd_change_credibility = \{ AMOUNT = (-?\d+) \}", body)
            for direction, n, amount in pairs:
                self.assertEqual(int(amount), int(n) if direction == "up" else -int(n), m.group(1))
            self.assertEqual(body.count("nd_change_credibility"), len(pairs),
                             f"{m.group(1)} changes credibility without its number line")

    def test_guarantee_honour_previews_its_ultimatum(self):
        body = block(self.effects, "nd_guarantee_act_honour")
        hidden = block(body, "hidden_effect")
        self.assertNotIn("nd_crisis_open", hidden)
        self.assertIn("nd_crisis_open = { TARGET = scope:nd_guarantee_attacker PUBLIC = yes }", body)

    def test_exercise_pressure_counts_only_the_issuers(self):
        self.assertIn("var:nd_crisis_exercise_by_issuer = 1", block(self.values, "nd_yp_exercise_value"))
        act = block(self.effects, "nd_crisis_act_exercise")
        self.assertIn("name = nd_crisis_exercise_by_issuer value = 1", act)
        self.assertIn("name = nd_crisis_exercise_by_issuer value = 0", act)
        self.assertIn("remove_variable = nd_crisis_exercise_by_issuer", block(self.effects, "nd_crisis_weekly_tick"))
        self.assertIn("remove_variable = nd_crisis_exercise_by_issuer", block(self.effects, "nd_crisis_clear_vars"))
        incidents = strip_comments(read(INCIDENT_EVENTS))
        self.assertIn("nd_crisis_exercise_by_issuer", option_body(incidents, "nuclear_incident.10.c"))
        self.assertIn("name = nd_crisis_exercise_by_issuer value = 1", option_body(incidents, "nuclear_incident.10.e"))

    def test_preview_charges_only_when_the_crisis_opens(self):
        body = block(self.effects, "nd_crisis_preview")
        gate = body.index("nd_crisis_parties_free = { TARGET = $TARGET$ }")
        self.assertLess(gate, body.index("change_infamy"))
        self.assertLess(gate, body.index("change_relations"))

    def test_refuse_talks_promises_pressure_only_from_confrontation(self):
        body = block(self.effects, "nd_crisis_act_refuse_talks")
        self.assertIn("custom_tooltip = nd_tt_refuse_talks_resume", body)
        self.assertIn("custom_tooltip = nd_tt_refuse_talks_no_pressure_yet", body)
        self.assertIn("6", loc_value("nd_tt_refuse_talks_resume"))

    def test_war_law_tooltips_match_the_exception(self):
        for key in ("nd_tt_war_law_permits_strike", "nd_tt_war_law_permits_tactical_strike"):
            self.assertIn("a war we are fighting", loc_value(key), key)

    def test_ft_reason_2_names_both_doctrines(self):
        self.assertIn("Warfighting", loc_value("nd_ft_reason_2"))

    def test_preview_header_is_pinned_and_points_to_the_journal(self):
        self.assertRegex(block(self.values, "nd_yp_base_value"), r"value = 30\b")
        header = loc_value("nd_tt_open_factors_header")
        self.assertIn("30", header)
        self.assertIn("journal entry", header)


STANCES = ["strongly_disapprove", "disapprove", "neutral", "approve", "strongly_approve", "count"]


def stance_clauses(trigger_body):
    """(negated, law, threshold) for each `law_stance = { law = … value > … }`
    in a trigger body, top-level or under one NOT."""
    out = []
    for m in re.finditer(r"(NOT = \{\s*)?law_stance = \{\s*law = law_type:(\w+)\s*value > (\w+)\s*\}", trigger_body):
        out.append((bool(m.group(1)), m.group(2), m.group(3)))
    return out


def holds(clauses, total, limited):
    for negated, law, threshold in clauses:
        value = total if law == "law_total_war" else limited
        result = STANCES.index(value) > STANCES.index(threshold)
        if result == negated:
            return False
    return True


class TestAtHomeReviewFixes(unittest.TestCase):
    """Fixes from the PR 2 whole-branch review."""

    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))
        self.sguis = strip_comments(read(SGUIS))

    def test_stance_truth_table(self):
        """Spec §4.1 over every pair of stances: the stronger approval of Total
        War or Limited War wins, a tie is no view, and `count` is never
        approval."""
        names = ("nd_stance_militarist_full", "nd_stance_militarist_mild",
                 "nd_stance_restraint_full", "nd_stance_restraint_mild")
        clauses = {n: stance_clauses(block(self.triggers, n)) for n in names}
        for n in names:
            self.assertTrue(clauses[n], n)
        real = STANCES[:5]
        for total in STANCES:
            for limited in STANCES:
                got = [n for n in names if holds(clauses[n], total, limited)]
                self.assertLessEqual(len(got), 1, (total, limited, got))
                if "count" in (total, limited):
                    expected = []
                else:
                    t, l = real.index(total), real.index(limited)
                    expected = []
                    if t > l and t >= 3:
                        expected = ["nd_stance_militarist_full" if t == 4 else "nd_stance_militarist_mild"]
                    elif l > t and l >= 3:
                        expected = ["nd_stance_restraint_full" if l == 4 else "nd_stance_restraint_mild"]
                self.assertEqual(got, expected, (total, limited))

    def test_fixed_class_leans_read_the_leader(self):
        self.assertIn("leader ?= { nd_stance_militarist = yes }", block(self.triggers, "nd_ig_lean_militarist"))
        self.assertIn("leader ?= { nd_stance_restraint = yes }", block(self.triggers, "nd_ig_lean_restraint"))
        self.assertIn("leader ?= { nd_stance_full = yes }", block(self.triggers, "nd_ig_view_full"))

    def test_incident_sites_pay_militarists_including_leans(self):
        text = strip_comments(read(INCIDENT_EVENTS))
        self.assertIn("limit = { nd_ig_is_militarist = yes }", text)
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "events").glob("*.txt")):
            self.assertNotRegex(strip_comments(read(path)), r"nd_ig_stance_(militarist|restraint|full)", path.name)

    def test_footer_follows_the_list_and_always_says_reviewed(self):
        gui = read(GUI)
        self.assertLess(gui.index("nd_home_list_sgui"), gui.index("nd_home_footer_sgui"))
        footer = block(self.sguis, "nd_home_footer_sgui")
        self.assertRegex(footer, r"custom_tooltip_no_bullet = nd_home_list_reviewed\s")
        self.assertIn("custom_tooltip_no_bullet = nd_home_list_waiting", footer)
        self.assertNotIn("nd_home_list_waiting", block(self.sguis, "nd_home_list_sgui"))

    def test_list_before_the_first_review_says_so(self):
        body = block(self.sguis, "nd_home_list_sgui")
        self.assertIn("has_variable = nd_stance_applied", body)
        self.assertIn("custom_tooltip_no_bullet = nd_home_list_not_reviewed", body)


class TestManagedFamilies(unittest.TestCase):
    def test_doctrine_and_readiness_families_exist(self):
        mods = set(re.findall(r"^(nd_\w+)\s*=\s*\{", read(MODIFIERS), re.M))
        for d in range(1, 6):
            self.assertIn(f"nd_doctrine_mod_{d}", mods)
        for r in (2, 3):
            self.assertIn(f"nd_readiness_mod_{r}", mods)
        self.assertIn("nd_upkeep_cost", mods)

    def test_every_family_member_is_removed_by_the_tracker_helpers(self):
        effects = read(EFFECTS)
        remove_doc = block(effects, "nd_remove_doctrine_modifier")
        for d in range(1, 6):
            self.assertIn(f"remove_modifier = nd_doctrine_mod_{d}", remove_doc)
        remove_rd = block(effects, "nd_remove_readiness_modifier")
        for r in (2, 3):
            self.assertIn(f"remove_modifier = nd_readiness_mod_{r}", remove_rd)

    def test_posture_wrappers_exist_for_every_value(self):
        effects = read(EFFECTS)
        for d in range(1, 6):
            self.assertRegex(effects, rf"(?m)^nd_set_doctrine_{d} = \{{")
        for r in range(0, 4):
            self.assertRegex(effects, rf"(?m)^nd_set_readiness_target_{r} = \{{")
        for a in range(1, 5):
            self.assertRegex(effects, rf"(?m)^nd_set_authority_{a} = \{{")

    def test_no_bare_parameterised_calls_remain(self):
        """Callers go through the wrappers, which pass the literal flags the
        core effects branch on (see nd_set_doctrine's header)."""
        for path in SCRIPT_FILES:
            text = strip_comments(read(path))
            for m in re.finditer(r"nd_set_(doctrine|readiness_target|authority) = \{ [DRA] = \d \}", text):
                self.fail(f"{path.name}: {m.group(0)} bypasses the wrapper")


class TestRecessed(unittest.TestCase):
    """Recessed readiness, level 0 (spec 2026-09-25 umbrella/recessed/dead-hand §2)."""

    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))
        self.effects = strip_comments(read(EFFECTS))
        self.crisis = strip_comments(read(CRISIS_EFFECTS))
        self.values = strip_comments(read(VALUES))

    def test_triggers_exist(self):
        for name in ("nd_readiness_recessed", "nd_forces_assembled"):
            self.assertRegex(self.triggers, rf"(?m)^{name} = \{{")

    def test_standdowns_never_raise_a_recessed_country(self):
        # A stand-down sets the target to Routine only when it is above Routine.
        self.assertIn("var:nd_readiness_target > 1", block(self.crisis, "nd_standdown_one_side"))
        concession = self.crisis[self.crisis.index("nd_crisis_programme_freeze"):]
        concession = concession[:concession.index("nd_readiness_lock_months_value")]
        self.assertIn("var:nd_readiness_target > 1", concession)

    def test_stood_down_alert_includes_recessed(self):
        self.assertIn("var:nd_readiness_target <= 1", self.crisis)
        self.assertNotRegex(self.crisis, r"var:nd_readiness_target = 1\b")

    def test_recessed_has_no_readiness_modifier(self):
        # nd_readiness_mod_on uses 0 for "none": a level-0 member could never be tracked.
        self.assertNotIn("nd_readiness_mod_0", read(MODIFIERS))
        self.assertNotIn("nd_readiness_mod_0", self.effects)

    def test_every_readiness_level_has_upkeep_and_a_row(self):
        for r in range(0, 4):
            self.assertRegex(self.values, rf"(?m)^nd_upkeep_weekly_at_readiness_{r} = \{{")
        self.assertIn(20, gui_ops(read(GUI), "nd_posture_sgui"))

    def test_lock_lets_routine_through(self):
        sg = strip_comments(read(SGUIS))
        for op, ok in ((20, "yes"), (21, "yes"), (22, "no"), (23, "no")):
            self.assertIn(f"nd_can_set_readiness = {{ R = {op - 20} LOCK_OK = {ok} }}", sg)
        self.assertIn("always = $LOCK_OK$", block(self.triggers, "nd_can_set_readiness"))

    def test_recessed_is_named_everywhere_a_level_is(self):
        custom = strip_comments(read(CUSTOM_LOC))
        self.assertIn("localization_key = nd_readiness_0", block(custom, "nd_readiness_name"))
        self.assertIn("localization_key = nd_readiness_moving_0", block(custom, "nd_readiness_moving"))
        self.assertIn("nd_readiness_recessed = yes", block(self.values, "nd_incident_permille"))


class TestLaunchGate(unittest.TestCase):
    """Nothing launches from Recessed; a struck recessed country can answer
    once assembled (umbrella/recessed/dead-hand spec §2.3–§2.4)."""

    def test_every_launch_path_needs_assembled_forces(self):
        nuke = strip_comments(read(NUKE))
        for action in ("nuke_diplo_action", "tactical_nuke_diplo_action"):
            self.assertIn("nd_forces_assembled = yes", block(block(nuke, action), "possible"), action)
        t = strip_comments(read(TRIGGERS))
        for name in ("nd_retaliation_permitted", "nd_incident_eligible_commander", "nd_monopoly_window_conditions"):
            self.assertIn("nd_forces_assembled = yes", block(t, name), name)
        e = strip_comments(read(EFFECTS))
        for name in ("nd_dispatch_strategic_strike", "nd_dispatch_tactical_strike"):
            self.assertIn("nd_forces_assembled = yes", block(e, name), name)
        ev = strip_comments(read(CRISIS_EVENTS))
        for opt in ("nuclear_crisis.4.g", "nuclear_crisis.7.a"):
            self.assertIn("nd_forces_assembled = yes", option_body(ev, opt), opt)
        inc = strip_comments(read(INCIDENT_EVENTS))
        ev20 = block(inc, "nuclear_incident.20")
        event_trigger = ev20[re.search(r"(?m)^\ttrigger = \{", ev20).start():]
        self.assertIn("nd_forces_assembled = yes", block(event_trigger, "trigger"))

    def test_struck_while_recessed_can_wait_and_answer(self):
        ev = strip_comments(read(WEAPON_EVENTS))
        self.assertIn("nd_assemble_for_retaliation = { ENEMY = scope:attacking_country }",
                      option_body(ev, "nuclear_weapon_events.1.g"))
        self.assertRegex(ev, r"(?m)^nuclear_weapon_events\.24 = \{")
        weekly = block(strip_comments(read(EFFECTS)), "nd_weekly_update")
        self.assertIn("nd_pending_retaliation", weekly)
        self.assertIn("id = nuclear_weapon_events.24", weekly)
        body = block(ev, "nuclear_weapon_events.24")
        self.assertIn("has_war_with = scope:nd_ready_enemy", block(body, "trigger"))

    def test_assembling_bypasses_the_lock_but_only_raises(self):
        body = block(strip_comments(read(EFFECTS)), "nd_assemble_for_retaliation")
        self.assertIn("var:nd_readiness_target < 1", body)
        self.assertIn("nd_set_readiness_target_1 = yes", body)
        self.assertNotIn("nd_can_set_readiness", body)


class TestAutomaticRetaliation(unittest.TestCase):
    """Authority 4 (umbrella/recessed/dead-hand spec §3)."""

    def setUp(self):
        self.t = strip_comments(read(TRIGGERS))
        self.ev = strip_comments(read(WEAPON_EVENTS))

    def test_authority_triggers(self):
        for name in ("nd_authority_automatic", "nd_can_adopt_automatic_retaliation", "nd_auto_answers_strike"):
            self.assertRegex(self.t, rf"(?m)^{name} = \{{")
        deleg = block(self.t, "nd_authority_delegated_or_warning")
        self.assertNotIn(">= 2", deleg)
        self.assertIn("var:nd_authority = 2", deleg)
        self.assertIn("var:nd_authority = 3", deleg)
        self.assertIn("mainframe_computers", block(self.t, "nd_can_adopt_automatic_retaliation"))
        self.assertIn(34, gui_ops(read(GUI), "nd_posture_sgui"))
        self.assertIn("localization_key = nd_authority_4", block(strip_comments(read(CUSTOM_LOC)), "nd_authority_name"))

    def test_first_strike_is_answered_automatically_and_only_there(self):
        auto = option_body(self.ev, "nuclear_weapon_events.1.e")
        self.assertIn("nd_auto_answers_strike = { ENEMY = scope:attacking_country }", auto)
        for opt in ("nuclear_weapon_events.1.a", "nuclear_weapon_events.1.b", "nuclear_weapon_events.1.c"):
            self.assertIn("nd_auto_answers_strike = { ENEMY = scope:attacking_country }", option_body(self.ev, opt), opt)
        # .11 (being answered) never fires by itself: no loop between two systems.
        self.assertNotIn("nd_auto_answers_strike", block(self.ev, "nuclear_weapon_events.11"))
        self.assertIn("nd_auto_answered_months", block(self.t, "nd_auto_answers_strike"))
        self.assertIn("nd_auto_answer_record", auto)

    def test_salvo_is_sized_before_anything_flies(self):
        auto = option_body(self.ev, "nuclear_weapon_events.1.e")
        # The stock-sized extra warheads come first, so the preview and the
        # run read the same stock; the first warhead flies last.
        self.assertLess(auto.index("var:nuclear_weapon_stockpile >= 3"), auto.index("position = 0"))

    def test_ready_event_answers_automatically_too(self):
        body = block(self.ev, "nuclear_weapon_events.24")
        # Gated on the answer being permitted, not the bare authority: a system
        # barred by a pledge must leave the ordinary options, not none.
        self.assertIn("nd_auto_answers_strike = { ENEMY = scope:attacking_country }",
                      option_body(body, "nuclear_weapon_events.24.e"))
        for opt in ("nuclear_weapon_events.24.a", "nuclear_weapon_events.24.b", "nuclear_weapon_events.24.c"):
            self.assertIn("NOT = { nd_auto_answers_strike = { ENEMY = scope:attacking_country } }",
                          option_body(body, opt), opt)

    def test_accident_branch_goes_through_the_launch_path(self):
        inc = strip_comments(read(INCIDENT_EVENTS))
        self.assertIn("nd_system_reads_attack = yes", block(inc, "nuclear_incident.30"))
        e = block(strip_comments(read(EFFECTS)), "nd_system_reads_attack")
        self.assertIn("KIND = system", e)
        self.assertIn("nd_authority_automatic = yes", e)
        self.assertIn("nd_roll_launch_hold = yes", e)
        self.assertIn("nd_strike_from_incident_of = { KIND = system }", block(self.t, "nd_strike_from_incident"))

    def test_warnings_route_to_the_government(self):
        warn = block(strip_comments(read(EFFECTS)), "nd_start_unconfirmed_warning")
        self.assertIn("nd_authority_launch_on_warning = yes", warn)
        self.assertNotIn("nd_authority_automatic", warn)


if __name__ == "__main__":
    unittest.main()
