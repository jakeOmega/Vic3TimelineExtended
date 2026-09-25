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
JE = ROOT / "common/journal_entries/je_nuclear_deterrence.txt"
CRISIS_EVENTS = ROOT / "events/nuclear_crisis_events.txt"
INCIDENT_EVENTS = ROOT / "events/nuclear_incident_events.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_deterrence_events.txt"
JE_DOC = ROOT / "docs/systems/journal_entry_systems.md"
LOC_DIR = ROOT / "localization/english"

# `trigger_event = { id = X }`, or nd_crisis_send_event's EVENT parameter.
FIRED = r"\b(?:id|EVENT) = ([a-z_]+\.\d+)"

SCRIPT_FILES = (EFFECTS, CRISIS_EFFECTS, TRIGGERS, ACTIONS, ARTICLE, JE, SGUIS,
                CRISIS_EVENTS, INCIDENT_EVENTS, DEBUG_EVENTS)
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
    """The body of the first `name = { ... }` block that opens a line."""
    m = re.search(r"^[ \t]*" + re.escape(name) + r"\s*=\s*\{", text, re.M)
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
        expanded |= {"nd_tt_crisis_opens_yes", "nd_tt_crisis_opens_no"}
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

    def test_journal_entry_keys(self):
        self.assert_keys({"je_nuclear_deterrence", "je_nuclear_deterrence_reason",
                          "je_nuclear_deterrence_status"}, JE.name)


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
