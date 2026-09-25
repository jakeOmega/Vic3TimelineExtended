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
        expanded |= {f"nd_tt_readiness_target_{r}" for r in range(1, 4)}
        expanded |= {f"nd_tt_authority_adopted_{a}" for a in range(1, 4)}
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
                  "nd_yp_danger", "nd_yp_exercise", "nd_yp_temperament", "nd_yp_war",
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
        self.assertIn("6", loc_value("nd_tt_act_refuse_talks"))
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
        for r in range(1, 4):
            self.assertRegex(effects, rf"(?m)^nd_set_readiness_target_{r} = \{{")
        for a in range(1, 4):
            self.assertRegex(effects, rf"(?m)^nd_set_authority_{a} = \{{")

    def test_no_bare_parameterised_calls_remain(self):
        """Callers go through the wrappers, which pass the literal flags the
        core effects branch on (see nd_set_doctrine's header)."""
        for path in SCRIPT_FILES:
            text = strip_comments(read(path))
            for m in re.finditer(r"nd_set_(doctrine|readiness_target|authority) = \{ [DRA] = \d \}", text):
                self.fail(f"{path.name}: {m.group(0)} bypasses the wrapper")


if __name__ == "__main__":
    unittest.main()
