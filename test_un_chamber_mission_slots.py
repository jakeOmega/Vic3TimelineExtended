# -*- coding: utf-8 -*-
"""The UN chamber's row tables agree in every copy of them.

Two sections of ``gui/journal_entry_widgets/un_chamber_widget.gui`` draw one
GUI row per entry and pass the entry's number to scripted GUIs as ``op``:

* **Missions in the Field** — one row per display slot (0-7). Every active
  mission holds a slot (``un_mission_assign_slot`` in
  ``common/scripted_effects/un_mission_effects.txt``), and each row asks
  ``un_chamber_mission_slot_sgui`` (is there a mission, and what it is),
  ``un_chamber_mission_join_sgui`` and ``un_chamber_mission_withdraw_sgui``.
* **Voting Details** — one row per archived resolution, newest first,
  through ``un_chamber_history_details_row_sgui``.

Rows rather than one script-built block, because the tooltip engine gathers
every line printed in one country's scope under that country's first
appearance in the block (gui_modding_guide.md gotcha #27): a country serving
in two missions was listed three times under the first and not at all under
the second. Nothing in the engine checks that op 3 means slot 3 in every
switch, or that a row passes one op everywhere; this test does.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
WIDGET = os.path.join(REPO, "gui", "journal_entry_widgets", "un_chamber_widget.gui")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "un_chamber_sguis.txt")
DISPLAY = os.path.join(REPO, "common", "scripted_effects", "un_chamber_display_effects.txt")
MISSION_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_mission_effects.txt")
MISSION_TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "un_mission_triggers.txt")
RESOLUTION_TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "un_resolution_triggers.txt")

MISSION_SLOTS = 8
HISTORY_ROWS = 30

_OP_BRANCH = re.compile(r"limit\s*=\s*\{\s*exists\s*=\s*scope:op\s+scope:op\s*=\s*(\d+)\s*\}")
_WIDGET_OP = re.compile(r"MakeScopeValue\(\s*'\(CFixedPoint\)(\d+)'\s*\)")
_TOP_LEVEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", re.M)


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _braced(text, start):
    """The body of the block whose opening brace is at or after ``start``."""
    i = text.index("{", start)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
    raise AssertionError("block is not closed")


def _block(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    return _braced(text, m.end() - 1)


def _sub_block(text, key):
    m = re.search(r"\b" + re.escape(key) + r"\s*=\s*\{", text)
    if m is None:
        raise AssertionError(f"{key} not found")
    return _braced(text, m.end() - 1)


def _branches(text):
    """``{op: text of that branch}`` for an if/else_if chain switching on scope:op."""
    hits = list(_OP_BRANCH.finditer(text))
    out = {}
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        op = int(m.group(1))
        if op in out:
            raise AssertionError(f"op {op} has two branches")
        out[op] = text[m.end():end]
    return out


def _widget_rows(widget, type_name):
    rows = []
    for m in re.finditer(r"^\t+" + re.escape(type_name) + r"\s*=\s*\{", widget, re.M):
        rows.append([int(op) for op in _WIDGET_OP.findall(_braced(widget, m.end() - 1))])
    return rows


class MissionSlotTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sguis = _read(SGUIS)
        cls.switches = {}
        for sgui in ("un_chamber_mission_slot_sgui", "un_chamber_mission_join_sgui", "un_chamber_mission_withdraw_sgui"):
            body = _block(sguis, sgui)
            cls.switches[(sgui, "is_valid")] = _branches(_sub_block(body, "is_valid"))
            cls.switches[(sgui, "effect")] = _branches(_sub_block(body, "effect"))
        cls.rows = _widget_rows(_read(WIDGET), "un_chamber_mission_row")
        cls.assign = _block(_read(MISSION_EFFECTS), "un_mission_assign_slot")

    def test_the_widget_has_one_row_per_slot(self):
        self.assertEqual(sorted(ops[0] for ops in self.rows), list(range(MISSION_SLOTS)))

    def test_each_row_passes_one_slot_everywhere(self):
        for ops in self.rows:
            # row visible and text; Join visible, enabled, onclick and the
            # tooltip's two calls; Withdraw visible, onclick and tooltip
            self.assertEqual(len(ops), 10, ops)
            self.assertEqual(len(set(ops)), 1, f"a mission row mixes slots {ops}")

    def test_every_switch_maps_op_to_the_same_slot(self):
        expected = {
            ("un_chamber_mission_slot_sgui", "is_valid"): "un_mission_slot_filled",
            ("un_chamber_mission_slot_sgui", "effect"): "un_chamber_mission_slot_entry",
            ("un_chamber_mission_join_sgui", "is_valid"): "un_mission_slot_can_volunteer",
            ("un_chamber_mission_join_sgui", "effect"): "un_mission_slot_volunteer",
            ("un_chamber_mission_withdraw_sgui", "is_valid"): "un_mission_slot_served",
            ("un_chamber_mission_withdraw_sgui", "effect"): "un_mission_slot_withdraw",
        }
        for key, call in expected.items():
            branches = self.switches[key]
            with self.subTest(switch=key):
                self.assertEqual(sorted(branches), list(range(MISSION_SLOTS)))
                for op, branch in branches.items():
                    found = re.findall(r"\b(\w+)\s*=\s*\{\s*SLOT\s*=\s*(\d+)\s*\}", branch)
                    self.assertEqual(found, [(call, str(op))], f"op {op}")

    def test_slots_are_assigned_lowest_first_and_all_of_them(self):
        pairs = re.findall(
            r"un_mission_slot_filled\s*=\s*\{\s*SLOT\s*=\s*(\d+)\s*\}\s*\}\s*\}\s*"
            r"set_variable\s*=\s*\{\s*name\s*=\s*un_msn_slot\s+value\s*=\s*(\d+)\s*\}",
            self.assign,
        )
        self.assertEqual(pairs, [(str(k), str(k)) for k in range(MISSION_SLOTS)])

    def test_every_name_the_switches_call_exists(self):
        defined = set()
        for path in (DISPLAY, MISSION_EFFECTS, MISSION_TRIGGERS):
            defined |= set(_TOP_LEVEL.findall(_read(path)))
        for (sgui, part), branches in self.switches.items():
            for op, branch in branches.items():
                for name in re.findall(r"\b(\w+)\s*=\s*\{\s*SLOT\s*=", branch):
                    with self.subTest(sgui=sgui, part=part, op=op):
                        self.assertIn(name, defined)


class VotingDetailsRowTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        body = _block(_read(SGUIS), "un_chamber_history_details_row_sgui")
        cls.valid = _branches(_sub_block(body, "is_valid"))
        cls.effect = _branches(_sub_block(body, "effect"))
        cls.rows = []
        widget = _read(WIDGET)
        for m in re.finditer(r"un_chamber_text\s*=\s*\{", widget):
            block = _braced(widget, m.end() - 1)
            if "un_chamber_history_details_row_sgui" in block and "ExecuteTooltip" in block:
                cls.rows.append([int(op) for op in _WIDGET_OP.findall(block)])

    def test_the_widget_has_one_row_per_position(self):
        self.assertEqual(sorted(ops[0] for ops in self.rows), list(range(HISTORY_ROWS)))
        for ops in self.rows:
            self.assertEqual(len(ops), 2, ops)
            self.assertEqual(len(set(ops)), 1, ops)

    def test_each_op_reads_its_own_position(self):
        self.assertEqual(sorted(self.valid), list(range(HISTORY_ROWS)))
        self.assertEqual(sorted(self.effect), list(range(HISTORY_ROWS)))
        for op in range(HISTORY_ROWS):
            with self.subTest(op=op):
                self.assertEqual(
                    re.findall(r"un_chamber_history_has_entry\s*=\s*\{\s*COUNT\s*=\s*(\d+)\s*\}", self.valid[op]),
                    [str(op + 1)],
                )
                self.assertEqual(
                    re.findall(
                        r"un_chamber_history_details_row\s*=\s*\{\s*POSITION\s*=\s*(\d+)\s+COUNT\s*=\s*(\d+)\s*\}",
                        self.effect[op],
                    ),
                    [(str(op), str(op + 1))],
                )

    def test_the_names_exist(self):
        self.assertIn("un_chamber_history_details_row", set(_TOP_LEVEL.findall(_read(DISPLAY))))
        self.assertIn("un_chamber_history_has_entry", set(_TOP_LEVEL.findall(_read(RESOLUTION_TRIGGERS))))


class MissionContributorLinesTest(unittest.TestCase):
    """A mission's contributors print from the mission's scope (gotcha #27)."""

    @classmethod
    def setUpClass(cls):
        display = _read(DISPLAY)
        cls.entry = _block(display, "un_chamber_mission_entry")
        cls.at = _block(display, "un_chamber_mission_contributor_at")

    def test_no_line_is_printed_inside_a_contributor_scope(self):
        self.assertNotRegex(self.entry, r"\bevery_in_list\b")
        # The one printing line of the helper sits after the iterator closes.
        iterator = _sub_block(self.at, "ordered_in_list")
        self.assertNotIn("custom_tooltip", iterator)

    def test_positions_and_counts_line_up(self):
        calls = re.findall(
            r"un_chamber_mission_contributor_at\s*=\s*\{\s*POSITION\s*=\s*(\d+)\s+COUNT\s*=\s*(\d+)\s*\}",
            self.entry,
        )
        self.assertEqual(calls, [(str(k), str(k + 1)) for k in range(len(calls))])
        more = re.search(r"count\s*>=\s*(\d+)\s+exists\s*=\s*this\s*\}\s*\}\s*custom_tooltip_no_bullet\s*=\s*je_un_chamber_mission_contributors_more", self.entry)
        self.assertIsNotNone(more)
        self.assertEqual(int(more.group(1)), len(calls) + 1)


if __name__ == "__main__":
    unittest.main()
