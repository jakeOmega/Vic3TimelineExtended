"""Tests for starting a culture merge: a journal entry, a start button and a progress bar per merge,
the start, join and release helpers, late joining, and the AI pressing the button.

Files under test:
* common/journal_entries/te_culture_merges_generated.txt (generated)
* common/scripted_buttons/te_culture_merges_generated_buttons.txt (generated)
* common/scripted_progress_bars/te_culture_merges_generated_bars.txt (generated)
* common/script_values/te_culture_merges_generated_values.txt (generated)
* the Task 5 additions to the generated triggers and effects, and the hand-written
  te_cm_start_merge / te_cm_join_part / te_cm_release_starter
  (common/scripted_effects/te_culture_merge_effects.txt)
* common/on_actions/te_culture_merge_on_actions.txt (the release of a lost starter)

The script can't be run offline, so the tests read its text: the shape of each block, the order
of its clauses, and that every name an output uses is defined somewhere.

Run: python3 -m unittest test_culture_merge_entries -v
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import culture_merges_config as cfg  # noqa: E402
import gen_culture_merges as gen  # noqa: E402
import test_add_journal_entry_guard as guard  # noqa: E402
import test_journal_entry_shape as shape  # noqa: E402
from je_multiplier_scope_audit import parse_text  # noqa: E402
from test_culture_merge_census import block, squash, text_of, tier_of, vanilla  # noqa: E402

JE_FILE = ROOT / "common/journal_entries/te_culture_merges_generated.txt"
BUTTONS = ROOT / "common/scripted_buttons/te_culture_merges_generated_buttons.txt"
BARS = ROOT / "common/scripted_progress_bars/te_culture_merges_generated_bars.txt"
VALUES = ROOT / "common/script_values/te_culture_merges_generated_values.txt"
HAND_VALUES = ROOT / "common/script_values/te_culture_merge_values.txt"
DISPLAY_VALUES = ROOT / "common/script_values/te_culture_merge_display_values.txt"
EFFECTS = ROOT / "common/scripted_effects/te_culture_merge_effects.txt"
GEN_EFFECTS = ROOT / "common/scripted_effects/te_culture_merges_generated_effects.txt"
GEN_TRIGGERS = ROOT / "common/scripted_triggers/te_culture_merges_generated_triggers.txt"
ON_ACTIONS = ROOT / "common/on_actions/te_culture_merge_on_actions.txt"
GEN_LOC = ROOT / "localization/english/te_culture_merges_generated_l_english.yml"
MISC_LOC = ROOT / "localization/english/te_miscellaneous_l_english.yml"
VANILLA_LOC = ROOT / "vanilla_parsed/localization_english.json"
NEW_FILES = (JE_FILE, BUTTONS, BARS, VALUES, DISPLAY_VALUES)
BOM = b"\xef\xbb\xbf"


def merge_index(merge):
    return 1 + [m.key for m in cfg.MERGES].index(merge.key)


def slot_cultures(merge):
    return [c for part in merge.core + merge.optional for c in part.cultures]


def absorb_result(merge, culture):
    return merge.new is None and culture == merge.result


def part_of(merge, culture):
    return next(p for p in merge.core + merge.optional if culture in p.cultures)


def idle(key):
    return "NOR = { global_var:te_cm_state_%s ?= 1 global_var:te_cm_state_%s ?= 2 }" % (key, key)


def loc_of(path):
    out = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r'^ (\S+):(\d+) "(.*)"(?:\s*#.*)?$', line)
        if match:
            out[match.group(1)] = match.group(3)
    return out


def defined_loc():
    """Every loc key the mod defines in English (the generated file and the miscellaneous one are enough here)."""
    return {**loc_of(GEN_LOC), **loc_of(MISC_LOC)}


def entry_nodes():
    nodes, _ = parse_text(JE_FILE.read_text(encoding="utf-8-sig"), "te_culture_merges_generated.txt")
    return {n.key: n for n in nodes if n.children}


def je_text(key):
    """The text of one entry (comments and BOM removed), for the checks that need the operators the parser drops."""
    return block(text_of(JE_FILE), "je_te_cm_%s" % key)


def inner(text, header):
    """The body of the first `header = {` in text (any indentation), or None."""
    m = re.search(re.escape(header) + r" = \{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth:
        depth += (text[i] == "{") - (text[i] == "}")
        i += 1
    return text[m.end():i - 1]


def child(node, key):
    return next((c for c in node.children if c.key == key), None)


def children(node, key):
    return [c for c in node.children if c.key == key]


class FilesTest(unittest.TestCase):
    def test_one_bom_tabs_and_header(self):
        for path in NEW_FILES:
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(BOM), path.name)
            self.assertFalse(raw[3:].startswith(BOM), path.name + " has two BOMs")
            lines = raw.decode("utf-8-sig").splitlines()
            for line in lines:
                self.assertFalse(line.startswith(" "), path.name + ": " + line)
            if path is not DISPLAY_VALUES:
                self.assertEqual(lines[0], gen.HEADER, path.name)

    def test_generated_files_are_current(self):
        self.assertFalse(gen.regenerate(dry_run=True)["changed"], "run python3 scripts/generators/gen_culture_merges.py")

    def test_the_new_outputs_are_planned(self):
        planned = set(gen.plan_outputs())
        for path in (JE_FILE, BUTTONS, BARS, VALUES):
            self.assertIn(path.relative_to(ROOT), planned)


class EntryShapeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = entry_nodes()
        cls.triggers = shape.load_triggers()

    def test_entry_shape(self):
        # test_journal_entry_shape's checks over the generated file: no field 1.15 dropped, an activation
        # description, and a disable_evaluation that prunes on a rule conjunct of the gate only.
        self.assertEqual(len(self.entries), len(cfg.MERGES))
        for name, entry in self.entries.items():
            with self.subTest(entry=name):
                self.assertEqual(shape.dropped_fields(entry), [])
                self.assertIsNotNone(shape.child(entry, "activation_description"))
                self.assertEqual(shape.prune_problems(entry, self.triggers), [])

    def test_every_entry_has_a_button_and_bar(self):
        buttons = text_of(BUTTONS)
        bars = text_of(BARS)
        self.assertEqual(set(self.entries), {"je_te_cm_%s" % m.key for m in cfg.MERGES})
        for merge in cfg.MERGES:
            key = merge.key
            entry = self.entries["je_te_cm_%s" % key]
            self.assertEqual([c.value for c in children(entry, "scripted_button")], ["te_cmg_start_%s_button" % key])
            self.assertEqual([c.value for c in children(entry, "scripted_progress_bar")], ["te_cmg_%s_bar" % key])
            self.assertIsNotNone(block(buttons, "te_cmg_start_%s_button" % key), key)
            self.assertIsNotNone(block(bars, "te_cmg_%s_bar" % key), key)
        self.assertEqual(len(re.findall(r"^te_cmg_start_\w+_button = \{", buttons, re.M)), len(cfg.MERGES))
        self.assertEqual(len(re.findall(r"^te_cmg_\w+_bar = \{", bars, re.M)), len(cfg.MERGES))

    def test_the_gate_is_the_rule_then_the_candidate(self):
        # `te_cm_system_enabled = yes` is its own conjunct (test_journal_entry_shape looks for the rule among
        # them), then the candidate; the prune is the rule's negation.
        for merge in cfg.MERGES:
            entry = self.entries["je_te_cm_%s" % merge.key]
            shown = [(c.key, c.value) for c in child(entry, "is_shown_when_inactive").children]
            self.assertEqual(shown, [("te_cm_system_enabled", "yes"), ("te_cmg_%s_is_candidate" % merge.key, "yes")])
            prune = child(entry, "disable_evaluation")
            self.assertEqual(squash(text_of_node(prune)), "NOT = { te_cm_system_enabled = yes }")

    def test_possible_is_the_real_conditions_or_the_starter(self):
        for merge in cfg.MERGES:
            key = merge.key
            entry = self.entries["je_te_cm_%s" % key]
            (possible,) = children(entry, "possible")
            (alt,) = possible.children
            self.assertEqual(alt.key, "OR")
            self.assertEqual(
                [(c.key, c.value) for c in alt.children],
                [("te_cmg_%s_can_start" % key, "yes"), ("te_cmg_%s_is_starter" % key, "yes")],
            )

    def test_stays_active_and_follows_a_revolution(self):
        for name, entry in self.entries.items():
            self.assertEqual(child(entry, "can_deactivate").value, "no", name)
            self.assertEqual(child(entry, "can_revolution_inherit").value, "yes", name)
            self.assertEqual(child(entry, "group").value, "je_group_internal_affairs", name)
            self.assertEqual(child(entry, "progressbar").value, "no", name)
            self.assertEqual(child(entry, "should_be_pinned_by_default_uninvolved_or_context").value, "yes", name)

    def test_a_complete_outcome_for_the_starter_and_a_silent_one_for_another_country(self):
        for merge in cfg.MERGES:
            key = merge.key
            entry = self.entries["je_te_cm_%s" % key]
            complete, invalid = children(entry, "outcome")
            # Complete first: when two are true on the same update the first declared wins.
            self.assertEqual(
                squash(text_of_node(child(complete, "trigger"))),
                # (the parsed tree keeps no operator: `?= 2` reads `= 2`)
                "te_cmg_%s_is_starter = yes global_var:te_cm_state_%s = 2" % (key, key),
            )
            self.assertEqual(child(complete, "conclusion_desc").value, "je_te_cm_%s_complete_conclusion_desc" % key)
            self.assertIsNone(child(complete, "flags"))
            raw = je_text(key)
            self.assertIn("flags = { hidden invalid_outcome }", raw)
            # R27: no outcome ends the entry for a rule switched off. Off is a pause.
            self.assertEqual(squash(child_text(invalid, "trigger")), "te_cmg_%s_has_other_starter = yes" % key)
            self.assertNotIn("te_cm_system_enabled", text_of_node(invalid))

    def test_the_other_starter_triggers(self):
        triggers = text_of(GEN_TRIGGERS)
        for merge in cfg.MERGES:
            key = merge.key
            running = "OR = { global_var:te_cm_state_%s ?= 1 global_var:te_cm_state_%s ?= 2 }" % (key, key)
            self.assertEqual(
                squash(block(triggers, "te_cmg_%s_is_starter" % key)),
                running + " exists = global_var:te_cm_starter_%s this = global_var:te_cm_starter_%s" % (key, key),
            )
            self.assertEqual(
                squash(block(triggers, "te_cmg_%s_has_other_starter" % key)),
                running + " exists = global_var:te_cm_starter_%s NOT = { this = global_var:te_cm_starter_%s }" % (key, key),
            )

    def test_the_bar_follows_the_progress_each_month_and_pauses_with_the_rule(self):
        for merge in cfg.MERGES:
            key = merge.key
            entry = self.entries["je_te_cm_%s" % key]
            pulse = squash(text_of_node(child(entry, "on_monthly_pulse")))
            self.assertIn("if = { limit = { te_cm_system_enabled = yes }", pulse)
            self.assertIn("set_variable = { name = te_cm_bar_%s value = te_cmg_%s_bar_pct }" % (key, key), pulse)
            self.assertIn(
                "scope:journal_entry = { set_bar_progress = { name = te_cmg_%s_bar value = root.var:te_cm_bar_%s } }" % (key, key),
                pulse,
            )
            self.assertLess(pulse.index("set_variable"), pulse.index("set_bar_progress"))

    def test_an_entry_never_resets_state_in_immediate(self):
        # Merge state is global variables a revolution's winner keeps; an entry with an `immediate` could reset it.
        for name, entry in self.entries.items():
            self.assertIsNone(child(entry, "immediate"), name)


def child_text(node, key):
    return text_of_node(child(node, key))


def text_of_node(node):
    """A parsed node's children as flat script text (enough to compare shapes)."""
    parts = []

    def walk(n):
        if n.children:
            parts.append("%s = {" % n.key)
            for c in n.children:
                walk(c)
            parts.append("}")
        else:
            parts.append("%s = %s" % (n.key, n.value) if n.value is not None else n.key)

    for c in node.children:
        walk(c)
    return " ".join(parts)


class StatusTextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = entry_nodes()
        cls.loc = defined_loc()

    def rows(self, key):
        """(the fallback desc lines, [(desc key, squashed trigger)]) of the entry's status text, from the raw text
        (the parsed tree has no operators)."""
        first_valid = inner(je_text(key), "first_valid")
        rows = []
        rest = first_valid
        while True:
            body = inner(rest, "triggered_desc")
            if body is None:
                break
            desc = re.search(r"desc = (\w+)", body).group(1)
            rows.append((desc, squash(inner(body, "trigger"))))
            rest = rest[rest.index(body) + len(body) + 1:]
        return first_valid, rows

    def test_one_row_per_state_then_the_first_failing_condition(self):
        for merge in cfg.MERGES:
            key = merge.key
            first_valid, rows = self.rows(key)
            descs = [d for d, _ in rows]
            self.assertEqual(descs[0], "je_te_cm_%s_status_complete" % key)
            self.assertEqual(descs[1], "je_te_cm_%s_status_running" % key)
            self.assertEqual(descs[2], "te_cm_status_elsewhere")
            self.assertEqual(descs[3:5], ["te_cm_status_not_candidate", "te_cm_status_unmeasured"])
            self.assertEqual(descs[-1], "te_cm_status_ready")
            # The unconditional fallback, after the last row (the only `desc` that no triggered_desc holds).
            self.assertEqual(squash(inner(je_text(key), "first_valid")).split(" desc = ")[-1], "te_cm_status_pending")
            self.assertTrue(first_valid)
            self.assertEqual(len(descs), len(set(descs)), key)
            # The standard-of-living row sits after every core slot and before the component and wait rows.
            sol = descs.index("te_cm_status_sol")
            for index, part in enumerate(merge.core, start=1):
                self.assertLess(descs.index("je_te_cm_%s_status_busy_%d" % (key, index)), sol)
            for component in merge.components:
                self.assertGreater(descs.index("je_te_cm_%s_status_component_%s" % (key, component)), sol)

    def test_running_shows_the_lowest_share_and_the_starters_speed(self):
        # R28: the starter's Culture Merge Speed total, beside the lowest core dominance.
        for merge in cfg.MERGES:
            text = self.loc["je_te_cm_%s_status_running" % merge.key]
            self.assertIn("ScriptValue('te_cmg_%s_lowest_dom')|%%0]" % merge.key, text)
            self.assertIn("ScriptValue('te_cm_speed_display')", text)
            self.assertIn("ScriptValue('te_cm_switch_share')", text)
        values = text_of(DISPLAY_VALUES)
        self.assertEqual(squash(block(values, "te_cm_speed_display")), "value = modifier:country_culture_merge_speed_mult")

    def test_a_failing_core_part_names_its_cause(self):
        # Hold, acceptance and (tiers 1b and 2) years each have a row for each core culture, in that order,
        # reading the variable the census wrote and guarding it with has_variable.
        for merge in cfg.MERGES:
            key = merge.key
            _, rows = self.rows(key)
            by_desc = dict(rows)
            for part in merge.core:
                for culture in part.cultures:
                    held = "te_cm_held_%s_%s" % (key, culture)
                    ok = "te_cm_ok_%s_%s" % (key, culture)
                    hold = by_desc["je_te_cm_%s_status_hold_%s" % (key, culture)]
                    self.assertIn("has_variable = %s var:%s < te_cm_hold_open" % (held, held), hold)
                    accept = by_desc["je_te_cm_%s_status_accept_%s" % (key, culture)]
                    self.assertIn("has_variable = %s var:%s = 0" % (ok, ok), accept)
                    years = "je_te_cm_%s_status_years_%s" % (key, culture)
                    if tier_of(merge, culture) > 1:
                        self.assertIn("NOT = { te_cmg_%s_%s_years_met = yes }" % (key, culture), by_desc[years])
                    else:
                        self.assertNotIn(years, by_desc)
                    # Each row applies only while the slot is unmet, so an earlier slot's failure shows first.
                    self.assertTrue(hold.startswith("NOT = { "), key)
                    descs = [d for d, _ in rows]
                    self.assertLess(
                        descs.index("je_te_cm_%s_status_hold_%s" % (key, culture)),
                        descs.index("je_te_cm_%s_status_accept_%s" % (key, culture)),
                    )

    def test_the_acceptance_line_names_the_threshold_of_its_tier(self):
        text = self.loc["je_te_cm_american_status_accept_yankee"]
        self.assertIn("ScriptValue('te_cm_accept_open')", text)
        # Afro-American is a tier-1b part of American, but optional: no status row. Latin's Spanish is tier 2
        # of the tier-3 merge, held to the usual mark; a tier-1b core part would name the very high one.
        for merge in cfg.MERGES:
            for part in merge.core:
                for culture in part.cultures:
                    text = self.loc["je_te_cm_%s_status_accept_%s" % (merge.key, culture)]
                    want = "te_cm_accept_high_open" if tier_of(merge, culture) == 2 else "te_cm_accept_open"
                    self.assertIn("ScriptValue('%s')" % want, text, "%s %s" % (merge.key, culture))

    def test_a_vanilla_wait_has_a_row_and_a_tooltip(self):
        waits = [(m, p) for m in cfg.MERGES for p in m.core if p.wait_for]
        self.assertEqual([(m.key, p.cultures[0]) for m, p in waits], [("east_slavic", "ukrainian"), ("east_slavic", "byelorussian"), ("american", "dixie")])
        for merge, part in waits:
            key, culture = merge.key, part.cultures[0]
            self.assertIn("je_te_cm_%s_status_wait_%s" % (key, culture), self.loc)
            self.assertIn("te_cmg_%s_wait_%s_tt" % (key, culture), self.loc)
            for entry in part.wait_for:
                self.assertIn("$%s$" % entry, self.loc["je_te_cm_%s_status_wait_%s" % (key, culture)])


class ButtonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = text_of(BUTTONS)

    def test_ai_presses_the_button(self):
        for merge in cfg.MERGES:
            body = squash(block(self.text, "te_cmg_start_%s_button" % merge.key))
            self.assertIn("ai_chance = { value = 100 }", body, merge.key)

    def test_visible_while_idle(self):
        for merge in cfg.MERGES:
            body = squash(block(self.text, "te_cmg_start_%s_button" % merge.key))
            self.assertIn("visible = { %s }" % idle(merge.key), body, merge.key)

    def test_every_entry_point_checks_the_rule(self):
        # R19: off pauses everything. Every on_action and every button's `possible` tests te_cm_system_enabled
        # (a button through its first custom_tooltip, which names the rule), and so do the entry's own gate and
        # the census's net.
        on_actions = text_of(ON_ACTIONS)
        for name in re.findall(r"^(\w+) = \{", on_actions, re.M):
            body = squash(block(on_actions, name))
            if name.startswith("on_"):
                self.assertIn("on_actions = {", body, name)  # a hook: the rule is tested by the action it calls
            else:
                self.assertIn("te_cm_system_enabled = yes", body, name)
        for merge in cfg.MERGES:
            body = squash(block(self.text, "te_cmg_start_%s_button" % merge.key))
            possible = body.split("possible = {", 1)[1]
            self.assertTrue(
                possible.lstrip().startswith("custom_tooltip = { text = te_cm_tt_rule_on te_cm_system_enabled = yes }"),
                merge.key,
            )
        entries = entry_nodes()
        for merge in cfg.MERGES:
            entry = entries["je_te_cm_%s" % merge.key]
            self.assertIn("te_cm_system_enabled", text_of_node(child(entry, "disable_evaluation")))
            self.assertIn("te_cm_system_enabled", text_of_node(child(entry, "is_shown_when_inactive")))
            self.assertIn("te_cm_system_enabled", squash(text_of_node(child(entry, "on_monthly_pulse"))))

    def test_possible_starts_with_the_rule_then_can_start_alone(self):
        for merge in cfg.MERGES:
            body = squash(block(self.text, "te_cmg_start_%s_button" % merge.key))
            self.assertIn(
                "possible = { custom_tooltip = { text = te_cm_tt_rule_on te_cm_system_enabled = yes } "
                "te_cmg_%s_can_start = yes } effect" % merge.key,
                body,
            )

    def test_the_effect_starts_the_merge_under_its_tooltip(self):
        for merge in cfg.MERGES:
            body = squash(block(self.text, "te_cmg_start_%s_button" % merge.key))
            self.assertIn(
                "effect = { custom_tooltip = { text = te_cmg_start_%s_effect_tt te_cmg_start_%s = yes } }" % (merge.key, merge.key),
                body,
            )

    def test_every_condition_has_a_reason_in_its_own_custom_tooltip(self):
        # can_start holds each condition in a custom_tooltip, so no raw script reaches the button's tooltip
        # (button_reason_audit). A bare condition outside one would show as script.
        triggers = text_of(GEN_TRIGGERS)
        for merge in cfg.MERGES:
            for name in ("te_cmg_%s_can_start" % merge.key, "te_cmg_%s_start_basics" % merge.key):
                body = block(triggers, name)
                if body is None:
                    continue
                depth = 0
                for line in body.splitlines():
                    stripped = line.strip()
                    if depth == 0 and stripped and not stripped.startswith(("custom_tooltip = {", "te_cmg_")):
                        self.fail("%s: a bare condition in %s: %s" % (merge.key, name, stripped))
                    depth += line.count("{") - line.count("}")
                self.assertEqual(depth, 0)


class CanStartTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = text_of(GEN_TRIGGERS)

    def items(self, key):
        """The custom_tooltips of can_start (through start_basics), as (text key, squashed body)."""
        body = block(self.triggers, "te_cmg_%s_can_start" % key)
        basics = block(self.triggers, "te_cmg_%s_start_basics" % key)
        text = (basics or "") + "\n" + body
        out = []
        for match in re.finditer(r"custom_tooltip = \{\n\s*text = (\w+)\n", text):
            depth, i = 1, match.end()
            start = i
            while depth:
                depth += (text[i] == "{") - (text[i] == "}")
                i += 1
            out.append((match.group(1), squash(text[start:i - 1])))
        return out

    def test_the_conditions_are_the_candidates_the_slots_the_gap_and_the_components(self):
        for merge in cfg.MERGES:
            key = merge.key
            items = self.items(key)
            texts = [t for t, _ in items]
            tier = max(tier_of(merge, p.cultures[0]) for p in merge.core)
            self.assertEqual(
                texts[:3 + len(merge.core)],
                ["te_cm_tt_idle", "te_cmg_%s_primary_tt" % key, "te_cm_tt_tech_%d" % tier]
                + ["te_cmg_%s_core_%d_tt" % (key, i) for i in range(1, len(merge.core) + 1)],
                key,
            )
            tail = texts[3 + len(merge.core):]
            waits = ["te_cmg_%s_wait_%s_tt" % (key, p.cultures[0]) for p in merge.core if p.wait_for]
            self.assertEqual(
                tail,
                ["te_cm_tt_sol"] + ["te_cmg_%s_comp_%s_tt" % (key, c) for c in merge.components] + waits,
                key,
            )
            by_text = dict(items)
            self.assertEqual(by_text["te_cm_tt_idle"], idle(key))
            self.assertEqual(by_text["te_cm_tt_sol"], "var:te_cm_sol_ok_%s ?= 1" % key)
            for component in merge.components:
                self.assertEqual(by_text["te_cmg_%s_comp_%s_tt" % (key, component)], "global_var:te_cm_state_%s ?= 2" % component)

    def test_can_start_restates_the_candidates_tests_and_core_oks_slots(self):
        # is_candidate and core_ok are Task 4's, can_start restates them in tooltips; they must not drift.
        for merge in cfg.MERGES:
            key = merge.key
            by_text = dict(self.items(key))
            candidate = squash(block(self.triggers, "te_cmg_%s_is_candidate" % key))
            primary = by_text["te_cmg_%s_primary_tt" % key]
            self.assertIn(primary, candidate, key)
            self.assertIn(by_text["te_cm_tt_tech_%d" % max(tier_of(merge, p.cultures[0]) for p in merge.core)], candidate, key)
            core_ok = squash(block(self.triggers, "te_cmg_%s_core_ok" % key))
            slots = " ".join(by_text["te_cmg_%s_core_%d_tt" % (key, i)] for i in range(1, len(merge.core) + 1))
            self.assertEqual(slots, core_ok, key)

    def test_waits_are_capped(self):
        # Each wait-listed vanilla entry on a core part is in can_start, OR'd with the cap.
        for merge in cfg.MERGES:
            key = merge.key
            body = squash(block(self.triggers, "te_cmg_%s_can_start" % key))
            counter = "te_cm_wait_years_%s" % key
            for part in merge.core:
                for entry in part.wait_for:
                    self.assertIn("has_journal_entry = %s" % entry, body, key)
                if part.wait_for:
                    self.assertIn(
                        "text = te_cmg_%s_wait_%s_tt OR = { NOT = { has_journal_entry = %s } AND = { has_variable = %s "
                        "trigger_if = { limit = { has_variable = %s } var:%s >= te_cm_wait_cap_years } } }"
                        % (key, part.cultures[0], part.wait_for[0], counter, counter, counter),
                        body,
                        key,
                    )
            if not any(p.wait_for for p in merge.core):
                self.assertNotIn("te_cm_wait_cap_years", body, key)
                self.assertIsNone(block(self.triggers, "te_cmg_%s_start_basics" % key), key)
        # An optional part's wait never gates the start (American's Afro-American, Anglophone's two).
        self.assertNotIn("je_acw_equality", block(self.triggers, "te_cmg_american_can_start"))
        self.assertNotIn("je_acw_reincorporate", block(self.triggers, "te_cmg_anglophone_can_start"))

    def test_a_waiting_part_is_waiting_only_until_the_cap(self):
        for merge in cfg.MERGES:
            for culture in slot_cultures(merge):
                waiting = block(self.triggers, "te_cmg_%s_%s_waiting" % (merge.key, culture))
                wait_for = part_of(merge, culture).wait_for
                if not wait_for or absorb_result(merge, culture):
                    self.assertIsNone(waiting, "%s %s" % (merge.key, culture))
                    continue
                flat = squash(waiting)
                counter = "te_cm_wait_years_%s" % merge.key
                self.assertTrue(flat.startswith("has_journal_entry = %s NOT = { AND = { has_variable = %s" % (wait_for[0], counter)), flat)
                self.assertIn("var:%s >= te_cm_wait_cap_years" % counter, flat)

    def test_colonial_holders_cannot_start(self):
        # A holder of Javan, Malay, Sumatran or Bornean as colonial subjects has none of them as a primary
        # culture: the Dutch East Indies' owner is not an Indonesian candidate.
        body = squash(block(self.triggers, "te_cmg_indonesian_is_candidate"))
        self.assertIn("country_has_primary_culture = cu:javan", body)
        self.assertIn("OR = { country_has_primary_culture = cu:javan", body)
        self.assertNotIn("culture_percent_country", body)
        primary = dict(self.items("indonesian"))["te_cmg_indonesian_primary_tt"]
        self.assertIn(primary, body)

    def test_a_candidate_start_is_idle(self):
        # A running or complete merge can't be started a second time, from the entry or the button.
        for merge in cfg.MERGES:
            self.assertEqual(self.items(merge.key)[0], ("te_cm_tt_idle", idle(merge.key)))


class HelpersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = text_of(EFFECTS)

    def test_start_merge(self):
        body = squash(block(self.text, "te_cm_start_merge"))
        self.assertEqual(
            body,
            "set_global_variable = { name = te_cm_state_$MERGE$ value = 1 } "
            "set_global_variable = { name = te_cm_starter_$MERGE$ value = this } "
            "if = { limit = { NOT = { country_has_primary_culture = cu:$RESULT$ } } add_primary_culture = cu:$RESULT$ }",
        )

    def test_join_part(self):
        body = squash(block(self.text, "te_cm_join_part"))
        self.assertEqual(
            body,
            "set_global_variable = { name = te_cm_joined_$MERGE$_$CULTURE$ value = 1 } "
            "set_global_variable = { name = te_cm_in_$CULTURE$ value = $INDEX$ }",
        )

    def test_release_goes_back_to_idle_and_keeps_everything_else(self):
        body = squash(block(self.text, "te_cm_release_starter"))
        self.assertEqual(
            body,
            "set_global_variable = { name = te_cm_state_$MERGE$ value = 0 } "
            "if = { limit = { has_global_variable = te_cm_starter_$MERGE$ } remove_global_variable = te_cm_starter_$MERGE$ }",
        )
        # Joined parts, dominance and counters stay: nothing but the starter is removed or unset.
        self.assertEqual(body.count("remove_global_variable"), 1)
        for kept in ("te_cm_joined_", "te_cm_in_", "te_cm_dom_", "te_cm_years_", "te_cm_wait_years_", "te_cm_home_"):
            self.assertNotIn(kept, body)

    def test_the_helpers_use_the_variables_the_gates_read(self):
        # Every global the helpers write is one the generated triggers read, spelled the same way.
        triggers = text_of(GEN_TRIGGERS)
        self.assertIn("global_var:te_cm_state_german ?= 1", triggers)
        self.assertIn("global_var:te_cm_starter_german", triggers)
        self.assertIn("global_var:te_cm_joined_german_north_german ?= 1", triggers)
        self.assertIn("global_var:te_cm_in_yankee ?= 12", triggers)

    def test_no_helper_takes_an_argument_it_never_names(self):
        for name, args in (
            ("te_cm_start_merge", ("MERGE", "RESULT")),
            ("te_cm_join_part", ("MERGE", "CULTURE", "INDEX")),
            ("te_cm_release_starter", ("MERGE",)),
        ):
            body = block(self.text, name)
            for arg in args:
                self.assertIn("$%s$" % arg, body, name + " " + arg)
        self.assertNotIn("$INDEX$", block(self.text, "te_cm_start_merge"))

    def test_every_call_matches_its_helper(self):
        import script_argument_audit

        result = script_argument_audit.audit(mod_path=str(ROOT), vanilla_game=None)
        mine = {str(p.relative_to(ROOT)) for p in (EFFECTS, GEN_EFFECTS, GEN_TRIGGERS, ON_ACTIONS, BUTTONS, JE_FILE)}
        self.assertEqual([(f.file, f.line, f.callee) for f in result.flags if f.file in mine], [])
        called = {name for name, calls in result.call_sites.items() if any(c.file in mine for c in calls)}
        for helper in ("te_cm_start_merge", "te_cm_join_part", "te_cm_release_starter"):
            self.assertIn(helper, called, helper)


class StarterLossTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = text_of(GEN_EFFECTS)
        cls.on_actions = text_of(ON_ACTIONS)

    def test_starter_loss_returns_merge_to_idle(self):
        # The yearly on_action runs the release of every running merge whose starter no longer exists, first.
        flat = squash(block(self.on_actions, "te_cm_yearly_on_action"))
        self.assertIn("te_cmg_release_lost_starters = yes", flat)
        self.assertLess(flat.index("te_cmg_release_lost_starters = yes"), flat.index("te_cmg_census_all = yes"))
        self.assertEqual(flat.count("te_cmg_release_lost_starters = yes"), 1)
        body = squash(block(self.effects, "te_cmg_release_lost_starters"))
        for merge in cfg.MERGES:
            key = merge.key
            self.assertEqual(body.count("te_cm_release_starter = { MERGE = %s }" % key), 1, key)
            self.assertIn(
                "if = { limit = { global_var:te_cm_state_%s ?= 1 OR = { NOT = { exists = global_var:te_cm_starter_%s } "
                "AND = { exists = global_var:te_cm_starter_%s global_var:te_cm_starter_%s = { is_country_alive = no } } } } "
                "te_cm_release_starter = { MERGE = %s } }" % (key, key, key, key, key),
                body,
                key,
            )

    def test_a_dead_starter_is_released_as_well_as_a_missing_one(self):
        # The task 4 review: a country that lost every state still resolves, so its absence can't be the only test.
        body = squash(block(self.effects, "te_cmg_release_lost_starters"))
        self.assertEqual(body.count("is_country_alive = no"), len(cfg.MERGES))
        self.assertEqual(body.count("NOT = { exists = global_var:te_cm_starter_"), len(cfg.MERGES))

    def test_only_a_running_merge_is_released(self):
        # A complete merge keeps its state with its starter gone; releasing it would let the merge start twice.
        body = squash(block(self.effects, "te_cmg_release_lost_starters"))
        self.assertNotIn("?= 2", body)

    def test_losing_the_result_as_primary_is_not_a_release(self):
        body = squash(block(self.effects, "te_cmg_release_lost_starters"))
        self.assertNotIn("country_has_primary_culture", body)

    def test_the_release_runs_behind_the_rule_and_the_year(self):
        flat = squash(block(self.on_actions, "te_cm_yearly_on_action"))
        self.assertLess(flat.index("te_cm_system_enabled = yes"), flat.index("te_cmg_release_lost_starters = yes"))
        self.assertLess(flat.index("name = te_cm_census_year"), flat.index("te_cmg_release_lost_starters = yes"))


class CensusTailTest(unittest.TestCase):
    """What the per-country census does after the gates: wait years, the entry net, late joins."""

    @classmethod
    def setUpClass(cls):
        cls.effects = text_of(GEN_EFFECTS)

    def settle(self, key):
        return squash(block(self.effects, "te_cmg_%s_settle" % key))

    def test_the_census_ends_in_the_settle_of_its_merge(self):
        for merge in cfg.MERGES:
            body = squash(block(self.effects, "te_cmg_census_%s_country" % merge.key))
            self.assertTrue(body.endswith("te_cmg_%s_settle = yes" % merge.key), merge.key)
            self.assertEqual(body.count("_settle = yes"), 1)

    def test_late_joining_runs_for_the_starter_of_a_running_or_complete_merge(self):
        for merge in cfg.MERGES:
            key = merge.key
            self.assertTrue(
                self.settle(key).endswith("if = { limit = { te_cmg_%s_is_starter = yes } te_cmg_%s_join_ready = yes }" % (key, key)), key
            )

    def test_join_ready_joins_each_qualifying_part_that_isnt_waiting_and_never_the_result(self):
        for merge in cfg.MERGES:
            key = merge.key
            body = squash(block(self.effects, "te_cmg_%s_join_ready" % key))
            for culture in slot_cultures(merge):
                call = "te_cm_join_part = { MERGE = %s CULTURE = %s INDEX = %d }" % (key, culture, merge_index(merge))
                if absorb_result(merge, culture):
                    self.assertNotIn("CULTURE = %s " % culture, body, key)
                    continue
                waiting = ""
                if part_of(merge, culture).wait_for:
                    waiting = " NOT = { te_cmg_%s_%s_waiting = yes }" % (key, culture)
                self.assertIn(
                    "if = { limit = { te_cmg_%s_%s_can_join = yes%s } %s }" % (key, culture, waiting, call), body, "%s %s" % (key, culture)
                )
            self.assertEqual(body.count("te_cm_join_part"), len([c for c in slot_cultures(merge) if not absorb_result(merge, c)]))

    def test_the_index_is_the_position_in_the_roster(self):
        # te_cm_in_<c> holds it, and te_cmg_<m>_<c>_available tests the others' (Task 4).
        triggers = text_of(GEN_TRIGGERS)
        index = merge_index(cfg.merge_by_key("american"))
        self.assertEqual(index, 12)
        self.assertIn("te_cm_in_yankee ?= %d" % index, triggers)
        self.assertIn("INDEX = %d" % index, squash(block(self.effects, "te_cmg_american_join_ready")))

    def test_the_button_starts_then_joins(self):
        for merge in cfg.MERGES:
            key = merge.key
            self.assertEqual(
                squash(block(self.effects, "te_cmg_start_%s" % key)),
                "te_cm_start_merge = { MERGE = %s RESULT = %s } te_cmg_%s_join_ready = yes" % (key, merge.result, key),
            )

    def test_a_wait_year_counts_once_a_census_while_the_merge_could_start_and_an_entry_is_open(self):
        for merge in cfg.MERGES:
            key = merge.key
            body = self.settle(key)
            counter = "te_cm_wait_years_%s" % key
            waits = [p for p in merge.core if p.wait_for]
            if not waits:
                self.assertNotIn(counter, body, key)
                continue
            opened = "OR = { %s }" % " ".join("has_journal_entry = %s" % p.wait_for[0] for p in waits)
            self.assertTrue(all(len(p.wait_for) == 1 for p in waits), "a part with two entries nests an OR; extend the test")
            self.assertTrue(
                body.startswith(
                    "if = { limit = { te_cmg_%s_start_basics = yes %s } "
                    "if = { limit = { NOT = { has_variable = %s } } set_variable = { name = %s value = 0 } } "
                    "if = { limit = { var:%s < te_cm_wait_cap_years } change_variable = { name = %s add = 1 } } }"
                    % (key, opened, counter, counter, counter, counter)
                ),
                body,
            )
        # The counter only rises: the one set is to 0 when it is missing, nothing removes it, and the cap is an
        # explicit test (change_variable's own min and max are a guess, change_variable_clamp_audit).
        for path in (EFFECTS, GEN_EFFECTS):
            text = text_of(path)
            self.assertEqual({v for _, v in re.findall(r"set_variable = \{ name = (te_cm_wait_years_\w+) value = (\S+) \}", text)} - {"0"}, set())
            self.assertNotRegex(text, r"remove_variable = te_cm_wait_years")
            self.assertNotRegex(text, r"change_variable = \{[^}]*te_cm_wait_years[^}]*(min|max) =")

    def test_the_entry_net_skips_an_inactive_copy_and_reads_the_entrys_own_gate(self):
        # R20: an idle merge's candidate that can start, or a running merge's starter, gets the entry back if it
        # holds neither the active nor the inactive record.
        for merge in cfg.MERGES:
            key = merge.key
            entry = "je_te_cm_%s" % key
            body = self.settle(key)
            net = (
                "if = { limit = { te_cm_system_enabled = yes NOT = { has_journal_entry = %s } NOT = { has_inactive_journal_entry = %s } "
                "OR = { te_cmg_%s_can_start = yes AND = { global_var:te_cm_state_%s ?= 1 te_cmg_%s_is_starter = yes } } } "
                "add_journal_entry = { type = %s } }" % (entry, entry, key, key, key, entry)
            )
            self.assertIn(net, body, key)
            self.assertEqual(body.count("add_journal_entry"), 1)

    def test_a_complete_merge_gets_no_entry_back(self):
        # Its finished entry is its end; a new one would conclude at once and fire the outcome every year.
        for merge in cfg.MERGES:
            self.assertNotIn("?= 2", self.settle(merge.key), merge.key)

    def test_the_net_passes_the_inactive_copy_guard_test(self):
        flags, stale = guard.audit_text(GEN_EFFECTS.read_text(encoding="utf-8-sig"), "te_culture_merges_generated_effects.txt",
                                        guard.load_entries(), guard.load_triggers())
        self.assertEqual(flags, [])
        self.assertEqual(stale, [])
        text = GEN_EFFECTS.read_text(encoding="utf-8-sig")
        self.assertEqual(text.count("add_journal_entry"), len(cfg.MERGES))
        # And every added type is an entry that exists.
        types = set(re.findall(r"add_journal_entry = \{ type = (\w+) \}", text))
        self.assertEqual(types, {"je_te_cm_%s" % m.key for m in cfg.MERGES})

    def test_merge_mechanics_never_key_on_the_entry(self):
        # R20: has_journal_entry of the merge's own entry appears only in the net, never in a gate or a join.
        for path in (GEN_TRIGGERS, EFFECTS):
            self.assertNotIn("has_journal_entry = je_te_cm_", text_of(path), path.name)
            self.assertNotIn("has_inactive_journal_entry = je_te_cm_", text_of(path), path.name)
        for merge in cfg.MERGES:
            for name in ("te_cmg_census_%s_country" % merge.key, "te_cmg_%s_join_ready" % merge.key, "te_cmg_start_%s" % merge.key):
                self.assertNotIn("je_te_cm_", block(self.effects, name), name)


class ValuesAndBarsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = text_of(VALUES)
        cls.bars = text_of(BARS)

    def test_progress_is_the_lowest_share_over_the_switch_share_capped_at_one(self):
        for merge in cfg.MERGES:
            key = merge.key
            core = [c for p in merge.core for c in p.cultures if not absorb_result(merge, c)]
            progress = squash(block(self.values, "te_cmg_%s_progress" % key))
            joined = " ".join("global_var:te_cm_joined_%s_%s ?= 1" % (key, c) for c in core)
            self.assertEqual(
                progress,
                "value = 0 if = { limit = { OR = { %s } } value = te_cmg_%s_lowest_dom divide = te_cm_switch_share max = 1 }" % (joined, key),
            )
            self.assertEqual(squash(block(self.values, "te_cmg_%s_bar_pct" % key)), "value = te_cmg_%s_progress multiply = 100" % key)

    def test_lowest_share_skips_switched_parts_and_counts_an_unmeasured_one_as_zero(self):
        for merge in cfg.MERGES:
            key = merge.key
            body = squash(block(self.values, "te_cmg_%s_lowest_dom" % key))
            self.assertTrue(body.startswith("value = 1 "), key)
            for culture in [c for p in merge.core for c in p.cultures if not absorb_result(merge, c)]:
                self.assertIn(
                    "if = { limit = { global_var:te_cm_joined_%s_%s ?= 1 NOT = { has_global_variable = te_cm_switched_%s } } "
                    "if = { limit = { has_global_variable = te_cm_dom_%s_%s } max = global_var:te_cm_dom_%s_%s } else = { max = 0 } }"
                    % (key, culture, culture, key, culture, key, culture),
                    body,
                    "%s %s" % (key, culture),
                )
            # Only core parts, and never an absorb merge's result (it is never joined).
            for part in merge.optional:
                self.assertNotIn("te_cm_joined_%s_%s " % (key, part.cultures[0]), body, key)

    def test_one_bar_per_merge_from_zero_to_a_hundred(self):
        for merge in cfg.MERGES:
            body = squash(block(self.bars, "te_cmg_%s_bar" % merge.key))
            self.assertEqual(
                body,
                'name = "te_cm_bar_name" desc = "te_cm_bar_desc" default_green = yes start_value = 0 min_value = 0 max_value = 100',
            )


class LocTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = defined_loc()
        cls.vanilla = json.loads(VANILLA_LOC.read_text(encoding="utf-8"))
        cls.generated = loc_of(GEN_LOC)

    def test_every_key_the_new_files_name_is_defined(self):
        used = set()
        je = JE_FILE.read_text(encoding="utf-8-sig")
        used.update(re.findall(r"\bdesc = (\w+)", je))
        used.update(re.findall(r"conclusion_desc = (\w+)", je))
        used.update(re.findall(r"\b(?:header|effect_header) = (\w+)", je))
        buttons = BUTTONS.read_text(encoding="utf-8-sig")
        used.update(re.findall(r'(?:name|desc) = "(\w+)"', buttons))
        used.update(re.findall(r"text = (\w+)", buttons))
        used.update(re.findall(r'(?:name|desc) = "(\w+)"', BARS.read_text(encoding="utf-8-sig")))
        used.update(re.findall(r"text = (\w+)", GEN_TRIGGERS.read_text(encoding="utf-8-sig")))
        # The two standard headers are vanilla's.
        vanilla_keys = {"je_standard_completion_header", "je_standard_on_completion_header"}
        self.assertTrue(vanilla_keys <= used)
        missing = sorted(k for k in used - vanilla_keys if k not in self.loc)
        self.assertEqual(missing, [])
        for key in vanilla_keys:
            self.assertIn(key, self.vanilla)

    def test_every_entry_has_a_name_and_a_reason(self):
        for merge in cfg.MERGES:
            self.assertIn("je_te_cm_%s" % merge.key, self.generated)
            self.assertIn("je_te_cm_%s_reason" % merge.key, self.generated)
            self.assertEqual(self.generated["je_te_cm_%s" % merge.key], "Cultural Merge: $%s$" % merge.result)

    def test_every_splice_resolves_and_names_are_spliced_not_spelled(self):
        known = set(self.loc) | set(self.vanilla)
        for key, text in self.generated.items():
            for splice in re.findall(r"\$([\w.\-]+)(?:\|[^$]*)?\$", text):
                self.assertIn(splice, known, "%s splices %s" % (key, splice))
        # A culture's display name never appears in a merge's text: the result and part names are splices.
        names = {merge.new.name for merge in cfg.MERGES if merge.new}
        results = gen.result_loc_keys()
        for key, text in self.generated.items():
            if key in results:
                continue
            plain = re.sub(r"\$[\w.\-]+\$|\[[^\]]*\]", "", text)
            for name in names:
                self.assertNotIn(name, plain, key)

    def test_script_values_in_the_text_exist(self):
        defined = set()
        for path in (VALUES, HAND_VALUES, DISPLAY_VALUES):
            defined.update(re.findall(r"^(\w+) = ", text_of(path), re.M))
        vanilla_values = json.loads((ROOT / "vanilla_parsed/common/script_values.json").read_text(encoding="utf-8"))
        defined.update(vanilla_values)
        for key, text in {**self.generated, **{k: v for k, v in self.loc.items() if k.startswith("te_cm_")}}.items():
            for name in re.findall(r"ScriptValue\('(\w+)'\)", text):
                self.assertIn(name, defined, "%s reads %s" % (key, name))

    def test_variables_in_the_text_are_ones_the_census_writes(self):
        census = text_of(EFFECTS) + text_of(GEN_EFFECTS)
        for key, text in self.generated.items():
            for name in re.findall(r"Var\('(\w+)'\)", text):
                self.assertTrue(name.startswith(("te_cm_held_", "te_cm_years_")), "%s reads %s" % (key, name))
        self.assertIn("te_cm_held_$MERGE$_$CULTURE$", census)
        self.assertIn("te_cm_years_$MERGE$_$CULTURE$", census)

    def test_text_is_american_and_uses_the_house_markup(self):
        for key, text in {**self.generated, **{k: v for k, v in self.loc.items() if k.startswith("te_cm_")}}.items():
            self.assertNotIn("[b]", text, key)
            self.assertNotIn("\\n", text, key)
            self.assertNotRegex(text, r"\b(?:colour|favour|organis|recognis|neighbour|centre|defence|labour)", key)

    def test_the_number_in_the_bar_text_is_the_switch_share(self):
        self.assertIn("ScriptValue('te_cm_switch_share')|%0]", self.loc["te_cm_bar_desc"])
        values = text_of(HAND_VALUES)
        self.assertIn("te_cm_switch_share = 0.667", values)

    def test_the_tech_lines_name_the_tier_technologies(self):
        for tier, tech in ((1, "pan-nationalism"), (2, "mass_media"), (3, "television")):
            self.assertEqual(self.loc["te_cm_tt_tech_%d" % tier], "$%s$ is researched." % tech)
        triggers = text_of(ROOT / "common/scripted_triggers/te_culture_merge_triggers.txt")
        for tier, tech in ((1, "pan-nationalism"), (2, "mass_media"), (3, "television")):
            self.assertIn("te_cm_tier_tech_%d = {\n\thas_technology_researched = %s\n}" % (tier, tech), triggers)

    def test_hand_written_phrases_file_in_the_miscellaneous_loc(self):
        import organize_loc

        for key in self.loc:
            if key.startswith("te_cm_"):
                self.assertEqual(organize_loc.categorize_key(key, set()), "MISCELLANEOUS", key)
        for key in self.generated:
            self.assertEqual(organize_loc.categorize_key(key, set()), "CULTURE_MERGES_GENERATED", key)


class ThePlanTest(unittest.TestCase):
    def test_entry_keys_do_not_collide_with_result_keys(self):
        self.assertFalse(set(gen.entry_loc(vanilla())) & gen.result_loc_keys())

    def test_each_row_key_is_unique_to_its_merge(self):
        seen = {}
        for merge in cfg.MERGES:
            for row in gen.status_rows(merge, vanilla(), cfg.MERGES):
                if row.text is None:
                    continue
                self.assertNotIn(row.key, seen, row.key)
                seen[row.key] = merge.key

    def test_a_loc_text_cannot_hold_a_quote_mark(self):
        broken = (cfg.Merge("x", "cm_x", cfg.NewCulture('X"', (1, 2, 3)), core=(cfg.Part(("north_german",)), cfg.Part(("south_german",)))),)
        with self.assertRaises(ValueError):
            gen.render_loc(gen.build_plan(vanilla(), broken))


if __name__ == "__main__":
    unittest.main()
