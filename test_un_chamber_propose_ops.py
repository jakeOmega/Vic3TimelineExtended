# -*- coding: utf-8 -*-
"""The UN chamber's "Table a Resolution" op table agrees in every copy of it.

Each proposal row in ``gui/journal_entry_widgets/un_chamber_widget.gui`` passes
an ``op`` number to three scripted GUIs, and each of those switches on it in
its own file:

* ``un_chamber_propose_sgui`` ``is_valid`` asks ``un_propose_<key>_available``
  and ``un_propose_<key>_possible``, and its ``effect`` runs
  ``un_propose_<key>_effect``
  (``common/scripted_guis/un_chamber_sguis.txt``);
* ``un_chamber_propose_row_sgui`` renders ``un_chamber_propose_<key>_row``
  (the same file, over ``common/scripted_effects/un_chamber_display_effects.txt``);
* ``un_chamber_propose_ready_sgui`` and ``un_chamber_propose_shelved_sgui``
  decide which of the list's two passes shows the row (the 2026-10-27 audit,
  UN-7): the topics with a case under "Ready to Table", the rest under "No
  Case Now", a topic in force in neither. Each row appears once in each pass.

Nothing in the engine checks that op 12 means the same topic in all of them:
a row whose description says one topic while its button tables another is
engine-silent. The files ask for the table to be kept in step by hand; this
test is what keeps it, and checks that every name the switches call exists.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
WIDGET = os.path.join(REPO, "gui", "journal_entry_widgets", "un_chamber_widget.gui")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "un_chamber_sguis.txt")
DISPLAY = os.path.join(REPO, "common", "scripted_effects", "un_chamber_display_effects.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_propose_effects.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "un_propose_triggers.txt")

_OP_BRANCH = re.compile(r"limit\s*=\s*\{\s*exists\s*=\s*scope:op\s+scope:op\s*=\s*(\d+)\s*\}")
_WIDGET_OP = re.compile(r"MakeScopeValue\(\s*'\(CFixedPoint\)(\d+)'\s*\)")
_TOP_LEVEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", re.M)


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
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


def _sub_block(text, key):
    m = re.search(r"\b" + re.escape(key) + r"\s*=\s*\{", text)
    if m is None:
        raise AssertionError(f"{key} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{key} is not closed")


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


def _one(pattern, branch, what, op):
    found = set(re.findall(pattern, branch))
    if len(found) != 1:
        raise AssertionError(f"op {op}: expected one {what}, found {sorted(found)}")
    return found.pop()


class ChamberProposeOpTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sguis = _read(SGUIS)
        propose = _block(sguis, "un_chamber_propose_sgui")
        cls.valid = _branches(_sub_block(propose, "is_valid"))
        cls.effect = _branches(_sub_block(propose, "effect"))
        cls.row = _branches(_block(sguis, "un_chamber_propose_row_sgui"))
        cls.ready = _branches(_sub_block(_block(sguis, "un_chamber_propose_ready_sgui"), "is_valid"))
        cls.shelved = _branches(_sub_block(_block(sguis, "un_chamber_propose_shelved_sgui"), "is_valid"))

        widget = _read(WIDGET)
        cls.widget_rows = []
        cls.widget_passes = []
        for m in re.finditer(r"^\t+un_chamber_propose_row\s*=\s*\{", widget, re.M):
            body = _sub_block(widget[m.start():], "un_chamber_propose_row")
            cls.widget_rows.append([int(op) for op in _WIDGET_OP.findall(body)])
            cls.widget_passes.append(re.findall(r"un_chamber_propose_(ready|shelved)_sgui", body))

        cls.defined = set()
        for path in (DISPLAY, EFFECTS, TRIGGERS):
            cls.defined |= set(_TOP_LEVEL.findall(_read(path)))

    def test_every_copy_covers_the_same_ops(self):
        half = len(self.widget_rows) // 2
        self.assertEqual(len(self.widget_rows), 2 * half, "the two passes differ in length")
        ready = [ops[0] for ops in self.widget_rows[:half]]
        shelved = [ops[0] for ops in self.widget_rows[half:]]
        self.assertEqual(ready, shelved, "the two passes list the rows in different orders")
        widget_ops = sorted(ready)
        self.assertEqual(widget_ops, sorted(set(widget_ops)), "a widget row is repeated in a pass")
        expected = list(range(len(widget_ops)))
        self.assertEqual(widget_ops, expected, "widget ops are not 0..N-1")
        self.assertEqual(sorted(self.valid), expected)
        self.assertEqual(sorted(self.effect), expected)
        self.assertEqual(sorted(self.row), expected)
        self.assertEqual(sorted(self.ready), expected)
        self.assertEqual(sorted(self.shelved), expected)

    def test_each_widget_row_passes_one_op_everywhere(self):
        for ops in self.widget_rows:
            # row visible, row text, button visible, enabled, onclick, and
            # the tooltip's two calls
            self.assertEqual(len(ops), 7, ops)
            self.assertEqual(len(set(ops)), 1, f"a widget row mixes ops {ops}")

    def test_ready_rows_come_first(self):
        half = len(self.widget_rows) // 2
        for i, passes in enumerate(self.widget_passes):
            with self.subTest(row=i):
                self.assertEqual(passes, ["ready" if i < half else "shelved"])

    def test_the_passes_split_on_the_rows_own_case(self):
        for op in sorted(self.valid):
            with self.subTest(op=op):
                key = _one(r"\bun_propose_(\w+?)_available\b", self.valid[op], "available gate", op)
                self.assertEqual(_one(r"\bun_propose_(\w+?)_available\b", self.ready[op], "ready gate", op), key)
                self.assertEqual(_one(r"\bun_propose_(\w+?)_available\b", self.shelved[op], "shelved gate", op), key)
                self.assertRegex(" ".join(self.shelved[op].split()),
                                 rf"NOT = \{{ un_propose_{key}_available = yes \}}")

    def test_each_op_names_one_topic_in_every_switch(self):
        for op in sorted(self.valid):
            with self.subTest(op=op):
                available = _one(r"\bun_propose_(\w+?)_available\b", self.valid[op], "available gate", op)
                possible = _one(r"\bun_propose_(\w+?)_possible\b", self.valid[op], "possible gate", op)
                effect = _one(r"\bun_propose_(\w+?)_effect\b", self.effect[op], "effect", op)
                row = _one(r"\bun_chamber_propose_(\w+?)_row\b", self.row[op], "row renderer", op)
                self.assertEqual({available, possible, effect, row}, {available}, f"op {op} disagrees")

    def test_every_name_the_switches_call_exists(self):
        for op in sorted(self.valid):
            key = _one(r"\bun_propose_(\w+?)_effect\b", self.effect[op], "effect", op)
            for name in (
                f"un_propose_{key}_available",
                f"un_propose_{key}_possible",
                f"un_propose_{key}_effect",
                f"un_chamber_propose_{key}_row",
            ):
                with self.subTest(op=op, name=name):
                    self.assertIn(name, self.defined)


if __name__ == "__main__":
    unittest.main()
